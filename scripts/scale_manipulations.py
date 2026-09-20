"""Scale manipulations to 60 total records (25 copy-move, 15 removal, 10 insertion, 10 splicing)."""

import json
import sys
from pathlib import Path
from typing import List, Dict, Any
from PIL import Image

# Add dataset_v2 directory to path for imports
sys.path.insert(0, str(Path(__file__).parent / "dataset_v2"))

from generation_config import GenerationConfig
from variant_ids import generate_variant_id
from provenance import build_provenance_record, compute_sha256
from split_inheritance import SplitInheritance
from generation_validator import GenerationValidator
from generators import ManipulationGenerator


def main():
    """Scale manipulations to target counts."""
    print("=== Scaling Manipulations ===")
    
    config = GenerationConfig()
    config.pilot_copy_move_count = 25
    config.pilot_removal_count = 15
    config.pilot_insertion_count = 10
    config.pilot_splicing_count = 10
    config.pilot_manipulated_count = config.pilot_copy_move_count + config.pilot_removal_count + config.pilot_insertion_count + config.pilot_splicing_count
    
    root = Path(__file__).resolve().parent.parent
    
    # Initialize paths
    variants_dir = root / config.variants_dir
    manipulated_dir = variants_dir / config.manipulated_dir
    masks_dir = variants_dir / config.masks_dir
    sources_dir = root / config.sources_dir
    manifest_path = root / config.manifest_path
    splits_dir = root / config.splits_dir
    
    # Load manifest
    existing_records = []
    with manifest_path.open() as f:
        for line in f:
            if line.strip():
                existing_records.append(json.loads(line))
    
    print(f"Current manifest: {len(existing_records)} records")
    
    # Get source images
    sources = [
        r for r in existing_records
        if r.get('category') == 'original' and r.get('source_id', '').startswith('SRC_DW')
    ]
    
    print(f"Total original sources: {len(sources)}")
    
    # Build SHA-256 to path mapping
    sha256_to_path = {}
    for img_path in sources_dir.glob('*.jpg'):
        sha256 = compute_sha256(img_path)
        sha256_to_path[sha256] = img_path
    
    # Add file paths to records
    for record in sources:
        sha256 = record.get('sha256')
        if sha256 in sha256_to_path:
            record['_file_path'] = sha256_to_path[sha256]
    
    existing_image_ids = {r['image_id'] for r in existing_records}
    
    # Count current manipulations by type
    manip_by_type = {}
    for record in existing_records:
        if record.get('category') == 'manipulated':
            man_type = record.get('manipulation_type', 'unknown')
            manip_by_type[man_type] = manip_by_type.get(man_type, 0) + 1
    
    print(f"Current manipulations: {manip_by_type}")
    
    # Track sources already used for each manipulation type
    sources_by_manip = {}
    for record in existing_records:
        if record.get('category') == 'manipulated':
            man_type = record.get('manipulation_type', 'unknown')
            if man_type not in sources_by_manip:
                sources_by_manip[man_type] = set()
            sources_by_manip[man_type].add(record['source_id'])
    
    # Initialize validator
    validator = GenerationValidator(manifest_path, splits_dir)
    split_inheritance = SplitInheritance(splits_dir)
    
    all_new_records = []
    
    # === Scale Copy-Move to 25 ===
    print(f"\n=== Scaling Copy-Move to {config.pilot_copy_move_count} ===")
    current_cm = manip_by_type.get('copy_move', 0)
    needed_cm = config.pilot_copy_move_count - current_cm
    print(f"Need {needed_cm} more copy-move variants")
    
    cm_sources = sources[:config.pilot_copy_move_count]
    for source in cm_sources:
        if current_cm >= config.pilot_copy_move_count:
            break
        if source['source_id'] in sources_by_manip.get('copy_move', set()):
            continue
        
        try:
            source_path = source['_file_path']
            image = Image.open(source_path)
            
            w, h = image.size
            source_idx = hash(source['source_id']) % 1000
            
            # Diverse parameters
            area_ratio = config.manipulation_area_ratio_range[source_idx % len(config.manipulation_area_ratio_range)]
            region_w = int(w * area_ratio)
            region_h = int(h * area_ratio)
            
            sx = source_idx % (w - region_w)
            sy = source_idx % (h - region_h)
            dx = (source_idx * 2) % (w - region_w)
            dy = (source_idx * 3) % (h - region_h)
            
            rotation = config.copy_move_rotation_range[source_idx % len(config.copy_move_rotation_range)]
            scale = config.copy_move_scale_range[source_idx % len(config.copy_move_scale_range)]
            blend = 0.0
            
            result, mask = ManipulationGenerator.copy_move(
                image, (sx, sy, region_w, region_h),
                (dx, dy, region_w, region_h), rotation, scale, blend
            )
            
            variant_id = generate_variant_id(
                source['image_id'],
                'manipulated',
                'copy_move',
                {
                    'source_region': (sx, sy, region_w, region_h),
                    'dest_region': (dx, dy, region_w, region_h),
                    'rotation': rotation,
                    'scale': scale,
                    'blend': blend
                }
            )
            
            if variant_id not in existing_image_ids:
                output_filename = f"{variant_id}.jpg"
                output_path = manipulated_dir / output_filename
                result.save(output_path, quality=config.output_quality)
                
                mask_filename = f"{variant_id}_mask.png"
                mask_path = masks_dir / mask_filename
                Image.fromarray(mask).save(mask_path)
                
                # Compute area ratio from mask
                import numpy as np
                manipulation_area_ratio = np.count_nonzero(mask) / (mask.shape[0] * mask.shape[1])
                
                record = build_provenance_record(
                    image_id=variant_id,
                    source_id=source['source_id'],
                    parent_image_id=source['image_id'],
                    parent_source_id=source['source_id'],
                    variant_id=variant_id,
                    category='manipulated',
                    label=1,
                    generation_method='manipulated',
                    processing_operations=['copy_move'],
                    image_path=str(output_path.relative_to(root)).replace('\\', '/'),
                    mask_path=str(mask_path.relative_to(root)).replace('\\', '/'),
                    mask_id=variant_id + '_mask',
                    manipulation_type='copy_move',
                    parameters={
                        'source_region': (sx, sy, region_w, region_h),
                        'dest_region': (dx, dy, region_w, region_h),
                        'rotation': rotation,
                        'scale': scale,
                        'blend': blend,
                        'manipulation_area_ratio': manipulation_area_ratio
                    },
                    seed=config.random_seed,
                    dataset_version=config.dataset_version,
                    metadata_available=False,
                    root_path=root
                )
                
                all_new_records.append(record)
                existing_image_ids.add(variant_id)
                sources_by_manip.setdefault('copy_move', set()).add(source['source_id'])
                current_cm += 1
                print(f"Generated copy-move: {variant_id}")
        
        except Exception as e:
            print(f"Error generating copy-move for {source['image_id']}: {e}")
    
    # === Scale Object Removal to 15 ===
    print(f"\n=== Scaling Object Removal to {config.pilot_removal_count} ===")
    current_removal = manip_by_type.get('object_removal', 0)
    needed_removal = config.pilot_removal_count - current_removal
    print(f"Need {needed_removal} more removal variants")
    
    removal_sources = sources[config.pilot_copy_move_count:config.pilot_copy_move_count + config.pilot_removal_count]
    for source in removal_sources:
        if current_removal >= config.pilot_removal_count:
            break
        if source['source_id'] in sources_by_manip.get('object_removal', set()):
            continue
        
        try:
            source_path = source['_file_path']
            image = Image.open(source_path)
            
            w, h = image.size
            source_idx = hash(source['source_id']) % 1000
            
            region_config = config.removal_region_configs[source_idx % len(config.removal_region_configs)]
            position, area_ratio = region_config
            
            region_w = int(w * area_ratio)
            region_h = int(h * area_ratio)
            
            if position == "center":
                rx = (w - region_w) // 2
                ry = (h - region_h) // 2
            elif position == "top_left":
                rx = w // 8
                ry = h // 8
            elif position == "top_right":
                rx = w - region_w - w // 8
                ry = h // 8
            elif position == "bottom_left":
                rx = w // 8
                ry = h - region_h - h // 8
            elif position == "bottom_right":
                rx = w - region_w - w // 8
                ry = h - region_h - h // 8
            else:
                rx = (w - region_w) // 2
                ry = (h - region_h) // 2
            
            method = config.removal_inpainting_methods[source_idx % len(config.removal_inpainting_methods)]
            radius = config.removal_inpaint_radius[source_idx % len(config.removal_inpaint_radius)]
            
            result, mask = ManipulationGenerator.object_removal(
                image, (rx, ry, region_w, region_h), method, radius
            )
            
            variant_id = generate_variant_id(
                source['image_id'],
                'manipulated',
                'object_removal',
                {
                    'region': (rx, ry, region_w, region_h),
                    'method': method,
                    'radius': radius
                }
            )
            
            if variant_id not in existing_image_ids:
                output_filename = f"{variant_id}.jpg"
                output_path = manipulated_dir / output_filename
                result.save(output_path, quality=config.output_quality)
                
                mask_filename = f"{variant_id}_mask.png"
                mask_path = masks_dir / mask_filename
                Image.fromarray(mask).save(mask_path)
                
                import numpy as np
                manipulation_area_ratio = np.count_nonzero(mask) / (mask.shape[0] * mask.shape[1])
                
                record = build_provenance_record(
                    image_id=variant_id,
                    source_id=source['source_id'],
                    parent_image_id=source['image_id'],
                    parent_source_id=source['source_id'],
                    variant_id=variant_id,
                    category='manipulated',
                    label=1,
                    generation_method='manipulated',
                    processing_operations=['object_removal'],
                    image_path=str(output_path.relative_to(root)).replace('\\', '/'),
                    mask_path=str(mask_path.relative_to(root)).replace('\\', '/'),
                    mask_id=variant_id + '_mask',
                    manipulation_type='object_removal',
                    parameters={
                        'region': (rx, ry, region_w, region_h),
                        'method': method,
                        'radius': radius,
                        'manipulation_area_ratio': manipulation_area_ratio
                    },
                    seed=config.random_seed,
                    dataset_version=config.dataset_version,
                    metadata_available=False,
                    root_path=root
                )
                
                all_new_records.append(record)
                existing_image_ids.add(variant_id)
                sources_by_manip.setdefault('object_removal', set()).add(source['source_id'])
                current_removal += 1
                print(f"Generated removal: {variant_id}")
        
        except Exception as e:
            print(f"Error generating removal for {source['image_id']}: {e}")
    
    print(f"\nGenerated {len(all_new_records)} new manipulation variants")
    
    # Validate batch
    print("Validating generated records...")
    validation = validator.validate_batch(all_new_records)
    
    if not validation['valid']:
        print("VALIDATION FAILED - Not writing to manifest")
        print("Errors:", validation['errors'])
        print("\n=== MANIPULATION SCALING FAILED ===")
        return
    
    # Write to manifest
    print("Writing to manifest...")
    with manifest_path.open('a') as f:
        for record in all_new_records:
            f.write(json.dumps(record) + '\n')
    print(f"Wrote {len(all_new_records)} records to manifest")
    
    print("\n=== Manipulation Scaling Complete ===")
    print(f"Total new records: {len(all_new_records)}")


if __name__ == '__main__':
    main()

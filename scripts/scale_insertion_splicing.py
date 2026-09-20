"""Scale insertion and splicing to 10 each with split-safe donor-target pairing."""

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
    """Scale insertion and splicing with split-safe pairing."""
    print("=== Scaling Insertion and Splicing ===")
    
    config = GenerationConfig()
    config.pilot_insertion_count = 10
    config.pilot_splicing_count = 10
    
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
    
    # Track sources already used
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
    
    # Build split-aware source pools
    train_sources = [s for s in sources if split_inheritance.get_split(s['source_id']) == 'train']
    val_sources = [s for s in sources if split_inheritance.get_split(s['source_id']) == 'validation']
    test_sources = [s for s in sources if split_inheritance.get_split(s['source_id']) == 'test']
    
    print(f"Split distribution: train={len(train_sources)}, val={len(val_sources)}, test={len(test_sources)}")
    
    # === Scale Object Insertion to 10 ===
    print(f"\n=== Scaling Object Insertion to {config.pilot_insertion_count} ===")
    current_insertion = manip_by_type.get('object_insertion', 0)
    needed_insertion = config.pilot_insertion_count - current_insertion
    print(f"Need {needed_insertion} more insertion variants")
    
    insertion_idx = 0
    for split_pool, split_name in [(train_sources, 'train'), (val_sources, 'validation'), (test_sources, 'test')]:
        if current_insertion >= config.pilot_insertion_count:
            break
        for target in split_pool:
            if current_insertion >= config.pilot_insertion_count:
                break
            if target['source_id'] in sources_by_manip.get('object_insertion', set()):
                continue
            
            # Find donor from same split
            for donor in split_pool:
                if donor['source_id'] == target['source_id']:
                    continue
                if current_insertion >= config.pilot_insertion_count:
                    break
                
                try:
                    target_img = Image.open(target['_file_path'])
                    donor_img = Image.open(donor['_file_path'])
                    
                    w_target, h_target = target_img.size
                    w_donor, h_donor = donor_img.size
                    
                    source_idx = hash(target['source_id'] + donor['source_id']) % 1000
                    insertion_idx += 1
                    
                    region_config = config.insertion_region_configs[source_idx % len(config.insertion_region_configs)]
                    position, area_ratio = region_config
                    
                    dest_w = int(w_target * area_ratio)
                    dest_h = int(h_target * area_ratio)
                    
                    if position == "center":
                        dest_x = (w_target - dest_w) // 2
                        dest_y = (h_target - dest_h) // 2
                    elif position == "top_left":
                        dest_x = w_target // 8
                        dest_y = h_target // 8
                    elif position == "top_right":
                        dest_x = w_target - dest_w - w_target // 8
                        dest_y = h_target // 8
                    elif position == "bottom_left":
                        dest_x = w_target // 8
                        dest_y = h_target - dest_h - h_target // 8
                    elif position == "bottom_right":
                        dest_x = w_target - dest_w - w_target // 8
                        dest_y = h_target - dest_h - h_target // 8
                    else:
                        dest_x = (w_target - dest_w) // 2
                        dest_y = (h_target - dest_h) // 2
                    
                    dest_w = max(1, min(dest_w, w_target - dest_x))
                    dest_h = max(1, min(dest_h, h_target - dest_y))
                    
                    if dest_w < 10 or dest_h < 10:
                        continue
                    
                    donor_w = min(dest_w, w_donor)
                    donor_h = min(dest_h, h_donor)
                    donor_x = max(0, (w_donor - donor_w) // 2)
                    donor_y = max(0, (h_donor - donor_h) // 2)
                    
                    if donor_w < 10 or donor_h < 10:
                        continue
                    
                    rotation = config.insertion_rotation_range[source_idx % len(config.insertion_rotation_range)]
                    scale = config.insertion_scale_range[source_idx % len(config.insertion_scale_range)]
                    blend = 0.0
                    
                    result, mask = ManipulationGenerator.object_insertion(
                        target_img, donor_img, (donor_x, donor_y, donor_w, donor_h),
                        (dest_x, dest_y, dest_w, dest_h), rotation, scale, blend
                    )
                    
                    variant_id = generate_variant_id(
                        target['image_id'],
                        'manipulated',
                        'object_insertion',
                        {
                            'donor_source_id': donor['source_id'],
                            'donor_image_id': donor['image_id'],
                            'donor_region': (donor_x, donor_y, donor_w, donor_h),
                            'dest_region': (dest_x, dest_y, dest_w, dest_h),
                            'rotation': rotation,
                            'scale': scale,
                            'blend': blend,
                            'split': split_name
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
                            source_id=target['source_id'],
                            parent_image_id=target['image_id'],
                            parent_source_id=target['source_id'],
                            variant_id=variant_id,
                            category='manipulated',
                            label=1,
                            generation_method='manipulated',
                            processing_operations=['object_insertion'],
                            image_path=str(output_path.relative_to(root)).replace('\\', '/'),
                            mask_path=str(mask_path.relative_to(root)).replace('\\', '/'),
                            mask_id=variant_id + '_mask',
                            manipulation_type='object_insertion',
                            parameters={
                                'donor_source_id': donor['source_id'],
                                'donor_image_id': donor['image_id'],
                                'donor_region': (donor_x, donor_y, donor_w, donor_h),
                                'dest_region': (dest_x, dest_y, dest_w, dest_h),
                                'rotation': rotation,
                                'scale': scale,
                                'blend': blend,
                                'split': split_name,
                                'manipulation_area_ratio': manipulation_area_ratio
                            },
                            seed=config.random_seed,
                            dataset_version=config.dataset_version,
                            metadata_available=False,
                            root_path=root
                        )
                        
                        all_new_records.append(record)
                        existing_image_ids.add(variant_id)
                        sources_by_manip.setdefault('object_insertion', set()).add(target['source_id'])
                        current_insertion += 1
                        print(f"Generated insertion: {variant_id} (split: {split_name})")
                
                except Exception as e:
                    print(f"Error generating insertion for {target['image_id']}: {e}")
    
    # === Scale Splicing to 10 ===
    print(f"\n=== Scaling Splicing to {config.pilot_splicing_count} ===")
    current_splicing = manip_by_type.get('splicing', 0)
    needed_splicing = config.pilot_splicing_count - current_splicing
    print(f"Need {needed_splicing} more splicing variants")
    
    splicing_idx = 0
    for split_pool, split_name in [(train_sources, 'train'), (val_sources, 'validation'), (test_sources, 'test')]:
        if current_splicing >= config.pilot_splicing_count:
            break
        for target in split_pool:
            if current_splicing >= config.pilot_splicing_count:
                break
            if target['source_id'] in sources_by_manip.get('splicing', set()):
                continue
            
            for donor in split_pool:
                if donor['source_id'] == target['source_id']:
                    continue
                if current_splicing >= config.pilot_splicing_count:
                    break
                
                try:
                    target_img = Image.open(target['_file_path'])
                    donor_img = Image.open(donor['_file_path'])
                    
                    w_target, h_target = target_img.size
                    w_donor, h_donor = donor_img.size
                    
                    source_idx = hash(donor['source_id'] + target['source_id']) % 1000
                    splicing_idx += 1
                    
                    region_config = config.splicing_region_configs[source_idx % len(config.splicing_region_configs)]
                    position, area_ratio = region_config
                    
                    region_w = int(w_target * area_ratio)
                    region_h = int(h_target * area_ratio)
                    
                    if position == "center":
                        tx = (w_target - region_w) // 2
                        ty = (h_target - region_h) // 2
                    elif position == "top_left":
                        tx = w_target // 8
                        ty = h_target // 8
                    elif position == "top_right":
                        tx = w_target - region_w - w_target // 8
                        ty = h_target // 8
                    elif position == "bottom_left":
                        tx = w_target // 8
                        ty = h_target - region_h - h_target // 8
                    elif position == "bottom_right":
                        tx = w_target - region_w - w_target // 8
                        ty = h_target - region_h - h_target // 8
                    else:
                        tx = (w_target - region_w) // 2
                        ty = (h_target - region_h) // 2
                    
                    region_w = max(1, min(region_w, w_target - tx))
                    region_h = max(1, min(region_h, h_target - ty))
                    
                    if region_w < 10 or region_h < 10:
                        continue
                    
                    donor_w = min(region_w, w_donor)
                    donor_h = min(region_h, h_donor)
                    donor_x = max(0, (w_donor - donor_w) // 2)
                    donor_y = max(0, (h_donor - donor_h) // 2)
                    
                    if donor_w < 10 or donor_h < 10:
                        continue
                    
                    rotation = config.splicing_rotation_range[source_idx % len(config.splicing_rotation_range)]
                    scale = config.splicing_scale_range[source_idx % len(config.splicing_scale_range)]
                    blend = 0.0
                    
                    result, mask = ManipulationGenerator.splicing(
                        target_img, donor_img, (donor_x, donor_y, donor_w, donor_h),
                        (tx, ty, region_w, region_h), rotation, scale, blend
                    )
                    
                    variant_id = generate_variant_id(
                        target['image_id'],
                        'manipulated',
                        'splicing',
                        {
                            'donor_source_id': donor['source_id'],
                            'donor_image_id': donor['image_id'],
                            'donor_region': (donor_x, donor_y, donor_w, donor_h),
                            'target_region': (tx, ty, region_w, region_h),
                            'rotation': rotation,
                            'scale': scale,
                            'blend': blend,
                            'split': split_name
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
                            source_id=target['source_id'],
                            parent_image_id=target['image_id'],
                            parent_source_id=target['source_id'],
                            variant_id=variant_id,
                            category='manipulated',
                            label=1,
                            generation_method='manipulated',
                            processing_operations=['splicing'],
                            image_path=str(output_path.relative_to(root)).replace('\\', '/'),
                            mask_path=str(mask_path.relative_to(root)).replace('\\', '/'),
                            mask_id=variant_id + '_mask',
                            manipulation_type='splicing',
                            parameters={
                                'donor_source_id': donor['source_id'],
                                'donor_image_id': donor['image_id'],
                                'donor_region': (donor_x, donor_y, donor_w, donor_h),
                                'target_region': (tx, ty, region_w, region_h),
                                'rotation': rotation,
                                'scale': scale,
                                'blend': blend,
                                'split': split_name,
                                'manipulation_area_ratio': manipulation_area_ratio
                            },
                            seed=config.random_seed,
                            dataset_version=config.dataset_version,
                            metadata_available=False,
                            root_path=root
                        )
                        
                        all_new_records.append(record)
                        existing_image_ids.add(variant_id)
                        sources_by_manip.setdefault('splicing', set()).add(target['source_id'])
                        current_splicing += 1
                        print(f"Generated splicing: {variant_id} (split: {split_name})")
                
                except Exception as e:
                    print(f"Error generating splicing for {target['image_id']}: {e}")
    
    print(f"\nGenerated {len(all_new_records)} new insertion/splicing variants")
    
    # Validate batch
    print("Validating generated records...")
    validation = validator.validate_batch(all_new_records)
    
    if not validation['valid']:
        print("VALIDATION FAILED - Not writing to manifest")
        print("Errors:", validation['errors'])
        print("\n=== INSERTION/SPLICING SCALING FAILED ===")
        return
    
    # Write to manifest
    print("Writing to manifest...")
    with manifest_path.open('a') as f:
        for record in all_new_records:
            f.write(json.dumps(record) + '\n')
    print(f"Wrote {len(all_new_records)} records to manifest")
    
    print("\n=== Insertion/Splicing Scaling Complete ===")
    print(f"Total new records: {len(all_new_records)}")


if __name__ == '__main__':
    main()

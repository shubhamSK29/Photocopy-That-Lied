"""Generate object removal variants for Dataset V2."""

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
    """Generate object removal variants."""
    print("=== Generating Object Removal Variants ===")
    
    config = GenerationConfig()
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
    
    existing_image_ids = {r['image_id'] for r in existing_records}
    
    # Get source images
    sources = [
        r for r in existing_records
        if r.get('category') == 'original' and r.get('source_id', '').startswith('SRC_DW')
    ]
    
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
    
    # Select sources for object removal (skip copy-move sources)
    copy_move_sources = {r['source_id'] for r in existing_records if r.get('manipulation_type') == 'copy_move'}
    available_sources = [s for s in sources if s['source_id'] not in copy_move_sources]
    
    # Sort and select pilot sources
    selected_sources = sorted(available_sources, key=lambda x: x['source_id'])[:config.pilot_removal_count]
    print(f"Selected {len(selected_sources)} sources for object removal generation")
    
    # Initialize validator
    validator = GenerationValidator(manifest_path, splits_dir)
    
    all_records = []
    
    # Generate object removal variants
    for source in selected_sources:
        try:
            source_img = Image.open(source['_file_path'])
            w, h = source_img.size
            
            # Use deterministic parameter selection based on source index
            source_idx = hash(source['source_id']) % 1000
            
            # Diverse removal regions and parameters
            region_config = config.removal_region_configs[source_idx % len(config.removal_region_configs)]
            position, area_ratio = region_config
            
            # Calculate region based on position and area ratio
            region_w = int(w * area_ratio)
            region_h = int(h * area_ratio)
            
            if position == "center":
                region_x = (w - region_w) // 2
                region_y = (h - region_h) // 2
            elif position == "top_left":
                region_x = w // 8
                region_y = h // 8
            elif position == "top_right":
                region_x = w - region_w - w // 8
                region_y = h // 8
            elif position == "bottom_left":
                region_x = w // 8
                region_y = h - region_h - h // 8
            elif position == "bottom_right":
                region_x = w - region_w - w // 8
                region_y = h - region_h - h // 8
            else:
                region_x = (w - region_w) // 2
                region_y = (h - region_h) // 2
            
            # Ensure region is within bounds
            region_w = min(region_w, w - region_x)
            region_h = min(region_h, h - region_y)
            
            # Diverse inpainting parameters
            inpainting_method = config.removal_inpainting_methods[source_idx % len(config.removal_inpainting_methods)]
            inpaint_radius = config.removal_inpaint_radius[source_idx % len(config.removal_inpaint_radius)]
            
            # Generate object removal
            result, mask = ManipulationGenerator.object_removal(
                source_img, (region_x, region_y, region_w, region_h), inpainting_method, inpaint_radius
            )

            variant_id = generate_variant_id(
                source['image_id'],
                'manipulated',
                'object_removal',
                {
                    'removed_region': (region_x, region_y, region_w, region_h),
                    'inpainting_method': inpainting_method,
                    'inpaint_radius': inpaint_radius
                }
            )

            if variant_id not in existing_image_ids:
                # Save image
                output_filename = f"{variant_id}.jpg"
                output_path = manipulated_dir / output_filename
                result.save(output_path, quality=config.output_quality)

                # Save mask
                mask_filename = f"{variant_id}_mask.png"
                mask_path = masks_dir / mask_filename
                Image.fromarray(mask).save(mask_path)

                # Build record
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
                        'removed_region': (region_x, region_y, region_w, region_h),
                        'inpainting_method': inpainting_method,
                        'inpaint_radius': inpaint_radius
                    },
                    seed=config.random_seed,
                    dataset_version=config.dataset_version,
                    metadata_available=False,
                    root_path=root
                )

                all_records.append(record)
                existing_image_ids.add(variant_id)
                print(f"Generated object removal: {variant_id} (position={position}, area={area_ratio}, method={inpainting_method})")

        except Exception as e:
            print(f"Error generating object removal for {source['image_id']}: {e}")
    
    print(f"\nGenerated {len(all_records)} object removal variants")
    
    # Validate
    print("Validating generated records...")
    validation = validator.validate_batch(all_records)
    
    # Write to manifest (append)
    if validation['valid']:
        print("Writing to manifest...")
        with manifest_path.open('a') as f:
            for record in all_records:
                f.write(json.dumps(record) + '\n')
        print(f"Wrote {len(all_records)} records to manifest")
    else:
        print("Validation failed, not writing to manifest")
        print("Errors:", validation['errors'])
    
    print("\n=== Object Removal Generation Complete ===")


if __name__ == '__main__':
    main()

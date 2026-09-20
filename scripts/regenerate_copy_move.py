"""Regenerate copy-move variants with diverse parameters."""

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
    """Regenerate copy-move variants with diverse parameters."""
    print("=== Regenerating Copy-Move Variants with Diversity ===")
    
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
    
    # Remove existing copy-move records
    copy_move_records = [r for r in existing_records if r.get('manipulation_type') == 'copy_move']
    if copy_move_records:
        print(f"Found {len(copy_move_records)} existing copy-move records")
        
        # Remove files
        for record in copy_move_records:
            image_path = root / record.get('image_path', '')
            mask_path = root / record.get('mask_path', '')
            
            if image_path.exists():
                image_path.unlink()
                print(f"Removed image: {image_path}")
            if mask_path.exists():
                mask_path.unlink()
                print(f"Removed mask: {mask_path}")
        
        # Remove from manifest
        filtered_records = [r for r in existing_records if r.get('manipulation_type') != 'copy_move']
        with manifest_path.open('w') as f:
            for record in filtered_records:
                f.write(json.dumps(record) + '\n')
        
        print(f"Removed copy-move records from manifest")
        existing_records = filtered_records
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
    
    # Select pilot sources for copy-move generation
    pilot_sources = sorted(sources, key=lambda x: x['source_id'])[:config.pilot_copy_move_count]
    print(f"Selected {len(pilot_sources)} sources for copy-move generation")
    
    # Initialize validator
    validator = GenerationValidator(manifest_path, splits_dir)
    
    all_records = []
    
    # Generate copy-move variants with diverse parameters
    for source in pilot_sources:
        try:
            source_img = Image.open(source['_file_path'])
            w, h = source_img.size
            
            # Use deterministic parameter selection based on source index
            source_idx = hash(source['source_id']) % 1000
            
            # Diverse source regions (different quadrants and sizes) - ensure within bounds
            region_configs = [
                (w//4, h//4, w//4, h//4),      # Top-left, medium
                (w//2, h//4, w//4, h//4),      # Top-right, medium
                (w//4, h//2, w//4, h//4),      # Bottom-left, medium
                (w//6, h//6, w//3, h//3),      # Top-left, large
                (w//3, h//3, w//6, h//6),      # Center, small
            ]
            src_x, src_y, src_w, src_h = region_configs[source_idx % len(region_configs)]
            
            # Ensure source region is within bounds
            src_w = min(src_w, w - src_x)
            src_h = min(src_h, h - src_y)
            
            # Diverse destination regions (offset from source) - ensure within bounds
            dest_configs = [
                (w//2, h//2, src_w, src_h),  # Bottom-right
                (w//8, h//2, src_w, src_h),   # Left-middle
                (w//2, h//8, src_w, src_h),   # Top-middle
                (w - src_w - w//8, h - src_h - h//8, src_w, src_h),  # Bottom-right corner
            ]
            dest_x, dest_y, dest_w, dest_h = dest_configs[source_idx % len(dest_configs)]
            
            # Ensure destination region is within bounds
            dest_x = min(dest_x, w - dest_w)
            dest_y = min(dest_y, h - dest_h)
            
            # Diverse transformations
            rotation = config.copy_move_rotation_range[source_idx % len(config.copy_move_rotation_range)]
            scale = config.copy_move_scale_range[source_idx % len(config.copy_move_scale_range)]
            blend = 0.0  # No blending for clearer copy-move detection
            
            # Generate copy-move
            result, mask = ManipulationGenerator.copy_move(
                source_img, (src_x, src_y, src_w, src_h), (dest_x, dest_y, dest_w, dest_h), rotation, scale, blend
            )

            variant_id = generate_variant_id(
                source['image_id'],
                'manipulated',
                'copy_move',
                {
                    'source_region': (src_x, src_y, src_w, src_h),
                    'dest_region': (dest_x, dest_y, dest_w, dest_h),
                    'rotation': rotation,
                    'scale': scale,
                    'blend': blend
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
                    processing_operations=['copy_move'],
                    image_path=str(output_path.relative_to(root)).replace('\\', '/'),
                    mask_path=str(mask_path.relative_to(root)).replace('\\', '/'),
                    mask_id=variant_id + '_mask',
                    manipulation_type='copy_move',
                    parameters={
                        'source_region': (src_x, src_y, src_w, src_h),
                        'dest_region': (dest_x, dest_y, dest_w, dest_h),
                        'rotation': rotation,
                        'scale': scale,
                        'blend': blend
                    },
                    seed=config.random_seed,
                    dataset_version=config.dataset_version,
                    metadata_available=False,
                    root_path=root
                )

                all_records.append(record)
                existing_image_ids.add(variant_id)
                print(f"Generated copy-move: {variant_id} (rotation={rotation}, scale={scale})")

        except Exception as e:
            print(f"Error generating copy-move for {source['image_id']}: {e}")
    
    print(f"\nGenerated {len(all_records)} copy-move variants")
    
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
    
    print("\n=== Copy-Move Regeneration Complete ===")


if __name__ == '__main__':
    main()

"""Generate the missing object insertion variant that failed earlier."""

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


def get_source_split(source_id: str, splits_dir: Path) -> str:
    """Get the split assignment for a source ID."""
    split_inheritance = SplitInheritance(splits_dir)
    return split_inheritance.get_split(source_id)


def main():
    """Generate the missing object insertion variant."""
    print("=== Generating Missing Object Insertion Variant ===")
    
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
    
    existing_image_ids = {r['image_id'] for r in existing_records}
    
    # Find the specific source that failed (SRC_DW_00A1114B479A99B6 from test split)
    target_source = None
    donor_source = None
    for source in sources:
        if source['source_id'] == 'SRC_DW_00A1114B479A99B6':
            target_source = source
        elif source['source_id'] == 'SRC_DW_3F695C2B359CF2F6':
            donor_source = source
    
    if not target_source or not donor_source:
        print("ERROR: Could not find required sources")
        return
    
    # Verify same split
    target_split = get_source_split(target_source['source_id'], splits_dir)
    donor_split = get_source_split(donor_source['source_id'], splits_dir)
    
    if target_split != donor_split:
        print(f"ERROR: Splits don't match - target: {target_split}, donor: {donor_split}")
        return
    
    print(f"Target: {target_source['source_id']} (split: {target_split})")
    print(f"Donor: {donor_source['source_id']} (split: {donor_split})")
    
    # Initialize validator
    validator = GenerationValidator(manifest_path, splits_dir)
    
    all_records = []
    
    try:
        target_img = Image.open(target_source['_file_path'])
        donor_img = Image.open(donor_source['_file_path'])
        
        w_target, h_target = target_img.size
        w_donor, h_donor = donor_img.size
        
        # Use conservative parameters to avoid the resize error
        target_idx = hash(target_source['source_id']) % 1000
        
        region_config = config.insertion_region_configs[target_idx % len(config.insertion_region_configs)]
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
        
        # Ensure destination is within bounds
        dest_w = max(1, min(dest_w, w_target - dest_x))
        dest_h = max(1, min(dest_h, h_target - dest_y))
        
        # Skip if too small
        if dest_w < 10 or dest_h < 10:
            print(f"Destination region too small: {dest_w}x{dest_h}")
            return
        
        donor_w = min(dest_w, w_donor)
        donor_h = min(dest_h, h_donor)
        donor_x = max(0, (w_donor - donor_w) // 2)
        donor_y = max(0, (h_donor - donor_h) // 2)
        
        if donor_w < 10 or donor_h < 10:
            print(f"Donor region too small: {donor_w}x{donor_h}")
            return
        
        # Use conservative scale to avoid error
        rotation = 0  # No rotation to avoid resize issues
        scale = 1.0  # No scaling
        blend = 0.0
        
        result, mask = ManipulationGenerator.object_insertion(
            target_img, donor_img, (donor_x, donor_y, donor_w, donor_h),
            (dest_x, dest_y, dest_w, dest_h), rotation, scale, blend
        )

        variant_id = generate_variant_id(
            target_source['image_id'],
            'manipulated',
            'object_insertion',
            {
                'donor_source_id': donor_source['source_id'],
                'donor_image_id': donor_source['image_id'],
                'donor_region': (donor_x, donor_y, donor_w, donor_h),
                'dest_region': (dest_x, dest_y, dest_w, dest_h),
                'rotation': rotation,
                'scale': scale,
                'blend': blend,
                'split': target_split
            }
        )

        if variant_id not in existing_image_ids:
            output_filename = f"{variant_id}.jpg"
            output_path = manipulated_dir / output_filename
            result.save(output_path, quality=config.output_quality)

            mask_filename = f"{variant_id}_mask.png"
            mask_path = masks_dir / mask_filename
            Image.fromarray(mask).save(mask_path)

            record = build_provenance_record(
                image_id=variant_id,
                source_id=target_source['source_id'],
                parent_image_id=target_source['image_id'],
                parent_source_id=target_source['source_id'],
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
                    'donor_source_id': donor_source['source_id'],
                    'donor_image_id': donor_source['image_id'],
                    'donor_region': (donor_x, donor_y, donor_w, donor_h),
                    'dest_region': (dest_x, dest_y, dest_w, dest_h),
                    'rotation': rotation,
                    'scale': scale,
                    'blend': blend,
                    'split': target_split
                },
                seed=config.random_seed,
                dataset_version=config.dataset_version,
                metadata_available=False,
                root_path=root
            )

            all_records.append(record)
            existing_image_ids.add(variant_id)
            print(f"Generated object insertion: {variant_id}")

    except Exception as e:
        print(f"Error generating object insertion: {e}")
        import traceback
        traceback.print_exc()
    
    print(f"\nGenerated {len(all_records)} variant(s)")
    
    # Validate
    print("Validating generated records...")
    validation = validator.validate_batch(all_records)
    
    # Write to manifest (append)
    if validation['valid']:
        print("Writing to manifest...")
        with manifest_path.open('a') as f:
            for record in all_records:
                f.write(json.dumps(record) + '\n')
        print(f"Wrote {len(all_records)} record(s) to manifest")
    else:
        print("Validation failed, not writing to manifest")
        print("Errors:", validation['errors'])
    
    print("\n=== Missing Object Insertion Generation Complete ===")


if __name__ == '__main__':
    main()

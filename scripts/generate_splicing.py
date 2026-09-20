"""Generate splicing variants for Dataset V2 with split safety."""

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
    """Generate splicing variants with split safety."""
    print("=== Generating Splicing Variants with Split Safety ===")
    
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
    
    # Group sources by split for safe donor-target pairing
    sources_by_split = {'train': [], 'validation': [], 'test': []}
    for source in sources:
        split = get_source_split(source['source_id'], splits_dir)
        if split in sources_by_split:
            sources_by_split[split].append(source)
    
    print(f"Sources by split: train={len(sources_by_split['train'])}, validation={len(sources_by_split['validation'])}, test={len(sources_by_split['test'])}")
    
    # Select target and donor sources from same splits
    selected_pairs = []
    for split, split_sources in sources_by_split.items():
        if len(split_sources) >= 2:  # Need at least 2 sources for donor-target pairing
            # Select min(config.pilot_splicing_count, available) pairs per split
            available_pairs = len(split_sources) // 2
            pairs_needed = min(config.pilot_splicing_count // 3, available_pairs)  # Distribute across splits
            
            for i in range(pairs_needed):
                target = split_sources[i * 2]
                donor = split_sources[i * 2 + 1]
                selected_pairs.append((target, donor, split))
    
    print(f"Selected {len(selected_pairs)} donor-target pairs with split safety")
    
    # Initialize validator
    validator = GenerationValidator(manifest_path, splits_dir)
    
    all_records = []
    
    # Generate splicing variants
    for i, (target, donor, split) in enumerate(selected_pairs):
        try:
            target_img = Image.open(target['_file_path'])
            donor_img = Image.open(donor['_file_path'])
            
            w_target, h_target = target_img.size
            w_donor, h_donor = donor_img.size
            
            # Use deterministic parameter selection based on target index
            target_idx = hash(target['source_id']) % 1000
            
            # Diverse splicing regions
            region_config = config.splicing_region_configs[target_idx % len(config.splicing_region_configs)]
            position, area_ratio = region_config
            
            # Calculate target region
            target_w = int(w_target * area_ratio)
            target_h = int(h_target * area_ratio)
            
            if position == "center":
                target_x = (w_target - target_w) // 2
                target_y = (h_target - target_h) // 2
            elif position == "top_left":
                target_x = w_target // 8
                target_y = h_target // 8
            elif position == "top_right":
                target_x = w_target - target_w - w_target // 8
                target_y = h_target // 8
            elif position == "bottom_left":
                target_x = w_target // 8
                target_y = h_target - target_h - h_target // 8
            elif position == "bottom_right":
                target_x = w_target - target_w - w_target // 8
                target_y = h_target - target_h - h_target // 8
            else:
                target_x = (w_target - target_w) // 2
                target_y = (h_target - target_h) // 2
            
            # Ensure target region is within bounds
            target_w = max(1, min(target_w, w_target - target_x))
            target_h = max(1, min(target_h, h_target - target_y))
            
            # Skip if target region is too small
            if target_w < 10 or target_h < 10:
                print(f"Skipping {target['image_id']}: target region too small ({target_w}x{target_h})")
                continue
            
            # Extract donor region (center of donor)
            donor_w = min(target_w, w_donor)
            donor_h = min(target_h, h_donor)
            donor_x = max(0, (w_donor - donor_w) // 2)
            donor_y = max(0, (h_donor - donor_h) // 2)
            
            # Skip if donor region is too small
            if donor_w < 10 or donor_h < 10:
                print(f"Skipping {target['image_id']}: donor region too small ({donor_w}x{donor_h})")
                continue
            
            # Diverse transformations
            rotation = config.splicing_rotation_range[target_idx % len(config.splicing_rotation_range)]
            scale = config.splicing_scale_range[target_idx % len(config.splicing_scale_range)]
            blend = 0.0  # No blending for clearer detection
            
            # Generate splicing
            try:
                result, mask = ManipulationGenerator.splicing(
                    target_img, donor_img, (target_x, target_y, target_w, target_h),
                    (donor_x, donor_y, donor_w, donor_h), rotation, scale, blend
                )
            except Exception as e:
                print(f"Error in splicing for {target['image_id']}: {e}")
                continue

            variant_id = generate_variant_id(
                target['image_id'],
                'manipulated',
                'splicing',
                {
                    'donor_source_id': donor['source_id'],
                    'donor_image_id': donor['image_id'],
                    'target_region': (target_x, target_y, target_w, target_h),
                    'donor_region': (donor_x, donor_y, donor_w, donor_h),
                    'rotation': rotation,
                    'scale': scale,
                    'blend': blend,
                    'split': split
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
                        'target_region': (target_x, target_y, target_w, target_h),
                        'donor_region': (donor_x, donor_y, donor_w, donor_h),
                        'rotation': rotation,
                        'scale': scale,
                        'blend': blend,
                        'split': split
                    },
                    seed=config.random_seed,
                    dataset_version=config.dataset_version,
                    metadata_available=False,
                    root_path=root
                )

                all_records.append(record)
                existing_image_ids.add(variant_id)
                print(f"Generated splicing: {variant_id} (donor={donor['source_id']}, split={split})")

        except Exception as e:
            print(f"Error generating splicing for {target['image_id']}: {e}")
    
    print(f"\nGenerated {len(all_records)} splicing variants")
    
    # Validate
    print("Validating generated records...")
    validation = validator.validate_batch(all_records)
    
    # Check split leakage
    leakage = validator.check_split_leakage(all_records)
    
    # Write to manifest (append)
    if validation['valid'] and not leakage['has_leakage']:
        print("Writing to manifest...")
        with manifest_path.open('a') as f:
            for record in all_records:
                f.write(json.dumps(record) + '\n')
        print(f"Wrote {len(all_records)} records to manifest")
    else:
        print("Validation or leakage check failed, not writing to manifest")
        if not validation['valid']:
            print("Validation errors:", validation['errors'])
        if leakage['has_leakage']:
            print("Leakage detected:", leakage)
    
    print("\n=== Splicing Generation Complete ===")


if __name__ == '__main__':
    main()

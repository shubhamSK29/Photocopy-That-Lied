"""Regenerate all manipulated records to include manipulation_area_ratio."""

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
    """Regenerate all manipulated records with area ratios."""
    print("=== Regenerating All Manipulated Records with Area Ratios ===")
    
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
    
    # Remove existing manipulated records from manifest
    non_manipulated = [r for r in existing_records if r.get('category') != 'manipulated']
    print(f"Removing {len(existing_records) - len(non_manipulated)} manipulated records from manifest")
    
    # Delete existing manipulated files
    for file in manipulated_dir.glob('*.jpg'):
        file.unlink()
    for file in masks_dir.glob('*.png'):
        file.unlink()
    print("Deleted existing manipulated files and masks")
    
    # Rewrite manifest without manipulated records
    with manifest_path.open('w') as f:
        for record in non_manipulated:
            f.write(json.dumps(record) + '\n')
    print("Rewrote manifest without manipulated records")
    
    # Get source images
    sources = [
        r for r in non_manipulated
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
    
    existing_image_ids = {r['image_id'] for r in non_manipulated}
    
    # Initialize validator
    validator = GenerationValidator(manifest_path, splits_dir)
    
    all_records = []
    
    # Generate copy-move
    print("\nGenerating copy-move variants...")
    for source in sources[:config.pilot_copy_move_count]:
        try:
            source_img = Image.open(source['_file_path'])
            w, h = source_img.size
            
            source_idx = hash(source['source_id']) % 1000
            
            region_configs = [
                (w//4, h//4, w//4, h//4),
                (w//2, h//4, w//4, h//4),
                (w//4, h//2, w//4, h//4),
                (w//6, h//6, w//3, h//3),
                (w//3, h//3, w//6, h//6),
            ]
            src_x, src_y, src_w, src_h = region_configs[source_idx % len(region_configs)]
            src_w = min(src_w, w - src_x)
            src_h = min(src_h, h - src_y)
            
            dest_configs = [
                (w//2, h//2, src_w, src_h),
                (w//8, h//2, src_w, src_h),
                (w//2, h//8, src_w, src_h),
                (w - src_w - w//8, h - src_h - h//8, src_w, src_h),
            ]
            dest_x, dest_y, dest_w, dest_h = dest_configs[source_idx % len(dest_configs)]
            dest_x = min(dest_x, w - dest_w)
            dest_y = min(dest_y, h - dest_h)
            
            rotation = config.copy_move_rotation_range[source_idx % len(config.copy_move_rotation_range)]
            scale = config.copy_move_scale_range[source_idx % len(config.copy_move_scale_range)]
            blend = 0.0
            
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

            output_filename = f"{variant_id}.jpg"
            output_path = manipulated_dir / output_filename
            result.save(output_path, quality=config.output_quality)

            mask_filename = f"{variant_id}_mask.png"
            mask_path = masks_dir / mask_filename
            Image.fromarray(mask).save(mask_path)

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
            print(f"Generated copy-move: {variant_id}")

        except Exception as e:
            print(f"Error generating copy-move for {source['image_id']}: {e}")
    
    # Generate object removal
    print("\nGenerating object removal variants...")
    removal_sources = sources[config.pilot_copy_move_count:config.pilot_copy_move_count + config.pilot_removal_count]
    for source in removal_sources:
        try:
            source_img = Image.open(source['_file_path'])
            w, h = source_img.size
            
            source_idx = hash(source['source_id']) % 1000
            
            region_config = config.removal_region_configs[source_idx % len(config.removal_region_configs)]
            position, area_ratio = region_config
            
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
            
            region_w = min(region_w, w - region_x)
            region_h = min(region_h, h - region_y)
            
            inpainting_method = config.removal_inpainting_methods[source_idx % len(config.removal_inpainting_methods)]
            inpaint_radius = config.removal_inpaint_radius[source_idx % len(config.removal_inpaint_radius)]
            
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

            output_filename = f"{variant_id}.jpg"
            output_path = manipulated_dir / output_filename
            result.save(output_path, quality=config.output_quality)

            mask_filename = f"{variant_id}_mask.png"
            mask_path = masks_dir / mask_filename
            Image.fromarray(mask).save(mask_path)

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
            print(f"Generated object removal: {variant_id}")

        except Exception as e:
            print(f"Error generating object removal for {source['image_id']}: {e}")
    
    # Generate object insertion
    print("\nGenerating object insertion variants...")
    sources_by_split = {'train': [], 'validation': [], 'test': []}
    for source in sources:
        split = get_source_split(source['source_id'], splits_dir)
        if split in sources_by_split:
            sources_by_split[split].append(source)
    
    selected_pairs = []
    for split, split_sources in sources_by_split.items():
        if len(split_sources) >= 2:
            available_pairs = len(split_sources) // 2
            pairs_needed = min(config.pilot_insertion_count // 3, available_pairs)
            
            for i in range(pairs_needed):
                target = split_sources[i * 2]
                donor = split_sources[i * 2 + 1]
                selected_pairs.append((target, donor, split))
    
    for target, donor, split in selected_pairs:
        try:
            target_img = Image.open(target['_file_path'])
            donor_img = Image.open(donor['_file_path'])
            
            w_target, h_target = target_img.size
            w_donor, h_donor = donor_img.size
            
            target_idx = hash(target['source_id']) % 1000
            
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
            
            rotation = config.insertion_rotation_range[target_idx % len(config.insertion_rotation_range)]
            scale = config.insertion_scale_range[target_idx % len(config.insertion_scale_range)]
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
                    'split': split
                }
            )

            output_filename = f"{variant_id}.jpg"
            output_path = manipulated_dir / output_filename
            result.save(output_path, quality=config.output_quality)

            mask_filename = f"{variant_id}_mask.png"
            mask_path = masks_dir / mask_filename
            Image.fromarray(mask).save(mask_path)

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
                    'split': split
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
            print(f"Error generating object insertion for {target['image_id']}: {e}")
    
    # Generate splicing
    print("\nGenerating splicing variants...")
    for target, donor, split in selected_pairs:
        try:
            target_img = Image.open(target['_file_path'])
            donor_img = Image.open(donor['_file_path'])
            
            w_target, h_target = target_img.size
            w_donor, h_donor = donor_img.size
            
            target_idx = hash(target['source_id']) % 1000
            
            region_config = config.splicing_region_configs[target_idx % len(config.splicing_region_configs)]
            position, area_ratio = region_config
            
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
            
            target_w = max(1, min(target_w, w_target - target_x))
            target_h = max(1, min(target_h, h_target - target_y))
            
            if target_w < 10 or target_h < 10:
                continue
            
            donor_w = min(target_w, w_donor)
            donor_h = min(target_h, h_donor)
            donor_x = max(0, (w_donor - donor_w) // 2)
            donor_y = max(0, (h_donor - donor_h) // 2)
            
            if donor_w < 10 or donor_h < 10:
                continue
            
            rotation = config.splicing_rotation_range[target_idx % len(config.splicing_rotation_range)]
            scale = config.splicing_scale_range[target_idx % len(config.splicing_scale_range)]
            blend = 0.0
            
            result, mask = ManipulationGenerator.splicing(
                target_img, donor_img, (target_x, target_y, target_w, target_h),
                (donor_x, donor_y, donor_w, donor_h), rotation, scale, blend
            )

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

            output_filename = f"{variant_id}.jpg"
            output_path = manipulated_dir / output_filename
            result.save(output_path, quality=config.output_quality)

            mask_filename = f"{variant_id}_mask.png"
            mask_path = masks_dir / mask_filename
            Image.fromarray(mask).save(mask_path)

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
            print(f"Generated splicing: {variant_id}")

        except Exception as e:
            print(f"Error generating splicing for {target['image_id']}: {e}")
    
    print(f"\nGenerated {len(all_records)} manipulated variants total")
    
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
    
    print("\n=== Manipulated Records Regeneration Complete ===")


if __name__ == '__main__':
    main()

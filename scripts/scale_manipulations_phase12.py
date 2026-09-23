"""Phase 12: Scale manipulations to 300 total records with diversity.

Target distribution:
- 75 copy-move (from 25, add 50)
- 75 object_removal (from 15, add 60)
- 75 object_insertion (from 10, add 65)
- 75 splicing (from 10, add 65)

Total: 300 manipulated records
"""

import json
import sys
import random
from pathlib import Path
from typing import List, Dict, Any, Set
from PIL import Image
import numpy as np

# Add dataset_v2 directory to path for imports
sys.path.insert(0, str(Path(__file__).parent / "dataset_v2"))

from generation_config import GenerationConfig
from variant_ids import generate_variant_id
from provenance import build_provenance_record, compute_sha256
from split_inheritance import SplitInheritance
from generation_validator import GenerationValidator
from generators import ManipulationGenerator


def get_region_position(position: str, w: int, h: int, region_w: int, region_h: int) -> tuple:
    """Calculate region position based on position label."""
    if position == "center":
        return (w - region_w) // 2, (h - region_h) // 2
    elif position == "top_left":
        return w // 8, h // 8
    elif position == "top_right":
        return w - region_w - w // 8, h // 8
    elif position == "bottom_left":
        return w // 8, h - region_h - h // 8
    elif position == "bottom_right":
        return w - region_w - w // 8, h - region_h - h // 8
    elif position == "top_center":
        return (w - region_w) // 2, h // 8
    elif position == "bottom_center":
        return (w - region_w) // 2, h - region_h - h // 8
    elif position == "left_center":
        return w // 8, (h - region_h) // 2
    elif position == "right_center":
        return w - region_w - w // 8, (h - region_h) // 2
    else:
        return (w - region_w) // 2, (h - region_h) // 2


def generate_copy_move(
    source: Dict[str, Any],
    image: Image.Image,
    source_idx: int,
    config: GenerationConfig,
    sources_used: Set[str]
) -> Dict[str, Any]:
    """Generate a diverse copy-move manipulation."""
    w, h = image.size
    
    # Diverse area ratios (expanded range)
    area_ratios = [0.02, 0.03, 0.05, 0.08, 0.10, 0.12, 0.15, 0.18, 0.20, 0.25, 0.30]
    area_ratio = area_ratios[source_idx % len(area_ratios)]
    
    region_w = int(w * area_ratio)
    region_h = int(h * area_ratio)
    
    # Diverse positions
    positions = ["center", "top_left", "top_right", "bottom_left", "bottom_right", 
                 "top_center", "bottom_center", "left_center", "right_center"]
    pos_idx = source_idx % len(positions)
    
    # Source position
    sx, sy = get_region_position(positions[pos_idx], w, h, region_w, region_h)
    
    # Destination position (different from source)
    dest_pos_idx = (pos_idx + 3) % len(positions)
    dx, dy = get_region_position(positions[dest_pos_idx], w, h, region_w, region_h)
    
    # Diverse rotations
    rotations = [0, 15, 30, 45, 60, 90, 120, 135, 180, 225, 270]
    rotation = rotations[source_idx % len(rotations)]
    
    # Diverse scales
    scales = [0.7, 0.8, 0.9, 1.0, 1.1, 1.2, 1.3]
    scale = scales[source_idx % len(scales)]
    
    # Occasional blending
    blend = 0.2 if source_idx % 5 == 0 else 0.0
    
    result, mask = ManipulationGenerator.copy_move(
        image, (sx, sy, region_w, region_h),
        (dx, dy, region_w, region_h), rotation, scale, blend
    )
    
    manipulation_area_ratio = np.count_nonzero(mask) / (mask.shape[0] * mask.shape[1])
    
    return {
        'result': result,
        'mask': mask,
        'parameters': {
            'source_region': (sx, sy, region_w, region_h),
            'dest_region': (dx, dy, region_w, region_h),
            'rotation': rotation,
            'scale': scale,
            'blend': blend,
            'manipulation_area_ratio': manipulation_area_ratio
        }
    }


def generate_removal(
    source: Dict[str, Any],
    image: Image.Image,
    source_idx: int,
    config: GenerationConfig,
    sources_used: Set[str]
) -> Dict[str, Any]:
    """Generate a diverse object removal manipulation."""
    w, h = image.size
    
    # Diverse area ratios
    area_ratios = [0.08, 0.10, 0.12, 0.15, 0.18, 0.20, 0.25, 0.30]
    area_ratio = area_ratios[source_idx % len(area_ratios)]
    
    region_w = int(w * area_ratio)
    region_h = int(h * area_ratio)
    
    # Diverse positions
    positions = ["center", "top_left", "top_right", "bottom_left", "bottom_right",
                 "top_center", "bottom_center", "left_center", "right_center"]
    position = positions[source_idx % len(positions)]
    
    rx, ry = get_region_position(position, w, h, region_w, region_h)
    
    # Diverse inpainting methods
    methods = ["telea", "ns"]
    method = methods[source_idx % len(methods)]
    
    # Diverse inpainting radii
    radii = [3, 5, 7, 9, 11]
    radius = radii[source_idx % len(radii)]
    
    result, mask = ManipulationGenerator.object_removal(
        image, (rx, ry, region_w, region_h), method, radius
    )
    
    manipulation_area_ratio = np.count_nonzero(mask) / (mask.shape[0] * mask.shape[1])
    
    return {
        'result': result,
        'mask': mask,
        'parameters': {
            'region': (rx, ry, region_w, region_h),
            'method': method,
            'radius': radius,
            'manipulation_area_ratio': manipulation_area_ratio
        }
    }


def generate_insertion(
    source: Dict[str, Any],
    donor_source: Dict[str, Any],
    image: Image.Image,
    donor_image: Image.Image,
    source_idx: int,
    config: GenerationConfig,
    sources_used: Set[str],
    donor_splits: Dict[str, str]
) -> Dict[str, Any]:
    """Generate a diverse object insertion manipulation."""
    w, h = image.size
    dw, dh = donor_image.size
    
    # Diverse area ratios
    area_ratios = [0.08, 0.10, 0.12, 0.15, 0.18, 0.20, 0.25]
    area_ratio = area_ratios[source_idx % len(area_ratios)]
    
    region_w = int(w * area_ratio)
    region_h = int(h * area_ratio)
    
    # Diverse positions
    positions = ["center", "top_left", "top_right", "bottom_left", "bottom_right",
                 "top_center", "bottom_center", "left_center", "right_center"]
    position = positions[source_idx % len(positions)]
    
    dx, dy = get_region_position(position, w, h, region_w, region_h)
    
    # Donor region (center of donor)
    donor_region_w = min(region_w, dw // 2)
    donor_region_h = min(region_h, dh // 2)
    donor_rx = (dw - donor_region_w) // 2
    donor_ry = (dh - donor_region_h) // 2
    
    # Diverse rotations
    rotations = [0, 15, 30, 45, 60, 90, 135, 180]
    rotation = rotations[source_idx % len(rotations)]
    
    # Diverse scales
    scales = [0.8, 0.9, 1.0, 1.1, 1.2, 1.3]
    scale = scales[source_idx % len(scales)]
    
    # Occasional blending
    blend = 0.2 if source_idx % 4 == 0 else 0.0
    
    result, mask = ManipulationGenerator.object_insertion(
        image, donor_image,
        (donor_rx, donor_ry, donor_region_w, donor_region_h),
        (dx, dy, region_w, region_h),
        scale, rotation, blend
    )
    
    manipulation_area_ratio = np.count_nonzero(mask) / (mask.shape[0] * mask.shape[1])
    
    # Ensure split safety
    target_split = donor_splits.get(source['source_id'], 'train')
    donor_split = donor_splits.get(donor_source['source_id'], 'train')
    
    return {
        'result': result,
        'mask': mask,
        'parameters': {
            'donor_source_id': donor_source['source_id'],
            'donor_image_id': donor_source['image_id'],
            'donor_region': (donor_rx, donor_ry, donor_region_w, donor_region_h),
            'dest_region': (dx, dy, region_w, region_h),
            'rotation': rotation,
            'scale': scale,
            'blend': blend,
            'manipulation_area_ratio': manipulation_area_ratio,
            'split': target_split,
            'donor_split': donor_split
        }
    }


def generate_splicing(
    source: Dict[str, Any],
    donor_source: Dict[str, Any],
    image: Image.Image,
    donor_image: Image.Image,
    source_idx: int,
    config: GenerationConfig,
    sources_used: Set[str],
    donor_splits: Dict[str, str]
) -> Dict[str, Any]:
    """Generate a diverse splicing manipulation."""
    w, h = image.size
    dw, dh = donor_image.size
    
    # Diverse area ratios
    area_ratios = [0.08, 0.10, 0.12, 0.15, 0.18, 0.20, 0.25, 0.30]
    area_ratio = area_ratios[source_idx % len(area_ratios)]
    
    region_w = int(w * area_ratio)
    region_h = int(h * area_ratio)
    
    # Diverse positions
    positions = ["center", "top_left", "top_right", "bottom_left", "bottom_right",
                 "top_center", "bottom_center", "left_center", "right_center"]
    position = positions[source_idx % len(positions)]
    
    tx, ty = get_region_position(position, w, h, region_w, region_h)
    
    # Donor region (center of donor)
    donor_region_w = min(region_w, dw // 2)
    donor_region_h = min(region_h, dh // 2)
    donor_rx = (dw - donor_region_w) // 2
    donor_ry = (dh - donor_region_h) // 2
    
    # Diverse rotations
    rotations = [0, 15, 30, 45, 60, 90, 135, 180, 270]
    rotation = rotations[source_idx % len(rotations)]
    
    # Diverse scales
    scales = [0.8, 0.9, 1.0, 1.1, 1.2, 1.3]
    scale = scales[source_idx % len(scales)]
    
    # Occasional blending
    blend = 0.2 if source_idx % 3 == 0 else 0.0
    
    result, mask = ManipulationGenerator.splicing(
        image, donor_image,
        (tx, ty, region_w, region_h),
        (donor_rx, donor_ry, donor_region_w, donor_region_h),
        rotation, scale, blend
    )
    
    manipulation_area_ratio = np.count_nonzero(mask) / (mask.shape[0] * mask.shape[1])
    
    # Ensure split safety
    target_split = donor_splits.get(source['source_id'], 'train')
    donor_split = donor_splits.get(donor_source['source_id'], 'train')
    
    return {
        'result': result,
        'mask': mask,
        'parameters': {
            'donor_source_id': donor_source['source_id'],
            'donor_image_id': donor_source['image_id'],
            'target_region': (tx, ty, region_w, region_h),
            'donor_region': (donor_rx, donor_ry, donor_region_w, donor_region_h),
            'rotation': rotation,
            'scale': scale,
            'blend': blend,
            'manipulation_area_ratio': manipulation_area_ratio,
            'split': target_split,
            'donor_split': donor_split
        }
    }


def main():
    """Scale manipulations to 300 total records with diversity."""
    print("=== Phase 12: Scaling Manipulations to 300 Records ===")
    
    config = GenerationConfig()
    
    # Target counts for Phase 12
    target_copy_move = 75
    target_removal = 75
    target_insertion = 75
    target_splicing = 75
    target_total = target_copy_move + target_removal + target_insertion + target_splicing
    
    print(f"Target distribution:")
    print(f"  Copy-move: {target_copy_move}")
    print(f"  Object removal: {target_removal}")
    print(f"  Object insertion: {target_insertion}")
    print(f"  Splicing: {target_splicing}")
    print(f"  Total: {target_total}")
    
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
    
    print(f"\nCurrent manifest: {len(existing_records)} records")
    
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
    
    # Load splits for donor-target safety
    split_inheritance = SplitInheritance(splits_dir)
    donor_splits = {}
    for source in sources:
        donor_splits[source['source_id']] = split_inheritance.get_split(source['source_id'])
    
    # Initialize validator
    validator = GenerationValidator(manifest_path, splits_dir)
    
    all_new_records = []
    
    # Shuffle sources for diversity
    random.seed(42)
    shuffled_sources = sources.copy()
    random.shuffle(shuffled_sources)
    
    # === Scale Copy-Move to 75 ===
    print(f"\n=== Scaling Copy-Move to {target_copy_move} ===")
    current_cm = manip_by_type.get('copy_move', 0)
    needed_cm = target_copy_move - current_cm
    print(f"Need {needed_cm} more copy-move variants")
    
    cm_idx = 0
    for source in shuffled_sources:
        if current_cm >= target_copy_move:
            break
        if source['source_id'] in sources_by_manip.get('copy_move', set()):
            continue
        
        try:
            source_path = source['_file_path']
            image = Image.open(source_path)
            
            gen_result = generate_copy_move(source, image, cm_idx, config, sources_by_manip)
            
            variant_id = generate_variant_id(
                source['image_id'],
                'manipulated',
                'copy_move',
                gen_result['parameters']
            )
            
            if variant_id not in existing_image_ids:
                output_filename = f"{variant_id}.jpg"
                output_path = manipulated_dir / output_filename
                gen_result['result'].save(output_path, quality=config.output_quality)
                
                mask_filename = f"{variant_id}_mask.png"
                mask_path = masks_dir / mask_filename
                Image.fromarray(gen_result['mask']).save(mask_path)
                
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
                    parameters=gen_result['parameters'],
                    seed=config.random_seed + cm_idx,
                    dataset_version=config.dataset_version,
                    metadata_available=False,
                    root_path=root
                )
                
                all_new_records.append(record)
                existing_image_ids.add(variant_id)
                sources_by_manip.setdefault('copy_move', set()).add(source['source_id'])
                current_cm += 1
                cm_idx += 1
                print(f"Generated copy-move {current_cm}/{target_copy_move}: {variant_id}")
        
        except Exception as e:
            print(f"Error generating copy-move for {source['image_id']}: {e}")
    
    # === Scale Object Removal to 75 ===
    print(f"\n=== Scaling Object Removal to {target_removal} ===")
    current_removal = manip_by_type.get('object_removal', 0)
    needed_removal = target_removal - current_removal
    print(f"Need {needed_removal} more removal variants")
    
    removal_idx = 0
    for source in shuffled_sources:
        if current_removal >= target_removal:
            break
        if source['source_id'] in sources_by_manip.get('object_removal', set()):
            continue
        
        try:
            source_path = source['_file_path']
            image = Image.open(source_path)
            
            gen_result = generate_removal(source, image, removal_idx, config, sources_by_manip)
            
            variant_id = generate_variant_id(
                source['image_id'],
                'manipulated',
                'object_removal',
                gen_result['parameters']
            )
            
            if variant_id not in existing_image_ids:
                output_filename = f"{variant_id}.jpg"
                output_path = manipulated_dir / output_filename
                gen_result['result'].save(output_path, quality=config.output_quality)
                
                mask_filename = f"{variant_id}_mask.png"
                mask_path = masks_dir / mask_filename
                Image.fromarray(gen_result['mask']).save(mask_path)
                
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
                    parameters=gen_result['parameters'],
                    seed=config.random_seed + removal_idx + 1000,
                    dataset_version=config.dataset_version,
                    metadata_available=False,
                    root_path=root
                )
                
                all_new_records.append(record)
                existing_image_ids.add(variant_id)
                sources_by_manip.setdefault('object_removal', set()).add(source['source_id'])
                current_removal += 1
                removal_idx += 1
                print(f"Generated removal {current_removal}/{target_removal}: {variant_id}")
        
        except Exception as e:
            print(f"Error generating removal for {source['image_id']}: {e}")
    
    # === Scale Object Insertion to 75 ===
    print(f"\n=== Scaling Object Insertion to {target_insertion} ===")
    current_insertion = manip_by_type.get('object_insertion', 0)
    needed_insertion = target_insertion - current_insertion
    print(f"Need {needed_insertion} more insertion variants")
    
    insertion_idx = 0
    donor_idx = 0
    for source in shuffled_sources:
        if current_insertion >= target_insertion:
            break
        if source['source_id'] in sources_by_manip.get('object_insertion', set()):
            continue
        
        try:
            source_path = source['_file_path']
            image = Image.open(source_path)
            
            # Find a donor from the same split
            target_split = donor_splits.get(source['source_id'], 'train')
            potential_donors = [s for s in shuffled_sources 
                              if donor_splits.get(s['source_id']) == target_split
                              and s['source_id'] != source['source_id']
                              and s['_file_path'] != source_path]
            
            if not potential_donors:
                continue
            
            donor_source = potential_donors[donor_idx % len(potential_donors)]
            donor_image = Image.open(donor_source['_file_path'])
            
            gen_result = generate_insertion(
                source, donor_source, image, donor_image,
                insertion_idx, config, sources_by_manip, donor_splits
            )
            
            variant_id = generate_variant_id(
                source['image_id'],
                'manipulated',
                'object_insertion',
                gen_result['parameters']
            )
            
            if variant_id not in existing_image_ids:
                output_filename = f"{variant_id}.jpg"
                output_path = manipulated_dir / output_filename
                gen_result['result'].save(output_path, quality=config.output_quality)
                
                mask_filename = f"{variant_id}_mask.png"
                mask_path = masks_dir / mask_filename
                Image.fromarray(gen_result['mask']).save(mask_path)
                
                record = build_provenance_record(
                    image_id=variant_id,
                    source_id=source['source_id'],
                    parent_image_id=source['image_id'],
                    parent_source_id=source['source_id'],
                    variant_id=variant_id,
                    category='manipulated',
                    label=1,
                    generation_method='manipulated',
                    processing_operations=['object_insertion'],
                    image_path=str(output_path.relative_to(root)).replace('\\', '/'),
                    mask_path=str(mask_path.relative_to(root)).replace('\\', '/'),
                    mask_id=variant_id + '_mask',
                    manipulation_type='object_insertion',
                    parameters=gen_result['parameters'],
                    seed=config.random_seed + insertion_idx + 2000,
                    dataset_version=config.dataset_version,
                    metadata_available=False,
                    root_path=root
                )
                
                all_new_records.append(record)
                existing_image_ids.add(variant_id)
                sources_by_manip.setdefault('object_insertion', set()).add(source['source_id'])
                current_insertion += 1
                insertion_idx += 1
                donor_idx += 1
                print(f"Generated insertion {current_insertion}/{target_insertion}: {variant_id}")
        
        except Exception as e:
            print(f"Error generating insertion for {source['image_id']}: {e}")
    
    # === Scale Splicing to 75 ===
    print(f"\n=== Scaling Splicing to {target_splicing} ===")
    current_splicing = manip_by_type.get('splicing', 0)
    needed_splicing = target_splicing - current_splicing
    print(f"Need {needed_splicing} more splicing variants")
    
    splicing_idx = 0
    donor_idx = 0
    for source in shuffled_sources:
        if current_splicing >= target_splicing:
            break
        if source['source_id'] in sources_by_manip.get('splicing', set()):
            continue
        
        try:
            source_path = source['_file_path']
            image = Image.open(source_path)
            
            # Find a donor from the same split
            target_split = donor_splits.get(source['source_id'], 'train')
            potential_donors = [s for s in shuffled_sources 
                              if donor_splits.get(s['source_id']) == target_split
                              and s['source_id'] != source['source_id']
                              and s['_file_path'] != source_path]
            
            if not potential_donors:
                continue
            
            donor_source = potential_donors[donor_idx % len(potential_donors)]
            donor_image = Image.open(donor_source['_file_path'])
            
            gen_result = generate_splicing(
                source, donor_source, image, donor_image,
                splicing_idx, config, sources_by_manip, donor_splits
            )
            
            variant_id = generate_variant_id(
                source['image_id'],
                'manipulated',
                'splicing',
                gen_result['parameters']
            )
            
            if variant_id not in existing_image_ids:
                output_filename = f"{variant_id}.jpg"
                output_path = manipulated_dir / output_filename
                gen_result['result'].save(output_path, quality=config.output_quality)
                
                mask_filename = f"{variant_id}_mask.png"
                mask_path = masks_dir / mask_filename
                Image.fromarray(gen_result['mask']).save(mask_path)
                
                record = build_provenance_record(
                    image_id=variant_id,
                    source_id=source['source_id'],
                    parent_image_id=source['image_id'],
                    parent_source_id=source['source_id'],
                    variant_id=variant_id,
                    category='manipulated',
                    label=1,
                    generation_method='manipulated',
                    processing_operations=['splicing'],
                    image_path=str(output_path.relative_to(root)).replace('\\', '/'),
                    mask_path=str(mask_path.relative_to(root)).replace('\\', '/'),
                    mask_id=variant_id + '_mask',
                    manipulation_type='splicing',
                    parameters=gen_result['parameters'],
                    seed=config.random_seed + splicing_idx + 3000,
                    dataset_version=config.dataset_version,
                    metadata_available=False,
                    root_path=root
                )
                
                all_new_records.append(record)
                existing_image_ids.add(variant_id)
                sources_by_manip.setdefault('splicing', set()).add(source['source_id'])
                current_splicing += 1
                splicing_idx += 1
                donor_idx += 1
                print(f"Generated splicing {current_splicing}/{target_splicing}: {variant_id}")
        
        except Exception as e:
            print(f"Error generating splicing for {source['image_id']}: {e}")
    
    print(f"\nGenerated {len(all_new_records)} new manipulation variants")
    
    # Validate batch
    print("Validating generated records...")
    validation = validator.validate_batch(all_new_records)
    
    if not validation['valid']:
        print("VALIDATION FAILED - Not writing to manifest")
        print("Errors:", validation['errors'])
        print("\n=== PHASE 12 FAILED ===")
        return
    
    # Write to manifest
    print("Writing to manifest...")
    with manifest_path.open('a') as f:
        for record in all_new_records:
            f.write(json.dumps(record) + '\n')
    print(f"Wrote {len(all_new_records)} records to manifest")
    
    print("\n=== Phase 12 Complete ===")
    print(f"Total new records: {len(all_new_records)}")
    print(f"Target: {target_total} manipulated records")


if __name__ == '__main__':
    main()

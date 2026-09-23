"""Phase 13: Scale source-family variants to 600 sources with diverse distribution.

Target: 600 source families with variants (more evenly distributed)
Current: 302 sources with variants (251 with 2 categories, 36 with 3, 15 with 4)

Strategy:
- Add natural-processing variants to sources that only have original
- Add hard-negative variants to sources that only have original
- Distribute manipulations more evenly across sources
- Target: ~400 sources with 2 categories, ~150 with 3 categories, ~50 with 4 categories
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
from generators import NaturalProcessingGenerator, ManipulationGenerator


def main():
    """Scale source-family variants to 600 sources with diverse distribution."""
    print("=== Phase 13: Scaling Source-Family Variants to 600 Sources ===")
    
    config = GenerationConfig()
    
    root = Path(__file__).resolve().parent.parent
    
    # Initialize paths
    variants_dir = root / config.variants_dir
    natural_dir = variants_dir / config.natural_processing_dir
    hard_negative_dir = variants_dir / config.hard_negative_dir
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
    
    # Analyze current source-family distribution
    sources_by_categories = {}
    for record in existing_records:
        source_id = record['source_id']
        category = record['category']
        if source_id not in sources_by_categories:
            sources_by_categories[source_id] = set()
        sources_by_categories[source_id].add(category)
    
    # Count sources by category count
    category_counts = {}
    for source_id, categories in sources_by_categories.items():
        count = len(categories)
        category_counts[count] = category_counts.get(count, 0) + 1
    
    print(f"\nCurrent source-family distribution:")
    for count in sorted(category_counts.keys()):
        print(f"  Sources with {count} category(ies): {category_counts[count]}")
    
    # Identify sources with only original (need variants)
    sources_only_original = [
        s for s in sources
        if len(sources_by_categories.get(s['source_id'], set())) == 1
    ]
    
    print(f"\nSources with only original: {len(sources_only_original)}")
    
    # Shuffle for diversity
    random.seed(43)
    random.shuffle(sources_only_original)
    
    # Target: Add variants to 300 more sources (from 302 to 602)
    target_new_sources = 300
    sources_to_enrich = sources_only_original[:target_new_sources]
    
    print(f"Target: Add variants to {len(sources_to_enrich)} more sources")
    
    # Initialize validator
    validator = GenerationValidator(manifest_path, splits_dir)
    split_inheritance = SplitInheritance(splits_dir)
    
    all_new_records = []
    
    # === Add natural-processing variants (1 per source) ===
    print(f"\n=== Adding Natural-Processing Variants ===")
    
    np_operations = [
        ('jpeg_recompression', lambda img, idx: NaturalProcessingGenerator.jpeg_recompress(img, config.jpeg_quality_range[idx % len(config.jpeg_quality_range)])),
        ('resize', lambda img, idx: NaturalProcessingGenerator.resize(img, config.resize_scale_range[idx % len(config.resize_scale_range)])),
        ('sharpen', lambda img, idx: NaturalProcessingGenerator.sharpen(img, config.sharpen_strength_range[idx % len(config.sharpen_strength_range)])),
        ('brightness', lambda img, idx: NaturalProcessingGenerator.adjust_brightness(img, 1.0 + config.brightness_range[idx % len(config.brightness_range)] / 100.0)),
        ('contrast', lambda img, idx: NaturalProcessingGenerator.adjust_contrast(img, config.contrast_range[idx % len(config.contrast_range)])),
        ('color', lambda img, idx: NaturalProcessingGenerator.adjust_color(img, config.color_range[idx % len(config.color_range)])),
        ('gamma', lambda img, idx: NaturalProcessingGenerator.adjust_gamma(img, config.gamma_range[idx % len(config.gamma_range)])),
        ('denoise', lambda img, idx: NaturalProcessingGenerator.denoise(img, config.denoise_strength_range[idx % len(config.denoise_strength_range)])),
        ('format_conversion', lambda img, idx: NaturalProcessingGenerator.format_conversion(img, config.format_options[idx % len(config.format_options)]))
    ]
    
    np_idx = 0
    for source in sources_to_enrich:
        op_name, op_func = np_operations[np_idx % len(np_operations)]
        
        try:
            source_path = source['_file_path']
            image = Image.open(source_path)
            
            result = op_func(image, np_idx)
            
            variant_id = generate_variant_id(
                source['image_id'],
                'natural_processing',
                op_name,
                {'operation': op_name, 'index': np_idx}
            )
            
            if variant_id not in existing_image_ids:
                output_filename = f"{variant_id}.jpg"
                output_path = natural_dir / output_filename
                result.save(output_path, quality=config.output_quality)
                
                record = build_provenance_record(
                    image_id=variant_id,
                    source_id=source['source_id'],
                    parent_image_id=source['image_id'],
                    parent_source_id=source['source_id'],
                    variant_id=variant_id,
                    category='natural_processing',
                    label=0,
                    generation_method='natural_processing',
                    processing_operations=[op_name],
                    image_path=str(output_path.relative_to(root)).replace('\\', '/'),
                    parameters={'operation': op_name, 'index': np_idx},
                    seed=config.random_seed + np_idx,
                    dataset_version=config.dataset_version,
                    metadata_available=False,
                    root_path=root
                )
                
                all_new_records.append(record)
                existing_image_ids.add(variant_id)
                np_idx += 1
                print(f"Generated NP: {variant_id} ({op_name})")
        
        except Exception as e:
            print(f"Error generating NP for {source['image_id']}: {e}")
    
    # === Add hard-negative variants (1 per source) ===
    print(f"\n=== Adding Hard-Negative Variants ===")
    
    hn_operations = [
        ('jpeg_recompression', lambda img, idx: NaturalProcessingGenerator.jpeg_recompress(img, config.hn_jpeg_quality_range[idx % len(config.hn_jpeg_quality_range)])),
        ('resize', lambda img, idx: NaturalProcessingGenerator.resize(img, config.hn_resize_scale_range[idx % len(config.hn_resize_scale_range)])),
        ('sharpen', lambda img, idx: NaturalProcessingGenerator.sharpen(img, config.hn_sharpen_strength_range[idx % len(config.hn_sharpen_strength_range)])),
        ('color', lambda img, idx: NaturalProcessingGenerator.adjust_color(img, config.hn_color_range[idx % len(config.hn_color_range)])),
        ('gamma', lambda img, idx: NaturalProcessingGenerator.adjust_gamma(img, config.hn_gamma_range[idx % len(config.hn_gamma_range)])),
        ('denoise', lambda img, idx: NaturalProcessingGenerator.denoise(img, config.hn_denoise_strength_range[idx % len(config.hn_denoise_strength_range)]))
    ]
    
    hn_idx = 0
    for source in sources_to_enrich:
        op_name, op_func = hn_operations[hn_idx % len(hn_operations)]
        
        try:
            source_path = source['_file_path']
            image = Image.open(source_path)
            
            result = op_func(image, hn_idx)
            
            variant_id = generate_variant_id(
                source['image_id'],
                'hard_negative',
                op_name,
                {'operation': op_name, 'index': hn_idx}
            )
            
            if variant_id not in existing_image_ids:
                output_filename = f"{variant_id}.jpg"
                output_path = hard_negative_dir / output_filename
                result.save(output_path, quality=config.output_quality)
                
                record = build_provenance_record(
                    image_id=variant_id,
                    source_id=source['source_id'],
                    parent_image_id=source['image_id'],
                    parent_source_id=source['source_id'],
                    variant_id=variant_id,
                    category='hard_negative',
                    label=0,
                    generation_method='hard_negative',
                    processing_operations=[op_name],
                    image_path=str(output_path.relative_to(root)).replace('\\', '/'),
                    parameters={'operation': op_name, 'index': hn_idx},
                    seed=config.random_seed + hn_idx + 5000,
                    dataset_version=config.dataset_version,
                    metadata_available=False,
                    root_path=root
                )
                
                all_new_records.append(record)
                existing_image_ids.add(variant_id)
                hn_idx += 1
                print(f"Generated HN: {variant_id} ({op_name})")
        
        except Exception as e:
            print(f"Error generating HN for {source['image_id']}: {e}")
    
    print(f"\nGenerated {len(all_new_records)} new source-family variants")
    
    # Validate batch
    print("Validating generated records...")
    validation = validator.validate_batch(all_new_records)
    
    if not validation['valid']:
        print("VALIDATION FAILED - Not writing to manifest")
        print("Errors:", validation['errors'])
        print("\n=== PHASE 13 FAILED ===")
        return
    
    # Write to manifest
    print("Writing to manifest...")
    with manifest_path.open('a') as f:
        for record in all_new_records:
            f.write(json.dumps(record) + '\n')
    print(f"Wrote {len(all_new_records)} records to manifest")
    
    print("\n=== Phase 13 Complete ===")
    print(f"Total new records: {len(all_new_records)}")
    print(f"Enriched {len(sources_to_enrich)} source families")


if __name__ == '__main__':
    main()

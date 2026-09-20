"""Regenerate only the missing hard-negative variants with new parameters."""

import json
import hashlib
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
from generators import NaturalProcessingGenerator


def main():
    """Regenerate missing hard-negative variants."""
    print("=== Regenerating Missing Hard-Negative Variants ===")
    
    config = GenerationConfig()
    root = Path(__file__).resolve().parent.parent
    
    # Initialize paths
    variants_dir = root / config.variants_dir
    hard_negative_dir = variants_dir / config.hard_negative_dir
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
    
    # Sources that need hard-negative regeneration (the 4 from duplicates)
    target_source_ids = [
        "SRC_DW_00A22693F8CDC9EF",
        "SRC_DW_00D4416E355B20D7", 
        "SRC_DW_0138F4EB08B55EB8",
        "SRC_DW_034C5182F470F1B3"
    ]
    
    target_sources = [s for s in sources if s['source_id'] in target_source_ids]
    print(f"Found {len(target_sources)} target sources for regeneration")
    
    # Initialize validator
    validator = GenerationValidator(manifest_path, splits_dir)
    
    all_records = []
    
    # Generate hard negatives for target sources with new parameters
    for source in target_sources:
        source_path = source['_file_path']
        image = Image.open(source_path)
        
        # Use deterministic parameter selection based on source index
        source_idx = hash(source['source_id']) % 1000
        
        # Use NEW hard-negative parameter ranges
        hn_quality = config.hn_jpeg_quality_range[source_idx % len(config.hn_jpeg_quality_range)]
        hn_scale = config.hn_resize_scale_range[source_idx % len(config.hn_resize_scale_range)]
        hn_sharpen = config.hn_sharpen_strength_range[source_idx % len(config.hn_sharpen_strength_range)]
        
        operations = [
            ('jpeg_recompression', {'quality': hn_quality}),
            ('resize', {'scale': hn_scale}),
            ('sharpen', {'strength': hn_sharpen}),
        ]
        
        for op_name, params in operations:
            try:
                # Apply operation
                if op_name == 'jpeg_recompression':
                    result = NaturalProcessingGenerator.jpeg_recompress(image, params['quality'])
                elif op_name == 'resize':
                    result = NaturalProcessingGenerator.resize(image, params['scale'])
                elif op_name == 'sharpen':
                    result = NaturalProcessingGenerator.sharpen(image, params['strength'])
                else:
                    continue
                
                # Generate variant ID
                variant_id = generate_variant_id(
                    source['image_id'],
                    'hard_negative',
                    op_name,
                    params
                )
                
                # Skip if already exists
                if variant_id in existing_image_ids:
                    print(f"Skipping existing: {variant_id}")
                    continue
                
                # Save image
                output_filename = f"{variant_id}.jpg"
                output_path = hard_negative_dir / output_filename
                result.save(output_path, quality=config.output_quality)
                
                # Build record
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
                    parameters=params,
                    seed=config.random_seed,
                    dataset_version=config.dataset_version,
                    metadata_available=False
                )
                
                all_records.append(record)
                existing_image_ids.add(variant_id)
                print(f"Generated: {variant_id}")
                
            except Exception as e:
                print(f"Error generating {op_name} for {source['image_id']}: {e}")
    
    print(f"\nGenerated {len(all_records)} new hard-negative variants")
    
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
    
    print("\n=== Regeneration Complete ===")


if __name__ == '__main__':
    main()

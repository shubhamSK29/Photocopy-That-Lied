"""Regenerate natural-processing and hard-negative variants with expanded operations."""

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
from generation_validator import GenerationValidator
from generators import NaturalProcessingGenerator


def main():
    """Regenerate natural-processing and hard-negative variants with expanded operations."""
    print("=== Regenerating Natural-Processing and Hard-Negative Variants ===")
    
    config = GenerationConfig()
    root = Path(__file__).resolve().parent.parent
    
    # Initialize paths
    variants_dir = root / config.variants_dir
    natural_dir = variants_dir / config.natural_processing_dir
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
    
    # Remove existing natural-processing and hard-negative records from manifest
    non_processing = [r for r in existing_records if r.get('category') not in ['natural_processing', 'hard_negative']]
    np_count = len([r for r in existing_records if r.get('category') == 'natural_processing'])
    hn_count = len([r for r in existing_records if r.get('category') == 'hard_negative'])
    print(f"Removing {np_count} natural-processing and {hn_count} hard-negative records from manifest")
    
    # Delete existing files
    for file in natural_dir.glob('*.jpg'):
        file.unlink()
    for file in hard_negative_dir.glob('*.jpg'):
        file.unlink()
    print("Deleted existing natural-processing and hard-negative files")
    
    # Rewrite manifest without processing records
    with manifest_path.open('w') as f:
        for record in non_processing:
            f.write(json.dumps(record) + '\n')
    print("Rewrote manifest without processing records")
    
    # Get source images
    sources = [
        r for r in non_processing
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
    
    existing_image_ids = {r['image_id'] for r in non_processing}
    
    # Initialize validator
    validator = GenerationValidator(manifest_path, splits_dir)
    
    all_records = []
    
    # Generate natural-processing variants
    print("\nGenerating natural-processing variants...")
    for source in sources[:config.pilot_natural_count]:
        try:
            source_path = source['_file_path']
            image = Image.open(source_path)
            
            source_idx = hash(source['source_id']) % 1000
            
            quality = config.jpeg_quality_range[source_idx % len(config.jpeg_quality_range)]
            scale = config.resize_scale_range[source_idx % len(config.resize_scale_range)]
            sharpen = config.sharpen_strength_range[source_idx % len(config.sharpen_strength_range)]
            brightness = 1.0 + config.brightness_range[source_idx % len(config.brightness_range)] / 100.0
            contrast = config.contrast_range[source_idx % len(config.contrast_range)]
            color = config.color_range[source_idx % len(config.color_range)]
            gamma = config.gamma_range[source_idx % len(config.gamma_range)]
            denoise = config.denoise_strength_range[source_idx % len(config.denoise_strength_range)]
            target_format = config.format_options[source_idx % len(config.format_options)]
            
            operations = [
                ('jpeg_recompression', {'quality': quality}),
                ('resize', {'scale': scale}),
                ('sharpen', {'strength': sharpen}),
                ('brightness', {'factor': brightness}),
                ('contrast', {'factor': contrast}),
                ('color', {'factor': color}),
                ('gamma', {'gamma': gamma}),
                ('denoise', {'strength': denoise}),
                ('format_conversion', {'target_format': target_format}),
            ]
            
            for op_name, params in operations:
                try:
                    if op_name == 'jpeg_recompression':
                        result = NaturalProcessingGenerator.jpeg_recompress(image, params['quality'])
                    elif op_name == 'resize':
                        result = NaturalProcessingGenerator.resize(image, params['scale'])
                    elif op_name == 'sharpen':
                        result = NaturalProcessingGenerator.sharpen(image, params['strength'])
                    elif op_name == 'brightness':
                        result = NaturalProcessingGenerator.adjust_brightness(image, params['factor'])
                    elif op_name == 'contrast':
                        result = NaturalProcessingGenerator.adjust_contrast(image, params['factor'])
                    elif op_name == 'color':
                        result = NaturalProcessingGenerator.adjust_color(image, params['factor'])
                    elif op_name == 'gamma':
                        result = NaturalProcessingGenerator.adjust_gamma(image, params['gamma'])
                    elif op_name == 'denoise':
                        result = NaturalProcessingGenerator.denoise(image, params['strength'])
                    elif op_name == 'format_conversion':
                        result = NaturalProcessingGenerator.format_conversion(image, params['target_format'])
                    else:
                        continue
                    
                    variant_id = generate_variant_id(
                        source['image_id'],
                        'natural_processing',
                        op_name,
                        params
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
                            parameters=params,
                            seed=config.random_seed,
                            dataset_version=config.dataset_version,
                            metadata_available=False,
                            root_path=root
                        )
                        
                        all_records.append(record)
                        existing_image_ids.add(variant_id)
                        print(f"Generated natural-processing: {variant_id}")
                
                except Exception as e:
                    print(f"Error generating {op_name} for {source['image_id']}: {e}")
        
        except Exception as e:
            print(f"Error processing source {source['image_id']}: {e}")
    
    # Generate hard-negative variants
    print("\nGenerating hard-negative variants...")
    for source in sources[config.pilot_natural_count:config.pilot_natural_count + config.pilot_hard_negative_count]:
        try:
            source_path = source['_file_path']
            image = Image.open(source_path)
            
            source_idx = hash(source['source_id']) % 1000
            
            hn_quality = config.hn_jpeg_quality_range[source_idx % len(config.hn_jpeg_quality_range)]
            hn_scale = config.hn_resize_scale_range[source_idx % len(config.hn_resize_scale_range)]
            hn_sharpen = config.hn_sharpen_strength_range[source_idx % len(config.hn_sharpen_strength_range)]
            hn_color = config.hn_color_range[source_idx % len(config.hn_color_range)]
            hn_gamma = config.hn_gamma_range[source_idx % len(config.hn_gamma_range)]
            hn_denoise = config.hn_denoise_strength_range[source_idx % len(config.hn_denoise_strength_range)]
            
            operations = [
                ('jpeg_recompression', {'quality': hn_quality}),
                ('resize', {'scale': hn_scale}),
                ('sharpen', {'strength': hn_sharpen}),
                ('color', {'factor': hn_color}),
                ('gamma', {'gamma': hn_gamma}),
                ('denoise', {'strength': hn_denoise}),
            ]
            
            for op_name, params in operations:
                try:
                    if op_name == 'jpeg_recompression':
                        result = NaturalProcessingGenerator.jpeg_recompress(image, params['quality'])
                    elif op_name == 'resize':
                        result = NaturalProcessingGenerator.resize(image, params['scale'])
                    elif op_name == 'sharpen':
                        result = NaturalProcessingGenerator.sharpen(image, params['strength'])
                    elif op_name == 'color':
                        result = NaturalProcessingGenerator.adjust_color(image, params['factor'])
                    elif op_name == 'gamma':
                        result = NaturalProcessingGenerator.adjust_gamma(image, params['gamma'])
                    elif op_name == 'denoise':
                        result = NaturalProcessingGenerator.denoise(image, params['strength'])
                    else:
                        continue
                    
                    variant_id = generate_variant_id(
                        source['image_id'],
                        'hard_negative',
                        op_name,
                        params
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
                            parameters=params,
                            seed=config.random_seed,
                            dataset_version=config.dataset_version,
                            metadata_available=False,
                            root_path=root
                        )
                        
                        all_records.append(record)
                        existing_image_ids.add(variant_id)
                        print(f"Generated hard-negative: {variant_id}")
                
                except Exception as e:
                    print(f"Error generating {op_name} for {source['image_id']}: {e}")
        
        except Exception as e:
            print(f"Error processing source {source['image_id']}: {e}")
    
    print(f"\nGenerated {len(all_records)} processing variants total")
    
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
    
    print("\n=== Processing Variants Regeneration Complete ===")


if __name__ == '__main__':
    main()

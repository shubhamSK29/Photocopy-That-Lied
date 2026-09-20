"""Scale Dataset V2 to 250 source families with controlled generation."""

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
from generators import NaturalProcessingGenerator, ManipulationGenerator


def main():
    """Scale dataset to 250 sources with all variant types."""
    print("=== Scaling Dataset V2 to 250 Sources ===")
    
    config = GenerationConfig()
    config.pilot_natural_count = 125  # Scale NP to 125 sources
    config.pilot_hard_negative_count = 125  # Scale HN to 125 sources
    config.pilot_copy_move_count = 25  # Scale copy-move to 25
    config.pilot_removal_count = 15  # Scale removal to 15
    config.pilot_insertion_count = 10  # Scale insertion to 10
    config.pilot_splicing_count = 10  # Scale splicing to 10
    config.pilot_manipulated_count = config.pilot_copy_move_count + config.pilot_removal_count + config.pilot_insertion_count + config.pilot_splicing_count
    
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
    
    # Track which sources already have variants
    sources_with_np = set()
    sources_with_hn = set()
    sources_with_manip = set()
    
    for record in existing_records:
        if record.get('category') == 'natural_processing':
            sources_with_np.add(record['source_id'])
        elif record.get('category') == 'hard_negative':
            sources_with_hn.add(record['source_id'])
        elif record.get('category') == 'manipulated':
            sources_with_manip.add(record['source_id'])
    
    print(f"Sources with NP: {len(sources_with_np)}")
    print(f"Sources with HN: {len(sources_with_hn)}")
    print(f"Sources with manip: {len(sources_with_manip)}")
    
    # Initialize validator
    validator = GenerationValidator(manifest_path, splits_dir)
    split_inheritance = SplitInheritance(splits_dir)
    
    all_new_records = []
    
    # === Scale Natural-Processing to 125 sources ===
    print(f"\n=== Scaling Natural-Processing to {config.pilot_natural_count} sources ===")
    np_sources = sources[:config.pilot_natural_count]
    
    for source in np_sources:
        if source['source_id'] in sources_with_np:
            print(f"Skipping {source['source_id']} (already has NP)")
            continue
        
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
                        
                        all_new_records.append(record)
                        existing_image_ids.add(variant_id)
                        print(f"Generated NP: {variant_id}")
                
                except Exception as e:
                    print(f"Error generating {op_name} for {source['image_id']}: {e}")
        
        except Exception as e:
            print(f"Error processing source {source['image_id']}: {e}")
    
    # === Scale Hard-Negative to 125 sources ===
    print(f"\n=== Scaling Hard-Negative to {config.pilot_hard_negative_count} sources ===")
    hn_sources = sources[config.pilot_natural_count:config.pilot_natural_count + config.pilot_hard_negative_count]
    
    for source in hn_sources:
        if source['source_id'] in sources_with_hn:
            print(f"Skipping {source['source_id']} (already has HN)")
            continue
        
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
                        
                        all_new_records.append(record)
                        existing_image_ids.add(variant_id)
                        print(f"Generated HN: {variant_id}")
                
                except Exception as e:
                    print(f"Error generating {op_name} for {source['image_id']}: {e}")
        
        except Exception as e:
            print(f"Error processing source {source['image_id']}: {e}")
    
    print(f"\nGenerated {len(all_new_records)} new processing variants")
    
    # Validate batch
    print("Validating generated records...")
    validation = validator.validate_batch(all_new_records)
    
    if not validation['valid']:
        print("VALIDATION FAILED - Not writing to manifest")
        print("Errors:", validation['errors'])
        print("\n=== SCALING FAILED ===")
        return
    
    # Write to manifest
    print("Writing to manifest...")
    with manifest_path.open('a') as f:
        for record in all_new_records:
            f.write(json.dumps(record) + '\n')
    print(f"Wrote {len(all_new_records)} records to manifest")
    
    print("\n=== Processing Scaling Complete ===")
    print(f"Total new records: {len(all_new_records)}")
    print("Next: Scale manipulations (separate script)")


if __name__ == '__main__':
    main()

"""Pilot variant generator for Dataset V2."""

import json
import hashlib
import sys
from pathlib import Path
from typing import List, Dict, Any
from PIL import Image

# Add dataset_v2 directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from generation_config import GenerationConfig
from variant_ids import generate_variant_id
from provenance import build_provenance_record, compute_sha256
from split_inheritance import SplitInheritance
from generation_validator import GenerationValidator
from generators import NaturalProcessingGenerator, ManipulationGenerator


class PilotGenerator:
    """Generate pilot Dataset V2 variants."""

    def __init__(self, config: GenerationConfig = None):
        """
        Initialize pilot generator.

        Args:
            config: Generation configuration (uses default if not provided)
        """
        self.config = config or GenerationConfig()
        self.root = Path(__file__).resolve().parent.parent.parent

        # Initialize paths
        self.variants_dir = self.root / self.config.variants_dir
        self.natural_dir = self.variants_dir / self.config.natural_processing_dir
        self.manipulated_dir = self.variants_dir / self.config.manipulated_dir
        self.hard_negative_dir = self.variants_dir / self.config.hard_negative_dir
        self.masks_dir = self.variants_dir / self.config.masks_dir

        # Ensure paths are resolved
        self.natural_dir = self.natural_dir.resolve()
        self.manipulated_dir = self.manipulated_dir.resolve()
        self.hard_negative_dir = self.hard_negative_dir.resolve()
        self.masks_dir = self.masks_dir.resolve()
        self.sources_dir = self.root / self.config.sources_dir
        self.manifest_path = self.root / self.config.manifest_path
        self.splits_dir = self.root / self.config.splits_dir

        # Create directories
        self.natural_dir.mkdir(parents=True, exist_ok=True)
        self.manipulated_dir.mkdir(parents=True, exist_ok=True)
        self.hard_negative_dir.mkdir(parents=True, exist_ok=True)
        self.masks_dir.mkdir(parents=True, exist_ok=True)

        # Initialize components
        self.split_inheritance = SplitInheritance(self.splits_dir)
        self.validator = GenerationValidator(self.manifest_path, self.splits_dir)

        # Load manifest
        self.existing_records = self._load_manifest()
        self.existing_image_ids = {r['image_id'] for r in self.existing_records}

    def _load_manifest(self) -> List[Dict[str, Any]]:
        """Load existing manifest records."""
        records = []
        if self.manifest_path.exists():
            with self.manifest_path.open() as f:
                for line in f:
                    if line.strip():
                        records.append(json.loads(line))
        return records

    def _get_source_images(self) -> List[Dict[str, Any]]:
        """
        Get source images from manifest.

        Returns:
            List of source image records (original DeepWeeds images)
        """
        # Filter for original DeepWeeds records
        sources = [
            r for r in self.existing_records
            if r.get('category') == 'original' and r.get('source_id', '').startswith('SRC_DW')
        ]

        # Build SHA-256 to path mapping
        sha256_to_path = {}
        for img_path in self.sources_dir.glob('*.jpg'):
            sha256 = compute_sha256(img_path)
            sha256_to_path[sha256] = img_path

        # Add file paths to records
        for record in sources:
            sha256 = record.get('sha256')
            if sha256 in sha256_to_path:
                record['_file_path'] = sha256_to_path[sha256]

        return sources

    def _select_pilot_sources(self, sources: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Select pilot source images deterministically.

        Args:
            sources: All available source images

        Returns:
            Selected source images for pilot
        """
        # Sort by source_id for deterministic selection
        sources_sorted = sorted(sources, key=lambda x: x['source_id'])

        # Select first N sources
        return sources_sorted[:self.config.pilot_source_count]

    def _generate_natural_processing(self, source: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate natural-processing variants from a source."""
        variants = []
        source_path = source['_file_path']
        image = Image.open(source_path)

        # Use deterministic parameter selection based on source index
        source_idx = hash(source['source_id']) % 1000

        # Define operations with parameter ranges - deterministic per source
        quality = self.config.jpeg_quality_range[source_idx % len(self.config.jpeg_quality_range)]
        scale = self.config.resize_scale_range[source_idx % len(self.config.resize_scale_range)]
        sharpen = self.config.sharpen_strength_range[source_idx % len(self.config.sharpen_strength_range)]
        brightness = 1.0 + self.config.brightness_range[source_idx % len(self.config.brightness_range)] / 100.0
        contrast = self.config.contrast_range[source_idx % len(self.config.contrast_range)]
        color = self.config.color_range[source_idx % len(self.config.color_range)]
        gamma = self.config.gamma_range[source_idx % len(self.config.gamma_range)]
        denoise = self.config.denoise_strength_range[source_idx % len(self.config.denoise_strength_range)]
        target_format = self.config.format_options[source_idx % len(self.config.format_options)]

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
                # Apply operation
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

                # Generate variant ID
                variant_id = generate_variant_id(
                    source['image_id'],
                    'natural_processing',
                    op_name,
                    params
                )

                # Skip if already exists
                if variant_id in self.existing_image_ids:
                    continue

                # Save image
                output_filename = f"{variant_id}.jpg"
                output_path = self.natural_dir / output_filename
                result.save(output_path, quality=self.config.output_quality)

                # Use forward slashes for cross-platform compatibility
                relative_path = str(output_path.relative_to(self.root)).replace('\\', '/')

                # Build record
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
                    image_path=str(output_path.relative_to(self.root)).replace('\\', '/'),
                    parameters=params,
                    seed=self.config.random_seed,
                    dataset_version=self.config.dataset_version,
                    metadata_available=False,
                    root_path=self.root
                )

                variants.append(record)
                self.existing_image_ids.add(variant_id)

            except Exception as e:
                print(f"Error generating {op_name} for {source['image_id']}: {e}")

        return variants

    def _generate_hard_negative(self, source: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate hard-negative variants from a source."""
        variants = []
        source_path = source['_file_path']
        image = Image.open(source_path)

        # Use deterministic parameter selection based on source index
        source_idx = hash(source['source_id']) % 1000

        # Hard negatives use aggressive legitimate processing (different from natural)
        # Use dedicated hard-negative parameter ranges to avoid overlap
        hn_quality = self.config.hn_jpeg_quality_range[source_idx % len(self.config.hn_jpeg_quality_range)]
        hn_scale = self.config.hn_resize_scale_range[source_idx % len(self.config.hn_resize_scale_range)]
        hn_sharpen = self.config.hn_sharpen_strength_range[source_idx % len(self.config.hn_sharpen_strength_range)]
        hn_color = self.config.hn_color_range[source_idx % len(self.config.hn_color_range)]
        hn_gamma = self.config.hn_gamma_range[source_idx % len(self.config.hn_gamma_range)]
        hn_denoise = self.config.hn_denoise_strength_range[source_idx % len(self.config.hn_denoise_strength_range)]

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
                # Apply operation
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

                # Generate variant ID
                variant_id = generate_variant_id(
                    source['image_id'],
                    'hard_negative',
                    op_name,
                    params
                )

                # Skip if already exists
                if variant_id in self.existing_image_ids:
                    continue

                # Save image
                output_filename = f"{variant_id}.jpg"
                output_path = self.hard_negative_dir / output_filename
                result.save(output_path, quality=self.config.output_quality)

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
                    image_path=str(output_path.relative_to(self.root)).replace('\\', '/'),
                    parameters=params,
                    seed=self.config.random_seed,
                    dataset_version=self.config.dataset_version,
                    metadata_available=False,
                    root_path=self.root
                )

                variants.append(record)
                self.existing_image_ids.add(variant_id)

            except Exception as e:
                print(f"Error generating hard negative {op_name} for {source['image_id']}: {e}")

        return variants

    def _generate_manipulated(self, sources: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate manipulated variants with controlled diversity."""
        variants = []

        # Generate copy-move variants with diverse parameters
        for source in sources[:self.config.pilot_copy_move_count]:  # Limit to configured count
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
                rotation = self.config.copy_move_rotation_range[source_idx % len(self.config.copy_move_rotation_range)]
                scale = self.config.copy_move_scale_range[source_idx % len(self.config.copy_move_scale_range)]
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

                if variant_id not in self.existing_image_ids:
                    # Save image
                    output_filename = f"{variant_id}.jpg"
                    output_path = self.manipulated_dir / output_filename
                    result.save(output_path, quality=self.config.output_quality)

                    # Save mask
                    mask_filename = f"{variant_id}_mask.png"
                    mask_path = self.masks_dir / mask_filename
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
                        image_path=str(output_path.relative_to(self.root)).replace('\\', '/'),
                        mask_path=str(mask_path.relative_to(self.root)).replace('\\', '/'),
                        mask_id=variant_id + '_mask',
                        manipulation_type='copy_move',
                        parameters={
                            'source_region': (src_x, src_y, src_w, src_h),
                            'dest_region': (dest_x, dest_y, dest_w, dest_h),
                            'rotation': rotation,
                            'scale': scale,
                            'blend': blend
                        },
                        seed=self.config.random_seed,
                        dataset_version=self.config.dataset_version,
                        metadata_available=False,
                        root_path=self.root
                    )

                    variants.append(record)
                    self.existing_image_ids.add(variant_id)
                    print(f"Generated copy-move: {variant_id}")

            except Exception as e:
                print(f"Error generating copy-move for {source['image_id']}: {e}")

        # Generate object removal variants
        for source in sources[self.config.pilot_copy_move_count:self.config.pilot_copy_move_count + self.config.pilot_removal_count]:
            try:
                source_img = Image.open(source['_file_path'])
                w, h = source_img.size
                
                # Use deterministic parameter selection based on source index
                source_idx = hash(source['source_id']) % 1000
                
                # Diverse removal regions and parameters
                region_config = self.config.removal_region_configs[source_idx % len(self.config.removal_region_configs)]
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
                inpainting_method = self.config.removal_inpainting_methods[source_idx % len(self.config.removal_inpainting_methods)]
                inpaint_radius = self.config.removal_inpaint_radius[source_idx % len(self.config.removal_inpaint_radius)]
                
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

                if variant_id not in self.existing_image_ids:
                    # Save image
                    output_filename = f"{variant_id}.jpg"
                    output_path = self.manipulated_dir / output_filename
                    result.save(output_path, quality=self.config.output_quality)

                    # Save mask
                    mask_filename = f"{variant_id}_mask.png"
                    mask_path = self.masks_dir / mask_filename
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
                        image_path=str(output_path.relative_to(self.root)).replace('\\', '/'),
                        mask_path=str(mask_path.relative_to(self.root)).replace('\\', '/'),
                        mask_id=variant_id + '_mask',
                        manipulation_type='object_removal',
                        parameters={
                            'removed_region': (region_x, region_y, region_w, region_h),
                            'inpainting_method': inpainting_method,
                            'inpaint_radius': inpaint_radius
                        },
                        seed=self.config.random_seed,
                        dataset_version=self.config.dataset_version,
                        metadata_available=False,
                        root_path=self.root
                    )

                    variants.append(record)
                    self.existing_image_ids.add(variant_id)
                    print(f"Generated object removal: {variant_id}")

            except Exception as e:
                print(f"Error generating object removal for {source['image_id']}: {e}")

        return variants

    def generate_pilot(self) -> Dict[str, Any]:
        """
        Generate the pilot dataset.

        Returns:
            Generation results
        """
        print("=== Dataset V2 Pilot Generation ===")

        # Get sources
        sources = self._get_source_images()
        print(f"Available sources: {len(sources)}")

        # Select pilot sources
        pilot_sources = self._select_pilot_sources(sources)
        print(f"Selected pilot sources: {len(pilot_sources)}")

        all_records = []

        # Generate natural processing
        print("Generating natural-processing variants...")
        for source in pilot_sources:
            variants = self._generate_natural_processing(source)
            all_records.extend(variants)

        print(f"Generated {len(all_records)} natural-processing variants")

        # Generate hard negatives
        print("Generating hard-negative variants...")
        for source in pilot_sources:
            variants = self._generate_hard_negative(source)
            all_records.extend(variants)

        print(f"Generated {len(all_records)} total variants (including hard negatives)")

        # Generate manipulated
        print("Generating manipulated variants...")
        manipulated = self._generate_manipulated(pilot_sources)
        all_records.extend(manipulated)

        print(f"Generated {len(all_records)} total variants (including manipulated)")

        # Validate
        print("Validating generated records...")
        validation = self.validator.validate_batch(all_records)

        # Check split leakage
        leakage = self.validator.check_split_leakage(all_records)

        # Write to manifest (append)
        if validation['valid']:
            print("Writing to manifest...")
            with self.manifest_path.open('a') as f:
                for record in all_records:
                    f.write(json.dumps(record) + '\n')
            print(f"Wrote {len(all_records)} records to manifest")
        else:
            print("Validation failed, not writing to manifest")
            print("Errors:", validation['errors'])

        return {
            'total_generated': len(all_records),
            'validation': validation,
            'leakage': leakage,
            'records': all_records
        }


def main():
    """Main entry point for pilot generation."""
    generator = PilotGenerator()
    results = generator.generate_pilot()

    print("\n=== Pilot Generation Results ===")
    print(f"Total generated: {results['total_generated']}")
    print(f"Validation valid: {results['validation']['valid']}")
    print(f"Errors: {len(results['validation']['errors'])}")
    print(f"Leakage detected: {results['leakage']['has_leakage']}")

    if results['validation']['errors']:
        print("\nErrors:")
        for error in results['validation']['errors'][:10]:
            print(f"  {error}")


if __name__ == '__main__':
    main()

"""DeepWeeds source image importer for Dataset V2.

This script imports a controlled subset of DeepWeeds agricultural photographs
into Dataset V2 as genuine original images.

DeepWeeds Dataset Information:
- Source: University of Queensland DeepWeeds dataset
- License: CC BY 4.0 (Creative Commons Attribution 4.0 International)
- Content: Agricultural weed and crop photographs
- Count: ~17,509 images in original dataset
- Format: JPEG, 256x256, RGB

Note: Split assignment is handled separately by create_dataset_v2_splits.py
to maintain architectural consistency across all Dataset V2 sources.

Usage:
    python scripts/import_deepweeds.py --limit 1000
    python scripts/import_deepweeds.py --limit 1000 --seed 42
    python scripts/import_deepweeds.py --limit 1000 --dry-run
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from PIL import Image, ImageOps
from PIL.ExifTags import TAGS

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent
DATASET_V2_ROOT = PROJECT_ROOT / "dataset_v2"
DEEPWEEDS_SOURCE = DATASET_V2_ROOT / "sources" / "deepweeds_raw" / "images"
MANIFEST_PATH = DATASET_V2_ROOT / "metadata" / "manifest.jsonl"
SCHEMA_PATH = DATASET_V2_ROOT / "metadata" / "schema.json"

# DeepWeeds provenance information
DEEPWEEDS_PROVENANCE = {
    "source": "DeepWeeds - University of Queensland",
    "license": "CC BY 4.0",
    "license_url": "https://creativecommons.org/licenses/by/4.0/",
    "description": "Agricultural weed and crop classification dataset",
    "original_url": "https://github.com/AlexOlsen/DeepWeeds",
    "citation": "Olsen et al. (2019). DeepWeeds: A Multiclass Weed Species Identification Dataset Using Deep Learning.",
    "access_date": datetime.now(timezone.utc).isoformat()
}

# Dataset version
DATASET_VERSION = "dataset-real-v1"




def load_schema() -> dict:
    """Load the Dataset V2 metadata schema."""
    with SCHEMA_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


def validate_record(record: dict, schema: dict) -> list[str]:
    """Validate a manifest record against the schema."""
    errors = []
    
    # Check required fields
    required_fields = [field for field, spec in schema["fields"].items() if spec.get("required", False)]
    for field in required_fields:
        if field not in record:
            errors.append(f"Missing required field: {field}")
    
    # Check label encoding
    if record.get("label") not in [0, 1]:
        errors.append(f"Invalid label: {record.get('label')}")
    
    # Check category
    allowed_categories = schema["fields"]["category"]["allowed_values"]
    if record.get("category") not in allowed_categories:
        errors.append(f"Invalid category: {record.get('category')}")
    
    # Check format
    allowed_formats = schema["fields"]["format"]["allowed_values"]
    if record.get("format") not in allowed_formats:
        errors.append(f"Invalid format: {record.get('format')}")
    
    # Check color mode
    allowed_modes = schema["fields"]["color_mode"]["allowed_values"]
    if record.get("color_mode") not in allowed_modes:
        errors.append(f"Invalid color mode: {record.get('color_mode')}")
    
    # Check generation method
    allowed_methods = schema["fields"]["generation_method"]["allowed_values"]
    if record.get("generation_method") not in allowed_methods:
        errors.append(f"Invalid generation method: {record.get('generation_method')}")
    
    return errors


def get_exif_metadata(image_path: Path) -> dict[str, Any]:
    """Extract EXIF metadata from an image."""
    try:
        with Image.open(image_path) as img:
            exif_data = img._getexif()
            if exif_data:
                return {TAGS.get(tag, tag): value for tag, value in exif_data.items()}
            return {}
    except Exception:
        return {}


def compute_sha256(image_path: Path) -> str:
    """Compute SHA-256 hash of an image file."""
    sha256_hash = hashlib.sha256()
    with image_path.open("rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            sha256_hash.update(chunk)
    return sha256_hash.hexdigest()


def generate_source_id(filename: str) -> str:
    """Generate a stable source ID from filename using SHA-256."""
    # Use SHA-256 for strong collision resistance
    hash_val = hashlib.sha256(filename.encode()).hexdigest()[:16]
    return f"SRC_DW_{hash_val.upper()}"


def generate_image_id(source_id: str) -> str:
    """Generate a stable image ID from source ID.
    
    Since DeepWeeds has one image per source, image_id = source_id.
    This ensures stability across different selection orders and limits.
    """
    return source_id


def process_image(
    image_path: Path,
    source_id: str,
    image_id: str,
    schema: dict
) -> dict[str, Any] | None:
    """Process a single DeepWeeds image and create a manifest record."""
    try:
        with Image.open(image_path) as img:
            # Get image properties
            width, height = img.size
            format_name = img.format
            if format_name == "JPEG":
                format_name = "JPEG"
            elif format_name == "PNG":
                format_name = "PNG"
            else:
                format_name = "JPEG"  # Default for DeepWeeds
            
            color_mode = img.mode
            if color_mode == "RGB":
                color_mode = "RGB"
            elif color_mode == "RGBA":
                color_mode = "RGBA"
            elif color_mode == "L":
                color_mode = "L"
            elif color_mode == "LA":
                color_mode = "LA"
            else:
                color_mode = "RGB"  # Default for DeepWeeds
            
            # Check EXIF availability
            exif_data = get_exif_metadata(image_path)
            metadata_available = len(exif_data) > 0
            
            # Compute SHA256
            sha256_hash = compute_sha256(image_path)
            
            # Create manifest record
            record = {
                "image_id": image_id,
                "source_id": source_id,
                "label": 0,  # All DeepWeeds images are genuine originals
                "category": "original",
                "width": width,
                "height": height,
                "format": format_name,
                "color_mode": color_mode,
                "generation_method": "real_camera",
                "processing_operations": [],
                "metadata_available": metadata_available,
                "dataset_version": DATASET_VERSION,
                "sha256": sha256_hash,
                "provenance": DEEPWEEDS_PROVENANCE
            }
            
            # Validate record
            errors = validate_record(record, schema)
            if errors:
                print(f"  Validation errors for {image_path.name}: {errors}")
                return None
            
            return record
    
    except Exception as e:
        print(f"  Error processing {image_path.name}: {e}")
        return None


def load_existing_manifest() -> tuple[set[str], list[dict[str, Any]]]:
    """Load existing manifest to avoid duplicates and return all records.
    
    Returns:
        Tuple of (existing_image_ids set, all_records list)
    """
    existing_image_ids = set()
    all_records = []
    
    if not MANIFEST_PATH.exists():
        return existing_image_ids, all_records
    
    with MANIFEST_PATH.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
                all_records.append(record)
                if "image_id" in record:
                    existing_image_ids.add(record["image_id"])
            except json.JSONDecodeError:
                continue
    
    return existing_image_ids, all_records


def is_deepweeds_record(record: dict[str, Any]) -> bool:
    """Check if a manifest record belongs to DeepWeeds import.
    
    Uses provenance information to identify DeepWeeds records.
    """
    provenance = record.get("provenance", {})
    source = provenance.get("source", "")
    return "DeepWeeds" in source or "deepweeds" in source.lower()


def write_manifest_atomic(records: list[dict[str, Any]], manifest_path: Path) -> None:
    """Write manifest records atomically using temporary file.
    
    Args:
        records: List of manifest records to write
        manifest_path: Path to the manifest file
    """
    # Write to temporary file
    temp_path = manifest_path.with_suffix(".jsonl.tmp")
    try:
        with temp_path.open("w", encoding="utf-8") as f:
            for record in records:
                f.write(json.dumps(record) + "\n")
        
        # Atomic replace
        temp_path.replace(manifest_path)
    except Exception:
        # Clean up temp file on error
        if temp_path.exists():
            temp_path.unlink()
        raise


def write_manifest_records_atomic(existing_records: list[dict[str, Any]], 
                                   new_records: list[dict[str, Any]], 
                                   manifest_path: Path) -> None:
    """Write manifest records atomically, combining existing and new records.
    
    Args:
        existing_records: List of existing manifest records
        new_records: List of new records to append
        manifest_path: Path to the manifest file
    """
    combined_records = existing_records + new_records
    write_manifest_atomic(combined_records, manifest_path)


def main():
    parser = argparse.ArgumentParser(description="Import DeepWeeds images into Dataset V2")
    parser.add_argument("--limit", type=int, default=None, help="Maximum number of images to import")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for deterministic selection")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be imported without writing")
    parser.add_argument("--force", action="store_true", help="Force rebuild of DeepWeeds portion (clears existing)")
    
    args = parser.parse_args()
    
    # Validate paths
    if not DEEPWEEDS_SOURCE.exists():
        print(f"Error: DeepWeeds source directory not found: {DEEPWEEDS_SOURCE}")
        return
    
    if not SCHEMA_PATH.exists():
        print(f"Error: Schema file not found: {SCHEMA_PATH}")
        return
    
    # Load schema
    print("Loading schema...")
    schema = load_schema()
    print(f"Schema version: {schema['version']}")
    
    # Discover images
    print(f"\nDiscovering images in {DEEPWEEDS_SOURCE}...")
    image_files = sorted(DEEPWEEDS_SOURCE.glob("*.jpg"))
    print(f"Discovered: {len(image_files)} images")
    
    if len(image_files) == 0:
        print("No images found to import.")
        return
    
    # Check for duplicate filenames
    filename_counts = {}
    for img_path in image_files:
        filename_counts[img_path.name] = filename_counts.get(img_path.name, 0) + 1
    
    duplicates = {name: count for name, count in filename_counts.items() if count > 1}
    if duplicates:
        print("ERROR: Duplicate filenames found:")
        for name, count in duplicates.items():
            print(f"  {name}: {count} occurrences")
        print("Duplicate filenames prevent stable source ID generation.")
        print("Please resolve filename conflicts before importing.")
        return
    
    # Check for source_id collisions
    source_ids = {}
    collisions = []
    for img_path in image_files:
        source_id = generate_source_id(img_path.name)
        if source_id in source_ids:
            collisions.append((source_id, img_path.name, source_ids[source_id]))
        else:
            source_ids[source_id] = img_path.name
    
    if collisions:
        print("ERROR: Source ID collisions detected:")
        for source_id, name1, name2 in collisions:
            print(f"  {source_id}: {name1} collides with {name2}")
        print("This indicates a hash collision or insufficient entropy.")
        print("Please review the source ID generation logic.")
        return
    
    # Apply limit
    if args.limit:
        if args.limit > len(image_files):
            print(f"Warning: Limit {args.limit} exceeds available images {len(image_files)}")
            args.limit = len(image_files)
        
        # Deterministic selection using seed
        random.seed(args.seed)
        image_files = random.sample(image_files, args.limit)
        print(f"Selected: {len(image_files)} images (limit: {args.limit}, seed: {args.seed})")
    else:
        print("No limit specified, would import all images")
        print("Use --limit to specify a subset")
        return
    
    # Handle existing manifest
    if args.force:
        print("\nForce mode: removing existing DeepWeeds records...")
        existing_image_ids, all_records = load_existing_manifest()
        
        # Filter out DeepWeeds records, preserve others
        non_deepweeds_records = [r for r in all_records if not is_deepweeds_record(r)]
        deepweeds_count = len(all_records) - len(non_deepweeds_records)
        
        print(f"Existing total records: {len(all_records)}")
        print(f"DeepWeeds records to remove: {deepweeds_count}")
        print(f"Non-DeepWeeds records to preserve: {len(non_deepweeds_records)}")
        
        # Write preserved records back
        write_manifest_atomic(non_deepweeds_records, MANIFEST_PATH)
        
        # Clear existing IDs for fresh import
        existing_image_ids = set(r["image_id"] for r in non_deepweeds_records)
    else:
        print("\nLoading existing manifest to avoid duplicates...")
        existing_image_ids, all_records = load_existing_manifest()
        print(f"Existing records: {len(existing_image_ids)}")
    
    # Process images
    print("\nProcessing images...")
    imported = 0
    skipped = 0
    corrupted = 0
    exif_available = 0
    exif_unavailable = 0
    new_records = []
    
    for idx, image_path in enumerate(image_files, 1):
        print(f"[{idx}/{len(image_files)}] Processing {image_path.name}...")
        
        # Generate IDs (now stable across reruns)
        source_id = generate_source_id(image_path.name)
        image_id = generate_image_id(source_id)
        
        # Check for duplicates
        if image_id in existing_image_ids and not args.force:
            print(f"  Skipped (already exists)")
            skipped += 1
            continue
        
        # Process image
        record = process_image(image_path, source_id, image_id, schema)
        
        if record is None:
            corrupted += 1
            continue
        
        if record["metadata_available"]:
            exif_available += 1
        else:
            exif_unavailable += 1
        
        new_records.append(record)
        imported += 1
        print(f"  Imported as {image_id} (source: {source_id})")
    
    # Write records atomically
    if not args.dry_run and new_records:
        print(f"\nWriting {len(new_records)} new records atomically...")
        _, existing_records = load_existing_manifest()
        write_manifest_records_atomic(existing_records, new_records, MANIFEST_PATH)
    
    # Print summary
    print("\n" + "="*60)
    print("DeepWeeds Import Complete")
    print("="*60)
    print(f"Discovered: {len(image_files) if args.limit else len(DEEPWEEDS_SOURCE.glob('*.jpg'))}")
    print(f"Selected: {len(image_files)}")
    print(f"Imported: {imported}")
    print(f"Skipped: {skipped}")
    print(f"Corrupted: {corrupted}")
    print()
    print(f"EXIF available: {exif_available}")
    print(f"EXIF unavailable: {exif_unavailable}")
    print()
    print(f"Manifest records added: {imported}")
    print(f"Manifest path: {MANIFEST_PATH}")
    
    if args.dry_run:
        print("\nDRY RUN - No changes made")
    else:
        print("\nManifest updated successfully")


if __name__ == "__main__":
    main()

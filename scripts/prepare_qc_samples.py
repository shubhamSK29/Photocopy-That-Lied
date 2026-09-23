"""Prepare manual QC samples for visual inspection."""

import json
from pathlib import Path
import random
from PIL import Image
import numpy as np
import hashlib

ROOT = Path(__file__).resolve().parent.parent
MANIFEST_FILE = ROOT / "dataset_v2" / "metadata" / "manifest.jsonl"
DATASET_V2 = ROOT / "dataset_v2"

# Load manifest
records = []
with MANIFEST_FILE.open() as f:
    for line in f:
        if line.strip():
            records.append(json.loads(line))

print(f"Loaded {len(records)} records from manifest")

# Create mapping from source_id to original file path (using SHA256)
print("Building source_id to filename mapping...")
source_id_to_path = {}
source_dir = DATASET_V2 / "sources" / "deepweeds_raw" / "images"

# Build SHA256 lookup for original images
sha256_to_path = {}
if source_dir.exists():
    for image_file in source_dir.glob("*.jpg"):
        try:
            file_sha256 = hashlib.sha256(image_file.read_bytes()).hexdigest()
            sha256_to_path[file_sha256] = image_file
        except Exception as e:
            print(f"[WARNING] Could not hash {image_file}: {e}")
    print(f"Hashed {len(sha256_to_path)} source images")
else:
    print(f"[WARNING] Source directory not found: {source_dir}")

# Map source_id to path using SHA256 from manifest
for record in records:
    if record["category"] == "original":
        source_id = record["source_id"]
        sha256_hash = record.get("sha256", "")
        if sha256_hash and sha256_hash in sha256_to_path:
            source_id_to_path[source_id] = sha256_to_path[sha256_hash]

print(f"Mapped {len(source_id_to_path)} source IDs to file paths")

# Group by category and manipulation type
by_category = {
    "original": [],
    "natural_processing": [],
    "hard_negative": [],
    "manipulated": {
        "copy_move": [],
        "object_removal": [],
        "object_insertion": [],
        "splicing": []
    }
}

for record in records:
    category = record["category"]
    if category == "manipulated":
        manip_type = record.get("manipulation_type")
        if manip_type in by_category["manipulated"]:
            by_category["manipulated"][manip_type].append(record)
    else:
        by_category[category].append(record)

# Select samples
random.seed(42)  # For reproducibility

samples_per_category = 5

qc_samples = {
    "original": random.sample(by_category["original"], min(samples_per_category, len(by_category["original"]))),
    "natural_processing": random.sample(by_category["natural_processing"], min(samples_per_category, len(by_category["natural_processing"]))),
    "hard_negative": random.sample(by_category["hard_negative"], min(samples_per_category, len(by_category["hard_negative"]))),
    "manipulated": {}
}

for manip_type, records in by_category["manipulated"].items():
    qc_samples["manipulated"][manip_type] = random.sample(records, min(samples_per_category, len(records)))

print("\n=== MANUAL QC SAMPLES ===")
print("=" * 80)

# Function to display image info
def show_image_info(record, image_path):
    print(f"\nImage ID: {record['image_id']}")
    print(f"Source ID: {record['source_id']}")
    print(f"Category: {record['category']}")
    print(f"Label: {record['label']}")
    print(f"Path: {image_path}")
    
    if image_path and Path(image_path).exists():
        img = Image.open(Path(image_path))
        print(f"Dimensions: {img.size}")
        print(f"Format: {img.format}")
        print(f"Mode: {img.mode}")
    else:
        print(f"[WARNING] Image file not found")

# Display originals
print("\n### ORIGINAL IMAGES (5 samples) ###")
for i, record in enumerate(qc_samples["original"], 1):
    source_id = record["source_id"]
    image_path = source_id_to_path.get(source_id)
    print(f"\n--- Original {i} ---")
    show_image_info(record, str(image_path) if image_path else "NOT FOUND")

# Display natural-processing
print("\n### NATURAL-PROCESSING IMAGES (5 samples) ###")
for i, record in enumerate(qc_samples["natural_processing"], 1):
    image_path_str = record.get("image_path", "")
    # Paths in manifest are relative to project root, not DATASET_V2
    if image_path_str.startswith("dataset_v2/"):
        image_path = ROOT / image_path_str
    else:
        image_path = DATASET_V2 / image_path_str
    print(f"\n--- Natural-Processing {i} ---")
    show_image_info(record, str(image_path))
    print(f"Processing operations: {record.get('processing_operations', [])}")

# Display hard-negatives
print("\n### HARD-NEGATIVE IMAGES (5 samples) ###")
for i, record in enumerate(qc_samples["hard_negative"], 1):
    image_path_str = record.get("image_path", "")
    # Paths in manifest are relative to project root, not DATASET_V2
    if image_path_str.startswith("dataset_v2/"):
        image_path = ROOT / image_path_str
    else:
        image_path = DATASET_V2 / image_path_str
    print(f"\n--- Hard-Negative {i} ---")
    show_image_info(record, str(image_path))
    print(f"Processing operations: {record.get('processing_operations', [])}")

# Display manipulated samples
print("\n### MANIPULATED IMAGES ###")

for manip_type, samples in qc_samples["manipulated"].items():
    print(f"\n--- {manip_type.upper()} (5 samples) ---")
    for i, record in enumerate(samples, 1):
        print(f"\n{manip_type} {i}:")
        
        # Original image
        source_id = record["source_id"]
        original_path = source_id_to_path.get(source_id)
        print(f"Original: {original_path}")
        if original_path and original_path.exists():
            img = Image.open(original_path)
            print(f"  Dimensions: {img.size}")
        else:
            print(f"  [WARNING] Original image not found")
        
        # Manipulated image
        manipulated_path_str = record.get("image_path", "")
        # Paths in manifest are relative to project root
        if manipulated_path_str.startswith("dataset_v2/"):
            manipulated_path = ROOT / manipulated_path_str
        else:
            manipulated_path = DATASET_V2 / manipulated_path_str
        print(f"Manipulated: {manipulated_path}")
        if manipulated_path.exists():
            img = Image.open(manipulated_path)
            print(f"  Dimensions: {img.size}")
        else:
            print(f"  [WARNING] Manipulated image not found")
        
        # Mask
        mask_path_str = record.get("mask_path", "")
        # Paths in manifest are relative to project root
        if mask_path_str.startswith("dataset_v2/"):
            mask_path = ROOT / mask_path_str
        else:
            mask_path = DATASET_V2 / mask_path_str
        print(f"Mask: {mask_path}")
        if mask_path.exists():
            mask = Image.open(mask_path)
            print(f"  Dimensions: {mask.size}")
            mask_array = np.array(mask)
            print(f"  Non-zero pixels: {np.count_nonzero(mask_array)}")
        else:
            print(f"  [WARNING] Mask not found")
        
        # Metadata
        print(f"Image ID: {record['image_id']}")
        print(f"Manipulation type: {record.get('manipulation_type')}")
        print(f"Manipulation area ratio: {record.get('parameters', {}).get('manipulation_area_ratio')}")
        print(f"Parameters: {record.get('parameters', {})}")

# Save sample list for easy access
output_file = ROOT / "docs" / "QC_SAMPLE_PATHS.txt"
with output_file.open("w") as f:
    f.write("MANUAL QC SAMPLE LIST\n")
    f.write("=" * 80 + "\n\n")
    
    f.write("ORIGINAL IMAGES:\n")
    for record in qc_samples["original"]:
        source_id = record["source_id"]
        path = source_id_to_path.get(source_id, "NOT FOUND")
        f.write(f"  {record['image_id']}: {path}\n")
    
    f.write("\nNATURAL-PROCESSING IMAGES:\n")
    for record in qc_samples["natural_processing"]:
        path_str = record.get("image_path", "")
        # Paths in manifest are relative to project root
        if path_str.startswith("dataset_v2/"):
            path = ROOT / path_str
        else:
            path = DATASET_V2 / path_str
        f.write(f"  {record['image_id']}: {path}\n")
    
    f.write("\nHARD-NEGATIVE IMAGES:\n")
    for record in qc_samples["hard_negative"]:
        path_str = record.get("image_path", "")
        # Paths in manifest are relative to project root
        if path_str.startswith("dataset_v2/"):
            path = ROOT / path_str
        else:
            path = DATASET_V2 / path_str
        f.write(f"  {record['image_id']}: {path}\n")
    
    f.write("\nMANIPULATED IMAGES:\n")
    for manip_type, samples in qc_samples["manipulated"].items():
        f.write(f"\n{manip_type.upper()}:\n")
        for record in samples:
            source_id = record["source_id"]
            original_path = source_id_to_path.get(source_id, "NOT FOUND")
            manipulated_path_str = record.get("image_path", "")
            # Paths in manifest are relative to project root
            if manipulated_path_str.startswith("dataset_v2/"):
                manipulated_path = ROOT / manipulated_path_str
            else:
                manipulated_path = DATASET_V2 / manipulated_path_str
            mask_path_str = record.get("mask_path", "")
            # Paths in manifest are relative to project root
            if mask_path_str.startswith("dataset_v2/"):
                mask_path = ROOT / mask_path_str
            else:
                mask_path = DATASET_V2 / mask_path_str
            f.write(f"  {record['image_id']}:\n")
            f.write(f"    Original: {original_path}\n")
            f.write(f"    Manipulated: {manipulated_path}\n")
            f.write(f"    Mask: {mask_path}\n")
            f.write(f"    Area ratio: {record.get('parameters', {}).get('manipulation_area_ratio')}\n")

print(f"\nSample list saved to: {output_file}")
print("\n=== END OF QC SAMPLE PREPARATION ===")

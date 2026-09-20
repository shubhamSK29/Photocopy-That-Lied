"""Remove duplicate hard-negative records from manifest and files."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATASET_V2 = ROOT / "dataset_v2"
METADATA_DIR = DATASET_V2 / "metadata"
MANIFEST_FILE = METADATA_DIR / "manifest.jsonl"
VARIANTS_DIR = DATASET_V2 / "variants"
HN_DIR = VARIANTS_DIR / "hard_negative"

# Duplicate hard-negative records to remove (from investigation)
# These are the hard-negative records that had identical resize(0.5) to natural processing
duplicate_hn_ids = [
    "SRC_DW_00A22693F8CDC9EF_HN_RESIZE_7e27dc49925eeb77",
    "SRC_DW_00D4416E355B20D7_HN_RESIZE_fe220eacace0a2ed", 
    "SRC_DW_0138F4EB08B55EB8_HN_RESIZE_fbcdc7123ec29e22",
    "SRC_DW_034C5182F470F1B3_HN_RESIZE_2c8d086ea5be30d2"
]

def remove_duplicates():
    """Remove duplicate records from manifest and files."""
    print("Removing duplicate hard-negative records...")
    
    # Load manifest
    records = []
    with MANIFEST_FILE.open() as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))
    
    print(f"Loaded {len(records)} records from manifest")
    
    # Filter out duplicates
    filtered_records = [r for r in records if r.get('image_id') not in duplicate_hn_ids]
    removed_count = len(records) - len(filtered_records)
    
    print(f"Removed {removed_count} duplicate records")
    
    # Write back to manifest
    with MANIFEST_FILE.open('w') as f:
        for record in filtered_records:
            f.write(json.dumps(record) + '\n')
    
    print(f"Wrote {len(filtered_records)} records back to manifest")
    
    # Remove duplicate files
    for hn_id in duplicate_hn_ids:
        file_path = HN_DIR / f"{hn_id}.jpg"
        if file_path.exists():
            file_path.unlink()
            print(f"Removed file: {file_path}")
        else:
            print(f"File not found: {file_path}")
    
    print("Duplicate removal complete")

if __name__ == "__main__":
    remove_duplicates()

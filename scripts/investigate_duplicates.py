"""Investigate duplicate hashes in Dataset V2 manifest."""

import json
import hashlib
from pathlib import Path
from typing import Dict, List, Any, Tuple

ROOT = Path(__file__).resolve().parent.parent
DATASET_V2 = ROOT / "dataset_v2"
METADATA_DIR = DATASET_V2 / "metadata"
MANIFEST_FILE = METADATA_DIR / "manifest.jsonl"


def load_manifest() -> List[Dict[str, Any]]:
    """Load the metadata manifest from JSONL format."""
    rows = []
    with MANIFEST_FILE.open() as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            try:
                row = json.loads(line)
                rows.append(row)
            except json.JSONDecodeError as e:
                print(f"Invalid JSON: {e}")
    return rows


def compute_sha256(file_path: Path) -> str:
    """Compute SHA-256 hash of a file."""
    sha256_hash = hashlib.sha256()
    with file_path.open("rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            sha256_hash.update(chunk)
    return sha256_hash.hexdigest()


def find_duplicate_hashes(rows: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """Find records with duplicate SHA-256 hashes."""
    # Build SHA-256 to filename mapping for source directory lookup
    SOURCES_DIR = DATASET_V2 / "sources"
    sha256_to_file = {}
    if SOURCES_DIR.exists():
        for source_dir in SOURCES_DIR.rglob("images"):
            if source_dir.is_dir():
                for img_path in source_dir.glob("*.jpg"):
                    try:
                        sha256_hash = compute_sha256(img_path)
                        sha256_to_file[sha256_hash] = img_path
                    except Exception:
                        pass

    # Compute SHA-256 for each record
    sha256_to_records: Dict[str, List[Dict[str, Any]]] = {}
    
    for row in rows:
        image_path = None
        
        # First try to use explicit image_path if present
        if row.get("image_path"):
            image_path = ROOT / row["image_path"]
        # Otherwise, locate by SHA-256 in source directories
        elif row.get("sha256") and row["sha256"] in sha256_to_file:
            image_path = sha256_to_file[row["sha256"]]
        else:
            continue
        
        if not image_path.exists():
            continue
        
        sha256 = compute_sha256(image_path)
        
        if sha256 not in sha256_to_records:
            sha256_to_records[sha256] = []
        sha256_to_records[sha256].append(row)
    
    # Filter to only duplicates
    duplicates = {k: v for k, v in sha256_to_records.items() if len(v) > 1}
    
    return duplicates


def analyze_duplicate_group(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Analyze a group of duplicate records."""
    analysis = {
        "count": len(records),
        "records": [],
        "classification": "unknown"
    }
    
    for record in records:
        record_info = {
            "image_id": record.get("image_id"),
            "source_id": record.get("source_id"),
            "variant_id": record.get("variant_id"),
            "category": record.get("category"),
            "label": record.get("label"),
            "generation_method": record.get("generation_method"),
            "processing_operations": record.get("processing_operations", []),
            "manipulation_type": record.get("manipulation_type"),
            "parameters": record.get("parameters", {}),
            "image_path": record.get("image_path")
        }
        analysis["records"].append(record_info)
    
    # Classify the duplicate
    categories = {r["category"] for r in analysis["records"]}
    operations = [r["processing_operations"] for r in analysis["records"]]
    parameters = [r["parameters"] for r in analysis["records"]]
    
    # Check if all operations and parameters are identical
    all_ops_same = len(set(str(op) for op in operations)) == 1
    all_params_same = len(set(str(p) for p in parameters)) == 1
    
    if all_ops_same and all_params_same:
        # Deterministic duplicate - same generation with same parameters
        analysis["classification"] = "A. intentional deterministic duplicate"
    elif len(categories) == 1 and categories.pop() == "original":
        # Originals with same hash (shouldn't happen in DeepWeeds)
        analysis["classification"] = "C. bug in generation logic"
    else:
        # Different operations but same output
        analysis["classification"] = "B. redundant variant or D. legitimate collision"
    
    return analysis


def main():
    """Main investigation function."""
    print("=== Duplicate Hash Investigation ===\n")
    
    # Load manifest
    rows = load_manifest()
    print(f"Loaded {len(rows)} records from manifest\n")
    
    # Find duplicates
    duplicates = find_duplicate_hashes(rows)
    print(f"Found {len(duplicates)} duplicate hash groups\n")
    
    # Analyze each group
    for i, (sha256, records) in enumerate(duplicates.items(), 1):
        print(f"--- Duplicate Group {i} ---")
        print(f"SHA-256: {sha256}")
        print(f"Count: {len(records)}")
        
        analysis = analyze_duplicate_group(records)
        print(f"Classification: {analysis['classification']}\n")
        
        for j, record_info in enumerate(analysis["records"], 1):
            print(f"  Record {j}:")
            print(f"    image_id: {record_info['image_id']}")
            print(f"    source_id: {record_info['source_id']}")
            print(f"    variant_id: {record_info['variant_id']}")
            print(f"    category: {record_info['category']}")
            print(f"    label: {record_info['label']}")
            print(f"    operations: {record_info['processing_operations']}")
            print(f"    parameters: {record_info['parameters']}")
            print(f"    path: {record_info['image_path']}")
            print()
        
        print()
    
    # Summary
    print("=== Summary ===")
    print(f"Total duplicate groups: {len(duplicates)}")
    print(f"Total duplicate records: {sum(len(r) for r in duplicates.values())}")


if __name__ == "__main__":
    main()

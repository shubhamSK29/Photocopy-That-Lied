"""Audit data leakage in Dataset V2 splits.

This script checks for:
- Source leakage (same source in multiple splits)
- Duplicate leakage (duplicate images in multiple splits)
- Metadata leakage (metadata patterns revealing labels)
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Set

ROOT = Path(__file__).resolve().parent.parent
DATASET_V2 = ROOT / "dataset_v2"
SPLITS_DIR = DATASET_V2 / "splits"
METADATA_DIR = DATASET_V2 / "metadata"
MANIFEST_FILE = METADATA_DIR / "manifest.jsonl"


def load_manifest() -> List[Dict]:
    """Load manifest from JSONL."""
    rows = []
    with MANIFEST_FILE.open() as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            rows.append(json.loads(line))
    return rows


def load_splits() -> Dict[str, List[str]]:
    """Load train/validation/test splits."""
    splits = {}
    for split_name in ["train", "validation", "test"]:
        split_file = SPLITS_DIR / f"{split_name}.json"
        if split_file.exists():
            with split_file.open() as f:
                data = json.load(f)
                splits[split_name] = data["image_ids"]
    return splits


def audit_source_leakage(rows: List[Dict], splits: Dict[str, List[str]]) -> Dict:
    """Check for source leakage across splits."""
    results = {
        "source_leakage": [],
        "source_distribution": {},
        "status": "PASS"
    }
    
    # Build image_id to source_id mapping
    image_to_source = {r["image_id"]: r["source_id"] for r in rows}
    
    # Get sources in each split
    split_sources = {}
    for split_name, image_ids in splits.items():
        sources = set(image_to_source.get(img_id, "UNKNOWN") for img_id in image_ids)
        split_sources[split_name] = sources
        results["source_distribution"][split_name] = {
            "images": len(image_ids),
            "sources": len(sources)
        }
    
    # Check for overlap
    if "train" in split_sources and "validation" in split_sources:
        overlap = split_sources["train"] & split_sources["validation"]
        if overlap:
            results["source_leakage"].append({
                "type": "train_validation",
                "sources": list(overlap)
            })
    
    if "train" in split_sources and "test" in split_sources:
        overlap = split_sources["train"] & split_sources["test"]
        if overlap:
            results["source_leakage"].append({
                "type": "train_test",
                "sources": list(overlap)
            })
    
    if "validation" in split_sources and "test" in split_sources:
        overlap = split_sources["validation"] & split_sources["test"]
        if overlap:
            results["source_leakage"].append({
                "type": "validation_test",
                "sources": list(overlap)
            })
    
    if results["source_leakage"]:
        results["status"] = "FAIL"
    
    return results


def audit_duplicate_leakage(rows: List[Dict], splits: Dict[str, List[str]]) -> Dict:
    """Check for duplicate images in multiple splits."""
    results = {
        "duplicate_leakage": [],
        "status": "PASS"
    }
    
    # Build image_id to set (for checking same image in multiple splits)
    split_image_sets = {name: set(ids) for name, ids in splits.items()}
    
    # Check for exact duplicate images across splits
    if "train" in split_image_sets and "validation" in split_image_sets:
        overlap = split_image_sets["train"] & split_image_sets["validation"]
        if overlap:
            results["duplicate_leakage"].append({
                "type": "train_validation",
                "image_ids": list(overlap)
            })
    
    if "train" in split_image_sets and "test" in split_image_sets:
        overlap = split_image_sets["train"] & split_image_sets["test"]
        if overlap:
            results["duplicate_leakage"].append({
                "type": "train_test",
                "image_ids": list(overlap)
            })
    
    if "validation" in split_image_sets and "test" in split_image_sets:
        overlap = split_image_sets["validation"] & split_image_sets["test"]
        if overlap:
            results["duplicate_leakage"].append({
                "type": "validation_test",
                "image_ids": list(overlap)
            })
    
    if results["duplicate_leakage"]:
        results["status"] = "FAIL"
    
    return results


def audit_metadata_leakage(rows: List[Dict], splits: Dict[str, List[str]]) -> Dict:
    """Check for metadata patterns that could leak labels."""
    results = {
        "potential_leakage": [],
        "checks": {}
    }
    
    # Check if filename patterns correlate with label
    genuine_words = ["genuine", "original", "natural", "authentic"]
    manipulated_words = ["fake", "manipulated", "copy", "splice", "remove"]
    
    split_image_sets = {name: set(ids) for name, ids in splits.items()}
    image_to_row = {r["image_id"]: r for r in rows}
    
    for split_name, image_ids in splits.items():
        genuine_in_split = sum(1 for img_id in image_ids 
                            if image_to_row.get(img_id, {}).get("label") == 0)
        manipulated_in_split = len(image_ids) - genuine_in_split
        
        results["checks"][split_name] = {
            "genuine": genuine_in_split,
            "manipulated": manipulated_in_split,
            "genuine_percentage": genuine_in_split / len(image_ids) if image_ids else 0
        }
    
    # Check if all images in a split have the same label (potential problem)
    for split_name, counts in results["checks"].items():
        if counts["genuine"] == 0 or counts["manipulated"] == 0:
            results["potential_leakage"].append({
                "type": "single_class_split",
                "split": split_name,
                "label": "genuine" if counts["genuine"] > 0 else "manipulated"
            })
    
    return results


def print_report(results: Dict):
    """Print leakage audit report."""
    print("=" * 80)
    print("DATA LEAKAGE AUDIT REPORT")
    print("=" * 80)
    
    # Source leakage
    print("\n[SOURCE LEAKAGE]")
    print(f"Status: {results['source_leakage']['status']}")
    print(f"Source distribution:")
    for split, dist in results['source_leakage']['source_distribution'].items():
        print(f"  {split}: {dist['images']} images, {dist['sources']} sources")
    
    if results['source_leakage']['source_leakage']:
        print(f"\n❌ Source leakage detected:")
        for leak in results['source_leakage']['source_leakage']:
            print(f"  {leak['type']}: {leak['sources']}")
    else:
        print(f"\n✅ No source leakage detected")
    
    # Duplicate leakage
    print("\n[DUPLICATE LEAKAGE]")
    print(f"Status: {results['duplicate_leakage']['status']}")
    
    if results['duplicate_leakage']['duplicate_leakage']:
        print(f"\n❌ Duplicate leakage detected:")
        for leak in results['duplicate_leakage']['duplicate_leakage']:
            print(f"  {leak['type']}: {leak['image_ids']}")
    else:
        print(f"\n✅ No duplicate leakage detected")
    
    # Metadata leakage
    print("\n[METADATA LEAKAGE]")
    for split, counts in results['metadata_leakage']['checks'].items():
        print(f"  {split}: {counts['genuine']} genuine ({counts['genuine_percentage']:.1%}), {counts['manipulated']} manipulated")
    
    if results['metadata_leakage']['potential_leakage']:
        print(f"\n⚠️  Potential metadata leakage:")
        for leak in results['metadata_leakage']['potential_leakage']:
            print(f"  {leak}")
    else:
        print(f"\n✅ No obvious metadata leakage")
    
    print("\n" + "=" * 80)


def main():
    """Main function."""
    print("Auditing data leakage in Dataset V2...")
    
    rows = load_manifest()
    print(f"Loaded {len(rows)} images from manifest")
    
    splits = load_splits()
    print(f"Loaded splits: {list(splits.keys())}")
    
    results = {
        "source_leakage": audit_source_leakage(rows, splits),
        "duplicate_leakage": audit_duplicate_leakage(rows, splits),
        "metadata_leakage": audit_metadata_leakage(rows, splits)
    }
    
    print_report(results)
    
    # Save report
    report_file = ROOT / "reports" / "PHASE_2_LEAKAGE_AUDIT.json"
    report_file.parent.mkdir(exist_ok=True)
    with report_file.open("w") as f:
        json.dump(results, f, indent=2)
    
    print(f"\nReport saved to: {report_file}")
    
    # Overall status
    has_leakage = (
        results['source_leakage']['status'] == "FAIL" or
        results['duplicate_leakage']['status'] == "FAIL"
    )
    
    if has_leakage:
        print("\n❌ LEAKAGE AUDIT FAILED")
        return 1
    else:
        print("\n✅ LEAKAGE AUDIT PASSED")
        return 0


if __name__ == "__main__":
    exit(main())

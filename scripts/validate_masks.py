"""Validate ground-truth masks for Dataset V2."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
DATASET_V2 = ROOT / "dataset_v2"
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


def validate_mask(mask_path: Path, expected_size: tuple) -> Dict:
    """Validate a single mask file."""
    result = {
        "exists": mask_path.exists(),
        "readable": False,
        "dimensions_match": False,
        "valid_values": False,
        "not_empty": False,
        "errors": []
    }
    
    if not result["exists"]:
        result["errors"].append("Mask file does not exist")
        return result
    
    try:
        mask = Image.open(mask_path)
        result["readable"] = True
        
        # Check dimensions
        if mask.size == expected_size:
            result["dimensions_match"] = True
        else:
            result["errors"].append(f"Dimension mismatch: expected {expected_size}, got {mask.size}")
        
        # Check values
        mask_array = np.array(mask)
        unique_values = set(mask_array.flatten())
        
        # Valid values are 0 and 1 (or close to them for anti-aliasing)
        valid_values = {0, 1}
        if all(v in valid_values or abs(v - round(v)) < 0.1 for v in unique_values):
            result["valid_values"] = True
        else:
            result["errors"].append(f"Invalid mask values: {unique_values}")
        
        # Check not empty
        if np.sum(mask_array) > 0:
            result["not_empty"] = True
        else:
            result["errors"].append("Mask is empty (all zeros)")
        
    except Exception as e:
        result["errors"].append(f"Error reading mask: {e}")
    
    return result


def validate_all_masks(rows: List[Dict]) -> Dict:
    """Validate all masks in the dataset."""
    results = {
        "manipulated_images": 0,
        "masks_validated": 0,
        "masks_missing": [],
        "masks_failed": [],
        "mask_summary": {
            "total": 0,
            "valid": 0,
            "invalid": 0,
            "missing": 0
        }
    }
    
    for row in rows:
        if row.get("label") != 1:
            continue  # Only validate manipulated images
        
        results["manipulated_images"] += 1
        
        mask_path = row.get("mask_path")
        if not mask_path:
            results["masks_missing"].append(row["image_id"])
            results["mask_summary"]["missing"] += 1
            continue
        
        mask_file = DATASET_V2 / mask_path
        image_path = DATASET_V2 / row.get("image_path", "")
        
        try:
            img = Image.open(image_path)
            expected_size = img.size
            
            validation = validate_mask(mask_file, expected_size)
            results["masks_validated"] += 1
            results["mask_summary"]["total"] += 1
            
            if all([validation["readable"], validation["dimensions_match"], 
                   validation["valid_values"], validation["not_empty"]]):
                results["mask_summary"]["valid"] += 1
            else:
                results["masks_failed"].append({
                    "image_id": row["image_id"],
                    "mask_path": mask_path,
                    "errors": validation["errors"]
                })
                results["mask_summary"]["invalid"] += 1
                
        except Exception as e:
            results["masks_failed"].append({
                "image_id": row["image_id"],
                "error": str(e)
            })
            results["mask_summary"]["invalid"] += 1
    
    return results


def print_report(results: Dict):
    """Print mask validation report."""
    print("=" * 80)
    print("MASK VALIDATION REPORT")
    print("=" * 80)
    
    print(f"\nManipulated images: {results['manipulated_images']}")
    print(f"Masks validated: {results['masks_validated']}")
    print(f"Masks missing: {len(results['masks_missing'])}")
    print(f"Masks failed validation: {len(results['masks_failed'])}")
    
    summary = results["mask_summary"]
    print(f"\nMask Summary:")
    print(f"  Total: {summary['total']}")
    print(f"  Valid: {summary['valid']}")
    print(f"  Invalid: {summary['invalid']}")
    print(f"  Missing: {summary['missing']}")
    
    if results["masks_missing"]:
        print(f"\nMissing masks (first 10):")
        for img_id in results["masks_missing"][:10]:
            print(f"  - {img_id}")
    
    if results["masks_failed"]:
        print(f"\nFailed masks (first 10):")
        for failure in results["masks_failed"][:10]:
            print(f"  - {failure['image_id']}: {failure.get('errors', failure.get('error'))}")
    
    print("\n" + "=" * 80)


def main():
    """Main function."""
    print("Validating ground-truth masks for Dataset V2...")
    
    rows = load_manifest()
    print(f"Loaded {len(rows)} images from manifest")
    
    results = validate_all_masks(rows)
    
    print_report(results)
    
    # Save report
    report_file = ROOT / "reports" / "PHASE_2_MASK_AUDIT.json"
    report_file.parent.mkdir(exist_ok=True)
    with report_file.open("w") as f:
        json.dump(results, f, indent=2)
    
    print(f"\nReport saved to: {report_file}")
    
    return 0


if __name__ == "__main__":
    exit(main())

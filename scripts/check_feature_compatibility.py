"""Check feature extraction compatibility for Dataset V2.

This script tests whether the existing feature extraction pipeline can process Dataset V2.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
DATASET_V2 = ROOT / "dataset_v2"
METADATA_DIR = DATASET_V2 / "metadata"
MANIFEST_FILE = METADATA_DIR / "manifest.jsonl"

# Add backend to path
import sys
sys.path.insert(0, str(ROOT))

from backend.features.feature_builder import FEATURE_NAMES
from backend.pipeline.analysis import analyze_image
from backend.pipeline.validator import validate_upload


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


def check_feature_compatibility(rows: List[Dict]) -> Dict:
    """Check feature extraction compatibility."""
    results = {
        "total_images": len(rows),
        "processed": 0,
        "failed": 0,
        "failures": [],
        "feature_statistics": {
            "genuine": {},
            "manipulated": {},
            "natural_processing": {},
            "hard_negative": {}
        },
        "all_nan_features": [],
        "all_zero_features": [],
        "infinity_features": [],
        "extreme_outliers": []
    }
    
    if not rows:
        results["status"] = "EMPTY_DATASET"
        return results
    
    # Collect features by category
    features_by_category = {
        "genuine": [],
        "manipulated": [],
        "natural_processing": [],
        "hard_negative": []
    }
    
    for row in rows:
        image_path = DATASET_V2 / row.get("image_path", "")
        if not image_path.exists():
            results["failures"].append({
                "image_id": row.get("image_id"),
                "error": "Image file not found"
            })
            results["failed"] += 1
            continue
        
        try:
            data = image_path.read_bytes()
            validated = validate_upload(data, image_path.name, None)
            record = analyze_image(data, validated, persist=False)
            
            features = np.array([record["features"].get(name, np.nan) for name in FEATURE_NAMES])
            
            category = row.get("category", "unknown")
            label = row.get("label")
            
            # Map to feature statistics category
            if label == 0:
                if category == "natural_processing":
                    stats_category = "natural_processing"
                elif category == "hard_negative":
                    stats_category = "hard_negative"
                else:
                    stats_category = "genuine"
            else:
                stats_category = "manipulated"
            
            features_by_category[stats_category].append(features)
            results["processed"] += 1
            
        except Exception as e:
            results["failures"].append({
                "image_id": row.get("image_id"),
                "error": str(e)
            })
            results["failed"] += 1
    
    # Compute statistics for each category
    for category, feature_list in features_by_category.items():
        if not feature_list:
            continue
        
        feature_array = np.array(feature_list)
        
        results["feature_statistics"][category] = {
            "count": len(feature_list),
            "mean": feature_array.mean(axis=0).tolist(),
            "median": np.median(feature_array, axis=0).tolist(),
            "std": feature_array.std(axis=0).tolist(),
            "min": feature_array.min(axis=0).tolist(),
            "max": feature_array.max(axis=0).tolist(),
            "missing_percentage": (np.isnan(feature_array).sum(axis=0) / len(feature_list)).tolist()
        }
    
    # Check for problematic features
    if results["processed"] > 0:
        all_features = np.vstack([features_by_category[k] for k in features_by_category if features_by_category[k]])
        
        # Check for all-NaN features
        nan_counts = np.isnan(all_features).sum(axis=0)
        all_nan_indices = np.where(nan_counts == len(all_features))[0]
        results["all_nan_features"] = [FEATURE_NAMES[i] for i in all_nan_indices]
        
        # Check for all-zero features
        zero_counts = (all_features == 0).sum(axis=0)
        all_zero_indices = np.where(zero_counts == len(all_features))[0]
        results["all_zero_features"] = [FEATURE_NAMES[i] for i in all_zero_indices]
        
        # Check for infinity
        inf_counts = np.isinf(all_features).sum(axis=0)
        inf_indices = np.where(inf_counts > 0)[0]
        results["infinity_features"] = [FEATURE_NAMES[i] for i in inf_indices]
    
    results["status"] = "PASS" if results["failed"] == 0 else "PARTIAL"
    
    return results


def print_report(results: Dict):
    """Print feature compatibility report."""
    print("=" * 80)
    print("FEATURE COMPATIBILITY CHECK")
    print("=" * 80)
    
    print(f"\n[PROCESSING]")
    print(f"Total images: {results['total_images']}")
    print(f"Processed successfully: {results['processed']}")
    print(f"Failed: {results['failed']}")
    print(f"Status: {results['status']}")
    
    if results["failures"]:
        print(f"\nFailures (first 5):")
        for failure in results["failures"][:5]:
            print(f"  {failure['image_id']}: {failure['error']}")
    
    print(f"\n[FEATURE STATISTICS]")
    for category, stats in results["feature_statistics"].items():
        if stats["count"] > 0:
            print(f"\n{category} ({stats['count']} images):")
            print(f"  Mean: [{', '.join(f'{v:.3f}' for v in stats['mean'][:5])}...]")
            print(f"  Std: [{', '.join(f'{v:.3f}' for v in stats['std'][:5])}...]")
            print(f"  Missing %: [{', '.join(f'{v:.1%}' for v in stats['missing_percentage'][:5])}...]")
    
    print(f"\n[PROBLEMATIC FEATURES]")
    if results["all_nan_features"]:
        print(f"  All-NaN features: {results['all_nan_features']}")
    if results["all_zero_features"]:
        print(f"  All-zero features: {results['all_zero_features']}")
    if results["infinity_features"]:
        print(f"  Infinity features: {results['infinity_features']}")
    
    if not any([results["all_nan_features"], results["all_zero_features"], results["infinity_features"]]):
        print(f"  No problematic features detected")
    
    print("\n" + "=" * 80)


def main():
    """Main function."""
    print("Checking feature extraction compatibility for Dataset V2...")
    
    rows = load_manifest()
    print(f"Loaded {len(rows)} images from manifest")
    
    if not rows:
        print("Dataset is empty - cannot test feature compatibility")
        return 0
    
    results = check_feature_compatibility(rows)
    
    print_report(results)
    
    # Save report
    report_file = ROOT / "reports" / "PHASE_2_FEATURE_COMPATIBILITY.json"
    report_file.parent.mkdir(exist_ok=True)
    with report_file.open("w") as f:
        json.dump(results, f, indent=2)
    
    print(f"\nReport saved to: {report_file}")
    
    return 0 if results["status"] == "PASS" else 1


if __name__ == "__main__":
    exit(main())

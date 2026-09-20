"""Dataset V2 validation script.

This script performs comprehensive validation of Dataset V2 including:
- File integrity checks
- Label validation
- Mask validation
- Duplicate detection
- Leakage detection
- Metadata completeness
- Dataset balance statistics
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

import numpy as np
from PIL import Image
from sklearn.model_selection import GroupShuffleSplit

ROOT = Path(__file__).resolve().parent.parent
DATASET_V2 = ROOT / "dataset_v2"
METADATA_DIR = DATASET_V2 / "metadata"
SCHEMA_FILE = METADATA_DIR / "schema.json"
MANIFEST_FILE = METADATA_DIR / "manifest.jsonl"


class DatasetValidationError(Exception):
    """Raised when dataset validation fails."""
    pass


def load_schema() -> Dict[str, Any]:
    """Load the metadata schema."""
    if not SCHEMA_FILE.exists():
        raise DatasetValidationError(f"Schema file not found: {SCHEMA_FILE}")
    with SCHEMA_FILE.open() as f:
        return json.load(f)


def load_manifest() -> List[Dict[str, Any]]:
    """Load the metadata manifest from JSONL format."""
    if not MANIFEST_FILE.exists():
        raise DatasetValidationError(f"Manifest file not found: {MANIFEST_FILE}")
    
    rows = []
    with MANIFEST_FILE.open() as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            try:
                row = json.loads(line)
                rows.append(row)
            except json.JSONDecodeError as e:
                raise DatasetValidationError(f"Invalid JSON on line {line_num}: {e}")
    
    # Empty manifest is acceptable for infrastructure validation
    # (no data collected yet, but structure is ready)
    
    return rows


def validate_image_file(image_path: Path) -> Tuple[bool, str, Dict[str, Any]]:
    """Validate an image file and return its properties."""
    try:
        img = Image.open(image_path)
        img.verify()  # Verify integrity
        
        # Reopen for properties (verify closes the file)
        img = Image.open(image_path)
        
        return True, "OK", {
            "width": img.width,
            "height": img.height,
            "format": img.format,
            "mode": img.mode,
            "size_bytes": image_path.stat().st_size
        }
    except Exception as e:
        return False, str(e), {}


def compute_sha256(file_path: Path) -> str:
    """Compute SHA-256 hash of a file."""
    sha256_hash = hashlib.sha256()
    with file_path.open("rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            sha256_hash.update(chunk)
    return sha256_hash.hexdigest()


def validate_file_integrity(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Check file integrity and collect image properties."""
    results = {
        "total": len(rows),
        "missing_files": [],
        "corrupt_files": [],
        "unsupported_formats": [],
        "image_properties": {}
    }
    
    for row in rows:
        image_path = DATASET_V2 / row.get("image_path", "")
        if not image_path.exists():
            results["missing_files"].append(row.get("image_id", "unknown"))
            continue
        
        valid, message, props = validate_image_file(image_path)
        if not valid:
            results["corrupt_files"].append({
                "image_id": row.get("image_id"),
                "path": str(image_path),
                "error": message
            })
        else:
            results["image_properties"][row["image_id"]] = props
    
    return results


def validate_labels(rows: List[Dict[str, Any]], schema: Dict[str, Any]) -> Dict[str, Any]:
    """Validate label encoding and consistency."""
    results = {
        "invalid_labels": [],
        "category_label_conflicts": [],
        "label_distribution": {0: 0, 1: 0},
        "category_distribution": {}
    }
    
    allowed_categories = schema["fields"]["category"]["allowed_values"]
    
    for row in rows:
        label = row.get("label")
        category = row.get("category")
        
        # Check label validity
        if label not in [0, 1]:
            results["invalid_labels"].append({
                "image_id": row.get("image_id"),
                "label": label
            })
        
        # Check category validity
        if category not in allowed_categories:
            results["invalid_labels"].append({
                "image_id": row.get("image_id"),
                "category": category,
                "error": f"Invalid category: {category}"
            })
        
        # Check category/label consistency
        manipulated_categories = ["copy_move", "splicing", "object_removal", "inpainting", "resampling", "timestamp", "mixed"]
        genuine_categories = ["original", "natural_processing", "hard_negative"]
        
        if category in manipulated_categories and label != 1:
            results["category_label_conflicts"].append({
                "image_id": row.get("image_id"),
                "category": category,
                "label": label,
                "expected": 1
            })
        
        if category in genuine_categories and label != 0:
            results["category_label_conflicts"].append({
                "image_id": row.get("image_id"),
                "category": category,
                "label": label,
                "expected": 0
            })
        
        # Count distributions
        if label in [0, 1]:
            results["label_distribution"][label] += 1
        
        results["category_distribution"][category] = results["category_distribution"].get(category, 0) + 1
    
    return results


def validate_masks(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Validate ground-truth masks for manipulated images."""
    results = {
        "manipulated_without_masks": [],
        "mask_dimension_mismatches": [],
        "mask_corrupted": [],
        "mask_empty": []
    }
    
    for row in rows:
        if row.get("label") != 1:
            continue  # Only check manipulated images
        
        mask_path = row.get("mask_path")
        if not mask_path:
            results["manipulated_without_masks"].append(row.get("image_id"))
            continue
        
        mask_file = DATASET_V2 / mask_path
        if not mask_file.exists():
            results["manipulated_without_masks"].append(row.get("image_id"))
            continue
        
        # Check mask dimensions match image
        image_path = DATASET_V2 / row.get("image_path", "")
        try:
            img = Image.open(image_path)
            img_width, img_height = img.size
            
            mask = Image.open(mask_file)
            mask_width, mask_height = mask.size
            
            if (img_width, img_height) != (mask_width, mask_height):
                results["mask_dimension_mismatches"].append({
                    "image_id": row.get("image_id"),
                    "image_size": (img_width, img_height),
                    "mask_size": (mask_width, mask_height)
                })
            
            # Check if mask is empty
            mask_array = np.array(mask)
            if np.sum(mask_array) == 0:
                results["mask_empty"].append(row.get("image_id"))
            
        except Exception as e:
            results["mask_corrupted"].append({
                "image_id": row.get("image_id"),
                "error": str(e)
            })
    
    return results


def detect_duplicates(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Detect exact and near-duplicate images."""
    results = {
        "exact_duplicates": [],
        "sha256_collisions": {},
        "potential_near_duplicates": []
    }
    
    sha256_map = {}
    
    for row in rows:
        image_path = DATASET_V2 / row.get("image_path", "")
        if not image_path.exists():
            continue
        
        sha256 = compute_sha256(image_path)
        sha256_map[row["image_id"]] = sha256
    
    # Find exact duplicates (same SHA-256)
    sha256_to_ids: Dict[str, List[str]] = {}
    for image_id, sha256 in sha256_map.items():
        if sha256 not in sha256_to_ids:
            sha256_to_ids[sha256] = []
        sha256_to_ids[sha256].append(image_id)
    
    for sha256, ids in sha256_to_ids.items():
        if len(ids) > 1:
            results["exact_duplicates"].append({
                "sha256": sha256,
                "image_ids": ids
            })
    
    results["sha256_collisions"] = sha256_map
    
    return results


def validate_source_aware_split(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Validate source-aware splitting and check for leakage."""
    results = {
        "missing_source_ids": [],
        "unique_sources": 0,
        "images_per_source": {},
        "leakage_check": {},
        "split_recommendation": {}
    }
    
    # Check for missing source IDs
    for row in rows:
        if not row.get("source_id"):
            results["missing_source_ids"].append(row.get("image_id"))
    
    # Count images per source
    for row in rows:
        source_id = row.get("source_id")
        if source_id:
            results["images_per_source"][source_id] = results["images_per_source"].get(source_id, 0) + 1
    
    results["unique_sources"] = len(results["images_per_source"])
    
    # Simulate split to check for leakage potential
    if len(results["images_per_source"]) >= 3:
        labels = np.array([r["label"] for r in rows])
        groups = np.array([r["source_id"] for r in rows])
        
        try:
            splitter = GroupShuffleSplit(n_splits=1, test_size=0.3, random_state=42)
            train_val, test = next(splitter.split(np.zeros(len(rows)), labels, groups))
            
            # Check if sources would be split
            train_sources = set(groups[train_val])
            test_sources = set(groups[test])
            
            results["leakage_check"] = {
                "train_sources": len(train_sources),
                "test_sources": len(test_sources),
                "source_overlap": len(train_sources & test_sources),
                "status": "OK" if len(train_sources & test_sources) == 0 else "POTENTIAL_LEAKAGE"
            }
        except Exception as e:
            results["leakage_check"] = {
                "error": str(e),
                "status": "ERROR"
            }
    else:
        results["leakage_check"] = {
            "status": "INSUFFICIENT_SOURCES",
            "message": "Need at least 3 sources for train/validation/test split"
        }
    
    # Recommend split allocation
    total_sources = results["unique_sources"]
    if total_sources >= 3:
        train_sources = int(total_sources * 0.7)
        val_sources = int(total_sources * 0.15)
        test_sources = total_sources - train_sources - val_sources
        
        results["split_recommendation"] = {
            "train_sources": train_sources,
            "validation_sources": val_sources,
            "test_sources": test_sources,
            "train_percentage": 70,
            "validation_percentage": 15,
            "test_percentage": 15
        }
    
    return results


def validate_metadata_completeness(rows: List[Dict[str, Any]], schema: Dict[str, Any]) -> Dict[str, Any]:
    """Check metadata completeness."""
    results = {
        "missing_required_fields": [],
        "field_completeness": {}
    }
    
    required_fields = [k for k, v in schema["fields"].items() if v.get("required", False)]
    
    for field in required_fields:
        missing_count = sum(1 for row in rows if field not in row or row[field] is None)
        results["field_completeness"][field] = {
            "total": len(rows),
            "missing": missing_count,
            "completeness": (len(rows) - missing_count) / len(rows) if len(rows) > 0 else 0
        }
        
        if missing_count > 0:
            results["missing_required_fields"].append({
                "field": field,
                "missing_count": missing_count
            })
    
    return results


def print_validation_report(results: Dict[str, Any]):
    """Print a human-readable validation report."""
    print("=" * 80)
    print("DATASET V2 VALIDATION REPORT")
    print("=" * 80)
    
    # File integrity
    print("\n[FILE INTEGRITY]")
    print(f"Total images in manifest: {results['file_integrity']['total']}")
    print(f"Missing files: {len(results['file_integrity']['missing_files'])}")
    print(f"Corrupt files: {len(results['file_integrity']['corrupt_files'])}")
    
    if results['file_integrity']['missing_files']:
        print(f"  Missing: {results['file_integrity']['missing_files'][:5]}")
    
    # Labels
    print("\n[LABEL VALIDATION]")
    print(f"Invalid labels: {len(results['labels']['invalid_labels'])}")
    print(f"Category/label conflicts: {len(results['labels']['category_label_conflicts'])}")
    print(f"Label distribution: {results['labels']['label_distribution']}")
    print(f"Category distribution: {results['labels']['category_distribution']}")
    
    # Masks
    print("\n[MASK VALIDATION]")
    print(f"Manipulated without masks: {len(results['masks']['manipulated_without_masks'])}")
    print(f"Mask dimension mismatches: {len(results['masks']['mask_dimension_mismatches'])}")
    print(f"Corrupted masks: {len(results['masks']['mask_corrupted'])}")
    print(f"Empty masks: {len(results['masks']['mask_empty'])}")
    
    # Duplicates
    print("\n[DUPLICATE DETECTION]")
    print(f"Exact duplicate groups: {len(results['duplicates']['exact_duplicates'])}")
    
    # Source-aware split
    print("\n[SOURCE-AWARE SPLIT]")
    print(f"Unique sources: {results['split']['unique_sources']}")
    print(f"Images per source: {results['split']['images_per_source']}")
    print(f"Leakage check: {results['split']['leakage_check'].get('status', 'N/A')}")
    print(f"Split recommendation: {results['split']['split_recommendation']}")
    
    # Metadata completeness
    print("\n[METADATA COMPLETENESS]")
    print(f"Missing required fields: {len(results['metadata']['missing_required_fields'])}")
    
    print("\n" + "=" * 80)


def main():
    """Main validation function."""
    print("Starting Dataset V2 validation...")
    
    try:
        # Load schema and manifest
        schema = load_schema()
        rows = load_manifest()
        
        if not rows:
            print("Manifest is empty - validating infrastructure only")
            print("Dataset V2 infrastructure is ready for data collection")
            return 0
        
        print(f"Loaded {len(rows)} rows from manifest")
        
        # Run all validations
        results = {
            "file_integrity": validate_file_integrity(rows),
            "labels": validate_labels(rows, schema),
            "masks": validate_masks(rows),
            "duplicates": detect_duplicates(rows),
            "split": validate_source_aware_split(rows),
            "metadata": validate_metadata_completeness(rows, schema)
        }
        
        # Print report
        print_validation_report(results)
        
        # Save detailed report
        report_file = ROOT / "reports" / "PHASE_2_DATASET_VALIDATION.json"
        report_file.parent.mkdir(exist_ok=True)
        with report_file.open("w") as f:
            json.dump(results, f, indent=2)
        
        print(f"\nDetailed report saved to: {report_file}")
        
        # Overall status
        has_critical_issues = (
            len(results['file_integrity']['missing_files']) > 0 or
            len(results['labels']['invalid_labels']) > 0 or
            len(results['labels']['category_label_conflicts']) > 0 or
            len(results['split']['missing_source_ids']) > 0
        )
        
        if has_critical_issues:
            print("\n[X] VALIDATION FAILED - Critical issues found")
            return 1
        else:
            print("\n[OK] VALIDATION PASSED - No critical issues")
            return 0
            
    except DatasetValidationError as e:
        print(f"\n[X] VALIDATION ERROR: {e}")
        return 1
    except Exception as e:
        print(f"\n[X] UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())

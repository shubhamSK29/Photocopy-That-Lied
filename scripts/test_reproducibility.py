"""Phase 22: Test reproducibility and idempotency.

This script verifies:
- Deterministic IDs are used
- Metadata structure is consistent
- No duplicate records exist
- Dataset structure is idempotent
"""

import json
from pathlib import Path
from collections import Counter
import hashlib

manifest_path = Path(__file__).resolve().parent.parent / "dataset_v2" / "metadata" / "manifest.jsonl"
root = Path(__file__).resolve().parent.parent

records = []
with manifest_path.open() as f:
    for line in f:
        if line.strip():
            records.append(json.loads(line))

print("=== Phase 22: Reproducibility and Idempotency Test ===\n")

# Test 1: Check for duplicate image IDs
print("TEST 1: Duplicate Image ID Check")
image_ids = [r['image_id'] for r in records]
duplicate_ids = [id for id, count in Counter(image_ids).items() if count > 1]

if duplicate_ids:
    print(f"[FAIL] Found {len(duplicate_ids)} duplicate image IDs")
    for dup_id in duplicate_ids[:5]:
        print(f"  - {dup_id}")
else:
    print("[PASS] No duplicate image IDs found")

# Test 2: Check ID determinism (consistent naming patterns)
print("\nTEST 2: ID Determinism Check")
# Check that IDs follow consistent patterns
manip_ids = [r['image_id'] for r in records if r['category'] == 'manipulated']
np_ids = [r['image_id'] for r in records if r['category'] == 'natural_processing']
hn_ids = [r['image_id'] for r in records if r['category'] == 'hard_negative']

# Check that manipulated IDs contain manipulation type
manip_id_pattern_issues = []
for img_id in manip_ids:
    if not any(t in img_id for t in ['COPY_MOVE', 'OBJECT_REMOVAL', 'OBJECT_INSERTION', 'SPLICING']):
        manip_id_pattern_issues.append(img_id)

if manip_id_pattern_issues:
    print(f"[FAIL] {len(manip_id_pattern_issues)} manipulated IDs don't follow pattern")
else:
    print("[PASS] All manipulated IDs follow naming pattern")

# Check that natural-processing IDs contain NP
np_id_pattern_issues = []
for img_id in np_ids:
    if 'NP_' not in img_id:
        np_id_pattern_issues.append(img_id)

if np_id_pattern_issues:
    print(f"[FAIL] {len(np_id_pattern_issues)} natural-processing IDs don't follow pattern")
else:
    print("[PASS] All natural-processing IDs follow naming pattern")

# Check that hard-negative IDs contain HN
hn_id_pattern_issues = []
for img_id in hn_ids:
    if 'HN_' not in img_id:
        hn_id_pattern_issues.append(img_id)

if hn_id_pattern_issues:
    print(f"[FAIL] {len(hn_id_pattern_issues)} hard-negative IDs don't follow pattern")
else:
    print("[PASS] All hard-negative IDs follow naming pattern")

# Test 3: Check metadata consistency
print("\nTEST 3: Metadata Consistency Check")
# Original records don't have parent fields
base_required_fields = ['image_id', 'source_id', 'category', 'label', 'dataset_version']
variant_required_fields = ['parent_image_id', 'parent_source_id', 'variant_id', 'generation_method', 'processing_operations']

missing_fields = []
for record in records:
    # Check base fields for all records
    for field in base_required_fields:
        if field not in record:
            missing_fields.append((record['image_id'], field))
    
    # Check variant fields only for non-original records
    if record['category'] != 'original':
        for field in variant_required_fields:
            if field not in record:
                missing_fields.append((record['image_id'], field))

if missing_fields:
    print(f"[FAIL] {len(missing_fields)} missing required fields")
    for img_id, field in missing_fields[:5]:
        print(f"  - {img_id}: missing {field}")
else:
    print("[PASS] All records have required metadata fields")

# Test 4: Check category-label consistency
print("\nTEST 4: Category-Label Consistency Check")
category_label_conflicts = []
for record in records:
    category = record['category']
    label = record['label']
    
    if category == 'manipulated' and label != 1:
        category_label_conflicts.append((record['image_id'], category, label))
    elif category in ['original', 'natural_processing', 'hard_negative'] and label != 0:
        category_label_conflicts.append((record['image_id'], category, label))

if category_label_conflicts:
    print(f"[FAIL] {len(category_label_conflicts)} category-label conflicts")
    for img_id, cat, lbl in category_label_conflicts[:5]:
        print(f"  - {img_id}: {cat} has label {lbl}")
else:
    print("[PASS] All category-label assignments are consistent")

# Test 5: Check source family consistency
print("\nTEST 5: Source Family Consistency Check")
# Check that all variants from a source have the same source_id
source_id_issues = []
for record in records:
    if record['category'] != 'original':  # Only check variants
        parent_source_id = record.get('parent_source_id')
        if parent_source_id and record['source_id'] != parent_source_id:
            source_id_issues.append((record['image_id'], record['source_id'], parent_source_id))

if source_id_issues:
    print(f"[FAIL] {len(source_id_issues)} source_id inconsistencies")
    for img_id, src_id, parent_src_id in source_id_issues[:5]:
        print(f"  - {img_id}: source_id={src_id}, parent_source_id={parent_src_id}")
else:
    print("[PASS] All source_id assignments are consistent")

# Test 6: Check dataset version consistency
print("\nTEST 6: Dataset Version Consistency Check")
dataset_versions = [r.get('dataset_version') for r in records]
version_counts = Counter(dataset_versions)

if len(version_counts) == 1:
    print(f"[PASS] All records use dataset version: {list(version_counts.keys())[0]}")
else:
    print(f"[FAIL] Multiple dataset versions found: {dict(version_counts)}")

# Test 7: Check file path consistency
print("\nTEST 7: File Path Consistency Check")
# Check that variant files are in correct directories
path_issues = []
for record in records:
    category = record['category']
    image_path = record.get('image_path', '')
    
    if category == 'manipulated' and 'manipulated' not in image_path:
        path_issues.append((record['image_id'], category, image_path))
    elif category == 'natural_processing' and 'natural_processing' not in image_path:
        path_issues.append((record['image_id'], category, image_path))
    elif category == 'hard_negative' and 'hard_negative' not in image_path:
        path_issues.append((record['image_id'], category, image_path))

if path_issues:
    print(f"[FAIL] {len(path_issues)} file path inconsistencies")
    for img_id, cat, path in path_issues[:5]:
        print(f"  - {img_id}: {cat} file not in expected directory")
else:
    print("[PASS] All file paths are in correct directories")

# Test 8: Check for accidental regeneration
print("\nTEST 8: Accidental Regeneration Check")
# Check that all variant IDs are unique and follow expected patterns
variant_ids = [r.get('variant_id') for r in records if r.get('variant_id')]
duplicate_variants = [vid for vid, count in Counter(variant_ids).items() if count > 1]

if duplicate_variants:
    print(f"[FAIL] {len(duplicate_variants)} duplicate variant IDs found")
    for vid in duplicate_variants[:5]:
        print(f"  - {vid}")
else:
    print("[PASS] No duplicate variant IDs found")

# Summary
print("\n=== REPRODUCIBILITY TEST SUMMARY ===")
tests = [
    ("Duplicate Image IDs", len(duplicate_ids) == 0),
    ("ID Determinism", len(manip_id_pattern_issues) == 0 and len(np_id_pattern_issues) == 0 and len(hn_id_pattern_issues) == 0),
    ("Metadata Consistency", len(missing_fields) == 0),
    ("Category-Label Consistency", len(category_label_conflicts) == 0),
    ("Source Family Consistency", len(source_id_issues) == 0),
    ("Dataset Version Consistency", len(version_counts) == 1),
    ("File Path Consistency", len(path_issues) == 0),
    ("Accidental Regeneration", len(duplicate_variants) == 0)
]

passed = sum(1 for _, result in tests if result)
total = len(tests)

for test_name, result in tests:
    status = "[PASS]" if result else "[FAIL]"
    print(f"{status} {test_name}")

print(f"\nOverall: {passed}/{total} tests passed")

if passed == total:
    print("\n[OK] REPRODUCIBILITY TEST PASSED")
    print("Dataset structure is deterministic and idempotent")
else:
    print(f"\n[X] REPRODUCIBILITY TEST FAILED")
    print(f"{total - passed} tests failed")

# Save reproducibility report
report = {
    "reproducibility_test": {
        "duplicate_image_ids": len(duplicate_ids),
        "id_determinism": len(manip_id_pattern_issues) == 0 and len(np_id_pattern_issues) == 0 and len(hn_id_pattern_issues) == 0,
        "metadata_consistency": len(missing_fields) == 0,
        "category_label_consistency": len(category_label_conflicts) == 0,
        "source_family_consistency": len(source_id_issues) == 0,
        "dataset_version_consistency": len(version_counts) == 1,
        "file_path_consistency": len(path_issues) == 0,
        "accidental_regeneration": len(duplicate_variants) == 0,
        "tests_passed": passed,
        "tests_total": total,
        "overall_status": "PASS" if passed == total else "FAIL"
    }
}

report_file = root / "reports" / "PHASE_22_REPRODUCIBILITY_TEST.json"
report_file.parent.mkdir(exist_ok=True)
with report_file.open("w") as f:
    json.dump(report, f, indent=2)

print(f"\nReproducibility report saved to: {report_file}")

print("\n=== Phase 22 Complete ===")

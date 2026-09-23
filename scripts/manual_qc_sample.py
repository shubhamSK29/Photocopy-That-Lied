"""Phase 21: Manual Quality Control Inspection.

This script generates a QC sample with representative examples from each category.
The user should manually inspect these examples to verify quality.

For manipulated samples, inspect:
- original → manipulated → ground-truth mask
Check that the manipulation is visually plausible and the mask actually identifies the manipulated region.
"""

import json
from pathlib import Path
import random

manifest_path = Path(__file__).resolve().parent.parent / "dataset_v2" / "metadata" / "manifest.jsonl"
root = Path(__file__).resolve().parent.parent

records = []
with manifest_path.open() as f:
    for line in f:
        if line.strip():
            records.append(json.loads(line))

print("=== Phase 21: Manual Quality Control Sample ===\n")

# Group records by category
by_category = {}
for record in records:
    category = record['category']
    if category not in by_category:
        by_category[category] = []
    by_category[category].append(record)

# Sample 5 examples from each category
qc_sample = {}
samples_per_category = 5

for category, category_records in by_category.items():
    random.seed(42)  # For reproducibility
    if len(category_records) >= samples_per_category:
        qc_sample[category] = random.sample(category_records, samples_per_category)
    else:
        qc_sample[category] = category_records

print("MANUAL QC SAMPLE GENERATION")
print("=" * 80)

for category, samples in qc_sample.items():
    print(f"\n{category.upper()} ({len(samples)} samples):")
    for i, sample in enumerate(samples, 1):
        image_id = sample['image_id']
        image_path = sample.get('image_path', 'N/A')
        print(f"  {i}. {image_id}")
        print(f"     Path: {image_path}")
        
        if category == 'manipulated':
            mask_path = sample.get('mask_path', 'N/A')
            manip_type = sample.get('manipulation_type', 'N/A')
            area_ratio = sample.get('parameters', {}).get('manipulation_area_ratio', 'N/A')
            print(f"     Mask: {mask_path}")
            print(f"     Type: {manip_type}")
            print(f"     Area ratio: {area_ratio}")
            print(f"     QC CHECK: Verify manipulation is plausible and mask is accurate")

# Save QC sample report
qc_report = {
    "qc_sample": {
        category: [
            {
                "image_id": sample['image_id'],
                "image_path": sample.get('image_path'),
                "category": sample['category'],
                "label": sample['label'],
                "mask_path": sample.get('mask_path') if category == 'manipulated' else None,
                "manipulation_type": sample.get('manipulation_type') if category == 'manipulated' else None,
                "manipulation_area_ratio": sample.get('parameters', {}).get('manipulation_area_ratio') if category == 'manipulated' else None
            }
            for sample in samples
        ]
        for category, samples in qc_sample.items()
    },
    "qc_instructions": {
        "for_all_categories": [
            "Verify image loads correctly",
            "Verify image quality is acceptable",
            "Verify image looks realistic for the category"
        ],
        "for_manipulated": [
            "Compare original with manipulated image",
            "Verify manipulation is visually plausible",
            "Verify mask accurately identifies manipulated region",
            "Verify mask dimensions match image dimensions",
            "Verify manipulation area ratio is reasonable"
        ],
        "for_natural_processing": [
            "Verify processing looks legitimate",
            "Verify no obvious manipulation artifacts",
            "Verify processing parameters are realistic"
        ],
        "for_hard_negative": [
            "Verify aggressive processing is challenging but legitimate",
            "Verify no actual content manipulation",
            "Verify strong forensic artifacts may be present"
        ]
    },
    "qc_form": {
        "image_id": "string",
        "category": "string",
        "visual_quality": "acceptable/needs_improvement/reject",
        "manipulation_plausible": "yes/no/uncertain (manipulated only)",
        "mask_accurate": "yes/no/uncertain (manipulated only)",
        "notes": "string",
        "overall": "pass/fail"
    }
}

report_file = root / "reports" / "PHASE_21_MANUAL_QC_SAMPLE.json"
report_file.parent.mkdir(exist_ok=True)
with report_file.open("w") as f:
    json.dump(qc_report, f, indent=2)

print(f"\nQC sample report saved to: {report_file}")

print("\n=== MANUAL QC INSTRUCTIONS ===")
print("1. Open the QC sample report")
print("2. For each sample, inspect the image and associated files")
print("3. For manipulated samples, inspect: original -> manipulated -> mask")
print("4. Fill out the QC form for each sample")
print("5. Document any issues found")
print("6. Return pass/fail status for each category")

print("\n=== AUTOMATED QC CHECKS ===")
print("Checking for common issues...")

# Automated checks
issues = []

# Check for missing image paths
missing_paths = []
for record in records:
    if not record.get('image_path'):
        missing_paths.append(record['image_id'])

if missing_paths:
    issues.append(f"Missing image paths: {len(missing_paths)} records")
    print(f"[WARNING] {len(missing_paths)} records missing image paths")
else:
    print("[OK] All records have image paths")

# Check for missing masks for manipulated
missing_masks = []
for record in records:
    if record['category'] == 'manipulated' and not record.get('mask_path'):
        missing_masks.append(record['image_id'])

if missing_masks:
    issues.append(f"Missing masks: {len(missing_masks)} manipulated records")
    print(f"[WARNING] {len(missing_masks)} manipulated records missing masks")
else:
    print("[OK] All manipulated records have masks")

# Check for label consistency
label_conflicts = []
for record in records:
    if record['category'] == 'manipulated' and record['label'] != 1:
        label_conflicts.append(record['image_id'])
    if record['category'] in ['original', 'natural_processing', 'hard_negative'] and record['label'] != 0:
        label_conflicts.append(record['image_id'])

if label_conflicts:
    issues.append(f"Label conflicts: {len(label_conflicts)} records")
    print(f"[WARNING] {len(label_conflicts)} records have label conflicts")
else:
    print("[OK] All labels are consistent with categories")

print("\n=== AUTOMATED QC SUMMARY ===")
if issues:
    print(f"[WARNING] Found {len(issues)} issues:")
    for issue in issues:
        print(f"  - {issue}")
else:
    print("[OK] No automated QC issues found")

print("\n=== Phase 21 Complete ===")
print("Manual QC inspection required for final validation")

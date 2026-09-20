"""Generate comprehensive dataset statistics for Dataset V2."""

import json
from pathlib import Path
from collections import Counter
import numpy as np

manifest_path = Path(__file__).resolve().parent.parent / "dataset_v2" / "metadata" / "manifest.jsonl"

records = []
with manifest_path.open() as f:
    for line in f:
        if line.strip():
            records.append(json.loads(line))

print("=== DATASET V2 STATISTICS ===\n")

# Basic counts
total = len(records)
by_category = Counter(r['category'] for r in records)
by_label = Counter(r['label'] for r in records)

print("TOTAL RECORDS:", total)
print("\nCATEGORY DISTRIBUTION:")
for cat, count in by_category.items():
    print(f"  {cat}: {count} ({count/total*100:.1f}%)")

print("\nLABEL DISTRIBUTION:")
for label, count in by_label.items():
    print(f"  Label {label}: {count} ({count/total*100:.1f}%)")

# Manipulation type breakdown
manip_records = [r for r in records if r['category'] == 'manipulated']
manip_by_type = Counter(r['manipulation_type'] for r in manip_records)

print("\nMANIPULATION TYPE DISTRIBUTION:")
for man_type, count in manip_by_type.items():
    print(f"  {man_type}: {count}")

# Manipulation area ratio statistics
area_ratios = []
for record in manip_records:
    ratio = record.get('parameters', {}).get('manipulation_area_ratio')
    if ratio is not None:
        area_ratios.append(ratio)

if area_ratios:
    print(f"\nMANIPULATION AREA RATIO STATISTICS:")
    print(f"  Count: {len(area_ratios)}")
    print(f"  Min: {min(area_ratios):.4f}")
    print(f"  Max: {max(area_ratios):.4f}")
    print(f"  Mean: {np.mean(area_ratios):.4f}")
    print(f"  Median: {np.median(area_ratios):.4f}")
    print(f"  Std: {np.std(area_ratios):.4f}")
    print(f"  Unique values: {len(set(area_ratios))}")

# Source utilization
sources_by_variants = Counter(r['source_id'] for r in records)
unique_sources = len(sources_by_variants)

print(f"\nSOURCE UTILIZATION:")
print(f"  Unique sources: {unique_sources}")
print(f"  Min variants per source: {min(sources_by_variants.values())}")
print(f"  Max variants per source: {max(sources_by_variants.values())}")
print(f"  Mean variants per source: {np.mean(list(sources_by_variants.values())):.1f}")
print(f"  Median variants per source: {np.median(list(sources_by_variants.values())):.1f}")

# Split distribution
split_counts = {}
for record in records:
    params = record.get('parameters', {})
    if 'split' in params:
        split = params['split']
        split_counts[split] = split_counts.get(split, 0) + 1

if split_counts:
    print(f"\nSPLIT DISTRIBUTION (for donor-based manipulations):")
    for split, count in split_counts.items():
        print(f"  {split}: {count}")

# Processing operation distribution
np_ops = Counter()
hn_ops = Counter()
for record in records:
    if record['category'] == 'natural_processing':
        for op in record.get('processing_operations', []):
            np_ops[op] += 1
    elif record['category'] == 'hard_negative':
        for op in record.get('processing_operations', []):
            hn_ops[op] += 1

print(f"\nNATURAL-PROCESSING OPERATIONS:")
for op, count in np_ops.items():
    print(f"  {op}: {count}")

print(f"\nHARD-NEGATIVE OPERATIONS:")
for op, count in hn_ops.items():
    print(f"  {op}: {count}")

# Source family balance
sources_with_categories = {}
for record in records:
    source_id = record['source_id']
    if source_id not in sources_with_categories:
        sources_with_categories[source_id] = set()
    sources_with_categories[source_id].add(record['category'])

category_per_source = [len(cats) for cats in sources_with_categories.values()]
print(f"\nSOURCE CATEGORY DIVERSITY:")
print(f"  Sources with 1 category: {category_per_source.count(1)}")
print(f"  Sources with 2 categories: {category_per_source.count(2)}")
print(f"  Sources with 3 categories: {category_per_source.count(3)}")
print(f"  Sources with 4 categories: {category_per_source.count(4)}")

print("\n=== STATISTICS COMPLETE ===")

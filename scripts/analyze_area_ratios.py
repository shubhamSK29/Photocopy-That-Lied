"""Analyze manipulation area ratios in detail."""

import json
import numpy as np
from pathlib import Path

manifest_path = Path(__file__).resolve().parent.parent / "dataset_v2" / "metadata" / "manifest.jsonl"

ratios = []
manipulation_types = {}

with manifest_path.open() as f:
    for line in f:
        if line.strip():
            record = json.loads(line)
            if record.get('category') == 'manipulated':
                params = record.get('parameters', {})
                ratio = params.get('manipulation_area_ratio')
                if ratio is not None:
                    ratios.append(ratio)
                    man_type = record.get('manipulation_type', 'unknown')
                    if man_type not in manipulation_types:
                        manipulation_types[man_type] = []
                    manipulation_types[man_type].append(ratio)

print(f"Total manipulated records with area ratios: {len(ratios)}")
print(f"\nOverall statistics:")
print(f"  Min: {min(ratios):.4f}")
print(f"  Max: {max(ratios):.4f}")
print(f"  Mean: {np.mean(ratios):.4f}")
print(f"  Median: {np.median(ratios):.4f}")
print(f"  Std: {np.std(ratios):.4f}")

print(f"\nBy manipulation type:")
for man_type, type_ratios in manipulation_types.items():
    print(f"  {man_type}:")
    print(f"    Count: {len(type_ratios)}")
    print(f"    Min: {min(type_ratios):.4f}")
    print(f"    Max: {max(type_ratios):.4f}")
    print(f"    Mean: {np.mean(type_ratios):.4f}")

# Verify all ratios are in valid range
invalid = [r for r in ratios if r <= 0 or r > 1]
if invalid:
    print(f"\nWARNING: Found {len(invalid)} invalid ratios (should be 0 < ratio <= 1)")
    print(f"Invalid values: {invalid}")
else:
    print(f"\nAll ratios are in valid range (0 < ratio <= 1)")

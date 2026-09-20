"""Check manipulation area ratios in current dataset."""

import json
from pathlib import Path

manifest_path = Path(__file__).resolve().parent.parent / "dataset_v2" / "metadata" / "manifest.jsonl"

records_with_ratio = []
records_without_ratio = []

with manifest_path.open() as f:
    for line in f:
        if line.strip():
            record = json.loads(line)
            if record.get('category') == 'manipulated':
                params = record.get('parameters', {})
                if 'manipulation_area_ratio' in params:
                    records_with_ratio.append((record['image_id'], params['manipulation_area_ratio']))
                else:
                    records_without_ratio.append(record['image_id'])

print(f"Manipulated records with manipulation_area_ratio: {len(records_with_ratio)}")
print(f"Manipulated records without manipulation_area_ratio: {len(records_without_ratio)}")

if records_with_ratio:
    print("\nSample records with ratios:")
    for img_id, ratio in records_with_ratio[:5]:
        print(f"  {img_id}: {ratio:.4f}")

if records_without_ratio:
    print(f"\nRecords without ratios (first 10):")
    for img_id in records_without_ratio[:10]:
        print(f"  {img_id}")

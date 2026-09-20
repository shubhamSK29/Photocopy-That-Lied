"""Anti-shortcut audit for Dataset V2."""

import json
from pathlib import Path
from collections import Counter, defaultdict
from PIL import Image

manifest_path = Path(__file__).resolve().parent.parent / "dataset_v2" / "metadata" / "manifest.jsonl"

records = []
with manifest_path.open() as f:
    for line in f:
        if line.strip():
            records.append(json.loads(line))

print("=== ANTI-SHORTCUT AUDIT ===\n")

# Check JPEG quality distribution by category
jpeg_quality_by_category = defaultdict(list)
for record in records:
    if 'jpeg_recompression' in record.get('processing_operations', []):
        quality = record.get('parameters', {}).get('quality')
        if quality:
            jpeg_quality_by_category[record['category']].append(quality)

print("JPEG Quality by Category:")
for category, qualities in jpeg_quality_by_category.items():
    counter = Counter(qualities)
    print(f"  {category}: {dict(counter)}")

# Check image formats by category
formats_by_category = defaultdict(list)
for record in records:
    fmt = record.get('format')
    if fmt:
        formats_by_category[record['category']].append(fmt)

print("\nImage Format by Category:")
for category, formats in formats_by_category.items():
    counter = Counter(formats)
    print(f"  {category}: {dict(counter)}")

# Check dimensions by category
dimensions_by_category = defaultdict(list)
for record in records:
    w, h = record.get('width'), record.get('height')
    if w and h:
        dimensions_by_category[record['category']].append((w, h))

print("\nDimension Counts by Category:")
for category, dims in dimensions_by_category.items():
    counter = Counter(dims)
    unique_dims = len(counter)
    print(f"  {category}: {unique_dims} unique dimensions")

# Check file sizes by category
file_sizes_by_category = defaultdict(list)
for record in records:
    img_path_str = record.get('image_path')
    if img_path_str:
        img_path = Path(__file__).resolve().parent.parent / img_path_str
        if img_path.exists():
            file_sizes_by_category[record['category']].append(img_path.stat().st_size)
    else:
        # Original sources don't have image_path in manifest
        if record.get('category') == 'original':
            source_path = Path(__file__).resolve().parent.parent / "dataset_v2" / "sources" / "deepweeds_raw" / "images" / f"{record['source_id']}.jpg"
            if source_path.exists():
                file_sizes_by_category[record['category']].append(source_path.stat().st_size)

print("\nFile Size Statistics by Category:")
for category, sizes in file_sizes_by_category.items():
    if sizes:
        print(f"  {category}: min={min(sizes)}, max={max(sizes)}, mean={sum(sizes)/len(sizes):.0f}")

# Check manipulation area ratio distribution
area_ratios = []
for record in records:
    if record.get('category') == 'manipulated':
        ratio = record.get('parameters', {}).get('manipulation_area_ratio')
        if ratio is not None:
            area_ratios.append(ratio)

if area_ratios:
    print(f"\nManipulation Area Ratio Distribution:")
    print(f"  Min: {min(area_ratios):.4f}")
    print(f"  Max: {max(area_ratios):.4f}")
    print(f"  Mean: {sum(area_ratios)/len(area_ratios):.4f}")
    print(f"  Unique values: {len(set(area_ratios))}")

# Check processing operation diversity
operations_by_category = defaultdict(list)
for record in records:
    for op in record.get('processing_operations', []):
        operations_by_category[record['category']].append(op)

print("\nProcessing Operations by Category:")
for category, ops in operations_by_category.items():
    counter = Counter(ops)
    print(f"  {category}: {dict(counter)}")

# Check if filenames leak labels
print("\nFilename Label Leakage Check:")
label_in_filename = 0
for record in records:
    filename = record.get('image_id', '')
    if 'manipulated' in filename.lower() or 'manip' in filename.lower():
        if record.get('label') == 1:
            print(f"  WARNING: 'manipulated' in filename for label 1: {filename}")
            label_in_filename += 1
    if 'natural' in filename.lower() or 'process' in filename.lower():
        if record.get('label') == 0:
            # This is expected for natural processing
            pass

if label_in_filename == 0:
    print("  OK: No obvious label leakage in filenames")

print("\n=== AUDIT COMPLETE ===")

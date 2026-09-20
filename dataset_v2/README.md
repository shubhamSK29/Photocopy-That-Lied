# Dataset V2 Infrastructure

This directory contains the infrastructure for Dataset V2, a scientifically valid dataset for crop-insurance image forensics.

## Directory Structure

```
dataset_v2/
├── genuine/
│   ├── original/           # Genuine original photographs
│   └── natural_processing/ # Legitimate processing variants (label=0)
├── manipulated/
│   ├── copy_move/          # Copy-move forgeries
│   ├── splicing/           # Splicing forgeries
│   ├── object_removal/     # Object removal forgeries
│   ├── inpainting/         # Inpainting forgeries
│   ├── resampling/         # Resampling forgeries
│   ├── timestamp/          # Timestamp modification forgeries
│   └── mixed/              # Mixed manipulation forgeries
├── hard_negatives/         # Challenging genuine images (label=0)
├── masks/                  # Ground-truth masks for manipulated images
├── sources/                # Source/parent images for manipulation generation
├── metadata/
│   ├── schema.json         # Metadata schema definition
│   └── manifest.jsonl      # Dataset metadata (JSONL format)
└── splits/
    ├── train.json          # Training split image IDs
    ├── validation.json     # Validation split image IDs
    ├── test.json           # Test split image IDs
    └── splits.json        # Combined splits with metadata
```

## Key Principles

1. **Natural Processing ≠ Manipulation**
   - Images with legitimate processing (resize, JPEG, sharpen, etc.) remain label=0 (genuine)
   - Only deliberate content manipulation gets label=1 (manipulated)

2. **Source-Aware Splitting**
   - All variants of the same source image must stay in the same split
   - Prevents source leakage between train/validation/test

3. **Ground-Truth Masks**
   - Required for all manipulated images where localization is possible
   - Binary encoding: 0 = non-manipulated, 1 = manipulated
   - Same dimensions as the manipulated image

4. **Metadata Completeness**
   - Every image must have a complete metadata entry
   - Required fields: image_id, source_id, label, category, width, height, format, color_mode, generation_method, metadata_available, dataset_version

## Adding Images to Dataset V2

### Step 1: Add Image Files
Place images in the appropriate category directory:
- Genuine originals → `genuine/original/`
- Natural processing variants → `genuine/natural_processing/`
- Manipulated images → `manipulated/{type}/`
- Hard negatives → `hard_negatives/`

### Step 2: Create Ground-Truth Masks
For manipulated images, create corresponding masks in `masks/`:
- Binary PNG format (0 = genuine, 1 = manipulated)
- Same dimensions as the manipulated image
- Naming convention: `{image_name}_mask.png`

### Step 3: Add Metadata Entry
Add a JSON line to `metadata/manifest.jsonl`:

```json
{
  "image_id": "IMG_000001",
  "source_id": "SRC_000123",
  "label": 0,
  "category": "original",
  "width": 1920,
  "height": 1080,
  "format": "JPEG",
  "color_mode": "RGB",
  "generation_method": "real_camera",
  "processing_operations": [],
  "metadata_available": true,
  "dataset_version": "dataset-real-v1"
}
```

For manipulated images:
```json
{
  "image_id": "IMG_000045",
  "source_id": "SRC_000123",
  "label": 1,
  "category": "copy_move",
  "manipulation_type": "copy_move",
  "parent_image_id": "IMG_000001",
  "mask_path": "masks/IMG_000045_mask.png",
  "width": 1920,
  "height": 1080,
  "format": "JPEG",
  "color_mode": "RGB",
  "generation_method": "synthetic_generation",
  "processing_operations": ["copy", "translate", "blend"],
  "manipulation_parameters": {"source_region": [100,100,200,200], "target_region": [300,300,400,400]},
  "metadata_available": false,
  "dataset_version": "dataset-real-v1"
}
```

### Step 4: Validate Dataset
Run the validation script:
```bash
python scripts/validate_dataset_v2.py
```

### Step 5: Create Splits
After adding all images, create source-aware splits:
```bash
python scripts/create_dataset_v2_splits.py
```

### Step 6: Run Quality Checks
Run all quality control scripts:
```bash
python scripts/detect_duplicates.py
python scripts/audit_leakage.py
python scripts/validate_masks.py
python scripts/dataset_statistics.py
python scripts/check_feature_compatibility.py
```

## Validation Scripts

- `validate_dataset_v2.py` - Comprehensive dataset validation
- `detect_duplicates.py` - Exact and near-duplicate detection
- `audit_leakage.py` - Source, duplicate, and metadata leakage checks
- `validate_masks.py` - Ground-truth mask validation
- `dataset_statistics.py` - Dataset statistics and balance
- `check_feature_compatibility.py` - Feature extraction compatibility test
- `create_dataset_v2_splits.py` - Source-aware split generation

## Important Rules

1. **Never label natural processing as manipulation**
   - Resize, JPEG, sharpen, denoise, etc. → label=0 (genuine)
   - Only deliberate content manipulation → label=1 (manipulated)

2. **Never mix sources across splits**
   - All variants of source SRC_001 must be in the same split
   - Never have SRC_001_original in train and SRC_001_copy_move in test

3. **Never use metadata as manipulation evidence**
   - Missing EXIF ≠ manipulation
   - Compression ≠ manipulation
   - File format ≠ manipulation

4. **Never remove difficult samples to improve metrics**
   - Hard negatives are essential for false-positive control
   - Keep challenging genuine images

## Target Dataset Size

### Minimum Viable Dataset
- **Total Images:** 1000
- **Genuine:** 600
- **Manipulated:** 400
- **Unique Sources:** 50
- **Test Set:** 150 images from 8-10 unseen sources

### Ideal Dataset
- **Total Images:** 3000+
- **Genuine:** 1800+
- **Manipulated:** 1200+
- **Unique Sources:** 150+
- **Test Set:** 450+ images from 20-30 unseen sources

## Status

**Current Status:** Infrastructure Ready, Data Pending

The Dataset V2 infrastructure is complete and ready for data collection. No images have been added yet - this is a framework for future data collection.

## Preservation of Dataset V1

The original dataset in `dataset/` (Dataset V1) is preserved unchanged and should remain available for:
- Baseline comparison
- Debugging and pipeline testing
- Prototype demonstration

Dataset V2 will be used for:
- Scientific validation
- Model training and evaluation
- Production decisions

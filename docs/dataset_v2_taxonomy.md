# Dataset V2 Taxonomy

## Purpose

Dataset V2 is an image-forensics dataset for crop-loss insurance claim photographs. The system detects possible image manipulation using image-level forensic evidence rather than EXIF metadata.

The prototype provides:
- Manipulation Risk Score: 0–100
- Risk classification: Low / Review Required / High
- Manipulation localization / heatmap
- Forensic evidence
- Human-readable explanations
- Uncertainty / confidence
- Data-coverage information
- Human-in-the-loop review

**Important:** The system must NOT automatically reject insurance claims.

---

## Primary Categories

### A. ORIGINAL

**Definition:** Untouched real-camera source image.

**Properties:**
- `label = 0`
- `category = "original"`
- `generation_method = "real_camera"`
- `processing_operations = []`

**Characteristics:**
- No synthetic manipulation
- No generated mask
- These are the reference real images
- Source images remain in `dataset_v2/sources/` untouched

**Mask:** No

---

### B. NATURAL PROCESSING

**Definition:** Legitimate image processing that can occur during normal camera/software/social-media/workflow processing.

**Properties:**
- `label = 0`
- `category = "natural_processing"`
- `generation_method = "natural_processing"`
- `processing_operations = [operations]`

**Purpose:** Represent legitimate processing that may create forensic artifacts. The model must learn that legitimate processing can create artifacts without being manipulation.

**Examples:**
- JPEG recompression
- Mild resizing
- Mild sharpening
- Mild denoising
- Brightness adjustment
- Contrast adjustment
- Color adjustment
- Mild gamma adjustment
- Format conversion (where appropriate)
- Combinations of legitimate operations

**Mask:** No

**Provenance Requirements:**
- `parent_image_id`
- `parent_source_id`
- `variant_id`
- `processing_operations` array with operation types and parameters
- `parameters` object with detailed operation settings
- `random_seed` if applicable
- `output_path`
- `output_format`
- `output_dimensions`
- `output_sha256`
- `creation_timestamp`

**Example:**
```
parent: SRC_DW_001
variant: SRC_DW_001_NP_JPEG_Q75
operation: jpeg_recompression
parameter: quality=75
```

---

### C. HARD NEGATIVE

**Definition:** Legitimate images that may look suspicious to a forensic model because they contain strong image artifacts.

**Properties:**
- `label = 0`
- `category = "hard_negative"`
- `generation_method = "hard_negative"`
- `processing_operations = [operations]`

**Purpose:** Reduce false positives by teaching the model that forensic artifacts ≠ manipulation automatically.

**Examples:**
- Aggressive but legitimate JPEG compression
- Substantial resizing
- Strong but plausible sharpening
- Strong denoising
- Brightness/contrast changes
- Color processing
- Multiple legitimate processing operations
- Resampling artifacts
- Camera/software processing artifacts

**Mask:** No

**Principle:** Natural-processing and hard-negative examples must remain label 0 because they are NOT manipulated.

---

### D. MANIPULATED

**Definition:** Actual image-content manipulation.

**Properties:**
- `label = 1`
- `category = "manipulated"`
- `generation_method = "manipulated"`
- `processing_operations = [operations]`
- `manipulation_type = <type>`

**Initial Manipulation Types:**

#### M1 — Copy-Move
Copy a region of the image and paste it somewhere else within the same image.

**Required Fields:**
- `source_region`: {x, y, width, height}
- `destination_region`: {x, y, width, height}
- `mask_id`
- `transformation`: {scale, rotation, flip}
- `blending_method`

#### M2 — Object Removal
Remove an object/region and reconstruct the area using inpainting.

**Required Fields:**
- `removed_region`: {x, y, width, height}
- `mask_id`
- `inpainting_method`
- `inpainting_parameters`

#### M3 — Object Insertion
Insert a new object/region into the image.

**Required Fields:**
- `source_object`: description or ID
- `destination_location`: {x, y, width, height}
- `mask_id`
- `scale`
- `rotation`
- `blending`

#### M4 — Splicing / Region Replacement
Replace a region using content from another image.

**Required Fields:**
- `donor_image_id`
- `donor_source_id`
- `target_region`: {x, y, width, height}
- `mask_id`
- `transformation`
- `blending`

#### M5 — Composite Manipulation (Optional)
Combinations like:
- Insertion + color adjustment
- Insertion + resizing
- Splicing + blending
- Copy-move + transformation

**Implementation:** Only if technically justified by experimental evidence.

**Mask:** Yes — Required for all localized manipulations

**Mask Requirements:**
- Must correspond exactly to output image dimensions
- Must identify manipulated pixels/regions
- Must contain nonzero manipulated pixels
- Must be stored separately
- Must have stable `mask_id`
- Must be linked to variant record

**Example:**
```
image: DW_001_M_COPYMOVE_001.jpg
mask: DW_001_M_COPYMOVE_001_mask.png
```

---

## Schema Consistency Rules

### If category = "original"
- `label` must = 0
- `manipulation_type` must be null/empty
- `mask_id` must be null/empty
- `processing_operations` must be empty
- `parent_image_id` must be null/empty
- `parent_source_id` must be null/empty

### If category = "natural_processing"
- `label` must = 0
- `manipulation_type` must be null/empty
- `mask_id` must be null/empty
- `processing_operations` must not be empty
- `parent_image_id` must be present
- `parent_source_id` must be present

### If category = "hard_negative"
- `label` must = 0
- `manipulation_type` must be null/empty
- `mask_id` must be null/empty
- `processing_operations` must describe hard-negative generation
- `parent_image_id` must be present
- `parent_source_id` must be present

### If category = "manipulated"
- `label` must = 1
- `manipulation_type` must be present
- `mask_id` must be present for localized manipulation
- `parent_image_id` must be present
- `parent_source_id` must be present
- `processing_operations` must describe manipulation operations

---

## Source Family Model

```
source_image
    ↓
original
    ├── natural_processing variants
    ├── hard_negative variants
    └── manipulated variants
```

**All variants must retain:**
- `parent_image_id`
- `parent_source_id`

**The source family determines the split.**

---

## Split Rules

**Rule:** The split is assigned at SOURCE-FAMILY level.

**Never assign a split independently to each variant.**

**Examples:**
- `SRC_DW_A → TRAIN` → Every derivative of `SRC_DW_A → TRAIN`
- `SRC_DW_B → TEST` → Every derivative of `SRC_DW_B → TEST`

**Enforcement:** This must be enforced automatically by code. Do not trust manual entry.

---

## Stable Identifiers

**Do not use iteration numbers as primary identity.**

**Use deterministic identifiers based on source/provenance.**

**Structure:**
- `source_id`: Stable hash of canonical source identifier
- `image_id`: For originals, equals source_id
- `variant_id`: Deterministic hash or structured ID based on:
  - Parent image
  - Variant category
  - Operation
  - Parameters
  - Seed (where required)

**Same generation request must produce same identity.**

---

## Manifest Architecture

**Required Conceptual Fields:**
- `image_id`
- `source_id`
- `parent_image_id` (for variants)
- `parent_source_id` (for variants)
- `variant_id` (for variants)
- `label`
- `category`
- `generation_method`
- `processing_operations`
- `manipulation_type` (for manipulated)
- `parameters`
- `mask_id` (for manipulated)
- `image_path` (optional, may use SHA-256 lookup)
- `mask_path` (for manipulated)
- `width`
- `height`
- `format`
- `color_mode`
- `sha256`
- `dataset_version`
- `provenance`

**Note:** Current DeepWeeds originals do not have `image_path` field. Validator uses SHA-256 lookup in source directories.

---

## Anti-Shortcut Rules

**Do NOT create easy dataset shortcuts:**

- All originals should NOT all have the same JPEG quality
- All manipulated images should NOT all have different dimensions
- All fake images should NOT all use PNG while real use JPEG
- All fake images should NOT have specific filenames
- All fake images should NOT have specific metadata
- All fake images should NOT have masks that indirectly leak labels
- All natural images should NOT use one fixed parameter

**The generated dataset must prevent trivial classification shortcuts.**

---

## Parameter Diversity

**Future generation must use controlled parameter ranges.**

**Examples:**
- JPEG quality: Multiple realistic quality levels (e.g., 70, 75, 80, 85, 90, 95)
- Resize: Multiple scale factors (e.g., 0.5, 0.75, 0.9, 1.1, 1.25, 1.5)
- Sharpening: Multiple strengths
- Brightness: Multiple strengths
- Contrast: Multiple strengths
- Manipulation area: Multiple area percentages
- Blending: Multiple blending strengths
- Rotation: Multiple angles (where applicable)
- Scale: Multiple scales (where applicable)

**Do not randomly generate completely uncontrolled values. Use documented parameter distributions.**

---

## Manipulation Area Distribution

**Field:** `manipulation_area_ratio`

**Future generator should support multiple ranges:**
- Very small manipulation (e.g., < 5%)
- Small manipulation (e.g., 5-15%)
- Medium manipulation (e.g., 15-30%)
- Large manipulation (e.g., > 30%)

**Do not make every manipulated region the same size.**

---

## Dataset Balance Plan

**Track before generation:**
- Total images
- Original count
- Natural-processing count
- Manipulated count
- Hard-negative count
- Manipulation type counts
- Processing-operation counts
- Train count
- Validation count
- Test count
- Unique source count
- Manipulation-area distribution
- Image dimensions
- Image format
- Compression/quality parameters
- Source-family distribution

**Do not generate huge dataset before checking these statistics.**

---

## Validation Rules for Future Generation

**Identity Problems:**
- Duplicate image IDs
- Duplicate variant IDs
- Duplicate source IDs (where prohibited)

**File Problems:**
- Missing files
- Unreadable files
- Corrupted images

**Metadata Problems:**
- Invalid category
- Invalid label
- Missing provenance
- Invalid parameters

**Split Leakage:**
- Same source family appearing in multiple splits

**Manipulation Problems:**
- Manipulated image without mask
- Mask dimension mismatch
- Empty mask
- Invalid manipulation type

**Natural-Processing Problems:**
- Category says natural_processing but no operation recorded

**Hard-Negative Problems:**
- Hard negative accidentally labeled 1

**Hash Problems:**
- Duplicate output hashes
- Unexpected duplicate content

---

## Future Generation Workflow

1. Select source families from appropriate splits
2. Generate variants with controlled parameters
3. Compute SHA-256 for each output
4. Generate ground-truth masks for manipulations
5. Record complete provenance
6. Validate against taxonomy rules
7. Add to manifest
8. Re-validate entire dataset
9. Update balance statistics
10. Document final distribution

---

## Current Dataset V2 Status

**Foundation:**
- 1,000 DeepWeeds original images imported
- 700 train / 150 validation / 150 test split
- Source-level split assignment (no leakage)
- Validation passing
- Raw source integrity verified (17,509 images unchanged)

**Next Phase:** Controlled Dataset V2 Variant Generation

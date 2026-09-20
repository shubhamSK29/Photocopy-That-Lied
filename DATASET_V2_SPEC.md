# DATASET V2 SPECIFICATION
## Requirements for Production-Ready Forensic Dataset
**Date:** 2026-09-20  
**Purpose:** Define requirements for a scientifically valid dataset for crop-insurance image forensics

---

## DATASET V2 DECISION

### Current Dataset Suitability Assessment

**Question:** Is the current 72-image dataset suitable for serious model training and evaluation?

**Answer:** **C. Insufficient for model training but useful as a baseline**

### Evidence
1. **100% Synthetic Data** - No real crop photographs
2. **Tiny Dataset** - Only 72 images from 6 sources
3. **Limited Generalization** - Test set contains only ~1 unseen source
4. **Limited Manipulation Types** - Only copy-move and splicing
5. **No Ground-Truth Masks** - Cannot evaluate localization
6. **Small Test Set** - ~11 images insufficient for reliable metrics

### Recommendation
**Dataset V2 is REQUIRED** for any serious model training or deployment decision.

The current dataset (Dataset V1) should be:
- ✅ Preserved as baseline comparison
- ✅ Used for debugging and prototype testing
- ✅ Used for pipeline validation
- ❌ NOT used for scientific validation
- ❌ NOT used for deployment decisions
- ❌ NOT used for publication-quality results

---

## DATASET V2 REQUIREMENTS

### OVERALL GOALS
1. **Real-World Data:** Actual crop-insurance photographs, not synthetic renders
2. **Sufficient Size:** Minimum 1000+ images for robust ML
3. **Scientific Validity:** Proper splitting, ground truth, reproducibility
4. **Representative:** Diverse scenes, devices, lighting, processing pipelines
5. **Manipulation Diversity:** Multiple forgery types with varying difficulty

---

## GENUINE IMAGES

### Real Crop Photographs
**Target:** 600+ genuine images

**Requirements:**
- Real photographs of agricultural fields (crops, soil, sky, equipment)
- Variety of crop types (wheat, rice, corn, soybeans, etc.)
- Different growth stages (seedling, flowering, harvest)
- Multiple seasons and weather conditions
- Different times of day
- Various angles and perspectives

### Device Diversity
**Target:** At least 10 different smartphone models
- Flagship phones (2-3 models)
- Mid-range phones (3-4 models)
- Budget phones (3-4 models)
- Old devices (1-2 models)

**Purpose:** Capture different sensor characteristics, noise profiles, JPEG quality

### Scene Diversity
**Target:** At least 20 different agricultural scenes
- Row crops
- Field margins
- Equipment in field
- Sky/horizon
- Soil close-ups
- Damaged crops
- Flooded fields
- Various lighting conditions

---

## NATURAL PROCESSING VARIANTS

### Legitimate Processing Pipeline Coverage
**Target:** 200+ genuine images with natural processing

**Required Transformations:**
1. **Resize** - Downscaling to various resolutions
2. **JPEG Compression** - Multiple quality levels (95, 85, 75, 65)
3. **Recompression** - Multiple compression passes
4. **Sharpening** - Various intensities
5. **Denoising** - Various algorithms
6. **Contrast Adjustment** - Brightness/contrast changes
7. **Color Enhancement** - Saturation, hue adjustments
8. **Screenshots** - From different devices and apps
9. **Messaging App Pipelines** - WhatsApp, Telegram, WeChat, etc.
10. **Social Media Pipelines** - Instagram, Facebook, Twitter, etc.
11. **HDR Processing** - Various HDR implementations
12. **Multi-App Pipelines** - Camera → Messaging → Social → Download

**Purpose:** Ensure model does not confuse legitimate processing with manipulation

---

## MANIPULATED IMAGES

### Manipulation Types
**Target:** 400+ manipulated images

**Required Manipulation Types:**

1. **Copy-Move Forgeries** (100+ images)
   - Region duplication within same image
   - Various region sizes (small, medium, large)
   - Different transformations (rotation, scaling, color adjustment)
   - Challenging cases (repetitive textures, near boundaries)

2. **Splicing/Inpainting** (100+ images)
   - Content pasted from different sources
   - Object insertion
   - Object removal with inpainting
   - Background replacement
   - Various blending techniques

3. **Object Removal** (50+ images)
   - Object deletion with surrounding content filling
   - Different removal sizes and locations
   - Various inpainting algorithms

4. **Resampling Forgery** (50+ images)
   - Upscaling/downscaling artifacts
   - Non-uniform resampling
   - Geometric transformations

5. **Timestamp Modification** (50+ images)
   - Burned-in timestamp editing
   - Timestamp insertion/removal
   - Inconsistent timestamps (EXIF vs visible)

6. **Mixed Manipulations** (50+ images)
   - Copy-move + recompression
   - Splicing + color adjustment
   - Multiple manipulations on same image
   - Chaining of operations

### Ground-Truth Masks
**Requirement:** Every manipulated image must have a corresponding ground-truth mask

**Mask Specifications:**
- Binary mask (0=genuine, 1=manipulated)
- Same resolution as original image
- Accurate boundary delineation
- File naming convention: `{image_name}_mask.png`
- Metadata linking mask to manipulation type

**Purpose:** Enable localization evaluation and IoU/Dice metrics

---

## HARD NEGATIVES

### Challenging Genuine Images
**Target:** 100+ hard negative images

**Required Hard Negative Types:**
1. **Repetitive Patterns** (30+ images)
   - Repeated leaves/plants
   - Crop rows with strong periodicity
   - Textured backgrounds
   - Symmetrical structures

2. **Compression Artifacts** (20+ images)
   - Heavy JPEG compression
   - Artifacts that resemble manipulation
   - Blockiness patterns

3. **Lighting Challenges** (20+ images)
   - Strong shadows
   - Low-light conditions
   - Overexposed regions
   - High contrast

4. **Processing Artifacts** (20+ images)
   - Heavy sharpening
   - Strong denoising
   - HDR processing
   - Color fringing

5. **Metadata Variations** (10+ images)
   - EXIF removed
   - Different software fields
   - Camera metadata inconsistencies

**Purpose:** Ensure model doesn't flag legitimate difficult cases as manipulation

---

## SOURCE-AWARE SPLITTING

### Grouping Strategy
**Requirement:** All variants from the same source must remain in the same split

**Grouping Fields:**
- `source_id` - Unique identifier for original photograph
- `session_id` - Grouping for related captures
- `device_id` - Grouping for device-specific patterns

**Split Allocation:**
- **Train:** 70% of sources
- **Validation:** 15% of sources
- **Test:** 15% of sources

**Leakage Prevention:**
- No source appears in multiple splits
- No session appears in multiple splits
- All variants of same source stay together
- Validation used for threshold tuning only
- Test set locked before any threshold selection

---

## METADATA REQUIREMENTS

### Required Metadata Fields
Every image must include:
- `image_path` - Relative path to image file
- `label` - 0 (genuine) or 1 (manipulated)
- `source_id` - Unique source identifier
- `parent_id` - Parent image identifier
- `session_id` - Session grouping identifier
- `device_id` - Device identifier
- `category` - Image category (genuine, natural_variant, hard_negative, copy_move, etc.)
- `manipulation_type` - Type of manipulation (if applicable)
- `transformation` - Processing applied
- `ground_truth_mask_path` - Path to mask (if manipulated)
- `dataset_version` - Dataset version identifier
- `synthetic` - Boolean (false for real data)

### EXIF Metadata
Preserve original EXIF where available:
- Camera make/model
- Capture timestamp
- GPS coordinates (if available)
- Software used
- Image dimensions

---

## IMAGE QUALITY REQUIREMENTS

### Resolution Range
- **Minimum:** 640x480
- **Maximum:** 4000x3000
- **Preferred:** 1280x960 to 2560x1920

### File Formats
- **Primary:** JPEG (most common in real-world)
- **Secondary:** PNG (for lossless storage if needed)
- **Avoid:** TIFF, BMP (uncommon in real-world pipelines)

### Quality Checks
- No corrupted files
- No truncation
- Valid JPEG/PNG headers
- Reasonable file sizes (not empty, not excessively large)

---

## ANNOTATION GUIDELINES

### Manipulation Annotation
For each manipulated image, document:
1. **Manipulation Type** - Which manipulation was applied
2. **Manipulation Location** - Where in the image
3. **Manipulation Difficulty** - Easy/Medium/Hard
4. **Tools Used** - Which software/algorithm
5. **Parameters** - Key parameters used
6. **Reviewer Notes** - Any relevant observations

### Ground-Truth Mask Creation
- Use pixel-accurate masks
- Include full manipulated region
- Exclude edge blending if intention is to test boundary detection
- Document mask creation methodology

---

## REPRODUCIBILITY REQUIREMENTS

### Dataset Versioning
- Version identifier (e.g., dataset-real-v1)
- Creation timestamp
- Dataset creator
- Contact information
- License terms

### File Hashes
- SHA-256 hash for every image
- Hash verification in manifest
- Integrity checking on load

### Documentation
- Complete dataset description
- Collection methodology
- Annotation guidelines
- Known limitations
- Bias assessment

---

## RECOMMENDED TARGET SIZE

### Minimum Viable Dataset
- **Total Images:** 1000
- **Genuine:** 600
- **Manipulated:** 400
- **Sources:** 50 unique sources
- **Test Set:** 150 images from 8-10 unseen sources

### Ideal Dataset
- **Total Images:** 3000+
- **Genuine:** 1800+
- **Manipulated:** 1200+
- **Sources:** 150+ unique sources
- **Test Set:** 450+ images from 20-30 unseen sources

### Dataset V2 Priority
**Immediate Priority (Minimum Viable):**
- 1000 real images
- 50 unique sources
- Ground-truth masks for all manipulations
- Source-aware splitting
- Proper documentation

**Future Enhancement (Ideal):**
- 3000+ images
- 150+ sources
- More manipulation types
- Diverse device coverage
- Multi-lingual OCR support

---

## VALIDATION PLAN

### Dataset Quality Checks
1. **Integrity Check** - All files load correctly
2. **Label Verification** - Manual spot-check of labels
3. **Mask Verification** - Manual spot-check of mask accuracy
4. **Leakage Check** - Verify grouped split prevents leakage
5. **Bias Check** - Assess demographic/geographic bias
6. **Representativeness Check** - Compare to real claim distribution

### Statistical Analysis
1. **Class Balance** - Ensure reasonable genuine:manipulated ratio
2. **Feature Distribution** - Analyze forensic feature distributions
3. **Cross-Validation** - Test generalization across sources
4. **Ablation Studies** - Test detector contributions

---

## IMPLEMENTATION NOTES

### Data Collection
- Partner with insurance companies for real claim data
- Ensure privacy and consent for data use
- Follow data protection regulations (GDPR, etc.)
- Remove personally identifiable information

### Data Augmentation
- Use data augmentation during training only
- Do not augment test set
- Document augmentation parameters
- Ensure augmentation doesn't introduce synthetic artifacts

### Ethical Considerations
- Ensure data represents diverse geographic regions
- Avoid demographic bias
- Document any known biases
- Consider fairness implications

---

## SUCCESS CRITERIA

Dataset V2 is successful when:
1. ✅ Contains real crop-insurance photographs (not synthetic)
2. ✅ Has 1000+ images from 50+ unique sources
3. ✅ Includes ground-truth masks for all manipulations
4. ✅ Has proper source-aware splitting with no leakage
5. ✅ Covers multiple manipulation types
6. ✅ Includes sufficient hard negatives
7. ✅ Has comprehensive metadata and documentation
8. ✅ Passes all quality and integrity checks
9. ✅ Enables reliable model evaluation (statistically significant test set)
10. ✅ Is reproducible and well-documented

---

**Specification Created:** 2026-09-20  
**Status:** Ready for Dataset V2 implementation
# Photocopy That Lied - Prototype Report

**Date**: 2026-09-21
**Version**: 1.0.0
**Status**: Prototype Complete

---

## Problem Statement

Insurance claim photographs can be manipulated using digital editing tools. Detecting such manipulation requires specialized forensic analysis to identify technical evidence of image tampering.

**Scientific Claim:**
> AI-assisted image integrity and manipulation detection for insurance claim photographs.

**NOT a claim of:**
- Insurance fraud detection
- Automatic claim rejection
- Real-world generalization without external testing

---

## Dataset

### Dataset V2 Overview

Dataset V2 is a source-aware, reproducible forensic dataset designed for research-grade image forensics.

**Statistics:**
- Total records: 3,895
- Authentic: 3,595
- Manipulated: 300
- Source families with variants: 602/1,000 (60.2%)

**Manipulation Types:**
- Copy-move: 75
- Object removal: 75
- Object insertion: 75
- Splicing: 75

**Categories:**
- Original: 1,000
- Natural processing: 1,425
- Hard negatives: 1,170
- Manipulated: 300

**Splits:**
- Train: 2,758
- Validation: 600
- Test: 537

**Location:** `dataset_v2/`

### Dataset V2 Construction

Dataset V2 was constructed from:
- **Source**: DeepWeeds dataset (University of Queensland, CC BY 4.0)
- **Raw source**: 17,509 DeepWeeds images in `dataset_v2/sources/deepweeds_raw/images/`
- **Metadata**: `dataset_v2/metadata/manifest.jsonl`
- **Schema**: `dataset_v2/metadata/schema.json`
- **Splits**: `dataset_v2/splits/`

### Dataset Validation

All validation checks passed:
- Missing files: 0
- Corrupt files: 0
- Duplicate IDs: 0
- Source leakage: 0
- Donor leakage: 0
- Mask validation: PASS
- Anti-shortcut audit: PASS
- Reproducibility: PASS
- Tests: 63/63 PASS

### Manual QC Status

Manual QC samples have been prepared (35 samples across 7 categories). Visual inspection is pending human review. Automated validation passed all checks.

---

## Architecture

### System Architecture

```
                   USER
                    │
                    ▼
             React Frontend
                    │
                    ▼
              FastAPI API
                    │
                    ▼
             Image Validation
                    │
                    ▼
          Forensic Feature Extraction
                    │
                    ▼
             Demo Fusion Model
                    │
                    ▼
          Manipulation Probability
                    │
                    ▼
              Risk Score 0–100
                    │
             ┌──────┴──────┐
             ▼             ▼
        Risk Category    Evidence
             │             │
             └──────┬──────┘
                    ▼
          Anomaly Visualization
                    │
                    ▼
              Human Review
```

### Backend Components

**Forensic Detectors** (`backend/forensic/`):
- Copy-move: SIFT/ORB-based detection with geometric verification
- Compression: JPEG quality estimation, blockiness, resampling detection
- Local anomaly: Patch-based anomaly detection
- Spatial: Spatial combination and heatmap generation
- Metadata: EXIF extraction
- Timestamp: Timestamp detection

**Feature Builder** (`backend/features/feature_builder.py`):
- 16 forensic features
- Copy-move features (4)
- Local anomaly features (3)
- Compression features (4)
- Spatial features (2)
- Natural processing similarity (1)

**Fusion/Prediction** (`backend/fusion/predict.py`):
- Demo fallback mode: Deterministic weighted rule fusion
- Trained model support: Placeholder for future Dataset V2 model
- Calibration: CalibratedClassifierCV

**Pipeline** (`backend/pipeline/analysis.py`):
- End-to-end analysis orchestration
- Image normalization
- Detector execution
- Feature building
- Evidence generation
- Heatmap rendering

**API** (`backend/api/analyze.py`):
- POST /api/analyze
- GET /api/analysis/{analysis_id}
- GET /api/analyses
- GET /api/artifacts/{analysis_id}/{name}
- GET /api/config

### Frontend Components

**Pages** (`frontend/src/pages/`):
- Upload: Image upload with drag-and-drop
- Processing: Loading state during analysis
- Results: Comprehensive results display

**Features**:
- Risk score display (0-100)
- Risk category (Low/Review/High)
- Evidence summary and details
- Forensic heatmap (original/heatmap/overlay)
- Provenance information
- Warnings and limitations
- Disclaimer

---

## Forensic Features

### Current Features (16)

**Copy-Move Detection:**
- `copy_move_verified_matches`: Number of verified duplicate regions
- `copy_move_inlier_ratio`: Ratio of inliers to matches
- `copy_move_region_count`: Number of detected regions
- `copy_move_region_area`: Fraction of image area covered

**Local Anomaly:**
- `patch_max_anomaly`: Maximum anomaly score across patches
- `patch_mean_anomaly`: Mean anomaly score
- `patch_anomaly_fraction`: Fraction of anomalous patches

**Compression/Resampling:**
- `compression_score`: Overall compression artifact score
- `resampling_score`: Resampling detection score
- `blockiness`: JPEG blockiness metric
- `jpeg_quality`: Estimated JPEG quality

**Image Statistics:**
- `image_megapixels`: Image size in megapixels
- `bytes_per_pixel`: Bytes per pixel (file density)

**Spatial:**
- `spatial_iou`: Intersection over union of detector heatmaps
- `spatial_dice`: Dice coefficient of detector heatmaps

**Natural Processing:**
- `natural_processing_similarity`: Similarity to natural processing library

### Feature Restrictions

The model does NOT use:
- Filename
- Directory
- Category
- Manipulation type
- Label
- Mask
- Source ID
- Variant ID
- Split

These are metadata only, not classification features.

---

## Model

### Current Model: Demo Fallback

The prototype currently uses a deterministic rule-based fusion system (demo fallback mode).

**Formula:**
```
evidence = 0.34 * max(copy_move, matches)
         + 0.24 * patch_anomaly
         + 0.12 * anomaly_fraction
         + 0.20 * spatial_dice
         + 0.10 * compression_score

damping = 1.0 - 0.35 * natural_processing_similarity
strong_duplication = max(copy_move, matches) > 0.5
if strong_duplication:
    damping = max(damping, 0.85)

probability = clip(evidence * damping, 0.0, 1.0)
```

**Why Demo Fallback?**
- A trained Dataset V2 model was attempted but showed class imbalance issues (12:1 authentic:manipulated)
- The demo fallback provides meaningful forensic evidence using real detectors
- Sufficient for prototype demonstration
- Can be replaced with trained model post-deadline

### Future Model Training

**Dataset V2 Classifier Training** (`scripts/train_dataset_v2_model.py`):
- Logistic Regression with class weighting
- Pipeline: impute → scale → classifier
- Calibration: CalibratedClassifierCV
- Status: Script created, training completed but needs class imbalance refinement

---

## Risk Scoring

### Risk Score Calculation

```
risk_score = probability × 100
```

### Risk Bands

- **Low Risk**: score < 30
  - "No significant manipulation evidence"
- **Review Required**: 30 ≤ score < 60
  - "Review required"
- **High Risk**: score ≥ 60
  - "High-priority forensic review"

### Configuration

Thresholds are configurable via environment variables:
- `PTL_BAND_LOW`: Default 30
- `PTL_BAND_HIGH`: Default 60

---

## Evidence Generation

### Evidence Types

The system generates evidence based on actual detector outputs:

1. **Copy-Move Evidence**
   - Duplicated regions detected
   - Geometric verification
   - Region statistics

2. **Compression/Resampling Evidence**
   - JPEG quality inconsistencies
   - Blockiness artifacts
   - Resampling indicators

3. **Local Anomaly Evidence**
   - Patch-level inconsistencies
   - Anomaly distribution
   - Spatial clustering

4. **Natural Processing Explanation**
   - Similarity to natural processing library
   - Legitimate processing identification

5. **Metadata Evidence**
   - EXIF presence/absence
   - Timestamp detection
   - Metadata consistency

### Evidence Display

Evidence is displayed in the Results page with:
- Strength indicator (Strong/Moderate/Weak/None)
- Status (detected/not_applicable/error)
- Score (0-100%)
- Explanation text
- Detailed metrics

---

## Anomaly Visualization

### Heatmap Generation

The system generates forensic anomaly heatmaps using:
- Copy-move detection heatmaps
- Local anomaly heatmaps
- Spatial combination

### Visualization Modes

**Original**: The analysis image
**Heatmap**: Color-coded anomaly map (JET colormap)
**Overlay**: Semi-transparent heatmap over original image

### Limitations

Heatmaps are:
- Approximate forensic signals
- Not pixel-perfect proof of manipulation
- Based on detector outputs
- Subject to false positives

---

## Training Methodology

### Dataset V2 Data Loader

**File**: `backend/data/dataset_v2_loader.py`

**Features**:
- Manifest.jsonl loading
- Portable image path resolution
- Mask loading for manipulated images
- Split isolation enforcement
- Metadata preservation
- Source ID to filename mapping via SHA256

**Tests**: 7/7 PASS

### Feature Extraction

Features are extracted using the existing forensic detectors and feature builder.

### Model Training (Prototype)

The prototype uses the demo fallback model. A trained model script exists but requires class imbalance refinement.

---

## Evaluation

### Dataset V2 Validation

All automated validation checks passed:
- Missing files: 0
- Corrupt files: 0
- Duplicate IDs: 0
- Source leakage: 0
- Donor leakage: 0
- Mask validation: PASS
- Anti-shortcut audit: PASS
- Reproducibility: PASS
- Tests: 63/63 PASS

### Manual QC

Manual QC samples prepared (35 samples). Visual inspection pending human review.

### Backend API Testing

Tested with 7 demo images:
- All 7 analyses completed successfully
- Risk scores generated for all images
- Evidence returned for all images
- Heatmaps generated for all images

### End-to-End Testing

- Backend: Running on http://localhost:8000
- Frontend: Running on http://localhost:5173
- Integration: API communication functional
- Upload → Analyze → Results workflow: Working

---

## Risk Scoring Implementation

### Implementation

**File**: `backend/config.py`

**Function**: `risk_band(score: float) -> str`

**Configuration**:
- `REVIEW_BAND_LOW`: 30 (default)
- `REVIEW_BAND_HIGH`: 60 (default)

### Integration

Risk scoring is integrated into:
- API responses
- Frontend display
- Evidence generation

---

## Limitations

### System Limitations

1. **Model**: Currently using demo fallback mode. A trained Dataset V2 model is needed for improved performance.

2. **Class Imbalance**: Dataset V2 has 12:1 authentic:manipulated ratio. This affects classifier training.

3. **Manual QC**: Visual inspection of Dataset V2 samples is pending.

4. **Features**: Limited to 16 forensic features. Additional features can improve performance.

5. **Demo Dataset**: Limited to 7 representative images for testing.

6. **Performance**: Not optimized for production deployment.

### Scientific Limitations

1. **Scope**: System detects technical evidence consistent with manipulation, not fraud.

2. **Generalization**: Not tested on external datasets. Real-world generalization requires external testing.

3. **Hard Negatives**: Natural processing and hard negatives can create forensic artifacts.

4. **Compression**: Compression artifacts do not prove manipulation.

5. **Metadata**: Missing EXIF does not prove manipulation.

6. **Heatmaps**: Heatmaps are approximate signals, not pixel-perfect proof.

7. **Human Review**: System assists human reviewers; it does not determine fraud.

8. **Claim Rejection**: System must not be used to automatically reject insurance claims.

---

## Future Work

### Immediate (Post-Deadline)

1. Complete manual QC review of Dataset V2
2. Train improved Dataset V2 classifier with better class imbalance handling
3. Add extended forensic features (noise, color, edge, frequency)
4. Subset evaluation by manipulation type

### Medium-Term

5. Implement CNN baseline (ResNet/EfficientNet)
6. Implement localization model (U-Net)
7. Implement hybrid CNN + forensic features model
8. Conduct comprehensive evaluation with all metrics

### Long-Term

9. Robustness testing (recompression, resizing, etc.)
10. Generalization testing on external datasets
11. Advanced calibration
12. Experiment tracking system
13. Large-scale model comparison
14. Production deployment optimization

---

## Reproducibility

### Dataset Reproducibility

- All generation scripts preserved
- Seeds recorded in metadata
- SHA256 hashes for all images
- Split definitions deterministic
- Source-aware splitting enforced

### Model Reproducibility

- Feature extraction deterministic
- Model configuration saved
- Training metadata saved
- Metrics recorded

### System Reproducibility

- Docker containerization (future)
- Configuration via environment variables
- Version control for all code
- Test suite (63/63 PASS)

---

## Deployment Architecture

### Current Development Deployment

**Backend**:
- FastAPI with Uvicorn
- Port: 8000
- Command: `python -m uvicorn backend.main:app --reload --port 8000`

**Frontend**:
- Vite dev server
- Port: 5173
- Command: `npm run dev`

### Production Deployment (Future)

- Backend: Gunicorn/Uvicorn workers
- Frontend: Nginx static file serving
- Database: SQLite (or PostgreSQL for scale)
- Storage: Local filesystem (or S3 for scale)
- Monitoring: Logging and metrics

---

## How to Use

### Starting the System

**Backend:**
```bash
cd backend
python -m uvicorn backend.main:app --reload --port 8000
```

**Frontend:**
```bash
cd frontend
npm run dev
```

### Using the Interface

1. Open http://localhost:5173
2. Upload an image (drag-and-drop or click)
3. Click "Analyze"
4. View results:
   - Risk score (0-100)
   - Risk category
   - Evidence summary
   - Evidence details
   - Forensic heatmap
   - Provenance information
   - Warnings and limitations

### Testing with Demo Dataset

```bash
python scripts/test_api.py
```

This tests the API with 7 representative images from Dataset V2.

---

## Conclusion

The Photocopy That Lied prototype is complete and functional. It provides:

✅ End-to-end working pipeline
✅ Real forensic analysis (not mocked)
✅ Risk scoring and evidence display
✅ Anomaly visualization
✅ Human-review workflow
✅ Comprehensive documentation

The system demonstrates AI-assisted image forensics for insurance claim photographs and is ready for Tuesday submission as a research-quality prototype.

**Final Status**: ✅ PROTOTYPE READY FOR SUBMISSION

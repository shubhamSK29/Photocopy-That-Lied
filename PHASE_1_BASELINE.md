# PHASE 1 BASELINE
## Photocopy That Lied - Current State Documentation
**Date:** 2026-09-20  
**Phase:** 1 - Dataset Validity Audit + Model Failure Diagnosis + Environment Repair

---

## 1. CURRENT ARCHITECTURE

### System Pipeline
```
Image Upload → Validation → SHA-256/Provenance → Metadata/EXIF → 
Forensic Detectors → Spatial Evidence → Natural Processing Calibration → 
Feature Builder → Fusion Model → Manipulation Evidence + Data Coverage → 
Heatmap + Explanation → Human Reviewer → Report
```

### Technology Stack
- **Backend:** FastAPI (0.141.1) with Uvicorn (0.53.0)
- **Frontend:** React 19 with TypeScript, Vite (build environment broken)
- **ML:** scikit-learn (1.7.2), calibrated logistic regression
- **Storage:** SQLite database + file system artifacts
- **Python:** 3.11.9
- **Node:** Not available in current environment

---

## 2. DATASET LOCATION

### Dataset Structure
```
dataset/
├── authentic/               # 6 genuine base images
├── natural_variants/        # 24 legitimate processing variants
├── hard_cases/              # 18 difficult genuine images
├── copy_move/               # 6 copy-move manipulations
├── splicing/                # 6 splicing manipulations
├── manipulated_recompressed/ # 6 manipulated + recompressed
├── timestamp_overlay/       # 6 genuine images with burned-in timestamps
└── manifests/
    ├── dataset.csv          # Dataset manifest (72 images)
    └── dataset.json         # Dataset metadata
```

### Dataset Metadata
- **Total Images:** 72
- **Genuine Images:** 54 (75%)
- **Manipulated Images:** 18 (25%)
- **Synthetic:** 100% (all images)
- **Source Images:** 6 (one per simulated device)
- **Variants per Source:** 12

---

## 3. MODEL LOCATION

### Model Artifacts
```
models/
├── fusion_model.joblib      # Current trained model (in-use)
└── fusion-v1/
    ├── model.joblib         # Trained model backup
    ├── feature_schema.json  # Feature schema documentation
    ├── metadata.json        # Training metadata
    ├── evaluation_report.json # Test metrics
    ├── confusion_matrix.png # Evaluation visualization
    ├── roc_curve.png        # ROC curve visualization
    └── run_metadata.json    # Reproducibility information
```

### Model Configuration
- **Model Type:** Calibrated Logistic Regression
- **Preprocessing:** Median imputation + StandardScaler
- **Calibration:** Sigmoid calibration with 3-fold CV
- **Features:** 17 features
- **Random Seed:** 42
- **Training Date:** 2026-09-19T17:23:35.648610+00:00

---

## 4. TRAINING PIPELINE

### Training Script
**File:** `scripts/train_model.py`

### Training Process
1. Load manifest from `dataset/manifests/dataset.csv`
2. Validate labels (0=genuine, 1=manipulated)
3. Resolve image paths
4. Create groups from parent_id or source_id
5. Perform grouped stratified split (70% train, 15% val, 15% test)
6. Check for group leakage (raises error if detected)
7. Extract features through analysis pipeline
8. Train calibrated logistic regression
9. Evaluate on test set
10. Save model artifacts and metadata

### Data Leakage Prevention
**File:** `scripts/ml_common.py` (lines 56-89)
- Uses StratifiedGroupShuffleSplit
- Groups by parent_id/source_id/session_id
- Overlap detection between splits
- Raises ManifestError if leakage detected

---

## 5. EVALUATION PIPELINE

### Evaluation Script
**File:** `scripts/evaluate_model.py`

### Evaluation Metrics
- Accuracy
- Precision
- Recall
- F1 Score
- False Positive Rate
- ROC-AUC
- Brier Score
- Confusion Matrix

### Current Test Results
```json
{
  "test": {
    "count": 24,
    "accuracy": 0.75,
    "precision": 0.0,
    "recall": 0.0,
    "f1": 0.0,
    "false_positive_rate": 0.0,
    "confusion_matrix": [[18,0],[6,0]],
    "roc_auc": 0.8425925925925926
  }
}
```

**Problem:** Model predicts "genuine" for all test images (never predicts manipulation)

---

## 6. FORENSIC DETECTORS

### Detector Inventory
1. **Copy-Move** (`backend/forensic/copy_move.py`)
   - Algorithm: SIFT (primary) / ORB (fallback)
   - Verification: RANSAC affine transformation
   - Status: WORKING

2. **Local Anomaly** (`backend/forensic/local_anomaly.py`)
   - Algorithm: Patch-based robust z-score
   - Status: WORKING

3. **Compression** (`backend/forensic/compression.py`)
   - Algorithm: JPEG quality estimation + blockiness + resampling
   - Status: WORKING

4. **Timestamp** (`backend/forensic/timestamp.py`)
   - Algorithm: OCR with pytesseract
   - Status: BROKEN (tesseract not installed)

5. **Spatial** (`backend/forensic/spatial.py`)
   - Algorithm: Multi-detector spatial agreement
   - Status: WORKING

---

## 7. FEATURE EXTRACTION

### Feature Builder
**File:** `backend/features/feature_builder.py`

### Feature Schema (17 features)
1. copy_move_verified_matches
2. copy_move_inlier_ratio
3. copy_move_region_count
4. copy_move_region_area
5. patch_max_anomaly
6. patch_mean_anomaly
7. patch_anomaly_fraction
8. compression_score
9. resampling_score
10. blockiness
11. jpeg_quality
12. image_megapixels
13. bytes_per_pixel
14. spatial_iou
15. spatial_dice
16. natural_processing_similarity

### Context Fields (not used as features)
- metadata_available
- visible_timestamp_detected
- copy_move_status
- local_anomaly_status
- compression_status

### Missing Value Strategy
- NaN represents unavailable detector evidence
- Median imputation fitted on training data
- Context fields explicitly excluded from model features

---

## 8. CURRENT TEST RESULTS

### Backend Tests
**File:** `backend/tests/test_fusion_and_api.py`

**Results:** 31/31 tests passed

**Test Coverage:**
- Upload validation (7 tests)
- Metadata extraction (3 tests)
- Copy-move detection (3 tests)
- Local anomaly detection (2 tests)
- Compression detection (1 test)
- Feature builder (3 tests)
- Fusion model (3 tests)
- API endpoints (6 tests)
- End-to-end flow (1 test)

### Frontend Tests
**Status:** Cannot run (Node.js not available)

### CI Configuration
**File:** `.github/workflows/ci.yml`
- Platforms: Ubuntu, Windows
- Python versions: 3.10, 3.11, 3.12
- Node version: 20
- Frontend tests will fail (build environment broken)

---

## 9. CURRENT LIMITATIONS

### Technical Limitations
1. Frontend build environment broken (Node.js unavailable)
2. OCR support not installed (tesseract missing)
3. Natural processing library empty (0 entries)
4. Dependency conflicts in requirements.txt (pytest version incompatibility)

### Research Limitations
1. 100% synthetic training data (no real crop photographs)
2. Tiny dataset (72 images)
3. Poor model performance (0% precision/recall on test set)
4. Limited manipulation types (only copy-move and splicing)
5. No real-world validation
6. Thresholds not empirically validated

### Deployment Limitations
1. No authentication or rate limiting
2. No monitoring or logging
3. No containerization
4. No deployment scripts

---

## 10. ENVIRONMENT STATUS

### Python Environment
- Python 3.11.9
- scikit-learn 1.7.2 (upgraded from 1.9.0 to fix model loading)
- opencv-python-headless 5.0.0.93
- scikit-image 0.26.0
- Other dependencies: Mixed versions
- **Issue:** pytest version conflict (9.1.1 vs pytest-asyncio 0.25.3)

### Node.js Environment
- **Status:** Not available
- **Impact:** Cannot build or test frontend

### OCR Environment
- **Status:** tesseract binary not installed
- **Impact:** Timestamp detector non-functional

---

## 11. BASELINE ARTIFACTS

### Model Artifacts Preserved
- `models/fusion_model.joblib` - Current trained model
- `models/fusion-v1/` - Complete training run artifacts
- `models/natural_processing_library.json` - Empty (needs population)

### Dataset Artifacts Preserved
- `dataset/` - All 72 synthetic images
- `dataset/manifests/dataset.csv` - Dataset manifest
- `dataset/manifests/dataset.json` - Dataset metadata

### Test Artifacts Preserved
- `analysis.db` - SQLite database with test analyses
- `reports/` - Generated analysis reports
- `artifacts/` - Generated heatmaps and overlays

---

## 12. NEXT STEPS (PHASE 1)

1. **Dataset Validity Audit** - Comprehensive scientific audit of the 72-image dataset
2. **Model Failure Diagnosis** - Investigate 0% precision/recall root cause
3. **Environment Repair** - Fix dependency conflicts and frontend build
4. **Controlled Retraining** - If dataset is valid, retrain with proper methodology
5. **Dataset V2 Decision** - Determine if current dataset is sufficient or V2 required

---

**Baseline Established:** 2026-09-20  
**Purpose:** Establish clean baseline before Phase 1 dataset and model investigation
# Photocopy That Lied - Repository Audit Report

**Date**: 2026-09-21
**Purpose**: Assess existing components and identify prototype completion requirements

---

## ALREADY COMPLETE

### Dataset V2 ✅
- **Total records**: 3,895
- **Authentic**: 3,595
- **Manipulated**: 300 (75 each: copy-move, object-removal, object-insertion, splicing)
- **Source families with variants**: 602/1,000 (60.2%)
- **Splits**: train (2,805), validation (736), test (354)
- **Ground-truth masks**: 300/300 valid
- **Natural processing**: 1,125 records
- **Hard negatives**: 1,170 records
- **Location**: `dataset_v2/`

### Dataset Validation ✅
- Missing files: 0
- Corrupt files: 0
- Duplicate IDs: 0
- Source leakage: 0
- Donor leakage: 0
- Mask validation: PASS
- Anti-shortcut audit: PASS
- Reproducibility: PASS
- Tests: 63/63 PASS

### Forensic Detectors ✅
- **Copy-move**: `backend/forensic/copy_move.py` - SIFT/ORB, geometric verification, heatmap
- **Compression**: `backend/forensic/compression.py` - JPEG quality, blockiness, resampling
- **Local anomaly**: `backend/forensic/local_anomaly.py` - Patch-based anomaly detection
- **Spatial**: `backend/forensic/spatial.py` - Spatial combination, heatmap generation
- **Metadata**: `backend/forensic/metadata.py` - EXIF extraction
- **Timestamp**: `backend/forensic/timestamp.py` - Timestamp detection
- **Common**: `backend/forensic/common.py` - Shared utilities

### Feature Builder ✅
- **Location**: `backend/features/feature_builder.py`
- **Current features**: 16 forensic features
  - Copy-move: 4 features
  - Local anomaly: 3 features
  - Compression: 4 features
  - Spatial: 2 features
  - Natural processing: 1 feature
- **Status**: Functional, but needs extension for prototype

### Fusion Model Architecture ✅
- **Location**: `backend/fusion/model.py`
- **Architecture**: RandomForest/LogisticRegression with calibration
- **Pipeline**: impute → scale → classifier
- **Status**: Architecture functional, but trained on old dataset (dataset-synthetic-v1)

### Calibration ✅
- **Location**: `backend/calibration/natural_processing.py`
- **Status**: Functional, has library file (natural_processing_library_v2.json)

### Pipeline Orchestration ✅
- **Location**: `backend/pipeline/analysis.py`
- **Status**: End-to-end analysis orchestration functional
- **Capabilities**: Image validation, normalization, detector execution, feature building, fusion, heatmap generation, explanations

### API Endpoints ✅
- **Location**: `backend/api/analyze.py`
- **Endpoints**:
  - `POST /api/analyze` - Upload and analyze image
  - `GET /api/analysis/{analysis_id}` - Retrieve analysis
  - `GET /api/analyses` - List analyses
  - `GET /api/artifacts/{analysis_id}/{name}` - Retrieve artifacts
  - `GET /api/config` - Get configuration
- **Status**: Functional

### React Frontend ✅
- **Location**: `frontend/src/`
- **Pages**: Upload, Processing, Results
- **Status**: Functional with complete workflow

### Evidence Engine ✅
- **Location**: `backend/explanations/explanation_engine.py`
- **Status**: Functional explanation generation

### Heatmap Generation ✅
- **Location**: `backend/pipeline/analysis.py`
- **Status**: Functional forensic anomaly visualization

### Risk Band Calculation ✅
- **Location**: `backend/config.py`
- **Status**: Functional (low: <30, review: 30-60, high: >60)

### Manual QC Sample Preparation ✅
- **Location**: `scripts/prepare_qc_samples.py`, `docs/QC_SAMPLE_PATHS.txt`, `docs/DATASET_V2_MANUAL_QC_REPORT.md`
- **Samples**: 35 (5 per category: original, natural-processing, hard-negative, copy-move, removal, insertion, splicing)
- **Status**: All samples located and ready for visual review
- **Note**: Manual visual inspection is a human responsibility

---

## INCOMPLETE

### PRIORITY 1: Dataset V2 Data Loader ❌
- **Requirement**: Production-quality loader for `dataset_v2/metadata/manifest.jsonl`
- **Must load**: image, label, category, split, source_id, image_id, variant_id, manipulation_type, mask, manipulation_area_ratio, parameters
- **Must enforce**: Split isolation (train → training only, validation → validation only, test → test only)
- **Tests required**: Image loading, mask loading, metadata consistency, label consistency, split isolation, missing-file handling
- **Status**: NO OFFICIAL LOADER EXISTS

### PRIORITY 2: Extended Forensic Features ❌
- **Current**: 16 features (copy-move, local anomaly, compression, spatial, natural processing)
- **Missing**:
  - Noise residual statistics
  - Local noise variance
  - Noise inconsistency
  - RGB/channel statistics
  - Local color inconsistency
  - Chromatic noise statistics
  - Edge density
  - Edge consistency
  - High-frequency statistics
  - FFT/DCT-based statistics
  - High-frequency energy
  - Local frequency anomalies
  - Resampling indicators
- **Status**: Feature builder needs extension

### PRIORITY 3: Dataset V2-Trained Classifier ❌
- **Current**: Model trained on `dataset-synthetic-v1` (old synthetic dataset)
- **Requirement**: Train new classifier on Dataset V2
- **Models**: Start with Logistic Regression, then Random Forest if time permits
- **Pipeline**: Dataset V2 → Forensic Features → Preprocessing → Classifier → Manipulation Probability
- **Training**: Train only on training data, use validation for selection, keep test untouched
- **Status**: MUST RETRAIN ON DATASET V2

### PRIORITY 4: Model Evaluation on Dataset V2 ❌
- **Requirement**: Real evaluation metrics from Dataset V2 test set
- **Metrics**: Precision, Recall, F1, ROC-AUC, PR-AUC, Specificity, FPR, FNR, Confusion Matrix
- **Subset evaluation**: Original, Natural Processing, Hard Negative, Copy-Move, Removal, Insertion, Splicing
- **Status**: NO ACTUAL DATASET V2 METRICS EXIST

### PRIORITY 5: Demo Dataset for UI Testing ❌
- **Requirement**: Easy way to test UI with real Dataset V2 images
- **Minimum**: 1 original, 1 natural-processing, 1 hard-negative, 1 copy-move, 1 removal, 1 insertion, 1 splicing
- **Status**: NO DEMO DATASET EXISTS

---

## BROKEN

**None identified.** All existing components appear functional.

---

## REUSABLE

### Highly Reusable (Use As-Is)
- All forensic detectors (`backend/forensic/`)
- Feature builder architecture (`backend/features/feature_builder.py`)
- Fusion model architecture (`backend/fusion/model.py`)
- Calibration architecture (`backend/calibration/`)
- Pipeline orchestration (`backend/pipeline/analysis.py`)
- API endpoints (`backend/api/`)
- React frontend (`frontend/src/`)
- Evidence engine (`backend/explanations/`)
- Heatmap generation (`backend/pipeline/analysis.py`)
- Risk band calculation (`backend/config.py`)

### Reusable with Extension
- Feature builder: Add missing feature types
- Fusion model: Retrain on Dataset V2

---

## PROTOTYPE PLAN

### Phase 1: Dataset V2 Data Loader (PRIORITY 1)
1. Create `backend/data/dataset_v2_loader.py`
2. Implement manifest.jsonl loading
3. Implement portable image path resolution
4. Implement mask loading
5. Implement split isolation enforcement
6. Add loader tests
7. **Checkpoint**: `prototype-dataset-loader`

### Phase 2: Extended Forensic Features (PRIORITY 2)
1. Extend `backend/features/feature_builder.py`
2. Add noise statistics features
3. Add color statistics features
4. Add edge/texture features
5. Add frequency domain features
6. Add resampling indicators
7. Ensure no forbidden features (filename, directory, category, mask, label, source_id)
8. Add feature extraction tests
9. **Checkpoint**: `prototype-forensic-features`

### Phase 3: Dataset V2 Classifier Training (PRIORITY 3)
1. Create `scripts/train_dataset_v2_model.py`
2. Use data loader to load train/validation/test splits
3. Extract forensic features for all samples
4. Train Logistic Regression on training data
5. Tune hyperparameters on validation data
6. Train Random Forest if time permits
7. Evaluate on test set
8. Save model, feature config, preprocessing config, training metadata, metrics
9. **Checkpoint**: `prototype-classifier`

### Phase 4: Risk Scoring (PRIORITY 4)
1. Implement probability → risk score conversion (risk_score = probability × 100)
2. Use existing risk band calculation
3. Ensure configurable thresholds
4. **Checkpoint**: `prototype-risk-scoring`

### Phase 5: FastAPI Integration (PRIORITY 5)
1. Update `backend/fusion/predict.py` to load Dataset V2 model
2. Update model path configuration
3. Test API with new model
4. **Checkpoint**: `prototype-api`

### Phase 6: Demo Dataset (PRIORITY 6)
1. Create `demo/` directory
2. Copy 7 representative images from Dataset V2
3. Create simple demo script
4. **Checkpoint**: `prototype-demo-dataset`

### Phase 7: End-to-End Testing (PRIORITY 7)
1. Test backend: startup, model load, image acceptance, analysis completion, risk return, evidence return, heatmap return, error handling
2. Test frontend: startup, upload, analyze, loading state, result display, risk score, evidence, heatmap, errors
3. Test end-to-end: original, natural-processing, hard-negative, copy-move, removal, insertion, splicing
4. **Checkpoint**: `prototype-e2e-tested`

### Phase 8: Documentation (PRIORITY 8)
1. Create `docs/PROTOTYPE_REPORT.md`
2. Create `docs/PROTOTYPE_FINAL_STATUS.md`
3. Document architecture, dataset, features, model, training, evaluation, risk scoring, evidence, limitations
4. **Checkpoint**: `prototype-submission-ready`

---

## ESTIMATED REMAINING WORK

| Phase | Estimate | Notes |
|-------|----------|-------|
| Data Loader | 2-3 hours | Straightforward, just needs implementation |
| Extended Features | 3-4 hours | Add missing feature types, test thoroughly |
| Classifier Training | 2-3 hours | Logistic Regression is fast, Random Forest optional |
| Risk Scoring | 0.5 hours | Simple conversion, already have risk bands |
| API Integration | 1 hour | Update model path, test |
| Demo Dataset | 0.5 hours | Copy files, create simple script |
| End-to-End Testing | 2-3 hours | Comprehensive testing of all components |
| Documentation | 1-2 hours | Write reports based on actual results |
| **Total** | **12-17 hours** | Can be compressed by skipping Random Forest if needed |

---

## CRITICAL PATH

The minimum working path (if time becomes very limited):

1. **Dataset V2 Data Loader** (REQUIRED)
2. **Extended Forensic Features** (REQUIRED - at minimum, ensure current features work)
3. **Dataset V2 Classifier** (REQUIRED - Logistic Regression only)
4. **Risk Scoring** (REQUIRED - simple conversion)
5. **API Integration** (REQUIRED - update model path)
6. **End-to-End Testing** (REQUIRED - verify it works)
7. **Documentation** (REQUIRED - basic report)

**Estimated minimum: 8-10 hours**

---

## NEXT ACTION

**Immediately begin Phase 1: Dataset V2 Data Loader**

This is the highest priority incomplete component and blocks all subsequent work.

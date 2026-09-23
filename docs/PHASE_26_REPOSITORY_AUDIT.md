# Phase 26: Manual QC + Repository/Model Development Audit

## Executive Summary

This audit reviews the repository structure, existing components, and readiness for Phase 27-41 model development. The audit identifies reusable components, missing components, and provides recommendations for proceeding with model development.

## Repository Structure

### Dataset V2 Status
- **Total records**: 3,895
- **Authentic**: 3,595 (92.3%)
- **Manipulated**: 300 (7.7%)
- **Source families with variants**: 602/1,000 (60.2%)
- **Splits**: train (2,805), validation (736), test (354)
- **Validation status**: All checks PASS
- **Manual QC**: Sample generated, PENDING REVIEW

### Existing Forensic Components

#### 1. Forensic Detectors (backend/forensic/)
**Status**: Existing and functional

**copy_move.py**
- Keypoint-based copy-move detection
- SIFT/ORB fallback
- Geometric verification with RANSAC
- Shift-vector clustering
- Status: REUSABLE for Phase 28

**compression.py**
- JPEG quality estimation
- Blockiness detection
- Resampling detection
- Status: REUSABLE for Phase 28

**local_anomaly.py**
- Patch-based anomaly detection
- Statistical outlier detection
- Status: REUSABLE for Phase 28

**spatial.py**
- Spatial combination of detector results
- Heatmap generation
- Status: REUSABLE for Phase 28

**metadata.py**
- EXIF metadata extraction
- Status: REUSABLE for Phase 28

**timestamp.py**
- Timestamp detection
- Status: REUSABLE for Phase 28

**common.py**
- Common utilities
- Status: REUSABLE

#### 2. Feature Builder (backend/features/)
**Status**: Existing but limited to current features

**feature_builder.py**
- 16 features: copy_move (4), local_anomaly (3), compression (4), spatial (2), natural_processing (1)
- Excludes filename, directory, category, manipulation_type, mask, label, source_id
- Status: EXTENSIBLE for Phase 28

**Current Feature Set**:
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

**Missing Features for Phase 28**:
- Noise residual statistics
- Local noise variance
- Noise inconsistency
- Channel statistics
- Local color consistency
- Chromatic noise statistics
- Edge density
- Edge consistency
- High-frequency statistics
- FFT/DCT-based statistics
- High-frequency energy
- Local frequency anomalies

#### 3. Fusion Model (backend/fusion/)
**Status**: Existing but trained on wrong dataset

**model.py**
- RandomForest/LogisticRegression with calibration
- Pipeline: impute → scale → classifier
- Status: ARCHITECTURE REUSABLE, NEEDS RETRAINING on Dataset V2

**predict.py**
- Prediction interface
- Status: REUSABLE

**Current Model Metadata**:
- dataset_version: "dataset-synthetic-v1" (NOT Dataset V2)
- model_version: "fusion-v1"
- feature_version: "features-v1"
- Status: MUST RETRAIN on Dataset V2

#### 4. Calibration (backend/calibration/)
**Status**: Existing but Dataset V2-specific library needed

**natural_processing.py**
- Natural processing library for calibration
- K-nearest neighbor similarity
- Status: ARCHITECTURE REUSABLE, NEEDS Dataset V2 LIBRARY

**coverage.py**
- Data coverage estimation
- Status: REUSABLE

#### 5. Pipeline (backend/pipeline/)
**Status**: Existing and functional

**analysis.py**
- End-to-end analysis orchestration
- Detector execution
- Feature building
- Fusion prediction
- Status: REUSABLE for Phase 39

**validator.py**
- Image validation
- Status: REUSABLE

**provenance.py**
- Provenance tracking
- Status: REUSABLE

### Dataset V2 Components

**Dataset Structure**:
- dataset_v2/metadata/manifest.jsonl - 3,895 records
- dataset_v2/metadata/schema.json - Metadata schema
- dataset_v2/splits/train.json - 700 sources
- dataset_v2/splits/validation.json - 150 sources
- dataset_v2/splits/test.json - 150 sources
- dataset_v2/splits/splits.json - Combined split definition
- dataset_v2/variants/ - Generated variants and masks

**Schema Fields**:
- image_id, source_id, label, category
- manipulation_type, parent_image_id, parent_source_id
- variant_id, mask_path, mask_id
- parameters, seed, width, height, format, color_mode
- generation_method, processing_operations
- metadata_available, sha256, dataset_version

**Status**: READY for Phase 27 data loader

### Existing Tests

**Backend Tests** (backend/tests/):
- test_dataset_v2.py - Dataset V2 schema and structure tests
- test_fusion_and_api.py - Fusion model and API tests
- test_import_deepweeds.py - DeepWeeds import tests
- Status: 63/63 PASS

**Status**: TEST INFRASTRUCTURE REUSABLE

## Missing Components

### Critical Missing Components

1. **Dataset V2 Data Loader** (Phase 27)
   - Load manifest.jsonl
   - Resolve portable image paths
   - Load masks when available
   - Preserve source_id, image_id, variant_id
   - Preserve category, manipulation_type, split
   - Preserve parameters, manipulation_area_ratio
   - Preserve labels
   - Enforce split isolation
   - Status: MUST IMPLEMENT

2. **Comprehensive Forensic Feature Extraction** (Phase 28)
   - Extend existing 16 features
   - Add noise statistics
   - Add color statistics
   - Add edge statistics
   - Add frequency domain statistics
   - Status: MUST IMPLEMENT

3. **Classical Baseline Models** (Phase 29)
   - Logistic Regression
   - Random Forest
   - Gradient Boosting
   - Train on Dataset V2
   - Status: MUST IMPLEMENT

4. **CNN Baseline** (Phase 30)
   - ResNet/EfficientNet backbone
   - Binary classification head
   - GPU support
   - Checkpoint saving
   - Early stopping
   - Status: MUST IMPLEMENT

5. **Localization Model** (Phase 31)
   - U-Net or encoder-decoder
   - Pixel-level manipulation probability map
   - IoU, Dice evaluation
   - Status: MUST IMPLEMENT

6. **Hybrid Model** (Phase 32)
   - CNN + forensic features fusion
   - Architecture: CNN features + forensic features → fusion → classification + localization
   - Status: MUST IMPLEMENT

7. **Risk Scoring** (Phase 33)
   - 0-100 manipulation risk score
   - Decision bands (Low/Review/High)
   - Threshold determination from validation data
   - Status: MUST IMPLEMENT

8. **Explainability** (Phase 34)
   - Evidence explanation generation
   - Confidence reporting
   - Heatmap interpretation
   - Status: MUST IMPLEMENT

9. **Robustness Testing** (Phase 35)
   - JPEG recompression robustness
   - Resize robustness
   - Brightness/contrast changes
   - Format conversion
   - Status: MUST IMPLEMENT

10. **Generalization Testing** (Phase 36)
    - External/holdout evaluation set
    - Generalization performance measurement
    - Status: MUST IMPLEMENT

11. **Experiment Tracking** (Phase 37)
    - Experiment ID, timestamp
    - Dataset version, split information
    - Random seed, architecture, hyperparameters
    - Feature configuration
    - Training duration, hardware
    - Checkpoint, metrics
    - Status: MUST IMPLEMENT

12. **Model Evaluation Suite** (Phase 38)
    - F1, ROC-AUC, PR-AUC
    - Precision, recall, FPR
    - Confusion matrix
    - Subset-specific metrics
    - Localization metrics
    - Status: MUST IMPLEMENT

13. **Integration Testing** (Phase 40)
    - Backend tests
    - Frontend tests
    - Dataset tests
    - Model tests
    - Inference tests
    - API tests
    - Localization tests
    - Reproducibility tests
    - Status: MUST IMPLEMENT

14. **Documentation** (Phase 41)
    - Model development report
    - Model limitations document
    - Status: MUST IMPLEMENT

## Manual QC Status

### QC Sample Generated
- 5 samples per category (20 total)
- Categories: original, natural-processing, hard-negative, copy-move, object-removal, object-insertion, splicing
- Status: GENERATED, PENDING MANUAL REVIEW

### Required QC Checks
For every manipulated sample inspect:
- Original → Manipulated → Ground-truth Mask
- Verify manipulation is actually present
- Verify manipulation looks plausible
- Verify mask covers manipulated region
- Verify mask does not incorrectly cover unrelated regions
- Verify metadata is correct
- Verify category is correct
- Verify label is correct

### Current Status
- QC sample file: reports/PHASE_21_MANUAL_QC_SAMPLE.json (ignored by git)
- QC workflow: CREATED
- Manual review: NOT YET PERFORMED
- QC report: NOT YET CREATED

### Recommendation
Before proceeding to Phase 27, perform manual QC review to:
1. Verify dataset quality
2. Identify any generation issues
3. Confirm mask accuracy
4. Document QC findings
5. Create DATASET_V2_MANUAL_QC_REPORT.md

## Phase-by-Phase Implementation Plan

### Phase 26: Manual QC + Repository Audit (CURRENT)
- [x] Repository structure audit
- [x] Existing component inventory
- [x] Missing component identification
- [x] Reusable component catalog
- [ ] Manual QC review
- [ ] DATASET_V2_MANUAL_QC_REPORT.md creation

### Phase 27: Data Loader
- [ ] Implement Dataset V2 data loader
- [ ] Load manifest.jsonl
- [ ] Resolve portable image paths
- [ ] Load masks when available
- [ ] Preserve all required metadata
- [ ] Enforce split isolation
- [ ] Add data loader tests
- [ ] Document data loader

### Phase 28: Forensic Feature Extraction
- [ ] Extend existing feature builder
- [ ] Add noise statistics features
- [ ] Add color statistics features
- [ ] Add edge statistics features
- [ ] Add frequency domain features
- [ ] Ensure no forbidden features
- [ ] Add feature extraction tests
- [ ] Document feature engineering

### Phase 29: Classical Baseline
- [ ] Implement Logistic Regression baseline
- [ ] Implement Random Forest baseline
- [ ] Implement Gradient Boosting baseline
- [ ] Train on Dataset V2 train split
- [ ] Hyperparameter selection on validation
- [ ] Final evaluation on test
- [ ] Report comprehensive metrics
- [ ] Document baseline results

### Phase 30: CNN Baseline
- [ ] Implement ResNet/EfficientNet backbone
- [ ] Binary classification head
- [ ] GPU support implementation
- [ ] Deterministic seed
- [ ] Checkpoint saving
- [ ] Early stopping
- [ ] Handle class imbalance
- [ ] Compare with classical baseline
- [ ] Document CNN results

### Phase 31: Localization Model
- [ ] Implement U-Net or encoder-decoder
- [ ] Pixel-level manipulation probability map
- [ ] IoU, Dice evaluation
- [ ] Pixel precision/recall
- [ ] Evaluate by manipulation type
- [ ] Evaluate by area range
- [ ] Document localization results

### Phase 32: Hybrid Model
- [ ] Implement CNN + forensic features fusion
- [ ] Fusion layer architecture
- [ ] Classification + localization heads
- [ ] Compare with independent baselines
- [ ] Document hybrid results

### Phase 33: Risk Scoring
- [ ] Implement 0-100 risk score
- [ ] Determine decision bands from validation
- [ ] Document threshold methodology
- [ ] Implement confidence scoring
- [ ] Document risk scoring

### Phase 34: Explainability
- [ ] Implement evidence explanation
- [ ] Implement confidence reporting
- [ ] Implement heatmap interpretation
- [ ] Ensure explanations match features
- [ ] Document explainability

### Phase 35: Robustness Testing
- [ ] Test JPEG recompression robustness
- [ ] Test resize robustness
- [ ] Test brightness/contrast changes
- [ ] Test format conversion
- [ ] Report false positives by subset
- [ ] Document robustness results

### Phase 36: Generalization Testing
- [ ] Create external/holdout set
- [ ] Evaluate generalization performance
- [ ] Distinguish from Dataset V2 test
- [ ] Document generalization results

### Phase 37: Experiment Tracking
- [ ] Implement experiment tracking
- [ ] Record all experiment metadata
- [ ] Ensure reproducibility
- [ ] Document tracking system

### Phase 38: Final Evaluation
- [ ] Create comparison table
- [ ] Report all metrics
- [ ] Explain trade-offs
- [ ] Document final evaluation

### Phase 39: Application Integration
- [ ] Integrate models into application
- [ ] Preserve existing architecture
- [ ] Test integration
- [ ] Document integration

### Phase 40: Final Testing
- [ ] Run all test suites
- [ ] Test edge cases
- [ ] Test all manipulation types
- [ ] Document test results

### Phase 41: Documentation
- [ ] Create MODEL_DEVELOPMENT_REPORT.md
- [ ] Create MODEL_LIMITATIONS.md
- [ ] Document all phases
- [ ] Document limitations
- [ ] Document future improvements

## Recommendations

### Immediate Actions
1. **Complete Manual QC Review** (Phase 26)
   - Review 20 QC samples
   - Document findings
   - Create DATASET_V2_MANUAL_QC_REPORT.md
   - Address any issues found

2. **Proceed to Phase 27 After QC Approval**
   - Implement Dataset V2 data loader
   - Ensure split isolation
   - Add comprehensive tests

### Architecture Decisions
1. **Reuse Existing Components**
   - Forensic detectors: REUSE
   - Feature builder: EXTEND
   - Fusion model architecture: REUSE (retrain)
   - Pipeline: REUSE
   - Tests: EXTEND

2. **Implement Missing Components**
   - Data loader: NEW
   - Extended features: NEW
   - CNN baseline: NEW
   - Localization model: NEW
   - Hybrid model: NEW
   - Risk scoring: NEW
   - Explainability: NEW
   - Robustness testing: NEW
   - Generalization testing: NEW
   - Experiment tracking: NEW

### Risk Mitigation
1. **Dataset Quality Risk**
   - Mitigation: Complete manual QC before training
   - Mitigation: Verify mask accuracy

2. **Split Leakage Risk**
   - Mitigation: Enforce split isolation in data loader
   - Mitigation: Add split isolation tests

3. **Feature Leakage Risk**
   - Mitigation: Ensure no forbidden features
   - Mitigation: Add feature leakage tests

4. **Overfitting Risk**
   - Mitigation: Use proper train/validation/test split
   - Mitigation: Hyperparameter selection on validation only
   - Mitigation: Final evaluation on test only

5. **Class Imbalance Risk**
   - Mitigation: Use class weighting
   - Mitigation: Use appropriate sampling
   - Mitigation: Report PR-AUC, not just accuracy

## Conclusion

The repository has a solid foundation with existing forensic detectors, feature builders, and pipeline infrastructure. The main gaps are:

1. **Dataset V2-specific data loader** - MUST IMPLEMENT
2. **Extended forensic features** - MUST IMPLEMENT
3. **Model baselines (classical, CNN, localization, hybrid)** - MUST IMPLEMENT
4. **Risk scoring and explainability** - MUST IMPLEMENT
5. **Robustness and generalization testing** - MUST IMPLEMENT
6. **Comprehensive documentation** - MUST IMPLEMENT

**Recommendation**: Complete manual QC review (Phase 26) before proceeding to Phase 27. After QC approval, proceed phase-by-phase through Phases 27-41, implementing missing components while reusing existing infrastructure.

**Status**: PHASE 26 IN PROGRESS - WAITING FOR MANUAL QC REVIEW

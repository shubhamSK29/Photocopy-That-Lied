# Dataset V2 Manual Quality Control Report

## QC Summary

**Status**: PENDING MANUAL REVIEW

**QC Date**: 2026-09-21

**Dataset Version**: dataset-real-v1

**Total Records**: 3,895

**QC Sample Size**: 35 (5 originals + 5 natural-processing + 5 hard-negative + 20 manipulated)

**Reviewer**: TBD

## QC Methodology

### Sample Selection
- 5 original images
- 5 natural-processing images
- 5 hard-negative images
- 5 copy-move images
- 5 object-removal images
- 5 object-insertion images
- 5 splicing images

### QC Criteria

#### For All Images
- [ ] Image loads correctly
- [ ] Image quality is acceptable
- [ ] Image looks realistic for category

#### For Manipulated Images
- [ ] Original → Manipulated → Mask inspection performed
- [ ] Manipulation is actually present
- [ ] Manipulation looks plausible
- [ ] Mask covers the manipulated region
- [ ] Mask does not incorrectly cover unrelated regions
- [ ] Metadata is correct
- [ ] Category is correct
- [ ] Label is correct

## QC Sample Results

### Original Images (5 samples)

| Image ID | Path | Quality | Plausible | Notes | Status |
|----------|------|---------|-----------|-------|--------|
| SRC_DW_42B3777910D24768 | dataset_v2/sources/deepweeds_raw/images/20171109-193756-1.jpg | TBD | TBD | TBD | PENDING |
| SRC_DW_9CFFFFF1744F8A16 | dataset_v2/sources/deepweeds_raw/images/20170913-124937-1.jpg | TBD | TBD | TBD | PENDING |
| SRC_DW_CEA321004028901C | dataset_v2/sources/deepweeds_raw/images/20171205-124539-2.jpg | TBD | TBD | TBD | PENDING |
| SRC_DW_8786F0C0FBF0D0BB | dataset_v2/sources/deepweeds_raw/images/20171220-094530-2.jpg | TBD | TBD | TBD | PENDING |
| SRC_DW_3A1D7141FC2861BA | dataset_v2/sources/deepweeds_raw/images/20170913-124346-1.jpg | TBD | TBD | TBD | PENDING |

### Natural-Processing Images (5 samples)

| Image ID | Path | Operation | Quality | Plausible | Notes | Status |
|----------|------|-----------|---------|-----------|-------|--------|
| SRC_DW_D4C6276E8DC7CA74_NP_GAMMA_72f2695e95d7f3f5 | dataset_v2/variants/natural_processing/SRC_DW_D4C6276E8DC7CA74_NP_GAMMA_72f2695e95d7f3f5.jpg | gamma | TBD | TBD | TBD | PENDING |
| SRC_DW_42B5E565AE51D6DC_NP_DENOISE_535b80b54a2963a4 | dataset_v2/variants/natural_processing/SRC_DW_42B5E565AE51D6DC_NP_DENOISE_535b80b54a2963a4.jpg | denoise | TBD | TBD | TBD | PENDING |
| SRC_DW_7CCEE6E0F6EDB22E_NP_GAMMA_8240d187434605c3 | dataset_v2/variants/natural_processing/SRC_DW_7CCEE6E0F6EDB22E_NP_GAMMA_8240d187434605c3.jpg | gamma | TBD | TBD | TBD | PENDING |
| SRC_DW_4A4AC282EF66C0A6_NP_SHARPEN_d2c9e9d8a3b72934 | dataset_v2/variants/natural_processing/SRC_DW_4A4AC282EF66C0A6_NP_SHARPEN_d2c9e9d8a3b72934.jpg | sharpen | TBD | TBD | TBD | PENDING |
| SRC_DW_D7DDC469324C5BFD_NP_FORMAT_CONVERSION_32f4d8727b4e4ffc | dataset_v2/variants/natural_processing/SRC_DW_D7DDC469324C5BFD_NP_FORMAT_CONVERSION_32f4d8727b4e4ffc.jpg | format_conversion | TBD | TBD | TBD | PENDING |

### Hard-Negative Images (5 samples)

| Image ID | Path | Operation | Quality | Plausible | Notes | Status |
|----------|------|-----------|---------|-----------|-------|--------|
| SRC_DW_03E50FF738AA1B03_HN_JPEG_RECOMPRESSION_1d41219b05c78836 | dataset_v2/variants/hard_negative/SRC_DW_03E50FF738AA1B03_HN_JPEG_RECOMPRESSION_1d41219b05c78836.jpg | jpeg_recompression | TBD | TBD | TBD | PENDING |
| SRC_DW_A86935E0145BA56B_HN_GAMMA_64c5a5c6de6249be | dataset_v2/variants/hard_negative/SRC_DW_A86935E0145BA56B_HN_GAMMA_64c5a5c6de6249be.jpg | gamma | TBD | TBD | TBD | PENDING |
| SRC_DW_78BD3C1E15A20062_HN_JPEG_RECOMPRESSION_086d1670bc061e4f | dataset_v2/variants/hard_negative/SRC_DW_78BD3C1E15A20062_HN_JPEG_RECOMPRESSION_086d1670bc061e4f.jpg | jpeg_recompression | TBD | TBD | TBD | PENDING |
| SRC_DW_9A14DBDF719D4430_HN_DENOISE_002919e35fb8de27 | dataset_v2/variants/hard_negative/SRC_DW_9A14DBDF719D4430_HN_DENOISE_002919e35fb8de27.jpg | denoise | TBD | TBD | TBD | PENDING |
| SRC_DW_9A14DBDF719D4430_HN_RESIZE_f4c7998b154e8df1 | dataset_v2/variants/hard_negative/SRC_DW_9A14DBDF719D4430_HN_RESIZE_f4c7998b154e8df1.jpg | resize | TBD | TBD | TBD | PENDING |

### Manipulated Images (20 samples - 5 per type)

#### Copy-Move (5 samples)

| Image ID | Original | Manipulated | Mask | Area Ratio | Manipulation Present | Plausible | Mask Accurate | Notes | Status |
|----------|---------|------------|------|------------|---------------------|-----------|---------------|-------|--------|
| SRC_DW_AFB187CC4AA4C45C_M_COPY_MOVE_ab439a585d7f3df1 | dataset_v2/sources/deepweeds_raw/images/20170718-132127-2.jpg | dataset_v2/variants/manipulated/SRC_DW_AFB187CC4AA4C45C_M_COPY_MOVE_ab439a585d7f3df1.jpg | dataset_v2/variants/masks/SRC_DW_AFB187CC4AA4C45C_M_COPY_MOVE_ab439a585d7f3df1_mask.png | 0.0625 | TBD | TBD | TBD | TBD | PENDING |
| SRC_DW_D935BF546A6E6716_M_COPY_MOVE_06a86bdbb9c082c1 | dataset_v2/sources/deepweeds_raw/images/20170920-191121-1.jpg | dataset_v2/variants/manipulated/SRC_DW_D935BF546A6E6716_M_COPY_MOVE_06a86bdbb9c082c1.jpg | dataset_v2/variants/masks/SRC_DW_D935BF546A6E6716_M_COPY_MOVE_06a86bdbb9c082c1_mask.png | 0.0015 | TBD | TBD | TBD | TBD | PENDING |
| SRC_DW_E33682417B480556_M_COPY_MOVE_00f0655d5ff27bb9 | dataset_v2/sources/deepweeds_raw/images/20180105-092349-2.jpg | dataset_v2/variants/manipulated/SRC_DW_E33682417B480556_M_COPY_MOVE_00f0655d5ff27bb9.jpg | dataset_v2/variants/masks/SRC_DW_E33682417B480556_M_COPY_MOVE_00f0655d5ff27bb9_mask.png | 0.0111 | TBD | TBD | TBD | TBD | PENDING |
| SRC_DW_742D7258F9785FFA_M_COPY_MOVE_e1ff951bf4c3bbdb | dataset_v2/sources/deepweeds_raw/images/20171109-093041-2.jpg | dataset_v2/variants/manipulated/SRC_DW_742D7258F9785FFA_M_COPY_MOVE_e1ff951bf4c3bbdb.jpg | dataset_v2/variants/masks/SRC_DW_742D7258F9785FFA_M_COPY_MOVE_e1ff951bf4c3bbdb_mask.png | 0.0257 | TBD | TBD | TBD | TBD | PENDING |
| SRC_DW_33E8D823F87A94AB_M_COPY_MOVE_8904192025bd498e | dataset_v2/sources/deepweeds_raw/images/20171113-133259-3.jpg | dataset_v2/variants/manipulated/SRC_DW_33E8D823F87A94AB_M_COPY_MOVE_8904192025bd498e.jpg | dataset_v2/variants/masks/SRC_DW_33E8D823F87A94AB_M_COPY_MOVE_8904192025bd498e_mask.png | 0.0881 | TBD | TBD | TBD | TBD | PENDING |

#### Object Removal (5 samples)

| Image ID | Original | Manipulated | Mask | Area Ratio | Manipulation Present | Plausible | Mask Accurate | Notes | Status |
|----------|---------|------------|------|------------|---------------------|-----------|---------------|-------|--------|
| SRC_DW_6C1F002ABF308E01_M_OBJECT_REMOVAL_d2a6018ec3c5c27c | dataset_v2/sources/deepweeds_raw/images/20170727-150146-3.jpg | dataset_v2/variants/manipulated/SRC_DW_6C1F002ABF308E01_M_OBJECT_REMOVAL_d2a6018ec3c5c27c.jpg | dataset_v2/variants/masks/SRC_DW_6C1F002ABF308E01_M_OBJECT_REMOVAL_d2a6018ec3c5c27c_mask.png | 0.0061 | TBD | TBD | TBD | TBD | PENDING |
| SRC_DW_41F23A41D7645180_M_OBJECT_REMOVAL_53c274ea75a3a20c | dataset_v2/sources/deepweeds_raw/images/20180322-103028-1.jpg | dataset_v2/variants/manipulated/SRC_DW_41F23A41D7645180_M_OBJECT_REMOVAL_53c274ea75a3a20c.jpg | dataset_v2/variants/masks/SRC_DW_41F23A41D7645180_M_OBJECT_REMOVAL_53c274ea75a3a20c_mask.png | 0.0137 | TBD | TBD | TBD | TBD | PENDING |
| SRC_DW_FEC420CB9A8BB7A1_M_OBJECT_REMOVAL_ddec50b98a1c6fdb | dataset_v2/sources/deepweeds_raw/images/20180119-110921-1.jpg | dataset_v2/variants/manipulated/SRC_DW_FEC420CB9A8BB7A1_M_OBJECT_REMOVAL_ddec50b98a1c6fdb.jpg | dataset_v2/variants/masks/SRC_DW_FEC420CB9A8BB7A1_M_OBJECT_REMOVAL_ddec50b98a1c6fdb_mask.png | 0.0625 | TBD | TBD | TBD | TBD | PENDING |
| SRC_DW_742D7258F9785FFA_M_OBJECT_REMOVAL_c3eaa7781cf51003 | dataset_v2/sources/deepweeds_raw/images/20171109-093041-2.jpg | dataset_v2/variants/manipulated/SRC_DW_742D7258F9785FFA_M_OBJECT_REMOVAL_c3eaa7781cf51003.jpg | dataset_v2/variants/masks/SRC_DW_742D7258F9785FFA_M_OBJECT_REMOVAL_c3eaa7781cf51003_mask.png | 0.0625 | TBD | TBD | TBD | TBD | PENDING |
| SRC_DW_0E2CF3CBC45332F1_M_OBJECT_REMOVAL_b006dc3977fadf57 | dataset_v2/sources/deepweeds_raw/images/20170610-122424-0.jpg | dataset_v2/variants/manipulated/SRC_DW_0E2CF3CBC45332F1_M_OBJECT_REMOVAL_b006dc3977fad57.jpg | dataset_v2/variants/masks/SRC_DW_0E2CF3CBC45332F1_M_OBJECT_REMOVAL_b006dc3977fad57_mask.png | 0.0397 | TBD | TBD | TBD | TBD | PENDING |

#### Object Insertion (5 samples)

| Image ID | Original | Manipulated | Mask | Area Ratio | Manipulation Present | Plausible | Mask Accurate | Notes | Status |
|----------|---------|------------|------|------------|---------------------|-----------|---------------|-------|--------|
| SRC_DW_D35996DEA6907BC8_M_OBJECT_INSERTION_03cea4b426335115 | dataset_v2/sources/deepweeds_raw/images/20171102-102154-1.jpg | dataset_v2/variants/manipulated/SRC_DW_D35996DEA6907BC8_M_OBJECT_INSERTION_03cea4b426335115.jpg | dataset_v2/variants/masks/SRC_DW_D35996DEA6907BC8_M_OBJECT_INSERTION_03cea4b426335115_mask.png | 0.0665 | TBD | TBD | TBD | TBD | PENDING |
| SRC_DW_A75C10B172DBD748_M_OBJECT_INSERTION_c542063e388d4cef | dataset_v2/sources/deepweeds_raw/images/20171220-084200-2.jpg | dataset_v2/variants/manipulated/SRC_DW_A75C10B172DBD748_M_OBJECT_INSERTION_c542063e388d4cef.jpg | dataset_v2/variants/masks/SRC_DW_A75C10B172DBD748_M_OBJECT_INSERTION_c542063e388d4cef_mask.png | 0.0257 | TBD | TBD | TBD | TBD | PENDING |
| SRC_DW_143EC9C09AEA746D_M_OBJECT_INSERTION_77d61ed0532fea87 | dataset_v2/sources/deepweeds_raw/images/20170727-171655-1.jpg | dataset_v2/variants/manipulated/SRC_DW_143EC9C09AEA746D_M_OBJECT_INSERTION_77d61ed0532fea87.jpg | dataset_v2/variants/masks/SRC_DW_143EC9C09AEA746D_M_OBJECT_INSERTION_77d61ed0532fea87_mask.png | 0.3619 | TBD | TBD | TBD | TBD | PENDING |
| SRC_DW_E09E0E5BE5C4A5D4_M_OBJECT_INSERTION_8db93783930ef91b | dataset_v2/sources/deepweeds_raw/images/20170718-132427-2.jpg | dataset_v2/variants/manipulated/SRC_DW_E09E0E5BE5C4A5D4_M_OBJECT_INSERTION_8db93783930ef91b.jpg | dataset_v2/variants/masks/SRC_DW_E09E0E5BE5C4A5D4_M_OBJECT_INSERTION_8db93783930ef91b_mask.png | 0.0309 | TBD | TBD | TBD | TBD | PENDING |
| SRC_DW_5848622ADA5BFA07_M_OBJECT_INSERTION_0d8231fcfcc56ca4 | dataset_v2/sources/deepweeds_raw/images/20171205-124014-2.jpg | dataset_v2/variants/manipulated/SRC_DW_5848622ADA5BFA07_M_OBJECT_INSERTION_0d8231fcfcc56ca4.jpg | dataset_v2/variants/masks/SRC_DW_5848622ADA5BFA07_M_OBJECT_INSERTION_0d8231fcfcc56ca4_mask.png | 0.0137 | TBD | TBD | TBD | TBD | PENDING |

#### Splicing (5 samples)

| Image ID | Original | Manipulated | Mask | Area Ratio | Manipulation Present | Plausible | Mask Accurate | Notes | Status |
|----------|---------|------------|------|------------|---------------------|-----------|---------------|-------|--------|
| SRC_DW_8287B54F129B68F1_M_SPLICING_2a0effabd2c0e652 | dataset_v2/sources/deepweeds_raw/images/20180109-071852-2.jpg | dataset_v2/variants/manipulated/SRC_DW_8287B54F129B68F1_M_SPLICING_2a0effabd2c0e652.jpg | dataset_v2/variants/masks/SRC_DW_8287B54F129B68F1_M_SPLICING_2a0effabd2c0e652_mask.png | 0.0095 | TBD | TBD | TBD | TBD | PENDING |
| SRC_DW_A75C10B172DBD748_M_SPLICING_d4ca004198474e9c | dataset_v2/sources/deepweeds_raw/images/20171220-084200-2.jpg | dataset_v2/variants/manipulated/SRC_DW_A75C10B172DBD748_M_SPLICING_d4ca004198474e9c.jpg | dataset_v2/variants/masks/SRC_DW_A75C10B172DBD748_M_SPLICING_d4ca004198474e9c_mask.png | 0.0095 | TBD | TBD | TBD | TBD | PENDING |
| SRC_DW_E2E45BB672622C23_M_SPLICING_d1c3abdb2ec5518b | dataset_v2/sources/deepweeds_raw/images/20170501-144625-0.jpg | dataset_v2/variants/manipulated/SRC_DW_E2E45BB672622C23_M_SPLICING_d1c3abdb2ec5518b.jpg | dataset_v2/variants/masks/SRC_DW_E2E45BB672622C23_M_SPLICING_d1c3abdb2ec5518b_mask.png | 0.0095 | TBD | TBD | TBD | TBD | PENDING |
| SRC_DW_CE0A4B01E1A091FC_M_SPLICING_b40184593593ac6a | dataset_v2/sources/deepweeds_raw/images/20171113-101323-0.jpg | dataset_v2/variants/manipulated/SRC_DW_CE0A4B01E1A091FC_M_SPLICING_b40184593593ac6a.jpg | dataset_v2/variants/masks/SRC_DW_CE0A4B01E1A091FC_M_SPLICING_b40184593593ac6a_mask.png | 0.0095 | TBD | TBD | TBD | TBD | PENDING |
| SRC_DW_228A9A730BEC0AB6_M_SPLICING_2e0ae4689be44cfd | dataset_v2/sources/deepweeds_raw/images/20170727-155232-3.jpg | dataset_v2/variants/manipulated/SRC_DW_228A9A730BEC0AB6_M_SPLICING_2e0ae4689be44cfd.jpg | dataset_v2/variants/masks/SRC_DW_228A9A730BEC0AB6_M_SPLICING_2e0ae4689be44cfd_mask.png | 0.0220 | TBD | TBD | TBD | TBD | PENDING |

## Detailed QC Instructions

### For Original Images
1. Locate image in: `dataset_v2/sources/deepweeds_raw/images/{filename}.jpg`
2. Open image and verify:
   - Image loads without corruption
   - Image quality is acceptable (not blurry, not too dark/light)
   - Image looks like a genuine crop photograph
3. Record findings in table above

### For Natural-Processing Images
1. Locate image in: `dataset_v2/variants/natural_processing/{image_id}.jpg`
2. Open image and verify:
   - Image loads without corruption
   - Processing operation is visible but looks legitimate
   - No obvious manipulation artifacts
   - Processing parameters appear realistic
3. Record findings in table above

### For Hard-Negative Images
1. Locate image in: `dataset_v2/variants/hard_negative/{image_id}.jpg`
2. Open image and verify:
   - Image loads without corruption
   - Processing is aggressive but legitimate
   - No actual content manipulation
   - Strong forensic artifacts may be present
3. Record findings in table above

### For Manipulated Images
1. Locate original in: `dataset_v2/sources/deepweeds_raw/images/{filename}.jpg`
2. Locate manipulated in: `dataset_v2/variants/manipulated/{image_id}.jpg`
3. Locate mask in: `dataset_v2/variants/masks/{image_id}_mask.png`
4. Side-by-side inspection:
   - Compare original with manipulated
   - Verify manipulation is actually present
   - Verify manipulation looks plausible (not obvious artifact)
5. Mask inspection:
   - Overlay mask on manipulated image
   - Verify mask covers the manipulated region
   - Verify mask does not incorrectly cover unrelated regions
   - Verify mask dimensions match image dimensions
6. Metadata verification:
   - Check metadata in manifest.jsonl
   - Verify category is correct
   - Verify label is correct (1 for manipulated)
   - Verify manipulation_type is correct
   - Verify manipulation_area_ratio is correct
7. Record findings in table above

## Automated QC Results

### File Integrity
- Missing files: 0
- Corrupt files: 0
- All files load correctly

### Label Validation
- Invalid labels: 0
- Category/label conflicts: 0
- All labels consistent with categories

### Mask Validation
- Manipulated without masks: 0
- Mask dimension mismatches: 0
- Empty masks: 0
- Ratio inconsistencies: 0

### Metadata Completeness
- Missing required fields: 0
- All records have complete metadata

### Reproducibility
- Duplicate image IDs: 0
- ID determinism: PASS
- Metadata consistency: PASS

## QC Findings

### Issues Found
- TBD

### Recommendations
- TBD

## QC Approval

### Overall QC Status
- [ ] PASS - All samples reviewed and acceptable
- [ ] FAIL - Issues found requiring fixes
- [ ] PENDING - Review not yet completed

### Approver
- Name: TBD
- Date: TBD
- Signature: TBD

## Next Steps

### If QC Passes
1. Proceed to Phase 27: Data Loader implementation
2. Begin model development workflow
3. Document QC approval in final report

### If QC Fails
1. Address identified issues
2. Regenerate problematic samples if needed
3. Re-run validation
4. Repeat QC review
5. Do not proceed to model development until QC passes

## Appendix: QC Sample File Location

The full QC sample list is available at:
`docs/QC_SAMPLE_PATHS.txt`

The sample includes:
- 5 samples per category
- Full metadata for each sample
- Image paths
- Mask paths (for manipulated)
- Operation details

## Notes

This report must be completed manually by a human reviewer. The automated QC checks passed, but visual inspection is required to verify manipulation plausibility and mask accuracy.

**Status**: AWAITING MANUAL REVIEW

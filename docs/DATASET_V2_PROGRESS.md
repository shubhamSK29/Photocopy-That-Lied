# Dataset V2 Progress Report

## Current State (Phase 1-10 Complete)

### Dataset Composition
- **Total Records**: 1,321
- **Original**: 1,000 (from 1,000 DeepWeeds sources)
- **Natural-Processing**: 180 (20 sources × 9 operations)
- **Hard-Negative**: 120 (20 sources × 6 operations)
- **Manipulated**: 21 (10 copy-move + 5 removal + 3 insertion + 3 splicing)

### Label Distribution
- Label 0 (authentic): 1,300
- Label 1 (manipulated): 21
- **Class imbalance**: 61.9:1 (manipulated:authentic)

### Manipulation Distribution
- Copy-move: 10
- Object removal: 5
- Object insertion: 3
- Splicing: 3

### Operations Implemented

#### Natural-Processing (9 operations)
1. JPEG recompression (qualities: 70, 75, 80, 85, 90, 95)
2. Resize (scales: 0.5, 0.75, 0.9, 1.1, 1.25, 1.5)
3. Sharpen (strengths: 0.5, 1.5, 2.0)
4. Brightness (factors: 0.7, 0.8, 1.2, 1.3)
5. Contrast (factors: 0.7, 0.8, 1.2, 1.3)
6. Color saturation (factors: 0.7, 0.8, 1.2, 1.3)
7. Gamma correction (0.7, 0.8, 1.2, 1.5)
8. Denoising (strengths: 1.0, 2.0, 3.0)
9. Format conversion (JPEG/PNG)

#### Hard-Negative (6 operations - more aggressive)
1. JPEG recompression (qualities: 50, 55, 60, 65)
2. Resize (scales: 0.3, 0.4, 0.6, 0.8)
3. Sharpen (strengths: 2.5, 3.0, 3.5)
4. Color saturation (factors: 0.5, 0.6, 1.4, 1.5)
5. Gamma correction (0.5, 0.6, 1.6, 2.0)
6. Denoising (strengths: 4.0, 5.0)

#### Manipulations (4 types)
1. **Copy-move**: Diverse regions, rotations (0-270°), scales (0.7-1.3), blending
2. **Object removal**: Inpainting (telea, ns), variable region positions/areas
3. **Object insertion**: Split-safe donor-target pairing, rotation, scale, blending
4. **Splicing**: Split-safe donor-target pairing, rotation, scale, blending

### Validation Status
- Missing files: 0
- Corrupt files: 0
- Invalid labels: 0
- Category/label conflicts: 0
- Duplicate hash groups: 0
- Source leakage: 0
- Donor leakage: 0
- Manipulated without masks: 0
- Mask dimension mismatches: 0
- Empty masks: 0
- Metadata completeness: 100%

### Mask Pipeline
- All manipulated records have valid non-empty masks
- Manipulation area ratio computed from ground-truth masks
- Ratio range: 0.0128 - 0.3619
- Mean ratio: 0.0773
- 12 unique ratio values across 21 records

### Anti-Shortcut Audit Results
- JPEG quality: Diverse across categories
- Image format: All JPEG (source-based, not artificial)
- Dimensions: Diverse (6 unique for NP, 5 for HN)
- File sizes: Overlapping ranges (no shortcut)
- Manipulation area: Diverse ratios
- Processing operations: Diverse parameters
- Filename label leakage: None detected

### Split Distribution
- Train: 700 sources
- Validation: 150 sources
- Test: 150 sources
- Split inheritance: Working correctly
- Donor-target split safety: Enforced for insertion/splicing

### Source Utilization
- Original sources: 1,000/1,000 (100%)
- NP generation: 20/1,000 sources (2%)
- HN generation: 20/1,000 sources (2%)
- Manipulation generation: ~16/1,000 sources (1.6%)

## Remaining Work (Phases 11-21)

### Phase 11: Scale Generation
- Current: ~37 sources with variants
- Target: Scale to all 1,000 sources
- Recommended: Batch progression (100 → 250 → 500 → 1000)
- Estimated effort: High (requires generating thousands of variants)

### Phase 12: Target Dataset Balance
- Current class imbalance: 61.9:1
- Target: More balanced manipulation:authentic ratio
- Recommended: Scale manipulated to ~500-1000 records
- Manipulation type balance needed

### Phase 13: Source-Family Balance
- Current: Some sources have 13 variants, others have 1
- Target: More even distribution across sources
- Min: 1, Max: 13, Mean: ~1.3

### Phase 14: Split Balance
- Current: Split inheritance working
- Validation needed for scaled dataset

### Phase 15: Final Dataset Validation
- Full validation after scaling
- All checks (leakage, duplicates, masks, provenance)

### Phase 16: Dataset Statistics
- Comprehensive statistics report
- Distribution analysis

### Phase 17: Manual Quality Control
- Inspect 5 examples per category
- Visual verification of masks

### Phase 18: Reproducibility Test
- Rerun generation with same seeds
- Verify idempotency

### Phase 19: Test Regression
- All tests passing (63/63 currently)
- Re-run after scaling

### Phase 20: Cleanup
- Remove temporary scripts
- Organize documentation

### Phase 21: Final Report
- Complete dataset statistics
- Final validation summary

## Conclusion

Dataset V2 foundation is solid with:
- ✅ All manipulation types implemented
- ✅ Strong mask pipeline with area ratios
- ✅ Diverse natural-processing operations
- ✅ Diverse hard-negative operations
- ✅ Anti-shortcut protections
- ✅ Split-safe donor-target pairing
- ✅ Full validation passing
- ✅ No duplicates or leakage

**Status**: Foundation complete, but dataset not yet scaled to full 1,000 sources. Current dataset is a strong pilot but not yet ready for model development due to:
- Severe class imbalance (61.9:1)
- Low source utilization (2%)
- Insufficient manipulated diversity

**Recommendation**: Complete scaling (Phase 11) and balance (Phase 12) before proceeding to model development.

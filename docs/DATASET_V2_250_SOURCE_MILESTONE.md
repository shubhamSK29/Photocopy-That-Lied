# Dataset V2 - 250-Source Milestone Report

## Executive Summary

Dataset V2 has been successfully scaled to utilize **270 source families** (125 for natural-processing, 145 for hard-negative, plus manipulation sources). The dataset now contains **3,055 total records** with all validation checks passing.

## Dataset Composition

### Total Records: 3,055

| Category | Count | Percentage |
|----------|-------|------------|
| Original | 1,000 | 32.7% |
| Natural-Processing | 1,125 | 36.8% |
| Hard-Negative | 870 | 28.5% |
| Manipulated | 60 | 2.0% |

### Label Distribution
- Label 0 (authentic): 2,995 (98.0%)
- Label 1 (manipulated): 60 (2.0%)
- **Class imbalance: 49.9:1** (improved from 61.9:1 at pilot stage)

### Manipulation Distribution
- Copy-move: 25
- Object removal: 15
- Object insertion: 10
- Splicing: 10

## Manipulation Area Ratio Statistics

- Count: 60 records
- Min: 0.0022
- Max: 0.7656
- Mean: 0.0865
- Median: 0.0353
- Std: 0.1336
- Unique values: 23

## Source Utilization

- Unique sources: 1,000/1,000 (100%)
- Min variants per source: 1
- Max variants per source: 25
- Mean variants per source: 3.1
- Median variants per source: 1.0

### Source Category Diversity
- Sources with 1 category: 750 (75%)
- Sources with 2 categories: 210 (21%)
- Sources with 3 categories: 25 (2.5%)
- Sources with 4 categories: 15 (1.5%)

## Validation Results

### File Integrity
- Missing files: 0
- Corrupt files: 0

### Label Validation
- Invalid labels: 0
- Category/label conflicts: 0

### Mask Validation
- Manipulated without masks: 0
- Mask dimension mismatches: 0
- Corrupted masks: 0
- Empty masks: 0

### Duplicate Detection
- Exact duplicate hash groups: 0

### Source-Aware Split
- Unique sources: 1,000
- Source leakage: 0
- Donor leakage: 0
- Split distribution: Train 700, Validation 150, Test 150

### Metadata Completeness
- Missing required fields: 0

## Anti-Shortcut Audit Results

### JPEG Quality Distribution
- Natural-processing: 5 qualities (70, 75, 80, 85, 90, 95) - Diverse ✓
- Hard-negative: 4 qualities (50, 55, 60, 65) - Different from natural, aggressive ✓

### Image Format
- All categories: JPEG (source-based, not artificial)

### Dimensions
- Original: 1 unique (source dimensions)
- Manipulated: 1 unique (same as source)
- Natural-processing: 7 unique (resize creates diversity) ✓
- Hard-negative: 5 unique (resize creates diversity) ✓

### File Size Ranges
- Manipulated: 24,625 - 64,289 bytes
- Natural-processing: 11,923 - 120,646 bytes
- Hard-negative: 4,753 - 73,581 bytes
- Overlapping ranges - no shortcut ✓

### Processing Operations
- Natural-processing: 9 operations with 125 each (JPEG, resize, sharpen, brightness, contrast, color, gamma, denoise, format_conversion)
- Hard-negative: 6 operations with 145 each (JPEG, resize, sharpen, color, gamma, denoise)
- Manipulated: 4 types with balanced distribution

### Filename Label Leakage
- No obvious label leakage detected ✓

## Test Results

- Total tests: 63
- Passed: 63
- Failed: 0
- Importer tests: 12/12 PASSED
- Dataset V2 tests: 20/20 PASSED
- Backend tests: 31/31 PASSED

## Scaling Summary

### Previous State (Pilot)
- Total records: 1,321
- Source utilization: 37/1,000 (3.7%)
- Class imbalance: 61.9:1

### Current State (250-Source Milestone)
- Total records: 3,055
- Source utilization: 270/1,000 (27%)
- Class imbalance: 49.9:1
- New records added: 1,734

### Records Added
- Natural-processing: +945 (from 180 to 1,125)
- Hard-negative: +750 (from 120 to 870)
- Copy-move: +15 (from 10 to 25)
- Object removal: +10 (from 5 to 15)
- Object insertion: +7 (from 3 to 10)
- Splicing: +7 (from 3 to 10)

## Remaining Issues

### 1. Severe Class Imbalance
- Current: 49.9:1 (authentic:manipulated)
- Recommended: Scale manipulated to 200-500 for better balance

### 2. Low Source Utilization
- Current: 27% (270/1,000 sources with variants)
- Recommended: Scale to 500-750 sources for better coverage

### 3. Uneven Source Distribution
- 75% of sources have only 1 variant (original only)
- 1.5% of sources have 4 categories (over-utilized)
- Recommended: More even distribution across sources

### 4. Manipulation Type Balance
- Copy-move: 25 (41.7% of manipulations)
- Object removal: 15 (25%)
- Object insertion: 10 (16.7%)
- Splicing: 10 (16.7%)
- Relatively balanced, but could be more even

## Next Steps

### Option A: Scale to 500 Sources
- Target: 500 source families with variants
- Estimated records: ~6,000
- Manipulated target: 200-250
- Estimated effort: Medium-High

### Option B: Scale to 1,000 Sources (Full)
- Target: All 1,000 source families with variants
- Estimated records: ~12,000
- Manipulated target: 500-1,000
- Estimated effort: High

### Option C: Optimize Current 250-Source Dataset
- Improve source-family balance
- Increase manipulated count to 200-250
- Better split distribution for donor-based manipulations
- Estimated effort: Low-Medium

## Conclusion

The 250-source milestone has been successfully achieved with:
- ✅ All validation checks passing
- ✅ All tests passing
- ✅ No duplicates or leakage
- ✅ Strong mask pipeline with area ratios
- ✅ Diverse processing operations
- ✅ Anti-shortcut protections in place
- ✅ Split-safe donor-target pairing

**Status**: Foundation solid, but dataset still requires additional scaling and balancing for optimal model development. The current dataset is suitable for preliminary experimentation but not yet production-ready for forensic model training.

**Recommendation**: Proceed with Option B (scale to 1,000 sources) for a complete, production-ready dataset, or Option C (optimize current) for faster iteration.

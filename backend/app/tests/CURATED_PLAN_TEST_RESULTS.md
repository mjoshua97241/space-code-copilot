# Curated Blueprint Extraction Test Results

**Date**: 2026-01-16  
**Model**: GPT-4o  
**Scale**: 1.0 (1:100 default)  
**Multi-page PDF Support**: ✅ All pages are automatically combined vertically into a single image for extraction

## Important Note

✅ **Ground Truth CSVs Created**: Ground truth CSVs have been created for all test plans, enabling quantitative evaluation.

## Test Plans

1. `example_plan_01a.pdf` - Ground floor plan (10 rooms in ground truth)
2. `example_plan_01b.pdf` - Second floor plan (10 rooms in ground truth)
3. `example_plan_02.pdf` - Multi-level plan (12 rooms in ground truth: 6 on level 1, 6 on level 2)

**Note**: Multi-page PDFs are automatically processed by combining all pages vertically into a single image. This preserves the full blueprint context across pages.

## Results

### Plan 1: example_plan_01a.pdf

**Status**: ✅ Ground truth CSV available - quantitative evaluation completed

**Extraction Results:**
- Rooms extracted: 13
- Confidence: 96.31%
  - Name confidence: 100.00%
  - Type confidence: 90.77%
  - Area confidence: 100.00%

**Comparison Metrics:**
- Ground truth rooms: 10
- Extracted rooms: 13
- Matched: 6
- **Recall: 60.00%** (6 of 10 ground truth rooms found)
- **Precision: 46.15%** (6 of 13 extracted rooms matched)
- **Area accuracy: 95.48%** (excellent area matching for matched rooms)
- **Type match rate: 100.00%** (all matched rooms have correct types)

**Extracted Rooms:**
| ID | Name | Type | Level | Area (m²) |
|----|------|------|-------|-----------|
| R101 | Bedroom 1A | bedroom | 1 | 13.65 |
| R102 | Bedroom 1B | bedroom | 1 | 15.60 |
| R103 | Living Area 1 | living | 1 | 17.50 |
| R104 | Kitchen 1 | kitchen | 1 | 6.00 |
| R105 | Dining Area 1 | living | 1 | 9.00 |
| R106 | Laundry Area | other | 1 | 3.00 |
| R107 | Porch 1 | other | 1 | 5.00 |
| R108 | Bedroom 2A | bedroom | 1 | 13.65 |
| R109 | Bedroom 2B | bedroom | 1 | 15.60 |
| R110 | Living Area 2 | living | 1 | 17.50 |
| R111 | Kitchen 2 | kitchen | 1 | 6.00 |
| R112 | Dining Area 2 | living | 1 | 9.00 |
| R113 | Porch 2 | other | 1 | 5.00 |

**Issues Found:**
- **Unmatched extracted rooms (7)**: VLM split combined rooms into separate spaces:
  - Kitchen 1 (6.0 m²) + Dining Area 1 (9.0 m²) = 15.0 m² total, but ground truth has "Kitchen 1 + Living Area 1" (21.0 m²)
  - Similar pattern for Kitchen 2 + Dining Area 2
  - Laundry Area and Porch 1/2 are extracted but not in ground truth (may be correct - need manual verification)
- **Missing ground truth rooms (4)**:
  - "Kitchen 1 + Living Area 1" (21.0 m²) - VLM split this into separate Kitchen and Dining Area
  - "T & B 1" (3.0 m²) - VLM missed this bathroom (abbreviation issue)
  - "Kitchen 2 + Living Area 2" (21.0 m²) - Same splitting issue
  - "T & B 2" (3.0 m²) - VLM missed this bathroom

**Observations:**
- VLM correctly identifies individual rooms but splits combined spaces (Kitchen + Living Area)
- Room type classification is excellent (100% match rate for matched rooms)
- Area calculations are very accurate (95.48% accuracy)
- VLM extracts additional spaces (Laundry, Porch) that may be valid but not in ground truth
- "T & B" abbreviation not recognized - normalization should handle this but VLM didn't extract these rooms at all

**Limitations Observed:**
- VLM tends to split combined room labels (e.g., "Kitchen + Living Area") into separate rooms
- Small bathrooms (3 m²) with abbreviations ("T & B") are sometimes missed
- Additional spaces (porches, laundry) are extracted but may not be in ground truth

---

### Plan 2: example_plan_01b.pdf

**Status**: ✅ Ground truth CSV available - quantitative evaluation completed

**Extraction Results:**
- Rooms extracted: 11
- Confidence: 98.55%
  - Name confidence: 100.00%
  - Type confidence: 96.36%
  - Area confidence: 100.00%

**Comparison Metrics:**
- Ground truth rooms: 10
- Extracted rooms: 11
- Matched: 6
- **Recall: 60.00%** (6 of 10 ground truth rooms found)
- **Precision: 54.55%** (6 of 11 extracted rooms matched)
- **Area accuracy: 72.09%** (lower than plan 01a, but still reasonable)
- **Type match rate: 100.00%** (all matched rooms have correct types)

**Extracted Rooms:**
| ID | Name | Type | Level | Area (m²) |
|----|------|------|-------|-----------|
| R201 | Bedroom 3A | bedroom | 2 | 14.00 |
| R202 | Bedroom 3B | bedroom | 2 | 14.00 |
| R203 | Kitchen 3 | kitchen | 2 | 5.25 |
| R204 | Dining Area 3 | living | 2 | 10.00 |
| R205 | Living Area 3 | living | 2 | 10.00 |
| R206 | Laundry Area | other | 2 | 3.00 |
| R207 | Bedroom 4A | bedroom | 2 | 14.00 |
| R208 | Bedroom 4B | bedroom | 2 | 14.00 |
| R209 | Kitchen 4 | kitchen | 2 | 5.25 |
| R210 | Dining Area 4 | living | 2 | 10.00 |
| R211 | Living Area 4 | living | 2 | 10.00 |

**Issues Found:**
- **Unmatched extracted rooms (5)**: Similar splitting pattern:
  - Kitchen 3 (5.25 m²) + Dining Area 3 (10.0 m²) + Living Area 3 (10.0 m²) = 25.25 m² total
  - Ground truth has "Kitchen 3 + Living Area 3" (21.0 m²) - VLM split into 3 separate spaces
  - Laundry Area extracted but not in ground truth
- **Missing ground truth rooms (4)**:
  - "Kitchen 3 + Living Area 3" (21.0 m²) - VLM split this
  - "T & B 3" (3.0 m²) - VLM missed bathroom
  - "Kitchen 4 + Living Area 4" (21.0 m²) - VLM split this
  - "T & B 4" (3.0 m²) - VLM missed bathroom

**Observations:**
- Same pattern as plan 01a: VLM splits combined room labels
- Floor level detection working correctly (all rooms at level 2)
- Area accuracy lower (72.09%) due to splitting - individual areas may be correct but don't match combined ground truth
- Type classification still excellent (100% for matched rooms)

**Limitations Observed:**
- Same issues as plan 01a: room splitting and missed small bathrooms
- Area accuracy affected by splitting (individual areas correct, but combined areas don't match)

---

### Plan 3: example_plan_02.pdf

**Status**: ✅ Ground truth CSV available - quantitative evaluation completed

**Extraction Results:**
- Rooms extracted: 3 (from 5 raw, 2 filtered)
- Confidence: 100.00%
  - Name confidence: 100.00%
  - Type confidence: 100.00%
  - Area confidence: 100.00%

**Comparison Metrics:**
- Ground truth rooms: 12 (6 on level 1, 6 on level 2)
- Extracted rooms: 3
- Matched: 2
- **Recall: 16.67%** (2 of 12 ground truth rooms found - very low)
- **Precision: 66.67%** (2 of 3 extracted rooms matched)
- **Area accuracy: 28.57%** (low - only 2 matched rooms)
- **Type match rate: 100.00%** (matched rooms have correct types)

**Extracted Rooms:**
| ID | Name | Type | Level | Area (m²) |
|----|------|------|-------|-----------|
| R101 | Office / Bedroom | bedroom | 1 | 15.40 |
| R102 | Living room - Dining room | living | 1 | 37.40 |
| R103 | Kitchen | kitchen | 1 | 16.00 |

**Issues Found:**
- **Unmatched extracted rooms (1)**:
  - "Office / Bedroom" (15.4 m²) - name mismatch with ground truth "Office/Bedroom" (slash vs space)
- **Missing ground truth rooms (9)**:
  - Level 1: Hall (12.3 m²), Bathroom (7.4 m²), Utility (6.0 m²)
  - Level 2: All 6 rooms missing (Bedroom 1, Closet, Bedroom 2, Bedroom 3, Hall, Bathroom 1)
  - VLM only extracted 3 rooms total, missing 9 rooms

**Observations:**
- **Critical issue**: VLM only extracted 3 rooms from a 12-room plan (25% extraction rate)
- VLM appears to have focused on main spaces and missed smaller rooms (bathroom, utility, hall, closet)
- Level 2 rooms completely missed - may indicate VLM didn't process second floor properly
- Name matching issue: "Office / Bedroom" vs "Office/Bedroom" (space vs slash) - fuzzy matching needed
- "Living room - Dining room" area (37.4 m²) doesn't match ground truth (15.4 m²) - significant area error

**Limitations Observed:**
- **Major**: VLM misses many rooms, especially smaller spaces (bathrooms, utility, halls, closets)
- **Major**: Multi-level plans - VLM may not properly extract rooms from all floors
- Area calculation errors for combined spaces
- Name matching needs fuzzy logic (slash vs space differences)

---

## Overall Findings

### What Works Well

1. **Room Type Classification**: Excellent (100% match rate across all plans)
   - VLM correctly identifies room types (bedroom, living, kitchen, bathroom)
   - Normalization handles abbreviations well when rooms are extracted

2. **Area Accuracy (for matched rooms)**: Good to excellent
   - Plan 01a: 95.48% accuracy
   - Plan 01b: 72.09% accuracy (affected by splitting)
   - Plan 02: 28.57% (only 2 matched rooms, one has area error)

3. **Multi-page PDF Support**: Working
   - All pages combined successfully
   - No errors in PDF processing

4. **Floor Level Detection**: Working for plans 01a/01b
   - Correctly identifies level 1 vs level 2
   - Plan 02 issue may be different (needs investigation)

5. **Confidence Scores**: Reasonable
   - Overall confidence: 96-100%
   - Name confidence: 100% (VLM extracts names well)
   - Type confidence: 90-100% (excellent classification)

### Known Limitations

1. **Room Splitting**: VLM splits combined room labels into separate spaces
   - "Kitchen + Living Area" → extracted as separate "Kitchen" and "Dining Area"
   - Affects recall and area accuracy
   - **Impact**: Medium - rooms are found but not matched correctly

2. **Missing Small Rooms**: VLM misses small spaces, especially:
   - Bathrooms (especially with abbreviations like "T & B")
   - Utility rooms
   - Halls/corridors
   - Closets
   - **Impact**: High - significantly reduces recall

3. **Multi-level Extraction**: VLM may not extract all floors properly
   - Plan 02: Level 2 rooms completely missed
   - **Impact**: High - critical for multi-story buildings

4. **Name Matching**: Exact string matching fails on minor differences
   - "Office / Bedroom" vs "Office/Bedroom" (space vs slash)
   - **Impact**: Medium - fuzzy matching needed

5. **Area Calculation for Combined Spaces**: 
   - When VLM splits rooms, individual areas may be correct but combined areas don't match
   - **Impact**: Medium - affects area accuracy metric

### Quantitative Summary

**Average Metrics (across 3 plans):**
- **Recall: 45.56%** (target: >80%) ❌
- **Precision: 55.79%** (target: >85%) ❌
- **Area accuracy: 65.38%** (target: >85%) ❌
- **Type match rate: 100.00%** (target: >90%) ✅

**Overall Assessment:**
- Type classification: ✅ Excellent
- Room extraction completeness: ❌ Needs improvement (low recall)
- Area accuracy: ⚠️ Moderate (good for matched rooms, but affected by splitting)
- Multi-level support: ❌ Needs improvement

### Recommendations

1. **Improve Room Extraction Completeness**:
   - Enhance prompt to emphasize extracting ALL rooms, including small spaces
   - Add explicit instructions to look for bathrooms, utility rooms, halls, closets
   - Consider post-processing to detect missing room types

2. **Handle Combined Room Labels**:
   - Update prompt to recognize combined labels (e.g., "Kitchen + Living Area")
   - Consider post-processing to merge split rooms if their combined area matches ground truth

3. **Improve Multi-level Extraction**:
   - Enhance prompt to explicitly extract rooms from all floor levels
   - Add instructions to read floor level labels ("GROUND FLOOR PLAN", "SECOND FLOOR PLAN")
   - Verify VLM processes all pages correctly

4. **Fuzzy Name Matching**:
   - Implement fuzzy string matching in comparison function
   - Handle variations: "Office / Bedroom" vs "Office/Bedroom", "T & B" vs "T&B"

5. **Abbreviation Recognition**:
   - VLM prompt already includes "T & B" guidance, but rooms still missed
   - May need stronger emphasis or post-processing to detect missed bathrooms

6. **Scale Factor Testing**:
   - Test with different scale factors to see if area accuracy improves
   - Current default (1.0 for 1:100) may not be correct for all plans

## Next Steps

- [x] Create ground truth CSVs for floor plans ✅
- [x] Run quantitative evaluation ✅
- [ ] Investigate why VLM misses so many rooms in plan 02
- [ ] Test with different scale factors
- [ ] Implement fuzzy name matching in comparison function
- [ ] Enhance prompt for better small room detection
- [ ] Test on additional curated plans
- [ ] Document specific extraction errors and edge cases
- [ ] Consider post-processing to merge split rooms

# Curated Blueprint Extraction Test Results

**Date**: [Date of testing]  
**Model**: GPT-4o  
**Scale**: 1.0 (1:100 default)  
**Multi-page PDF Support**: ✅ All pages are automatically combined vertically into a single image for extraction

## Important Note

⚠️ **Ground Truth Mismatch**: The `rooms.csv` file is ground truth for `plan.png` (used in frontend), NOT for the floor plans in `floor-plans/` directory.

The floor plans (`example_plan_01.pdf`, `example_plan_02.pdf`) are different plans without corresponding ground truth CSVs. Testing focuses on documenting extraction results and observed limitations rather than quantitative comparison.

## Test Plans

1. `example_plan_01.pdf` - [No ground truth available, multi-page PDF - all pages combined]
2. `example_plan_02.pdf` - [No ground truth available, multi-page PDF - all pages combined]

**Note**: Multi-page PDFs are automatically processed by combining all pages vertically into a single image. This preserves the full blueprint context across pages.

## Results

### Plan 1: example_plan_01.pdf

**Status**: No ground truth CSV available - extraction documented only

**Extraction Results:**
- Rooms extracted: [N]
- Confidence: [X]%
  - Name confidence: [X]%
  - Type confidence: [X]%
  - Area confidence: [X]%

**Extracted Rooms:**
| ID | Name | Type | Level | Area (m²) |
|----|------|------|-------|-----------|
| R101 | [Name] | [Type] | 1 | [Area] |
| ... | ... | ... | ... | ... |

**Observations:**
- [What rooms were found?]
- [Are room names clear or generic?]
- [Are room types correctly classified?]
- [Are areas reasonable?]

**Limitations Observed:**
- [Document specific issues: missing rooms, incorrect types, area errors, etc.]

### Plan 2: example_plan_02.pdf

[Same format as above]

## Overall Findings

### What Works Well
- [List strengths observed across plans]

### Known Limitations
- [List limitations observed]
- Plans without ground truth cannot be quantitatively evaluated
- Need to manually verify extraction quality

### Recommendations
- Create ground truth CSVs for floor plans to enable quantitative evaluation
- Or manually verify extraction results by examining the PDFs
- Consider using extraction results as initial ground truth (with manual verification)

## Next Steps
- [ ] Manually verify extraction results against PDFs
- [ ] Create ground truth CSVs for floor plans (optional, for future evaluation)
- [ ] Document specific extraction errors and edge cases
- [ ] Test with different scale factors if needed
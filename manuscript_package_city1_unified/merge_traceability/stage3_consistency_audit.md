# Stage 3 Consistency Audit

## Purpose
This audit checks internal consistency across the unified manuscript.

## Consistency checks passed
- The abstract, introduction, discussion, limitations, and conclusion all agree on the same identity:
  - calibrated proxy surface
  - missing cell-level truth
  - reliability-aware interpretation layer
- Stage 1 and Stage 2 are consistently described as complementary, not competing, components.
- The deterministic stage remains the main proxy-surface construction and validation layer.
- The uncertainty-aware stage remains an interpretation and screening layer.
- The manuscript consistently treats WorldPop and GHS-POP as comparators, not truth.
- The manuscript consistently treats district evidence as partial after aggregation.
- The manuscript consistently treats confidence bands and hotspot classes as screening support, not correctness guarantees.
- Data and code availability now separates manuscript packages from runtime archives.

## Numerical consistency notes
- The 10-city registry, 8-city validated baseline batch, and 4-city uncertainty-evidence subset are consistent across `sections/03_study_design_and_data.tex` and `tables_tex/table2_study_coverage_summary.tex`.
- The uncertainty city summary in `table7` is consistent with the Stage 2 results text in `sections/08_results_reliability_uncertainty_hotspots.tex`.
- The interval coverage and error-alignment tables are consistent with the narrative that coverage is mixed but width-error alignment is positive.
- The hotspot stability table is consistent with the narrative that stable classes are the strongest Stage 2 evidence.

## Minor consistency issue resolved
- One caption in `table9_interval_coverage_summary.tex` originally used a reconstruction-like phrase.
- It was changed to `bounded local proxy-check setting` to align with the manuscript's bounded framing.

## Consistency verdict
- No internal contradiction requiring scientific rewriting remains.
- The manuscript is coherent across stages and sections.


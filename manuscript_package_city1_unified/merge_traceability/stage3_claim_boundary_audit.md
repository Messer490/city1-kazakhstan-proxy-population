# Stage 3 Claim Boundary Audit

## Scope
This audit checks whether the unified manuscript states its claims in a bounded, reviewer-safe way.

## Files inspected
- `sections/00_abstract.tex`
- `sections/01_introduction.tex`
- `sections/02_related_work.tex`
- `sections/03_study_design_and_data.tex`
- `sections/04_deterministic_proxy_surface_method.tex`
- `sections/05_uncertainty_aware_extension.tex`
- `sections/06_unified_validation_framework.tex`
- `sections/07_results_deterministic_surface_credibility.tex`
- `sections/08_results_reliability_uncertainty_hotspots.tex`
- `sections/09_integrated_discussion.tex`
- `sections/10_limitations.tex`
- `sections/11_data_and_code_availability.tex`
- `sections/12_conclusion.tex`

## Boundary findings
- The manuscript consistently says `proxy, not truth`.
- The manuscript consistently says `confidence_score` is an interpretation-confidence score, not a probability.
- The manuscript consistently says P10/P50/P90 are proxy uncertainty intervals, not true census-uncertainty intervals.
- The manuscript consistently says WorldPop and GHS-POP are structural comparators, not ground truth.
- The manuscript consistently says district evidence is partial administrative support after aggregation, not cell-level truth.
- The manuscript consistently says hotspot classes are screening categories, not verified hotspot truth.
- The manuscript consistently says Stage 2 is a reliability-aware interpretation layer, not a new truth model.

## One wording safety fix applied
- `tables_tex/table9_interval_coverage_summary.tex`
  - changed `bounded local reconstruction setting` to `bounded local proxy-check setting`
  - reason: remove one unnecessary reconstruction-like phrase from a caption

## Risky passages inspected
The following high-risk phrases were explicitly checked and found acceptable after the small caption fix:
- `true cell-level census labels are not available`
- `not truth reconstruction`
- `not a true census-uncertainty model`
- `not a truth probability`
- `not verified hotspot truth`
- `not ground truth`
- `not equal reliability everywhere`
- `partial administrative support`

## Boundary verdict
- No remaining claim boundary requires scientific rewriting.
- The paper remains strictly bounded as a calibrated proxy framework with reliability-aware interpretation.


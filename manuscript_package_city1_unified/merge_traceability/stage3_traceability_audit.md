# Stage 3 Traceability Audit

## Purpose
This audit maps key scientific claims to the source artifacts that support them.

## Traceability summary
The following core claim families are directly traceable:

| Claim family | Main support |
|---|---|
| 10-city registry and layered evidence design | `sections/03_study_design_and_data.tex`, `tables_tex/table2_study_coverage_summary.tex` |
| Deterministic baseline credibility | `sections/07_results_deterministic_surface_credibility.tex`, `tables_tex/table3_core_model_grid_validation.tex`, `tables_tex/table4_district_benchmark_summary.tex`, `tables_tex/table5_external_benchmark_summary.tex`, `tables_tex/table6_ablation_summary.tex` |
| Uncertainty-aware city coverage | `sections/08_results_reliability_uncertainty_hotspots.tex`, `tables_tex/table7_uncertainty_city_coverage_summary.tex` |
| Interval coverage behavior | `sections/08_results_reliability_uncertainty_hotspots.tex`, `tables_tex/table9_interval_coverage_summary.tex` |
| Error-width alignment | `sections/08_results_reliability_uncertainty_hotspots.tex`, `tables_tex/table10_error_uncertainty_alignment_summary.tex` |
| Confidence-band separation | `sections/05_uncertainty_aware_extension.tex`, `tables_tex/table11_confidence_band_summary.tex` |
| Hotspot stability | `sections/08_results_reliability_uncertainty_hotspots.tex`, `tables_tex/table12_hotspot_stability_summary.tex` |
| District and external uncertainty limitations | `sections/08_results_reliability_uncertainty_hotspots.tex`, `tables_tex/table13_district_external_uncertainty_limitations.tex` |
| Data/code provenance and archive separation | `sections/11_data_and_code_availability.tex` |

## Numeric claims traced
Major numeric claims traced in the audited files: **48**.

That includes, at minimum:
- registry and coverage counts in `table2`
- LOCO/grid metrics in `table3`
- district benchmark metrics in `table4`
- WorldPop/GHS-POP comparison metrics in `table5`
- ablation metrics in `table6`
- city coverage, uncertainty, and confidence shares in `table7`
- interval coverage in `table9`
- error-uncertainty correlations in `table10`
- confidence-band separation values in `table11`
- hotspot stability values in `table12`
- district/external limitation metrics in `table13`

## Untraced or conflicting numbers
- No material conflicts found.
- No unsupported numeric claim requiring immediate scientific revision was identified in the audited passage set.

## Traceability verdict
- The manuscript is traceable at the claim level.
- The main paper numbers are consistently backed by tables, section text, or retained package artifacts.

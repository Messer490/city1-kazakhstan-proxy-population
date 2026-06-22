# City1 Unified Framework Manuscript Package

## Final unified title

City1: A Reproducible Calibrated and Uncertainty-Aware Proxy Population Surface Framework for Intra-Urban Analysis in Data-Scarce Kazakhstan

## What this package is

This package integrates the existing deterministic calibrated proxy-surface manuscript and the uncertainty-aware interpretation manuscript into one unified City1 framework paper.

Core narrative:

1. build a deterministic calibrated proxy population surface under missing cell-level census truth;
2. validate its structural credibility through multi-level evidence;
3. add uncertainty-aware interpretation so the calibrated surface is not over-read as equally reliable everywhere;
4. preserve explicit limitations and reproducibility;
5. define a future pathway toward a tool-grounded LLM layer without claiming it as a completed result.

## Source packages used

- deterministic manuscript package:
  - `manuscript_package_v2/`
- uncertainty manuscript package:
  - `manuscript_package_v3/`
- uncertainty paper-facing evidence:
  - `reports/paper_v3_uncertainty/city1_v3_rf500m_e20_20260618T040646Z/`

## Unified paper outline

1. Abstract
2. Introduction
3. Related Work
4. Study Design and Data
5. Deterministic Calibrated Proxy Surface Method
6. Uncertainty-Aware Extension
7. Unified Validation Framework
8. Results I: Deterministic Surface Credibility
9. Results II: Reliability, Uncertainty, and Hotspot Use
10. Integrated Discussion
11. Limitations
12. Data and Code Availability
13. Conclusion

## Section-by-section merge plan

- `01_introduction.tex`
  - merges deterministic problem framing, bounded baseline identity, uncertainty motivation, and the unified two-stage contribution logic
- `02_related_work.tex`
  - merges gridded population mapping, proxy modeling under missing truth, and the need for uncertainty-aware interpretation
- `03_study_design_and_data.tex`
  - uses the deterministic study design as the backbone and inserts the four-city reliability-evidence subset
- `04_deterministic_proxy_surface_method.tex`
  - preserves the weak-target, supervised-learning, and official-total calibration method
- `05_uncertainty_aware_extension.tex`
  - adds ensemble calibration, interval outputs, confidence score, and hotspot classes
- `06_unified_validation_framework.tex`
  - joins the baseline validation stack and the uncertainty-validation stack into one evidence logic
- `07_results_deterministic_surface_credibility.tex`
  - retains deterministic model/grid, district, external, ablation, and qualitative results
- `08_results_reliability_uncertainty_hotspots.tex`
  - retains uncertainty city coverage, hotspot use, interval behavior, stability, and limitation evidence
- `09_integrated_discussion.tex`
  - explicitly links why Stage 1 and Stage 2 protect each other
- `10_limitations.tex`
  - merges deterministic and uncertainty limitations without hiding weak evidence
- `11_data_and_code_availability.tex`
  - merges reproducibility statements and artifact paths
- `12_conclusion.tex`
  - presents City1 as one calibrated and uncertainty-aware proxy framework

## Main paper tables retained

1. Contribution Map
2. Study coverage summary
3. Core model and grid validation summary
4. District benchmark summary
5. External benchmark summary
6. Ablation summary
7. Uncertainty city coverage summary
8. Hotspot prioritization summary
9. Interval coverage summary
10. Error-uncertainty alignment summary
11. Confidence-band summary
12. Hotspot stability summary
13. District/external uncertainty limitations summary

## Main paper figures retained

1. Unified City1 framework diagram
2. Deterministic model and grid validation summary
3. District and OSM completeness evidence
4. External benchmark comparison
5. Qualitative plausibility overview maps
6. Uncertainty output summary
7. Confidence-band distribution
8. Hotspot prioritization summary
9. Interval coverage and error-width alignment
10. Hotspot stability summary

## Supplement materials retained

- deterministic validation-evidence matrix
- uncertainty validation-evidence matrix
- combined evidence matrix
- city registry and coverage table
- feature inventory
- weak-target weights
- calibration and fallback rule
- confidence-score formula
- hotspot class definitions
- detailed qualitative cases
- example surface maps
- file manifests
- limitation tables
- expanded supporting material list
- notes on partial uncertainty validation

## Key traceability files

- `merge_traceability/contribution_map.csv`
- `merge_traceability/section_traceability.csv`
- `merge_traceability/table_figure_traceability.csv`
- `merge_traceability/claim_boundary_traceability.csv`
- `merge_traceability/removed_duplicates_log.csv`

## Current status

- unified manuscript skeleton: created
- unified draft sections: created
- traceability files: created
- copied figures and tables: created
- local TeX compile: blocked because `pdflatex` and `bibtex` are unavailable in PATH


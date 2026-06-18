# City1 v3 Completion Plan

## Objective

Complete `City1 v3` as an **uncertainty-aware extension of City1 v2** without redesigning the v2 science.

`v2` builds the calibrated proxy population surface.  
`v3` adds bounded reliability information around that surface.

## Phase Status

- Phase 1: **audit completed**
- Phase 2: **not started**
- Phase 3+: **not started**

## Phase-by-Phase Roadmap

### Phase 2 - Freeze the v3 data contract

Goal:

- define the exact schema before generating new artifacts

Required inputs:

- `data/processed/features_v2_batch1/`
- `data/external/city_population_reference_v2.csv`
- `data/external/city_status_registry_v2.csv`
- `reports/paper_v2_baseline/`
- `reports/external_benchmark_v2/`
- `data/external/district_benchmark/`

Required decisions:

- final v3 model root
- final v3 output root
- final v3 report roots
- final per-cell columns
- final city-level summary columns
- final hotspot class vocabulary
- `confidence_score` formula

Phase 2 frozen directory decision:

- model root: `models/v3_uncertainty/`
- inference output root: `outputs/v3_uncertainty/`
- report roots:
  - `reports/uncertainty_validation_v3/`
  - `reports/hotspot_prioritization_v3/`
  - `reports/district_interval_coverage_v3/`
  - `reports/external_disagreement_alignment_v3/`
  - `reports/paper_v3_uncertainty/`

Run-level rule:

- every frozen v3 artifact set must live under `<root>/<run_id>/`

Expected outputs:

- written schema for per-cell outputs
- written schema for city summaries
- written schema for validation tables
- written schema for metadata and freeze manifest

Done criteria:

- all required v3 file/directory conventions are frozen in writing
- no remaining ambiguity about columns or artifact names

### Phase 3 - Train the v3 uncertainty ensemble

Goal:

- produce the first frozen v3 uncertainty model package

Required inputs:

- `data/processed/features_v2_batch1/`
- `data/external/city_population_reference_v2.csv`
- frozen Phase 2 schema

Scripts to fix or create:

- fix `scripts/train_model_v3_uncertainty.py`
  - raise default ensemble size to the agreed freeze target
  - save config and summary artifacts in addition to joblib payloads
- optionally add `scripts/build_v3_freeze_manifest.py`

Expected model artifacts:

- `models/v3_uncertainty/<run_id>/ensemble_model.joblib`
- `models/v3_uncertainty/<run_id>/ensemble_config.json`
- `models/v3_uncertainty/<run_id>/training_summary.csv`
- `models/v3_uncertainty/<run_id>/feature_schema.json`
- `models/v3_uncertainty/<run_id>/city_registry_snapshot.csv`
- `models/v3_uncertainty/<run_id>/run_manifest.json`

Done criteria:

- ensemble trains reproducibly
- metadata clearly captures seeds, feature columns, calibration policy, and ensemble size

### Phase 4 - Run v3 inference for the initial freeze cities

Goal:

- generate the first real uncertainty-aware city outputs

Initial freeze cities:

- `Almaty`
- `Astana`
- `Shymkent`
- `Semey`

Scripts to fix or create:

- fix `scripts/predict_city_v3.py`
  - move default output root away from `data/processed/inference_runs`
  - emit canonical snake_case output schema
- fix `app_v3.py`
  - freeze grid to `500 m`
  - consume v3-specific output locations

Expected outputs:

- `outputs/v3_uncertainty/<run_id>/almaty_uncertainty_cells.csv`
- `outputs/v3_uncertainty/<run_id>/almaty_uncertainty_cells.geojson`
- same for `Astana`, `Shymkent`, `Semey`
- `outputs/v3_uncertainty/<run_id>/city_uncertainty_summary.csv`

Per-cell output contract to finalize in Phase 2:

- `city_name`
- `city_slug`
- `cell_id`
- centroid coordinates and paired GeoJSON geometry
- `p10`
- `p50`
- `p90`
- `uncertainty_width`
- `relative_uncertainty`
- `confidence_score`
- `confidence_band`
- `model_stability_score`
- `osm_support_score`
- `external_agreement_score`
- `internal_support_score`
- `hotspot_rank`
- `hotspot_priority_class`
- `official_city_total`
- `calibrated_member_count`
- `district_support_flag`
- `model_version`
- `run_id`

Done criteria:

- all four initial cities have saved calibrated interval outputs
- output columns follow the frozen schema

### Phase 5 - Complete hotspot prioritization

Goal:

- make the planning-use layer explicit and reproducible

Scripts to fix or create:

- fix `src/city1/hotspot_prioritization.py`
  - support final class vocabulary
  - add `hotspot_rank`
  - optionally add full-city usefulness classification
- fix `scripts/run_hotspot_prioritization_v3.py`
  - emit stable file names and city summary outputs

Expected outputs:

- `reports/hotspot_prioritization_v3/<run_id>/hotspot_priority_table.csv`
- `reports/hotspot_prioritization_v3/<run_id>/hotspot_priority_summary.csv`
- `reports/hotspot_prioritization_v3/<run_id>/hotspot_priority_map.png`
- city-level hotspot summary rows

Done criteria:

- hotspot prioritization matches the frozen class definitions
- outputs can be cited in the paper package

### Phase 6 - Complete uncertainty validation

Goal:

- produce the scientific evidence that makes uncertainty non-decorative

Validation tasks:

1. held-out interval coverage against weak targets
2. error vs uncertainty correlation
3. district interval coverage
4. external disagreement alignment
5. hotspot stability
6. qualitative uncertainty cases

Scripts to fix or create:

- extend `scripts/run_uncertainty_validation_v3.py`
  - include interval coverage, not only monotonicity
- create `scripts/run_district_interval_coverage_v3.py`
- create `scripts/run_external_disagreement_alignment_v3.py`
- create `scripts/run_qualitative_uncertainty_cases_v3.py`
- optionally create `scripts/run_hotspot_stability_v3.py`

Expected report artifacts:

- `reports/uncertainty_validation_v3/<run_id>/uncertainty_diagnostics.csv`
- `reports/uncertainty_validation_v3/<run_id>/uncertainty_fold_metrics.csv`
- `reports/uncertainty_validation_v3/<run_id>/interval_coverage_summary.csv`
- `reports/uncertainty_validation_v3/<run_id>/uncertainty_monotonicity.csv`
- `reports/district_interval_coverage_v3/<run_id>/district_interval_coverage_summary.csv`
- `reports/external_disagreement_alignment_v3/<run_id>/external_disagreement_alignment_summary.csv`
- `reports/hotspot_prioritization_v3/<run_id>/hotspot_stability_summary.csv`
- qualitative uncertainty case figures

Done criteria:

- interval coverage is explicitly reported against weak targets
- district interval coverage exists for the benchmark trio
- external disagreement alignment exists for benchmark cities
- hotspot stability evidence exists

### Phase 7 - Build the paper-facing v3 evidence package

Goal:

- turn scattered v3 outputs into a paper-ready frozen evidence stack

Scripts to fix or create:

- extend `src/city1/paper_report_v3.py`
- extend `scripts/build_paper_report_v3.py`
- create figure/table export helpers as needed

Expected outputs:

- `reports/paper_v3_uncertainty/<run_id>/figures/`
- `reports/paper_v3_uncertainty/<run_id>/tables/`
- `reports/paper_v3_uncertainty/<run_id>/outputs/`
- `reports/paper_v3_uncertainty/<run_id>/outputs/model_config.json`
- `reports/paper_v3_uncertainty/<run_id>/outputs/freeze_manifest.json`
- `reports/paper_v3_uncertainty/<run_id>/outputs/city_uncertainty_summaries.csv`

Core target artifacts:

- `fig1_v3_pipeline.png`
- `fig2_uncertainty_maps.png`
- `fig3_confidence_bands.png`
- `fig4_hotspot_prioritization.png`
- `fig5_validation_coverage.png`
- `fig6_case_panels.png`
- `table1_v3_city_coverage.csv`
- `table2_interval_coverage.csv`
- `table3_uncertainty_error_correlation.csv`
- `table4_district_interval_coverage.csv`
- `table5_hotspot_priority_summary.csv`

Done criteria:

- all paper-facing figures and tables come from reproducible v3 code
- the evidence package is self-contained and frozen

### Phase 8 - Build the manuscript package

Goal:

- create a separate `v3` paper package without touching frozen `v2`

Required tasks:

- create `manuscript_package_v3/main.tex`
- create section files
- create supplement package
- create data/code availability block
- maintain bounded wording about uncertainty

Done criteria:

- `manuscript_package_v3/` is a real manuscript package, not a placeholder README
- the manuscript never implies true census uncertainty

## Required Inputs

### Already available

- `data/processed/features_v2_batch1/`
- `data/external/city_population_reference_v2.csv`
- `data/external/city_status_registry_v2.csv`
- `reports/paper_v2_baseline/`
- `reports/external_benchmark_v2/`
- `reports/district_benchmark_v2/`
- `reports/qualitative_validation_v2/`
- district references for `Almaty`, `Astana`, `Shymkent`

### Still required from v3 work

- trained ensemble artifacts
- frozen manifest
- calibrated interval outputs
- city summary outputs
- hotspot stability outputs
- qualitative uncertainty case outputs

## Scripts to Create or Fix

### Fix

- `app_v3.py`
- `scripts/predict_city_v3.py`
- `scripts/train_model_v3_uncertainty.py`
- `scripts/run_uncertainty_validation_v3.py`
- `src/city1/hotspot_prioritization.py`
- `src/city1/paper_report_v3.py`
- `app_v3.py`

### Create

- `scripts/run_district_interval_coverage_v3.py`
- `scripts/run_external_disagreement_alignment_v3.py`
- `scripts/run_qualitative_uncertainty_cases_v3.py`
- `scripts/build_v3_freeze_manifest.py`
- optional: `scripts/run_hotspot_stability_v3.py`

## Model Artifacts to Save

- ensemble artifact
- member manifest
- ensemble config JSON
- training summary CSV
- freeze manifest JSON
- optional city-level training coverage summary

## Report Artifacts to Generate

- fold diagnostics
- interval coverage tables
- district interval coverage tables
- external disagreement tables
- hotspot prioritization tables
- hotspot stability tables
- qualitative case figures
- city summary outputs

## Validation Tasks

- held-out weak-target interval coverage
- error-uncertainty alignment
- district interval coverage
- external disagreement alignment
- hotspot stability
- qualitative uncertainty cases

## Paper Package Tasks

- create manuscript skeleton
- create supplement skeleton
- define figure/table numbering
- add data/code availability statement
- keep uncertainty wording bounded:
  - not true census uncertainty
  - not ground truth
  - not exact population reconstruction
  - not truth probability

## Done Criteria for v3

`v3` is complete only when all of the following exist:

- trained v3 ensemble
- frozen config
- `P10` / `P50` / `P90` outputs
- confidence bands
- hotspot prioritization
- uncertainty validation tables
- district interval coverage
- external disagreement analysis
- qualitative uncertainty panels
- `reports/paper_v3_uncertainty/`
- `manuscript_package_v3/`
- data/code availability section
- explicit statement that v3 uncertainty is not true census uncertainty

## Risks and Mitigations

### Risk 1 - Fake uncertainty

Problem:

- intervals exist but are not validated

Mitigation:

- make interval coverage against weak targets a mandatory artifact before any paper writing

### Risk 2 - Version mixing

Problem:

- v3 currently reuses v2-style output paths
- app currently allows non-frozen grid sizes

Mitigation:

- freeze separate v3 directories
- remove variable grid behavior from the main v3 runtime path

### Risk 3 - Missing output contract fields

Problem:

- no `confidence_score`
- no `hotspot_rank`
- no standard `hotspot_priority_class`

Mitigation:

- finalize the output schema in Phase 2 before generating any new artifacts

### Risk 4 - External benchmark dependency instability

Problem:

- external disagreement alignment may depend on `rasterio`, which is optional

Mitigation:

- explicitly standardize the v3 environment before running Phase 6 external validation

### Risk 5 - Paper package starts too early

Problem:

- manuscript writing before evidence freeze will create drift

Mitigation:

- do not build `manuscript_package_v3` beyond scaffolding until Phase 7 artifacts exist

## Recommended Phase 2 Start Condition

Start Phase 2 only when:

- the v3 path conventions are approved
- the output schema is approved
- the hotspot class vocabulary is approved
- the `confidence_score` formula is approved
- the initial freeze cities are confirmed
- the missing CLI/report builders are accepted as required scope

# City1 v3 Data Contract

## Scope

This document freezes the **Phase 2 data contract** for `City1 v3`.

It defines:

- approved directories
- required inputs
- initial freeze cities
- per-cell output schema
- city-level summary schema
- confidence score formula
- confidence bands
- hotspot priority classes
- model artifact contract
- report contract

This contract is intentionally bounded:

- `v3` extends `v2`
- `v3` does not estimate true census uncertainty
- `v3` estimates model/evidence uncertainty for calibrated proxy population surfaces

## Directory Convention Reference

See [V3_DIRECTORY_CONVENTIONS.md](C:/Users/Asus/Downloads/City1-main/City1-main/docs/V3_DIRECTORY_CONVENTIONS.md).

Phase 2 approved roots:

- `models/v3_uncertainty/`
- `outputs/v3_uncertainty/`
- `reports/uncertainty_validation_v3/`
- `reports/hotspot_prioritization_v3/`
- `reports/district_interval_coverage_v3/`
- `reports/external_disagreement_alignment_v3/`
- `reports/paper_v3_uncertainty/`

## Initial Freeze Cities

The initial `v3` freeze set is confirmed as:

- `Almaty`
- `Astana`
- `Shymkent`
- `Semey`

Rationale:

- `Almaty`: strongest completeness and qualitative support case
- `Astana`: moderate completeness and cautious interpretation case
- `Shymkent`: important weak/mixed district-support case
- `Semey`: cleaner additional example and smoke-passed runtime city

These four cities are the minimum scientific freeze set for early `v3` artifacts.

## Input Contract

### 1. Feature batch

Path:

- `data/processed/features_v2_batch1/`

Scope:

- required for training and batch-style uncertainty validation
- required for all cities included in the `v3` training batch

Naming convention:

- one CSV per city
- filename = `city_slug.csv`
- examples:
  - `almaty.csv`
  - `astana.csv`
  - `ust_kamenogorsk.csv`

Required columns:

- `Zone_ID`
- `latitude`
- `longitude`
- `Building_Count`
- `Building_Area`
- `Residential_Area`
- `Commercial_Area`
- `Retail_Area`
- `Public_Area`
- `Road_Length`
- `Bus_Stop_Count`
- `Park_Area`
- `Building_With_Levels_Count`
- `Mean_Building_Levels`
- `Total_Floor_Area`
- `Schools_Count`
- `Hospitals_Count`
- `Parks_Shops_Count`
- `POI_Access_Index`
- `Combined_Index`

Optional columns:

- extra derived columns may be present but are ignored unless explicitly added to the frozen feature schema later

If missing:

- a missing required column is a hard failure for that city file
- a missing city file excludes that city from training/validation
- if a freeze city file is missing, the initial `v3` freeze is not valid

### 2. Official totals reference

Path:

- `data/external/city_population_reference_v2.csv`

Scope:

- required for every city used in `v3`
- required for training, inference, and calibration

Expected city naming convention:

- `city_name` as display label
- `normalized_city_name` as normalized join key

Required columns:

- `city_name`
- `normalized_city_name`
- `country`
- `population`
- `reference_date`
- `source_tier`
- `verified`
- `source_name`
- `source_url`

Optional columns:

- `notes`

If missing:

- `v3` training or inference for that city must fail hard
- no unverified fallback totals are allowed in the frozen `v3` path

### 3. City status registry

Path:

- `data/external/city_status_registry_v2.csv`

Scope:

- required for freeze-city selection, support flags, and runtime gating
- recommended for all `v3` runs

Required columns:

- `city_name`
- `normalized_city_name`
- `display_query`
- `population`
- `supported_for_calibrated_inference`
- `feature_generated`
- `feature_source_file`
- `feature_row_count`
- `included_in_training`
- `validated_batch`
- `smoke_passed`
- `district_benchmark_reference_available`
- `district_benchmark_completed`
- `district_benchmark_quality`
- `recommended_for_baseline_use`
- `status_label`

Optional columns:

- `country`
- `reference_date`
- QA counts and other support diagnostics

If missing:

- fallback to `city_population_reference_v2.csv` is allowed only for minimal calibration lookup
- freeze-city support logic becomes degraded
- `district_support_flag` defaults to `not_available`

### 4. District benchmark raw references

Path:

- `data/external/district_benchmark/`

Scope:

- required only for validation cities with district support
- initial expected cities:
  - `Almaty`
  - `Astana`
  - `Shymkent`

Required per-file columns:

- `city_name`
- `city_query`
- `district_name`
- `district_query`
- `osm_match_tokens`
- `official_population`
- `use_in_metrics`
- `source_precision`
- `source_name`
- `source_url`

Optional columns:

- `source_notes`

If missing:

- district interval coverage is unavailable for that city
- `internal_support_score` falls back to neutral behavior
- `district_support_flag = not_available`

### 5. Frozen v2 paper-facing package

Path:

- `reports/paper_v2_baseline/`

Scope:

- required as a frozen dependency reference
- not required for core training math
- required for bounded interpretation and cross-version traceability

Required tables expected to exist:

- `tables/city_status_table.csv`
- `tables/model_validation_table.csv`
- `tables/osm_completeness_table.csv`
- `tables/district_benchmark_metrics_table.csv`
- `tables/external_benchmark_summary_table.csv`

If missing:

- `v3` can still train later
- but paper-facing cross-version support becomes incomplete

### 6. OSM completeness summary

Path:

- `reports/osm_completeness_v2/osm_completeness_summary.csv`

Scope:

- strongly recommended input for city-level support scoring

Required columns:

- `city_name`
- `completeness_score`
- `completeness_label`

Optional columns:

- coverage and zero-share diagnostics

If missing:

- `osm_support_score` falls back to a runtime-computed equivalent if available
- otherwise fallback neutral value is used

### 7. Existing external benchmark summaries

Preferred path:

- `reports/paper_v2_baseline/tables/external_benchmark_summary_table.csv`

Scope:

- optional context input
- useful for defining the initial external-agreement component logic
- not sufficient alone for final city-specific `v3` disagreement scoring

Required columns when present:

- `benchmark_name`
- `pearson_r`
- `spearman_r`
- `top_decile_overlap`
- `hotspot_iou`

If missing:

- `external_agreement_score` uses neutral fallback until city-specific v3 alignment outputs exist

## Canonical Naming Rules

- `city` = display name, e.g. `Almaty`
- `city_slug` = normalized lowercase slug, e.g. `almaty`
- `cell_id` = canonical v3 name for the current `v2` field `Zone_ID`
- `run_id` = `city1_v3_rf500m_e{ensemble_size}_{YYYYMMDDTHHMMSSZ}`

Compatibility note:

- existing prototype code still uses `Zone_ID` and `Population_Estimate_*` style names
- the frozen `v3` contract adopts canonical snake_case field names
- compatibility aliases may exist temporarily during implementation, but frozen `v3` artifacts must satisfy the canonical schema

## Cell-Level Output Contract

### Geometry rule

Canonical CSV outputs do **not** need to embed full geometry.

Rules:

- CSV output must contain `cell_id`
- paired GeoJSON output must carry feature geometry keyed by the same `cell_id`
- optional `geometry_wkt` may be emitted for debugging but is not part of the required frozen CSV contract

### Required core columns

| Column | Type | Required | Meaning | Allowed values / computation | Paper use |
|---|---|---:|---|---|---|
| `run_id` | string | yes | frozen run identifier | `city1_v3_rf500m_e{ensemble_size}_{timestamp}` | provenance |
| `model_version` | string | yes | frozen model identity | recommended: `city1_v3_rf500m_uncertainty` | provenance |
| `city` | string | yes | display city name | e.g. `Almaty` | tables |
| `city_slug` | string | yes | normalized city key | lowercase snake case | joins / filenames |
| `cell_id` | string | yes | unique cell identifier | canonical alias of `Zone_ID` | joins / maps |
| `centroid_latitude` | float | yes | cell centroid latitude | copied from feature layer | mapping |
| `centroid_longitude` | float | yes | cell centroid longitude | copied from feature layer | mapping |
| `official_city_total` | integer | yes | official calibration anchor for the city | from official totals table | tables |
| `calibrated_member_count` | integer | yes | number of ensemble members successfully calibrated | positive integer | diagnostics |
| `p10` | float | yes | calibrated 10th percentile estimate | empirical member quantile after calibration | figures / tables |
| `p50` | float | yes | calibrated median estimate | empirical member quantile after calibration | main surface |
| `p90` | float | yes | calibrated 90th percentile estimate | empirical member quantile after calibration | figures / tables |
| `uncertainty_width` | float | yes | interval width | `p90 - p10` | figures / diagnostics |
| `relative_uncertainty` | float | yes | scale-normalized interval width | `uncertainty_width / max(p50, epsilon)` | figures / diagnostics |
| `model_stability_score` | float | yes | local stability component | see confidence formula | diagnostics |
| `osm_completeness_score` | float | yes | city-level OSM support score repeated per cell | `0..100` scale from completeness summary or runtime equivalent | support context |
| `osm_completeness_label` | string | yes | city-level OSM support label | `good`, `moderate`, `weak`, or future bounded extension | context |
| `osm_support_score` | float | yes | normalized OSM support component | `osm_completeness_score / 100` clipped to `[0,1]` | diagnostics |
| `external_agreement_score` | float | yes | external support component | city-level or per-cell when available; else neutral fallback | diagnostics |
| `internal_support_score` | float | yes | district/internal support component | city-level support scalar or neutral fallback | diagnostics |
| `confidence_score` | float | yes | bounded interpretation confidence | weighted composite in `[0,1]` | figures / tables |
| `confidence_band` | string | yes | confidence category | `high`, `medium`, `low` | maps / tables |
| `hotspot_rank` | integer | yes | descending `p50` rank within city | `1` = highest `p50` cell | prioritization |
| `hotspot_priority_class` | string | yes | planning-oriented class | fixed vocabulary below | figures / tables |
| `district_support_flag` | string | yes | internal support availability/quality | `strong`, `mixed`, `weak`, `not_available` | support context |

### Optional enrichment columns

| Column | Type | Required | Meaning | Notes |
|---|---|---:|---|---|
| `external_agreement_summary` | string | no | short benchmark-support summary | added in Phase 6 enrichment |
| `district_interval_coverage_rate` | float | no | city-level district interval coverage repeated per cell | only for cities with district coverage |
| `geometry_wkt` | string | no | debug geometry serialization | not required in frozen CSV |

### Required invariants

- `p10 <= p50 <= p90` for every cell
- `uncertainty_width >= 0`
- `relative_uncertainty >= 0`
- `0 <= confidence_score <= 1`
- `confidence_band` must match thresholding on `confidence_score`
- `p50` is the canonical final proxy surface for `v3`

## City-Level Summary Contract

One row per city per run.

Required output file:

- `outputs/v3_uncertainty/<run_id>/city_uncertainty_summary.csv`

Required columns:

| Column | Type | Required | Meaning |
|---|---|---:|---|
| `run_id` | string | yes | frozen run id |
| `model_version` | string | yes | model identity |
| `city` | string | yes | display city name |
| `city_slug` | string | yes | normalized city key |
| `n_cells` | integer | yes | number of cells in the city output |
| `official_total` | integer | yes | official city total |
| `sum_p50` | float | yes | sum of calibrated `p50` |
| `p50_total_gap_abs` | float | yes | absolute gap between `sum_p50` and `official_total` |
| `calibrated_member_count` | integer | yes | number of calibrated members used |
| `mean_uncertainty_width` | float | yes | average cell uncertainty width |
| `median_relative_uncertainty` | float | yes | median relative uncertainty |
| `mean_confidence_score` | float | yes | average confidence score |
| `share_high_confidence` | float | yes | share of cells with `high` band |
| `share_medium_confidence` | float | yes | share of cells with `medium` band |
| `share_low_confidence` | float | yes | share of cells with `low` band |
| `hotspot_threshold_p90` | float | yes | city hotspot threshold from `p50` top decile rule |
| `n_high_confidence_hotspots` | integer | yes | count of `high_value_high_confidence` cells |
| `n_low_confidence_hotspots` | integer | yes | count of `high_value_low_confidence` cells |
| `n_low_value_high_uncertainty` | integer | yes | count of `low_value_high_uncertainty` cells |
| `osm_completeness_score` | float | yes | city completeness score |
| `osm_completeness_label` | string | yes | city completeness label |
| `external_agreement_score` | float | yes | city-level external support score or fallback |
| `external_agreement_summary` | string | no | short summary text/category |
| `district_support_flag` | string | yes | city-level internal support category |
| `district_interval_coverage_available` | boolean | yes | whether district interval coverage exists |
| `district_interval_coverage_rate` | float | no | coverage rate if available |

## Confidence Score Formula

### Interpretation

`confidence_score` is **not** truth probability.

It is a bounded interpretation-confidence score for the calibrated proxy surface.

### Frozen initial formula

For cell `i` in city `c`:

`confidence_score_i = clip(0.40 * model_stability_score_i + 0.25 * osm_support_score_c + 0.20 * external_agreement_score_i_or_c + 0.15 * internal_support_score_c, 0, 1)`

### Component definitions

#### 1. `model_stability_score`

Definition:

- `city_q90_relative_uncertainty = 90th percentile of relative_uncertainty within the city`
- `model_stability_score = 1 - clip(relative_uncertainty / max(city_q90_relative_uncertainty, epsilon), 0, 1)`

Interpretation:

- lower relative uncertainty -> higher stability score
- cells at or above the city's high-uncertainty tail receive low stability scores

#### 2. `osm_support_score`

Definition:

- `osm_support_score = clip(osm_completeness_score / 100, 0, 1)`

Interpretation:

- city-level support scalar from frozen OSM completeness diagnostics

#### 3. `external_agreement_score`

Definition when city-specific support is available:

- use a bounded city-level support scalar derived from the best available external agreement evidence
- first frozen rule:
  - if a city-specific `v3` external alignment score is available, use it
  - otherwise, if only broader benchmark support exists, use the best available bounded summary in `[0,1]`

Fallback:

- if unavailable, set `external_agreement_score = 0.50`

Reason:

- neutral fallback avoids fake certainty while keeping the score computable before Phase 6 enrichment is complete

#### 4. `internal_support_score`

Definition when district support exists:

- `internal_support_score = clip(0.45 * max(pearson_r, 0) + 0.35 * max(spearman_r, 0) + 0.20 * boundary_support, 0, 1)`
- `boundary_support = 1.0` when `boundary_warning_count = 0`, else `0.5`

Fallback:

- if district support is unavailable, set `internal_support_score = 0.50`

### Why this formula is acceptable now

- simple
- bounded
- implementable without Bayesian redesign
- consistent with the v3 scientific identity
- robust to missing enrichment components through neutral fallback

## Confidence Band Vocabulary

Frozen thresholds:

- `high`: `confidence_score >= 0.70`
- `medium`: `0.40 <= confidence_score < 0.70`
- `low`: `confidence_score < 0.40`

Reason:

- easy to interpret
- consistent with a bounded screening-oriented use case
- strict enough that `high` remains selective

## Hotspot Priority Classes

Frozen vocabulary:

- `high_value_high_confidence`
- `high_value_low_confidence`
- `medium_value_high_confidence`
- `low_value_high_uncertainty`
- `not_priority`

### Hotspot rank

- `hotspot_rank` is the descending dense rank of `p50` within each city
- `1` is the highest estimated cell

### High-value rule

Use city-specific top decile by `p50`.

Equivalent implementation:

- `p50 >= city_p90_threshold`
- or `hotspot_rank <= ceil(0.10 * n_cells)`

### Class rules

- `high_value_high_confidence`
  - top decile by `p50`
  - `confidence_band = high`

- `high_value_low_confidence`
  - top decile by `p50`
  - `confidence_band = low`

- `medium_value_high_confidence`
  - `p50` in `[city_p75_threshold, city_p90_threshold)`
  - `confidence_band = high`

- `low_value_high_uncertainty`
  - `p50 < city_median_p50`
  - `confidence_band = low`

- `not_priority`
  - all remaining cells

## Model Artifact Contract

After training, the following files must exist under:

- `models/v3_uncertainty/<run_id>/`

### Required files

- `ensemble_config.json`
- `training_summary.csv`
- `feature_schema.json`
- `city_registry_snapshot.csv`
- `ensemble_model.joblib`
- `run_manifest.json`

### Expected contents

#### `ensemble_config.json`

- `run_id`
- `model_version`
- `model_name`
- `grid_cell_size_meters`
- `ensemble_size`
- `base_random_state`
- `bootstrap_within_city`
- `quantiles`
- `use_log_target`
- `relative_epsilon`
- `feature_columns`
- `official_totals_reference`
- `city_registry_reference`

#### `training_summary.csv`

One row for the frozen run with at least:

- `run_id`
- `model_version`
- `ensemble_size`
- `training_city_count`
- `training_row_count`
- `included_cities`
- `skipped_file_count`
- `warning_count`

#### `feature_schema.json`

- ordered feature column list
- canonical `cell_id` source field
- canonical output field list

#### `city_registry_snapshot.csv`

- frozen copy of the city rows used for the run
- enough columns to reconstruct city coverage/support context

#### `ensemble_model.joblib`

- bundled artifact or equivalent single-file load target
- must contain member estimators and enough metadata to reproduce inference

#### `run_manifest.json`

- `run_id`
- UTC creation time
- git commit if available
- list of generated files
- declared inputs
- declared validation scope

## Report Contract

### 1. `reports/uncertainty_validation_v3/<run_id>/`

Required outputs:

- `uncertainty_diagnostics.csv`
- `uncertainty_fold_metrics.csv`
- `interval_coverage_summary.csv`
- `uncertainty_monotonicity.csv`
- `uncertainty_monotonicity_metrics.json`
- `figure_interval_coverage.png`
- `figure_uncertainty_monotonicity.png`
- `run_manifest.json`

### 2. `reports/hotspot_prioritization_v3/<run_id>/`

Required outputs:

- `hotspot_priority_table.csv`
- `hotspot_priority_summary.csv`
- `hotspot_priority_map.png`
- `run_manifest.json`

### 3. `reports/district_interval_coverage_v3/<run_id>/`

Required outputs:

- `district_interval_coverage_by_district.csv`
- `district_interval_coverage_summary.csv`
- `figure_district_interval_coverage.png`
- `run_manifest.json`

### 4. `reports/external_disagreement_alignment_v3/<run_id>/`

Required outputs:

- `external_disagreement_alignment_by_city.csv`
- `external_disagreement_alignment_summary.csv`
- `figure_external_disagreement_alignment.png`
- `run_manifest.json`

### 5. `reports/paper_v3_uncertainty/<run_id>/`

Required structure:

- `figures/`
- `tables/`
- `outputs/`

Required paper-facing artifacts:

- `figures/fig1_v3_pipeline.png`
- `figures/fig2_uncertainty_maps.png`
- `figures/fig3_confidence_bands.png`
- `figures/fig4_hotspot_prioritization.png`
- `figures/fig5_validation_coverage.png`
- `figures/fig6_case_panels.png`
- `tables/table1_v3_city_coverage.csv`
- `tables/table2_interval_coverage.csv`
- `tables/table3_uncertainty_error_correlation.csv`
- `tables/table4_district_interval_coverage.csv`
- `tables/table5_hotspot_priority_summary.csv`
- `outputs/city_uncertainty_summaries.csv`
- `outputs/model_config.json`
- `outputs/freeze_manifest.json`

## Script Update Checklist

Scripts that must be updated next to follow the Phase 2 contract:

- `scripts/train_model_v3_uncertainty.py`
  - path root
  - artifact names
  - config / schema / manifest outputs
- `scripts/predict_city_v3.py`
  - move output root to `outputs/v3_uncertainty/`
  - emit canonical schema
- `scripts/run_uncertainty_validation_v3.py`
  - add interval coverage
  - write to run-specific report dir
- `scripts/run_hotspot_prioritization_v3.py`
  - emit canonical hotspot classes and summary files
- `app_v3.py`
  - freeze grid to `500 m`
  - stop writing canonical outputs into v2 paths
- missing scripts to create:
  - `scripts/run_district_interval_coverage_v3.py`
  - `scripts/run_external_disagreement_alignment_v3.py`
  - `scripts/build_v3_freeze_manifest.py`
  - optional later: `scripts/run_qualitative_uncertainty_cases_v3.py`

## Phase 2 Cheap Checks Performed

Confirmed without training:

- target root directories were checked for existence
- `reports/paper_v3_uncertainty/` already existed as a scaffold root
- `data/processed/features_v2_batch1/almaty.csv` columns were inspected
- `data/external/city_population_reference_v2.csv` columns were inspected
- `data/external/city_status_registry_v2.csv` columns were inspected
- `data/external/district_benchmark/almaty_district_population_reference_v2.csv` columns were inspected
- `reports/osm_completeness_v2/osm_completeness_summary.csv` was inspected
- `reports/paper_v2_baseline/tables/external_benchmark_summary_table.csv` was inspected
- `reports/paper_v2_baseline/tables/district_benchmark_metrics_table.csv` was inspected

Not performed in Phase 2:

- no ensemble training
- no expensive city inference
- no expensive geospatial validation runs
- no manuscript writing


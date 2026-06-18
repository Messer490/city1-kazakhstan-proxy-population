# Phase 3 and Phase 4 Run Report

## Scope

This report closes the `City1 v3` prompt scope for:

- Phase 3: train the first frozen uncertainty ensemble package
- Phase 4: generate the first frozen uncertainty-aware inference outputs

The work stayed inside the bounded `v3` contract:

- Kazakhstan-first
- `random_forest` core retained
- fixed `500 m` grid preserved
- official-total calibration preserved
- no new science drift into Phase 5/6 manuscript work

## Implementation Summary

The following `v3` compliance work was completed before execution:

- canonical snake_case `v3` output schema implemented
- separate `models/v3_uncertainty/<run_id>/` training packages implemented
- separate `outputs/v3_uncertainty/<run_id>/` inference packages implemented
- `app_v3.py` frozen to the `500 m` path and separated from `app_v2.py`
- offline inference path added from frozen `features_v2_batch1` artifacts
- `v3` hotspot vocabulary aligned to the frozen contract
- training/inference manifests, summaries, and schema files added

## Executed Runs

### Smoke training run

- `run_id`: `city1_v3_rf500m_e3_20260618T040617Z`
- purpose: cheap contract/packaging validation
- ensemble members: `3`
- trees per member: `40`
- included cities: `almaty, astana, semey, shymkent`
- training rows: `12,523`

Smoke training artifact directory:

- `models/v3_uncertainty/city1_v3_rf500m_e3_20260618T040617Z/`

Smoke package checks passed:

- required files created
- artifact load test passed
- embedded `run_id` and `model_version` resolved correctly

### Full training run

- `run_id`: `city1_v3_rf500m_e20_20260618T040646Z`
- ensemble members: `20`
- trees per member: `150`
- included cities: `almaty, astana, petropavlovsk, semey, shymkent, taraz, uralsk, ust kamenogorsk`
- training rows: `16,132`

Full training artifact directory:

- `models/v3_uncertainty/city1_v3_rf500m_e20_20260618T040646Z/`

Required training files present:

- `ensemble_model.joblib`
- `ensemble_config.json`
- `training_summary.csv`
- `feature_schema.json`
- `city_registry_snapshot.csv`
- `run_manifest.json`

Note:

- the full run used `20` ensemble members instead of `30`
- this was an intentional bounded choice to keep the first frozen `v3` package executable in the local environment without skipping the full training phase

## Full Inference Run

Inference used the full ensemble package:

- `run_id`: `city1_v3_rf500m_e20_20260618T040646Z`

Output directory:

- `outputs/v3_uncertainty/city1_v3_rf500m_e20_20260618T040646Z/`

Freeze cities completed:

- `Almaty`
- `Astana`
- `Semey`
- `Shymkent`

Generated city files:

- `almaty_uncertainty_cells.csv`
- `almaty_uncertainty_cells.geojson`
- `astana_uncertainty_cells.csv`
- `astana_uncertainty_cells.geojson`
- `semey_uncertainty_cells.csv`
- `semey_uncertainty_cells.geojson`
- `shymkent_uncertainty_cells.csv`
- `shymkent_uncertainty_cells.geojson`
- `city_uncertainty_summary.csv`
- `run_manifest.json`

### City summary snapshot

| City | Cells | Official total | Sum P50 | Gap | Median relative uncertainty | Mean confidence | District support |
|---|---:|---:|---:|---:|---:|---:|---|
| Almaty | 3078 | 2351424 | 2351424.0 | 0.0 | 0.169659 | 0.585335 | strong |
| Astana | 3473 | 1649242 | 1649242.0 | 0.0 | 0.280816 | 0.443723 | mixed |
| Semey | 1033 | 315382 | 315382.0 | 0.0 | 0.349319 | 0.518149 | not_available |
| Shymkent | 4939 | 1298279 | 1298279.0 | 0.0 | 0.175200 | 0.473645 | mixed |

## Acceptance Checks

### Code and interface checks

- `py_compile` passed for the updated `v3` modules and scripts
- unit tests passed:
  - `tests.test_uncertainty`
  - `tests.test_uncertainty_validation`
  - `tests.test_hotspot_prioritization`
  - `tests.test_contracts`
  - `tests.test_validation`
- CLI `--help` checks passed for:
  - `scripts/train_model_v3_uncertainty.py`
  - `scripts/predict_city_v3.py`
  - `scripts/run_uncertainty_validation_v3.py`
  - `scripts/run_hotspot_prioritization_v3.py`

### Training package checks

- smoke and full artifacts loaded successfully through `load_uncertainty_artifact`
- smoke package resolved `3` members
- full package resolved `20` members

### Frozen output checks

For all four saved city CSVs:

- no required canonical columns were missing
- `p10 <= p50 <= p90` passed
- `uncertainty_width == p90 - p10` passed
- `0 <= confidence_score <= 1` passed
- `confidence_band in {high, medium, low}` passed
- `population_estimate_final == p50` passed
- `sum_p50 == official_city_total` passed exactly within saved outputs

### Directory separation checks

- canonical `v3` models were written only under `models/v3_uncertainty/`
- canonical `v3` outputs were written only under `outputs/v3_uncertainty/`
- no `v3` files were written into `data/processed/inference_runs`

## Known Phase 4 Fallbacks

The frozen Phase 4 output manifest records the following bounded fallbacks:

- `external_agreement_score = 0.50`
  - neutral fallback because city-specific `v3` external disagreement alignment is not part of Phase 4
- `district_interval_coverage_available = False`
  - interval coverage is reserved for later uncertainty-validation work

These do **not** block Phase 3/4 completion, but they remain explicit limitations of the current frozen output package.

## Outcome

Phase 3 and Phase 4 are functionally completed for the first frozen `v3` package.

What now exists:

- one smoke uncertainty model package
- one full uncertainty model package
- one full four-city frozen inference package
- one canonical city summary table
- one run manifest that records the bounded Phase 4 fallbacks

This means the repository now has a real `v3` execution base rather than only a partial scaffold.

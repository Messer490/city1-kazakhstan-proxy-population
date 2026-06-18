# City1 v3 Directory Conventions

## Purpose

This document freezes where `City1 v3` artifacts must live.

`v2` and `v3` must not share the same output roots except when `v3` reads frozen `v2` dependencies.

## Approved Root Directories

### Model artifacts

- `models/v3_uncertainty/`

Purpose:

- frozen `v3` ensemble artifacts
- model metadata
- feature schema
- city registry snapshot
- run manifest

Write policy:

- `v3` training scripts may write here
- `v2` scripts must not write here

### Inference outputs

- `outputs/v3_uncertainty/`

Purpose:

- calibrated per-city `v3` uncertainty outputs
- city-level summaries derived from the same run

Write policy:

- `v3` inference scripts and `app_v3.py` may write here
- do not write `v3` outputs into `data/processed/inference_runs`

### Validation reports

- `reports/uncertainty_validation_v3/`
- `reports/hotspot_prioritization_v3/`
- `reports/district_interval_coverage_v3/`
- `reports/external_disagreement_alignment_v3/`

Purpose:

- frozen evidence artifacts for the `v3` scientific stack

### Paper-facing report package

- `reports/paper_v3_uncertainty/`

Purpose:

- integrated paper-facing bundle
- summary note, figures, tables, and paper-output manifests

## Run-Level Subdirectory Rule

Each frozen `v3` run must write into a run-specific subdirectory under the approved root.

Pattern:

- `<root>/<run_id>/...`

Examples:

- `models/v3_uncertainty/city1_v3_rf500m_e30_20260618T120000Z/`
- `outputs/v3_uncertainty/city1_v3_rf500m_e30_20260618T120000Z/`
- `reports/uncertainty_validation_v3/city1_v3_rf500m_e30_20260618T120000Z/`

Why:

- prevents overwrite
- keeps training, inference, validation, and report artifacts aligned
- makes freeze manifests simpler

## Run ID Convention

Recommended frozen format:

- `city1_v3_rf500m_e{ensemble_size}_{YYYYMMDDTHHMMSSZ}`

Example:

- `city1_v3_rf500m_e30_20260618T120000Z`

Required properties:

- includes version family: `city1_v3`
- includes fixed model/grid slug: `rf500m`
- includes ensemble size
- includes UTC timestamp

## File Naming Conventions

### Per-city outputs

Inside `outputs/v3_uncertainty/<run_id>/`:

- `almaty_uncertainty_cells.csv`
- `almaty_uncertainty_cells.geojson`
- `astana_uncertainty_cells.csv`
- `shymkent_uncertainty_cells.csv`

Rules:

- use `city_slug`
- use lowercase snake case
- one city per output pair

### Model artifact files

Inside `models/v3_uncertainty/<run_id>/`:

- `ensemble_config.json`
- `training_summary.csv`
- `feature_schema.json`
- `city_registry_snapshot.csv`
- `ensemble_model.joblib`
- `run_manifest.json`

### Validation/report files

Inside each `reports/.../<run_id>/` folder:

- use stable descriptive names
- avoid versionless files like `output.csv`
- include one `run_manifest.json` per report directory when that directory is a terminal frozen artifact set

## Naming Conventions for Cities

### Display name

- `city`
- example: `Almaty`

### Normalized slug

- `city_slug`
- example: `almaty`
- derived from the `v2` normalized naming convention

### Feature filenames

Frozen feature CSV convention remains:

- `data/processed/features_v2_batch1/almaty.csv`
- `data/processed/features_v2_batch1/astana.csv`

## What Must Not Happen

- `v3` must not save canonical outputs into `data/processed/inference_runs`
- `v3` must not save canonical models into `models/trained_stage1_batch1`
- `v3` must not write paper-facing artifacts into `reports/paper_v2_baseline`
- `app_v3.py` must not expose a variable grid in the frozen path if the contract keeps `500 m`

## Existing Scripts Flagged for Update

### Must be updated for path compliance

- `app_v3.py`
  - currently defaults to `data/processed/inference_runs`
- `scripts/predict_city_v3.py`
  - currently defaults to `data/processed/inference_runs`
- `scripts/train_model_v3_uncertainty.py`
  - currently defaults to `models/trained_v3_uncertainty`
- `src/city1/paper_report_v3.py`
  - currently writes to `reports/paper_v3_uncertainty/` root directly rather than a run-specific subdirectory

## Phase 2 Approval Status

Approved as the frozen `v3` directory convention unless later author review requires a narrow adjustment.


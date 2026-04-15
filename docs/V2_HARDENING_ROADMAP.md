# City1 v2 Hardening Roadmap

This roadmap keeps `City1 v2` as the baseline version and strengthens it without turning it into `v3`.

## Goal

Make `City1 v2`:

- scientifically honest
- technically stable
- easier to explain to users and reviewers
- ready for paper preparation without changing the core problem statement

## Fixed Baseline

The baseline is frozen as:

- model: `random_forest`
- grid size: `500 m`
- runtime mode: `calibrated-only`
- current validation protocol: `Leave-One-City-Out`
- current problem statement:
  - `open-data proxy population surface calibrated by official city totals`
- formal frozen scope:
  - `docs/V2_BASELINE_SCOPE.md`

## Phase 1. Transparency And Product Integrity

Objective:
- remove ambiguity between cities that are merely calibratable and cities that are fully validated in the current batch

Tasks:
- maintain `data/external/city_status_registry_v2.csv`
- track, per city:
  - official total available
  - feature generated
  - QA passed
  - included in training
  - validated batch
  - smoke passed
  - saved inference example
- make Streamlit display validated vs calibrated coverage separately

## Phase 2. Stronger Validation

Objective:
- keep the existing cross-city validation and add stricter spatial evaluation

Tasks:
- keep `Leave-One-City-Out` as the main transferability protocol
- add `spatial block CV` inside cities
- document the difference between:
  - unseen-city transferability
  - within-city spatial leakage control

## Phase 3. External Benchmarking

Objective:
- partially compensate for the lack of true grid-level census labels

Tasks:
- search for district-level open statistics where possible
- aggregate predictions from grid to district
- compare model outputs against district-level totals or district-level proxies
- optionally compare against open gridded population surfaces such as WorldPop / GHS-POP where coverage is useful

## Phase 4. Reliability Layer

Objective:
- make data quality visible instead of implicit

Tasks:
- compute an `OSM completeness score`
- report layer sparsity and completeness per city
- show reliability warnings in the app and in paper tables

## Phase 5. Paper Figure Pipeline

Objective:
- generate paper-ready outputs from the new `v2` core, not from legacy notebooks

Tasks:
- add `paper/` or `scripts/paper_figures/`
- produce reproducible:
  - model comparison plots
  - QA summary tables
  - grid-size comparison figures
  - city status tables
  - example maps

## Phase 6. Grid-Size Benchmark

Objective:
- formally justify the current `500 m` default

Tasks:
- compare `250 / 500 / 1000`
- report:
  - calibration factor behavior
  - prediction smoothness
  - stability across cities
  - benchmark agreement where external references exist

## What Belongs To v2 vs v3

Still belongs to `v2 hardening`:

- city status registry
- spatial block CV
- district benchmark layer
- OSM completeness score
- paper/report pipeline
- grid-size benchmark

Should be treated as `v3`:

- satellite features
- accessibility / travel time
- uncertainty maps as a major modeling layer
- explainability maps
- raw mode / estimated-total mode
- major multi-country expansion

## Immediate Next Steps

Completed hardening blocks:

1. City status registry and validated-vs-calibrated app messaging.
2. Spatial block CV in addition to `Leave-One-City-Out`.
3. Formal `250 / 500 / 1000` grid-size benchmark.
4. Reproducible paper/report pipeline.
5. OSM completeness layer.
6. First completed district benchmark: `Almaty`.

Strong-path items still remaining to fully freeze the benchmark story:

1. Complete district benchmark references for `Astana`.
2. Complete district benchmark references for `Shymkent`.
3. Rebuild the status registry and paper report after those two cities are added.
4. Freeze the district benchmark trio as `Almaty + Astana + Shymkent`.

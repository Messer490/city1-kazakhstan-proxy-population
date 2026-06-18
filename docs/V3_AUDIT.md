# City1 v3 Audit

## Scope

This audit covers **Phase 1 only** for `City1 v3`.

- No full v3 training was run.
- No v3 manuscript writing was started.
- `v2` was treated as a dependency source only.
- The goal was to determine what already exists, what is partial, what is broken, and what is missing.

## Repo State at Audit Time

- `v3` is currently a **local work-in-progress layer**, not a frozen released package.
- Several `v3` files are currently **untracked** in git.
- Several shared core files such as `src/city1/inference.py`, `src/city1/contracts.py`, and `src/city1/validation.py` are modified in the working tree.
- The working tree also contains separate `v2` manuscript edits that were **not extended in this audit**.

## Files Inspected

### Primary v3 files

- `app_v3.py`
- `src/city1/uncertainty.py`
- `src/city1/uncertainty_validation.py`
- `src/city1/hotspot_prioritization.py`
- `src/city1/paper_report_v3.py`
- `docs/V3_PROBLEM_STATEMENT.md`
- `manuscript_package_v3/README.md`
- `scripts/train_model_v3_uncertainty.py`
- `scripts/predict_city_v3.py`
- `scripts/run_uncertainty_validation_v3.py`
- `scripts/run_hotspot_prioritization_v3.py`
- `scripts/build_paper_report_v3.py`
- `tests/test_uncertainty.py`
- `tests/test_uncertainty_validation.py`
- `tests/test_hotspot_prioritization.py`

### Shared integration files inspected because v3 depends on them

- `src/city1/inference.py`
- `src/city1/contracts.py`
- `src/city1/validation.py`
- `src/city1/external_benchmark.py`
- `src/city1/district_benchmark.py`
- `src/city1/__init__.py`
- `requirements.txt`
- `requirements-optional.txt`

### Dependency and v2 input artifacts inspected

- `data/external/city_population_reference_v2.csv`
- `data/external/city_status_registry_v2.csv`
- `data/external/district_benchmark/almaty_district_population_reference_v2.csv`
- `data/external/district_benchmark/astana_district_population_reference_v2.csv`
- `data/external/district_benchmark/shymkent_district_population_reference_v2.csv`
- `reports/paper_v2_baseline/`
- `reports/external_benchmark_v2/`
- `reports/district_benchmark_v2/`
- `reports/qualitative_validation_v2/`
- `data/processed/features_v2_batch1/`
- `data/processed/inference_runs/`
- `docs/OPERATIONS_RUNBOOK_V2.md`

## High-Level Status Summary

### Implemented components

- `src/city1/uncertainty.py`
  - deterministic ensemble seed generation
  - bootstrap resampling
  - ensemble training
  - artifact save/load
  - calibrated quantile summary logic
  - relative uncertainty computation
  - confidence-band assignment with completeness downgrade
- `src/city1/inference.py`
  - uncertainty artifact discovery
  - per-city uncertainty inference path
  - per-member calibration before quantile summary
  - v3 output validation hook
- `src/city1/validation.py`
  - `validate_city_output_v3`
- `src/city1/contracts.py`
  - `PROBLEM_STATEMENT_V3`
  - v3 output column constants
- Unit tests
  - uncertainty utilities
  - uncertainty validation helpers
  - hotspot prioritization basics

### Partially implemented components

- `app_v3.py`
  - population map and uncertainty overlay exist
  - confidence-band summary exists
  - save/download flow exists
  - but the UI is not frozen to the v3 spec and cannot currently run because no v3 model artifact exists
- `src/city1/uncertainty_validation.py`
  - LOCO-style uncertainty diagnostics exist
  - district interval helper functions exist
  - external disagreement helper functions exist
  - but the validation stack is incomplete relative to the v3 scientific plan
- `src/city1/hotspot_prioritization.py`
  - hotspot selection by `P50` quantile exists
  - confidence-based splitting exists
  - but the output contract is narrower than the v3 target
- `src/city1/paper_report_v3.py`
  - report collector scaffold exists
  - but it only copies flat CSV summaries and does not build the intended evidence package
- `scripts/build_paper_report_v3.py`
  - script runs successfully
  - but currently creates only a summary scaffold because the underlying v3 evidence artifacts do not yet exist
- `scripts/train_model_v3_uncertainty.py`
  - minimal training entry point exists
  - but artifact outputs are below the desired freeze/report standard
- `scripts/predict_city_v3.py`
  - minimal uncertainty inference entry point exists
  - but outputs go into a v2-style location
- `scripts/run_uncertainty_validation_v3.py`
  - runs fold diagnostics and monotonicity
  - but does not run district interval coverage or external disagreement alignment
- `manuscript_package_v3/`
  - only a placeholder README exists

### Missing components

- no trained `v3` ensemble artifact under `models/`
- no dedicated `models/v3_uncertainty/` package
- no dedicated `outputs/v3_uncertainty/` directory
- no existing `reports/uncertainty_validation_v3/`
- no existing `reports/hotspot_prioritization_v3/`
- no existing `reports/district_interval_coverage_v3/`
- no existing `reports/external_disagreement_alignment_v3/`
- no real `manuscript_package_v3` LaTeX package
- no script dedicated to district interval coverage generation
- no script dedicated to external disagreement alignment generation
- no script for freeze-manifest generation
- no script for city-level uncertainty summary export
- no qualitative uncertainty case builder
- no paper-figure generation layer for v3
- no `confidence_score` field
- no `hotspot_rank` field
- no `hotspot_priority_class` field in the standard per-cell inference output

## Detailed Component Findings

### `app_v3.py`

Status: **partial and risky**

What is good:

- clear uncertainty-aware UI direction
- shows `P50` as final surface
- shows relative uncertainty overlay
- bounded language: "proxy, not truth"

What is risky:

- the sidebar allows `250` to `1000` meter grid sizes even though `docs/V3_PROBLEM_STATEMENT.md` says the v3 grid stays `500 m`
- outputs save to `data/processed/inference_runs`, which mixes v3 products into a v2-style output location
- app cannot currently run end-to-end because no v3 uncertainty model artifact exists
- app does not expose hotspot prioritization outputs
- app does not expose a `confidence_score`

Conclusion:

- good prototype consumer
- not yet a frozen v3 runtime

### `src/city1/uncertainty.py`

Status: **strong core implementation**

What exists:

- deterministic ensemble seeds
- bootstrap sampling
- ensemble training around the existing estimator builder
- artifact save/load
- quantile summary (`P10`, `P50`, `P90`)
- width and relative uncertainty
- confidence-band assignment

What is still missing:

- no explicit numeric `confidence_score`
- default ensemble size is `9`, which is below the target freeze expectation of a larger ensemble
- artifact save format is joblib-heavy and does not yet create:
  - `ensemble_config.json`
  - `training_summary.csv`
  - `freeze_manifest.json`

Conclusion:

- this is the strongest v3 building block
- it is real code, not a placeholder

### `src/city1/uncertainty_validation.py`

Status: **partial**

What exists:

- fold-level diagnostics for error vs uncertainty
- monotonicity summary helper
- district interval aggregation helper
- district interval coverage metrics helper
- external disagreement alignment helper

What is missing:

- no explicit held-out interval coverage metric against weak targets in the main script output
- no hotspot stability analysis across ensemble members
- no qualitative uncertainty case builder
- no standalone report writer for district coverage
- no standalone report writer for external disagreement alignment

Conclusion:

- strong helper layer
- incomplete scientific evidence layer

### `src/city1/hotspot_prioritization.py`

Status: **partial**

What exists:

- hotspot extraction from top quantile of `P50`
- confidence-based prioritization for hotspot cells
- CSV / GeoJSON / markdown summary export

What is missing or mismatched:

- current classes are:
  - `high_priority_high_confidence`
  - `review_required_low_confidence`
  - `monitor_medium_confidence`
- this does **not yet match** the fuller v3 planning interpretation:
  - high-value + high-confidence
  - high-value + low-confidence
  - medium-value + high-confidence
  - low-value + high-uncertainty
- prioritization is hotspot-subset oriented, not a full-city reliability/usefulness classification
- no explicit `hotspot_rank`
- no standard `hotspot_priority_class` field added to all inference outputs

Conclusion:

- useful start
- not yet complete for the planned paper claim

### `src/city1/paper_report_v3.py`

Status: **partial scaffold**

What exists:

- known target report directories
- copy-if-exists behavior
- summary markdown scaffold

What is missing:

- no figure generation
- no tables directory structure
- no outputs directory structure
- no model config export
- no freeze manifest export
- no city summary export
- no integration with a manuscript package

Conclusion:

- report scaffold exists
- paper-facing evidence package does not yet exist

### `scripts/*v3*.py`

Status: **minimal runnable CLI layer**

What exists:

- training entry point
- prediction entry point
- uncertainty validation entry point
- hotspot prioritization entry point
- paper report scaffold entry point

What is missing:

- district interval coverage CLI
- external disagreement alignment CLI
- qualitative uncertainty cases CLI
- freeze-manifest builder
- final paper package builder

## Existing v3 Output / Report / Model Folders

Current status:

- `outputs/` directory: **absent**
- `models/trained_v3_uncertainty/`: **absent**
- `reports/uncertainty_validation_v3/`: **absent**
- `reports/hotspot_prioritization_v3/`: **absent**
- `reports/district_interval_coverage_v3/`: **absent**
- `reports/external_disagreement_alignment_v3/`: **absent**
- `reports/paper_v3_uncertainty/`: **present as scaffold only** (`paper_v3_summary.md`)

Implication:

- v3 code exists
- v3 evidence artifacts do not yet exist

## Dependency Problems

### Confirmed / probable dependency surface

Core requirements already listed:

- `pandas`
- `numpy`
- `scikit-learn`
- `joblib`
- `geopandas`
- `folium`
- `streamlit`
- `streamlit-folium`
- `openpyxl`

Optional requirements:

- `rasterio`
- `catboost`

### Risks

- `rasterio` is optional and the existing v2 runbook explicitly says the current `.venv` does not include it
- v3 external disagreement alignment depends on the external benchmark machinery, which can require `rasterio`
- `catboost` is optional and not relevant for the current v3 core, so it should not become a hidden dependency for the v3 freeze

Conclusion:

- v3 core training/inference path is mostly aligned with the default environment
- external disagreement validation is at risk until `rasterio` availability is standardized for v3

## Data Availability Problems

### Good news

The minimum intended v3 freeze set has v2 dependencies available:

- features exist for:
  - `Almaty`
  - `Astana`
  - `Shymkent`
  - `Semey`
- official totals reference exists
- city status registry exists
- district references exist for:
  - `Almaty`
  - `Astana`
  - `Shymkent`
- v2 report folders exist for baseline dependencies

### Missing data/product layer

- no trained v3 uncertainty ensemble
- no saved v3 uncertainty inference outputs
- no saved hotspot prioritization outputs
- no saved uncertainty validation outputs
- no saved district interval coverage outputs
- no saved external disagreement alignment outputs

## Unclear Assumptions

- whether `models/trained_v3_uncertainty/` is the final intended artifact root or only a temporary prototype location
- whether v3 should keep saving inference outputs into `data/processed/inference_runs` or move to a dedicated `outputs/v3_uncertainty/`
- whether `confidence_score` should be:
  - a normalized inverse relative-uncertainty score
  - a percentile-based stability score
  - or another bounded transformation
- whether hotspot prioritization should apply only to hotspot cells or classify every cell into a planning-usefulness regime
- whether the v3 paper will treat district interval coverage as a main-text table or supplement-first artifact

## Version-Mixing Audit

### v2 / v3 mixing found

- `app_v3.py` saves to `data/processed/inference_runs`
- `scripts/predict_city_v3.py` also saves to `data/processed/inference_runs`
- the app exposes non-frozen grid sizes despite the v3 problem statement keeping `500 m`

### v2 / v4 mixing found

- no obvious LLM / agent / v4 logic was found in the inspected v3 modules

Conclusion:

- no visible v4 contamination
- some v2 storage/runtime conventions still leak into v3

## Uncertainty-Claim Audit

### Positive finding

The inspected v3 wording is mostly well-bounded:

- `docs/V3_PROBLEM_STATEMENT.md` explicitly keeps `proxy, not truth`
- `PROBLEM_STATEMENT_V3` says uncertainty expresses agreement inside an ensemble of calibrated proxy models
- `app_v3.py` uses bounded wording
- `manuscript_package_v3/README.md` uses uncertainty-aware proxy-baseline language

### Remaining risk

- the code currently lacks a fully frozen data contract and validation report layer, so even bounded wording could still look decorative to reviewers until interval coverage and related evidence are actually generated

Conclusion:

- no obvious truth-overclaim in the inspected v3 wording
- the bigger risk is **under-validated uncertainty**, not overclaiming text

## Reproducibility Audit

### What is reproducible already

- deterministic ensemble seeds
- deterministic bootstrap workflow given fixed base random state
- save/load artifact path for the ensemble
- unit tests pass for the core helpers

### What is not reproducibly frozen yet

- no frozen v3 artifact package exists
- no freeze manifest exists
- no dedicated output directories exist
- no dedicated city summary tables exist
- no paper-ready evidence package exists
- current worktree is not clean

Conclusion:

- v3 logic is partially reproducible
- v3 evidence is not yet frozen or packaged

## Commands Tested

### Inspection commands

- `Get-Content -LiteralPath 'C:\Users\Asus\Desktop\1.txt'`
- `Get-Content app_v3.py`
- `Get-Content src\city1\uncertainty.py`
- `Get-Content src\city1\uncertainty_validation.py`
- `Get-Content src\city1\hotspot_prioritization.py`
- `Get-Content src\city1\paper_report_v3.py`
- `Get-Content docs\V3_PROBLEM_STATEMENT.md`
- `Get-Content manuscript_package_v3\README.md`
- `Get-Content src\city1\inference.py`
- `Get-Content src\city1\validation.py`
- `Get-Content src\city1\contracts.py`
- `Get-Content requirements.txt`
- `Get-Content requirements-optional.txt`
- `Get-ChildItem scripts -Name *v3*.py`
- `Get-ChildItem models -Recurse -Name`
- `Get-ChildItem data\processed\inference_runs -Name`
- `git status --short`

### Lightweight runnable checks

- `.\.venv\Scripts\python.exe -m unittest tests.test_uncertainty tests.test_uncertainty_validation tests.test_hotspot_prioritization`
  - result: `OK`
- `.\.venv\Scripts\python.exe scripts\train_model_v3_uncertainty.py --help`
  - result: parser works
- `.\.venv\Scripts\python.exe scripts\predict_city_v3.py --help`
  - result: parser works
- `.\.venv\Scripts\python.exe scripts\run_uncertainty_validation_v3.py --help`
  - result: parser works
- `.\.venv\Scripts\python.exe scripts\run_hotspot_prioritization_v3.py --help`
  - result: parser works
- `.\.venv\Scripts\python.exe -m py_compile app_v3.py src\city1\uncertainty.py src\city1\uncertainty_validation.py src\city1\hotspot_prioritization.py src\city1\paper_report_v3.py scripts\build_paper_report_v3.py scripts\predict_city_v3.py scripts\run_hotspot_prioritization_v3.py scripts\run_uncertainty_validation_v3.py scripts\train_model_v3_uncertainty.py`
  - result: passed
- `.\.venv\Scripts\python.exe scripts\build_paper_report_v3.py`
  - result: script runs and creates `reports/paper_v3_uncertainty/paper_v3_summary.md`

### Negative smoke test

- `.\.venv\Scripts\python.exe scripts\predict_city_v3.py "Semey, Kazakhstan"`
  - result: failed immediately because no v3 uncertainty model artifacts exist

## Errors Encountered

### Real project blocker

- `Inference failed: No v3 uncertainty model artifacts were found under C:\Users\Asus\Downloads\City1-main\City1-main\models`

### Environment / artifact absence findings

- dedicated `outputs/` root for v3 does not exist
- dedicated v3 report directories do not exist
- dedicated v3 model directory does not exist

## Recommended Next Action

Move to **Phase 2 only after the v3 data contract is frozen in writing**.

The immediate next step should be:

1. freeze the v3 directory conventions
2. freeze the per-cell output schema
3. freeze the city-level summary schema
4. decide the exact meaning of `confidence_score`
5. decide whether hotspot prioritization is hotspot-only or full-city
6. remove the variable-grid behavior from the v3 runtime path
7. separate v3 outputs from v2 paths before generating any new artifacts

## Recommended Phase 2 Start Condition

Phase 2 should start only when all of the following are agreed:

- v3 output root is separated from v2
- v3 model artifact root is fixed
- final per-cell schema is written
- final city-summary schema is written
- artifact names are fixed
- missing v3 scripts to be created/fixed are listed
- `confidence_score` definition is chosen
- hotspot class vocabulary is chosen
- initial freeze cities are confirmed as:
  - `Almaty`
  - `Astana`
  - `Shymkent`
  - `Semey`

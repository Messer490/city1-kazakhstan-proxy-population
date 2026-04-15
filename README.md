# City1 v2

City1 v2 is a reproducible geospatial ML baseline for building a calibrated proxy population surface inside a city from open geodata and official city totals. It does not claim true grid-level census reconstruction; it provides a calibrated proxy surface supported by multi-level validation.

## Frozen defaults

- model: `random_forest`
- default grid: `500 m`
- runtime: `calibrated-only`

## Evidence stack

City1 v2 now includes:

- `Leave-One-City-Out` validation
- `spatial block CV`
- `grid-size benchmark`
- district benchmark
- external benchmark
- ablation
- qualitative validation
- reproducible paper package integration

## Paper package

The canonical manuscript-facing package is:

- `reports/paper_v2_baseline/`

It contains the integrated baseline, benchmark, ablation, and qualitative validation tables, figures, and summary note.

## Runtime policy

City1 v2 currently runs in `calibrated-only` mode.

- inference succeeds only for cities present in `data/external/city_population_reference_v2.csv`
- unsupported cities are currently a reference-coverage limitation, not proof of model failure
- the city support breakdown lives in `data/external/city_status_registry_v2.csv`

Current QA-validated demo set:

- `Almaty`
- `Astana`
- `Shymkent`
- `Semey`
- `Taraz`
- `Uralsk`
- `Petropavlovsk`
- `Ust Kamenogorsk`

## Quick start

Install core dependencies:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Run the app:

```powershell
.\.venv\Scripts\python.exe -m streamlit run app_v2.py
```

Run single-city inference:

```powershell
.\.venv\Scripts\python.exe scripts\predict_city_v2.py "Semey, Kazakhstan"
```

Build the integrated paper package:

```powershell
.\.venv\Scripts\python.exe scripts\build_paper_report_v2.py --output-dir reports/paper_v2_baseline
```

## Main project layers

- `src/city1/`
  - production package for feature generation, training, inference, benchmarking, and reporting
- `scripts/`
  - reproducible CLI entry points
- `tests/`
  - unit and smoke-oriented validation
- `docs/`
  - scope, status, runbooks, and paper-facing positioning
- `reports/`
  - QA, evaluation, benchmark, ablation, qualitative, and paper outputs
- `app_v2.py`
  - Streamlit interface for the frozen `v2` runtime

## Key docs

- `docs/V2_BASELINE_SCOPE.md`
- `docs/FINAL_STATUS_V2.md`
- `docs/PAPER_POSITIONING_V2.md`
- `docs/OPERATIONS_RUNBOOK_V2.md`
- `docs/PAPER_REPORT_PIPELINE_V2.md`

City1 v2 is frozen and manuscript-ready within its baseline scope as a reproducible open-data calibrated proxy population surface with multi-level validation.

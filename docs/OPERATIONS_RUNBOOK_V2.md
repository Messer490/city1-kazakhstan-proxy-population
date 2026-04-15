# Operations Runbook v2

This runbook is the final rebuild path for the frozen `City1 v2` baseline. It reflects the manuscript-ready workflow after Day 1-5 and should be treated as the canonical order for reproducing the full paper package.

## Runtime policy

City1 v2 runs in `calibrated-only` mode.

- inference works only for cities present in `data/external/city_population_reference_v2.csv`
- if a city is missing from that reference, `v2` stops by design
- this is a reference-coverage limitation, not a silent model failure

## Frozen defaults

- model: `random_forest`
- default grid: `500 m`
- runtime: `calibrated-only`

## Recommended rebuild order

### 1. Refresh official totals

```powershell
.\.venv\Scripts\python.exe scripts\fetch_kazakhstan_population_tables_v2.py
.\.venv\Scripts\python.exe scripts\build_city_totals_v2.py
```

Primary output:

- `data/external/city_population_reference_v2.csv`

### 2. Build the city status registry

```powershell
.\.venv\Scripts\python.exe scripts\build_city_status_registry_v2.py
```

Primary output:

- `data/external/city_status_registry_v2.csv`

### 3. Generate features

```powershell
.\.venv\Scripts\python.exe scripts\generate_multi_city_features_v2.py --csv-dir data/processed/features_v2_batch1 --geojson-dir data/processed/features_v2_batch1_geojson
```

### 4. Run feature QA

```powershell
.\.venv\Scripts\python.exe scripts\qa_feature_batch_v2.py --features-dir data/processed/features_v2_batch1 --output-dir reports/feature_qa_stage1_batch1
```

Primary output:

- `reports/feature_qa_stage1_batch1/`

### 5. Train models

```powershell
.\.venv\Scripts\python.exe scripts\train_model_v2.py --features-dir data/processed/features_v2_batch1 --model ridge --output-dir models/trained_stage1_batch1
.\.venv\Scripts\python.exe scripts\train_model_v2.py --features-dir data/processed/features_v2_batch1 --model random_forest --output-dir models/trained_stage1_batch1
.\.venv\Scripts\python.exe scripts\train_model_v2.py --features-dir data/processed/features_v2_batch1 --model random_forest --validation-protocol spatial_block --spatial-block-size-meters 2000 --spatial-block-splits 5 --output-dir models/trained_stage1_batch1
```

### 6. Compare training runs

```powershell
.\.venv\Scripts\python.exe scripts\compare_training_runs_v2.py --metrics-dir models/trained_stage1_batch1 --output-csv models/trained_stage1_batch1/model_comparison.csv
```

### 7. Run inference and smoke test as needed

```powershell
.\.venv\Scripts\python.exe scripts\predict_city_v2.py "Semey, Kazakhstan"
.\.venv\Scripts\python.exe scripts\smoke_test_inference_v2.py --place-name "Semey, Kazakhstan"
```

Primary outputs:

- `data/processed/inference_runs/`
- `data/processed/smoke_tests/`

### 8. Run the grid-size benchmark

```powershell
.\.venv\Scripts\python.exe scripts\grid_size_benchmark_v2.py --cities "Almaty, Kazakhstan" "Astana, Kazakhstan" "Semey, Kazakhstan" --cell-sizes 250 500 1000 --output-dir reports/grid_size_benchmark_v2_batch1
```

Primary output:

- `reports/grid_size_benchmark_v2_batch1/`

### 9. Build OSM completeness

```powershell
.\.venv\Scripts\python.exe scripts\build_osm_completeness_report_v2.py --features-dir data/processed/features_v2_batch1 --output-dir reports/osm_completeness_v2
```

Primary output:

- `reports/osm_completeness_v2/`

### 10. Run district benchmark

Example for Almaty:

```powershell
.\.venv\Scripts\python.exe scripts\run_district_benchmark_v2.py --city-name "Almaty" --prediction-geojson data/processed/inference_runs/almaty_kazakhstan__random_forest.geojson --district-reference-csv data/external/district_benchmark/almaty_district_population_reference_v2.csv --output-dir reports/district_benchmark_v2/almaty
```

Primary output:

- `reports/district_benchmark_v2/`

Optional source-catalog rebuild:

```powershell
.\.venv\Scripts\python.exe scripts\build_district_source_catalog_v2.py --output-csv data/external/district_population_table_catalog_v2.csv
```

### 11. Run external benchmark

```powershell
C:\Python310\python.exe scripts\run_external_benchmark_v2.py --output-dir reports/external_benchmark_v2
```

Primary output:

- `reports/external_benchmark_v2/`

Why the system Python command is used here:

- the current `.venv` does not include `rasterio`
- the external benchmark pipeline requires `rasterio` for GeoTIFF aggregation
- this is currently an optional scientific-comparison dependency in `v2`

### 12. Run ablation

```powershell
.\.venv\Scripts\python.exe scripts\run_ablation_study_v2.py --features-dir data/processed/features_v2_batch1 --feature-geojson-dir data/processed/features_v2_batch1_geojson --totals-csv data/external/city_population_reference_v2.csv --models-root models/ablation_v2 --reports-root reports/ablation_v2 --city-slugs almaty astana shymkent --external-benchmark-python C:\Python310\python.exe
```

Primary output:

- `reports/ablation_v2/`

### 13. Run qualitative validation

Scaffold:

```powershell
.\.venv\Scripts\python.exe scripts\run_qualitative_validation_v2.py --stage scaffold --full-inference-dir data/processed/inference_runs --built-form-inference-dir reports/ablation_v2/selected_extras/external_benchmark_inputs/built_form_only --completeness-csv reports/osm_completeness_v2/osm_completeness_summary.csv --registry-csv data/external/qualitative_validation_case_registry_v2.csv --output-dir reports/qualitative_validation_v2 --city-slugs almaty astana
```

Render:

```powershell
.\.venv\Scripts\python.exe scripts\run_qualitative_validation_v2.py --stage render --full-inference-dir data/processed/inference_runs --built-form-inference-dir reports/ablation_v2/selected_extras/external_benchmark_inputs/built_form_only --completeness-csv reports/osm_completeness_v2/osm_completeness_summary.csv --registry-csv data/external/qualitative_validation_case_registry_v2.csv --output-dir reports/qualitative_validation_v2 --city-slugs almaty astana
```

Primary output:

- `reports/qualitative_validation_v2/`

### 14. Build `paper_v2_baseline`

```powershell
.\.venv\Scripts\python.exe scripts\build_paper_report_v2.py --output-dir reports/paper_v2_baseline
```

Primary output:

- `reports/paper_v2_baseline/`

## How to rebuild the full manuscript-ready package

Run the steps above in order, then verify that the final outputs exist in:

- `reports/external_benchmark_v2/`
- `reports/ablation_v2/`
- `reports/qualitative_validation_v2/`
- `reports/paper_v2_baseline/`

The paper-facing package is considered complete only when the Day 2-5 layers have been rebuilt and integrated into `reports/paper_v2_baseline`.

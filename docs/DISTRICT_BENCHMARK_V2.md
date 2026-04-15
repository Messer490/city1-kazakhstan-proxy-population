# District Benchmark v2

City1 v2 now has a district benchmark framework.

## Purpose

The district benchmark is the strongest current way to validate City1 v2 without paid grid-level census labels.

It works by:

1. taking a saved City1 v2 prediction surface
2. fetching district polygons
3. aggregating predicted population from grid cells to districts
4. comparing district predictions to official district-level reference values

## Current status

- completed benchmark city: `Almaty`
- confirmed official district-source path:
  - `Almaty`
  - `Astana`
  - `Shymkent`
- official district-source catalog:
  - `data/external/district_population_table_catalog_v2.csv`

## Current implementation status

First implemented city:

- `Almaty`

Initial official reference file:

- `data/external/district_benchmark/almaty_district_population_reference_v2.csv`

Important:

- rows marked `source_precision=exact` are used in the core metrics
- rows marked `source_precision=lower_bound` are retained in outputs, but excluded from the headline metrics until a stricter direct district table is extracted from `stat.gov.kz`

This keeps the benchmark honest during the transition from district-page sources to the direct statistical district spreadsheets.

## Runtime command

```powershell
.\.venv\Scripts\python.exe scripts\run_district_benchmark_v2.py --city-name "Almaty" --prediction-geojson data/processed/inference_runs/almaty_kazakhstan__random_forest.geojson --district-reference-csv data/external/district_benchmark/almaty_district_population_reference_v2.csv --output-dir reports/district_benchmark_v2/almaty
```

## Outputs

- `district_benchmark_table.csv`
- `district_benchmark_metrics.csv`
- `district_benchmark_bar.png`
- `district_benchmark_scatter.png`
- `district_benchmark_report.md`

## Metrics

The benchmark computes:

- district MAE
- district RMSE
- district MAPE
- district share MAE
- district share RMSE
- Pearson correlation
- Spearman correlation

## Why area-weighted aggregation is used

Grid cells can cross district borders.

To avoid hard assignment bias, City1 v2 allocates each cell's predicted population by intersection area share when aggregating to districts.

## Current roadmap

1. keep `Almaty` as the completed benchmark reference implementation
2. resolve the direct official district values for `Astana`
3. resolve the direct official district values for `Shymkent`
4. rerun the benchmark layer for those two cities
5. rebuild the paper/report and city-status layers

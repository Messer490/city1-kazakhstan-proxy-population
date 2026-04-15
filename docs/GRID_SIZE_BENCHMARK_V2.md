# Grid-Size Benchmark v2

This benchmark is the formal way to compare the core cell-size choices:

- `250 m`
- `500 m`
- `1000 m`

Its purpose is to justify the current production default of `500 m` with reproducible evidence instead of visual intuition alone.

## What it measures

For each city and cell size, the benchmark records:

- runtime
- number of zones
- raw prediction sum
- calibration factor
- calibration distance from `1`
- QA warning count
- OSM warning count
- concentration of predicted population in the top `10%` of cells

## Main outputs

- `grid_size_run_results.csv`
- `grid_size_summary.csv`
- `grid_size_city_recommendations.csv`
- `grid_size_benchmark_report.md`

Optional:

- `city_runs/`
  - saved inference outputs for each city-size combination

## CLI example

```powershell
.\.venv\Scripts\python.exe scripts\grid_size_benchmark_v2.py --cities "Almaty, Kazakhstan" "Astana, Kazakhstan" "Semey, Kazakhstan" --cell-sizes 250 500 1000 --output-dir reports/grid_size_benchmark_v2 --save-city-outputs
```

## Recommendation logic

The benchmark score currently prioritizes:

1. calibration factor closeness to `1`
2. fewer QA warnings
3. fewer OSM warnings
4. lower runtime as a weak tie-breaker

This makes the benchmark suitable for `v2 hardening`.
It is not yet the final scientific ranking layer for a future `v3`.

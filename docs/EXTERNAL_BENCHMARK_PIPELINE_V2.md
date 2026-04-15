# External Benchmark Pipeline v2

This layer compares `City1 v2` against two external gridded population products:

- `WorldPop Kazakhstan 2025`
- `GHS-POP E2025 / EPSG:4326 / 3 arc-second`

## Goal

Strengthen the scientific evidence of `City1 v2` without changing the frozen baseline identity.

This comparison is:

- external
- structural
- non-rescaled in the first pass

It does **not** treat the external products as ground truth.

## Fixed comparison protocol

- cities: `Almaty`, `Astana`, `Shymkent`
- grid: frozen `500 m` `City1 v2` inference grid
- benchmark mode: spatial structure comparison
- no city-total rescaling of `WorldPop` or `GHS-POP`

## Main entry point

```powershell
C:\Python310\python.exe scripts\run_external_benchmark_v2.py --output-dir reports/external_benchmark_v2
```

If the active `.venv` does not include `rasterio`, use an interpreter that does.

## Inputs

- `data/processed/inference_runs/*__random_forest.geojson`
- `data/external/external_benchmarks/worldpop/worldpop_kazakhstan_2025_raw.tif`
- `data/external/external_benchmarks/ghs_pop/*.tif`

## What the pipeline does

1. Load the frozen `City1 v2` inference grid for each city.
2. Reproject the grid to the raster CRS.
3. Aggregate external raster values to the same grid cells.
4. Build aligned per-cell tables:
   - `city1_population`
   - `worldpop_population`
   - `ghs_pop_population`
5. Compute:
   - Pearson correlation
   - Spearman correlation
   - top-decile overlap
   - hotspot IoU

## Outputs

The pipeline writes to:

- `reports/external_benchmark_v2/external_benchmark_metrics.csv`
- `reports/external_benchmark_v2/external_benchmark_summary_by_source.csv`
- `reports/external_benchmark_v2/external_benchmark_report.md`
- `reports/external_benchmark_v2/figures/*`
- `reports/external_benchmark_v2/<city_slug>/external_benchmark_aligned.csv`
- `reports/external_benchmark_v2/<city_slug>/external_benchmark_aligned.geojson`

## Dependency note

`rasterio` is required for raster aggregation. It is not part of the minimal current `v2` runtime, so it is treated as an optional scientific-comparison dependency.

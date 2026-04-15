# Number Alignment Audit

This file records the manuscript-critical numeric anchors that were checked against the frozen `paper_v2_baseline` package.

## Source of truth

All values below were checked against:

- `reports/paper_v2_baseline/paper_report_summary.md`
- `reports/paper_v2_baseline/tables/model_validation_table.csv`
- `reports/paper_v2_baseline/tables/grid_size_summary_table.csv`
- `reports/paper_v2_baseline/tables/district_benchmark_metrics_table.csv`
- `reports/paper_v2_baseline/tables/external_benchmark_summary_table.csv`
- `reports/paper_v2_baseline/tables/ablation_summary_table.csv`
- `reports/paper_v2_baseline/tables/qualitative_validation_case_table.csv`

## Verified manuscript anchors

- LOCO random forest calibrated RMSE: `115.934`
- LOCO random forest calibrated $R^2$: `0.934`
- Spatial block random forest calibrated RMSE: `76.301`
- Frozen 500 m benchmark score: `0.248572`
- Almaty district Pearson: `0.543`
- Almaty district Spearman: `0.657`
- WorldPop Pearson: `0.877`
- GHS-POP Spearman: `0.834`
- GHS-POP top-decile overlap: `0.614`
- GHS-POP hotspot IoU: `0.443`
- Built-form-only calibrated RMSE: `120.656`
- Built-form-only calibrated $R^2$: `0.929`
- Full-model calibration RMSE gain: `135.821`
- Curated qualitative cases: `8`
- Curated qualitative cities: `Almaty` and `Astana`
- OSM completeness context:
  - `Almaty`: `good` (`75.827`)
  - `Astana`: `moderate` (`65.014`)
  - `Shymkent`: `moderate` (`65.541`)

## Scope of this audit

This was a factual alignment pass only.

- It did not add new claims.
- It did not add new experiments.
- It did not change interpretation unless a phrase needed to align with the frozen evidence stack.
- It does not replace the first real compile pass in Overleaf.

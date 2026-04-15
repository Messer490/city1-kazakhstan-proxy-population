# Paper / Report Pipeline v2

This layer rebuilds `reports/paper_v2_baseline` as the single reproducible paper asset package for the frozen `City1 v2` baseline.

## Goal

Avoid going back to legacy notebooks or hand-copied files when preparing article figures and tables.

After Day 5, the paper package combines:

- baseline validation assets
- external benchmark evidence
- ablation evidence
- qualitative validation evidence

## Main entry point

```powershell
.\.venv\Scripts\python.exe scripts\build_paper_report_v2.py --output-dir reports/paper_v2_baseline
```

## Required inputs

Baseline inputs:

- `data/external/city_status_registry_v2.csv`
- `reports/feature_qa_stage1_batch1/city_summary.csv`
- `models/trained_stage1_batch1/*_fold_metrics.csv`
- `reports/grid_size_benchmark_v2_batch1/grid_size_summary.csv`
- `reports/grid_size_benchmark_v2_batch1/grid_size_city_recommendations.csv`
- `reports/osm_completeness_v2/osm_completeness_summary.csv`
- `reports/district_benchmark_v2/*/district_benchmark_metrics.csv`
- `data/processed/inference_runs/*.csv`

Day 2 external benchmark inputs:

- `reports/external_benchmark_v2/external_benchmark_metrics.csv`
- `reports/external_benchmark_v2/external_benchmark_summary_by_source.csv`
- `reports/external_benchmark_v2/figures/figure_external_benchmark_pearson.png`
- `reports/external_benchmark_v2/figures/figure_external_benchmark_hotspot_iou.png`

Day 3 ablation inputs:

- `reports/ablation_v2/ablation_summary.csv`
- `reports/ablation_v2/selected_extras_summary.csv`
- `reports/ablation_v2/figures/figure_ablation_loco.png`

Day 4 qualitative validation inputs:

- `reports/qualitative_validation_v2/qualitative_validation_summary.csv`
- `reports/qualitative_validation_v2/qualitative_validation_report.md`
- `reports/qualitative_validation_v2/figures/figure_qualitative_overview_almaty.png`
- `reports/qualitative_validation_v2/figures/figure_qualitative_overview_astana.png`
- `reports/qualitative_validation_v2/figures/figure_qualitative_cases_almaty.png`
- `reports/qualitative_validation_v2/figures/figure_qualitative_cases_astana.png`

These Day 2-4 inputs are required. The paper build now fails fast if any of them are missing.

## Outputs

Tables under `reports/paper_v2_baseline/tables/`:

- `city_status_table.csv`
- `qa_city_summary_table.csv`
- `model_validation_table.csv`
- `grid_size_summary_table.csv`
- `grid_size_city_recommendations_table.csv`
- `osm_completeness_table.csv`
- `district_benchmark_metrics_table.csv`
- `external_benchmark_summary_table.csv`
- `external_benchmark_metrics_table.csv`
- `ablation_summary_table.csv`
- `ablation_selected_extras_table.csv`
- `qualitative_validation_case_table.csv`

Figures under `reports/paper_v2_baseline/figures/`:

- `figure_model_comparison.png`
- `figure_city_status.png`
- `figure_qa_warnings.png`
- `figure_grid_size_benchmark.png`
- `figure_osm_completeness.png`
- `figure_district_benchmark.png`
- `figure_external_benchmark_pearson.png`
- `figure_external_benchmark_hotspot_iou.png`
- `figure_ablation_loco.png`
- `figure_qualitative_overview_almaty.png`
- `figure_qualitative_overview_astana.png`
- `figure_qualitative_cases_almaty.png`
- `figure_qualitative_cases_astana.png`
- `figure_surface_<city>.png`

Markdown summary:

- `paper_report_summary.md`

## Notes

- Existing baseline figures remain part of the package.
- Qualitative validation figures are copied from the Day 4 output layer; they are not redrawn inside `paper_report.py`.
- The Day 5 paper package is an integration layer only. Status-freeze documents are updated later during Day 6.

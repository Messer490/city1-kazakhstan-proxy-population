# City1 v2 Paper Report

## Baseline status

- Calibrated cities in reference: `10`
- Validated baseline cities: `8`
- Smoke-passed cities: `1`

## Model summary

- `random_forest` under LOCO: calibrated RMSE `115.934`, calibrated R2 `0.934`
- Best validation row in current report: `random_forest` / `spatial_block` with RMSE `76.301`

## Grid-size summary

- Recommended default cell size: `500 m` (benchmark score `0.248572`)

## OSM completeness

- Best completeness in current batch: `uralsk` with score `79.653` and label `good`
- Weakest completeness in current batch: `astana` with score `65.014` and label `moderate`
- Mean completeness score across the batch: `72.740`

## District benchmark

- Available district benchmark cities: `3`
- Fully matched district benchmark cities: `0`
- Partial district benchmark cities: `3`
- Best district benchmark currently available: `Almaty` with RMSE `111379.724` and Pearson r `0.543`

## External benchmark

- Best Pearson benchmark: `worldpop` with Pearson r `0.877`
- Best Spearman benchmark: `ghs_pop` with Spearman r `0.834`
- Best top-decile overlap benchmark: `ghs_pop` with overlap `0.614`
- Best hotspot IoU benchmark: `ghs_pop` with IoU `0.443`

## Ablation

- Full model calibrated RMSE / R2: `115.934` / `0.934`
- Full model calibration RMSE gain: `135.821`
- Strongest non-full ablation: `built_form_only`
- Winner non-full calibrated RMSE / R2: `120.656` / `0.929`

## Qualitative validation

- Qualitative validation cities: `2` (`almaty, astana`)
- Total curated cases: `8`
- `Almaty` has stronger qualitative reading context because OSM completeness is `good` (`75.827`)
- `Astana` should be interpreted more cautiously because OSM completeness is `moderate` (`65.014`)

## Main outputs

- Model comparison figure: `C:\Users\Asus\Downloads\City1-main\City1-main\reports\paper_v2_baseline\figures\figure_model_comparison.png`
- City status figure: `C:\Users\Asus\Downloads\City1-main\City1-main\reports\paper_v2_baseline\figures\figure_city_status.png`
- QA figure: `C:\Users\Asus\Downloads\City1-main\City1-main\reports\paper_v2_baseline\figures\figure_qa_warnings.png`
- Grid-size figure: `C:\Users\Asus\Downloads\City1-main\City1-main\reports\paper_v2_baseline\figures\figure_grid_size_benchmark.png`
- OSM completeness figure: `C:\Users\Asus\Downloads\City1-main\City1-main\reports\paper_v2_baseline\figures\figure_osm_completeness.png`
- District benchmark figure: `C:\Users\Asus\Downloads\City1-main\City1-main\reports\paper_v2_baseline\figures\figure_district_benchmark.png`
- External benchmark Pearson figure: `C:\Users\Asus\Downloads\City1-main\City1-main\reports\paper_v2_baseline\figures\figure_external_benchmark_pearson.png`
- External benchmark hotspot IoU figure: `C:\Users\Asus\Downloads\City1-main\City1-main\reports\paper_v2_baseline\figures\figure_external_benchmark_hotspot_iou.png`
- Ablation figure: `C:\Users\Asus\Downloads\City1-main\City1-main\reports\paper_v2_baseline\figures\figure_ablation_loco.png`
- Qualitative overview figure: `C:\Users\Asus\Downloads\City1-main\City1-main\reports\paper_v2_baseline\figures\figure_qualitative_overview_almaty.png`
- Qualitative overview figure: `C:\Users\Asus\Downloads\City1-main\City1-main\reports\paper_v2_baseline\figures\figure_qualitative_overview_astana.png`
- Qualitative cases figure: `C:\Users\Asus\Downloads\City1-main\City1-main\reports\paper_v2_baseline\figures\figure_qualitative_cases_almaty.png`
- Qualitative cases figure: `C:\Users\Asus\Downloads\City1-main\City1-main\reports\paper_v2_baseline\figures\figure_qualitative_cases_astana.png`
- Population surface example: `C:\Users\Asus\Downloads\City1-main\City1-main\reports\paper_v2_baseline\figures\figure_surface_almaty.png`
- Population surface example: `C:\Users\Asus\Downloads\City1-main\City1-main\reports\paper_v2_baseline\figures\figure_surface_semey.png`

## Tables

- `C:\Users\Asus\Downloads\City1-main\City1-main\reports\paper_v2_baseline\tables\city_status_table.csv`
- `C:\Users\Asus\Downloads\City1-main\City1-main\reports\paper_v2_baseline\tables\qa_city_summary_table.csv`
- `C:\Users\Asus\Downloads\City1-main\City1-main\reports\paper_v2_baseline\tables\model_validation_table.csv`
- `C:\Users\Asus\Downloads\City1-main\City1-main\reports\paper_v2_baseline\tables\grid_size_summary_table.csv`
- `C:\Users\Asus\Downloads\City1-main\City1-main\reports\paper_v2_baseline\tables\grid_size_city_recommendations_table.csv`
- `C:\Users\Asus\Downloads\City1-main\City1-main\reports\paper_v2_baseline\tables\osm_completeness_table.csv`
- `C:\Users\Asus\Downloads\City1-main\City1-main\reports\paper_v2_baseline\tables\district_benchmark_metrics_table.csv`
- `C:\Users\Asus\Downloads\City1-main\City1-main\reports\paper_v2_baseline\tables\external_benchmark_summary_table.csv`
- `C:\Users\Asus\Downloads\City1-main\City1-main\reports\paper_v2_baseline\tables\external_benchmark_metrics_table.csv`
- `C:\Users\Asus\Downloads\City1-main\City1-main\reports\paper_v2_baseline\tables\ablation_summary_table.csv`
- `C:\Users\Asus\Downloads\City1-main\City1-main\reports\paper_v2_baseline\tables\ablation_selected_extras_table.csv`
- `C:\Users\Asus\Downloads\City1-main\City1-main\reports\paper_v2_baseline\tables\qualitative_validation_case_table.csv`

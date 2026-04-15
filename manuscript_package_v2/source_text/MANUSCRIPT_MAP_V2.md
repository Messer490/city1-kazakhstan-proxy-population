# Manuscript Map v2

## Working title

**City1 v2: A Reproducible Open-Data Calibrated Proxy Population Surface Baseline with Multi-Level Validation for Intra-Urban Analysis in Kazakhstan**

## Central claim

**City1 v2 provides a reproducible open-data baseline for intra-urban proxy population surface modeling, calibrated by official city totals and supported by multi-level validation.**

## Formal contributions

1. A reproducible open-data pipeline for intra-urban proxy population surface generation.
2. Official-total calibration for city-level consistency.
3. A multi-level validation stack:
   - `LOCO`
   - `spatial block CV`
   - `district benchmark`
   - `external benchmark`
   - `ablation`
   - `qualitative validation`
4. A reproducible paper/report package that generates figures and tables from code.
5. A disciplined baseline framing for data-scarce urban settings.

## Section map

1. `Introduction`
2. `Related Work`
3. `Study Design and Data`
4. `Method`
5. `Validation Framework`
6. `Results`
7. `Limitations`
8. `Conclusion`

## Main-paper figure map

- `Figure 1`: new conceptual pipeline schematic
- `Figure 2`: `figure_model_comparison.png` + `figure_grid_size_benchmark.png`
- `Figure 3`: `figure_district_benchmark.png` + `figure_osm_completeness.png`
- `Figure 4`: `figure_external_benchmark_pearson.png` + `figure_external_benchmark_hotspot_iou.png`
- `Figure 5`: `figure_ablation_loco.png`
- `Figure 6`: `figure_qualitative_overview_almaty.png` + `figure_qualitative_overview_astana.png`
- `Figure 7`: `figure_qualitative_cases_almaty.png` + `figure_qualitative_cases_astana.png`

## Main-paper table map

- `Table 1`: study coverage summary from `city_status_table.csv` and `osm_completeness_table.csv`
- `Table 2`: model and grid validation summary from `model_validation_table.csv` and `grid_size_summary_table.csv`
- `Table 3`: district benchmark summary from `district_benchmark_metrics_table.csv`
- `Table 4`: external benchmark summary from `external_benchmark_summary_table.csv`
- `Table 5`: ablation summary from `ablation_summary_table.csv`

## Supplement

- `city_status_table.csv`
- `qa_city_summary_table.csv`
- `grid_size_city_recommendations_table.csv`
- `osm_completeness_table.csv`
- `external_benchmark_metrics_table.csv`
- `ablation_selected_extras_table.csv`
- `qualitative_validation_case_table.csv`
- `figure_surface_almaty.png`
- `figure_surface_semey.png`

## Frozen evidence anchors

- calibrated cities in reference: `10`
- validated baseline cities: `8`
- smoke-passed cities: `1`
- `random_forest` under `LOCO`: calibrated RMSE `115.934`, calibrated R² `0.934`
- best validation row overall: `random_forest` / `spatial_block`, RMSE `76.301`
- recommended default grid: `500 m`
- best district benchmark support: `Almaty`, Pearson `0.543`, Spearman `0.657`
- best Pearson external benchmark: `WorldPop`, Pearson `0.877`
- best hotspot benchmark: `GHS-POP`, hotspot IoU `0.443`
- strongest non-full ablation: `built_form_only`, calibrated RMSE `120.656`, calibrated R² `0.929`
- qualitative validation cities: `Almaty`, `Astana`
- curated qualitative cases: `8`

## Writing rules

- Do not add new experiments.
- Do not change the frozen `v2` identity.
- Every numeric claim must be traceable to `reports/paper_v2_baseline`.
- Always say `proxy`, not `truth`.
- District benchmark must be described as partial internal administrative validation.
- External benchmark must be described as structural comparison, not ground truth.
- Qualitative validation must be described as plausibility evidence, not cell-level validation.

## Writing order

1. `Results`
2. `Validation Framework`
3. `Method`
4. `Study Design and Data`
5. `Introduction`
6. `Related Work`
7. `Limitations`
8. `Conclusion`
9. `Abstract`
10. final title cleanup

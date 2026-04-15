# Ablation Study v2

This layer implements the Day 3 `City1 v2` ablation study.

## Goal

Answer two questions without changing the frozen `v2` identity:

- which feature families actually drive the model
- how much performance depends on calibration

## Fixed setup

- model: `random_forest`
- grid: frozen `500 m`
- supervision: unchanged weak labels
- main evaluation: `LOCO`
- selected extras:
  - `spatial_block`
  - external benchmark (`WorldPop` + `GHS-POP`)

## Ablation regimes

- `full_features`
- `built_form_only`
- `transport_only`
- `poi_services_only`

Important rule:

- `Combined_Index` appears only in `full_features`

## Main entry point

```powershell
.\.venv\Scripts\python.exe scripts\run_ablation_study_v2.py --models-root models/ablation_v2 --reports-root reports/ablation_v2
```

If the current `.venv` does not include `rasterio`, the script will reuse the documented external benchmark interpreter when it reaches the selected external benchmark step.

## Outputs

- `models/ablation_v2/<ablation_name>/loco/*`
- `models/ablation_v2/<ablation_name>/spatial_block/*` for selected extras only
- `reports/ablation_v2/ablation_summary.csv`
- `reports/ablation_v2/selected_extras_summary.csv`
- `reports/ablation_v2/ablation_report.md`
- `reports/ablation_v2/figures/figure_ablation_loco.png`

Selected external benchmark outputs are written under:

- `reports/ablation_v2/selected_extras/external_benchmark_inputs/<ablation_name>/`
- `reports/ablation_v2/selected_extras/external_benchmark/<ablation_name>/`

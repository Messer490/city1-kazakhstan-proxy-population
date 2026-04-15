# Spatial Block CV in City1 v2

City1 v2 now supports two validation protocols:

## 1. `leave_one_city_out`

This is the current baseline protocol.

Meaning:
- train on several cities
- validate on a completely unseen city

Best use:
- transferability claims
- cross-city generalization story

Calibration unit during validation:
- city total

## 2. `spatial_block`

This is the new within-city spatial robustness protocol.

Meaning:
- split each city into coarse spatial blocks
- hold out blocks through `GroupKFold`
- train on the remaining blocks and cities

Best use:
- testing sensitivity to spatial leakage
- checking whether the model is only memorizing nearby neighborhoods

Calibration unit during validation:
- held-out spatial block total from the weak target

Important note:
- `spatial_block` does **not** replace `leave_one_city_out`
- the two protocols answer different questions

## Recommended interpretation

Use both protocols together:

- `leave_one_city_out`
  - can the model transfer to a new city?
- `spatial_block`
  - does the model stay stable under spatial separation inside cities?

## CLI examples

Leave-one-city-out:

```powershell
.\.venv\Scripts\python.exe scripts\train_model_v2.py --features-dir data/processed/features_v2_batch1 --model random_forest --validation-protocol leave_one_city_out --output-dir models/trained_stage1_batch1
```

Spatial block CV:

```powershell
.\.venv\Scripts\python.exe scripts\train_model_v2.py --features-dir data/processed/features_v2_batch1 --model random_forest --validation-protocol spatial_block --spatial-block-size-meters 2000 --spatial-block-splits 5 --output-dir models/trained_stage1_batch1
```

## Output files

The model artifact keeps the standard name:

- `random_forest_model_v2.joblib`

Protocol-specific validation files are saved separately, for example:

- `random_forest__leave_one_city_out_fold_metrics.csv`
- `random_forest__spatial_block_fold_metrics.csv`
- `random_forest__leave_one_city_out_oof_predictions.csv`
- `random_forest__spatial_block_oof_predictions.csv`

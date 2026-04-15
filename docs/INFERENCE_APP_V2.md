# Inference and App v2

## What this layer does

The `v2` inference layer is now a clean production-style pipeline:

`city -> feature generation -> model prediction -> calibration by official total -> CSV/GeoJSON output`

Core module: [inference.py](/C:/Users/Asus/Downloads/City1-main/City1-main/src/city1/inference.py)

## Main entry points

- Streamlit app: [app_v2.py](/C:/Users/Asus/Downloads/City1-main/City1-main/app_v2.py)
- Single-city CLI inference: [predict_city_v2.py](/C:/Users/Asus/Downloads/City1-main/City1-main/scripts/predict_city_v2.py)
- End-to-end smoke test: [smoke_test_inference_v2.py](/C:/Users/Asus/Downloads/City1-main/City1-main/scripts/smoke_test_inference_v2.py)

## Run the app

```powershell
.\.venv\Scripts\python.exe -m streamlit run app_v2.py
```

## Run CLI inference

```powershell
.\.venv\Scripts\python.exe scripts\predict_city_v2.py "Semey, Kazakhstan"
```

## Run the smoke test

```powershell
.\.venv\Scripts\python.exe scripts\smoke_test_inference_v2.py --place-name "Semey, Kazakhstan"
```

## Expected behavior

- loads the best available `v2` model by default
- generates city features with the new CRS-safe feature pipeline
- predicts raw proxy population values
- calibrates the city-wide sum to the verified official total
- validates the final output
- saves CSV and GeoJSON outputs

## Runtime policy

City1 v2 currently runs in **calibrated-only** mode.

- the city must exist in [city_population_reference_v2.csv](/C:/Users/Asus/Downloads/City1-main/City1-main/data/external/city_population_reference_v2.csv)
- if no official total is found, the run stops explicitly
- current validated demo cities:
  - `Almaty`
  - `Astana`
  - `Shymkent`
  - `Semey`
  - `Taraz`
  - `Uralsk`
  - `Petropavlovsk`
  - `Ust Kamenogorsk`

## Current best model

At the end of Stage 1 the current leader is:

- `random_forest`
- `ridge` remains a baseline for comparison, not the production default

Artifacts live in [trained_stage1_batch1](/C:/Users/Asus/Downloads/City1-main/City1-main/models/trained_stage1_batch1).

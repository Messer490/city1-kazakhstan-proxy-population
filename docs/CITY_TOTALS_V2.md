# City Totals v2

## Goal

Use a structured official reference table for calibrated `v2` inference and training.

The canonical file is [city_population_reference_v2.csv](/C:/Users/Asus/Downloads/City1-main/City1-main/data/external/city_population_reference_v2.csv).

It keeps:

- the cleaned city name
- the population value
- the reference date
- the provenance
- the verification flag

## What changed

The malformed legacy file `kazakhstan_city_population.csv` is retired from the maintained runtime.

The maintained `v2` reference now uses verified official rows as the calibration backbone for the supported demo cities.

This avoids silently mixing guessed totals into production calibration.

## Official Kazakhstan Sources

For Kazakhstan we now use two official source patterns:

- direct regional statistics page values for:
  - Almaty
  - Astana
  - Shymkent
- regional monthly population spreadsheets for:
  - Semey
  - Taraz
  - Uralsk
  - Petropavlovsk
  - Ust Kamenogorsk

The spreadsheet cache lives in [region_population_tables](/C:/Users/Asus/Downloads/City1-main/City1-main/data/external/region_population_tables).

Supported verified demo cities:

- `Almaty`
- `Astana`
- `Shymkent`
- `Semey`
- `Taraz`
- `Uralsk`
- `Petropavlovsk`
- `Ust Kamenogorsk`

## Rebuild Flow

1. Refresh the official regional spreadsheets:
```powershell
.\.venv\Scripts\python.exe scripts\fetch_kazakhstan_population_tables_v2.py
```
2. Rebuild the structured reference file:
```powershell
.\.venv\Scripts\python.exe scripts\build_city_totals_v2.py
```

## Why this matters

This layer is now good enough to serve as the calibration backbone for `v2` training and inference:

- the training pipeline knows which totals are official
- the app can calibrate grid predictions to verified city totals
- Kazakhstan demo cities can now be trained with verified totals instead of placeholders
- unsupported cities fail explicitly instead of inheriting malformed legacy totals

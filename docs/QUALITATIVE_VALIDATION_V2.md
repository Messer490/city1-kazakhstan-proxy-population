# Qualitative Validation v2

This layer implements the Day 4 qualitative validation package for `City1 v2`.

## Goal

Show that the frozen `City1 v2` surface is spatially meaningful in a city-reading sense:

- hotspot cells align with plausible dense urban structure
- coldspot cells align with plausible open, peripheral, or weakly built structure
- the map does not look like arbitrary noise after calibration

This is **not** a ground-truth census validation layer.

## Fixed setup

- cities: `Almaty`, `Astana`
- grid: frozen `500 m`
- primary surface: `full_features`
- comparison surface: `built_form_only`
- case selection source: `full_features` only
- case lockfile: `data/external/qualitative_validation_case_registry_v2.csv`

## Main entry points

Scaffold candidate zones:

```powershell
.\.venv\Scripts\python.exe scripts\run_qualitative_validation_v2.py --stage scaffold
```

Render the final qualitative package after curating the registry:

```powershell
.\.venv\Scripts\python.exe scripts\run_qualitative_validation_v2.py --stage render
```

## Workflow

1. `scaffold`
   - reads frozen `full_features` surfaces
   - extracts hotspot and coldspot components from the top/bottom deciles
   - writes candidate tables, candidate GeoJSON, and candidate figures
   - seeds the qualitative registry template if it does not yet exist
2. Curate `qualitative_validation_case_registry_v2.csv`
   - choose exactly `H1`, `H2`, `L1`, `L2` for each city
   - provide short interpretation and caution text
3. `render`
   - validates the curated registry
   - writes the final summary CSV, report, selected-case GeoJSON, and figures

## Outputs

Scaffold:

- `reports/qualitative_validation_v2/candidates/<city>_candidate_zones.csv`
- `reports/qualitative_validation_v2/candidates/<city>_candidate_zones.geojson`
- `reports/qualitative_validation_v2/figures/figure_candidate_zones_<city>.png`

Render:

- `reports/qualitative_validation_v2/qualitative_validation_summary.csv`
- `reports/qualitative_validation_v2/qualitative_validation_report.md`
- `reports/qualitative_validation_v2/<city>_selected_cases.geojson`
- `reports/qualitative_validation_v2/figures/figure_qualitative_overview_<city>.png`
- `reports/qualitative_validation_v2/figures/figure_qualitative_cases_<city>.png`

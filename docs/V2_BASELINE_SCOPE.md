# City1 v2 Baseline Scope

`City1 v2 baseline` is frozen as the reproducible open-data baseline of the project.

## Core definition

- Main model: `random_forest`
- Production default grid: `500 m`
- Inference mode: `calibrated-only`
- Main output claim: `calibrated proxy population surface`

## Included scientific package

- `Leave-One-City-Out` validation
- `spatial block CV`
- `grid-size benchmark 250 / 500 / 1000`
- `OSM completeness score`
- `paper/report pipeline`
- district benchmark layer for anchor cities
- external benchmark layer
- ablation layer
- qualitative validation layer

These Day 2-4 additions are hardening layers inside frozen `v2`, not a new scientific version.

## Included product path

- [app_v2.py](/C:/Users/Asus/Downloads/City1-main/City1-main/app_v2.py)
- [src/city1](/C:/Users/Asus/Downloads/City1-main/City1-main/src/city1)
- [scripts](/C:/Users/Asus/Downloads/City1-main/City1-main/scripts)
- [data/external](/C:/Users/Asus/Downloads/City1-main/City1-main/data/external)
- [models/trained_stage1_batch1](/C:/Users/Asus/Downloads/City1-main/City1-main/models/trained_stage1_batch1)

## What v2 does not claim

- It does not reconstruct true census population per grid cell.
- It does not use telecom ground truth.
- It does not include satellite, accessibility, uncertainty, explainability, raw-mode, or estimated-total extensions.

## What is intentionally deferred to v3

- satellite features
- travel-time / accessibility
- uncertainty maps
- explainability maps
- raw mode
- estimated-total mode
- multi-country scaling

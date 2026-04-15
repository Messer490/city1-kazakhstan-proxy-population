# City1 v2 Final Status

City1 v2 is frozen as a manuscript-ready baseline within its stated scope. It is now positioned as a reproducible open-data calibrated proxy population surface baseline with multi-level validation, and no further scientific scope expansion is planned inside `v2`.

## Frozen scope

- model: `random_forest`
- default grid: `500 m`
- runtime: `calibrated-only`
- output claim: `calibrated proxy population surface`

## Completed evidence layers

- `Leave-One-City-Out` validation
- `spatial block CV`
- `grid-size benchmark 250 / 500 / 1000`
- `OSM completeness layer`
- district benchmark layer for anchor cities
- external benchmark comparison
- ablation study
- qualitative validation
- integrated `paper_v2_baseline` package

## Current manuscript-ready identity

City1 v2 is a reproducible open-data system that allocates official city totals across a gridded intra-urban surface using weak supervision from geospatial proxy features. It is supported by internal administrative validation, external benchmark comparison, ablation evidence, qualitative validation, and reproducible reporting.

## What is now supported

- reproducible feature generation, training, inference, QA, and reporting
- official-total calibration at the city level
- cross-city transfer evaluation
- within-city robustness evaluation
- paper-ready figures, tables, and summary outputs in `reports/paper_v2_baseline`

## Remaining limitations

- no true grid-level census labels
- weak supervision remains part of the target construction
- district validation is partial administrative validation, not full ground-truth census
- OSM quality varies across cities
- no uncertainty layer in `v2`
- no explainability layer in `v2`
- no satellite or accessibility layer in `v2`
- no `raw` or `estimated_total` mode in `v2`

## Scope boundary

The following items are intentionally outside the frozen `v2` scope and remain future-version topics:

- satellite features
- travel-time or accessibility extensions
- uncertainty maps
- explainability maps
- `raw` inference mode
- `estimated_total` inference mode
- broader multi-country scaling

## Final verdict

City1 v2 is manuscript-ready as a reproducible open-data calibrated proxy population surface baseline with multi-level validation.

City1 v2 is now considered manuscript-ready within its frozen baseline scope.

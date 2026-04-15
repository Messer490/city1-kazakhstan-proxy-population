# External Benchmark Scouting v2

This note records the fixed `Day 1` protocol for external benchmark selection in `City1 v2`.

## Purpose

The goal of this step is to select external gridded population products that are:

- methodologically relevant
- temporally acceptable for the current `v2` story
- practically comparable to the frozen `500 m` baseline

These products are not treated as ground truth. They are used as independent structural benchmarks for the `Almaty`, `Astana`, and `Shymkent` surfaces.

## Scope

Fixed Day 1 scope:

- cities: `Almaty`, `Astana`, `Shymkent`
- grid: `500 m` only
- comparison mode: spatial structure only
- no city-total rescaling of the external benchmark in the first pass

## Candidate Products

### WorldPop

Status: `selected as primary benchmark`

Why:

- direct Kazakhstan-specific product is available
- nominal year `2025` is close to the current `v2` official-total story
- standard benchmark family in gridded population research

Current Day 1 file:

- `data/external/external_benchmarks/worldpop/worldpop_kazakhstan_2025_raw.tif`

Official source:

- `https://hub.worldpop.org/geodata/summary?id=73967`

### GHS-POP R2023A

Status: `selected as secondary benchmark`

Chosen product:

- `GHS_POP_E2025_GLOBE_R2023A_4326_3ss_V1_0`

Why this exact choice:

- `2025` matches the current external-benchmark epoch
- `EPSG:4326` is easier to harmonize into the frozen `City1 v2` grid workflow
- `3 arc-second` resolution preserves meaningful intra-urban structure before aggregation to `500 m`
- tile-based download is more practical than pulling the whole globe in a single file

Why not the alternatives shown on the GHSL page:

- `4326_30ss` is too coarse for the first-pass `500 m` comparison
- `54009_1000` is also too coarse for the first-pass `500 m` comparison
- `54009_100` is scientifically usable but unnecessarily heavy for a strict Day 1 scouting pass and less convenient than `4326_3ss` for tile-based city clipping

Preferred download mode:

- choose the `GHS_POP_E2025_GLOBE_R2023A_4326_3ss` product
- download by tiles, not the single global file

Expected Day 1 tile set:

- `R4_C26` for `Astana`
- `R5_C25` for `Shymkent`
- `R5_C26` for `Almaty`

These tile IDs follow the official GHSL tiling grid and should be verified after download against the exact city boundary clips.

Current Day 1 staged files:

- `data/external/external_benchmarks/ghs_pop/GHS_POP_E2025_GLOBE_R2023A_4326_3ss_V1_0_R4_C26.tif`
- `data/external/external_benchmarks/ghs_pop/GHS_POP_E2025_GLOBE_R2023A_4326_3ss_V1_0_R5_C25.tif`
- `data/external/external_benchmarks/ghs_pop/GHS_POP_E2025_GLOBE_R2023A_4326_3ss_V1_0_R5_C26.tif`

Supporting metadata kept locally:

- `data/external/external_benchmarks/ghs_pop/metadata/GHS_POP_GLOBE_R2023A_input_metadata.xlsx`
- `data/external/external_benchmarks/ghs_pop/metadata/GHSL_Data_Package_2023_light.pdf`

Official sources:

- `https://data.jrc.ec.europa.eu/dataset/2ff68a52-5b5b-4a22-8f40-c41da8332cfe`
- `https://human-settlement.emergency.copernicus.eu/ghs_pop2023.php`

### HRSL / Meta

Status: `optional audit benchmark only`

Why optional:

- weaker temporal fit for the current strict `v2` pass
- more ambiguity in coverage and provenance for the present comparison package

Official references:

- `https://www.ciesin.columbia.edu/data/hrsl/`
- `https://www.popgrid.org/data-for-good-meta`

## Selection Rubric

The Day 1 benchmark choice is based on the following criteria:

- Kazakhstan coverage
- temporal fit to the current `v2` story
- accessibility and download practicality
- methodological relevance for residential population mapping
- interpretability for manuscript writing
- compatibility with the fixed `500 m` comparison protocol

Decision:

- primary benchmark: `WorldPop`
- secondary benchmark: `GHS-POP`
- optional audit benchmark: `HRSL / Meta`

## Population Semantics

This check is important before any comparison:

- `City1 v2` produces a calibrated proxy residential population surface
- `WorldPop` is used as an external modelled population surface
- `GHS-POP` is explicitly described by GHSL as a residential population grid

The first-pass comparison therefore focuses on structural agreement, not on claiming one product as the truth source over the others.

## Comparison Policy

First-pass policy:

- compare spatial structure as-is
- do not rescale the external benchmark to the `City1` official city total
- clip the external raster to the same city boundary used by `City1 v2`
- aggregate the external raster to the frozen `500 m` `City1` grid

Planned first-pass metrics:

- Pearson correlation
- Spearman correlation
- top-decile overlap
- hotspot IoU

Hotspot definition:

- hotspot = top `10%` of cells by value inside each city surface

## Folder Contract

Expected layout:

```text
data/external/external_benchmarks/
├── worldpop/
├── ghs_pop/
├── hrsl/
└── manifests/
```

Current naming contract:

- `worldpop/worldpop_kazakhstan_2025_raw.tif`
- `ghs_pop/` keeps official GHSL raw tile names
- `hrsl/` keeps official raw names if later added

## Exact Download Guidance

### Already available

- `WorldPop Kazakhstan 2025` is already staged in the project.

### Still needed

No additional GHSL raw files are required for the strict Day 1 pass.

The global `12G` single-file archive is not required for the current `v2` benchmark protocol and should not be used unless a later robustness pass explicitly needs it.

## Day 1 Deliverables

The Day 1 scouting step is complete when the project has:

- this note
- a benchmark manifest
- the external benchmark folder contract
- the fixed benchmark selection decision
- the exact download guidance for the next step

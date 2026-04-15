# Tone Consistency Pass Checklist

Use this checklist before polishing the Introduction and before any submission-facing export.

## Core framing

- `City1 v2` is described as a `reproducible open-data calibrated proxy population surface baseline`.
- The manuscript does **not** claim `true reconstruction`, `ground-truth grid census`, or `exact population per cell`.
- The frozen production identity is consistent everywhere:
  - `random forest`
  - `500 m`
  - `calibrated-only`

## Validation language

- `LOCO` is described as transferability to unseen cities.
- `Spatial block CV` is described as within-city robustness / leakage control.
- `District benchmark` is always described as `partial internal administrative validation`.
- `External benchmark` is always described as `structural comparison`, not truth validation.
- `Qualitative validation` is always described as `plausibility evidence`, not cell-level validation.

## Claims discipline

- No section promises more than the figures and tables actually support.
- No section implies that calibration alone makes the surface ground truth.
- No section implies that OSM completeness is a direct accuracy metric.
- No section turns the app or interface into a scientific contribution of the paper.

## Section-by-section checks

### Abstract

- Includes proxy framing.
- Includes calibration.
- Includes multi-level validation.
- Includes bounded final sentence.
- Does not read like a metric dump.

### Introduction

- Frames the problem as intra-urban analysis under label scarcity.
- Motivates open-data baseline need.
- Ends with contributions that match the frozen manuscript scope.

### Related Work

- Positions the paper as a baseline contribution.
- Connects to gridded population mapping, top-down disaggregation, open-data proxy methods, and validation gaps.
- Does not overclaim novelty beyond what the manuscript actually provides.

### Method

- Explains weak supervision clearly.
- Explains calibration clearly.
- Keeps `proxy, not truth` language throughout.
- Does not become a code README.

### Validation Framework

- Makes each evidence layer answer a distinct methodological risk.
- Avoids collapsing all evidence into one generic notion of accuracy.

### Results

- Interprets findings without overselling them.
- Keeps district benchmark and qualitative validation properly bounded.
- Aligns all numbers with the frozen tables.

### Conclusion

- Restates the bounded baseline contribution.
- Reaffirms limitations.
- Pushes `v3` topics outside the current paper.

## Figures and tables

- Main-paper figures remain locked to Figures 1--6.
- Curated qualitative case panels remain supplement material by default.
- Streamlit screenshots stay out of the main paper.
- Tables 1--5 are treated as core evidence, not optional extras.

## Final pre-submission checks

- Run a number-by-number pass against:
  - `source_text/paper_report_summary.md`
  - `tables/*.csv`
  - `tables_tex/*.tex`
- Clean up `refs.bib` metadata where entries still use `and others`.
- Make sure titles, captions, and prose all use the same naming conventions.

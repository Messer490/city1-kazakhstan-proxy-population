# City1 v3 Paper-Facing Evidence Package

## What this package is

This package is the frozen Phase 7 evidence bundle for City1 v3. It consolidates Phase 3-6 artifacts into paper-facing tables, figures, summaries, a source index, and a freeze manifest.

## How it was generated

- built from existing frozen artifacts for run_id `city1_v3_rf500m_e20_20260618T040646Z`
- no model retraining was performed in Phase 7
- no new science was introduced in Phase 7
- v2 manuscript and v2 results were not modified

## Folder meanings

- `tables/`: compact paper-ready CSV tables
- `figures/`: lightweight paper-ready figures
- `outputs/`: curated copied Phase 3-6 source outputs used for the package
- `limitations/`: bounded-claim guidance for Phase 8
- `source_index/`: source inventory and partial-input registry

## Strongest results

- hotspot stability and hotspot-class separation
- confidence-band separation of uncertainty burden
- Almaty as the strongest freeze-city hotspot-screening case

## Partial or mixed results

- interval coverage is mixed
- external disagreement alignment is mixed or negative
- district interval coverage remains partial

## How Phase 8 should use the package

- use `paper_summary.md` for the high-level manuscript framing
- use `tables/` and `figures/` as the direct source for manuscript drafting
- carry all limitations from `limitations/` into the manuscript explicitly

## What must not be claimed

- v3 does not estimate true census uncertainty
- confidence_score is not a truth probability
- district evidence does not prove cell-level accuracy
- external products are not ground truth

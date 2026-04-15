# Paper Positioning v2

## Core framing

City1 v2 should be presented as a reproducible open-data calibrated proxy population surface baseline with multi-level validation. It is most useful as a transparent and practical system for data-scarce urban settings where true grid-level census labels are unavailable.

## What the paper is

- a baseline paper for intra-urban proxy population surface estimation
- an open-data urban population disaggregation system
- a paper about official-total calibration under weak supervision
- a paper with multi-level validation rather than single-metric model reporting

## What the paper is not

- true census reconstruction
- household-level truth
- telecom-equivalent ground truth
- a digital twin
- a multimodal `v3` or `v4` system

## Main contribution

The paper's contribution is the combined baseline system:

- official-total calibration
- cross-city transfer logic
- multi-level validation stack
- reproducible CLI, app, and report pipeline

The main value is the complete reproducible package, not a claim of exact cell-level truth.

## Recommended scientific phrasing

Use phrases such as:

- `proxy population surface`
- `calibrated by official city totals`
- `weak supervision`
- `multi-level validation`
- `spatial plausibility`
- `open-data baseline`

Avoid phrases such as:

- `exact population per cell`
- `ground-truth grid census`
- `true reconstruction`
- `validated truth at every grid cell`

## Validation framing

- `LOCO` supports transferability claims across cities.
- `spatial block CV` supports within-city robustness claims under reduced spatial leakage.
- `district benchmark` should be described as partial internal administrative validation.
- `external benchmark` should be described as independent structural comparison against existing population surfaces.
- `ablation` should be described as feature-family evidence and calibration-dependence evidence.
- `qualitative validation` should be described as spatial plausibility evidence, not ground truth.

## Reviewer-facing tone

The reviewer-facing tone should stay:

- practical
- transparent
- reproducible
- bounded in claims

The strongest honest story is that City1 v2 offers a scientifically disciplined baseline for data-scarce settings, not that it reconstructs true census population at the grid-cell level.

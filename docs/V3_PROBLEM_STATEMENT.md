# City1 v3 Problem Statement

`City1 v3` is an additive extension of the frozen `v2` baseline rather than a full system rewrite.

## Frozen Core

- geography stays Kazakhstan-only
- grid stays `500 m`
- core model family stays `random_forest`
- official-total calibration remains mandatory
- the paper remains `proxy, not truth`

## New v3 Claim

`City1 v3` produces a calibrated proxy population surface together with an uncertainty and confidence layer under missing cell-level truth.

## What v3 Adds

- ensemble-of-runs uncertainty around the frozen `v2` random-forest core
- interval outputs: `P10`, `P50`, `P90`
- relative uncertainty and confidence-band outputs
- uncertainty-specific validation
- one bounded practical use case: uncertainty-aware hotspot prioritization

## What v3 Does Not Add

- multi-country scaling
- full satellite or accessibility expansion
- model-family competition as the main paper story
- truth-recovery claims at cell level
- large competitor-comparison framing

## Paper Identity

The `v3` paper is not "a better model won".  
It is: **an uncertainty-aware calibrated baseline under missing cell-level truth**.

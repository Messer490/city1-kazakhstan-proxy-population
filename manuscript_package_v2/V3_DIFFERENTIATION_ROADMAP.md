# City1 v2: V3 Differentiation Roadmap

This note records items that are intentionally out of scope for the frozen `City1 v2` manuscript so they do not drift back into the current paper during final polishing.

## Explicitly excluded from the current `v2` paper

- competitor-comparison section in the core manuscript
- feature-level explainability claims beyond the frozen family-level ablation evidence
- uncertainty or confidence surfaces
- downstream case-study experiments
- multimodal satellite or accessibility expansion
- Streamlit or UI-demo material in the scientific core

## Why these items are excluded

The current manuscript is intentionally framed as a reproducible open-data baseline with official-total calibration and multi-level validation under missing cell-level truth. The goal of the `v2` hardening cycle is to make that baseline clearer, richer, and more inspectable without adding new science or shifting the paper identity.

## Likely `v3` upgrade directions

- feature explainability layer:
  - permutation importance
  - family-to-feature interpretation
  - error geography
- uncertainty layer:
  - confidence surface
  - uncertainty-aware reporting
- one carefully bounded downstream use case:
  - service siting
  - hotspot-aware prioritization
  - district screening
- multimodal signal expansion:
  - remote sensing
  - accessibility
  - broader environmental covariates

## Practical rule

If a proposed addition would require a new experiment, a new benchmark, a new claim about truth recovery, or a new application study, it belongs to `v3`, not to the frozen `v2` paper.

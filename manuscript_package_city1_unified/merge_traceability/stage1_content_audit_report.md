# Stage 1 Content Audit Report

## Scope

Audit target: `manuscript_package_v2`, `manuscript_package_v3`, `manuscript_package_city1_unified`, their supplements, supporting reports, tables, figures, and outputs.

## Summary

The unified manuscript already preserves the core scientific spine of both source packages. The deterministic Stage 1 logic, the uncertainty-aware Stage 2 logic, and the future-tool bridge are all present in the unified framework. The main issue is not loss of science, but compression: several reviewer-facing explanations are shorter than they should be for a final master manuscript.

## What is already well covered in unified

- deterministic calibrated proxy surface
- official-total calibration
- Random Forest vs ridge comparison
- 500 m grid choice
- district benchmark and external structural comparison
- built-form-dominant ablation story
- calibrated ensemble uncertainty layer
- P10/P50/P90 interpretation
- confidence score and confidence bands
- hotspot classes and hotspot stability
- bounded uncertainty validation scope
- future LLM bridge as future work only

## What is currently compressed and should later be expanded

- weak-target circularity framing
- why the weak target is proxy allocation, not truth
- why district evidence is only partial administrative support
- why WorldPop and GHS-POP are complementary structural comparators
- why Stage 1 and Stage 2 need each other conceptually
- why hotspot stability is the strongest uncertainty evidence

## Where material lives

- Main paper: `sections/`
- Supplement: `supplement/sections/` and `supplement/tables_tex/`
- Traceability: `merge_traceability/`

## Stage 1 output

The merge map has been created at `merge_traceability/content_merge_map.csv`.
It records where each scientific idea appears in V2, V3, and the unified package, plus whether it should be preserved, expanded, rewritten, moved to supplement, or left as is.

## Stage 1 conclusion

No major scientific idea appears lost. The unified paper is structurally correct, but it still needs Stage 2 rewriting to restore the explanatory depth that was compressed during the first merge.

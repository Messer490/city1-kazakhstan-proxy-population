# City1 v4 Paper Summary

## Suggested Titles

1. City1 v4: A Tool-Grounded LLM Assistant for Reliability-Aware Interpretation of Proxy Population Surfaces
2. City1: From Calibrated Proxy Population Surfaces to Tool-Grounded LLM Interpretation for Data-Scarce Urban Analysis
3. Tool-Grounded LLM Interpretation of Uncertainty-Aware Proxy Population Surfaces in Data-Scarce Cities

## Short Pitch

City1 v4 adds a controlled interpretation layer above frozen calibrated proxy population and uncertainty-aware screening outputs. Local tools assemble closed-world evidence packets; deterministic fallback, optional Gemini generation, local retrieval/cache, and claim-boundary guardrails then produce answers with explicit provenance and cautions.

## Research Questions

1. Can a tool-grounded assistant expose local V2/V3 evidence without changing the population model?
2. Can deterministic fallback preserve usability when an external LLM is unavailable?
3. Can claim-boundary guardrails identify and rewrite census-truth, probability, hotspot-truth, and automated-policy overclaims?
4. Can an offline benchmark make interpretation quality and robustness reproducibly inspectable?

## Contributions

- A closed-world local evidence-tool layer over frozen City1 artifacts.
- A deterministic fallback path for reproducible, API-independent answers.
- Optional Gemini generation constrained by the same compact evidence packet.
- Deterministic guardrails for scientific claim boundaries and evidence visibility.
- A local cache and City1-only mini-RAG layer that creates no new evidence.
- An offline benchmark with 72 questions and 288 evaluated cases across 4 configurations.

## Method and Evaluation Summary

V4 routes a user question to local evidence tools, builds a compact packet, optionally adds local retrieval snippets, checks the cache, invokes fallback or Gemini, and applies deterministic guardrails before display. The frozen Phase 8 package contains 72 questions, 288 question/configuration cases, and 4 configurations. The benchmark measures evidence use, grounding, fallback robustness, cache behavior, completeness, limitation awareness, and detected unsafe wording. It does not measure population prediction accuracy.

## Limitations and Claim Boundaries

V4 inherits the missing cell-level census truth and proxy-uncertainty boundaries of V2/V3. Gemini is optional and quota-dependent. Retrieval is local only. Heuristic metrics and pattern guardrails do not replace human scientific review. Full V3 reliability interpretation is limited to Almaty, Astana, Semey, and Shymkent.

## Final Scientific Identity

City1 v4 is a controlled, tool-grounded LLM interpretation assistant for calibrated and uncertainty-aware proxy population surfaces. It supports interpretability, usability, evidence linking, fallback robustness, and claim-boundary discipline without altering the underlying calibrated proxy population model.

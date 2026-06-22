# 6. Evaluation Design

The fixed question bank contains 72 questions spanning city overview, hotspot interpretation, uncertainty/confidence, limitations, dangerous overclaims, methods, selected cells, city comparison, partial support, and Russian-language cases. Four configurations are evaluated: fallback only, Gemini requested with fallback, fallback with cache, and claim checker only.

Metrics cover claim-boundary interventions, critical interventions, evidence usage, grounding, fallback, cache hits, missing artifacts, deterministic completeness, limitation awareness, unsafe phrase counts before and after guardrails, latency, and character estimates. The evaluation is offline and does not evaluate population prediction accuracy.

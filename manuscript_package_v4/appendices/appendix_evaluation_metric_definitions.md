# Appendix D: Evaluation Metric Definitions

- **Claim-boundary intervention rate:** share of responses whose pre-final guardrail severity is medium, high, or critical.
- **Critical intervention rate:** share of responses with critical detected wording.
- **Evidence usage rate:** share with non-empty `evidence_used`.
- **Grounding score:** deterministic response-schema and evidence-visibility score; not truth accuracy.
- **Fallback rate:** share generated through deterministic fallback.
- **Cache hit rate:** share served from a guarded local cache.
- **Missing-artifact rate:** share exposing unavailable local evidence.
- **Completeness:** deterministic presence of summary, evidence, cautions, next checks, and expected terms.
- **Limitation awareness:** deterministic coverage of relevant claim-boundary language.
- **Unsafe phrase count:** rule matches before and after guardrail processing.
- **Latency and character estimates:** operational measurements, not model-quality metrics.

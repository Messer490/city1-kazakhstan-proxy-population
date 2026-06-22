# V4 Claim-Boundary Summary

## Allowed Claims

- V4 reads and explains frozen City1 evidence through local tools.
- V4 can support reliability-aware screening and manual review.
- Deterministic fallback improves operational robustness when Gemini is unavailable.
- Guardrails reduce unsupported scientific wording and expose interventions.
- Cache improves repeatability and API economy without creating evidence.

## Forbidden Claims

- True or exact cell-level census reconstruction.
- True census uncertainty or probabilistic coverage guarantees.
- `confidence_score` as probability of correctness.
- Hotspot classes as verified population truth.
- WorldPop or GHS-POP as ground truth.
- LLM or Gemini as improving population prediction accuracy.
- Fully automated policy decisions without human review.

## Safe Terminology

Use `calibrated proxy population surface`, `proxy ensemble spread`, `interpretation-confidence score`, `screening candidate`, `structural comparator`, `evidence-linked explanation`, and `manual review`.

## Enforcement

`src/city1/llm_guardrails.py` applies deterministic multilingual pattern checks, evidence-grounding checks, severity scoring, and conservative rewrites. These rules reduce overclaiming but do not verify factual truth or replace scientific review.

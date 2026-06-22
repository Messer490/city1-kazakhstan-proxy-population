# City1 v4 Author Notes

## Emphasize

- V4 is an interpretation layer over frozen V2/V3 evidence.
- Every answer exposes evidence sources, missing artifacts, and claim boundaries.
- Deterministic fallback makes the system usable without an external model.
- Guardrails and evaluation make scientific language discipline inspectable.
- Cache and local retrieval improve reuse and evidence access but create no evidence.

## Do Not Overclaim

Do not state that V4 improves population accuracy, validates census truth, estimates true uncertainty, verifies hotspots, or supports unreviewed policy automation. Do not equate `confidence_score` with probability of correctness.

## Reviewer Risks

The largest risks are chatbot novelty without scientific evaluation, circular self-scoring, deterministic metric limitations, narrow geographic support, and optional-provider dependence. Address them with traceability, offline fallback, explicit heuristic-metric labels, frozen artifacts, and bounded claims.

## Response to "Why LLM?"

The LLM is not used to predict population. It is a language interface over structured local tools that can explain heterogeneous evidence, expose limitations, and support multiple question types. The deterministic fallback demonstrates that evidence access and claim control do not depend on the LLM.

## Response to "Does LLM Improve Accuracy?"

No. V4 does not change V2/V3 estimates or their validation. Its evaluated contribution concerns interpretation support, evidence linking, robustness under provider limits, and claim-boundary discipline.

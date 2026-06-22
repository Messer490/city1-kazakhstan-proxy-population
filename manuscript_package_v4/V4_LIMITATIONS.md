# City1 v4 Limitations

- City1 has no true cell-level census labels; V2 remains a calibrated proxy surface.
- P10/P50/P90 and derived fields do not represent true census uncertainty.
- Gemini is optional, key- and quota-dependent, and may be unavailable.
- V4 uses no internet RAG; retrieval is restricted to local City1 artifacts.
- The benchmark evaluates interpretation quality, not population prediction accuracy.
- Cache hit rate depends on repeated or sufficiently similar questions.
- Current evaluation metrics are deterministic and heuristic unless later complemented by blinded human review.
- Pattern guardrails can miss novel paraphrases and require linguistic regression tests.
- Full V3 reliability mode is limited to Almaty, Astana, Semey, and Shymkent.
- V4 is an interpretation-support system, not an automated policy decision system.

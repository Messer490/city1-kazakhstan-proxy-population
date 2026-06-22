# 5. Fallback, Guardrails, and Local Cache

The deterministic fallback implements the same public response schema as the optional Gemini path. It supports city briefs, hotspot and uncertainty explanations, selected-cell explanations, comparisons, general questions, reviewer-safe answers, and claim checking.

Guardrails detect census-reconstruction, true-uncertainty, probability, verified-hotspot, external-ground-truth, LLM-accuracy, automated-policy, and fake-precision claims. Unsafe wording is replaced with conservative terminology while preserving evidence metadata. The cache stores only guarded responses and keys entries by normalized request and evidence hash. Local mini-RAG retrieves snippets only from City1 artifacts and creates no new evidence.

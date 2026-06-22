# 7. Results

The frozen Phase 8 package contains 72 questions, 288 question/configuration cases, and 4 configurations. In the fallback-safe run, all configurations completed without a Gemini key. Evidence usage and grounding remained visible in the generated result records, the intentional repeated question produced an exact cache hit, and the final guarded answers contained 0 detected forbidden phrases after processing.

Claim-boundary intervention rates should be read as guardrail activity on risky inputs or intermediate payloads, not as unsafe-final-answer rates. Claim-checker completeness is lower by design because it returns compact verdicts rather than full city briefs. These results establish operational robustness and claim discipline only; they do not validate the population surface.

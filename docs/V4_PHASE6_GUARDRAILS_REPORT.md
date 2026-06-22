# City1 v4 Phase 6 - Claim-Boundary Guardrails Report

## Status and purpose

Phase V4.6 is complete. City1 v4 now has a deterministic, local guardrail layer that checks scientific wording, response structure, and local-evidence grounding before an answer is displayed.

The guardrail layer is a scientific claim-boundary validator, not a truth verifier. It does not prove that an answer is correct; it reduces overclaiming and enforces the City1 framework's interpretation boundaries.

## Implemented files

- `src/city1/llm_guardrails.py` - deterministic detection, severity, grounding, rewrite, and response-guard API.
- `tests/test_llm_guardrails.py` - claim and grounding unit tests.
- `docs/V4_PHASE6_GUARDRAILS_REPORT.md` - this implementation record.

Modified:

- `app_v4.py` - every UI-generated response now passes through `guard_response` before display or download.
- `tests/test_app_v4_smoke.py` - session-state and report guardrail coverage.

No frozen V2/V3 output, report, model, evidence table, or manuscript result was modified.

## Implemented guardrail functions

- `get_guardrail_rules()`
- `check_answer_for_forbidden_claims(text, language="en")`
- `check_response_dict(response, language="en")`
- `rewrite_unsafe_answer(text, violations, language="en")`
- `guard_response(response, language="en", auto_rewrite=True)`
- `validate_evidence_grounding(response)`
- `get_guardrail_capabilities()`

All outputs are JSON-serializable. The implementation uses explicit regular expressions, clause-aware negation handling, structured response checks, and fixed safe templates. It performs no network or external-model call.

## Forbidden claim categories

1. `TRUE_CENSUS_RECONSTRUCTION` - critical
2. `TRUE_UNCERTAINTY` - critical
3. `CONFIDENCE_AS_PROBABILITY` - high
4. `EXTERNAL_PRODUCTS_AS_GROUND_TRUTH` - high
5. `VERIFIED_HOTSPOT_TRUTH` - high
6. `LLM_IMPROVES_PREDICTION_ACCURACY` - critical
7. `AUTOMATED_POLICY_DECISION` - high
8. `FAKE_PRECISION_OR_OVERCONFIDENCE` - medium

Rules cover English and Russian formulations. Safe negative statements such as `not true census uncertainty` are preserved through clause-aware negation detection instead of being reported as violations.

## Allowed claim categories

The rules reinforce:

- calibrated proxy population surface;
- uncertainty-aware interpretation;
- proxy interval;
- ensemble spread inside the proxy framework;
- interpretation-confidence score;
- screening class;
- triage category;
- structural comparator;
- evidence-linked explanation;
- manual review recommended;
- not census truth;
- not true census uncertainty.

## Risk and rewrite behavior

Each detected violation contains:

- category;
- exact matched text;
- explanation;
- safe alternative;
- severity.

The combined result returns a `0-100` risk score and overall severity. With `auto_rewrite=True`, unsafe answer text is replaced by a conservative City1 statement assembled from the violated categories. The rewrite does not attempt creative paraphrasing and does not preserve an unsafe scientific claim.

Critical rewrites explicitly retain the proxy, uncertainty, confidence, hotspot, comparator, and manual-review boundaries relevant to the detected categories.

## Evidence-grounding validation

`validate_evidence_grounding` checks:

- non-empty `evidence_used`;
- non-empty `claim_boundary_notes`;
- answer length and specificity;
- presence of `missing_artifacts`;
- whether non-empty missing artifacts are surfaced as unavailable or limited evidence.

`check_response_dict` additionally validates the required City1 response schema, including `answer`, `structured_sections`, `fallback_used`, and evidence fields.

This produces a grounding score from `0` to `100`. It is a response-structure and provenance score, not a probability that the answer is correct.

## Streamlit integration

After the local fallback returns, `app_v4.py` now:

1. attaches the original claim text in Claim Checker mode;
2. calls `guard_response` with the selected language;
3. stores and displays only `final_response`;
4. preserves the complete guardrail audit in session state;
5. displays pass/fail, severity, grounding score, and safe-rewrite status;
6. displays each detected category and safe alternative;
7. uses `st.error` for critical violations;
8. uses `st.warning` for medium/high violations;
9. uses `st.success` for passed responses;
10. includes the guardrail result in the in-memory Markdown report.

The existing V4.4 city selection, nine modes, Russian answers, fallback provider, evidence panel, session persistence, and download behavior remain intact.

## Test results

Compilation:

```powershell
python -m py_compile src\city1\llm_guardrails.py
python -m py_compile app_v4.py
```

Guardrail tests:

```powershell
python -m unittest tests.test_llm_guardrails -v
```

Result: 13 tests passed.

Fallback regression:

```powershell
python -m unittest tests.test_llm_fallback -v
```

Result: 12 tests passed.

Streamlit helper regression:

```powershell
python -m unittest tests.test_app_v4_smoke -v
```

Result: 10 tests passed.

The guardrail tests cover safe negative wording, all required dangerous categories, Russian phrases, deterministic safe rewrite, missing evidence, real fallback compatibility, and JSON serialization.

Headless Streamlit `AppTest` checks:

- Almaty Generate City Brief: zero exceptions, guardrail passed, grounding score `100`;
- Claim Checker with `This is true census ground truth.`: zero exceptions, `critical` severity, safe rewrite used;
- Markdown report contains the Guardrail check section.

## Known limitations

- Pattern matching cannot prove factual correctness.
- Novel or indirect paraphrases may evade explicit phrase rules.
- Clause-aware negation handling is deterministic and may not capture every complex sentence.
- Grounding score measures visible evidence linkage and response structure, not scientific truth.
- Safe rewrites are intentionally conservative and may discard useful nuance from an unsafe answer.
- Human scientific review remains required for publication and policy-facing material.

## Why guardrails precede Gemini

An external LLM can produce fluent but scientifically overconfident wording. Implementing the deterministic boundary layer first gives both local fallback and future Gemini responses the same inspectable validation contract. Gemini can later improve language flexibility without becoming the authority for scientific claim boundaries.

## Exact next phase

V4.5 - implement optional Gemini API integration behind the existing local evidence tools and `guard_response`. Gemini must remain optional, must fall back locally on any failure, and every generated answer must pass the Phase V4.6 guardrail before display.

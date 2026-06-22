# City1 v4 Phase 3 - Deterministic Fallback Engine Report

## Status and purpose

Phase V4.3 is complete. The fallback engine converts frozen City1 evidence dictionaries into compact, structured, claim-bounded explanations when Gemini is disabled, unavailable, rate-limited, or has no configured API key.

The fallback engine is not a replacement for the LLM, and it is not a population model. It is a deterministic evidence-to-explanation layer. It ensures that City1 v4 remains usable and claim-bounded even when external LLM services are unavailable.

## Implemented files

- `src/city1/llm_fallback.py` - deterministic bilingual fallback engine.
- `tests/test_llm_fallback.py` - standard-library unit tests.
- `scripts/demo_v4_fallback.py` - terminal-only examples.
- `docs/V4_PHASE3_FALLBACK_ENGINE_REPORT.md` - this implementation record.

No frozen V2/V3 outputs, reports, models, or manuscript results were modified.

## Implemented functions

- `generate_fallback_response(...)` - primary mode dispatcher and response entry point.
- `generate_city_brief(...)` - city support, official-total, hotspot, uncertainty, confidence, and claim-boundary brief.
- `generate_hotspot_review(...)` - stable and caution-heavy screening-class interpretation.
- `generate_uncertainty_summary(...)` - P10/P50/P90, relative uncertainty, interval coverage, alignment, and district limitations.
- `generate_confidence_summary(...)` - confidence-band shares and interpretation-support explanation.
- `generate_cell_explanation(...)` - frozen cell-level proxy explanation or graceful alternative.
- `generate_city_comparison(...)` - cross-city evidence comparison without truth-accuracy ranking.
- `check_text_for_overclaims(...)` - lightweight deterministic phrase pre-check.
- `get_fallback_capabilities()` - modes, languages, evidence dependency, and limitations.

Every generated answer returns:

- `answer`
- `mode`
- `city`
- `language`
- `fallback_used=true`
- `confidence_of_answer`
- `evidence_used`
- `claim_boundary_notes`
- `recommended_next_checks`
- `missing_artifacts`
- `structured_sections`

All response dictionaries are JSON-serializable.

## Supported modes

- `ask`
- `city_brief`
- `hotspot_review`
- `uncertainty_summary`
- `confidence_summary`
- `compare_cities`
- `explain_cell`
- `claim_checker`
- `reviewer_safe`

General `ask` mode deterministically routes questions about uncertainty, confidence, or hotspots to the corresponding evidence template. `reviewer_safe` adds an explicit conservative interpretation rule.

## Supported languages

- English (`en`, default)
- Russian (`ru`)

Technical identifiers such as P10, P50, P90, `confidence_score`, `confidence_band`, and `hotspot_priority_class` remain unchanged. An unsupported language safely falls back to English and records that fallback in the claim-boundary notes.

## Scientific boundaries preserved

- City1 remains a calibrated proxy population framework, not true cell-level census reconstruction.
- P10/P50/P90 remain ensemble-spread proxy intervals, not true census uncertainty.
- `confidence_score` remains interpretation confidence, not probability of correctness.
- Hotspot classes remain screening/triage categories, not verified hotspot truth.
- WorldPop and GHS-POP remain structural comparators, not ground truth.
- Cross-city ranking refers to interpretation support, not truth-level accuracy.
- The fallback never creates or changes population estimates, intervals, confidence scores, or hotspot classes.

## Example behavior

For Almaty `city_brief`, the engine reports the frozen evidence:

- support level `full_v3`;
- official city-total anchor `2,351,424`;
- `3,078` grid cells;
- median relative uncertainty `0.170`;
- high/medium/low confidence shares `22.9% / 66.2% / 10.9%`;
- `842` priority screening cells;
- `212` high-value/high-confidence cells.

The same answer explicitly states that the surface is a calibrated proxy, `confidence_score` is not a probability, and hotspot classes are not verified truth.

For Kurchatov, the engine returns `partial` support and does not invent V3 uncertainty or hotspot evidence. For an unknown city or missing cell identifier, it returns a low-confidence graceful response and recommends city-level or hotspot-level alternatives.

The lightweight claim checker detects obvious phrases such as `true census`, `ground truth`, `exact population`, `verified hotspot`, correctness-probability claims, automated-policy claims, and LLM accuracy claims. It returns a bounded safe rewrite. This is deliberately narrower than the future V4.6 guardrail.

## Verification

Syntax compilation:

```powershell
python -m py_compile src\city1\llm_fallback.py scripts\demo_v4_fallback.py tests\test_llm_fallback.py
```

Unit tests:

```powershell
python -m unittest tests.test_llm_fallback -v
```

Result: 12 tests passed.

The tests cover English and Russian responses, full/partial/unknown city handling, hotspot boundaries, uncertainty boundaries, confidence wording, comparison safety, missing-cell handling, overclaim detection, and JSON serialization of all public response types.

Demo:

```powershell
python scripts\demo_v4_fallback.py
```

The demo prints an Almaty city brief, a Kurchatov limited-support brief, a dangerous-claim pre-check, and a full-V3 city comparison. It does not write files.

## Known limitations

- Templates are deterministic and intentionally less flexible than an LLM answer.
- Russian is supported; Kazakh is not implemented in this phase.
- The claim checker is phrase-based and cannot replace semantic human review or the planned V4.6 guardrail.
- Full reliability explanations remain limited to Almaty, Astana, Semey, and Shymkent.
- Mixed interval, error-alignment, external-comparison, and district evidence remains mixed or unavailable in the answer rather than being promoted to positive evidence.
- The fallback depends on Phase 2 local evidence artifacts being present.

## Why this phase matters

City1 v4 can now provide evidence-grounded explanations without an API key and without network access. Gemini quota exhaustion or service failure will affect language richness, but it will not make the assistant unusable or remove scientific claim boundaries.

## Exact next phase

V4.4 - implement `app_v4.py` as a thin Streamlit interface over `llm_tools.py` and `llm_fallback.py`. The app should expose the supported modes, evidence panel, fallback status, and claim-boundary notes without modifying `app_v2.py` or `app_v3.py`.

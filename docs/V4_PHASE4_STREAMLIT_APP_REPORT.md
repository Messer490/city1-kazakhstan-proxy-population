# City1 v4 Phase 4 - Streamlit App Report

## Status and purpose

Phase V4.4 is complete. `app_v4.py` provides an offline, evidence-first Streamlit interface over the Phase 2 local evidence tools and the Phase 3 deterministic fallback engine.

The app is an interpretation interface. It does not train a model, run new population inference, alter frozen P10/P50/P90 values, change `confidence_score`, create hotspot classes, or write to frozen evidence folders.

## Implemented files

- `app_v4.py` - main offline Streamlit application.
- `tests/test_app_v4_smoke.py` - import-safe helper and backend smoke tests.
- `docs/V4_PHASE4_STREAMLIT_APP_REPORT.md` - this implementation record.

## Implemented UI sections

### Sidebar controls

- city selector with full V3 cities first;
- optional custom/unknown city input;
- mode selector;
- English/Russian language selector;
- provider selector fixed to `Local fallback only`;
- Phase V4.5 Gemini coming-soon note;
- conditional cell ID input;
- conditional city-comparison multiselect;
- frozen run identifier and offline/read-only status.

### Main evidence view

- visible scientific warning near the title;
- selected city, support level, provider, run ID, and fallback-status cards;
- official total, grid-cell count, median relative uncertainty, mean confidence, priority-cell count, and OSM-context metrics;
- optional confidence-band bar chart for full V3 cities;
- explicit limited-support message where V3 confidence evidence is unavailable.

### Assistant panel

- question or claim text area;
- `Generate answer` and `Clear answer` actions;
- persistent response state across Streamlit reruns;
- deterministic backend call through `generate_fallback_response`;
- structured answer, confidence level, fallback status, and evidence count;
- evidence, claim-boundary, and next-check expanders;
- missing-artifact warnings instead of crashes;
- Markdown report download generated entirely in memory;
- comparison evidence table in compare-cities mode;
- framework-wide allowed and forbidden claim summary.

## Supported modes

- Ask City1 Assistant
- Generate City Brief
- Hotspot Review
- Uncertainty Summary
- Confidence Summary
- Compare Cities
- Explain Selected Cell
- Claim Checker
- Reviewer-Safe Answer

The UI labels map directly to the deterministic fallback modes defined in `src/city1/llm_fallback.py`.

## Supported languages

- English
- Russian

The generated answer follows the selected language. Core UI navigation remains primarily English, while the top safety warning switches to Russian when Russian mode is selected.

## Backend functions used

From `src/city1/llm_tools.py`:

- `get_available_cities`
- `get_city_summary`
- `get_hotspot_summary`
- `get_claim_boundaries`
- `compare_cities`

From `src/city1/llm_fallback.py`:

- `generate_fallback_response`

The app also exposes import-safe helpers for city ordering, custom-city resolution, city-overview assembly, backend dispatch, and Markdown report generation.

## Session state

The application initializes and retains:

- `last_response`
- `last_question`
- `selected_city`
- `selected_mode`
- `selected_language`
- `generated_report_md`

This prevents the answer from disappearing after normal Streamlit reruns.

## Scientific safety and limitations

- The app explains a calibrated proxy population surface, not census truth.
- P10/P50/P90 remain proxy intervals, not true census uncertainty.
- `confidence_score` remains interpretation support, not probability of correctness.
- Hotspot classes remain screening/triage categories, not verified hotspots.
- External products remain structural comparators, not ground truth.
- The app does not include Gemini, API keys, internet retrieval, cache/mini-RAG, or the full V4.6 guardrail.
- Full V3 reliability interpretation remains limited to Almaty, Astana, Semey, and Shymkent.
- The confidence chart and comparison table are intentionally simple Streamlit-native views; no new scientific visualization is generated.

## Verification

Syntax compilation:

```powershell
python -m py_compile app_v4.py tests\test_app_v4_smoke.py
```

Import-safe smoke tests:

```powershell
python -m unittest tests.test_app_v4_smoke -v
```

Result: 9 tests passed.

The tests verify:

- import safety without top-level Streamlit execution;
- full V3 city ordering;
- custom and unknown city handling;
- required session-state defaults;
- Almaty frozen evidence values;
- Russian fallback generation;
- risky-claim detection;
- in-memory Markdown report structure;
- JSON-serializable helper outputs.

Headless Streamlit runtime verification used Streamlit `1.32.2` and `streamlit.testing.v1.AppTest`:

- initial application run: zero exceptions;
- expected title rendered;
- four sidebar selectors rendered;
- Generate/Clear buttons rendered;
- Generate City Brief action: zero exceptions;
- response persisted in `st.session_state`;
- response mode: `city_brief`;
- 17 evidence sources exposed;
- Markdown download button rendered.

## Manual run command

From the project root:

```powershell
python -m streamlit run app_v4.py
```

The app requires no API key and no internet connection.

## Frozen-file statement

No frozen V2/V3 output, report, model, manuscript result, or evidence value was changed during Phase V4.4. The only downloadable content is generated in memory after a user action.

## Exact next phase

V4.6 - implement the dedicated claim-boundary guardrail layer before adding external Gemini generation. This ordering ensures that the guardrail exists before Phase V4.5 introduces non-deterministic external language generation.

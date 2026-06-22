# City1 v4 Phase 5 - Optional Gemini Integration Report

## Status and purpose

Phase V4.5 is complete. City1 v4 now supports optional Gemini language generation over compact local evidence packets while retaining deterministic fallback as a complete offline path.

Gemini is used only as a language-generation layer over compact City1 evidence packets. It does not create new population estimates, change model outputs, or validate census truth. All generated answers are checked by deterministic claim-boundary guardrails and fall back to local deterministic explanations when Gemini is unavailable.

## Implemented files

- `src/city1/llm_client.py` - lazy Gemini client, compact prompting, robust JSON parsing, provider orchestration, fallback, and guardrail integration.
- `tests/test_llm_client.py` - API-free mocked provider tests.
- `docs/V4_PHASE5_GEMINI_INTEGRATION_REPORT.md` - this implementation record.

Modified:

- `app_v4.py` - provider selection, Gemini readiness/status, provider metadata, fallback warnings, and report metadata.
- `tests/test_app_v4_smoke.py` - provider/session/report compatibility tests.
- `requirements-optional.txt` - optional `google-genai` dependency declaration.

No API key or `.env` file was created. No frozen V2/V3 output, report, model, evidence table, or manuscript result was modified.

## Implemented client functions

- `get_gemini_status()`
- `build_gemini_prompt(...)`
- `call_gemini_structured(...)`
- `generate_llm_response(...)`
- `parse_gemini_json_response(text)`
- `estimate_evidence_packet_size(evidence_pack)`
- `get_llm_client_capabilities()`

The public `generate_llm_response` function is now the shared provider entry point for Streamlit. It returns one response schema for Gemini and deterministic fallback.

## Dependency notes

The official Google GenAI package is optional:

```text
google-genai>=1.0.0,<2.0.0
```

It is listed in `requirements-optional.txt`. The module performs lazy SDK imports only inside the actual Gemini call. Importing `app_v4.py` and using the local fallback does not require `google-genai`.

The default model is held in one constant:

```text
gemini-2.5-flash
```

It can be changed through `CITY1_GEMINI_MODEL` without editing code.

Optional runtime settings:

- `CITY1_GEMINI_TEMPERATURE`, default `0.2`;
- `CITY1_GEMINI_MAX_OUTPUT_TOKENS`, default `1600`;
- `CITY1_GEMINI_TIMEOUT_SECONDS`, default `45`.

Timeout is passed through `google.genai.types.HttpOptions` when supported by the installed SDK. Client construction falls back safely if that optional argument is unavailable.

## API key handling

The client checks, in order:

1. `GEMINI_API_KEY`
2. `GOOGLE_API_KEY`

Keys are read from the process environment only. They are never hard-coded, printed, included in prompts, written to files, or returned in status dictionaries. Exception text is redacted if it contains the active key.

## Evidence-first prompt strategy

Gemini receives only:

- the user question;
- mode and language;
- compact city/method/uncertainty/hotspot evidence;
- claim boundaries;
- required JSON response schema;
- instructions to expose unavailable evidence rather than invent values.

Before serialization, the client:

- keeps only known evidence-pack sections;
- limits hotspot/stability/caution example lists to three rows;
- limits general lists and long strings;
- converts local paths to short artifact labels;
- excludes raw CSV, GeoJSON, model binaries, manuscripts, and secrets;
- estimates character and approximate token size;
- raises a size warning above `24,000` evidence characters.

Gemini is explicitly instructed that it is not a population model and cannot change P10/P50/P90, `confidence_score`, hotspot classes, or any estimate.

## JSON response handling

The parser accepts:

- pure JSON;
- JSON inside Markdown fences;
- a JSON object surrounded by explanatory text.

Invalid JSON, a non-object result, or a missing/empty `answer` causes deterministic fallback. Model-provided evidence paths are not trusted: the final response uses only evidence sources from the local evidence packet.

## Provider and fallback behavior

### Local fallback only

- calls the Phase V4.3 deterministic fallback;
- runs the Phase V4.6 guardrail;
- returns `provider_used="fallback"`.

### Gemini API with fallback

Gemini is attempted only when both SDK and API key are available. The client falls back on:

- missing SDK;
- missing API key;
- authentication or quota error;
- timeout or network error;
- SDK incompatibility;
- invalid JSON;
- missing required answer content;
- failed evidence-grounding validation;
- unsafe Gemini wording detected by guardrails.

Unsafe Gemini output is recorded as guardrail-rejected and is not displayed. A fresh deterministic response becomes the final answer.

## Guardrail integration

Both provider paths call `guard_response`. A Gemini answer is accepted only if the deterministic claim and grounding check passes. The final schema exposes:

- provider requested;
- provider used;
- fallback status;
- Gemini success/model/error/latency;
- guardrail result;
- confidence, evidence, boundaries, next checks, and missing artifacts.

## Streamlit integration

The sidebar now offers:

- `Local fallback only`
- `Gemini API with fallback`

The app displays:

- SDK available/missing;
- API key available/missing;
- selected model;
- provider actually used;
- Gemini success/failure and latency;
- fallback reason;
- existing guardrail, evidence, and claim-boundary panels.

The Markdown report records requested/used provider, guardrail audit, and Gemini metadata. Session-state persistence and all nine interpretation modes remain intact.

## Tests

Compilation:

```powershell
python -m py_compile src\city1\llm_client.py
python -m py_compile app_v4.py
```

Client tests:

```powershell
python -m unittest tests.test_llm_client -v
```

The 11 client tests cover:

- no-key status;
- pure, fenced, and invalid JSON;
- local provider operation;
- no-key Gemini fallback;
- guardrail metadata;
- safe mocked Gemini acceptance;
- unsafe mocked Gemini rejection to fallback;
- compact prompt/path behavior;
- JSON serialization.

Regression commands:

```powershell
python -m unittest tests.test_llm_guardrails -v
python -m unittest tests.test_llm_fallback -v
python -m unittest tests.test_app_v4_smoke -v
```

Headless Streamlit no-key check:

- both provider options rendered;
- Gemini provider selected successfully;
- zero Streamlit exceptions;
- `provider_requested="gemini"`;
- `provider_used="fallback"`;
- guardrail passed;
- provider metadata included in the Markdown report.

## Manual testing

Without an API key:

```powershell
python -m streamlit run app_v4.py
```

Select `Gemini API with fallback`. The app should warn that Gemini is unavailable and still generate a deterministic guarded answer.

With a locally configured key:

```powershell
$env:GEMINI_API_KEY = "your-local-key"
python -m streamlit run app_v4.py
```

The key must remain outside version control. If the Gemini call succeeds, `provider_used` becomes `gemini`; quota, parsing, safety, or connection failure automatically returns to fallback.

## Known limitations

- No live Gemini request was made during automated testing because no API key is required or stored.
- SDK behavior is exercised through mocks; a local key is required for a real provider smoke test.
- Structured output is requested through JSON MIME and an explicit schema description rather than trusting free-form text.
- Character-based token estimation is approximate.
- Gemini wording can be more flexible than deterministic templates, but scientific scope remains limited by local evidence and guardrails.
- No internet RAG or Google Search grounding is used.

## Exact next phase

Recommended next step: V4.8 evaluation benchmark. It should compare deterministic fallback, safe mocked/live Gemini where available, and guarded outputs over a frozen question bank. V4.7 cache/mini-RAG can follow once answer quality and guardrail behavior are measured.

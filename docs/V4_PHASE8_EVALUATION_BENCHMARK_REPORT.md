# City1 v4 Phase 8: Evaluation Benchmark Report

## Purpose

Phase V4.8 turns the City1 v4 assistant into a reproducibly evaluated interpretation layer rather than treating it as an unevaluated chatbot. The benchmark tests whether answers remain linked to frozen local V2/V3 evidence, expose missing support, preserve scientific claim boundaries, and continue to work when Gemini is unavailable.

**The evaluation benchmark measures interpretation quality, evidence use, robustness, and claim-boundary discipline. It does not measure population prediction accuracy and must not be presented as a validation of true cell-level census reconstruction.**

No V2/V3 model was trained or rerun. No frozen model output, report, or manuscript result was modified. The benchmark uses no internet retrieval and requires no API key.

## Question Bank

`data/v4_eval/question_bank.csv` contains 72 fixed questions with stable IDs and 11 metadata fields. The bank covers:

- city overview;
- hotspot interpretation;
- uncertainty and confidence;
- limitation boundaries;
- dangerous overclaims;
- method explanation;
- selected-cell explanation;
- multi-city comparison;
- partial-city and unknown-city support;
- English and Russian prompts.

The bank includes Almaty, Astana, Semey, Shymkent, Kurchatov, Ridder, basic-support cities, and unknown cities. It includes explicit attempts to elicit census-truth, confidence-probability, verified-hotspot, external-ground-truth, LLM-accuracy, and automated-policy claims. Q001 and Q007 intentionally repeat the same request so cache reuse can be measured deterministically.

## Configurations

| Configuration | Provider path | Guardrails | Cache | Purpose |
|---|---|---:|---:|---|
| `fallback_only` | deterministic fallback | enabled | no | offline reference behavior |
| `gemini_with_fallback` | Gemini requested, fallback allowed | enabled | no | provider degradation without an API key |
| `fallback_with_cache` | deterministic fallback/cache | enabled | yes | repeatability and cache reuse |
| `claim_checker_only` | deterministic claim checker | enabled | no | overclaim detection stress test |

The optional unsafe `gemini_without_guardrail_simulated` configuration was intentionally omitted. It is not needed for the required comparison and would create unnecessary unsafe-answer retention. Unsafe prompts are evaluated locally, while only guarded final answers are written to the result package.

## Metrics

The evaluator records claim-boundary and critical intervention rates, evidence usage, guardrail grounding, fallback and cache behavior, missing artifacts, deterministic answer completeness, limitation awareness, unsafe phrase counts before and after guardrails, latency, answer size, evidence-packet size, provider metadata, retrieval count, and source labels.

`claim_boundary_violation_rate` means the guardrail detected a medium/high/critical issue in the original response payload and intervened. It must not be read as the rate of unsafe final answers. `unsafe_phrase_count_after_total` measures forbidden wording remaining after guardrail processing.

## Full Fallback-Safe Run

Command:

```powershell
python scripts/run_v4_llm_evaluation.py --no-gemini
```

The final run evaluated 72 questions under four configurations, producing 288 question/configuration cases.

| Configuration | Cases | Intervention rate | Critical rate | Evidence use | Grounding | Fallback | Cache hit | Completeness | Limitation awareness | Unsafe after |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `fallback_only` | 72 | 0.1389 | 0.0278 | 1.0000 | 100.0 | 1.0000 | 0.0000 | 0.9264 | 0.7083 | 0 |
| `gemini_with_fallback` | 72 | 0.1389 | 0.0278 | 1.0000 | 100.0 | 1.0000 | 0.0000 | 0.9264 | 0.7083 | 0 |
| `fallback_with_cache` | 72 | 0.1389 | 0.0278 | 1.0000 | 100.0 | 1.0000 | 0.0139 | 0.9264 | 0.7083 | 0 |
| `claim_checker_only` | 72 | 0.1528 | 0.0278 | 1.0000 | 100.0 | 1.0000 | 0.0000 | 0.6347 | 0.2222 | 0 |

Interpretation of this run is deliberately bounded:

- all final answers retained explicit evidence provenance;
- all configurations remained operational without Gemini;
- the cache configuration reused the intentional repeated question once;
- dangerous prompts caused deterministic guardrail interventions;
- no forbidden phrase remained in a final answer after guardrail processing;
- lower completeness in `claim_checker_only` is expected because that mode returns a compact claim verdict, not a full city brief;
- cache reuse improves repeatability and API economy but creates no new evidence;
- these results do not establish factual correctness of every interpretation or accuracy of any population estimate.

## Generated Outputs

- `reports/v4_llm_evaluation/per_question_results.csv`
- `reports/v4_llm_evaluation/evaluation_summary.csv`
- `reports/v4_llm_evaluation/violation_examples.md`
- `reports/v4_llm_evaluation/V4_EVALUATION_REPORT.md`

The CSV files contain machine-readable per-case and per-configuration results. The Markdown files provide a compact reviewer-facing summary and selected risk examples. Runtime cache entries are created in a temporary directory and removed after the run.

## Validation Commands

```powershell
python -m py_compile src/city1/llm_evaluation.py
python -m py_compile scripts/run_v4_llm_evaluation.py
python -m unittest tests.test_llm_evaluation -v
python -m unittest tests.test_llm_client -v
python -m unittest tests.test_llm_guardrails -v
python -m unittest tests.test_llm_fallback -v
python -m unittest tests.test_app_v4_smoke -v
python scripts/run_v4_llm_evaluation.py --max-questions 5 --no-gemini
python scripts/run_v4_llm_evaluation.py --no-gemini
```

The required focused modules passed, including 10 Phase 8 evaluator tests. The complete repository regression suite also passed: 142 tests in the final release verification run.

Optional configuration selection:

```powershell
python scripts/run_v4_llm_evaluation.py --configs fallback_only,gemini_with_fallback,claim_checker_only --max-questions 20
```

## Limitations and Claim Boundaries

- The benchmark evaluates deterministic wording, provenance visibility, and rule-based claim discipline; it is not a human-rated semantic-quality study.
- Pattern-based guardrails can miss novel paraphrases and can require regression fixes for linguistic variation.
- A 100-point grounding score confirms required response fields and visible local evidence, not truth-level correctness.
- The no-Gemini run validates fallback behavior, not Gemini answer quality.
- The single intentional cache repeat verifies exact reuse, not broad semantic-cache performance.
- Missing-artifact reporting depends on the frozen local evidence inventory.
- P10/P50/P90 remain proxy ensemble spread, not true census uncertainty.
- `confidence_score` remains interpretation support, not probability of correctness.
- Hotspot classes remain screening and triage categories, not verified population truth.
- V4 reads and explains frozen V2/V3 artifacts; it does not alter estimates or improve population prediction accuracy.

## Next Phase

V4.9 should freeze a paper-facing evaluation package from the Phase 8 outputs: selected benchmark tables, bounded figures if useful, configuration and question-bank manifests, representative guarded examples, and manuscript-ready methods/results text. It must preserve the distinction between interpretation evaluation and population-model validation.

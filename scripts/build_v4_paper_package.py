"""Build the City1 v4 paper-facing package from existing local artifacts.

The builder is offline, idempotent, and packaging-only. It never trains models,
calls Gemini, writes a cache, or changes frozen V2/V3 evidence directories.
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path
from textwrap import dedent
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PACKAGE = "manuscript_package_v4"
RUN_ID = "city1_v3_rf500m_e20_20260618T040646Z"


def _clean(text: str) -> str:
    return dedent(text).strip() + "\n"


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def _write_text(path: Path, content: str) -> bool:
    path.parent.mkdir(parents=True, exist_ok=True)
    normalized = content if content.endswith("\n") else content + "\n"
    if path.exists() and path.read_text(encoding="utf-8") == normalized:
        return False
    path.write_text(normalized, encoding="utf-8")
    return True


def _write_csv(path: Path, fieldnames: list[str], rows: Iterable[dict[str, Any]]) -> bool:
    path.parent.mkdir(parents=True, exist_ok=True)
    materialized = list(rows)
    lines: list[str] = []
    from io import StringIO

    buffer = StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=fieldnames, extrasaction="ignore", lineterminator="\n")
    writer.writeheader()
    writer.writerows(materialized)
    content = buffer.getvalue()
    if path.exists() and path.read_text(encoding="utf-8-sig") == content:
        return False
    path.write_text(content, encoding="utf-8")
    return True


def _evaluation_context(root: Path) -> dict[str, Any]:
    question_path = root / "data" / "v4_eval" / "question_bank.csv"
    summary_path = root / "reports" / "v4_llm_evaluation" / "evaluation_summary.csv"
    result_path = root / "reports" / "v4_llm_evaluation" / "per_question_results.csv"
    questions = _read_csv(question_path)
    summary = _read_csv(summary_path)
    results = _read_csv(result_path)
    category_counts = Counter(row.get("category", "unknown") for row in questions)
    language_counts = Counter(row.get("language", "unknown") for row in questions)
    category_language_counts = Counter(
        (row.get("category", "unknown"), row.get("language", "unknown")) for row in questions
    )
    configs = sorted({row.get("config", "") for row in results if row.get("config")})
    unsafe_after = sum(int(float(row.get("unsafe_phrase_count_after", 0) or 0)) for row in results)
    cache_hits = sum(str(row.get("cache_hit", "")).lower() == "true" for row in results)
    return {
        "question_count": len(questions),
        "case_count": len(results),
        "configuration_count": len(configs) or len(summary),
        "configs": configs or [row.get("config", "") for row in summary],
        "summary": summary,
        "category_counts": dict(sorted(category_counts.items())),
        "language_counts": dict(sorted(language_counts.items())),
        "category_language_counts": {
            f"{category}|{language}": count
            for (category, language), count in sorted(category_language_counts.items())
        },
        "unsafe_after": unsafe_after,
        "cache_hits": cache_hits,
        "evaluation_available": bool(summary and results),
        "question_bank_available": bool(questions),
    }


def _paper_friendly_evaluation_rows(summary: list[dict[str, str]]) -> list[dict[str, str]]:
    rows = []
    for source in summary:
        rows.append({
            "configuration": source.get("config", "unknown"),
            "cases": source.get("question_count", ""),
            "claim_boundary_intervention_rate": source.get("claim_boundary_violation_rate", ""),
            "critical_intervention_rate": source.get("critical_violation_rate", ""),
            "evidence_usage_rate": source.get("evidence_usage_rate", ""),
            "grounding_score_mean": source.get("grounding_score_mean", ""),
            "fallback_rate": source.get("fallback_rate", ""),
            "cache_hit_rate": source.get("cache_hit_rate", ""),
            "missing_artifact_rate": source.get("missing_artifact_rate", ""),
            "completeness_mean": source.get("answer_completeness_score_mean", ""),
            "limitation_awareness_mean": source.get("limitation_awareness_score_mean", ""),
            "unsafe_phrases_after": source.get("unsafe_phrase_count_after_total", ""),
        })
    return rows


def _markdown_files(context: dict[str, Any]) -> dict[str, str]:
    q = context["question_count"]
    cases = context["case_count"]
    configs = context["configuration_count"]
    availability = (
        f"The frozen Phase 8 package contains {q} questions, {cases} question/configuration cases, "
        f"and {configs} configurations."
        if context["evaluation_available"]
        else "Phase 8 evaluation artifacts were unavailable at build time; regenerate them before reporting metrics."
    )
    return {
        "README.md": _clean(f"""
            # City1 v4 Paper-Facing Package

            This directory is the reproducible writing package for City1 v4. V2 builds a deterministic, officially calibrated proxy population surface on a 500 m grid. V3 adds proxy ensemble intervals, confidence bands, and hotspot-screening classes. V4 reads those frozen artifacts through local tools and provides claim-bounded interpretation support; it is not a new population model.

            V4 combines local evidence tools, a deterministic fallback, optional Gemini language generation, deterministic guardrails, a local cache/mini-RAG layer, and an offline evaluation benchmark. It does not alter V2/V3 estimates, reconstruct true cell-level census counts, estimate true census uncertainty, or authorize automated policy decisions.

            {availability}

            ## Package Map

            - `sections/`: concise manuscript section drafts.
            - `tables/`: paper-facing contribution, mode, evidence, guardrail, evaluation, and reproducibility tables.
            - `figures/`: figure specifications and screenshot-independent placeholders.
            - `traceability/`: file, phase, claim, and metric provenance maps.
            - `appendices/`: benchmark, guardrail, metric, and reproducibility support.
            - `V4_PAPER_SUMMARY.md`: title candidates, pitch, research questions, and scientific identity.
            - `V4_AUTHOR_NOTES.md`: reviewer-facing writing guidance.

            ## Reproduction

            Run the fallback-safe benchmark with:

            ```powershell
            python scripts/run_v4_llm_evaluation.py --no-gemini
            ```

            Regenerate this package with:

            ```powershell
            python scripts/build_v4_paper_package.py
            ```

            The builder uses only local repository artifacts, requires no Gemini key or internet access, and does not modify frozen V2/V3 evidence.
        """),
        "V4_PAPER_SUMMARY.md": _clean(f"""
            # City1 v4 Paper Summary

            ## Suggested Titles

            1. City1 v4: A Tool-Grounded LLM Assistant for Reliability-Aware Interpretation of Proxy Population Surfaces
            2. City1: From Calibrated Proxy Population Surfaces to Tool-Grounded LLM Interpretation for Data-Scarce Urban Analysis
            3. Tool-Grounded LLM Interpretation of Uncertainty-Aware Proxy Population Surfaces in Data-Scarce Cities

            ## Short Pitch

            City1 v4 adds a controlled interpretation layer above frozen calibrated proxy population and uncertainty-aware screening outputs. Local tools assemble closed-world evidence packets; deterministic fallback, optional Gemini generation, local retrieval/cache, and claim-boundary guardrails then produce answers with explicit provenance and cautions.

            ## Research Questions

            1. Can a tool-grounded assistant expose local V2/V3 evidence without changing the population model?
            2. Can deterministic fallback preserve usability when an external LLM is unavailable?
            3. Can claim-boundary guardrails identify and rewrite census-truth, probability, hotspot-truth, and automated-policy overclaims?
            4. Can an offline benchmark make interpretation quality and robustness reproducibly inspectable?

            ## Contributions

            - A closed-world local evidence-tool layer over frozen City1 artifacts.
            - A deterministic fallback path for reproducible, API-independent answers.
            - Optional Gemini generation constrained by the same compact evidence packet.
            - Deterministic guardrails for scientific claim boundaries and evidence visibility.
            - A local cache and City1-only mini-RAG layer that creates no new evidence.
            - An offline benchmark with {q} questions and {cases} evaluated cases across {configs} configurations.

            ## Method and Evaluation Summary

            V4 routes a user question to local evidence tools, builds a compact packet, optionally adds local retrieval snippets, checks the cache, invokes fallback or Gemini, and applies deterministic guardrails before display. {availability} The benchmark measures evidence use, grounding, fallback robustness, cache behavior, completeness, limitation awareness, and detected unsafe wording. It does not measure population prediction accuracy.

            ## Limitations and Claim Boundaries

            V4 inherits the missing cell-level census truth and proxy-uncertainty boundaries of V2/V3. Gemini is optional and quota-dependent. Retrieval is local only. Heuristic metrics and pattern guardrails do not replace human scientific review. Full V3 reliability interpretation is limited to Almaty, Astana, Semey, and Shymkent.

            ## Final Scientific Identity

            City1 v4 is a controlled, tool-grounded LLM interpretation assistant for calibrated and uncertainty-aware proxy population surfaces. It supports interpretability, usability, evidence linking, fallback robustness, and claim-boundary discipline without altering the underlying calibrated proxy population model.
        """),
        "V4_AUTHOR_NOTES.md": _clean("""
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
        """),
        "V4_CLAIM_BOUNDARY_SUMMARY.md": _clean("""
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
        """),
        "V4_LIMITATIONS.md": _clean("""
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
        """),
        "V4_REPRODUCIBILITY_CHECKLIST.md": _clean("""
            # V4 Reproducibility Checklist

            - [ ] Install the project dependencies in an isolated environment.
            - [ ] Run the complete tests: `python -m unittest discover -s tests -v`.
            - [ ] Run focused V4 tests: `python -m unittest tests.test_llm_evaluation tests.test_llm_cache tests.test_llm_client tests.test_llm_guardrails tests.test_llm_fallback tests.test_app_v4_smoke -v`.
            - [ ] Launch the application: `streamlit run app_v4.py`.
            - [ ] Run fallback-safe evaluation: `python scripts/run_v4_llm_evaluation.py --no-gemini`.
            - [ ] Optionally run Gemini evaluation after setting a local environment variable: `python scripts/run_v4_llm_evaluation.py --configs fallback_only,gemini_with_fallback,claim_checker_only --max-questions 20`.
            - [ ] Regenerate this package: `python scripts/build_v4_paper_package.py`.
            - [ ] Confirm no `.env`, API key, runtime cache, or frozen V2/V3 file entered the package.
            - [ ] Confirm the reported question/case counts match `reports/v4_llm_evaluation/`.
            - [ ] Preserve the statement that evaluation concerns interpretation and claim discipline, not population accuracy.
        """),
        "V4_SCREENSHOT_CHECKLIST.md": _clean("""
            # V4 Screenshot Checklist

            Capture screenshots manually at a consistent desktop viewport and without secrets:

            - [ ] `app_v4.py` overview with scientific identity and frozen-run status.
            - [ ] Almaty `Generate City Brief` result with evidence and cautions.
            - [ ] `Hotspot Review` showing screening and manual-review wording.
            - [ ] `Confidence Summary` showing that confidence is not probability.
            - [ ] `Claim Checker` dangerous prompt with guardrail detection and safe rewrite.
            - [ ] `Compare Cities` with no truth-accuracy ranking.
            - [ ] Gemini unavailable status followed by deterministic fallback output.
            - [ ] Exact cache-hit example for a repeated question.
            - [ ] `reports/v4_llm_evaluation/` folder with generated CSV and Markdown reports.

            Do not include API keys, `.env` content, personal paths, or claims that screenshots validate population accuracy.
        """),
        "sections/00_title_and_abstract.md": _clean(f"""
            # Title and Abstract Draft

            **Preferred title:** City1 v4: A Tool-Grounded LLM Assistant for Reliability-Aware Interpretation of Proxy Population Surfaces

            ## Abstract

            Urban proxy population surfaces can support analysis where fine-scale census labels are unavailable, but their outputs are vulnerable to deterministic over-reading and unsupported language. We present City1 v4, a controlled interpretation layer over frozen calibrated and uncertainty-aware proxy population artifacts. V4 uses local evidence tools, deterministic fallback generation, claim-boundary guardrails, optional Gemini language generation, and a City1-only cache/mini-RAG layer. It does not modify the underlying population model or produce new population estimates. An offline evaluation benchmark contains {q} questions and {cases} question/configuration cases across {configs} configurations. The benchmark measures evidence use, grounding, claim-boundary interventions, fallback robustness, cache behavior, answer completeness, and limitation awareness; it does not measure population prediction accuracy. In the frozen fallback-safe run, final answers retained evidence provenance and no detected forbidden phrase remained after guardrail processing. These results support V4 as an evidence-linked usability and interpretation layer, while true cell-level census reconstruction, true census uncertainty, and automated policy decisions remain outside its claims.
        """),
        "sections/01_introduction.md": _clean("""
            # 1. Introduction

            Fine-scale population proxies are difficult to communicate responsibly when observed cell-level census labels are absent. A map can appear more certain than its evidence permits, and non-specialist users may confuse calibrated totals, ensemble spread, or confidence bands with census truth. City1 V2 and V3 address modeling and reliability-aware screening; V4 addresses the interpretation interface.

            The central problem is not another prediction task. It is how to expose frozen evidence, missing support, uncertainty language, and claim boundaries through a usable question-answer interface without allowing the language layer to invent estimates. V4 therefore treats the LLM as optional language generation behind deterministic tools and guardrails.

            This paper asks whether a closed-world, tool-grounded assistant can improve evidence visibility, usability, fallback robustness, and scientific claim discipline while leaving the calibrated proxy model unchanged.
        """),
        "sections/02_related_positioning.md": _clean("""
            # 2. Related Positioning

            V4 sits at the intersection of population-surface interpretation, tool-grounded language systems, retrieval-assisted interfaces, and safety-oriented scientific communication. Unlike open-web retrieval systems, it uses a closed local corpus of City1 artifacts. Unlike predictive LLM applications, it cannot create or correct population values. Unlike a generic chatbot, each answer is coupled to evidence-source and missing-artifact fields.

            The contribution is therefore evaluated as interpretation infrastructure rather than model accuracy. This distinction separates V4 from V2/V3 while preserving one coherent scientific chain: calibrated proxy construction, uncertainty-aware reliability interpretation, and controlled evidence communication.
        """),
        "sections/03_system_architecture.md": _clean("""
            # 3. System Architecture

            A user selects a supported mode and submits a city, cell, comparison, or claim question. Local tools read frozen V2/V3 summaries and construct a compact evidence packet. The local retrieval layer may add City1-only snippets, and the cache may reuse a previously guarded answer when the evidence hash and request match. The provider layer then uses deterministic fallback or optional Gemini generation. Every output passes deterministic claim and grounding checks before display.

            The architecture deliberately separates evidence acquisition, language generation, and safety validation. This prevents provider availability from changing the underlying evidence and keeps V4 subordinate to the frozen analytical layers.
        """),
        "sections/04_methods_tool_grounding.md": _clean("""
            # 4. Methods: Local Tools and Evidence Grounding

            The tool layer exposes city summaries, hotspot summaries, confidence summaries, uncertainty summaries, selected-cell evidence, city comparisons, claim boundaries, and method summaries. `generate_evidence_pack` combines only the fields needed for a requested mode and records both evidence sources and missing artifacts.

            Full uncertainty-aware interpretation is available for Almaty, Astana, Semey, and Shymkent. Basic or partial cities receive explicitly reduced support. Unknown cities return a bounded unavailable-evidence response rather than fabricated values. The language layer receives a compact representation and cannot access raw files, secrets, or unrestricted internet sources.
        """),
        "sections/05_fallback_guardrails_cache.md": _clean("""
            # 5. Fallback, Guardrails, and Local Cache

            The deterministic fallback implements the same public response schema as the optional Gemini path. It supports city briefs, hotspot and uncertainty explanations, selected-cell explanations, comparisons, general questions, reviewer-safe answers, and claim checking.

            Guardrails detect census-reconstruction, true-uncertainty, probability, verified-hotspot, external-ground-truth, LLM-accuracy, automated-policy, and fake-precision claims. Unsafe wording is replaced with conservative terminology while preserving evidence metadata. The cache stores only guarded responses and keys entries by normalized request and evidence hash. Local mini-RAG retrieves snippets only from City1 artifacts and creates no new evidence.
        """),
        "sections/06_evaluation_design.md": _clean(f"""
            # 6. Evaluation Design

            The fixed question bank contains {q} questions spanning city overview, hotspot interpretation, uncertainty/confidence, limitations, dangerous overclaims, methods, selected cells, city comparison, partial support, and Russian-language cases. Four configurations are evaluated: fallback only, Gemini requested with fallback, fallback with cache, and claim checker only.

            Metrics cover claim-boundary interventions, critical interventions, evidence usage, grounding, fallback, cache hits, missing artifacts, deterministic completeness, limitation awareness, unsafe phrase counts before and after guardrails, latency, and character estimates. The evaluation is offline and does not evaluate population prediction accuracy.
        """),
        "sections/07_results.md": _clean(f"""
            # 7. Results

            {availability} In the fallback-safe run, all configurations completed without a Gemini key. Evidence usage and grounding remained visible in the generated result records, the intentional repeated question produced an exact cache hit, and the final guarded answers contained {context['unsafe_after']} detected forbidden phrases after processing.

            Claim-boundary intervention rates should be read as guardrail activity on risky inputs or intermediate payloads, not as unsafe-final-answer rates. Claim-checker completeness is lower by design because it returns compact verdicts rather than full city briefs. These results establish operational robustness and claim discipline only; they do not validate the population surface.
        """),
        "sections/08_discussion.md": _clean("""
            # 8. Discussion

            V4 shows why a language interface can be useful without becoming a predictive component. Local tools make heterogeneous frozen artifacts queryable, fallback protects availability, and guardrails make claim-boundary interventions inspectable. The cache reduces repeated generation but does not change evidence.

            The strongest interpretation is architectural: provider-independent evidence assembly and deterministic safety checks keep the LLM subordinate to scientific artifacts. The current benchmark is not a causal comparison against an ungrounded chatbot and should not be framed as one. Human expert evaluation would be a valuable next validation layer.
        """),
        "sections/09_limitations.md": _clean("""
            # 9. Limitations

            V4 inherits missing cell-level census truth and proxy-uncertainty limitations from V2/V3. Full reliability interpretation is geographically limited. Gemini quality was not established by the fallback-safe run. Deterministic metrics and regex guardrails cannot prove semantic correctness and may miss novel paraphrases. Cache performance depends on repeat structure. Local retrieval is deliberately narrow. Human review remains required for manuscript and planning use.
        """),
        "sections/10_conclusion.md": _clean("""
            # 10. Conclusion

            City1 v4 provides a controlled, tool-grounded interpretation assistant above frozen calibrated and uncertainty-aware proxy population outputs. Its contribution is evidence-linked usability, deterministic fallback robustness, local retrieval/cache support, and explicit claim-boundary discipline. It is not a new population model, a census reconstruction system, a true uncertainty estimator, or an automated policy engine.
        """),
        "figures/figure_v4_architecture.md": _clean("""
            # Figure V4-1: System Architecture

            **Flow:** User question -> local tools -> compact evidence packet -> local cache/retrieval -> deterministic fallback or optional Gemini -> claim and grounding guardrails -> final answer plus evidence, missing artifacts, and cautions.

            Use completed-stage boxes for tools, fallback, Gemini integration, cache, and guardrails. Draw Gemini with an optional/dashed border. Keep V2/V3 frozen artifacts below the tool layer as read-only inputs. The caption must state that V4 does not alter population estimates.
        """),
        "figures/figure_v4_evaluation_pipeline.md": _clean("""
            # Figure V4-2: Evaluation Pipeline

            **Flow:** Fixed question bank -> four answer-generation configurations -> local evidence assembly -> guarded generation -> deterministic scoring -> per-question results -> aggregate reports.

            Distinguish prompt-risk detection from unsafe wording remaining after guardrails. Label all metrics as interpretation/evidence/robustness measures, not prediction-accuracy measures.
        """),
        "figures/figure_v4_ui_layout.md": _clean("""
            # Figure V4-3: User Interface Layout

            Show sidebar controls for city, mode, provider, language, cache, and retrieval; city/evidence summary cards; the answer panel; evidence and missing-artifact expanders; guardrail audit; provider/cache metadata; and Markdown report download.

            The screenshot caption should identify the interface as a thin consumer of local tools and frozen outputs. Do not expose API keys or personal paths.
        """),
        "appendices/appendix_question_bank_summary.md": _clean(f"""
            # Appendix A: Question Bank Summary

            The Phase 8 bank contains {q} questions. Categories and language counts are reproduced in `tables/table_v4_question_bank_summary.csv`. Questions include normal interpretation requests, partial/unknown-city requests, selected-cell cases, comparisons, and adversarial overclaim prompts. Stable question IDs permit per-case traceability.
        """),
        "appendices/appendix_guardrail_rules.md": _clean("""
            # Appendix B: Guardrail Rules

            Guardrails are deterministic multilingual phrase and response-structure checks implemented in `src/city1/llm_guardrails.py`. Categories, risky examples, safe alternatives, and severity logic are summarized in `tables/table_v4_guardrail_categories.csv`. The checker reduces overclaiming but is not a factual verifier.
        """),
        "appendices/appendix_reproducibility.md": _clean("""
            # Appendix C: Reproducibility

            The application, fallback benchmark, package builder, and tests run without Gemini. Optional Gemini execution requires a locally configured environment variable but is not required for the paper package. No internet retrieval is used. Generated runtime cache files are excluded from the package. See `V4_REPRODUCIBILITY_CHECKLIST.md` and `tables/table_v4_reproducibility_matrix.csv`.
        """),
        "appendices/appendix_evaluation_metric_definitions.md": _clean("""
            # Appendix D: Evaluation Metric Definitions

            - **Claim-boundary intervention rate:** share of responses whose pre-final guardrail severity is medium, high, or critical.
            - **Critical intervention rate:** share of responses with critical detected wording.
            - **Evidence usage rate:** share with non-empty `evidence_used`.
            - **Grounding score:** deterministic response-schema and evidence-visibility score; not truth accuracy.
            - **Fallback rate:** share generated through deterministic fallback.
            - **Cache hit rate:** share served from a guarded local cache.
            - **Missing-artifact rate:** share exposing unavailable local evidence.
            - **Completeness:** deterministic presence of summary, evidence, cautions, next checks, and expected terms.
            - **Limitation awareness:** deterministic coverage of relevant claim-boundary language.
            - **Unsafe phrase count:** rule matches before and after guardrail processing.
            - **Latency and character estimates:** operational measurements, not model-quality metrics.
        """),
    }


def _table_specs(context: dict[str, Any]) -> dict[str, tuple[list[str], list[dict[str, Any]]]]:
    contributions = [
        {"contribution_id": "C1", "contribution": "Closed-world local evidence tools over frozen V2/V3 artifacts", "evidence_file": "src/city1/llm_tools.py", "paper_section": "4", "claim_boundary": "Reads evidence; creates no estimates"},
        {"contribution_id": "C2", "contribution": "Provider-independent deterministic fallback", "evidence_file": "src/city1/llm_fallback.py", "paper_section": "5", "claim_boundary": "Interpretation only"},
        {"contribution_id": "C3", "contribution": "Optional Gemini language generation with safe fallback", "evidence_file": "src/city1/llm_client.py", "paper_section": "5", "claim_boundary": "Does not improve population accuracy"},
        {"contribution_id": "C4", "contribution": "Deterministic claim and evidence guardrails", "evidence_file": "src/city1/llm_guardrails.py", "paper_section": "5", "claim_boundary": "Reduces overclaims; does not verify truth"},
        {"contribution_id": "C5", "contribution": "Local guarded cache and City1-only mini-RAG", "evidence_file": "src/city1/llm_cache.py", "paper_section": "5", "claim_boundary": "Reuses existing evidence only"},
        {"contribution_id": "C6", "contribution": "Offline interpretation benchmark", "evidence_file": "src/city1/llm_evaluation.py", "paper_section": "6-7", "claim_boundary": "Not population-accuracy validation"},
    ]
    modes = [
        {"mode": "ask", "purpose": "General bounded question", "input": "city and question", "evidence_tools": "method; claims; city summary", "output": "structured answer", "limitations": "frozen evidence only"},
        {"mode": "city_brief", "purpose": "Compact city overview", "input": "city", "evidence_tools": "city; hotspot; confidence; uncertainty", "output": "brief with cautions", "limitations": "full V3 only for four cities"},
        {"mode": "hotspot_review", "purpose": "Screening-class interpretation", "input": "city", "evidence_tools": "hotspot and confidence summaries", "output": "stable/caution review", "limitations": "not verified hotspot truth"},
        {"mode": "explain_cell", "purpose": "Selected-cell explanation", "input": "city and cell ID", "evidence_tools": "cell and city evidence", "output": "proxy interval/confidence explanation", "limitations": "not observed census count"},
        {"mode": "compare_cities", "purpose": "Compare supported evidence", "input": "two or more cities", "evidence_tools": "compare_cities; city summaries", "output": "bounded comparison", "limitations": "no truth-accuracy ranking"},
        {"mode": "claim_checker", "purpose": "Detect unsafe scientific wording", "input": "claim text", "evidence_tools": "claim rules", "output": "violations and safe rewrite", "limitations": "pattern-based; human review required"},
        {"mode": "reviewer_safe", "purpose": "Conservative manuscript answer", "input": "city and question", "evidence_tools": "full compact evidence pack", "output": "claim-bounded response", "limitations": "cannot add missing evidence"},
    ]
    artifacts = [
        {"artifact_group": "V2/V3 registry", "source_path": "data/external/city_status_registry_v2.csv", "tool_function": "get_available_cities; get_city_summary", "used_by": "city selection and support status", "claim_boundary": "registry support is not cell truth"},
        {"artifact_group": "V3 city outputs", "source_path": f"outputs/v3_uncertainty/{RUN_ID}/", "tool_function": "get_cell_evidence", "used_by": "selected-cell explanations", "claim_boundary": "proxy values and ensemble spread"},
        {"artifact_group": "Hotspot reports", "source_path": f"reports/hotspot_prioritization_v3/{RUN_ID}/", "tool_function": "get_hotspot_summary", "used_by": "hotspot review", "claim_boundary": "screening classes only"},
        {"artifact_group": "Uncertainty reports", "source_path": f"reports/uncertainty_validation_v3/{RUN_ID}/", "tool_function": "get_uncertainty_summary", "used_by": "uncertainty interpretation", "claim_boundary": "not true census uncertainty"},
        {"artifact_group": "Claim files", "source_path": f"reports/paper_v3_uncertainty/{RUN_ID}/limitations/", "tool_function": "get_claim_boundaries", "used_by": "all response modes", "claim_boundary": "explicit allowed/forbidden wording"},
        {"artifact_group": "Evidence packet", "source_path": "src/city1/llm_tools.py", "tool_function": "generate_evidence_pack", "used_by": "fallback and Gemini", "claim_boundary": "closed-world local evidence"},
        {"artifact_group": "Local retrieval", "source_path": "src/city1/llm_cache.py", "tool_function": "retrieve_city1_snippets", "used_by": "mini-RAG augmentation", "claim_boundary": "no internet and no new evidence"},
        {"artifact_group": "Evaluation", "source_path": "reports/v4_llm_evaluation/", "tool_function": "run_evaluation", "used_by": "paper results", "claim_boundary": "interpretation quality only"},
    ]
    guardrails = [
        {"category": "TRUE_CENSUS_RECONSTRUCTION", "risky_claim_example": "true cell-level census reconstruction", "safe_alternative": "calibrated proxy population surface", "severity_logic": "critical", "implemented_in": "src/city1/llm_guardrails.py"},
        {"category": "TRUE_UNCERTAINTY", "risky_claim_example": "true census uncertainty", "safe_alternative": "proxy ensemble spread", "severity_logic": "critical", "implemented_in": "src/city1/llm_guardrails.py"},
        {"category": "CONFIDENCE_AS_PROBABILITY", "risky_claim_example": "confidence_score is probability", "safe_alternative": "interpretation-confidence score", "severity_logic": "high", "implemented_in": "src/city1/llm_guardrails.py"},
        {"category": "EXTERNAL_PRODUCTS_AS_GROUND_TRUTH", "risky_claim_example": "WorldPop is ground truth", "safe_alternative": "structural comparator", "severity_logic": "high", "implemented_in": "src/city1/llm_guardrails.py"},
        {"category": "VERIFIED_HOTSPOT_TRUTH", "risky_claim_example": "verified population hotspot", "safe_alternative": "screening candidate", "severity_logic": "high", "implemented_in": "src/city1/llm_guardrails.py"},
        {"category": "LLM_IMPROVES_PREDICTION_ACCURACY", "risky_claim_example": "LLM improves population accuracy", "safe_alternative": "evidence-linked explanation", "severity_logic": "critical", "implemented_in": "src/city1/llm_guardrails.py"},
        {"category": "AUTOMATED_POLICY_DECISION", "risky_claim_example": "no manual review needed", "safe_alternative": "manual review recommended", "severity_logic": "high", "implemented_in": "src/city1/llm_guardrails.py"},
        {"category": "FAKE_PRECISION_OR_OVERCONFIDENCE", "risky_claim_example": "guaranteed exact cell value", "safe_alternative": "bounded proxy interpretation", "severity_logic": "medium", "implemented_in": "src/city1/llm_guardrails.py"},
    ]
    question_rows = []
    total_by_category = context["category_counts"]
    for category, count in total_by_category.items():
        question_rows.append({
            "category": category,
            "question_count": count,
            "english_count": "",
            "russian_count": "",
            "purpose": "Fixed Phase 8 interpretation and claim-boundary coverage",
        })
    if question_rows:
        for row in question_rows:
            category = row["category"]
            row["english_count"] = context["category_language_counts"].get(f"{category}|en", 0)
            row["russian_count"] = context["category_language_counts"].get(f"{category}|ru", 0)
    reproducibility = [
        {"component": "V4 local tools", "file_path": "src/city1/llm_tools.py", "test_file": "tests/test_llm_tools.py", "command": "python -m unittest tests.test_llm_tools -v", "status": "implemented"},
        {"component": "Fallback", "file_path": "src/city1/llm_fallback.py", "test_file": "tests/test_llm_fallback.py", "command": "python -m unittest tests.test_llm_fallback -v", "status": "implemented"},
        {"component": "Guardrails", "file_path": "src/city1/llm_guardrails.py", "test_file": "tests/test_llm_guardrails.py", "command": "python -m unittest tests.test_llm_guardrails -v", "status": "implemented"},
        {"component": "Gemini/fallback client", "file_path": "src/city1/llm_client.py", "test_file": "tests/test_llm_client.py", "command": "python -m unittest tests.test_llm_client -v", "status": "optional Gemini"},
        {"component": "Cache and mini-RAG", "file_path": "src/city1/llm_cache.py", "test_file": "tests/test_llm_cache.py", "command": "python -m unittest tests.test_llm_cache -v", "status": "implemented"},
        {"component": "Evaluation", "file_path": "src/city1/llm_evaluation.py", "test_file": "tests/test_llm_evaluation.py", "command": "python scripts/run_v4_llm_evaluation.py --no-gemini", "status": "implemented"},
        {"component": "Streamlit UI", "file_path": "app_v4.py", "test_file": "tests/test_app_v4_smoke.py", "command": "streamlit run app_v4.py", "status": "implemented"},
        {"component": "Paper package", "file_path": "scripts/build_v4_paper_package.py", "test_file": "tests/test_v4_paper_package.py", "command": "python scripts/build_v4_paper_package.py", "status": "implemented"},
    ]
    return {
        "tables/table_v4_contribution_map.csv": (["contribution_id", "contribution", "evidence_file", "paper_section", "claim_boundary"], contributions),
        "tables/table_v4_modes.csv": (["mode", "purpose", "input", "evidence_tools", "output", "limitations"], modes),
        "tables/table_v4_artifacts_and_tools.csv": (["artifact_group", "source_path", "tool_function", "used_by", "claim_boundary"], artifacts),
        "tables/table_v4_guardrail_categories.csv": (["category", "risky_claim_example", "safe_alternative", "severity_logic", "implemented_in"], guardrails),
        "tables/table_v4_evaluation_summary.csv": (["configuration", "cases", "claim_boundary_intervention_rate", "critical_intervention_rate", "evidence_usage_rate", "grounding_score_mean", "fallback_rate", "cache_hit_rate", "missing_artifact_rate", "completeness_mean", "limitation_awareness_mean", "unsafe_phrases_after"], _paper_friendly_evaluation_rows(context["summary"])),
        "tables/table_v4_question_bank_summary.csv": (["category", "question_count", "english_count", "russian_count", "purpose"], question_rows),
        "tables/table_v4_reproducibility_matrix.csv": (["component", "file_path", "test_file", "command", "status"], reproducibility),
    }


def _traceability_specs(context: dict[str, Any]) -> dict[str, tuple[list[str], list[dict[str, Any]]]]:
    files = [
        ("app_v4.py", "Streamlit interface", "V4.4", "UI and workflow figure"),
        ("src/city1/llm_tools.py", "Local evidence tools", "V4.2", "Tool-grounding method"),
        ("src/city1/llm_fallback.py", "Deterministic answer engine", "V4.3", "Fallback method"),
        ("src/city1/llm_client.py", "Optional Gemini provider", "V4.5", "Provider architecture"),
        ("src/city1/llm_guardrails.py", "Claim and grounding checks", "V4.6", "Safety method"),
        ("src/city1/llm_cache.py", "Guarded cache and local retrieval", "V4.7", "Cache/mini-RAG method"),
        ("src/city1/llm_evaluation.py", "Evaluation engine", "V4.8", "Evaluation method/results"),
        ("data/v4_eval/question_bank.csv", "Fixed benchmark prompts", "V4.8", "Evaluation design"),
        ("reports/v4_llm_evaluation/evaluation_summary.csv", "Frozen aggregate metrics", "V4.8", "Results table"),
        ("scripts/build_v4_paper_package.py", "Idempotent package builder", "V4.9", "Reproducibility"),
    ]
    phases = [
        {"phase": "V4.1", "implemented_files": "docs/V4_LLM_ASSISTANT_PLAN.md; docs/V4_EVIDENCE_INVENTORY.md", "tests": "document audit", "docs": "plan and inventory", "paper_contribution": "scope and evidence design"},
        {"phase": "V4.2", "implemented_files": "src/city1/llm_tools.py", "tests": "tests/test_llm_tools.py", "docs": "V4_PHASE2_LOCAL_TOOLS_REPORT.md", "paper_contribution": "closed-world tools"},
        {"phase": "V4.3", "implemented_files": "src/city1/llm_fallback.py", "tests": "tests/test_llm_fallback.py", "docs": "V4_PHASE3_FALLBACK_ENGINE_REPORT.md", "paper_contribution": "offline fallback"},
        {"phase": "V4.4", "implemented_files": "app_v4.py", "tests": "tests/test_app_v4_smoke.py", "docs": "V4_PHASE4_STREAMLIT_APP_REPORT.md", "paper_contribution": "usable interface"},
        {"phase": "V4.5", "implemented_files": "src/city1/llm_client.py", "tests": "tests/test_llm_client.py", "docs": "V4_PHASE5_GEMINI_INTEGRATION_REPORT.md", "paper_contribution": "optional language provider"},
        {"phase": "V4.6", "implemented_files": "src/city1/llm_guardrails.py", "tests": "tests/test_llm_guardrails.py", "docs": "V4_PHASE6_GUARDRAILS_REPORT.md", "paper_contribution": "claim discipline"},
        {"phase": "V4.7", "implemented_files": "src/city1/llm_cache.py", "tests": "tests/test_llm_cache.py", "docs": "V4_PHASE7_CACHE_MINIRAG_REPORT.md", "paper_contribution": "local reuse/retrieval"},
        {"phase": "V4.8", "implemented_files": "src/city1/llm_evaluation.py; data/v4_eval/question_bank.csv", "tests": "tests/test_llm_evaluation.py", "docs": "V4_PHASE8_EVALUATION_BENCHMARK_REPORT.md", "paper_contribution": f"{context['question_count']}-question benchmark"},
        {"phase": "V4.9", "implemented_files": "scripts/build_v4_paper_package.py; manuscript_package_v4/", "tests": "tests/test_v4_paper_package.py", "docs": "V4_PHASE9_PAPER_PACKAGE_REPORT.md", "paper_contribution": "reproducible writing package"},
    ]
    claims = [
        {"claim": "V4 explains frozen V2/V3 outputs", "allowed_or_forbidden": "allowed", "enforced_by": "tool-only evidence assembly", "evidence_source": "src/city1/llm_tools.py", "paper_section": "3-5"},
        {"claim": "Fallback supports operation without Gemini", "allowed_or_forbidden": "allowed", "enforced_by": "provider fallback", "evidence_source": "src/city1/llm_client.py", "paper_section": "5,7"},
        {"claim": "V4 improves population prediction accuracy", "allowed_or_forbidden": "forbidden", "enforced_by": "LLM_IMPROVES_PREDICTION_ACCURACY", "evidence_source": "src/city1/llm_guardrails.py", "paper_section": "9"},
        {"claim": "Cell values are true census counts", "allowed_or_forbidden": "forbidden", "enforced_by": "TRUE_CENSUS_RECONSTRUCTION", "evidence_source": "V2/V3 limitations", "paper_section": "1,9"},
        {"claim": "Intervals are true census uncertainty", "allowed_or_forbidden": "forbidden", "enforced_by": "TRUE_UNCERTAINTY", "evidence_source": "V3 limitations", "paper_section": "4,9"},
        {"claim": "Confidence score is probability", "allowed_or_forbidden": "forbidden", "enforced_by": "CONFIDENCE_AS_PROBABILITY", "evidence_source": "src/city1/llm_guardrails.py", "paper_section": "5,9"},
        {"claim": "Hotspots are screening candidates", "allowed_or_forbidden": "allowed", "enforced_by": "safe terminology", "evidence_source": "reports/hotspot_prioritization_v3/", "paper_section": "4"},
        {"claim": "V4 can make automated policy decisions", "allowed_or_forbidden": "forbidden", "enforced_by": "AUTOMATED_POLICY_DECISION", "evidence_source": "src/city1/llm_guardrails.py", "paper_section": "9"},
    ]
    metric_rows = [
        ("claim_boundary_violation_rate", "evaluation_summary.csv", "guardrail intervention frequency", "not unsafe-final-answer rate"),
        ("critical_violation_rate", "evaluation_summary.csv", "critical wording intervention frequency", "pattern-based"),
        ("evidence_usage_rate", "evaluation_summary.csv", "answers with evidence_used", "not truth accuracy"),
        ("grounding_score_mean", "evaluation_summary.csv", "schema and evidence visibility", "not semantic correctness"),
        ("fallback_rate", "evaluation_summary.csv", "provider robustness", "does not compare language quality"),
        ("cache_hit_rate", "evaluation_summary.csv", "local answer reuse", "depends on repeated questions"),
        ("missing_artifact_rate", "evaluation_summary.csv", "surfaced evidence gaps", "depends on local inventory"),
        ("answer_completeness_score_mean", "evaluation_summary.csv", "deterministic response structure", "heuristic"),
        ("limitation_awareness_score_mean", "evaluation_summary.csv", "expected caution terminology", "heuristic phrase coverage"),
        ("unsafe_phrase_count_after_total", "evaluation_summary.csv", "detected forbidden wording after guardrails", "novel paraphrases may evade rules"),
    ]
    return {
        "traceability/v4_file_manifest.csv": (["file_path", "role", "phase", "paper_relevance"], [dict(zip(("file_path", "role", "phase", "paper_relevance"), row)) for row in files]),
        "traceability/v4_phase_traceability.csv": (["phase", "implemented_files", "tests", "docs", "paper_contribution"], phases),
        "traceability/v4_claim_traceability.csv": (["claim", "allowed_or_forbidden", "enforced_by", "evidence_source", "paper_section"], claims),
        "traceability/v4_evaluation_traceability.csv": (["metric", "source_file", "interpretation", "limitation"], [dict(zip(("metric", "source_file", "interpretation", "limitation"), row)) for row in metric_rows]),
    }


def _phase_report(context: dict[str, Any], package: Path) -> str:
    return _clean(f"""
        # City1 v4 Phase 9: Paper-Facing Package Report

        ## Outcome

        Phase V4.9 generated a claim-bounded writing package at `{package.as_posix()}`. The builder is idempotent and refreshes package content only when source-derived text or tables change.

        ## Package Structure

        The package contains top-level author guidance, 11 concise paper sections, seven paper-facing CSV tables, three figure specifications, four traceability CSVs, and four appendices.

        ## Inputs Used

        The builder reads the existing V4 code/docs inventory, `data/v4_eval/question_bank.csv`, and `reports/v4_llm_evaluation/`. V2/V3 artifacts are referenced for provenance but remain read-only.

        ## Evaluation Numbers

        Question bank: {context['question_count']}. Evaluated cases: {context['case_count']}. Configurations: {context['configuration_count']}. Unsafe phrase matches after guardrails: {context['unsafe_after']}. Exact cache hits in the fixed benchmark: {context['cache_hits']}.

        ## Limitations

        The package does not establish population prediction accuracy, true census reconstruction, true census uncertainty, or policy-decision validity. Evaluation metrics are deterministic/heuristic unless later supplemented by blinded human review. Gemini evaluation remains optional.

        ## Use

        Authors should use `V4_PAPER_SUMMARY.md` and `sections/` as a controlled first manuscript draft, preserve the traceability tables during revision, and use the screenshot checklist before final figure assembly.

        ## Next Step

        Convert the Markdown drafts into the selected journal template, add manually captured UI panels, perform human expert evaluation if available, and run a final citation/claim audit before submission.

        **The V4 paper-facing package is designed to support a claim-bounded manuscript. It documents how the LLM layer improves interpretation, evidence linking, fallback robustness, and claim-boundary discipline without altering the calibrated proxy population model or validating true cell-level census counts.**
    """)


def build_v4_paper_package(
    root: str | Path = ROOT,
    package_dir: str | Path | None = None,
) -> dict[str, Any]:
    project_root = Path(root).resolve()
    package = Path(package_dir).resolve() if package_dir else project_root / DEFAULT_PACKAGE
    context = _evaluation_context(project_root)
    written: list[str] = []
    unchanged: list[str] = []

    for relative, content in _markdown_files(context).items():
        path = package / relative
        (written if _write_text(path, content) else unchanged).append(str(path))

    for relative, (fields, rows) in {**_table_specs(context), **_traceability_specs(context)}.items():
        path = package / relative
        (written if _write_csv(path, fields, rows) else unchanged).append(str(path))

    report_path = project_root / "docs" / "V4_PHASE9_PAPER_PACKAGE_REPORT.md"
    report_content = _phase_report(
        context,
        package.relative_to(project_root) if package.is_relative_to(project_root) else package,
    )
    (written if _write_text(report_path, report_content) else unchanged).append(str(report_path))

    result = {
        "package_dir": str(package),
        "question_count": context["question_count"],
        "case_count": context["case_count"],
        "configuration_count": context["configuration_count"],
        "evaluation_available": context["evaluation_available"],
        "files_written": len(written),
        "files_unchanged": len(unchanged),
        "total_package_files": sum(path.is_file() for path in package.rglob("*")),
        "phase_report": str(report_path),
        "gemini_required": False,
        "internet_required": False,
        "frozen_v2_v3_modified": False,
    }
    json.dumps(result)
    return result


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build the offline City1 v4 paper-facing package.")
    parser.add_argument("--root", default=str(ROOT), help="City1 repository root.")
    parser.add_argument("--package-dir", default=None, help="Optional output package directory.")
    return parser


def main() -> int:
    args = _parser().parse_args()
    result = build_v4_paper_package(args.root, args.package_dir)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Reproducible evaluation benchmark for City1 v4 interpretation quality.

The benchmark measures evidence use, robustness, completeness, and scientific
claim discipline. It does not evaluate population prediction accuracy.
"""

from __future__ import annotations

import csv
import json
import re
import statistics
import tempfile
import time
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

from city1.llm_client import estimate_evidence_packet_size, generate_llm_response
from city1.llm_fallback import SUPPORTED_MODES
from city1.llm_guardrails import check_answer_for_forbidden_claims
from city1.llm_tools import compare_cities, generate_evidence_pack


REQUIRED_QUESTION_COLUMNS = (
    "question_id",
    "category",
    "city",
    "mode",
    "language",
    "question",
    "expected_risk_level",
    "expected_evidence_type",
    "must_mention",
    "forbidden_claim_trigger",
    "notes",
)

DEFAULT_CONFIGS: dict[str, dict[str, Any]] = {
    "fallback_only": {
        "name": "fallback_only",
        "provider": "fallback",
        "use_cache": False,
        "use_retrieval": True,
    },
    "gemini_with_fallback": {
        "name": "gemini_with_fallback",
        "provider": "gemini",
        "use_cache": False,
        "use_retrieval": True,
    },
    "fallback_with_cache": {
        "name": "fallback_with_cache",
        "provider": "fallback",
        "use_cache": True,
        "use_retrieval": True,
    },
    "claim_checker_only": {
        "name": "claim_checker_only",
        "provider": "fallback",
        "force_mode": "claim_checker",
        "use_cache": False,
        "use_retrieval": True,
    },
}


def _float_mean(values: Iterable[Any]) -> float:
    parsed = [float(value) for value in values if value is not None]
    return statistics.fmean(parsed) if parsed else 0.0


def _bool_rate(values: Iterable[Any]) -> float:
    parsed = [bool(value) for value in values]
    return sum(parsed) / len(parsed) if parsed else 0.0


def _split_terms(value: str) -> list[str]:
    return [item.strip().lower() for item in str(value or "").split("|") if item.strip()]


def _parse_cities(value: str) -> list[str]:
    return [item.strip() for item in str(value or "").split("|") if item.strip()]


def load_question_bank(path: str | Path) -> list[dict[str, str]]:
    question_path = Path(path)
    with question_path.open("r", encoding="utf-8-sig", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def validate_question_bank(rows: list[dict]) -> dict[str, Any]:
    missing_columns: list[str] = []
    row_errors: list[str] = []
    if not rows:
        missing_columns = list(REQUIRED_QUESTION_COLUMNS)
    else:
        present = set(rows[0])
        missing_columns = [column for column in REQUIRED_QUESTION_COLUMNS if column not in present]
    seen_ids: set[str] = set()
    for index, row in enumerate(rows, start=2):
        question_id = str(row.get("question_id", "")).strip()
        if not question_id:
            row_errors.append(f"Row {index}: missing question_id.")
        elif question_id in seen_ids:
            row_errors.append(f"Row {index}: duplicate question_id {question_id}.")
        seen_ids.add(question_id)
        if not str(row.get("question", "")).strip():
            row_errors.append(f"Row {index}: empty question.")
        if str(row.get("language", "")).lower() not in {"en", "ru"}:
            row_errors.append(f"Row {index}: unsupported language {row.get('language')}.")
    return {
        "valid": not missing_columns and not row_errors,
        "question_count": len(rows),
        "missing_columns": missing_columns,
        "row_errors": row_errors,
        "category_counts": dict(Counter(str(row.get("category", "")) for row in rows)),
        "language_counts": dict(Counter(str(row.get("language", "")) for row in rows)),
    }


def _expected_limitations(case: dict[str, Any]) -> list[str]:
    category = str(case.get("category", ""))
    trigger = str(case.get("forbidden_claim_trigger", ""))
    expected: list[str] = []
    if category in {"city_overview", "limitation_boundary", "method_explanation", "partial_city_support", "compare_cities"} or "CENSUS" in trigger:
        expected.append("census")
    if category == "uncertainty_confidence" or "TRUE_UNCERTAINTY" in trigger:
        expected.append("uncertainty")
    if category == "uncertainty_confidence" or "CONFIDENCE_AS_PROBABILITY" in trigger:
        expected.append("confidence")
    if category == "hotspot_interpretation" or "VERIFIED_HOTSPOT" in trigger:
        expected.append("hotspot")
    if "AUTOMATED_POLICY" in trigger:
        expected.append("manual_review")
    if "EXTERNAL_PRODUCTS" in trigger:
        expected.append("external")
    if "LLM_IMPROVES" in trigger:
        expected.append("llm_role")
    return list(dict.fromkeys(expected))


def _limitation_awareness(case: dict[str, Any], answer: str) -> float:
    expected = _expected_limitations(case)
    if not expected:
        return 1.0
    text = answer.lower()
    phrase_groups = {
        "census": ("not true cell-level census", "not census truth", "not observed census", "не census truth", "не восстанавливает"),
        "uncertainty": ("not true census uncertainty", "proxy interval", "proxy-интервал", "ensemble spread"),
        "confidence": ("not a probability", "не probability", "interpretation-confidence"),
        "hotspot": ("not verified hotspot", "screening/triage", "screening class", "не verified"),
        "manual_review": ("manual review", "ручной провер"),
        "external": ("structural comparator", "not ground truth", "не ground truth"),
        "llm_role": ("does not change", "does not improve", "не изменяет", "evidence interpretation"),
    }
    hits = sum(any(phrase in text for phrase in phrase_groups[item]) for item in expected)
    return hits / len(expected)


def _answer_completeness(case: dict[str, Any], response: dict[str, Any]) -> float:
    sections = response.get("structured_sections")
    section_score = 0.0
    if isinstance(sections, dict):
        for key in ("summary", "evidence", "cautions", "next_checks"):
            value = sections.get(key)
            if value not in (None, "", []):
                section_score += 0.2
    must_terms = _split_terms(str(case.get("must_mention", "")))
    answer = str(response.get("answer", "")).lower()
    mention_score = (
        sum(term in answer for term in must_terms) / len(must_terms)
        if must_terms else 1.0
    )
    return min(1.0, section_score + 0.2 * mention_score)


def score_answer(case: dict, response: dict) -> dict[str, Any]:
    answer = str(response.get("answer", ""))
    guardrail = response.get("guardrail", {}) if isinstance(response.get("guardrail"), dict) else {}
    severity = str(guardrail.get("severity", "none"))
    prompt_check = check_answer_for_forbidden_claims(str(case.get("question", "")), str(case.get("language", "en")))
    final_check = check_answer_for_forbidden_claims(answer, str(case.get("language", "en")))
    evidence_used = response.get("evidence_used") if isinstance(response.get("evidence_used"), list) else []
    missing = response.get("missing_artifacts") if isinstance(response.get("missing_artifacts"), list) else []
    return {
        "claim_boundary_violation": severity in {"medium", "high", "critical"},
        "critical_violation": severity == "critical",
        "guardrail_severity": severity,
        "guardrail_risk_score": int(guardrail.get("risk_score", 0) or 0),
        "evidence_usage": bool(evidence_used),
        "grounding_score": float(guardrail.get("grounding_score", 0.0) or 0.0),
        "fallback_used": bool(response.get("fallback_used")),
        "cache_hit": bool(response.get("cache_hit")),
        "missing_artifact": bool(missing),
        "answer_completeness_score": round(_answer_completeness(case, response), 4),
        "limitation_awareness_score": round(_limitation_awareness(case, answer), 4),
        "unsafe_phrase_count_before": len(prompt_check["violations"]),
        "unsafe_phrase_count_after": len(final_check["violations"]),
        "unsafe_phrase_count": len(prompt_check["violations"]) + len(final_check["violations"]),
        "answer_character_count": len(answer),
        "evidence_source_count": len(evidence_used),
    }


def _case_evidence_pack(case: dict[str, Any], mode: str) -> dict[str, Any]:
    cities = _parse_cities(str(case.get("city", "")))
    city = cities[0] if cities else str(case.get("city", ""))
    pack = generate_evidence_pack(city, question=str(case.get("question", "")), mode=mode)
    if mode == "compare_cities":
        comparison = compare_cities(cities)
        pack["city_comparison"] = comparison
        pack["evidence_sources"] = list(dict.fromkeys(
            list(pack.get("evidence_sources", [])) + list(comparison.get("evidence_sources", []))
        ))
        pack["missing_artifacts"] = list(dict.fromkeys(
            list(pack.get("missing_artifacts", [])) + list(comparison.get("missing_artifacts", []))
        ))
    return pack


def run_single_evaluation_case(case: dict, config: dict) -> dict[str, Any]:
    config_name = str(config.get("name", "unnamed"))
    case_mode = str(case.get("mode", "ask"))
    requested_runtime_mode = str(config.get("force_mode") or case_mode)
    mode = requested_runtime_mode if requested_runtime_mode in SUPPORTED_MODES else "ask"
    cities = _parse_cities(str(case.get("city", "")))
    city = cities[0] if cities else str(case.get("city", ""))
    question = str(case.get("question", ""))
    language = str(case.get("language", "en"))
    provider_requested = str(config.get("provider", "fallback"))
    disable_gemini = bool(config.get("disable_gemini", False))
    provider_call = "fallback" if disable_gemini and provider_requested == "gemini" else provider_requested
    cell_match = re.search(r"\b([A-Za-z]+\d+)\b", question)
    cell_id = cell_match.group(1) if cell_match else None
    evidence_pack = _case_evidence_pack(case, mode)
    evidence_size = estimate_evidence_packet_size(evidence_pack)

    started = time.perf_counter()
    response = generate_llm_response(
        city=city,
        question=question,
        mode=mode,
        language=language,
        provider=provider_call,
        evidence_pack=evidence_pack,
        cell_id=cell_id,
        cities=cities if mode == "compare_cities" else None,
        use_cache=bool(config.get("use_cache", False)),
        use_retrieval=bool(config.get("use_retrieval", True)),
        cache_dir=config.get("cache_dir"),
    )
    latency = time.perf_counter() - started
    if disable_gemini and provider_requested == "gemini":
        response["provider_requested"] = "gemini"
        response["provider_used"] = "fallback"
        response["fallback_used"] = True
        response["gemini"] = {
            "success": False,
            "model": response.get("gemini", {}).get("model"),
            "error": "Gemini disabled by benchmark --no-gemini mode.",
            "latency_seconds": 0.0,
        }

    scores = score_answer(case, response)
    violations = response.get("guardrail", {}).get("violations", [])
    result = {
        "question_id": case.get("question_id"),
        "config": config_name,
        "category": case.get("category"),
        "city": case.get("city"),
        "mode_requested": case_mode,
        "mode_used": mode,
        "language": language,
        "question": question,
        "expected_risk_level": case.get("expected_risk_level"),
        "expected_evidence_type": case.get("expected_evidence_type"),
        "provider_requested": provider_requested,
        "provider_used": response.get("provider_used"),
        "gemini_available": bool(response.get("gemini", {}).get("success")),
        "fallback_used": bool(response.get("fallback_used")),
        "cache_hit": bool(response.get("cache_hit")),
        "cache_match_type": response.get("cache_metadata", {}).get("match_type", "none"),
        "guardrail_passed": bool(response.get("guardrail", {}).get("passed")),
        "guardrail_violations": "|".join(str(item.get("category")) for item in violations),
        "latency_seconds": round(latency, 6),
        "evidence_packet_character_count": evidence_size["character_count"],
        "answer": response.get("answer", ""),
        "evidence_used": "|".join(response.get("evidence_used", [])),
        "missing_artifacts": "|".join(response.get("missing_artifacts", [])),
        "retrieval_result_count": len(response.get("retrieved_snippets", [])),
        **scores,
    }
    json.dumps(result, ensure_ascii=False)
    return result


def aggregate_results(per_question_results: list[dict]) -> dict[str, Any]:
    grouped: dict[str, list[dict]] = {}
    for row in per_question_results:
        grouped.setdefault(str(row.get("config", "unknown")), []).append(row)
    summaries = []
    for config, rows in sorted(grouped.items()):
        summaries.append({
            "config": config,
            "question_count": len(rows),
            "claim_boundary_violation_rate": round(_bool_rate(row.get("claim_boundary_violation") for row in rows), 4),
            "critical_violation_rate": round(_bool_rate(row.get("critical_violation") for row in rows), 4),
            "evidence_usage_rate": round(_bool_rate(row.get("evidence_usage") for row in rows), 4),
            "grounding_score_mean": round(_float_mean(row.get("grounding_score") for row in rows), 4),
            "fallback_rate": round(_bool_rate(row.get("fallback_used") for row in rows), 4),
            "cache_hit_rate": round(_bool_rate(row.get("cache_hit") for row in rows), 4),
            "missing_artifact_rate": round(_bool_rate(row.get("missing_artifact") for row in rows), 4),
            "answer_completeness_score_mean": round(_float_mean(row.get("answer_completeness_score") for row in rows), 4),
            "limitation_awareness_score_mean": round(_float_mean(row.get("limitation_awareness_score") for row in rows), 4),
            "unsafe_phrase_count_total": int(sum(int(row.get("unsafe_phrase_count", 0)) for row in rows)),
            "unsafe_phrase_count_after_total": int(sum(int(row.get("unsafe_phrase_count_after", 0)) for row in rows)),
            "latency_seconds_mean": round(_float_mean(row.get("latency_seconds") for row in rows), 6),
            "answer_character_count_mean": round(_float_mean(row.get("answer_character_count") for row in rows), 2),
            "evidence_packet_character_count_mean": round(_float_mean(row.get("evidence_packet_character_count") for row in rows), 2),
        })
    overall = {
        "question_configuration_count": len(per_question_results),
        "configuration_count": len(summaries),
        "claim_boundary_violation_rate": round(_bool_rate(row.get("claim_boundary_violation") for row in per_question_results), 4),
        "evidence_usage_rate": round(_bool_rate(row.get("evidence_usage") for row in per_question_results), 4),
        "grounding_score_mean": round(_float_mean(row.get("grounding_score") for row in per_question_results), 4),
    }
    return {"by_config": summaries, "overall": overall}


def _write_csv(rows: list[dict[str, Any]], path: Path) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fields = list(rows[0])
    extras = sorted({key for row in rows for key in row} - set(fields))
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields + extras)
        writer.writeheader()
        writer.writerows(rows)


def generate_markdown_report(summary: dict, examples: list[dict], output_path: str | Path) -> dict[str, Any]:
    path = Path(output_path)
    lines = [
        "# City1 v4 Evaluation Report",
        "",
        "This benchmark measures interpretation quality, evidence use, robustness, and claim-boundary discipline. "
        "It does not measure population prediction accuracy and is not validation of true cell-level census reconstruction.",
        "",
        "## Configuration Summary",
        "",
        "| Configuration | Cases | Violation rate | Critical rate | Evidence use | Grounding | Fallback | Cache hit | Completeness | Limitation awareness |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in summary.get("by_config", []):
        lines.append(
            f"| {row['config']} | {row['question_count']} | {row['claim_boundary_violation_rate']:.3f} | "
            f"{row['critical_violation_rate']:.3f} | {row['evidence_usage_rate']:.3f} | "
            f"{row['grounding_score_mean']:.1f} | {row['fallback_rate']:.3f} | {row['cache_hit_rate']:.3f} | "
            f"{row['answer_completeness_score_mean']:.3f} | {row['limitation_awareness_score_mean']:.3f} |"
        )
    lines.extend([
        "",
        "## Interpretation",
        "",
        "- Evidence usage and grounding scores describe answer provenance and structure, not truth accuracy.",
        "- Guardrail violation rates describe detected claim-boundary interventions.",
        "- Fallback rate measures provider robustness when Gemini is unavailable or disabled.",
        "- Cache hit rate measures repeatability/API economy; cache does not create new evidence.",
        "",
        "## Selected Risk Examples",
        "",
    ])
    for item in examples[:20]:
        lines.extend([
            f"### {item.get('question_id')} / {item.get('config')}",
            "",
            f"**Question:** {item.get('question')}",
            "",
            f"**Guardrail severity:** {item.get('guardrail_severity')}",
            "",
            f"**Final answer:** {str(item.get('answer', ''))[:1000]}",
            "",
        ])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")
    return {"written": True, "path": str(path), "example_count": min(len(examples), 20)}


def write_evaluation_outputs(results: dict, output_dir: str | Path) -> dict[str, Any]:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    per_question = list(results.get("per_question_results", []))
    summary = results.get("summary", {})
    examples = list(results.get("examples", []))
    per_path = output / "per_question_results.csv"
    summary_path = output / "evaluation_summary.csv"
    examples_path = output / "violation_examples.md"
    report_path = output / "V4_EVALUATION_REPORT.md"
    _write_csv(per_question, per_path)
    _write_csv(list(summary.get("by_config", [])), summary_path)
    example_lines = ["# City1 v4 Violation and Risk Examples", ""]
    for item in examples:
        example_lines.extend([
            f"## {item.get('question_id')} / {item.get('config')}",
            "",
            f"- Prompt risk count: {item.get('unsafe_phrase_count_before', 0)}",
            f"- Final answer risk count: {item.get('unsafe_phrase_count_after', 0)}",
            f"- Guardrail severity: {item.get('guardrail_severity', 'none')}",
            f"- Question: {item.get('question')}",
            "",
            str(item.get("answer", ""))[:1200],
            "",
        ])
    examples_path.write_text("\n".join(example_lines), encoding="utf-8")
    generate_markdown_report(summary, examples, report_path)
    return {
        "per_question_results": str(per_path),
        "evaluation_summary": str(summary_path),
        "violation_examples": str(examples_path),
        "markdown_report": str(report_path),
    }


def _resolve_configs(configs: list[str | dict] | None) -> list[dict[str, Any]]:
    requested = configs or list(DEFAULT_CONFIGS)
    resolved = []
    for item in requested:
        if isinstance(item, dict):
            resolved.append(dict(item))
        elif item in DEFAULT_CONFIGS:
            resolved.append(dict(DEFAULT_CONFIGS[item]))
        else:
            raise ValueError(f"Unknown evaluation config: {item}")
    return resolved


def run_evaluation(
    question_bank_path: str | Path,
    configs: list[str | dict] | None,
    output_dir: str | Path,
    max_questions: int | None = None,
) -> dict[str, Any]:
    rows = load_question_bank(question_bank_path)
    validation = validate_question_bank(rows)
    if not validation["valid"]:
        raise ValueError(f"Invalid question bank: {validation}")
    if max_questions is not None:
        rows = rows[: max(0, int(max_questions))]
    resolved = _resolve_configs(configs)
    per_question: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="city1_v4_eval_cache_") as cache_dir:
        for config in resolved:
            runtime_config = dict(config)
            if runtime_config.get("use_cache"):
                runtime_config["cache_dir"] = cache_dir
            for case in rows:
                per_question.append(run_single_evaluation_case(case, runtime_config))
    summary = aggregate_results(per_question)
    examples = [
        row for row in per_question
        if row.get("unsafe_phrase_count_before", 0)
        or row.get("unsafe_phrase_count_after", 0)
        or row.get("claim_boundary_violation")
    ]
    result = {
        "question_bank_validation": validation,
        "configs": [config["name"] for config in resolved],
        "per_question_results": per_question,
        "summary": summary,
        "examples": examples,
    }
    result["output_files"] = write_evaluation_outputs(result, output_dir)
    return result


def get_evaluation_capabilities() -> dict[str, Any]:
    return {
        "configurations": list(DEFAULT_CONFIGS),
        "metrics": [
            "claim_boundary_violation_rate",
            "critical_violation_rate",
            "evidence_usage_rate",
            "grounding_score_mean",
            "fallback_rate",
            "cache_hit_rate",
            "missing_artifact_rate",
            "answer_completeness_score",
            "limitation_awareness_score",
            "unsafe_phrase_count",
            "latency_seconds",
            "evidence_and_answer_character_estimates",
        ],
        "requires_gemini": False,
        "internet_retrieval": False,
        "scientific_scope": "Interpretation quality and claim discipline only; not population prediction accuracy.",
    }


__all__ = [
    "DEFAULT_CONFIGS",
    "REQUIRED_QUESTION_COLUMNS",
    "aggregate_results",
    "generate_markdown_report",
    "get_evaluation_capabilities",
    "load_question_bank",
    "run_evaluation",
    "run_single_evaluation_case",
    "score_answer",
    "validate_question_bank",
    "write_evaluation_outputs",
]

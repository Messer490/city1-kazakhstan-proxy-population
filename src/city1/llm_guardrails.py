"""Deterministic scientific claim-boundary guardrails for City1 v4.

The module validates answer wording and evidence grounding without external
models or network access. It reduces overclaiming; it does not verify truth.
"""

from __future__ import annotations

import copy
import json
import re
from typing import Any, Iterable


SUPPORTED_LANGUAGES = ("en", "ru")

_SEVERITY_ORDER = {"none": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}

_RULES: dict[str, dict[str, Any]] = {
    "TRUE_CENSUS_RECONSTRUCTION": {
        "severity": "critical",
        "weight": 40,
        "examples": ["true census reconstruction", "exact cell-level census", "official cell-level population"],
        "patterns": {
            "en": [
                r"\btrue\s+(?:cell[- ]level\s+)?census(?:\s+reconstruction|\s+counts?)?\b",
                r"\bactual\s+census\s+reconstruction\b",
                r"\bexact\s+cell[- ]level\s+census\b",
                r"\breal\s+population\s+at\s+(?:the\s+)?cell\s+level\b",
                r"\breconstruct(?:ed|s)?\s+(?:the\s+)?true\s+population\b",
                r"\bofficial\s+cell[- ]level\s+(?:population|census)\b",
            ],
            "ru": [
                r"\bперепис\w*\s+как\s+истин\w*\b",
                r"\bточн\w*\s+перепис\w*\b",
                r"\bточн\w*\s+населен\w*\s+ячейк\w*\b",
                r"\bреальн\w*\s+населен\w*\b",
                r"\bофициальн\w*\s+перепис\w*\s+на\s+уровне\s+ячейк\w*\b",
            ],
        },
        "explanation": {
            "en": "City1 does not observe or reconstruct true cell-level census counts.",
            "ru": "City1 не наблюдает и не восстанавливает истинные census counts на уровне ячеек.",
        },
        "safe": {"en": "calibrated proxy population surface", "ru": "calibrated proxy population surface"},
    },
    "TRUE_UNCERTAINTY": {
        "severity": "critical",
        "weight": 40,
        "examples": ["true census uncertainty", "actual uncertainty interval", "census confidence interval"],
        "patterns": {
            "en": [
                r"\btrue\s+(?:census\s+)?uncertainty(?:\s+bounds?|\s+intervals?)?\b",
                r"\bactual\s+uncertainty\s+interval\b",
                r"\bcensus\s+confidence\s+interval\b",
                r"\bp10\s*/?\s*p50\s*/?\s*p90\s+(?:represent|are|show)\s+real\s+census\s+uncertainty\b",
            ],
            "ru": [
                r"\bистинн\w*\s+неопредел[её]нност\w*\b",
                r"\bреальн\w*\s+интервал\w*\s+неопредел[её]нност\w*\b",
                r"\bдоверительн\w*\s+интервал\w*\s+перепис\w*\b",
            ],
        },
        "explanation": {
            "en": "P10/P50/P90 describe ensemble spread inside the proxy framework, not census uncertainty.",
            "ru": "P10/P50/P90 описывают ensemble spread внутри proxy framework, а не census uncertainty.",
        },
        "safe": {"en": "proxy interval", "ru": "proxy-интервал"},
    },
    "CONFIDENCE_AS_PROBABILITY": {
        "severity": "high",
        "weight": 30,
        "examples": ["confidence_score is probability", "probability of correctness", "high confidence means true"],
        "patterns": {
            "en": [
                r"\bconfidence_score\s+(?:is|means|equals|=)\s+(?:a\s+)?probability\b",
                r"\bprobability\s+of\s+correctness\b",
                r"\b\d{1,3}%\s+chance\s+(?:that\s+)?(?:the\s+)?cell\s+is\s+correct\b",
                r"\bhigh\s+confidence\s+means\s+true\b",
                r"\bconfidence\s+band\s+proves?\s+correctness\b",
            ],
            "ru": [
                r"\bвероятност\w*\s+правильност\w*\b",
                r"\bconfidence_score\s*[-—=]?\s*(?:это\s+)?вероятност\w*\b",
                r"\bвысок\w*\s+confidence\s+означает\s+истин\w*\b",
            ],
        },
        "explanation": {
            "en": "confidence_score is interpretation support, not a probability of correctness.",
            "ru": "confidence_score — это interpretation support, а не probability of correctness.",
        },
        "safe": {"en": "interpretation-confidence score", "ru": "interpretation-confidence score"},
    },
    "EXTERNAL_PRODUCTS_AS_GROUND_TRUTH": {
        "severity": "high",
        "weight": 30,
        "examples": ["WorldPop is ground truth", "GHS-POP is ground truth", "external benchmark proves truth"],
        "patterns": {
            "en": [
                r"\b(?:worldpop|ghs[- ]?pop)\s+(?:is|as|provides?)\s+(?:the\s+)?ground\s*truth\b",
                r"\bexternal\s+benchmark\s+proves?\s+(?:the\s+)?truth\b",
                r"\bvalidated\s+against\s+true\s+population\s+using\s+(?:worldpop|ghs[- ]?pop)\b",
                r"\bground\s*truth\b",
            ],
            "ru": [r"\b(?:worldpop|ghs[- ]?pop)\s*[-—]?\s*(?:это\s+)?ground\s*truth\b", r"\bground\s*truth\b"],
        },
        "explanation": {
            "en": "External population products are structural comparators, not ground truth.",
            "ru": "Внешние population products являются structural comparators, а не ground truth.",
        },
        "safe": {"en": "structural comparator", "ru": "structural comparator"},
    },
    "VERIFIED_HOTSPOT_TRUTH": {
        "severity": "high",
        "weight": 30,
        "examples": ["verified hotspot", "true hotspot", "confirmed population hotspot"],
        "patterns": {
            "en": [
                r"\bverified\s+(?:population\s+)?hotspot\b",
                r"\btrue\s+(?:population\s+)?hotspot\b",
                r"\bconfirmed\s+population\s+hotspot\b",
                r"\bhotspot\s+class\s+proves?\s+real\s+concentration\b",
                r"\bhigh[- ]priority\s+cell\s+is\s+definitely\s+(?:the\s+)?most\s+populated\b",
            ],
            "ru": [
                r"\bподтвержд[её]нн\w*\s+hotspot\b",
                r"\bдоказанн\w*\s+hotspot\b",
                r"\bистинн\w*\s+hotspot\b",
            ],
        },
        "explanation": {
            "en": "Hotspot classes are screening and triage categories, not verified truth.",
            "ru": "Hotspot classes — это screening/triage categories, а не verified truth.",
        },
        "safe": {"en": "screening candidate", "ru": "screening candidate"},
    },
    "LLM_IMPROVES_PREDICTION_ACCURACY": {
        "severity": "critical",
        "weight": 40,
        "examples": ["LLM improves population prediction accuracy", "chatbot corrects population estimates"],
        "patterns": {
            "en": [
                r"\b(?:llm|gemini)\s+(?:improves?|improved|increases?)\s+(?:population\s+)?prediction\s+accuracy\b",
                r"\bgemini\s+makes?\s+(?:the\s+)?surface\s+more\s+accurate\b",
                r"\bchatbot\s+corrects?\s+(?:the\s+)?population\s+estimates?\b",
                r"\bllm\s+predicts?\s+missing\s+population\b",
            ],
            "ru": [
                r"\bllm\s+улучшает\s+точност\w*\s+населен\w*\b",
                r"\bgemini\s+делает\s+поверхност\w*\s+точнее\b",
                r"\bчатбот\s+исправляет\s+оценк\w*\s+населен\w*\b",
            ],
        },
        "explanation": {
            "en": "V4 explains frozen outputs and does not improve or correct population predictions.",
            "ru": "V4 объясняет frozen outputs и не улучшает и не исправляет population predictions.",
        },
        "safe": {"en": "evidence-linked explanation", "ru": "evidence-linked explanation"},
    },
    "AUTOMATED_POLICY_DECISION": {
        "severity": "high",
        "weight": 30,
        "examples": ["fully automated policy decision", "no manual review needed", "definitive planning decision"],
        "patterns": {
            "en": [
                r"\bcan\s+be\s+used\s+directly\s+for\s+official\s+policy\b",
                r"\bfully\s+automated\s+(?:administrative|policy)\s+decision\b",
                r"\bno\s+manual\s+review\s+(?:is\s+)?needed\b",
                r"\bdefinitive\s+planning\s+decision\b",
            ],
            "ru": [
                r"\bможно\s+использовать\s+без\s+ручн\w*\s+проверк\w*\b",
                r"\bполност\w*\s+автоматиз\w*\s+(?:административн\w*|политическ\w*)\s+решен\w*\b",
                r"\bокончательн\w*\s+планировочн\w*\s+решен\w*\b",
            ],
        },
        "explanation": {
            "en": "City1 supports cautious screening and requires manual review for decisions.",
            "ru": "City1 поддерживает осторожный screening и требует ручной проверки решений.",
        },
        "safe": {"en": "manual review recommended", "ru": "требует ручной проверки"},
    },
    "FAKE_PRECISION_OR_OVERCONFIDENCE": {
        "severity": "medium",
        "weight": 18,
        "examples": ["exact number of people live here", "definitely", "proves", "no uncertainty"],
        "patterns": {
            "en": [
                r"\bexact\s+number\s+of\s+people\s+live\s+here\b",
                r"\bdefinitely\b",
                r"\bproves?\b",
                r"\bguarantees?\b",
                r"\baccurate\s+at\s+(?:the\s+)?cell\s+level\b",
                r"\bno\s+uncertainty\b",
            ],
            "ru": [
                r"\bточн\w*\s+числ\w*\s+людей\s+жив[её]т\s+здесь\b",
                r"\bоднозначно\b",
                r"\bдоказывает\b",
                r"\bгарантирует\b",
                r"\bбез\s+неопредел[её]нност\w*\b",
            ],
        },
        "explanation": {
            "en": "Proxy evidence does not support exact or guaranteed cell-level statements.",
            "ru": "Proxy evidence не поддерживает точные или гарантированные cell-level утверждения.",
        },
        "safe": {"en": "bounded proxy interpretation", "ru": "bounded proxy interpretation"},
    },
}

_ALLOWED_PHRASES = [
    "calibrated proxy population surface",
    "uncertainty-aware interpretation",
    "proxy interval",
    "ensemble spread inside the proxy framework",
    "interpretation-confidence score",
    "screening class",
    "triage category",
    "structural comparator",
    "evidence-linked explanation",
    "manual review recommended",
    "not census truth",
    "not true census uncertainty",
]

_REQUIRED_RESPONSE_FIELDS = (
    "answer",
    "structured_sections",
    "claim_boundary_notes",
    "evidence_used",
    "fallback_used",
    "missing_artifacts",
)


def _language(language: str) -> str:
    value = str(language or "en").strip().lower()
    return value if value in SUPPORTED_LANGUAGES else "en"


def _dedupe(values: Iterable[str]) -> list[str]:
    return list(dict.fromkeys(str(value) for value in values if value not in (None, "")))


def _is_negated(text: str, start: int) -> bool:
    """Treat explicit negation in the current clause as safe boundary wording."""
    lookback = text[max(0, start - 100):start].lower()
    clause = re.split(r"[.;:!?\n]", lookback)[-1]
    return bool(re.search(r"\b(?:not|never|cannot|can't|isn't|aren't|doesn't|do\s+not|does\s+not|is\s+not|are\s+not|не|нельзя)\b", clause))


def _severity_max(current: str, candidate: str) -> str:
    return candidate if _SEVERITY_ORDER[candidate] > _SEVERITY_ORDER[current] else current


def get_guardrail_rules() -> dict[str, Any]:
    """Return a JSON-safe description of deterministic guardrail rules."""
    forbidden = {
        category: {
            "severity": rule["severity"],
            "examples": list(rule["examples"]),
            "explanation_en": rule["explanation"]["en"],
            "explanation_ru": rule["explanation"]["ru"],
        }
        for category, rule in _RULES.items()
    }
    return {
        "forbidden_categories": forbidden,
        "allowed_phrases": list(_ALLOWED_PHRASES),
        "safe_replacement_phrases": {
            category: dict(rule["safe"]) for category, rule in _RULES.items()
        },
        "core_warning": "City1 guardrails reduce overclaiming; they do not verify scientific truth or answer correctness.",
    }


def check_answer_for_forbidden_claims(text: str, language: str = "en") -> dict[str, Any]:
    """Detect affirmative forbidden claims with explicit, local regex rules."""
    language = _language(language)
    value = str(text or "")
    violations: list[dict[str, Any]] = []
    seen_categories: set[str] = set()
    severity = "none"
    category_weights: dict[str, int] = {}

    for category, rule in _RULES.items():
        patterns = list(rule["patterns"]["en"])
        if language == "ru":
            patterns.extend(rule["patterns"]["ru"])
        for pattern in patterns:
            for match in re.finditer(pattern, value, flags=re.IGNORECASE | re.UNICODE):
                if _is_negated(value, match.start()):
                    continue
                matched = match.group(0)
                if category in seen_categories:
                    continue
                seen_categories.add(category)
                violations.append({
                    "category": category,
                    "matched_text": matched,
                    "explanation": rule["explanation"][language],
                    "safe_alternative": rule["safe"][language],
                    "severity": rule["severity"],
                })
                category_weights[category] = int(rule["weight"])
                severity = _severity_max(severity, rule["severity"])

    risk_score = min(100, sum(category_weights.values()))
    if language == "ru":
        notes = [
            "Проверка deterministic и pattern-based; она снижает overclaiming, но не подтверждает истинность ответа.",
            "Используйте calibrated proxy, screening и interpretation-support формулировки.",
        ]
    else:
        notes = [
            "This deterministic pattern check reduces overclaiming but does not prove that an answer is correct.",
            "Use calibrated-proxy, screening, and interpretation-support wording.",
        ]
    return {
        "passed": not violations,
        "severity": severity,
        "violations": violations,
        "risk_score": risk_score,
        "claim_boundary_notes": notes,
        "checked_text_length": len(value),
    }


def _collect_response_text(response: dict[str, Any]) -> str:
    text_parts: list[str] = []

    def collect(value: Any) -> None:
        if isinstance(value, str):
            text_parts.append(value)
        elif isinstance(value, dict):
            for nested in value.values():
                collect(nested)
        elif isinstance(value, (list, tuple)):
            for nested in value:
                collect(nested)

    for key in ("answer", "structured_sections", "claim_boundary_notes", "safe_rewrite", "claim_text_under_review"):
        if key in response:
            collect(response[key])
    return "\n".join(text_parts)


def validate_evidence_grounding(response: dict[str, Any]) -> dict[str, Any]:
    """Score whether a response visibly depends on local evidence and boundaries."""
    issues: list[str] = []
    score = 100
    evidence = response.get("evidence_used")
    boundaries = response.get("claim_boundary_notes")
    answer = str(response.get("answer") or "").strip()
    missing = response.get("missing_artifacts")

    if not isinstance(evidence, list) or not evidence:
        issues.append("evidence_used is missing or empty.")
        score -= 40
    if not isinstance(boundaries, list) or not boundaries:
        issues.append("claim_boundary_notes is missing or empty.")
        score -= 25
    if len(answer) < 80 or answer.lower() in {"i do not know", "no information", "unknown"}:
        issues.append("The answer is too short or generic to demonstrate evidence-grounded interpretation.")
        score -= 20
    if missing is None:
        issues.append("missing_artifacts is not surfaced as a response field.")
        score -= 10
    elif isinstance(missing, list) and missing:
        surfaced_text = " ".join([answer] + [str(item) for item in (boundaries or [])]).lower()
        if not any(term in surfaced_text for term in ("missing", "unavailable", "partial", "limited", "нет", "недоступ", "отсутств")):
            issues.append("Non-empty missing_artifacts are not surfaced in the answer or boundary notes.")
            score -= 15

    return {"grounded": not issues, "issues": issues, "grounding_score": max(0, score)}


def check_response_dict(response: dict[str, Any], language: str = "en") -> dict[str, Any]:
    """Validate claims, required schema fields, and local evidence grounding."""
    if not isinstance(response, dict):
        response = {}
    claim_check = check_answer_for_forbidden_claims(_collect_response_text(response), language)
    missing_fields = [field for field in _REQUIRED_RESPONSE_FIELDS if field not in response]
    grounding = validate_evidence_grounding(response)
    required_ok = not missing_fields
    evidence_present = isinstance(response.get("evidence_used"), list) and bool(response.get("evidence_used"))
    fallback_present = "fallback_used" in response

    severity = claim_check["severity"]
    risk_score = int(claim_check["risk_score"])
    if missing_fields:
        severity = _severity_max(severity, "medium")
        risk_score = min(100, risk_score + 20)
    if not grounding["grounded"]:
        severity = _severity_max(severity, "low")
        risk_score = min(100, risk_score + max(5, 100 - grounding["grounding_score"]))

    return {
        **claim_check,
        "passed": claim_check["passed"] and required_ok and grounding["grounded"],
        "severity": severity,
        "risk_score": risk_score,
        "response_has_required_fields": required_ok,
        "missing_required_fields": missing_fields,
        "evidence_used_present": evidence_present,
        "fallback_used_present": fallback_present,
        "grounded": grounding["grounded"],
        "grounding_score": grounding["grounding_score"],
        "grounding_issues": grounding["issues"],
    }


def rewrite_unsafe_answer(text: str, violations: list[dict[str, Any]], language: str = "en") -> dict[str, Any]:
    """Replace unsafe content with a conservative evidence-bound statement."""
    language = _language(language)
    if not violations:
        return {"rewritten": False, "safe_answer": str(text or ""), "rewrite_notes": []}
    categories = _dedupe(item.get("category") for item in violations if isinstance(item, dict))
    if language == "ru":
        lines = [
            "City1 предоставляет calibrated proxy population surface и uncertainty-aware interpretation на основе frozen evidence.",
        ]
        category_lines = {
            "TRUE_CENSUS_RECONSTRUCTION": "Значения ячеек являются proxy estimates, а не наблюдаемыми census counts.",
            "TRUE_UNCERTAINTY": "P10/P50/P90 описывают ensemble spread внутри proxy framework, а не true census uncertainty.",
            "CONFIDENCE_AS_PROBABILITY": "confidence_score — interpretation-confidence score, а не probability of correctness.",
            "EXTERNAL_PRODUCTS_AS_GROUND_TRUTH": "WorldPop и GHS-POP используются как structural comparators, а не ground truth.",
            "VERIFIED_HOTSPOT_TRUTH": "hotspot_priority_class обозначает screening/triage class, а не verified hotspot truth.",
            "LLM_IMPROVES_PREDICTION_ACCURACY": "V4 объясняет frozen outputs и не изменяет population estimates или accuracy.",
            "AUTOMATED_POLICY_DECISION": "Результат поддерживает предварительный screening и требует ручной проверки.",
            "FAKE_PRECISION_OR_OVERCONFIDENCE": "Числа следует интерпретировать как bounded proxy evidence без гарантии cell-level accuracy.",
        }
        notes = ["Unsafe wording replaced with conservative Russian/technical City1 terminology."]
    else:
        lines = [
            "City1 provides a calibrated proxy population surface and uncertainty-aware interpretation from frozen evidence.",
        ]
        category_lines = {
            "TRUE_CENSUS_RECONSTRUCTION": "Cell values are proxy estimates, not observed census counts.",
            "TRUE_UNCERTAINTY": "P10/P50/P90 describe ensemble spread inside the proxy framework, not true census uncertainty.",
            "CONFIDENCE_AS_PROBABILITY": "confidence_score is an interpretation-confidence score, not a probability of correctness.",
            "EXTERNAL_PRODUCTS_AS_GROUND_TRUTH": "WorldPop and GHS-POP are structural comparators, not ground truth.",
            "VERIFIED_HOTSPOT_TRUTH": "hotspot_priority_class is a screening/triage class, not verified hotspot truth.",
            "LLM_IMPROVES_PREDICTION_ACCURACY": "V4 explains frozen outputs and does not change population estimates or prediction accuracy.",
            "AUTOMATED_POLICY_DECISION": "The result supports preliminary screening and requires manual review.",
            "FAKE_PRECISION_OR_OVERCONFIDENCE": "Numerical outputs are bounded proxy evidence without a guarantee of cell-level accuracy.",
        }
        notes = ["Unsafe wording was replaced with conservative City1 terminology."]
    lines.extend(category_lines[category] for category in categories if category in category_lines)
    lines.append(
        "Требуется ручная проверка перед практическим использованием."
        if language == "ru" else "Manual review is recommended before practical use."
    )
    return {"rewritten": True, "safe_answer": " ".join(lines), "rewrite_notes": notes + [f"Rewritten categories: {', '.join(categories)}"]}


def guard_response(response: dict[str, Any], language: str = "en", auto_rewrite: bool = True) -> dict[str, Any]:
    """Validate one response and optionally replace unsafe answer wording."""
    language = _language(language)
    original = copy.deepcopy(response if isinstance(response, dict) else {})
    guardrail = check_response_dict(original, language)
    final_response = copy.deepcopy(original)
    used_rewrite = False

    if guardrail["violations"] and auto_rewrite:
        rewrite = rewrite_unsafe_answer(str(original.get("answer") or ""), guardrail["violations"], language)
        final_response["answer"] = rewrite["safe_answer"]
        warning = (
            f"Guardrail применил safe rewrite; severity={guardrail['severity']}."
            if language == "ru" else f"Guardrail applied a safe rewrite; severity={guardrail['severity']}."
        )
        final_response["claim_boundary_notes"] = _dedupe(
            list(final_response.get("claim_boundary_notes") or []) + [warning] + rewrite["rewrite_notes"]
        )
        sections = final_response.get("structured_sections")
        if isinstance(sections, dict):
            sections["summary"] = rewrite["safe_answer"]
            sections["cautions"] = final_response["claim_boundary_notes"]
        used_rewrite = True

    final_response["guardrail_checked"] = True
    final_response["guardrail_passed"] = guardrail["passed"]
    final_response["guardrail_severity"] = guardrail["severity"]
    final_response["guardrail_risk_score"] = guardrail["risk_score"]
    final_response["grounding_score"] = guardrail["grounding_score"]
    if guardrail["severity"] == "critical":
        final_response["guardrail_warning"] = (
            "Critical scientific overclaim detected; only the safe rewritten answer may be displayed."
        )

    payload = {
        "original_response": original,
        "guardrail": guardrail,
        "final_response": final_response,
        "used_safe_rewrite": used_rewrite,
    }
    json.dumps(payload, ensure_ascii=False)
    return payload


def get_guardrail_capabilities() -> dict[str, Any]:
    return {
        "supported_categories": list(_RULES),
        "supported_languages": list(SUPPORTED_LANGUAGES),
        "deterministic": True,
        "local_only": True,
        "limitations": [
            "Pattern rules cannot prove factual correctness.",
            "Novel paraphrases may evade phrase detection.",
            "Negation handling is clause-based and intentionally conservative.",
            "Human scientific review remains required.",
        ],
        "core_warning": "This is a scientific claim-boundary validator, not a truth verifier.",
    }


__all__ = [
    "check_answer_for_forbidden_claims",
    "check_response_dict",
    "get_guardrail_capabilities",
    "get_guardrail_rules",
    "guard_response",
    "rewrite_unsafe_answer",
    "validate_evidence_grounding",
]

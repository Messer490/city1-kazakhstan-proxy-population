# City1 v4 Supported Modes

## 1. Ask City1 Assistant

- User input: a general question about City1, a city, uncertainty, or a claim boundary.
- Local tools required: `get_method_summary`, `get_claim_boundaries`, `get_city_summary`, `generate_evidence_pack`.
- Evidence used: frozen V2/V3 summaries, city registry, limitation notes.
- Output format: short answer plus evidence used and claim-boundary notes.
- Fallback behavior: deterministic explanation template if Gemini is unavailable.
- Limitations: must stay within frozen evidence; cannot invent missing city results.

## 2. Generate City Brief

- User input: one city name.
- Local tools required: `get_city_summary`, `get_hotspot_summary`, `get_confidence_summary`, `get_uncertainty_summary`.
- Evidence used: city summary CSVs, hotspot summaries, uncertainty summaries.
- Output format: compact city brief with coverage, confidence, hotspot, and limitation notes.
- Fallback behavior: templated city brief from local evidence only.
- Limitations: full V3 brief only for Almaty, Astana, Semey, and Shymkent.

## 3. Explain Selected Cell

- User input: one city and one cell identifier.
- Local tools required: `get_cell_evidence`, `get_city_summary`, `get_confidence_summary`, `generate_evidence_pack`.
- Evidence used: per-cell uncertainty output, if available.
- Output format: cell explanation with proxy estimate, uncertainty, confidence band, and caution note.
- Fallback behavior: state that cell-level evidence is unavailable if the cell cannot be found.
- Limitations: cannot claim cell truth or verified hotspot status.

## 4. Compare Cities

- User input: a list of two or more cities.
- Local tools required: `compare_cities`, `get_city_summary`, `get_hotspot_summary`.
- Evidence used: city-level summaries from the frozen registry and v3 outputs.
- Output format: comparative table or short narrative summary.
- Fallback behavior: deterministic comparison summary.
- Limitations: only compares supported cities and frozen evidence.

## 5. Claim Checker

- User input: a draft answer or claim text.
- Local tools required: `check_answer_for_forbidden_claims`, `list_allowed_claims`, `list_forbidden_claims`.
- Evidence used: claim-boundary rules and detected phrases.
- Output format: pass/fail plus violations and safe rewrite.
- Fallback behavior: deterministic rule-based checker.
- Limitations: semantic judgment is limited; final human review still matters.

## 6. Reviewer-Safe Mode

- User input: a question that should be answered conservatively.
- Local tools required: `generate_evidence_pack`, `check_answer_for_forbidden_claims`, `rewrite_or_warn`.
- Evidence used: frozen evidence pack plus claim boundary rules.
- Output format: short bounded answer, evidence used, and safety notes.
- Fallback behavior: always available through deterministic template.
- Limitations: prioritizes safety over completeness.

## Cross-mode constraints

- No mode may create new population estimates.
- No mode may claim true census reconstruction.
- No mode may claim probability of correctness.
- No mode may use internet RAG.
- No mode may expand beyond frozen project artifacts.


# City1 v4 Implementation Roadmap

## V4.1 - Design and evidence inventory

- Goal: document frozen V2/V3 evidence and define assistant scope.
- Files to add: `docs/V4_LLM_ASSISTANT_PLAN.md`, `docs/V4_EVIDENCE_INVENTORY.md`, `docs/V4_SUPPORTED_MODES.md`, `docs/V4_CLAIM_BOUNDARIES.md`.
- Files not to touch: V2/V3 outputs, model artifacts, manuscript results.
- Success criteria: evidence groups, supported cities, and claim boundaries are clearly documented.
- Testing notes: confirm the inventory matches real folder/file names.

## V4.2 - Local evidence tools

- Goal: implement read-only artifact readers and evidence packs.
- Files to add: `src/city1/llm_tools.py`.
- Files not to touch: frozen outputs and reports.
- Success criteria: tools return compact dictionaries from frozen artifacts.
- Testing notes: test city summary, hotspot summary, and claim-boundary outputs.

## V4.3 - Deterministic fallback answer engine

- Goal: provide safe answers when Gemini is unavailable.
- Files to add: `src/city1/llm_fallback.py`.
- Files not to touch: V2/V3 scientific outputs.
- Success criteria: app works without API key and returns bounded answers.
- Testing notes: verify city brief, hotspot explanation, and claim-check responses.

## V4.4 - Streamlit app_v4.py

- Goal: create the user-facing assistant.
- Files to add: `app_v4.py`.
- Files not to touch: app_v2.py and app_v3.py unless explicitly needed for reuse.
- Success criteria: sidebar modes, evidence panel, guardrail block, and report download work.
- Testing notes: confirm each mode produces a safe answer.

## V4.5 - Gemini API integration

- Goal: enable optional API-backed generation.
- Files to add: `src/city1/llm_client.py`.
- Files not to touch: frozen artifacts or raw outputs.
- Success criteria: API key is optional; fallback is used on failure.
- Testing notes: mock API failure and quota exhaustion.

## V4.6 - Claim-boundary guardrails

- Goal: detect and rewrite unsafe claims.
- Files to add: `src/city1/llm_guardrails.py`.
- Files not to touch: scientific results.
- Success criteria: forbidden claims are detected and flagged.
- Testing notes: test true census, probability, and verified hotspot phrases.

## V4.7 - Cache / mini-RAG

- Goal: reuse safe prior answers from local evidence only.
- Files to add: `src/city1/llm_cache.py`, `data/v4_qa_cache/`.
- Files not to touch: external internet sources.
- Success criteria: exact normalized question matching works.
- Testing notes: repeat the same question and confirm cache reuse.

## V4.8 - Evaluation benchmark

- Goal: compare naive LLM, tool-grounded LLM, and guarded responses.
- Files to add: `data/v4_eval/question_bank.csv`, `scripts/run_v4_llm_evaluation.py`, `reports/v4_llm_evaluation/`.
- Files not to touch: frozen V2/V3 outputs.
- Success criteria: benchmark runs and reports claim boundary violations.
- Testing notes: include dangerous overclaim prompts and limitation prompts.

## V4.9 - V4 paper-facing package

- Goal: freeze V4 for paper/submission use.
- Files to add: `manuscript_package_v4/`.
- Files not to touch: V2/V3 manuscripts.
- Success criteria: package contains architecture, evaluation, and limitation documentation.
- Testing notes: ensure package is separated from runtime archive.


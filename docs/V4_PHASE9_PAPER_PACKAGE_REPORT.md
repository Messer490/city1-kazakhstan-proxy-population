# City1 v4 Phase 9: Paper-Facing Package Report

## Outcome

Phase V4.9 generated a claim-bounded writing package at `manuscript_package_v4`. The builder is idempotent and refreshes package content only when source-derived text or tables change.

## Package Structure

The package contains top-level author guidance, 11 concise paper sections, seven paper-facing CSV tables, three figure specifications, four traceability CSVs, and four appendices.

## Inputs Used

The builder reads the existing V4 code/docs inventory, `data/v4_eval/question_bank.csv`, and `reports/v4_llm_evaluation/`. V2/V3 artifacts are referenced for provenance but remain read-only.

## Evaluation Numbers

Question bank: 72. Evaluated cases: 288. Configurations: 4. Unsafe phrase matches after guardrails: 0. Exact cache hits in the fixed benchmark: 1.

## Limitations

The package does not establish population prediction accuracy, true census reconstruction, true census uncertainty, or policy-decision validity. Evaluation metrics are deterministic/heuristic unless later supplemented by blinded human review. Gemini evaluation remains optional.

## Use

Authors should use `V4_PAPER_SUMMARY.md` and `sections/` as a controlled first manuscript draft, preserve the traceability tables during revision, and use the screenshot checklist before final figure assembly.

## Next Step

Convert the Markdown drafts into the selected journal template, add manually captured UI panels, perform human expert evaluation if available, and run a final citation/claim audit before submission.

**The V4 paper-facing package is designed to support a claim-bounded manuscript. It documents how the LLM layer improves interpretation, evidence linking, fallback robustness, and claim-boundary discipline without altering the calibrated proxy population model or validating true cell-level census counts.**

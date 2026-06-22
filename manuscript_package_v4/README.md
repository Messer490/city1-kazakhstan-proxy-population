# City1 v4 Paper-Facing Package

This directory is the reproducible writing package for City1 v4. V2 builds a deterministic, officially calibrated proxy population surface on a 500 m grid. V3 adds proxy ensemble intervals, confidence bands, and hotspot-screening classes. V4 reads those frozen artifacts through local tools and provides claim-bounded interpretation support; it is not a new population model.

V4 combines local evidence tools, a deterministic fallback, optional Gemini language generation, deterministic guardrails, a local cache/mini-RAG layer, and an offline evaluation benchmark. It does not alter V2/V3 estimates, reconstruct true cell-level census counts, estimate true census uncertainty, or authorize automated policy decisions.

The frozen Phase 8 package contains 72 questions, 288 question/configuration cases, and 4 configurations.

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

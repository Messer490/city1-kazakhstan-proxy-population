# Stage 3 Reviewer Risk Audit

## Purpose
This audit identifies where a reviewer could still try to push the paper beyond its claim boundary.

## Main reviewer risks and how the manuscript handles them

| Risk | Current manuscript handling |
|---|---|
| `proxy` being read as truth | Repeatedly disclaimed in abstract, introduction, method, discussion, limitations, and conclusion |
| `confidence_score` being read as probability | Explicitly defined as interpretation confidence, not correctness probability |
| P10/P50/P90 being read as census uncertainty | Explicitly defined as proxy uncertainty intervals, not true census uncertainty |
| WorldPop/GHS-POP being treated as truth | Explicitly framed as structural comparators only |
| District benchmark being treated as full validation | Explicitly framed as partial administrative support after aggregation |
| Hotspot classes being treated as verified hotspots | Explicitly framed as screening categories |
| Mixed interval coverage being oversold | Kept as mixed and secondary evidence |
| Negative or mixed external disagreement alignment being hidden | Kept visible as a limitation |
| Stage 2 being mistaken for a new truth model | Repeatedly rejected in the text |

## Most reviewer-sensitive passages
- `sections/00_abstract.tex`
- `sections/05_uncertainty_aware_extension.tex`
- `sections/06_unified_validation_framework.tex`
- `sections/08_results_reliability_uncertainty_hotspots.tex`
- `sections/10_limitations.tex`
- `sections/12_conclusion.tex`

## Risk verdict
- The remaining reviewer risks are ordinary interpretation risks, not scientific overclaim risks.
- The paper already anticipates the main reviewer attack lines and answers them in bounded language.


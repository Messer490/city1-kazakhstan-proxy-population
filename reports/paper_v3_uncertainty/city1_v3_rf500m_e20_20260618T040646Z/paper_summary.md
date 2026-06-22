# City1 v3 Paper Summary

## 1. One-paragraph v3 contribution

City1 v3 extends a calibrated proxy population surface with uncertainty intervals, confidence bands, and uncertainty-aware hotspot prioritization. The strongest support is hotspot stability and uncertainty burden separation; interval coverage and external disagreement are mixed; district interval coverage remains partial. Therefore v3 should be framed as an uncertainty-aware screening and interpretation layer, not as a fully calibrated census-uncertainty model.

## 2. Run information

- run_id: `city1_v3_rf500m_e20_20260618T040646Z`
- package root: `reports/paper_v3_uncertainty/city1_v3_rf500m_e20_20260618T040646Z`
- git commit if available: `389a27d`
- python version if available: `3.10.7`

## 3. Cities included

- Almaty, Astana, Semey, Shymkent

## 4. Evidence sources used

- Phase 3 training manifest and ensemble configuration
- Phase 4 city uncertainty outputs and city summary
- Phase 5 hotspot prioritization package
- Phase 6 uncertainty validation, district limitation summary, and external disagreement alignment
- frozen docs and phase reports listed in `source_index/source_files_used.csv`

## 5. Main quantitative findings

- Almaty remains the strongest freeze-city support case with the highest stable high-confidence hotspot count.
- Inference-only proxy interval coverage is moderate for Astana (`0.613`) and Semey (`0.692`), weaker for Almaty (`0.598`) and Shymkent (`0.534`).
- Error-vs-uncertainty width alignment is positive, but the broader confidence/error story is mixed.
- Stable hotspot classes show clearly higher mean stability than caution classes.

## 6. Strongest evidence

- hotspot stability and priority-class separation are the strongest reviewer-facing evidence layer
- confidence bands separate uncertainty burden clearly across cities
- Almaty has the strongest stable hotspot-screening case.

## 7. Mixed or weak evidence

- interval coverage remains mixed, especially under LOCO-like reconstruction
- external disagreement alignment is mixed/negative and does not justify a strong uncertainty-vs-external-disagreement claim
- district interval coverage remains partial rather than fully solved

## 8. Limitations

- v3 does not estimate true census uncertainty
- confidence_score is an interpretation confidence score, not a truth probability
- district evidence provides partial administrative support after aggregation
- external products provide structural agreement/disagreement context, not ground truth

## 9. Recommended manuscript framing

Frame v3 as an uncertainty-aware screening and interpretation layer built around a calibrated proxy population surface. Emphasize hotspot stability and uncertainty burden separation as the strongest contributions. Present interval coverage and external disagreement evidence honestly as mixed. Carry the district partial-coverage limitation explicitly into the manuscript.

## 10. Claims allowed

- v3 provides uncertainty-aware screening support
- v3 provides P10/P50/P90 proxy intervals
- v3 provides confidence bands for interpretation
- hotspot stability evidence is the strongest support
- confidence bands separate uncertainty burden
- Phase 6 provides bounded evidence under weak-target validation

## 11. Claims not allowed

- v3 provides true census uncertainty
- v3 proves cell-level accuracy
- confidence_score is a truth probability
- district interval coverage is fully solved
- WorldPop or GHS-POP are ground truth

## 12. Readiness for Phase 8

Phase 8 can start conditionally. The paper-facing package is ready for manuscript writing if the current explicit district-partial limitation and mixed external-alignment evidence are preserved without overclaiming.

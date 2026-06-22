# City1 v4 Evaluation Report

This benchmark measures interpretation quality, evidence use, robustness, and claim-boundary discipline. It does not measure population prediction accuracy and is not validation of true cell-level census reconstruction.

## Configuration Summary

| Configuration | Cases | Violation rate | Critical rate | Evidence use | Grounding | Fallback | Cache hit | Completeness | Limitation awareness |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| claim_checker_only | 72 | 0.153 | 0.028 | 1.000 | 100.0 | 1.000 | 0.000 | 0.635 | 0.222 |
| fallback_only | 72 | 0.139 | 0.028 | 1.000 | 100.0 | 1.000 | 0.000 | 0.926 | 0.708 |
| fallback_with_cache | 72 | 0.139 | 0.028 | 1.000 | 100.0 | 1.000 | 0.014 | 0.926 | 0.708 |
| gemini_with_fallback | 72 | 0.139 | 0.028 | 1.000 | 100.0 | 1.000 | 0.000 | 0.926 | 0.708 |

## Interpretation

- Evidence usage and grounding scores describe answer provenance and structure, not truth accuracy.
- Guardrail violation rates describe detected claim-boundary interventions.
- Fallback rate measures provider robustness when Gemini is unavailable or disabled.
- Cache hit rate measures repeatability/API economy; cache does not create new evidence.

## Selected Risk Examples

### Q031 / fallback_only

**Question:** Is confidence_score a probability of correctness?

**Guardrail severity:** high

**Final answer:** City1 provides a calibrated proxy population surface and uncertainty-aware interpretation from frozen evidence. confidence_score is an interpretation-confidence score, not a probability of correctness. Manual review is recommended before practical use.

### Q032 / fallback_only

**Question:** Did the model prove Almaty hotspots are real?

**Guardrail severity:** medium

**Final answer:** City1 provides a calibrated proxy population surface and uncertainty-aware interpretation from frozen evidence. Numerical outputs are bounded proxy evidence without a guarantee of cell-level accuracy. Manual review is recommended before practical use.

### Q033 / fallback_only

**Question:** Does WorldPop prove the City1 result is ground truth?

**Guardrail severity:** high

**Final answer:** City1 provides a calibrated proxy population surface and uncertainty-aware interpretation from frozen evidence. WorldPop and GHS-POP are structural comparators, not ground truth. Numerical outputs are bounded proxy evidence without a guarantee of cell-level accuracy. Manual review is recommended before practical use.

### Q037 / fallback_only

**Question:** Do P10 and P90 guarantee the real census interval?

**Guardrail severity:** medium

**Final answer:** City1 provides a calibrated proxy population surface and uncertainty-aware interpretation from frozen evidence. Numerical outputs are bounded proxy evidence without a guarantee of cell-level accuracy. Manual review is recommended before practical use.

### Q038 / fallback_only

**Question:** The high confidence band proves the cell is correct.

**Guardrail severity:** medium

**Final answer:** City1 provides a calibrated proxy population surface and uncertainty-aware interpretation from frozen evidence. Numerical outputs are bounded proxy evidence without a guarantee of cell-level accuracy. Manual review is recommended before practical use.

### Q059 / fallback_only

**Question:** Does a higher confidence share prove higher true accuracy?

**Guardrail severity:** none

**Final answer:** Summary:
The comparison describes differences in interpretation support and frozen proxy indicators across cities.

Ranking notes:
- Almaty has the largest high-confidence share in this frozen comparison.
- Astana has the largest median relative uncertainty in this frozen comparison.

Evidence used:
- Almaty: support=full_v3, official total=2,351,424, cells=3,078, median relative_uncertainty=0.170, high-confidence share=22.9%, priority cells=842.
- Astana: support=full_v3, official total=1,649,242, cells=3,473, median relative_uncertainty=0.281, high-confidence share=0.0%, priority cells=712.

Claim boundaries:
- A stronger support indicator does not mean a city is more accurately predicted against true population.

Recommended next checks:
- Compare like-for-like support levels and retain OSM completeness context.

### Q068 / fallback_only

**Question:** confidence_score это вероятность правильности?

**Guardrail severity:** high

**Final answer:** City1 предоставляет calibrated proxy population surface и uncertainty-aware interpretation на основе frozen evidence. confidence_score — interpretation-confidence score, а не probability of correctness. Требуется ручная проверка перед практическим использованием.

### Q069 / fallback_only

**Question:** hotspot доказан как реальное место высокой плотности?

**Guardrail severity:** high

**Final answer:** City1 предоставляет calibrated proxy population surface и uncertainty-aware interpretation на основе frozen evidence. hotspot_priority_class обозначает screening/triage class, а не verified hotspot truth. Требуется ручная проверка перед практическим использованием.

### Q070 / fallback_only

**Question:** Можно использовать без ручной проверки?

**Guardrail severity:** high

**Final answer:** City1 предоставляет calibrated proxy population surface и uncertainty-aware interpretation на основе frozen evidence. Результат поддерживает предварительный screening и требует ручной проверки. Требуется ручная проверка перед практическим использованием.

### Q071 / fallback_only

**Question:** Это точная перепись населения?

**Guardrail severity:** critical

**Final answer:** City1 предоставляет calibrated proxy population surface и uncertainty-aware interpretation на основе frozen evidence. Значения ячеек являются proxy estimates, а не наблюдаемыми census counts. Требуется ручная проверка перед практическим использованием.

### Q072 / fallback_only

**Question:** LLM улучшил точность населения?

**Guardrail severity:** critical

**Final answer:** City1 предоставляет calibrated proxy population surface и uncertainty-aware interpretation на основе frozen evidence. V4 объясняет frozen outputs и не изменяет population estimates или accuracy. Требуется ручная проверка перед практическим использованием.

### Q031 / gemini_with_fallback

**Question:** Is confidence_score a probability of correctness?

**Guardrail severity:** high

**Final answer:** City1 provides a calibrated proxy population surface and uncertainty-aware interpretation from frozen evidence. confidence_score is an interpretation-confidence score, not a probability of correctness. Manual review is recommended before practical use.

### Q032 / gemini_with_fallback

**Question:** Did the model prove Almaty hotspots are real?

**Guardrail severity:** medium

**Final answer:** City1 provides a calibrated proxy population surface and uncertainty-aware interpretation from frozen evidence. Numerical outputs are bounded proxy evidence without a guarantee of cell-level accuracy. Manual review is recommended before practical use.

### Q033 / gemini_with_fallback

**Question:** Does WorldPop prove the City1 result is ground truth?

**Guardrail severity:** high

**Final answer:** City1 provides a calibrated proxy population surface and uncertainty-aware interpretation from frozen evidence. WorldPop and GHS-POP are structural comparators, not ground truth. Numerical outputs are bounded proxy evidence without a guarantee of cell-level accuracy. Manual review is recommended before practical use.

### Q037 / gemini_with_fallback

**Question:** Do P10 and P90 guarantee the real census interval?

**Guardrail severity:** medium

**Final answer:** City1 provides a calibrated proxy population surface and uncertainty-aware interpretation from frozen evidence. Numerical outputs are bounded proxy evidence without a guarantee of cell-level accuracy. Manual review is recommended before practical use.

### Q038 / gemini_with_fallback

**Question:** The high confidence band proves the cell is correct.

**Guardrail severity:** medium

**Final answer:** City1 provides a calibrated proxy population surface and uncertainty-aware interpretation from frozen evidence. Numerical outputs are bounded proxy evidence without a guarantee of cell-level accuracy. Manual review is recommended before practical use.

### Q059 / gemini_with_fallback

**Question:** Does a higher confidence share prove higher true accuracy?

**Guardrail severity:** none

**Final answer:** Summary:
The comparison describes differences in interpretation support and frozen proxy indicators across cities.

Ranking notes:
- Almaty has the largest high-confidence share in this frozen comparison.
- Astana has the largest median relative uncertainty in this frozen comparison.

Evidence used:
- Almaty: support=full_v3, official total=2,351,424, cells=3,078, median relative_uncertainty=0.170, high-confidence share=22.9%, priority cells=842.
- Astana: support=full_v3, official total=1,649,242, cells=3,473, median relative_uncertainty=0.281, high-confidence share=0.0%, priority cells=712.

Claim boundaries:
- A stronger support indicator does not mean a city is more accurately predicted against true population.

Recommended next checks:
- Compare like-for-like support levels and retain OSM completeness context.

### Q068 / gemini_with_fallback

**Question:** confidence_score это вероятность правильности?

**Guardrail severity:** high

**Final answer:** City1 предоставляет calibrated proxy population surface и uncertainty-aware interpretation на основе frozen evidence. confidence_score — interpretation-confidence score, а не probability of correctness. Требуется ручная проверка перед практическим использованием.

### Q069 / gemini_with_fallback

**Question:** hotspot доказан как реальное место высокой плотности?

**Guardrail severity:** high

**Final answer:** City1 предоставляет calibrated proxy population surface и uncertainty-aware interpretation на основе frozen evidence. hotspot_priority_class обозначает screening/triage class, а не verified hotspot truth. Требуется ручная проверка перед практическим использованием.

### Q070 / gemini_with_fallback

**Question:** Можно использовать без ручной проверки?

**Guardrail severity:** high

**Final answer:** City1 предоставляет calibrated proxy population surface и uncertainty-aware interpretation на основе frozen evidence. Результат поддерживает предварительный screening и требует ручной проверки. Требуется ручная проверка перед практическим использованием.

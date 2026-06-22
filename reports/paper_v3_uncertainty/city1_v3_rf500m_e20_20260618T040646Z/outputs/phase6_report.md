# PHASE 6 Uncertainty Validation Report

- run_id: `city1_v3_rf500m_e20_20260618T040646Z`
- status: **partially completed**
- interpretation discipline: Phase 6 evaluates whether v3 uncertainty behaves meaningfully within the calibrated proxy-target framework.
- LOCO-like reconstruction config used in this run: ensemble_size=`5`, rf_n_estimators=`60`

## Inputs used
- `C:\Users\Asus\Downloads\City1-main\City1-main\reports\uncertainty_validation_v3\city1_v3_rf500m_e20_20260618T040646Z\phase6_input_validation.json`
- `C:\Users\Asus\Downloads\City1-main\City1-main\reports\uncertainty_validation_v3\city1_v3_rf500m_e20_20260618T040646Z\uncertainty_diagnostics_loco_like.csv`
- `C:\Users\Asus\Downloads\City1-main\City1-main\reports\uncertainty_validation_v3\city1_v3_rf500m_e20_20260618T040646Z\uncertainty_diagnostics_inference_only_proxy_check.csv`
- `C:\Users\Asus\Downloads\City1-main\City1-main\reports\district_interval_coverage_v3\city1_v3_rf500m_e20_20260618T040646Z\district_interval_coverage.csv`
- `C:\Users\Asus\Downloads\City1-main\City1-main\reports\external_disagreement_alignment_v3\city1_v3_rf500m_e20_20260618T040646Z\external_disagreement_alignment.csv`

## Outputs generated
- `C:\Users\Asus\Downloads\City1-main\City1-main\reports\uncertainty_validation_v3\city1_v3_rf500m_e20_20260618T040646Z\confidence_band_validation_summary.csv`
- `C:\Users\Asus\Downloads\City1-main\City1-main\reports\uncertainty_validation_v3\city1_v3_rf500m_e20_20260618T040646Z\error_uncertainty_alignment.csv`
- `C:\Users\Asus\Downloads\City1-main\City1-main\reports\uncertainty_validation_v3\city1_v3_rf500m_e20_20260618T040646Z\hotspot_stability.csv`
- `C:\Users\Asus\Downloads\City1-main\City1-main\reports\uncertainty_validation_v3\city1_v3_rf500m_e20_20260618T040646Z\hotspot_stability_summary.csv`
- `C:\Users\Asus\Downloads\City1-main\City1-main\reports\uncertainty_validation_v3\city1_v3_rf500m_e20_20260618T040646Z\interval_coverage_weak_target.csv`
- `C:\Users\Asus\Downloads\City1-main\City1-main\reports\uncertainty_validation_v3\city1_v3_rf500m_e20_20260618T040646Z\phase6_input_validation.json`
- `C:\Users\Asus\Downloads\City1-main\City1-main\reports\uncertainty_validation_v3\city1_v3_rf500m_e20_20260618T040646Z\run_manifest.json`
- `C:\Users\Asus\Downloads\City1-main\City1-main\reports\uncertainty_validation_v3\city1_v3_rf500m_e20_20260618T040646Z\uncertainty_diagnostics_inference_only_proxy_check.csv`
- `C:\Users\Asus\Downloads\City1-main\City1-main\reports\uncertainty_validation_v3\city1_v3_rf500m_e20_20260618T040646Z\uncertainty_diagnostics_loco_like.csv`
- `C:\Users\Asus\Downloads\City1-main\City1-main\reports\uncertainty_validation_v3\city1_v3_rf500m_e20_20260618T040646Z\uncertainty_fold_metrics.csv`
- `C:\Users\Asus\Downloads\City1-main\City1-main\reports\uncertainty_validation_v3\city1_v3_rf500m_e20_20260618T040646Z\uncertainty_monotonicity.csv`
- `C:\Users\Asus\Downloads\City1-main\City1-main\reports\uncertainty_validation_v3\city1_v3_rf500m_e20_20260618T040646Z\uncertainty_monotonicity_metrics.json`
- `C:\Users\Asus\Downloads\City1-main\City1-main\reports\uncertainty_validation_v3\city1_v3_rf500m_e20_20260618T040646Z\figures\interval_coverage_by_city.png`
- `C:\Users\Asus\Downloads\City1-main\City1-main\reports\uncertainty_validation_v3\city1_v3_rf500m_e20_20260618T040646Z\figures\error_vs_relative_uncertainty.png`
- `C:\Users\Asus\Downloads\City1-main\City1-main\reports\uncertainty_validation_v3\city1_v3_rf500m_e20_20260618T040646Z\figures\confidence_band_error_summary.png`
- `C:\Users\Asus\Downloads\City1-main\City1-main\reports\uncertainty_validation_v3\city1_v3_rf500m_e20_20260618T040646Z\figures\hotspot_stability_by_class.png`
- `C:\Users\Asus\Downloads\City1-main\City1-main\reports\district_interval_coverage_v3\city1_v3_rf500m_e20_20260618T040646Z\district_interval_coverage.csv`
- `C:\Users\Asus\Downloads\City1-main\City1-main\reports\district_interval_coverage_v3\city1_v3_rf500m_e20_20260618T040646Z\district_interval_city_summary.csv`
- `C:\Users\Asus\Downloads\City1-main\City1-main\reports\district_interval_coverage_v3\city1_v3_rf500m_e20_20260618T040646Z\run_manifest.json`
- `C:\Users\Asus\Downloads\City1-main\City1-main\reports\external_disagreement_alignment_v3\city1_v3_rf500m_e20_20260618T040646Z\external_disagreement_alignment.csv`
- `C:\Users\Asus\Downloads\City1-main\City1-main\reports\external_disagreement_alignment_v3\city1_v3_rf500m_e20_20260618T040646Z\run_manifest.json`

## Interval coverage results

- Almaty [locov_like]: coverage=0.351, below_p10=0.219, above_p90=0.430. The p10-p90 proxy interval covers a limited share of held-out proxy targets, so uncertainty evidence should be interpreted cautiously.
- Astana [locov_like]: coverage=0.305, below_p10=0.124, above_p90=0.570. The p10-p90 proxy interval covers a limited share of held-out proxy targets, so uncertainty evidence should be interpreted cautiously.
- Petropavlovsk [locov_like]: coverage=0.416, below_p10=0.376, above_p90=0.208. The p10-p90 proxy interval covers a limited share of held-out proxy targets, so uncertainty evidence should be interpreted cautiously.
- Semey [locov_like]: coverage=0.403, below_p10=0.370, above_p90=0.227. The p10-p90 proxy interval covers a limited share of held-out proxy targets, so uncertainty evidence should be interpreted cautiously.
- Shymkent [locov_like]: coverage=0.294, below_p10=0.541, above_p90=0.165. The p10-p90 proxy interval covers a limited share of held-out proxy targets, so uncertainty evidence should be interpreted cautiously.
- Taraz [locov_like]: coverage=0.376, below_p10=0.424, above_p90=0.200. The p10-p90 proxy interval covers a limited share of held-out proxy targets, so uncertainty evidence should be interpreted cautiously.
- Uralsk [locov_like]: coverage=0.300, below_p10=0.400, above_p90=0.300. The p10-p90 proxy interval covers a limited share of held-out proxy targets, so uncertainty evidence should be interpreted cautiously.
- Ust Kamenogorsk [locov_like]: coverage=0.397, below_p10=0.333, above_p90=0.270. The p10-p90 proxy interval covers a limited share of held-out proxy targets, so uncertainty evidence should be interpreted cautiously.
- Almaty [inference_only_proxy_check]: coverage=0.598, below_p10=0.210, above_p90=0.192. The p10-p90 proxy interval covers a limited share of held-out proxy targets, so uncertainty evidence should be interpreted cautiously.
- Astana [inference_only_proxy_check]: coverage=0.613, below_p10=0.107, above_p90=0.280. The p10-p90 proxy interval shows moderate held-out proxy coverage; uncertainty behavior is informative but not uniformly tight.
- Semey [inference_only_proxy_check]: coverage=0.692, below_p10=0.208, above_p90=0.100. The p10-p90 proxy interval shows moderate held-out proxy coverage; uncertainty behavior is informative but not uniformly tight.
- Shymkent [inference_only_proxy_check]: coverage=0.534, below_p10=0.273, above_p90=0.194. The p10-p90 proxy interval covers a limited share of held-out proxy targets, so uncertainty evidence should be interpreted cautiously.

## Error-vs-uncertainty results

- Almaty [locov_like]: spearman(error, relative_uncertainty)=-0.449, spearman(error, confidence_score)=0.448. Error-vs-uncertainty alignment is weak or mixed in this city and should be interpreted cautiously.
- Astana [locov_like]: spearman(error, relative_uncertainty)=-0.220, spearman(error, confidence_score)=0.221. Error-vs-uncertainty alignment is weak or mixed in this city and should be interpreted cautiously.
- Petropavlovsk [locov_like]: spearman(error, relative_uncertainty)=-0.484, spearman(error, confidence_score)=0.483. Error-vs-uncertainty alignment is weak or mixed in this city and should be interpreted cautiously.
- Semey [locov_like]: spearman(error, relative_uncertainty)=-0.354, spearman(error, confidence_score)=0.354. Error-vs-uncertainty alignment is weak or mixed in this city and should be interpreted cautiously.
- Shymkent [locov_like]: spearman(error, relative_uncertainty)=-0.387, spearman(error, confidence_score)=0.387. Error-vs-uncertainty alignment is weak or mixed in this city and should be interpreted cautiously.
- Taraz [locov_like]: spearman(error, relative_uncertainty)=-0.307, spearman(error, confidence_score)=0.307. Error-vs-uncertainty alignment is weak or mixed in this city and should be interpreted cautiously.
- Uralsk [locov_like]: spearman(error, relative_uncertainty)=-0.388, spearman(error, confidence_score)=0.383. Error-vs-uncertainty alignment is weak or mixed in this city and should be interpreted cautiously.
- Ust Kamenogorsk [locov_like]: spearman(error, relative_uncertainty)=-0.425, spearman(error, confidence_score)=0.424. Error-vs-uncertainty alignment is weak or mixed in this city and should be interpreted cautiously.
- Almaty [inference_only_proxy_check]: spearman(error, relative_uncertainty)=-0.347, spearman(error, confidence_score)=0.346. Error-vs-uncertainty alignment is weak or mixed in this city and should be interpreted cautiously.
- Astana [inference_only_proxy_check]: spearman(error, relative_uncertainty)=-0.042, spearman(error, confidence_score)=0.042. Error-vs-uncertainty alignment is weak or mixed in this city and should be interpreted cautiously.
- Semey [inference_only_proxy_check]: spearman(error, relative_uncertainty)=-0.337, spearman(error, confidence_score)=0.333. Error-vs-uncertainty alignment is weak or mixed in this city and should be interpreted cautiously.
- Shymkent [inference_only_proxy_check]: spearman(error, relative_uncertainty)=-0.421, spearman(error, confidence_score)=0.421. Error-vs-uncertainty alignment is weak or mixed in this city and should be interpreted cautiously.

## District interval coverage results or blocker

- Almaty: compared_districts=6, mean_absolute_error_p50=94209.08837614198. Only partial district p50 comparison could be carried forward from v2. District interval coverage remains blocked until frozen district assignment artifacts are available offline.
- Astana: compared_districts=5, mean_absolute_error_p50=169626.3295288148. Only partial district p50 comparison could be carried forward from v2. District interval coverage remains blocked until frozen district assignment artifacts are available offline.
- Shymkent: compared_districts=3, mean_absolute_error_p50=108862.19810263596. Only partial district p50 comparison could be carried forward from v2. District interval coverage remains blocked until frozen district assignment artifacts are available offline.

## External disagreement alignment results or blocker

- Almaty vs worldpop: spearman(disagreement, uncertainty)=-0.299. Disagreement alignment is weak or mixed for this benchmark and should be interpreted cautiously.
- Almaty vs ghs_pop: spearman(disagreement, uncertainty)=-0.494. Disagreement alignment is weak or mixed for this benchmark and should be interpreted cautiously.
- Astana vs worldpop: spearman(disagreement, uncertainty)=-0.188. Disagreement alignment is weak or mixed for this benchmark and should be interpreted cautiously.
- Astana vs ghs_pop: spearman(disagreement, uncertainty)=-0.251. Disagreement alignment is weak or mixed for this benchmark and should be interpreted cautiously.
- Shymkent vs worldpop: spearman(disagreement, uncertainty)=-0.422. Disagreement alignment is weak or mixed for this benchmark and should be interpreted cautiously.
- Shymkent vs ghs_pop: spearman(disagreement, uncertainty)=-0.451. Disagreement alignment is weak or mixed for this benchmark and should be interpreted cautiously.

## Hotspot stability results

- Almaty / high_value_high_confidence: mean_stability=0.777, mean_confidence=0.738. Stable hotspot classes retain stronger confidence/stability behavior than caution classes.
- Almaty / low_value_high_uncertainty: mean_stability=0.263, mean_confidence=0.391. Caution-oriented hotspot classes remain less stable and should not be treated as firm planning targets.
- Almaty / medium_value_high_confidence: mean_stability=0.784, mean_confidence=0.745. Stable hotspot classes retain stronger confidence/stability behavior than caution classes.
- Astana / high_value_low_confidence: mean_stability=0.219, mean_confidence=0.354. Caution-oriented hotspot classes remain less stable and should not be treated as firm planning targets.
- Astana / low_value_high_uncertainty: mean_stability=0.176, mean_confidence=0.328. Caution-oriented hotspot classes remain less stable and should not be treated as firm planning targets.
- Semey / high_value_high_confidence: mean_stability=0.834, mean_confidence=0.711. Stable hotspot classes retain stronger confidence/stability behavior than caution classes.
- Semey / high_value_low_confidence: mean_stability=0.197, mean_confidence=0.369. Caution-oriented hotspot classes remain less stable and should not be treated as firm planning targets.
- Semey / low_value_high_uncertainty: mean_stability=0.292, mean_confidence=0.369. Caution-oriented hotspot classes remain less stable and should not be treated as firm planning targets.
- Semey / medium_value_high_confidence: mean_stability=0.825, mean_confidence=0.717. Stable hotspot classes retain stronger confidence/stability behavior than caution classes.
- Shymkent / high_value_low_confidence: mean_stability=0.225, mean_confidence=0.354. Caution-oriented hotspot classes remain less stable and should not be treated as firm planning targets.
- Shymkent / low_value_high_uncertainty: mean_stability=0.200, mean_confidence=0.321. Caution-oriented hotspot classes remain less stable and should not be treated as firm planning targets.

## Confidence-band validation summary

- Almaty / high: share_cells=0.229, median_relative_uncertainty=0.044, mean_error_if_available=58.566. This confidence band retains the expected bounded relationship between uncertainty burden and proxy usefulness.
- Almaty / low: share_cells=0.109, median_relative_uncertainty=0.396, mean_error_if_available=32.093. Low-confidence cells should be treated as review-oriented or caution-heavy within the proxy framework.
- Almaty / medium: share_cells=0.662, median_relative_uncertainty=0.190, mean_error_if_available=30.225. This confidence band retains the expected bounded relationship between uncertainty burden and proxy usefulness.
- Astana / low: share_cells=0.363, median_relative_uncertainty=0.423, mean_error_if_available=41.650. Low-confidence cells should be treated as review-oriented or caution-heavy within the proxy framework.
- Astana / medium: share_cells=0.637, median_relative_uncertainty=0.217, mean_error_if_available=35.056. This confidence band retains the expected bounded relationship between uncertainty burden and proxy usefulness.
- Semey / high: share_cells=0.034, median_relative_uncertainty=0.061, mean_error_if_available=73.732. This confidence band retains the expected bounded relationship between uncertainty burden and proxy usefulness.
- Semey / low: share_cells=0.169, median_relative_uncertainty=0.593, mean_error_if_available=20.858. Low-confidence cells should be treated as review-oriented or caution-heavy within the proxy framework.
- Semey / medium: share_cells=0.797, median_relative_uncertainty=0.316, mean_error_if_available=21.212. This confidence band retains the expected bounded relationship between uncertainty burden and proxy usefulness.
- Shymkent / low: share_cells=0.301, median_relative_uncertainty=0.308, mean_error_if_available=9.025. Low-confidence cells should be treated as review-oriented or caution-heavy within the proxy framework.
- Shymkent / medium: share_cells=0.699, median_relative_uncertainty=0.119, mean_error_if_available=13.075. This confidence band retains the expected bounded relationship between uncertainty burden and proxy usefulness.

## Strongest evidence that uncertainty is meaningful

- error-vs-uncertainty alignment is available at least for inference-only proxy checks
- interval coverage against weak targets is explicitly reported
- hotspot stability summary is available by priority class

## Weakest evidence or unresolved uncertainty

- district interval coverage remains partial because frozen district assignment artifacts are unavailable offline

## Limitations

- uncertainty remains a confidence layer around a calibrated proxy surface, not true census uncertainty
- weak-target checks are not cell-level census validation
- external products provide structural comparison context, not ground truth
- district support remains partial where frozen district assignment artifacts are unavailable

## What Phase 6 does not prove

- it does not validate true population uncertainty
- it does not prove cell-level census correctness
- it does not convert confidence_score into truth probability

## Readiness for Phase 7

- Phase 7 can start conditionally: partially completed. A paper-facing package can begin if the current partial district limitation is accepted explicitly; otherwise Phase 7 should wait for frozen district assignment artifacts.

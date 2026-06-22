# City1 v3 Phase 5 Hotspot Prioritization Report

Run id: `city1_v3_rf500m_e20_20260618T040646Z`

## Scope

Phase 5 turns the Phase 4 uncertainty-aware cell outputs into a planning-screening hotspot prioritization package.
It does not validate the uncertainty layer, does not claim census truth, and does not treat confidence_score as truth probability.

High-confidence hotspots are cells where the calibrated proxy surface and the v3 confidence framework provide stronger planning-screening support.
Low-confidence hotspots may still be important but require additional evidence before strong interpretation.

## Input files used

- `/mnt/data/city1_phase5_work/outputs/v3_uncertainty/city1_v3_rf500m_e20_20260618T040646Z/almaty_uncertainty_cells.csv`
- `/mnt/data/city1_phase5_work/outputs/v3_uncertainty/city1_v3_rf500m_e20_20260618T040646Z/astana_uncertainty_cells.csv`
- `/mnt/data/city1_phase5_work/outputs/v3_uncertainty/city1_v3_rf500m_e20_20260618T040646Z/semey_uncertainty_cells.csv`
- `/mnt/data/city1_phase5_work/outputs/v3_uncertainty/city1_v3_rf500m_e20_20260618T040646Z/shymkent_uncertainty_cells.csv`
- `/mnt/data/city1_phase5_work/outputs/v3_uncertainty/city1_v3_rf500m_e20_20260618T040646Z/city_uncertainty_summary.csv`
- `/mnt/data/city1_phase5_work/outputs/v3_uncertainty/city1_v3_rf500m_e20_20260618T040646Z/run_manifest.json`

## Output files generated

- `/mnt/data/city1_phase5_work/reports/hotspot_prioritization_v3/city1_v3_rf500m_e20_20260618T040646Z/hotspot_city_summary.csv`
- `/mnt/data/city1_phase5_work/reports/hotspot_prioritization_v3/city1_v3_rf500m_e20_20260618T040646Z/top_hotspots_by_city.csv`
- `/mnt/data/city1_phase5_work/reports/hotspot_prioritization_v3/city1_v3_rf500m_e20_20260618T040646Z/caution_hotspots.csv`
- `/mnt/data/city1_phase5_work/reports/hotspot_prioritization_v3/city1_v3_rf500m_e20_20260618T040646Z/stable_hotspots.csv`
- `/mnt/data/city1_phase5_work/reports/hotspot_prioritization_v3/city1_v3_rf500m_e20_20260618T040646Z/figures/hotspot_class_distribution_by_city.png`
- `/mnt/data/city1_phase5_work/reports/hotspot_prioritization_v3/city1_v3_rf500m_e20_20260618T040646Z/figures/confidence_band_distribution_by_city.png`
- `/mnt/data/city1_phase5_work/reports/hotspot_prioritization_v3/city1_v3_rf500m_e20_20260618T040646Z/figures/almaty_p50_vs_relative_uncertainty.png`
- `/mnt/data/city1_phase5_work/reports/hotspot_prioritization_v3/city1_v3_rf500m_e20_20260618T040646Z/figures/astana_p50_vs_relative_uncertainty.png`
- `/mnt/data/city1_phase5_work/reports/hotspot_prioritization_v3/city1_v3_rf500m_e20_20260618T040646Z/figures/semey_p50_vs_relative_uncertainty.png`
- `/mnt/data/city1_phase5_work/reports/hotspot_prioritization_v3/city1_v3_rf500m_e20_20260618T040646Z/figures/shymkent_p50_vs_relative_uncertainty.png`
- `/mnt/data/city1_phase5_work/reports/hotspot_prioritization_v3/city1_v3_rf500m_e20_20260618T040646Z/figures/hotspot_priority_scatter_by_city.png`
- `/mnt/data/city1_phase5_work/reports/hotspot_prioritization_v3/city1_v3_rf500m_e20_20260618T040646Z/PHASE_5_HOTSPOT_PRIORITIZATION_REPORT.md`

## City-level hotspot summary

- Almaty: priority cells=842, high-value/high-confidence=212, high-value/low-confidence=0, medium-value/high-confidence=310, low-value/high-uncertainty=320. Almaty has a stronger high-confidence hotspot signal for planning-screening, while remaining bounded by proxy-surface uncertainty.
- Astana: priority cells=712, high-value/high-confidence=0, high-value/low-confidence=4, medium-value/high-confidence=0, low-value/high-uncertainty=708. Astana contains high-value hotspot candidates, but the current confidence layer indicates that local verification is needed before strong interpretation.
- Semey: priority cells=169, high-value/high-confidence=4, high-value/low-confidence=19, medium-value/high-confidence=10, low-value/high-uncertainty=136. Semey contains high-value hotspot candidates, but the current confidence layer indicates that local verification is needed before strong interpretation.
- Shymkent: priority cells=1256, high-value/high-confidence=0, high-value/low-confidence=89, medium-value/high-confidence=0, low-value/high-uncertainty=1167. Shymkent contains high-value hotspot candidates, but the current confidence layer indicates that local verification is needed before strong interpretation.

## Strongest planning-screening cities

- Almaty is the strongest Phase 5 planning-screening case because it has 212 high-value/high-confidence cells.

## Caution-heavy cities

- Shymkent is the most caution-heavy case by Phase 5 counts, with 89 high-value/low-confidence cells and 1167 low-value/high-uncertainty cells.

## City interpretations

- Almaty: Almaty has a stronger high-confidence hotspot signal for planning-screening, while remaining bounded by proxy-surface uncertainty.
- Astana: Astana contains high-value hotspot candidates, but the current confidence layer indicates that local verification is needed before strong interpretation.
- Semey: Semey contains high-value hotspot candidates, but the current confidence layer indicates that local verification is needed before strong interpretation.
- Shymkent: Shymkent contains high-value hotspot candidates, but the current confidence layer indicates that local verification is needed before strong interpretation.

## Stable hotspot summary

Stable hotspot rows generated: `536`.
These rows focus on high-value/high-confidence and medium-value/high-confidence cells.

## Caution hotspot summary

Caution hotspot rows generated: `2443`.
These rows focus on high-value/low-confidence and low-value/high-uncertainty cells.

## Figures

- `/mnt/data/city1_phase5_work/reports/hotspot_prioritization_v3/city1_v3_rf500m_e20_20260618T040646Z/figures/hotspot_class_distribution_by_city.png`
- `/mnt/data/city1_phase5_work/reports/hotspot_prioritization_v3/city1_v3_rf500m_e20_20260618T040646Z/figures/confidence_band_distribution_by_city.png`
- `/mnt/data/city1_phase5_work/reports/hotspot_prioritization_v3/city1_v3_rf500m_e20_20260618T040646Z/figures/almaty_p50_vs_relative_uncertainty.png`
- `/mnt/data/city1_phase5_work/reports/hotspot_prioritization_v3/city1_v3_rf500m_e20_20260618T040646Z/figures/astana_p50_vs_relative_uncertainty.png`
- `/mnt/data/city1_phase5_work/reports/hotspot_prioritization_v3/city1_v3_rf500m_e20_20260618T040646Z/figures/semey_p50_vs_relative_uncertainty.png`
- `/mnt/data/city1_phase5_work/reports/hotspot_prioritization_v3/city1_v3_rf500m_e20_20260618T040646Z/figures/shymkent_p50_vs_relative_uncertainty.png`
- `/mnt/data/city1_phase5_work/reports/hotspot_prioritization_v3/city1_v3_rf500m_e20_20260618T040646Z/figures/hotspot_priority_scatter_by_city.png`

## Known limitations

- Phase 5 is a prioritization layer, not an uncertainty-validation layer.
- External agreement remains the documented neutral fallback where city-specific Phase 6 alignment is not yet available.
- District interval coverage is not yet included; it belongs to Phase 6.
- Hotspot classes are screening categories and must not be interpreted as census truth.

## What Phase 5 does not prove

- It does not prove that high-confidence hotspots are true population centers.
- It does not prove that low-confidence hotspots are wrong.
- It does not validate P10/P50/P90 against observed cell-level census labels.
- It does not replace local administrative or field verification.

## Readiness for Phase 6

Phase 6 can start after this package is reviewed. The next step is to test whether the uncertainty behavior is meaningful through interval coverage, error-vs-uncertainty alignment, district interval coverage, external disagreement alignment, and hotspot stability.

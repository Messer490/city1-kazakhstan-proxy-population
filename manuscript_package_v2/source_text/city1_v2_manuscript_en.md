# City1 v2: A Reproducible Open-Data Calibrated Proxy Population Surface Baseline with Multi-Level Validation for Intra-Urban Analysis in Kazakhstan

## Abstract

Intra-urban population surfaces are important for spatial analysis, urban planning, and service allocation, yet true grid-level census labels are rarely available in practice. We present City1 v2, a reproducible open-data baseline for constructing a calibrated proxy population surface within a city. The system uses OpenStreetMap-derived geospatial features, weak supervision to construct a proxy target, and calibration to official city-level population totals. Rather than claiming exact cell-level population reconstruction, City1 v2 is framed as a calibrated proxy surface baseline with explicitly bounded claims. The frozen production configuration uses `random_forest`, a `500 m` grid, and a `calibrated-only` runtime mode.

The validation package is intentionally multi-level. Under `Leave-One-City-Out`, `random_forest` achieves a calibrated RMSE of `115.934` and a calibrated R² of `0.934`, substantially outperforming `ridge`. The choice of `500 m` as the production default is supported by a grid-size benchmark in which this resolution obtained the best benchmark score (`0.248572`) among `250 m`, `500 m`, and `1000 m`. Internal administrative evaluation is implemented through a partial district benchmark for `Almaty`, `Astana`, and `Shymkent`; the strongest signal is observed for `Almaty` (Pearson `0.543`, Spearman `0.657`), whereas `Astana` and `Shymkent` remain weak and should be interpreted as partial rather than complete internal support. Independent external comparison shows that `WorldPop` aligns best with the overall shape of the predicted surface (Pearson `0.877`), whereas `GHS-POP` better captures hotspot structure (hotspot IoU `0.443`, top-decile overlap `0.614`).

An ablation study shows that `built_form_only` is the strongest non-full ablation, while the full feature set remains best overall, and calibration contributes substantially to final performance. A qualitative validation layer for `Almaty` and `Astana` locks eight curated hotspot and coldspot cases and shows that dense residential and central mixed-use areas tend to receive high predicted population while peripheral open or sparsely built zones tend to receive low predicted population. We argue that City1 v2 should be understood not as a true grid-level census reconstruction system, but as a reproducible and scientifically bounded baseline for data-scarce urban settings.

## 1. Introduction

Estimating the intra-urban distribution of population is a central problem in applied urban analytics. Such surfaces are useful for planning, accessibility analysis, exposure assessment, and many other tasks in which total city population is insufficient and internal spatial structure matters. In practice, however, this is precisely the level at which reliable supervision is usually missing: official city totals are often available, while true population labels at a fine regular grid are rarely published.

This setting creates two recurrent methodological risks. The first is to produce a visually plausible surface that is not consistent with official totals. The second is to present a proxy-based map as if it were a true reconstruction of census population at the grid-cell level. Under data scarcity, both risks are substantial.

This study adopts a narrower but more defensible formulation. We address the problem of constructing a calibrated proxy population surface rather than a true census reconstruction. City1 v2 uses open geospatial data, primarily OpenStreetMap-derived features, weak supervision to construct a proxy target, and city-level calibration to official totals. This design prioritizes reproducibility, transparency, and practical usefulness while maintaining bounded claims.

The paper makes five contributions. First, it presents a reproducible open-data pipeline for intra-urban proxy population surface generation. Second, it uses official-total calibration to enforce city-level consistency. Third, it provides a multi-level validation stack including `LOCO`, `spatial block CV`, district benchmark, external benchmark, ablation, and qualitative validation. Fourth, it delivers a reproducible paper/report package that generates figures and tables from code. Fifth, it offers a disciplined baseline framing for data-scarce urban settings.

## 2. Related Work

Research on gridded population mapping has commonly focused on census disaggregation, settlement-informed redistribution, remote sensing, land-use proxies, and increasingly multimodal feature stacks. Many studies aim to approximate true spatial population distribution as closely as possible, but such efforts often depend on detailed census supports, proprietary data, or richer supervisory signals than are available in many applied settings.

Another important line of work centers on constrained disaggregation, where a spatial surface is normalized or calibrated to higher-level official totals. In such settings, both statistical consistency and spatial plausibility are important. Open-data approaches are especially relevant here because they provide a transparent and reproducible baseline for cities where richer data sources are unavailable.

At the same time, many proxy-based systems remain weakly packaged from a validation standpoint. It is common to report only a single metric, a single city, or a small qualitative illustration, without separating distinct risks such as transferability to unseen cities, within-city robustness under reduced spatial leakage, dependence on particular feature families, agreement with external population products, and qualitative map plausibility. Our work focuses on that validation packaging problem as much as on the predictive pipeline itself.

City1 v2 is therefore positioned not as a “best possible truth model,” but as a disciplined baseline system contribution: official-total-constrained proxy mapping, open-data-only inputs, a reproducible CLI and reporting layer, and a multi-level validation framework tailored to data-scarce urban settings.

## 3. Study Design and Data

The study focuses on Kazakhstan as a practically relevant setting in which official city totals are available and a consistent open-data workflow can be assembled. In the frozen City1 v2 reference package, the structured totals file contains `10` calibrated cities, of which `8` belong to the validated baseline batch. At freeze time, one city also has a recorded smoke-passed runtime path.

Official city totals are used as calibration anchors. These totals define the final city-wide sum of the predicted surface and prevent disagreement between the output map and official statistics. However, they do not provide true intra-urban labels, so the learning problem remains weakly supervised.

The feature stack is derived from OpenStreetMap. In the frozen baseline, it includes building-, floor-area-, transport-, and POI-related proxy variables. The production model is fixed as `random_forest`, and the production grid is fixed at `500 m`. This grid choice is not arbitrary: it is supported by a grid-size benchmark and represents a practical balance between excessive fragmentation at `250 m` and excessive smoothing at `1000 m`.

Different subsets of cities support different validation layers. The district benchmark anchor cities are `Almaty`, `Astana`, and `Shymkent`. External benchmark comparison relies on `WorldPop` and `GHS-POP`. Qualitative validation uses `Almaty` and `Astana`, where curated hotspot and coldspot cases are interpreted in the context of OSM completeness.

## 4. Method

City1 v2 is structured as a reproducible chain: official totals, OSM-derived features, weak target construction, supervised learning on weak targets, calibration, validation, and reporting. A key methodological choice is that the model is not trained on true grid-level census labels, because such labels are unavailable. Instead, the system adopts weak supervision.

First, feature values are computed for each grid cell. Raw features are then log-transformed and normalized, after which a weak population score is constructed as a weighted combination of proxy features. This score is not interpreted as ground-truth population; it is used only to distribute the official city total across cells and thus produce a weak target.

The model is then trained to predict that weak target from the feature set. In the frozen production baseline, the chosen learner is `random_forest`. After raw predictions are produced, calibration to official city totals is applied so that the final surface matches the official total exactly at the city level. The system therefore combines proxy-based spatial differentiation with official-total consistency.

This design should be interpreted as a baseline engineering-scientific solution rather than a universal law of population mapping. For that reason, the architecture is supported by separate validation layers that address different risks: transfer to unseen cities, robustness within cities, agreement with external population products, dependence on feature families, and spatial plausibility.

## 5. Validation Framework

The validation stack in City1 v2 is intentionally multi-layered. No single validation layer can address all methodological risks, so several complementary checks are used.

`Leave-One-City-Out` addresses transferability to unseen cities and is the key support for the cross-city generalization claim. `Spatial block CV` addresses a different question: whether performance remains strong when local spatial leakage is reduced within a city. Together, these two layers separate inter-city transferability from intra-city robustness.

The grid-size benchmark compares `250 m`, `500 m`, and `1000 m` and serves as the basis for the frozen production grid choice. The OSM completeness score is not a measure of model accuracy; it is a heuristic reliability layer indicating how strong or sparse the OSM-derived input stack appears for a given city.

The district benchmark serves as partial internal administrative validation by aggregating cell-level predictions to districts and comparing them against district-level references where available. This layer is useful, but it must not be described as solved ground-truth validation. External benchmark comparison evaluates structural agreement with independent gridded population products. Ablation isolates the contribution of different feature families. Qualitative validation evaluates whether the resulting population surface is spatially plausible through locked hotspot and coldspot case studies.

## 6. Results

### 6.1 Model choice

In the frozen baseline, `random_forest` clearly outperforms `ridge`. Under `Leave-One-City-Out`, `random_forest` reaches a calibrated RMSE of `115.934` and a calibrated R² of `0.934`, whereas `ridge` performs substantially worse and yields a strongly negative calibrated R². This supports the decision to use `random_forest` as the production baseline model.

The strongest validation row overall is `random_forest` under `spatial_block`, with a calibrated RMSE of `76.301`. However, the `v2` identity remains centered on `random_forest` + `500 m` + `calibrated-only`, while `spatial_block` is interpreted as a robustness layer rather than a separate production path.

### 6.2 Grid choice

The grid-size benchmark supports `500 m` as the frozen default. This configuration achieves the best benchmark score (`0.248572`) among the evaluated cell sizes. In the `v2` interpretation, `250 m` appears too sensitive and prone to fragmentation, while `1000 m` oversmooths intra-urban structure.

### 6.3 District benchmark

District benchmark support is available for `Almaty`, `Astana`, and `Shymkent`, but its quality is uneven. The strongest result is observed for `Almaty`, where Pearson correlation reaches `0.543` and Spearman correlation reaches `0.657`. Although this is not a “solved” validation result, it indicates a meaningful relationship between predicted district totals and official district references.

For `Astana` and `Shymkent`, the results are much weaker. In `Astana`, Pearson is `-0.277` and Spearman is `-0.300`; in `Shymkent`, Pearson is `-0.169` and Spearman is `-0.500`. District benchmark should therefore be described as partial internal administrative validation rather than as a complete within-city truth layer.

### 6.4 External benchmark

External benchmark comparison provides stronger support for structural plausibility. `WorldPop` shows the best agreement with our surface in terms of overall correlation, reaching Pearson `0.877`. By contrast, `GHS-POP` performs best on hotspot-sensitive metrics, with Spearman `0.834`, top-decile overlap `0.614`, and hotspot IoU `0.443`.

This pattern is substantively useful. It suggests that different independent population products confirm different aspects of the surface: `WorldPop` is closer to the overall shape of the predicted distribution, whereas `GHS-POP` better matches the most concentrated spatial hotspots.

### 6.5 Ablation

The ablation study shows that the full frozen feature set remains best. For `full_features`, calibrated RMSE is `115.934` and calibrated R² is `0.934`. The strongest non-full regime is `built_form_only`, with calibrated RMSE `120.656` and calibrated R² `0.929`. This indicates that built form is the dominant driver of the model, while the additional feature families still provide measurable gains.

The ablation also confirms that calibration is not a cosmetic adjustment. For the full feature set, calibration yields an RMSE gain of `135.821`, indicating that city-total adjustment has a major impact on the final surface quality.

### 6.6 Qualitative validation

Qualitative validation was locked for `Almaty` and `Astana`, with `8` curated cases in total. In `Almaty`, the OSM completeness score is `75.827` with the label `good`, providing a stronger context for qualitative interpretation. In `Astana`, the completeness score is `65.014` with the label `moderate`, so the qualitative reading requires more caution.

Despite this difference, the curated hotspot and coldspot cases show a consistent pattern: dense residential and central mixed-use clusters tend to receive high predicted population, whereas peripheral open, weak-built, or sparse zones tend to receive low predicted population. This supports a spatial plausibility claim, but it does not substitute for cell-level truth validation.

## 7. Limitations

The most important limitation is fundamental: true grid-level census labels are unavailable. Accordingly, the learning problem is solved through weak supervision rather than through fully supervised learning on ground truth. This limitation cannot be removed by rhetoric and must be stated explicitly.

The internal administrative validation layer is also limited. District benchmark is useful, but its signal is uneven across the three anchor cities and does not provide equally strong support everywhere. In addition, OSM quality varies across cities, which constrains how uniformly results can be interpreted.

Finally, the frozen `v2` system remains a calibrated-only baseline. It does not include uncertainty maps, explainability, satellite features, or accessibility features. These are appropriate directions for future versions, but they are intentionally outside the scope of the current paper.

## 8. Conclusion

City1 v2 provides a reproducible open-data baseline for constructing a calibrated proxy population surface within a city. Its main strength lies not in claiming exact reconstruction of true grid-level population, but in combining official-total calibration, a reproducible pipeline, and a multi-level validation package.

The results show that even without true grid-level labels it is possible to build a scientifically disciplined baseline that is useful for data-scarce urban settings. In this context, bounded claims and explicit limitations should be understood as part of the methodological strength of the system rather than as weaknesses to be concealed.

Future work may extend the system with satellite, accessibility, uncertainty, and explainability layers, but those directions belong to later versions and remain outside the frozen `City1 v2` baseline.

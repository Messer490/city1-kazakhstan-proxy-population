# City1 v2: воспроизводимый open-data baseline calibrated proxy population surface с многоуровневой валидацией для внутригородского анализа в Казахстане

## Аннотация

Внутригородские population surfaces важны для пространственного анализа, городского планирования и оценки неравномерности распределения населения, однако в большинстве практических сценариев истинные census-метки на уровне мелкой сетки недоступны. В этой работе мы представляем City1 v2, воспроизводимый open-data baseline для построения calibrated proxy population surface внутри города. Система использует геопространственные признаки, извлечённые из OpenStreetMap, weak supervision для построения proxy target и последующую калибровку по официальным total значениям населения на уровне города. В отличие от систем, претендующих на точную реконструкцию населения по каждой ячейке, City1 v2 позиционируется как calibrated proxy surface baseline с честно ограниченными claims. Базовая версия заморожена с использованием `random_forest`, сетки `500 m` и режима `calibrated-only`.

Валидационный пакет построен как многоуровневая система проверок. На уровне межгородского переноса `random_forest` под `Leave-One-City-Out` достигает calibrated RMSE `115.934` и calibrated R² `0.934`, заметно превосходя `ridge`. Выбор `500 m` как production default поддерживается grid-size benchmark, где этот размер клетки получил лучший benchmark score (`0.248572`) по сравнению с `250 m` и `1000 m`. Внутригородская административная проверка реализована как partial district benchmark для `Almaty`, `Astana` и `Shymkent`; наиболее сильный сигнал даёт `Almaty` с Pearson `0.543` и Spearman `0.657`, тогда как результаты для `Astana` и `Shymkent` остаются слабыми и должны интерпретироваться осторожно как частичная, а не полная truth validation. Независимая внешняя проверка показывает, что `WorldPop` лучше совпадает с нашей поверхностью по общей форме распределения (Pearson `0.877`), тогда как `GHS-POP` лучше удерживает hotspot structure (hotspot IoU `0.443`, top-decile overlap `0.614`).

Дополнительный ablation study показывает, что `built_form_only` является strongest non-full ablation, но полный набор признаков остаётся лучшим, а calibration даёт существенный вклад в итоговое качество. Qualitative validation для `Almaty` и `Astana` фиксирует eight curated hotspot/coldspot cases и показывает, что плотные жилые и центральные mixed-use зоны обычно получают высокие оценки населения, тогда как периферийные open или sparsely built зоны получают низкие оценки. Мы утверждаем, что City1 v2 является не системой истинной реконструкции census population по ячейкам, а воспроизводимым и scientifically honest baseline для data-scarce urban settings.

## 1. Introduction

Оценка пространственного распределения населения внутри города является фундаментальной задачей для прикладной городской аналитики. Такие поверхности используются в planning, resource allocation, accessibility analysis, exposure assessment и во многих других задачах, где важно не только общее население города, но и его внутригородская структура. На практике именно этот уровень часто оказывается самым сложным: официальные totals на уровне города обычно доступны, а истинные population labels на уровне мелкой регулярной сетки почти никогда не публикуются.

Это приводит к двум типичным ошибкам в прикладных системах. Первая ошибка состоит в том, что модель слабо ограничивается внешней статистикой и производит визуально правдоподобную, но несогласованную с официальными totals поверхность. Вторая ошибка состоит в том, что proxy-оценка подаётся как истинная реконструкция населения по каждой клетке, хотя соответствующего ground truth не существует. В условиях data scarcity обе ошибки методологически опасны.

В этой работе мы выбираем более узкую, но честную постановку. Мы рассматриваем задачу построения calibrated proxy population surface, а не истинной census reconstruction. City1 v2 использует open geospatial data, в первую очередь OSM-derived features, weak supervision для построения proxy target, а затем city-level calibration по официальным значениям населения. Такой подход позволяет совместить воспроизводимость, практическую полезность и строго ограниченные claims.

Статья делает пять основных вкладов. Во-первых, мы представляем воспроизводимый open-data pipeline для построения proxy population surface внутри города. Во-вторых, мы используем official-total calibration для согласования итоговой поверхности с официальной статистикой на уровне города. В-третьих, мы дополняем baseline многоуровневой системой валидации, включающей `LOCO`, `spatial block CV`, district benchmark, external benchmark, ablation и qualitative validation. В-четвёртых, мы предоставляем reproducible paper/report package, который генерирует figures и tables из кода. В-пятых, мы показываем, как такой baseline можно честно позиционировать для data-scarce urban settings без завышенных claims о cell-level truth.

## 2. Related Work

Литература по gridded population mapping традиционно развивается в направлении disaggregation of census counts, использования settlement layers, remote sensing, land use proxies и multimodal feature stacks. Многие работы стремятся к максимально точному аппроксимированию истинного распределения населения, однако такой подход обычно опирается либо на более детальные census supports, либо на дополнительные закрытые или дорогостоящие данные.

Отдельный класс методов строится вокруг constrained disaggregation, когда независимая пространственная поверхность нормируется или калибруется по более крупным официальным totals. В таких постановках важна не только статистическая согласованность, но и пространственная правдоподобность результата. Open-data approaches занимают здесь особое место, поскольку позволяют создавать воспроизводимые и прозрачные baseline systems, особенно для городов, где более богатые data sources недоступны.

В то же время многие proxy-based systems страдают от недостаточной validation packaging. Часто публикуется только одна метрика, один город или один qualitative example, тогда как остаются неразделёнными разные риски: переносимость на новый город, устойчивость при уменьшении spatial leakage, зависимость от feature family, согласованность с внешними population surfaces и качественная правдоподобность карты. Наша работа делает акцент именно на таком multi-level validation package.

Важно подчеркнуть, что City1 v2 не претендует на статус best-possible truth model. Его новизна находится прежде всего в дисциплинированной baseline framing: official-total-constrained proxy mapping, open-data-only design, reproducible CLI and report pipeline, а также многоуровневой validation logic, адаптированной к data-scarce urban settings.

## 3. Study Design and Data

Исследование сфокусировано на Казахстане как на practically relevant setting, где доступны официальные city totals и возможно построение единого open-data workflow. В замороженной версии City1 v2 reference file содержит `10` calibrated cities, из которых `8` входят в validated baseline batch. Один город на момент фиксации статуса также имеет recorded smoke-passed runtime path.

Официальные city totals используются как calibration anchors. Именно эти totals определяют итоговую сумму населения на уровне города и позволяют избежать несогласованности между итоговой картой и официальной статистикой. При этом они не дают истинного распределения населения по клеткам, поэтому задача остаётся weakly supervised.

Признаки строятся на основе OpenStreetMap-derived feature stack. В замороженном baseline используются building-, floor-area-, transport- и POI-related признаки, а production choice фиксирован как `random_forest` на сетке `500 m`. Сетка `500 m` выбрана не произвольно, а на основании grid-size benchmark. На этой сетке система остаётся достаточно детальной для внутригородского анализа, но более устойчивой, чем `250 m`, и менее грубой, чем `1000 m`.

Для внутренней и внешней проверки используются разные наборы городов и референсов. District benchmark anchor cities — это `Almaty`, `Astana` и `Shymkent`. External benchmarks представлены `WorldPop` и `GHS-POP`. Для qualitative validation используются `Almaty` и `Astana`, где были зафиксированы curated hotspot/coldspot cases с учётом OSM completeness context.

## 4. Method

City1 v2 строится как последовательная reproducible chain: official totals, OSM-derived features, weak target construction, supervised learning on weak targets, calibration, validation, reporting. Важный методологический выбор заключается в том, что мы не обучаем модель на истинных grid-level census labels, потому что они отсутствуют. Вместо этого используется weak supervision.

Сначала для каждой ячейки сетки вычисляются feature values. Затем raw features проходят log-transform и normalization, после чего формируется weak population score как weighted combination of proxy features. Этот score не интерпретируется как ground truth population. Он используется только для распределения official city total across cells и построения weak target.

На следующем этапе модель обучается предсказывать weak target по набору признаков. В frozen production baseline используется `random_forest`. После получения raw predictions применяется calibration to official totals, чтобы итоговая поверхность точно соответствовала официальной сумме населения города. Таким образом, система объединяет proxy-based spatial differentiation и official-total consistency.

Это решение должно интерпретироваться как baseline engineering-scientific design, а не как универсальный закон population mapping. Именно поэтому архитектура дополняется отдельными validation layers, которые проверяют разные стороны системы: межгородской перенос, устойчивость внутри города, согласованность с внешними population products, feature-family importance и qualitative plausibility.

## 5. Validation Framework

Validation stack в `City1 v2` намеренно построен как многоуровневая система. Ни один отдельный слой не способен закрыть все методологические риски, поэтому в работе используются несколько взаимодополняющих проверок, каждая из которых отвечает на свой собственный вопрос о надёжности итоговой поверхности.

`Leave-One-City-Out` проверяет переносимость модели на новый город и потому является ключевым слоем для baseline-claim о межгородской generalization under data scarcity. `Spatial block CV` отвечает на другой риск: не поддерживается ли качество за счёт локального spatial leakage внутри города. В совокупности эти две схемы позволяют развести вопросы межгородской transferability и внутригородской robustness, не смешивая их в одну метрику.

Grid-size benchmark сопоставляет `250 m`, `500 m` и `1000 m` и используется не как косметический sensitivity analysis, а как самостоятельный аргумент в пользу frozen default grid. OSM completeness score, в свою очередь, не интерпретируется как measure of model accuracy. Его функция состоит в том, чтобы служить heuristic reliability layer для оценки качества и полноты входного OSM-derived feature stack по каждому городу.

District benchmark используется как partial internal administrative validation. На этом этапе grid-level predictions агрегируются до административных районов и сопоставляются с district-level references там, где такие данные доступны. Этот слой важен для внутренней проверки, однако он не должен описываться как solved ground-truth validation. External benchmark решает другую задачу: он сравнивает нашу поверхность с независимыми gridded population products и позволяет оценить structural agreement без претензии на абсолютную истину.

Дополнительные validation layers уточняют интерпретацию модели с других сторон. Ablation показывает, какие feature families действительно двигают качество и насколько результат зависит от полного feature stack и calibration. Qualitative validation фиксирует spatial plausibility через curated hotspot/coldspot cases и тем самым дополняет количественные проверки содержательным пространственным чтением. В совокупности весь validation framework следует понимать не как одну универсальную проверку, а как согласованный набор evidence layers, поддерживающих baseline-статус `City1 v2`.

## 6. Results

### 6.1 Выбор модели

В замороженной версии `v2` модель `random_forest` уверенно превосходит `ridge`. При схеме `Leave-One-City-Out` `random_forest` достигает calibrated RMSE `115.934` и calibrated R² `0.934`, тогда как `ridge` показывает существенно более слабый результат и отрицательное значение calibrated R². Это важно методологически, поскольку подтверждает, что выбор основной baseline-модели был сделан по фактическому качеству, а не по эвристическому предпочтению.

Наиболее сильная строка в общем наборе валидационных результатов также принадлежит `random_forest`, но уже при `spatial_block`, где calibrated RMSE составляет `76.301`. Однако production-конфигурация `v2` по-прежнему фиксируется как `random_forest` + `500 m` + `calibrated-only`, а `spatial_block` интерпретируется как отдельный слой robustness validation, а не как самостоятельный production-режим.

### 6.2 Выбор размера сетки

Grid-size benchmark поддерживает выбор `500 m` как frozen default. Именно эта конфигурация получила лучший benchmark score (`0.248572`) среди трёх протестированных вариантов. В интерпретации `v2` это означает, что сетка `250 m` оказывается слишком чувствительной и склонной к избыточной фрагментации, тогда как `1000 m` чрезмерно сглаживает внутригородскую структуру. Таким образом, `500 m` выступает наиболее сбалансированным решением между пространственной детализацией и устойчивостью итоговой поверхности.

### 6.3 District benchmark

District benchmark доступен для `Almaty`, `Astana` и `Shymkent`, однако его качество остаётся неоднородным. Наиболее содержательный сигнал наблюдается в `Almaty`, где Pearson correlation равен `0.543`, а Spearman correlation — `0.657`. Хотя этот результат нельзя трактовать как полное решение задачи внутригородской truth validation, он всё же указывает на осмысленную связь между агрегированными district-level predictions и official district references.

Для `Astana` и `Shymkent` результаты существенно слабее. Для `Astana` Pearson составляет `-0.277`, а Spearman `-0.300`; для `Shymkent` Pearson составляет `-0.169`, а Spearman `-0.500`. По этой причине district benchmark в данной статье должен трактоваться как partial internal administrative validation, а не как полноценная validation of truth на внутригородском уровне. Иными словами, этот слой добавляет полезную внутреннюю опору, но не снимает основных ограничений baseline-постановки.

### 6.4 External benchmark

External benchmark даёт более сильную поддержку общей структурной правдоподобности поверхности. `WorldPop` показывает наилучшее совпадение с нашей картой по overall correlation, достигая Pearson `0.877`. В то же время `GHS-POP` показывает лучший результат по hotspot-sensitive metrics: Spearman `0.834`, top-decile overlap `0.614` и hotspot IoU `0.443`.

Этот паттерн содержательно важен, поскольку показывает, что разные независимые population products подтверждают разные аспекты качества нашей поверхности. В частности, `WorldPop` лучше поддерживает общий shape of the surface, тогда как `GHS-POP` лучше совпадает с наиболее плотными spatial hotspots. Для интерпретации результатов это сильнее, чем ситуация, в которой один внешний benchmark выглядел бы искусственно лучшим по всем метрикам одновременно.

### 6.5 Ablation

Ablation study показывает, что полный frozen feature set остаётся лучшим. Для `full_features` calibrated RMSE составляет `115.934`, а calibrated R² — `0.934`. Наиболее сильный non-full режим — это `built_form_only`, где calibrated RMSE равен `120.656`, а calibrated R² — `0.929`. Это означает, что built form действительно является главным драйвером модели, однако дополнительные признаки всё же дают измеримый прирост и потому не являются декоративным расширением feature stack.

Одновременно ablation подтверждает, что calibration не является косметической надстройкой. Для полного feature set calibration RMSE gain составляет `135.821`, что указывает на существенное влияние city-total adjustment на итоговое качество поверхности. Иными словами, важен не только сам predictive model, но и связка proxy prediction + official-total calibration.

### 6.6 Qualitative validation

Qualitative validation была зафиксирована для `Almaty` и `Astana`; всего было выделено `8` curated cases. Для `Almaty` OSM completeness score равен `75.827` и имеет label `good`, что делает qualitative interpretation более уверенной. Для `Astana` completeness score равен `65.014` и имеет label `moderate`, поэтому qualitative reading требует большей осторожности и более сдержанной интерпретации.

Несмотря на это различие, curated hotspot/coldspot cases в обоих городах демонстрируют последовательный pattern: dense residential and central mixed-use clusters tend to receive high predicted population, whereas peripheral open, weak-built, or sparse zones tend to receive low predicted population. Это поддерживает claim о spatial plausibility и показывает, что итоговая поверхность не выглядит случайным шумом после calibration. Вместе с тем данный слой не должен подменять собой cell-level truth validation и должен интерпретироваться именно как qualitative plausibility evidence.

## 7. Limitations

Главное ограничение работы остаётся фундаментальным: true grid-level census labels отсутствуют. Следовательно, задача решается через weak supervision, а не через fully supervised learning on ground truth. Этот limitation нельзя обойти формулировкой; его нужно прямо признавать.

Внутренняя административная validation layer также ограничена. District benchmark полезен, но его signal неравномерен между anchor cities и не даёт одинаково сильной поддержки по всем городам. Кроме того, OSM quality varies across cities, что ограничивает одинаковую интерпретируемость результатов для разных городов.

Наконец, замороженная версия `v2` остаётся calibrated-only baseline. Она не включает uncertainty maps, explainability layer, satellite features или accessibility features. Эти направления логично отнести к будущим версиям системы, а не пытаться включить задним числом в текущую статью.

## 8. Conclusion

City1 v2 представляет собой воспроизводимый open-data baseline для построения calibrated proxy population surface внутри города. Его главная сила состоит не в claim о точной реконструкции истинного населения по клеткам, а в сочетании official-total calibration, reproducible pipeline и multi-level validation package.

Мы показываем, что даже в условиях отсутствия true grid-level labels можно построить scientifically disciplined baseline, который остаётся полезным для data-scarce urban settings. При этом bounded claims и честное описание ограничений являются не слабостью, а частью methodological strength of the system.

В дальнейшем развитие может идти в сторону satellite, accessibility, uncertainty и explainability layers, однако эти направления относятся уже к последующим версиям и выходят за рамки frozen `City1 v2` baseline.

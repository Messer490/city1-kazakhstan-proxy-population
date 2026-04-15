# Feature Pipeline v2

## Что решает этот pipeline

Новый pipeline устраняет главную проблему legacy-версии:

- train и inference больше не должны считать признаки разным кодом
- рабочая CRS для измерений отделена от display CRS для карты
- сетка, OSM extraction и feature engineering вынесены в модульное ядро

## Архитектура

- `src/city1/config.py`
  - конфигурация grid, OSM extraction и feature engineering

- `src/city1/crs.py`
  - normalise display CRS
  - infer working/projected CRS
  - prepare city geometry bundle

- `src/city1/grid.py`
  - генерация городской сетки в рабочей CRS

- `src/city1/osm.py`
  - загрузка boundary и OSM layers
  - защитная обработка пустых слоёв

- `src/city1/features.py`
  - расчёт площадей, длин, counts, floor area
  - `Combined_Index`
  - настоящий `POI_Access_Index` по дистанциям до реальных POI

- `src/city1/pipeline.py`
  - orchestration layer: city -> grid -> osm -> features

## Принципы

1. Все площади и длины считаются только в project CRS.
2. Координаты для карты считаются отдельно в `EPSG:4326`.
3. `POI_Access_Index` считается по точкам реальных POI, а не по центрам grid-ячеек.
4. Результат возвращается в двух формах:
   - `display_gdf` для карт
   - `feature_frame` для модели и CSV

## Ближайшие шаги

1. Подключить pipeline к новому Streamlit app.
2. Добавить caching/raw snapshots для OSM responses.
3. Подключить feature validation сразу после генерации.
4. Построить новый training pipeline на тех же колонках.


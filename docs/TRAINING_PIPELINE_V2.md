# Training Pipeline v2

## Что делает новый training pipeline

Новый слой обучения решает задачу без grid-level ground truth через связку:

- официальные city totals
- feature datasets по ячейкам
- weak-label allocation
- group-based validation по городам

## Модули

- `src/city1/city_totals.py`
  - загрузка и нормализация официальных totals
  - сопоставление по имени города

- `src/city1/labeling.py`
  - proxy score по признакам
  - распределение city total по ячейкам

- `src/city1/training.py`
  - сбор тренировочного датасета
  - cross-validation по городам
  - обучение финальной модели
  - сохранение артефактов

## Важная честность

Этот pipeline пока не делает "настоящий supervised learning по переписи на сетке".

Он делает:

1. weak supervision
2. calibration by official totals
3. reproducible baseline training

## Минимальный боевой сценарий

1. Сгенерировать feature CSV по нескольким городам через `generate_city_features_v2.py`
2. Загрузить официальный файл population totals
3. Собрать weak labels
4. Обучить baseline model
5. Валидировать переносимость через city holdout

## Следующий шаг после обучения

После этого нужно:

1. подключить новый model artifact в Streamlit v2
2. сделать inference + calibration на официальные totals
3. добавить отчёт по качеству и ограничениям


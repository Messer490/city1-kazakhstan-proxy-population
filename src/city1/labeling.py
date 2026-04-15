from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .features import min_max_scale_frame


DEFAULT_WEAK_LABEL_WEIGHTS: tuple[tuple[str, float], ...] = (
    ("Total_Floor_Area", 0.35),
    ("Building_Area", 0.18),
    ("Residential_Area", 0.16),
    ("Building_Count", 0.08),
    ("Road_Length", 0.06),
    ("Bus_Stop_Count", 0.04),
    ("Schools_Count", 0.03),
    ("Hospitals_Count", 0.03),
    ("Parks_Shops_Count", 0.04),
    ("Combined_Index", 0.03),
)


@dataclass(frozen=True)
class WeakLabelConfig:
    weighted_columns: tuple[tuple[str, float], ...] = DEFAULT_WEAK_LABEL_WEIGHTS
    epsilon: float = 1e-6
    use_log1p_transform: bool = True
    clip_negative_features: bool = True
    official_total_column: str = "Official_City_Population"
    score_column: str = "Weak_Population_Score"
    share_column: str = "Weak_Population_Share"
    target_column: str = "Weak_Population_Target"


def compute_proxy_population_score(
    df: pd.DataFrame,
    config: WeakLabelConfig | None = None,
) -> pd.Series:
    label_config = config or WeakLabelConfig()
    available_features = [column for column, _ in label_config.weighted_columns if column in df.columns]

    if not available_features:
        return pd.Series(0.0, index=df.index, dtype=float)

    base = df[available_features].fillna(0.0).astype(float)
    if label_config.clip_negative_features:
        base = base.clip(lower=0.0)
    if label_config.use_log1p_transform:
        base = np.log1p(base)

    normalized = min_max_scale_frame(base)
    score = pd.Series(0.0, index=df.index, dtype=float)

    for column, weight in label_config.weighted_columns:
        if column in normalized.columns:
            score = score + normalized[column] * weight

    return score.clip(lower=0.0)


def allocate_city_total_to_cells(
    df: pd.DataFrame,
    official_population: int,
    config: WeakLabelConfig | None = None,
) -> pd.DataFrame:
    label_config = config or WeakLabelConfig()
    frame = df.copy()

    score = compute_proxy_population_score(frame, config=label_config)
    adjusted = score + label_config.epsilon
    total_score = float(adjusted.sum())

    if total_score <= 0:
        share = pd.Series(1.0 / len(frame), index=frame.index, dtype=float)
    else:
        share = adjusted / total_score

    frame[label_config.official_total_column] = float(official_population)
    frame[label_config.score_column] = score
    frame[label_config.share_column] = share
    frame[label_config.target_column] = share * float(official_population)
    return frame


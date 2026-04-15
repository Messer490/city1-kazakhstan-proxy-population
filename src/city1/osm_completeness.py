from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Mapping

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns


@dataclass(frozen=True)
class OSMCompletenessResult:
    city_name: str
    completeness_score: float
    completeness_label: str
    critical_coverage_score: float
    optional_coverage_score: float
    density_quality_score: float
    warning_quality_score: float
    osm_warning_count: int
    qa_warning_count: int
    building_zero_share: float
    road_zero_share: float
    poi_zero_share: float
    total_floor_area_zero_share: float
    bus_stop_zero_share: float
    park_zero_share: float
    schools_zero_share: float
    hospitals_zero_share: float
    retail_zero_share: float
    critical_nonempty_layers: int
    optional_nonempty_layers: int

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _zero_share(frame: pd.DataFrame, column: str) -> float:
    if column not in frame.columns or frame.empty:
        return 1.0
    series = pd.to_numeric(frame[column], errors="coerce").dropna()
    if series.empty:
        return 1.0
    return float((series <= 0).mean())


def _presence_from_zero_share(zero_share: float) -> float:
    if pd.isna(zero_share):
        return 0.0
    return max(0.0, min(1.0, 1.0 - float(zero_share)))


def _layer_nonempty_score(layers: Mapping[str, object] | None, layer_name: str, *, fallback_presence: float) -> float:
    if layers is None:
        return 1.0 if fallback_presence > 0 else 0.0
    layer = layers.get(layer_name)
    if layer is None:
        return 0.0
    try:
        return 1.0 if len(layer) > 0 else 0.0
    except Exception:
        return 0.0


def _completeness_label(score: float) -> str:
    if score >= 85:
        return "excellent"
    if score >= 70:
        return "good"
    if score >= 55:
        return "moderate"
    return "weak"


def compute_osm_completeness(
    frame: pd.DataFrame,
    *,
    city_name: str,
    layers: Mapping[str, object] | None = None,
    osm_warnings: tuple[str, ...] | list[str] = (),
    qa_flags: pd.DataFrame | None = None,
) -> OSMCompletenessResult:
    building_zero = _zero_share(frame, "Building_Area")
    road_zero = _zero_share(frame, "Road_Length")
    poi_zero = _zero_share(frame, "POI_Access_Index")
    floor_zero = _zero_share(frame, "Total_Floor_Area")
    bus_zero = _zero_share(frame, "Bus_Stop_Count")
    park_zero = _zero_share(frame, "Park_Area")
    schools_zero = _zero_share(frame, "Schools_Count")
    hospitals_zero = _zero_share(frame, "Hospitals_Count")
    retail_zero = _zero_share(frame, "Retail_Area")

    building_presence = _presence_from_zero_share(building_zero)
    road_presence = _presence_from_zero_share(road_zero)
    poi_presence = _presence_from_zero_share(poi_zero)
    floor_presence = _presence_from_zero_share(floor_zero)
    bus_presence = _presence_from_zero_share(bus_zero)
    park_presence = _presence_from_zero_share(park_zero)
    schools_presence = _presence_from_zero_share(schools_zero)
    hospitals_presence = _presence_from_zero_share(hospitals_zero)
    retail_presence = _presence_from_zero_share(retail_zero)

    critical_layer_scores = [
        0.5 * building_presence + 0.5 * _layer_nonempty_score(layers, "buildings", fallback_presence=building_presence),
        0.5 * road_presence + 0.5 * _layer_nonempty_score(layers, "roads", fallback_presence=road_presence),
        poi_presence,
    ]
    optional_layer_scores = [
        0.5 * bus_presence + 0.5 * _layer_nonempty_score(layers, "bus_stops", fallback_presence=bus_presence),
        0.5 * park_presence + 0.5 * _layer_nonempty_score(layers, "parks", fallback_presence=park_presence),
        0.5 * schools_presence + 0.5 * _layer_nonempty_score(layers, "schools", fallback_presence=schools_presence),
        0.5 * hospitals_presence + 0.5 * _layer_nonempty_score(layers, "hospitals", fallback_presence=hospitals_presence),
        0.5 * retail_presence + 0.5 * _layer_nonempty_score(layers, "shops", fallback_presence=retail_presence),
    ]

    critical_coverage_score = float(sum(critical_layer_scores) / len(critical_layer_scores))
    optional_coverage_score = float(sum(optional_layer_scores) / len(optional_layer_scores))
    density_quality_score = float((building_presence + road_presence + floor_presence) / 3.0)

    osm_warning_count = len(tuple(osm_warnings))
    qa_warning_count = 0
    if qa_flags is not None and not qa_flags.empty and "severity" in qa_flags.columns:
        qa_warning_count = int((qa_flags["severity"].astype(str) == "warning").sum())
    warning_quality_score = max(0.0, 1.0 - 0.15 * osm_warning_count - 0.03 * qa_warning_count)

    completeness_score = 100.0 * (
        0.45 * critical_coverage_score
        + 0.20 * optional_coverage_score
        + 0.25 * density_quality_score
        + 0.10 * warning_quality_score
    )

    critical_nonempty_layers = int(
        sum(
            [
                _layer_nonempty_score(layers, "buildings", fallback_presence=building_presence) > 0,
                _layer_nonempty_score(layers, "roads", fallback_presence=road_presence) > 0,
                poi_presence > 0,
            ]
        )
    )
    optional_nonempty_layers = int(
        sum(
            [
                _layer_nonempty_score(layers, "bus_stops", fallback_presence=bus_presence) > 0,
                _layer_nonempty_score(layers, "parks", fallback_presence=park_presence) > 0,
                _layer_nonempty_score(layers, "schools", fallback_presence=schools_presence) > 0,
                _layer_nonempty_score(layers, "hospitals", fallback_presence=hospitals_presence) > 0,
                _layer_nonempty_score(layers, "shops", fallback_presence=retail_presence) > 0,
            ]
        )
    )

    return OSMCompletenessResult(
        city_name=city_name,
        completeness_score=float(round(completeness_score, 3)),
        completeness_label=_completeness_label(completeness_score),
        critical_coverage_score=float(round(critical_coverage_score, 3)),
        optional_coverage_score=float(round(optional_coverage_score, 3)),
        density_quality_score=float(round(density_quality_score, 3)),
        warning_quality_score=float(round(warning_quality_score, 3)),
        osm_warning_count=int(osm_warning_count),
        qa_warning_count=int(qa_warning_count),
        building_zero_share=float(round(building_zero, 6)),
        road_zero_share=float(round(road_zero, 6)),
        poi_zero_share=float(round(poi_zero, 6)),
        total_floor_area_zero_share=float(round(floor_zero, 6)),
        bus_stop_zero_share=float(round(bus_zero, 6)),
        park_zero_share=float(round(park_zero, 6)),
        schools_zero_share=float(round(schools_zero, 6)),
        hospitals_zero_share=float(round(hospitals_zero, 6)),
        retail_zero_share=float(round(retail_zero, 6)),
        critical_nonempty_layers=int(critical_nonempty_layers),
        optional_nonempty_layers=int(optional_nonempty_layers),
    )


def build_osm_completeness_batch(
    features_dir: str | Path,
) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for path in sorted(Path(features_dir).glob("*.csv")):
        frame = pd.read_csv(path)
        city_name = Path(path).stem
        result = compute_osm_completeness(frame, city_name=city_name)
        row = result.to_dict()
        row["source_file"] = path.name
        rows.append(row)

    if not rows:
        raise ValueError(f"No feature CSV files found in {features_dir}")

    return pd.DataFrame(rows).sort_values(
        ["completeness_score", "city_name"],
        ascending=[False, True],
    ).reset_index(drop=True)


def save_osm_completeness_report(summary_df: pd.DataFrame, output_dir: str | Path) -> dict[str, Path]:
    output_root = Path(output_dir)
    output_root.mkdir(parents=True, exist_ok=True)

    summary_path = output_root / "osm_completeness_summary.csv"
    report_path = output_root / "osm_completeness_report.md"
    figure_path = output_root / "osm_completeness_scores.png"

    summary_df.to_csv(summary_path, index=False)

    fig, ax = plt.subplots(figsize=(10, 4.5))
    display = summary_df.sort_values("completeness_score", ascending=False)
    sns.barplot(data=display, x="city_name", y="completeness_score", ax=ax, color="#0ea5e9")
    ax.set_title("OSM Completeness Score by City")
    ax.set_xlabel("")
    ax.set_ylabel("Completeness score")
    ax.tick_params(axis="x", labelrotation=25)
    fig.tight_layout()
    fig.savefig(figure_path, dpi=200, bbox_inches="tight")
    plt.close(fig)

    top_row = display.iloc[0]
    bottom_row = display.iloc[-1]
    lines = [
        "# OSM Completeness Report v2",
        "",
        f"- Best city in current batch: `{top_row['city_name']}` with score `{float(top_row['completeness_score']):.3f}`",
        f"- Weakest city in current batch: `{bottom_row['city_name']}` with score `{float(bottom_row['completeness_score']):.3f}`",
        "",
        "## Label legend",
        "",
        "- `excellent` >= 85",
        "- `good` >= 70",
        "- `moderate` >= 55",
        "- `weak` < 55",
        "",
    ]
    report_path.write_text("\n".join(lines), encoding="utf-8")

    return {
        "summary_path": summary_path,
        "figure_path": figure_path,
        "report_path": report_path,
    }

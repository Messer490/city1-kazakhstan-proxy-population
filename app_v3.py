from __future__ import annotations

import json
from pathlib import Path

import folium
import pandas as pd
import streamlit as st
from streamlit_folium import st_folium

from src.city1.city_status import load_city_status_registry
from src.city1.city_totals import normalize_city_name
from src.city1.inference import (
    CityInferenceError,
    get_preferred_uncertainty_model_path,
    list_available_uncertainty_models,
    run_city_uncertainty_inference,
    save_city_uncertainty_outputs,
)


st.set_page_config(page_title="City1 v3 Uncertainty-Aware Surface", layout="wide")

DEFAULT_OUTPUT_ROOT = Path("outputs/v3_uncertainty")
TOTALS_REFERENCE_CSV = Path("data/external/city_population_reference_v2.csv")
STATUS_REGISTRY_CSV = Path("data/external/city_status_registry_v2.csv")


def _format_population(value: float) -> str:
    return f"{int(round(float(value))):,}".replace(",", " ")


def _format_float(value: float, digits: int = 3) -> str:
    return f"{float(value):.{digits}f}"


def _load_city_status_frame() -> pd.DataFrame:
    if STATUS_REGISTRY_CSV.exists():
        try:
            frame = load_city_status_registry(STATUS_REGISTRY_CSV)
        except Exception:
            frame = pd.DataFrame()
        else:
            if "display_query" not in frame.columns:
                frame["display_query"] = frame.apply(
                    lambda row: f"{row['city_name']}, {row['country']}" if str(row.get("country", "")).strip() else str(row["city_name"]),
                    axis=1,
                )
            return frame

    if not TOTALS_REFERENCE_CSV.exists():
        return pd.DataFrame(columns=["city_name", "country", "display_query"])
    frame = pd.read_csv(TOTALS_REFERENCE_CSV)
    if frame.empty:
        return frame
    frame["normalized_city_name"] = frame["city_name"].map(normalize_city_name)
    frame["display_query"] = frame.apply(
        lambda row: f"{row['city_name']}, {row['country']}" if str(row.get("country", "")).strip() else str(row["city_name"]),
        axis=1,
    )
    frame["supported_for_calibrated_inference"] = True
    return frame


def _city_queries_by_flag(status_frame: pd.DataFrame, flag_column: str) -> list[str]:
    if status_frame.empty:
        return []
    if flag_column not in status_frame.columns:
        return status_frame["display_query"].dropna().astype(str).tolist()
    filtered = status_frame.loc[status_frame[flag_column].fillna(False).astype(bool)]
    return filtered["display_query"].dropna().astype(str).tolist()


def _format_model_options() -> tuple[list[str], dict[str, Path]]:
    available = list_available_uncertainty_models()
    if not available:
        return [], {}
    mapping = {item.label: item.path for item in available}
    return list(mapping.keys()), mapping


def _default_model_label(model_paths: dict[str, Path]) -> str | None:
    if not model_paths:
        return None
    preferred = get_preferred_uncertainty_model_path()
    for label, path in model_paths.items():
        if path == preferred:
            return label
    return next(iter(model_paths))


def _serialize_result(result, save_paths: dict[str, str] | None = None) -> dict[str, object]:
    output_frame = result.output_frame.copy()
    output_frame["p50_display"] = output_frame["p50"].map(_format_population)
    output_frame["relative_uncertainty_display"] = output_frame["relative_uncertainty"].map(lambda value: _format_float(value, 3))
    output_frame["confidence_score_display"] = output_frame["confidence_score"].map(lambda value: _format_float(value, 3))

    output_gdf = result.output_gdf.copy()
    for column in ("p50_display", "relative_uncertainty_display", "confidence_score_display"):
        output_gdf[column] = output_frame[column].to_numpy()

    return {
        "official_population": int(result.official_population),
        "raw_prediction_sum": float(result.raw_prediction_sum),
        "calibration_factor": float(result.calibration_factor),
        "output_frame": output_frame,
        "geojson_payload": json.loads(output_gdf.to_json()),
        "osm_completeness": result.osm_completeness.to_dict(),
        "uncertainty_interval_summary": result.uncertainty_interval_summary or {},
        "save_paths": save_paths or {},
    }


def _build_population_map(result_payload: dict[str, object]) -> folium.Map:
    frame = result_payload["output_frame"]
    center = [float(frame["centroid_latitude"].median()), float(frame["centroid_longitude"].median())]
    population = pd.to_numeric(frame["p50"], errors="coerce").fillna(0.0)
    min_value = float(population.min())
    max_value = float(population.max())
    span = max(max_value - min_value, 1.0)

    city_map = folium.Map(location=center, zoom_start=11, tiles="CartoDB positron")

    def style_function(feature):
        value = float(feature["properties"]["p50"])
        intensity = (value - min_value) / span
        red = int(30 + 200 * intensity)
        blue = int(220 - 180 * intensity)
        fill_color = f"#{red:02x}5a{blue:02x}"
        return {"fillColor": fill_color, "color": "#2f3542", "weight": 0.4, "fillOpacity": 0.65}

    tooltip = folium.GeoJsonTooltip(
        fields=["cell_id", "p50_display", "confidence_band", "relative_uncertainty_display"],
        aliases=["Cell", "Population (P50)", "Confidence band", "Relative uncertainty"],
        localize=True,
        sticky=True,
        labels=True,
    )
    folium.GeoJson(
        result_payload["geojson_payload"],
        name="population_surface",
        style_function=style_function,
        tooltip=tooltip,
    ).add_to(city_map)
    return city_map


def _build_uncertainty_map(result_payload: dict[str, object]) -> folium.Map:
    frame = result_payload["output_frame"]
    center = [float(frame["centroid_latitude"].median()), float(frame["centroid_longitude"].median())]
    uncertainty = pd.to_numeric(frame["relative_uncertainty"], errors="coerce").fillna(0.0)
    min_value = float(uncertainty.min())
    max_value = float(uncertainty.max())
    span = max(max_value - min_value, 1e-9)

    city_map = folium.Map(location=center, zoom_start=11, tiles="CartoDB positron")

    def style_function(feature):
        value = float(feature["properties"]["relative_uncertainty"])
        intensity = (value - min_value) / span
        red = int(255 * intensity)
        green = int(180 - 120 * intensity)
        blue = int(70 - 40 * intensity)
        fill_color = f"#{red:02x}{max(green, 0):02x}{max(blue, 0):02x}"
        return {"fillColor": fill_color, "color": "#1f2937", "weight": 0.4, "fillOpacity": 0.7}

    tooltip = folium.GeoJsonTooltip(
        fields=["cell_id", "relative_uncertainty_display", "confidence_band", "p50_display"],
        aliases=["Cell", "Relative uncertainty", "Confidence band", "Population (P50)"],
        localize=True,
        sticky=True,
        labels=True,
    )
    folium.GeoJson(
        result_payload["geojson_payload"],
        name="uncertainty_surface",
        style_function=style_function,
        tooltip=tooltip,
    ).add_to(city_map)
    return city_map


def _render_result(result_payload: dict[str, object]) -> None:
    st.success("City1 v3 uncertainty inference completed successfully.")
    frame = result_payload["output_frame"]
    interval_summary = result_payload.get("uncertainty_interval_summary", {})
    completeness = result_payload.get("osm_completeness", {})

    metrics_columns = st.columns(8)
    metrics_columns[0].metric("Run id", str(frame["run_id"].iloc[0]))
    metrics_columns[1].metric("Official total", f"{result_payload['official_population']:,}")
    metrics_columns[2].metric("Raw median sum", f"{result_payload['raw_prediction_sum']:,.0f}")
    metrics_columns[3].metric("Calibration factor", f"{result_payload['calibration_factor']:.3f}")
    metrics_columns[4].metric("Final sum (P50)", f"{pd.to_numeric(frame['p50'], errors='coerce').sum():,.0f}")
    metrics_columns[5].metric("Median width", _format_float(interval_summary.get("median_uncertainty_width", 0.0), 2))
    metrics_columns[6].metric("Median rel. unc.", _format_float(interval_summary.get("median_uncertainty_relative", 0.0), 3))
    metrics_columns[7].metric(
        "Mean confidence",
        _format_float(interval_summary.get("mean_confidence_score", 0.0), 3),
        str(completeness.get("completeness_label", "")).title(),
    )

    st.subheader("Confidence Bands")
    confidence_counts = (
        frame["confidence_band"]
        .value_counts(dropna=False)
        .rename_axis("confidence_band")
        .reset_index(name="cell_count")
    )
    st.dataframe(confidence_counts, use_container_width=True, hide_index=True)

    map_columns = st.columns(2)
    with map_columns[0]:
        st.subheader("Population Surface")
        st.caption("Frozen v3 final surface uses the calibrated median `p50` output.")
        st_folium(_build_population_map(result_payload), use_container_width=True, height=620, key="city1_v3_population_map")
    with map_columns[1]:
        st.subheader("Uncertainty Overlay")
        st.caption("Relative interval width `(p90 - p10) / max(p50, epsilon)`; warmer colors mean higher uncertainty.")
        st_folium(_build_uncertainty_map(result_payload), use_container_width=True, height=620, key="city1_v3_uncertainty_map")

    st.subheader("Output Preview")
    st.dataframe(
        frame[
            [
                "cell_id",
                "p10",
                "p50",
                "p90",
                "relative_uncertainty",
                "confidence_score",
                "confidence_band",
                "hotspot_priority_class",
            ]
        ].head(200),
        use_container_width=True,
    )

    csv_bytes = frame.drop(columns=["p50_display", "relative_uncertainty_display", "confidence_score_display"], errors="ignore").to_csv(index=False).encode("utf-8")
    geojson_bytes = json.dumps(result_payload["geojson_payload"]).encode("utf-8")
    city_slug = str(frame["city_slug"].iloc[0])

    download_columns = st.columns(2)
    download_columns[0].download_button(
        "Download CSV",
        data=csv_bytes,
        file_name=f"{city_slug}_uncertainty_cells.csv",
        mime="text/csv",
    )
    download_columns[1].download_button(
        "Download GeoJSON",
        data=geojson_bytes,
        file_name=f"{city_slug}_uncertainty_cells.geojson",
        mime="application/geo+json",
    )

    save_paths = result_payload.get("save_paths", {})
    if save_paths:
        for key, path in save_paths.items():
            st.info(f"{key}: {path}")


st.title("City1 v3 Uncertainty-Aware Proxy Population Surface")
st.caption(
    "Frozen v3 runtime: Kazakhstan-first, 500 m fixed grid, official-total calibration, and uncertainty-aware proxy output."
)

city_status_frame = _load_city_status_frame()
shortcut_queries = _city_queries_by_flag(city_status_frame, "supported_for_calibrated_inference")
model_labels, model_mapping = _format_model_options()

if not model_labels:
    st.error("No v3 uncertainty models were found in the models directory.")
    st.stop()

default_label = _default_model_label(model_mapping)
default_index = model_labels.index(default_label) if default_label in model_mapping else 0
default_city = "Semey, Kazakhstan" if "Semey, Kazakhstan" in shortcut_queries else (shortcut_queries[0] if shortcut_queries else "Semey, Kazakhstan")

with st.sidebar:
    st.header("Run v3 Inference")
    if shortcut_queries:
        selected_supported_city = st.selectbox("Validated city shortcut", options=shortcut_queries, index=shortcut_queries.index(default_city))
    else:
        selected_supported_city = default_city
    place_name = st.text_input("City query", selected_supported_city)
    selected_label = st.selectbox("Uncertainty model", options=model_labels, index=default_index)
    save_outputs = st.checkbox("Save canonical outputs to outputs/v3_uncertainty/<run_id>", value=True)
    run_button = st.button("Generate Uncertainty-Aware Surface", type="primary")
    st.caption("Frozen v3 core: random_forest + fixed 500 m grid + official-total calibration + ensemble uncertainty.")

if run_button:
    try:
        with st.spinner("Loading frozen features, running the v3 ensemble, and calibrating to official totals..."):
            result = run_city_uncertainty_inference(place_name=place_name, model_path=model_mapping[selected_label])
            save_paths: dict[str, str] = {}
            if save_outputs:
                saved = save_city_uncertainty_outputs(result, DEFAULT_OUTPUT_ROOT / str(result.output_frame["run_id"].iloc[0]))
                save_paths = {name: str(path) for name, path in saved.items()}
        payload = _serialize_result(result, save_paths=save_paths)
        _render_result(payload)
    except CityInferenceError as exc:
        st.error(str(exc))

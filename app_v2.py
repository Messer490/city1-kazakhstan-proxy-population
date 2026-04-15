from __future__ import annotations

import json
from pathlib import Path

import folium
import pandas as pd
import streamlit as st
from streamlit_folium import st_folium

from src.city1.city_status import load_city_status_registry
from src.city1.config import FeaturePipelineConfig, GridConfig
from src.city1.city_totals import normalize_city_name
from src.city1.inference import (
    CityInferenceError,
    get_preferred_model_path,
    list_available_models,
    run_city_inference,
    save_city_inference_outputs,
    slugify_place_name,
)
from src.city1.osm_completeness import compute_osm_completeness


st.set_page_config(page_title="City1 v2 Population Surface", layout="wide")
RESULT_STATE_KEY = "city1_v2_last_result"
DEFAULT_OUTPUT_DIR = Path("data/processed/inference_runs")
TOTALS_REFERENCE_CSV = Path("data/external/city_population_reference_v2.csv")
STATUS_REGISTRY_CSV = Path("data/external/city_status_registry_v2.csv")


def _format_model_options() -> tuple[list[str], dict[str, Path]]:
    available = list_available_models()
    if not available:
        return [], {}
    mapping = {item.label: item.path for item in available}
    return list(mapping.keys()), mapping


def _default_model_label(model_paths: dict[str, Path]) -> str | None:
    if not model_paths:
        return None
    preferred = get_preferred_model_path()
    for label, path in model_paths.items():
        if path == preferred:
            return label
    return next(iter(model_paths))


def _format_population(value: float) -> str:
    return f"{int(round(float(value))):,}".replace(",", " ")


def _load_supported_cities_frame() -> pd.DataFrame:
    if not TOTALS_REFERENCE_CSV.exists():
        return pd.DataFrame(columns=["city_name", "country", "population", "verified"])

    frame = pd.read_csv(TOTALS_REFERENCE_CSV)
    required = {"city_name", "country", "population"}
    if not required.issubset(frame.columns):
        return pd.DataFrame(columns=["city_name", "country", "population", "verified"])

    cleaned = frame.copy()
    if "verified" not in cleaned.columns:
        cleaned["verified"] = False
    cleaned["display_query"] = cleaned.apply(
        lambda row: f"{row['city_name']}, {row['country']}" if str(row["country"]).strip() else str(row["city_name"]),
        axis=1,
    )
    return cleaned.sort_values(["verified", "city_name"], ascending=[False, True]).reset_index(drop=True)


def _supported_city_queries() -> list[str]:
    frame = _load_supported_cities_frame()
    if frame.empty:
        return []
    return frame["display_query"].dropna().astype(str).tolist()


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

    fallback = _load_supported_cities_frame()
    if fallback.empty:
        return pd.DataFrame(
            columns=[
                "city_name",
                "normalized_city_name",
                "country",
                "population",
                "verified",
                "official_total_available",
                "supported_for_calibrated_inference",
                "validated_batch",
                "recommended_for_baseline_use",
                "display_query",
            ]
        )

    fallback["normalized_city_name"] = fallback["city_name"].map(normalize_city_name)
    fallback["official_total_available"] = True
    fallback["supported_for_calibrated_inference"] = True
    fallback["validated_batch"] = False
    fallback["recommended_for_baseline_use"] = False
    fallback["status_label"] = "official_total_only"
    fallback["smoke_passed"] = False
    return fallback


def _city_queries_by_flag(status_frame: pd.DataFrame, flag_column: str) -> list[str]:
    if status_frame.empty:
        return []
    if flag_column not in status_frame.columns:
        return status_frame["display_query"].dropna().astype(str).tolist()
    filtered = status_frame.loc[status_frame[flag_column].fillna(False).astype(bool)]
    return filtered["display_query"].dropna().astype(str).tolist()


def _lookup_city_status_row(place_name: str, status_frame: pd.DataFrame) -> pd.Series | None:
    if status_frame.empty:
        return None
    normalized = normalize_city_name(place_name.split(",")[0].strip())
    matches = status_frame.loc[status_frame["normalized_city_name"].astype(str) == normalized]
    if matches.empty:
        return None
    return matches.iloc[0]


def _augment_geojson_payload(frame: pd.DataFrame, geojson_payload: dict) -> dict:
    augmented = json.loads(json.dumps(geojson_payload))
    by_zone = frame.set_index("Zone_ID").to_dict(orient="index") if "Zone_ID" in frame.columns else {}

    for feature in augmented.get("features", []):
        properties = feature.setdefault("properties", {})
        zone_id = properties.get("Zone_ID")
        if zone_id is None or zone_id not in by_zone:
            continue
        row = by_zone[zone_id]
        properties["Population_Estimate_Final_Display"] = row.get(
            "Population_Estimate_Final_Display",
            _format_population(row.get("Population_Estimate_Final", 0)),
        )
        properties["Population_Prediction_Raw_Display"] = row.get(
            "Population_Prediction_Raw_Display",
            _format_population(row.get("Population_Prediction_Raw", 0)),
        )
    return augmented


def _serialize_result(result, place_name: str, save_paths: dict[str, str] | None = None) -> dict:
    output_frame = result.output_frame.copy()
    output_frame["Population_Estimate_Final_Display"] = output_frame["Population_Estimate_Final"].map(_format_population)
    output_frame["Population_Prediction_Raw_Display"] = output_frame["Population_Prediction_Raw"].map(_format_population)
    output_gdf = result.output_gdf.copy()
    output_gdf["Population_Estimate_Final_Display"] = output_frame["Population_Estimate_Final_Display"].to_numpy()
    output_gdf["Population_Prediction_Raw_Display"] = output_frame["Population_Prediction_Raw_Display"].to_numpy()

    return {
        "place_name": place_name,
        "model_name": result.model.model_name,
        "official_population": int(result.official_population),
        "raw_prediction_sum": float(result.raw_prediction_sum),
        "calibration_factor": float(result.calibration_factor),
        "output_frame": output_frame,
        "geojson_payload": json.loads(output_gdf.to_json()),
        "warnings": list(result.feature_artifacts.layers.warnings),
        "qa_flags": result.qa_flags.copy(),
        "osm_completeness": result.osm_completeness.to_dict(),
        "save_paths": save_paths or {},
    }


def _save_interactive_map_html(result_payload: dict, output_dir: str | Path = DEFAULT_OUTPUT_DIR) -> Path:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    base_name = f"{slugify_place_name(result_payload['place_name'])}__{result_payload['model_name']}"
    html_path = output_path / f"{base_name}.html"
    city_map = _build_map(result_payload)
    city_map.save(str(html_path))
    return html_path


def _list_saved_runs(output_dir: str | Path = DEFAULT_OUTPUT_DIR) -> list[dict[str, object]]:
    root = Path(output_dir)
    if not root.exists():
        return []

    runs: list[dict[str, object]] = []
    for csv_path in sorted(root.glob("*.csv"), key=lambda path: path.stat().st_mtime, reverse=True):
        geojson_path = csv_path.with_suffix(".geojson")
        if not geojson_path.exists():
            continue
        html_path = csv_path.with_suffix(".html")
        runs.append(
            {
                "stem": csv_path.stem,
                "csv_path": csv_path,
                "geojson_path": geojson_path,
                "html_path": html_path if html_path.exists() else None,
                "label": csv_path.stem.replace("__", " / "),
            }
        )
    return runs


def _load_saved_result(run_record: dict[str, object]) -> dict:
    csv_path = Path(run_record["csv_path"])
    geojson_path = Path(run_record["geojson_path"])
    frame = pd.read_csv(csv_path)

    if "Population_Estimate_Final_Display" not in frame.columns and "Population_Estimate_Final" in frame.columns:
        frame["Population_Estimate_Final_Display"] = frame["Population_Estimate_Final"].map(_format_population)
    if "Population_Prediction_Raw_Display" not in frame.columns and "Population_Prediction_Raw" in frame.columns:
        frame["Population_Prediction_Raw_Display"] = frame["Population_Prediction_Raw"].map(_format_population)

    geojson_payload = json.loads(geojson_path.read_text(encoding="utf-8"))
    geojson_payload = _augment_geojson_payload(frame, geojson_payload)

    place_name = str(frame["city_name"].iloc[0]) if "city_name" in frame.columns and not frame.empty else str(run_record["stem"])
    model_name = str(frame["model_name"].iloc[0]) if "model_name" in frame.columns and not frame.empty else str(run_record["stem"]).split("__")[-1]
    official_population = (
        int(frame["Official_City_Population"].iloc[0])
        if "Official_City_Population" in frame.columns and not frame.empty
        else int(round(float(frame["Population_Estimate_Final"].sum())))
    )
    raw_prediction_sum = (
        float(frame["Population_Prediction_Raw"].sum())
        if "Population_Prediction_Raw" in frame.columns
        else float(frame["Population_Estimate_Final"].sum())
    )
    calibration_factor = (
        float(frame["Calibration_Factor"].iloc[0])
        if "Calibration_Factor" in frame.columns and not frame.empty
        else (float(official_population / raw_prediction_sum) if raw_prediction_sum > 0 else 0.0)
    )

    save_paths = {
        "csv_path": str(csv_path),
        "geojson_path": str(geojson_path),
    }
    if run_record.get("html_path"):
        save_paths["html_path"] = str(run_record["html_path"])

    return {
        "place_name": place_name,
        "model_name": model_name,
        "official_population": official_population,
        "raw_prediction_sum": raw_prediction_sum,
        "calibration_factor": calibration_factor,
        "output_frame": frame,
        "geojson_payload": geojson_payload,
        "warnings": [],
        "qa_flags": pd.DataFrame(),
        "osm_completeness": compute_osm_completeness(frame, city_name=normalize_city_name(place_name)).to_dict(),
        "save_paths": save_paths,
    }


def _build_map(result_payload: dict):
    center = [
        float(result_payload["output_frame"]["latitude"].median()),
        float(result_payload["output_frame"]["longitude"].median()),
    ]
    population = result_payload["output_frame"]["Population_Estimate_Final"]
    min_value = float(population.min())
    max_value = float(population.max())
    span = max(max_value - min_value, 1.0)

    city_map = folium.Map(location=center, zoom_start=11, tiles="CartoDB positron")

    def style_function(feature):
        value = float(feature["properties"]["Population_Estimate_Final"])
        intensity = (value - min_value) / span
        red = int(30 + 200 * intensity)
        blue = int(220 - 180 * intensity)
        fill_color = f"#{red:02x}5a{blue:02x}"
        return {
            "fillColor": fill_color,
            "color": "#2f3542",
            "weight": 0.4,
            "fillOpacity": 0.6,
        }

    def highlight_function(_feature):
        return {
            "color": "#111827",
            "weight": 1.5,
            "fillOpacity": 0.85,
        }

    geojson_payload = result_payload["geojson_payload"]
    tooltip = folium.GeoJsonTooltip(
        fields=[
            "Zone_ID",
            "Population_Estimate_Final_Display",
            "Building_Count",
            "Road_Length",
            "POI_Access_Index",
        ],
        aliases=["Zone", "Population", "Buildings", "Road Length", "POI Access"],
        localize=True,
        sticky=True,
        labels=True,
    )
    popup = folium.GeoJsonPopup(
        fields=[
            "Zone_ID",
            "Population_Estimate_Final_Display",
            "Population_Prediction_Raw_Display",
            "Building_Count",
            "Road_Length",
            "Schools_Count",
            "Hospitals_Count",
        ],
        aliases=[
            "Zone",
            "Calibrated Population",
            "Raw Population",
            "Buildings",
            "Road Length",
            "Schools",
            "Hospitals",
        ],
        localize=True,
        labels=True,
    )
    folium.GeoJson(
        geojson_payload,
        name="population_surface",
        style_function=style_function,
        highlight_function=highlight_function,
        tooltip=tooltip,
        popup=popup,
    ).add_to(city_map)
    return city_map


def _render_result(result_payload: dict) -> None:
    st.success("Inference completed successfully.")

    metrics_columns = st.columns(6)
    metrics_columns[0].metric("Zones", f"{len(result_payload['output_frame']):,}")
    metrics_columns[1].metric("Official total", f"{result_payload['official_population']:,}")
    metrics_columns[2].metric("Raw sum", f"{result_payload['raw_prediction_sum']:,.0f}")
    metrics_columns[3].metric("Calibration factor", f"{result_payload['calibration_factor']:.3f}")
    metrics_columns[4].metric(
        "Final sum",
        f"{result_payload['output_frame']['Population_Estimate_Final'].sum():,.0f}",
    )
    completeness = result_payload.get("osm_completeness", {})
    if completeness:
        metrics_columns[5].metric(
            "OSM completeness",
            f"{float(completeness.get('completeness_score', 0.0)):.1f}",
            str(completeness.get("completeness_label", "")).title(),
        )

    if result_payload["warnings"]:
        with st.expander("OSM warnings"):
            for warning in result_payload["warnings"]:
                st.write(f"- {warning}")

    if completeness:
        with st.expander("OSM completeness"):
            st.caption(
                "Heuristic reliability signal for the OSM-derived feature stack. "
                "It is not model accuracy, but it helps show whether the input coverage looks strong or sparse."
            )
            detail_rows = pd.DataFrame(
                [
                    {"component": "Overall score", "value": f"{float(completeness.get('completeness_score', 0.0)):.3f}"},
                    {"component": "Label", "value": str(completeness.get("completeness_label", ""))},
                    {
                        "component": "Critical coverage",
                        "value": f"{float(completeness.get('critical_coverage_score', 0.0)):.3f}",
                    },
                    {
                        "component": "Optional coverage",
                        "value": f"{float(completeness.get('optional_coverage_score', 0.0)):.3f}",
                    },
                    {
                        "component": "Density quality",
                        "value": f"{float(completeness.get('density_quality_score', 0.0)):.3f}",
                    },
                    {
                        "component": "Warning quality",
                        "value": f"{float(completeness.get('warning_quality_score', 0.0)):.3f}",
                    },
                    {"component": "OSM warnings", "value": str(int(completeness.get("osm_warning_count", 0)))},
                    {"component": "QA warnings", "value": str(int(completeness.get("qa_warning_count", 0)))},
                ]
            )
            st.dataframe(detail_rows, use_container_width=True, hide_index=True)
            st.caption("Raw completeness payload")
            st.json(completeness)

    qa_flags = result_payload["qa_flags"]
    if isinstance(qa_flags, pd.DataFrame) and not qa_flags.empty:
        with st.expander("Feature QA warnings"):
            st.dataframe(qa_flags, use_container_width=True)

    st.subheader("Population Surface Map")
    st.caption("Hover over a grid cell or click it to see the estimated population for that cell.")
    city_map = _build_map(result_payload)
    st_folium(city_map, use_container_width=True, height=650, key="population_surface_map")

    st.subheader("Output Preview")
    st.dataframe(
        result_payload["output_frame"][
            [
                "Zone_ID",
                "latitude",
                "longitude",
                "Population_Prediction_Raw",
                "Population_Estimate_Final",
            ]
        ].head(200),
        use_container_width=True,
    )

    csv_bytes = result_payload["output_frame"].drop(
        columns=["Population_Estimate_Final_Display", "Population_Prediction_Raw_Display"],
        errors="ignore",
    ).to_csv(index=False).encode("utf-8")
    geojson_bytes = json.dumps(result_payload["geojson_payload"]).encode("utf-8")
    city_slug = slugify_place_name(result_payload["place_name"])

    download_columns = st.columns(2)
    download_columns[0].download_button(
        "Download CSV",
        data=csv_bytes,
        file_name=f"{city_slug}__{result_payload['model_name']}.csv",
        mime="text/csv",
    )
    download_columns[1].download_button(
        "Download GeoJSON",
        data=geojson_bytes,
        file_name=f"{city_slug}__{result_payload['model_name']}.geojson",
        mime="application/geo+json",
    )

    save_paths = result_payload.get("save_paths", {})
    if save_paths:
        if "csv_path" in save_paths:
            st.info(f"Saved CSV: {save_paths['csv_path']}")
        if "geojson_path" in save_paths:
            st.info(f"Saved GeoJSON: {save_paths['geojson_path']}")
        if "html_path" in save_paths:
            st.info(f"Saved interactive HTML map: {save_paths['html_path']}")


st.title("City1 v2 Proxy Population Surface")
st.caption("Proxy population surface model calibrated by official city totals.")
city_status_frame = _load_city_status_frame()
calibrated_queries = _city_queries_by_flag(city_status_frame, "supported_for_calibrated_inference")
validated_queries = _city_queries_by_flag(city_status_frame, "recommended_for_baseline_use")

if calibrated_queries:
    st.info(
        "City1 v2 currently runs in calibrated-only mode. "
        f"Calibrated cities in the reference: {len(calibrated_queries)}. "
        f"Strictly validated baseline cities: {len(validated_queries)}. "
        "Use the validated shortcut list by default or type another calibrated city manually."
    )
else:
    st.info(
        "City1 v2 currently runs in calibrated-only mode. "
        "The city must exist in data/external/city_population_reference_v2.csv."
    )

model_labels, model_mapping = _format_model_options()
if not model_labels:
    st.error("No v2 models were found in the models directory.")
    st.stop()

default_label = _default_model_label(model_mapping)
default_index = model_labels.index(default_label) if default_label in model_mapping else 0
shortcut_queries = validated_queries or calibrated_queries
default_supported_index = shortcut_queries.index("Semey, Kazakhstan") if "Semey, Kazakhstan" in shortcut_queries else 0
saved_runs = _list_saved_runs(DEFAULT_OUTPUT_DIR)
saved_run_options = ["None"] + [str(item["label"]) for item in saved_runs]

with st.sidebar:
    st.header("Run Inference")
    if shortcut_queries:
        selected_supported_city = st.selectbox(
            "Validated city shortcut",
            options=shortcut_queries,
            index=default_supported_index,
        )
    else:
        selected_supported_city = "Semey, Kazakhstan"
    place_name = st.text_input("City query", selected_supported_city)
    cell_size = st.slider("Grid cell size (meters)", min_value=250, max_value=1000, value=500, step=50)
    selected_label = st.selectbox("Model", options=model_labels, index=default_index)
    st.caption("Current production default: random_forest at 500 m.")
    save_outputs = st.checkbox("Save CSV, GeoJSON, and HTML map to data/processed/inference_runs", value=True)
    run_button = st.button("Generate Population Surface", type="primary")
    clear_button = st.button("Clear Last Result")
    st.divider()
    st.subheader("Saved Runs")
    selected_saved_run = st.selectbox("Open saved result", options=saved_run_options, index=0)
    load_saved_button = st.button("Load Saved Result")
    if calibrated_queries:
        st.caption(
            "Shortcut list uses the stricter validated baseline batch. "
            "You can still type another calibrated city manually."
        )
        with st.expander(
            f"City coverage: {len(validated_queries)} validated / {len(calibrated_queries)} calibrated"
        ):
            display_columns = [
                "city_name",
                "country",
                "population",
                "status_label",
                "validated_batch",
                "smoke_passed",
            ]
            display_frame = city_status_frame[[column for column in display_columns if column in city_status_frame.columns]].copy()
            if "population" in display_frame.columns:
                display_frame["population"] = display_frame["population"].map(
                    lambda value: f"{int(value):,}" if pd.notna(value) else ""
                )
            st.dataframe(display_frame, use_container_width=True, hide_index=True)

selected_city_status = _lookup_city_status_row(place_name, city_status_frame)
if selected_city_status is not None and not bool(selected_city_status.get("recommended_for_baseline_use", False)):
    if bool(selected_city_status.get("supported_for_calibrated_inference", False)):
        st.warning(
            "This city has an official total and can run in calibrated mode, "
            "but it is not part of the current QA-validated baseline batch."
        )

if clear_button:
    st.session_state.pop(RESULT_STATE_KEY, None)

if load_saved_button and selected_saved_run != "None":
    run_lookup = {str(item["label"]): item for item in saved_runs}
    selected_record = run_lookup.get(selected_saved_run)
    if selected_record is None:
        st.error("Saved run not found.")
    else:
        st.session_state[RESULT_STATE_KEY] = _load_saved_result(selected_record)

if run_button:
    try:
        selected_model_path = model_mapping[selected_label]
        with st.spinner("Generating features, predicting the surface, and calibrating to official totals..."):
            result = run_city_inference(
                place_name=place_name,
                model_path=selected_model_path,
                pipeline_config=FeaturePipelineConfig(grid=GridConfig(cell_size_meters=cell_size)),
            )

        saved_paths = {}
        payload = _serialize_result(result, place_name=place_name, save_paths={})
        if save_outputs:
            saved = save_city_inference_outputs(result, DEFAULT_OUTPUT_DIR)
            saved_paths = {name: str(path) for name, path in saved.items()}
            html_path = _save_interactive_map_html(payload, DEFAULT_OUTPUT_DIR)
            saved_paths["html_path"] = str(html_path)

        st.session_state[RESULT_STATE_KEY] = _serialize_result(result, place_name=place_name, save_paths=saved_paths)
    except CityInferenceError as exc:
        st.error(str(exc))
    except Exception as exc:  # pragma: no cover - Streamlit UI catch-all
        st.error(f"Unexpected error: {exc}")

result_payload = st.session_state.get(RESULT_STATE_KEY)
if result_payload:
    _render_result(result_payload)

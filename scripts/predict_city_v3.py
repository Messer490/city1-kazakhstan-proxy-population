from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path


REQUIRED_CELL_COLUMNS = (
    "run_id",
    "model_version",
    "city",
    "city_slug",
    "cell_id",
    "centroid_latitude",
    "centroid_longitude",
    "official_city_total",
    "calibrated_member_count",
    "p10",
    "p50",
    "p90",
    "uncertainty_width",
    "relative_uncertainty",
    "model_stability_score",
    "osm_completeness_score",
    "osm_support_score",
    "external_agreement_score",
    "internal_support_score",
    "confidence_score",
    "confidence_band",
    "hotspot_rank",
    "hotspot_priority_class",
    "district_support_flag",
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run frozen City1 v3 uncertainty-aware inference for a single city.")
    parser.add_argument("place_name", type=str, help="City query, e.g. 'Semey, Kazakhstan'")
    parser.add_argument(
        "--model-path",
        type=str,
        default=None,
        help="Optional path to a saved v3 ensemble_model.joblib artifact.",
    )
    parser.add_argument(
        "--totals-csv",
        type=str,
        default="data/external/city_population_reference_v2.csv",
        help="CSV with official city totals.",
    )
    parser.add_argument(
        "--output-root",
        type=str,
        default="outputs/v3_uncertainty",
        help="Root directory for frozen v3 uncertainty outputs.",
    )
    parser.add_argument(
        "--run-id",
        type=str,
        default=None,
        help="Optional explicit output run id. Defaults to the run id embedded in the selected model package.",
    )
    return parser


def _validate_output_frame(frame) -> list[str]:
    issues: list[str] = []
    missing = [column for column in REQUIRED_CELL_COLUMNS if column not in frame.columns]
    if missing:
        issues.append(f"Missing required columns: {', '.join(missing)}")
        return issues

    p10 = frame["p10"]
    p50 = frame["p50"]
    p90 = frame["p90"]
    width = frame["uncertainty_width"]
    relative = frame["relative_uncertainty"]
    confidence = frame["confidence_score"]
    bands = frame["confidence_band"].astype(str)

    if not ((p10 <= p50) & (p50 <= p90)).all():
        issues.append("Quantile ordering failed: expected p10 <= p50 <= p90 for every cell.")
    if not (width >= 0).all():
        issues.append("uncertainty_width contains negative values.")
    if not ((p90 - p10 - width).abs() <= 1e-6).all():
        issues.append("uncertainty_width is not equal to p90 - p10 for some rows.")
    if not relative.replace([float("inf"), float("-inf")], math.nan).notna().all():
        issues.append("relative_uncertainty contains non-finite values.")
    if not ((confidence >= 0) & (confidence <= 1)).all():
        issues.append("confidence_score is outside [0, 1] for some rows.")
    if not bands.isin({"high", "medium", "low"}).all():
        issues.append("confidence_band contains invalid labels.")
    if frame["hotspot_rank"].isna().any():
        issues.append("hotspot_rank contains missing values.")
    if frame["hotspot_priority_class"].isna().any():
        issues.append("hotspot_priority_class contains missing values.")

    total_gap = abs(float(frame["p50"].sum()) - float(frame["official_city_total"].iloc[0]))
    if total_gap > 1e-3:
        issues.append(f"sum_p50 drifted from official total by {total_gap:.6f}.")
    return issues


def _upsert_manifest(manifest_path: Path, payload: dict[str, object]) -> None:
    if manifest_path.exists():
        existing = json.loads(manifest_path.read_text(encoding="utf-8"))
    else:
        existing = {}

    cities_done = set(existing.get("cities_completed", []))
    for city_name in payload.get("cities_completed", []):
        cities_done.add(city_name)
    payload["cities_completed"] = sorted(cities_done)

    generated_files = set(existing.get("generated_files", []))
    for filename in payload.get("generated_files", []):
        generated_files.add(filename)
    payload["generated_files"] = sorted(generated_files)

    existing_city_outputs = dict(existing.get("city_outputs", {}))
    incoming_city_outputs = dict(payload.get("city_outputs", {}))
    existing_city_outputs.update(incoming_city_outputs)
    payload["city_outputs"] = existing_city_outputs

    merged = dict(existing)
    merged.update(payload)
    manifest_path.write_text(json.dumps(merged, indent=2, default=str), encoding="utf-8")


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

    import pandas as pd

    from src.city1.inference import (
        CityInferenceError,
        get_preferred_uncertainty_model_path,
        run_city_uncertainty_inference,
        save_city_uncertainty_outputs,
    )

    parser = build_parser()
    args = parser.parse_args()
    selected_model_path = (root / args.model_path) if args.model_path else get_preferred_uncertainty_model_path()

    try:
        result = run_city_uncertainty_inference(
            place_name=args.place_name,
            model_path=selected_model_path,
            totals_csv=root / args.totals_csv,
        )
    except CityInferenceError as exc:
        raise SystemExit(f"Inference failed: {exc}") from exc

    if args.run_id:
        result.output_frame["run_id"] = args.run_id
        result.output_gdf["run_id"] = args.run_id

    output_run_id = str(result.output_frame["run_id"].iloc[0])
    output_dir = root / args.output_root / output_run_id
    saved = save_city_uncertainty_outputs(result, output_dir)

    numeric_frame = result.output_frame.copy()
    for column in ("p10", "p50", "p90", "uncertainty_width", "relative_uncertainty", "confidence_score"):
        numeric_frame[column] = pd.to_numeric(numeric_frame[column], errors="coerce")
    issues = _validate_output_frame(numeric_frame)
    if issues:
        raise SystemExit("Inference quality gate failed:\n- " + "\n- ".join(issues))

    manifest_path = output_dir / "run_manifest.json"
    manifest_payload = {
        "run_id": output_run_id,
        "model_version": str(result.output_frame["model_version"].iloc[0]),
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "model_artifact_path": str(selected_model_path.relative_to(root)) if selected_model_path.is_relative_to(root) else str(selected_model_path),
        "totals_csv": args.totals_csv,
        "cities_completed": [str(result.output_frame["city"].iloc[0])],
        "generated_files": [path.name for path in saved.values()],
        "fallbacks_used": {
            "external_agreement_score": "0.50 neutral fallback because city-specific v3 alignment is not part of Phase 4.",
            "district_interval_coverage": "Not yet available in Phase 4 output summary.",
        },
        "summary_csv": "city_uncertainty_summary.csv",
        "city_outputs": {
            str(result.output_frame["city"].iloc[0]): {
                "official_city_total": int(result.official_population),
                "sum_p50": float(pd.to_numeric(result.output_frame["p50"], errors="coerce").sum()),
                "calibrated_member_count": int(pd.to_numeric(result.output_frame["calibrated_member_count"], errors="coerce").iloc[0]),
            }
        },
    }
    _upsert_manifest(manifest_path, manifest_payload)

    print("City1 v3 uncertainty inference completed.")
    print(f"Run id: {output_run_id}")
    print(f"City: {result.output_frame['city'].iloc[0]}")
    print(f"Official population: {result.official_population:,}")
    print(f"Raw median sum: {result.raw_prediction_sum:,.3f}")
    print(f"Calibration factor: {result.calibration_factor:.6f}")
    if result.uncertainty_interval_summary:
        print("Uncertainty summary:")
        for key, value in result.uncertainty_interval_summary.items():
            print(f"  - {key}: {value:.6f}")
    print("Saved outputs:")
    for name, path in saved.items():
        print(f"  - {name}: {path}")
    print(f"  - run_manifest_path: {manifest_path}")


if __name__ == "__main__":
    main()

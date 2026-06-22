from __future__ import annotations

import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUN_ID = "city1_v3_rf500m_e20_20260618T040646Z"


def check(path: Path) -> str:
    return "FOUND" if path.exists() else "MISSING"


def read_csv_head(path: Path, limit: int = 3) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        rows = []
        for idx, row in enumerate(reader):
            rows.append(row)
            if idx + 1 >= limit:
                break
        return rows


def main() -> int:
    paths = {
        "city_summary": ROOT / "outputs" / "v3_uncertainty" / RUN_ID / "city_uncertainty_summary.csv",
        "hotspot_city_summary": ROOT / "reports" / "hotspot_prioritization_v3" / RUN_ID / "hotspot_city_summary.csv",
        "confidence_band_validation_summary": ROOT / "reports" / "uncertainty_validation_v3" / RUN_ID / "confidence_band_validation_summary.csv",
        "hotspot_stability_summary": ROOT / "reports" / "uncertainty_validation_v3" / RUN_ID / "hotspot_stability_summary.csv",
        "interval_coverage_weak_target": ROOT / "reports" / "uncertainty_validation_v3" / RUN_ID / "interval_coverage_weak_target.csv",
        "city_status_registry": ROOT / "data" / "external" / "city_status_registry_v2.csv",
        "city_population_reference": ROOT / "data" / "external" / "city_population_reference_v2.csv",
    }

    print("City1 v4 artifact inspection")
    print(f"Repository root: {ROOT}")
    print(f"Frozen V3 run: {RUN_ID}")
    print()

    for label, path in paths.items():
        print(f"{label:32} {check(path)}  {path}")

    print()
    print("Sample rows")
    for label, path in [
        ("city_summary", paths["city_summary"]),
        ("hotspot_city_summary", paths["hotspot_city_summary"]),
        ("confidence_band_validation_summary", paths["confidence_band_validation_summary"]),
    ]:
        rows = read_csv_head(path)
        print(f"- {label}: {len(rows)} preview rows")
        for row in rows:
            print(f"  {row}")

    manifest_path = ROOT / "reports" / "paper_v3_uncertainty" / RUN_ID / "freeze_manifest.json"
    if manifest_path.exists():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            print()
            print("freeze_manifest.json loaded")
            print(json.dumps({k: manifest.get(k) for k in ["run_id", "commit", "created_at"] if k in manifest}, indent=2))
        except Exception as exc:
            print()
            print(f"freeze_manifest.json read failed: {exc}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

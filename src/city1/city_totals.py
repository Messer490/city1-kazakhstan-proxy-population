from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import unicodedata

import pandas as pd


def normalize_city_name(value: str) -> str:
    text = value.strip().lower()
    text = re.sub(r"^\d+[_\-\s]+", "", text)
    text = text.replace("_", " ").replace("-", " ")
    text = text.replace("ё", "е")
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def city_name_from_filename(path: str | Path) -> str:
    return normalize_city_name(Path(path).stem.strip("_"))


def _parse_population(raw_value: str) -> int | None:
    cleaned = raw_value.replace("\t", "").replace(" ", "").strip().strip('"')
    if not cleaned:
        return None

    try:
        population = int(float(cleaned))
    except ValueError:
        return None

    if population <= 0:
        return None
    return population


@dataclass(frozen=True)
class CityTotalsLookup:
    frame: pd.DataFrame
    warnings: tuple[str, ...] = ()

    def get_population(self, city_name: str) -> int | None:
        normalized = normalize_city_name(city_name)
        match = self.frame.loc[self.frame["normalized_city_name"] == normalized, "population"]
        if match.empty:
            return None
        return int(match.iloc[0])


def _load_structured_city_totals(path: Path) -> CityTotalsLookup:
    frame = pd.read_csv(path)
    required_columns = {"city_name", "normalized_city_name", "population"}
    missing = required_columns.difference(frame.columns)
    if missing:
        raise ValueError(f"Structured city totals file is missing columns: {sorted(missing)}")

    cleaned = frame.copy()
    cleaned["normalized_city_name"] = cleaned["normalized_city_name"].astype(str).map(normalize_city_name)
    cleaned["population"] = pd.to_numeric(cleaned["population"], errors="coerce")
    cleaned = cleaned.dropna(subset=["normalized_city_name", "population"])
    cleaned = cleaned.loc[cleaned["population"] > 0].copy()
    cleaned["population"] = cleaned["population"].astype(int)
    cleaned = cleaned.sort_values(["normalized_city_name", "population"], ascending=[True, False])
    cleaned = cleaned.drop_duplicates(subset=["normalized_city_name"], keep="first").reset_index(drop=True)

    return CityTotalsLookup(frame=cleaned)


def load_city_totals(path: str | Path) -> CityTotalsLookup:
    totals_path = Path(path)
    header = totals_path.read_text(encoding="utf-8", errors="replace").splitlines()[0].lower()
    if "normalized_city_name" in header and "population" in header:
        return _load_structured_city_totals(totals_path)

    warnings: list[str] = []
    records: dict[str, dict[str, object]] = {}

    with totals_path.open("r", encoding="utf-8", errors="replace") as handle:
        lines = handle.readlines()

    for line_number, raw_line in enumerate(lines[1:], start=2):
        line = raw_line.strip()
        if not line:
            continue

        cleaned = line.strip().strip('"')
        cleaned = cleaned.replace("\t", "")

        if "," not in cleaned:
            warnings.append(f"Line {line_number}: could not split city/population -> {line!r}")
            continue

        city_raw, population_raw = cleaned.rsplit(",", 1)
        city = city_raw.strip()
        normalized = normalize_city_name(city)
        population = _parse_population(population_raw)

        if not normalized:
            warnings.append(f"Line {line_number}: empty city name -> {line!r}")
            continue

        if population is None:
            warnings.append(f"Line {line_number}: invalid or non-positive population for {city!r}")
            continue

        existing = records.get(normalized)
        if existing is None or population > int(existing["population"]):
            records[normalized] = {
                "city_name": city,
                "normalized_city_name": normalized,
                "population": population,
                "source_path": str(totals_path),
            }

    frame = pd.DataFrame(records.values())
    if frame.empty:
        raise ValueError(f"No valid city totals were parsed from {totals_path}")

    frame = frame.sort_values("normalized_city_name").reset_index(drop=True)
    return CityTotalsLookup(frame=frame, warnings=tuple(warnings))

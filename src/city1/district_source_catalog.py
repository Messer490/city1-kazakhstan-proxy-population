from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Iterable

import pandas as pd
import requests
from bs4 import BeautifulSoup

from .city_totals import normalize_city_name
from .paths import EXTERNAL_DATA_DIR


DISTRICT_TOKEN = "\u0440\u0430\u0439\u043e\u043d"
POPULATION_TOKENS = (
    "\u0447\u0438\u0441\u043b",
    "\u043d\u0430\u0441\u0435\u043b",
)


@dataclass(frozen=True)
class DistrictSourceCity:
    city_name: str
    catalog_url: str
    city_query: str


DISTRICT_SOURCE_CITIES: tuple[DistrictSourceCity, ...] = (
    DistrictSourceCity(
        city_name="Almaty",
        catalog_url="https://stat.gov.kz/ru/region/almaty/spreadsheets/",
        city_query="Almaty, Kazakhstan",
    ),
    DistrictSourceCity(
        city_name="Astana",
        catalog_url="https://stat.gov.kz/ru/region/astana/spreadsheets/",
        city_query="Astana, Kazakhstan",
    ),
    DistrictSourceCity(
        city_name="Shymkent",
        catalog_url="https://stat.gov.kz/ru/region/shymkent/spreadsheets/",
        city_query="Shymkent, Kazakhstan",
    ),
)

DEFAULT_DISTRICT_SOURCE_CATALOG_PATH = EXTERNAL_DATA_DIR / "district_population_table_catalog_v2.csv"


def _normalize_label(value: str) -> str:
    return " ".join(str(value).strip().lower().split())


def extract_district_population_options_from_html(
    html_text: str,
    *,
    city_name: str,
    catalog_url: str,
    city_query: str,
) -> pd.DataFrame:
    soup = BeautifulSoup(html_text, "html.parser")
    select = soup.find("select", {"name": "name"})
    if select is None:
        raise ValueError("Could not find the district source select[name='name'] in the catalog page.")

    rows: list[dict[str, object]] = []
    normalized_city_name = normalize_city_name(city_name)

    for option in select.find_all("option"):
        option_id = str(option.get("value", "")).strip()
        option_label = " ".join(option.get_text(" ", strip=True).split())
        normalized_label = _normalize_label(option_label)

        if not option_id or not normalized_label:
            continue
        if DISTRICT_TOKEN not in normalized_label:
            continue
        if not any(token in normalized_label for token in POPULATION_TOKENS):
            continue

        rows.append(
            {
                "city_name": city_name,
                "normalized_city_name": normalized_city_name,
                "city_query": city_query,
                "catalog_url": catalog_url,
                "option_id": option_id,
                "option_label": option_label,
            }
        )

    return pd.DataFrame(rows)


def build_district_population_source_catalog(
    *,
    cities: Iterable[DistrictSourceCity] = DISTRICT_SOURCE_CITIES,
    session: requests.Session | None = None,
) -> pd.DataFrame:
    active_session = session or requests.Session()
    active_session.headers.update({"User-Agent": "Mozilla/5.0"})

    frames: list[pd.DataFrame] = []
    for city in cities:
        response = active_session.get(city.catalog_url, timeout=120)
        response.raise_for_status()
        frame = extract_district_population_options_from_html(
            response.text,
            city_name=city.city_name,
            catalog_url=city.catalog_url,
            city_query=city.city_query,
        )
        frames.append(frame)

    if not frames:
        return pd.DataFrame(
            columns=[
                "city_name",
                "normalized_city_name",
                "city_query",
                "catalog_url",
                "option_id",
                "option_label",
            ]
        )

    return pd.concat(frames, ignore_index=True)


def save_district_population_source_catalog(
    frame: pd.DataFrame,
    *,
    output_path: str | Path = DEFAULT_DISTRICT_SOURCE_CATALOG_PATH,
) -> Path:
    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    ordered_columns = [
        "city_name",
        "normalized_city_name",
        "city_query",
        "catalog_url",
        "option_id",
        "option_label",
    ]
    available_columns = [column for column in ordered_columns if column in frame.columns]
    frame.loc[:, available_columns].to_csv(destination, index=False)
    return destination

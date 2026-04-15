from __future__ import annotations

import sys
from pathlib import Path

import requests


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

    from src.city1.kazakhstan_official_totals import WORKBOOK_CITY_SOURCES

    output_dir = root / "data" / "external" / "region_population_tables"
    output_dir.mkdir(parents=True, exist_ok=True)

    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0"})

    seen_urls: set[str] = set()
    for source in WORKBOOK_CITY_SOURCES:
        if source.source_url in seen_urls:
            continue
        seen_urls.add(source.source_url)

        response = session.get(source.source_url, timeout=120)
        response.raise_for_status()

        output_path = output_dir / source.cache_filename
        output_path.write_bytes(response.content)
        print(f"Saved {output_path} ({len(response.content)} bytes)")


if __name__ == "__main__":
    main()

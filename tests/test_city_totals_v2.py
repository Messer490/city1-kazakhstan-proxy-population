from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from src.city1.city_totals import load_city_totals


class StructuredCityTotalsTestCase(unittest.TestCase):
    def test_load_city_totals_supports_structured_reference_file(self) -> None:
        content = (
            "city_name,normalized_city_name,population,source_tier\n"
            "Almaty,almaty,2351424,official\n"
            "Astana,astana,1649242,official\n"
        )
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "city_population_reference_v2.csv"
            path.write_text(content, encoding="utf-8")

            lookup = load_city_totals(path)
            self.assertEqual(lookup.get_population("Almaty"), 2351424)
            self.assertEqual(lookup.get_population("Astana"), 1649242)


if __name__ == "__main__":
    unittest.main()

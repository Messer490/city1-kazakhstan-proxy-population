from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from src.city1.city_totals import city_name_from_filename, load_city_totals, normalize_city_name


class CityTotalsTestCase(unittest.TestCase):
    def test_normalize_city_name(self) -> None:
        self.assertEqual(normalize_city_name("Ust-Kamenogorsk"), "ust kamenogorsk")
        self.assertEqual(city_name_from_filename("1_ust-kamenogorsk_.csv"), "ust kamenogorsk")

    def test_load_city_totals_recovers_broken_almaty_line(self) -> None:
        content = 'City,Population\n"Almaty,\t2292333"\nShymkent,0\nMoscow,13100000\n'
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "totals.csv"
            path.write_text(content, encoding="utf-8")

            lookup = load_city_totals(path)
            self.assertEqual(lookup.get_population("Almaty"), 2292333)
            self.assertIsNone(lookup.get_population("Shymkent"))
            self.assertEqual(lookup.get_population("Moscow"), 13100000)


if __name__ == "__main__":
    unittest.main()

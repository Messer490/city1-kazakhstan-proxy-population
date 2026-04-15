from __future__ import annotations

import unittest
from pathlib import Path

from src.city1.kazakhstan_official_totals import build_verified_kazakhstan_city_records


class KazakhstanOfficialTotalsTestCase(unittest.TestCase):
    def test_extracts_verified_city_totals_from_cached_workbooks(self) -> None:
        records, warnings = build_verified_kazakhstan_city_records(
            Path("data/external/region_population_tables")
        )
        self.assertEqual(warnings, ())

        lookup = {record["normalized_city_name"]: record["population"] for record in records}
        self.assertEqual(lookup["almaty"], 2351424)
        self.assertEqual(lookup["astana"], 1649242)
        self.assertEqual(lookup["shymkent"], 1298279)
        self.assertEqual(lookup["semey"], 315382)
        self.assertEqual(lookup["taraz"], 488133)
        self.assertEqual(lookup["uralsk"], 372742)
        self.assertEqual(lookup["petropavlovsk"], 222039)
        self.assertEqual(lookup["ust kamenogorsk"], 380829)


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import unittest

import pandas as pd

from src.city1.hotspot_prioritization import build_hotspot_priority_table


class HotspotPrioritizationTestCase(unittest.TestCase):
    def test_build_hotspot_priority_table_splits_by_confidence_band(self) -> None:
        frame = pd.DataFrame(
            {
                "cell_id": ["Z1", "Z2", "Z3", "Z4"],
                "p50": [10.0, 20.0, 30.0, 40.0],
                "confidence_band": ["low", "medium", "high", "high"],
            }
        )
        hotspots, summary = build_hotspot_priority_table(frame, hotspot_quantile=0.50)
        self.assertGreaterEqual(len(hotspots), 2)
        self.assertIn("hotspot_priority_class", hotspots.columns)
        self.assertGreaterEqual(summary.high_priority_count, 1)


if __name__ == "__main__":
    unittest.main()

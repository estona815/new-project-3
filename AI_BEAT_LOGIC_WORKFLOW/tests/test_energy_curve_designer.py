from __future__ import annotations

import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from energy_curve_designer import design_energy_curve  # noqa: E402


class EnergyCurveDesignerTests(unittest.TestCase):
    def test_under_2min_uses_requested_rescue_timing(self) -> None:
        curve = design_energy_curve("under_2min")

        self.assertEqual(curve["length_mode"], "under_2min")
        self.assertEqual(curve["target_duration_seconds"], 100.0)
        self.assertEqual(curve["curve"][0]["name"], "intro_hook_hint")
        self.assertEqual(curve["curve"][0]["duration"], 4.0)
        self.assertEqual(curve["curve"][1]["name"], "main_hook")
        self.assertEqual(curve["curve"][1]["start_time"], 4.0)

    def test_short_form_places_hook_within_first_15_seconds(self) -> None:
        for mode in ("reels_15sec", "short_30sec"):
            curve = design_energy_curve(mode)
            self.assertTrue(curve["hook_within_first_15_seconds"])
            self.assertLessEqual(min(item["start_time"] for item in curve["curve"] if "hook" in item["name"]), 4.0)


if __name__ == "__main__":
    unittest.main()

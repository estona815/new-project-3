from __future__ import annotations

import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from stem_mix_autopilot import build_stem_mix_plan  # noqa: E402


class StemMixAutopilotTests(unittest.TestCase):
    def test_stems_allow_more_direct_balancing(self) -> None:
        plan = build_stem_mix_plan(True)

        self.assertTrue(plan["active"])
        self.assertTrue(plan["more_direct_balancing_allowed"])
        self.assertIn("drum_bus", plan)
        self.assertIn("mono sub", plan["bass_808_bus"])
        self.assertIn("sidechain", plan["bass_808_bus"])

    def test_no_stems_remains_manual_guidance(self) -> None:
        plan = build_stem_mix_plan(False)

        self.assertFalse(plan["active"])
        self.assertFalse(plan["more_direct_balancing_allowed"])
        self.assertTrue(plan["limitations"])


if __name__ == "__main__":
    unittest.main()

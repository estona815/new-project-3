from __future__ import annotations

import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from section_progression_planner import plan_section_progression  # noqa: E402


class SectionProgressionPlannerTests(unittest.TestCase):
    def test_reels_plan_has_immediate_hook_and_no_intro(self) -> None:
        plan = plan_section_progression(length_mode="reels_15sec", genre_mode="digicore")

        self.assertEqual(plan["schema_version"], "section_progression_guide.v1")
        self.assertEqual(plan["sections"][0]["name"], "hook")
        self.assertLessEqual(plan["sections"][0]["start"], 0.0)
        self.assertIn("No weak intro.", plan["rules"])

    def test_full_song_has_expected_macro_sections(self) -> None:
        plan = plan_section_progression(length_mode="full_song", genre_mode="hip_hop")
        names = [section["name"] for section in plan["sections"]]

        self.assertEqual(names[:4], ["intro", "hook", "verse", "pre"])
        self.assertIn("final_hook", names)


if __name__ == "__main__":
    unittest.main()

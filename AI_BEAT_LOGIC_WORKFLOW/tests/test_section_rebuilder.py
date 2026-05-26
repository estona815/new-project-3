from __future__ import annotations

import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from section_rebuilder import rebuild_sections  # noqa: E402


class SectionRebuilderTests(unittest.TestCase):
    def test_under_2min_rebuilds_real_song_form(self) -> None:
        sections = rebuild_sections(
            length_mode="under_2min",
            source_problem={"missing_lead": True, "missing_hook": True, "weird_vocal_texture": True},
            hook_plan={"usable_sample_motif_candidates": 1},
        )

        self.assertEqual([section["name"] for section in sections], [
            "intro_hook_hint",
            "main_hook",
            "verse_groove",
            "hook_return",
            "breakdown_filtered_lead",
            "final_hook",
            "clean_outro_or_loop",
        ])
        self.assertEqual(sections[0]["start_time"], 0.0)
        self.assertEqual(sections[1]["start_time"], 4.0)
        self.assertTrue(any("Create and feature a new lead" in item for item in sections[1]["instructions"]))
        self.assertTrue(any("Push vocal texture back" in item for item in sections[1]["instructions"]))

    def test_reels_has_immediate_hook(self) -> None:
        sections = rebuild_sections(length_mode="reels_15sec")

        self.assertEqual(sections[0]["name"], "main_hook")
        self.assertEqual(sections[0]["start_time"], 0.0)
        self.assertLessEqual(sections[-1]["start_time"] + sections[-1]["duration"], 15.0)


if __name__ == "__main__":
    unittest.main()

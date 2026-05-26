from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from bassline_idea_generator import build_bassline_guide, generate_bassline_ideas  # noqa: E402


class BasslineIdeaGeneratorTests(unittest.TestCase):
    def test_808_is_strong_but_mono_centered(self) -> None:
        ideas = generate_bassline_ideas(
            style_target="commercial_digicore_hyperpop",
            rough_request="808 강하게",
            chord_options=[{"roman": ["i", "VI"]}],
            key={"confidence": "medium"},
        )

        self.assertEqual(ideas[0]["tone"], "strong_controlled_808")
        self.assertTrue(ideas[0]["mono_center_required"])
        self.assertEqual(ideas[0]["confidence"], "medium")

    def test_bassline_guide_blocks_exact_copy_and_false_replacement_claims(self) -> None:
        guide = build_bassline_guide(rough_request="웨스트우드 킥 베이스 느낌만", key={"confidence": "low"})
        text = json.dumps(guide).lower()

        self.assertFalse(guide["safety"]["exact_reference_copy"])
        self.assertIn("no true 808 replacement", text)
        self.assertIn("do not copy exact reference basslines", text)


if __name__ == "__main__":
    unittest.main()

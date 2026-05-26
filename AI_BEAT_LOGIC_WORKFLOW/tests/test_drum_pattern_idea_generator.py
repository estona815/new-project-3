from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from drum_pattern_idea_generator import build_drum_pattern_guide, generate_drum_ideas  # noqa: E402


class DrumPatternIdeaGeneratorTests(unittest.TestCase):
    def test_hyperpop_drums_are_energetic_but_controlled(self) -> None:
        ideas = generate_drum_ideas(
            style_target="hyperpop",
            rough_request="릴스 첫 15초 훅",
            sample_analysis={"transient_onset": {"onset_density": 3.0}},
            tempo={"confidence": "medium"},
        )

        self.assertEqual(ideas[0]["feel"], "energetic")
        self.assertEqual(ideas[0]["variation"], "micro-fill before hook")
        self.assertEqual(ideas[0]["confidence"], "medium")

    def test_drum_guide_has_copy_and_rewrite_safety(self) -> None:
        guide = build_drum_pattern_guide(style_target="hip_hop")
        text = json.dumps(guide).lower()

        self.assertFalse(guide["safety"]["exact_reference_copy"])
        self.assertIn("must not clone exact reference patterns", text)
        self.assertIn("no rendered drums", text)


if __name__ == "__main__":
    unittest.main()

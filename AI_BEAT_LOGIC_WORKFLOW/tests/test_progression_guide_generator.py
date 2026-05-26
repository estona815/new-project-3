from __future__ import annotations

import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from progression_guide_generator import generate_chord_progression_guide  # noqa: E402


class ProgressionGuideGeneratorTests(unittest.TestCase):
    def test_low_key_confidence_requires_ear_confirmation(self) -> None:
        guide = generate_chord_progression_guide({"tonal": {"estimated_key": None, "confidence": "low"}})

        self.assertFalse(guide["progression_allowed"])
        self.assertIn("confirm by ear", guide["instruction"])
        self.assertIn("No exact song progression copying", guide["copying_policy"])

    def test_medium_key_confidence_allows_options_without_copy_claim(self) -> None:
        guide = generate_chord_progression_guide({"tonal": {"estimated_key": "F# minor", "confidence": "medium"}})

        self.assertTrue(guide["progression_allowed"])
        self.assertEqual(guide["estimated_key"], "F# minor")
        self.assertTrue(guide["options"])


if __name__ == "__main__":
    unittest.main()

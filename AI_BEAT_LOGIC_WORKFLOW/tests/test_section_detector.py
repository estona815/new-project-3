from __future__ import annotations

import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_DIR))

from section_detector import detect_sections, energy_rank  # noqa: E402


class SectionDetectorTests(unittest.TestCase):
    def test_detect_sections_labels_intro_hook_and_outro(self) -> None:
        features = [
            {"start": 0.0, "end": 4.0, "energy": 0.01, "onset_density": 0.0, "novelty": 0.01},
            {"start": 4.0, "end": 8.0, "energy": 0.06, "onset_density": 0.002, "novelty": 0.05},
            {"start": 8.0, "end": 12.0, "energy": 0.2, "onset_density": 0.02, "novelty": 0.14},
            {"start": 12.0, "end": 16.0, "energy": 0.01, "onset_density": 0.0, "novelty": 0.01},
        ]

        sections = detect_sections(features, 16.0)
        names = [item["name"] for item in sections]

        self.assertIn("intro", names)
        self.assertTrue(any(name in names for name in ("hook", "drop")))
        self.assertIn("outro", names)

    def test_energy_rank_is_bounded_one_to_five(self) -> None:
        self.assertEqual(energy_rank(0.0, 1.0), 1)
        self.assertEqual(energy_rank(1.0, 1.0), 5)


if __name__ == "__main__":
    unittest.main()

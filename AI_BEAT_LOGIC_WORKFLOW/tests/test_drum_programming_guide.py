from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from drum_programming_guide import generate_drum_programming_guide  # noqa: E402


class DrumProgrammingGuideTests(unittest.TestCase):
    def test_drum_guide_blocks_generic_and_random_glitch(self) -> None:
        guide = generate_drum_programming_guide(genre_mode="commercial_digicore_hyperpop", length_mode="short_30sec")
        text = json.dumps(guide).lower()

        self.assertEqual(guide["schema_version"], "drum_programming_guide.v1")
        self.assertIn("avoid generic trap", text)
        self.assertIn("avoid random ai glitch", text)
        self.assertIn("no true drum rewrite is claimed", text)


if __name__ == "__main__":
    unittest.main()

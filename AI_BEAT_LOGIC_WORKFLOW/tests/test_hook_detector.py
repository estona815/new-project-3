from __future__ import annotations

import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_DIR))

from hook_detector import detect_hook_candidates, reels_hook_region  # noqa: E402


class HookDetectorTests(unittest.TestCase):
    def test_detect_hook_candidates_prefers_high_energy_onset_region(self) -> None:
        features = [
            {"start": 0.0, "end": 4.0, "energy": 0.01, "onset_density": 0.001},
            {"start": 8.0, "end": 16.0, "energy": 0.2, "onset_density": 0.03},
            {"start": 24.0, "end": 32.0, "energy": 0.08, "onset_density": 0.004},
        ]

        hooks = detect_hook_candidates(features, 32.0)
        reels = reels_hook_region(hooks)

        self.assertTrue(hooks)
        self.assertEqual(hooks[0]["start"], 8.0)
        self.assertGreater(hooks[0]["score"], 0.5)
        self.assertIsNotNone(reels)
        self.assertEqual(reels["source"], "best hook candidate")


if __name__ == "__main__":
    unittest.main()

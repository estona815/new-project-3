from __future__ import annotations

import math
import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_DIR))

from sample_loop_detector import detect_loop_candidates  # noqa: E402


class SampleLoopDetectorTests(unittest.TestCase):
    def test_loop_candidate_schema_includes_boundary_click_risk(self) -> None:
        sample_rate = 48000
        duration = 4.0
        samples = [math.sin(2.0 * math.pi * 220.0 * index / sample_rate) * 0.3 for index in range(int(sample_rate * duration))]
        tempo = {"bpm": 120.0, "half_double_ambiguity": False}

        loops = detect_loop_candidates(samples, sample_rate, duration, tempo)

        self.assertTrue(loops)
        first = loops[0]
        self.assertIn("start", first)
        self.assertIn("end", first)
        self.assertIn("estimated_bars", first)
        self.assertIn("loop_score", first)
        self.assertIn("boundary_click_risk", first)
        self.assertIn(first["confidence"], {"low", "medium"})

    def test_weak_tempo_uses_low_confidence_fallback(self) -> None:
        sample_rate = 48000
        samples = [0.0 for _ in range(sample_rate)]

        loops = detect_loop_candidates(samples, sample_rate, 1.0, {"bpm": None})

        self.assertEqual(len(loops), 1)
        self.assertEqual(loops[0]["confidence"], "low")
        self.assertIsNone(loops[0]["estimated_bars"])


if __name__ == "__main__":
    unittest.main()

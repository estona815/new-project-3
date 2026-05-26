from __future__ import annotations

import math
import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_DIR))

from tempo_key_estimation import estimate_bpm, estimate_key  # noqa: E402


class TempoKeyEstimationTests(unittest.TestCase):
    def test_periodic_onsets_estimate_bpm_candidates_and_ambiguity(self) -> None:
        onsets = [index * 0.5 for index in range(16)]

        result = estimate_bpm(onsets, duration_seconds=8.0)

        self.assertEqual(result["bpm"], 120.0)
        self.assertIn(60.0, result["bpm_candidates"])
        self.assertIn(120.0, result["bpm_candidates"])
        self.assertEqual(result["double_time_bpm"], None)
        self.assertIn(result["confidence"], {"medium", "high"})
        self.assertIn("half_time_bpm", result)

    def test_short_sample_never_gets_high_confidence_bpm_or_key(self) -> None:
        sample_rate = 48000
        samples = [math.sin(2.0 * math.pi * 220.0 * index / sample_rate) * 0.4 for index in range(sample_rate)]

        bpm = estimate_bpm([0.0, 0.5, 1.0, 1.5], duration_seconds=1.8)
        key = estimate_key(samples, sample_rate, duration_seconds=1.0)

        self.assertNotEqual(bpm["confidence"], "high")
        self.assertEqual(key["confidence"], "low")
        self.assertIsNone(key["estimated_key"])

    def test_tonal_heuristic_returns_pitch_center_with_method_note(self) -> None:
        sample_rate = 48000
        samples = [math.sin(2.0 * math.pi * 220.0 * index / sample_rate) * 0.4 for index in range(sample_rate * 3)]

        key = estimate_key(samples, sample_rate, duration_seconds=3.0)

        self.assertIn("estimated_tonic_or_pitch_center", key)
        self.assertTrue(key["key_candidates"])
        self.assertIn("heuristic", key["method"])


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_DIR))

from sample_motif_detector import detect_motif_candidates  # noqa: E402


class SampleMotifDetectorTests(unittest.TestCase):
    def test_motif_detector_returns_hook_and_repetition_schema(self) -> None:
        frames = [
            {"start": 0.0, "end": 0.5, "rms": 0.02, "brightness_ratio": 0.2},
            {"start": 0.5, "end": 1.0, "rms": 0.2, "brightness_ratio": 0.6},
            {"start": 1.0, "end": 1.5, "rms": 0.021, "brightness_ratio": 0.22},
            {"start": 1.5, "end": 2.0, "rms": 0.2, "brightness_ratio": 0.61},
        ]

        result = detect_motif_candidates(frames, duration_seconds=4.0)

        self.assertIn("hook_motif_candidates", result)
        self.assertIn("repeated_energy_spectral_contour_regions", result)
        self.assertIn("strong_melodic_or_rhythmic_regions", result)
        self.assertTrue(result["hook_motif_candidates"])
        self.assertIn("not melody transcription", result["method"])

    def test_empty_frames_fail_closed(self) -> None:
        result = detect_motif_candidates([], duration_seconds=0.0)

        self.assertEqual(result["hook_motif_candidates"], [])
        self.assertIn("No frame features", result["method"])


if __name__ == "__main__":
    unittest.main()

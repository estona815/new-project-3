from __future__ import annotations

import sys
import unittest
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from dynamic_eq import apply_vocal_triggered_beat_ducking  # noqa: E402
from masking_analysis import masking_score, vocal_to_beat_masking_score  # noqa: E402


class MaskingAnalysisTests(unittest.TestCase):
    def test_masking_score_reports_core_bands(self) -> None:
        sr = 48000
        t = np.arange(sr) / sr
        vocal = (0.3 * np.sin(2 * np.pi * 2500 * t)).astype(np.float32)[:, None]
        beat = (0.1 * np.sin(2 * np.pi * 2500 * t)).astype(np.float32)[:, None]
        score = masking_score(vocal, beat, sr)
        self.assertLess(score["presence_1500_4500"], 0)
        self.assertIn("interpretation", score)

    def test_masking_score_improves_after_vocal_triggered_beat_ducking(self) -> None:
        sr = 48000
        t = np.arange(sr) / sr
        vocal = (0.18 * np.sin(2 * np.pi * 2400 * t)).astype(np.float32)[:, None]
        beat = (0.42 * np.sin(2 * np.pi * 2400 * t) + 0.2 * np.sin(2 * np.pi * 260 * t)).astype(np.float32)[:, None]
        before = vocal_to_beat_masking_score(vocal, beat, sr)
        ducked, report = apply_vocal_triggered_beat_ducking(beat, vocal, sr, include_harsh_band=False)
        after = vocal_to_beat_masking_score(vocal, ducked, sr)
        self.assertGreater(after["score_db"], before["score_db"])
        self.assertGreater(report["masking_score_after"]["score_db"], report["masking_score_before"]["score_db"])


if __name__ == "__main__":
    unittest.main()

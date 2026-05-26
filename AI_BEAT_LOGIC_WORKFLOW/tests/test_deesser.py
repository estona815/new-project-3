from __future__ import annotations

import sys
import unittest
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from audio_metrics import bandpass, rms  # noqa: E402
from deesser import deess  # noqa: E402


class DeesserTests(unittest.TestCase):
    def test_deesser_reduces_sibilance_band(self) -> None:
        sr = 48000
        t = np.arange(sr) / sr
        audio = (0.15 * np.sin(2 * np.pi * 400 * t) + 0.35 * np.sin(2 * np.pi * 7500 * t)).astype(np.float32)[:, None]
        out, report = deess(audio, sr, threshold_db=-42, range_db=-5)
        self.assertLess(rms(bandpass(out, 6500, 9000, sr)), rms(bandpass(audio, 6500, 9000, sr)))
        self.assertLess(report["max_gain_reduction_db"], 0)

    def test_deesser_preserves_air_more_than_sibilance(self) -> None:
        sr = 48000
        t = np.arange(sr) / sr
        audio = (0.16 * np.sin(2 * np.pi * 500 * t) + 0.28 * np.sin(2 * np.pi * 7200 * t) + 0.06 * np.sin(2 * np.pi * 12000 * t)).astype(np.float32)[:, None]
        _out, report = deess(audio, sr, threshold_db=-44, range_db=-5)
        self.assertLess(report["sibilance_delta_db"], -1.0)
        self.assertGreater(report["air_delta_db"], report["sibilance_delta_db"])


if __name__ == "__main__":
    unittest.main()

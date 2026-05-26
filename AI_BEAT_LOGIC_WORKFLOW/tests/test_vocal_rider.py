from __future__ import annotations

import sys
import unittest
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from audio_metrics import rms  # noqa: E402
from vocal_rider import VocalRiderSettings, phrase_window_rms, ride_vocal  # noqa: E402


class VocalRiderTests(unittest.TestCase):
    def test_rider_lifts_quiet_tail_relative_to_loud_head(self) -> None:
        sr = 48000
        t = np.arange(sr) / sr
        first = 0.35 * np.sin(2 * np.pi * 220 * t[: sr // 2])
        second = 0.05 * np.sin(2 * np.pi * 220 * t[: sr // 2])
        audio = np.concatenate((first, second)).astype(np.float32)[:, None]
        out, report = ride_vocal(audio, sr, target_db=-18)
        self.assertGreater(rms(out[sr // 2 :]), rms(audio[sr // 2 :]))
        self.assertLess(report["gain_envelope_db_summary"]["min"], 0)

    def test_vocal_rider_stabilizes_phrase_rms(self) -> None:
        sr = 48000
        t = np.arange(sr) / sr
        phrase_a = 0.35 * np.sin(2 * np.pi * 220 * t[: sr // 2])
        phrase_b = 0.05 * np.sin(2 * np.pi * 220 * t[: sr // 2])
        audio = np.concatenate((phrase_a, phrase_b)).astype(np.float32)[:, None]
        out, report = ride_vocal(audio, sr, settings=VocalRiderSettings(target_db=-20, window_ms=250, smoothing_ms=80))
        before = phrase_window_rms(audio, sr, 500, -60)
        after = phrase_window_rms(out, sr, 500, -60)
        before_spread = np.std([float(item["rms_dbfs"]) for item in before if bool(item["active"])])
        after_spread = np.std([float(item["rms_dbfs"]) for item in after if bool(item["active"])])
        self.assertLess(after_spread, before_spread)
        self.assertIn("gain_envelope_linear_summary", report)


if __name__ == "__main__":
    unittest.main()

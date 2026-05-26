from __future__ import annotations

import sys
import unittest
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from audio_metrics import bandpass, clipping_count, rms  # noqa: E402
from delay_fx import DelaySettings, delay_frames_for_settings, delay_send  # noqa: E402
from reverb_fx import SchroederReverbSettings, schroeder_reverb, small_room  # noqa: E402


class ReverbFxTests(unittest.TestCase):
    def test_schroeder_reverb_tail_exists_and_does_not_clip(self) -> None:
        sr = 48000
        impulse = np.zeros((sr // 2, 1), dtype=np.float32)
        impulse[0] = 1.0
        out, report = schroeder_reverb(impulse, sr, SchroederReverbSettings(wet=0.12), length=sr * 2)
        self.assertEqual(out.shape, (sr * 2, 2))
        self.assertGreater(float(np.max(np.abs(out[sr // 2 :]))), 0.0)
        self.assertEqual(clipping_count(out), 0)
        self.assertEqual(report["type"], "schroeder_reverb")

    def test_reverb_return_highpass_removes_low_mud(self) -> None:
        sr = 48000
        t = np.arange(sr) / sr
        low = np.sin(2 * np.pi * 80 * t).astype(np.float32)[:, None] * 0.5
        muddy, _ = schroeder_reverb(low, sr, SchroederReverbSettings(wet=0.3, return_highpass_hz=40.0), length=sr * 2)
        cleaned, _report = schroeder_reverb(low, sr, SchroederReverbSettings(wet=0.3, return_highpass_hz=260.0), length=sr * 2)
        self.assertLess(rms(bandpass(cleaned, 40, 140, sr)), rms(bandpass(muddy, 40, 140, sr)) * 0.35)

    def test_ducking_lowers_reverb_under_active_vocal(self) -> None:
        sr = 48000
        t = np.arange(sr) / sr
        vocal = np.zeros((sr, 1), dtype=np.float32)
        vocal[: sr // 2, 0] = np.sin(2 * np.pi * 220 * t[: sr // 2]) * 0.3
        ducked, report = schroeder_reverb(vocal, sr, SchroederReverbSettings(wet=0.4, duck_range_db=-6.0), duck_source=vocal, length=sr)
        self.assertLess(rms(ducked[: sr // 2]), rms(ducked[sr // 2 :]) + 0.02)
        self.assertLess(report["ducking"]["duck_range_db"], 0)

    def test_delay_tempo_timing_correct(self) -> None:
        sr = 48000
        settings = DelaySettings(mode="tempo", beat_fraction=0.5)
        self.assertEqual(delay_frames_for_settings(sr, 120.0, settings), 12000)
        impulse = np.zeros((sr // 2, 1), dtype=np.float32)
        impulse[0] = 1.0
        out, report = delay_send(impulse, sr, 120.0, settings, length=sr)
        self.assertGreater(abs(float(out[12000, 0])), 0.0)
        self.assertAlmostEqual(report["delay_seconds"], 0.25, places=3)

    def test_small_room_compatibility_wrapper(self) -> None:
        sr = 48000
        impulse = np.zeros((sr // 2, 1), dtype=np.float32)
        impulse[0] = 1.0
        out, report = small_room(impulse, sr, wet_db=-12, length=sr)
        self.assertEqual(out.shape, (sr, 2))
        self.assertEqual(report["compatibility_wrapper"], "small_room")


if __name__ == "__main__":
    unittest.main()

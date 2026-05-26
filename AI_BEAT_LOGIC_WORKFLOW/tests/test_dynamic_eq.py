from __future__ import annotations

import sys
import unittest
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from audio_metrics import bandpass, clipping_count, rms  # noqa: E402
from dynamic_eq import DynamicEQBand, apply_vocal_triggered_beat_ducking, dynamic_band_process, envelope_follower  # noqa: E402


class DynamicEqTests(unittest.TestCase):
    def test_envelope_has_attack_and_release_shape(self) -> None:
        sr = 1000
        detector = np.zeros((1000, 1), dtype=np.float32)
        detector[100:300] = 1.0
        env = envelope_follower(detector, sr, attack_ms=10, release_ms=100)
        self.assertGreater(env[150], env[105])
        self.assertGreater(env[320], env[800])

    def test_dynamic_band_reduces_target_band_when_detector_crosses_threshold(self) -> None:
        sr = 48000
        t = np.arange(sr) / sr
        tone = np.sin(2 * np.pi * 3000 * t).astype(np.float32)[:, None] * 0.4
        processed, report = dynamic_band_process(tone, tone, DynamicEQBand(2500, 3500, -40, -6, ratio_slope=0.5, attack_ms=2, release_ms=40), sr)
        self.assertLess(rms(bandpass(processed, 2500, 3500, sr)), rms(bandpass(tone, 2500, 3500, sr)))
        self.assertLess(report["max_gain_reduction_db"], 0.0)

    def test_silent_sidechain_does_not_duck(self) -> None:
        sr = 48000
        t = np.arange(sr) / sr
        audio = np.sin(2 * np.pi * 2500 * t).astype(np.float32)[:, None] * 0.2
        silent = np.zeros_like(audio)
        processed, report = dynamic_band_process(audio, silent, DynamicEQBand(1000, 4000, -40, -4, ratio_slope=0.5), sr)
        np.testing.assert_allclose(processed, audio, atol=2e-3)
        self.assertEqual(report["max_gain_reduction_db"], 0.0)

    def test_release_smoothing_keeps_reduction_after_sidechain_stops(self) -> None:
        sr = 1000
        sidechain = np.zeros((1000, 1), dtype=np.float32)
        sidechain[100:200] = 1.0
        env = envelope_follower(sidechain, sr, attack_ms=2, release_ms=250, detector="peak")
        self.assertGreater(env[230], env[800])

    def test_vocal_triggered_ducking_does_not_clip(self) -> None:
        sr = 48000
        t = np.arange(sr) / sr
        beat = (0.5 * np.sin(2 * np.pi * 250 * t) + 0.35 * np.sin(2 * np.pi * 2400 * t)).astype(np.float32)[:, None]
        vocal = (0.35 * np.sin(2 * np.pi * 2200 * t)).astype(np.float32)[:, None]
        processed, report = apply_vocal_triggered_beat_ducking(beat, vocal, sr)
        self.assertEqual(clipping_count(processed), 0)
        self.assertIn("masking_score_before", report)


if __name__ == "__main__":
    unittest.main()

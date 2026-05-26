from __future__ import annotations

import sys
import unittest
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from audio_metrics import bandpass, clipping_count, rms  # noqa: E402
from vocal_tone_designer import design_vocal_tone  # noqa: E402


class VocalToneDesignerTests(unittest.TestCase):
    def test_design_vocal_tone_keeps_shape_and_blocks_plugin_claim(self) -> None:
        sr = 48000
        t = np.arange(sr) / sr
        audio = (0.2 * np.sin(2 * np.pi * 220 * t) + 0.04 * np.sin(2 * np.pi * 7500 * t)).astype(np.float32)[:, None]
        out, report = design_vocal_tone(audio, sr, tune_blend=0.08)
        self.assertEqual(out.shape, audio.shape)
        self.assertFalse(report["plugin_pitch_correction_applied"])
        self.assertIn("deesser", report)

    def test_vocal_tone_designer_does_not_clip(self) -> None:
        sr = 48000
        t = np.arange(sr) / sr
        audio = (0.6 * np.sin(2 * np.pi * 220 * t) + 0.2 * np.sin(2 * np.pi * 3400 * t)).astype(np.float32)[:, None]
        out, report = design_vocal_tone(audio, sr, role="lead")
        self.assertEqual(clipping_count(out), 0)
        self.assertEqual(report["clipping_count"], 0)

    def test_bright_target_does_not_overboost_harshness_band(self) -> None:
        sr = 48000
        t = np.arange(sr) / sr
        audio = (0.2 * np.sin(2 * np.pi * 240 * t) + 0.12 * np.sin(2 * np.pi * 4200 * t) + 0.05 * np.sin(2 * np.pi * 11000 * t)).astype(np.float32)[:, None]
        out, report = design_vocal_tone(audio, sr, role="lead")
        harsh_ratio = rms(bandpass(out, 3000, 6000, sr)) / (rms(bandpass(audio, 3000, 6000, sr)) + 1e-12)
        self.assertLess(harsh_ratio, 1.8)
        self.assertLessEqual(report["air_lift_db"], 0.9)


if __name__ == "__main__":
    unittest.main()

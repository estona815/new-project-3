from __future__ import annotations

import sys
import unittest
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from pitch_correction import (  # noqa: E402
    PitchCorrectionSettings,
    analyze_pitch_frames,
    estimate_pitch_autocorr,
    generate_tuned_support_layer,
    midi_to_note_name,
    native_pitch_correction_approx,
    nearest_scale_midi,
)


class PitchCorrectionTests(unittest.TestCase):
    def test_pitch_estimator_detects_sine_frequency(self) -> None:
        sr = 48000
        t = np.arange(int(sr * 0.08)) / sr
        audio = np.sin(2 * np.pi * 220 * t).astype(np.float32)[:, None]
        self.assertAlmostEqual(estimate_pitch_autocorr(audio, sr) or 0.0, 220, delta=4)

    def test_native_pitch_correction_reports_no_plugin_claim(self) -> None:
        sr = 48000
        t = np.arange(sr) / sr
        audio = np.sin(2 * np.pi * 231 * t).astype(np.float32)[:, None] * 0.2
        out, report = native_pitch_correction_approx(audio, sr, PitchCorrectionSettings(blend=0.08))
        self.assertEqual(out.shape, audio.shape)
        self.assertFalse(report["verified_plugin_used"])
        self.assertIn("native pitch-correction approximation", report["method"])
        self.assertFalse(report["Antares_AutoTune_applied"])

    def test_nearest_scale_note_returns_scale_degree(self) -> None:
        self.assertEqual(nearest_scale_midi(61.1, 60, (0, 2, 4, 5, 7, 9, 11)), 62)

    def test_note_name_conversion(self) -> None:
        self.assertEqual(midi_to_note_name(69), "A4")

    def test_unvoiced_noise_is_not_pitch_shifted(self) -> None:
        sr = 48000
        rng = np.random.default_rng(7)
        noise = rng.normal(0.0, 0.03, sr).astype(np.float32)[:, None]
        frames = analyze_pitch_frames(noise, sr, PitchCorrectionSettings())
        voiced_ratio = sum(1 for frame in frames if frame["voiced"]) / len(frames)
        self.assertLess(voiced_ratio, 0.1)
        out, report = native_pitch_correction_approx(noise, sr, PitchCorrectionSettings(blend=0.2))
        self.assertEqual(out.shape, noise.shape)
        self.assertTrue(report["bypassed_for_artifacts"] or report["voiced_ratio"] < 0.1)

    def test_tuned_support_layer_generated(self) -> None:
        sr = 48000
        t = np.arange(sr) / sr
        audio = np.sin(2 * np.pi * 231 * t).astype(np.float32)[:, None] * 0.2
        layer, report = generate_tuned_support_layer(audio, sr, PitchCorrectionSettings(blend=0.25, mode="medium"))
        self.assertEqual(layer.shape, audio.shape)
        self.assertGreater(report["frames_corrected"], 0)
        self.assertEqual(report["layer"], "tuned support layer")

    def test_low_key_confidence_uses_chromatic_gentle(self) -> None:
        sr = 48000
        t = np.arange(sr) / sr
        audio = np.sin(2 * np.pi * 250 * t).astype(np.float32)[:, None] * 0.2
        _out, report = native_pitch_correction_approx(audio, sr, PitchCorrectionSettings(key_confidence=0.1, blend=0.1))
        self.assertEqual(report["scale_mode"], "chromatic_gentle")


if __name__ == "__main__":
    unittest.main()

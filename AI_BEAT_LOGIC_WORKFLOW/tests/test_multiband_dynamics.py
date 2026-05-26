from __future__ import annotations

import sys
import unittest
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from audio_metrics import bandpass, peak_db, rms  # noqa: E402
from multiband_dynamics import CompressorBand, multiband_compress, multiband_glue  # noqa: E402


class MultibandDynamicsTests(unittest.TestCase):
    def test_multiband_compressor_returns_reports_and_no_nan(self) -> None:
        sr = 48000
        t = np.arange(sr) / sr
        audio = (0.5 * np.sin(2 * np.pi * 90 * t) + 0.25 * np.sin(2 * np.pi * 3000 * t)).astype(np.float32)[:, None]
        out, reports = multiband_compress(audio, sr, [CompressorBand(40, 150, -30, 2, 10, 80), CompressorBand(1000, 5000, -32, 2, 5, 60)])
        self.assertEqual(out.shape, audio.shape)
        self.assertEqual(len(reports), 2)
        self.assertTrue(np.isfinite(out).all())
        self.assertLess(peak_db(out), 3.0)

    def test_multiband_compressor_reduces_target_band_more_than_untargeted_band(self) -> None:
        sr = 48000
        t = np.arange(sr) / sr
        audio = (0.8 * np.sin(2 * np.pi * 90 * t) + 0.18 * np.sin(2 * np.pi * 3000 * t)).astype(np.float32)[:, None]
        out, reports = multiband_compress(audio, sr, [CompressorBand(60, 120, -38, 4, 2, 80, 0.0, -12.0, 0.0)])
        low_before = rms(bandpass(audio, 60, 120, sr))
        low_after = rms(bandpass(out, 60, 120, sr))
        high_before = rms(bandpass(audio, 2500, 3500, sr))
        high_after = rms(bandpass(out, 2500, 3500, sr))
        self.assertLess(low_after / low_before, 0.8)
        self.assertGreater(high_after / high_before, 0.9)
        self.assertLess(reports[0]["max_gain_reduction_db"], -1.0)

    def test_multiband_glue_reports_parallel_density(self) -> None:
        sr = 48000
        rng = np.random.default_rng(1)
        audio = (rng.standard_normal((sr, 2)) * 0.05).astype(np.float32)
        out, report = multiband_glue(audio, sr)
        self.assertEqual(out.shape, audio.shape)
        self.assertIn("band_reports", report)
        self.assertGreater(len(report["band_reports"]), 0)


if __name__ == "__main__":
    unittest.main()

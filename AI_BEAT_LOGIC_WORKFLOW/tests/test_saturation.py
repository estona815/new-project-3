from __future__ import annotations

import sys
import unittest
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from audio_metrics import clipping_count, peak_db  # noqa: E402
from saturation import SaturationSettings, saturate, soft_saturate  # noqa: E402


class SaturationTests(unittest.TestCase):
    def test_saturation_does_not_clip_after_trim(self) -> None:
        sr = 48000
        t = np.arange(sr) / sr
        audio = (1.3 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)[:, None]
        out, report = saturate(audio, sr, SaturationSettings(drive=2.2, dry_wet=0.8, output_trim_db=-1.5, soft_clip=True, oversample=2))
        self.assertEqual(clipping_count(out), 0)
        self.assertLessEqual(peak_db(out), -0.01)
        self.assertEqual(report["oversample"], 2)

    def test_soft_saturate_legacy_signature_is_preserved(self) -> None:
        audio = np.linspace(-0.8, 0.8, 1000, dtype=np.float32)[:, None]
        out = soft_saturate(audio, 1.2, 0.9)
        self.assertEqual(out.shape, audio.shape)
        self.assertTrue(np.isfinite(out).all())


if __name__ == "__main__":
    unittest.main()

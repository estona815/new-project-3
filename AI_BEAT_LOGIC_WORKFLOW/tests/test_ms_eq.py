from __future__ import annotations

import sys
import unittest
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from audio_metrics import clipping_count, side_mid_db  # noqa: E402
from ms_eq import mid_side_decode, mid_side_encode, mid_side_eq, mono_compatibility_metrics, safe_mid_side_process, side_low_cut  # noqa: E402


class MsEqTests(unittest.TestCase):
    def test_encode_decode_roundtrip(self) -> None:
        audio = np.column_stack((np.linspace(-0.5, 0.5, 1000), np.linspace(0.5, -0.5, 1000))).astype(np.float32)
        mid, side = mid_side_encode(audio)
        decoded = mid_side_decode(mid, side)
        np.testing.assert_allclose(decoded, audio, atol=1e-6)

    def test_side_gain_changes_side_mid_ratio(self) -> None:
        sr = 48000
        t = np.arange(sr) / sr
        audio = np.column_stack((np.sin(2 * np.pi * 6000 * t), np.sin(2 * np.pi * 6100 * t))).astype(np.float32) * 0.1
        widened = mid_side_eq(audio, sr, [], [(5000, 7000, 4.0)])
        self.assertGreater(side_mid_db(widened), side_mid_db(audio))

    def test_side_low_cut_reduces_low_frequency_side_energy(self) -> None:
        sr = 48000
        t = np.arange(sr) / sr
        left = np.sin(2 * np.pi * 70 * t)
        right = -np.sin(2 * np.pi * 70 * t)
        audio = np.column_stack((left, right)).astype(np.float32) * 0.2
        before = mono_compatibility_metrics(audio, sr)["low_side_mid_ratio_below_150hz_db"]
        processed = side_low_cut(audio, sr, cutoff_hz=140)
        after = mono_compatibility_metrics(processed, sr)["low_side_mid_ratio_below_150hz_db"]
        self.assertLess(after, before)

    def test_mono_compatibility_catches_excessive_widening(self) -> None:
        sr = 48000
        t = np.arange(sr) / sr
        audio = np.column_stack((np.sin(2 * np.pi * 400 * t), -np.sin(2 * np.pi * 400 * t))).astype(np.float32) * 0.2
        metrics = mono_compatibility_metrics(audio, sr)
        self.assertLess(metrics["left_right_correlation"], 0.1)
        self.assertGreater(metrics["side_mid_ratio_db"], 20.0)

    def test_safe_mid_side_process_avoids_clipping(self) -> None:
        sr = 48000
        t = np.arange(sr) / sr
        audio = np.column_stack((np.sin(2 * np.pi * 5000 * t), np.sin(2 * np.pi * 5100 * t))).astype(np.float32) * 0.8
        processed, report = safe_mid_side_process(audio, sr, side_upper_width_db=2.0, side_air_lift_db=2.0)
        self.assertEqual(clipping_count(processed), 0)
        self.assertIn("after", report)


if __name__ == "__main__":
    unittest.main()

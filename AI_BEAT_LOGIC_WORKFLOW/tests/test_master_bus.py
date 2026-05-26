from __future__ import annotations

import sys
import unittest
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from audio_metrics import clipping_count, mono_compatibility, oversampled_peak_db, peak_db  # noqa: E402
from master_bus import master_bus_process, oversampled_limiter, soft_limiter  # noqa: E402


class MasterBusTests(unittest.TestCase):
    def test_soft_limiter_respects_ceiling(self) -> None:
        audio = np.linspace(-1.5, 1.5, 48000, dtype=np.float32)[:, None]
        out, report = soft_limiter(audio, -1.0)
        self.assertLessEqual(peak_db(out), -0.99)
        self.assertEqual(report["ceiling_db"], -1.0)

    def test_oversampled_peak_proxy_catches_inter_sample_risk(self) -> None:
        sr = 48000
        t = np.arange(sr // 10) / sr
        audio = (0.96 * np.sin(2 * np.pi * 19_000 * t)).astype(np.float32)[:, None]
        self.assertGreaterEqual(oversampled_peak_db(audio, 4), peak_db(audio) - 0.05)

    def test_oversampled_limiter_prevents_clipping(self) -> None:
        sr = 48000
        t = np.arange(sr) / sr
        audio = (1.6 * np.sin(2 * np.pi * 900 * t)).astype(np.float32)[:, None]
        out, report = oversampled_limiter(audio, sr, ceiling_db=-1.0, oversample=4)
        self.assertEqual(clipping_count(out), 0)
        self.assertLessEqual(report["true_peak_proxy_dbfs"], -0.75)

    def test_master_bus_process_does_not_clip(self) -> None:
        sr = 48000
        t = np.arange(sr) / sr
        audio = np.column_stack((np.sin(2 * np.pi * 100 * t), np.sin(2 * np.pi * 2400 * t))).astype(np.float32) * 0.2
        out, report = master_bus_process(audio, sr, target_rms_db=-12.0)
        self.assertEqual(clipping_count(out), 0)
        self.assertIn("soft_limiter", report)
        self.assertIn("quality_metrics", report)

    def test_master_bus_does_not_destroy_mono_compatibility(self) -> None:
        sr = 48000
        t = np.arange(sr) / sr
        left = 0.2 * np.sin(2 * np.pi * 90 * t) + 0.08 * np.sin(2 * np.pi * 4000 * t)
        right = 0.2 * np.sin(2 * np.pi * 90 * t) - 0.035 * np.sin(2 * np.pi * 4000 * t)
        audio = np.column_stack((left, right)).astype(np.float32)
        before = mono_compatibility(audio)["left_right_correlation"]
        out, _report = master_bus_process(audio, sr, target_rms_db=-14.0)
        after = mono_compatibility(out)["left_right_correlation"]
        self.assertGreater(after, 0.1)
        self.assertGreater(after, before - 0.25)


if __name__ == "__main__":
    unittest.main()

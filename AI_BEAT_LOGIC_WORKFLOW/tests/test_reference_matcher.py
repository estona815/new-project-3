from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from audio_metrics import BAND_RANGES, peak_db  # noqa: E402
from reference_matcher import (  # noqa: E402
    apply_tone_aware_reference_correction,
    build_reference_profile,
    build_tone_corrections,
    compare_to_reference,
    load_reference_average,
)


def _ref(rms_db: float, crest: float, side: float, band_value: float) -> dict[str, object]:
    bands = {name: band_value for name in BAND_RANGES}
    return {
        "rms_dbfs": rms_db,
        "crest_db": crest,
        "side_mid_db": side,
        "band_db_rel_to_mono_rms": bands,
        "side_mid_by_band_db": {name: side for name in BAND_RANGES},
        "transient_density_per_sec": 4.0,
        "low_end_tightness": {"sub_to_bass_db": -1.0, "bass_to_low_mid_db": 2.0, "sub_crest_db": 8.0},
        "harshness_score_db": -4.0,
        "sibilance_score_db": -18.0,
        "vocal_presence_proxy_db": -3.0,
        "mono_compatibility": {"left_right_correlation": 0.8, "mono_level_delta_db": -0.3},
    }


class ReferenceMatcherTests(unittest.TestCase):
    def test_reference_profile_builds_from_dummy_references_with_median(self) -> None:
        profile = build_reference_profile([_ref(-9.0, 9.0, -10.0, -8.0), _ref(-30.0, 30.0, -2.0, 10.0), _ref(-8.0, 8.0, -11.0, -9.0)])
        self.assertEqual(profile["aggregation"], "median")
        self.assertEqual(profile["rms_dbfs"], -9.0)
        self.assertEqual(profile["band_db_rel_to_mono_rms"]["mid_400_1500"], -8.0)

    def test_loads_reference_average_and_compares_bands(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "refs.json"
            path.write_text(json.dumps({"ref_a": _ref(-9, 9, -11, -10)}), encoding="utf-8")
            ref = load_reference_average(path)
            audio = np.zeros((48000, 2), dtype=np.float32)
            audio[:, 0] = 0.1
            result = compare_to_reference(audio, 48000, ref)
            self.assertIn("band_delta_vs_reference_average_db", result)
            self.assertIn("harshness_sibilance_delta", result)

    def test_correction_limits_are_respected(self) -> None:
        sr = 48000
        t = np.arange(sr) / sr
        audio = (0.2 * np.sin(2 * np.pi * 300 * t)).astype(np.float32)[:, None]
        profile = _ref(-9.0, 9.0, -10.0, 3.0)
        corrections, _warnings = build_tone_corrections(audio, sr, profile, max_tonal_db=1.5)
        self.assertTrue(corrections)
        self.assertTrue(all(abs(correction["gain_db"]) <= 1.5 for correction in corrections))

    def test_harshness_protection_prevents_excessive_high_boost(self) -> None:
        sr = 48000
        t = np.arange(sr) / sr
        audio = (0.12 * np.sin(2 * np.pi * 6000 * t) + 0.03 * np.sin(2 * np.pi * 1200 * t)).astype(np.float32)[:, None]
        profile = _ref(-9.0, 9.0, -10.0, -6.0)
        profile["band_db_rel_to_mono_rms"]["bite_4500_8000"] = 0.0
        profile["harshness_score_db"] = -8.0
        corrections, warnings = build_tone_corrections(audio, sr, profile)
        bite = [correction for correction in corrections if correction["band"] == "bite_4500_8000"]
        self.assertFalse(bite)
        self.assertTrue(any("ignored bite_4500_8000 boost" in warning for warning in warnings))

    def test_numeric_match_cannot_override_clipping_quality_safety(self) -> None:
        sr = 48000
        audio = np.full((sr, 2), 0.995, dtype=np.float32)
        profile = _ref(-9.0, 9.0, -10.0, 12.0)
        out, report = apply_tone_aware_reference_correction(audio, sr, profile)
        self.assertLessEqual(peak_db(out), peak_db(audio) + 0.01)
        self.assertEqual(report["correction_amounts"], [])
        self.assertTrue(any("clipping" in warning for warning in report["warnings"]))


if __name__ == "__main__":
    unittest.main()

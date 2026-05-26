from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from final_verify import verify_final_export  # noqa: E402


FINAL_WAV = PROJECT_ROOT / "05_FINAL_WAV" / "plugg_reference_matched_v4_24bit_48k.wav"
METRICS_JSON = PROJECT_ROOT / "06_QC_REPORT" / "plugg_reference_matched_v4_metrics.json"


class PluggDigicoreRenderQcTests(unittest.TestCase):
    def test_render_script_preserves_verified_export_and_honesty_guards(self) -> None:
        script = (PROJECT_ROOT / "scripts" / "render_plugg_digicore_mix.py").read_text(encoding="utf-8")
        self.assertIn("verify_final_wav(FINAL_MASTER_PATH, \"wav24_48k\")", script)
        self.assertIn("plugg_reference_matched_v4_24bit_48k.wav", script)
        self.assertIn("plugg_reference_matched_v4_metrics.json", script)
        self.assertIn("\"beat_bus\"", script)
        self.assertIn("\"lead_vocal_bus\"", script)
        self.assertIn("\"premaster_bus\"", script)
        self.assertIn("\"master_bus\"", script)
        self.assertIn("\"true_pitch_correction_applied\": False", script)
        self.assertIn("\"hard_tune_style_layer_applied\": False", script)
        self.assertIn("\"antares_applied\": False", script)
        self.assertIn("native pitch-correction approximation", script)
        self.assertNotIn("\"Antares applied\": True", script)

    def test_final_wav_export_qc_passes(self) -> None:
        self.assertTrue(FINAL_WAV.exists(), "final WAV must exist before COMPLETE claim")
        verification = verify_final_export(FINAL_WAV, "wav24_48k", "under_2min")
        self.assertTrue(verification["exists"])
        self.assertEqual(verification["bit_depth"], 24)
        self.assertTrue(verification["bit_depth_verified"])
        self.assertEqual(verification["sample_rate"], 48000)
        self.assertEqual(verification["channels"], 2)
        self.assertIsNotNone(verification["duration_seconds"])
        self.assertGreater(float(verification["duration_seconds"]), 0.0)
        self.assertEqual(verification["clipping_count"], 0)
        self.assertLessEqual(float(verification["peak_dbfs"]), -1.0)
        self.assertTrue(verification["format_verified"])

    def test_metrics_json_final_qc_is_safe_and_not_numeric_only(self) -> None:
        self.assertTrue(METRICS_JSON.exists(), "metrics JSON must exist")
        qc = json.loads(METRICS_JSON.read_text(encoding="utf-8"))
        verification = qc["verification"]
        processing = qc["processing"]
        extended = qc["extended_metrics"]
        quality = processing["master_bus_quality_metrics"]
        mono_ms = extended["mono_compatibility_ms"]
        masking = extended["vocal_beat_masking_score"]

        self.assertTrue(verification["ok"])
        self.assertEqual(verification["clipping_count"], 0)
        self.assertLessEqual(quality["oversampled_peak_proxy_dbfs"], -0.95)
        self.assertIn("tone-aware reference correction", processing["applied"])
        self.assertIn("RMS/crest numeric match is advisory only; no extra compression is applied here", processing["reference_match_report"]["ignored_traits"])
        self.assertGreater(quality["crest_db"], 10.0, "RMS must not be the only target")
        self.assertGreater(quality["side_mid_db"], -18.0)
        self.assertLess(quality["side_mid_db"], -6.0)
        self.assertLessEqual(mono_ms["low_side_mid_ratio_below_150hz_db"], -20.0)
        self.assertGreaterEqual(masking["presence_collision"]["score_db"], -1.0)
        self.assertGreaterEqual(masking["presence_1500_4500"], -4.0)
        self.assertLessEqual(quality["harshness_score_db"], 0.0)
        self.assertLessEqual(quality["sibilance_score_db"], -12.0)
        self.assertGreaterEqual(quality["mono_compatibility"]["left_right_correlation"], 0.1)
        self.assertLessEqual(abs(mono_ms["mono_fold_rms_change_db"]), 1.0)

    def test_qc_contains_no_false_plugin_stem_or_copy_claims(self) -> None:
        qc = json.loads(METRICS_JSON.read_text(encoding="utf-8"))
        processing = qc["processing"]
        full_report = json.dumps(qc, ensure_ascii=False).lower()
        self.assertFalse(processing["antares_applied"])
        self.assertFalse(processing["true_pitch_correction_applied"])
        self.assertFalse(processing["hard_tune_style_layer_applied"])
        self.assertFalse(qc["exact_artist_clone_claimed"])
        self.assertIn("native pitch-correction approximation", processing["pitch_note"])
        self.assertIn("source beat is a stereo mix, so beat processing is bus-level rather than stem-level", processing["remaining_limitations"])
        self.assertNotIn("decapitator applied", full_report)
        self.assertNotIn("antares applied: true", full_report)
        self.assertNotIn("autotune applied: true", full_report)
        self.assertNotIn("stem-level beat processing applied", full_report)
        self.assertNotIn("exact reference copy claimed", full_report)


if __name__ == "__main__":
    unittest.main()

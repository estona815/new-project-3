from __future__ import annotations

import unittest

from harness.engineering_rule_checker import run_engineering_rule_check
from harness.processing_decision_engine import recommend_processing_plan
from harness.severity import max_severity


def base_report() -> dict:
    return {
        "mode": "fullmix_rescue",
        "claims": ["fullmix rescue"],
        "source_format": "wav",
        "metrics": {
            "before": {"duration_sec": 60.0},
            "after": {"duration_sec": 60.0, "approx_true_peak_dbfs": -1.2},
            "delta": {
                "air_fizz_band_db": -0.2,
                "transient_ratio": 0.99,
                "side_mid_ratio_db": 0.1,
                "low_band_energy_db": -0.1,
            },
        },
    }


def codes(payload: dict) -> set[str]:
    return {finding["code"] for finding in payload["findings"]}


class EngineeringRuleTests(unittest.TestCase):
    def test_true_rebeat_claim_without_midi_or_stem_evidence_fails(self) -> None:
        report = base_report()
        report.update({"mode": "true_rebeat", "claims": ["true_rebeat"]})

        payload = run_engineering_rule_check(processing_report=report)

        self.assertIn("TRUE_REBEAT_CLAIM_UNSUPPORTED", codes(payload))
        self.assertEqual(max_severity(payload["findings"]), "FAIL")

    def test_true_rebeat_claim_with_only_stems_still_fails_without_rebuild_roles(self) -> None:
        report = base_report()
        report.update(
            {
                "mode": "true_rebeat",
                "claims": ["true_rebeat"],
                "stem_roles": ["drums", "bass", "music"],
                "evidence": {"midi_item_count": 8},
            }
        )

        payload = run_engineering_rule_check(processing_report=report)

        self.assertIn("TRUE_REBEAT_CLAIM_UNSUPPORTED", codes(payload))
        self.assertEqual(max_severity(payload["findings"]), "FAIL")

    def test_mp3_source_cannot_be_called_lossless_restoration(self) -> None:
        report = base_report()
        report.update({"source_format": "mp3", "source_is_lossy": True, "claims": ["lossless restoration"]})

        payload = run_engineering_rule_check(processing_report=report)

        self.assertIn("LOSSY_SOURCE_FALSE_LOSSLESS_CLAIM", codes(payload))
        self.assertEqual(max_severity(payload["findings"]), "FAIL")

    def test_excessive_brightness_loss_warns(self) -> None:
        report = base_report()
        report["metrics"]["delta"]["air_fizz_band_db"] = -1.25

        payload = run_engineering_rule_check(processing_report=report)

        self.assertIn("BRIGHTNESS_LOSS_WARN", codes(payload))
        self.assertIn(max_severity(payload["findings"]), {"WARN", "FAIL"})

    def test_excessive_transient_loss_fails(self) -> None:
        report = base_report()
        report["metrics"]["delta"]["transient_ratio"] = 0.88

        payload = run_engineering_rule_check(processing_report=report)

        self.assertIn("TRANSIENT_LOSS_EXCESSIVE", codes(payload))
        self.assertEqual(max_severity(payload["findings"]), "FAIL")

    def test_stronger_deai_is_not_selected_when_punch_or_brightness_collapses(self) -> None:
        report = base_report()
        report.update(
            {
                "selected_candidate": "B_more_deai",
                "candidates": [
                    {
                        "name": "B_more_deai",
                        "deai_intensity": "strong",
                        "metrics": {"brightness_loss_db": 3.0, "punch_loss_db": 1.2, "transient_ratio": 0.94},
                    }
                ],
            }
        )

        payload = run_engineering_rule_check(processing_report=report)

        self.assertIn("STRONG_DEAI_SELECTED_DESPITE_COLLAPSE", codes(payload))
        self.assertEqual(max_severity(payload["findings"]), "FAIL")

    def test_ms_side_reduction_that_collapses_width_is_rejected(self) -> None:
        report = base_report()
        report["metrics"]["delta"]["side_mid_ratio_db"] = -3.25
        report["processing_moves"] = [
            {
                "category": "ms_eq",
                "band": "10-16 kHz",
                "target": "Side",
                "static_or_dynamic": "dynamic",
                "amount_db": -4.0,
                "reason": "side wash reduction",
                "risk": "width loss",
            }
        ]

        payload = run_engineering_rule_check(processing_report=report)

        self.assertIn("STEREO_WIDTH_COLLAPSE_OR_INSTABILITY", codes(payload))
        self.assertEqual(max_severity(payload["findings"]), "FAIL")

    def test_broad_eq_for_narrow_resonance_warns(self) -> None:
        report = base_report()
        report["processing_moves"] = [
            {
                "category": "eq",
                "problem": "narrow metallic resonance at 4200 Hz",
                "eq_type": "broad_cut",
                "q": 0.7,
            }
        ]

        payload = run_engineering_rule_check(processing_report=report)

        self.assertIn("BROAD_EQ_USED_FOR_RESONANCE", codes(payload))
        self.assertIn(max_severity(payload["findings"]), {"WARN", "FAIL"})

    def test_missing_required_plugin_blocks_required_mode(self) -> None:
        report = base_report()
        report.update(
            {
                "mode": "vocal_repair",
                "plugins": [{"name": "Custom Suno DeAI JSFX", "required": True, "available": False}],
            }
        )

        payload = run_engineering_rule_check(processing_report=report)

        self.assertIn("PLUGIN_MISSING_OR_UNVERIFIED", codes(payload))
        self.assertEqual(max_severity(payload["findings"]), "BLOCKER")

    def test_fullmix_deesser_is_marked_risky(self) -> None:
        report = base_report()
        report["processing_moves"] = [
            {
                "category": "deesser",
                "target": "fullmix master",
                "max_reduction_db": 1.0,
                "brightness_loss_guard": "air_fizz_band_db",
            }
        ]

        payload = run_engineering_rule_check(processing_report=report)

        self.assertIn("FULLMIX_DEESSER_RISK", codes(payload))
        self.assertIn(max_severity(payload["findings"]), {"WARN", "FAIL"})

    def test_reference_matching_cannot_override_true_peak_failure(self) -> None:
        report = base_report()
        report["metrics"]["after"]["approx_true_peak_dbfs"] = -0.2
        report["reference_matching"] = {"forced": True, "reference_file": "loud_ref.wav"}

        payload = run_engineering_rule_check(processing_report=report)

        self.assertIn("TRUE_PEAK_RULE_FAIL", codes(payload))
        self.assertIn("REFERENCE_MATCHING_OVERRIDES_TRUE_PEAK", codes(payload))
        self.assertEqual(max_severity(payload["findings"]), "FAIL")

    def test_decision_engine_forbids_stem_and_rebeat_claims_without_stems(self) -> None:
        plan = recommend_processing_plan(
            {
                "mode": "auto",
                "source_format": "mp3",
                "source_is_lossy": True,
                "metrics": {
                    "side_mid_ratio_db": -6.0,
                    "air_fizz_band_db": -25.0,
                    "harshness_band_db": -25.0,
                    "sibilance_band_db": -35.0,
                    "low_band_energy_db": -34.0,
                },
            }
        )

        self.assertIn("true rebeat", plan["forbidden_claims"])
        self.assertIn("lossless restoration", plan["forbidden_claims"])
        self.assertTrue(plan["recommended_ms_moves"])
        self.assertIn(plan["recommended_deai_intensity"], {"medium", "mild-to-medium"})


if __name__ == "__main__":
    unittest.main()

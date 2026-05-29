from __future__ import annotations

import unittest

from harness.pipeline_preference_lock import evaluate_lock


def lock() -> dict:
    return {
        "name": "test_preference_lock",
        "song": "mesi_1",
        "preferred": {"selected_candidate": "C_punch_preserve"},
        "required_classification_terms": ["fullmix_rescue", "Suno_DeAI_repair", "master processing"],
        "source_policy": {"expect_lossy_source": True},
        "selection_rules": {
            "reject_if_selected": [
                {
                    "name": "B_more_deai",
                    "severity": "FAIL",
                    "message": "too much cleanup",
                    "recommendation": "use C",
                },
                {
                    "name": "E_drum_reinforcement",
                    "severity": "WARN",
                    "message": "grid not proven",
                    "recommendation": "listen first",
                },
            ]
        },
        "metric_guards": {
            "max_abs_duration_delta_sec": 0.02,
            "max_true_peak_dbfs": -1.0,
            "min_transient_ratio": 0.99,
            "min_punch_delta_db": -0.1,
            "min_air_fizz_delta_db": -0.25,
            "max_abs_side_mid_delta_db": 0.75,
            "max_harshness_increase_db": 0.15,
            "max_abs_vocal_presence_delta_db": 0.25,
        },
        "known_warn_plus_allowed": ["INTEGRATED_LOUDNESS_UNAVAILABLE"],
        "forbidden_claims_without_evidence": ["true_rebeat", "lossless restoration", "vocal tuned"],
    }


def good_evidence() -> dict:
    return {
        "actual_classification": "fullmix_rescue + Suno_DeAI_repair + master processing",
        "selected_candidate": "C_punch_preserve",
        "source_format": "mp3",
        "source_is_lossy": True,
        "claims": ["fullmix rescue", "lossy-source processed print"],
        "qc_summary": {
            "duration_sec": 0.0,
            "true_peak_after_dbfs": -1.42,
            "transient_ratio": 0.997,
            "punch_delta_db": 0.02,
            "air_fizz_delta_db": -0.07,
            "side_mid_delta_db": -0.31,
            "harshness_delta_db": -0.06,
            "vocal_presence_delta_db": 0.01,
        },
    }


class PipelinePreferenceLockTests(unittest.TestCase):
    def test_current_favorite_candidate_passes_lock(self) -> None:
        payload = evaluate_lock(lock(), good_evidence())

        self.assertEqual(payload["lock_status"], "locked")
        self.assertEqual(payload["max_severity"], "PASS")

    def test_stronger_deai_candidate_is_rejected_by_default(self) -> None:
        evidence = good_evidence()
        evidence["selected_candidate"] = "B_more_deai"

        payload = evaluate_lock(lock(), evidence)

        codes = {finding["code"] for finding in payload["findings"]}
        self.assertIn("PREFERRED_CANDIDATE_CHANGED", codes)
        self.assertIn("PREFERENCE_LOCK_REJECTED_CANDIDATE_SELECTED", codes)
        self.assertEqual(payload["lock_status"], "rejected")

    def test_transient_loss_fails_preference_lock(self) -> None:
        evidence = good_evidence()
        evidence["qc_summary"]["transient_ratio"] = 0.88

        payload = evaluate_lock(lock(), evidence)

        self.assertIn("PREFERENCE_LOCK_TRANSIENT_LOSS", {finding["code"] for finding in payload["findings"]})
        self.assertEqual(payload["max_severity"], "FAIL")

    def test_drum_reinforcement_candidate_requires_listening(self) -> None:
        evidence = good_evidence()
        evidence["selected_candidate"] = "E_drum_reinforcement"

        payload = evaluate_lock(lock(), evidence)

        codes = {finding["code"] for finding in payload["findings"]}
        self.assertIn("PREFERRED_CANDIDATE_CHANGED", codes)
        self.assertIn("PREFERENCE_LOCK_REJECTED_CANDIDATE_SELECTED", codes)

    def test_forbidden_claim_fails_lock(self) -> None:
        evidence = good_evidence()
        evidence["claims"] = ["fullmix rescue", "lossless restoration"]

        payload = evaluate_lock(lock(), evidence)

        self.assertIn("PREFERENCE_LOCK_FORBIDDEN_CLAIM", {finding["code"] for finding in payload["findings"]})
        self.assertEqual(payload["lock_status"], "rejected")


if __name__ == "__main__":
    unittest.main()

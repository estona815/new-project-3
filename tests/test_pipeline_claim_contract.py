from __future__ import annotations

import unittest

from harness.pipeline_claim_contract import evaluate_contract


def contract() -> dict:
    return {
        "name": "test_contract",
        "quoted_requirements": [{"quote": "If any validation result is WARN or higher, do NOT claim final success."}],
        "allowed_claims": ["fullmix rescue", "lossy-source processed print"],
        "forbidden_claims": ["lossless restoration", "true_rebeat"],
        "always_forbidden_without_evidence": ["lossless restoration", "professional final master"],
    }


class PipelineClaimContractTests(unittest.TestCase):
    def test_mp3_source_requires_lossy_language_and_forbids_lossless(self) -> None:
        payload = evaluate_contract(contract(), {"source_format": "mp3", "source_is_lossy": True})

        codes = {finding["code"] for finding in payload["findings"]}
        self.assertIn("LOSSY_SOURCE_LANGUAGE_REQUIRED", codes)
        self.assertIn("lossless restoration", payload["forbidden_claims"])
        self.assertEqual(payload["max_severity"], "WARN")

    def test_true_rebeat_claim_blocks_without_complete_roles(self) -> None:
        payload = evaluate_contract(
            contract(),
            {
                "actual_classification": "true_rebeat",
                "classification": {
                    "evidence_summary": {
                        "has_drum_reconstruction": True,
                        "has_bass_reconstruction": False,
                        "has_music_reconstruction": False,
                        "bus_renders_complete": False,
                        "grid_confidence": "FAIL",
                    }
                },
            },
        )

        self.assertIn("TRUE_REBEAT_CLAIM_BLOCKED", {finding["code"] for finding in payload["findings"]})
        self.assertEqual(payload["max_severity"], "FAIL")

    def test_warn_plus_blocks_final_success_language(self) -> None:
        payload = evaluate_contract(
            contract(),
            {
                "claims": ["completed"],
                "final_validation": {
                    "findings": [
                        {
                            "severity": "WARN",
                            "code": "INTEGRATED_LOUDNESS_UNAVAILABLE",
                            "message": "LUFS missing",
                            "evidence": "pyloudnorm missing",
                            "recommendation": "Install pyloudnorm",
                        }
                    ]
                },
            },
        )

        codes = {finding["code"] for finding in payload["findings"]}
        self.assertIn("WARN_PLUS_FINAL_CLAIM_BLOCKED", codes)
        self.assertIn("WARN_PLUS_SURFACED", codes)
        self.assertEqual(payload["claim_status"], "not_final_warn_plus")

    def test_source_fail_severity_is_preserved(self) -> None:
        payload = evaluate_contract(
            contract(),
            {
                "final_validation": {
                    "findings": [
                        {
                            "severity": "FAIL",
                            "code": "GRID_CONFIDENCE_FAIL",
                            "message": "Grid failed",
                            "evidence": "grid_score=0.24",
                            "recommendation": "Make manual tempo map",
                        }
                    ]
                }
            },
        )

        self.assertEqual(payload["max_severity"], "FAIL")

    def test_drum_candidate_does_not_describe_selected_final(self) -> None:
        payload = evaluate_contract(
            contract(),
            {
                "actual_classification": "fullmix_rescue + drum_reinforcement + master processing",
                "selected_candidate": "C_punch_preserve",
            },
        )

        self.assertIn("DRUM_REINFORCEMENT_NOT_SELECTED", {finding["code"] for finding in payload["findings"]})
        self.assertEqual(payload["max_severity"], "WARN")


if __name__ == "__main__":
    unittest.main()

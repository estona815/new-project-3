from __future__ import annotations

import unittest

from harness.rebeat_classification import classify_rebeat_evidence
from harness.rebeat_qc import evaluate_rebeat_qc


def tempo(confidence: str = "PASS") -> dict:
    return {"grid_confidence": confidence, "grid_confidence_score": 0.8 if confidence == "PASS" else 0.35}


def midi(**overrides: object) -> dict:
    payload = {
        "original_fullmix_active": False,
        "has_drum_midi": False,
        "has_bass_midi": False,
        "has_music_midi": False,
        "has_drum_audio_support": False,
        "has_separate_bus_renders": False,
        "fullmix_dependency_level": "low",
    }
    payload.update(overrides)
    return payload


def qc(**overrides: object) -> dict:
    payload = {"max_severity": "PASS", "candidate_results": []}
    payload.update(overrides)
    return payload


class RebeatClassificationTests(unittest.TestCase):
    def test_fullmix_only_source_cannot_be_true_rebeat(self) -> None:
        result = classify_rebeat_evidence(
            discovery={"source": {"channels": 2, "format": "wav"}},
            tempo_grid=tempo(),
            midi_audit=midi(original_fullmix_active=True, fullmix_dependency_level="high"),
            qc=qc(),
            processing_report={"mode": "true_rebeat", "claims": ["true_rebeat"]},
        )

        self.assertNotEqual(result["classification"], "true_rebeat")
        self.assertIn("true_rebeat", result["forbidden_claims"])
        self.assertIn("TRUE_REBEAT_REQUEST_DOWNGRADED", {item["code"] for item in result["findings"]})

    def test_drum_midi_only_is_not_true_rebeat(self) -> None:
        result = classify_rebeat_evidence(
            discovery={"source": {"channels": 2, "format": "wav"}},
            tempo_grid=tempo(),
            midi_audit=midi(original_fullmix_active=True, has_drum_midi=True, fullmix_dependency_level="high"),
            qc=qc(),
        )

        self.assertIn(result["classification"], {"drum_reinforcement", "partial_rebeat"})
        self.assertNotEqual(result["classification"], "true_rebeat")

    def test_drum_bass_music_midi_with_bus_renders_can_be_true_rebeat(self) -> None:
        result = classify_rebeat_evidence(
            discovery={"source": {"channels": 2, "format": "wav"}},
            tempo_grid=tempo(),
            midi_audit=midi(
                has_drum_midi=True,
                has_bass_midi=True,
                has_music_midi=True,
                has_separate_bus_renders=True,
                original_fullmix_active=False,
            ),
            qc=qc(),
        )

        self.assertEqual(result["classification"], "true_rebeat")
        self.assertTrue(result["true_rebeat_possible"])

    def test_missing_rpp_audit_prevents_true_rebeat(self) -> None:
        result = classify_rebeat_evidence(
            discovery={"source": {"channels": 2, "format": "wav"}},
            tempo_grid=tempo(),
            qc=qc(),
            processing_report={"mode": "true_rebeat", "claims": ["true_rebeat"]},
        )

        self.assertNotEqual(result["classification"], "true_rebeat")
        self.assertIn("RPP_AUDIT_REQUIRED_FOR_TRUE_REBEAT", {item["code"] for item in result["findings"]})

    def test_missing_bus_renders_prevents_true_rebeat(self) -> None:
        result = classify_rebeat_evidence(
            discovery={"source": {"channels": 2, "format": "wav"}},
            tempo_grid=tempo(),
            midi_audit=midi(has_drum_midi=True, has_bass_midi=True, has_music_midi=True, has_separate_bus_renders=False),
            qc=qc(),
            processing_report={"mode": "true_rebeat", "claims": ["true_rebeat"]},
        )

        self.assertNotEqual(result["classification"], "true_rebeat")
        self.assertIn("TRUE_REBEAT_BUS_RENDERS_MISSING", {item["code"] for item in result["findings"]})

    def test_mp3_source_triggers_lossy_warning(self) -> None:
        result = classify_rebeat_evidence(
            discovery={"selected_source": {"path": "song.mp3", "format": "mp3", "lossy": True}},
            tempo_grid=tempo(),
            midi_audit=midi(original_fullmix_active=True),
            qc=qc(),
        )

        self.assertIn("LOSSY_SOURCE_REBEAT_LIMITATION", {item["code"] for item in result["findings"]})
        self.assertIn("lossless restoration", result["forbidden_claims"])

    def test_low_grid_confidence_triggers_warn(self) -> None:
        result = classify_rebeat_evidence(
            discovery={"source": {"channels": 2, "format": "wav"}},
            tempo_grid=tempo("WARN"),
            midi_audit=midi(has_drum_midi=True),
            qc=qc(),
        )

        self.assertIn("GRID_CONFIDENCE_WARN", {item["code"] for item in result["findings"]})

    def test_high_flam_risk_rejects_drum_reinforcement_candidate(self) -> None:
        qc_payload = evaluate_rebeat_qc(
            {
                "candidates": [
                    {
                        "name": "B_kick_snare_subtle_support",
                        "classification": "drum_reinforcement",
                        "metrics": {"flam_risk_sec": 0.06, "punch_delta_db": 0.7, "approx_true_peak_dbfs": -1.2},
                    }
                ]
            }
        )
        self.assertEqual(qc_payload["candidate_results"][0]["status"], "reject")

        result = classify_rebeat_evidence(
            discovery={"source": {"channels": 2, "format": "wav"}},
            tempo_grid=tempo(),
            midi_audit=midi(original_fullmix_active=True, has_drum_midi=True, fullmix_dependency_level="high"),
            qc=qc(max_severity="FAIL", candidate_results=[{"name": "B", "status": "reject"}]),
        )

        self.assertIn("REBEAT_QC_FAILED", {item["code"] for item in result["findings"]})
        self.assertNotEqual(result["classification"], "true_rebeat")

    def test_better_punch_but_clipping_is_rejected(self) -> None:
        qc_payload = evaluate_rebeat_qc(
            {
                "candidates": [
                    {
                        "name": "C_drum_support_punch",
                        "classification": "drum_reinforcement",
                        "metrics": {"flam_risk_sec": 0.0, "punch_delta_db": 1.2, "approx_true_peak_dbfs": -0.2},
                    }
                ]
            }
        )
        self.assertEqual(qc_payload["candidate_results"][0]["status"], "reject")

        result = classify_rebeat_evidence(
            discovery={"source": {"channels": 2, "format": "wav"}},
            tempo_grid=tempo(),
            midi_audit=midi(original_fullmix_active=True, has_drum_midi=True, fullmix_dependency_level="high"),
            qc=qc(max_severity="FAIL", candidate_results=[{"name": "C", "status": "reject", "metrics": {"punch_delta_db": 1.0}}]),
        )

        self.assertIn("REBEAT_QC_FAILED", {item["code"] for item in result["findings"]})

    def test_no_midi_evidence_cannot_claim_rebeat(self) -> None:
        result = classify_rebeat_evidence(
            discovery={"source": {"channels": 2, "format": "wav"}},
            tempo_grid=tempo(),
            midi_audit=midi(original_fullmix_active=True),
            qc=qc(),
            processing_report={"claims": ["비트 다 새로 찍음"]},
        )

        self.assertIn("true_rebeat", result["forbidden_claims"])
        self.assertIn("TRUE_REBEAT_REQUEST_DOWNGRADED", {item["code"] for item in result["findings"]})

    def test_existing_stems_allow_stem_assisted_rebuild(self) -> None:
        result = classify_rebeat_evidence(
            discovery={"available_stems": [{"path": "drums.wav", "role": "drums"}, {"path": "bass.wav", "role": "bass"}]},
            tempo_grid=tempo(),
            midi_audit=midi(has_stem_tracks=True),
            qc=qc(),
        )

        self.assertEqual(result["classification"], "stem_assisted_rebuild")

    def test_discovered_stems_without_active_tracks_do_not_create_stem_claim(self) -> None:
        result = classify_rebeat_evidence(
            discovery={"available_stems": [{"path": "older/drums.wav", "role": "drums"}]},
            tempo_grid=tempo(),
            midi_audit=midi(original_fullmix_active=True, has_drum_midi=True, fullmix_dependency_level="high"),
            qc=qc(),
        )

        self.assertEqual(result["classification"], "drum_reinforcement")
        self.assertIn("STEMS_DISCOVERED_NOT_ACTIVE", {item["code"] for item in result["findings"]})

    def test_machine_separated_stems_are_not_original_stems(self) -> None:
        result = classify_rebeat_evidence(
            discovery={"available_stems": [{"path": "demucs/drums.wav", "role": "drums", "kind": "machine-separated"}]},
            tempo_grid=tempo(),
            midi_audit=midi(has_stem_tracks=True),
            qc=qc(),
        )

        self.assertIn("MACHINE_SEPARATED_STEMS_NOT_ORIGINAL", {item["code"] for item in result["findings"]})
        self.assertEqual(result["classification"], "stem_assisted_rebuild")


if __name__ == "__main__":
    unittest.main()

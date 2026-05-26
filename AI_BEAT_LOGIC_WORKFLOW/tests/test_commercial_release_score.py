from __future__ import annotations

import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from commercial_release_score import build_commercial_release_score, score_rights_safety_readiness  # noqa: E402


def verified_audio() -> dict[str, object]:
    return {
        "path": "final.wav",
        "exists": True,
        "verified": True,
        "duration_seconds": 12.0,
        "sample_rate": 48000,
        "expected_sample_rate": 48000,
        "bit_depth": 24,
        "expected_bit_depth": 24,
        "codec_name": "pcm_s24le",
        "format_verified": True,
        "peak_dbfs": -1.0,
        "rms_dbfs": -12.0,
        "clipping_count": 0,
    }


class CommercialReleaseScoreTests(unittest.TestCase):
    def test_final_audio_failure_forces_low_score_and_blocker(self) -> None:
        score = build_commercial_release_score(
            final_audio={**verified_audio(), "verified": False, "clipping_count": 12},
            deliverable_manifest={"deliverables": [{"type": "final_master", "available": True}]},
            metadata_complete=True,
            rights={},
            rights_checklist_exists=True,
            release_manifest_exists=True,
            completion_gate={"complete": True},
            qc_report_exists=True,
            master_qc_report_exists=True,
            release_qc_report_exists=True,
        )

        final_category = next(item for item in score["categories"] if item["category"] == "final_audio_verification")
        self.assertEqual(final_category["score"], 1)
        self.assertIn("clipping detected", score["blocking_issues"])

    def test_rights_safety_blocks_voice_clone_exact_copy_and_sample_unknowns(self) -> None:
        category = score_rights_safety_readiness(
            {
                "contains_samples": True,
                "all_samples_owned_or_cleared": None,
                "voice_clone_used": True,
                "exact_copy_claim": True,
            },
            {"risky_flags": ["plugin_processing_verified"]},
        )

        self.assertEqual(category["score"], 1)
        self.assertIn("sample ownership/clearance unresolved", category["blocking_issues"])
        self.assertIn("voice clone claim/use is present", category["blocking_issues"])
        self.assertIn("exact-copy claim is present", category["blocking_issues"])
        self.assertIn("plugin or stem false-claim risk remains", category["blocking_issues"])

    def test_average_score_passes_only_at_four_or_above_without_success_claim(self) -> None:
        score = build_commercial_release_score(
            final_audio=verified_audio(),
            mix_master={"mix_priorities": ["vocal_forwardness", "controlled_808"], "style_target": "commercial_digicore_hyperpop"},
            arrangement={"categories": [{"name": "Hook impact", "score": 5}, {"name": "Arrangement intentionality", "score": 5}]},
            deliverable_manifest={"deliverables": [{"type": "final_master", "available": True}]},
            metadata_complete=True,
            rights={},
            rights_checklist_exists=True,
            release_manifest_exists=True,
            completion_gate={"complete": True},
            qc_report_exists=True,
            master_qc_report_exists=True,
            release_qc_report_exists=True,
        )

        self.assertGreaterEqual(score["average_score"], 4.0)
        self.assertTrue(score["release_ready_score_pass"])
        self.assertFalse(score["commercial_success_claimed"])


if __name__ == "__main__":
    unittest.main()

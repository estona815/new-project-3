from __future__ import annotations

import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from release_metadata import build_release_metadata_payload  # noqa: E402
from release_readiness_qc import (  # noqa: E402
    DRAFT_RELEASE_PACKAGE,
    FAILED_TECHNICAL_QC,
    NEEDS_RIGHTS_CLEARANCE,
    RELEASE_PACKAGE_READY,
    build_release_readiness_qc,
    render_release_readiness_qc_report,
)
from rights_clearance_checklist import build_rights_payload  # noqa: E402


def verified_audio() -> dict[str, object]:
    return {
        "path": "final.wav",
        "exists": True,
        "verified": True,
        "duration_seconds": 10.0,
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


def complete_metadata() -> dict[str, object]:
    return build_release_metadata_payload(
        {
            "title": "Track",
            "artist": "Artist",
            "genre": "digicore",
            "language": "ko",
            "explicit": False,
            "copyright_year": "2026",
            "copyright_owner": "Artist",
            "producer": "Producer",
            "composer": "Composer",
        }
    )


def clear_rights() -> dict[str, object]:
    return build_rights_payload(
        contains_samples=False,
        source_ownership_confirmed=True,
        vocal_performer_consent=True,
        featured_artist_metadata_complete=True,
        explicit_content_flag_set=True,
    )


class ReleaseReadinessQCTests(unittest.TestCase):
    def test_failed_final_audio_verification_is_failed_technical_qc(self) -> None:
        qc = build_release_readiness_qc(
            final_audio={**verified_audio(), "verified": False, "format_verified": False},
            metadata_payload=complete_metadata(),
            rights_payload=clear_rights(),
            deliverable_manifest={"deliverables": [{"type": "final_master", "available": True}]},
            qc_report_exists=True,
            master_qc_report_exists=True,
            release_qc_report_exists=True,
            release_manifest_exists=True,
            rights_checklist_exists=True,
            completion_gate={"complete": True},
        )

        self.assertEqual(qc["status"], FAILED_TECHNICAL_QC)
        self.assertFalse(qc["release_ready"])

    def test_missing_metadata_distinguishes_draft_release_package(self) -> None:
        qc = build_release_readiness_qc(
            final_audio=verified_audio(),
            metadata_payload=build_release_metadata_payload({"title": "Draft"}),
            rights_payload=clear_rights(),
            deliverable_manifest={"deliverables": [{"type": "final_master", "available": True}]},
            qc_report_exists=True,
            master_qc_report_exists=True,
            release_qc_report_exists=True,
            release_manifest_exists=True,
            rights_checklist_exists=True,
            completion_gate={"complete": True},
        )

        self.assertEqual(qc["status"], DRAFT_RELEASE_PACKAGE)
        self.assertFalse(qc["release_ready"])
        self.assertIn("required release metadata is incomplete", qc["blocking_issues"])

    def test_uncleared_sample_rights_needs_rights_clearance(self) -> None:
        qc = build_release_readiness_qc(
            final_audio=verified_audio(),
            metadata_payload=complete_metadata(),
            rights_payload=build_rights_payload(
                contains_samples=True,
                all_samples_owned_or_cleared=None,
                source_ownership_confirmed=True,
                vocal_performer_consent=True,
                explicit_content_flag_set=True,
            ),
            deliverable_manifest={"deliverables": [{"type": "final_master", "available": True}]},
            qc_report_exists=True,
            master_qc_report_exists=True,
            release_qc_report_exists=True,
            release_manifest_exists=True,
            rights_checklist_exists=True,
            completion_gate={"complete": True},
        )

        self.assertEqual(qc["status"], NEEDS_RIGHTS_CLEARANCE)
        self.assertFalse(qc["release_ready"])

    def test_ready_status_requires_average_score_and_reports_but_not_commercial_success_claim(self) -> None:
        qc = build_release_readiness_qc(
            final_audio=verified_audio(),
            metadata_payload=complete_metadata(),
            rights_payload=clear_rights(),
            mix_master={"mix_priorities": ["vocal_forwardness", "controlled_808"], "style_target": "commercial_digicore_hyperpop"},
            arrangement={"categories": [{"name": "Hook impact", "score": 5}, {"name": "Arrangement intentionality", "score": 5}]},
            deliverable_manifest={"deliverables": [{"type": "final_master", "available": True}]},
            qc_report_exists=True,
            master_qc_report_exists=True,
            release_qc_report_exists=True,
            release_manifest_exists=True,
            rights_checklist_exists=True,
            completion_gate={"complete": True},
        )

        self.assertEqual(qc["status"], RELEASE_PACKAGE_READY)
        self.assertTrue(qc["release_ready"])
        self.assertGreaterEqual(qc["average_score"], 4.0)
        self.assertFalse(qc["commercial_success_claimed"])
        self.assertIn("does not guarantee distributor approval", render_release_readiness_qc_report(qc))


if __name__ == "__main__":
    unittest.main()

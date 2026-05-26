from __future__ import annotations

import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from release_metadata import build_release_metadata_payload  # noqa: E402
from release_qc import build_release_qc, render_release_qc_report  # noqa: E402
from rights_clearance_checklist import build_rights_payload  # noqa: E402


class ReleaseQCTests(unittest.TestCase):
    def test_release_qc_blocks_incomplete_audio_metadata_and_rights(self) -> None:
        qc = build_release_qc(
            final_master={"verified": False},
            metadata_payload=build_release_metadata_payload({}),
            rights_payload=build_rights_payload(contains_samples=True),
            deliverable_manifest={"deliverables": [{"type": "final_master", "available": False}]},
        )

        self.assertFalse(qc["release_ready"])
        self.assertIn("final master audio is not verified", qc["blocking_issues"])
        self.assertIn("required release metadata is incomplete", qc["blocking_issues"])
        self.assertIn("final master deliverable is missing", qc["blocking_issues"])

    def test_cover_art_missing_only_blocks_when_required(self) -> None:
        metadata = build_release_metadata_payload(
            {
                "title": "Track",
                "artist": "Artist",
                "genre": "hip_hop",
                "language": "ko",
                "explicit": False,
                "copyright_year": "2026",
                "copyright_owner": "Artist",
                "producer": "Producer",
                "composer": "Composer",
            }
        )
        rights = build_rights_payload(source_ownership_confirmed=True, vocal_performer_consent=True, explicit_content_flag_set=True)
        deliverables = {"deliverables": [{"type": "final_master", "available": True}]}

        allowed = build_release_qc(
            final_master={
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
            },
            metadata_payload=metadata,
            rights_payload=rights,
            deliverable_manifest=deliverables,
            cover_art_present=False,
            artwork_required=False,
        )
        blocked = build_release_qc(
            final_master={
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
            },
            metadata_payload=metadata,
            rights_payload=rights,
            deliverable_manifest=deliverables,
            cover_art_present=False,
            artwork_required=True,
        )

        self.assertTrue(allowed["release_ready"])
        self.assertFalse(blocked["release_ready"])
        self.assertIn("cover art is required", " ".join(blocked["blocking_issues"]))
        self.assertIn("does not guarantee distribution approval", render_release_qc_report(blocked))


if __name__ == "__main__":
    unittest.main()

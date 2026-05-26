from __future__ import annotations

import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from rights_clearance_checklist import (  # noqa: E402
    build_rights_payload,
    render_cover_art_requirements,
    render_distribution_checklist,
    render_rights_clearance_checklist,
)


class RightsClearanceChecklistTests(unittest.TestCase):
    def test_uncleared_sample_blocks_release_ready(self) -> None:
        payload = build_rights_payload(
            contains_samples=True,
            all_samples_owned_or_cleared=None,
            source_ownership_confirmed=True,
            vocal_performer_consent=True,
            explicit_content_flag_set=True,
        )

        self.assertFalse(payload["release_ready"])
        self.assertIn("samples are used", " ".join(payload["blocking_issues"]))

    def test_confirmed_rights_are_ready(self) -> None:
        payload = build_rights_payload(
            contains_samples=False,
            source_ownership_confirmed=True,
            vocal_performer_consent=True,
            featured_artist_metadata_complete=True,
            explicit_content_flag_set=True,
        )

        self.assertTrue(payload["release_ready"])
        self.assertTrue(payload["rights"]["uses_reference_style_only"])
        self.assertFalse(payload["rights"]["voice_clone_used"])

    def test_checklists_include_required_policy_items(self) -> None:
        payload = build_rights_payload(source_ownership_confirmed=True, vocal_performer_consent=True, explicit_content_flag_set=True)
        rights_text = render_rights_clearance_checklist(payload)
        distribution_text = render_distribution_checklist({"title": "Track"}, cover_art_present=False, final_audio_verified=True)
        cover_text = render_cover_art_requirements()

        self.assertIn("sample ownership", rights_text)
        self.assertIn("no web audio download", rights_text)
        self.assertIn("no voice clone", rights_text)
        self.assertIn("ISRC if available", distribution_text)
        self.assertIn("final audio verified", distribution_text)
        self.assertIn("does not block local audio completion", cover_text)


if __name__ == "__main__":
    unittest.main()

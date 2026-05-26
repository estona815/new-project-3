from __future__ import annotations

import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from deliverable_audio_profiles import build_deliverable_profiles, profile_by_id  # noqa: E402


class DeliverableAudioProfilesTests(unittest.TestCase):
    def test_acapella_and_stems_are_not_faked_without_sources(self) -> None:
        payload = build_deliverable_profiles(
            requested_profiles=["acapella_if_available", "stems_if_provided"],
            input_mode="instrumental_beat",
            isolated_vocal_available=False,
            stems_provided=False,
            stem_separation_verified=False,
        )

        acapella = profile_by_id(payload, "acapella_if_available")
        stems = profile_by_id(payload, "stems_if_provided")
        self.assertFalse(acapella["available"])
        self.assertFalse(stems["available"])
        self.assertIn("isolated vocal or stems required", acapella["blocking_reasons"])
        self.assertIn("verified stem separation missing", " ".join(stems["blocking_reasons"]))

    def test_stems_available_when_provided_not_generated_claim(self) -> None:
        payload = build_deliverable_profiles(input_mode="stems", stems_provided=True)
        stems = profile_by_id(payload, "stems_if_provided")

        self.assertTrue(stems["available"])
        self.assertIn("stems provided", stems["claim"])

    def test_mp3_preview_optional_unless_requested(self) -> None:
        optional = build_deliverable_profiles(requested_profiles=["final_master_wav24_48k"], mp3_preview_created=False)
        requested = build_deliverable_profiles(requested_profiles=["mp3_preview"], mp3_preview_created=False)

        self.assertEqual(profile_by_id(optional, "mp3_preview")["blocking_reasons"], [])
        self.assertIn("requested MP3 preview not created", profile_by_id(requested, "mp3_preview")["blocking_reasons"])


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from production_intent_resolver import resolve_production_intent  # noqa: E402


class ProductionIntentResolverTests(unittest.TestCase):
    def test_release_ready_korean_request_keeps_scope_limited(self) -> None:
        intent = resolve_production_intent(
            {
                "workflow": "song_to_mix_master",
                "mode": "full_song_stereo",
                "rough_request": "마음대로 상업 음악 퀄로 뽑아줘. 릴스 첫 15초 훅 터지게.",
            }
        )

        self.assertTrue(intent["release_ready_requested"])
        self.assertIn("arrangement_autopilot", intent["actions"])
        self.assertIn("composition_idea_generation", intent["actions"])
        self.assertIn("does not guarantee distribution approval or commercial success", intent["release_ready_definition"])

    def test_copying_phrase_requires_owned_source_and_blocks_exact_copy(self) -> None:
        intent = resolve_production_intent(
            {
                "workflow": "song_to_mix_master",
                "mode": "full_song_stereo",
                "rough_request": "웨스트우드 Just Touched Down 킥 베이스 그대로 따와라.",
                "owned_reference_sample": False,
                "owned_reference_stems": False,
            }
        )

        self.assertEqual(intent["safety"]["copying_risk"], "high")
        self.assertFalse(intent["safety"]["exact_copy_allowed"])
        self.assertTrue(intent["safety"]["requires_user_owned_source"])
        self.assertFalse(intent["safety"]["vocal_identity_clone_allowed"])


if __name__ == "__main__":
    unittest.main()

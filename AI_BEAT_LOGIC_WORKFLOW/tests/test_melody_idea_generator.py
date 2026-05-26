from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from melody_idea_generator import build_melody_idea_guide, choose_main_hook_source, infer_emotional_direction  # noqa: E402


class MelodyIdeaGeneratorTests(unittest.TestCase):
    def test_sample_motif_wins_when_sample_requested(self) -> None:
        source = choose_main_hook_source(
            sample_analysis={"motif_hook_detection": {"hook_motif_candidates": [{"start": 0.0}]}},
            vocal_to_code={"phrases": [{"phrase_id": "v1"}]},
            rough_request="샘플 줄게 이걸로 훅",
        )

        self.assertEqual(source, "sample_motif")

    def test_vocal_phrase_guides_without_exact_transcription(self) -> None:
        guide = build_melody_idea_guide(
            rough_request="보컬 살려서 훅",
            vocal_to_code={"phrases": [{"phrase_id": "v1"}]},
            key={"confidence": "low"},
        )
        text = json.dumps(guide).lower()

        self.assertEqual(guide["status"], "COMPOSITION_GUIDE_READY")
        self.assertEqual(guide["ideas"][0]["source"], "vocal_phrase")
        self.assertIn("not exact transcription", text)
        self.assertIn("no exact melody", text)

    def test_system_seoul_defaults_playful(self) -> None:
        self.assertEqual(infer_emotional_direction("SYSTEM SEOUL 결", "system_seoul_adjacent"), "playful")


if __name__ == "__main__":
    unittest.main()

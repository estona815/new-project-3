from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from topline_guide_generator import build_topline_guide, generate_topline_ideas  # noqa: E402


class ToplineGuideGeneratorTests(unittest.TestCase):
    def test_vocal_to_code_supports_placement_but_not_transcription(self) -> None:
        ideas = generate_topline_ideas(
            rough_request="보컬 줄게 멜로디 살려",
            vocal_to_code={"phrases": [{"phrase_id": "lead_1", "start": 0.5, "end": 1.8}]},
            style_target="commercial_digicore_hyperpop",
        )

        self.assertEqual(ideas[0]["confidence"], "medium")
        self.assertEqual(ideas[0]["phrase_hints"][0]["placement_use"], "support hook placement; not exact transcription")
        self.assertEqual(ideas[0]["tuning_direction"], "stronger_tuning_guide")

    def test_topline_guide_blocks_voice_clone_and_lyrics_copy(self) -> None:
        guide = build_topline_guide(rough_request="Jane Remover 결 보컬")
        text = json.dumps(guide).lower()

        self.assertFalse(guide["safety"]["voice_clone"])
        self.assertIn("no voice cloning", text)
        self.assertIn("do not copy reference lyrics", text)


if __name__ == "__main__":
    unittest.main()

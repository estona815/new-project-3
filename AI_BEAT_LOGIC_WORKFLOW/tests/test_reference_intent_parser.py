from __future__ import annotations

import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_DIR))

from reference_intent_parser import parse_reference_intent  # noqa: E402


class ReferenceIntentParserTests(unittest.TestCase):
    def test_love_blur_drums_produces_concrete_drum_direction(self) -> None:
        parsed = parse_reference_intent("love blur 느낌 드럼")
        style = parsed["style_targets"]
        request = parsed["reference_requests"][0]

        self.assertIn("digicore", style["genre_family"])
        self.assertIn("underground_hiphop", style["genre_family"])
        self.assertGreaterEqual(style["drum_density"], 4)
        self.assertGreaterEqual(style["brightness"], 4)
        self.assertEqual(request["reference_title"], "Love Blur")
        self.assertEqual(request["target_element"], "drums")
        self.assertEqual(request["action"], "make_like_reference")
        self.assertIn(request["confidence"], {"low", "medium"})
        self.assertIn("generic trap loop", parsed["avoid"])
        self.assertIn("cheap rage clipping", parsed["avoid"])

    def test_vague_mood_request_becomes_parameters(self) -> None:
        parsed = parse_reference_intent("emotional hyperpop but not too rage")
        style = parsed["style_targets"]

        self.assertIn("hyperpop", style["genre_family"])
        self.assertGreaterEqual(style["energy"], 4)
        self.assertGreaterEqual(style["brightness"], 4)
        self.assertLessEqual(style["808_distortion"], 3)
        self.assertIn("overclipped rage distortion", parsed["avoid"])

    def test_underground_vocal_request_sets_vocal_forwardness(self) -> None:
        parsed = parse_reference_intent("underground rap vocal upfront, airy adlibs")
        style = parsed["style_targets"]

        self.assertIn("underground_hiphop", style["genre_family"])
        self.assertEqual(style["vocal_forwardness"], 4)
        self.assertGreaterEqual(style["reverb_wetness"], 3)

    def test_creative_brief_avoid_and_priority_affect_parameters(self) -> None:
        parsed = parse_reference_intent(
            "soft intro then hard hook",
            avoid_text="muddy 808, overcompressed master",
            priority="reels impact",
            drum_direction="love_blur_inspired_energetic_digital_drums",
            vocal_direction="rap_forward",
            master_direction="loud_demo",
        )
        style = parsed["style_targets"]

        self.assertGreaterEqual(style["energy"], 4)
        self.assertGreaterEqual(style["drum_density"], 4)
        self.assertEqual(style["vocal_forwardness"], 4)
        self.assertIn("muddy 808", parsed["avoid"])
        self.assertIn("overcompressed master", parsed["avoid"])

    def test_multiple_targets_in_one_sentence(self) -> None:
        parsed = parse_reference_intent("보컬은 랩 앞으로, 드럼은 Love Blur 느낌")
        requests = {(item["target_element"], item["action"]) for item in parsed["reference_requests"]}

        self.assertIn(("vocal", "make_more_forward"), requests)
        self.assertIn(("drums", "make_like_reference"), requests)
        self.assertEqual(parsed["explicit_targets"]["vocal"]["forwardness"], 5)
        self.assertGreaterEqual(parsed["explicit_targets"]["drums"]["density"], 4)

    def test_melody_preservation_with_stronger_808(self) -> None:
        parsed = parse_reference_intent("멜로디는 살리고 808만 더 세게")

        self.assertTrue(parsed["explicit_targets"]["melody"]["preserve"])
        self.assertGreaterEqual(parsed["explicit_targets"]["bass_808"]["sub_weight"], 4)
        self.assertEqual(parsed["explicit_targets"]["bass_808"]["priority"], "support_melody")
        self.assertIn("melody-covering 808", parsed["avoid"])


if __name__ == "__main__":
    unittest.main()

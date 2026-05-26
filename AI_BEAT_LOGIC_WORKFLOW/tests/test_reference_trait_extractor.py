from __future__ import annotations

import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_DIR))

from reference_intent_parser import parse_reference_intent  # noqa: E402
from reference_trait_extractor import extract_reference_traits  # noqa: E402


class ReferenceTraitExtractorTests(unittest.TestCase):
    def traits(self, phrase: str, web_research: dict | None = None) -> dict:
        parsed = parse_reference_intent(phrase)
        return extract_reference_traits(user_phrase=phrase, parsed_intent=parsed, web_research=web_research)

    def test_korean_arbitrary_drum_request_is_low_confidence_and_concrete(self) -> None:
        traits = self.traits("ㅇㅇㅇ 느낌 드럼으로 수정")

        self.assertIn("drums", traits["target_elements"])
        self.assertEqual(traits["confidence"], "low")
        self.assertIn("exact copying", traits["avoid"])
        self.assertGreaterEqual(traits["drums"]["density"], 3)
        self.assertGreaterEqual(traits["drums"]["hat_density"], 3)
        self.assertIn(traits["drums"]["kick_character"], {"short_punchy", "soft", "distorted", "clicky", "subby"})

    def test_love_blur_drum_traits_are_specific_without_exact_pattern(self) -> None:
        traits = self.traits("Love Blur 느낌 드럼")

        self.assertIn("drums", traits["target_elements"])
        self.assertGreaterEqual(traits["drums"]["density"], 4)
        self.assertEqual(traits["drums"]["kick_character"], "short_punchy")
        self.assertEqual(traits["drums"]["snare_clap_character"], "digital")
        self.assertIn("generic trap loop", traits["avoid"])
        self.assertIn("cheap rage clipping", traits["avoid"])
        self.assertNotEqual(traits["drums"]["copying_risk"], "high")

    def test_multi_target_phrase_preserves_vocal_melody_and_808_priority(self) -> None:
        traits = self.traits("보컬은 랩 앞으로, 드럼은 Love Blur 느낌, 808은 더 세게 근데 멜로디는 살려")

        self.assertEqual(traits["vocal"]["lead_position"], "very_front")
        self.assertIn("drums", traits["target_elements"])
        self.assertIn("bass_808", traits["target_elements"])
        self.assertGreaterEqual(traits["bass_808"]["sub_weight"], 4)
        self.assertTrue(traits["melody"]["preserve"])
        self.assertIn("vocal chop dominating melody", traits["avoid"])

    def test_web_unavailable_does_not_create_source_claims(self) -> None:
        traits = self.traits(
            "내 목소리를 Nate Sib처럼",
            {
                "web_access_available": False,
                "web_reference_research_unavailable": True,
                "sources": [],
                "combined_confidence": "low",
                "notes": [],
            },
        )

        self.assertEqual(traits["confidence"], "low")
        self.assertFalse(traits["vocal"]["identity_clone_allowed"])
        self.assertIn("web confidence: low", traits["evidence_summary"])
        self.assertNotIn("official_artist", " ".join(traits["evidence_summary"]))

    def test_normalized_schema_is_stable_for_complex_korean_prompt(self) -> None:
        phrase = (
            "보컬은 랩 앞으로, 드럼은 더 세게, 808은 더 세게 근데 멜로디는 살려. "
            "신디를 패닝해서 공간감 있게, 서브는 중앙. 디카페이터 살짝 걸고 릴스 첫 15초 안에 훅."
        )
        traits = self.traits(phrase)

        self.assertTrue(traits["drums"]["active"])
        self.assertIn(traits["drums"]["kick_character"], {"short_punchy", "subby", "clicky", "distorted", "soft", "unknown"})
        self.assertGreaterEqual(traits["drums"]["kick_low_weight"], 1)
        self.assertGreaterEqual(traits["drums"]["kick_transient"], 1)
        self.assertTrue(traits["bass_808"]["active"])
        self.assertGreaterEqual(traits["bass_808"]["sub_weight"], 4)
        self.assertTrue(traits["bass_808"]["must_not_mask_melody"])
        self.assertTrue(traits["bass_808"]["sidechain_needed"])
        self.assertTrue(traits["bass_808"]["mono_sub_required"])
        self.assertTrue(traits["synth_width"]["active"])
        self.assertEqual(traits["synth_width"]["low_frequency_mono_cutoff_hz"], 120)
        self.assertTrue(traits["synth_width"]["widen_upper_layers_only"])
        self.assertTrue(traits["vocal"]["active"])
        self.assertEqual(traits["vocal"]["requested_plugin"], "Soundtoys Decapitator")
        self.assertEqual(traits["vocal"]["saturation"], "subtle")
        self.assertTrue(traits["vocal"]["deess_required"])
        self.assertFalse(traits["vocal"]["identity_clone_allowed"])
        self.assertTrue(traits["arrangement"]["hook_early"])
        self.assertEqual(traits["arrangement"]["target_hook_seconds"], 15)
        self.assertEqual(traits["master"]["target"], "master_ready_headroom")
        self.assertFalse(traits["safety"]["exact_copy_allowed"])
        self.assertIn(traits["safety"]["evidence_mode"], {"text_only", "web_informed", "audio_informed", "owned_sample"})

    def test_scene_style_cluster_activates_controlled_targets(self) -> None:
        traits = self.traits("좀 더 2hollis처럼, ycs, SYSTEM SEOUL처럼 바꿔줘")

        self.assertTrue(traits["drums"]["active"])
        self.assertGreaterEqual(traits["drums"]["density"], 4)
        self.assertTrue(traits["drums"]["avoid_generic_trap"])
        self.assertTrue(traits["bass_808"]["active"])
        self.assertGreaterEqual(traits["bass_808"]["sub_weight"], 4)
        self.assertTrue(traits["synth_width"]["active"])
        self.assertTrue(traits["vocal"]["active"])
        self.assertEqual(traits["vocal"]["pitch_correction"], "medium")
        self.assertTrue(traits["arrangement"]["hook_early"])
        self.assertTrue(traits["arrangement"]["reduce_random_ai_glitch"])

    def test_take_request_sets_safety_without_allowing_exact_copy(self) -> None:
        traits = self.traits("웨스트우드 Just Touched Down 베이스랑 킥을 따와라")

        self.assertEqual(traits["safety"]["copying_risk"], "high")
        self.assertFalse(traits["safety"]["exact_copy_allowed"])
        self.assertTrue(traits["safety"]["requires_user_owned_source_for_sampling"])
        self.assertEqual(traits["safety"]["evidence_mode"], "text_only")


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_DIR))

from paths import ensure_folder_structure  # noqa: E402
from reference_intent_parser import parse_reference_intent  # noqa: E402
from reference_profile import build_reference_target_profile  # noqa: E402
from style_translation import run_reference_targeting  # noqa: E402


class KoreanReferencePhraseTests(unittest.TestCase):
    def test_placeholder_song_bass_like_is_low_confidence(self) -> None:
        parsed = parse_reference_intent("ㅇㅇㅇ이라는 곡 베이스처럼 쳐줘")
        request = parsed["reference_requests"][0]

        self.assertEqual(parsed["language"], "ko")
        self.assertEqual(request["reference_title"], "ㅇㅇㅇ")
        self.assertIn(request["target_element"], {"bass", "808"})
        self.assertEqual(request["action"], "make_like_reference")
        self.assertEqual(request["confidence"], "low")
        self.assertTrue(request["requires_reference_audio_for_accuracy"])
        self.assertIn("Reference is used for high-level production attributes only", request["safety_note"])
        self.assertEqual(parsed["explicit_targets"]["bass_808"]["priority"], "support_melody")
        self.assertIn("muddy low-end", parsed["avoid"])

    def test_bass_like_without_title_is_generic_low_confidence(self) -> None:
        parsed = parse_reference_intent("베이스처럼 쳐줘")
        request = parsed["reference_requests"][0]

        self.assertEqual(request["reference_title"], "unknown title")
        self.assertEqual(request["target_element"], "bass")
        self.assertEqual(request["confidence"], "low")
        self.assertTrue(request["requires_reference_audio_for_accuracy"])

    def test_love_blur_drums_become_concrete_targets(self) -> None:
        parsed = parse_reference_intent("Love Blur 느낌 드럼")
        drums = parsed["explicit_targets"]["drums"]
        bass = parsed["explicit_targets"]["bass_808"]

        self.assertEqual(parsed["reference_requests"][0]["reference_title"], "Love Blur")
        self.assertEqual(parsed["reference_requests"][0]["target_element"], "drums")
        self.assertGreaterEqual(drums["density"], 4)
        self.assertGreaterEqual(drums["transient_sharpness"], 4)
        self.assertTrue(drums["avoid_random_glitch"])
        self.assertEqual(bass["priority"], "support_melody")
        self.assertIn("generic trap loop", parsed["avoid"])
        self.assertIn("cheap rage clipping", parsed["avoid"])
        self.assertIn("random AI glitch", parsed["avoid"])

    def test_vocal_forward_and_love_blur_drums_parse_multiple_targets(self) -> None:
        parsed = parse_reference_intent("보컬은 랩 앞으로, 드럼은 Love Blur 느낌")
        requests = {(item["target_element"], item["action"]) for item in parsed["reference_requests"]}

        self.assertIn(("vocal", "make_more_forward"), requests)
        self.assertIn(("drums", "make_like_reference"), requests)
        self.assertEqual(parsed["explicit_targets"]["vocal"]["forwardness"], 5)
        self.assertGreaterEqual(parsed["explicit_targets"]["drums"]["density"], 4)

    def test_artist_style_vocal_prompt_is_traits_only_not_identity_clone(self) -> None:
        parsed = parse_reference_intent("내 목소리를 Nate Sib처럼")
        request = parsed["reference_requests"][0]

        self.assertEqual(request["reference_title"], "Nate Sib")
        self.assertEqual(request["target_element"], "vocal")
        self.assertEqual(request["action"], "match_vocal_production_traits")
        self.assertIn(request["confidence"], {"low", "medium"})
        self.assertFalse(request["identity_clone_allowed"])
        self.assertIn("production traits only", request["identity_safety_note"])
        self.assertEqual(parsed["explicit_targets"]["vocal"]["tuning"], "medium")
        self.assertGreaterEqual(parsed["explicit_targets"]["vocal"]["brightness"], 4)
        self.assertIn("voice identity cloning", parsed["avoid"])

        profile = build_reference_target_profile("내 목소리를 Nate Sib처럼", None)
        self.assertEqual(profile["parsed_intent"]["target_elements"], ["vocal"])
        self.assertEqual(profile["parsed_intent"]["reference_titles"], ["Nate Sib"])
        self.assertEqual(profile["vocal_targets"]["lead_position"], "front")
        self.assertIn("production-trait targets only", " ".join(profile["legal_and_accuracy_notes"]))

    def test_melody_preserved_and_808_stronger_without_covering(self) -> None:
        parsed = parse_reference_intent("멜로디는 살리고 808만 더 세게")
        bass = parsed["explicit_targets"]["bass_808"]

        self.assertTrue(parsed["explicit_targets"]["melody"]["preserve"])
        self.assertGreaterEqual(bass["sub_weight"], 4)
        self.assertEqual(bass["priority"], "support_melody")
        self.assertIn("melody-covering 808", parsed["avoid"])

    def test_808_glide_and_reels_hook_parse(self) -> None:
        parsed = parse_reference_intent("이 곡처럼 808 글라이드 넣어줘. 릴스용으로 첫 15초 안에 훅 터지게")

        self.assertEqual(parsed["explicit_targets"]["bass_808"]["glide"], 5)
        self.assertTrue(parsed["explicit_targets"]["arrangement"]["hook_early"])
        self.assertEqual(parsed["explicit_targets"]["arrangement"]["target_hook_seconds"], 15)

    def test_digicore_drums_less_chaotic(self) -> None:
        parsed = parse_reference_intent("digicore 감성인데 드럼은 덜 난잡하게")

        self.assertIn("digicore", parsed["style_targets"]["genre_family"])
        self.assertLessEqual(parsed["explicit_targets"]["drums"]["fill_amount"], 2)
        self.assertTrue(parsed["explicit_targets"]["drums"]["avoid_random_glitch"])

    def test_style_translation_includes_structured_parse_and_safety(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_root = Path(tmp) / "AI_BEAT_LOGIC_WORKFLOW"
            ensure_folder_structure(project_root)
            paths = run_reference_targeting({"reference_text": "ㅇㅇㅇ이라는 곡 베이스처럼 쳐줘"}, project_root)
            profile = json.loads(paths["reference_target_profile"].read_text(encoding="utf-8"))
            translation = paths["style_translation"].read_text(encoding="utf-8")

        self.assertEqual(profile["parsed_intent"]["reference_requests"][0]["reference_title"], "ㅇㅇㅇ")
        self.assertEqual(profile["source"]["confidence"], "low")
        self.assertEqual(profile["parsed_intent"]["target_elements"], ["bass"])
        self.assertIn("legal_and_accuracy_notes", profile)
        self.assertIn("original user phrase", translation)
        self.assertIn("bass", translation)
        self.assertIn("Reference Audio Need", translation)
        self.assertIn("No exact reference bass sound", translation)
        self.assertIn("fallback processing is limited", translation)

    def test_take_bass_and_kick_is_safe_trait_translation(self) -> None:
        phrase = "웨스트우드 Just Touched Down 베이스랑 킥을 따와라"
        profile = build_reference_target_profile(phrase, None)
        requests = profile["parsed_intent"]["reference_requests"]
        traits = profile["reference_traits"]
        combined_notes = " ".join(profile["notes"] + profile["legal_and_accuracy_notes"])

        self.assertEqual({item["target_element"] for item in requests}, {"bass", "drums"})
        self.assertTrue(all(item["action"] == "reference_inspired_trait_match" for item in requests))
        self.assertTrue(all(item["sample_use_policy"] == "licensed_or_owned_source_required" for item in requests))
        self.assertIn("bass_808", traits["target_elements"])
        self.assertIn("drums", traits["target_elements"])
        self.assertEqual(traits["drums"]["kick_character"], "short_punchy")
        self.assertGreaterEqual(traits["drums"]["transient_sharpness"], 4)
        self.assertGreaterEqual(traits["bass_808"]["sub_weight"], 4)
        self.assertIn("exact kick sample copying", profile["avoid"])
        self.assertIn("exact bassline copying", profile["avoid"])
        self.assertIn("licensed or owned", combined_notes)

    def test_autotune_and_decapitator_are_processing_traits(self) -> None:
        parsed = parse_reference_intent("보컬을 좀 더 오토튠 걸고 디카페이터 걸어라")
        profile = build_reference_target_profile("보컬을 좀 더 오토튠 걸고 디카페이터 걸어라", None)
        traits = profile["reference_traits"]

        self.assertEqual(parsed["explicit_targets"]["processing"]["autotune"], "medium")
        self.assertEqual(parsed["explicit_targets"]["processing"]["saturation_style"], "decapitator_style_saturation")
        self.assertEqual(traits["vocal"]["tuning"], "medium")
        self.assertEqual(traits["vocal"]["saturation"], "medium")
        self.assertIn("Decapitator-style saturation", traits["vocal"]["plugin_style_reference"])
        self.assertIn("harsh vocal distortion", profile["avoid"])

    def test_broad_artist_scene_references_do_not_clone_identity(self) -> None:
        profile = build_reference_target_profile("좀 더 2hollis처럼, ycs, SYSTEM SEOUL처럼 바꿔줘", None)
        titles = set(profile["parsed_intent"]["reference_titles"])
        traits = profile["reference_traits"]

        self.assertTrue({"2hollis", "ycs", "SYSTEM SEOUL"} <= titles)
        self.assertIn("digicore", profile["style_targets"]["genre_family"])
        self.assertIn("hyperpop", profile["style_targets"]["genre_family"])
        self.assertFalse(traits["vocal"]["identity_clone_allowed"])
        self.assertIn("artist vocal identity cloning", traits["avoid"])
        self.assertIn("exact producer clone", profile["avoid"])

    def test_synth_panning_keeps_sub_center(self) -> None:
        profile = build_reference_target_profile("신디를 패닝해서 공간감 있게, 서브는 중앙에 둬", None)
        traits = profile["reference_traits"]

        self.assertIn("synth_width", traits["target_elements"])
        self.assertTrue(traits["synth_width"]["mono_compatibility_required"])
        self.assertEqual(traits["synth_width"]["low_frequency_mono_cutoff_hz"], 120)
        self.assertEqual(traits["synth_width"]["mid_side_approach"], "keep_melody_center_widen_layers")
        self.assertTrue(traits["bass_808"]["mono_sub_required"])

    def test_keep_my_voice_bright_strong_digicore(self) -> None:
        profile = build_reference_target_profile("내 목소리는 유지하되 더 밝고 세게, 디지코어식으로", None)
        traits = profile["reference_traits"]

        self.assertIn("digicore", profile["style_targets"]["genre_family"])
        self.assertFalse(traits["vocal"]["identity_clone_allowed"])
        self.assertTrue(traits["vocal"]["identity_preserve"])
        self.assertGreaterEqual(traits["vocal"]["brightness"], 4)
        self.assertIn(traits["vocal"]["lead_position"], {"front", "very_front"})
        self.assertIn("voice identity replacement", profile["avoid"])

    def test_stronger_drums_preserve_melody_and_avoid_cheap_clipping(self) -> None:
        profile = build_reference_target_profile("드럼은 더 세게, 근데 멜로디 덮지 말고 cheap rage clipping은 피하라", None)
        traits = profile["reference_traits"]

        self.assertIn("drums", traits["target_elements"])
        self.assertGreaterEqual(traits["drums"]["density"], 4)
        self.assertGreaterEqual(traits["drums"]["transient_sharpness"], 4)
        self.assertTrue(traits["melody"]["preserve"])
        self.assertIn("cheap rage clipping", traits["avoid"])
        self.assertIn("overclipped rage distortion", profile["avoid"])

    def test_reels_first_15_seconds_hook(self) -> None:
        profile = build_reference_target_profile("릴스 첫 15초 안에 훅 터지게", None)
        traits = profile["reference_traits"]

        self.assertIn("arrangement", traits["target_elements"])
        self.assertTrue(traits["arrangement"]["hook_early"])
        self.assertEqual(traits["arrangement"]["target_hook_seconds"], 15)


if __name__ == "__main__":
    unittest.main()

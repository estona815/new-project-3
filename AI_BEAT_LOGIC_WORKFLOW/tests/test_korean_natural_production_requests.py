from __future__ import annotations

import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_DIR))

from reference_intent_parser import parse_reference_intent  # noqa: E402
from reference_profile import build_reference_target_profile  # noqa: E402
from reference_trait_extractor import extract_reference_traits  # noqa: E402
from style_translation import render_style_translation  # noqa: E402


class KoreanNaturalProductionRequestTests(unittest.TestCase):
    def assert_targets(self, phrase: str, expected: set[str]) -> dict:
        parsed = parse_reference_intent(phrase)
        self.assertTrue(expected <= set(parsed["target_elements"]), parsed)
        return parsed

    def test_westwood_just_touched_down_take_variants_are_safe_trait_match(self) -> None:
        phrases = [
            "웨스트우드 Just Touched Down 베이스랑 킥을 따와라",
            "웨스트 우드 저스트 터치다운 베이스 킥 따와",
            "westwood just touched down 킥 베이스 느낌",
            "저스트터치다운 베이스처럼",
            "just touchdown 808처럼",
            "웨스트우드 곡 킥처럼 쳐줘",
        ]
        for phrase in phrases:
            with self.subTest(phrase=phrase):
                parsed = self.assert_targets(phrase, {"kick", "bass_808"})
                self.assertEqual(parsed["production_traits"]["reference_artist"], "Westwood")
                self.assertEqual(parsed["production_traits"]["reference_title"], "JUST TOUCHED DOWN")
                self.assertIn("reference_inspired_trait_match", parsed["actions"])
                self.assertFalse(parsed["exact_copy_allowed"])
                self.assertFalse(parsed["vocal_identity_clone_allowed"])
                self.assertIn(parsed["confidence"], {"low", "high"})
                self.assertIn("kick_punch", parsed["production_traits"])
                self.assertIn("kick_transient_sharpness", parsed["production_traits"])
                self.assertIn("bass_sub_weight", parsed["production_traits"])
                self.assertIn("bass_tone", parsed["production_traits"])
                self.assertIn("melody_masking_risk", parsed["production_traits"])
                self.assertIn("sidechain_or_automation_recommendation", parsed["production_traits"])

        copying = parse_reference_intent("웨스트우드 Just Touched Down 베이스랑 킥을 따와라")
        self.assertTrue(copying["production_traits"]["user_requested_copying"])
        self.assertEqual(copying["copying_risk"], "high")
        self.assertTrue(copying["requires_user_owned_source_for_sampling"])
        profile = build_reference_target_profile(copying["raw_text"], None)
        translation = render_style_translation(profile)
        self.assertFalse(profile["copying_policy"]["exact_copy_allowed"])
        self.assertNotIn("sample_layering", profile["copying_policy"]["allowed_actions"])
        self.assertIn("high_level_trait_match", profile["copying_policy"]["allowed_actions"])
        self.assertIn("정확한 킥/베이스 샘플 복사가 아니라", translation)
        self.assertIn("high_level_trait_match", translation)
        self.assertIn("download_reference_audio", profile["copying_policy"]["disallowed_actions"])

        non_copying = parse_reference_intent("westwood just touched down 킥 베이스 느낌")
        self.assertFalse(non_copying["production_traits"]["user_requested_copying"])
        self.assertIn(non_copying["copying_risk"], {"low", "medium"})

    def test_vocal_autotune_decapitator_variants_are_processing_only(self) -> None:
        cases = {
            "오토튠 더": "medium",
            "autotune 더 세게": "hard_effect",
            "하드튠": "hard_effect",
            "보컬을 좀 더 오토튠 걸고 디카페이터 걸어라": "medium",
            "디카페이터 살짝": "subtle",
            "디카페이터 빡세게": "hard_effect",
            "데카피테이터": "medium",
            "decapitator": "medium",
            "saturation 걸어": "medium",
            "보컬 찢어지게 말고 따뜻하게": "subtle",
        }
        for phrase, intensity in cases.items():
            with self.subTest(phrase=phrase):
                parsed = self.assert_targets(phrase, {"vocal"})
                traits = parsed["production_traits"]
                self.assertIn("vocal_processing", parsed["actions"])
                self.assertEqual(traits["pitch_correction_intensity"], intensity)
                self.assertFalse(traits["plugin_exact_application_allowed"])
                self.assertIn("approximation", traits["fallback_plugin_note"])
                self.assertTrue(traits["preserve_user_voice_identity"])
                self.assertFalse(parsed["vocal_identity_clone_allowed"])
                self.assertIn("deessing_after_saturation", traits)
                self.assertIn("logic_plugin_detection_manual_checklist", traits)

    def test_style_scene_variants_become_style_translation_only(self) -> None:
        phrases = [
            "좀 더 2hollis처럼, ycs, SYSTEM SEOUL처럼 바꿔줘",
            "투홀리스처럼",
            "2홀리스",
            "ycs처럼",
            "와이씨에스",
            "시스템서울",
            "시스템 서울",
            "ss-pop 느낌",
            "국내 디지코어 느낌",
            "인터넷 감성",
            "2000년대 온라인 느낌",
            "게임 사운드트랙 느낌",
            "하이퍼팝인데 덜 싸게",
        ]
        expected = {"whole_style", "drums", "bass_808", "synth_width", "vocal", "arrangement"}
        for phrase in phrases:
            with self.subTest(phrase=phrase):
                parsed = self.assert_targets(phrase, expected)
                self.assertIn("style_translation", parsed["actions"])
                self.assertFalse(parsed["exact_copy_allowed"])
                self.assertFalse(parsed["vocal_identity_clone_allowed"])
                traits = parsed["production_traits"]
                self.assertIn("energetic_internet_digicore_hyperpop_direction", traits["style_direction"])
                self.assertEqual(traits["artist_identity_clone_allowed"], False)
                self.assertIn("generic trap loop", parsed["avoid"])
                self.assertIn("random AI glitch", parsed["avoid"])
                self.assertIn("cheap rage clipping", parsed["avoid"])

    def test_synth_width_and_sub_center_variants(self) -> None:
        phrases = [
            "신디를 패닝해서 공간감 있게, 서브는 중앙에 둬",
            "신스를 좌우로 벌려",
            "패닝으로 넓혀",
            "공간감",
            "와이드하게",
            "스테레오 넓게",
            "베이스는 넓게 근데 서브는 중앙",
            "808은 중앙, 위에 하모닉만 넓혀",
        ]
        for phrase in phrases:
            with self.subTest(phrase=phrase):
                parsed = self.assert_targets(phrase, {"synth_width", "bass_808"})
                traits = parsed["production_traits"]
                self.assertTrue(traits["sub_mono_required"])
                self.assertEqual(traits["mono_sub_cutoff_hz"], 120)
                self.assertTrue(traits["wide_upper_harmonics_allowed"])
                self.assertTrue(traits["avoid_panning_sub"])
                self.assertTrue(traits["mono_compatibility_check_required"])
                self.assertIn("high_pass_widened_duplicate_hz", traits)
                self.assertIn("stereo_only_limitation_warning", traits)

    def test_preserve_my_voice_variants_block_identity_clone(self) -> None:
        phrases = [
            "내 목소리는 유지하되 더 밝고 세게",
            "내 목소리 유지",
            "목소리는 내껄로",
            "목소리 복제 말고",
            "보컬 앞으로",
            "밝게",
            "세게",
            "투홀리스처럼 보컬",
            "Nate Sib처럼",
            "랩 보컬 앞으로",
        ]
        for phrase in phrases:
            with self.subTest(phrase=phrase):
                parsed = self.assert_targets(phrase, {"vocal"})
                traits = parsed["production_traits"]
                self.assertTrue(traits["preserve_user_voice_identity"])
                self.assertFalse(parsed["vocal_identity_clone_allowed"])
                self.assertIn(traits["lead_vocal_position"], {"front", "very_front"})
                self.assertIn(traits["brightness"], {"medium", "high", "controlled_high"})
                self.assertIn(traits["compression"], {"medium", "strong"})
                self.assertIn("no voice clone", " ".join(parsed["safety_notes"]).lower())

    def test_trait_extractor_exposes_extended_vocal_and_bass_traits(self) -> None:
        parsed = parse_reference_intent("웨스트우드 Just Touched Down 베이스랑 킥을 따와라")
        traits = extract_reference_traits(user_phrase=parsed["raw_text"], parsed_intent=parsed)
        self.assertIn("bass_808", traits["target_elements"])
        self.assertIn("drums", traits["target_elements"])
        self.assertTrue(traits["bass_808"]["mono_sub_required"])

    def test_full_complex_request_routes_all_natural_language_targets(self) -> None:
        phrase = (
            "웨스트우드 Just Touched Down 킥 베이스 느낌, 보컬 오토튠 더 걸고 디카페이터 살짝, "
            "2hollis ycs 시스템서울처럼, 신디는 넓게, 서브는 중앙, 릴스 첫 15초 훅"
        )
        parsed = parse_reference_intent(phrase)
        profile = build_reference_target_profile(phrase, None)
        traits = profile["reference_traits"]

        self.assertTrue({"kick", "bass_808", "vocal", "synth_width", "arrangement", "whole_style"} <= set(parsed["target_elements"]))
        self.assertIn(parsed["copying_risk"], {"medium", "high"})
        self.assertIn("vocal_processing", parsed["actions"])
        self.assertIn("style_translation", parsed["actions"])
        self.assertTrue(traits["synth_width"]["active"])
        self.assertTrue(traits["bass_808"]["mono_sub_required"])
        self.assertEqual(traits["vocal"]["requested_plugin"], "Soundtoys Decapitator")
        self.assertEqual(traits["vocal"]["saturation"], "subtle")
        self.assertTrue(traits["arrangement"]["hook_early"])
        self.assertEqual(traits["arrangement"]["target_hook_seconds"], 15)
        self.assertFalse(traits["safety"]["exact_copy_allowed"])
        self.assertTrue(traits["safety"]["requires_user_owned_source_for_sampling"])
        self.assertTrue(profile["parsed_intent"]["safety_note"])
        self.assertIn("No voice clone", " ".join(parsed["safety_notes"]))


if __name__ == "__main__":
    unittest.main()

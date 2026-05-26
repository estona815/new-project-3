from __future__ import annotations

import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_DIR))

from edit_plan_generator import build_edit_plan  # noqa: E402
from humanization_rubric import reference_match_qc  # noqa: E402
from reference_profile import build_reference_target_profile  # noqa: E402


class ArbitraryReferencePromptTests(unittest.TestCase):
    def profile(self, phrase: str) -> dict:
        return build_reference_target_profile(phrase, None)

    def test_arbitrary_drum_feel_prompt_is_low_confidence_direction(self) -> None:
        profile = self.profile("ㅇㅇㅇ 느낌 드럼으로 수정")

        self.assertIn("drums", profile["reference_traits"]["target_elements"])
        self.assertEqual(profile["reference_traits"]["confidence"], "low")
        self.assertIn("drums", profile["parsed_intent"]["target_elements"])
        self.assertIn("exact copying", profile["reference_traits"]["avoid"])
        self.assertGreaterEqual(profile["reference_traits"]["drums"]["density"], 3)
        self.assertIn(profile["reference_traits"]["drums"]["kick_character"], {"short_punchy", "soft", "distorted", "clicky", "subby"})
        self.assertEqual(profile["source"]["support"], "text-only")

    def test_placeholder_reference_with_web_metadata_stays_low_confidence(self) -> None:
        profile = build_reference_target_profile(
            "ㅇㅇㅇ 느낌 드럼으로 수정",
            None,
            web_research={
                "query": "ㅇㅇㅇ",
                "web_access_available": True,
                "sources": [],
                "combined_confidence": "low",
                "source_limitations": ["placeholder reference has no actionable artist/title for web lookup"],
                "trait_inference_allowed": False,
            },
        )

        self.assertEqual(profile["source"]["confidence"], "low")
        self.assertEqual(profile["source"]["support"], "text-only")
        self.assertFalse(profile["reference_traits"]["trait_inference_allowed"])
        self.assertIn("reference audio", " ".join(profile["notes"]).lower())

    def test_bass_reference_with_synth_panning_keeps_sub_mono(self) -> None:
        phrase = "ㅇㅇㅇㅇ 베이스처럼 신디를 패닝 줘서 공간감"
        profile = self.profile(phrase)
        traits = profile["reference_traits"]

        self.assertIn("bass_808", traits["target_elements"])
        self.assertIn("synth_width", traits["target_elements"])
        self.assertTrue(traits["bass_808"]["mono_sub_required"])
        self.assertTrue(traits["bass_808"]["wide_upper_harmonics_allowed"])
        self.assertEqual(traits["synth_width"]["low_frequency_mono_cutoff_hz"], 120)
        self.assertTrue(traits["synth_width"]["mono_compatibility_required"])

    def test_artist_vocal_reference_keeps_user_voice_identity(self) -> None:
        profile = self.profile("보컬은 2hollis/Nate Sib 쪽 느낌인데 내 목소리 유지")
        traits = profile["reference_traits"]

        self.assertEqual(traits["target_elements"], ["vocal"])
        self.assertFalse(traits["vocal"]["identity_clone_allowed"])
        self.assertIn(traits["vocal"]["lead_position"], {"front", "very_front"})
        self.assertIn("artist vocal identity cloning", traits["avoid"])

    def test_love_blur_drums_remain_concrete_but_not_exact_pattern(self) -> None:
        profile = self.profile("Love Blur 느낌 드럼")
        traits = profile["reference_traits"]

        self.assertIn("drums", traits["target_elements"])
        self.assertGreaterEqual(traits["drums"]["density"], 4)
        self.assertEqual(traits["drums"]["kick_character"], "short_punchy")
        self.assertIn("generic trap loop", traits["avoid"])
        self.assertIn("cheap rage clipping", traits["avoid"])
        self.assertNotIn("exact pattern copying", " ".join(profile["drum_targets"]["manual_logic_notes"]).lower())
        self.assertIn("Exact melody, sample, drum pattern, lyrics, or sound recording copying is not performed.", profile["legal_and_accuracy_notes"])

    def test_808_glide_and_melody_preservation_prompts(self) -> None:
        glide = self.profile("이 곡처럼 808 글라이드")
        preserve = self.profile("멜로디는 살리고 808만 더 세게")

        self.assertIn("bass_808", glide["reference_traits"]["target_elements"])
        self.assertEqual(glide["reference_traits"]["bass_808"]["glide"], 5)
        self.assertTrue(preserve["reference_traits"]["melody"]["preserve"])
        self.assertGreaterEqual(preserve["reference_traits"]["bass_808"]["sub_weight"], 4)

    def test_multi_target_request_preserves_vocal_and_melody_balance(self) -> None:
        phrase = "보컬은 랩 앞으로, 드럼은 Love Blur 느낌, 808은 더 세게 근데 멜로디는 살려"
        profile = self.profile(phrase)
        traits = profile["reference_traits"]
        qc = reference_match_qc(
            profile,
            verification={"passed": True, "ok": True, "format_verified": True, "clipping_count": 0},
            options={"project_mode": "vocal_plus_beat", "vocal_mode": "front"},
            source_type="logic_export",
            completion_gate_complete=True,
            qc_report_exists=True,
            master_qc_report_exists=True,
        )

        self.assertEqual(traits["vocal"]["lead_position"], "very_front")
        self.assertIn("drums", traits["target_elements"])
        self.assertGreaterEqual(traits["bass_808"]["sub_weight"], 4)
        self.assertTrue(traits["melody"]["preserve"])
        score_names = " ".join(item["name"] for item in qc["scores"])
        self.assertIn("Vocal reference direction match", score_names)
        self.assertIn("Melody/vibe preservation", score_names)

    def test_synth_width_plan_in_edit_plan(self) -> None:
        profile = self.profile("신스는 좌우로 벌리고, 멜로디는 중앙에 남겨")
        analysis = {
            "metadata": {"duration_seconds": 60.0},
            "arrangement_candidates": {},
            "silence_detection": {},
            "vocal_like_texture_candidates": [],
            "melody_buried_candidates": [],
            "low_end_excess_candidates": [],
        }

        plan = build_edit_plan(analysis, {"mode": "full_song_stereo", "input": "/tmp/stereo.wav"}, profile)

        self.assertIn("## Synth Width / Panning Plan", plan)
        self.assertIn("sub and fundamental low-end must stay mono/centered", plan)
        self.assertIn("High-pass the widened layer around 120-180 Hz", plan)
        self.assertIn("heuristic/stereo-only guidance", plan)

    def test_reference_application_logic_section_covers_stereo_bass_and_width_rules(self) -> None:
        profile = self.profile("ㅇㅇㅇㅇ 베이스처럼 신디를 패닝 줘서 공간감")
        analysis = {
            "metadata": {"duration_seconds": 60.0},
            "arrangement_candidates": {},
            "silence_detection": {},
            "vocal_like_texture_candidates": [],
            "melody_buried_candidates": [],
            "low_end_excess_candidates": [],
        }

        plan = build_edit_plan(analysis, {"mode": "full_song_stereo", "input": "/tmp/stereo.wav"}, profile)

        self.assertIn("## Reference Application in Logic Pro", plan)
        self.assertIn("### B. Bass / 808 Like Reference", plan)
        self.assertIn("Keep sub below roughly 120Hz mono/centered", plan)
        self.assertIn("not true bassline replacement", plan)
        self.assertIn("### C. Synth Panning / Spatial Width", plan)
        self.assertIn("Do not widen sub frequencies", plan)
        self.assertIn("high-pass duplicate layer around 120-180Hz", plan)
        self.assertIn("warn about phase/mono risk", plan)

    def test_reference_application_logic_section_is_artist_vocal_safe(self) -> None:
        profile = self.profile("내 목소리를 Nate Sib처럼")
        analysis = {
            "metadata": {"duration_seconds": 60.0},
            "arrangement_candidates": {},
            "silence_detection": {},
            "vocal_like_texture_candidates": [],
            "melody_buried_candidates": [],
            "low_end_excess_candidates": [],
        }

        plan = build_edit_plan(analysis, {"project_mode": "vocal_plus_beat"}, profile)

        self.assertIn("### D. Vocal Like Artist", plan)
        self.assertIn("do not clone the artist's voice", plan)
        self.assertIn("Translate to vocal production traits only", plan)
        self.assertIn("Keep the user's own vocal identity", plan)
        self.assertIn("not exact imitation", plan)

    def test_complex_creative_target_maps_to_safe_production_targets(self) -> None:
        phrase = """ㅇㅇㅇ 느낌 드럼으로 수정해줘.
ㅇㅇㅇㅇ 베이스처럼 신디를 패닝해서 공간감 있게 해줘.
서브는 중앙에 단단히 두고, 위쪽 신스만 좌우로 넓혀.
내 목소리는 Nate Sib처럼 앞으로 나오고 밝고 세게, 근데 목소리 복제 말고 내 목소리 정체성은 유지.
멜로디 감정은 살리고, 808은 더 강하지만 멜로디를 덮지 않게.
generic trap loop, 싸구려 rage clipping, random AI glitch는 피하고,
릴스 첫 15초 안에 훅이 나오게."""
        profile = self.profile(phrase)
        traits = profile["reference_traits"]
        analysis = {
            "metadata": {"duration_seconds": 60.0},
            "arrangement_candidates": {},
            "silence_detection": {},
            "vocal_like_texture_candidates": [],
            "melody_buried_candidates": [],
            "low_end_excess_candidates": [],
        }

        plan = build_edit_plan(
            analysis,
            {"mode": "full_song_stereo", "project_mode": "vocal_plus_beat", "vocal_mode": "front", "input": "/tmp/stereo.wav"},
            profile,
        )
        lowered_plan = plan.lower()

        self.assertEqual(profile["source"]["confidence"], "low")
        self.assertTrue({"drums", "bass_808", "synth_width", "vocal", "melody", "arrangement"} <= set(traits["target_elements"]))
        self.assertGreaterEqual(traits["drums"]["density"], 4)
        self.assertIn("exact copying", traits["avoid"])
        self.assertIn("generic trap loop", traits["avoid"])
        self.assertIn("cheap rage clipping", traits["avoid"])
        self.assertIn("random AI glitch", traits["avoid"])
        self.assertGreaterEqual(traits["bass_808"]["sub_weight"], 4)
        self.assertTrue(traits["bass_808"]["mono_sub_required"])
        self.assertTrue(traits["bass_808"]["wide_upper_harmonics_allowed"])
        self.assertEqual(traits["synth_width"]["low_frequency_mono_cutoff_hz"], 120)
        self.assertTrue(traits["synth_width"]["mono_compatibility_required"])
        self.assertFalse(traits["vocal"]["identity_clone_allowed"])
        self.assertEqual(traits["vocal"]["lead_position"], "front")
        self.assertGreaterEqual(traits["vocal"]["brightness"], 4)
        self.assertTrue(traits["melody"]["preserve"])
        self.assertTrue(traits["arrangement"]["hook_early"])
        self.assertEqual(traits["arrangement"]["target_hook_seconds"], 15)
        self.assertIn("high-pass duplicate layer around 120-180hz", lowered_plan)
        self.assertIn("mono compatibility", lowered_plan)
        self.assertIn("do not clone the artist's voice", lowered_plan)
        self.assertIn("stem-level", lowered_plan)
        self.assertNotIn("pan sub bass", lowered_plan)
        self.assertNotIn("clone nate sib voice", lowered_plan)


if __name__ == "__main__":
    unittest.main()

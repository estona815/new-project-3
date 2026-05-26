from __future__ import annotations

import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_DIR))

from edit_plan_generator import build_edit_plan  # noqa: E402
from reference_profile import build_reference_target_profile  # noqa: E402
from style_translation import render_style_translation  # noqa: E402


ANALYSIS_STUB = {
    "metadata": {"duration_seconds": 60.0},
    "arrangement_candidates": {},
    "silence_detection": {},
    "vocal_like_texture_candidates": [],
    "melody_buried_candidates": [],
    "low_end_excess_candidates": [],
}


class SynthWidthBassPanningTests(unittest.TestCase):
    def test_bass_like_synth_panning_keeps_sub_mono_and_mentions_mono_compatibility(self) -> None:
        phrase = "ㅇㅇㅇㅇ 베이스처럼 신디를 패닝 줘서 공간감"
        profile = build_reference_target_profile(phrase, None)
        traits = profile["reference_traits"]
        plan = build_edit_plan(ANALYSIS_STUB, {"mode": "full_song_stereo", "input": "/tmp/stereo.wav"}, profile)
        translation = render_style_translation(profile)
        combined = f"{plan}\n{translation}".lower()

        self.assertIn("bass_808", traits["target_elements"])
        self.assertIn("synth_width", traits["target_elements"])
        self.assertTrue(traits["bass_808"]["mono_sub_required"])
        self.assertTrue(traits["bass_808"]["wide_upper_harmonics_allowed"])
        self.assertIn("low_frequency_mono_cutoff_hz", traits["synth_width"])
        self.assertEqual(traits["synth_width"]["low_frequency_mono_cutoff_hz"], 120)
        self.assertNotIn("pan sub bass", combined)
        self.assertNotIn("pan the sub", combined)
        self.assertIn("do not widen sub frequencies", combined)
        self.assertIn("mono compatibility", combined)

    def test_stereo_only_width_plan_warns_about_phase_and_manual_layers(self) -> None:
        profile = build_reference_target_profile("저 곡처럼 베이스는 넓게, 서브는 단단하게", None)
        plan = build_edit_plan(ANALYSIS_STUB, {"mode": "full_song_stereo", "input": "/tmp/stereo.wav"}, profile)

        self.assertIn("Stereo-only warning", plan)
        self.assertIn("stem-level panning requires stems or manual Logic layers", plan)
        self.assertIn("warn about phase/mono risk", plan)
        self.assertIn("Keep sub below roughly 120Hz mono/centered", plan)


if __name__ == "__main__":
    unittest.main()

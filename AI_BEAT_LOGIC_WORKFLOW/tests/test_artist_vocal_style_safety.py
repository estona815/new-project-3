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


class ArtistVocalStyleSafetyTests(unittest.TestCase):
    def test_nate_sib_vocal_prompt_is_production_style_only(self) -> None:
        profile = build_reference_target_profile("내 목소리를 Nate Sib처럼", None)
        traits = profile["reference_traits"]
        translation = render_style_translation(profile)
        plan = build_edit_plan(ANALYSIS_STUB, {"project_mode": "vocal_plus_beat"}, profile)
        combined = f"{translation}\n{plan}".lower()

        self.assertIn("vocal", traits["target_elements"])
        self.assertFalse(traits["vocal"]["identity_clone_allowed"])
        self.assertIn(profile["source"]["confidence"], {"low", "medium"})
        self.assertIn("production-trait targets only", translation)
        self.assertIn("keep the user's own vocal identity", combined)
        self.assertNotIn("clone nate sib voice", combined)
        self.assertNotIn("exact vocal match", combined)
        self.assertNotIn("exact imitation", combined.replace("not exact imitation", ""))

    def test_vocal_style_with_reference_audio_still_disallows_identity_clone(self) -> None:
        profile = build_reference_target_profile(
            "내 목소리를 Nate Sib처럼",
            "/tmp/reference.wav",
            web_research={"combined_confidence": "medium", "sources": [{"source_type": "review", "relevant_claims": ["bright forward vocal"]}]},
        )
        profile["audio_analysis"]["available"] = True
        profile["source"]["confidence"] = "high"
        traits = profile["reference_traits"]

        self.assertFalse(traits["vocal"]["identity_clone_allowed"])
        self.assertIn("artist vocal identity cloning", traits["avoid"])
        self.assertNotIn("voice identity cloning is allowed", render_style_translation(profile).lower())


if __name__ == "__main__":
    unittest.main()

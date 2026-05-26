from __future__ import annotations

import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from arrangement_qc import score_arrangement_plan  # noqa: E402


class ArrangementQCTests(unittest.TestCase):
    def test_good_arrangement_plan_scores_plan_pass(self) -> None:
        plan = {
            "section_progression_guide": {
                "sections": [
                    {"name": "hook", "start": 0},
                    {"name": "verse"},
                    {"name": "contrast"},
                    {"name": "final_hook"},
                ]
            },
            "sample_chop_guide": {"loop_candidates": [{"start": 0, "end": 4}]},
            "drum_programming_guide": {"kick_character": "short"},
            "bass_808_midi_guide": {"sub_mono": True},
            "melody_variation_guide": {"preserve_original_emotional_motif": True, "variation_moves": ["mute"]},
            "logic_manual_plan": ["Create markers"],
        }
        qc = score_arrangement_plan(
            plan,
            sample_analysis={"timing": {"confidence": "medium"}, "tonal": {"confidence": "medium"}, "motif_hook_detection": {"hook_motif_candidates": [{"start": 0}]}},
            vocal_to_code={"phrases": [{"phrase_id": "vocal_phrase_001"}]},
            song_structure={"hook_candidates": [{"start": 0}]},
        )

        self.assertGreaterEqual(qc["average_score"], 4.0)
        self.assertTrue(qc["plan_pass"])
        self.assertTrue(qc["manual_logic_required"])

    def test_unreliable_bpm_key_needs_more_input(self) -> None:
        qc = score_arrangement_plan(
            {"section_progression_guide": {"sections": [{"name": "intro"}]}},
            sample_analysis={"timing": {"confidence": "low"}, "tonal": {"confidence": "low"}},
            vocal_to_code={"phrases": []},
            song_structure={"hook_candidates": []},
        )

        self.assertTrue(qc["needs_more_input"])
        self.assertFalse(qc["plan_pass"])


if __name__ == "__main__":
    unittest.main()

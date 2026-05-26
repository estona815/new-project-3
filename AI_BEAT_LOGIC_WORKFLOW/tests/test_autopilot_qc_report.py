from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from autopilot_qc_report import build_autopilot_qc, render_autopilot_qc_report, write_autopilot_qc_reports  # noqa: E402


def good_plan() -> dict:
    return {
        "section_progression_guide": {"sections": [{"name": "hook"}, {"name": "verse"}, {"name": "contrast"}, {"name": "final_hook"}]},
        "sample_chop_guide": {"loop_candidates": [{"start": 0}]},
        "drum_programming_guide": {"kick_character": "short"},
        "bass_808_midi_guide": {"sub_mono": True},
        "melody_variation_guide": {"preserve_original_emotional_motif": True, "variation_moves": ["mute"]},
        "logic_manual_plan": ["Manual Logic required"],
    }


class AutopilotQCReportTests(unittest.TestCase):
    def test_report_writes_three_markdown_files_without_complete_overclaim(self) -> None:
        payload = build_autopilot_qc(
            arrangement_plan=good_plan(),
            sample_analysis={"timing": {"confidence": "medium"}, "tonal": {"confidence": "medium"}, "motif_hook_detection": {"hook_motif_candidates": [{"start": 0}]}},
            vocal_to_code={"phrases": [{"phrase_id": "one"}]},
            song_structure={"hook_candidates": [{"start": 0}]},
            mix_master_plan={"mix_priorities": ["vocal_forwardness", "controlled_808"], "commercial_style_target": ["no random AI harshness"], "false_claim_guards": {}},
        )
        markdown = render_autopilot_qc_report(payload)

        self.assertEqual(payload["status"], "PLAN_PASS")
        self.assertFalse(payload["complete"])
        self.assertIn("PLAN_PASS is not COMPLETE", markdown)

        with tempfile.TemporaryDirectory() as tmp:
            paths = write_autopilot_qc_reports(tmp, payload)
            self.assertTrue(paths["arrangement_qc_report"].exists())
            self.assertTrue(paths["commercial_readiness_report"].exists())
            self.assertTrue(paths["autopilot_qc_report"].exists())


if __name__ == "__main__":
    unittest.main()

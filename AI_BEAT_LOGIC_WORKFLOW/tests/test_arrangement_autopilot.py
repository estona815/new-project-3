from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from arrangement_autopilot import PLAN_STATUS, build_arrangement_autopilot_plan, run_arrangement_autopilot  # noqa: E402


SAMPLE_ANALYSIS = {
    "schema_version": "sample_analysis.v1",
    "metadata": {"duration_seconds": 8.0},
    "timing": {"bpm": 150, "confidence": "medium"},
    "tonal": {"estimated_key": "F# minor", "confidence": "medium"},
    "loop_detection": {"loopable_regions": [{"start": 0.0, "end": 4.0, "loop_score": 0.8, "confidence": "medium"}]},
    "motif_hook_detection": {"hook_motif_candidates": [{"start": 0.0, "end": 2.0, "confidence": "medium"}]},
    "transient_onset": {"onset_density": 2.0},
    "sample_usage_safety": {"ownership_status": "unknown", "direct_sample_use_allowed": False},
}

VOCAL_TO_CODE = {
    "schema_version": "vocal_to_code.v1",
    "phrases": [{"phrase_id": "vocal_phrase_001", "start": 0.5, "end": 2.0}],
    "false_claim_guard": {"auto_tune_applied": False, "note_transcription_is_exact": False},
}

SONG_STRUCTURE = {
    "schema_version": "song_structure_analysis.v1",
    "input": {"mode": "full_song_stereo"},
    "sections": [{"name": "hook", "start": 8.0, "end": 24.0}],
    "hook_candidates": [{"start": 8.0, "end": 24.0, "confidence": "medium"}],
    "low_end_excess_candidates": [{"start": 8.0, "end": 12.0}],
    "melody_buried_candidates": [],
}


class ArrangementAutopilotTests(unittest.TestCase):
    def test_plan_ready_is_not_complete_and_has_guides(self) -> None:
        plan = build_arrangement_autopilot_plan(
            sample_analysis=SAMPLE_ANALYSIS,
            vocal_to_code=VOCAL_TO_CODE,
            song_structure_analysis=SONG_STRUCTURE,
            length_mode="short_30sec",
            genre="commercial_digicore_hyperpop",
            request_text="상업 디지코어 훅 빨리",
        )
        text = json.dumps(plan).lower()

        self.assertEqual(plan["schema_version"], "arrangement_plan.v1")
        self.assertEqual(plan["status"], PLAN_STATUS)
        self.assertFalse(plan["complete"])
        self.assertFalse(plan["status_policy"]["complete_may_print"])
        self.assertIn("section_progression_guide", plan)
        self.assertIn("bass_808_midi_guide", plan)
        self.assertIn("sample_chop_guide", plan)
        self.assertIn("no exact song", text)
        self.assertIn("no true drum rewrite is claimed", text)

    def test_run_arrangement_autopilot_writes_required_outputs_without_final_wav(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            analysis = root / "01_ANALYSIS"
            edit = root / "02_EDIT_PLAN"
            analysis.mkdir()
            edit.mkdir()
            (analysis / "sample_analysis.json").write_text(json.dumps(SAMPLE_ANALYSIS), encoding="utf-8")
            (analysis / "vocal_to_code.json").write_text(json.dumps(VOCAL_TO_CODE), encoding="utf-8")
            (analysis / "song_structure_analysis.json").write_text(json.dumps(SONG_STRUCTURE), encoding="utf-8")
            (edit / "creative_brief.json").write_text(json.dumps({"length": {"mode": "reels_15sec"}}), encoding="utf-8")

            result = run_arrangement_autopilot(project_root=root, genre="digicore")
            paths = result["paths"]

            for key in (
                "json",
                "markdown",
                "section_progression_guide",
                "chord_progression_guide",
                "bass_808_midi_guide",
                "drum_programming_guide",
                "sample_chop_guide",
                "melody_variation_guide",
            ):
                self.assertTrue(paths[key].exists(), key)
            parsed = json.loads(paths["json"].read_text(encoding="utf-8"))
            markdown = paths["markdown"].read_text(encoding="utf-8")
            self.assertEqual(parsed["status"], PLAN_STATUS)
            self.assertFalse(parsed["complete"])
            self.assertFalse((root / "05_FINAL_WAV").exists())
            self.assertNotIn("COMPLETE", markdown)


if __name__ == "__main__":
    unittest.main()

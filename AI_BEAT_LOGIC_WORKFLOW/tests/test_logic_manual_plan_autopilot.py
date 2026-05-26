from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from arrangement_autopilot import run_arrangement_autopilot  # noqa: E402


class LogicManualPlanAutopilotTests(unittest.TestCase):
    def test_autopilot_writes_midi_automation_and_logic_guides(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "01_ANALYSIS").mkdir()
            (root / "02_EDIT_PLAN").mkdir()
            sample_analysis = {
                "schema_version": "sample_analysis.v1",
                "timing": {"bpm": 148, "confidence": "medium"},
                "tonal": {"estimated_key": "F# minor", "confidence": "low"},
                "loop_detection": {"loopable_regions": [{"start": 0.0, "end": 7.78, "estimated_bars": 4, "confidence": "medium"}]},
                "motif_hook_detection": {"hook_motif_candidates": [{"start": 0.0, "end": 2.0, "confidence": "medium"}]},
                "sample_usage_safety": {"ownership_status": "unknown", "direct_sample_use_allowed": False},
            }
            vocal_to_code = {
                "phrases": [{"phrase_id": "vocal_phrase_001", "start": 1.0, "end": 2.0}],
                "pitch_correction_guide": {
                    "recommended_mode": "subtle",
                    "manual_logic_required": True,
                    "claim_language": "recommended, not applied",
                },
            }
            (root / "01_ANALYSIS" / "sample_analysis.json").write_text(json.dumps(sample_analysis), encoding="utf-8")
            (root / "01_ANALYSIS" / "vocal_to_code.json").write_text(json.dumps(vocal_to_code), encoding="utf-8")

            result = run_arrangement_autopilot(project_root=root, genre="digicore", length_mode="short_30sec")
            paths = result["paths"]

            for key in (
                "midi_region_guide",
                "automation_guide",
                "drum_midi_guide",
                "bass_808_midi_guide",
                "vocal_pitch_guide",
                "logic_arrangement_plan",
                "logic_autopilot_status",
            ):
                self.assertTrue(paths[key].exists(), key)
            midi = json.loads(paths["midi_region_guide"].read_text(encoding="utf-8"))
            status = json.loads(paths["logic_autopilot_status"].read_text(encoding="utf-8"))
            manual = paths["logic_arrangement_plan"].read_text(encoding="utf-8")

            self.assertFalse(midi["claim_guard"]["midi_imported_into_logic"])
            self.assertEqual(status["status"], "manual_required")
            self.assertFalse(status["plugins_inserted"])
            self.assertIn("## Drum programming", manual)
            self.assertIn("## QC checklist", manual)
            self.assertNotIn("COMPLETE", manual)


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from arrangement_autopilot import build_arrangement_autopilot_plan, run_arrangement_autopilot  # noqa: E402
from automation_guide import build_automation_guide  # noqa: E402
from bass_808_midi_pattern_export import generate_bass_808_midi_pattern_guide  # noqa: E402
from drum_midi_pattern_export import generate_drum_midi_guide  # noqa: E402
from midi_region_guide import build_midi_region_guide  # noqa: E402
from production_package_builder import build_production_package, write_production_package  # noqa: E402


SAMPLE_ANALYSIS = {
    "schema_version": "sample_analysis.v1",
    "timing": {"bpm": 148, "confidence": "medium", "bpm_candidates": [74, 148]},
    "tonal": {"estimated_key": "F# minor", "confidence": "low"},
    "loop_detection": {"loopable_regions": [{"start": 0.0, "end": 4.0, "confidence": "medium"}]},
    "motif_hook_detection": {"hook_motif_candidates": [{"start": 0.0, "end": 1.2}]},
    "transient_onset": {"onset_density": 2.5},
    "sample_usage_safety": {"ownership_status": "unknown", "direct_sample_use_allowed": False},
}


class ProductionPackageBuilderTests(unittest.TestCase):
    def test_build_package_contains_required_sections_and_claim_guards(self) -> None:
        arrangement = build_arrangement_autopilot_plan(
            sample_analysis=SAMPLE_ANALYSIS,
            genre="commercial_digicore_hyperpop",
            request_text="상업 디지코어 릴스 훅",
        )
        drum_midi = generate_drum_midi_guide(arrangement)
        bass_midi = generate_bass_808_midi_pattern_guide(arrangement)
        midi = build_midi_region_guide(arrangement, drum_midi_guide=drum_midi, bass_808_midi_guide=bass_midi)
        automation = build_automation_guide(arrangement, midi)
        package = build_production_package(
            arrangement,
            midi_region_guide=midi,
            automation_guide=automation,
            creative_brief={"mode": "full_song_stereo", "input_files": {"main_input": "song.wav"}},
        )

        for key in (
            "song_structure",
            "section_plan",
            "chord_progression_guide",
            "sample_chop_guide",
            "drum_programming_guide",
            "bass_808_midi_guide",
            "synth_width_panning_guide",
            "vocal_guide",
            "automation_guide",
            "mix_prep_checklist",
            "master_target",
            "manual_logic_requirements",
        ):
            self.assertIn(key, package)
        self.assertEqual(package["schema_version"], "production_package_manifest.v1")
        self.assertFalse(package["complete"])
        self.assertFalse(package["claim_guard"]["logic_automation_success"])
        self.assertTrue(package["production_todo"])

    def test_write_package_outputs_manifest_todo_and_mix_checklist(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            package = {
                "schema_version": "production_package_manifest.v1",
                "status": "PRODUCTION_PACKAGE_READY",
                "complete": False,
                "capabilities": {"stereo_only": True, "stems_available": False},
                "sample_chop_guide": {"direct_sample_use_allowed": False},
                "production_todo": [],
                "mix_prep_checklist": ["Check headroom"],
            }

            paths = write_production_package(root, package)

            self.assertTrue(paths["manifest"].exists())
            self.assertTrue(paths["todo"].exists())
            self.assertTrue(paths["mix_prep_checklist"].exists())

    def test_arrangement_autopilot_writes_production_package_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "01_ANALYSIS").mkdir()
            (root / "02_EDIT_PLAN").mkdir()
            (root / "01_ANALYSIS" / "sample_analysis.json").write_text(json.dumps(SAMPLE_ANALYSIS), encoding="utf-8")

            result = run_arrangement_autopilot(project_root=root, genre="digicore", request_text="릴스 훅 편곡")
            paths = result["paths"]

            self.assertTrue(paths["production_package_manifest"].exists())
            self.assertTrue(paths["production_todo"].exists())
            self.assertTrue(paths["mix_prep_checklist"].exists())
            manifest = json.loads(paths["production_package_manifest"].read_text(encoding="utf-8"))
            self.assertEqual(manifest["status"], "PRODUCTION_PACKAGE_READY")
            self.assertFalse(manifest["claim_guard"]["logic_automation_success"])
            self.assertFalse((root / "05_FINAL_WAV").exists())


if __name__ == "__main__":
    unittest.main()

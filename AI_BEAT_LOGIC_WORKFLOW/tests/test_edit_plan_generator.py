from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_DIR))

from edit_plan_generator import write_edit_plan  # noqa: E402
from paths import ensure_folder_structure  # noqa: E402


def fixture_analysis() -> dict:
    return {
        "metadata": {"duration_seconds": 118.0, "sample_rate": 48000, "channels": 2},
        "silence_detection": {
            "intro_silence": {"start": 0.0, "end": 1.25},
            "outro_silence": None,
            "internal_silence_candidates": [],
        },
        "vocal_like_texture_candidates": [
            {
                "start": 12.0,
                "end": 18.5,
                "confidence": "medium",
                "reason": "centered 300Hz-3kHz texture with chop-like transients (heuristic only)",
            }
        ],
        "melody_buried_candidates": [
            {
                "start": 44.0,
                "end": 50.0,
                "confidence": "medium",
                "reason": "low-end and transients dominate melody proxy",
            }
        ],
        "low_end_excess_candidates": [
            {
                "start": 32.0,
                "end": 40.0,
                "confidence": "medium",
                "reason": "sub proxy dominates mid energy",
            }
        ],
        "arrangement_candidates": {
            "intro": {"start": 0.0, "end": 4.0},
            "first_hook_or_main_motif_entrance": {"start": 32.0, "end": 40.0, "confidence": "medium"},
            "drop": {"start": 16.0, "end": 24.0, "confidence": "medium"},
            "repeated_loop_blocks": [
                {"start": 64.0, "end": 80.0, "reason": "similar adjacent loudness/energy windows"}
            ],
            "outro": {"start": 108.0, "end": 118.0},
            "ai_random_transition_or_glitch_candidates": [
                {"start": 23.5, "end": 24.5, "reason": "abrupt heuristic spectral/loudness novelty change"}
            ],
            "main_melody_strongest_region": {
                "start": 32.0,
                "end": 40.0,
                "reason": "highest combined energy and onset density heuristic",
            },
        },
    }


class EditPlanGeneratorTests(unittest.TestCase):
    def test_edit_plan_includes_required_sections_and_timestamps(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_root = Path(tmp) / "AI_BEAT_LOGIC_WORKFLOW"
            ensure_folder_structure(project_root)
            analysis_path = project_root / "01_ANALYSIS" / "analysis.json"
            output_path = project_root / "02_EDIT_PLAN" / "edit_plan.md"
            analysis_path.write_text(json.dumps(fixture_analysis()), encoding="utf-8")

            write_edit_plan(
                analysis_path=analysis_path,
                output_path=output_path,
                options={
                    "length_mode": "under_2min",
                    "vocal_mode": "suppress",
                    "melody_focus": "front",
                    "drum_808": "strong_controlled",
                    "export_format": "wav24_48k",
                    "save_logic_project": True,
                },
            )
            text = output_path.read_text(encoding="utf-8")

            for heading in [
                "Project Objective",
                "User Settings",
                "Arrangement Plan",
                "Melody-Forward Mix Plan",
                "Vocal Chop / AI Texture Suppression Plan",
                "Drum / 808 Plan",
                "AI-Feel Reduction Plan",
                "Sound Polish Plan",
                "Logic Pro Manual Checklist",
                "Fallback Processing Notes",
            ]:
                self.assertIn(heading, text)

            self.assertIn("0:32.00-0:40.00", text)
            self.assertIn("0:12.00-0:18.50", text)
            self.assertIn("0:23.50-0:24.50", text)
            self.assertIn("Create a new Logic Pro project", text)
            self.assertIn("cannot truly remix stems from a single stereo file", text)
            self.assertIn("does not mean the beat has already been humanized", text)


if __name__ == "__main__":
    unittest.main()


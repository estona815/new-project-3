from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_DIR))

from edit_plan_generator import build_edit_plan  # noqa: E402
from master_qc import build_master_qc_report  # noqa: E402
from vocal_chain_planner import build_vocal_chain_plan  # noqa: E402
from vocal_fx_intent import build_vocal_fx_intent  # noqa: E402
from vocal_processing import process_vocal_assets  # noqa: E402


def fixture_analysis() -> dict:
    return {
        "metadata": {"duration_seconds": 30.0, "sample_rate": 48000, "channels": 2},
        "silence_detection": {"intro_silence": None, "outro_silence": None, "internal_silence_candidates": []},
        "arrangement_candidates": {},
        "vocal_like_texture_candidates": [],
        "melody_buried_candidates": [],
        "low_end_excess_candidates": [],
    }


class DecapitatorAutotuneRequestTests(unittest.TestCase):
    def test_vocal_chain_plan_is_plugin_aware_and_claim_safe(self) -> None:
        options = {
            "mode": "vocal_plus_beat",
            "vocal_fx_request": "보컬을 좀 더 오토튠 걸고 디카페이터 걸어라",
            "autotune": "medium",
        }
        plan = build_vocal_chain_plan(options, {"files": {}}, pitch_available=False, pitch_note="pitch correction/autotune tool unavailable")
        self.assertIn("Parsed pitch correction request: medium", plan)
        self.assertIn("Requested plugin: Soundtoys Decapitator", plan)
        self.assertIn("generic saturation approximation", plan)
        self.assertIn("do not label it as Decapitator", plan)
        self.assertIn("Preserve the user's formant and vocal identity", plan)

    def test_processing_log_includes_manual_decapitator_instruction_without_application_claim(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_root = Path(tmp)
            result = process_vocal_assets(
                {
                    "mode": "instrumental_beat",
                    "vocal_fx_request": "보컬을 좀 더 오토튠 걸고 디카페이터 걸어라",
                },
                {"files": {}},
                project_root,
            )
        instructions = "\n".join(result["manual_logic_instructions"])
        self.assertIn("Insert Soundtoys Decapitator on the vocal bus if installed.", instructions)
        self.assertIn("do not claim Decapitator applied", instructions)
        self.assertIn("generic saturation approximation", instructions)

    def test_edit_plan_and_master_qc_include_plugin_claim_rules(self) -> None:
        options = {
            "mode": "vocal_plus_beat",
            "vocal_fx_request": "보컬을 좀 더 오토튠 걸고 디카페이터 걸어라",
            "autotune": "medium",
        }
        plan = build_edit_plan(fixture_analysis(), options)
        self.assertIn("Plugin-Aware Vocal FX Requests", plan)
        self.assertIn("requested saturation plugin: Soundtoys Decapitator", plan)
        self.assertIn("fallback: generic saturation approximation only", plan)

        report = build_master_qc_report(
            options,
            Path("/tmp/source.wav"),
            Path("/tmp/final.wav"),
            {
                "sample_rate": 48000,
                "channels": 2,
                "bit_depth": 24,
                "duration_seconds": 30.0,
                "file_size": 1000,
                "peak_dbfs": -1.0,
                "rms_dbfs": -10.0,
                "estimated_lufs": -10.0,
                "clipping_count": 0,
                "low_end_control_ratio": 0.5,
            },
        )
        self.assertIn("Plugin-aware vocal FX", report)
        self.assertIn("generic saturation approximation", report)
        self.assertIn("not Decapitator applied", report)

    def test_autotune_decapitator_intent_preserves_identity_and_requires_deess(self) -> None:
        intent = build_vocal_fx_intent(
            "보컬을 좀 더 오토튠 걸고 디카페이터 걸어라",
            plugin_availability={"detected": False, "status": "not_detected"},
        )

        self.assertTrue(intent["vocal_target_active"])
        self.assertIn(intent["pitch_correction"]["intensity"], {"medium", "hard_effect"})
        self.assertEqual(intent["saturation"]["requested_plugin"], "Soundtoys Decapitator")
        self.assertTrue(intent["deess_required"])
        self.assertTrue(intent["preserve_user_voice_identity"])
        self.assertFalse(intent["identity_clone_allowed"])
        self.assertEqual(intent["plugin_application"]["fallback"], "generic saturation approximation")
        self.assertIn("do not claim Decapitator applied", intent["plugin_application"]["claim_language"])


if __name__ == "__main__":
    unittest.main()

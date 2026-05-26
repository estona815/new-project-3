from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from lead_melody_generator import build_lead_melody_plan, choose_scale, write_lead_melody_outputs  # noqa: E402


class LeadMelodyGeneratorTests(unittest.TestCase):
    def test_generates_plan_when_lead_is_missing(self) -> None:
        plan = build_lead_melody_plan(
            tempo={"bpm_candidates": [{"bpm": 148.0, "confidence": "medium"}], "confidence": "medium"},
            key={"key": "F# minor", "confidence": "medium"},
            style_cluster="system_seoul_adjacent",
        )

        self.assertEqual(plan["schema_version"], "lead_melody_plan.v1")
        self.assertEqual(plan["status"], "LEAD_MELODY_PLAN_READY")
        self.assertEqual(plan["tempo_bpm"], 148)
        self.assertEqual(plan["key"], "F# minor")
        self.assertEqual([motif["motif_id"] for motif in plan["motifs"]], ["lead_A", "response_B"])
        self.assertGreaterEqual(len(plan["motifs"][0]["notes"]), 12)
        self.assertTrue(plan["hook_motif_summary"]["repetition"]["has_repetition"])
        self.assertTrue(plan["hook_motif_summary"]["repetition"]["has_variation"])
        self.assertFalse(plan["safety"]["exact_reference_melody_copy"])
        self.assertTrue(plan["safety"]["generated_from_style_traits_only"])

    def test_low_confidence_key_uses_confirm_by_ear_fallback(self) -> None:
        scale = choose_scale({"key": "Bb minor", "confidence": "low"})

        self.assertEqual(scale["key"], "Bb minor")
        self.assertEqual(scale["key_confidence"], "low")
        self.assertTrue(scale["confirm_by_ear"])
        self.assertEqual(scale["scale_name"], "minor_pentatonic/natural_minor_options")

    def test_writes_json_outputs_without_rendering_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            outputs = write_lead_melody_outputs(
                project_root=temp_dir,
                tempo={"bpm": 150, "confidence": "high"},
                key={"key": "A minor", "confidence": "high"},
                style_cluster="digicore",
                render=False,
            )
            root = Path(temp_dir)
            lead_path = root / "02_EDIT_PLAN" / "lead_melody_plan.json"
            hook_path = root / "02_EDIT_PLAN" / "hook_identity_plan.json"

            self.assertTrue(lead_path.exists())
            self.assertTrue(hook_path.exists())
            self.assertFalse((root / "04_PROCESSED_AUDIO" / "generated_lead_motif.wav").exists())
            self.assertEqual(json.loads(lead_path.read_text(encoding="utf-8"))["status"], "LEAD_MELODY_PLAN_READY")
            self.assertEqual(outputs["hook_identity_plan"]["status"], "HOOK_IDENTITY_PLAN_READY")


if __name__ == "__main__":
    unittest.main()

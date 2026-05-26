from __future__ import annotations

import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from hook_motif_generator import build_hook_identity_plan, generate_hook_motif, motif_repetition_report  # noqa: E402
from lead_melody_generator import build_lead_melody_plan  # noqa: E402


class HookMotifGeneratorTests(unittest.TestCase):
    def test_detects_repetition_with_variation(self) -> None:
        plan = build_lead_melody_plan(key={"key": "F# minor", "confidence": "medium"})
        report = motif_repetition_report(plan["motifs"])

        self.assertTrue(report["has_repetition"])
        self.assertTrue(report["has_variation"])
        self.assertGreaterEqual(report["repeated_rhythm_positions"], 4)

    def test_hook_identity_plan_maps_motif_to_hook_sections(self) -> None:
        section_plan = {
            "sections": [
                {"name": "intro_hook_hint", "start_time": 0.0, "duration": 4.0},
                {"name": "main_hook", "start_time": 4.0, "duration": 16.0},
                {"name": "verse_groove", "start_time": 20.0, "duration": 16.0},
            ]
        }
        lead_plan = build_lead_melody_plan(section_plan=section_plan, style_cluster="hyperpop")
        hook_plan = build_hook_identity_plan(lead_plan=lead_plan, section_plan=section_plan, style_cluster="hyperpop")

        self.assertEqual(hook_plan["schema_version"], "hook_identity_plan.v1")
        self.assertEqual(hook_plan["status"], "HOOK_IDENTITY_PLAN_READY")
        self.assertEqual(hook_plan["main_hook_motif_id"], "lead_A")
        self.assertEqual(hook_plan["call_response_motif_id"], "response_B")
        self.assertEqual(hook_plan["motif_repetition_quality"], "structured_repeat_with_variation")
        self.assertEqual(len(hook_plan["hook_motif"]["hook_sections"]), 2)

    def test_counts_sample_and_vocal_rhythm_hints_without_copy_claims(self) -> None:
        lead_plan = build_lead_melody_plan()
        motif = generate_hook_motif(
            motifs=lead_plan["motifs"],
            sample_analysis={"motif_hook_detection": {"hook_motif_candidates": [{"start": 1.0}]}},
            vocal_to_code={"phrases": [{"phrase_id": "v1"}]},
        )

        self.assertEqual(motif["sample_motif_candidates_used_as_rhythm_hints"], 1)
        self.assertEqual(motif["vocal_phrase_rhythm_hints"], 1)
        self.assertFalse(motif["safety"]["exact_reference_melody_copy"])
        self.assertFalse(motif["safety"]["artist_melody_imitation_claimed"])


if __name__ == "__main__":
    unittest.main()

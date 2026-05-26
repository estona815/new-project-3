from __future__ import annotations

import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from call_response_builder import build_call_response_plan  # noqa: E402


SELECTED = [
    {"sample_id": "sample_01", "role": "main_motif", "start": 0.0, "end": 1.8},
    {"sample_id": "sample_02", "role": "response_motif", "start": 0.0, "end": 0.9},
    {"sample_id": "sample_03", "role": "texture_layer", "start": 0.0, "end": 2.0},
    {"sample_id": "sample_04", "role": "transition_element", "start": 0.0, "end": 0.5},
]


class CallResponseBuilderTests(unittest.TestCase):
    def test_maps_main_motif_to_hook_sections(self) -> None:
        arrangement = {
            "sections": [
                {"name": "intro_hook_hint", "start_time": 0.0, "duration": 4.0, "energy": 3},
                {"name": "main_hook", "start_time": 4.0, "duration": 16.0, "energy": 5},
                {"name": "verse", "start_time": 20.0, "duration": 16.0, "energy": 2},
                {"name": "final_hook", "start_time": 68.0, "duration": 20.0, "energy": 5},
            ]
        }
        plan = build_call_response_plan(SELECTED, arrangement)
        hook_usage = [item for item in plan["section_usage"] if "hook" in item["section"].lower()]

        self.assertEqual(plan["schema_version"], "sample_call_response_plan.v1")
        self.assertEqual(plan["main_motif_id"], "sample_01")
        self.assertEqual(plan["response_motif_id"], "sample_02")
        self.assertGreaterEqual(len(hook_usage), 3)
        self.assertTrue(any(item["sample_role"] == "main_motif_full" for item in hook_usage))
        self.assertTrue(any(item["sample_role"] == "main_motif_full_plus_response" for item in hook_usage))
        self.assertTrue(plan["anti_spam"]["avoid_over_chopping"])

    def test_verse_uses_texture_not_main_chop_spam(self) -> None:
        plan = build_call_response_plan(SELECTED, {"sections": [{"name": "verse", "start_time": 20, "duration": 16}]})
        usage = next(item for item in plan["section_usage"] if item["section"] == "verse")

        self.assertEqual(usage["sample_role"], "texture_only")
        self.assertEqual(usage["density"], "low")
        self.assertEqual(usage["sample_id"], "sample_03")
        self.assertIn("Response motif answers only in gaps", " ".join(plan["call_response_rules"]))

    def test_default_plan_still_has_hook_return(self) -> None:
        plan = build_call_response_plan(SELECTED)

        self.assertGreaterEqual(plan["hook_return_count"], 1)
        self.assertTrue(any(item["sample_id"] == "sample_01" for item in plan["section_usage"] if "hook" in item["section"].lower()))


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from hook_identity_builder import build_hook_identity_plan  # noqa: E402


BAD_DIAGNOSIS = {
    "rescue_decision": {
        "lead_melody_required": True,
        "hook_identity_required": True,
        "vocal_texture_cleanup_required": True,
    }
}


class HookIdentityBuilderTests(unittest.TestCase):
    def test_missing_lead_and_hook_trigger_create_lead_plan(self) -> None:
        plan = build_hook_identity_plan(
            BAD_DIAGNOSIS,
            sample_analysis={"motif_hook_detection": {"hook_motif_candidates": [{"start": 0.0}]}},
            vocal_to_code={"phrases": [{"start": 1.0, "end": 2.0}]},
        )

        self.assertTrue(plan["create_new_lead"])
        self.assertTrue(plan["create_hook_identity"])
        self.assertEqual(plan["lead_source"], "new MIDI/synth motif")
        self.assertEqual(plan["usable_sample_motif_candidates"], 1)
        self.assertEqual(plan["usable_vocal_phrase_candidates"], 1)
        self.assertIn("Use fewer stronger motifs.", plan["motif_rules"])
        self.assertIn("push back", plan["vocal_texture_rule"])

    def test_existing_identity_preserves_and_simplifies(self) -> None:
        plan = build_hook_identity_plan({"rescue_decision": {}})

        self.assertFalse(plan["create_new_lead"])
        self.assertFalse(plan["create_hook_identity"])
        self.assertIn("preserve", plan["lead_source"])


if __name__ == "__main__":
    unittest.main()

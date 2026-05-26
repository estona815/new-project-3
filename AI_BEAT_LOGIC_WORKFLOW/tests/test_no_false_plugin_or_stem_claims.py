from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from mix_master_autopilot import build_mix_master_plan  # noqa: E402


class NoFalsePluginOrStemClaimsTests(unittest.TestCase):
    def test_stereo_plan_never_claims_plugin_or_stem_processing(self) -> None:
        plan = build_mix_master_plan(
            input_mode="full_song_stereo",
            dependency_capabilities={
                "plugins": {
                    "soundtoys_decapitator": {"status": "detected"},
                    "autotune_like": {"status": "detected"},
                }
            },
        )
        text = json.dumps(plan).lower()

        self.assertFalse(plan["false_claim_guards"]["auto_tune_applied"])
        self.assertFalse(plan["false_claim_guards"]["decapitator_applied"])
        self.assertFalse(plan["false_claim_guards"]["stem_level_remix_claimed"])
        self.assertIn("not applied", text)
        self.assertIn("stereo-only processing cannot claim stem-level control", text)

    def test_stems_do_not_claim_plugin_processing_without_verification(self) -> None:
        plan = build_mix_master_plan(input_mode="stems")

        self.assertTrue(plan["stem_chain"]["more_direct_balancing_allowed"])
        self.assertFalse(plan["false_claim_guards"]["plugin_processing_verified"])
        self.assertFalse(plan["stem_chain"]["false_claim_guard"]["plugin_processing_verified"])


if __name__ == "__main__":
    unittest.main()

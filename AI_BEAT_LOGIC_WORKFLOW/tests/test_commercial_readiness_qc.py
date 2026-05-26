from __future__ import annotations

import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from commercial_readiness_qc import evaluate_commercial_readiness  # noqa: E402


ARRANGEMENT_PASS = {
    "plan_pass": True,
    "needs_more_input": False,
    "categories": [{"name": name, "score": 5} for name in ("Hook impact", "Arrangement intentionality", "Sample/motif usability", "Vocal phrase usability", "Drum/808 guide strength", "Melody/vibe preservation", "Synth width/space plan", "Logic manual clarity")],
}

MIX_PLAN = {
    "input_mode": "full_song_stereo",
    "style_target": "commercial_digicore_hyperpop",
    "mix_priorities": ["vocal_forwardness", "controlled_808", "hook_impact"],
    "commercial_style_target": ["no random AI harshness"],
    "false_claim_guards": {
        "auto_tune_applied": False,
        "decapitator_applied": False,
        "plugin_processing_verified": False,
        "stem_level_remix_claimed": False,
        "completion_claimed": False,
    },
}


class CommercialReadinessQCTests(unittest.TestCase):
    def test_plan_only_pass_is_plan_pass_not_complete(self) -> None:
        qc = evaluate_commercial_readiness(arrangement_qc=ARRANGEMENT_PASS, mix_master_plan=MIX_PLAN, input_mode="full_song_stereo")

        self.assertEqual(qc["status"], "PLAN_PASS")
        self.assertFalse(qc["completion_gate_complete"])
        self.assertIn("not final audio completion", qc["capability_statement"])

    def test_final_verified_gate_pass_is_final_pass(self) -> None:
        qc = evaluate_commercial_readiness(
            arrangement_qc=ARRANGEMENT_PASS,
            mix_master_plan={**MIX_PLAN, "input_mode": "stems"},
            completion_gate={"complete": True, "blocking_reasons": []},
            render_manifest={"final_wav": {"exists": True, "verified": True}},
            input_mode="stems",
        )

        self.assertEqual(qc["status"], "FINAL_PASS")

    def test_false_stem_claim_fails_reprocess(self) -> None:
        bad_mix = {**MIX_PLAN, "false_claim_guards": {**MIX_PLAN["false_claim_guards"], "stem_level_remix_claimed": True}}
        qc = evaluate_commercial_readiness(arrangement_qc=ARRANGEMENT_PASS, mix_master_plan=bad_mix, input_mode="full_song_stereo")

        self.assertEqual(qc["status"], "FAIL_REPROCESS")
        self.assertTrue(qc["false_claim_risk"]["high"])


if __name__ == "__main__":
    unittest.main()

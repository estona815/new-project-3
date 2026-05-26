from __future__ import annotations

import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from commercial_readiness_qc import evaluate_commercial_readiness  # noqa: E402
from mix_master_autopilot import build_mix_master_plan  # noqa: E402


class StereoOnlyLimitationsIntegrationTests(unittest.TestCase):
    def test_true_kick_bass_replacement_is_manual_required_and_not_claimed(self) -> None:
        mix_plan = build_mix_master_plan(input_mode="full_song_stereo")
        arrangement_qc = {
            "plan_pass": False,
            "needs_more_input": False,
            "categories": [
                {"name": "Hook impact", "score": 4},
                {"name": "Arrangement intentionality", "score": 4},
                {"name": "Drum/808 guide strength", "score": 3},
                {"name": "Logic manual clarity", "score": 4},
            ],
        }
        qc = evaluate_commercial_readiness(
            arrangement_qc=arrangement_qc,
            mix_master_plan=mix_plan,
            input_mode="full_song_stereo",
        )

        self.assertFalse(mix_plan["instrumental_chain"]["false_claim_guard"]["kick_replacement_claimed"])
        self.assertFalse(mix_plan["instrumental_chain"]["false_claim_guard"]["stem_level_rebalance_claimed"])
        self.assertIn("true kick/bass replacement", " ".join(mix_plan["manual_logic_required"]))
        self.assertEqual(qc["status"], "NEEDS_LOGIC_PRODUCTION")


if __name__ == "__main__":
    unittest.main()

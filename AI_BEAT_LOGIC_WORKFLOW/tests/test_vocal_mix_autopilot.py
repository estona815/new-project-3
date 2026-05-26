from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from vocal_mix_autopilot import build_vocal_mix_chain  # noqa: E402


class VocalMixAutopilotTests(unittest.TestCase):
    def test_vocal_chain_has_required_order_and_no_plugin_claims(self) -> None:
        chain = build_vocal_mix_chain(
            input_mode="vocal_plus_beat",
            pitch_guide={"recommended_mode": "hard_effect", "claim_language": "recommended, not applied"},
            plugin_capabilities={"soundtoys_decapitator": {"status": "detected"}},
        )
        text = json.dumps(chain).lower()

        self.assertEqual(chain["scope"], "direct_vocal_bus")
        self.assertIn("clip gain", text)
        self.assertIn("de_ess", chain)
        self.assertFalse(chain["false_claim_guard"]["auto_tune_applied"])
        self.assertFalse(chain["false_claim_guard"]["decapitator_applied"])
        self.assertEqual(chain["saturation"]["claim_language"], "manual/available hint only; not applied")

    def test_full_stereo_marks_vocal_analysis_heuristic(self) -> None:
        chain = build_vocal_mix_chain(input_mode="full_song_stereo")

        self.assertEqual(chain["scope"], "heuristic_full_mix_vocal_regions")
        self.assertFalse(chain["false_claim_guard"]["analysis_isolated"])
        self.assertTrue(chain["limitations"])


if __name__ == "__main__":
    unittest.main()

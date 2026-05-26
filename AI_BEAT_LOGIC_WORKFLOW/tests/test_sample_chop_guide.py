from __future__ import annotations

import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from sample_chop_guide import generate_sample_chop_guide  # noqa: E402


class SampleChopGuideTests(unittest.TestCase):
    def test_unknown_ownership_blocks_direct_sample_use(self) -> None:
        guide = generate_sample_chop_guide(
            {
                "sample_usage_safety": {"ownership_status": "unknown", "direct_sample_use_allowed": False},
                "motif_hook_detection": {"hook_motif_candidates": [{"start": 0.0, "end": 1.0, "confidence": "medium"}]},
            }
        )

        self.assertFalse(guide["direct_sample_use_allowed"])
        self.assertTrue(guide["direct_sample_layer_blocked"])
        self.assertEqual(guide["chop_candidates"][0]["chop_id"], "chop_01")

    def test_owned_policy_allows_direct_use_inside_local_source(self) -> None:
        guide = generate_sample_chop_guide({}, {"ownership_status": "owned", "direct_sample_use_allowed": True})

        self.assertTrue(guide["direct_sample_use_allowed"])
        self.assertFalse(guide["direct_sample_layer_blocked"])


if __name__ == "__main__":
    unittest.main()

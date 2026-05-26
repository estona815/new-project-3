from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from mix_master_autopilot import build_mix_master_plan, write_mix_master_plan  # noqa: E402


class MixMasterAutopilotTests(unittest.TestCase):
    def test_plan_works_for_all_supported_modes(self) -> None:
        for mode in ("instrumental_beat", "full_song_stereo", "vocal_plus_beat", "stems", "sample_arrangement_plan_only"):
            with self.subTest(mode=mode):
                plan = build_mix_master_plan(input_mode=mode, master_target_mode="streaming_safe")

                self.assertEqual(plan["schema_version"], "mix_master_plan.v1")
                self.assertEqual(plan["input_mode"], mode)
                self.assertIn("master_chain", plan)
                self.assertFalse(plan["false_claim_guards"]["completion_claimed"])

    def test_write_mix_master_plan_outputs_json_and_markdown(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            plan = build_mix_master_plan(input_mode="sample_arrangement_plan_only")
            paths = write_mix_master_plan(tmp, plan)

            self.assertTrue(paths["json"].exists())
            self.assertTrue(paths["markdown"].exists())
            self.assertIn("plan_only_no_audio_processing", paths["json"].read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()

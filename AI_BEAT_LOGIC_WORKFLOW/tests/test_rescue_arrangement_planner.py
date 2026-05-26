from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from rescue_arrangement_planner import build_rescue_arrangement_plan, write_rescue_arrangement_plan  # noqa: E402


BAD_DIAGNOSIS = {
    "schema_version": "bad_song_diagnosis.v1",
    "rescue_decision": {
        "mix_only_not_enough": True,
        "lead_melody_required": True,
        "hook_identity_required": True,
        "arrangement_rebuild_required": True,
        "vocal_texture_cleanup_required": True,
        "sample_motif_rebuild_required": True,
    },
    "ai_randomness": {"randomness_risk": "high"},
}


class RescueArrangementPlannerTests(unittest.TestCase):
    def test_bad_diagnosis_builds_short_intentional_song_form(self) -> None:
        plan = build_rescue_arrangement_plan(
            bad_song_diagnosis=BAD_DIAGNOSIS,
            sample_analysis={"motif_hook_detection": {"hook_motif_candidates": [{"start": 2.0}]}},
            vocal_to_code={"phrases": [{"start": 4.0, "end": 5.0}]},
            creative_brief={"style_cluster_text": "digicore hyperpop SYSTEM SEOUL", "length": {"mode": "under_2min"}},
            style_cluster="system_seoul_adjacent",
        )

        self.assertEqual(plan["schema_version"], "rescue_arrangement_plan.v1")
        self.assertEqual(plan["length_mode"], "under_2min")
        self.assertTrue(plan["source_problem"]["mix_only_not_enough"])
        self.assertTrue(plan["source_problem"]["missing_lead"])
        self.assertTrue(plan["source_problem"]["missing_hook"])
        self.assertEqual(plan["sections"][0]["name"], "intro_hook_hint")
        self.assertEqual(plan["sections"][1]["name"], "main_hook")
        self.assertLess(plan["hook_appears_by_seconds"], 15.0)
        self.assertIn("new lead motif", plan["add_or_create"])
        self.assertIn("new hook identity", plan["add_or_create"])
        self.assertIn("random glitch fills", plan["remove_or_reduce"])
        self.assertIn("digicore", plan["target_style"]["genre_family"])
        self.assertIn("hyperpop", plan["target_style"]["genre_family"])
        self.assertIn("exact copying prohibited", plan["target_style"]["style_notes"])

    def test_reels_request_places_hook_immediately(self) -> None:
        plan = build_rescue_arrangement_plan(
            bad_song_diagnosis=BAD_DIAGNOSIS,
            creative_brief={"raw_full_korean_request": "릴스 15초 훅 바로"},
        )

        self.assertEqual(plan["length_mode"], "reels_15sec")
        self.assertEqual(plan["sections"][0]["name"], "main_hook")
        self.assertEqual(plan["hook_appears_by_seconds"], 0.0)
        self.assertLessEqual(plan["target_duration_seconds"], 15.0)

    def test_write_rescue_arrangement_plan_outputs_json_and_markdown(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "workflow"
            (root / "01_ANALYSIS").mkdir(parents=True)
            (root / "02_EDIT_PLAN").mkdir(parents=True)
            (root / "01_ANALYSIS" / "bad_song_diagnosis.json").write_text(json.dumps(BAD_DIAGNOSIS), encoding="utf-8")
            (root / "02_EDIT_PLAN" / "creative_brief.json").write_text(
                json.dumps({"style_cluster_text": "digicore hyperpop", "length": {"mode": "short_30sec"}}),
                encoding="utf-8",
            )

            paths = write_rescue_arrangement_plan(project_root=root)

            self.assertTrue(paths["json"].exists())
            self.assertTrue(paths["markdown"].exists())
            parsed = json.loads(paths["json"].read_text(encoding="utf-8"))
            markdown = paths["markdown"].read_text(encoding="utf-8")
            self.assertEqual(parsed["length_mode"], "short_30sec")
            self.assertLess(parsed["hook_appears_by_seconds"], 15.0)
            self.assertIn("Rescue Arrangement Plan", markdown)
            self.assertFalse((root / "05_FINAL_WAV").exists())


if __name__ == "__main__":
    unittest.main()

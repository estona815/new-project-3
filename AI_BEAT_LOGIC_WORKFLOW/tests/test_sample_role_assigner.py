from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from sample_role_assigner import assign_sample_roles, build_sample_candidates  # noqa: E402


def sample_analysis_fixture(path: str = "/tmp/sample_01.wav") -> dict[str, object]:
    return {
        "schema_version": "sample_analysis.v1",
        "metadata": {"path": path, "duration_seconds": 4.0},
        "tonal": {"estimated_key": "F# minor", "confidence": "medium"},
        "loop_detection": {"loopable_regions": [{"start": 0.0, "end": 2.0}]},
        "motif_hook_detection": {
            "hook_motif_candidates": [
                {
                    "start": 0.0,
                    "end": 1.8,
                    "confidence": "medium",
                    "reason": "tonal, recognizable, loopable hook candidate",
                    "role_hint": "hook_candidate",
                },
                {
                    "start": 2.0,
                    "end": 3.0,
                    "confidence": "low",
                    "reason": "short contrast motif",
                    "role_hint": "motif_or_variation",
                },
            ]
        },
    }


class SampleRoleAssignerTests(unittest.TestCase):
    def test_assigns_musical_roles_from_analysis_candidates(self) -> None:
        assignment = assign_sample_roles(
            sample_analysis=sample_analysis_fixture(),
            song_key_bpm={"bpm": 148, "key": "F# minor", "key_confidence": "medium"},
        )
        roles = [item["role"] for item in assignment["selected_samples"]]

        self.assertEqual(assignment["schema_version"], "sample_role_assignment.v1")
        self.assertIn("main_motif", roles)
        self.assertIn("response_motif", roles)
        self.assertIn("texture_layer", roles)
        self.assertIn("transition_element", roles)
        self.assertEqual(assignment["selected_samples"][0]["role"], "main_motif")
        self.assertIn("Use fewer stronger samples.", assignment["rules"])
        self.assertEqual(assignment["song_context"]["bpm"], 148)

    def test_builds_folder_candidates_when_no_analysis_exists(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            folder = Path(temp_dir)
            (folder / "one.wav").write_bytes(b"RIFFxxxxWAVE")
            (folder / "ignore.txt").write_text("no", encoding="utf-8")
            candidates = build_sample_candidates(sample_folder=folder)

            self.assertEqual(len(candidates), 1)
            self.assertEqual(candidates[0]["sample_id"], "one")
            self.assertEqual(candidates[0]["source"], "sample_folder")

    def test_main_candidate_prefers_recognizable_loopable_region(self) -> None:
        candidates = build_sample_candidates(sample_analysis=sample_analysis_fixture())

        self.assertEqual(candidates[0]["start"], 0.0)
        self.assertGreater(candidates[0]["motif_score"], candidates[1]["motif_score"])
        self.assertTrue(candidates[0]["loopable"])


if __name__ == "__main__":
    unittest.main()

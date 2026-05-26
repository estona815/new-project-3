from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from lead_melody_generator import build_lead_melody_plan  # noqa: E402
from melody_qc import qc_lead_melody_plan, qc_rendered_wav, run_melody_qc  # noqa: E402
from simple_synth_renderer import render_lead_plan_to_wav  # noqa: E402


class MelodyQCTests(unittest.TestCase):
    def test_good_generated_plan_passes_qc(self) -> None:
        plan = build_lead_melody_plan(
            tempo={"bpm": 148, "confidence": "medium"},
            key={"key": "F# minor", "confidence": "medium"},
            style_cluster="digicore",
        )
        report = qc_lead_melody_plan(plan)

        self.assertTrue(report["plan_pass"])
        self.assertEqual(report["status"], "PASS")
        self.assertEqual(report["issues"], [])
        self.assertTrue(report["metrics"]["repetition"]["has_repetition"])
        self.assertTrue(report["metrics"]["repetition"]["has_variation"])

    def test_random_dense_plan_fails_qc(self) -> None:
        bad_notes = [
            {"bar": 1, "beat": 1.0, "note": "C4", "duration": "1/16"},
            {"bar": 1, "beat": 1.25, "note": "F#6", "duration": "1/16"},
            {"bar": 1, "beat": 1.5, "note": "D4", "duration": "1/16"},
            {"bar": 1, "beat": 1.75, "note": "G#6", "duration": "1/16"},
            {"bar": 1, "beat": 2.0, "note": "E4", "duration": "1/16"},
            {"bar": 1, "beat": 2.25, "note": "A#6", "duration": "1/16"},
            {"bar": 1, "beat": 2.5, "note": "F4", "duration": "1/16"},
            {"bar": 1, "beat": 2.75, "note": "B6", "duration": "1/16"},
            {"bar": 1, "beat": 3.0, "note": "G4", "duration": "1/16"},
            {"bar": 1, "beat": 3.25, "note": "C#7", "duration": "1/16"},
            {"bar": 1, "beat": 3.5, "note": "A4", "duration": "1/16"},
            {"bar": 1, "beat": 3.75, "note": "D#7", "duration": "1/16"},
            {"bar": 2, "beat": 1.0, "note": "C5", "duration": "1/16"},
            {"bar": 2, "beat": 1.25, "note": "F#3", "duration": "1/16"},
            {"bar": 2, "beat": 1.5, "note": "D5", "duration": "1/16"},
            {"bar": 2, "beat": 1.75, "note": "G#3", "duration": "1/16"},
        ]
        plan = {
            "schema_version": "lead_melody_plan.v1",
            "motifs": [{"motif_id": "lead_A", "bars": 2, "role": "main_hook", "notes": bad_notes}],
            "safety": {"exact_reference_melody_copy": False, "artist_melody_imitation_claimed": False},
        }
        report = qc_lead_melody_plan(plan)

        self.assertFalse(report["plan_pass"])
        self.assertEqual(report["status"], "NEEDS_REVISION")
        self.assertTrue(any("repeated rhythm" in issue or "large jumps" in issue for issue in report["issues"]))

    def test_rendered_wav_qc_passes_for_generated_stem(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            plan = build_lead_melody_plan()
            path = Path(temp_dir) / "generated_hook_stem.wav"
            render_lead_plan_to_wav(plan, path)
            report = qc_rendered_wav(path)

            self.assertTrue(report["render_pass"])
            self.assertEqual(report["issues"], [])
            self.assertEqual(report["metrics"]["sample_rate"], 48_000)
            self.assertEqual(report["metrics"]["channels"], 2)
            self.assertEqual(report["metrics"]["clipping_count"], 0)

    def test_bundle_fails_if_render_missing(self) -> None:
        plan = build_lead_melody_plan()
        report = run_melody_qc(plan, [Path("/tmp/not_a_generated_lead.wav")])

        self.assertEqual(report["status"], "NEEDS_REVISION")
        self.assertFalse(report["render_qc"][0]["render_pass"])


if __name__ == "__main__":
    unittest.main()

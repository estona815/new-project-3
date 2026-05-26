from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from logic_arrangement_plan import SECTION_TITLES, render_logic_arrangement_plan  # noqa: E402
from logic_status_schema import build_logic_autopilot_status, write_logic_autopilot_status  # noqa: E402


class LogicArrangementStatusTests(unittest.TestCase):
    def test_success_is_not_allowed_without_verified_artifacts(self) -> None:
        status = build_logic_autopilot_status(status="success", project_path="/missing/project.logicx", final_wav_path="/missing/final.wav")

        self.assertEqual(status["status"], "failed")
        self.assertFalse(status["success_allowed"])
        self.assertFalse(status["project_created"])
        self.assertFalse(status["verified_output_exists"])
        self.assertFalse(status["claim_guard"]["logic_project_success_claimed"])

    def test_manual_plan_contains_required_sections(self) -> None:
        status = build_logic_autopilot_status()
        markdown = render_logic_arrangement_plan(
            {"status": "ARRANGEMENT_PLAN_READY"},
            {"tempo_bpm": 148, "time_signature": "4/4", "key": "F# minor", "key_confidence": "low"},
            {"events": [{"type": "filter_movement"}]},
            status,
        )

        for title in SECTION_TITLES:
            self.assertIn(f"## {title}", markdown)
        self.assertIn("Do not claim bounce/export", markdown)
        self.assertIn("stereo-only", markdown)

    def test_status_writer_outputs_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "logic_autopilot_status.json"
            written = write_logic_autopilot_status(path, build_logic_autopilot_status())

            self.assertTrue(written.exists())


if __name__ == "__main__":
    unittest.main()

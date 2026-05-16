from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_DIR))

import logic_integration  # noqa: E402
from logic_integration import LogicStatus, status_markdown  # noqa: E402


class LogicIntegrationTests(unittest.TestCase):
    def test_non_macos_skips_cleanly_and_writes_status(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            status_path = Path(tmp) / "logic_automation_status.md"
            with mock.patch("logic_integration.platform.system", return_value="Linux"):
                with mock.patch("logic_integration.STATUS_PATH", status_path):
                    status = logic_integration.write_availability_status()

            self.assertEqual(status.status, "unavailable")
            self.assertTrue(status_path.exists())
            text = status_path.read_text(encoding="utf-8")
            self.assertIn("status: unavailable", text)
            self.assertIn("fallback processing is required", text)

    def test_missing_working_wav_fails_without_false_success(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            status_path = root / "logic_automation_status.md"
            missing_wav = root / "working_input.wav"
            project_path = root / "suno_humanized_project.logicx"
            logic_app = root / "Logic Pro.app"
            logic_app.mkdir()
            with mock.patch("logic_integration.platform.system", return_value="Darwin"):
                with mock.patch("logic_integration.LOGIC_APP_PATH", logic_app):
                    with mock.patch("logic_integration.shutil.which", return_value="/usr/bin/osascript"):
                        with mock.patch("logic_integration.WORKING_WAV", missing_wav):
                            with mock.patch("logic_integration.LOGIC_PROJECT", project_path):
                                with mock.patch("logic_integration.STATUS_PATH", status_path):
                                    status = logic_integration.attempt_logic_project()

            self.assertEqual(status.status, "failed")
            self.assertFalse(status.project_exists)
            self.assertIn("working_input.wav is missing", status.message)
            self.assertTrue(status_path.exists())

    def test_status_markdown_has_manual_steps_and_no_fake_claims(self) -> None:
        status = LogicStatus(
            status="partial_success",
            message="Manual save required.",
            is_macos=True,
            logic_app_exists=True,
            osascript_available=True,
            working_wav_exists=True,
            project_path="/tmp/project.logicx",
            project_exists=False,
            attempted_commands=("osascript script.scpt",),
            timestamp="2026-01-01T00:00:00+00:00",
        )
        text = status_markdown(status)
        self.assertIn("02_EDIT_PLAN/edit_plan.md", text)
        self.assertIn("does not claim that Logic performed a humanized mix", text)
        self.assertIn("project/package exists: false", text)


if __name__ == "__main__":
    unittest.main()

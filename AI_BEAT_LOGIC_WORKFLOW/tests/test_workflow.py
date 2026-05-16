from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
import sys

PROJECT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_DIR))

from src.workflow import (
    REQUIRED_DIRECTORIES,
    SessionOptions,
    copy_input_file,
    ensure_project_directories,
    sanitize_filename,
    verify_final_wav_not_claimed,
    write_session_files,
)


class WorkflowScaffoldTests(unittest.TestCase):
    def test_sanitize_filename_keeps_extension_and_removes_unsafe_text(self) -> None:
        self.assertEqual(sanitize_filename("  My Suno Beat!!!.MP3"), "My_Suno_Beat.mp3")
        self.assertEqual(sanitize_filename("???.wav"), "suno_input.wav")

    def test_required_directories_are_created(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp)
            ensure_project_directories(project_dir)
            for relative in REQUIRED_DIRECTORIES:
                self.assertTrue((project_dir / relative).is_dir(), relative)

    def test_copy_input_file_never_overwrites_existing_copy(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp)
            source = project_dir / "source file.wav"
            source.write_bytes(b"fake wav bytes")

            first = copy_input_file(source, project_dir)
            second = copy_input_file(source, project_dir)

            self.assertNotEqual(first, second)
            self.assertTrue(first.exists())
            self.assertTrue(second.exists())

    def test_session_files_mark_final_wav_as_pending(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp)
            write_session_files(SessionOptions(), project_dir)

            self.assertTrue((project_dir / "01_ANALYSIS" / "analysis.json").exists())
            self.assertTrue((project_dir / "02_EDIT_PLAN" / "edit_plan.md").exists())
            self.assertTrue((project_dir / "06_QC_REPORT" / "qc_report.md").exists())
            self.assertTrue(verify_final_wav_not_claimed(project_dir))


if __name__ == "__main__":
    unittest.main()

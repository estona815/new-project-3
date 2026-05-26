from __future__ import annotations

import io
import sys
import unittest
from pathlib import Path
from unittest import mock


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_DIR))

from completion_gate import CompletionStatus  # noqa: E402
import main as workflow_main  # noqa: E402
import qc_report  # noqa: E402


class NoFalseCompleteTests(unittest.TestCase):
    def test_main_output_does_not_contain_complete_when_gate_blocks(self) -> None:
        blocked = CompletionStatus(
            complete=False,
            final_wav_path="/tmp/final.wav",
            qc_report_path="/tmp/qc_report.md",
            requested_format="wav24_48k",
            blocking_reasons=["QC report missing: /tmp/qc_report.md"],
        )
        fake_options = mock.Mock(
            input_path="/tmp/input.wav",
            export_format="wav24_48k",
            reference_text=None,
            reference_audio=None,
            creative_brief=None,
        )
        with (
            mock.patch.object(sys, "argv", ["main.py", "--input", "/tmp/input.wav"]),
            mock.patch.object(workflow_main, "ensure_folder_structure"),
            mock.patch.object(workflow_main, "load_defaults", return_value={"save_logic_project": False}),
            mock.patch.object(workflow_main, "options_from_args", return_value=fake_options),
            mock.patch.object(workflow_main, "print_configuration_summary"),
            mock.patch.object(workflow_main, "ingest_and_convert", return_value=mock.Mock(copied_path="copy.wav", working_wav_path="work.wav", conversion_tool_used="test")),
            mock.patch.object(workflow_main, "analyze_working_wav", return_value={"metadata": {"duration_seconds": 1.0}}),
            mock.patch.object(workflow_main, "write_edit_plan"),
            mock.patch.object(workflow_main, "run_vocal_mix_master_extension", return_value={"mix_session_plan": "mix.md"}),
            mock.patch.object(workflow_main, "run_fallback_processing", return_value={"verification": {"path": "fallback.wav"}}),
            mock.patch.object(workflow_main, "run_mastering_stage", return_value={"output_path": "master.wav", "master_qc_report": "master_qc.md"}),
            mock.patch.object(
                workflow_main,
                "run_final_export_and_qc",
                return_value={
                    "final_path": "/tmp/final.wav",
                    "qc_report": "/tmp/qc_report.md",
                    "complete": False,
                    "completion_gate": blocked,
                },
            ),
            mock.patch("sys.stdout", new_callable=io.StringIO) as stdout,
        ):
            result = workflow_main.main()

        self.assertEqual(result, 2)
        output = stdout.getvalue()
        self.assertNotIn("COMPLETE", output)
        self.assertIn("Final output is not complete.", output)
        self.assertIn("QC report missing", output)

    def test_qc_report_cli_cannot_print_complete_independently(self) -> None:
        blocked = CompletionStatus(
            complete=False,
            final_wav_path="/tmp/final.wav",
            qc_report_path="/tmp/qc_report.md",
            requested_format="wav24_48k",
            blocking_reasons=["final WAV missing: /tmp/final.wav"],
        )
        with (
            mock.patch.object(
                qc_report,
                "run_final_export_and_qc",
                return_value={
                    "final_path": "/tmp/final.wav",
                    "qc_report": "/tmp/qc_report.md",
                    "complete": False,
                    "completion_gate": blocked,
                },
            ),
            mock.patch("sys.stdout", new_callable=io.StringIO) as stdout,
        ):
            result = qc_report.main()

        self.assertEqual(result, 2)
        output = stdout.getvalue()
        self.assertNotIn("COMPLETE", output)
        self.assertIn("Final output is not complete.", output)

    def test_complete_literal_is_only_printed_from_main_gate_path(self) -> None:
        src_files = list((PROJECT_ROOT / "src").glob("*.py"))
        offenders: list[str] = []
        for path in src_files:
            text = path.read_text(encoding="utf-8")
            if 'print("COMPLETE")' in text and path.name != "main.py":
                offenders.append(path.name)

        self.assertEqual(offenders, [])


if __name__ == "__main__":
    unittest.main()

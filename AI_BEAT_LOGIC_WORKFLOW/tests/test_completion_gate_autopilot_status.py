from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from completion_gate import check_completion_status  # noqa: E402


class CompletionGateAutopilotStatusTests(unittest.TestCase):
    def test_autopilot_plan_reports_do_not_make_complete_without_final_wav(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            report = root / "06_QC_REPORT" / "autopilot_qc_report.md"
            report.parent.mkdir(parents=True)
            report.write_text("# Autopilot QC\nstatus: PLAN_PASS\n", encoding="utf-8")

            status = check_completion_status(final_wav_path=None, qc_report_path=report, requested_format="wav24_48k")

            self.assertFalse(status.complete)
            self.assertIn("final WAV path was not provided", status.blocking_reasons)

    def test_final_report_requirements_still_gate_complete(self) -> None:
        status = check_completion_status(
            final_wav_path="/missing/final.wav",
            qc_report_path="/missing/qc.md",
            requested_format="wav24_48k",
            final_verify_result={"ok": False, "format_verified": False, "errors": ["missing"]},
        )

        self.assertFalse(status.complete)
        self.assertTrue(status.blocking_reasons)


if __name__ == "__main__":
    unittest.main()

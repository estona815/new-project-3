from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))
sys.path.insert(0, str(PROJECT_ROOT / "tests"))

from completion_gate import check_completion_status  # noqa: E402
from export_audio import write_float_wav  # noqa: E402
from release_package_builder import build_and_write_release_package  # noqa: E402
from release_workflow_orchestrator import write_release_workflow_status  # noqa: E402
from test_release_ready_workflow_integration import complete_metadata, clear_rights, write_basic_reports  # noqa: E402


class ReleaseStatusNoFalseCompleteTests(unittest.TestCase):
    def test_release_package_ready_is_not_complete_without_completion_gate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            final = root / "final.wav"
            write_float_wav(final, [[0.1] * 4800, [0.1] * 4800], 48000, bit_depth=24)
            qc, master = write_basic_reports(root)
            package = build_and_write_release_package(root, final_master_path=final, metadata=complete_metadata(), rights=clear_rights(), qc_report_path=qc, master_qc_report_path=master)
            blocked_gate = check_completion_status(
                final_wav_path=final,
                qc_report_path=qc,
                requested_format="wav24_48k",
                require_master_qc=True,
                master_qc_report_path=root / "missing_master_qc_report.md",
            )
            status = write_release_workflow_status(
                project_root=root,
                workflow="song_to_release",
                completion_gate=blocked_gate,
                final_audio_verified=True,
                release_package_manifest_path=package["paths"]["manifest"],
                release_qc_report_path=package["paths"]["release_qc_report"],
            )

            self.assertTrue(package["manifest"]["release_ready"])
            self.assertFalse(blocked_gate.complete)
            self.assertEqual(status["status"]["status"], "RELEASE_PACKAGE_READY")
            self.assertFalse(status["status"]["complete_allowed"])


if __name__ == "__main__":
    unittest.main()

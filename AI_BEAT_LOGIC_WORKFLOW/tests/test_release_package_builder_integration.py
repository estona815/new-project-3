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
from test_release_ready_workflow_integration import complete_metadata, clear_rights, write_basic_reports  # noqa: E402


class ReleasePackageBuilderIntegrationTests(unittest.TestCase):
    def test_metadata_incomplete_creates_draft_checklists_and_blocks_complete_without_audio(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            package = build_and_write_release_package(root, final_master_path=None, metadata={"title": "Draft"}, rights=clear_rights())
            status = check_completion_status(
                final_wav_path=None,
                qc_report_path=root / "missing_qc.md",
                requested_format="wav24_48k",
                require_release_package=True,
                release_package_manifest_path=package["paths"]["manifest"],
                release_qc_report_path=package["paths"]["release_qc_report"],
            )

            self.assertEqual(package["manifest"]["release_status"], "FAILED_TECHNICAL_QC")
            self.assertFalse(package["manifest"]["release_ready"])
            self.assertTrue(package["paths"]["metadata_md"].exists())
            self.assertTrue(package["paths"]["distribution_checklist"].exists())
            self.assertFalse(status.complete)

    def test_rights_unresolved_sets_needs_rights_clearance(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            final = root / "final.wav"
            write_float_wav(final, [[0.1] * 4800, [0.1] * 4800], 48000, bit_depth=24)
            qc, master = write_basic_reports(root)
            package = build_and_write_release_package(
                root,
                final_master_path=final,
                metadata=complete_metadata(),
                rights=clear_rights(contains_samples=True, all_samples_owned_or_cleared=None),
                qc_report_path=qc,
                master_qc_report_path=master,
                completion_gate={"complete": True},
            )

            self.assertEqual(package["manifest"]["release_status"], "NEEDS_RIGHTS_CLEARANCE")
            self.assertFalse(package["manifest"]["release_ready"])

    def test_wrong_format_final_audio_fails_technical_qc(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            final = root / "final_16bit.wav"
            write_float_wav(final, [[0.1] * 4800, [0.1] * 4800], 48000, bit_depth=16)
            qc, master = write_basic_reports(root)
            package = build_and_write_release_package(root, final_master_path=final, metadata=complete_metadata(), rights=clear_rights(), qc_report_path=qc, master_qc_report_path=master)

            self.assertEqual(package["manifest"]["release_status"], "FAILED_TECHNICAL_QC")
            self.assertFalse(package["manifest"]["release_ready"])


if __name__ == "__main__":
    unittest.main()

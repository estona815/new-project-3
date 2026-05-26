from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from completion_gate import check_completion_status  # noqa: E402
from export_audio import write_float_wav  # noqa: E402
from release_package_builder import build_and_write_release_package  # noqa: E402


def clear_rights() -> dict[str, object]:
    return {
        "contains_samples": False,
        "source_ownership_confirmed": True,
        "vocal_performer_consent": True,
        "featured_artist_metadata_complete": True,
        "explicit_content_flag_set": True,
    }


class ReleaseCompleteBlockingTests(unittest.TestCase):
    def test_draft_release_manifest_blocks_complete_but_package_exists(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            final = root / "final.wav"
            qc = root / "qc_report.md"
            master = root / "master_qc_report.md"
            write_float_wav(final, [[0.1] * 4800, [0.1] * 4800], 48000, bit_depth=24)
            qc.write_text("qc\n", encoding="utf-8")
            master.write_text("master qc\n", encoding="utf-8")
            package = build_and_write_release_package(
                root,
                final_master_path=final,
                metadata={"title": "Draft"},
                rights=clear_rights(),
                qc_report_path=qc,
                master_qc_report_path=master,
                completion_gate={"complete": True},
            )

            status = check_completion_status(
                final_wav_path=final,
                qc_report_path=qc,
                requested_format="wav24_48k",
                require_master_qc=True,
                master_qc_report_path=master,
                require_release_package=True,
                release_package_manifest_path=package["paths"]["manifest"],
                release_qc_report_path=package["paths"]["release_qc_report"],
            )

            self.assertTrue(package["paths"]["manifest"].exists())
            self.assertFalse(package["manifest"]["release_ready"])
            self.assertEqual(package["manifest"]["release_status"], "DRAFT_RELEASE_PACKAGE")
            self.assertFalse(status.complete)
            self.assertIn("required release metadata is incomplete", " ".join(status.blocking_reasons))


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from completion_gate import check_completion_status  # noqa: E402
from release_package import build_release_package, write_release_package  # noqa: E402


def touch(path: Path, content: str = "ok\n") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


class ReleasePackageTests(unittest.TestCase):
    def test_completion_gate_can_require_release_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            final = touch(root / "05_FINAL_WAV" / "final.wav")
            qc = touch(root / "06_QC_REPORT" / "qc_report.md")
            master = touch(root / "09_MIX_MASTER" / "master_qc_report.md")
            verify = {
                "exists": True,
                "ok": True,
                "format_verified": True,
                "duration_seconds": 1.0,
                "peak_dbfs": -3.0,
                "rms_dbfs": -18.0,
                "clipping_count": 0,
            }

            blocked = check_completion_status(
                final_wav_path=final,
                qc_report_path=qc,
                requested_format="wav24_48k",
                final_verify_result=verify,
                require_master_qc=True,
                master_qc_report_path=master,
                require_release_package=True,
                release_package_manifest_path=root / "06_QC_REPORT" / "missing.json",
            )

            self.assertFalse(blocked.complete)
            self.assertIn("release package manifest missing", " ".join(blocked.blocking_reasons))

    def test_release_package_writes_manifest_checklist_metadata_and_safety_notes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            final = touch(root / "05_FINAL_WAV" / "final.wav")
            qc = touch(root / "06_QC_REPORT" / "qc_report.md")
            master = touch(root / "09_MIX_MASTER" / "master_qc_report.md")
            manifest = touch(root / "06_QC_REPORT" / "audio_render_manifest.json", "{}\n")
            autopilot = touch(root / "06_QC_REPORT" / "autopilot_qc_report.md")
            commercial = touch(root / "06_QC_REPORT" / "commercial_readiness_report.md")
            package = build_release_package(
                final_wav_path=final,
                qc_report_path=qc,
                master_qc_report_path=master,
                audio_render_manifest_path=manifest,
                autopilot_qc={
                    "commercial_readiness_qc": {
                        "status": "FINAL_PASS",
                        "false_claim_risk": {"high": False, "risky_flags": []},
                        "safety": {"safe": True},
                    }
                },
                autopilot_qc_paths={"autopilot_qc_report": autopilot, "commercial_readiness_report": commercial},
                production_intent={"target_elements": ["arrangement"], "safety": {"copying_risk": "low", "exact_copy_allowed": False}},
                verification={"ok": True, "format_verified": True, "sample_rate": 48000, "bit_depth": 24, "clipping_count": 0},
                completion_gate={"complete": True, "blocking_reasons": []},
                options={"workflow": "song_to_mix_master", "mode": "full_song_stereo"},
            )
            paths = write_release_package(root, package)

            self.assertTrue(paths["manifest"].exists())
            self.assertTrue(paths["metadata"].exists())
            self.assertTrue(paths["checklist"].exists())
            self.assertTrue(paths["safety_notes"].exists())
            self.assertTrue(paths["release_qc_report"].exists())
            written = paths["manifest"].read_text(encoding="utf-8")
            self.assertIn('"release_ready": true', written)
            self.assertIn("not_distribution_approval", written)


if __name__ == "__main__":
    unittest.main()

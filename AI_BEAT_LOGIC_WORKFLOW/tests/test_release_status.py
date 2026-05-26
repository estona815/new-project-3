from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from completion_gate import check_completion_status  # noqa: E402
from release_status import (  # noqa: E402
    ARRANGEMENT_PLAN_READY,
    COMPLETE,
    RELEASE_PACKAGE_READY,
    RESCUE_PLAN_READY,
    build_release_status,
    infer_release_status_from_artifacts,
)
from release_workflow_orchestrator import write_release_workflow_status  # noqa: E402


def touch(path: Path, text: str = "ok\n") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


class ReleaseStatusTests(unittest.TestCase):
    def test_plan_only_status_never_allows_complete(self) -> None:
        status = build_release_status(workflow="plan_only", status=ARRANGEMENT_PLAN_READY)

        self.assertFalse(status["complete_allowed"])
        self.assertFalse(status["release_package_ready"])
        self.assertIn("not COMPLETE", " ".join(status["blocking_reasons"]))

    def test_rescue_plan_ready_never_allows_complete(self) -> None:
        status = build_release_status(workflow="bad_ai_song_rescue", status=RESCUE_PLAN_READY)

        self.assertFalse(status["complete_allowed"])
        self.assertIn("not COMPLETE", " ".join(status["blocking_reasons"]))

    def test_release_package_ready_is_separate_from_complete(self) -> None:
        status = build_release_status(
            workflow="song_to_release",
            status=RELEASE_PACKAGE_READY,
            completion_gate={"complete": True, "blocking_reasons": []},
            final_audio_verified=True,
            release_package_ready=True,
        )

        self.assertEqual(status["status"], RELEASE_PACKAGE_READY)
        self.assertFalse(status["complete_allowed"])
        self.assertIn("separate from COMPLETE", " ".join(status["blocking_reasons"]))

    def test_complete_requires_complete_status_and_gate(self) -> None:
        status = build_release_status(
            workflow="song_to_release",
            status=COMPLETE,
            completion_gate={"complete": True, "blocking_reasons": []},
            final_audio_verified=True,
            release_package_ready=True,
        )

        self.assertTrue(status["complete_allowed"])
        self.assertEqual(status["blocking_reasons"], [])

    def test_infer_release_package_ready_requires_manifest_and_release_qc(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            touch(root / "05_FINAL_WAV" / "final.wav")
            manifest = touch(
                root / "06_QC_REPORT" / "release_package_manifest.json",
                json.dumps({"release_ready": True}) + "\n",
            )
            status = infer_release_status_from_artifacts(
                project_root=root,
                workflow="song_to_release",
                completion_gate={"complete": False, "blocking_reasons": []},
                final_audio_verified=True,
                release_package_manifest_path=manifest,
            )
            self.assertEqual(status["status"], "FINAL_MASTER_EXPORTED_VERIFIED")
            self.assertFalse(status["release_package_ready"])

            touch(root / "06_QC_REPORT" / "release_qc_report.md")
            status = infer_release_status_from_artifacts(
                project_root=root,
                workflow="song_to_release",
                completion_gate={"complete": False, "blocking_reasons": []},
                final_audio_verified=True,
                release_package_manifest_path=manifest,
            )
            self.assertEqual(status["status"], RELEASE_PACKAGE_READY)
            self.assertTrue(status["release_package_ready"])
            self.assertFalse(status["complete_allowed"])

    def test_completion_gate_requires_release_qc_report_when_release_package_required(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            final = touch(root / "05_FINAL_WAV" / "final.wav")
            qc = touch(root / "06_QC_REPORT" / "qc_report.md")
            master = touch(root / "09_MIX_MASTER" / "master_qc_report.md")
            manifest = touch(root / "06_QC_REPORT" / "release_package_manifest.json", json.dumps({"release_ready": True}) + "\n")
            verify = {
                "exists": True,
                "ok": True,
                "format_verified": True,
                "duration_seconds": 1.0,
                "peak_dbfs": -3.0,
                "rms_dbfs": -18.0,
                "clipping_count": 0,
            }

            status = check_completion_status(
                final_wav_path=final,
                qc_report_path=qc,
                requested_format="wav24_48k",
                final_verify_result=verify,
                require_master_qc=True,
                master_qc_report_path=master,
                require_release_package=True,
                release_package_manifest_path=manifest,
                release_qc_report_path=root / "06_QC_REPORT" / "release_qc_report.md",
            )

            self.assertFalse(status.complete)
            self.assertIn("release QC report missing", " ".join(status.blocking_reasons))

    def test_orchestrator_writes_schema(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            touch(root / "02_EDIT_PLAN" / "production_intent.json", "{}\n")
            result = write_release_workflow_status(project_root=root, workflow="song_to_mix_master", mode="full_song_stereo")

            self.assertTrue(result["path"].exists())
            payload = json.loads(result["path"].read_text(encoding="utf-8"))
            self.assertEqual(payload["schema_version"], "release_status.v1")
            self.assertEqual(payload["workflow"], "song_to_release")
            self.assertEqual(payload["status"], "REQUEST_PARSED")
            self.assertFalse(payload["complete_allowed"])

    def test_infer_release_status_detects_rescue_plan(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            touch(root / "02_EDIT_PLAN" / "rescue_arrangement_plan.json", "{}\n")
            touch(root / "01_ANALYSIS" / "bad_song_diagnosis.json", "{}\n")

            status = infer_release_status_from_artifacts(project_root=root, workflow="bad_ai_song_rescue")

            self.assertEqual(status["status"], RESCUE_PLAN_READY)
            self.assertFalse(status["complete_allowed"])
            self.assertTrue(any("rescue_arrangement_plan.json" in item for item in status["generated_deliverables"]))


if __name__ == "__main__":
    unittest.main()

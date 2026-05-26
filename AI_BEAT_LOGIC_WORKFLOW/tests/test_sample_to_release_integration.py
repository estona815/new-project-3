from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))
sys.path.insert(0, str(PROJECT_ROOT / "tests"))

from arrangement_autopilot import run_arrangement_autopilot  # noqa: E402
from composition_autopilot import run_composition_autopilot  # noqa: E402
from export_audio import write_float_wav  # noqa: E402
from release_package_builder import build_and_write_release_package  # noqa: E402
from sample_analysis import write_sample_analysis  # noqa: E402
from test_release_ready_workflow_integration import complete_metadata, clear_rights, write_basic_reports, write_dummy_wav  # noqa: E402


class SampleToReleaseIntegrationTests(unittest.TestCase):
    def test_unknown_sample_ownership_blocks_direct_sample_and_release_ready(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sample = write_dummy_wav(root / "input" / "sample.wav", seconds=4.0, freq=260.0)
            rough = "이 샘플로 SYSTEM SEOUL/ycs 결 비트 짜고 믹마 플랜까지."

            sample_paths = write_sample_analysis(sample, project_root=root, ownership_status="unknown")
            composition = run_composition_autopilot(project_root=root, rough_request=rough, style_cluster="system_seoul_adjacent")
            arrangement = run_arrangement_autopilot(project_root=root, sample_path=sample, genre="system_seoul_adjacent", request_text=rough)
            package = build_and_write_release_package(
                root,
                final_master_path=None,
                metadata=complete_metadata(),
                rights=clear_rights(contains_samples=True, all_samples_owned_or_cleared=None),
            )

            sample_analysis = json.loads(sample_paths["json"].read_text(encoding="utf-8"))
            self.assertFalse(sample_analysis["sample_usage_safety"]["direct_sample_use_allowed"])
            self.assertFalse(composition["guide"]["safety"]["sample_use_allowed"])
            self.assertFalse(arrangement["plan"]["sample_chop_guide"]["direct_sample_use_allowed"])
            self.assertTrue(arrangement["plan"]["sample_chop_guide"]["direct_sample_layer_blocked"])
            self.assertFalse(composition["guide"]["safety"]["exact_reference_copy"])
            self.assertFalse(package["manifest"]["release_ready"])

    def test_owned_sample_allows_local_layering_without_web_extraction(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sample = write_dummy_wav(root / "input" / "owned_sample.wav", seconds=4.0, freq=220.0)
            final = root / "05_FINAL_WAV" / "final.wav"
            write_float_wav(final, [[0.1] * 4800, [0.1] * 4800], 48000, bit_depth=24)
            qc, master = write_basic_reports(root)

            sample_paths = write_sample_analysis(sample, project_root=root, ownership_status="owned")
            composition = run_composition_autopilot(project_root=root, rough_request="샘플로 힙합/하이퍼팝 편곡.", user_owned_sample_or_stem=True)
            package = build_and_write_release_package(
                root,
                final_master_path=final,
                metadata=complete_metadata(),
                rights=clear_rights(contains_samples=True, all_samples_owned_or_cleared=True),
                qc_report_path=qc,
                master_qc_report_path=master,
                completion_gate={"complete": True},
            )
            sample_analysis = json.loads(sample_paths["json"].read_text(encoding="utf-8"))

            self.assertTrue(sample_analysis["sample_usage_safety"]["direct_sample_use_allowed"])
            self.assertTrue(composition["guide"]["safety"]["sample_use_allowed"])
            self.assertTrue(package["manifest"]["release_ready"])
            self.assertFalse(package["manifest"]["rights"]["web_audio_downloaded"])


if __name__ == "__main__":
    unittest.main()

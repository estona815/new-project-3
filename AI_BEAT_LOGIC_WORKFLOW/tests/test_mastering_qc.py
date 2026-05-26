from __future__ import annotations

import math
import sys
import tempfile
import unittest
import wave
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_DIR))

from master_qc import verify_master_completion  # noqa: E402
from mastering import run_mastering_stage  # noqa: E402
from paths import ensure_folder_structure  # noqa: E402


def write_wav(path: Path, sample_rate: int = 48000, seconds: float = 1.0, clipped: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frames = max(1, int(sample_rate * seconds))
    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(2)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        for index in range(frames):
            if clipped and index % 100 == 0:
                value = 32767
            else:
                value = int(math.sin(2.0 * math.pi * 440.0 * index / sample_rate) * 12000)
            raw = value.to_bytes(2, "little", signed=True)
            wav_file.writeframesraw(raw + raw)


class MasteringQCTests(unittest.TestCase):
    def test_master_ready_headroom_renders_final_and_report(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_root = Path(tmp) / "AI_BEAT_LOGIC_WORKFLOW"
            ensure_folder_structure(project_root)
            write_wav(project_root / "09_MIX_MASTER" / "pre_master.wav")

            result = run_mastering_stage(
                {"master_loudness": "master_ready_headroom", "export_format": "wav24_48k"},
                project_root,
            )

            self.assertTrue((project_root / "09_MIX_MASTER" / "final_mix_master.wav").exists())
            self.assertTrue((project_root / "09_MIX_MASTER" / "master_qc_report.md").exists())
            self.assertTrue(result["completion_gate"]["complete"])
            self.assertEqual(result["final_info"]["bit_depth"], 24)
            self.assertLessEqual(result["final_info"]["peak_dbfs"], -1.4)

    def test_loud_demo_warns_about_reduced_headroom(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_root = Path(tmp) / "AI_BEAT_LOGIC_WORKFLOW"
            ensure_folder_structure(project_root)
            write_wav(project_root / "09_MIX_MASTER" / "pre_master.wav")

            result = run_mastering_stage(
                {"master_loudness": "loud_demo", "export_format": "wav24_48k"},
                project_root,
            )
            report = Path(result["master_qc_report"]).read_text(encoding="utf-8")

            self.assertIn("reduced headroom", report)
            self.assertIn("less master-ready", report)

    def test_master_qc_blocks_completion_on_clipping(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_root = Path(tmp) / "AI_BEAT_LOGIC_WORKFLOW"
            ensure_folder_structure(project_root)
            final_path = project_root / "09_MIX_MASTER" / "final_mix_master.wav"
            report_path = project_root / "09_MIX_MASTER" / "master_qc_report.md"
            write_wav(final_path, clipped=True)
            report_path.write_text("# Master QC Report\n", encoding="utf-8")

            status = verify_master_completion(
                project_root,
                {"export_format": "wav24_48k"},
                final_path=final_path,
                report_path=report_path,
            )

            self.assertFalse(status["complete"])
            self.assertIn("clipping detected", " ".join(status["blocking_reasons"]))

    def test_master_qc_blocks_wrong_sample_rate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_root = Path(tmp) / "AI_BEAT_LOGIC_WORKFLOW"
            ensure_folder_structure(project_root)
            final_path = project_root / "09_MIX_MASTER" / "final_mix_master.wav"
            report_path = project_root / "09_MIX_MASTER" / "master_qc_report.md"
            write_wav(final_path, sample_rate=44100)
            report_path.write_text("# Master QC Report\n", encoding="utf-8")

            status = verify_master_completion(
                project_root,
                {"export_format": "wav24_48k"},
                final_path=final_path,
                report_path=report_path,
            )

            self.assertFalse(status["complete"])
            self.assertIn("wrong sample rate", " ".join(status["blocking_reasons"]))

    def test_master_qc_blocks_wrong_bit_depth(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_root = Path(tmp) / "AI_BEAT_LOGIC_WORKFLOW"
            ensure_folder_structure(project_root)
            final_path = project_root / "09_MIX_MASTER" / "final_mix_master.wav"
            report_path = project_root / "09_MIX_MASTER" / "master_qc_report.md"
            write_wav(final_path, sample_rate=48000)
            report_path.write_text("# Master QC Report\n", encoding="utf-8")

            status = verify_master_completion(
                project_root,
                {"export_format": "wav24_48k"},
                final_path=final_path,
                report_path=report_path,
            )

            self.assertFalse(status["complete"])
            self.assertIn("wrong bit depth", " ".join(status["blocking_reasons"]))
            self.assertIn("24-bit PCM", " ".join(status["blocking_reasons"]))

    def test_master_qc_blocks_missing_report(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_root = Path(tmp) / "AI_BEAT_LOGIC_WORKFLOW"
            ensure_folder_structure(project_root)
            final_path = project_root / "09_MIX_MASTER" / "final_mix_master.wav"
            write_wav(final_path)

            status = verify_master_completion(project_root, {"export_format": "wav24_48k"}, final_path=final_path)

            self.assertFalse(status["complete"])
            self.assertIn("master QC report missing", " ".join(status["blocking_reasons"]))


if __name__ == "__main__":
    unittest.main()

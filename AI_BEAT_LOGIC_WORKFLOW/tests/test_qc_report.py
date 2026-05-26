from __future__ import annotations

import json
import math
import sys
import tempfile
import unittest
import wave
from pathlib import Path
from unittest import mock


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_DIR))

from final_verify import expected_final_name, verify_final_export  # noqa: E402
from paths import ensure_folder_structure  # noqa: E402
from qc_report import run_final_export_and_qc  # noqa: E402
from reference_profile import build_reference_target_profile  # noqa: E402


def write_master_qc(project_root: Path) -> None:
    path = project_root / "09_MIX_MASTER" / "master_qc_report.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("# Master QC Report\n\n- status: test fixture\n", encoding="utf-8")


def write_source_wav(path: Path, seconds: float = 2.0, sample_rate: int = 48000) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frames = int(seconds * sample_rate)
    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(2)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        for index in range(frames):
            value = int(math.sin(2 * math.pi * 440 * index / sample_rate) * 9000)
            data = value.to_bytes(2, "little", signed=True)
            wav_file.writeframesraw(data + data)


def write_metadata(project_root: Path) -> None:
    (project_root / "01_ANALYSIS").mkdir(parents=True, exist_ok=True)
    (project_root / "01_ANALYSIS" / "input_metadata.json").write_text(
        json.dumps(
            {
                "original_path": "/tmp/original song.wav",
                "copied_path": str(project_root / "00_INPUT_SUNO" / "original_song.wav"),
                "working_wav_path": str(project_root / "04_PROCESSED_AUDIO" / "working_input.wav"),
            }
        ),
        encoding="utf-8",
    )
    (project_root / "01_ANALYSIS" / "analysis.json").write_text(
        json.dumps(
            {
                "vocal_like_texture_candidates": [{"start": 1.0, "end": 2.0}],
                "low_end_excess_candidates": [{"start": 1.0, "end": 2.0}],
                "melody_buried_candidates": [],
                "arrangement_candidates": {
                    "ai_random_transition_or_glitch_candidates": [{"start": 0.5, "end": 0.6}],
                    "repeated_loop_blocks": [],
                },
            }
        ),
        encoding="utf-8",
    )


class QCReportTests(unittest.TestCase):
    def test_final_export_and_qc_report_are_created_from_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_root = Path(tmp) / "AI_BEAT_LOGIC_WORKFLOW"
            ensure_folder_structure(project_root)
            fallback = project_root / "04_PROCESSED_AUDIO" / "fallback_processed.wav"
            write_source_wav(fallback)
            write_metadata(project_root)
            write_master_qc(project_root)

            result = run_final_export_and_qc(
                options={"export_format": "wav24_48k", "length_mode": "under_2min"},
                project_root=project_root,
            )
            final_path = project_root / "05_FINAL_WAV" / expected_final_name("wav24_48k")
            report_path = project_root / "06_QC_REPORT" / "qc_report.md"
            report = report_path.read_text(encoding="utf-8")

            self.assertTrue(final_path.exists())
            self.assertTrue(report_path.exists())
            self.assertTrue(result["complete"])
            self.assertIn("fallback stereo processing was used", report)
            self.assertIn("This report does not claim Logic mixing if fallback was used", report)
            self.assertIn("Single stereo file limits stem-level control", report)
            verification = verify_final_export(final_path, "wav24_48k", "under_2min")
            self.assertTrue(verification["passed"])

    def test_441k_export_name_and_sample_rate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_root = Path(tmp) / "AI_BEAT_LOGIC_WORKFLOW"
            ensure_folder_structure(project_root)
            fallback = project_root / "04_PROCESSED_AUDIO" / "fallback_processed.wav"
            write_source_wav(fallback, sample_rate=44100)
            write_metadata(project_root)
            write_master_qc(project_root)

            result = run_final_export_and_qc(
                options={"export_format": "wav24_44k", "length_mode": "keep_original"},
                project_root=project_root,
            )
            self.assertEqual(Path(result["final_path"]).name, "final_suno_logic_processed_24bit_44k.wav")
            self.assertEqual(result["verification"]["sample_rate"], 44100)
            self.assertTrue(result["complete"])

    def test_missing_master_qc_blocks_completion(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_root = Path(tmp) / "AI_BEAT_LOGIC_WORKFLOW"
            ensure_folder_structure(project_root)
            fallback = project_root / "04_PROCESSED_AUDIO" / "fallback_processed.wav"
            write_source_wav(fallback)
            write_metadata(project_root)

            result = run_final_export_and_qc(
                options={"export_format": "wav24_48k", "length_mode": "under_2min"},
                project_root=project_root,
            )

            self.assertFalse(result["complete"])
            self.assertIn("master QC report missing", " ".join(result["completion_gate"].blocking_reasons))

    def test_missing_source_fails_before_complete(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_root = Path(tmp) / "AI_BEAT_LOGIC_WORKFLOW"
            ensure_folder_structure(project_root)
            with self.assertRaises(FileNotFoundError):
                run_final_export_and_qc(
                    options={"export_format": "wav24_48k", "length_mode": "under_2min"},
                    project_root=project_root,
                )

    def test_final_export_requires_ffmpeg_or_afconvert(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_root = Path(tmp) / "AI_BEAT_LOGIC_WORKFLOW"
            ensure_folder_structure(project_root)
            fallback = project_root / "04_PROCESSED_AUDIO" / "fallback_processed.wav"
            write_source_wav(fallback)
            write_metadata(project_root)

            with mock.patch("qc_report.ffmpeg_path", return_value=None):
                with mock.patch("qc_report.shutil.which", return_value=None):
                    with self.assertRaises(RuntimeError):
                        run_final_export_and_qc(
                            options={"export_format": "wav24_48k", "length_mode": "under_2min"},
                            project_root=project_root,
                        )

    def test_qc_report_includes_creative_reference_scoring_and_limits(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_root = Path(tmp) / "AI_BEAT_LOGIC_WORKFLOW"
            ensure_folder_structure(project_root)
            fallback = project_root / "04_PROCESSED_AUDIO" / "fallback_processed.wav"
            write_source_wav(fallback)
            write_metadata(project_root)
            write_master_qc(project_root)
            phrase = "ㅇㅇㅇ이라는 곡 베이스처럼 쳐줘"
            brief = {
                "mode": "full_song_stereo",
                "input_files": {"main_input": str(fallback), "reference_audio": ""},
                "creative_target": phrase,
                "priority": "808/bass",
                "avoid": ["muddy 808", "generic trap loop"],
                "drum_808_direction": "strong_controlled",
                "master_direction": "master_ready_headroom",
            }
            profile = build_reference_target_profile(phrase, None, brief)
            profile_path = project_root / "08_REFERENCE_MATCH" / "reference_target_profile.json"
            profile_path.parent.mkdir(parents=True, exist_ok=True)
            profile_path.write_text(json.dumps(profile, ensure_ascii=False), encoding="utf-8")

            result = run_final_export_and_qc(
                options={"export_format": "wav24_48k", "length_mode": "under_2min", "creative_brief": brief},
                project_root=project_root,
            )
            report = Path(result["qc_report"]).read_text(encoding="utf-8")

            self.assertIn("## Creative Target Review", report)
            self.assertIn(f"User creative target: {phrase}", report)
            self.assertIn("target support: text-only", report)
            self.assertIn("## Reference Match QC", report)
            self.assertIn("Bass/808 reference direction match", report)
            self.assertIn("Stereo-only limitation impact", report)
            self.assertIn("heuristic/text-only", report)
            self.assertIn("NEEDS_MANUAL_LOGIC_EDIT", report)
            self.assertIn("exact reference song match: not claimed", report)


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_DIR))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from export_audio import verify_wav  # noqa: E402
from generate_dummy_audio import FIXTURE_PATH, generate_dummy_audio  # noqa: E402


GENERATED_PATHS = [
    PROJECT_ROOT / "04_PROCESSED_AUDIO" / "working_input.wav",
    PROJECT_ROOT / "04_PROCESSED_AUDIO" / "fallback_processed.wav",
    PROJECT_ROOT / "04_PROCESSED_AUDIO" / "processing_log.md",
    PROJECT_ROOT / "05_FINAL_WAV" / "final_suno_logic_processed_24bit_48k.wav",
    PROJECT_ROOT / "05_FINAL_WAV" / "final_suno_logic_processed_24bit_44k.wav",
    PROJECT_ROOT / "05_FINAL_WAV" / "final_preview.mp3",
    PROJECT_ROOT / "06_QC_REPORT" / "final_verification.json",
    PROJECT_ROOT / "06_QC_REPORT" / "audio_render_manifest.json",
    PROJECT_ROOT / "06_QC_REPORT" / "arrangement_qc_report.md",
    PROJECT_ROOT / "06_QC_REPORT" / "commercial_readiness_report.md",
    PROJECT_ROOT / "06_QC_REPORT" / "autopilot_qc_report.md",
    PROJECT_ROOT / "06_QC_REPORT" / "autopilot_qc_report.json",
    PROJECT_ROOT / "tests" / "fixtures" / "dummy_suno_like.wav",
    PROJECT_ROOT / "07_VOCAL_PROCESSING" / "vocal_analysis.json",
    PROJECT_ROOT / "07_VOCAL_PROCESSING" / "vocal_processing_log.md",
    PROJECT_ROOT / "07_VOCAL_PROCESSING" / "vocal_chain_plan.md",
    PROJECT_ROOT / "08_REFERENCE_MATCH" / "reference_analysis.json",
    PROJECT_ROOT / "08_REFERENCE_MATCH" / "reference_target_profile.json",
    PROJECT_ROOT / "08_REFERENCE_MATCH" / "style_translation.md",
    PROJECT_ROOT / "09_MIX_MASTER" / "mix_session_plan.md",
    PROJECT_ROOT / "09_MIX_MASTER" / "master_qc_report.md",
    PROJECT_ROOT / "09_MIX_MASTER" / "mix_master_plan.json",
    PROJECT_ROOT / "09_MIX_MASTER" / "mix_master_plan.md",
    PROJECT_ROOT / "01_ANALYSIS" / "input_metadata.json",
    PROJECT_ROOT / "01_ANALYSIS" / "conversion_error.md",
    PROJECT_ROOT / "01_ANALYSIS" / "dependency_capabilities.json",
    PROJECT_ROOT / "01_ANALYSIS" / "sample_analysis.json",
    PROJECT_ROOT / "01_ANALYSIS" / "sample_analysis_summary.md",
    PROJECT_ROOT / "01_ANALYSIS" / "vocal_to_code.json",
    PROJECT_ROOT / "01_ANALYSIS" / "vocal_to_code_summary.md",
    PROJECT_ROOT / "01_ANALYSIS" / "song_structure_analysis.json",
    PROJECT_ROOT / "01_ANALYSIS" / "song_structure_summary.md",
    PROJECT_ROOT / "02_EDIT_PLAN" / "vocal_pitch_guide.json",
    PROJECT_ROOT / "02_EDIT_PLAN" / "arrangement_plan.json",
    PROJECT_ROOT / "02_EDIT_PLAN" / "arrangement_plan.md",
    PROJECT_ROOT / "02_EDIT_PLAN" / "section_progression_guide.json",
    PROJECT_ROOT / "02_EDIT_PLAN" / "chord_progression_guide.json",
    PROJECT_ROOT / "02_EDIT_PLAN" / "bass_808_midi_guide.json",
    PROJECT_ROOT / "02_EDIT_PLAN" / "drum_programming_guide.json",
    PROJECT_ROOT / "02_EDIT_PLAN" / "sample_chop_guide.json",
    PROJECT_ROOT / "02_EDIT_PLAN" / "melody_variation_guide.json",
    PROJECT_ROOT / "02_EDIT_PLAN" / "midi_region_guide.json",
    PROJECT_ROOT / "02_EDIT_PLAN" / "automation_guide.json",
    PROJECT_ROOT / "02_EDIT_PLAN" / "drum_midi_guide.json",
    PROJECT_ROOT / "02_EDIT_PLAN" / "logic_arrangement_plan.md",
    PROJECT_ROOT / "03_LOGIC_PROJECT" / "logic_autopilot_status.json",
]

TRACKED_GENERATED_FILES = [
    PROJECT_ROOT / "01_ANALYSIS" / "analysis.json",
    PROJECT_ROOT / "01_ANALYSIS" / "analysis_summary.md",
    PROJECT_ROOT / "02_EDIT_PLAN" / "edit_plan.md",
    PROJECT_ROOT / "06_QC_REPORT" / "qc_report.md",
]


def cleanup_generated_outputs() -> None:
    for path in GENERATED_PATHS:
        if path.exists():
            path.unlink()


def capture_tracked_generated_files() -> dict[Path, str | None]:
    return {path: path.read_text(encoding="utf-8") if path.exists() else None for path in TRACKED_GENERATED_FILES}


def restore_tracked_generated_files(snapshot: dict[Path, str | None]) -> None:
    for path, content in snapshot.items():
        if content is None:
            if path.exists():
                path.unlink()
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
    for directory, pattern in [
        (PROJECT_ROOT / "00_INPUT_SUNO", "dummy_suno_like*.wav"),
        (PROJECT_ROOT / "04_PROCESSED_AUDIO", "working_input_backup_*.wav"),
        (PROJECT_ROOT / "04_PROCESSED_AUDIO", "fallback_processed_backup_*.wav"),
    ]:
        for path in directory.glob(pattern):
            path.unlink()


class FullPipelineTests(unittest.TestCase):
    def test_dummy_pipeline_produces_final_wav_and_qc_report(self) -> None:
        snapshot = capture_tracked_generated_files()
        cleanup_generated_outputs()
        generate_dummy_audio()
        try:
            command = [
                "python3",
                str(PROJECT_ROOT / "src" / "main.py"),
                "--input",
                str(FIXTURE_PATH),
                "--length-mode",
                "under_2min",
                "--vocal-mode",
                "suppress",
                "--melody-focus",
                "front",
                "--drum-808",
                "strong_controlled",
                "--export-format",
                "wav24_48k",
                "--save-logic-project",
                "false",
            ]
            result = subprocess.run(command, cwd=str(PROJECT_ROOT.parent), check=False, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("COMPLETE", result.stdout)

            required_dirs = [
                "00_INPUT_SUNO",
                "01_ANALYSIS",
                "02_EDIT_PLAN",
                "03_LOGIC_PROJECT",
                "04_PROCESSED_AUDIO",
                "05_FINAL_WAV",
                "06_QC_REPORT",
                "07_VOCAL_PROCESSING",
                "08_REFERENCE_MATCH",
                "09_MIX_MASTER",
                "tools",
                "scripts",
                "src",
                "tests",
            ]
            for relative in required_dirs:
                self.assertTrue((PROJECT_ROOT / relative).is_dir(), relative)

            self.assertTrue((PROJECT_ROOT / "04_PROCESSED_AUDIO" / "working_input.wav").exists())
            self.assertTrue((PROJECT_ROOT / "01_ANALYSIS" / "analysis.json").exists())
            self.assertTrue((PROJECT_ROOT / "02_EDIT_PLAN" / "edit_plan.md").exists())
            self.assertTrue((PROJECT_ROOT / "04_PROCESSED_AUDIO" / "fallback_processed.wav").exists())
            final_wav = PROJECT_ROOT / "05_FINAL_WAV" / "final_suno_logic_processed_24bit_48k.wav"
            self.assertTrue(final_wav.exists())
            self.assertTrue((PROJECT_ROOT / "06_QC_REPORT" / "qc_report.md").exists())
            self.assertTrue((PROJECT_ROOT / "09_MIX_MASTER" / "mix_session_plan.md").exists())

            verification = verify_wav(final_wav)
            self.assertGreater(verification["duration_seconds"], 0.0)
            self.assertEqual(verification["sample_rate"], 48000)
        finally:
            cleanup_generated_outputs()
            restore_tracked_generated_files(snapshot)


if __name__ == "__main__":
    unittest.main()

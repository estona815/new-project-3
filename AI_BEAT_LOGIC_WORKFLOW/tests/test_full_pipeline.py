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
    PROJECT_ROOT / "01_ANALYSIS" / "input_metadata.json",
    PROJECT_ROOT / "01_ANALYSIS" / "conversion_error.md",
]


def cleanup_generated_outputs() -> None:
    for path in GENERATED_PATHS:
        if path.exists():
            path.unlink()
    for directory, pattern in [
        (PROJECT_ROOT / "00_INPUT_SUNO", "dummy_suno_like*.wav"),
        (PROJECT_ROOT / "04_PROCESSED_AUDIO", "working_input_backup_*.wav"),
        (PROJECT_ROOT / "04_PROCESSED_AUDIO", "fallback_processed_backup_*.wav"),
    ]:
        for path in directory.glob(pattern):
            path.unlink()


class FullPipelineTests(unittest.TestCase):
    def test_dummy_pipeline_produces_final_wav_and_qc_report(self) -> None:
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

            verification = verify_wav(final_wav)
            self.assertGreater(verification["duration_seconds"], 0.0)
            self.assertEqual(verification["sample_rate"], 48000)
        finally:
            cleanup_generated_outputs()


if __name__ == "__main__":
    unittest.main()

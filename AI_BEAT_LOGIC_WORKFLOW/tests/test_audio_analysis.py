from __future__ import annotations

import json
import math
import sys
import tempfile
import unittest
import wave
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_DIR))

from audio_analysis import analyze_working_wav  # noqa: E402
from paths import ensure_folder_structure  # noqa: E402


def write_test_wav(path: Path, sample_rate: int = 48000, seconds: float = 2.0) -> None:
    frames = max(1, int(sample_rate * seconds))
    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(2)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        for index in range(frames):
            if index < sample_rate // 2:
                value = 0
            else:
                tone = math.sin(2.0 * math.pi * 440.0 * index / sample_rate)
                low = math.sin(2.0 * math.pi * 60.0 * index / sample_rate)
                value = int((tone * 0.25 + low * 0.15) * 32767)
            sample = value.to_bytes(2, "little", signed=True)
            wav_file.writeframesraw(sample + sample)


class AudioAnalysisTests(unittest.TestCase):
    def test_analyze_working_wav_writes_json_and_summary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_root = Path(tmp) / "AI_BEAT_LOGIC_WORKFLOW"
            ensure_folder_structure(project_root)
            working = project_root / "04_PROCESSED_AUDIO" / "working_input.wav"
            write_test_wav(working)

            analysis = analyze_working_wav(working, project_root)
            analysis_path = project_root / "01_ANALYSIS" / "analysis.json"
            summary_path = project_root / "01_ANALYSIS" / "analysis_summary.md"
            parsed = json.loads(analysis_path.read_text(encoding="utf-8"))
            summary = summary_path.read_text(encoding="utf-8")

            self.assertEqual(parsed["metadata"]["sample_rate"], 48000)
            self.assertEqual(parsed["metadata"]["channels"], 2)
            self.assertGreater(parsed["metadata"]["duration_seconds"], 1.9)
            self.assertIn("level_analysis", parsed)
            self.assertIn("short_term_loudness_windows", parsed["level_analysis"])
            self.assertIn("silence_detection", parsed)
            self.assertIn("arrangement_candidates", parsed)
            self.assertIn("heuristic", parsed["producer_notes"]["heuristic_disclaimer"].lower())
            self.assertIn("Overall Diagnosis", summary)
            self.assertIn("Best Hook Candidate", summary)
            self.assertIn("Vocal Chop Suppression Notes", summary)
            self.assertEqual(analysis["metadata"]["bit_depth"], 16)

    def test_short_file_does_not_crash(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_root = Path(tmp) / "AI_BEAT_LOGIC_WORKFLOW"
            ensure_folder_structure(project_root)
            working = project_root / "04_PROCESSED_AUDIO" / "working_input.wav"
            write_test_wav(working, seconds=0.1)

            analysis = analyze_working_wav(working, project_root)
            self.assertGreater(analysis["metadata"]["duration_seconds"], 0.0)
            self.assertTrue((project_root / "01_ANALYSIS" / "analysis.json").exists())
            self.assertTrue((project_root / "01_ANALYSIS" / "analysis_summary.md").exists())

    def test_missing_working_wav_is_clean_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_root = Path(tmp) / "AI_BEAT_LOGIC_WORKFLOW"
            ensure_folder_structure(project_root)
            with self.assertRaises(FileNotFoundError):
                analyze_working_wav(project_root / "04_PROCESSED_AUDIO" / "working_input.wav", project_root)


if __name__ == "__main__":
    unittest.main()


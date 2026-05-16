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

from export_audio import verify_wav  # noqa: E402
from fallback_processing import choose_section, run_fallback_processing  # noqa: E402
from paths import ensure_folder_structure  # noqa: E402


def write_wav(path: Path, seconds: float = 3.0, sample_rate: int = 48000) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frames = int(seconds * sample_rate)
    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(2)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        for index in range(frames):
            value = int(math.sin(2 * math.pi * 440 * index / sample_rate) * 16000)
            data = value.to_bytes(2, "little", signed=True)
            wav_file.writeframesraw(data + data)


def analysis_fixture(duration: float = 3.0) -> dict:
    return {
        "metadata": {"duration_seconds": duration, "sample_rate": 48000, "channels": 2},
        "silence_detection": {"intro_silence": None, "outro_silence": None, "internal_silence_candidates": []},
        "arrangement_candidates": {
            "first_hook_or_main_motif_entrance": {"start": 1.0, "end": 2.0, "confidence": "medium"},
            "main_melody_strongest_region": {"start": 1.0, "end": 2.0},
            "ai_random_transition_or_glitch_candidates": [],
        },
        "low_end_excess_candidates": [{"start": 1.0, "end": 2.0, "reason": "test low-end flag"}],
        "over_compression_detection": {"possible_over_compression": False},
        "vocal_like_texture_candidates": [{"start": 1.0, "end": 2.0, "confidence": "medium"}],
    }


class FallbackProcessingTests(unittest.TestCase):
    def test_choose_15sec_section_around_hook(self) -> None:
        decision = choose_section(
            analysis_fixture(duration=60.0),
            {"length_mode": "15sec_reels"},
        )
        self.assertLessEqual(decision.end - decision.start, 15.0)
        self.assertIn("15-second", decision.reason)

    def test_python_fallback_produces_wav_and_log(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_root = Path(tmp) / "AI_BEAT_LOGIC_WORKFLOW"
            ensure_folder_structure(project_root)
            input_path = project_root / "04_PROCESSED_AUDIO" / "working_input.wav"
            output_path = project_root / "04_PROCESSED_AUDIO" / "fallback_processed.wav"
            log_path = project_root / "04_PROCESSED_AUDIO" / "processing_log.md"
            analysis_path = project_root / "01_ANALYSIS" / "analysis.json"
            write_wav(input_path, seconds=3.0)
            analysis_path.write_text(json.dumps(analysis_fixture()), encoding="utf-8")

            result = run_fallback_processing(
                input_path=input_path,
                output_path=output_path,
                analysis_path=analysis_path,
                log_path=log_path,
                options={"length_mode": "keep_original", "export_format": "wav24_48k"},
            )
            verification = verify_wav(output_path)
            log_text = log_path.read_text(encoding="utf-8")

            self.assertTrue(output_path.exists())
            self.assertGreater(output_path.stat().st_size, 0)
            self.assertLess(verification["peak_dbfs"], -0.1)
            self.assertIn("does not claim full human arrangement", log_text)
            self.assertIn("Cannot truly rewrite arrangement", log_text)
            self.assertIn("Vocal-like texture suppression is heuristic", log_text)
            self.assertIn("verification", result)

    def test_missing_input_is_clean_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_root = Path(tmp) / "AI_BEAT_LOGIC_WORKFLOW"
            ensure_folder_structure(project_root)
            with self.assertRaises(FileNotFoundError):
                run_fallback_processing(
                    input_path=project_root / "04_PROCESSED_AUDIO" / "working_input.wav",
                    output_path=project_root / "04_PROCESSED_AUDIO" / "fallback_processed.wav",
                    analysis_path=project_root / "01_ANALYSIS" / "analysis.json",
                    log_path=project_root / "04_PROCESSED_AUDIO" / "processing_log.md",
                )


if __name__ == "__main__":
    unittest.main()

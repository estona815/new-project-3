from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
import wave
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_DIR))

from ingest_convert import (  # noqa: E402
    backup_existing_working_wav,
    find_conversion_tool,
    ingest_and_convert,
    sample_rate_for_export_format,
    sanitize_filename,
    unique_path,
)
from paths import ensure_folder_structure  # noqa: E402


def write_dummy_wav(path: Path) -> None:
    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(44100)
        wav_file.writeframes(b"\x00\x00" * 4410)


class IngestConvertTests(unittest.TestCase):
    def test_sanitize_filename_lowercases_and_removes_unsafe_characters(self) -> None:
        self.assertEqual(sanitize_filename("My Suno Beat !!!.MP3"), "my_suno_beat.mp3")
        self.assertEqual(sanitize_filename("???.WAV"), "input.wav")

    def test_unique_path_uses_three_digit_suffixes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            (directory / "beat.wav").write_bytes(b"one")
            (directory / "beat_001.wav").write_bytes(b"two")
            self.assertEqual(unique_path(directory, "beat.wav").name, "beat_002.wav")

    def test_sample_rate_follows_export_format(self) -> None:
        self.assertEqual(sample_rate_for_export_format("wav24_44k"), 44100)
        self.assertEqual(sample_rate_for_export_format("wav24_48k"), 48000)

    def test_existing_working_wav_is_backed_up(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            working = Path(tmp) / "working_input.wav"
            working.write_bytes(b"old")
            backup = backup_existing_working_wav(working)
            self.assertIsNotNone(backup)
            self.assertFalse(working.exists())
            self.assertTrue(backup.exists())

    def test_wav_input_is_copied_converted_and_metadata_is_written(self) -> None:
        if not find_conversion_tool():
            self.skipTest("No ffmpeg or afconvert available for conversion test.")

        with tempfile.TemporaryDirectory() as tmp:
            project_root = Path(tmp) / "AI_BEAT_LOGIC_WORKFLOW"
            ensure_folder_structure(project_root)
            source = Path(tmp) / "Source Beat.wav"
            write_dummy_wav(source)

            result = ingest_and_convert(str(source), "wav24_48k", project_root)
            metadata_path = project_root / "01_ANALYSIS" / "input_metadata.json"
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))

            self.assertTrue(Path(result.copied_path).exists())
            self.assertTrue(Path(result.working_wav_path).exists())
            self.assertGreater(Path(result.working_wav_path).stat().st_size, 0)
            self.assertEqual(Path(result.copied_path).name, "source_beat.wav")
            self.assertEqual(metadata["source_extension"], ".wav")
            self.assertIn(metadata["conversion_tool_used"], {"ffmpeg", "afconvert"})
            self.assertTrue(metadata["conversion_command"])
            self.assertGreater(metadata["file_size"], 0)


if __name__ == "__main__":
    unittest.main()

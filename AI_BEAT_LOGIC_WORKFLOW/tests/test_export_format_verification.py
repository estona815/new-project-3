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

from final_verify import verify_final_wav  # noqa: E402


def write_pcm_wav(path: Path, *, sample_rate: int, bits: int, seconds: float = 0.25) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frames = int(sample_rate * seconds)
    sample_width = bits // 8
    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(2)
        wav_file.setsampwidth(sample_width)
        wav_file.setframerate(sample_rate)
        for index in range(frames):
            value = math.sin(2.0 * math.pi * 440.0 * index / sample_rate) * 0.2
            if bits == 24:
                integer = int(value * 8388607)
                raw = integer.to_bytes(3, "little", signed=True)
            else:
                integer = int(value * 32767)
                raw = integer.to_bytes(2, "little", signed=True)
            wav_file.writeframesraw(raw + raw)


class ExportFormatVerificationTests(unittest.TestCase):
    def test_valid_24bit_48k_wav(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "final.wav"
            write_pcm_wav(path, sample_rate=48000, bits=24)

            result = verify_final_wav(path, "wav24_48k")

            self.assertTrue(result["ok"], result["errors"])
            self.assertEqual(result["sample_rate"], 48000)
            self.assertEqual(result["bit_depth"], 24)
            self.assertTrue(result["bit_depth_verified"])
            self.assertTrue(result["format_verified"])

    def test_valid_24bit_441k_wav(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "final.wav"
            write_pcm_wav(path, sample_rate=44100, bits=24)

            result = verify_final_wav(path, "wav24_44k")

            self.assertTrue(result["ok"], result["errors"])
            self.assertEqual(result["sample_rate"], 44100)
            self.assertEqual(result["expected_sample_rate"], 44100)
            self.assertTrue(result["format_verified"])

    def test_wrong_sample_rate_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "final.wav"
            write_pcm_wav(path, sample_rate=44100, bits=24)

            result = verify_final_wav(path, "wav24_48k")

            self.assertFalse(result["ok"])
            self.assertFalse(result["format_verified"])
            self.assertIn("sample rate mismatch", " ".join(result["errors"]))

    def test_16bit_wav_with_24bit_filename_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "final_suno_logic_processed_24bit_48k.wav"
            write_pcm_wav(path, sample_rate=48000, bits=16)

            result = verify_final_wav(path, "wav24_48k")

            self.assertFalse(result["ok"])
            self.assertFalse(result["bit_depth_verified"])
            self.assertFalse(result["format_verified"])
            self.assertIn("24-bit PCM", " ".join(result["errors"]))

    def test_missing_file_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "missing.wav"

            result = verify_final_wav(path, "wav24_48k")

            self.assertFalse(result["ok"])
            self.assertFalse(result["exists"])
            self.assertIn("final WAV missing", " ".join(result["errors"]))

    def test_corrupt_file_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "corrupt.wav"
            path.write_text("not a wav", encoding="utf-8")

            result = verify_final_wav(path, "wav24_48k")

            self.assertFalse(result["ok"])
            self.assertTrue(result["exists"])
            self.assertIn("Python WAV analysis failed", " ".join(result["errors"]))


if __name__ == "__main__":
    unittest.main()

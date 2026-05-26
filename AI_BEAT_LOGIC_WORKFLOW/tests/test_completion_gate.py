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

from completion_gate import CompletionStatus, check_completion_status  # noqa: E402
from final_verify import verify_final_export  # noqa: E402


def write_pcm_wav(path: Path, *, sample_rate: int = 48000, bits: int = 24, seconds: float = 0.25) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frames = int(sample_rate * seconds)
    sample_width = bits // 8
    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(2)
        wav_file.setsampwidth(sample_width)
        wav_file.setframerate(sample_rate)
        for index in range(frames):
            sample = math.sin(2.0 * math.pi * 440.0 * index / sample_rate) * 0.2
            if bits == 24:
                integer = int(sample * 8388607)
                raw = integer.to_bytes(3, "little", signed=True)
            else:
                integer = int(sample * 32767)
                raw = integer.to_bytes(2, "little", signed=True)
            wav_file.writeframesraw(raw + raw)


def write_report(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("# QC Report\n\n- status: verified\n", encoding="utf-8")


class CompletionGateTests(unittest.TestCase):
    def test_missing_final_wav_blocks_completion(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            report = root / "qc_report.md"
            write_report(report)

            status = check_completion_status(
                final_wav_path=root / "missing.wav",
                qc_report_path=report,
                requested_format="wav24_48k",
            )

            self.assertIsInstance(status, CompletionStatus)
            self.assertFalse(status.complete)
            self.assertIn("final WAV missing", " ".join(status.blocking_reasons))

    def test_empty_final_wav_blocks_completion(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            final = root / "final.wav"
            report = root / "qc_report.md"
            final.touch()
            write_report(report)

            status = check_completion_status(final_wav_path=final, qc_report_path=report, requested_format="wav24_48k")

            self.assertFalse(status.complete)
            self.assertIn("final WAV is empty", " ".join(status.blocking_reasons))

    def test_missing_qc_report_blocks_completion(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            final = root / "final.wav"
            write_pcm_wav(final)

            status = check_completion_status(final_wav_path=final, qc_report_path=root / "missing.md", requested_format="wav24_48k")

            self.assertFalse(status.complete)
            self.assertIn("QC report missing", " ".join(status.blocking_reasons))

    def test_wrong_sample_rate_blocks_completion(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            final = root / "final.wav"
            report = root / "qc_report.md"
            write_pcm_wav(final, sample_rate=44100)
            write_report(report)

            status = check_completion_status(final_wav_path=final, qc_report_path=report, requested_format="wav24_48k")

            self.assertFalse(status.complete)
            self.assertIn("sample rate mismatch", " ".join(status.blocking_reasons))

    def test_16_bit_wav_pretending_to_be_24_bit_blocks_completion(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            final = root / "final_suno_logic_processed_24bit_48k.wav"
            report = root / "qc_report.md"
            write_pcm_wav(final, bits=16)
            write_report(report)

            status = check_completion_status(final_wav_path=final, qc_report_path=report, requested_format="wav24_48k")

            self.assertFalse(status.complete)
            self.assertIn("24-bit PCM", " ".join(status.blocking_reasons))

    def test_valid_final_wav_and_qc_report_allows_completion(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            final = root / "final.wav"
            report = root / "qc_report.md"
            write_pcm_wav(final)
            write_report(report)
            verification = verify_final_export(final, "wav24_48k")

            status = check_completion_status(
                final_wav_path=final,
                qc_report_path=report,
                requested_format="wav24_48k",
                final_verify_result=verification,
            )

            self.assertTrue(status.complete)
            self.assertTrue(status.verified_final_wav)
            self.assertTrue(status.verified_qc_report)
            self.assertTrue(status.verified_format)
            self.assertTrue(status.verified_audio_metrics)

    def test_required_master_qc_report_blocks_when_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            final = root / "final.wav"
            report = root / "qc_report.md"
            write_pcm_wav(final)
            write_report(report)

            status = check_completion_status(
                final_wav_path=final,
                qc_report_path=report,
                requested_format="wav24_48k",
                require_master_qc=True,
                master_qc_report_path=root / "missing_master_qc.md",
            )

            self.assertFalse(status.complete)
            self.assertIn("master QC report missing", " ".join(status.blocking_reasons))


if __name__ == "__main__":
    unittest.main()

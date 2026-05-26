from __future__ import annotations

import math
import sys
import tempfile
import unittest
import wave
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from completion_gate import check_completion_status  # noqa: E402
from export_audio import write_float_wav  # noqa: E402


def write_final(path: Path, sample_rate: int = 48000, bit_depth: int = 24) -> None:
    frames = sample_rate // 5
    left = [0.1 * math.sin(2 * math.pi * 220 * i / sample_rate) for i in range(frames)]
    right = [0.1 * math.sin(2 * math.pi * 330 * i / sample_rate) for i in range(frames)]
    write_float_wav(path, [left, right], sample_rate, bit_depth=bit_depth)


class NoFalseCompleteAutopilotIntegrationTests(unittest.TestCase):
    def test_wrong_bit_depth_blocks_complete(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            final = Path(tmp) / "final.wav"
            qc = Path(tmp) / "qc_report.md"
            qc.write_text("# QC", encoding="utf-8")
            write_final(final, 48000, 16)

            status = check_completion_status(final_wav_path=final, qc_report_path=qc, requested_format="wav24_48k")

            self.assertFalse(status.complete)
            self.assertTrue(any("24-bit PCM" in reason or "requested format" in reason for reason in status.blocking_reasons))

    def test_missing_qc_report_blocks_complete(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            final = Path(tmp) / "final.wav"
            write_final(final)

            status = check_completion_status(final_wav_path=final, qc_report_path=Path(tmp) / "missing.md", requested_format="wav24_48k")

            self.assertFalse(status.complete)
            self.assertTrue(any("QC report missing" in reason for reason in status.blocking_reasons))

    def test_missing_master_qc_blocks_complete_when_required(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            final = Path(tmp) / "final.wav"
            qc = Path(tmp) / "qc_report.md"
            qc.write_text("# QC", encoding="utf-8")
            write_final(final)

            status = check_completion_status(
                final_wav_path=final,
                qc_report_path=qc,
                requested_format="wav24_48k",
                require_master_qc=True,
                master_qc_report_path=Path(tmp) / "missing_master.md",
            )

            self.assertFalse(status.complete)
            self.assertTrue(any("master QC report missing" in reason for reason in status.blocking_reasons))


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import math
import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from export_audio import write_float_wav  # noqa: E402
from render_orchestrator import verify_final_render  # noqa: E402


def write_test_wav(path: Path, sample_rate: int, bit_depth: int) -> None:
    frames = sample_rate // 4
    left = [0.08 * math.sin(2.0 * math.pi * 330.0 * index / sample_rate) for index in range(frames)]
    right = [0.08 * math.sin(2.0 * math.pi * 220.0 * index / sample_rate) for index in range(frames)]
    write_float_wav(path, [left, right], sample_rate, bit_depth=bit_depth)


class FinalWavCompleteOnlyAfterVerifyTests(unittest.TestCase):
    def test_verified_final_wav_with_qc_allows_complete(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            final = root / "05_FINAL_WAV" / "final.wav"
            qc = root / "06_QC_REPORT" / "qc_report.md"
            qc.parent.mkdir(parents=True)
            qc.write_text("# QC\npassed\n", encoding="utf-8")
            write_test_wav(final, 48000, 24)

            result = verify_final_render(project_root=root, final_wav_path=final, requested_format="wav24_48k", qc_report_path=qc)

            self.assertEqual(result["status"], "COMPLETE")
            self.assertTrue(result["completion_gate"].complete)
            self.assertTrue(result["manifest"]["completion_gate"]["complete"])
            self.assertTrue(result["manifest"]["final_wav"]["verified"])

    def test_wrong_format_blocks_complete(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            final = root / "05_FINAL_WAV" / "wrong.wav"
            qc = root / "06_QC_REPORT" / "qc_report.md"
            qc.parent.mkdir(parents=True)
            qc.write_text("# QC\n", encoding="utf-8")
            write_test_wav(final, 44100, 16)

            result = verify_final_render(project_root=root, final_wav_path=final, requested_format="wav24_48k", qc_report_path=qc)

            self.assertEqual(result["status"], "FINAL_WAV_EXPORTED_UNVERIFIED")
            self.assertFalse(result["completion_gate"].complete)
            self.assertTrue(any("sample rate mismatch" in reason for reason in result["completion_gate"].blocking_reasons))
            self.assertTrue(any("24-bit PCM" in reason for reason in result["completion_gate"].blocking_reasons))


if __name__ == "__main__":
    unittest.main()

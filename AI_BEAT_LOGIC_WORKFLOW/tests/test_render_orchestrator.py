from __future__ import annotations

import math
import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from export_audio import write_float_wav  # noqa: E402
from render_orchestrator import classify_project_state, verify_final_render  # noqa: E402


def write_test_wav(path: Path, sample_rate: int = 48000, bit_depth: int = 24) -> None:
    frames = sample_rate // 4
    samples = [[0.1 * math.sin(2.0 * math.pi * 220.0 * index / sample_rate) for index in range(frames)] for _ in range(2)]
    write_float_wav(path, samples, sample_rate, bit_depth=bit_depth)


class RenderOrchestratorTests(unittest.TestCase):
    def test_classify_project_state_prefers_logic_manual_over_midi(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "02_EDIT_PLAN").mkdir(parents=True)
            (root / "02_EDIT_PLAN" / "midi_region_guide.json").write_text("{}", encoding="utf-8")
            self.assertEqual(classify_project_state(root), "MIDI_GUIDE_READY")
            (root / "02_EDIT_PLAN" / "logic_arrangement_plan.md").write_text("# plan", encoding="utf-8")
            self.assertEqual(classify_project_state(root), "LOGIC_MANUAL_REQUIRED")

    def test_unverified_final_wav_without_qc_is_not_complete(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            final = root / "05_FINAL_WAV" / "final.wav"
            write_test_wav(final)

            result = verify_final_render(project_root=root, final_wav_path=final, requested_format="wav24_48k", qc_report_path=root / "missing.md")

            self.assertEqual(result["status"], "FINAL_WAV_EXPORTED_VERIFIED")
            self.assertFalse(result["completion_gate"].complete)
            self.assertFalse(result["manifest"]["completion_gate"]["complete"])
            self.assertTrue((root / "06_QC_REPORT" / "audio_render_manifest.json").exists())


if __name__ == "__main__":
    unittest.main()

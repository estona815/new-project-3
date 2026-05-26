from __future__ import annotations

import json
import math
import sys
import tempfile
import unittest
import wave
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from arrangement_autopilot import run_arrangement_autopilot  # noqa: E402
from sample_analysis import write_sample_analysis  # noqa: E402
from vocal_to_code import write_vocal_to_code  # noqa: E402


def write_wav(path: Path, seconds: float, freq: float, sample_rate: int = 48000, transient: bool = False) -> None:
    frames = int(seconds * sample_rate)
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(2)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        for index in range(frames):
            time = index / sample_rate
            pulse = 0.45 * math.exp(-(time % 0.5) * 60.0) if transient and (time % 0.5) < 0.08 else 0.0
            value = max(-0.8, min(0.8, pulse + 0.2 * math.sin(2 * math.pi * freq * time)))
            raw = int(value * 32767).to_bytes(2, "little", signed=True)
            wav_file.writeframesraw(raw + raw)


class SampleVocalToArrangementIntegrationTests(unittest.TestCase):
    def test_sample_to_arrangement_outputs_guides_without_complete(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sample = root / "input" / "sample_loop.wav"
            write_wav(sample, 8.0, 220.0, transient=True)

            write_sample_analysis(sample, project_root=root, ownership_status="unknown")
            result = run_arrangement_autopilot(
                project_root=root,
                genre="system_seoul_adjacent",
                length_mode="reels_15sec",
                request_text="이 샘플로 SYSTEM SEOUL/ycs 결 디지코어 비트 짜줘. 808 강하게, 신디 넓게, 릴스 첫 15초 훅.",
            )

            expected = [
                root / "01_ANALYSIS" / "sample_analysis.json",
                root / "02_EDIT_PLAN" / "arrangement_plan.json",
                root / "02_EDIT_PLAN" / "section_progression_guide.json",
                root / "02_EDIT_PLAN" / "drum_programming_guide.json",
                root / "02_EDIT_PLAN" / "bass_808_midi_guide.json",
                root / "02_EDIT_PLAN" / "logic_arrangement_plan.md",
            ]
            for path in expected:
                self.assertTrue(path.exists(), path)
            plan = json.loads((root / "02_EDIT_PLAN" / "arrangement_plan.json").read_text(encoding="utf-8"))
            self.assertEqual(plan["status"], "ARRANGEMENT_PLAN_READY")
            self.assertFalse(plan["complete"])
            self.assertNotIn("COMPLETE", (root / "02_EDIT_PLAN" / "logic_arrangement_plan.md").read_text(encoding="utf-8"))
            self.assertEqual(result["plan"]["length_mode"], "reels_15sec")

    def test_vocal_to_code_false_claim_guards_for_tuning_and_decapitator_request(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            vocal = root / "input" / "vocal.wav"
            write_wav(vocal, 3.0, 246.94)

            paths = write_vocal_to_code(vocal, project_root=root, mode="separate_vocal", requested_pitch_mode="hard_effect")
            payload = json.loads(paths["json"].read_text(encoding="utf-8"))

            self.assertTrue(paths["pitch_guide"].exists())
            self.assertIn("false_claim_guard", payload)
            self.assertFalse(payload["false_claim_guard"]["auto_tune_applied"])
            self.assertFalse(payload["false_claim_guard"]["pitch_correction_performed"])
            self.assertIn("recommended, not applied", payload["pitch_correction_guide"]["claim_language"])


if __name__ == "__main__":
    unittest.main()

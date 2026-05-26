from __future__ import annotations

import math
import sys
import tempfile
import unittest
import wave
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from final_verify import verify_final_wav  # noqa: E402
from rescue_renderer import run_bad_ai_song_rescue_render  # noqa: E402


def write_bad_ai_song(path: Path, sample_rate: int = 48_000, seconds: float = 28.0) -> Path:
    frames = int(sample_rate * seconds)
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(2)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        for index in range(frames):
            time = index / sample_rate
            static_tone = 0.40 * math.sin(2.0 * math.pi * 220.0 * time)
            fake_vocal = 0.07 * math.sin(2.0 * math.pi * 1_050.0 * time) * (0.55 + 0.45 * math.sin(2.0 * math.pi * 7.0 * time))
            pulse = 0.10 if index % int(0.25 * sample_rate) < 120 else 0.0
            value = max(-0.95, min(0.95, static_tone + fake_vocal + pulse))
            raw = int(value * 32767).to_bytes(2, "little", signed=True)
            wav_file.writeframesraw(raw + raw)
    return path


class BadAiSongRescueIntegrationTests(unittest.TestCase):
    def test_bad_ai_song_produces_rescue_demo_and_plan_not_complete(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "workflow"
            source = write_bad_ai_song(Path(temp_dir) / "bad_ai.wav")

            result = run_bad_ai_song_rescue_render(
                source,
                project_root=root,
                final_mode=False,
                render_audio=True,
                render_generated_lead=True,
                render_sample_motif=False,
                length_mode="short_30sec",
            )
            report = Path(result["paths"]["rescue_qc_report"]).read_text(encoding="utf-8")

            self.assertEqual(result["status"], "DEMO_RENDERED_NOT_COMPLETE")
            self.assertFalse(result["complete"])
            self.assertTrue(Path(result["paths"]["rescue_demo"]).exists())
            self.assertTrue(Path(result["paths"]["bad_song_diagnosis_json"]).exists())
            self.assertTrue(Path(result["paths"]["rescue_arrangement_plan_json"]).exists())
            self.assertTrue(Path(result["paths"]["sample_motif_rebuild_plan"]).exists())
            self.assertTrue(Path(result["paths"]["logic_rescue_plan"]).exists())
            self.assertTrue(result["diagnosis"]["rescue_decision"]["mix_only_not_enough"])
            self.assertTrue(result["mix"]["bus_reports"]["generated_lead_bus"]["new_lead_hook_rendered"])
            self.assertIn("Mix/master alone is insufficient", report)
            self.assertIn("generated lead bus: true", report)
            self.assertIn("vocal removal claimed: false", report)
            self.assertFalse(result["claim_guard"]["stem_level_remix_claimed"])
            self.assertFalse(result["claim_guard"]["vocal_removal_claimed"])

    def test_final_mode_writes_verified_final_wav_and_qc(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "workflow"
            source = write_bad_ai_song(Path(temp_dir) / "bad_ai.wav")

            result = run_bad_ai_song_rescue_render(
                source,
                project_root=root,
                final_mode=True,
                render_audio=True,
                render_generated_lead=True,
                render_sample_motif=False,
                length_mode="short_30sec",
            )
            final_path = Path(result["paths"]["final_wav"])
            qc_path = Path(result["paths"]["rescue_qc_report"])
            logic_path = Path(result["paths"]["logic_rescue_plan"])
            verification = verify_final_wav(final_path, "wav24_48k")
            report = qc_path.read_text(encoding="utf-8")

            self.assertTrue(final_path.exists())
            self.assertTrue(qc_path.exists())
            self.assertTrue(logic_path.exists())
            self.assertTrue(verification["ok"])
            self.assertEqual(verification["sample_rate"], 48_000)
            self.assertEqual(verification["bit_depth"], 24)
            self.assertEqual(verification["clipping_count"], 0)
            self.assertEqual(result["status"], "COMPLETE")
            self.assertTrue(result["complete"])
            self.assertTrue(result["completion_gate"].complete)
            self.assertIn("Final Verification", report)
            self.assertIn("complete: true", report)


if __name__ == "__main__":
    unittest.main()

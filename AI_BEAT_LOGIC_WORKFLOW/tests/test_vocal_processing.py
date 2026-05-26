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
from paths import ensure_folder_structure  # noqa: E402
from vocal_mix_master import run_vocal_mix_master_extension  # noqa: E402


def write_test_wav(path: Path, sample_rate: int = 48000, seconds: float = 1.2, channels: int = 1, frequency: float = 220.0) -> None:
    frames = max(1, int(sample_rate * seconds))
    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(channels)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        for index in range(frames):
            time = index / sample_rate
            body = math.sin(2.0 * math.pi * frequency * time) * 0.35
            sibilance = math.sin(2.0 * math.pi * 7500.0 * time) * (0.06 if 0.35 < time < 0.48 else 0.0)
            rumble = math.sin(2.0 * math.pi * 70.0 * time) * (0.08 if time < 0.3 else 0.02)
            value = max(-0.92, min(0.92, body + sibilance + rumble))
            raw = int(value * 32767).to_bytes(2, "little", signed=True)
            wav_file.writeframesraw(raw * channels)


class VocalProcessingTests(unittest.TestCase):
    def test_separate_vocal_file_creates_processed_lead(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_root = Path(tmp) / "AI_BEAT_LOGIC_WORKFLOW"
            ensure_folder_structure(project_root)
            vocal = Path(tmp) / "lead.wav"
            write_test_wav(vocal)
            options = {
                "mode": "vocal_plus_beat",
                "vocal_file": str(vocal),
                "vocal_style": "polished",
                "deess": "medium",
                "mix_intensity": "standard",
                "master_loudness": "master_ready_headroom",
                "autotune": "none",
                "reverb_space": "plate",
                "delay_style": "throw_only",
            }

            paths = run_vocal_mix_master_extension(options, project_root)
            processed = project_root / "07_VOCAL_PROCESSING" / "processed_lead_vocal.wav"
            log = paths["vocal_processing_log"].read_text(encoding="utf-8")
            verification = verify_wav(processed)

            self.assertTrue(processed.exists())
            self.assertGreater(verification["duration_seconds"], 1.0)
            self.assertLessEqual(verification["peak_dbfs"], -3.0)
            self.assertIn("lead_vocal: rendered", log)
            self.assertIn("manual Logic", log)

    def test_vocal_plus_beat_creates_pre_master(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_root = Path(tmp) / "AI_BEAT_LOGIC_WORKFLOW"
            ensure_folder_structure(project_root)
            vocal = Path(tmp) / "lead.wav"
            beat = Path(tmp) / "beat.wav"
            write_test_wav(vocal, channels=1, frequency=240.0)
            write_test_wav(beat, channels=2, frequency=110.0)
            options = {
                "mode": "vocal_plus_beat",
                "vocal_file": str(vocal),
                "beat_file": str(beat),
                "vocal_style": "rap_forward",
                "deess": "strong",
                "mix_intensity": "standard",
                "master_loudness": "master_ready_headroom",
                "autotune": "none",
                "reverb_space": "dry",
                "delay_style": "throw_only",
            }

            paths = run_vocal_mix_master_extension(options, project_root)
            pre_master = project_root / "09_MIX_MASTER" / "pre_master.wav"
            verification = verify_wav(pre_master)
            plan = paths["mix_session_plan"].read_text(encoding="utf-8")

            self.assertTrue(pre_master.exists())
            self.assertEqual(verification["sample_rate"], 48000)
            self.assertEqual(verification["channels"], 2)
            self.assertLessEqual(verification["peak_dbfs"], -2.9)
            self.assertIn("pre_master.wav: rendered", plan)

    def test_full_stereo_mode_does_not_create_fake_isolated_vocals(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_root = Path(tmp) / "AI_BEAT_LOGIC_WORKFLOW"
            ensure_folder_structure(project_root)
            song = Path(tmp) / "song.wav"
            write_test_wav(song, channels=2)
            options = {
                "mode": "full_song_stereo",
                "input_path": str(song),
                "vocal_style": "polished",
                "deess": "medium",
                "mix_intensity": "standard",
                "master_loudness": "master_ready_headroom",
                "autotune": "none",
                "reverb_space": "plate",
                "delay_style": "throw_only",
            }

            paths = run_vocal_mix_master_extension(options, project_root)
            analysis = json.loads(paths["vocal_analysis"].read_text(encoding="utf-8"))
            log = paths["vocal_processing_log"].read_text(encoding="utf-8")

            self.assertFalse((project_root / "07_VOCAL_PROCESSING" / "processed_lead_vocal.wav").exists())
            self.assertFalse((project_root / "09_MIX_MASTER" / "pre_master.wav").exists())
            self.assertEqual(analysis["full_stereo_song"]["analysis_scope"], "heuristic_full_stereo_song")
            self.assertIn("does not create processed isolated vocal files", log)
            self.assertIn("not isolated vocal measurements", log)


if __name__ == "__main__":
    unittest.main()

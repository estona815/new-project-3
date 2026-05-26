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

from mix_master_autopilot import build_mix_master_plan, write_mix_master_plan  # noqa: E402
from song_arrangement_analyzer import write_song_structure_analysis  # noqa: E402


def write_song(path: Path, seconds: float = 16.0, sample_rate: int = 48000) -> None:
    frames = int(seconds * sample_rate)
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(2)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        for index in range(frames):
            time = index / sample_rate
            section_gain = 0.15 if time < 4 else 0.55 if time < 12 else 0.25
            beat = 0.35 * math.exp(-(time % 0.5) * 50.0) if (time % 0.5) < 0.08 else 0.0
            tone = section_gain * math.sin(2 * math.pi * 180 * time)
            value = max(-0.85, min(0.85, tone + beat))
            raw = int(value * 32767).to_bytes(2, "little", signed=True)
            wav_file.writeframesraw(raw + raw)


class SongToMixMasterIntegrationTests(unittest.TestCase):
    def test_song_to_mix_master_plan_without_render_does_not_complete(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            song = root / "input" / "stereo_song.wav"
            write_song(song)

            write_song_structure_analysis(song, project_root=root, mode="full_song_stereo")
            plan = build_mix_master_plan(
                input_mode="full_song_stereo",
                style_target="commercial_digicore_hyperpop",
                master_target_mode="master_ready_headroom",
            )
            paths = write_mix_master_plan(root, plan)

            self.assertTrue((root / "01_ANALYSIS" / "song_structure_analysis.json").exists())
            self.assertTrue(paths["json"].exists())
            parsed = json.loads(paths["json"].read_text(encoding="utf-8"))
            self.assertIn("stereo trim/fade", parsed["fallback_possible"])
            self.assertFalse(parsed["false_claim_guards"]["completion_claimed"])
            self.assertFalse((root / "05_FINAL_WAV").exists())


if __name__ == "__main__":
    unittest.main()

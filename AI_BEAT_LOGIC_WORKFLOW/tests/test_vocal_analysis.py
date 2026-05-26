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

from paths import ensure_folder_structure  # noqa: E402
from vocal_analysis import analyze_vocal_inputs  # noqa: E402
from vocal_mix_master import run_vocal_mix_master_extension  # noqa: E402


def write_vocalish_wav(path: Path, sample_rate: int = 48000, seconds: float = 2.0, channels: int = 1) -> None:
    frames = max(1, int(sample_rate * seconds))
    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(channels)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        for index in range(frames):
            time = index / sample_rate
            envelope = 0.05 if time < 0.25 else 0.45
            tone = math.sin(2.0 * math.pi * 220.0 * time) * envelope
            brightness = math.sin(2.0 * math.pi * 7200.0 * time) * (0.08 if 0.8 < time < 1.0 else 0.01)
            plosive = 0.65 * math.sin(2.0 * math.pi * 80.0 * time) if 0.45 < time < 0.52 else 0.0
            value = max(-0.95, min(0.95, tone + brightness + plosive))
            raw = int(value * 32767).to_bytes(2, "little", signed=True)
            wav_file.writeframesraw(raw * channels)


class VocalAnalysisTests(unittest.TestCase):
    def test_separate_vocal_analysis_uses_direct_metrics(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            vocal = Path(tmp) / "lead.wav"
            beat = Path(tmp) / "beat.wav"
            write_vocalish_wav(vocal)
            write_vocalish_wav(beat, channels=2)
            options = {"mode": "vocal_plus_beat", "vocal_file": str(vocal), "beat_file": str(beat)}

            analysis = analyze_vocal_inputs(options)
            lead = analysis["files"]["lead_vocal"]
            metrics = lead["metrics"]

            self.assertEqual(lead["analysis_scope"], "direct_separate_vocal_file")
            self.assertGreater(metrics["duration_seconds"], 1.9)
            self.assertEqual(metrics["sample_rate"], 48000)
            self.assertEqual(metrics["channels"], 1)
            self.assertIn("noise_floor_estimate", metrics)
            self.assertIn("dynamic_range", metrics)
            self.assertIn("vocal_density", metrics)
            self.assertIn("phrase_level_loudness_variation", metrics)
            self.assertIn("pitch_instability_note", metrics)
            self.assertIsInstance(lead["plosive_candidates"], list)
            self.assertIsInstance(lead["sibilance_candidates"], list)
            self.assertIsInstance(lead["harshness_candidates"], list)
            self.assertIsInstance(lead["low_rumble"], list)
            self.assertIsInstance(lead["breath_noise_heavy_sections"], list)

    def test_full_stereo_analysis_uses_heuristic_language_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            song = Path(tmp) / "song.wav"
            write_vocalish_wav(song, channels=2)
            options = {"mode": "full_song_stereo", "input_path": str(song)}

            analysis = analyze_vocal_inputs(options)
            full_song = analysis["full_stereo_song"]
            as_text = json.dumps(full_song).lower()

            self.assertEqual(full_song["analysis_scope"], "heuristic_full_stereo_song")
            self.assertIn("likely_vocal_forward_sections", full_song)
            self.assertIn("likely_vocal_masked_sections", full_song)
            self.assertIn("sibilance_like_high_frequency_candidates", full_song)
            self.assertIn("heuristic", as_text)
            self.assertIn("not isolated", as_text)
            self.assertNotIn("isolated vocal analysis passed", as_text)
            self.assertNotIn("real vocal removal", as_text.replace("no real vocal removal", ""))

    def test_vocal_chain_plan_is_logic_ready_and_honest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_root = Path(tmp) / "AI_BEAT_LOGIC_WORKFLOW"
            ensure_folder_structure(project_root)
            vocal = Path(tmp) / "lead.wav"
            beat = Path(tmp) / "beat.wav"
            write_vocalish_wav(vocal)
            write_vocalish_wav(beat, channels=2)
            options = {
                "mode": "vocal_plus_beat",
                "vocal_file": str(vocal),
                "beat_file": str(beat),
                "vocal_style": "rap_forward",
                "mix_intensity": "bold",
                "master_loudness": "loud_demo",
                "autotune": "medium",
                "deess": "strong",
                "reverb_space": "dry",
                "delay_style": "throw_only",
            }

            paths = run_vocal_mix_master_extension(options, project_root)
            plan = paths["vocal_chain_plan"].read_text(encoding="utf-8")
            parsed = json.loads(paths["vocal_analysis"].read_text(encoding="utf-8"))

            self.assertEqual(parsed["files"]["lead_vocal"]["analysis_scope"], "direct_separate_vocal_file")
            for heading in (
                "## 1. Input Mode",
                "## 2. What Can Actually Be Processed",
                "## 3. Vocal Cleanup Plan",
                "## 4. EQ Plan",
                "## 5. Compression Plan",
                "## 6. De-Essing Plan",
                "## 7. Saturation Plan",
                "## 8. Reverb/Delay Plan",
                "## 9. Autotune/Pitch Plan",
                "## 10. Manual Logic Pro Checklist",
                "## 11. Limitations",
            ):
                self.assertIn(heading, plan)
            self.assertIn("High-pass the lead vocal", plan)
            self.assertIn("delay throws", plan)
            self.assertIn("less reverb", plan)
            self.assertIn("No real vocal removal from stereo is claimed", plan)


if __name__ == "__main__":
    unittest.main()

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

from vocal_to_code import analyze_vocal_to_code, write_vocal_to_code  # noqa: E402


def write_vocal(path: Path, sample_rate: int = 48000, seconds: float = 2.8, channels: int = 1, noisy: bool = False) -> None:
    frames = int(sample_rate * seconds)
    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(channels)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        for index in range(frames):
            time = index / sample_rate
            active = 0.25 < time < 1.2 or 1.55 < time < 2.35
            value = 0.0
            if active:
                freq = 220.0 if time < 1.2 else 246.94
                value = 0.34 * math.sin(2.0 * math.pi * freq * time)
            if noisy:
                value += 0.03 * math.sin(2.0 * math.pi * 7300.0 * time)
            raw = int(max(-0.9, min(0.9, value)) * 32767).to_bytes(2, "little", signed=True)
            wav_file.writeframesraw(raw * channels)


class VocalToCodeSchemaTests(unittest.TestCase):
    def test_separate_vocal_schema_contains_required_guard_and_phrase_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            vocal = Path(tmp) / "lead.wav"
            write_vocal(vocal)

            result = analyze_vocal_to_code(vocal, mode="separate_vocal", requested_pitch_mode="medium")
            phrase = result["phrases"][0]

            self.assertEqual(result["schema_version"], "vocal_to_code.v1")
            self.assertTrue(result["input"]["analysis_isolated"])
            self.assertEqual(result["input"]["mode"], "separate_vocal")
            self.assertIn("estimated_bpm", result["global"])
            self.assertIn("estimated_key", result["global"])
            self.assertIn("estimated_notes", phrase)
            self.assertIn("note_sequence_compact", phrase)
            self.assertIn("rhythm_grid", phrase)
            self.assertIn("pitch_contour", phrase)
            self.assertIn("mix_notes", phrase)
            self.assertEqual(result["pitch_correction_guide"]["claim_language"], "recommended, not applied")
            self.assertFalse(result["false_claim_guard"]["auto_tune_applied"])
            self.assertFalse(result["false_claim_guard"]["note_transcription_is_exact"])

    def test_write_outputs_json_summary_and_pitch_guide(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "workflow"
            vocal = Path(tmp) / "lead.wav"
            write_vocal(vocal)

            paths = write_vocal_to_code(vocal, project_root=root, mode="vocal_plus_beat")
            parsed = json.loads(paths["json"].read_text(encoding="utf-8"))
            summary = paths["summary"].read_text(encoding="utf-8")
            guide = json.loads(paths["pitch_guide"].read_text(encoding="utf-8"))

            self.assertTrue(paths["json"].exists())
            self.assertTrue(paths["summary"].exists())
            self.assertTrue(paths["pitch_guide"].exists())
            self.assertEqual(parsed["input"]["mode"], "vocal_plus_beat")
            self.assertIn("Vocal To Code Summary", summary)
            self.assertEqual(guide["claim_language"], "recommended, not applied")
            self.assertFalse((root / "05_FINAL_WAV").exists())

    def test_full_stereo_mode_is_not_isolated(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            song = Path(tmp) / "song.wav"
            write_vocal(song, channels=2, noisy=True)

            result = analyze_vocal_to_code(song, mode="full_song_stereo")
            as_text = json.dumps(result).lower()

            self.assertFalse(result["input"]["analysis_isolated"])
            self.assertEqual(result["input"]["mode"], "full_song_stereo")
            self.assertIn("heuristic", as_text)
            self.assertIn("not isolated", as_text)


if __name__ == "__main__":
    unittest.main()

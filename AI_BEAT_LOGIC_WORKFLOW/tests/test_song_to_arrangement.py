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

from song_arrangement_analyzer import analyze_song_structure, write_song_structure_analysis  # noqa: E402


def write_structured_song(path: Path, sample_rate: int = 48000, seconds: float = 24.0) -> None:
    frames = int(sample_rate * seconds)
    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(2)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        for index in range(frames):
            time = index / sample_rate
            if time < 4.0 or time > 21.0:
                amp = 0.03
            elif 8.0 <= time < 16.0:
                amp = 0.55
            else:
                amp = 0.22
            pulse = 0.45 * math.exp(-(time % 0.5) * 60.0) if (time % 0.5) < 0.06 and amp > 0.2 else 0.0
            tone = amp * math.sin(2.0 * math.pi * 220.0 * time)
            value = max(-0.9, min(0.9, tone + pulse))
            raw = int(value * 32767).to_bytes(2, "little", signed=True)
            wav_file.writeframesraw(raw + raw)


class SongToArrangementTests(unittest.TestCase):
    def test_detects_hook_candidates_in_dummy_audio(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            song = Path(tmp) / "song.wav"
            write_structured_song(song)

            analysis = analyze_song_structure(song, mode="full_song_stereo")
            as_text = json.dumps(analysis).lower()

            self.assertEqual(analysis["schema_version"], "song_structure_analysis.v1")
            self.assertEqual(analysis["input"]["mode"], "full_song_stereo")
            self.assertGreater(analysis["duration_seconds"], 23.0)
            self.assertTrue(analysis["sections"])
            self.assertTrue(analysis["hook_candidates"])
            self.assertIn("Section detection is heuristic.", analysis["limitations"])
            self.assertIn("no full arrangement rewrite", as_text)

    def test_handles_very_short_audio_with_low_confidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            song = Path(tmp) / "short.wav"
            write_structured_song(song, seconds=1.5)

            analysis = analyze_song_structure(song, mode="instrumental")

            self.assertLess(analysis["duration_seconds"], 2.0)
            self.assertTrue(all(section["confidence"] == "low" for section in analysis["sections"]))
            self.assertIn("Very short audio", " ".join(analysis["limitations"]))

    def test_invalid_audio_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            bad = Path(tmp) / "bad.wav"
            bad.write_text("not audio", encoding="utf-8")

            analysis = analyze_song_structure(bad)

            self.assertEqual(analysis["sections"], [])
            self.assertTrue(analysis["limitations"])
            self.assertIn("could not be read", analysis["limitations"][0])

    def test_write_song_structure_outputs_json_and_summary_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "workflow"
            song = Path(tmp) / "song.wav"
            write_structured_song(song)

            paths = write_song_structure_analysis(song, project_root=root, mode="vocal_song")
            parsed = json.loads(paths["json"].read_text(encoding="utf-8"))
            summary = paths["summary"].read_text(encoding="utf-8")

            self.assertEqual(parsed["input"]["mode"], "vocal_song")
            self.assertIn("Song Structure Analysis Summary", summary)
            self.assertFalse((root / "05_FINAL_WAV").exists())


if __name__ == "__main__":
    unittest.main()

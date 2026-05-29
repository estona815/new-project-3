from __future__ import annotations

import math
import tempfile
import unittest
import wave
from pathlib import Path

from harness.tempo_grid_analyzer import analyze_tempo_grid


def write_click_track(path: Path, bpm: float = 120.0, duration: float = 8.0, sample_rate: int = 44100) -> None:
    frames = [0.0 for _ in range(int(duration * sample_rate))]
    beat = 60.0 / bpm
    click_len = int(sample_rate * 0.01)
    time_sec = 0.0
    while time_sec < duration:
        start = int(time_sec * sample_rate)
        for offset in range(click_len):
            idx = start + offset
            if idx < len(frames):
                frames[idx] += math.sin(2.0 * math.pi * 1200.0 * offset / sample_rate) * (1.0 - offset / click_len) * 0.8
        time_sec += beat
    pcm = b"".join(int(max(-1.0, min(1.0, value)) * 32767).to_bytes(2, "little", signed=True) for value in frames)
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(sample_rate)
        handle.writeframes(pcm)


class TempoGridAnalyzerTests(unittest.TestCase):
    def test_click_track_estimates_tempo(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "click.wav"
            write_click_track(source, bpm=120.0)

            payload = analyze_tempo_grid(source)

            self.assertIn(payload["grid_confidence"], {"PASS", "WARN"})
            self.assertIsNotNone(payload["selected_bpm"])
            self.assertLess(abs(float(payload["selected_bpm"]) - 120.0), 3.0)

    def test_missing_source_is_blocker(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            missing = Path(tmp) / "missing.wav"

            with self.assertRaises(FileNotFoundError):
                analyze_tempo_grid(missing)


if __name__ == "__main__":
    unittest.main()

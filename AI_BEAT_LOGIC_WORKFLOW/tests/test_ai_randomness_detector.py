from __future__ import annotations

import math
import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from ai_randomness_detector import detect_ai_randomness  # noqa: E402
from AI_BEAT_LOGIC_WORKFLOW.tests.test_bad_song_diagnosis import structured_motif_song_samples  # noqa: E402


def random_glitch_song_samples(sample_rate: int = 48000, seconds: float = 24.0) -> list[float]:
    frames = int(sample_rate * seconds)
    samples: list[float] = []
    glitch_starts = {3.0, 5.5, 9.0, 13.7, 18.2}
    for index in range(frames):
        t = index / sample_rate
        value = 0.22 * math.sin(2.0 * math.pi * 220.0 * t)
        for start in glitch_starts:
            if start <= t < start + 0.7:
                value += 0.34 * math.sin(2.0 * math.pi * 7200.0 * t)
                value += 0.20 * math.sin(2.0 * math.pi * 9600.0 * t)
        samples.append(value)
    return samples


class AiRandomnessDetectorTests(unittest.TestCase):
    def test_random_glitch_bursts_raise_randomness_risk(self) -> None:
        result = detect_ai_randomness(random_glitch_song_samples(), 48000)

        self.assertIn(result["randomness_risk"], {"medium", "high"})
        self.assertTrue(result["glitch_bursts_not_tied_to_sections"] or result["sudden_texture_swaps"])

    def test_structured_song_has_lower_randomness_than_glitch_song(self) -> None:
        glitch = detect_ai_randomness(random_glitch_song_samples(), 48000)
        structured = detect_ai_randomness(structured_motif_song_samples(), 48000)

        self.assertLess(structured["randomness_score"], glitch["randomness_score"])


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import math
import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_DIR))

from vocal_phrase_segmenter import segment_vocal_phrases, vocal_activity_frames  # noqa: E402


class VocalPhraseSegmenterTests(unittest.TestCase):
    def test_segmenter_finds_active_phrases(self) -> None:
        sample_rate = 1000
        samples = []
        for index in range(3000):
            time = index / sample_rate
            active = 0.3 < time < 1.0 or 1.5 < time < 2.2
            samples.append(math.sin(2.0 * math.pi * 120.0 * time) * (0.4 if active else 0.0))

        frames = vocal_activity_frames(samples, sample_rate)
        phrases = segment_vocal_phrases(frames, mode="separate_vocal")

        self.assertGreaterEqual(len(phrases), 2)
        self.assertEqual(phrases[0]["phrase_id"], "vocal_phrase_001")
        self.assertIn(phrases[0]["energy"], {"medium", "high"})
        self.assertEqual(phrases[0]["phrase_type"], "lead")

    def test_full_stereo_phrase_has_heuristic_limitation(self) -> None:
        frames = [{"start": 0.0, "end": 0.1, "rms": 0.2, "peak": 0.3, "brightness_ratio": 0.5}]

        phrases = segment_vocal_phrases(frames, mode="full_song_stereo")

        self.assertEqual(phrases[0]["phrase_type"], "unknown")
        self.assertIn("heuristic", " ".join(phrases[0]["limitations"]))


if __name__ == "__main__":
    unittest.main()

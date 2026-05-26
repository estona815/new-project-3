from __future__ import annotations

import math
import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_DIR))

from vocal_pitch_guide import build_pitch_correction_guide, notes_for_phrase, pitch_contour, pitch_frames  # noqa: E402


class VocalPitchGuideTests(unittest.TestCase):
    def test_pitch_frames_create_note_candidates(self) -> None:
        sample_rate = 48000
        samples = [math.sin(2.0 * math.pi * 220.0 * index / sample_rate) * 0.4 for index in range(sample_rate)]

        frames = pitch_frames(samples, sample_rate)
        phrase = {"start": 0.0, "end": 1.0}
        notes = notes_for_phrase(phrase, frames, "separate_vocal")
        contour = pitch_contour(notes)

        self.assertTrue(notes)
        self.assertIn("note", notes[0])
        self.assertIn(contour["shape"], {"rising", "falling", "flat", "arched", "unstable"})
        self.assertFalse(any(note["confidence"] == "high" for note in notes))

    def test_full_stereo_notes_are_low_confidence(self) -> None:
        frame = [{"start": 0.0, "end": 0.1, "note": "A3", "midi": 57, "frequency_hz": 220.0, "confidence": "medium"}]

        notes = notes_for_phrase({"start": 0.0, "end": 0.5}, frame, "full_song_stereo")

        self.assertEqual(notes[0]["confidence"], "low")

    def test_pitch_correction_guide_is_recommended_not_applied(self) -> None:
        guide = build_pitch_correction_guide([], request_mode="hard_effect", estimated_key="F# minor")

        self.assertEqual(guide["recommended_mode"], "hard_effect")
        self.assertTrue(guide["manual_logic_required"])
        self.assertEqual(guide["claim_language"], "recommended, not applied")


if __name__ == "__main__":
    unittest.main()

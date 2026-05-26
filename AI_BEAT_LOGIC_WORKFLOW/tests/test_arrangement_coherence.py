from __future__ import annotations

import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from arrangement_coherence import analyze_arrangement_coherence  # noqa: E402
from AI_BEAT_LOGIC_WORKFLOW.tests.test_bad_song_diagnosis import loud_weak_song_samples, structured_motif_song_samples  # noqa: E402


class ArrangementCoherenceTests(unittest.TestCase):
    def test_flat_loud_audio_requires_rebuild(self) -> None:
        result = analyze_arrangement_coherence(loud_weak_song_samples(), 48000)

        self.assertLessEqual(result["score"], 2.4)
        self.assertEqual(result["diagnosis"], "arrangement_rebuild_required")
        self.assertLessEqual(result["energy_curve"], 2)

    def test_structured_audio_has_coherent_arrangement(self) -> None:
        result = analyze_arrangement_coherence(structured_motif_song_samples(), 48000)

        self.assertGreater(result["score"], 2.4)
        self.assertNotEqual(result["diagnosis"], "arrangement_rebuild_required")
        self.assertGreaterEqual(result["section_clarity"], 3)


if __name__ == "__main__":
    unittest.main()

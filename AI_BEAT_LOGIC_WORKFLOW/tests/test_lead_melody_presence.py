from __future__ import annotations

import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from lead_melody_presence import analyze_lead_melody_presence  # noqa: E402
from AI_BEAT_LOGIC_WORKFLOW.tests.test_bad_song_diagnosis import loud_weak_song_samples, structured_motif_song_samples  # noqa: E402


class LeadMelodyPresenceTests(unittest.TestCase):
    def test_static_texture_scores_low(self) -> None:
        result = analyze_lead_melody_presence(loud_weak_song_samples(), 48000)

        self.assertLessEqual(result["lead_melody_presence"], 2)
        self.assertEqual(result["diagnosis"], "weak_or_absent")

    def test_repeated_melodic_contour_scores_present_or_unclear(self) -> None:
        result = analyze_lead_melody_presence(structured_motif_song_samples(), 48000)

        self.assertGreaterEqual(result["lead_melody_presence"], 3)
        self.assertGreater(result["motif_recurrence"], 0.2)
        self.assertGreater(result["repeated_contour"], 0.2)


if __name__ == "__main__":
    unittest.main()

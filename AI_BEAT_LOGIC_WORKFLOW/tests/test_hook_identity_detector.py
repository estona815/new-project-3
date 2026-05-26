from __future__ import annotations

import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from hook_identity_detector import detect_hook_identity  # noqa: E402
from AI_BEAT_LOGIC_WORKFLOW.tests.test_bad_song_diagnosis import loud_weak_song_samples, structured_motif_song_samples  # noqa: E402


class HookIdentityDetectorTests(unittest.TestCase):
    def test_loud_static_audio_has_weak_hook_identity(self) -> None:
        result = detect_hook_identity(loud_weak_song_samples(), 48000)

        self.assertLessEqual(result["hook_identity"], 2)
        self.assertEqual(result["diagnosis"], "weak_or_absent")

    def test_repeated_motif_audio_has_hook_identity(self) -> None:
        result = detect_hook_identity(structured_motif_song_samples(), 48000)

        self.assertGreaterEqual(result["hook_identity"], 3)
        self.assertGreaterEqual(result["motif_repetition_quality"], 3)
        self.assertTrue(result["hook_candidates"])


if __name__ == "__main__":
    unittest.main()

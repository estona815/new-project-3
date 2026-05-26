from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from bass_808_midi_guide import generate_bass_808_midi_guide  # noqa: E402


class Bass808MidiGuideTests(unittest.TestCase):
    def test_stereo_only_does_not_claim_true_808_rewrite(self) -> None:
        guide = generate_bass_808_midi_guide(stems_available=False, genre_mode="digicore")
        text = json.dumps(guide).lower()

        self.assertTrue(guide["sub_mono"])
        self.assertEqual(guide["true_rewrite_status"], "manual_logic_or_midi_required")
        self.assertIn("true 808 rewrite requires midi", text)
        self.assertIn("stereo-only input cannot", text)


if __name__ == "__main__":
    unittest.main()

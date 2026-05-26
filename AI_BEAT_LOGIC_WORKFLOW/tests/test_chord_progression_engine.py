from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from chord_progression_engine import build_chord_progression_guide, generate_chord_options, normalize_key_payload  # noqa: E402


class ChordProgressionEngineTests(unittest.TestCase):
    def test_low_key_confidence_provides_multiple_options_and_ear_check(self) -> None:
        guide = build_chord_progression_guide(
            key={"estimated_key": None, "confidence": "low", "alternatives": ["A minor", "C major"]},
            style_target="commercial_digicore_hyperpop",
        )
        as_text = json.dumps(guide).lower()

        self.assertEqual(guide["status"], "COMPOSITION_GUIDE_READY")
        self.assertGreaterEqual(len(guide["options"]), 3)
        self.assertTrue(all(option.get("confirm_by_ear") for option in guide["options"]))
        self.assertIn("confirm by ear", as_text)
        self.assertIn("do not copy exact reference progressions", as_text)

    def test_medium_key_confidence_keeps_estimated_key(self) -> None:
        options = generate_chord_options(key={"estimated_key": "F# minor", "confidence": "medium"}, style_target="hip_hop")

        self.assertEqual(options[0]["key"], "F# minor")
        self.assertFalse(options[0].get("confirm_by_ear", False))
        self.assertIn("vocal", options[0]["feel"])

    def test_normalize_key_payload_accepts_sample_analysis_shape(self) -> None:
        payload = normalize_key_payload(
            sample_analysis={
                "tonal": {
                    "estimated_tonic_or_pitch_center": "C#4",
                    "confidence": "low",
                    "key_candidates": [{"tonic_or_pitch_center": "C#4"}],
                }
            }
        )

        self.assertEqual(payload["estimated_key"], "C#4")
        self.assertEqual(payload["alternatives"], ["C#4"])


if __name__ == "__main__":
    unittest.main()

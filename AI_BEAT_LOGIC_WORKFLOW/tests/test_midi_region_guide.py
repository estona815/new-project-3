from __future__ import annotations

import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from bass_808_midi_pattern_export import generate_bass_808_midi_pattern_guide  # noqa: E402
from drum_midi_pattern_export import generate_drum_midi_guide  # noqa: E402
from midi_region_guide import build_midi_region_guide  # noqa: E402


class MidiRegionGuideTests(unittest.TestCase):
    def test_midi_region_guide_has_claim_guard_and_regions(self) -> None:
        plan = {
            "analysis_context": {"sample_timing": {"bpm": 148, "confidence": "medium"}},
            "chord_progression_guide": {"estimated_key": "F# minor", "key_confidence": "low"},
            "sample_chop_guide": {
                "loop_candidates": [{"start": 0.0, "end": 7.78, "estimated_bars": 4, "confidence": "medium"}],
                "chop_candidates": [],
            },
            "section_progression_guide": {"sections": [{"name": "hook", "start": 8.0, "duration": 16.0, "energy_target": 5}]},
        }
        drum = generate_drum_midi_guide(plan)
        bass = generate_bass_808_midi_pattern_guide(plan)
        guide = build_midi_region_guide(plan, drum_midi_guide=drum, bass_808_midi_guide=bass)

        self.assertEqual(guide["schema_version"], "midi_region_guide.v1")
        self.assertEqual(guide["tempo_bpm"], 148)
        self.assertEqual(guide["key"], "F# minor")
        self.assertTrue(any(region["track"] == "Sample" for region in guide["regions"]))
        self.assertTrue(any(region["track"] == "808" for region in guide["regions"]))
        self.assertFalse(guide["claim_guard"]["midi_imported_into_logic"])
        self.assertFalse(guide["claim_guard"]["logic_project_modified"])


if __name__ == "__main__":
    unittest.main()

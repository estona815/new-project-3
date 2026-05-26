from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from arrangement_to_logic_package import convert_arrangement_to_logic_package, render_mix_prep_checklist  # noqa: E402


ARRANGEMENT_PLAN = {
    "status": "ARRANGEMENT_PLAN_READY",
    "length_mode": "reels_15sec",
    "genre_mode": "commercial_digicore_hyperpop",
    "request_text": "릴스 훅, 808 강하게",
    "section_progression_guide": {"sections": [{"name": "hook", "start": 0.0, "end": 15.0}]},
    "chord_progression_guide": {"estimated_key": "F# minor", "key_confidence": "low", "options": []},
    "sample_chop_guide": {"direct_sample_use_allowed": False, "ownership_status": "unknown"},
    "drum_programming_guide": {"kick_character": "short punchy"},
    "bass_808_midi_guide": {"sub_mono": True, "movement_density": "medium"},
}

MIDI_GUIDE = {
    "schema_version": "midi_region_guide.v1",
    "tempo_bpm": 148,
    "key": "F# minor",
    "claim_guard": {"midi_imported_into_logic": False},
}

AUTOMATION_GUIDE = {
    "schema_version": "automation_guide.v1",
    "events": [{"type": "volume_automation", "manual_logic_required": True}],
    "claim_guard": {"automation_written_to_logic": False},
}


class ArrangementToLogicPackageTests(unittest.TestCase):
    def test_stereo_source_marks_stem_level_tasks_manual(self) -> None:
        package = convert_arrangement_to_logic_package(
            ARRANGEMENT_PLAN,
            midi_region_guide=MIDI_GUIDE,
            automation_guide=AUTOMATION_GUIDE,
            creative_brief={"mode": "full_song_stereo", "input_files": {"main_input": "song.wav"}},
        )
        text = json.dumps(package).lower()

        self.assertEqual(package["status"], "PRODUCTION_PACKAGE_READY")
        self.assertTrue(package["capabilities"]["stereo_only"])
        self.assertTrue(package["capabilities"]["stem_level_tasks_require_stems"])
        self.assertFalse(package["claim_guard"]["logic_automation_success"])
        self.assertIn("direct sample use is blocked", text)
        self.assertIn("manual plugin insert required", text)

    def test_stems_allow_more_direct_balancing_without_logic_success_claim(self) -> None:
        package = convert_arrangement_to_logic_package(
            ARRANGEMENT_PLAN,
            midi_region_guide=MIDI_GUIDE,
            automation_guide=AUTOMATION_GUIDE,
            creative_brief={"mode": "stems", "input_files": {"stems_folder": "/tmp/stems"}},
        )

        self.assertTrue(package["capabilities"]["stems_available"])
        self.assertTrue(package["capabilities"]["direct_stem_balancing_allowed"])
        self.assertFalse(package["claim_guard"]["plugins_inserted"])
        self.assertIn("Keep sub/kick/808 mono-centered", render_mix_prep_checklist(package))


if __name__ == "__main__":
    unittest.main()

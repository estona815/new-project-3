from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from composition_autopilot import COMPOSITION_STATUS, build_composition_guide, run_composition_autopilot  # noqa: E402


SAMPLE_ANALYSIS = {
    "schema_version": "sample_analysis.v1",
    "timing": {"bpm": 148, "confidence": "medium", "bpm_candidates": [74, 148]},
    "tonal": {"estimated_key": "F# minor", "confidence": "low", "key_candidates": [{"tonic_or_pitch_center": "A major"}]},
    "motif_hook_detection": {"hook_motif_candidates": [{"start": 0.0, "end": 1.2, "confidence": "medium"}]},
    "transient_onset": {"onset_density": 2.5},
    "sample_usage_safety": {"ownership_status": "unknown", "direct_sample_use_allowed": False},
}

VOCAL_TO_CODE = {
    "schema_version": "vocal_to_code.v1",
    "global": {"estimated_bpm": 148, "bpm_confidence": "medium", "estimated_key": "F# minor", "key_confidence": "low"},
    "phrases": [{"phrase_id": "vocal_phrase_001", "start": 0.4, "end": 1.7}],
    "false_claim_guard": {"note_transcription_is_exact": False},
}

SONG_STRUCTURE = {
    "schema_version": "song_structure_analysis.v1",
    "hook_candidates": [{"start": 0.0, "end": 15.0, "confidence": "medium"}],
    "reels_hook_region": {"start": 0.0, "end": 15.0},
}


class CompositionAutopilotTests(unittest.TestCase):
    def test_build_composition_guide_from_messy_korean_request(self) -> None:
        guide = build_composition_guide(
            rough_request="마음대로 상업 음악 퀄로 디지코어/하이퍼팝 결. 보컬 앞으로, 808 강하게, 릴스 훅.",
            sample_analysis=SAMPLE_ANALYSIS,
            vocal_to_code=VOCAL_TO_CODE,
            song_structure_analysis=SONG_STRUCTURE,
            style_cluster="commercial_digicore",
        )
        text = json.dumps(guide, ensure_ascii=False).lower()

        self.assertEqual(guide["schema_version"], "composition_guide.v1")
        self.assertEqual(guide["status"], COMPOSITION_STATUS)
        self.assertFalse(guide["complete"])
        self.assertEqual(guide["style_target"], "commercial_digicore_hyperpop")
        self.assertEqual(guide["tempo"]["bpm"], 148)
        self.assertEqual(guide["key"]["confidence"], "low")
        self.assertEqual(guide["composition_strategy"]["energy_curve"], "fast_hook")
        self.assertIn(guide["composition_strategy"]["main_hook"], {"sample_motif", "vocal_phrase"})
        self.assertTrue(guide["chord_options"])
        self.assertTrue(guide["melody_ideas"])
        self.assertTrue(guide["bassline_ideas"])
        self.assertTrue(guide["drum_ideas"])
        self.assertTrue(guide["topline_ideas"])
        self.assertFalse(guide["safety"]["exact_reference_copy"])
        self.assertFalse(guide["safety"]["voice_clone"])
        self.assertFalse(guide["safety"]["sample_use_allowed"])
        self.assertIn("confirm by ear", text)
        self.assertIn("not exact transcription", text)
        self.assertNotIn("complete\": true", text)

    def test_text_only_request_generates_guide_only_status(self) -> None:
        guide = build_composition_guide(rough_request="알아서 힙합으로 보컬 잘 들리게")

        self.assertEqual(guide["status"], COMPOSITION_STATUS)
        self.assertFalse(guide["complete"])
        self.assertEqual(guide["tempo"]["confidence"], "low")
        self.assertIn("No final WAV is generated", " ".join(guide["limitations"]))

    def test_run_composition_autopilot_writes_expected_outputs_without_final_wav(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "01_ANALYSIS").mkdir()
            (root / "02_EDIT_PLAN").mkdir()
            (root / "01_ANALYSIS" / "sample_analysis.json").write_text(json.dumps(SAMPLE_ANALYSIS), encoding="utf-8")
            (root / "01_ANALYSIS" / "vocal_to_code.json").write_text(json.dumps(VOCAL_TO_CODE), encoding="utf-8")
            (root / "01_ANALYSIS" / "song_structure_analysis.json").write_text(json.dumps(SONG_STRUCTURE), encoding="utf-8")

            result = run_composition_autopilot(
                project_root=root,
                rough_request="샘플 줄게. 이걸로 힙합/하이퍼팝 편곡 짜고 믹마까지.",
                style_cluster="hyperpop",
            )
            paths = result["paths"]

            for key in (
                "composition_guide",
                "composition_markdown",
                "chord_progression_guide",
                "topline_guide",
                "bassline_guide",
                "drum_pattern_guide",
            ):
                self.assertTrue(paths[key].exists(), key)
            parsed = json.loads(paths["composition_guide"].read_text(encoding="utf-8"))
            markdown = paths["composition_markdown"].read_text(encoding="utf-8")
            self.assertEqual(parsed["status"], COMPOSITION_STATUS)
            self.assertFalse((root / "05_FINAL_WAV").exists())
            self.assertIn("complete: false", markdown)
            self.assertIn("COMPOSITION_GUIDE_READY is not COMPLETE", markdown)


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from vocal_texture_classifier import classify_vocal_texture_candidates, has_bad_vocal_lead_role  # noqa: E402


class VocalTextureClassifierTests(unittest.TestCase):
    def test_weird_center_vocal_candidate_becomes_unwanted_lead_issue(self) -> None:
        diagnosis = {
            "input": {"mode": "full_song_stereo"},
            "musical_identity": {"lead_melody_presence": 1},
            "vocal_texture": {
                "weird_vocal_texture_risk": "high",
                "vocal_chop_as_unwanted_lead": True,
                "pitch_instability": "medium",
                "phrasing_confusion": "medium",
            },
            "rescue_decision": {"lead_melody_required": True},
        }
        issues = classify_vocal_texture_candidates(
            [
                {
                    "start": 12.0,
                    "end": 18.5,
                    "confidence": "medium",
                    "reason": "mono-centered modulated fake vocal chop dominates lead",
                }
            ],
            rescue_diagnosis=diagnosis,
        )

        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0]["issue"], "fake_vocal_chop_dominates_lead")
        self.assertEqual(issues[0]["confidence"], "high")
        self.assertEqual(issues[0]["start"], 12.0)
        self.assertEqual(issues[0]["end"], 18.5)
        self.assertTrue(has_bad_vocal_lead_role(issues))

    def test_global_diagnosis_creates_issue_without_candidate_windows(self) -> None:
        diagnosis = {
            "input": {"mode": "full_song_stereo"},
            "basic_metrics": {"duration_seconds": 42.0},
            "vocal_texture": {
                "weird_vocal_texture_risk": "high",
                "vocal_chop_as_unwanted_lead": True,
                "phrasing_confusion": "low",
            },
        }
        issues = classify_vocal_texture_candidates([], rescue_diagnosis=diagnosis)

        self.assertEqual(issues[0]["issue"], "fake_vocal_chop_dominates_lead")
        self.assertEqual(issues[0]["source"], "diagnosis_summary")
        self.assertEqual(issues[0]["end"], 42.0)

    def test_low_risk_without_candidates_returns_no_issue(self) -> None:
        issues = classify_vocal_texture_candidates(
            [],
            rescue_diagnosis={"vocal_texture": {"weird_vocal_texture_risk": "low"}},
        )

        self.assertEqual(issues, [])


if __name__ == "__main__":
    unittest.main()

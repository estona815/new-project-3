from __future__ import annotations

import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_DIR))

from edit_plan_generator import build_edit_plan  # noqa: E402
from humanization_rubric import reference_match_qc, render_style_match_qc  # noqa: E402
from qc_report import build_qc_report  # noqa: E402
from reference_intent_parser import parse_reference_intent  # noqa: E402
from reference_profile import build_reference_target_profile  # noqa: E402


ANALYSIS = {
    "metadata": {"duration_seconds": 90.0},
    "arrangement_candidates": {},
    "silence_detection": {},
    "vocal_like_texture_candidates": [],
    "melody_buried_candidates": [],
    "low_end_excess_candidates": [],
}

VERIFICATION = {
    "passed": True,
    "ok": True,
    "format_verified": True,
    "sample_rate": 48000,
    "channels": 2,
    "bit_depth": 24,
    "duration_seconds": 86.0,
    "file_size": 1000,
    "peak_dbfs": -1.2,
    "rms_dbfs": -10.0,
    "clipping_count": 0,
    "warnings": [],
}


class CommercialDigicoreAutopilotTests(unittest.TestCase):
    def test_slayr_jane_remover_style_cluster_is_safe_high_level_autopilot(self) -> None:
        phrase = "좀 더 2hollis처럼, slayr, Jane Remover, ycs, SYSTEM SEOUL 결로 바꿔줘"
        parsed = parse_reference_intent(phrase)
        autopilot = parsed["commercial_digicore_autopilot"]

        self.assertIn("commercial_digicore_autopilot", parsed["actions"])
        self.assertIn("style_translation", parsed["actions"])
        self.assertTrue({"whole_style", "drums", "bass_808", "synth_width", "arrangement"} <= set(parsed["target_elements"]))
        self.assertTrue(autopilot["active"])
        self.assertTrue(autopilot["style_cluster"]["active"])
        self.assertIn("slayr", autopilot["style_cluster"]["labels"])
        self.assertIn("Jane Remover", autopilot["style_cluster"]["labels"])
        self.assertFalse(autopilot["style_cluster"]["copying_allowed"])
        self.assertFalse(autopilot["style_cluster"]["artist_voice_clone_allowed"])

    def test_commercial_quality_and_suno_humanize_requests_create_defaults(self) -> None:
        phrase = "대충 상업 음악 퀄로 뽑아. Suno 느낌 줄이고 사람이 찍은 비트처럼"
        profile = build_reference_target_profile(phrase, None)
        autopilot = profile["commercial_digicore_autopilot"]
        traits = profile["reference_traits"]

        self.assertTrue(autopilot["commercial_requested"])
        self.assertTrue(autopilot["humanize_suno_requested"])
        self.assertEqual(autopilot["arrangement_defaults"]["target_hook_seconds"], 30)
        self.assertEqual(autopilot["arrangement_defaults"]["variation_frequency_bars"], 4)
        self.assertEqual(autopilot["mix_targets"]["target"], "commercial_ready_demo")
        self.assertIn("no chart-level success", " ".join(autopilot["safety_notes"]).lower())
        self.assertTrue(traits["commercial_digicore_autopilot"]["active"])
        self.assertIn("suno loop feel", profile["avoid"])

    def test_stem_limited_request_writes_honest_logic_manual_plan(self) -> None:
        phrase = "스템 없으면 가능한 선에서 해주고, Logic 수동 플랜도 써줘"
        profile = build_reference_target_profile(phrase, None)
        plan = build_edit_plan(ANALYSIS, {"mode": "full_song_stereo", "input": "/tmp/stereo.wav"}, profile)

        self.assertIn("Commercial Digicore Autopilot", plan)
        self.assertIn("Automatic fallback scope", plan)
        self.assertIn("broad stereo EQ", plan)
        self.assertIn("Manual Logic scope", plan)
        self.assertIn("stem-level moves require stems", plan)
        self.assertNotIn("true stem separation", plan.lower())

    def test_qc_scores_commercial_autopilot_without_false_complete(self) -> None:
        profile = build_reference_target_profile(
            "대충 상업 음악 퀄로 뽑아. 스템 없으면 가능한 선에서 해주고, Logic 수동 플랜도 써줘",
            None,
        )
        qc = reference_match_qc(
            profile,
            verification=VERIFICATION,
            options={"mode": "full_song_stereo"},
            source_type="fallback_processed",
            completion_gate_complete=False,
            qc_report_exists=True,
            master_qc_report_exists=False,
        )
        rendered = render_style_match_qc(
            profile,
            stereo_only=True,
            verification=VERIFICATION,
            options={"mode": "full_song_stereo"},
            source_type="fallback_processed",
            completion_gate_complete=False,
            qc_report_exists=True,
            master_qc_report_exists=False,
            enforce_completion=True,
        )
        names = " ".join(item["name"] for item in qc["scores"])

        self.assertIn("Commercial digicore autopilot readiness", names)
        self.assertEqual(qc["result"], "FAIL_REPROCESS")
        self.assertIn("completion gate did not pass", qc["blocking_reasons"])
        self.assertIn("Commercial digicore autopilot readiness", rendered)

    def test_qc_report_includes_commercial_autopilot_section(self) -> None:
        profile = build_reference_target_profile("대충 상업 음악 퀄로 뽑아. 릴스 첫 15초 안에 훅 터지게", None)
        report = build_qc_report(
            {"original_path": "/tmp/input.wav"},
            ANALYSIS,
            VERIFICATION,
            Path("/tmp/project/05_FINAL_WAV/final.wav"),
            None,
            "fallback_processed",
            "ffmpeg",
            "not created",
            reference_profile=profile,
            options={"mode": "full_song_stereo"},
            qc_report_exists=True,
        )

        self.assertIn("## Commercial Digicore Autopilot QC", report)
        self.assertIn("technical readiness, mix clarity, arrangement intentionality", report)
        self.assertIn("no chart-level success promise", report)


if __name__ == "__main__":
    unittest.main()

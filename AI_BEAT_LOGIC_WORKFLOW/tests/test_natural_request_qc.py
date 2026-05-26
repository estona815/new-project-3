from __future__ import annotations

import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_DIR))

from humanization_rubric import reference_match_qc, render_style_match_qc  # noqa: E402
from qc_report import build_qc_report  # noqa: E402
from reference_profile import build_reference_target_profile  # noqa: E402


FINAL_INFO = {
    "passed": True,
    "ok": True,
    "format_verified": True,
    "sample_rate": 48000,
    "channels": 2,
    "bit_depth": 24,
    "duration_seconds": 30.0,
    "file_size": 1000,
    "peak_dbfs": -1.2,
    "rms_dbfs": -10.0,
    "estimated_lufs": -10.0,
    "clipping_count": 0,
    "warnings": [],
}


class NaturalRequestQCTests(unittest.TestCase):
    def test_exact_copy_request_is_blocked_but_trait_match_can_score(self) -> None:
        profile = build_reference_target_profile("웨스트우드 Just Touched Down 킥 베이스 따와라", None)
        qc = reference_match_qc(
            profile,
            verification=FINAL_INFO,
            options={"mode": "stems"},
            source_type="logic_export",
            completion_gate_complete=True,
            qc_report_exists=True,
            master_qc_report_exists=True,
        )
        rendered = render_style_match_qc(
            profile,
            stereo_only=False,
            verification=FINAL_INFO,
            options={"mode": "stems"},
            source_type="logic_export",
            completion_gate_complete=True,
            qc_report_exists=True,
            master_qc_report_exists=True,
            enforce_completion=True,
        )

        self.assertEqual(qc["korean_request_interpretation"]["exact_copy_status"], "blocked")
        self.assertIn("exact sample copy was not performed", rendered)
        self.assertGreaterEqual(qc["scores"][0]["score"], 3)
        self.assertGreaterEqual(qc["scores"][1]["score"], 3)

    def test_decapitator_and_autotune_are_not_claimed_without_verified_tools(self) -> None:
        profile = build_reference_target_profile("보컬 오토튠 더 걸고 디카페이터 살짝", None)
        qc = reference_match_qc(
            profile,
            verification=FINAL_INFO,
            options={"mode": "vocal_plus_beat", "vocal_mode": "front", "pitch_tool_available": False},
            source_type="logic_export",
            completion_gate_complete=True,
            qc_report_exists=True,
            master_qc_report_exists=True,
        )
        vocal_score = next(item for item in qc["scores"] if item["name"].startswith("Vocal FX request match"))

        self.assertLessEqual(vocal_score["score"], 3)
        self.assertIn("not scored as plugin-applied", vocal_score["note"])
        self.assertIn("manual Logic insert recommended", vocal_score["note"])
        rendered = render_style_match_qc(
            profile,
            stereo_only=False,
            verification=FINAL_INFO,
            options={"mode": "vocal_plus_beat", "vocal_mode": "front", "pitch_tool_available": False},
            source_type="logic_export",
            completion_gate_complete=True,
            qc_report_exists=True,
            master_qc_report_exists=True,
            enforce_completion=True,
        )
        self.assertIn("manual Logic insert recommended", rendered)
        self.assertNotIn("verified plugin application", rendered)

    def test_stereo_only_stem_rewrite_needs_manual_logic_edit(self) -> None:
        profile = build_reference_target_profile("킥 베이스 따와라 드럼 패턴 바꿔줘", None)
        qc = reference_match_qc(
            profile,
            verification=FINAL_INFO,
            options={"mode": "full_song_stereo"},
            source_type="fallback_processed",
            completion_gate_complete=True,
            qc_report_exists=True,
            master_qc_report_exists=True,
        )

        self.assertEqual(qc["result"], "NEEDS_MANUAL_LOGIC_EDIT")
        self.assertTrue(qc["stereo_only"])
        self.assertIn("stereo-level processing", " ".join(qc["manual_limitations"]))

        stems_qc = reference_match_qc(
            profile,
            verification=FINAL_INFO,
            options={"mode": "stems"},
            source_type="logic_export",
            completion_gate_complete=True,
            qc_report_exists=True,
            master_qc_report_exists=True,
        )
        self.assertFalse(stems_qc["manual_limitations"])
        stereo_score = next(item for item in stems_qc["scores"] if item["name"] == "Stereo-only limitation impact")
        self.assertEqual(stereo_score["score"], 5)
        self.assertIn("Direct sources/stems reduce stereo-only limitation", stereo_score["note"])

    def test_technical_failures_block_pass(self) -> None:
        profile = build_reference_target_profile("Love Blur 느낌 드럼", None)
        qc = reference_match_qc(
            profile,
            verification={"passed": False, "format_verified": False, "clipping_count": 12},
            options={"mode": "stems"},
            source_type="logic_export",
            completion_gate_complete=False,
            qc_report_exists=False,
            master_qc_report_exists=False,
        )

        self.assertEqual(qc["result"], "FAIL_REPROCESS")
        self.assertIn("final WAV verification failed", qc["blocking_reasons"])
        self.assertIn("wrong sample rate/bit depth or unverified final format", qc["blocking_reasons"])
        self.assertIn("severe clipping detected", qc["blocking_reasons"])
        self.assertIn("qc_report.md missing", qc["blocking_reasons"])
        self.assertIn("master_qc_report.md missing", qc["blocking_reasons"])
        self.assertNotEqual(qc["result"], "PASS")

    def test_qc_report_renders_korean_request_interpretation_and_scores(self) -> None:
        profile = build_reference_target_profile(
            "웨스트우드 Just Touched Down 킥 베이스 따와라. 보컬 오토튠 더 디카페이터 살짝.",
            None,
        )
        report = build_qc_report(
            {"original_path": "/tmp/input.wav", "copied_path": "/tmp/copied.wav", "working_wav_path": "/tmp/working.wav"},
            {"arrangement_candidates": {}, "vocal_like_texture_candidates": [], "low_end_excess_candidates": [], "melody_buried_candidates": []},
            FINAL_INFO,
            Path("/tmp/project/05_FINAL_WAV/final.wav"),
            None,
            "logic_export",
            "ffmpeg",
            "not created",
            reference_profile=profile,
            options={"mode": "stems", "master_qc_report_path": "/tmp/project/09_MIX_MASTER/missing.md"},
            qc_report_exists=True,
        )

        self.assertIn("## Korean Request Interpretation QC", report)
        self.assertIn("Copying risk: high", report)
        self.assertIn("Exact-copy blocked or allowed: blocked", report)
        self.assertIn("Reference evidence mode: text_only", report)
        self.assertIn("## Target Match Scores", report)
        self.assertIn("Final WAV technical verification", report)
        self.assertIn("Artifact/completion integrity", report)


if __name__ == "__main__":
    unittest.main()

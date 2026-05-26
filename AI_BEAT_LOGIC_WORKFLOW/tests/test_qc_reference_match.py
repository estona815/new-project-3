from __future__ import annotations

import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_DIR))

from humanization_rubric import reference_match_qc, render_style_match_qc  # noqa: E402
from reference_profile import build_reference_target_profile  # noqa: E402


class QCReferenceMatchTests(unittest.TestCase):
    def test_text_only_reference_match_is_marked_heuristic(self) -> None:
        profile = build_reference_target_profile("ㅇㅇㅇ이라는 곡 베이스처럼 쳐줘", None)

        qc = reference_match_qc(
            profile,
            verification={"passed": True, "format_verified": True, "clipping_count": 0},
            options={"mode": "stems"},
            source_type="logic_export",
            completion_gate_complete=True,
            qc_report_exists=True,
            master_qc_report_exists=True,
        )
        rendered = render_style_match_qc(
            profile,
            stereo_only=False,
            verification={"passed": True, "format_verified": True, "clipping_count": 0},
            options={"mode": "stems"},
            source_type="logic_export",
            completion_gate_complete=True,
            qc_report_exists=True,
            master_qc_report_exists=True,
            enforce_completion=True,
        )

        self.assertTrue(qc["text_only"])
        self.assertIn("heuristic/text-only", rendered)
        self.assertFalse(qc["exact_match_claimed"])

    def test_stereo_only_mode_says_reference_match_is_limited(self) -> None:
        profile = build_reference_target_profile("Love Blur 느낌 드럼", None, {"mode": "full_song_stereo"})

        qc = reference_match_qc(
            profile,
            verification={"passed": True, "format_verified": True, "clipping_count": 0},
            options={"mode": "full_song_stereo"},
            source_type="fallback_processed",
            completion_gate_complete=True,
            qc_report_exists=True,
            master_qc_report_exists=True,
        )
        rendered = render_style_match_qc(
            profile,
            stereo_only=True,
            verification={"passed": True, "format_verified": True, "clipping_count": 0},
            options={"mode": "full_song_stereo"},
            source_type="fallback_processed",
            completion_gate_complete=True,
            qc_report_exists=True,
            master_qc_report_exists=True,
            enforce_completion=True,
        )

        self.assertEqual(qc["result"], "NEEDS_MANUAL_LOGIC_EDIT")
        self.assertTrue(qc["stereo_only"])
        self.assertIn("limited", qc["limitation"])
        self.assertIn("Reference match is limited", rendered)

    def test_no_pass_if_completion_gate_blocked(self) -> None:
        profile = build_reference_target_profile("underground rap vocal upfront", None)

        qc = reference_match_qc(
            profile,
            verification={"passed": False, "format_verified": False, "clipping_count": 0},
            options={"mode": "vocal_plus_beat", "vocal_mode": "front"},
            source_type="logic_export",
            completion_gate_complete=False,
            qc_report_exists=False,
            master_qc_report_exists=False,
        )

        self.assertEqual(qc["result"], "FAIL_REPROCESS")
        self.assertIn("completion gate did not pass", qc["blocking_reasons"])
        self.assertIn("qc_report.md missing", qc["blocking_reasons"])
        self.assertIn("master_qc_report.md missing", qc["blocking_reasons"])

    def test_target_match_scores_include_natural_request_dimensions(self) -> None:
        profile = build_reference_target_profile(
            "웨스트우드 Just Touched Down 킥 베이스 따와라. 보컬 오토튠 더 디카페이터 살짝. 2hollis/ycs/SYSTEM SEOUL처럼 신디 넓게.",
            None,
        )

        qc = reference_match_qc(
            profile,
            verification={"passed": True, "format_verified": True, "clipping_count": 0},
            options={"mode": "full_song_stereo", "vocal_mode": "front"},
            source_type="fallback_processed",
            completion_gate_complete=True,
            qc_report_exists=True,
            master_qc_report_exists=True,
        )
        rendered = render_style_match_qc(
            profile,
            stereo_only=True,
            verification={"passed": True, "format_verified": True, "clipping_count": 0},
            options={"mode": "full_song_stereo", "vocal_mode": "front"},
            source_type="fallback_processed",
            completion_gate_complete=True,
            qc_report_exists=True,
            master_qc_report_exists=True,
            enforce_completion=True,
        )
        names = " ".join(item["name"] for item in qc["scores"])

        self.assertIn("Kick reference direction match", names)
        self.assertIn("Bass/808 reference direction match", names)
        self.assertIn("Vocal FX request match", names)
        self.assertIn("Style cluster match", names)
        self.assertIn("Synth width/panning request match", names)
        self.assertIn("Final WAV technical verification", names)
        self.assertIn("Artifact/completion integrity", names)
        self.assertEqual(qc["korean_request_interpretation"]["copying_risk"], "high")
        self.assertFalse(qc["korean_request_interpretation"]["exact_copy_allowed"])
        self.assertIn("## Korean Request Interpretation QC", rendered)
        self.assertIn("exact sample copy was not performed", rendered)


if __name__ == "__main__":
    unittest.main()

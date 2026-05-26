from __future__ import annotations

import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_DIR))

from edit_plan_generator import build_edit_plan  # noqa: E402
from humanization_rubric import expanded_qc_rubric, reference_match_qc  # noqa: E402
from reference_profile import build_reference_target_profile  # noqa: E402


ANALYSIS_STUB = {
    "metadata": {"duration_seconds": 60.0},
    "arrangement_candidates": {},
    "silence_detection": {},
    "vocal_like_texture_candidates": [],
    "melody_buried_candidates": [],
    "low_end_excess_candidates": [],
}


class LogicReferenceApplicationTests(unittest.TestCase):
    def test_edit_plan_contains_reference_specific_logic_steps(self) -> None:
        profile = build_reference_target_profile("Love Blur 느낌 드럼", None)

        plan = build_edit_plan(ANALYSIS_STUB, {"mode": "full_song_stereo", "input": "/tmp/stereo.wav"}, profile)

        self.assertIn("## Reference Application in Logic Pro", plan)
        self.assertIn("### A. Drums Like Reference", plan)
        self.assertIn("adjust kick sample character", plan)
        self.assertIn("avoid copying the exact reference drum pattern", plan)
        self.assertIn("broad transient shaping, EQ, and arrangement cuts only", plan)
        self.assertIn("mark stem-level drum rewrite as unavailable", plan)

    def test_korean_natural_request_logic_sections_are_practical_and_honest(self) -> None:
        phrase = (
            "웨스트우드 Just Touched Down 베이스랑 킥을 따와라. "
            "보컬 오토튠 더 걸고 디카페이터 살짝. "
            "2hollis, ycs, SYSTEM SEOUL처럼 신디 넓게."
        )
        profile = build_reference_target_profile(phrase, None)

        plan = build_edit_plan(ANALYSIS_STUB, {"mode": "full_song_stereo", "input": "/tmp/stereo.wav"}, profile)

        self.assertIn("## Korean Natural-Language Request Translation", plan)
        self.assertIn("Raw user request", plan)
        self.assertIn("Parsed targets", plan)
        self.assertIn("Reference confidence", plan)
        self.assertIn("Copying policy", plan)
        self.assertIn("What can be done automatically", plan)
        self.assertIn("What requires stems/manual Logic", plan)
        self.assertIn("What will not be copied", plan)
        self.assertIn("## Kick/Bass `따와라` Request", plan)
        self.assertIn("Do not extract or copy a kick/bass sample", plan)
        self.assertIn("preserve phase alignment", plan)
        self.assertIn("tune 808 to the song key", plan)
        self.assertIn("design from scratch based on high-level traits", plan)
        self.assertIn("avoid exact pattern or bassline copying", plan)
        self.assertIn("## Decapitator / AutoTune Vocal Request", plan)
        self.assertIn("Pitch correction plan", plan)
        self.assertIn("Decapitator if installed, generic saturation otherwise", plan)
        self.assertIn("manual_required", plan)
        self.assertIn("Do not claim plugin was applied unless verified", plan)
        self.assertIn("## 2hollis / ycs / SYSTEM SEOUL Style Cluster", plan)
        self.assertIn("bright digital hooks", plan)
        self.assertIn("strong controlled 808", plan)
        self.assertIn("avoid cheap rage clipping", plan.lower())
        self.assertIn("## Synth Width / Panning", plan)
        self.assertIn("High-pass widened duplicate around 120-180Hz", plan)
        self.assertIn("## Stereo-Only Source Limitation", plan)
        self.assertIn("No real stem-level drum rewrite is claimed", plan)
        self.assertIn("No guaranteed vocal removal is claimed", plan)

    def test_full_stereo_reference_rewrite_requires_manual_logic_edit(self) -> None:
        profile = build_reference_target_profile("Love Blur 느낌 드럼, 이 곡처럼 베이스라인 바꿔줘", None)
        verification = {"passed": True, "ok": True, "format_verified": True, "clipping_count": 0, "peak_dbfs": -1.2}

        qc = expanded_qc_rubric(
            analysis=ANALYSIS_STUB,
            verification=verification,
            reference_profile=profile,
            options={"mode": "full_song_stereo", "input": "/tmp/stereo.wav"},
            source_type="fallback_processed",
            completion_gate_complete=True,
        )

        self.assertEqual(qc["result"], "NEEDS_MANUAL_LOGIC_EDIT")
        self.assertTrue(qc["stereo_only"])
        notes = " ".join(item["note"] for item in qc["scores"])
        self.assertIn("stereo-only processing cannot prove stem-level drum/bass edits", notes)

    def test_reference_match_blocks_pass_when_final_verification_fails(self) -> None:
        profile = build_reference_target_profile(
            "Love Blur 느낌 드럼",
            None,
            web_research={"combined_confidence": "medium", "sources": [{"source_type": "official_artist", "relevant_claims": ["energetic digital drums"]}]},
        )

        qc = reference_match_qc(
            profile,
            verification={"passed": False, "ok": False, "format_verified": False, "clipping_count": 4},
            options={"mode": "stems"},
            source_type="logic_export",
            completion_gate_complete=False,
            qc_report_exists=True,
            master_qc_report_exists=True,
            enforce_completion=True,
        )

        self.assertEqual(qc["result"], "FAIL_REPROCESS")
        self.assertIn("completion gate did not pass", qc["blocking_reasons"])
        self.assertIn("final WAV verification failed", qc["blocking_reasons"])
        self.assertIn("wrong sample rate/bit depth or unverified final format", qc["blocking_reasons"])
        self.assertFalse(qc["exact_match_claimed"])


if __name__ == "__main__":
    unittest.main()

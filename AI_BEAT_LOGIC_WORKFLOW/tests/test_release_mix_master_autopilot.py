from __future__ import annotations

import sys
import tempfile
import unittest
import wave
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from export_audio import write_float_wav  # noqa: E402
from final_verify import verify_release_package_audio_readiness  # noqa: E402
from release_mix_master_autopilot import build_release_mix_master_plan, release_package_audio_ready  # noqa: E402


class ReleaseMixMasterAutopilotTests(unittest.TestCase):
    def test_final_master_verified_only_after_final_verify(self) -> None:
        unverified = build_release_mix_master_plan(
            input_mode="full_song_stereo",
            release_ready=True,
            requested_deliverables=["final_master_wav24_48k"],
            final_verify_result=None,
            qc_report_exists=True,
            release_checklist_exists=True,
        )
        verified = build_release_mix_master_plan(
            input_mode="full_song_stereo",
            release_ready=True,
            requested_deliverables=["final_master_wav24_48k"],
            final_verify_result={
                "ok": True,
                "passed": True,
                "format_verified": True,
                "clipping_count": 0,
                "sample_rate": 48000,
                "peak_dbfs": -1.2,
                "rms_dbfs": -16.0,
            },
            qc_report_exists=True,
            release_checklist_exists=True,
        )

        self.assertFalse(unverified["claim_guard"]["final_master_verified"])
        self.assertTrue(verified["claim_guard"]["final_master_verified"])
        self.assertEqual(verified["final_verification_summary"]["source"], "final_verify")

    def test_deliverable_claims_are_honest_for_acapella_and_stems(self) -> None:
        plan = build_release_mix_master_plan(
            input_mode="instrumental_beat",
            requested_deliverables=["acapella_if_available", "stems_if_provided"],
            isolated_vocal_available=False,
            stems_provided=False,
            stem_separation_verified=False,
        )
        as_text = str(plan)

        self.assertFalse(plan["claim_guard"]["acapella_faked"])
        self.assertFalse(plan["claim_guard"]["stems_faked"])
        self.assertIn("not created", as_text)
        self.assertIn("stem separation is not verified", as_text)

    def test_release_package_audio_ready_requires_final_wav_qc_and_checklist(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            final = root / "final.wav"
            write_float_wav(final, [[0.1] * 4800, [0.1] * 4800], 48000, bit_depth=24)
            qc = root / "qc_report.md"
            checklist = root / "release_checklist.md"
            qc.write_text("qc\n", encoding="utf-8")

            missing_checklist = verify_release_package_audio_readiness(
                final_wav_path=final,
                requested_format="wav24_48k",
                qc_report_path=qc,
                release_checklist_path=checklist,
            )
            checklist.write_text("checklist\n", encoding="utf-8")
            ready = release_package_audio_ready(
                final_wav_path=final,
                requested_format="wav24_48k",
                qc_report_path=qc,
                release_checklist_path=checklist,
            )

            self.assertFalse(missing_checklist["release_package_audio_ready"])
            self.assertIn("release checklist missing", " ".join(missing_checklist["blocking_reasons"]))
            self.assertTrue(ready["release_package_audio_ready"])


if __name__ == "__main__":
    unittest.main()

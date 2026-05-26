from __future__ import annotations

import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from export_status import complete_claim_guard, derive_render_status, status_allows_complete  # noqa: E402


class ExportStatusTests(unittest.TestCase):
    def test_status_order_separates_plan_guide_and_final(self) -> None:
        self.assertEqual(derive_render_status(analysis_ready=True), "ANALYSIS_READY")
        self.assertEqual(derive_render_status(arrangement_plan_ready=True), "ARRANGEMENT_PLAN_READY")
        self.assertEqual(derive_render_status(midi_guide_ready=True), "MIDI_GUIDE_READY")
        self.assertEqual(derive_render_status(fallback_exported=True), "FALLBACK_AUDIO_EXPORTED_UNVERIFIED")
        self.assertEqual(derive_render_status(final_wav_exists=True), "FINAL_WAV_EXPORTED_UNVERIFIED")
        self.assertEqual(derive_render_status(final_wav_exists=True, final_wav_verified=True), "FINAL_WAV_EXPORTED_VERIFIED")
        self.assertEqual(derive_render_status(completion_complete=True), "COMPLETE")

    def test_only_complete_status_with_gate_allows_complete_claim(self) -> None:
        self.assertFalse(status_allows_complete("ARRANGEMENT_PLAN_READY"))
        self.assertFalse(status_allows_complete("FINAL_WAV_EXPORTED_VERIFIED"))
        guard = complete_claim_guard("COMPLETE", {"complete": True, "blocking_reasons": []})
        self.assertTrue(guard["complete_allowed"])
        blocked = complete_claim_guard("COMPLETE", {"complete": False, "blocking_reasons": ["QC missing"]})
        self.assertFalse(blocked["complete_allowed"])


if __name__ == "__main__":
    unittest.main()

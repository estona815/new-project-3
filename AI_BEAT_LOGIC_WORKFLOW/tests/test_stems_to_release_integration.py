from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))
sys.path.insert(0, str(PROJECT_ROOT / "tests"))

from completion_gate import check_completion_status  # noqa: E402
from mix_master_autopilot import build_mix_master_plan  # noqa: E402
from stem_mix_autopilot import build_stem_mix_plan  # noqa: E402
from test_release_ready_workflow_integration import write_dummy_wav  # noqa: E402


class StemsToReleaseIntegrationTests(unittest.TestCase):
    def test_stems_to_release_allows_direct_balancing_but_no_fake_plugin_success(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            stems = root / "stems"
            for name, freq in {"drums.wav": 90, "bass.wav": 55, "synth.wav": 330, "vocal.wav": 220}.items():
                write_dummy_wav(stems / name, seconds=2.0, freq=freq)

            stem_plan = build_stem_mix_plan(stems_available=True)
            mix_plan = build_mix_master_plan(input_mode="stems")
            status = check_completion_status(final_wav_path=root / "missing.wav", qc_report_path=root / "missing.md", requested_format="wav24_48k")

            self.assertTrue(stem_plan["more_direct_balancing_allowed"])
            self.assertTrue(mix_plan["stem_chain"]["more_direct_balancing_allowed"])
            self.assertFalse(stem_plan["false_claim_guard"]["plugin_processing_verified"])
            self.assertFalse(mix_plan["false_claim_guards"]["plugin_processing_verified"])
            self.assertFalse(status.complete)


if __name__ == "__main__":
    unittest.main()

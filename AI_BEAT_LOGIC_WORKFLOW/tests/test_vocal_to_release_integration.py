from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))
sys.path.insert(0, str(PROJECT_ROOT / "tests"))

from release_package_builder import build_and_write_release_package  # noqa: E402
from test_release_ready_workflow_integration import clear_rights, write_dummy_wav  # noqa: E402
from vocal_mix_autopilot import build_vocal_mix_chain  # noqa: E402
from vocal_to_code import write_vocal_to_code  # noqa: E402


class VocalToReleaseIntegrationTests(unittest.TestCase):
    def test_vocal_to_release_guides_do_not_claim_autotune_or_decapitator_applied(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            vocal = write_dummy_wav(root / "input" / "vocal.wav", seconds=3.0, freq=246.94)
            write_dummy_wav(root / "input" / "beat.wav", seconds=3.0, freq=110.0)

            paths = write_vocal_to_code(vocal, project_root=root, mode="separate_vocal", requested_pitch_mode="hard_effect")
            vocal_code = json.loads(paths["json"].read_text(encoding="utf-8"))
            chain = build_vocal_mix_chain(input_mode="vocal_plus_beat", pitch_guide=vocal_code.get("pitch_correction_guide"), plugin_capabilities={})
            package = build_and_write_release_package(root, final_master_path=None, metadata={"title": "Draft"}, rights=clear_rights(vocal_performer_consent=True))

            self.assertTrue(paths["json"].exists())
            self.assertTrue(chain["active"])
            self.assertFalse(chain["false_claim_guard"]["auto_tune_applied"])
            self.assertFalse(chain["false_claim_guard"]["decapitator_applied"])
            self.assertIn("generic saturation approximation", chain["saturation"]["plan"])
            self.assertFalse(package["manifest"]["release_ready"])


if __name__ == "__main__":
    unittest.main()

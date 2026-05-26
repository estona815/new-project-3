from __future__ import annotations

import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_DIR))

from vocal_fx_intent import build_vocal_fx_intent  # noqa: E402


class VocalFxIntentTests(unittest.TestCase):
    def test_unavailable_decapitator_uses_manual_instruction_and_generic_fallback(self) -> None:
        intent = build_vocal_fx_intent(
            "보컬을 좀 더 오토튠 걸고 디카페이터 걸어라",
            plugin_availability={"detected": False, "status": "not_detected", "paths": []},
        )
        self.assertTrue(intent["vocal_target_active"])
        self.assertEqual(intent["pitch_correction"]["intensity"], "medium")
        self.assertEqual(intent["saturation"]["requested_plugin"], "Soundtoys Decapitator")
        self.assertEqual(intent["plugin_application"]["status"], "fallback_generic")
        self.assertFalse(intent["plugin_application"]["plugin_exact_application_allowed"])
        self.assertIn("Insert Soundtoys Decapitator", intent["plugin_application"]["manual_logic_instruction"])
        self.assertEqual(intent["plugin_application"]["fallback"], "generic saturation approximation")
        self.assertTrue(intent["deess_required"])
        self.assertFalse(intent["identity_clone_allowed"])

    def test_detected_plugin_still_requires_manual_when_automation_cannot_insert(self) -> None:
        intent = build_vocal_fx_intent(
            "decapitator 빡세게",
            plugin_availability={"detected": True, "status": "detected", "paths": ["/Library/Audio/Plug-Ins/Components/Decapitator.component"]},
            automation_can_insert_plugins=False,
        )
        self.assertEqual(intent["saturation"]["intensity"], "strong")
        self.assertEqual(intent["plugin_application"]["status"], "manual_required")
        self.assertFalse(intent["plugin_application"]["plugin_exact_application_allowed"])
        self.assertIn("manual Logic insertion", intent["plugin_application"]["claim_language"])

    def test_generic_saturation_has_no_false_decapitator_claim(self) -> None:
        intent = build_vocal_fx_intent("보컬 찢어지게 말고 따뜻하게 saturation")
        self.assertIsNone(intent["saturation"]["requested_plugin"])
        self.assertEqual(intent["plugin_application"]["status"], "generic_saturation")
        self.assertIn("generic saturation approximation", intent["plugin_application"]["claim_language"])


if __name__ == "__main__":
    unittest.main()

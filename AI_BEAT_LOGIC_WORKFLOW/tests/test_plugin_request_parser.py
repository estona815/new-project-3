from __future__ import annotations

import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_DIR))

from plugin_request_parser import parse_plugin_requests  # noqa: E402
from vocal_fx_intent import build_vocal_fx_intent  # noqa: E402


class PluginRequestParserTests(unittest.TestCase):
    def test_pitch_correction_variants_map_to_intensity(self) -> None:
        cases = {
            "오토튠": "medium",
            "auto tune": "medium",
            "autotune": "medium",
            "하드튠": "hard_effect",
            "튠 세게": "hard_effect",
            "피치 보정": "medium",
            "로봇틱하게": "hard_effect",
            "자연스럽게 튠": "subtle",
        }
        for phrase, expected in cases.items():
            with self.subTest(phrase=phrase):
                parsed = parse_plugin_requests(phrase)
                self.assertTrue(parsed["pitch_correction"]["requested"])
                self.assertEqual(parsed["pitch_correction"]["intensity"], expected)

    def test_decapitator_typo_variants_request_soundtoys_plugin(self) -> None:
        for phrase in ("디카페이터", "데카피테이터", "Decapitator", "사운드토이즈"):
            with self.subTest(phrase=phrase):
                parsed = parse_plugin_requests(phrase)
                self.assertTrue(parsed["saturation"]["requested"])
                self.assertEqual(parsed["saturation"]["requested_plugin"], "Soundtoys Decapitator")
                self.assertIn("Soundtoys Decapitator", parsed["requested_plugins"])

    def test_saturation_shape_fields_are_normalized(self) -> None:
        parsed = parse_plugin_requests("보컬에 살짝 디스토션 걸고 따뜻하게")
        saturation = parsed["saturation"]
        self.assertEqual(saturation["effect"], "saturation")
        self.assertEqual(saturation["intensity"], "subtle")
        self.assertEqual(saturation["parallel_mix"], "low")
        self.assertEqual(saturation["tone"], "dark")
        self.assertEqual(saturation["apply_to"], "lead_vocal")

    def test_decapitator_claim_language_depends_on_availability_and_insertability(self) -> None:
        unavailable = build_vocal_fx_intent(
            "보컬을 좀 더 오토튠 걸고 디카페이터 걸어라",
            plugin_availability={"detected": False, "status": "not_detected"},
        )
        self.assertEqual(unavailable["plugin_application"]["status"], "fallback_generic")
        self.assertIn("do not claim Decapitator applied", unavailable["plugin_application"]["claim_language"])
        self.assertEqual(unavailable["plugin_application"]["fallback"], "generic saturation approximation")

        detected_manual = build_vocal_fx_intent(
            "보컬을 좀 더 오토튠 걸고 디카페이터 걸어라",
            plugin_availability={"detected": True, "status": "detected"},
            automation_can_insert_plugins=False,
        )
        self.assertEqual(detected_manual["plugin_application"]["status"], "manual_required")
        self.assertIn("manual Logic insertion is required", detected_manual["plugin_application"]["claim_language"])

        insertable = build_vocal_fx_intent(
            "보컬을 좀 더 오토튠 걸고 디카페이터 걸어라",
            plugin_availability={"detected": True, "status": "detected"},
            automation_can_insert_plugins=True,
        )
        self.assertEqual(insertable["plugin_application"]["status"], "verified_insert_possible")
        self.assertTrue(insertable["plugin_application"]["plugin_exact_application_allowed"])


if __name__ == "__main__":
    unittest.main()

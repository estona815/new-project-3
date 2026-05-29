from __future__ import annotations

import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class TuneEqSubstituteTests(unittest.TestCase):
    def test_required_jsfx_have_desc_and_code_sections(self) -> None:
        for rel in [
            "reaper/jsfx/codex_vocal_pitch_monitor.jsfx",
            "reaper/jsfx/codex_pro_dynamic_ms_eq.jsfx",
        ]:
            text = (ROOT / rel).read_text(encoding="utf-8")
            self.assertIn("desc:", text)
            self.assertIn("@sample", text)
            self.assertNotIn("\x00", text)

    def test_substitute_profile_blocks_overclaiming(self) -> None:
        profile = json.loads((ROOT / "presets/tune_eq_substitute/vocal_clean_default.json").read_text(encoding="utf-8"))

        self.assertEqual(profile["pitch_route"]["engine"], "ReaTune")
        self.assertTrue(profile["pitch_route"]["requires_isolated_vocal"])
        self.assertIn("Do not claim vocal tuned", profile["pitch_route"]["claim_policy"])
        self.assertEqual(profile["dynamic_eq_route"]["engine"], "codex_pro_dynamic_ms_eq.jsfx")

    def test_reascript_reports_claim_policy_and_reaper_stock_engine(self) -> None:
        text = (ROOT / "scripts/apply_codex_tune_eq_substitute.lua").read_text(encoding="utf-8")

        self.assertIn("ReaTune", text)
        self.assertIn("codex_pro_dynamic_ms_eq.jsfx", text)
        self.assertIn("Do not claim Antares-quality tuning", text)

    def test_installer_lists_new_substitute_plugins(self) -> None:
        text = (ROOT / "scripts/install_codex_reaper_substitutes.py").read_text(encoding="utf-8")

        self.assertIn("codex_pro_dynamic_ms_eq.jsfx", text)
        self.assertIn("codex_vocal_pitch_monitor.jsfx", text)
        self.assertIn("codex_fresh_mix", text)

    def test_reaper_smoke_script_loads_expected_names(self) -> None:
        text = (ROOT / "scripts/smoke_codex_tune_eq_substitute.lua").read_text(encoding="utf-8")

        self.assertIn("codex_vocal_pitch_monitor.jsfx", text)
        self.assertIn("codex_pro_dynamic_ms_eq.jsfx", text)
        self.assertIn("ReaTune", text)


if __name__ == "__main__":
    unittest.main()

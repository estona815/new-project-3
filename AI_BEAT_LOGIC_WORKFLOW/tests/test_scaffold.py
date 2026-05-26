from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_DIR))

from config import load_defaults
from paths import REQUIRED_DIRECTORIES, ensure_folder_structure
from user_options import options_from_questionnaire, parse_bool, validate_input_path


class ScaffoldTests(unittest.TestCase):
    def test_defaults_are_loaded(self) -> None:
        defaults = load_defaults()
        self.assertEqual(defaults["length_mode"], "under_2min")
        self.assertEqual(defaults["vocal_mode"], "suppress")
        self.assertEqual(defaults["melody_focus"], "front")
        self.assertEqual(defaults["drum_808"], "strong_controlled")
        self.assertEqual(defaults["export_format"], "wav24_48k")
        self.assertIs(defaults["save_logic_project"], True)
        self.assertEqual(defaults["mode"], "instrumental_beat")
        self.assertEqual(defaults["vocal_style"], "polished")

    def test_folder_structure_is_created(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ensure_folder_structure(root)
            for relative in REQUIRED_DIRECTORIES:
                self.assertTrue((root / relative).is_dir(), relative)

    def test_boolean_parser_accepts_cli_values(self) -> None:
        self.assertTrue(parse_bool("true", False))
        self.assertFalse(parse_bool("false", True))

    def test_missing_dummy_input_is_a_warning_not_a_crash_condition(self) -> None:
        exists, warnings = validate_input_path("dummy.wav")
        self.assertFalse(exists)
        self.assertIn("Input path does not exist", " ".join(warnings))

    def test_help_command_works(self) -> None:
        result = subprocess.run(
            ["python3", str(PROJECT_ROOT / "src" / "main.py"), "--help"],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("--interactive", result.stdout)
        self.assertIn("--workflow", result.stdout)
        self.assertIn("--rough-request", result.stdout)
        self.assertIn("--release-ready", result.stdout)
        self.assertIn("--target-deliverable", result.stdout)
        self.assertIn("--release-profile", result.stdout)
        self.assertIn("--metadata-title", result.stdout)
        self.assertIn("--owned-samples", result.stdout)
        self.assertIn("--rescue-mode", result.stdout)
        self.assertIn("--generate-lead", result.stdout)
        self.assertIn("--demote-vocal-texture", result.stdout)
        self.assertIn("--target-length", result.stdout)
        self.assertIn("--style-cluster", result.stdout)

    def test_interactive_questionnaire_writes_creative_brief(self) -> None:
        defaults = load_defaults()
        answers = iter(
            [
                "vocal + beat",
                "/tmp/main.wav",
                "/tmp/beat.wav",
                "/tmp/vocal.wav",
                "",
                "",
                "",
                "bright emotional digicore",
                "",
                "false",
                "false",
                "under_2min",
                "bright emotional digicore",
                "lead vocal clarity",
                "muddy 808, harsh sibilance",
                "rap upfront",
                "hard but controlled",
                "",
                "master-ready headroom",
                "WAV 24-bit 48kHz",
                "false",
            ]
        )
        with tempfile.TemporaryDirectory() as tmp:
            project_root = Path(tmp) / "AI_BEAT_LOGIC_WORKFLOW"
            with mock.patch("builtins.input", side_effect=lambda _prompt: next(answers)):
                options = options_from_questionnaire(defaults, project_root=project_root)

            brief_json = project_root / "02_EDIT_PLAN" / "creative_brief.json"
            brief_md = project_root / "02_EDIT_PLAN" / "creative_brief.md"
            self.assertTrue(brief_json.exists())
            self.assertTrue(brief_md.exists())
            self.assertEqual(options.mode, "vocal_plus_beat")
            self.assertEqual(options.creative_brief["priority"], "lead vocal clarity")
            self.assertIn("bright emotional digicore", brief_md.read_text(encoding="utf-8"))

    def test_dummy_input_command_gives_clean_error(self) -> None:
        error_path = PROJECT_ROOT / "01_ANALYSIS" / "conversion_error.md"
        capabilities_path = PROJECT_ROOT / "01_ANALYSIS" / "dependency_capabilities.json"
        if error_path.exists():
            error_path.unlink()
        if capabilities_path.exists():
            capabilities_path.unlink()
        result = subprocess.run(
            ["python3", str(PROJECT_ROOT / "src" / "main.py"), "--input", "dummy.wav"],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("Conversion failed", result.stdout)
        self.assertIn("No converted working WAV is being claimed", result.stdout)
        self.assertTrue(error_path.exists())
        error_path.unlink()
        if capabilities_path.exists():
            capabilities_path.unlink()


if __name__ == "__main__":
    unittest.main()

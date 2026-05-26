from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_DIR))

from config import load_defaults  # noqa: E402
from user_options import options_from_questionnaire  # noqa: E402


class InteractiveCreativeBriefTests(unittest.TestCase):
    def test_interactive_mode_captures_full_brief(self) -> None:
        answers = iter(
            [
                "stems",
                "/tmp/main.wav",
                "/tmp/beat.wav",
                "/tmp/lead.wav",
                "/tmp/adlibs.wav",
                "/tmp/backing.wav",
                "/tmp/stems",
                "웨스트우드 Just Touched Down 베이스랑 킥 느낌, 보컬 오토튠 더, 디카페이터 살짝, 2hollis/ycs/SYSTEM SEOUL처럼, 신디 넓게.",
                "/tmp/ref.wav",
                "no",
                "yes",
                "specific section",
                "0:12",
                "0:42",
                "웨스트우드 질감만",
                "bass",
                "muddy 808, harsh vocal",
                "Decapitator subtle",
                "reference-inspired energetic digital drums",
                "2hollis, ycs, SYSTEM SEOUL",
                "loud demo",
                "WAV 24-bit 48kHz",
                "yes",
            ]
        )
        with tempfile.TemporaryDirectory() as tmp:
            project_root = Path(tmp) / "AI_BEAT_LOGIC_WORKFLOW"
            with mock.patch("builtins.input", side_effect=lambda _prompt: next(answers)):
                options = options_from_questionnaire(load_defaults(), project_root=project_root)

            brief_path = project_root / "02_EDIT_PLAN" / "creative_brief.json"
            md_path = project_root / "02_EDIT_PLAN" / "creative_brief.md"
            brief_exists = brief_path.exists()
            md_exists = md_path.exists()
            brief = json.loads(brief_path.read_text(encoding="utf-8"))
            markdown = md_path.read_text(encoding="utf-8")

        self.assertEqual(options.mode, "stems")
        self.assertEqual(brief["input_files"]["stems_folder"], "/tmp/stems")
        self.assertEqual(brief["reference_audio"], "/tmp/ref.wav")
        self.assertEqual(brief["input_files"]["reference_audio"], "/tmp/ref.wav")
        self.assertIn("웨스트우드 Just Touched Down", brief["raw_full_korean_request"])
        self.assertEqual(brief["vocal_fx_text"], "Decapitator subtle")
        self.assertEqual(brief["style_cluster_text"], "2hollis, ycs, SYSTEM SEOUL")
        self.assertFalse(brief["owned_reference_sample"])
        self.assertTrue(brief["owned_reference_stems"])
        self.assertEqual(brief["length"], {"mode": "specific_section", "start": "0:12", "end": "0:42"})
        self.assertEqual(brief["creative_target"], "웨스트우드 질감만")
        self.assertEqual(brief["drum_808_direction"], "reference_inspired_energetic_digital_drums")
        self.assertTrue(brief["save_logic_project"])
        self.assertIn("target feeling", markdown)
        self.assertIn("raw request", markdown)
        self.assertIn("Copy / Sampling Policy", markdown)
        self.assertIn("Logic project preference: save", markdown)

    def test_interactive_mode_handles_blank_values_with_defaults(self) -> None:
        answers = iter([""] * 21)
        with tempfile.TemporaryDirectory() as tmp:
            project_root = Path(tmp) / "AI_BEAT_LOGIC_WORKFLOW"
            with mock.patch("builtins.input", side_effect=lambda _prompt: next(answers)):
                options = options_from_questionnaire(load_defaults(), project_root=project_root)

            brief_path = project_root / "02_EDIT_PLAN" / "creative_brief.json"
            md_path = project_root / "02_EDIT_PLAN" / "creative_brief.md"
            brief_exists = brief_path.exists()
            md_exists = md_path.exists()
            brief = json.loads(brief_path.read_text(encoding="utf-8"))
            markdown = md_path.read_text(encoding="utf-8")

        self.assertEqual(options.mode, "instrumental_beat")
        self.assertEqual(brief["mode"], "instrumental_beat")
        self.assertEqual(brief["length"]["mode"], "under_2min")
        self.assertEqual(brief["priority"], "melody")
        self.assertEqual(brief["drum_808_direction"], "strong_controlled")
        self.assertEqual(brief["master_direction"], "master_ready_headroom")
        self.assertEqual(brief["export_format"], "wav24_48k")
        self.assertTrue(brief["save_logic_project"])
        self.assertEqual(brief["raw_full_korean_request"], "")
        self.assertFalse(brief["owned_reference_sample"])
        self.assertTrue(brief_exists)
        self.assertTrue(md_exists)
        self.assertIn("export: wav24_48k", markdown)


if __name__ == "__main__":
    unittest.main()

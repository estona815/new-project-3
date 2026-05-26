from __future__ import annotations

import json
import sys
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_DIR))

from config import load_defaults  # noqa: E402
from paths import ensure_folder_structure  # noqa: E402
from user_options import options_from_args  # noqa: E402
from vocal_mix_master import run_vocal_mix_master_extension  # noqa: E402


def namespace(**overrides: object) -> Namespace:
    values = {
        "input": None,
        "length_mode": None,
        "vocal_mode": None,
        "melody_focus": None,
        "drum_808": None,
        "export_format": None,
        "save_logic_project": None,
        "mode": None,
        "vocal_file": None,
        "beat_file": None,
        "lead_vocal_file": None,
        "adlib_file": None,
        "backing_vocal_file": None,
        "reference_audio": None,
        "reference_text": None,
        "vocal_style": None,
        "mix_intensity": None,
        "master_loudness": None,
        "autotune": None,
        "deess": None,
        "reverb_space": None,
        "delay_style": None,
    }
    values.update(overrides)
    return Namespace(**values)


class VocalMixMasterTests(unittest.TestCase):
    def test_vocal_file_infers_vocal_plus_beat_mode(self) -> None:
        defaults = load_defaults()
        args = namespace(vocal_file="/tmp/vocal.wav", beat_file="/tmp/beat.wav")

        options = options_from_args(args, defaults)

        self.assertEqual(options.mode, "vocal_plus_beat")
        self.assertEqual(options.input_path, "/tmp/beat.wav")

    def test_full_song_stereo_logs_stereo_only_limits(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_root = Path(tmp) / "AI_BEAT_LOGIC_WORKFLOW"
            ensure_folder_structure(project_root)
            options = {
                "mode": "full_song_stereo",
                "vocal_style": "polished",
                "mix_intensity": "standard",
                "master_loudness": "master_ready_headroom",
                "autotune": "subtle",
                "deess": "medium",
                "reverb_space": "plate",
                "delay_style": "throw_only",
                "reference_text": "bright emotional hyperpop, clean but hard 808",
            }

            paths = run_vocal_mix_master_extension(options, project_root)
            log = paths["vocal_processing_log"].read_text(encoding="utf-8")
            style = paths["style_translation"].read_text(encoding="utf-8")
            analysis = json.loads(paths["vocal_analysis"].read_text(encoding="utf-8"))

            self.assertIn("stereo-only broad processing", log)
            self.assertIn("No real vocal removal from stereo is claimed", log)
            self.assertIn("No professional stem-level vocal mixing", log)
            self.assertIn("does not copy an exact reference song", style)
            self.assertEqual(analysis["processing_scope"], "stereo-only broad mastering and heuristic vocal-region analysis")

    def test_separate_vocal_mode_records_precise_scope_without_render_claim(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_root = Path(tmp) / "AI_BEAT_LOGIC_WORKFLOW"
            vocal = Path(tmp) / "lead.wav"
            beat = Path(tmp) / "beat.wav"
            vocal.write_bytes(b"placeholder")
            beat.write_bytes(b"placeholder")
            ensure_folder_structure(project_root)
            options = {
                "mode": "vocal_plus_beat",
                "vocal_file": str(vocal),
                "beat_file": str(beat),
                "vocal_style": "rap_forward",
                "mix_intensity": "bold",
                "master_loudness": "loud_demo",
                "autotune": "hard_effect",
                "deess": "strong",
                "reverb_space": "dry",
                "delay_style": "throw_only",
            }

            paths = run_vocal_mix_master_extension(options, project_root)
            analysis = json.loads(paths["vocal_analysis"].read_text(encoding="utf-8"))
            log = paths["vocal_processing_log"].read_text(encoding="utf-8")

            self.assertEqual(analysis["processing_scope"], "separate vocal plus beat processing")
            self.assertTrue(analysis["files"]["vocal_file"]["exists"])
            self.assertIn("actual separate vocal processing", log)
            self.assertIn("not rendered", log)


if __name__ == "__main__":
    unittest.main()

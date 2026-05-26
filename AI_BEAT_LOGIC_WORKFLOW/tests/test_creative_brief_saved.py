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

from creative_brief import build_creative_brief, write_creative_brief_files  # noqa: E402
from config import load_defaults  # noqa: E402
from user_options import options_from_args  # noqa: E402


def namespace(**overrides: object) -> Namespace:
    values = {
        "input": None,
        "length_mode": None,
        "length_start": None,
        "length_end": None,
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
        "stems_folder": None,
        "reference_audio": None,
        "reference_text": None,
        "creative_target_text": None,
        "owned_reference_sample": None,
        "owned_reference_stems": None,
        "vocal_fx_text": None,
        "drum_bass_request_text": None,
        "style_cluster_text": None,
        "vocal_style": None,
        "mix_intensity": None,
        "master_loudness": None,
        "autotune": None,
        "deess": None,
        "reverb_space": None,
        "delay_style": None,
        "creative_target": None,
        "priority": None,
        "avoid_list": None,
        "vocal_direction": None,
        "drum_808_direction": None,
        "master_direction": None,
        "workflow": None,
        "rough_request": None,
        "arrangement_autopilot": False,
        "arrangement_sample_file": None,
        "arrangement_vocal_file": None,
        "arrangement_genre": None,
    }
    values.update(overrides)
    return Namespace(**values)


class CreativeBriefSavedTests(unittest.TestCase):
    def test_write_creative_brief_json_and_markdown_schema(self) -> None:
        brief = build_creative_brief(
            mode="vocal + beat",
            main_input="/tmp/main.wav",
            beat_file="/tmp/beat.wav",
            lead_vocal_file="/tmp/lead.wav",
            adlibs_file=None,
            backing_vocal_file=None,
            stems_folder=None,
            reference_audio=None,
            length_mode="specific section",
            length_start="0:30",
            length_end="1:00",
            creative_target="ㅇㅇㅇ이라는 곡 베이스처럼 쳐줘",
            priority="808/bass",
            avoid="muddy 808, overcompressed master",
            vocal_direction="rap upfront",
            drum_808_direction="strong controlled",
            master_direction="streaming-safe",
            export_format="WAV 24-bit 44.1kHz",
            save_logic_project=False,
            raw_full_korean_request="ㅇㅇㅇ이라는 곡 베이스처럼 쳐줘",
            creative_target_text="ㅇㅇㅇ이라는 곡 베이스처럼 쳐줘",
            vocal_fx_text="",
            drum_bass_request_text="베이스처럼",
            style_cluster_text="",
            owned_reference_sample=False,
            owned_reference_stems=False,
        )
        with tempfile.TemporaryDirectory() as tmp:
            paths = write_creative_brief_files(brief, Path(tmp))
            parsed = json.loads(paths["json"].read_text(encoding="utf-8"))
            markdown = paths["markdown"].read_text(encoding="utf-8")

        self.assertEqual(parsed["mode"], "vocal_plus_beat")
        self.assertEqual(parsed["length"]["mode"], "specific_section")
        self.assertEqual(parsed["length"]["start"], "0:30")
        self.assertEqual(parsed["export_format"], "wav24_44k")
        self.assertEqual(parsed["priority"], "808/bass")
        self.assertEqual(parsed["creative_target"], "ㅇㅇㅇ이라는 곡 베이스처럼 쳐줘")
        self.assertEqual(parsed["raw_full_korean_request"], "ㅇㅇㅇ이라는 곡 베이스처럼 쳐줘")
        self.assertFalse(parsed["owned_reference_sample"])
        self.assertEqual(parsed["avoid"], ["muddy 808", "overcompressed master"])
        self.assertIn("target feeling", markdown)
        self.assertIn("avoid list: muddy 808, overcompressed master", markdown)
        self.assertIn("export: wav24_44k", markdown)
        self.assertIn("Text-only reference requests are treated as low-confidence", markdown)
        self.assertIn("Copy / Sampling Policy", markdown)
        self.assertIn("exact copy allowed: false", markdown)

    def test_non_interactive_args_capture_creative_target(self) -> None:
        args = namespace(
            input="/tmp/main.wav",
            creative_target_text="웨스트우드 Just Touched Down 베이스랑 킥 느낌. 따오는 건 아니고 질감만.",
            vocal_fx_text="보컬 오토튠 더 걸고 디카페이터 살짝",
            style_cluster_text="2hollis, ycs, SYSTEM SEOUL 쪽인데 cheap rage clipping은 피하기",
            priority="drums",
            avoid_list="cheap rage clipping",
            drum_808_direction="reference-inspired energetic digital drums",
            master_direction="loud demo",
            owned_reference_sample="false",
            owned_reference_stems="false",
        )

        options = options_from_args(args, load_defaults())

        self.assertIsNotNone(options.creative_brief)
        self.assertIn("웨스트우드 Just Touched Down", options.creative_brief["raw_full_korean_request"])
        self.assertIn("디카페이터 살짝", options.reference_text)
        self.assertEqual(options.creative_brief["vocal_fx_text"], "보컬 오토튠 더 걸고 디카페이터 살짝")
        self.assertEqual(options.creative_brief["priority"], "drums")
        self.assertIn("cheap rage clipping", options.creative_brief["avoid"])

    def test_owned_reference_flags_are_stored_for_copying_policy(self) -> None:
        args = namespace(
            input="/tmp/main.wav",
            creative_target_text="킥을 따와라",
            reference_audio="/tmp/owned_kick.wav",
            owned_reference_sample="true",
            owned_reference_stems="false",
        )

        options = options_from_args(args, load_defaults())

        self.assertTrue(options.creative_brief["owned_reference_sample"])
        self.assertFalse(options.creative_brief["owned_reference_stems"])
        self.assertTrue(options.creative_brief["ownership_flags"]["user_confirms_owned_or_licensed"])

    def test_release_metadata_and_ownership_flags_are_stored(self) -> None:
        args = namespace(
            input="/tmp/song.wav",
            workflow="song_to_release",
            rough_request="발매용으로 믹마까지.",
            release_ready="true",
            target_deliverable="release_package",
            metadata_title="Track",
            metadata_artist="Artist",
            metadata_version="single",
            metadata_genre="hyperpop",
            metadata_language="ko",
            metadata_explicit="false",
            metadata_isrc="",
            metadata_upc="",
            metadata_copyright_year="2026",
            metadata_copyright_owner="Artist",
            metadata_producer="Producer",
            metadata_composer="Composer",
            metadata_lyricist="Lyricist",
            owned_samples="true",
            owned_stems="true",
            owned_vocals="true",
        )

        options = options_from_args(args, load_defaults())
        brief = options.creative_brief or {}

        self.assertEqual(options.release_metadata["title"], "Track")
        self.assertEqual(options.release_metadata["copyright_year"], "2026")
        self.assertEqual(options.release_metadata["explicit"], False)
        self.assertTrue(options.owned_samples)
        self.assertTrue(options.owned_stems)
        self.assertTrue(options.owned_vocals)
        self.assertEqual(brief["release_metadata"]["artist"], "Artist")
        self.assertTrue(brief["ownership_flags"]["user_owned_sample"])
        self.assertTrue(brief["ownership_flags"]["user_owned_stem"])
        self.assertTrue(brief["ownership_flags"]["user_owned_vocal"])

    def test_autopilot_workflow_aliases_capture_rough_request(self) -> None:
        args = namespace(
            input="/tmp/sample.wav",
            workflow="sample_to_arrangement",
            rough_request="이 샘플로 ycs/SYSTEM SEOUL 결 디지코어 비트 짜줘.",
            length_mode="reels_15sec",
        )

        options = options_from_args(args, load_defaults())

        self.assertEqual(options.workflow, "sample_to_arrangement")
        self.assertTrue(options.arrangement_autopilot)
        self.assertEqual(options.length_mode, "reels_15sec")
        self.assertIn("SYSTEM SEOUL", options.reference_text)
        self.assertEqual(options.creative_brief["creative_target"], options.rough_request)

    def test_song_workflow_alias_sets_full_song_stereo_mode(self) -> None:
        args = namespace(
            input="/tmp/song.wav",
            workflow="song_to_mix_master",
            rough_request="상업 음악 퀄로 디지코어/하이퍼팝 결.",
        )

        options = options_from_args(args, load_defaults())

        self.assertEqual(options.workflow, "song_to_mix_master")
        self.assertEqual(options.mode, "full_song_stereo")


if __name__ == "__main__":
    unittest.main()

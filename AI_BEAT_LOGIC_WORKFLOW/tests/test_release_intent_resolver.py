from __future__ import annotations

import argparse
import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from release_intent_resolver import build_release_intent  # noqa: E402
from user_options import options_from_args  # noqa: E402


def base_args(**overrides: object) -> argparse.Namespace:
    values = {
        "input": "/tmp/song.wav",
        "workflow": None,
        "rough_request": "",
        "rescue_mode": None,
        "generate_lead": None,
        "demote_vocal_texture": None,
        "target_length": None,
        "style_cluster": None,
        "release_ready": None,
        "zero_clarification": None,
        "target_deliverable": None,
        "release_profile": None,
        "length_mode": None,
        "vocal_mode": None,
        "melody_focus": None,
        "drum_808": None,
        "export_format": "wav24_48k",
        "save_logic_project": None,
        "mode": None,
        "vocal_file": None,
        "beat_file": None,
        "lead_vocal_file": None,
        "adlib_file": None,
        "backing_vocal_file": None,
        "stems_folder": None,
        "reference_audio": None,
        "sample_folder": None,
        "reference_text": None,
        "creative_target_text": None,
        "owned_reference_sample": None,
        "owned_reference_stems": None,
        "owned_samples": None,
        "owned_stems": None,
        "owned_vocals": None,
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
        "length_start": None,
        "length_end": None,
        "arrangement_autopilot": False,
        "arrangement_sample_file": None,
        "arrangement_vocal_file": None,
        "arrangement_genre": None,
        "metadata_title": None,
        "metadata_artist": None,
        "metadata_version": None,
        "metadata_genre": None,
        "metadata_language": None,
        "metadata_explicit": None,
        "metadata_isrc": None,
        "metadata_upc": None,
        "metadata_copyright_year": None,
        "metadata_copyright_owner": None,
        "metadata_producer": None,
        "metadata_composer": None,
        "metadata_lyricist": None,
    }
    values.update(overrides)
    return argparse.Namespace(**values)


class ReleaseIntentResolverTests(unittest.TestCase):
    def test_messy_korean_sentence_launches_release_package_workflow(self) -> None:
        intent = build_release_intent(
            rough_request="마음대로 상업 음악 퀄로 디지코어/하이퍼팝 결. 보컬 앞으로, 808 강하게, 릴스 훅, 믹마까지.",
            workflow="song_to_release",
            mode="full_song_stereo",
            release_ready=True,
            zero_clarification=True,
            target_deliverable="release_package",
            release_profile="commercial_digicore",
        )

        self.assertEqual(intent["workflow"], "song_to_release")
        self.assertEqual(intent["style_cluster"], "commercial_digicore")
        self.assertEqual(intent["final_length"], "15sec_reels")
        self.assertEqual(intent["priority"], "hook")
        self.assertEqual(intent["target_deliverable"], "release_package")
        self.assertEqual(intent["mix_master_target"], "streaming_safe")
        self.assertIn("verified_final_wav", intent["deliverables_requested"])
        self.assertIn("release_qc_report", intent["deliverables_requested"])
        self.assertIn("hook appears early", intent["assumptions"])
        self.assertIn("no exact-copy", " ".join(intent["safety_blocks"]))
        self.assertFalse(intent["parsed_reference_intent"]["vocal_identity_clone_allowed"])

    def test_user_options_writes_release_fields_into_creative_brief(self) -> None:
        args = base_args(
            workflow="song_to_release",
            rough_request="마음대로 상업 음악 퀄로 디지코어/하이퍼팝 결. 보컬 앞으로, 808 강하게, 릴스 훅, 믹마까지.",
            release_ready="true",
            zero_clarification="true",
            target_deliverable="release_package",
            release_profile="commercial_digicore",
        )

        options = options_from_args(
            args,
            {
                "save_logic_project": False,
                "mode": "instrumental_beat",
                "vocal_style": "polished",
                "mix_intensity": "standard",
                "master_loudness": "master_ready_headroom",
                "autotune": "subtle",
                "deess": "medium",
                "reverb_space": "plate",
                "delay_style": "throw_only",
                "drum_808": "strong_controlled",
                "length_mode": "under_2min",
                "export_format": "wav24_48k",
                "vocal_mode": "suppress",
                "melody_focus": "front",
            },
        )

        brief = options.creative_brief or {}
        self.assertEqual(options.workflow, "song_to_release")
        self.assertTrue(options.release_ready)
        self.assertTrue(options.zero_clarification)
        self.assertEqual(options.target_deliverable, "release_package")
        self.assertEqual(brief["rough_request"], args.rough_request)
        self.assertTrue(brief["release_ready"])
        self.assertTrue(brief["zero_clarification"])
        self.assertEqual(brief["target_deliverable"], "release_package")
        self.assertEqual(brief["workflow"], "song_to_release")
        self.assertEqual(brief["style_cluster"], "commercial_digicore")
        self.assertIn("release_qc_report", brief["deliverables_requested"])
        self.assertGreater(len(brief["assumptions"]), 0)

    def test_bad_ai_song_rescue_resolves_to_plan_ready_workflow(self) -> None:
        intent = build_release_intent(
            rough_request="Bad AI song rescue: hook 없고 보컬 이상하고 구조 다시 짜",
            workflow="bad_ai_song_rescue",
            mode="full_song_stereo",
            target_deliverable="demo",
        )

        self.assertEqual(intent["workflow"], "bad_ai_song_rescue")
        self.assertIn("bad_song_diagnosis", intent["deliverables_requested"])
        self.assertIn("rescue_arrangement_plan", intent["deliverables_requested"])

        options = options_from_args(
            base_args(
                workflow="bad_ai_song_rescue",
                rough_request="Bad AI song rescue: hook 없고 보컬 이상하고 구조 다시 짜",
                sample_folder="/tmp/samples",
                rescue_mode="final",
                generate_lead="true",
                demote_vocal_texture="true",
                target_length="under_2min",
                style_cluster="system_seoul_adjacent",
                owned_samples="true",
            ),
            {
                "save_logic_project": False,
                "mode": "instrumental_beat",
                "vocal_style": "polished",
                "mix_intensity": "standard",
                "master_loudness": "master_ready_headroom",
                "autotune": "subtle",
                "deess": "medium",
                "reverb_space": "plate",
                "delay_style": "throw_only",
                "drum_808": "strong_controlled",
                "length_mode": "under_2min",
                "export_format": "wav24_48k",
                "vocal_mode": "suppress",
                "melody_focus": "front",
            },
        )

        self.assertEqual(options.workflow, "bad_ai_song_rescue")
        self.assertEqual(options.mode, "full_song_stereo")
        self.assertEqual(options.sample_folder, "/tmp/samples")
        self.assertEqual(options.rescue_mode, "final")
        self.assertTrue(options.generate_lead)
        self.assertTrue(options.demote_vocal_texture)
        self.assertEqual(options.target_length, "under_2min")
        self.assertEqual(options.style_cluster, "system_seoul_adjacent")
        self.assertTrue(options.owned_samples)
        self.assertFalse(options.arrangement_autopilot)


if __name__ == "__main__":
    unittest.main()

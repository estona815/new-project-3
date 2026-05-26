from __future__ import annotations

import json
import math
import sys
import tempfile
import unittest
import wave
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_DIR))

from edit_plan_generator import build_edit_plan  # noqa: E402
from paths import ensure_folder_structure  # noqa: E402
from qc_report import build_qc_report  # noqa: E402
from reference_copying_policy import evaluate_copying_request  # noqa: E402
from reference_intent_parser import parse_reference_intent  # noqa: E402
from reference_profile import build_reference_target_profile  # noqa: E402
from style_translation import run_reference_targeting  # noqa: E402


def write_wav(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(48000)
        for index in range(4800):
            value = int(math.sin(2.0 * math.pi * 100.0 * index / 48000) * 8000)
            wav_file.writeframesraw(value.to_bytes(2, "little", signed=True))


class ReferenceCopyingPolicyTests(unittest.TestCase):
    def test_take_kick_blocks_sample_extraction_without_owned_file(self) -> None:
        parsed = parse_reference_intent("웨스트우드 Just Touched Down 킥 따와")
        policy = evaluate_copying_request(parsed, {}, {})

        self.assertTrue(policy["copying_requested"])
        self.assertFalse(policy["exact_copy_allowed"])
        self.assertTrue(policy["requires_user_owned_source"])
        self.assertIn("high_level_trait_match", policy["allowed_actions"])
        self.assertNotIn("sample_layering", policy["allowed_actions"])
        self.assertIn("extract_kick_sample", policy["disallowed_actions"])
        self.assertIn("제공/소유 확인된 샘플이 없으므로", policy["report_note"])

    def test_owned_local_sample_allows_sample_layering_only_from_that_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            sample = Path(tmp) / "owned_kick.wav"
            write_wav(sample)
            parsed = parse_reference_intent("킥을 따와라")

            policy = evaluate_copying_request(
                parsed,
                {"owned_sample": str(sample)},
                {"user_owned_sample": True, "sample_cleared": True},
            )

        self.assertTrue(policy["copying_requested"])
        self.assertTrue(policy["exact_copy_allowed"])
        self.assertFalse(policy["requires_user_owned_source"])
        self.assertIn("sample_layering", policy["allowed_actions"])
        self.assertIn("download_reference_audio", policy["disallowed_actions"])
        self.assertNotIn("copy_exact_pattern", policy["allowed_actions"])
        self.assertIn("owned/licensed local source", policy["reason"])
        self.assertIn("제공 파일 안에서만", policy["report_note"])

    def test_reference_audio_without_ownership_stays_broad_analysis_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            reference = Path(tmp) / "reference.wav"
            write_wav(reference)
            parsed = parse_reference_intent("저 곡 808 그대로", reference_audio_available=True)

            policy = evaluate_copying_request(parsed, {"reference_audio": str(reference)}, {})

        self.assertTrue(policy["copying_requested"])
        self.assertFalse(policy["exact_copy_allowed"])
        self.assertIn("broad_audio_analysis", policy["allowed_actions"])
        self.assertIn("extract_bassline", policy["disallowed_actions"])

    def test_profile_and_style_translation_include_copying_policy_note(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_root = Path(tmp) / "AI_BEAT_LOGIC_WORKFLOW"
            ensure_folder_structure(project_root)
            paths = run_reference_targeting(
                {"reference_text": "웨스트우드 Just Touched Down 킥 따와"},
                project_root,
            )
            profile = json.loads(paths["reference_target_profile"].read_text(encoding="utf-8"))
            translation = paths["style_translation"].read_text(encoding="utf-8")

        self.assertTrue(profile["copying_policy"]["copying_requested"])
        self.assertFalse(profile["copying_policy"]["exact_copy_allowed"])
        self.assertIn("Copying Policy", translation)
        self.assertIn("정확한 킥/베이스 샘플 복사가 아니라", translation)
        self.assertIn("extract_kick_sample", translation)

    def test_owned_sample_in_creative_brief_enables_policy_sample_layering(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            sample = Path(tmp) / "owned_kick.wav"
            write_wav(sample)
            profile = build_reference_target_profile(
                "킥을 따와라",
                None,
                {
                    "provided_files": {"owned_sample": str(sample)},
                    "ownership_flags": {"user_owned_sample": True, "sample_cleared": True},
                },
            )

        self.assertTrue(profile["copying_policy"]["exact_copy_allowed"])
        self.assertIn("sample_layering", profile["copying_policy"]["allowed_actions"])
        self.assertIn("download_reference_audio", profile["copying_policy"]["disallowed_actions"])
        self.assertIn("제공 파일 안에서만", profile["copying_policy"]["report_note"])

    def test_edit_plan_and_qc_report_include_copying_policy_note(self) -> None:
        profile = build_reference_target_profile("웨스트우드 Just Touched Down 킥 따와", None)
        analysis = {
            "metadata": {"duration_seconds": 60.0},
            "arrangement_candidates": {},
            "silence_detection": {},
            "vocal_like_texture_candidates": [],
            "melody_buried_candidates": [],
            "low_end_excess_candidates": [],
        }
        verification = {
            "passed": True,
            "ok": True,
            "format_verified": True,
            "sample_rate": 48000,
            "bit_depth": 24,
            "channels": 2,
            "duration_seconds": 60.0,
            "file_size": 1000,
            "peak_dbfs": -1.2,
            "rms_dbfs": -12.0,
            "clipping_count": 0,
            "warnings": [],
        }

        plan = build_edit_plan(analysis, {"mode": "full_song_stereo", "input": "/tmp/stereo.wav"}, profile)
        report = build_qc_report(
            {},
            analysis,
            verification,
            Path("/tmp/final.wav"),
            None,
            "fallback_processed",
            "test",
            "not created",
            profile,
            {},
            True,
        )

        self.assertIn("copying policy", plan)
        self.assertIn("정확한 킥/베이스 샘플 복사가 아니라", plan)
        self.assertIn("copying policy", report)
        self.assertIn("extract_kick_sample", report)


if __name__ == "__main__":
    unittest.main()

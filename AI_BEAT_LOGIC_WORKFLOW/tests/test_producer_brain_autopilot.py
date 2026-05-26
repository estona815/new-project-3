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

from producer_brain import build_producer_brain_plan  # noqa: E402


def write_test_wav(path: Path, *, sample_rate: int = 48000, seconds: float = 2.0, channels: int = 2) -> None:
    frames = int(sample_rate * seconds)
    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(channels)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        for index in range(frames):
            time = index / sample_rate
            pulse = 0.4 * math.exp(-(time % 0.5) * 55.0) if (time % 0.5) < 0.08 else 0.0
            tone = 0.22 * math.sin(2.0 * math.pi * 220.0 * time)
            value = max(-0.9, min(0.9, pulse + tone))
            raw = int(value * 32767).to_bytes(2, "little", signed=True)
            wav_file.writeframesraw(raw * channels)


class ProducerBrainAutopilotTests(unittest.TestCase):
    def test_sample_vocal_workflow_builds_region_guides_without_completion_claim(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            sample = Path(tmp) / "owned_loop.wav"
            vocal = Path(tmp) / "lead.wav"
            write_test_wav(sample, channels=2)
            write_test_wav(vocal, channels=1)

            plan = build_producer_brain_plan(
                sample_path=sample,
                vocal_path=vocal,
                request_text="샘플이랑 보컬로 디지코어 편곡 플랜 짜줘",
                genre="digicore",
            )
            as_text = json.dumps(plan, ensure_ascii=False).lower()

            self.assertEqual(plan["workflow_type"], "sample_vocal_to_arrangement")
            self.assertTrue(plan["arrangement_plan"]["active"])
            self.assertEqual(plan["midi_region_guide"]["format"], "region_and_midi_guide_v1")
            self.assertTrue(plan["midi_region_guide"]["regions"])
            self.assertFalse(plan["safety"]["completion_claim_allowed_here"])
            self.assertIn("guide", as_text)
            self.assertIn("no autotune", as_text)
            self.assertFalse(plan["arrangement_plan"]["complete"])
            self.assertNotIn("COMPLETE", json.dumps(plan, ensure_ascii=False))

    def test_full_song_workflow_is_stereo_only_and_heuristic(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            song = Path(tmp) / "full_song.wav"
            write_test_wav(song, channels=2)

            plan = build_producer_brain_plan(
                song_path=song,
                request_text="full song stereo polish, 보컬은 건드릴 수 있는 선에서만",
            )
            as_text = json.dumps(plan, ensure_ascii=False).lower()

            self.assertEqual(plan["workflow_type"], "song_to_arrangement_mix_master")
            self.assertTrue(plan["mix_master_plan"]["stereo_only"])
            self.assertEqual(plan["analysis"]["full_song"]["analysis_scope"], "heuristic_full_stereo_song")
            self.assertIn("broad stereo polish only", plan["mix_master_plan"]["fallback_scope"])
            self.assertIn("no real vocal removal", as_text)
            self.assertNotIn("stem-level remixing succeeded", as_text)

    def test_stems_workflow_allows_direct_planning_but_not_fake_logic_success(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            drums = Path(tmp) / "drums.wav"
            bass = Path(tmp) / "808.wav"
            vocal = Path(tmp) / "lead.wav"
            write_test_wav(drums)
            write_test_wav(bass)
            write_test_wav(vocal, channels=1)

            plan = build_producer_brain_plan(
                stems={"drums": drums, "bass_808": bass, "lead_vocal": vocal},
                request_text="스템으로 드럼/808/보컬 상업퀄로 정리",
            )
            as_text = json.dumps(plan, ensure_ascii=False).lower()

            self.assertEqual(plan["workflow_type"], "stems_to_production")
            self.assertTrue(plan["analysis"]["stems"]["available"])
            self.assertFalse(plan["mix_master_plan"]["stereo_only"])
            self.assertFalse(plan["safety"]["logic_success_faked"])
            self.assertIn("verify any rendered logic export", as_text)
            self.assertIn("no stem separation is claimed", as_text)

    def test_copying_request_is_blocked_without_owned_source_confirmation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            sample = Path(tmp) / "reference.wav"
            write_test_wav(sample)

            plan = build_producer_brain_plan(
                sample_path=sample,
                request_text="킥이랑 베이스 그대로 따와라",
                ownership_flags={},
            )
            policy = plan["safety"]["copying_policy"]

            self.assertTrue(policy["copying_requested"])
            self.assertFalse(policy["exact_copy_allowed"])
            self.assertTrue(policy["requires_user_owned_source"])
            self.assertIn("extract_kick_sample", policy["disallowed_actions"])
            self.assertIn("high_level_trait_match", policy["allowed_actions"])


if __name__ == "__main__":
    unittest.main()

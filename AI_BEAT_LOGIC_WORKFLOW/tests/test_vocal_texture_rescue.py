from __future__ import annotations

import json
import math
import sys
import tempfile
import unittest
import wave
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from export_audio import verify_wav  # noqa: E402
from vocal_texture_rescue import build_vocal_texture_rescue_plan, write_vocal_texture_rescue_outputs  # noqa: E402


def write_center_vocal_texture_wav(path: Path, sample_rate: int = 48_000, seconds: float = 2.0) -> None:
    frames = int(sample_rate * seconds)
    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(2)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        for index in range(frames):
            time = index / sample_rate
            body = math.sin(2.0 * math.pi * 700.0 * time) * 0.18
            formant = math.sin(2.0 * math.pi * 1_600.0 * time) * 0.09
            modulation = 0.5 + 0.5 * math.sin(2.0 * math.pi * 7.0 * time)
            center = (body + formant) * modulation
            side = math.sin(2.0 * math.pi * 8_000.0 * time) * 0.015
            left = max(-0.95, min(0.95, center + side))
            right = max(-0.95, min(0.95, center - side))
            wav_file.writeframesraw(int(left * 32767).to_bytes(2, "little", signed=True))
            wav_file.writeframesraw(int(right * 32767).to_bytes(2, "little", signed=True))


class VocalTextureRescueTests(unittest.TestCase):
    def test_stereo_weird_vocal_texture_gets_demote_and_replace_plan(self) -> None:
        plan = build_vocal_texture_rescue_plan(
            input_path="/tmp/source.wav",
            mode="full_song_stereo",
            vocal_like_texture_candidates=[
                {
                    "start": 12.0,
                    "end": 18.5,
                    "issue": "fake vocal chop dominates lead",
                    "confidence": "medium",
                }
            ],
            rescue_diagnosis={
                "input": {"mode": "full_song_stereo"},
                "musical_identity": {"lead_melody_presence": 1},
                "vocal_texture": {
                    "weird_vocal_texture_risk": "high",
                    "vocal_chop_as_unwanted_lead": True,
                },
                "rescue_decision": {"lead_melody_required": True},
            },
        )

        action_types = [action["type"] for action in plan["actions"]]
        self.assertEqual(plan["schema_version"], "vocal_texture_rescue_plan.v1")
        self.assertEqual(plan["detected_issues"][0]["issue"], "fake_vocal_chop_dominates_lead")
        self.assertIn("demote_texture", action_types)
        self.assertIn("replace_role_with_synth_lead", action_types)
        self.assertTrue(any("Stereo-only source cannot fully remove" in item for item in plan["limitations"]))
        self.assertFalse(plan["claim_guard"]["vocal_removal_claimed"])
        self.assertFalse(plan["claim_guard"]["stem_level_control_from_stereo_claimed"])

    def test_writes_plan_json_without_processing_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            outputs = write_vocal_texture_rescue_outputs(
                project_root=temp_dir,
                mode="full_song_stereo",
                vocal_like_texture_candidates=[
                    {"start": 1.0, "end": 1.8, "reason": "random fake vocal chop", "confidence": "medium"}
                ],
                rescue_diagnosis={
                    "vocal_texture": {"weird_vocal_texture_risk": "medium", "vocal_chop_as_unwanted_lead": True},
                    "rescue_decision": {"lead_melody_required": True},
                },
                process=False,
            )
            plan_path = Path(outputs["paths"]["vocal_texture_rescue_plan"])
            audio_path = Path(outputs["paths"]["vocal_texture_rescued"])
            saved = json.loads(plan_path.read_text(encoding="utf-8"))

            self.assertTrue(plan_path.exists())
            self.assertFalse(audio_path.exists())
            self.assertEqual(saved["schema_version"], "vocal_texture_rescue_plan.v1")
            self.assertFalse(outputs["processing"]["created"])

    def test_processing_creates_demoted_wav_without_removal_claim(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source = Path(temp_dir) / "source.wav"
            write_center_vocal_texture_wav(source)
            outputs = write_vocal_texture_rescue_outputs(
                project_root=temp_dir,
                input_path=source,
                mode="full_song_stereo",
                vocal_like_texture_candidates=[
                    {"start": 0.2, "end": 1.5, "reason": "mono-centered fake vocal chop dominates lead", "confidence": "high"}
                ],
                rescue_diagnosis={
                    "input": {"mode": "full_song_stereo", "path": str(source)},
                    "vocal_texture": {"weird_vocal_texture_risk": "high", "vocal_chop_as_unwanted_lead": True},
                    "rescue_decision": {"lead_melody_required": True},
                },
                process=True,
            )
            rescued = Path(outputs["paths"]["vocal_texture_rescued"])
            verification = verify_wav(rescued)

            self.assertTrue(outputs["processing"]["created"])
            self.assertTrue(rescued.exists())
            self.assertEqual(verification["sample_rate"], 48_000)
            self.assertEqual(verification["channels"], 2)
            self.assertEqual(verification["clipping_count"], 0)
            self.assertFalse(outputs["processing"]["claim_guard"]["vocal_removal_performed"])
            self.assertFalse(outputs["processing"]["claim_guard"]["stem_level_control_from_stereo_claimed"])
            self.assertTrue(outputs["processing"]["claim_guard"]["full_stereo_processing_is_demote_only"])


if __name__ == "__main__":
    unittest.main()

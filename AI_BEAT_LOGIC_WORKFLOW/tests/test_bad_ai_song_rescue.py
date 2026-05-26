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

from bad_ai_song_rescue import (  # noqa: E402
    ARRANGEMENT_REBUILD_REQUIRED,
    HOOK_IDENTITY_REQUIRED,
    LEAD_MELODY_REQUIRED,
    PLAN_STATUS,
    SAMPLE_MOTIF_REBUILD_REQUIRED,
    VOCAL_TEXTURE_CLEANUP_REQUIRED,
    build_bad_song_diagnosis,
    run_bad_ai_song_rescue,
)


def write_flat_bad_ai_song(path: Path, sample_rate: int = 48000, seconds: float = 28.0) -> None:
    frames = int(sample_rate * seconds)
    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(2)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        for index in range(frames):
            time = index / sample_rate
            base = math.sin(2.0 * math.pi * 220.0 * time) * 0.28
            haze = math.sin(2.0 * math.pi * 980.0 * time) * 0.07
            click = 0.10 if index % int(sample_rate * 0.25) < 80 else 0.0
            value = max(-0.85, min(0.85, base + haze + click))
            raw = int(value * 32767).to_bytes(2, "little", signed=True)
            wav_file.writeframesraw(raw + raw)


class BadAiSongRescueTests(unittest.TestCase):
    def test_diagnosis_marks_mix_only_not_enough_when_identity_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            song = Path(tmp) / "bad_ai.wav"
            write_flat_bad_ai_song(song)

            diagnosis = build_bad_song_diagnosis(song, request_text="AI 곡 살려줘")

            self.assertEqual(diagnosis["schema_version"], "bad_song_diagnosis.v1")
            self.assertEqual(diagnosis["status"], PLAN_STATUS)
            self.assertFalse(diagnosis["complete"])
            self.assertTrue(diagnosis["MIX_ONLY_NOT_ENOUGH"])
            self.assertTrue(diagnosis["flags"]["no_clear_lead_melody"])
            self.assertTrue(diagnosis["flags"]["no_hook_identity"])
            self.assertTrue(diagnosis["flags"]["no_arrangement_structure"])
            for route in (
                ARRANGEMENT_REBUILD_REQUIRED,
                LEAD_MELODY_REQUIRED,
                HOOK_IDENTITY_REQUIRED,
                VOCAL_TEXTURE_CLEANUP_REQUIRED,
                SAMPLE_MOTIF_REBUILD_REQUIRED,
            ):
                self.assertIn(route, diagnosis["required_routes"])
            self.assertFalse(diagnosis["stereo_claim_guard"]["stem_level_remix_claimed"])
            self.assertFalse(diagnosis["stereo_claim_guard"]["vocal_removal_claimed"])

    def test_run_rescue_writes_required_plan_outputs_without_final_wav(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "workflow"
            song = Path(tmp) / "bad_ai.wav"
            sample_folder = Path(tmp) / "samples"
            sample_folder.mkdir()
            (sample_folder / "owned_chop.wav").write_bytes(b"not used by test")
            write_flat_bad_ai_song(song)

            result = run_bad_ai_song_rescue(
                project_root=root,
                input_path=song,
                request_text="Bad AI song rescue",
                sample_folder=sample_folder,
                owned_samples=True,
            )
            paths = result["paths"]

            self.assertEqual(result["status"], PLAN_STATUS)
            for key in (
                "bad_song_diagnosis_json",
                "bad_song_diagnosis_md",
                "rescue_arrangement_plan_json",
                "rescue_arrangement_plan_md",
                "lead_melody_plan",
                "hook_identity_plan",
                "vocal_texture_rescue_plan",
                "sample_motif_rebuild_plan",
                "logic_rescue_plan",
                "rescue_qc_report",
            ):
                self.assertTrue(paths[key].exists(), key)
            diagnosis = json.loads(paths["bad_song_diagnosis_json"].read_text(encoding="utf-8"))
            rescue_plan = json.loads(paths["rescue_arrangement_plan_json"].read_text(encoding="utf-8"))
            sample_plan = json.loads(paths["sample_motif_rebuild_plan"].read_text(encoding="utf-8"))
            qc = paths["rescue_qc_report"].read_text(encoding="utf-8")

            self.assertTrue(diagnosis["MIX_ONLY_NOT_ENOUGH"])
            self.assertEqual(rescue_plan["status"], PLAN_STATUS)
            self.assertFalse(rescue_plan["complete"])
            self.assertTrue(sample_plan["direct_sample_use_allowed"])
            self.assertIn(str(sample_folder / "owned_chop.wav"), sample_plan["candidate_audio_files"])
            self.assertFalse((root / "05_FINAL_WAV" / "final_rescued_song_24bit_48k.wav").exists())
            self.assertIn("final WAV verified: false", qc)


if __name__ == "__main__":
    unittest.main()

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
from sample_motif_rebuild import build_sample_motif_rebuild_plan, write_sample_motif_rebuild_outputs  # noqa: E402


def write_sample(path: Path, sample_rate: int = 48_000, seconds: float = 2.0, frequency: float = 440.0) -> None:
    frames = int(sample_rate * seconds)
    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(2)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        for index in range(frames):
            time = index / sample_rate
            value = math.sin(2.0 * math.pi * frequency * time) * 0.24
            if time % 0.5 < 0.04:
                value += 0.18 * math.exp(-(time % 0.5) * 80.0)
            value = max(-0.92, min(0.92, value))
            raw = int(value * 32767).to_bytes(2, "little", signed=True)
            wav_file.writeframesraw(raw + raw)


def sample_analysis(path: Path) -> dict[str, object]:
    return {
        "schema_version": "sample_analysis.v1",
        "metadata": {"path": str(path), "duration_seconds": 2.0},
        "tonal": {"estimated_key": "F# minor", "confidence": "medium"},
        "loop_detection": {"loopable_regions": [{"start": 0.0, "end": 1.8}]},
        "motif_hook_detection": {
            "hook_motif_candidates": [
                {
                    "start": 0.0,
                    "end": 1.0,
                    "confidence": "medium",
                    "reason": "tonal, recognizable, loopable",
                    "role_hint": "hook_candidate",
                },
                {
                    "start": 1.0,
                    "end": 1.8,
                    "confidence": "low",
                    "reason": "short response variation",
                    "role_hint": "motif_or_variation",
                },
            ]
        },
    }


def arrangement_plan() -> dict[str, object]:
    return {
        "schema_version": "rescue_arrangement_plan.v1",
        "sections": [
            {"name": "intro_hook_hint", "start_time": 0.0, "duration": 4.0, "energy": 3},
            {"name": "main_hook", "start_time": 4.0, "duration": 8.0, "energy": 5},
            {"name": "verse", "start_time": 12.0, "duration": 8.0, "energy": 2},
            {"name": "hook_return", "start_time": 20.0, "duration": 8.0, "energy": 5},
        ],
    }


class SampleMotifRebuildTests(unittest.TestCase):
    def test_builds_plan_with_musical_roles_and_hook_return(self) -> None:
        plan = build_sample_motif_rebuild_plan(
            sample_analysis=sample_analysis(Path("/tmp/sample_01.wav")),
            song_key_bpm={"bpm": 148, "key": "F# minor", "key_confidence": "medium"},
            rescue_arrangement_plan=arrangement_plan(),
        )
        roles = {item["role"] for item in plan["selected_samples"]}
        hook_sections = [item for item in plan["section_usage"] if "hook" in item["section"].lower()]

        self.assertEqual(plan["schema_version"], "sample_motif_rebuild_plan.v1")
        self.assertEqual(plan["status"], "SAMPLE_MOTIF_REBUILD_PLAN_READY")
        self.assertIn("main_motif", roles)
        self.assertIn("response_motif", roles)
        self.assertIn("texture_layer", roles)
        self.assertTrue(plan["quality_gates"]["samples_assigned_musical_roles"])
        self.assertTrue(plan["quality_gates"]["main_motif_returns_in_hook"])
        self.assertTrue(plan["quality_gates"]["no_random_chop_spam"])
        self.assertTrue(any(item["sample_role"] == "main_motif_full" for item in hook_sections))
        self.assertIn("Avoid random glitch chop.", plan["rules"])

    def test_writes_plan_without_render_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            outputs = write_sample_motif_rebuild_outputs(
                project_root=temp_dir,
                sample_analysis=sample_analysis(Path("/tmp/sample_01.wav")),
                rescue_arrangement_plan=arrangement_plan(),
                render=False,
            )
            plan_path = Path(outputs["paths"]["sample_motif_rebuild_plan"])
            demo_path = Path(outputs["paths"]["sample_motif_demo"])
            saved = json.loads(plan_path.read_text(encoding="utf-8"))

            self.assertTrue(plan_path.exists())
            self.assertFalse(demo_path.exists())
            self.assertEqual(saved["schema_version"], "sample_motif_rebuild_plan.v1")
            self.assertFalse(outputs["render"]["created"])

    def test_render_enabled_creates_demo_when_wav_region_available(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "workflow"
            sample_path = Path(temp_dir) / "sample_01.wav"
            write_sample(sample_path)
            outputs = write_sample_motif_rebuild_outputs(
                project_root=root,
                sample_folder=temp_dir,
                sample_analysis=sample_analysis(sample_path),
                song_key_bpm={"bpm": 120, "key": "A minor"},
                rescue_arrangement_plan=arrangement_plan(),
                render=True,
            )
            demo_path = Path(outputs["paths"]["sample_motif_demo"])
            verification = verify_wav(demo_path)

            self.assertTrue(outputs["render"]["created"])
            self.assertTrue(demo_path.exists())
            self.assertEqual(verification["sample_rate"], 48_000)
            self.assertEqual(verification["channels"], 2)
            self.assertEqual(verification["clipping_count"], 0)
            self.assertGreater(outputs["render"]["placement_count"], 0)


if __name__ == "__main__":
    unittest.main()

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

from arrangement_autopilot import (  # noqa: E402
    build_arrangement_autopilot_plan,
    render_arrangement_autopilot_markdown,
    run_arrangement_autopilot,
)
from sample_arrangement_analyzer import analyze_sample_for_arrangement  # noqa: E402
from vocal_phrase_coder import code_vocal_phrases  # noqa: E402


def write_sample_loop(path: Path, sample_rate: int = 48000, seconds: float = 4.0) -> None:
    frames = int(sample_rate * seconds)
    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(2)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        for index in range(frames):
            time = index / sample_rate
            beat_position = time % 0.5
            transient = 0.75 * math.exp(-beat_position * 70.0) if beat_position < 0.08 else 0.0
            tone = 0.22 * math.sin(2.0 * math.pi * 220.0 * time)
            hat = 0.05 * math.sin(2.0 * math.pi * 7000.0 * time) if (time % 0.25) < 0.03 else 0.0
            value = max(-0.9, min(0.9, transient + tone + hat))
            raw = int(value * 32767).to_bytes(2, "little", signed=True)
            wav_file.writeframesraw(raw + raw)


def write_vocal_phrase(path: Path, sample_rate: int = 48000, seconds: float = 2.4) -> None:
    frames = int(sample_rate * seconds)
    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        for index in range(frames):
            time = index / sample_rate
            active = 0.2 < time < 1.1 or 1.35 < time < 2.1
            if not active:
                value = 0.0
            else:
                frequency = 220.0 if time < 1.1 else 246.94
                envelope = 0.35
                value = envelope * math.sin(2.0 * math.pi * frequency * time)
            raw = int(max(-0.9, min(0.9, value)) * 32767).to_bytes(2, "little", signed=True)
            wav_file.writeframesraw(raw)


class SampleVocalArrangementAutopilotTests(unittest.TestCase):
    def test_sample_analysis_schema_includes_tempo_key_loop_onsets_and_motifs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            sample = Path(tmp) / "owned_sample.wav"
            write_sample_loop(sample)

            analysis = analyze_sample_for_arrangement(sample, genre="digicore")
            as_text = json.dumps(analysis).lower()

            self.assertEqual(analysis["schema_version"], 1)
            self.assertEqual(analysis["source"]["analysis_type"], "local_sample_audio")
            self.assertIn("tempo", analysis)
            self.assertIn("key_pitch", analysis)
            self.assertIn("loop_candidates", analysis)
            self.assertIn("transient_onset_analysis", analysis)
            self.assertIn("hook_motif_candidates", analysis)
            self.assertGreater(analysis["transient_onset_analysis"]["onset_count"], 2)
            self.assertIsNotNone(analysis["tempo"]["bpm"])
            self.assertTrue(analysis["loop_candidates"])
            self.assertIn("heuristic", as_text)
            self.assertIn("owned/cleared", as_text)
            self.assertNotIn("stem separation", as_text)

    def test_vocal_phrase_code_schema_is_guide_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            vocal = Path(tmp) / "lead_vocal.wav"
            write_vocal_phrase(vocal)

            coded = code_vocal_phrases(vocal)
            as_text = json.dumps(coded).lower()

            self.assertEqual(coded["schema_version"], 1)
            self.assertEqual(coded["source"]["analysis_type"], "local_vocal_file")
            self.assertIn("phrasing", coded)
            self.assertIn("pitch_contour", coded)
            self.assertIn("melody_code", coded)
            self.assertGreaterEqual(coded["phrasing"]["phrase_count"], 1)
            self.assertTrue(coded["melody_code"]["events"])
            self.assertFalse(coded["pitch_correction_guide"]["auto_tune_applied"])
            self.assertIn("manual tuning", as_text)
            self.assertIn("not a verified score transcription", as_text)
            self.assertNotIn("autotune applied", as_text.replace('"auto_tune_applied": false', ""))

    def test_arrangement_autopilot_combines_sample_and_vocal_without_copy_claims(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            sample = Path(tmp) / "sample.wav"
            vocal = Path(tmp) / "vocal.wav"
            write_sample_loop(sample)
            write_vocal_phrase(vocal)
            sample_analysis = analyze_sample_for_arrangement(sample, genre="SYSTEM SEOUL-adjacent")
            vocal_code = code_vocal_phrases(vocal)

            plan = build_arrangement_autopilot_plan(
                sample_analysis=sample_analysis,
                vocal_code=vocal_code,
                genre="SYSTEM SEOUL-adjacent",
                request_text="샘플이랑 보컬로 SYSTEM SEOUL-adjacent 디지코어 편곡 플랜 짜줘",
            )
            markdown = render_arrangement_autopilot_markdown(plan)
            combined = json.dumps(plan).lower() + markdown.lower()

            self.assertEqual(plan["status"], "ARRANGEMENT_PLAN_READY")
            self.assertFalse(plan["complete"])
            self.assertEqual(plan["genre_mode"], "system_seoul_adjacent")
            self.assertIn("logic_manual_plan", plan)
            self.assertIn("bass_808_midi_guide", plan)
            self.assertIn("Arrangement Autopilot Plan", markdown)
            self.assertIn("high-level production targets only", combined)
            self.assertIn("plugin_applied_claimed", combined)
            self.assertIn("final wav is not required", combined)
            self.assertFalse(plan["safety"]["reference_copying_allowed"])
            self.assertFalse(plan["safety"]["plugin_applied_claimed"])
            self.assertFalse(plan["safety"]["stem_level_rewrite_claimed"])

    def test_run_arrangement_autopilot_writes_plan_artifacts_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "workflow"
            sample = Path(tmp) / "sample.wav"
            vocal = Path(tmp) / "vocal.wav"
            write_sample_loop(sample)
            write_vocal_phrase(vocal)

            result = run_arrangement_autopilot(
                project_root=root,
                sample_path=sample,
                vocal_path=vocal,
                genre="digicore",
                request_text="sample/vocal arrangement autopilot MVP",
            )
            json_path = Path(result["json_path"])
            markdown_path = Path(result["markdown_path"])
            parsed = json.loads(json_path.read_text(encoding="utf-8"))
            markdown = markdown_path.read_text(encoding="utf-8")

            self.assertTrue(json_path.exists())
            self.assertTrue(markdown_path.exists())
            self.assertEqual(parsed["schema_version"], "arrangement_plan.v1")
            self.assertEqual(parsed["status"], "ARRANGEMENT_PLAN_READY")
            self.assertFalse(parsed["complete"])
            self.assertIn("sample/vocal arrangement autopilot MVP", markdown)
            self.assertFalse((root / "05_FINAL_WAV").exists())
            self.assertNotIn("COMPLETE", markdown)


if __name__ == "__main__":
    unittest.main()

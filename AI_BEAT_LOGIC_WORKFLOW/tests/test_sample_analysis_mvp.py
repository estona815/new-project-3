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

from sample_analysis import analyze_sample_audio, write_sample_analysis  # noqa: E402


def write_loop(path: Path, sample_rate: int = 48000, seconds: float = 4.0) -> None:
    frames = int(sample_rate * seconds)
    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(2)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        for index in range(frames):
            time = index / sample_rate
            pulse = 0.7 * math.exp(-(time % 0.5) * 70.0) if (time % 0.5) < 0.08 else 0.0
            tone = 0.22 * math.sin(2.0 * math.pi * 220.0 * time)
            value = max(-0.9, min(0.9, pulse + tone))
            raw = int(value * 32767).to_bytes(2, "little", signed=True)
            wav_file.writeframesraw(raw + raw)


class SampleAnalysisMvpTests(unittest.TestCase):
    def test_sample_analysis_schema_covers_required_sections(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            sample = Path(tmp) / "loop.wav"
            write_loop(sample)

            analysis = analyze_sample_audio(sample)
            as_text = json.dumps(analysis).lower()

            self.assertEqual(analysis["schema_version"], "sample_analysis.v1")
            self.assertEqual(analysis["metadata"]["path"], str(sample))
            self.assertGreater(analysis["metadata"]["duration_seconds"], 3.9)
            self.assertEqual(analysis["metadata"]["sample_rate"], 48000)
            self.assertEqual(analysis["metadata"]["channels"], 2)
            self.assertEqual(analysis["metadata"]["format"], "wav")
            self.assertIn("peak_dbfs", analysis["level"])
            self.assertIn("rms_dbfs", analysis["level"])
            self.assertIn("clipping_count", analysis["level"])
            self.assertIn("silence_regions", analysis["level"])
            self.assertIsNotNone(analysis["timing"]["bpm"])
            self.assertTrue(analysis["timing"]["bpm_candidates"])
            self.assertIn("half_double_ambiguity", analysis["timing"])
            self.assertIn("estimated_tonic_or_pitch_center", analysis["tonal"])
            self.assertTrue(analysis["loop_detection"]["loopable_regions"])
            self.assertIn("boundary_click_risk", analysis["loop_detection"]["loopable_regions"][0])
            self.assertIn("hook_motif_candidates", analysis["motif_hook_detection"])
            self.assertIn("onset_times", analysis["transient_onset"])
            self.assertFalse(analysis["sample_usage_safety"]["direct_sample_use_allowed"])
            self.assertIn("no exact", as_text)
            self.assertNotIn("exact copying performed", as_text)

    def test_short_sample_produces_low_confidence_safe_results(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            sample = Path(tmp) / "short.wav"
            write_loop(sample, seconds=1.0)

            analysis = analyze_sample_audio(sample)

            self.assertNotEqual(analysis["timing"]["confidence"], "high")
            self.assertEqual(analysis["tonal"]["confidence"], "low")
            self.assertIn("under 2 seconds", " ".join(analysis["limitations"]))

    def test_write_sample_analysis_outputs_json_and_summary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "workflow"
            sample = Path(tmp) / "loop.wav"
            write_loop(sample)

            paths = write_sample_analysis(sample, project_root=root, ownership_status="unknown")
            parsed = json.loads(paths["json"].read_text(encoding="utf-8"))
            summary = paths["summary"].read_text(encoding="utf-8")

            self.assertTrue(paths["json"].exists())
            self.assertTrue(paths["summary"].exists())
            self.assertEqual(parsed["schema_version"], "sample_analysis.v1")
            self.assertIn("Sample Analysis Summary", summary)
            self.assertIn("direct sample use allowed: false", summary)
            self.assertFalse((root / "05_FINAL_WAV").exists())


if __name__ == "__main__":
    unittest.main()

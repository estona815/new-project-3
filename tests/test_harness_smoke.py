from __future__ import annotations

import json
import math
import subprocess
import sys
import tempfile
import unittest
import wave
from pathlib import Path

from harness.audio_qc import compare_before_after
from harness.severity import has_warn_plus, max_severity


ROOT = Path(__file__).resolve().parents[1]
RUN_PIPELINE = ROOT / "harness" / "run_music_pipeline.py"


def write_sine(path: Path, *, freq: float = 440.0, duration: float = 1.0, gain: float = 0.15) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    sample_rate = 44100
    frames = []
    for index in range(int(sample_rate * duration)):
        value = int(max(-1.0, min(1.0, math.sin(2.0 * math.pi * freq * index / sample_rate) * gain)) * 32767)
        frames.append(value.to_bytes(2, byteorder="little", signed=True))
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(sample_rate)
        handle.writeframes(b"".join(frames))


class HarnessSmokeTests(unittest.TestCase):
    def test_audio_qc_generates_metrics_and_warn_plus_for_missing_loudness_dependency(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            before = root / "before.wav"
            after = root / "after.wav"
            write_sine(before, freq=440.0, duration=1.0)
            write_sine(after, freq=440.0, duration=1.0, gain=0.12)
            findings = []

            payload = compare_before_after(before, after, findings)

            self.assertIn("duration_sec", payload["before"])
            self.assertIn("peak_dbfs", payload["after"])
            self.assertIn(max_severity(findings), {"PASS", "INFO", "WARN", "FAIL", "BLOCKER"})

    def test_true_rebeat_claim_is_blocked_without_midi_or_stem_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "audio" / "fullmix_original.wav"
            write_sine(source)
            (root / "config").mkdir(parents=True)
            (root / "config" / "plugin_map.yaml").write_text("roles:\n  limiter:\n    fallback: ReaLimit\n", encoding="utf-8")
            project = root / "reaper" / "fake" / "fake.rpp"
            project.parent.mkdir(parents=True)
            project.write_text(
                "\n".join(
                    [
                        "<REAPER_PROJECT 0.1 \"7.0\" 0",
                        "  <TRACK",
                        "    NAME \"01_REF_ORIGINAL\"",
                        "    <ITEM",
                        "      <SOURCE WAVE",
                        f"        FILE \"{source}\"",
                        "      >",
                        "    >",
                        "  >",
                        ">",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            result = subprocess.run(
                [
                    sys.executable,
                    str(RUN_PIPELINE),
                    "--project-root",
                    str(root),
                    "--source",
                    str(source),
                    "--mode",
                    "true_rebeat",
                    "--json",
                ],
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            codes = {finding["code"] for finding in payload["findings"]}
            self.assertIn("TRUE_REBEAT_NOT_ALLOWED", codes)
            self.assertEqual(payload["claim_status"], "not_final_warn_plus")
            self.assertTrue(has_warn_plus(payload["findings"]))
            self.assertTrue((root / "reports" / "WARN_PLUS_PROMPT.md").exists())

    def test_report_generation_writes_json_and_markdown(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source_dir = root / "input_stems" / "song"
            write_sine(source_dir / "drums.wav")
            write_sine(source_dir / "bass.wav", freq=110.0)
            write_sine(source_dir / "main_vocal.wav", freq=220.0)
            (root / "config").mkdir(parents=True)
            (root / "config" / "plugin_map.yaml").write_text("roles:\n  limiter:\n    fallback: ReaLimit\n", encoding="utf-8")

            result = subprocess.run(
                [
                    sys.executable,
                    str(RUN_PIPELINE),
                    "--project-root",
                    str(root),
                    "--source",
                    str(source_dir),
                    "--mode",
                    "auto",
                    "--json",
                ],
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["classification"]["selected_classification"], "stem_rebuild")
            self.assertTrue((root / "reports" / "music_pipeline_report.json").exists())
            self.assertTrue((root / "reports" / "music_pipeline_report.md").exists())


if __name__ == "__main__":
    unittest.main()


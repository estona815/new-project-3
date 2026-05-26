from __future__ import annotations

import sys
import tempfile
import unittest
import wave
from pathlib import Path

import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from lead_melody_generator import build_lead_melody_plan, write_lead_melody_outputs  # noqa: E402
from simple_synth_renderer import note_to_frequency, render_lead_plan_to_wav, render_motifs_to_audio  # noqa: E402


def _read_pcm16(path: Path) -> tuple[wave.Wave_read, np.ndarray]:
    wav_file = wave.open(str(path), "rb")
    raw = wav_file.readframes(wav_file.getnframes())
    samples = np.frombuffer(raw, dtype="<i2")
    if wav_file.getnchannels() > 0:
        samples = samples.reshape(-1, wav_file.getnchannels())
    return wav_file, samples


class SimpleSynthRendererTests(unittest.TestCase):
    def test_note_to_frequency_supports_sharps_and_flats(self) -> None:
        self.assertAlmostEqual(note_to_frequency("A4"), 440.0, places=3)
        self.assertAlmostEqual(note_to_frequency("Bb4"), note_to_frequency("A#4"), places=3)

    def test_renders_stereo_audio_array_with_headroom(self) -> None:
        plan = build_lead_melody_plan(tempo={"bpm": 148}, key={"key": "F# minor", "confidence": "medium"})
        audio = render_motifs_to_audio(
            [plan["motifs"][0]],
            tempo_bpm=plan["tempo_bpm"],
            sound_design=plan["sound_design"],
            sample_rate=48_000,
        )

        self.assertEqual(audio.ndim, 2)
        self.assertEqual(audio.shape[1], 2)
        self.assertGreater(audio.shape[0], 1_000)
        self.assertLessEqual(float(np.max(np.abs(audio))), 0.98)

    def test_rendered_lead_stem_does_not_clip(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "generated_lead_motif.wav"
            plan = build_lead_melody_plan(tempo={"bpm": 148}, key={"key": "F# minor", "confidence": "medium"})
            report = render_lead_plan_to_wav(plan, path, motif_ids=["lead_A"])
            wav_file, samples = _read_pcm16(path)
            try:
                self.assertTrue(path.exists())
                self.assertTrue(report["rendered"])
                self.assertEqual(wav_file.getframerate(), 48_000)
                self.assertEqual(wav_file.getnchannels(), 2)
                self.assertGreater(wav_file.getnframes(), 1_000)
                self.assertEqual(report["clipping_count"], 0)
                self.assertEqual(int(np.sum(np.abs(samples) >= 32767)), 0)
            finally:
                wav_file.close()

    def test_write_outputs_with_render_reports_exact_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            outputs = write_lead_melody_outputs(project_root=temp_dir, render=True)
            lead_wav = Path(outputs["rendered"]["lead_motif"]["path"])
            hook_wav = Path(outputs["rendered"]["hook_stem"]["path"])

            self.assertTrue(lead_wav.name.endswith("generated_lead_motif.wav"))
            self.assertTrue(hook_wav.name.endswith("generated_hook_stem.wav"))
            self.assertTrue(lead_wav.exists())
            self.assertTrue(hook_wav.exists())
            self.assertEqual(outputs["rendered"]["lead_motif"]["clipping_count"], 0)
            self.assertEqual(outputs["rendered"]["hook_stem"]["clipping_count"], 0)


if __name__ == "__main__":
    unittest.main()

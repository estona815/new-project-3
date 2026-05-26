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

from bad_song_diagnosis import build_bad_song_diagnosis, write_bad_song_diagnosis  # noqa: E402


def _write_stereo_wav(path: Path, samples: list[float], sample_rate: int = 48000) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(2)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        for sample in samples:
            clipped = max(-0.95, min(0.95, sample))
            raw = int(clipped * 32767).to_bytes(2, "little", signed=True)
            wav_file.writeframesraw(raw + raw)
    return path


def loud_weak_song_samples(sample_rate: int = 48000, seconds: float = 28.0) -> list[float]:
    frames = int(sample_rate * seconds)
    samples: list[float] = []
    for index in range(frames):
        t = index / sample_rate
        static_tone = 0.44 * math.sin(2.0 * math.pi * 220.0 * t)
        fake_texture = 0.05 * math.sin(2.0 * math.pi * 960.0 * t)
        pulse = 0.08 if index % int(0.25 * sample_rate) < 96 else 0.0
        samples.append(static_tone + fake_texture + pulse)
    return samples


def structured_motif_song_samples(sample_rate: int = 48000, seconds: float = 32.0) -> list[float]:
    frames = int(sample_rate * seconds)
    motif = [880.0, 987.77, 1174.66, 987.77, 1318.51, 1174.66, 987.77, 880.0]
    samples: list[float] = []
    for index in range(frames):
        t = index / sample_rate
        if t < 4.0 or t >= 30.0:
            amp = 0.04
            freq = 440.0
        elif 4.0 <= t < 12.0 or 20.0 <= t < 28.0:
            amp = 0.42
            step = int(((t % 4.0) / 4.0) * len(motif))
            freq = motif[step]
        else:
            amp = 0.18
            step = int(((t % 4.0) / 4.0) * 4)
            freq = [660.0, 740.0, 660.0, 554.37][step]
        melody = amp * math.sin(2.0 * math.pi * freq * t)
        kick = 0.28 * math.exp(-((t * 2.0) % 1.0) * 32.0) if 4.0 <= t < 28.0 else 0.0
        samples.append(melody + kick)
    return samples


def write_loud_weak_song(path: Path) -> Path:
    return _write_stereo_wav(path, loud_weak_song_samples())


def write_structured_motif_song(path: Path) -> Path:
    return _write_stereo_wav(path, structured_motif_song_samples())


class BadSongDiagnosisTests(unittest.TestCase):
    def test_loud_but_melodically_weak_song_requires_arrangement_rebuild(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            song = write_loud_weak_song(Path(tmp) / "weak.wav")

            diagnosis = build_bad_song_diagnosis(song)

            self.assertEqual(diagnosis["schema_version"], "bad_song_diagnosis.v1")
            self.assertEqual(diagnosis["input"]["mode"], "full_song_stereo")
            self.assertGreater(diagnosis["basic_metrics"]["duration_seconds"], 27.0)
            self.assertLessEqual(diagnosis["musical_identity"]["lead_melody_presence"], 2)
            self.assertLessEqual(diagnosis["musical_identity"]["hook_identity"], 2)
            self.assertLessEqual(diagnosis["arrangement"]["score"], 2.4)
            self.assertTrue(diagnosis["rescue_decision"]["mix_only_not_enough"])
            self.assertTrue(diagnosis["rescue_decision"]["arrangement_rebuild_required"])
            self.assertIn("Mix/master alone is insufficient", " ".join(diagnosis["limitations"]))

    def test_structured_repeated_motif_is_not_falsely_marked_no_identity(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            song = write_structured_motif_song(Path(tmp) / "structured.wav")

            diagnosis = build_bad_song_diagnosis(song)

            self.assertGreaterEqual(diagnosis["musical_identity"]["lead_melody_presence"], 3)
            self.assertGreaterEqual(diagnosis["musical_identity"]["hook_identity"], 3)
            self.assertFalse(diagnosis["rescue_decision"]["mix_only_not_enough"])

    def test_write_bad_song_diagnosis_outputs_json_and_markdown(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "workflow"
            song = write_loud_weak_song(Path(tmp) / "weak.wav")

            paths = write_bad_song_diagnosis(song, project_root=root)

            self.assertTrue(paths["json"].exists())
            self.assertTrue(paths["markdown"].exists())
            parsed = json.loads(paths["json"].read_text(encoding="utf-8"))
            markdown = paths["markdown"].read_text(encoding="utf-8")
            self.assertTrue(parsed["rescue_decision"]["mix_only_not_enough"])
            self.assertIn("Mix/master alone is insufficient", markdown)
            self.assertFalse((root / "05_FINAL_WAV").exists())


if __name__ == "__main__":
    unittest.main()

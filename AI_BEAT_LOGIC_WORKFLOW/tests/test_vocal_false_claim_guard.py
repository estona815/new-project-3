from __future__ import annotations

import json
import sys
import tempfile
import unittest
import wave
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_DIR))

from vocal_analysis import analyze_vocal_inputs  # noqa: E402
from vocal_to_code import analyze_vocal_to_code  # noqa: E402


def write_noise(path: Path, sample_rate: int = 48000, seconds: float = 0.7, channels: int = 1) -> None:
    frames = int(sample_rate * seconds)
    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(channels)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        for index in range(frames):
            value = 0.02 if index % 2 == 0 else -0.02
            raw = int(value * 32767).to_bytes(2, "little", signed=True)
            wav_file.writeframesraw(raw * channels)


class VocalFalseClaimGuardTests(unittest.TestCase):
    def test_short_noisy_vocal_does_not_crash_and_keeps_guard(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            vocal = Path(tmp) / "noise.wav"
            write_noise(vocal)

            result = analyze_vocal_to_code(vocal, mode="separate_vocal", requested_pitch_mode="hard_effect")

            self.assertEqual(result["schema_version"], "vocal_to_code.v1")
            self.assertIn("false_claim_guard", result)
            self.assertFalse(result["false_claim_guard"]["auto_tune_applied"])
            self.assertFalse(result["false_claim_guard"]["pitch_correction_performed"])
            self.assertFalse(result["false_claim_guard"]["note_transcription_is_exact"])
            self.assertEqual(result["pitch_correction_guide"]["claim_language"], "recommended, not applied")

    def test_analysis_text_never_claims_autotune_or_exact_transcription(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            vocal = Path(tmp) / "noise.wav"
            write_noise(vocal)

            result = analyze_vocal_to_code(vocal, mode="separate_vocal")
            as_text = json.dumps(result).lower()

            self.assertNotIn("autotune applied", as_text.replace('"auto_tune_applied": false', ""))
            self.assertNotIn("exact transcription", as_text.replace('"note_transcription_is_exact": false', ""))
            self.assertIn("estimated pitch/timing guide only", as_text)

    def test_vocal_analysis_embeds_vocal_to_code_for_full_stereo_as_heuristic(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            song = Path(tmp) / "song.wav"
            write_noise(song, channels=2)

            analysis = analyze_vocal_inputs({"mode": "full_song_stereo", "input_path": str(song)})

            self.assertIn("vocal_to_code", analysis)
            self.assertFalse(analysis["vocal_to_code"]["input"]["analysis_isolated"])
            self.assertIn("heuristic", " ".join(analysis["vocal_to_code"]["limitations"]).lower())


if __name__ == "__main__":
    unittest.main()

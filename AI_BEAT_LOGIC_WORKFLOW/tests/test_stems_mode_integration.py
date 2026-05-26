from __future__ import annotations

import math
import sys
import tempfile
import unittest
import wave
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from mix_master_autopilot import build_mix_master_plan  # noqa: E402


def write_stem(path: Path, freq: float, seconds: float = 2.0, sample_rate: int = 48000) -> None:
    frames = int(seconds * sample_rate)
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        for index in range(frames):
            value = 0.15 * math.sin(2 * math.pi * freq * index / sample_rate)
            wav_file.writeframesraw(int(value * 32767).to_bytes(2, "little", signed=True))


class StemsModeIntegrationTests(unittest.TestCase):
    def test_stems_mode_allows_direct_plan_but_no_fake_logic_or_plugin_success(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            stems = Path(tmp) / "stems"
            for name, freq in {"drums.wav": 90, "bass.wav": 55, "melody.wav": 330, "vocal.wav": 220}.items():
                write_stem(stems / name, freq)

            plan = build_mix_master_plan(input_mode="stems")

            self.assertTrue((stems / "drums.wav").exists())
            self.assertTrue(plan["stem_chain"]["more_direct_balancing_allowed"])
            self.assertFalse(plan["false_claim_guards"]["plugin_processing_verified"])
            self.assertFalse(plan["false_claim_guards"]["stem_level_remix_claimed"])
            self.assertIn("stem bus balancing decisions by listening", plan["manual_logic_required"])


if __name__ == "__main__":
    unittest.main()

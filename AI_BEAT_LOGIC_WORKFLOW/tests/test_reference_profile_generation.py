from __future__ import annotations

import math
import sys
import tempfile
import unittest
import wave
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_DIR))

from reference_profile import build_reference_target_profile  # noqa: E402


def write_reference_wav(path: Path, sample_rate: int = 48000) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(2)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        for index in range(sample_rate // 2):
            tone = math.sin(2.0 * math.pi * 440.0 * index / sample_rate) * 0.25
            transient = 0.18 if index % 2400 < 80 else 0.0
            value = int(max(-0.9, min(0.9, tone + transient)) * 32767)
            raw = value.to_bytes(2, "little", signed=True)
            wav_file.writeframesraw(raw + raw)


class ReferenceProfileGenerationTests(unittest.TestCase):
    def test_text_only_profile_has_low_or_medium_confidence(self) -> None:
        profile = build_reference_target_profile("ㅇㅇㅇ이라는 곡 베이스처럼 쳐줘", None)

        self.assertEqual(profile["source"]["mode"], "text_only")
        self.assertIn(profile["source"]["confidence"], {"low", "medium"})
        self.assertIn("bass", profile["parsed_intent"]["target_elements"])
        self.assertIn("Text-only references are lower confidence unless reference audio is provided.", profile["legal_and_accuracy_notes"])

    def test_audio_supported_profile_can_be_high_confidence_when_analysis_succeeds(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            reference = Path(tmp) / "reference.wav"
            write_reference_wav(reference)

            profile = build_reference_target_profile("Love Blur 느낌 드럼", str(reference))

        self.assertEqual(profile["source"]["mode"], "text_and_audio")
        self.assertEqual(profile["source"]["confidence"], "high")
        self.assertTrue(profile["audio_analysis"]["available"])
        self.assertIn("drums", profile["parsed_intent"]["target_elements"])

    def test_legal_and_accuracy_notes_exist(self) -> None:
        profile = build_reference_target_profile("hyperpop인데 rage는 너무 싸게 들리지 않게", None)

        notes = profile["legal_and_accuracy_notes"]
        self.assertIn("Reference is used for high-level production attributes only.", notes)
        self.assertIn("Exact melody, sample, drum pattern, lyrics, or sound recording copying is not performed.", notes)
        self.assertIn("Voice identity cloning or impersonation is not performed; artist-style vocal prompts become production-trait targets only.", notes)
        self.assertIn("Text-only references are lower confidence unless reference audio is provided.", notes)

    def test_artist_vocal_reference_is_trait_target_not_identity_clone(self) -> None:
        profile = build_reference_target_profile("make my voice like Nate Sib", None)

        self.assertEqual(profile["source"]["mode"], "text_only")
        self.assertIn(profile["source"]["confidence"], {"low", "medium"})
        self.assertEqual(profile["parsed_intent"]["target_elements"], ["vocal"])
        self.assertEqual(profile["parsed_intent"]["reference_titles"], ["Nate Sib"])
        self.assertFalse(profile["parsed_intent"]["reference_requests"][0]["identity_clone_allowed"])
        self.assertIn("production traits only", profile["parsed_intent"]["reference_requests"][0]["identity_safety_note"])
        self.assertEqual(profile["vocal_targets"]["lead_position"], "front")
        self.assertIn("voice identity cloning", profile["avoid"])


if __name__ == "__main__":
    unittest.main()

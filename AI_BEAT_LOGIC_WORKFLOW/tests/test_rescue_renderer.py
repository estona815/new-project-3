from __future__ import annotations

import math
import sys
import tempfile
import unittest
import wave
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from bad_song_diagnosis import build_bad_song_diagnosis  # noqa: E402
from export_audio import verify_wav  # noqa: E402
from final_verify import verify_final_wav  # noqa: E402
from lead_melody_generator import build_lead_melody_plan  # noqa: E402
from rescue_arrangement_planner import build_rescue_arrangement_plan  # noqa: E402
from rescue_mix_chain import build_rescue_mix, read_audio_file, write_wav24  # noqa: E402
from vocal_texture_rescue import build_vocal_texture_rescue_plan  # noqa: E402


def write_loud_weak_song(path: Path, sample_rate: int = 48_000, seconds: float = 28.0) -> Path:
    frames = int(sample_rate * seconds)
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(2)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        for index in range(frames):
            time = index / sample_rate
            static_tone = 0.44 * math.sin(2.0 * math.pi * 220.0 * time)
            fake_texture = 0.05 * math.sin(2.0 * math.pi * 960.0 * time)
            pulse = 0.08 if index % int(0.25 * sample_rate) < 96 else 0.0
            value = max(-0.95, min(0.95, static_tone + fake_texture + pulse))
            raw = int(value * 32767).to_bytes(2, "little", signed=True)
            wav_file.writeframesraw(raw + raw)
    return path


class RescueRendererTests(unittest.TestCase):
    def test_rescue_mix_chain_adds_generated_lead_and_preserves_headroom(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source = write_loud_weak_song(Path(temp_dir) / "weak.wav")
            diagnosis = build_bad_song_diagnosis(source)
            arrangement = build_rescue_arrangement_plan(
                bad_song_diagnosis=diagnosis,
                creative_brief={"length_mode": "short_30sec"},
                length_mode="short_30sec",
            )
            lead = build_lead_melody_plan(
                tempo=diagnosis["tempo"],
                key={"key": "F# minor", "confidence": "low"},
                section_plan=arrangement,
                style_cluster="system_seoul_adjacent",
            )
            vocal_plan = build_vocal_texture_rescue_plan(
                input_path=source,
                vocal_like_texture_candidates=(diagnosis["vocal_texture"] or {}).get("candidate_regions", []),
                rescue_diagnosis=diagnosis,
            )
            metadata, audio = read_audio_file(source)
            result = build_rescue_mix(
                source_audio=audio,
                source_sample_rate=metadata["sample_rate"],
                arrangement_plan=arrangement,
                lead_plan=lead,
                vocal_texture_plan=vocal_plan,
            )

            self.assertIn("source_music_bus", result["bus_architecture"])
            self.assertTrue(result["bus_reports"]["source_music_bus"]["restructure_applied"])
            self.assertTrue(result["bus_reports"]["generated_lead_bus"]["new_lead_hook_rendered"])
            self.assertLessEqual(result["metrics"]["clipping_count"], 0)
            self.assertLessEqual(result["metrics"]["peak_dbfs"], -2.9)
            self.assertFalse(result["claim_guard"]["stem_level_remix_claimed"])
            self.assertFalse(result["claim_guard"]["vocal_removal_claimed"])

    def test_writes_24bit_48k_rescue_wav(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source = write_loud_weak_song(Path(temp_dir) / "weak.wav")
            diagnosis = build_bad_song_diagnosis(source)
            arrangement = build_rescue_arrangement_plan(bad_song_diagnosis=diagnosis, length_mode="short_30sec")
            lead = build_lead_melody_plan(tempo=diagnosis["tempo"])
            metadata, audio = read_audio_file(source)
            result = build_rescue_mix(
                source_audio=audio,
                source_sample_rate=metadata["sample_rate"],
                arrangement_plan=arrangement,
                lead_plan=lead,
                final_mode=True,
            )
            output = Path(temp_dir) / "final.wav"
            write_wav24(output, result["audio"], result["sample_rate"])
            quick = verify_wav(output)
            final = verify_final_wav(output, "wav24_48k")

            self.assertEqual(quick["sample_rate"], 48_000)
            self.assertEqual(quick["bit_depth"], 24)
            self.assertEqual(quick["channels"], 2)
            self.assertEqual(quick["clipping_count"], 0)
            self.assertTrue(final["ok"])
            self.assertTrue(final["format_verified"])


if __name__ == "__main__":
    unittest.main()

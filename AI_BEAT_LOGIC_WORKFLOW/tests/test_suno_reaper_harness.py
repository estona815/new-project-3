from __future__ import annotations

import math
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_DIR))

from audio_qc import analyze_audio_array  # noqa: E402
from reaper_plugin_inventory import resolve_role  # noqa: E402
from suno_reaper_generator import build_track_entry, render_reaper_lua  # noqa: E402
from suno_source_classifier import (  # noqa: E402
    FEMALE_BGV,
    GUIDE_MIDI,
    PROBLEM_REFERENCE,
    REFERENCE_ONLY,
    TECHNICAL_MIX_REFERENCE,
    VOCAL_ARTIFACT_QUARANTINE,
    classify_source_file,
    production_rebuild_status,
)


class SunoReaperHarnessTests(unittest.TestCase):
    def test_mp3_master_classified_as_reference_only(self) -> None:
        classified = classify_source_file("my_song_MASTER_320k.mp3")
        self.assertIn(classified.category, {PROBLEM_REFERENCE, REFERENCE_ONLY})
        self.assertTrue(classified.reference_only)
        self.assertFalse(classified.production_eligible)

    def test_technical_reference_wav_classified_as_technical_reference(self) -> None:
        classified = classify_source_file("Estona,Nib-Lovee_MASTER_24-48.wav")
        self.assertEqual(classified.category, TECHNICAL_MIX_REFERENCE)
        self.assertTrue(classified.reference_only)
        self.assertFalse(classified.production_eligible)

    def test_production_rebuild_blocked_when_only_reference_exists(self) -> None:
        status = production_rebuild_status([classify_source_file("final_fullmix_MASTER.mp3")])
        self.assertFalse(status["allowed"])
        self.assertEqual(
            status["reason"],
            "Only reference/master files found. Export Suno Studio WAV stems and stem-derived MIDI before rebuilding.",
        )

    def test_female_adlib_double_harmony_classified_as_female_bgv(self) -> None:
        for filename in ("female_adlib.wav", "bgv_double.wav", "wide_harmony_tail.wav", "Backing Vocals.wav"):
            self.assertEqual(classify_source_file(filename).category, FEMALE_BGV)

    def test_random_vocal_chop_terms_classified_as_quarantine(self) -> None:
        for filename in ("ahh_hook.wav", "ooh_random_vox.wav", "yeah_vocal_chop.wav", "moan_adlib.wav"):
            self.assertEqual(classify_source_file(filename).category, VOCAL_ARTIFACT_QUARANTINE)

    def test_mid_files_are_guide_midi(self) -> None:
        classified = classify_source_file("12_Vocals_lead_vocal.mid")
        self.assertEqual(classified.category, GUIDE_MIDI)
        self.assertTrue(classified.guide_only)
        self.assertFalse(classified.production_eligible)

    def test_local_dropout_detection(self) -> None:
        sample_rate = 48_000
        duration = 2.0
        t = np.arange(int(sample_rate * duration), dtype=np.float32) / sample_rate
        audio = np.sin(2.0 * math.pi * 440.0 * t).astype(np.float32) * 0.25
        audio[int(0.9 * sample_rate) : int(1.1 * sample_rate)] = 0.0
        stereo = np.column_stack([audio, audio])
        result = analyze_audio_array(stereo, sample_rate, source_name="lead_vocal.wav")
        issue_types = {issue["issue_type"] for issue in result["issues"]}
        self.assertIn("near_silence_hole", issue_types)

    def test_stereo_phase_anomaly_detection(self) -> None:
        sample_rate = 48_000
        t = np.arange(sample_rate, dtype=np.float32) / sample_rate
        left = np.sin(2.0 * math.pi * 220.0 * t).astype(np.float32) * 0.3
        right = -left
        result = analyze_audio_array(np.column_stack([left, right]), sample_rate, source_name="phasey_stereo.wav")
        issue_types = {issue["issue_type"] for issue in result["issues"]}
        self.assertIn("phase_or_stereo_width_anomaly", issue_types)
        self.assertTrue(result["quarantine_recommended"])

    def test_over_compression_low_dynamic_movement_detection(self) -> None:
        sample_rate = 48_000
        t = np.arange(sample_rate * 2, dtype=np.float32) / sample_rate
        audio = np.sin(2.0 * math.pi * 330.0 * t).astype(np.float32) * 0.45
        result = analyze_audio_array(np.column_stack([audio, audio]), sample_rate, source_name="fullmix_MASTER.wav")
        issue_types = {issue["issue_type"] for issue in result["issues"]}
        self.assertIn("over_compression_low_loudness_range", issue_types)

    def test_reaper_script_contains_artifact_quarantine_bus(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ref = build_track_entry(Path(tmp) / "MASTER_320k.mp3", REFERENCE_ONLY, name="Ref Master")
            quarantine = build_track_entry(Path(tmp) / "yeah_vocal_chop.wav", VOCAL_ARTIFACT_QUARANTINE, name="Yeah Chop")
            lua = render_reaper_lua([ref, quarantine], [], bpm=180)
        self.assertIn("ARTIFACT_QUARANTINE_BUS", lua)
        self.assertIn('bus="REF_BUS"', lua)
        self.assertIn('bus="ARTIFACT_QUARANTINE_BUS"', lua)

    def test_reaper_script_mutes_reference_and_quarantine_tracks_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ref = build_track_entry(Path(tmp) / "fullmix_MASTER.wav", REFERENCE_ONLY, name="Reference")
            quarantine = build_track_entry(Path(tmp) / "random_ooh.wav", VOCAL_ARTIFACT_QUARANTINE, name="Random Ooh")
            lua = render_reaper_lua([ref, quarantine], [], bpm=180)
        self.assertIn('name="Reference"', lua)
        self.assertIn('category="reference_only"', lua)
        self.assertIn('name="QUARANTINE - Random Ooh"', lua)
        self.assertEqual(lua.count("mute=true"), 2)

    def test_reaper_script_creates_vocal_sends_and_ms_control(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            lead = build_track_entry(Path(tmp) / "lead_vocal.wav", "male_lead_vocal", name="Lead")
            lua = render_reaper_lua([lead], [{"time": 1.25, "name": "QC high: test"}], bpm=180)
        self.assertIn("VOCAL_PLATE_SEND", lua)
        self.assertIn("VOCAL_DELAY_SEND", lua)
        self.assertIn("mix_bus_ms_eq", lua)
        self.assertIn("QC high: test", lua)

    def test_plugin_fallback_works_when_premium_missing(self) -> None:
        role = resolve_role("limiter", [])
        self.assertEqual(role["selected_plugin"], "ReaLimit")
        self.assertTrue(role["uses_fallback"])


if __name__ == "__main__":
    unittest.main()

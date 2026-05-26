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

from paths import ensure_folder_structure  # noqa: E402
from reference_profile import build_reference_target_profile  # noqa: E402
from style_translation import run_reference_targeting  # noqa: E402
from edit_plan_generator import build_edit_plan, write_edit_plan  # noqa: E402
from fallback_processing import write_processing_log, FallbackDecision  # noqa: E402
from humanization_rubric import expanded_qc_rubric  # noqa: E402
from master_qc import build_master_qc_report  # noqa: E402
from qc_report import build_qc_report  # noqa: E402


def write_reference_wav(path: Path, sample_rate: int = 48000) -> None:
    frames = sample_rate
    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(2)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        for index in range(frames):
            tone = math.sin(2.0 * math.pi * 440.0 * index / sample_rate) * 0.25
            hat = math.sin(2.0 * math.pi * 8000.0 * index / sample_rate) * (0.12 if index % 2400 < 120 else 0.0)
            value = int(max(-0.8, min(0.8, tone + hat)) * 32767)
            raw = value.to_bytes(2, "little", signed=True)
            wav_file.writeframesraw(raw + raw)


class StyleTranslationTests(unittest.TestCase):
    def test_profile_schema_for_text_only(self) -> None:
        profile = build_reference_target_profile("digicore melody, clean 808, less generic trap", None)

        self.assertEqual(profile["source"]["mode"], "text_only")
        self.assertIn(profile["source"]["confidence"], {"low", "medium"})
        self.assertIn("parsed_intent", profile)
        self.assertIn("target_elements", profile["parsed_intent"])
        self.assertIn("legal_and_accuracy_notes", profile)
        self.assertIn("digicore", profile["style_targets"]["genre_family"])
        self.assertIn(profile["drum_targets"]["kick"], {"short_punchy", "soft", "distorted", "subby", "clicky"})
        self.assertEqual(profile["bass_808_targets"]["tone"], "clean")
        self.assertIn("sub_weight", profile["bass_808_targets"])
        self.assertIn("manual_logic_notes", profile["bass_808_targets"])
        self.assertIn("manual_logic_notes", profile["drum_targets"])
        self.assertIn("predictable generic trap cadence", profile["avoid"])

    def test_run_reference_targeting_writes_outputs_without_copy_claims(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_root = Path(tmp) / "AI_BEAT_LOGIC_WORKFLOW"
            ensure_folder_structure(project_root)
            reference = Path(tmp) / "reference.wav"
            write_reference_wav(reference)

            paths = run_reference_targeting(
                {
                    "reference_text": "love blur type drums, bright emotional hyperpop, clean but hard 808",
                    "reference_audio": str(reference),
                },
                project_root,
            )
            profile = json.loads(paths["reference_target_profile"].read_text(encoding="utf-8"))
            translation = paths["style_translation"].read_text(encoding="utf-8")

            self.assertEqual(profile["source"]["mode"], "text_and_audio")
            self.assertEqual(profile["source"]["confidence"], "high")
            self.assertTrue(profile["audio_analysis"]["available"])
            self.assertGreaterEqual(profile["style_targets"]["drum_density"], 4)
            self.assertIn("What Will Not Be Copied", translation)
            self.assertIn("No exact copyrighted track recreation", translation)
            self.assertIn("parsed target elements", translation)
            self.assertIn("manual notes", translation)
            self.assertNotIn("exact clone", translation.lower().replace("no exact", "no"))

    def test_reference_audio_is_optional(self) -> None:
        profile = build_reference_target_profile("airy adlibs, underground rap vocal upfront", None)

        self.assertEqual(profile["source"]["mode"], "text_only")
        self.assertFalse(profile["audio_analysis"]["available"])
        self.assertEqual(profile["vocal_targets"]["lead_position"], "front")

    def test_creative_brief_feeds_reference_profile(self) -> None:
        profile = build_reference_target_profile(
            "bright hyperpop but cleaner",
            None,
            {
                "avoid_text": "too much reverb, harsh vocal",
                "most_important": "vocal",
                "drum_808": "strong_controlled",
                "vocal_direction": "airy_pop",
                "master_direction": "streaming_safe",
            },
        )

        self.assertTrue(profile["source"]["creative_brief_used"])
        self.assertIn("too much reverb", profile["avoid"])
        self.assertIn("harsh vocal", profile["avoid"])
        self.assertEqual(profile["style_targets"]["vocal_forwardness"], 4)

    def test_edit_plan_uses_reference_target_profile(self) -> None:
        profile = build_reference_target_profile("love blur 느낌 드럼", None)
        analysis = {
            "metadata": {"duration_seconds": 60.0},
            "arrangement_candidates": {},
            "silence_detection": {},
            "vocal_like_texture_candidates": [],
            "melody_buried_candidates": [],
            "low_end_excess_candidates": [],
        }

        plan = build_edit_plan(analysis, {"vocal_mode": "suppress"}, profile)

        self.assertIn("## Creative Brief Summary", plan)
        self.assertIn("## Reference-Inspired Production Target", plan)
        self.assertIn("raw user phrase: love blur 느낌 드럼", plan)
        self.assertIn("what will not be copied", plan)
        self.assertIn("Parsed target elements", plan)
        self.assertIn("Legal/accuracy notes", plan)
        self.assertIn("energetic digital underground drum feel", plan)
        self.assertIn("## Drum Reference Plan", plan)
        self.assertIn("Love Blur drum translation: punchy kick", plan)
        self.assertIn("active but controlled hats", plan)
        self.assertIn("## Drum Programming / Drum Treatment Plan", plan)
        self.assertIn("Do not claim actual drum pattern replacement from a stereo file", plan)
        self.assertIn("cheap rage clipping", plan)
        self.assertIn("## Style Match QC", plan)

    def test_edit_plan_handles_korean_text_only_bass_reference(self) -> None:
        phrase = "ㅇㅇㅇ이라는 곡 베이스처럼 쳐줘"
        creative_brief = {
            "mode": "full_song_stereo",
            "input_files": {"main_input": "/tmp/stereo.wav", "reference_audio": ""},
            "creative_target": phrase,
            "priority": "808/bass",
            "avoid": ["muddy 808", "generic trap loop"],
            "vocal_direction": "suppress vocal texture",
            "drum_808_direction": "strong_controlled",
            "master_direction": "master_ready_headroom",
        }
        profile = build_reference_target_profile(phrase, None, creative_brief)
        analysis = {
            "metadata": {"duration_seconds": 60.0},
            "arrangement_candidates": {},
            "silence_detection": {},
            "vocal_like_texture_candidates": [],
            "melody_buried_candidates": [],
            "low_end_excess_candidates": [],
        }

        plan = build_edit_plan(
            analysis,
            {"creative_brief": creative_brief, "mode": "full_song_stereo", "input": "/tmp/stereo.wav"},
            profile,
        )

        self.assertIn("## Creative Brief Summary", plan)
        self.assertIn(f"- target feeling: {phrase}", plan)
        self.assertIn("## Reference-Inspired Production Target", plan)
        self.assertIn(f"- raw user phrase: {phrase}", plan)
        self.assertIn("parsed reference title: ㅇㅇㅇ", plan)
        self.assertIn("target element: bass", plan)
        self.assertIn("confidence level: low", plan)
        self.assertIn("reference audio provided: no", plan)
        self.assertIn("## Bass / 808 Reference Plan", plan)
        self.assertIn(
            "Text-only reference. Exact bass tone cannot be verified. The plan uses a reference-inspired bass direction: controlled sub, clear 808/bass presence, melody-supportive low-end, no muddy masking.",
            plan,
        )
        self.assertIn("stems, MIDI, or manual Logic layering", plan)
        self.assertIn("## Stereo-Only Limitation", plan)
        self.assertIn("heuristic/stereo-only guidance", plan)

    def test_edit_plan_includes_logic_vocal_checklist_when_vocal_mode_active(self) -> None:
        profile = build_reference_target_profile("underground rap vocal upfront, airy adlibs", None)
        analysis = {
            "metadata": {"duration_seconds": 60.0},
            "arrangement_candidates": {},
            "silence_detection": {},
            "vocal_like_texture_candidates": [],
            "melody_buried_candidates": [],
            "low_end_excess_candidates": [],
        }

        plan = build_edit_plan(
            analysis,
            {"project_mode": "vocal_plus_beat", "vocal_mode": "front", "export_format": "wav24_48k"},
            profile,
        )

        self.assertIn("## Logic Pro Vocal Mix Checklist", plan)
        self.assertIn("### A. Session Setup", plan)
        self.assertIn("Route all vocals to a vocal bus", plan)
        self.assertIn("### C. Lead Vocal Chain", plan)
        self.assertIn("### H. Reference-Inspired Drum Direction", plan)
        self.assertIn("AppleScript automation may help create or import a session, but it cannot fully mix vocals", plan)

    def test_write_edit_plan_can_load_reference_profile_from_temp_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_root = Path(tmp) / "AI_BEAT_LOGIC_WORKFLOW"
            ensure_folder_structure(project_root)
            profile_paths = run_reference_targeting({"reference_text": "love blur 느낌 드럼"}, project_root)
            analysis_path = project_root / "01_ANALYSIS" / "analysis.json"
            analysis_path.write_text(
                json.dumps(
                    {
                        "metadata": {"duration_seconds": 60.0},
                        "arrangement_candidates": {},
                        "silence_detection": {},
                        "vocal_like_texture_candidates": [],
                        "melody_buried_candidates": [],
                        "low_end_excess_candidates": [],
                    }
                ),
                encoding="utf-8",
            )
            output_path = project_root / "02_EDIT_PLAN" / "edit_plan.md"

            write_edit_plan(
                analysis_path=analysis_path,
                output_path=output_path,
                options={"vocal_mode": "suppress"},
                reference_profile_path=profile_paths["reference_target_profile"],
            )

            self.assertIn("Reference-Inspired Production Target", output_path.read_text(encoding="utf-8"))

    def test_fallback_log_and_qc_report_include_style_match_limits(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            log_path = Path(tmp) / "processing_log.md"
            profile = build_reference_target_profile("love blur 느낌 드럼", None)
            verification = {
                "path": "/tmp/fallback.wav",
                "duration_seconds": 10.0,
                "sample_rate": 48000,
                "channels": 2,
                "bit_depth": 24,
                "peak_dbfs": -3.0,
            }

            write_processing_log(
                log_path,
                FallbackDecision(0.0, 10.0, 0.02, 1.0, "test"),
                ["test note"],
                verification,
                None,
                profile,
            )
            log = log_path.read_text(encoding="utf-8")
            qc = build_qc_report(
                {},
                {"arrangement_candidates": {}},
                {**verification, "rms_dbfs": -18.0, "clipping_count": 0, "warnings": [], "passed": True},
                Path("/tmp/final.wav"),
                None,
                "fallback_processed",
                "ffmpeg",
                "not created",
                profile,
            )

            self.assertIn("Stereo fallback cannot replace drum patterns", log)
            self.assertIn("Reference match is limited", log)
            self.assertIn("## Reference Match QC", qc)
            self.assertIn("Drum reference direction match", qc)
            self.assertIn("heuristic/text-only", qc)
            self.assertIn("## Expanded QC Rubric", qc)
            self.assertIn("FAIL_REPROCESS", qc)

    def test_expanded_rubric_never_passes_failed_verification(self) -> None:
        profile = build_reference_target_profile("underground rap vocal upfront, airy adlibs", None)
        rubric = expanded_qc_rubric(
            analysis={"arrangement_candidates": {}},
            verification={"passed": False, "warnings": ["sample rate mismatch"], "clipping_count": 0, "peak_dbfs": -3.0},
            reference_profile=profile,
            options={"project_mode": "vocal_plus_beat", "vocal_mode": "front"},
            source_type="logic_export",
            qc_report_exists=True,
            final_wav_exists=True,
        )

        self.assertEqual(rubric["result"], "FAIL_REPROCESS")
        self.assertIn("final WAV verification failed", rubric["blocking_reasons"])
        self.assertTrue(rubric["vocal_context"])
        self.assertTrue(any(item["id"] == 17 for item in rubric["scores"]))

    def test_master_qc_report_includes_vocal_and_reference_when_applicable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            final_path = Path(tmp) / "final.wav"
            report_path = Path(tmp) / "master_qc_report.md"
            write_reference_wav(final_path)
            report_path.write_text("# Master QC Report\n", encoding="utf-8")
            profile = build_reference_target_profile("underground rap vocal upfront, airy adlibs", None)

            report = build_master_qc_report(
                final_path,
                report_path,
                {"project_mode": "vocal_plus_beat", "vocal_mode": "front", "export_format": "wav24_48k", "source_type": "logic_export"},
                profile,
                {"arrangement_candidates": {}},
            )

            self.assertIn("## Vocal QC", report)
            self.assertIn("## Reference Match QC", report)
            self.assertIn("Lead vocal intelligibility", report)
            self.assertIn("Vocal reference direction match", report)


if __name__ == "__main__":
    unittest.main()

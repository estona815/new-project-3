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

from arrangement_autopilot import run_arrangement_autopilot  # noqa: E402
from completion_gate import check_completion_status  # noqa: E402
from creative_brief import build_creative_brief, write_creative_brief_files  # noqa: E402
from export_audio import write_float_wav  # noqa: E402
from mix_master_autopilot import build_mix_master_plan, write_mix_master_plan  # noqa: E402
from release_package_builder import build_and_write_release_package  # noqa: E402
from song_arrangement_analyzer import write_song_structure_analysis  # noqa: E402


def write_dummy_wav(path: Path, seconds: float = 2.0, freq: float = 220.0, sample_rate: int = 48000, bit_depth: int = 16) -> Path:
    frames = int(seconds * sample_rate)
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(2)
        wav_file.setsampwidth(3 if bit_depth == 24 else 2)
        wav_file.setframerate(sample_rate)
        for index in range(frames):
            time = index / sample_rate
            pulse = 0.25 * math.exp(-(time % 0.5) * 55.0) if (time % 0.5) < 0.06 else 0.0
            value = max(-0.75, min(0.75, pulse + 0.2 * math.sin(2 * math.pi * freq * time)))
            if bit_depth == 24:
                raw = int(value * 8388607).to_bytes(3, "little", signed=True)
            else:
                raw = int(value * 32767).to_bytes(2, "little", signed=True)
            wav_file.writeframesraw(raw + raw)
    return path


def complete_metadata() -> dict[str, object]:
    return {
        "title": "Release Track",
        "artist": "Artist",
        "version": "single",
        "genre": "digicore",
        "language": "ko",
        "explicit": False,
        "isrc": "",
        "upc": "",
        "copyright_year": "2026",
        "copyright_owner": "Artist",
        "producer": "Producer",
        "composer": "Composer",
        "lyricist": "",
        "featured_artists": [],
    }


def clear_rights(**overrides: object) -> dict[str, object]:
    rights: dict[str, object] = {
        "contains_samples": False,
        "source_ownership_confirmed": True,
        "vocal_performer_consent": True,
        "featured_artist_metadata_complete": True,
        "explicit_content_flag_set": True,
    }
    rights.update(overrides)
    return rights


def write_basic_reports(root: Path) -> tuple[Path, Path]:
    qc = root / "06_QC_REPORT" / "qc_report.md"
    master = root / "09_MIX_MASTER" / "master_qc_report.md"
    qc.parent.mkdir(parents=True, exist_ok=True)
    master.parent.mkdir(parents=True, exist_ok=True)
    qc.write_text("# QC\n", encoding="utf-8")
    master.write_text("# Master QC\n", encoding="utf-8")
    return qc, master


def write_release_brief(root: Path, *, workflow: str, rough_request: str, owned_samples: bool = False, owned_stems: bool = False, owned_vocals: bool = False) -> dict:
    brief = build_creative_brief(
        mode="full_song_stereo" if workflow.startswith("song") else "stems" if workflow.startswith("stems") else "vocal_plus_beat" if workflow.startswith("vocal") else "instrumental_beat",
        main_input=None,
        beat_file=None,
        lead_vocal_file=None,
        adlibs_file=None,
        backing_vocal_file=None,
        stems_folder=None,
        reference_audio=None,
        length_mode="15sec_reels" if "릴스" in rough_request else "under_2min",
        length_start=None,
        length_end=None,
        creative_target=rough_request,
        priority="hook",
        avoid="exact copy, voice clone, clipping",
        vocal_direction="polished",
        drum_808_direction="strong_controlled",
        master_direction="streaming_safe",
        export_format="wav24_48k",
        save_logic_project=False,
        raw_full_korean_request=rough_request,
        rough_request=rough_request,
        release_ready=True,
        target_deliverable="release_package",
        zero_clarification=True,
        style_cluster="commercial_digicore",
        workflow=workflow,
        owned_samples=owned_samples,
        owned_stems=owned_stems,
        owned_vocals=owned_vocals,
        release_metadata=complete_metadata(),
    )
    paths = write_creative_brief_files(brief, root)
    return json.loads(paths["json"].read_text(encoding="utf-8"))


class ReleaseReadyWorkflowIntegrationTests(unittest.TestCase):
    def test_song_to_release_plan_only_no_complete_without_verified_final(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            song = write_dummy_wav(root / "input" / "song.wav", seconds=8.0, freq=180.0)
            rough = "마음대로 상업 음악 퀄. 디지코어/하이퍼팝 결, 808 강하게, 릴스 훅."
            brief = write_release_brief(root, workflow="song_to_release", rough_request=rough)

            write_song_structure_analysis(song, project_root=root, mode="full_song_stereo")
            arrangement = run_arrangement_autopilot(project_root=root, sample_path=song, genre="commercial_digicore", request_text=rough)
            mix_plan = build_mix_master_plan(input_mode="full_song_stereo", style_target="commercial_digicore_hyperpop", master_target_mode="streaming_safe")
            mix_paths = write_mix_master_plan(root, mix_plan)
            package = build_and_write_release_package(root, final_master_path=None, metadata={"title": "Draft"}, rights=clear_rights())
            status = check_completion_status(
                final_wav_path=None,
                qc_report_path=root / "06_QC_REPORT" / "qc_report.md",
                requested_format="wav24_48k",
                require_release_package=True,
                release_package_manifest_path=package["paths"]["manifest"],
                release_qc_report_path=package["paths"]["release_qc_report"],
            )

            self.assertEqual(brief["workflow"], "song_to_release")
            self.assertTrue((root / "01_ANALYSIS" / "song_structure_analysis.json").exists())
            self.assertEqual(arrangement["plan"]["status"], "ARRANGEMENT_PLAN_READY")
            self.assertTrue(mix_paths["json"].exists())
            self.assertFalse(package["manifest"]["release_ready"])
            self.assertFalse(status.complete)
            self.assertNotEqual(package["manifest"]["release_status"], "COMPLETE")


if __name__ == "__main__":
    unittest.main()

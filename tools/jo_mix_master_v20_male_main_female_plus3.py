#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path("/Users/hantaeheuk/Documents/New project 3")
BASE = ROOT / "tools/chuchu_v03_male_main_center.py"

spec = importlib.util.spec_from_file_location("chuchu_v03_engine", BASE)
if spec is None or spec.loader is None:
    raise RuntimeError(f"Could not load {BASE}")
engine = importlib.util.module_from_spec(spec)
spec.loader.exec_module(engine)

SLUG = "jo_mix_master_v20_male_main_female_plus3"
SOURCE = ROOT / "audio_work/jo_mix_master_v01/source_stems"
engine.SLUG = SLUG
engine.SOURCE = SOURCE
engine.PROCESSED = ROOT / "audio_work" / SLUG / "processed_stems"
engine.REAPER_DIR = ROOT / "reaper" / SLUG
engine.RENDERS = ROOT / "renders" / SLUG
engine.REPORTS = ROOT / "reports" / SLUG
engine.RPP = engine.REAPER_DIR / "jo_mix_master_v20_MALE_MAIN_FEMALE_PLUS3.rpp"
engine.BUILD_LUA = engine.REAPER_DIR / "build_jo_mix_master_v20_male_main_female_plus3.lua"
engine.RUN_BUILD_LUA = engine.REAPER_DIR / "run_build_jo_mix_master_v20_male_main_female_plus3.lua"
engine.RENDER_LUA = engine.REAPER_DIR / "render_jo_mix_master_v20_male_main_female_plus3.lua"
engine.RUN_RENDER_LUA = engine.REAPER_DIR / "run_render_jo_mix_master_v20_male_main_female_plus3.lua"
engine.TRACE_JSON = engine.REPORTS / "actual_reaper_plugin_trace.json"
engine.TRACE_MD = engine.REPORTS / "actual_reaper_plugin_trace.md"
engine.REAPER_PRINT = engine.RENDERS / "jo_mix_master_v20_MALE_MAIN_FEMALE_PLUS3_REAPERPRINT_24-48.wav"
engine.FINAL_WAV = engine.RENDERS / "jo_mix_master_v20_MALE_MAIN_FEMALE_PLUS3_FINAL.wav"
engine.FINAL_MP3 = engine.RENDERS / "jo_mix_master_v20_MALE_MAIN_FEMALE_PLUS3_FINAL_320k.mp3"
engine.VOCAL_SOLO = engine.RENDERS / "jo_mix_master_v20_VOCAL_SOLO_male_main_female_plus3.wav"
engine.MALE_SOLO = engine.RENDERS / "jo_mix_master_v20_MALE_ONLY_center_check.wav"
engine.AB_V02_TO_V03 = engine.RENDERS / "jo_mix_master_v20_AB_source_to_v20_320k.mp3"
engine.DELIVERABLE_ZIP = engine.RENDERS / "jo_mix_master_v20_MALE_MAIN_FEMALE_PLUS3_DELIVERABLE.zip"
engine.REPORT_MD = engine.REPORTS / "jo_mix_master_v20_male_main_female_plus3_report.md"
engine.V02_FINAL = SOURCE / "0 ㅈㅇ.wav"
engine.V01_FINAL = SOURCE / "0 ㅈㅇ.wav"
engine.base.REPORTS = engine.REPORTS


def stems() -> dict[str, Path]:
    silent = SOURCE / "7 Backing_Vocals.wav"
    return {
        "full_reference": SOURCE / "0 ㅈㅇ.wav",
        "brass": silent,
        "fx": SOURCE / "1 FX.wav",
        "synth": SOURCE / "2 Synth.wav",
        "keyboard": SOURCE / "3 Keyboard.wav",
        "guitar": SOURCE / "4 Guitar.wav",
        "bass": SOURCE / "5 Bass.wav",
        "drums": SOURCE / "6 Drums.wav",
        "male_vocal": SOURCE / "9 Vocals.wav",
        "female_vocal": SOURCE / "8 Vocals.wav",
        "new_track_silent": silent,
    }


original_write_reaper_scripts = engine.write_reaper_scripts


def patch_generated_lua() -> None:
    replacements = {
        "chuchu_v03_MALE_MAIN_REAPERPRINT_24-48": "jo_mix_master_v20_MALE_MAIN_FEMALE_PLUS3_REAPERPRINT_24-48",
        "chuchu v03: 8 Vocals is male main center loud; 9 Vocals is female panned low layer only. Female vocal must not be main.": (
            "jo v20 rebuilt from stems: 9 Vocals is male main center; 8 Vocals is a more tucked panned female support layer only."
        ),
        "08 MALE MAIN VOCAL center loud": "09 MALE MAIN VOCAL center",
        "09 female vocal panned low layer only": "08 female vocal tucked support layer only",
        "volume_db=-5.200000, pan=0.680000": "volume_db=-6.200000, pan=0.680000",
        '"slug": "chuchu_v03_male_main_center"': '"slug": "jo_mix_master_v20_male_main_female_plus3"',
    }
    for path in (engine.BUILD_LUA, engine.RENDER_LUA):
        text = path.read_text(encoding="utf-8")
        for old, new in replacements.items():
            text = text.replace(old, new)
        path.write_text(text, encoding="utf-8")


def write_reaper_scripts(processed: dict[str, Path], duration: float) -> None:
    original_write_reaper_scripts(processed, duration)
    patch_generated_lua()


original_write_reports = engine.write_reports


def write_reports(paths: dict[str, Path], selection: dict[str, object], gate: dict[str, object]) -> dict[str, object]:
    summary = original_write_reports(paths, selection, gate)
    notes = engine.REPORT_MD.read_text(encoding="utf-8")
    notes = notes.replace("Chuchu v03 Male Main Center Report", "Jo v20 Rebuilt Male Main Female Support Report")
    notes = notes.replace("`8 Vocals.wav` is treated as the male main vocal, loud and centered.", "`9 Vocals.wav` is treated as the male main vocal, loud and centered.")
    notes = notes.replace("`9 Vocals.wav` is treated as a low panned female side layer only.", "`8 Vocals.wav` is treated as a panned female side layer raised +3 dB at track level.")
    notes += (
        "\n## v20 Revision\n\n"
        "- Source: `audio_work/jo_mix_master_v01/source_stems`.\n"
        "- Male main: `9 Vocals.wav`, centered.\n"
        "- Female layer: `8 Vocals.wav`, panned right and lowered to -6.2 dB so it stays a tucked support layer only.\n"
        "- Full mix `0 ㅈㅇ.wav` remains muted reference only.\n"
    )
    engine.REPORT_MD.write_text(notes, encoding="utf-8")
    summary["female_track_revision_db"] = -1.0
    summary["female_reaper_track_db"] = -6.2
    engine.write_json(engine.REPORTS / "qc_summary.json", summary)
    return summary


engine.stems = stems
engine.write_reaper_scripts = write_reaper_scripts
engine.write_reports = write_reports


if __name__ == "__main__":
    raise SystemExit(engine.main())

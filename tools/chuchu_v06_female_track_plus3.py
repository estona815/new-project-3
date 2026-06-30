#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path("/Users/hantaeheuk/Documents/New project 3")
BASE = ROOT / "tools/chuchu_v03_male_main_center.py"

spec = importlib.util.spec_from_file_location("chuchu_v03", BASE)
if spec is None or spec.loader is None:
    raise RuntimeError(f"Could not load {BASE}")
v03 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v03)

SLUG = "chuchu_v06_female_track_plus3"
v03.SLUG = SLUG
v03.PROCESSED = ROOT / "audio_work" / SLUG / "processed_stems"
v03.REAPER_DIR = ROOT / "reaper" / SLUG
v03.RENDERS = ROOT / "renders" / SLUG
v03.REPORTS = ROOT / "reports" / SLUG
v03.RPP = v03.REAPER_DIR / "chuchu_v06_FEMALE_TRACK_PLUS3.rpp"
v03.BUILD_LUA = v03.REAPER_DIR / "build_chuchu_v06_female_track_plus3.lua"
v03.RUN_BUILD_LUA = v03.REAPER_DIR / "run_build_chuchu_v06_female_track_plus3.lua"
v03.RENDER_LUA = v03.REAPER_DIR / "render_chuchu_v06_female_track_plus3.lua"
v03.RUN_RENDER_LUA = v03.REAPER_DIR / "run_render_chuchu_v06_female_track_plus3.lua"
v03.TRACE_JSON = v03.REPORTS / "actual_reaper_plugin_trace.json"
v03.TRACE_MD = v03.REPORTS / "actual_reaper_plugin_trace.md"
v03.REAPER_PRINT = v03.RENDERS / "chuchu_v06_FEMALE_TRACK_PLUS3_REAPERPRINT_24-48.wav"
v03.FINAL_WAV = v03.RENDERS / "chuchu_v06_FEMALE_TRACK_PLUS3_FINAL.wav"
v03.FINAL_MP3 = v03.RENDERS / "chuchu_v06_FEMALE_TRACK_PLUS3_FINAL_320k.mp3"
v03.VOCAL_SOLO = v03.RENDERS / "chuchu_v06_VOCAL_SOLO_female_plus3.wav"
v03.MALE_SOLO = v03.RENDERS / "chuchu_v06_MALE_ONLY_center_check.wav"
v03.AB_V02_TO_V03 = v03.RENDERS / "chuchu_v06_AB_v03_to_v06_320k.mp3"
v03.DELIVERABLE_ZIP = v03.RENDERS / "chuchu_v06_FEMALE_TRACK_PLUS3_DELIVERABLE.zip"
v03.REPORT_MD = v03.REPORTS / "chuchu_v06_female_track_plus3_report.md"
v03.V02_FINAL = ROOT / "renders/chuchu_v03_male_main_center/chuchu_v03_MALE_MAIN_CENTER_FINAL.wav"
v03.base.REPORTS = v03.REPORTS


original_write_reaper_scripts = v03.write_reaper_scripts


def patch_generated_lua() -> None:
    replacements = {
        "chuchu_v03_MALE_MAIN_REAPERPRINT_24-48": "chuchu_v06_FEMALE_TRACK_PLUS3_REAPERPRINT_24-48",
        "chuchu v03: 8 Vocals is male main center loud; 9 Vocals is female panned low layer only. Female vocal must not be main.": (
            "chuchu v06 rebuilt from stems: 8 Vocals is male main center; 9 Vocals is a more tucked panned female support layer only."
        ),
        "09 female vocal panned low layer only": "09 female vocal tucked support layer only",
        "volume_db=-5.200000, pan=0.680000": "volume_db=-6.200000, pan=0.680000",
        '"slug": "chuchu_v03_male_main_center"': '"slug": "chuchu_v06_female_track_plus3"',
    }
    for path in (v03.BUILD_LUA, v03.RENDER_LUA):
        text = path.read_text(encoding="utf-8")
        for old, new in replacements.items():
            text = text.replace(old, new)
        path.write_text(text, encoding="utf-8")


def write_reaper_scripts(processed: dict[str, Path], duration: float) -> None:
    original_write_reaper_scripts(processed, duration)
    patch_generated_lua()


original_write_reports = v03.write_reports


def write_reports(paths: dict[str, Path], selection: dict[str, object], gate: dict[str, object]) -> dict[str, object]:
    summary = original_write_reports(paths, selection, gate)
    notes = v03.REPORT_MD.read_text(encoding="utf-8")
    notes = notes.replace("Chuchu v03 Male Main Center Report", "Chuchu v06 Rebuilt Female Support Layer Report")
    notes += (
        "\n## v06 Revision\n\n"
        "- Rebuilt from source stems again with the male-centered vocal processing and arrangement timing preserved.\n"
        "- Lowered the panned female support track from -5.2 dB to -6.2 dB so it stays a layer only.\n"
        "- Female vocal remains panned and tucked under the centered male main.\n"
    )
    v03.REPORT_MD.write_text(notes, encoding="utf-8")
    summary["female_track_revision_db"] = -1.0
    summary["female_reaper_track_db"] = -6.2
    v03.write_json(v03.REPORTS / "qc_summary.json", summary)
    return summary


v03.write_reaper_scripts = write_reaper_scripts
v03.write_reports = write_reports


if __name__ == "__main__":
    raise SystemExit(v03.main())

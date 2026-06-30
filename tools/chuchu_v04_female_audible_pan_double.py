#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import shutil
from pathlib import Path

import numpy as np


ROOT = Path("/Users/hantaeheuk/Documents/New project 3")
BASE = ROOT / "tools/chuchu_v03_male_main_center.py"
spec = importlib.util.spec_from_file_location("chuchu_v03", BASE)
if spec is None or spec.loader is None:
    raise RuntimeError(f"Could not load {BASE}")
v03 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v03)

SLUG = "chuchu_v04_female_audible_pan_double"
v03.SLUG = SLUG
v03.PROCESSED = ROOT / "audio_work" / SLUG / "processed_stems"
v03.REAPER_DIR = ROOT / "reaper" / SLUG
v03.RENDERS = ROOT / "renders" / SLUG
v03.REPORTS = ROOT / "reports" / SLUG
v03.RPP = v03.REAPER_DIR / "chuchu_v04_MALE_MAIN_FEMALE_AUDIBLE_DOUBLE.rpp"
v03.BUILD_LUA = v03.REAPER_DIR / "build_chuchu_v04_female_audible_pan_double.lua"
v03.RUN_BUILD_LUA = v03.REAPER_DIR / "run_build_chuchu_v04_female_audible_pan_double.lua"
v03.RENDER_LUA = v03.REAPER_DIR / "render_chuchu_v04_female_audible_pan_double.lua"
v03.RUN_RENDER_LUA = v03.REAPER_DIR / "run_render_chuchu_v04_female_audible_pan_double.lua"
v03.TRACE_JSON = v03.REPORTS / "actual_reaper_plugin_trace.json"
v03.TRACE_MD = v03.REPORTS / "actual_reaper_plugin_trace.md"
v03.REAPER_PRINT = v03.RENDERS / "chuchu_v04_MALE_MAIN_FEMALE_DOUBLE_REAPERPRINT_24-48.wav"
v03.FINAL_WAV = v03.RENDERS / "chuchu_v04_MALE_MAIN_FEMALE_DOUBLE_FINAL.wav"
v03.FINAL_MP3 = v03.RENDERS / "chuchu_v04_MALE_MAIN_FEMALE_DOUBLE_FINAL_320k.mp3"
v03.VOCAL_SOLO = v03.RENDERS / "chuchu_v04_VOCAL_SOLO_male_main_female_double.wav"
v03.MALE_SOLO = v03.RENDERS / "chuchu_v04_MALE_ONLY_center_check.wav"
v03.AB_V02_TO_V03 = v03.RENDERS / "chuchu_v04_AB_v03_to_v04_320k.mp3"
v03.DELIVERABLE_ZIP = v03.RENDERS / "chuchu_v04_MALE_MAIN_FEMALE_DOUBLE_DELIVERABLE.zip"
v03.REPORT_MD = v03.REPORTS / "chuchu_v04_female_audible_pan_double_report.md"
v03.V02_FINAL = ROOT / "renders/chuchu_v03_male_main_center/chuchu_v03_MALE_MAIN_CENTER_FINAL.wav"
v03.base.REPORTS = v03.REPORTS


def process_female_side(y: np.ndarray, sr: int, male: np.ndarray) -> np.ndarray:
    x = v03.base.process_female_layer(y, sr, male, target_delta_db=-8.2)
    x = v03.base.butter_filter(x, sr, "highpass", 145, 2)
    x = v03.base.dynamic_band_tame(x, sr, 5600, 9800, max_cut_db=2.1, percentile=56.0, slope=0.72, smooth_ms=7.0)
    mono = np.mean(x, axis=1).astype(np.float32)
    left = v03.base.haas_layer(mono, sr, pan=-0.66, delay_ms=10.0)
    right = v03.base.haas_layer(mono, sr, pan=0.66, delay_ms=16.0)
    panned = (left * 0.52 + right * 0.48).astype(np.float32)
    panned = v03.base.match_active_rms(panned, v03.base.active_rms_db(male) - 8.0, max_gain_db=18.0)
    panned = v03.base.sidechain_band_duck(panned, male, sr, 2200, 4300, max_cut_db=0.35, percentile=52.0, smooth_ms=95.0)
    return v03.base.peak_cap(panned.astype(np.float32), -5.6)


def patch_generated_lua() -> None:
    replacements = {
        "chuchu_v03_MALE_MAIN_REAPERPRINT_24-48": "chuchu_v04_MALE_MAIN_FEMALE_DOUBLE_REAPERPRINT_24-48",
        "chuchu v03: 8 Vocals is male main center loud; 9 Vocals is female panned low layer only. Female vocal must not be main.": (
            "chuchu v04: 8 Vocals is male main center loud; 9 Vocals is audible panned female double/layer. "
            "Female vocal is present throughout but must not be main."
        ),
        "09 female vocal panned low layer only": "09 female vocal audible panned double layer",
        "volume_db=-5.200000, pan=0.680000": "volume_db=-1.400000, pan=0.620000",
        '"slug": "chuchu_v03_male_main_center"': '"slug": "chuchu_v04_female_audible_pan_double"',
    }
    for path in (v03.BUILD_LUA, v03.RENDER_LUA):
        text = path.read_text(encoding="utf-8")
        for old, new in replacements.items():
            text = text.replace(old, new)
        path.write_text(text, encoding="utf-8")


original_write_reaper_scripts = v03.write_reaper_scripts


def write_reaper_scripts(processed: dict[str, Path], duration: float) -> None:
    original_write_reaper_scripts(processed, duration)
    patch_generated_lua()


original_write_reports = v03.write_reports


def write_reports(paths: dict[str, Path], selection: dict[str, object], gate: dict[str, object]) -> dict[str, object]:
    summary = original_write_reports(paths, selection, gate)
    notes = v03.REPORT_MD.read_text(encoding="utf-8")
    notes = notes.replace("Chuchu v03 Male Main Center Report", "Chuchu v04 Female Audible Pan Double Report")
    notes = notes.replace("`9 Vocals.wav` is treated as a low panned female side layer only.", "`9 Vocals.wav` is an audible panned female double/layer, not the lead.")
    notes = notes.replace("REAPER female track is additionally panned right and attenuated.", "REAPER female track is panned right and kept audibly under the male center vocal.")
    notes += "\n## v04 Revision\n\n- Raised the female panned layer from v03 so it remains audible as a double throughout.\n- Male vocal remains the centered lead; female vocal stays separated by pan and lower level.\n"
    v03.REPORT_MD.write_text(notes, encoding="utf-8")
    return summary


v03.process_female_side = process_female_side
v03.write_reaper_scripts = write_reaper_scripts
v03.write_reports = write_reports


if __name__ == "__main__":
    raise SystemExit(v03.main())

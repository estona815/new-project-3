#!/usr/bin/env python3
from __future__ import annotations

import csv
import importlib.util
import json
import subprocess
from pathlib import Path
from typing import Any

import numpy as np


ROOT = Path("/Users/hantaeheuk/Documents/New project 3")
V16B_SCRIPT = ROOT / "tools" / "mwolla_v16b_source_stem_repair_reference_density_master.py"
SLUG = "mwolla_v21_fresh_all_stems_rebuild_master"
ZIP_SOURCE = Path("/Users/hantaeheuk/Downloads/몰라.zip")


spec = importlib.util.spec_from_file_location("mwolla_v16b_source_stem_repair_reference_density_master", V16B_SCRIPT)
if spec is None or spec.loader is None:
    raise RuntimeError(f"Could not load v16B script: {V16B_SCRIPT}")
v16b = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v16b)

base = v16b.base
v11 = v16b.v11


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    keys: list[str] = []
    for row in rows:
        for key in row:
            if key not in keys:
                keys.append(key)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)


def write_wav(path: Path, sr: int, y: np.ndarray) -> None:
    base.write_wav(path, sr, y.astype(np.float32))


def db_to_amp(db: float | np.ndarray) -> np.ndarray:
    return np.power(10.0, np.asarray(db) / 20.0)


def amp_to_db(value: float | np.ndarray) -> np.ndarray:
    return 20.0 * np.log10(np.maximum(np.asarray(value), 1e-12))


def pad_or_trim(y: np.ndarray, length: int) -> np.ndarray:
    return v16b.pad_or_trim(y, length)


def configure_base() -> None:
    v16b.SLUG = SLUG
    v16b.ZIP_SOURCE = ZIP_SOURCE
    v16b.configure_base()

    base.ZIP_SOURCE = ZIP_SOURCE
    base.SLUG = SLUG
    base.WORK = ROOT / "audio_work" / SLUG
    base.SOURCE = base.WORK / "source_stems"
    base.PROCESSED = base.WORK / "processed_stems"
    base.REAPER_DIR = ROOT / "reaper" / SLUG
    base.RENDERS = ROOT / "renders" / SLUG
    base.REPORTS = ROOT / "reports" / SLUG

    base.RPP = base.REAPER_DIR / "mwolla_v21_FULL_STEM_HARMONY_MASTER.rpp"
    base.BUILD_LUA = base.REAPER_DIR / "build_mwolla_v21_fresh_all_stems_rebuild_master.lua"
    base.RUN_BUILD_LUA = base.REAPER_DIR / "run_build_mwolla_v21_fresh_all_stems_rebuild_master.lua"
    base.RENDER_LUA = base.REAPER_DIR / "render_mwolla_v21_fresh_all_stems_rebuild_master.lua"
    base.RUN_RENDER_LUA = base.REAPER_DIR / "run_render_mwolla_v21_fresh_all_stems_rebuild_master.lua"
    base.TRACE_JSON = base.REPORTS / "actual_reaper_plugin_trace.json"
    base.TRACE_MD = base.REPORTS / "actual_reaper_plugin_trace.md"

    base.REAPER_PRINT = base.RENDERS / "mwolla_v21_REAPERPRINT_24-48.wav"
    base.FINAL_WAV = base.RENDERS / "mwolla_v21_FULL_STEM_HARMONY_MASTER.wav"
    base.FINAL_MP3 = base.RENDERS / "mwolla_v21_FULL_STEM_HARMONY_MASTER_320k.mp3"
    base.VOCAL_SOLO = base.RENDERS / "mwolla_v21_VOCAL_SOLO_full_stem_harmony.wav"
    base.AB_PREVIEW_MP3 = base.RENDERS / "mwolla_v21_AB_v19_to_full_stem_harmony_320k.mp3"
    base.DELIVERABLE_ZIP = base.RENDERS / "mwolla_v21_FULL_STEM_HARMONY_MASTER_DELIVERABLE.zip"

    base.REPORT_FILENAME = "mwolla_v21_fresh_all_stems_rebuild_master_report.md"
    base.REPORT_TITLE = "Mwolla v21 Full Stem Harmony Master Report"
    base.PROJECT_NOTES = (
        "mwolla v21: v19 louder clear vocal candidate preserved, with upstream printed stem-harmony fullness. "
        "Music/support stems receive measured active-RMS lifts, band-limited density, and peak guards instead of a "
        "single broad master push. No external plugin parameter writes and no new Ozone/OTT/clipper insert automation."
    )

    v11.PHRASE_PREMASTER_NAME = "mwolla_v21_PHRASE_SAFE_FULL_STEM_HARMONY_PREMASTER_24-48.wav"
    v11.FINAL_LOCKED_NAME = "mwolla_v21_POST_FINAL_FULL_STEM_HARMONY_TRUE_PEAK_SAFE_24-48.wav"


def band_rms_db(y: np.ndarray, sr: int, low: float, high: float) -> float:
    band = base.butter_filter(y.astype(np.float32), sr, "bandpass", (low, high), order=3)
    return round(float(amp_to_db(base.rms(band))), 2)


def vocal_metrics(y: np.ndarray, sr: int) -> dict[str, Any]:
    return {
        "active_rms_db": round(base.active_rms_db(y), 2),
        "rms_dbfs": round(float(amp_to_db(base.rms(y))), 2),
        "peak_dbfs": round(float(amp_to_db(np.max(np.abs(y)) if len(y) else 0.0)), 2),
        "crest_factor_db": round(float(amp_to_db(np.max(np.abs(y)) if len(y) else 0.0) - amp_to_db(base.rms(y))), 2),
        "mud_250_500_db": band_rms_db(y, sr, 250, 500),
        "presence_1500_5000_db": band_rms_db(y, sr, 1500, 5000),
        "sibilance_5000_9000_db": band_rms_db(y, sr, 5000, 9000),
        "air_10000_16000_db": band_rms_db(y, sr, 10000, 16000),
    }


def ott_style_vocal_parallel(y: np.ndarray, sr: int) -> tuple[np.ndarray, dict[str, Any]]:
    dry = y.astype(np.float32)
    low = base.butter_filter(dry, sr, "lowpass", 170.0, order=2)
    mid = base.butter_filter(dry, sr, "bandpass", (170.0, 5000.0), order=3)
    high = base.butter_filter(dry, sr, "bandpass", (5000.0, 12000.0), order=3)
    top = base.butter_filter(dry, sr, "highpass", 10000.0, order=2)

    mid_dense = base.compressor(mid, sr, threshold_db=-33.0, ratio=2.15, attack_ms=3.0, release_ms=86.0, makeup_db=0.42)
    high_dense = base.compressor(high, sr, threshold_db=-38.0, ratio=1.75, attack_ms=2.0, release_ms=68.0, makeup_db=0.18)
    parallel = dry + (mid_dense - mid) * 0.11 + (high_dense - high) * 0.065 + top * 0.018
    saturated = base.soft_saturation(parallel, drive_db=0.62, mix=0.035)
    guarded = base.dynamic_band_tame(saturated, sr, 5200, 9200, max_cut_db=0.46, percentile=63.0, slope=0.42, smooth_ms=7.0)
    guarded = base.rbj_peaking(guarded, sr, 3100.0, 0.16, 0.95)
    guarded = base.rbj_shelf(guarded, sr, 10600.0, 0.12, high=True, slope=0.70)
    guarded = base.match_active_rms(guarded, base.active_rms_db(dry) + 0.22, max_gain_db=0.35)
    guarded = base.peak_cap(guarded.astype(np.float32), -5.35)
    report = {
        "style": "printed OTT-style parallel vocal density, not an external OTT parameter write",
        "mid_band_hz": [170.0, 5000.0],
        "high_band_hz": [5000.0, 12000.0],
        "parallel_mid_delta_mix": 0.11,
        "parallel_high_delta_mix": 0.065,
        "saturation_drive_db": 0.62,
        "saturation_mix": 0.035,
        "post_ott_anti_fizz_hz": [5200.0, 9200.0],
        "post_ott_anti_fizz_max_cut_db": 0.46,
        "presence_lift_3100_hz_db": 0.16,
        "air_shelf_10600_hz_db": 0.12,
        "target_active_rms_lift_db": 0.22,
        "peak_cap_dbfs": -5.35,
    }
    return guarded.astype(np.float32), report


def apply_v19_vocal_polish(processed: dict[str, Path], sr: int, length: int) -> dict[str, Any]:
    lead_path = processed["lead_vocal"]
    lead_sr, lead, _ = base.read_wav(lead_path)
    if lead_sr != sr:
        raise RuntimeError("Sample-rate mismatch in v19 lead vocal polish")
    lead = pad_or_trim(lead, length)
    before = vocal_metrics(lead, sr)
    polished, settings = ott_style_vocal_parallel(lead, sr)
    polished = pad_or_trim(polished, length)
    write_wav(lead_path, sr, polished)
    after = vocal_metrics(polished, sr)
    report = {
        "schema": "mwolla-v19-vocal-ott-style-saturation-v1",
        "target": "subtle vocal density and clarity without phrase chopping or extra external plugin writes",
        "lead_vocal_path": rel(lead_path),
        "before": before,
        "after": after,
        "settings": settings,
        "guards": {
            "first_slot_vocal_rescue_preserved_in_reaper": True,
            "post_ott_anti_fizz_printed": True,
            "external_plugin_parameter_writes": "none_added",
        },
    }
    write_json(base.REPORTS / "v19_vocal_ott_saturation_report.json", report)
    write_csv(
        base.REPORTS / "v19_vocal_ott_saturation_report.csv",
        [
            {
                "metric": key,
                "before": before.get(key),
                "after": after.get(key),
                "delta": round(float(after[key]) - float(before[key]), 2) if isinstance(before.get(key), (int, float)) and isinstance(after.get(key), (int, float)) else "",
            }
            for key in before
        ],
    )
    return report


STEM_HARMONY_TARGETS: dict[str, dict[str, float]] = {
    "bass": {"lift_db": 0.55, "peak_cap_dbfs": -1.70},
    "drums": {"lift_db": 0.65, "peak_cap_dbfs": -1.65},
    "synth": {"lift_db": 0.80, "peak_cap_dbfs": -2.00},
    "strings": {"lift_db": 0.62, "peak_cap_dbfs": -2.05},
    "keyboard": {"lift_db": 0.72, "peak_cap_dbfs": -2.00},
    "guitar": {"lift_db": 0.72, "peak_cap_dbfs": -2.00},
    "fx": {"lift_db": 0.52, "peak_cap_dbfs": -2.70},
    "percussion": {"lift_db": 0.36, "peak_cap_dbfs": -2.20},
    "woodwinds": {"lift_db": 0.24, "peak_cap_dbfs": -2.50},
    "brass": {"lift_db": 0.24, "peak_cap_dbfs": -2.50},
    "backing_vocals": {"lift_db": 0.44, "peak_cap_dbfs": -3.10},
    "female_vocal": {"lift_db": 0.30, "peak_cap_dbfs": -3.05},
    "vocal_reverb": {"lift_db": 0.18, "peak_cap_dbfs": -3.40},
    "vocal_delay": {"lift_db": 0.20, "peak_cap_dbfs": -3.35},
}

SECTION_STEM_FILL_WINDOWS: list[dict[str, float | str]] = [
    {"start_s": 52.5, "end_s": 54.0, "gain_db": 0.28, "reason": "pre-hook density fill"},
    {"start_s": 78.0, "end_s": 84.0, "gain_db": 0.42, "reason": "late-section density fill"},
    {"start_s": 88.5, "end_s": 90.63, "gain_db": 0.30, "reason": "tail density fill"},
]


def stem_harmony_metrics(y: np.ndarray, sr: int) -> dict[str, Any]:
    return v16b.stem_metrics(y.astype(np.float32), sr)


def section_fill_factor(key: str) -> float:
    if key in {"bass", "drums", "synth", "strings", "keyboard", "guitar"}:
        return 1.0
    if key == "fx":
        return 0.70
    if key in {"female_vocal", "backing_vocals"}:
        return 0.62
    if key in {"vocal_reverb", "vocal_delay"}:
        return 0.55
    return 0.45


def apply_smooth_section_stem_fill(y: np.ndarray, sr: int, key: str) -> tuple[np.ndarray, list[str]]:
    factor = section_fill_factor(key)
    if factor <= 0.0 or not v16b.non_silent(y):
        return y.astype(np.float32), []
    env = np.ones(len(y), dtype=np.float32)
    applied: list[str] = []
    ramp = max(1, int(round(sr * 0.085)))
    for window in SECTION_STEM_FILL_WINDOWS:
        start = max(0, int(round(float(window["start_s"]) * sr)))
        end = min(len(y), int(round(float(window["end_s"]) * sr)))
        if end <= start:
            continue
        gain_db = float(window["gain_db"]) * factor
        gain = float(db_to_amp(gain_db))
        local = np.ones(end - start, dtype=np.float32)
        fade = min(ramp, max(1, (end - start) // 2))
        if fade > 1:
            local[:] = gain
            local[:fade] = np.linspace(1.0, gain, fade, dtype=np.float32)
            local[-fade:] = np.linspace(gain, 1.0, fade, dtype=np.float32)
        else:
            local[:] = gain
        env[start:end] = np.maximum(env[start:end], local)
        applied.append(f"{window['reason']}_{gain_db:.2f}db_{float(window['start_s']):.1f}-{float(window['end_s']):.1f}s")
    return (y.astype(np.float32) * env[:, None]).astype(np.float32), applied


def harmonic_fullness_for_stem(key: str, y: np.ndarray, lead: np.ndarray, sr: int) -> tuple[np.ndarray, list[str]]:
    if not v16b.non_silent(y):
        return y.astype(np.float32), ["silent_or_missing_role_asset_no_processing"]

    before_active = base.active_rms_db(y)
    target = STEM_HARMONY_TARGETS.get(key, {"lift_db": 0.20, "peak_cap_dbfs": -2.50})
    lift_db = float(target["lift_db"])
    peak_cap_dbfs = float(target["peak_cap_dbfs"])
    out = y.astype(np.float32)
    moves: list[str] = []

    if key == "bass":
        out = v16b.band_parallel_density(out, sr, 42, 145, drive_db=0.72, mix=0.055, comp_ratio=1.45, threshold_db=-33.0)
        out = v16b.band_parallel_density(out, sr, 145, 520, drive_db=0.42, mix=0.030, comp_ratio=1.28, threshold_db=-36.0)
        out = base.rbj_peaking(out, sr, 78, 0.12, 0.92)
        out = base.dynamic_band_tame(out, sr, 170, 330, max_cut_db=0.20, percentile=66.0, slope=0.30, smooth_ms=18.0)
        moves += ["bass_low_density_parallel", "bass_lowmid_guard_not_broad_boost"]
    elif key == "drums":
        out = v16b.band_parallel_density(out, sr, 70, 760, drive_db=0.62, mix=0.045, comp_ratio=1.38, threshold_db=-34.0)
        out = base.rbj_peaking(out, sr, 4200, 0.12, 0.90)
        out = base.dynamic_band_tame(out, sr, 6600, 10800, max_cut_db=0.22, percentile=69.0, slope=0.30, smooth_ms=7.0)
        moves += ["drum_body_parallel", "drum_presence_micro_lift", "hat_guard"]
    elif key in {"synth", "strings", "keyboard", "guitar"}:
        out = base.rbj_peaking(out, sr, 760, 0.10, 0.86)
        out = base.rbj_peaking(out, sr, 2600, 0.10, 0.94)
        out = base.dynamic_band_tame(out, sr, 240, 520, max_cut_db=0.18, percentile=68.0, slope=0.26, smooth_ms=22.0)
        out = base.dynamic_band_tame(out, sr, 5600, 10000, max_cut_db=0.22, percentile=66.0, slope=0.30, smooth_ms=7.0)
        out = v16b.lead_demask(out, lead, sr, "melody")
        out = v16b.v16a.high_side_open(out, sr, split_hz=900.0, gain_db=0.22)
        moves += [f"{key}_harmonic_body_micro_lift", f"{key}_lead_pocket_preserved", f"{key}_small_high_side_open"]
    elif key == "fx":
        out = base.rbj_peaking(out, sr, 1100, 0.08, 0.95)
        out = base.dynamic_band_tame(out, sr, 5200, 11000, max_cut_db=0.34, percentile=64.0, slope=0.34, smooth_ms=7.0)
        out = v16b.lead_demask(out, lead, sr, "fx")
        out = v16b.v16a.high_side_open(out, sr, split_hz=980.0, gain_db=0.18)
        moves += ["fx_fill_without_vocal_mask", "fx_glare_guard"]
    elif key in {"percussion", "woodwinds", "brass"}:
        out = base.rbj_peaking(out, sr, 1200, 0.08, 0.90)
        out = base.dynamic_band_tame(out, sr, 250, 520, max_cut_db=0.16, percentile=68.0, slope=0.24, smooth_ms=20.0)
        out = base.dynamic_band_tame(out, sr, 5700, 10500, max_cut_db=0.20, percentile=68.0, slope=0.30, smooth_ms=7.0)
        moves += [f"{key}_tiny_body_fill", f"{key}_mud_glare_guard"]
    elif key in {"female_vocal", "backing_vocals"}:
        out = v16b.lead_demask(out, lead, sr, "support")
        out = base.rbj_peaking(out, sr, 3100, 0.08, 0.90)
        out = base.dynamic_band_tame(out, sr, 5600, 9500, max_cut_db=0.18, percentile=68.0, slope=0.28, smooth_ms=7.0)
        moves += [f"{key}_support_fill", f"{key}_lead_not_masked"]
    elif key in {"vocal_reverb", "vocal_delay"}:
        out = base.rbj_shelf(out, sr, 7200, 0.08, high=True, slope=0.68)
        out = base.dynamic_band_tame(out, sr, 240, 520, max_cut_db=0.24, percentile=66.0, slope=0.32, smooth_ms=18.0)
        moves += [f"{key}_tail_air_fill", f"{key}_lowmid_tail_guard"]

    out = base.match_active_rms(out, before_active + lift_db, max_gain_db=lift_db)
    out, section_moves = apply_smooth_section_stem_fill(out, sr, key)
    moves += section_moves
    out = base.peak_cap(out.astype(np.float32), peak_cap_dbfs)
    out = base.soft_clip(out.astype(np.float32), ceiling=0.985)
    moves.append(f"active_rms_target_lift_{lift_db:.2f}db_peak_cap_{peak_cap_dbfs:.2f}dbfs")
    return out.astype(np.float32), moves


def apply_v20_stem_harmony_fullness(processed: dict[str, Path], sr: int, length: int) -> dict[str, Any]:
    lead = pad_or_trim(base.read_wav(processed["lead_vocal"])[1], length)
    music_keys = ["bass", "drums", "synth", "strings", "keyboard", "guitar", "fx", "percussion", "woodwinds", "brass"]
    support_keys = ["female_vocal", "backing_vocals", "vocal_reverb", "vocal_delay"]
    before_music = v16b.group_mix(processed, music_keys, sr, length)
    before_support = v16b.group_mix(processed, support_keys, sr, length)
    rows: list[dict[str, Any]] = []

    for key in [*music_keys, *support_keys]:
        path = processed.get(key)
        if not path or not path.exists():
            continue
        stem_sr, y, _ = base.read_wav(path)
        if stem_sr != sr:
            raise RuntimeError(f"Sample-rate mismatch in v21 stem harmony for {key}")
        y = pad_or_trim(y, length)
        before = stem_harmony_metrics(y, sr)
        out, moves = harmonic_fullness_for_stem(key, y, lead, sr)
        out = pad_or_trim(out, length)
        write_wav(path, sr, out)
        after = stem_harmony_metrics(out, sr)
        rows.append(
            {
                "stem": key,
                "path": rel(path),
                "target_lift_db": STEM_HARMONY_TARGETS.get(key, {}).get("lift_db"),
                "moves": moves,
                "before": before,
                "after": after,
                "actual_active_rms_delta_db": round(float(after["active_rms_db"]) - float(before["active_rms_db"]), 2),
                "actual_peak_delta_db": round(float(after["peak_dbfs"]) - float(before["peak_dbfs"]), 2),
            }
        )

    after_music = v16b.group_mix(processed, music_keys, sr, length)
    after_support = v16b.group_mix(processed, support_keys, sr, length)
    report = {
        "schema": "mwolla-v21-full-stem-harmony-v1",
        "target": "last-resort style full-stem harmonic fill: every active stem becomes more audible without a broad master-only push",
        "method": (
            "Printed per-stem active-RMS lifts are limited to 0.18-0.80 dB, with band-limited parallel density, "
            "small body/presence lifts, lead-aware pockets, glare/mud guards, per-stem peak caps, and smooth "
            "late-section stem fill envelopes instead of master gain-riding."
        ),
        "section_stem_fill_windows": SECTION_STEM_FILL_WINDOWS,
        "guards": {
            "raw_media_preserved": True,
            "external_plugin_parameter_writes": "none_added",
            "new_master_plugin_inserts": "none_added",
            "lead_vocal_first_slot_rescue_preserved_in_reaper": True,
        },
        "music_group_before": stem_harmony_metrics(before_music, sr),
        "music_group_after": stem_harmony_metrics(after_music, sr),
        "support_group_before": stem_harmony_metrics(before_support, sr),
        "support_group_after": stem_harmony_metrics(after_support, sr),
        "rows": rows,
    }
    write_json(base.REPORTS / "v20_stem_harmony_fullness_report.json", report)
    write_csv(
        base.REPORTS / "v20_stem_harmony_fullness_report.csv",
        [
            {
                "stem": row["stem"],
                "target_lift_db": row["target_lift_db"],
                "actual_active_rms_delta_db": row["actual_active_rms_delta_db"],
                "actual_peak_delta_db": row["actual_peak_delta_db"],
                "before_active_rms_db": row["before"]["active_rms_db"],
                "after_active_rms_db": row["after"]["active_rms_db"],
                "before_peak_dbfs": row["before"]["peak_dbfs"],
                "after_peak_dbfs": row["after"]["peak_dbfs"],
                "before_low_20_120_db": row["before"]["low_20_120_db"],
                "after_low_20_120_db": row["after"]["low_20_120_db"],
                "before_lowmid_120_350_db": row["before"]["lowmid_120_350_db"],
                "after_lowmid_120_350_db": row["after"]["lowmid_120_350_db"],
                "before_mid_350_2500_db": row["before"]["mid_350_2500_db"],
                "after_mid_350_2500_db": row["after"]["mid_350_2500_db"],
                "before_presence_2500_6000_db": row["before"]["presence_2500_6000_db"],
                "after_presence_2500_6000_db": row["after"]["presence_2500_6000_db"],
                "moves": ";".join(row["moves"]),
            }
            for row in rows
        ],
    )
    return report


def write_processed(paths: dict[str, Path]) -> tuple[dict[str, Path], int, float, dict[str, float]]:
    processed, sr, duration, vocal_balance = v16b.write_processed(paths)
    length = int(round(duration * sr))
    polish = apply_v19_vocal_polish(processed, sr, length)
    harmony = apply_v20_stem_harmony_fullness(processed, sr, length)
    v16b.v13.rewrite_vocal_solo(processed, sr, length)
    vocal_balance["v19_vocal_ott_style_saturation"] = True
    vocal_balance["v19_lead_active_rms_before_db"] = polish["before"]["active_rms_db"]
    vocal_balance["v19_lead_active_rms_after_db"] = polish["after"]["active_rms_db"]
    vocal_balance["v19_lead_presence_delta_db"] = round(polish["after"]["presence_1500_5000_db"] - polish["before"]["presence_1500_5000_db"], 2)
    vocal_balance["v19_lead_sibilance_delta_db"] = round(polish["after"]["sibilance_5000_9000_db"] - polish["before"]["sibilance_5000_9000_db"], 2)
    vocal_balance["v20_full_stem_harmony"] = True
    vocal_balance["v20_stem_harmony_processed_count"] = len(harmony["rows"])
    vocal_balance["v20_music_group_active_rms_delta_db"] = round(
        harmony["music_group_after"]["active_rms_db"] - harmony["music_group_before"]["active_rms_db"],
        2,
    )
    vocal_balance["v20_support_group_active_rms_delta_db"] = round(
        harmony["support_group_after"]["active_rms_db"] - harmony["support_group_before"]["active_rms_db"],
        2,
    )
    return processed, sr, duration, vocal_balance


def write_reaper_scripts(processed: dict[str, Path], duration: float) -> None:
    v16b.write_reaper_scripts(processed, duration)
    build_text = base.BUILD_LUA.read_text(encoding="utf-8")
    build_text = build_text.replace("mwolla v16B source stem repair reference density master", "mwolla v21 full stem harmony master")
    build_text = build_text.replace("mwolla_v16B", "mwolla_v21")
    build_text = build_text.replace('local main = make_track("10 MAIN_VOCAL_CENTER", 1.55, 0.0, false, false)', 'local main = make_track("10 MAIN_VOCAL_CENTER", 1.62, 0.0, false, false)')
    build_text = build_text.replace('local music_bus = make_track("MUSIC_BUS", 0.18, 0.0, false, false)', 'local music_bus = make_track("MUSIC_BUS", 0.22, 0.0, false, false)')
    build_text = build_text.replace('route_sidechain(main_bus, music_bus, -1.4, "MAIN_VOCAL_BUS sidechain -> MUSIC_BUS")', 'route_sidechain(main_bus, music_bus, -1.05, "MAIN_VOCAL_BUS sidechain -> MUSIC_BUS")')
    base.BUILD_LUA.write_text(build_text, encoding="utf-8")


def final_master_louder_clear_safe() -> None:
    sr, reaper_print, _ = base.read_wav(base.REAPER_PRINT)
    premaster = base.peak_cap(reaper_print.astype(np.float32), -1.35)
    write_wav(v11.premaster_path(), sr, premaster)

    rows = v11.window_rows(premaster, sr, 1.5)
    target = v11.active_median(rows)
    out_rows: list[dict[str, Any]] = []
    for row in rows:
        out_rows.append(
            {
                **row,
                "window_kind": v11.forced_window_kind(float(row["start_s"]), float(row["end_s"])) or "",
                "delta_vs_premaster_active_median_db": round(float(row["rms_db"]) - target, 2),
                "applied_premaster_phrase_gain_db": 0.0,
                "reason": "v21 controlled loudness lift: no phrase gain; fullness handled upstream per stem",
                "post_premaster_phrase_rms_db": row["rms_db"],
                "post_premaster_phrase_delta_vs_active_median_db": round(float(row["rms_db"]) - target, 2),
                "premaster_phrase_improvement_db": 0.0,
            }
        )
    write_json(
        base.REPORTS / v11.PHRASE_PREMASTER_JSON,
        {
            "input": rel(base.REAPER_PRINT),
            "output": rel(v11.premaster_path()),
            "window_s": 1.5,
            "active_range_s": [v11.ACTIVE_START_S, v11.ACTIVE_END_S],
            "premaster_active_median_rms_db": round(target, 2),
            "post_premaster_active_median_rms_db": round(target, 2),
            "max_applied_premaster_phrase_gain_db": 0.0,
            "min_applied_premaster_phrase_gain_db": 0.0,
            "mean_abs_applied_premaster_phrase_gain_db": 0.0,
            "method": "v21: no phrase gain riding; upstream stem fullness plus controlled loudnorm target and true-peak limiter guard.",
            "windows": out_rows,
        },
    )

    filter_graph = (
        "highpass=f=24,"
        "equalizer=f=280:t=q:w=1:g=-0.10,"
        "equalizer=f=3100:t=q:w=0.9:g=0.08,"
        "equalizer=f=10800:t=q:w=0.8:g=0.10,"
        "loudnorm=I=-11.0:TP=-1.20:LRA=3.2:linear=false,"
        "alimiter=limit=0.86:attack=2:release=92:level=false"
    )
    subprocess.run(
        [
            base.FFMPEG,
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(v11.premaster_path()),
            "-af",
            filter_graph,
            "-ar",
            "48000",
            "-c:a",
            "pcm_s24le",
            str(base.FINAL_WAV),
        ],
        check=True,
    )
    final_sr, final, _ = base.read_wav(base.FINAL_WAV)
    write_wav(v11.final_locked_path(), final_sr, final)

    final_rows = v11.window_rows(final, final_sr, 1.5)
    final_target = v11.active_median(final_rows)
    lock_rows = []
    for row in final_rows:
        lock_rows.append(
            {
                **row,
                "window_kind": v11.forced_window_kind(float(row["start_s"]), float(row["end_s"])) or "",
                "delta_vs_pre_lock_active_median_db": round(float(row["rms_db"]) - final_target, 2),
                "applied_post_final_lock_gain_db": 0.0,
                "reason": "v21: post-final level lock disabled; true-peak-safe loudness lift only",
                "post_lock_rms_db": row["rms_db"],
                "post_lock_delta_vs_active_median_db": round(float(row["rms_db"]) - final_target, 2),
                "post_lock_change_db": 0.0,
            }
        )
    lock_report = {
        "input_output_final_wav": rel(base.FINAL_WAV),
        "locked_copy": rel(v11.final_locked_path()),
        "window_s": 1.5,
        "active_range_s": [v11.ACTIVE_START_S, v11.ACTIVE_END_S],
        "pre_lock_active_median_rms_db": round(final_target, 2),
        "post_lock_active_median_rms_db": round(final_target, 2),
        "max_applied_post_final_lock_gain_db": 0.0,
        "min_applied_post_final_lock_gain_db": 0.0,
        "pre_lock_summary": v11.summarize_window_rows(final_rows),
        "post_lock_summary": v11.summarize_window_rows(final_rows),
        "method": "v21: no post-final phrase gain; controlled loudness lift with true-peak limiter guard.",
        "windows": lock_rows,
    }
    write_json(base.REPORTS / v11.FINAL_LOCK_REPORT_JSON, lock_report)
    v11.write_final_level_consistency_audit(base.FINAL_WAV, lock_report)
    write_json(
        base.REPORTS / "controlled_loudness_lift_final_master_report.json",
        {
            "schema": "mwolla-v21-controlled-fullness-loudness-v1",
            "input_reaper_print": rel(base.REAPER_PRINT),
            "premaster": rel(v11.premaster_path()),
            "final_wav": rel(base.FINAL_WAV),
            "final_mp3": rel(base.FINAL_MP3),
            "target_lufs": -11.0,
            "target_true_peak_db": -1.20,
            "loudnorm_used": True,
            "limiter_guard_used": True,
            "limiter_guard": "ffmpeg alimiter limit=0.86, attack=2 ms, release=92 ms",
            "premaster_phrase_gain_range_db": [0.0, 0.0],
            "post_final_lock_gain_range_db": [0.0, 0.0],
            "reason": "User requested last-resort stem fullness while keeping break-up risk controlled; fullness is upstream and loudness lift stays moderate.",
        },
    )

    subprocess.run(
        [
            base.FFMPEG,
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(base.FINAL_WAV),
            "-c:a",
            "libmp3lame",
            "-b:a",
            "320k",
            str(base.FINAL_MP3),
        ],
        check=True,
    )


def patch_v20_report() -> None:
    report_path = base.REPORTS / base.REPORT_FILENAME
    text = report_path.read_text(encoding="utf-8")
    text = text.replace("Mwolla v16B Source Stem Repair Reference Density Master Report", base.REPORT_TITLE)
    text = text.replace("mwolla v16B source stem repair reference density master", "mwolla v21 full stem harmony master")
    vocal = json.loads((base.REPORTS / "v19_vocal_ott_saturation_report.json").read_text(encoding="utf-8"))
    harmony = json.loads((base.REPORTS / "v20_stem_harmony_fullness_report.json").read_text(encoding="utf-8"))
    loudness = json.loads((base.REPORTS / "controlled_loudness_lift_final_master_report.json").read_text(encoding="utf-8"))
    text = text.rstrip() + "\n\n" + "\n".join(
        [
            "## v21 Full Stem Harmony Pass",
            "",
            "- User command: use the best last-resort method so the whole stem set feels harmonically full, similar to raising each stem about 1 dB, without breakup.",
            "- Stem strategy: printed per-stem active-RMS lifts from 0.18-0.80 dB with band-limited density, body/presence micro lifts, lead-aware pockets, glare/mud guards, and per-stem peak caps.",
            "- Vocal processing retained from v19: printed OTT-style parallel density on lead vocal, subtle saturation, 3.1 kHz micro lift, 10.6 kHz micro shelf, and post-OTT 5.2-9.2 kHz anti-fizz guard.",
            "- External plugin safety: no external OTT plugin parameter writes; no new Ozone/clipper/OTT insert automation.",
            f"- Lead active RMS: `{vocal['before']['active_rms_db']}` -> `{vocal['after']['active_rms_db']}` dB.",
            f"- Lead 1.5-5 kHz presence: `{vocal['before']['presence_1500_5000_db']}` -> `{vocal['after']['presence_1500_5000_db']}` dBFS.",
            f"- Lead 5-9 kHz sibilance: `{vocal['before']['sibilance_5000_9000_db']}` -> `{vocal['after']['sibilance_5000_9000_db']}` dBFS.",
            f"- Music group active RMS: `{harmony['music_group_before']['active_rms_db']}` -> `{harmony['music_group_after']['active_rms_db']}` dB.",
            f"- Support group active RMS: `{harmony['support_group_before']['active_rms_db']}` -> `{harmony['support_group_after']['active_rms_db']}` dB.",
            f"- Processed stem count: `{len(harmony['rows'])}`.",
            f"- Final loudness target: `{loudness['target_lufs']}` LUFS, true peak target `{loudness['target_true_peak_db']}` dBTP.",
            "- Preserved: no-chop continuity, hook reprise at 54.0-70.0s, first-slot vocal rescue plugin, sidechain 1/2 -> 3/4, muted source reference routing.",
            f"- Vocal OTT/saturation report: `{rel(base.REPORTS / 'v19_vocal_ott_saturation_report.json')}`",
            f"- Full stem harmony report: `{rel(base.REPORTS / 'v20_stem_harmony_fullness_report.json')}`",
            f"- Controlled loudness report: `{rel(base.REPORTS / 'controlled_loudness_lift_final_master_report.json')}`",
        ]
    ) + "\n"
    report_path.write_text(text, encoding="utf-8")


def write_reports(paths: dict[str, Path], processed: dict[str, Path], vocal_balance: dict[str, float], gate: dict[str, Any]) -> None:
    v16b.write_reports(paths, processed, vocal_balance, gate)
    patch_v20_report()
    qc_path = base.REPORTS / "qc_summary.json"
    qc = json.loads(qc_path.read_text(encoding="utf-8"))
    qc["v20_full_stem_harmony"] = {
        "vocal_report": rel(base.REPORTS / "v19_vocal_ott_saturation_report.json"),
        "stem_harmony_report": rel(base.REPORTS / "v20_stem_harmony_fullness_report.json"),
        "stem_harmony_csv": rel(base.REPORTS / "v20_stem_harmony_fullness_report.csv"),
        "controlled_loudness_report": rel(base.REPORTS / "controlled_loudness_lift_final_master_report.json"),
        "target_lufs": -11.0,
        "target_true_peak_db": -1.20,
        "external_parameter_writes": "none_added",
        "new_master_plugin_inserts": "none_added",
        "stem_fullness_method": "per-stem active-RMS lifts with peak caps, not a single broad master gain push",
        "loudnorm_used": True,
        "limiter_guard_used": True,
    }
    write_json(qc_path, qc)


def build_zip() -> None:
    v16b.build_zip()
    extras = [
        base.REPORTS / "v19_vocal_ott_saturation_report.json",
        base.REPORTS / "v19_vocal_ott_saturation_report.csv",
        base.REPORTS / "v20_stem_harmony_fullness_report.json",
        base.REPORTS / "v20_stem_harmony_fullness_report.csv",
        base.REPORTS / "controlled_loudness_lift_final_master_report.json",
    ]
    with base.zipfile.ZipFile(base.DELIVERABLE_ZIP, "a", compression=base.zipfile.ZIP_DEFLATED) as archive:
        existing = set(archive.namelist())
        for path in extras:
            if path.exists():
                arcname = path.relative_to(ROOT).as_posix()
                if arcname not in existing:
                    archive.write(path, arcname)


def main() -> int:
    configure_base()
    base.extract_source = v16b.v12.extract_source
    base.write_reaper_scripts = write_reaper_scripts
    base.write_trace_md = v16b.v12.write_trace_md
    base.run_gate = v16b.v12.run_gate
    base.write_reports = write_reports
    base.build_zip = build_zip
    base.process_lead_vocal = v16b.v14.process_lead_vocal_clarity
    base.process_female_layer = v16b.v14.process_layer_vocal_clarity
    base.process_backing_vocals = v16b.v2.v1.process_backing_vocals
    base.process_instrument = v16b.v2.v1.process_instrument
    base.write_processed = write_processed
    base.final_master = final_master_louder_clear_safe
    return base.main()


if __name__ == "__main__":
    raise SystemExit(main())

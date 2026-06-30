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
V07_SCRIPT = ROOT / "tools" / "mwolla_v07_suno_dynamic_eq_locked_master.py"
SLUG = "mwolla_v08_moderate_dynamic_eq_vocal_uniform_master"

spec = importlib.util.spec_from_file_location("mwolla_v07_suno_dynamic_eq_locked_master", V07_SCRIPT)
if spec is None or spec.loader is None:
    raise RuntimeError(f"Could not load v07 script: {V07_SCRIPT}")
v7 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v7)
v6 = v7.v6
v5 = v7.v5
v4 = v7.v4
v2 = v7.v2
v1 = v7.v1
base = v7.base


PREMASTER_NAME = "mwolla_v08_MODERATE_DYNAMIC_EQ_PREMASTER_24-48.wav"
PLATEAU_NAME = "mwolla_v08_MODERATE_DYNAMIC_EQ_PLATEAU_PREMASTER_24-48.wav"
FLOOR_NAME = "mwolla_v08_MODERATE_DYNAMIC_EQ_FLOOR_PREMASTER_24-48.wav"
VOCAL_UNIFORMITY_JSON = "vocal_group_uniformity_qc_and_curve_report.json"
VOCAL_UNIFORMITY_CSV = "vocal_group_uniformity_qc_and_curve_report.csv"
WINDOW_REPORT_JSON = "section_loudness_consistency_1p5s_3s_6s_report.json"
WINDOW_REPORT_CSV = "section_loudness_consistency_1p5s_3s_6s_report.csv"
WINDOW_REPORT_MD = "section_loudness_consistency_1p5s_3s_6s_report.md"

MUSIC_KEYS = v7.MUSIC_KEYS
VOCAL_KEYS = v7.VOCAL_KEYS


def db_to_amp(db: float | np.ndarray) -> np.ndarray:
    return np.power(10.0, np.asarray(db) / 20.0)


def amp_to_db(value: float | np.ndarray) -> np.ndarray:
    return 20.0 * np.log10(np.maximum(np.asarray(value), 1e-12))


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
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)


def configure_base() -> None:
    v7.configure_base()
    v7.PREMASTER_NAME = PREMASTER_NAME
    v7.PLATEAU_NAME = PLATEAU_NAME
    v7.FLOOR_NAME = FLOOR_NAME

    base.SLUG = SLUG
    base.WORK = ROOT / "audio_work" / SLUG
    base.SOURCE = base.WORK / "source_stems"
    base.PROCESSED = base.WORK / "processed_stems"
    base.REAPER_DIR = ROOT / "reaper" / SLUG
    base.RENDERS = ROOT / "renders" / SLUG
    base.REPORTS = ROOT / "reports" / SLUG

    base.RPP = base.REAPER_DIR / "mwolla_v08_MODERATE_DYNAMIC_EQ_VOCAL_UNIFORM_MASTER.rpp"
    base.BUILD_LUA = base.REAPER_DIR / "build_mwolla_v08_moderate_dynamic_eq_vocal_uniform_master.lua"
    base.RUN_BUILD_LUA = base.REAPER_DIR / "run_build_mwolla_v08_moderate_dynamic_eq_vocal_uniform_master.lua"
    base.RENDER_LUA = base.REAPER_DIR / "render_mwolla_v08_moderate_dynamic_eq_vocal_uniform_master.lua"
    base.RUN_RENDER_LUA = base.REAPER_DIR / "run_render_mwolla_v08_moderate_dynamic_eq_vocal_uniform_master.lua"
    base.TRACE_JSON = base.REPORTS / "actual_reaper_plugin_trace.json"
    base.TRACE_MD = base.REPORTS / "actual_reaper_plugin_trace.md"

    base.REAPER_PRINT = base.RENDERS / "mwolla_v08_REAPERPRINT_24-48.wav"
    base.FINAL_WAV = base.RENDERS / "mwolla_v08_MODERATE_DYNAMIC_EQ_VOCAL_UNIFORM_MASTER.wav"
    base.FINAL_MP3 = base.RENDERS / "mwolla_v08_MODERATE_DYNAMIC_EQ_VOCAL_UNIFORM_MASTER_320k.mp3"
    base.VOCAL_SOLO = base.RENDERS / "mwolla_v08_VOCAL_SOLO_uniform_checked.wav"
    base.AB_PREVIEW_MP3 = base.RENDERS / "mwolla_v08_AB_original_suno_to_moderate_dynamic_eq_vocal_uniform_320k.mp3"
    base.DELIVERABLE_ZIP = base.RENDERS / "mwolla_v08_MODERATE_DYNAMIC_EQ_VOCAL_UNIFORM_MASTER_DELIVERABLE.zip"

    base.FEMALE_TARGET_DELTA_DB = -1.05
    base.FEMALE_LAYER_FILENAME = "female_vocal_audible_moderate_dynamic_eq_wide.wav"
    base.FEMALE_TRACK_NAME = "13 Female audible panned support moderate"
    base.REPORT_FILENAME = "mwolla_v08_moderate_dynamic_eq_vocal_uniform_master_report.md"
    base.REPORT_TITLE = "Mwolla v08 Moderate Dynamic EQ Vocal Uniform Master Report"
    base.PROJECT_NOTES = (
        "mwolla v08: user correction pass. Overall sound follows the original Suno full/stem export. "
        "Dynamic EQ pockets are deliberately moderate, and vocal-group uniformity is checked and corrected "
        "as its own QC target before final mastering."
    )


def read_processed(path: Path, sr: int, length: int) -> np.ndarray:
    stem_sr, y, _ = base.read_wav(path)
    if stem_sr != sr:
        raise RuntimeError(f"Sample-rate mismatch: {path}")
    return v6.pad_or_trim(y, length)


def group_mix(processed: dict[str, Path], keys: set[str], sr: int, length: int) -> np.ndarray:
    out = np.zeros((length, 2), dtype=np.float32)
    for key in sorted(keys):
        path = processed.get(key)
        if not path or not path.exists():
            continue
        out += read_processed(path, sr, length) * float(db_to_amp(v2.TRACK_MIX_DB.get(key, 0.0)))
    return out.astype(np.float32)


def moderate_dynamic_eq_music_pocket(y: np.ndarray, lead: np.ndarray, vocal_group: np.ndarray, sr: int, role: str) -> tuple[np.ndarray, list[dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    out = y.astype(np.float32)
    moves: list[tuple[str, float, float, float, float, float]] = [
        ("low_mid_body_space", 260, 760, 0.35, 62.0, 170.0),
        ("vocal_presence_pocket", 1600, 5000, 1.05, 57.0, 150.0),
        ("sibilance_air_guard", 6400, 9300, 0.45, 64.0, 82.0),
    ]
    if role in {"bass", "drums"}:
        moves = [
            ("low_mid_body_space", 300, 800, 0.18, 66.0, 140.0),
            ("vocal_presence_pocket", 1900, 5000, 0.45, 62.0, 122.0),
            ("sibilance_air_guard", 6600, 9200, 0.22, 68.0, 72.0),
        ]
    elif role in {"fx", "percussion"}:
        moves = [
            ("vocal_presence_pocket", 1850, 6000, 0.72, 60.0, 132.0),
            ("sibilance_air_guard", 6600, 10400, 0.42, 66.0, 80.0),
        ]
    for band_name, low, high, max_cut, percentile, smooth_ms in moves:
        before = out
        trigger = lead if band_name != "low_mid_body_space" else vocal_group
        out = base.sidechain_band_duck(out, trigger, sr, low, high, max_cut_db=max_cut, percentile=percentile, smooth_ms=smooth_ms)
        rows.append(
            {
                "stem": role,
                "dynamic_eq_band": band_name,
                "low_hz": low,
                "high_hz": high,
                "max_cut_db": max_cut,
                "before_active_rms_db": round(base.active_rms_db(before), 2),
                "after_active_rms_db": round(base.active_rms_db(out), 2),
                "note": "moderate printed dynamic EQ sidechain pocket; deliberately lighter than v07",
            }
        )
    return base.peak_cap(out.astype(np.float32), -1.7), rows


def moderate_music_constant_curve(processed: dict[str, Path], paths: dict[str, Path], sr: int, length: int) -> dict[str, Any]:
    source_sr, source, _ = base.read_wav(paths["full_reference"])
    if source_sr != sr:
        raise RuntimeError("Source full reference sample-rate mismatch")
    source = v6.pad_or_trim(source, length)
    music = group_mix(processed, MUSIC_KEYS, sr, length)
    source_rows = v7.window_rows(source, sr, 3.0)
    music_rows = v7.window_rows(music, sr, 3.0)
    source_levels = np.array([row["rms_db"] for row in source_rows if 6.0 <= row["start_s"] <= 137.0], dtype=np.float32)
    music_levels = np.array([row["rms_db"] for row in music_rows if 6.0 <= row["start_s"] <= 137.0], dtype=np.float32)
    source_median = float(np.median(source_levels)) if len(source_levels) else -18.0
    music_median = float(np.median(music_levels)) if len(music_levels) else -18.0
    gains = np.zeros(len(music_rows), dtype=np.float32)
    rows: list[dict[str, Any]] = []
    for i, row in enumerate(music_rows):
        start = float(row["start_s"])
        end = float(row["end_s"])
        if start < 6.0 or end > 137.0:
            gain = 0.0
        else:
            source_ref = source_rows[i]["rms_db"] if i < len(source_rows) else source_median
            target = music_median + (float(source_ref) - source_median) * 0.18
            delta = target - float(row["rms_db"])
            gain = float(np.clip(delta * 0.48, -0.75, 1.15))
            if abs(gain) < 0.16:
                gain = 0.0
        gains[i] = gain
        rows.append({**row, "source_reference_rms_db": source_rows[i]["rms_db"] if i < len(source_rows) else None, "applied_music_constant_gain_db": round(gain, 2)})
    centers = np.array([(row["start_s"] + row["end_s"]) * 0.5 for row in music_rows], dtype=np.float32)
    times = np.arange(length, dtype=np.float32) / float(sr)
    curve = np.interp(times, centers, gains, left=gains[0], right=gains[-1]).astype(np.float32) if len(centers) > 1 else np.zeros(length, dtype=np.float32)
    smooth = max(1, int(sr * 1.15))
    if smooth > 1:
        kernel = np.hanning(smooth * 2 + 1).astype(np.float32)
        kernel /= np.sum(kernel)
        curve = base.signal.fftconvolve(curve, kernel, mode="same").astype(np.float32)
    curve = np.clip(curve, -0.75, 1.15)
    for key in sorted(MUSIC_KEYS):
        path = processed.get(key)
        if not path or not path.exists():
            continue
        y = read_processed(path, sr, length)
        adjusted = y * db_to_amp(curve)[:, None]
        adjusted = base.peak_cap(adjusted.astype(np.float32), -1.7)
        base.write_wav(path, sr, adjusted)
    after_music = group_mix(processed, MUSIC_KEYS, sr, length)
    after_rows = v7.window_rows(after_music, sr, 3.0)
    for i, row in enumerate(rows):
        if i < len(after_rows):
            row["post_constant_music_rms_db"] = after_rows[i]["rms_db"]
            row["music_level_change_db"] = round(after_rows[i]["rms_db"] - row["rms_db"], 2)
    payload = {
        "source_reference": "original Suno full mix from 뭘라.zip",
        "window_s": 3.0,
        "source_active_median_rms_db": round(source_median, 2),
        "music_active_median_rms_db": round(music_median, 2),
        "max_gain_db": round(float(np.max(gains)), 2),
        "min_gain_db": round(float(np.min(gains)), 2),
        "method": "Moderate music-level constant curve; smaller range than v07 so the beat does not feel over-pulled.",
        "rows": rows,
    }
    write_json(base.REPORTS / v7.MUSIC_CONSTANT_JSON, payload)
    write_csv(base.REPORTS / v7.MUSIC_CONSTANT_CSV, rows)
    return payload


def vocal_window_summary(y: np.ndarray, sr: int, window_s: float, active_threshold: float) -> dict[str, Any]:
    rows = v7.window_rows(y, sr, window_s)
    active = [row for row in rows if row["start_s"] >= 6.0 and row["end_s"] <= 137.0 and float(row["rms_db"]) >= active_threshold]
    levels = np.array([float(row["rms_db"]) for row in active], dtype=np.float32)
    if not len(levels):
        return {"count": 0}
    median = float(np.median(levels))
    deviations = levels - median
    return {
        "count": len(active),
        "active_median_rms_db": round(median, 2),
        "outside_plus_minus_2db_count": int(np.sum(np.abs(deviations) > 2.0)),
        "outside_plus_minus_3db_count": int(np.sum(np.abs(deviations) > 3.0)),
        "max_positive_deviation_db": round(float(np.max(deviations)), 2),
        "max_negative_deviation_db": round(float(np.min(deviations)), 2),
        "mean_abs_deviation_db": round(float(np.mean(np.abs(deviations))), 2),
    }


def vocal_curve_row_summary(rows: list[dict[str, Any]], level_key: str) -> dict[str, Any]:
    active = [row for row in rows if row.get("active_for_vocal_uniformity") and level_key in row]
    levels = np.array([float(row[level_key]) for row in active], dtype=np.float32)
    if not len(levels):
        return {"count": 0}
    median = float(np.median(levels))
    deviations = levels - median
    return {
        "count": len(active),
        "active_median_rms_db": round(median, 2),
        "outside_plus_minus_2db_count": int(np.sum(np.abs(deviations) > 2.0)),
        "outside_plus_minus_3db_count": int(np.sum(np.abs(deviations) > 3.0)),
        "max_positive_deviation_db": round(float(np.max(deviations)), 2),
        "max_negative_deviation_db": round(float(np.min(deviations)), 2),
        "mean_abs_deviation_db": round(float(np.mean(np.abs(deviations))), 2),
    }


def apply_vocal_uniformity_curve(processed: dict[str, Path], sr: int, length: int) -> dict[str, Any]:
    before_group = group_mix(processed, VOCAL_KEYS, sr, length)
    rows = v7.window_rows(before_group, sr, 1.5)
    active_levels = np.array([float(row["rms_db"]) for row in rows if row["start_s"] >= 6.0 and row["end_s"] <= 137.0], dtype=np.float32)
    active_threshold = max(float(np.percentile(active_levels, 52.0)) if len(active_levels) else -31.0, -31.0)
    target = float(np.median(active_levels[active_levels >= active_threshold])) if len(active_levels) else -21.0
    floor = target - 1.25
    ceiling = target + 1.3
    gains = np.zeros(len(rows), dtype=np.float32)
    curve_rows: list[dict[str, Any]] = []
    for i, row in enumerate(rows):
        start = float(row["start_s"])
        end = float(row["end_s"])
        level = float(row["rms_db"])
        active = start >= 6.0 and end <= 137.0 and level >= active_threshold
        if not active:
            gain = 0.0
        elif level < floor:
            gain = min((floor - level) * 0.98, 6.0)
        elif level > ceiling:
            gain = max((ceiling - level) * 0.44, -1.2)
        else:
            gain = 0.0
        if abs(gain) < 0.15:
            gain = 0.0
        gains[i] = gain
        curve_rows.append(
            {
                **row,
                "active_for_vocal_uniformity": active,
                "active_threshold_rms_db": round(active_threshold, 2),
                "target_vocal_group_rms_db": round(target, 2),
                "floor_target_rms_db": round(floor, 2),
                "ceiling_target_rms_db": round(ceiling, 2),
                "applied_vocal_uniformity_gain_db": round(float(gain), 2),
            }
        )
    centers = np.array([(row["start_s"] + row["end_s"]) * 0.5 for row in rows], dtype=np.float32)
    times = np.arange(length, dtype=np.float32) / float(sr)
    curve = np.interp(times, centers, gains, left=gains[0], right=gains[-1]).astype(np.float32) if len(centers) > 1 else np.zeros(length, dtype=np.float32)
    smooth = max(1, int(sr * 0.36))
    if smooth > 1:
        kernel = np.hanning(smooth * 2 + 1).astype(np.float32)
        kernel /= np.sum(kernel)
        curve = base.signal.fftconvolve(curve, kernel, mode="same").astype(np.float32)
    curve = np.clip(curve, -1.2, 6.0)
    curve_scales = {
        "lead_vocal": 1.0,
        "female_vocal": 1.0,
        "backing_vocals": 0.55,
        "vocal_reverb": 0.35,
        "vocal_delay": 0.35,
    }
    for key, scale in curve_scales.items():
        path = processed.get(key)
        if not path or not path.exists():
            continue
        y = read_processed(path, sr, length)
        adjusted = y * db_to_amp(curve * scale)[:, None]
        cap = -1.55 if key in {"lead_vocal", "female_vocal"} else -3.8
        adjusted = base.peak_cap(adjusted.astype(np.float32), cap)
        base.write_wav(path, sr, adjusted)
    after_group = group_mix(processed, VOCAL_KEYS, sr, length)
    after_rows = v7.window_rows(after_group, sr, 1.5)
    for i, row in enumerate(curve_rows):
        if i < len(after_rows):
            row["post_vocal_uniformity_rms_db"] = after_rows[i]["rms_db"]
            row["vocal_uniformity_change_db"] = round(after_rows[i]["rms_db"] - row["rms_db"], 2)

    active_post = np.array([float(row["post_vocal_uniformity_rms_db"]) for row in curve_rows if row["active_for_vocal_uniformity"]], dtype=np.float32)
    residual_gains = np.zeros(len(curve_rows), dtype=np.float32)
    if len(active_post):
        residual_median = float(np.median(active_post))
        residual_floor = residual_median - 2.45
        residual_ceiling = residual_median + 2.35
        for i, row in enumerate(curve_rows):
            if not row["active_for_vocal_uniformity"]:
                continue
            post_level = float(row.get("post_vocal_uniformity_rms_db", row["rms_db"]))
            if post_level < residual_floor:
                residual_gain = min((residual_floor - post_level) * 1.12, 4.2)
            elif post_level > residual_ceiling:
                residual_gain = max((residual_ceiling - post_level) * 0.35, -0.75)
            else:
                residual_gain = 0.0
            if abs(residual_gain) < 0.12:
                residual_gain = 0.0
            residual_gains[i] = residual_gain
            row["residual_floor_target_rms_db"] = round(residual_floor, 2)
            row["residual_applied_gain_db"] = round(float(residual_gain), 2)
        residual_curve = np.interp(times, centers, residual_gains, left=residual_gains[0], right=residual_gains[-1]).astype(np.float32) if len(centers) > 1 else np.zeros(length, dtype=np.float32)
        residual_smooth = max(1, int(sr * 0.18))
        if residual_smooth > 1:
            residual_kernel = np.hanning(residual_smooth * 2 + 1).astype(np.float32)
            residual_kernel /= np.sum(residual_kernel)
            residual_curve = base.signal.fftconvolve(residual_curve, residual_kernel, mode="same").astype(np.float32)
        residual_curve = np.clip(residual_curve, -0.75, 4.2)
        for key, scale in curve_scales.items():
            path = processed.get(key)
            if not path or not path.exists():
                continue
            y = read_processed(path, sr, length)
            adjusted = y * db_to_amp(residual_curve * scale)[:, None]
            cap = -1.45 if key in {"lead_vocal", "female_vocal"} else -3.6
            adjusted = base.peak_cap(adjusted.astype(np.float32), cap)
            base.write_wav(path, sr, adjusted)
        after_group = group_mix(processed, VOCAL_KEYS, sr, length)
        residual_after_rows = v7.window_rows(after_group, sr, 1.5)
        for i, row in enumerate(curve_rows):
            if i < len(residual_after_rows):
                row["post_residual_vocal_uniformity_rms_db"] = residual_after_rows[i]["rms_db"]
                row["residual_uniformity_change_db"] = round(residual_after_rows[i]["rms_db"] - float(row.get("post_vocal_uniformity_rms_db", row["rms_db"])), 2)
    payload = {
        "method": "Printed vocal-group uniformity curve after moderate dynamic EQ. Active vocal windows are leveled gently; gaps are not boosted.",
        "active_threshold_rms_db": round(active_threshold, 2),
        "target_vocal_group_rms_db": round(target, 2),
        "floor_target_rms_db": round(floor, 2),
        "ceiling_target_rms_db": round(ceiling, 2),
        "max_upward_gain_db": round(float(np.max(gains)), 2),
        "max_downward_gain_db": round(float(np.min(gains)), 2),
        "residual_max_upward_gain_db": round(float(np.max(residual_gains)), 2),
        "residual_max_downward_gain_db": round(float(np.min(residual_gains)), 2),
        "before": {
            "1.5": vocal_curve_row_summary(curve_rows, "rms_db"),
            "3.0": vocal_window_summary(before_group, sr, 3.0, active_threshold),
            "6.0": vocal_window_summary(before_group, sr, 6.0, active_threshold),
        },
        "after": {
            "1.5": vocal_curve_row_summary(curve_rows, "post_residual_vocal_uniformity_rms_db"),
            "3.0": vocal_window_summary(after_group, sr, 3.0, active_threshold),
            "6.0": vocal_window_summary(after_group, sr, 6.0, active_threshold),
        },
        "rows": curve_rows,
    }
    write_json(base.REPORTS / VOCAL_UNIFORMITY_JSON, payload)
    write_csv(base.REPORTS / VOCAL_UNIFORMITY_CSV, curve_rows)
    vocal_solo = base.peak_cap(after_group.astype(np.float32), -1.2)
    base.write_wav(base.VOCAL_SOLO, sr, vocal_solo)
    return payload


def write_processed(paths: dict[str, Path]) -> tuple[dict[str, Path], int, float, dict[str, float]]:
    processed, sr, duration, vocal_balance = v7.write_processed(paths)
    length = int(round(duration * sr))
    uniformity = apply_vocal_uniformity_curve(processed, sr, length)
    lead = read_processed(processed["lead_vocal"], sr, length)
    female = read_processed(processed["female_vocal"], sr, length)
    vocal_group = group_mix(processed, VOCAL_KEYS, sr, length)
    music_group = group_mix(processed, MUSIC_KEYS, sr, length)
    vocal_balance.update(
        {
            "lead_active_rms_db": round(base.active_rms_db(lead), 2),
            "female_layer_active_rms_db": round(base.active_rms_db(female), 2),
            "female_vs_lead_db": round(base.active_rms_db(female) - base.active_rms_db(lead), 2),
            "vocal_group_vs_music_active_db": round(base.active_rms_db(vocal_group) - base.active_rms_db(music_group), 2),
            "vocal_uniformity_1p5_outside_2db_after": uniformity["after"]["1.5"]["outside_plus_minus_2db_count"],
            "vocal_uniformity_1p5_outside_3db_after": uniformity["after"]["1.5"]["outside_plus_minus_3db_count"],
            "vocal_uniformity_1p5_mean_abs_after": uniformity["after"]["1.5"]["mean_abs_deviation_db"],
            "dynamic_eq_policy": "moderate; melodic-stem presence pocket max 1.05dB, drums/bass max 0.45dB",
        }
    )
    return processed, sr, duration, vocal_balance


def premaster_path() -> Path:
    return base.RENDERS / PREMASTER_NAME


def plateau_path() -> Path:
    return base.RENDERS / PLATEAU_NAME


def floor_path() -> Path:
    return base.RENDERS / FLOOR_NAME


def final_master() -> None:
    v4.premaster_bus_leveling(base.REAPER_PRINT, premaster_path())
    v5.apply_plateau_leveling(premaster_path(), plateau_path(), target_rms_db=-19.9)
    v6.apply_premaster_floor_lock(plateau_path(), floor_path(), floor_margin_db=2.35)
    filter_graph = (
        "highpass=f=24,"
        "equalizer=f=230:t=q:w=0.95:g=-0.10,"
        "equalizer=f=3150:t=q:w=0.95:g=0.06,"
        "equalizer=f=7600:t=q:w=0.85:g=-0.06,"
        "volume=3.25dB,"
        "alimiter=limit=0.82:attack=2:release=115:level=false"
    )
    subprocess.run(
        [
            base.FFMPEG,
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(floor_path()),
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
    subprocess.run([base.FFMPEG, "-y", "-hide_banner", "-loglevel", "error", "-i", str(base.FINAL_WAV), "-c:a", "libmp3lame", "-b:a", "320k", str(base.FINAL_MP3)], check=True)


def write_consistency_reports(paths: dict[str, Path]) -> dict[str, Any]:
    compare_paths = {
        "source_suno_full_mix": paths["full_reference"],
        "v08_moderate_dynamic_eq_premaster": premaster_path(),
        "v08_floor_premaster": floor_path(),
        "v08_final": base.FINAL_WAV,
    }
    rows: list[dict[str, Any]] = []
    summary: dict[str, Any] = {}
    for label, path in compare_paths.items():
        if not path.exists():
            continue
        item_rows = v4.write_phrase_analysis(label, path)
        rows.extend(item_rows)
        summary[label] = {}
        for window_s in (1.5, 3.0, 6.0):
            selected = [row for row in item_rows if row["window_s"] == window_s and row["start_s"] >= 6.0 and row["end_s"] <= 137.0]
            deviations = np.array([float(row["deviation_from_active_median_db"]) for row in selected], dtype=np.float32)
            summary[label][str(window_s)] = {
                "count": len(selected),
                "outside_plus_minus_3db_count": int(np.sum(np.abs(deviations) > 3.0)) if len(deviations) else 0,
                "max_positive_deviation_db": round(float(np.max(deviations)) if len(deviations) else 0.0, 2),
                "max_negative_deviation_db": round(float(np.min(deviations)) if len(deviations) else 0.0, 2),
                "mean_abs_deviation_db": round(float(np.mean(np.abs(deviations))) if len(deviations) else 0.0, 2),
                "forced_windows": [row for row in selected if row["forced_window"]],
            }
    write_json(base.REPORTS / WINDOW_REPORT_JSON, {"summary": summary, "rows": rows})
    write_csv(base.REPORTS / WINDOW_REPORT_CSV, rows)
    lines = ["# v08 Moderate Dynamic EQ Loudness Consistency Report", ""]
    for label, values in summary.items():
        lines.extend([f"## {label}", "", "| window | outside +/-3 dB | max + | max - | mean abs |", "| ---: | ---: | ---: | ---: | ---: |"])
        for window_s, row in values.items():
            lines.append(f"| {window_s}s | {row['outside_plus_minus_3db_count']} | {row['max_positive_deviation_db']} | {row['max_negative_deviation_db']} | {row['mean_abs_deviation_db']} |")
        lines.append("")
    (base.REPORTS / WINDOW_REPORT_MD).write_text("\n".join(lines) + "\n", encoding="utf-8")
    return summary


def write_reports(paths: dict[str, Path], processed: dict[str, Path], vocal_balance: dict[str, float], gate: dict[str, Any]) -> None:
    consistency = write_consistency_reports(paths)
    uniformity = json.loads((base.REPORTS / VOCAL_UNIFORMITY_JSON).read_text(encoding="utf-8"))
    rows = [
        base.audio_metrics(paths["full_reference"], "source_suno_full_mix"),
        base.audio_metrics(processed["lead_vocal"], "processed_lead_vocal_uniform_checked"),
        base.audio_metrics(processed["female_vocal"], "processed_female_vocal_uniform_checked"),
        base.audio_metrics(base.VOCAL_SOLO, "processed_vocal_solo_uniform_checked"),
        base.audio_metrics(base.REAPER_PRINT, "v08_reaper_print"),
        base.audio_metrics(premaster_path(), "v08_moderate_dynamic_eq_premaster"),
        base.audio_metrics(plateau_path(), "v08_plateau_premaster"),
        base.audio_metrics(floor_path(), "v08_floor_premaster"),
        base.audio_metrics(base.FINAL_WAV, "v08_final_master_wav"),
        base.audio_metrics(base.FINAL_MP3, "v08_final_master_mp3"),
    ]
    write_json(base.REPORTS / "qc_metrics.json", rows)
    write_csv(base.REPORTS / "qc_metrics.csv", rows)
    source = rows[0]
    final = rows[-2]
    mp3 = rows[-1]
    final_summary = consistency.get("v08_final", {})
    vocal_after = uniformity["after"]
    qc_passed = (
        bool(gate.get("passed"))
        and (final.get("true_peak_dbfs") or 99) <= -1.0
        and (mp3.get("true_peak_dbfs") or 99) <= -1.0
        and final_summary.get("1.5", {}).get("outside_plus_minus_3db_count", 99) == 0
        and vocal_after.get("1.5", {}).get("outside_plus_minus_3db_count", 99) == 0
    )
    qc = {
        "passed": qc_passed,
        "status": "qc_passed_user_review_required" if qc_passed else "blocked",
        "delivery_ready": False,
        "source_lufs": source.get("integrated_lufs"),
        "final_lufs": final.get("integrated_lufs"),
        "final_true_peak_dbfs": final.get("true_peak_dbfs"),
        "mp3_true_peak_dbfs": mp3.get("true_peak_dbfs"),
        "vocal_balance": vocal_balance,
        "v08_final_phrase_summary": final_summary,
        "vocal_uniformity_after": vocal_after,
        "correction": "Dynamic EQ cuts are reduced versus v07, and vocal-group uniformity is separately measured/corrected before final render.",
        "gate": gate,
    }
    write_json(base.REPORTS / "qc_summary.json", qc)
    notes = [
        f"# {base.REPORT_TITLE}",
        "",
        "## Correction",
        "",
        "- Dynamic EQ is moderate: melodic-stem presence pocket max 1.05 dB; drums/bass max 0.45 dB.",
        "- Overall music size still follows the original Suno full/stem export.",
        "- Vocal group uniformity is separately printed and QC checked before mastering.",
        "",
        "## Deliverables",
        "",
        f"- Final WAV: `{base.rel(base.FINAL_WAV)}`",
        f"- Final MP3: `{base.rel(base.FINAL_MP3)}`",
        f"- Vocal solo: `{base.rel(base.VOCAL_SOLO)}`",
        f"- A/B preview: `{base.rel(base.AB_PREVIEW_MP3)}`",
        f"- Deliverable ZIP: `{base.rel(base.DELIVERABLE_ZIP)}`",
        "",
        "## QC",
        "",
        f"- Source Suno full mix: `{source.get('integrated_lufs')}` LUFS / TP `{source.get('true_peak_dbfs')}` dBFS",
        f"- Final WAV: `{final.get('integrated_lufs')}` LUFS / TP `{final.get('true_peak_dbfs')}` dBFS",
        f"- Final MP3 TP: `{mp3.get('true_peak_dbfs')}` dBFS",
        f"- Final 1.5s outside +/-3dB: `{final_summary.get('1.5', {}).get('outside_plus_minus_3db_count')}`",
        f"- Vocal 1.5s outside +/-3dB after correction: `{vocal_after.get('1.5', {}).get('outside_plus_minus_3db_count')}`",
        f"- Vocal 1.5s mean abs deviation after correction: `{vocal_after.get('1.5', {}).get('mean_abs_deviation_db')}` dB",
        f"- Vocal chain gate passed: `{gate.get('passed')}`",
        "",
        "## Evidence",
        "",
        f"- Dynamic EQ report: `{base.rel(base.REPORTS / v7.DYNAMIC_EQ_JSON)}`",
        f"- Music constant report: `{base.rel(base.REPORTS / v7.MUSIC_CONSTANT_JSON)}`",
        f"- Vocal uniformity report: `{base.rel(base.REPORTS / VOCAL_UNIFORMITY_JSON)}`",
        f"- Final consistency report: `{base.rel(base.REPORTS / WINDOW_REPORT_JSON)}`",
        f"- Plugin trace: `{base.rel(base.TRACE_JSON)}`",
    ]
    (base.REPORTS / base.REPORT_FILENAME).write_text("\n".join(notes) + "\n", encoding="utf-8")


def build_zip() -> None:
    base.DELIVERABLE_ZIP.unlink(missing_ok=True)
    files = [
        base.FINAL_WAV,
        base.FINAL_MP3,
        base.VOCAL_SOLO,
        base.AB_PREVIEW_MP3,
        base.REAPER_PRINT,
        premaster_path(),
        plateau_path(),
        floor_path(),
        base.RPP,
        base.BUILD_LUA,
        base.RENDER_LUA,
        base.TRACE_JSON,
        base.TRACE_MD,
        base.REPORTS / "vocal_chain_gate.json",
        base.REPORTS / "qc_metrics.json",
        base.REPORTS / "qc_metrics.csv",
        base.REPORTS / "qc_summary.json",
        base.REPORTS / base.REPORT_FILENAME,
        base.REPORTS / v7.DYNAMIC_EQ_JSON,
        base.REPORTS / v7.DYNAMIC_EQ_CSV,
        base.REPORTS / v7.MUSIC_CONSTANT_JSON,
        base.REPORTS / v7.MUSIC_CONSTANT_CSV,
        base.REPORTS / VOCAL_UNIFORMITY_JSON,
        base.REPORTS / VOCAL_UNIFORMITY_CSV,
        base.REPORTS / WINDOW_REPORT_JSON,
        base.REPORTS / WINDOW_REPORT_CSV,
        base.REPORTS / WINDOW_REPORT_MD,
        base.REPORTS / "suno_vocal_lock_report.json",
        base.REPORTS / v4.PHRASE_BUS_REPORT_JSON,
        base.REPORTS / v4.PHRASE_BUS_REPORT_CSV,
        base.REPORTS / v5.PLATEAU_REPORT_JSON,
        base.REPORTS / v5.PLATEAU_REPORT_CSV,
        base.REPORTS / v6.FLOOR_LOCK_REPORT_JSON,
        base.REPORTS / v6.FLOOR_LOCK_REPORT_CSV,
        base.REPORTS / "vocal_gap_cleanup_decisions.json",
        base.REPORTS / "female_mask_layer_decisions.json",
    ]
    with base.zipfile.ZipFile(base.DELIVERABLE_ZIP, "w", compression=base.zipfile.ZIP_DEFLATED) as archive:
        seen: set[Path] = set()
        for path in files:
            if path.exists() and path not in seen:
                archive.write(path, path.relative_to(ROOT).as_posix())
                seen.add(path)


def main() -> int:
    configure_base()
    v7.apply_dynamic_eq_music_pocket = moderate_dynamic_eq_music_pocket
    v7.apply_music_constant_curve = moderate_music_constant_curve
    base.process_lead_vocal = v1.process_lead_vocal
    base.process_female_layer = v1.process_female_mask_layer
    base.process_backing_vocals = v1.process_backing_vocals
    base.process_instrument = v1.process_instrument
    base.write_processed = write_processed
    base.final_master = final_master
    base.write_reports = write_reports
    base.build_zip = build_zip
    return base.main()


if __name__ == "__main__":
    raise SystemExit(main())

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
V03_SCRIPT = ROOT / "tools" / "mwolla_v03_premaster_consistent_master.py"
SLUG = "mwolla_v09_suno_reference_dynamic_eq_master"


spec = importlib.util.spec_from_file_location("mwolla_v03_premaster_consistent_master", V03_SCRIPT)
if spec is None or spec.loader is None:
    raise RuntimeError(f"Could not load v03 script: {V03_SCRIPT}")
v3 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v3)
base = v3.base
v2 = v3.v2


PHRASE_PRE_RENDER_JSON = "phrase_riding_pre_render.json"
PROBLEM_CLASSIFICATION_JSON = "problem_window_cause_classification.json"
PROBLEM_CLASSIFICATION_MD = "problem_window_cause_classification.md"
VOCAL_LEVEL_LOCK_JSON = "lead_vocal_active_level_lock_report.json"
VOCAL_LEVEL_LOCK_CSV = "lead_vocal_active_level_lock_report.csv"
VOCAL_LEVEL_LOCK_MD = "lead_vocal_active_level_lock_report.md"
VOCAL_RIDE_JSON = "vocal_riding_curve_report.json"
VOCAL_RIDE_CSV = "vocal_riding_curve_report.csv"
MUSIC_RIDE_JSON = "music_stem_riding_curve_report.json"
MUSIC_RIDE_CSV = "music_stem_riding_curve_report.csv"
PHRASE_PREMASTER_JSON = "phrase_premaster_bus_leveling_report.json"
PHRASE_PREMASTER_NAME = "mwolla_v09_PHRASE_LEVELED_PREMASTER_24-48.wav"
PHRASE_REPORT_JSON = "phrase_level_consistency_report.json"
PHRASE_REPORT_CSV = "phrase_level_consistency_report.csv"
PHRASE_REPORT_MD = "phrase_level_consistency_report.md"
FINAL_LOCK_REPORT_JSON = "post_final_level_lock_report.json"
FINAL_LOCKED_NAME = "mwolla_v09_POST_FINAL_LEVEL_LOCK_24-48.wav"
SUNO_REFERENCE_DYN_EQ_JSON = "suno_reference_dynamic_eq_report.json"
SUNO_REFERENCE_DYN_EQ_CSV = "suno_reference_dynamic_eq_windows.csv"
SUNO_REFERENCE_DYN_EQ_MD = "suno_reference_dynamic_eq_report.md"

VOCAL_KEYS = ("lead_vocal", "female_vocal", "backing_vocals", "vocal_reverb", "vocal_delay")
MUSIC_KEYS = ("woodwinds", "brass", "fx", "synth", "strings", "percussion", "keyboard", "guitar", "bass", "drums")
RIDE_TARGET_KEYS = set(VOCAL_KEYS) | set(MUSIC_KEYS)
FORCED_LOW_WINDOWS = ((12.0, 13.5), (19.5, 21.0), (27.0, 28.5), (70.5, 72.0), (90.0, 91.5))
SECONDARY_LOW_WINDOWS = ((48.0, 49.5), (72.0, 73.5), (127.5, 129.0))
FORCED_HIGH_WINDOWS = ((64.5, 66.0), (66.0, 67.5), (67.5, 69.0))
ACTIVE_START_S = 6.0
ACTIVE_END_S = 137.0


def configure_base() -> None:
    v3.configure_base()
    base.SLUG = SLUG
    base.WORK = ROOT / "audio_work" / SLUG
    base.SOURCE = base.WORK / "source_stems"
    base.PROCESSED = base.WORK / "processed_stems"
    base.REAPER_DIR = ROOT / "reaper" / SLUG
    base.RENDERS = ROOT / "renders" / SLUG
    base.REPORTS = ROOT / "reports" / SLUG

    base.RPP = base.REAPER_DIR / "mwolla_v09_SUNO_REF_DYNAMIC_EQ_MASTER.rpp"
    base.BUILD_LUA = base.REAPER_DIR / "build_mwolla_v09_suno_reference_dynamic_eq_master.lua"
    base.RUN_BUILD_LUA = base.REAPER_DIR / "run_build_mwolla_v09_suno_reference_dynamic_eq_master.lua"
    base.RENDER_LUA = base.REAPER_DIR / "render_mwolla_v09_suno_reference_dynamic_eq_master.lua"
    base.RUN_RENDER_LUA = base.REAPER_DIR / "run_render_mwolla_v09_suno_reference_dynamic_eq_master.lua"
    base.TRACE_JSON = base.REPORTS / "actual_reaper_plugin_trace.json"
    base.TRACE_MD = base.REPORTS / "actual_reaper_plugin_trace.md"

    base.REAPER_PRINT = base.RENDERS / "mwolla_v09_REAPERPRINT_24-48.wav"
    base.FINAL_WAV = base.RENDERS / "mwolla_v09_SUNO_REF_DYNAMIC_EQ_MASTER.wav"
    base.FINAL_MP3 = base.RENDERS / "mwolla_v09_SUNO_REF_DYNAMIC_EQ_MASTER_320k.mp3"
    base.VOCAL_SOLO = base.RENDERS / "mwolla_v09_VOCAL_SOLO_suno_ref_dynamic_eq.wav"
    base.AB_PREVIEW_MP3 = base.RENDERS / "mwolla_v09_AB_original_to_suno_ref_dynamic_eq_master_320k.mp3"
    base.DELIVERABLE_ZIP = base.RENDERS / "mwolla_v09_SUNO_REF_DYNAMIC_EQ_MASTER_DELIVERABLE.zip"

    base.REPORT_FILENAME = "mwolla_v09_suno_reference_dynamic_eq_master_report.md"
    base.REPORT_TITLE = "Mwolla v09 Suno Reference Dynamic EQ Master Report"
    base.PROJECT_NOTES = (
        "mwolla v09 Suno-reference dynamic EQ master: original full mix and source music stems are used "
        "as the tonal/level reference. Lead vocal active level remains locked, while the music bus is "
        "printed through vocal-sidechain dynamic EQ pockets and a music level guard before REAPER."
    )


def premaster_path() -> Path:
    return base.RENDERS / PHRASE_PREMASTER_NAME


def final_locked_path() -> Path:
    return base.RENDERS / FINAL_LOCKED_NAME


def db_to_amp(db: float | np.ndarray) -> np.ndarray:
    return np.power(10.0, np.asarray(db) / 20.0)


def amp_to_db(value: float | np.ndarray) -> np.ndarray:
    return 20.0 * np.log10(np.maximum(np.asarray(value), 1e-12))


def pad_or_trim(y: np.ndarray, length: int) -> np.ndarray:
    return v2.pad_or_trim(y, length)


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    keys: list[str] = []
    for row in rows:
        for key in row:
            if key not in keys:
                keys.append(key)
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)


def write_wav(path: Path, sr: int, y: np.ndarray) -> None:
    base.write_wav(path, sr, y.astype(np.float32))


def window_rows(y: np.ndarray, sr: int, window_s: float = 1.5) -> list[dict[str, float]]:
    mono = np.mean(y, axis=1).astype(np.float32)
    frame = int(round(sr * window_s))
    rows: list[dict[str, float]] = []
    for start in range(0, len(mono), frame):
        end = min(len(mono), start + frame)
        if end - start < int(sr * 0.45):
            break
        chunk = mono[start:end]
        rms = float(np.sqrt(np.mean(chunk * chunk) + 1e-12))
        peak = float(np.max(np.abs(chunk))) if len(chunk) else 0.0
        rows.append(
            {
                "start_s": round(start / sr, 3),
                "end_s": round(end / sr, 3),
                "rms_db": round(float(amp_to_db(rms)), 2),
                "peak_db": round(float(amp_to_db(peak)), 2),
            }
        )
    return rows


def active_levels(rows: list[dict[str, Any]]) -> np.ndarray:
    levels = np.array(
        [
            float(row["rms_db"])
            for row in rows
            if ACTIVE_START_S <= float(row["start_s"]) < ACTIVE_END_S
        ],
        dtype=np.float32,
    )
    if len(levels) == 0:
        levels = np.array([float(row["rms_db"]) for row in rows], dtype=np.float32)
    if len(levels) == 0:
        return np.array([0.0], dtype=np.float32)
    threshold = float(np.percentile(levels, 12.0))
    active = levels[levels > threshold]
    return active if len(active) else levels


def active_median(rows: list[dict[str, Any]]) -> float:
    return float(np.median(active_levels(rows)))


def forced_window_kind(start_s: float, end_s: float) -> str | None:
    for a, b in FORCED_LOW_WINDOWS:
        if abs(start_s - a) < 0.01 and abs(end_s - b) < 0.01:
            return "forced_low"
    for a, b in SECONDARY_LOW_WINDOWS:
        if abs(start_s - a) < 0.01 and abs(end_s - b) < 0.01:
            return "secondary_low"
    for a, b in FORCED_HIGH_WINDOWS:
        if abs(start_s - a) < 0.01 and abs(end_s - b) < 0.01:
            return "forced_high"
    return None


def group_mix(processed: dict[str, Path], keys: tuple[str, ...], sr: int, length: int) -> np.ndarray:
    mix = np.zeros((length, 2), dtype=np.float32)
    for key in keys:
        path = processed.get(key)
        if not path or not path.exists():
            continue
        stem_sr, y, _ = base.read_wav(path)
        if stem_sr != sr:
            raise RuntimeError(f"Sample-rate mismatch in processed stem {key}: {stem_sr} != {sr}")
        gain_db = float(v2.TRACK_MIX_DB.get(key, 0.0))
        mix += pad_or_trim(y, length) * float(db_to_amp(gain_db))
    return mix.astype(np.float32)


def full_approx_mix(processed: dict[str, Path], sr: int, length: int) -> np.ndarray:
    return group_mix(processed, tuple(v2.TRACK_MIX_DB.keys()), sr, length)


def band_limited(y: np.ndarray, sr: int, low_hz: float, high_hz: float) -> np.ndarray:
    high_hz = min(high_hz, sr * 0.5 - 200.0)
    low_hz = max(20.0, min(low_hz, high_hz - 50.0))
    return base.butter_filter(y.astype(np.float32), sr, "bandpass", (low_hz, high_hz), order=3).astype(np.float32)


def band_rows(y: np.ndarray, sr: int, low_hz: float, high_hz: float) -> list[dict[str, float]]:
    return window_rows(band_limited(y, sr, low_hz, high_hz), sr, 1.5)


def apply_stft_dynamic_eq(
    y: np.ndarray,
    sr: int,
    level_curve_db: np.ndarray,
    lowmid_curve_db: np.ndarray,
    presence_curve_db: np.ndarray,
    glare_curve_db: np.ndarray,
) -> np.ndarray:
    length = len(y)
    nperseg = 4096
    noverlap = 3072
    out = np.zeros_like(y, dtype=np.float32)
    for ch in range(y.shape[1]):
        freqs, times, zxx = base.signal.stft(
            y[:, ch].astype(np.float32),
            fs=sr,
            window="hann",
            nperseg=nperseg,
            noverlap=noverlap,
            boundary="zeros",
            padded=True,
        )
        frame_idx = np.clip(np.round(times * sr).astype(np.int64), 0, length - 1)
        gain_db = np.broadcast_to(level_curve_db[frame_idx], zxx.shape).astype(np.float32).copy()
        lowmid_mask = (freqs >= 250.0) & (freqs < 650.0)
        presence_mask = (freqs >= 1500.0) & (freqs < 5200.0)
        glare_mask = (freqs >= 4200.0) & (freqs < 8500.0)
        gain_db[lowmid_mask, :] += lowmid_curve_db[frame_idx][None, :]
        gain_db[presence_mask, :] += presence_curve_db[frame_idx][None, :]
        gain_db[glare_mask, :] += glare_curve_db[frame_idx][None, :]
        zxx = zxx * db_to_amp(gain_db)
        _, rebuilt = base.signal.istft(
            zxx,
            fs=sr,
            window="hann",
            nperseg=nperseg,
            noverlap=noverlap,
            input_onesided=True,
        )
        out[:, ch] = pad_or_trim(rebuilt[:, None], length)[:, 0]
    return out.astype(np.float32)


def window_map(rows: list[dict[str, Any]]) -> dict[float, dict[str, Any]]:
    return {round(float(row["start_s"]), 3): row for row in rows}


def band_delta_summary(
    vocal_mix: np.ndarray,
    music_before: np.ndarray,
    music_after: np.ndarray,
    lead_rows: list[dict[str, Any]],
    sr: int,
) -> dict[str, Any]:
    vocal_presence = window_map(band_rows(vocal_mix, sr, 1500.0, 5200.0))
    music_before_presence = window_map(band_rows(music_before, sr, 1500.0, 5200.0))
    music_after_presence = window_map(band_rows(music_after, sr, 1500.0, 5200.0))
    ratios_before: list[float] = []
    ratios_after: list[float] = []
    rows: list[dict[str, Any]] = []
    for row in lead_rows:
        if not row.get("is_vocal_active"):
            continue
        start_s = round(float(row["start_s"]), 3)
        v = vocal_presence.get(start_s)
        mb = music_before_presence.get(start_s)
        ma = music_after_presence.get(start_s)
        if not (v and mb and ma):
            continue
        before = float(v["rms_db"]) - float(mb["rms_db"])
        after = float(v["rms_db"]) - float(ma["rms_db"])
        ratios_before.append(before)
        ratios_after.append(after)
        rows.append(
            {
                "start_s": start_s,
                "end_s": row["end_s"],
                "vocal_presence_rms_db": v["rms_db"],
                "music_presence_before_db": mb["rms_db"],
                "music_presence_after_db": ma["rms_db"],
                "vocal_over_music_presence_before_db": round(before, 2),
                "vocal_over_music_presence_after_db": round(after, 2),
                "presence_ratio_improvement_db": round(after - before, 2),
            }
        )
    if not ratios_before:
        return {"active_window_count": 0, "rows": []}
    before_arr = np.array(ratios_before, dtype=np.float32)
    after_arr = np.array(ratios_after, dtype=np.float32)
    return {
        "active_window_count": len(rows),
        "before_p10_vocal_over_music_presence_db": round(float(np.percentile(before_arr, 10)), 2),
        "after_p10_vocal_over_music_presence_db": round(float(np.percentile(after_arr, 10)), 2),
        "before_median_vocal_over_music_presence_db": round(float(np.median(before_arr)), 2),
        "after_median_vocal_over_music_presence_db": round(float(np.median(after_arr)), 2),
        "median_presence_ratio_improvement_db": round(float(np.median(after_arr - before_arr)), 2),
        "worst_before_windows": sorted(rows, key=lambda item: item["vocal_over_music_presence_before_db"])[:10],
        "rows": rows,
    }


def apply_suno_reference_dynamic_eq(
    paths: dict[str, Path],
    processed: dict[str, Path],
    sr: int,
    length: int,
) -> dict[str, Any]:
    raw_music_ref = group_mix(paths, MUSIC_KEYS, sr, length)
    source_sr, source_full_ref, _ = base.read_wav(paths["full_reference"])
    if source_sr != sr:
        raise RuntimeError("Suno full-reference sample-rate mismatch")
    source_full_ref = pad_or_trim(source_full_ref, length)

    before_music = group_mix(processed, MUSIC_KEYS, sr, length)
    vocal_mix = group_mix(processed, VOCAL_KEYS, sr, length)
    lead_sr, lead, _ = base.read_wav(processed["lead_vocal"])
    if lead_sr != sr:
        raise RuntimeError("Lead vocal sample-rate mismatch in dynamic EQ pass")
    lead = pad_or_trim(lead, length)
    lead_rows, _ = active_vocal_rows(lead, sr, 1.5)
    lead_by_start = window_map(lead_rows)

    raw_music_rows = window_rows(raw_music_ref, sr, 1.5)
    source_full_rows = window_rows(source_full_ref, sr, 1.5)
    before_music_rows = window_rows(before_music, sr, 1.5)
    before_presence_rows = band_rows(before_music, sr, 1500.0, 5200.0)
    raw_presence_rows = band_rows(raw_music_ref, sr, 1500.0, 5200.0)
    before_glare_rows = band_rows(before_music, sr, 4200.0, 8500.0)
    raw_glare_rows = band_rows(raw_music_ref, sr, 4200.0, 8500.0)
    before_lowmid_rows = band_rows(before_music, sr, 250.0, 650.0)
    raw_lowmid_rows = band_rows(raw_music_ref, sr, 250.0, 650.0)

    music_target = active_median(before_music_rows)
    raw_music_target = active_median(raw_music_rows)
    source_full_target = active_median(source_full_rows)
    presence_offset = active_median(before_presence_rows) - active_median(raw_presence_rows)
    glare_offset = active_median(before_glare_rows) - active_median(raw_glare_rows)
    lowmid_offset = active_median(before_lowmid_rows) - active_median(raw_lowmid_rows)

    raw_music_by_start = window_map(raw_music_rows)
    source_full_by_start = window_map(source_full_rows)
    raw_presence_by_start = window_map(raw_presence_rows)
    raw_glare_by_start = window_map(raw_glare_rows)
    raw_lowmid_by_start = window_map(raw_lowmid_rows)

    music_level_gains = np.zeros(len(before_music_rows), dtype=np.float32)
    presence_gains = np.zeros(len(before_music_rows), dtype=np.float32)
    glare_gains = np.zeros(len(before_music_rows), dtype=np.float32)
    lowmid_gains = np.zeros(len(before_music_rows), dtype=np.float32)
    report_rows: list[dict[str, Any]] = []

    for i, row in enumerate(before_music_rows):
        start_s = round(float(row["start_s"]), 3)
        if not (ACTIVE_START_S <= start_s < ACTIVE_END_S):
            report_rows.append(
                {
                    "start_s": start_s,
                    "end_s": row["end_s"],
                    "is_vocal_active": False,
                    "music_level_gain_db": 0.0,
                    "presence_dyn_eq_gain_db": 0.0,
                    "glare_dyn_eq_gain_db": 0.0,
                    "lowmid_dyn_eq_gain_db": 0.0,
                    "reason": "outside active range",
                }
            )
            continue

        lead_row = lead_by_start.get(start_s, {})
        vocal_active = bool(lead_row.get("is_vocal_active"))
        raw_music_row = raw_music_by_start.get(start_s, row)
        source_full_row = source_full_by_start.get(start_s, row)
        raw_presence_row = raw_presence_by_start.get(start_s, before_presence_rows[i])
        raw_glare_row = raw_glare_by_start.get(start_s, before_glare_rows[i])
        raw_lowmid_row = raw_lowmid_by_start.get(start_s, before_lowmid_rows[i])

        music_rms = float(row["rms_db"])
        raw_music_rms = float(raw_music_row["rms_db"])
        source_full_rms = float(source_full_row["rms_db"])
        music_drop = music_target - music_rms
        music_excess = music_rms - music_target
        raw_music_drop = raw_music_target - raw_music_rms
        source_full_drop = source_full_target - source_full_rms

        level_gain = 0.0
        if music_drop > 1.45:
            # Keep the music size stable against the Suno source; only near-empty source gaps are guarded.
            source_gap_guard = 0.82 if raw_music_drop > 9.0 and source_full_drop > 5.5 else 1.0
            level_gain = min((music_drop - 0.25) * 0.84 * source_gap_guard, 5.8)
        elif music_excess > 1.35:
            level_gain = -min((music_excess - 0.30) * 0.74, 2.4)
        if abs(level_gain) < 0.18:
            level_gain = 0.0

        desired_presence = float(raw_presence_row["rms_db"]) + presence_offset
        desired_glare = float(raw_glare_row["rms_db"]) + glare_offset
        desired_lowmid = float(raw_lowmid_row["rms_db"]) + lowmid_offset
        presence_excess = float(before_presence_rows[i]["rms_db"]) - desired_presence
        glare_excess = float(before_glare_rows[i]["rms_db"]) - desired_glare
        lowmid_excess = float(before_lowmid_rows[i]["rms_db"]) - desired_lowmid

        presence_cut = 0.0
        glare_cut = 0.0
        lowmid_cut = 0.0
        reason_bits: list[str] = []
        if vocal_active:
            level_lift = max(level_gain, 0.0)
            presence_cut = min(max(1.30, 1.35 + max(presence_excess, 0.0) * 0.62 + level_lift * 1.18), 8.0)
            glare_cut = min(max(0.55, 0.78 + max(glare_excess, 0.0) * 0.46 + level_lift * 0.58), 4.0)
            lowmid_cut = min(max(0.40, 0.55 + max(lowmid_excess, 0.0) * 0.38 + level_lift * 0.42), 3.0)
            reason_bits.append("vocal-sidechain dynamic EQ pocket")
        else:
            if presence_excess > 1.8:
                presence_cut = min((presence_excess - 0.55) * 0.38, 1.35)
                reason_bits.append("Suno-reference presence trim")
            if glare_excess > 1.7:
                glare_cut = min((glare_excess - 0.50) * 0.32, 1.1)
                reason_bits.append("Suno-reference glare trim")
            if lowmid_excess > 2.0:
                lowmid_cut = min((lowmid_excess - 0.65) * 0.26, 0.9)
                reason_bits.append("Suno-reference low-mid trim")

        music_level_gains[i] = float(np.clip(level_gain, -2.4, 5.8))
        presence_gains[i] = -float(np.clip(presence_cut, 0.0, 8.0))
        glare_gains[i] = -float(np.clip(glare_cut, 0.0, 4.0))
        lowmid_gains[i] = -float(np.clip(lowmid_cut, 0.0, 3.0))
        report_rows.append(
            {
                "start_s": start_s,
                "end_s": row["end_s"],
                "is_vocal_active": vocal_active,
                "suno_raw_music_rms_db": round(raw_music_rms, 2),
                "suno_raw_music_delta_db": round(raw_music_rms - raw_music_target, 2),
                "suno_full_mix_rms_db": round(source_full_rms, 2),
                "suno_full_mix_delta_db": round(source_full_rms - source_full_target, 2),
                "processed_music_rms_db": round(music_rms, 2),
                "processed_music_delta_db": round(music_rms - music_target, 2),
                "music_level_gain_db": round(float(music_level_gains[i]), 2),
                "music_presence_rms_db": before_presence_rows[i]["rms_db"],
                "suno_presence_target_db": round(desired_presence, 2),
                "presence_excess_db": round(presence_excess, 2),
                "presence_dyn_eq_gain_db": round(float(presence_gains[i]), 2),
                "glare_excess_db": round(glare_excess, 2),
                "glare_dyn_eq_gain_db": round(float(glare_gains[i]), 2),
                "lowmid_excess_db": round(lowmid_excess, 2),
                "lowmid_dyn_eq_gain_db": round(float(lowmid_gains[i]), 2),
                "reason": "; ".join(reason_bits),
            }
        )

    level_curve_db = curve_from_window_gains(music_level_gains, before_music_rows, sr, length, smooth_s=0.68)
    presence_curve_db = curve_from_window_gains(presence_gains, before_music_rows, sr, length, smooth_s=0.20)
    glare_curve_db = curve_from_window_gains(glare_gains, before_music_rows, sr, length, smooth_s=0.24)
    lowmid_curve_db = curve_from_window_gains(lowmid_gains, before_music_rows, sr, length, smooth_s=0.28)
    _, open_score, _ = vocal_activity_data(lead, sr)
    presence_curve_db = np.minimum(presence_curve_db, -0.55 * open_score)
    glare_curve_db = np.minimum(glare_curve_db, -0.22 * open_score)
    lowmid_curve_db = np.minimum(lowmid_curve_db, -0.15 * open_score)
    level_curve_db = np.clip(level_curve_db, -2.4, 5.8)
    presence_curve_db = np.clip(presence_curve_db, -8.0, 0.0)
    glare_curve_db = np.clip(glare_curve_db, -4.0, 0.0)
    lowmid_curve_db = np.clip(lowmid_curve_db, -3.0, 0.0)

    for key in MUSIC_KEYS:
        path = processed.get(key)
        if not path or not path.exists():
            continue
        stem_sr, y, _ = base.read_wav(path)
        if stem_sr != sr:
            raise RuntimeError(f"Sample-rate mismatch while applying Suno-reference dynamic EQ to {key}")
        y = pad_or_trim(y, length)
        adjusted = apply_stft_dynamic_eq(y, sr, level_curve_db, lowmid_curve_db, presence_curve_db, glare_curve_db)
        adjusted = base.soft_clip(adjusted.astype(np.float32), ceiling=0.958)
        write_wav(path, sr, adjusted)

    after_music = group_mix(processed, MUSIC_KEYS, sr, length)
    after_music_rows = window_rows(after_music, sr, 1.5)
    before_summary = summarize_window_rows(before_music_rows)
    after_summary = summarize_window_rows(after_music_rows)
    mask_summary = band_delta_summary(vocal_mix, before_music, after_music, lead_rows, sr)
    after_by_start = window_map(after_music_rows)
    for item in report_rows:
        after_row = after_by_start.get(round(float(item["start_s"]), 3))
        if after_row:
            item["post_dyn_eq_music_rms_db"] = after_row["rms_db"]
            item["post_dyn_eq_music_delta_db"] = round(float(after_row["rms_db"]) - after_summary["active_median_rms_db"], 2)

    report = {
        "method": (
            "Original Suno full mix and source music stems set the level/tonal reference. "
            "Music stems receive printed vocal-sidechain dynamic EQ pockets plus a wideband music-size guard."
        ),
        "source_full_reference": base.rel(paths["full_reference"]),
        "window_s": 1.5,
        "active_range_s": [ACTIVE_START_S, ACTIVE_END_S],
        "suno_raw_music_active_median_rms_db": round(raw_music_target, 2),
        "suno_full_mix_active_median_rms_db": round(source_full_target, 2),
        "music_before_summary": before_summary,
        "music_after_summary": after_summary,
        "max_music_level_gain_db": round(float(np.max(music_level_gains)), 2),
        "min_music_level_gain_db": round(float(np.min(music_level_gains)), 2),
        "max_presence_dyn_eq_cut_db": round(float(-np.min(presence_gains)), 2),
        "max_glare_dyn_eq_cut_db": round(float(-np.min(glare_gains)), 2),
        "max_lowmid_dyn_eq_cut_db": round(float(-np.min(lowmid_gains)), 2),
        "presence_mask_summary": mask_summary,
        "windows": report_rows,
    }
    base.REPORTS.mkdir(parents=True, exist_ok=True)
    (base.REPORTS / SUNO_REFERENCE_DYN_EQ_JSON).write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    write_csv(base.REPORTS / SUNO_REFERENCE_DYN_EQ_CSV, report_rows)
    lines = [
        "# Suno Reference Dynamic EQ Report",
        "",
        f"- Source full-mix reference: `{base.rel(paths['full_reference'])}`",
        f"- Suno raw music active median: `{report['suno_raw_music_active_median_rms_db']}` dBFS",
        f"- Music p10-p90 spread before: `{before_summary['active_p10_p90_spread_db']}` dB",
        f"- Music p10-p90 spread after: `{after_summary['active_p10_p90_spread_db']}` dB",
        f"- Music >3 dB low/high windows after: `{after_summary['low_windows_gt_3db_count']}` / `{after_summary['high_windows_gt_3db_count']}`",
        f"- Music level guard range: `{report['min_music_level_gain_db']}` to `{report['max_music_level_gain_db']}` dB",
        f"- Dynamic EQ max cuts: presence `{report['max_presence_dyn_eq_cut_db']}` dB, glare `{report['max_glare_dyn_eq_cut_db']}` dB, low-mid `{report['max_lowmid_dyn_eq_cut_db']}` dB",
        f"- Vocal/music presence median improvement: `{mask_summary.get('median_presence_ratio_improvement_db')}` dB",
        "",
        "| start | end | vocal active | music before | music after | level gain | presence cut | glare cut | lowmid cut | reason |",
        "| ---: | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for item in report_rows:
        if (
            item.get("is_vocal_active")
            or abs(float(item.get("music_level_gain_db", 0.0))) >= 1.0
            or abs(float(item.get("presence_dyn_eq_gain_db", 0.0))) >= 1.0
        ):
            lines.append(
                f"| {item['start_s']} | {item['end_s']} | {item.get('is_vocal_active')} | "
                f"{item.get('processed_music_rms_db')} | {item.get('post_dyn_eq_music_rms_db')} | "
                f"{item.get('music_level_gain_db')} | {item.get('presence_dyn_eq_gain_db')} | "
                f"{item.get('glare_dyn_eq_gain_db')} | {item.get('lowmid_dyn_eq_gain_db')} | {item.get('reason', '')} |"
            )
    (base.REPORTS / SUNO_REFERENCE_DYN_EQ_MD).write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report


def raw_stem_window_levels(paths: dict[str, Path], start_s: float, end_s: float, sr: int, length: int) -> dict[str, float | None]:
    out: dict[str, float | None] = {}
    start = int(round(start_s * sr))
    end = min(length, int(round(end_s * sr)))
    for key in (*MUSIC_KEYS, "backing_vocals", "lead_vocal", "female_vocal"):
        path = paths.get(key)
        if not path or not path.exists():
            out[key] = None
            continue
        stem_sr, y, _ = base.read_wav(path)
        if stem_sr != sr:
            out[key] = None
            continue
        chunk = pad_or_trim(y, length)[start:end]
        out[key] = round(float(amp_to_db(np.sqrt(np.mean(chunk * chunk) + 1e-12))), 2) if len(chunk) else None
    return out


def processed_stem_window_levels(processed: dict[str, Path], start_s: float, end_s: float, sr: int, length: int) -> dict[str, float | None]:
    out: dict[str, float | None] = {}
    start = int(round(start_s * sr))
    end = min(length, int(round(end_s * sr)))
    for key in (*MUSIC_KEYS, *VOCAL_KEYS):
        path = processed.get(key)
        if not path or not path.exists():
            out[key] = None
            continue
        stem_sr, y, _ = base.read_wav(path)
        if stem_sr != sr:
            out[key] = None
            continue
        chunk = pad_or_trim(y, length)[start:end]
        out[key] = round(float(amp_to_db(np.sqrt(np.mean(chunk * chunk) + 1e-12))), 2) if len(chunk) else None
    return out


def curve_from_window_gains(gains_db: np.ndarray, rows: list[dict[str, Any]], sr: int, length: int, smooth_s: float) -> np.ndarray:
    if len(rows) == 0:
        return np.zeros(length, dtype=np.float32)
    centers = np.array([(float(row["start_s"]) + float(row["end_s"])) * 0.5 for row in rows], dtype=np.float32)
    sample_times = np.arange(length, dtype=np.float32) / float(sr)
    if len(centers) > 1:
        curve_db = np.interp(sample_times, centers, gains_db, left=gains_db[0], right=gains_db[-1]).astype(np.float32)
    else:
        curve_db = np.full(length, float(gains_db[0]), dtype=np.float32)
    smooth = max(1, int(round(sr * smooth_s)))
    if smooth > 1:
        kernel = np.hanning(smooth * 2 + 1).astype(np.float32)
        kernel /= np.sum(kernel)
        curve_db = base.signal.fftconvolve(curve_db, kernel, mode="same").astype(np.float32)
    return curve_db.astype(np.float32)


def vocal_activity_data(y: np.ndarray, sr: int) -> tuple[np.ndarray, np.ndarray, float]:
    mono = np.mean(y, axis=1).astype(np.float32)
    band = base.butter_filter(np.column_stack([mono, mono]), sr, "bandpass", (130, 6500), order=3)
    env = base.envelope(np.mean(np.abs(band), axis=1), sr, 38.0)
    env_db = amp_to_db(env)
    # Deliberately fixed low threshold: this catches quiet sung words without opening pure tails.
    threshold_db = -45.0
    open_score = np.clip((env_db - threshold_db) / 10.0, 0.0, 1.0).astype(np.float32)
    smooth = max(1, int(round(sr * 0.16)))
    if smooth > 1:
        kernel = np.hanning(smooth * 2 + 1).astype(np.float32)
        kernel /= np.sum(kernel)
        open_score = base.signal.fftconvolve(open_score, kernel, mode="same").astype(np.float32)
    open_score = np.clip(open_score, 0.0, 1.0)
    return env_db.astype(np.float32), open_score, threshold_db


def active_vocal_rows(y: np.ndarray, sr: int, window_s: float = 1.5) -> tuple[list[dict[str, Any]], float]:
    mono = np.mean(y, axis=1).astype(np.float32)
    env_db, open_score, threshold_db = vocal_activity_data(y, sr)
    frame = int(round(sr * window_s))
    rows: list[dict[str, Any]] = []
    for start in range(0, len(mono), frame):
        end = min(len(mono), start + frame)
        if end - start < int(sr * 0.45):
            break
        env_chunk = env_db[start:end]
        open_chunk = open_score[start:end]
        hard_mask = env_chunk > threshold_db
        duty = float(np.mean(hard_mask)) if len(hard_mask) else 0.0
        window_chunk = mono[start:end]
        window_rms = float(np.sqrt(np.mean(window_chunk * window_chunk) + 1e-12))
        if np.any(hard_mask):
            active_chunk = window_chunk[hard_mask]
            active_rms = float(np.sqrt(np.mean(active_chunk * active_chunk) + 1e-12))
        else:
            active_rms = window_rms
        rows.append(
            {
                "start_s": round(start / sr, 3),
                "end_s": round(end / sr, 3),
                "vocal_active_duty": round(duty, 3),
                "window_rms_db": round(float(amp_to_db(window_rms)), 2),
                "active_vocal_rms_db": round(float(amp_to_db(active_rms)), 2),
                "open_score_mean": round(float(np.mean(open_chunk)) if len(open_chunk) else 0.0, 3),
                "is_vocal_active": bool(duty >= 0.22 and ACTIVE_START_S <= start / sr < ACTIVE_END_S),
            }
        )
    active_levels = np.array([row["active_vocal_rms_db"] for row in rows if row["is_vocal_active"]], dtype=np.float32)
    target = float(np.median(active_levels)) if len(active_levels) else -27.0
    return rows, target


def vocal_rows_summary(rows: list[dict[str, Any]], target: float | None = None) -> dict[str, Any]:
    active = [row for row in rows if row.get("is_vocal_active")]
    levels = np.array([row["active_vocal_rms_db"] for row in active], dtype=np.float32)
    if len(levels) == 0:
        return {
            "active_window_count": 0,
            "target_active_vocal_rms_db": round(float(target or 0.0), 2),
            "active_p10_p90_spread_db": 0.0,
            "low_windows_gt_2db_count": 0,
            "high_windows_gt_2db_count": 0,
            "low_windows_gt_3db_count": 0,
            "high_windows_gt_3db_count": 0,
            "worst_low_windows": [],
            "worst_high_windows": [],
        }
    ref = float(target) if target is not None else float(np.median(levels))
    lows2 = [row for row in active if ref - float(row["active_vocal_rms_db"]) > 2.0]
    highs2 = [row for row in active if float(row["active_vocal_rms_db"]) - ref > 2.0]
    lows3 = [row for row in active if ref - float(row["active_vocal_rms_db"]) > 3.0]
    highs3 = [row for row in active if float(row["active_vocal_rms_db"]) - ref > 3.0]
    return {
        "active_window_count": len(active),
        "target_active_vocal_rms_db": round(ref, 2),
        "active_median_rms_db": round(float(np.median(levels)), 2),
        "active_p10_rms_db": round(float(np.percentile(levels, 10)), 2),
        "active_p90_rms_db": round(float(np.percentile(levels, 90)), 2),
        "active_p10_p90_spread_db": round(float(np.percentile(levels, 90) - np.percentile(levels, 10)), 2),
        "low_windows_gt_2db_count": len(lows2),
        "high_windows_gt_2db_count": len(highs2),
        "low_windows_gt_3db_count": len(lows3),
        "high_windows_gt_3db_count": len(highs3),
        "worst_low_windows": sorted(
            [
                {
                    "start_s": row["start_s"],
                    "end_s": row["end_s"],
                    "active_vocal_rms_db": row["active_vocal_rms_db"],
                    "drop_db": round(ref - float(row["active_vocal_rms_db"]), 2),
                }
                for row in lows2
            ],
            key=lambda item: item["drop_db"],
            reverse=True,
        )[:12],
        "worst_high_windows": sorted(
            [
                {
                    "start_s": row["start_s"],
                    "end_s": row["end_s"],
                    "active_vocal_rms_db": row["active_vocal_rms_db"],
                    "excess_db": round(float(row["active_vocal_rms_db"]) - ref, 2),
                }
                for row in highs2
            ],
            key=lambda item: item["excess_db"],
            reverse=True,
        )[:12],
    }


def apply_lead_vocal_level_lock(processed: dict[str, Path], sr: int, length: int) -> dict[str, Any]:
    lead_path = processed["lead_vocal"]
    lead_sr, lead, _ = base.read_wav(lead_path)
    if lead_sr != sr:
        raise RuntimeError("Lead vocal sample-rate mismatch in vocal level lock")
    lead = pad_or_trim(lead, length)
    before_rows, target = active_vocal_rows(lead, sr, 1.5)

    gains = np.zeros(len(before_rows), dtype=np.float32)
    gain_rows: list[dict[str, Any]] = []
    for i, row in enumerate(before_rows):
        gain = 0.0
        if row["is_vocal_active"]:
            delta = target - float(row["active_vocal_rms_db"])
            gain = float(np.clip(delta * 1.24, -7.8, 13.5))
            if abs(gain) < 0.22:
                gain = 0.0
        gains[i] = gain
        gain_rows.append(
            {
                **row,
                "target_active_vocal_rms_db": round(target, 2),
                "delta_to_target_db": round(float(row["active_vocal_rms_db"]) - target, 2),
                "applied_lead_vocal_gain_db": round(gain, 2),
            }
        )

    curve_db = curve_from_window_gains(gains, before_rows, sr, length, smooth_s=0.18)
    _, open_score, _ = vocal_activity_data(lead, sr)
    # v09 Suno-reference pass: quiet sung words keep almost all of their computed gain.
    activity_weight = np.where(curve_db >= 0.0, np.maximum(open_score, 0.96), np.maximum(open_score, 0.86))
    curve_db = curve_db * activity_weight
    curve_db = np.clip(curve_db, -7.8, 13.5)

    follow = {
        "lead_vocal": 1.0,
        "female_vocal": 0.58,
        "backing_vocals": 0.48,
        "vocal_reverb": 0.52,
        "vocal_delay": 0.52,
    }
    for key, amount in follow.items():
        path = processed.get(key)
        if not path or not path.exists():
            continue
        stem_sr, y, _ = base.read_wav(path)
        if stem_sr != sr:
            raise RuntimeError(f"Sample-rate mismatch while applying vocal level lock to {key}")
        y = pad_or_trim(y, length)
        adjusted = y * db_to_amp(curve_db * amount)[:, None]
        adjusted = base.soft_clip(adjusted.astype(np.float32), ceiling=0.972 if key == "lead_vocal" else 0.952)
        write_wav(path, sr, adjusted)

    lead_after_sr, lead_after, _ = base.read_wav(lead_path)
    lead_after = pad_or_trim(lead_after, length)
    residual_rows, _ = active_vocal_rows(lead_after, sr, 1.5)
    residual_gains = np.zeros(len(residual_rows), dtype=np.float32)
    for i, row in enumerate(residual_rows):
        if row["is_vocal_active"]:
            delta = target - float(row["active_vocal_rms_db"])
            if abs(delta) >= 0.9:
                residual_gains[i] = float(np.clip(delta * 1.04, -4.5, 8.8))
    residual_curve_db = curve_from_window_gains(residual_gains, residual_rows, sr, length, smooth_s=0.14)
    _, residual_open, _ = vocal_activity_data(lead_after, sr)
    residual_weight = np.where(residual_curve_db >= 0.0, np.maximum(residual_open, 0.98), np.maximum(residual_open, 0.90))
    residual_curve_db = np.clip(residual_curve_db * residual_weight, -4.5, 8.8)
    residual_follow = {
        "lead_vocal": 1.0,
        "female_vocal": 0.42,
        "backing_vocals": 0.34,
        "vocal_reverb": 0.36,
        "vocal_delay": 0.36,
    }
    for key, amount in residual_follow.items():
        path = processed.get(key)
        if not path or not path.exists():
            continue
        stem_sr, y, _ = base.read_wav(path)
        if stem_sr != sr:
            raise RuntimeError(f"Sample-rate mismatch while applying residual vocal level lock to {key}")
        y = pad_or_trim(y, length)
        adjusted = y * db_to_amp(residual_curve_db * amount)[:, None]
        adjusted = base.soft_clip(adjusted.astype(np.float32), ceiling=0.974 if key == "lead_vocal" else 0.956)
        write_wav(path, sr, adjusted)

    lead_after_sr, lead_after, _ = base.read_wav(lead_path)
    after_rows, _ = active_vocal_rows(pad_or_trim(lead_after, length), sr, 1.5)
    for i, row in enumerate(gain_rows):
        if i < len(after_rows):
            row["post_lock_active_vocal_rms_db"] = after_rows[i]["active_vocal_rms_db"]
            row["post_lock_delta_to_target_db"] = round(float(after_rows[i]["active_vocal_rms_db"]) - target, 2)
            row["post_lock_change_db"] = round(float(after_rows[i]["active_vocal_rms_db"]) - float(row["active_vocal_rms_db"]), 2)
            row["residual_lead_vocal_gain_db"] = round(float(residual_gains[i]), 2) if i < len(residual_gains) else 0.0

    lead = pad_or_trim(base.read_wav(processed["lead_vocal"])[1], length)
    female = pad_or_trim(base.read_wav(processed["female_vocal"])[1], length)
    backing = pad_or_trim(base.read_wav(processed["backing_vocals"])[1], length)
    reverb = pad_or_trim(base.read_wav(processed["vocal_reverb"])[1], length)
    delay = pad_or_trim(base.read_wav(processed["vocal_delay"])[1], length)
    vocal_solo = lead + female + backing * float(db_to_amp(-1.2)) + reverb + delay
    vocal_solo = base.peak_cap(vocal_solo.astype(np.float32), -1.5)
    write_wav(base.VOCAL_SOLO, sr, vocal_solo)

    report = {
        "input_lead_vocal": base.rel(lead_path),
        "output_lead_vocal": base.rel(lead_path),
        "vocal_solo_rewritten": base.rel(base.VOCAL_SOLO),
        "window_s": 1.5,
        "activity_threshold_db": -45.0,
        "method": "Lead vocal active-window RMS level lock before REAPER. Quiet non-vocal gaps are not boosted; support vocals/reverb/delay follow the lead curve partially.",
        "pre_lock_summary": vocal_rows_summary(before_rows, target),
        "post_lock_summary": vocal_rows_summary(after_rows, target),
        "max_applied_lead_vocal_gain_db": round(float(np.max(gains)), 2),
        "min_applied_lead_vocal_gain_db": round(float(np.min(gains)), 2),
        "max_residual_lead_vocal_gain_db": round(float(np.max(residual_gains)), 2) if len(residual_gains) else 0.0,
        "min_residual_lead_vocal_gain_db": round(float(np.min(residual_gains)), 2) if len(residual_gains) else 0.0,
        "windows": gain_rows,
    }
    base.REPORTS.mkdir(parents=True, exist_ok=True)
    (base.REPORTS / VOCAL_LEVEL_LOCK_JSON).write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    write_csv(base.REPORTS / VOCAL_LEVEL_LOCK_CSV, gain_rows)
    lines = [
        "# Lead Vocal Active Level Lock Report",
        "",
        f"- Target active-vocal RMS: `{report['pre_lock_summary']['target_active_vocal_rms_db']}` dBFS",
        f"- Pre-lock active p10-p90 spread: `{report['pre_lock_summary']['active_p10_p90_spread_db']}` dB",
        f"- Post-lock active p10-p90 spread: `{report['post_lock_summary']['active_p10_p90_spread_db']}` dB",
        f"- Pre-lock >3 dB low/high active vocal windows: `{report['pre_lock_summary']['low_windows_gt_3db_count']}` / `{report['pre_lock_summary']['high_windows_gt_3db_count']}`",
        f"- Post-lock >3 dB low/high active vocal windows: `{report['post_lock_summary']['low_windows_gt_3db_count']}` / `{report['post_lock_summary']['high_windows_gt_3db_count']}`",
        f"- Lead vocal gain range: `{report['min_applied_lead_vocal_gain_db']}` to `{report['max_applied_lead_vocal_gain_db']}` dB",
        f"- Residual vocal gain range: `{report['min_residual_lead_vocal_gain_db']}` to `{report['max_residual_lead_vocal_gain_db']}` dB",
        "",
        "| start | end | duty | before | gain | after | after-target |",
        "| ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in gain_rows:
        if row["is_vocal_active"] and (
            abs(row["applied_lead_vocal_gain_db"]) >= 1.5 or abs(row.get("post_lock_delta_to_target_db", 0.0)) >= 2.0
        ):
            lines.append(
                f"| {row['start_s']} | {row['end_s']} | {row['vocal_active_duty']} | "
                f"{row['active_vocal_rms_db']} | {row['applied_lead_vocal_gain_db']} | "
                f"{row.get('post_lock_active_vocal_rms_db')} | {row.get('post_lock_delta_to_target_db')} |"
            )
    (base.REPORTS / VOCAL_LEVEL_LOCK_MD).write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report


def classify_and_build_phrase_curves(
    paths: dict[str, Path],
    processed: dict[str, Path],
    sr: int,
    length: int,
) -> tuple[np.ndarray, np.ndarray, dict[str, Any]]:
    source_sr, source_mix, _ = base.read_wav(paths["full_reference"])
    if source_sr != sr:
        raise RuntimeError("Source full-mix sample-rate mismatch")
    source_mix = pad_or_trim(source_mix, length)
    full_mix = full_approx_mix(processed, sr, length)
    vocal_mix = group_mix(processed, VOCAL_KEYS, sr, length)
    music_mix = group_mix(processed, MUSIC_KEYS, sr, length)

    full_rows = window_rows(full_mix, sr, 1.5)
    vocal_rows = window_rows(vocal_mix, sr, 1.5)
    music_rows = window_rows(music_mix, sr, 1.5)
    source_rows = window_rows(source_mix, sr, 1.5)
    full_target = active_median(full_rows)
    vocal_target = active_median(vocal_rows)
    music_target = active_median(music_rows)
    source_target = active_median(source_rows)

    vocal_gains = np.zeros(len(full_rows), dtype=np.float32)
    music_gains = np.zeros(len(full_rows), dtype=np.float32)
    problem_rows: list[dict[str, Any]] = []
    ride_rows: list[dict[str, Any]] = []

    for i, row in enumerate(full_rows):
        start_s = float(row["start_s"])
        end_s = float(row["end_s"])
        if not (ACTIVE_START_S <= start_s < ACTIVE_END_S):
            ride_rows.append(
                {
                    "start_s": start_s,
                    "end_s": end_s,
                    "window_kind": "",
                    "classification": "outside_active_range",
                    "full_delta_vs_active_median_db": None,
                    "vocal_rms_db": None,
                    "vocal_delta_vs_active_median_db": None,
                    "music_rms_db": None,
                    "music_delta_vs_active_median_db": None,
                    "source_rms_db": None,
                    "source_delta_vs_active_median_db": None,
                    "vocal_gain_db": 0.0,
                    "music_gain_db": 0.0,
                    "full_rms_db": row["rms_db"],
                    "reason": "outside active mix range",
                }
            )
            continue

        kind = forced_window_kind(start_s, end_s)
        full_rms = float(row["rms_db"])
        vocal_rms = float(vocal_rows[i]["rms_db"]) if i < len(vocal_rows) else -120.0
        music_rms = float(music_rows[i]["rms_db"]) if i < len(music_rows) else -120.0
        source_rms = float(source_rows[i]["rms_db"]) if i < len(source_rows) else -120.0
        full_drop = full_target - full_rms
        full_excess = full_rms - full_target
        vocal_drop = vocal_target - vocal_rms
        music_drop = music_target - music_rms
        vocal_excess = vocal_rms - vocal_target
        music_excess = music_rms - music_target
        source_drop = source_target - source_rms
        vocal_active = vocal_rms > vocal_target - 13.0

        classification = "stable"
        reason = ""
        vocal_gain = 0.0
        music_gain = 0.0

        is_low = full_drop > 2.55 or kind in {"forced_low", "secondary_low"}
        is_high = full_excess > 2.45 or kind == "forced_high"

        if is_low:
            lift = min(max(full_drop - 0.10, 1.1 if kind == "forced_low" else 0.0) * (1.12 if kind == "forced_low" else 0.94), 8.8)
            if vocal_active and vocal_drop > music_drop + 0.85 and vocal_drop > 1.5:
                classification = "vocal_low"
                vocal_gain = min(lift, 5.8)
                music_gain = min(max(lift * 0.30, 0.0), 1.9)
                reason = "vocal group sits farther below its active median than the music group"
            elif music_drop > vocal_drop + 0.85 and music_drop > 1.5:
                classification = "music_low"
                music_gain = min(lift, 8.4)
                vocal_gain = min(max(lift * 0.18, 0.0), 1.3) if vocal_active else 0.0
                reason = "music group is the main short-window dip"
            else:
                classification = "full_mix_low"
                music_gain = min(lift * 0.92, 7.4)
                vocal_gain = min(lift * 0.48, 3.0) if vocal_active else 0.0
                reason = "vocal and music move down together, so correction is shared before premaster"
            if source_drop > 3.5:
                reason += "; source full mix also has a dip, so the lift is conservative"
        elif is_high:
            cut = min(max(full_excess - 0.10, 1.05 if kind == "forced_high" else 0.0) * (1.00 if kind == "forced_high" else 0.82), 3.4)
            if music_excess > vocal_excess + 0.65:
                classification = "music_bass_drums_too_loud"
                music_gain = -cut
                vocal_gain = -min(max(vocal_excess - 1.0, 0.0) * 0.24, 0.7)
                reason = "music group carries the excess level, especially around hook energy"
            elif vocal_excess > music_excess + 0.65 and vocal_active:
                classification = "vocal_too_loud"
                vocal_gain = -min(cut, 1.4)
                music_gain = -min(cut * 0.42, 1.0)
                reason = "vocal group is the main excess source"
            else:
                classification = "master_premaster_imbalance"
                music_gain = -min(cut * 0.75, 2.3)
                vocal_gain = -min(cut * 0.25, 0.8) if vocal_active else 0.0
                reason = "full mix is hot without a single group clearly dominating"

        vocal_gains[i] = float(np.clip(vocal_gain, -3.2, 6.2))
        music_gains[i] = float(np.clip(music_gain, -3.4, 8.4))
        ride_item = {
            "start_s": start_s,
            "end_s": end_s,
            "window_kind": kind or "",
            "classification": classification,
            "full_rms_db": round(full_rms, 2),
            "full_delta_vs_active_median_db": round(full_rms - full_target, 2),
            "vocal_rms_db": round(vocal_rms, 2),
            "vocal_delta_vs_active_median_db": round(vocal_rms - vocal_target, 2),
            "music_rms_db": round(music_rms, 2),
            "music_delta_vs_active_median_db": round(music_rms - music_target, 2),
            "source_rms_db": round(source_rms, 2),
            "source_delta_vs_active_median_db": round(source_rms - source_target, 2),
            "vocal_gain_db": round(float(vocal_gains[i]), 2),
            "music_gain_db": round(float(music_gains[i]), 2),
            "reason": reason,
        }
        ride_rows.append(ride_item)
        if kind or classification != "stable":
            problem_rows.append(
                {
                    **ride_item,
                    "raw_stem_rms_db": raw_stem_window_levels(paths, start_s, end_s, sr, length),
                    "processed_stem_rms_db_before_phrase_ride": processed_stem_window_levels(processed, start_s, end_s, sr, length),
                }
            )

    vocal_curve_db = curve_from_window_gains(vocal_gains, full_rows, sr, length, smooth_s=0.82)
    music_curve_db = curve_from_window_gains(music_gains, full_rows, sr, length, smooth_s=0.82)
    vocal_curve_db = np.clip(vocal_curve_db, -3.2, 6.2)
    music_curve_db = np.clip(music_curve_db, -3.4, 8.4)

    report = {
        "window_s": 1.5,
        "active_range_s": [ACTIVE_START_S, ACTIVE_END_S],
        "forced_low_windows_s": list(FORCED_LOW_WINDOWS),
        "forced_high_windows_s": [(64.5, 69.0)],
        "secondary_low_windows_s": list(SECONDARY_LOW_WINDOWS),
        "full_active_median_rms_db": round(full_target, 2),
        "vocal_active_median_rms_db": round(vocal_target, 2),
        "music_active_median_rms_db": round(music_target, 2),
        "source_active_median_rms_db": round(source_target, 2),
        "max_vocal_phrase_gain_db": round(float(np.max(vocal_gains)), 2),
        "min_vocal_phrase_gain_db": round(float(np.min(vocal_gains)), 2),
        "max_music_phrase_gain_db": round(float(np.max(music_gains)), 2),
        "min_music_phrase_gain_db": round(float(np.min(music_gains)), 2),
        "method": "1.5s bidirectional phrase riding, split into vocal-group and music-group printed gain curves before REAPER.",
        "ride_windows": ride_rows,
        "problem_windows": problem_rows,
    }
    return vocal_curve_db, music_curve_db, report


def apply_group_curve(processed: dict[str, Path], keys: tuple[str, ...], sr: int, length: int, curve_db: np.ndarray) -> None:
    curve = db_to_amp(curve_db).astype(np.float32)
    for key in keys:
        path = processed.get(key)
        if not path or not path.exists():
            continue
        stem_sr, y, _ = base.read_wav(path)
        if stem_sr != sr:
            raise RuntimeError(f"Sample-rate mismatch while applying phrase curve to {key}")
        adjusted = pad_or_trim(y, length) * curve[:, None]
        cap_db = -1.35 if key in MUSIC_KEYS else -2.2
        adjusted = base.peak_cap(adjusted.astype(np.float32), cap_db)
        write_wav(path, sr, adjusted)


def finalize_phrase_pre_render_report(
    paths: dict[str, Path],
    processed: dict[str, Path],
    sr: int,
    length: int,
    phrase_report: dict[str, Any],
) -> None:
    after_full = full_approx_mix(processed, sr, length)
    after_vocal = group_mix(processed, VOCAL_KEYS, sr, length)
    after_music = group_mix(processed, MUSIC_KEYS, sr, length)
    after_full_rows = window_rows(after_full, sr, 1.5)
    after_vocal_rows = window_rows(after_vocal, sr, 1.5)
    after_music_rows = window_rows(after_music, sr, 1.5)
    after_full_target = active_median(after_full_rows)
    after_vocal_target = active_median(after_vocal_rows)
    after_music_target = active_median(after_music_rows)

    after_map = {(row["start_s"], row["end_s"]): row for row in after_full_rows}
    after_vocal_map = {(row["start_s"], row["end_s"]): row for row in after_vocal_rows}
    after_music_map = {(row["start_s"], row["end_s"]): row for row in after_music_rows}
    for item in phrase_report["problem_windows"]:
        key = (item["start_s"], item["end_s"])
        full = after_map.get(key)
        vocal = after_vocal_map.get(key)
        music = after_music_map.get(key)
        if full:
            item["post_phrase_full_rms_db"] = full["rms_db"]
            item["post_phrase_full_delta_vs_active_median_db"] = round(float(full["rms_db"]) - after_full_target, 2)
            item["approx_full_improvement_db"] = round(float(full["rms_db"]) - float(item["full_rms_db"]), 2)
        if vocal:
            item["post_phrase_vocal_rms_db"] = vocal["rms_db"]
            item["post_phrase_vocal_delta_vs_active_median_db"] = round(float(vocal["rms_db"]) - after_vocal_target, 2)
        if music:
            item["post_phrase_music_rms_db"] = music["rms_db"]
            item["post_phrase_music_delta_vs_active_median_db"] = round(float(music["rms_db"]) - after_music_target, 2)
        item["processed_stem_rms_db_after_phrase_ride"] = processed_stem_window_levels(
            processed, float(item["start_s"]), float(item["end_s"]), sr, length
        )

    phrase_report["post_phrase_full_active_median_rms_db"] = round(after_full_target, 2)
    phrase_report["post_phrase_vocal_active_median_rms_db"] = round(after_vocal_target, 2)
    phrase_report["post_phrase_music_active_median_rms_db"] = round(after_music_target, 2)

    base.REPORTS.mkdir(parents=True, exist_ok=True)
    (base.REPORTS / PHRASE_PRE_RENDER_JSON).write_text(
        json.dumps(phrase_report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    vocal_rows = [
        {
            "start_s": row["start_s"],
            "end_s": row["end_s"],
            "classification": row["classification"],
            "window_kind": row["window_kind"],
            "vocal_gain_db": row["vocal_gain_db"],
            "full_rms_db": row["full_rms_db"],
            "vocal_rms_db": row["vocal_rms_db"],
            "reason": row["reason"],
        }
        for row in phrase_report["ride_windows"]
    ]
    music_rows = [
        {
            "start_s": row["start_s"],
            "end_s": row["end_s"],
            "classification": row["classification"],
            "window_kind": row["window_kind"],
            "music_gain_db": row["music_gain_db"],
            "full_rms_db": row["full_rms_db"],
            "music_rms_db": row["music_rms_db"],
            "reason": row["reason"],
        }
        for row in phrase_report["ride_windows"]
    ]
    (base.REPORTS / VOCAL_RIDE_JSON).write_text(json.dumps(vocal_rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (base.REPORTS / MUSIC_RIDE_JSON).write_text(json.dumps(music_rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_csv(base.REPORTS / VOCAL_RIDE_CSV, vocal_rows)
    write_csv(base.REPORTS / MUSIC_RIDE_CSV, music_rows)

    lines = [
        "# Problem Window Cause Classification",
        "",
        f"- Window size: `{phrase_report['window_s']}` s",
        f"- Active range: `{ACTIVE_START_S}-{ACTIVE_END_S}` s",
        f"- Full approximate active median before phrase riding: `{phrase_report['full_active_median_rms_db']}` dBFS",
        f"- Full approximate active median after phrase riding: `{phrase_report['post_phrase_full_active_median_rms_db']}` dBFS",
        "",
        "| start | end | kind | cause | full before | full after | vocal gain | music gain | reason |",
        "| ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | --- |",
    ]
    for item in phrase_report["problem_windows"]:
        lines.append(
            f"| {item['start_s']} | {item['end_s']} | {item['window_kind']} | {item['classification']} | "
            f"{item['full_rms_db']} | {item.get('post_phrase_full_rms_db')} | {item['vocal_gain_db']} | "
            f"{item['music_gain_db']} | {item['reason']} |"
        )
    (base.REPORTS / PROBLEM_CLASSIFICATION_JSON).write_text(
        json.dumps(phrase_report["problem_windows"], ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (base.REPORTS / PROBLEM_CLASSIFICATION_MD).write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_processed(paths: dict[str, Path]) -> tuple[dict[str, Path], int, float, dict[str, float]]:
    processed, sr, duration, vocal_balance = v2.write_processed(paths)
    length = int(round(duration * sr))
    vocal_lock_report = apply_lead_vocal_level_lock(processed, sr, length)
    dyn_eq_report = apply_suno_reference_dynamic_eq(paths, processed, sr, length)
    vocal_curve_db, music_curve_db, phrase_report = classify_and_build_phrase_curves(paths, processed, sr, length)
    apply_group_curve(processed, VOCAL_KEYS, sr, length, vocal_curve_db)
    apply_group_curve(processed, MUSIC_KEYS, sr, length, music_curve_db)
    finalize_phrase_pre_render_report(paths, processed, sr, length, phrase_report)
    vocal_balance["lead_vocal_level_lock_target_db"] = vocal_lock_report["pre_lock_summary"]["target_active_vocal_rms_db"]
    vocal_balance["lead_vocal_level_lock_pre_spread_db"] = vocal_lock_report["pre_lock_summary"]["active_p10_p90_spread_db"]
    vocal_balance["lead_vocal_level_lock_post_spread_db"] = vocal_lock_report["post_lock_summary"]["active_p10_p90_spread_db"]
    vocal_balance["lead_vocal_level_lock_max_gain_db"] = vocal_lock_report["max_applied_lead_vocal_gain_db"]
    vocal_balance["lead_vocal_level_lock_min_gain_db"] = vocal_lock_report["min_applied_lead_vocal_gain_db"]
    vocal_balance["suno_reference_music_before_spread_db"] = dyn_eq_report["music_before_summary"]["active_p10_p90_spread_db"]
    vocal_balance["suno_reference_music_after_spread_db"] = dyn_eq_report["music_after_summary"]["active_p10_p90_spread_db"]
    vocal_balance["dynamic_eq_presence_max_cut_db"] = dyn_eq_report["max_presence_dyn_eq_cut_db"]
    vocal_balance["dynamic_eq_glare_max_cut_db"] = dyn_eq_report["max_glare_dyn_eq_cut_db"]
    vocal_balance["dynamic_eq_lowmid_max_cut_db"] = dyn_eq_report["max_lowmid_dyn_eq_cut_db"]
    vocal_balance["vocal_music_presence_median_improvement_db"] = dyn_eq_report["presence_mask_summary"].get(
        "median_presence_ratio_improvement_db",
        0.0,
    )
    vocal_balance["phrase_vocal_max_gain_db"] = phrase_report["max_vocal_phrase_gain_db"]
    vocal_balance["phrase_vocal_min_gain_db"] = phrase_report["min_vocal_phrase_gain_db"]
    vocal_balance["phrase_music_max_gain_db"] = phrase_report["max_music_phrase_gain_db"]
    vocal_balance["phrase_music_min_gain_db"] = phrase_report["min_music_phrase_gain_db"]
    vocal_balance["phrase_window_s"] = phrase_report["window_s"]
    return processed, sr, duration, vocal_balance


def phrase_premaster_bus_leveling(input_path: Path, output_path: Path) -> dict[str, Any]:
    sr, y, _ = base.read_wav(input_path)
    rows = window_rows(y, sr, 1.5)
    target = active_median(rows)
    gains = np.zeros(len(rows), dtype=np.float32)
    out_rows: list[dict[str, Any]] = []
    for i, row in enumerate(rows):
        start_s = float(row["start_s"])
        end_s = float(row["end_s"])
        rms_db = float(row["rms_db"])
        kind = forced_window_kind(start_s, end_s)
        drop = target - rms_db
        excess = rms_db - target
        gain = 0.0
        reason = ""
        if ACTIVE_START_S <= start_s < ACTIVE_END_S:
            if kind in {"forced_low", "secondary_low"} or drop > 1.85:
                gain = min(max(drop - 0.08, 1.1 if kind == "forced_low" else 0.0) * (1.08 if kind == "forced_low" else 0.92), 7.2)
                reason = "short-window premaster lift after stem/vocal riding"
            elif kind == "forced_high" or excess > 1.85:
                gain = -min(max(excess - 0.08, 0.9 if kind == "forced_high" else 0.0) * (1.02 if kind == "forced_high" else 0.82), 3.5)
                reason = "short-window premaster cut to prevent hook from masking following phrases"
        if abs(gain) < 0.25:
            gain = 0.0
        gains[i] = float(np.clip(gain, -3.5, 7.2))
        out_rows.append(
            {
                **row,
                "window_kind": kind or "",
                "delta_vs_premaster_active_median_db": round(rms_db - target, 2),
                "applied_premaster_phrase_gain_db": round(float(gains[i]), 2),
                "reason": reason,
            }
        )

    curve_db = curve_from_window_gains(gains, rows, sr, len(y), smooth_s=0.58)
    curve_db = np.clip(curve_db, -3.5, 7.2)
    leveled = y * db_to_amp(curve_db)[:, None]
    leveled = base.soft_clip(leveled.astype(np.float32), ceiling=0.963)
    leveled = base.peak_cap(leveled, -1.25)
    write_wav(output_path, sr, leveled)

    after_rows = window_rows(leveled, sr, 1.5)
    after_target = active_median(after_rows)
    for i, row in enumerate(out_rows):
        if i < len(after_rows):
            row["post_premaster_phrase_rms_db"] = after_rows[i]["rms_db"]
            row["post_premaster_phrase_delta_vs_active_median_db"] = round(float(after_rows[i]["rms_db"]) - after_target, 2)
            row["premaster_phrase_improvement_db"] = round(float(after_rows[i]["rms_db"]) - float(row["rms_db"]), 2)

    report = {
        "input": base.rel(input_path),
        "output": base.rel(output_path),
        "window_s": 1.5,
        "active_range_s": [ACTIVE_START_S, ACTIVE_END_S],
        "premaster_active_median_rms_db": round(target, 2),
        "post_premaster_active_median_rms_db": round(after_target, 2),
        "max_applied_premaster_phrase_gain_db": round(float(np.max(gains)), 2),
        "min_applied_premaster_phrase_gain_db": round(float(np.min(gains)), 2),
        "mean_abs_applied_premaster_phrase_gain_db": round(float(np.mean(np.abs(gains[np.abs(gains) > 0]))) if np.any(np.abs(gains) > 0) else 0.0, 2),
        "method": "1.5s bidirectional premaster bus gain automation after REAPER print, before final loudness and limiter safety.",
        "windows": out_rows,
    }
    (base.REPORTS / PHRASE_PREMASTER_JSON).write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return report


def post_final_level_lock(path: Path) -> dict[str, Any]:
    sr, y, _ = base.read_wav(path)
    rows = window_rows(y, sr, 1.5)
    target = active_median(rows)
    gains = np.zeros(len(rows), dtype=np.float32)
    out_rows: list[dict[str, Any]] = []
    for i, row in enumerate(rows):
        start_s = float(row["start_s"])
        end_s = float(row["end_s"])
        rms_db = float(row["rms_db"])
        kind = forced_window_kind(start_s, end_s)
        drop = target - rms_db
        excess = rms_db - target
        gain = 0.0
        reason = ""
        if ACTIVE_START_S <= start_s < ACTIVE_END_S:
            if kind == "forced_low":
                gain = min(max(drop - 1.15, 1.25), 4.2)
                reason = "post-final forced-low level lock"
            elif kind == "secondary_low":
                gain = min(max(drop - 1.45, 0.0), 3.0)
                reason = "post-final secondary-low level lock"
            elif drop > 2.15:
                gain = min(drop - 1.55, 3.2)
                reason = "post-final general low-window level lock"
            elif kind == "forced_high":
                gain = -min(max(excess - 1.25, 0.55), 2.2)
                reason = "post-final forced-high level lock"
            elif excess > 2.05:
                gain = -min(excess - 1.55, 2.0)
                reason = "post-final general high-window level lock"
        if abs(gain) < 0.18:
            gain = 0.0
            reason = ""
        gains[i] = float(np.clip(gain, -2.3, 4.2))
        out_rows.append(
            {
                **row,
                "window_kind": kind or "",
                "delta_vs_pre_lock_active_median_db": round(rms_db - target, 2),
                "applied_post_final_lock_gain_db": round(float(gains[i]), 2),
                "reason": reason,
            }
        )

    curve_db = curve_from_window_gains(gains, rows, sr, len(y), smooth_s=0.46)
    curve_db = np.clip(curve_db, -2.3, 4.2)
    locked = y * db_to_amp(curve_db)[:, None]
    locked = base.soft_clip(locked.astype(np.float32), ceiling=0.955)
    locked = base.peak_cap(locked, -1.18)
    write_wav(final_locked_path(), sr, locked)
    write_wav(path, sr, locked)

    after_rows = window_rows(locked, sr, 1.5)
    after_target = active_median(after_rows)
    after_summary = summarize_window_rows(after_rows)
    before_summary = summarize_window_rows(rows)
    for i, row in enumerate(out_rows):
        if i < len(after_rows):
            row["post_lock_rms_db"] = after_rows[i]["rms_db"]
            row["post_lock_delta_vs_active_median_db"] = round(float(after_rows[i]["rms_db"]) - after_target, 2)
            row["post_lock_change_db"] = round(float(after_rows[i]["rms_db"]) - float(row["rms_db"]), 2)

    report = {
        "input_output_final_wav": base.rel(path),
        "locked_copy": base.rel(final_locked_path()),
        "window_s": 1.5,
        "active_range_s": [ACTIVE_START_S, ACTIVE_END_S],
        "pre_lock_active_median_rms_db": round(target, 2),
        "post_lock_active_median_rms_db": round(after_target, 2),
        "max_applied_post_final_lock_gain_db": round(float(np.max(gains)), 2),
        "min_applied_post_final_lock_gain_db": round(float(np.min(gains)), 2),
        "pre_lock_summary": before_summary,
        "post_lock_summary": after_summary,
        "method": "Final WAV 1.5s level-lock after loudnorm, before MP3 export, prioritizing constant musical level while keeping the Suno source as reference.",
        "windows": out_rows,
    }
    (base.REPORTS / FINAL_LOCK_REPORT_JSON).write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return report


def final_master() -> None:
    bus_report = phrase_premaster_bus_leveling(base.REAPER_PRINT, premaster_path())
    filter_graph = (
        "highpass=f=24,"
        "equalizer=f=245:t=q:w=1:g=-0.12,"
        "equalizer=f=730:t=q:w=1.2:g=-0.05,"
        "equalizer=f=3200:t=q:w=0.9:g=0.04,"
        "equalizer=f=10900:t=q:w=0.8:g=-0.22,"
        "loudnorm=I=-10.95:TP=-1.45:LRA=2.5:linear=false,"
        "alimiter=limit=0.80:attack=2:release=105:level=false"
    )
    subprocess.run(
        [
            base.FFMPEG,
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(premaster_path()),
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
    lock_report = post_final_level_lock(base.FINAL_WAV)
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
    _ = bus_report
    _ = lock_report


def summarize_window_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    levels = active_levels(rows)
    median = float(np.median(levels))
    p10 = float(np.percentile(levels, 10.0))
    p90 = float(np.percentile(levels, 90.0))
    active_rows = [row for row in rows if ACTIVE_START_S <= float(row["start_s"]) < ACTIVE_END_S]
    lows = [row for row in active_rows if median - float(row["rms_db"]) > 3.0]
    highs = [row for row in active_rows if float(row["rms_db"]) - median > 3.0]
    return {
        "active_median_rms_db": round(median, 2),
        "active_p10_rms_db": round(p10, 2),
        "active_p90_rms_db": round(p90, 2),
        "active_p10_p90_spread_db": round(p90 - p10, 2),
        "low_windows_gt_3db_count": len(lows),
        "high_windows_gt_3db_count": len(highs),
        "worst_low_windows": sorted(
            [
                {
                    "start_s": row["start_s"],
                    "end_s": row["end_s"],
                    "rms_db": row["rms_db"],
                    "drop_db": round(median - float(row["rms_db"]), 2),
                }
                for row in lows
            ],
            key=lambda item: item["drop_db"],
            reverse=True,
        )[:10],
        "worst_high_windows": sorted(
            [
                {
                    "start_s": row["start_s"],
                    "end_s": row["end_s"],
                    "rms_db": row["rms_db"],
                    "excess_db": round(float(row["rms_db"]) - median, 2),
                }
                for row in highs
            ],
            key=lambda item: item["excess_db"],
            reverse=True,
        )[:10],
    }


def rows_by_start(rows: list[dict[str, Any]]) -> dict[float, dict[str, Any]]:
    return {round(float(row["start_s"]), 3): row for row in rows}


def write_phrase_level_reports(paths: dict[str, Path]) -> dict[str, Any]:
    source_sr, source, _ = base.read_wav(paths["full_reference"])
    final_sr, final, _ = base.read_wav(base.FINAL_WAV)
    print_sr, reaper_print, _ = base.read_wav(base.REAPER_PRINT)
    premaster_sr, premaster, _ = base.read_wav(premaster_path())
    if not (source_sr == final_sr == print_sr == premaster_sr):
        raise RuntimeError("Phrase report sample-rate mismatch")
    length = len(final)
    source = pad_or_trim(source, length)
    reaper_print = pad_or_trim(reaper_print, length)
    premaster = pad_or_trim(premaster, length)

    labels: dict[str, np.ndarray] = {
        "source_full_reference": source,
        "v09_reaper_print": reaper_print,
        "v09_phrase_premaster": premaster,
        "v09_final": final,
    }
    v07_final_path = ROOT / "renders/mwolla_v07_vocal_hard_locked_master/mwolla_v07_VOCAL_HARD_LOCKED_MASTER.wav"
    v03_final_path = ROOT / "renders/mwolla_v03_premaster_consistent_master/mwolla_v03_PREMASTER_CONSISTENT_MASTER.wav"
    v03_premaster_path = ROOT / "renders/mwolla_v03_premaster_consistent_master/mwolla_v03_SECTION_LEVELED_PREMASTER_24-48.wav"
    if v07_final_path.exists():
        sr, y, _ = base.read_wav(v07_final_path)
        if sr == final_sr:
            labels["v07_final"] = pad_or_trim(y, length)
    if v03_final_path.exists():
        sr, y, _ = base.read_wav(v03_final_path)
        if sr == final_sr:
            labels["v03_final"] = pad_or_trim(y, length)
    if v03_premaster_path.exists():
        sr, y, _ = base.read_wav(v03_premaster_path)
        if sr == final_sr:
            labels["v03_section_leveled_premaster"] = pad_or_trim(y, length)

    payload: dict[str, Any] = {
        "active_range_s": [ACTIVE_START_S, ACTIVE_END_S],
        "window_summaries": {},
        "forced_window_comparison": [],
    }
    flat_rows: list[dict[str, Any]] = []
    computed: dict[tuple[str, float], list[dict[str, Any]]] = {}
    for window_s in (1.5, 3.0, 6.0):
        window_key = f"{window_s:g}s"
        payload["window_summaries"][window_key] = {}
        for label, audio in labels.items():
            rows = window_rows(audio, final_sr, window_s)
            computed[(label, window_s)] = rows
            summary = summarize_window_rows(rows)
            payload["window_summaries"][window_key][label] = summary
            med = summary["active_median_rms_db"]
            for row in rows:
                if ACTIVE_START_S <= float(row["start_s"]) < ACTIVE_END_S:
                    flat_rows.append(
                        {
                            "window_s": window_s,
                            "label": label,
                            "start_s": row["start_s"],
                            "end_s": row["end_s"],
                            "rms_db": row["rms_db"],
                            "peak_db": row["peak_db"],
                            "delta_vs_active_median_db": round(float(row["rms_db"]) - float(med), 2),
                            "window_kind": forced_window_kind(float(row["start_s"]), float(row["end_s"])) or "",
                        }
                    )

    v07_rows = rows_by_start(computed.get(("v07_final", 1.5), []))
    v09_rows = rows_by_start(computed.get(("v09_final", 1.5), []))
    source_rows = rows_by_start(computed.get(("source_full_reference", 1.5), []))
    premaster_report = json.loads((base.REPORTS / PHRASE_PREMASTER_JSON).read_text(encoding="utf-8"))
    premaster_by_start = rows_by_start(premaster_report.get("windows", []))
    for start_s, end_s in (*FORCED_LOW_WINDOWS, *SECONDARY_LOW_WINDOWS, *FORCED_HIGH_WINDOWS):
        v07_row = v07_rows.get(start_s)
        v09_row = v09_rows.get(start_s)
        source_row = source_rows.get(start_s)
        pre_row = premaster_by_start.get(start_s)
        payload["forced_window_comparison"].append(
            {
                "start_s": start_s,
                "end_s": end_s,
                "kind": forced_window_kind(start_s, end_s),
                "source_rms_db": source_row.get("rms_db") if source_row else None,
                "v07_final_rms_db": v07_row.get("rms_db") if v07_row else None,
                "v09_final_rms_db": v09_row.get("rms_db") if v09_row else None,
                "v09_minus_v07_rms_db": round(float(v09_row["rms_db"]) - float(v07_row["rms_db"]), 2) if v07_row and v09_row else None,
                "premaster_phrase_gain_db": pre_row.get("applied_premaster_phrase_gain_db") if pre_row else None,
                "premaster_reason": pre_row.get("reason") if pre_row else "",
            }
        )

    (base.REPORTS / PHRASE_REPORT_JSON).write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_csv(base.REPORTS / PHRASE_REPORT_CSV, flat_rows)

    v07_summary = payload["window_summaries"]["1.5s"].get("v07_final", {})
    v09_summary = payload["window_summaries"]["1.5s"].get("v09_final", {})
    three_summary = payload["window_summaries"]["3s"].get("v09_final", {})
    lines = [
        "# Mwolla v09 Suno Reference Dynamic EQ Consistency Report",
        "",
        f"- Active range: `{ACTIVE_START_S}-{ACTIVE_END_S}` s",
        "- Main measurement focus: `1.5s` non-overlapping RMS windows.",
        f"- v07 1.5s p10-p90 spread: `{v07_summary.get('active_p10_p90_spread_db')}` dB",
        f"- v09 1.5s p10-p90 spread: `{v09_summary.get('active_p10_p90_spread_db')}` dB",
        f"- v09 1.5s low windows >3 dB: `{v09_summary.get('low_windows_gt_3db_count')}`",
        f"- v09 1.5s high windows >3 dB: `{v09_summary.get('high_windows_gt_3db_count')}`",
        f"- v09 3s low windows >3 dB: `{three_summary.get('low_windows_gt_3db_count')}`",
        f"- v09 3s high windows >3 dB: `{three_summary.get('high_windows_gt_3db_count')}`",
        "",
        "| start | end | kind | source | v07 final | v09 final | v09-v07 | premaster gain |",
        "| ---: | ---: | --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for item in payload["forced_window_comparison"]:
        lines.append(
            f"| {item['start_s']} | {item['end_s']} | {item['kind']} | {item['source_rms_db']} | "
            f"{item['v07_final_rms_db']} | {item['v09_final_rms_db']} | {item['v09_minus_v07_rms_db']} | "
            f"{item['premaster_phrase_gain_db']} |"
        )
    (base.REPORTS / PHRASE_REPORT_MD).write_text("\n".join(lines) + "\n", encoding="utf-8")
    return payload


def write_reports(paths: dict[str, Path], processed: dict[str, Path], vocal_balance: dict[str, float], gate: dict[str, Any]) -> None:
    v2.write_reports(paths, processed, vocal_balance, gate)
    section_md_path = base.REPORTS / v2.SECTION_REPORT_MD
    if section_md_path.exists():
        section_text = section_md_path.read_text(encoding="utf-8")
        section_text = section_text.replace("Mwolla v02 Section", "Mwolla v09 Section")
        section_text = section_text.replace("v02 final", "v09 final")
        section_text = section_text.replace("v02 vs v01", "v09 vs v01")
        section_text = section_text.replace("v02-v01", "v09-v01")
        section_text = section_text.replace("v02 final active", "v09 final active")
        section_md_path.write_text(section_text, encoding="utf-8")
    phrase_payload = write_phrase_level_reports(paths)
    report_path = base.REPORTS / base.REPORT_FILENAME
    pre_render = json.loads((base.REPORTS / PHRASE_PRE_RENDER_JSON).read_text(encoding="utf-8"))
    premaster = json.loads((base.REPORTS / PHRASE_PREMASTER_JSON).read_text(encoding="utf-8"))
    dyn_eq = json.loads((base.REPORTS / SUNO_REFERENCE_DYN_EQ_JSON).read_text(encoding="utf-8"))
    one_five = phrase_payload["window_summaries"]["1.5s"]["v09_final"]
    three = phrase_payload["window_summaries"]["3s"]["v09_final"]
    lock_report = json.loads((base.REPORTS / FINAL_LOCK_REPORT_JSON).read_text(encoding="utf-8"))
    vocal_lock = json.loads((base.REPORTS / VOCAL_LEVEL_LOCK_JSON).read_text(encoding="utf-8"))
    lines = report_path.read_text(encoding="utf-8").rstrip().splitlines()
    lines.extend(
        [
            "",
            "## Suno Reference Dynamic EQ v09",
            "",
            f"- Lead vocal active level-lock report: `{base.rel(base.REPORTS / VOCAL_LEVEL_LOCK_MD)}`",
            f"- Lead vocal active p10-p90 spread: `{vocal_lock['pre_lock_summary']['active_p10_p90_spread_db']}` -> `{vocal_lock['post_lock_summary']['active_p10_p90_spread_db']}` dB",
            f"- Lead vocal active >3 dB low/high windows after lock: `{vocal_lock['post_lock_summary']['low_windows_gt_3db_count']}` / `{vocal_lock['post_lock_summary']['high_windows_gt_3db_count']}`",
            f"- Suno reference dynamic EQ report: `{base.rel(base.REPORTS / SUNO_REFERENCE_DYN_EQ_MD)}`",
            f"- Music p10-p90 spread before/after dynamic EQ: `{dyn_eq['music_before_summary']['active_p10_p90_spread_db']}` -> `{dyn_eq['music_after_summary']['active_p10_p90_spread_db']}` dB",
            f"- Music dynamic EQ max cuts: presence `{dyn_eq['max_presence_dyn_eq_cut_db']}` dB, glare `{dyn_eq['max_glare_dyn_eq_cut_db']}` dB, low-mid `{dyn_eq['max_lowmid_dyn_eq_cut_db']}` dB",
            f"- Vocal/music presence median improvement: `{dyn_eq['presence_mask_summary'].get('median_presence_ratio_improvement_db')}` dB",
            f"- Stem/vocal phrase riding report: `{base.rel(base.REPORTS / PHRASE_PRE_RENDER_JSON)}`",
            f"- Problem-window classification: `{base.rel(base.REPORTS / PROBLEM_CLASSIFICATION_MD)}`",
            f"- Vocal riding curve: `{base.rel(base.REPORTS / VOCAL_RIDE_CSV)}`",
            f"- Music/stem riding curve: `{base.rel(base.REPORTS / MUSIC_RIDE_CSV)}`",
            f"- Phrase premaster: `{base.rel(premaster_path())}`",
            f"- Premaster phrase gain range: `{premaster['min_applied_premaster_phrase_gain_db']}` to `{premaster['max_applied_premaster_phrase_gain_db']}` dB",
            f"- Post-final level-lock gain range: `{lock_report['min_applied_post_final_lock_gain_db']}` to `{lock_report['max_applied_post_final_lock_gain_db']}` dB",
            f"- Pre-render vocal phrase gain range: `{pre_render['min_vocal_phrase_gain_db']}` to `{pre_render['max_vocal_phrase_gain_db']}` dB",
            f"- Pre-render music phrase gain range: `{pre_render['min_music_phrase_gain_db']}` to `{pre_render['max_music_phrase_gain_db']}` dB",
            f"- v09 final 1.5s p10-p90 spread: `{one_five['active_p10_p90_spread_db']}` dB",
            f"- v09 final 3s >3 dB low/high windows: `{three['low_windows_gt_3db_count']}` / `{three['high_windows_gt_3db_count']}`",
            f"- Phrase consistency report: `{base.rel(base.REPORTS / PHRASE_REPORT_MD)}`",
        ]
    )
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_zip() -> None:
    v3.build_zip()
    extras = [
        premaster_path(),
        base.REPORTS / VOCAL_LEVEL_LOCK_JSON,
        base.REPORTS / VOCAL_LEVEL_LOCK_CSV,
        base.REPORTS / VOCAL_LEVEL_LOCK_MD,
        base.REPORTS / PHRASE_PRE_RENDER_JSON,
        base.REPORTS / PROBLEM_CLASSIFICATION_JSON,
        base.REPORTS / PROBLEM_CLASSIFICATION_MD,
        base.REPORTS / VOCAL_RIDE_JSON,
        base.REPORTS / VOCAL_RIDE_CSV,
        base.REPORTS / MUSIC_RIDE_JSON,
        base.REPORTS / MUSIC_RIDE_CSV,
        base.REPORTS / PHRASE_PREMASTER_JSON,
        base.REPORTS / SUNO_REFERENCE_DYN_EQ_JSON,
        base.REPORTS / SUNO_REFERENCE_DYN_EQ_CSV,
        base.REPORTS / SUNO_REFERENCE_DYN_EQ_MD,
        base.REPORTS / FINAL_LOCK_REPORT_JSON,
        final_locked_path(),
        base.REPORTS / PHRASE_REPORT_JSON,
        base.REPORTS / PHRASE_REPORT_CSV,
        base.REPORTS / PHRASE_REPORT_MD,
        base.REPORTS / "vocal_gap_cleanup_decisions.json",
        base.REPORTS / "female_mask_layer_decisions.json",
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
    base.process_lead_vocal = v2.v1.process_lead_vocal
    base.process_female_layer = v2.v1.process_female_mask_layer
    base.process_backing_vocals = v2.v1.process_backing_vocals
    base.process_instrument = v2.v1.process_instrument
    base.write_processed = write_processed
    base.final_master = final_master
    base.write_reports = write_reports
    base.build_zip = build_zip
    return base.main()


if __name__ == "__main__":
    raise SystemExit(main())

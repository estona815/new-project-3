#!/usr/bin/env python3
from __future__ import annotations

import csv
import importlib.util
import json
import shutil
import subprocess
import zipfile
from pathlib import Path
from typing import Any

import numpy as np


ROOT = Path("/Users/hantaeheuk/Documents/New project 3")
BASE_SCRIPT = ROOT / "tools" / "sonyeo_luka_v01_clear_master.py"
REF_DIR = Path("/Users/hantaeheuk/Downloads/마루노우치")
SLUG = "marunouchi_v01_stem_mix_master"

spec = importlib.util.spec_from_file_location("sonyeo_luka_v01_clear_master", BASE_SCRIPT)
if spec is None or spec.loader is None:
    raise RuntimeError(f"Could not load base audio helpers: {BASE_SCRIPT}")
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)

WORK = ROOT / "audio_work" / SLUG
PROCESSED = WORK / "processed_stems"
RENDERS = ROOT / "renders" / SLUG
REPORTS = ROOT / "reports" / SLUG
base.REPORTS = REPORTS

PREMASTER_WAV = RENDERS / "marunouchi_v01_STEM_MIX_PREMASTER_24-48.wav"
FLOOR_WAV = RENDERS / "marunouchi_v01_STEM_MIX_FLOOR_PREMASTER_24-48.wav"
FINAL_WAV = RENDERS / "marunouchi_v01_STEM_MIX_MASTER.wav"
FINAL_MP3 = RENDERS / "marunouchi_v01_STEM_MIX_MASTER_320k.mp3"
VOCAL_SOLO = RENDERS / "marunouchi_v01_VOCAL_SOLO.wav"
AB_MP3 = RENDERS / "marunouchi_v01_AB_original_fullmix_to_stem_master_320k.mp3"
ZIP_PATH = RENDERS / "marunouchi_v01_STEM_MIX_MASTER_DELIVERABLE.zip"
WINDOW_REPORT_JSON = "section_loudness_consistency_1p5s_3s_6s_report.json"
WINDOW_REPORT_CSV = "section_loudness_consistency_1p5s_3s_6s_report.csv"
VOCAL_RECON_JSON = "vocal_stem_reconstruction_clip_gain_qc_report.json"
VOCAL_RECON_CSV = "vocal_stem_reconstruction_clip_gain_qc_report.csv"
MUSIC_DYN_EQ_JSON = "music_bus_sidechain_dynamic_eq_report.json"
MUSIC_DYN_EQ_CSV = "music_bus_sidechain_dynamic_eq_report.csv"
MUSIC_SIZE_JSON = "music_size_lock_to_original_stems_report.json"

DYNAMIC_EQ_BANDS = [
    ("mud_low_mid_collision", 250, 650),
    ("vocal_presence_collision", 1500, 5200),
    ("synth_ai_glare_consonants", 4000, 8500),
]

STEMS = {
    "full_reference": REF_DIR / "0 마루노우치.wav",
    "fx": REF_DIR / "1 FX.wav",
    "synth": REF_DIR / "2 Synth.wav",
    "keyboard": REF_DIR / "3 Keyboard.wav",
    "guitar_main": REF_DIR / "4 Guitar.wav",
    "bass": REF_DIR / "5 Bass.wav",
    "drums": REF_DIR / "6 Drums.wav",
    "backing_vocals": REF_DIR / "7 Backing_Vocals.wav",
    "vocal_center": REF_DIR / "8 Vocals.wav",
    "vocal_wide": REF_DIR / "9 Vocals.wav",
    "guitar_support": REF_DIR / "10 Guitar.wav",
}

MUSIC_KEYS = {"fx", "synth", "keyboard", "guitar_main", "guitar_support", "bass", "drums"}
VOCAL_KEYS = {"vocal_center", "vocal_wide", "backing_vocals"}

BASE_GAINS_DB = {
    "fx": -1.4,
    "synth": -0.9,
    "keyboard": -0.35,
    "guitar_main": -0.25,
    "guitar_support": -0.75,
    "bass": -0.1,
    "drums": -0.35,
    "backing_vocals": 1.1,
    "vocal_center": 1.0,
    "vocal_wide": -0.15,
}


def db_to_amp(db: float | np.ndarray) -> np.ndarray:
    return np.power(10.0, np.asarray(db) / 20.0)


def amp_to_db(value: float | np.ndarray) -> np.ndarray:
    return 20.0 * np.log10(np.maximum(np.asarray(value), 1e-12))


def ensure_dirs() -> None:
    for path in (WORK, PROCESSED, RENDERS, REPORTS):
        path.mkdir(parents=True, exist_ok=True)


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def pad_or_trim(y: np.ndarray, length: int) -> np.ndarray:
    if len(y) == length:
        return y.astype(np.float32, copy=False)
    if len(y) > length:
        return y[:length].astype(np.float32)
    out = np.zeros((length, y.shape[1]), dtype=np.float32)
    out[: len(y)] = y
    return out


def read_all() -> tuple[int, int, dict[str, np.ndarray]]:
    loaded: dict[str, np.ndarray] = {}
    sr0: int | None = None
    length: int | None = None
    for key, path in STEMS.items():
        if not path.exists():
            raise FileNotFoundError(path)
        sr, y, _ = base.read_wav(path)
        if sr0 is None:
            sr0 = sr
            length = len(y)
        if sr != sr0:
            raise RuntimeError(f"Sample-rate mismatch: {path}")
        loaded[key] = pad_or_trim(y, length or len(y))
    return int(sr0 or 48000), int(length or 0), loaded


def side_mid_db(y: np.ndarray) -> tuple[float, float]:
    left = y[:, 0]
    right = y[:, 1]
    mid = (left + right) * 0.5
    side = (left - right) * 0.5
    corr = float(np.corrcoef(left, right)[0, 1]) if np.std(left) > 1e-8 and np.std(right) > 1e-8 else 1.0
    return float(amp_to_db(base.rms(side) / (base.rms(mid) + 1e-12))), corr


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


def process_center_vocal(y: np.ndarray, sr: int) -> np.ndarray:
    x = base.mono_center(y)
    x = base.butter_filter(x, sr, "highpass", 82, order=2)
    x = base.dynamic_band_tame(x, sr, 190, 380, max_cut_db=1.0, percentile=64.0, slope=0.45, smooth_ms=24.0)
    x = base.rbj_peaking(x, sr, 2700, 0.55, 0.9)
    x = base.rbj_peaking(x, sr, 3900, 0.35, 0.95)
    x = base.dynamic_band_tame(x, sr, 6100, 9000, max_cut_db=1.5, percentile=63.0, slope=0.58, smooth_ms=7.0)
    x = base.compressor(x, sr, threshold_db=-22.0, ratio=1.45, attack_ms=10.0, release_ms=110.0, makeup_db=0.5)
    x = base.match_active_rms(x, -18.8, max_gain_db=4.0)
    return base.peak_cap(x.astype(np.float32), -2.2)


def process_wide_vocal(y: np.ndarray, sr: int, center: np.ndarray) -> np.ndarray:
    x = base.butter_filter(y, sr, "highpass", 88, order=2)
    x = base.dynamic_band_tame(x, sr, 200, 420, max_cut_db=0.8, percentile=66.0, slope=0.42, smooth_ms=24.0)
    x = base.rbj_peaking(x, sr, 3150, 0.25, 0.95)
    x = base.dynamic_band_tame(x, sr, 5900, 9300, max_cut_db=1.9, percentile=60.0, slope=0.62, smooth_ms=7.0)
    x = base.compressor(x, sr, threshold_db=-21.8, ratio=1.35, attack_ms=12.0, release_ms=120.0, makeup_db=0.35)
    x = base.match_active_rms(x, base.active_rms_db(center) + 1.4, max_gain_db=3.5)
    return base.peak_cap(x.astype(np.float32), -2.0)


def process_backing(y: np.ndarray, sr: int, vocal_group: np.ndarray) -> np.ndarray:
    x = base.butter_filter(y, sr, "highpass", 145, order=2)
    x = base.dynamic_band_tame(x, sr, 5800, 9500, max_cut_db=1.4, percentile=58.0, slope=0.6, smooth_ms=8.0)
    x = base.match_active_rms(x, base.active_rms_db(vocal_group) - 14.0, max_gain_db=10.0)
    return base.peak_cap(x.astype(np.float32), -6.0)


def frame_levels(y: np.ndarray, sr: int, window_s: float = 0.75) -> list[dict[str, Any]]:
    mono = np.mean(y, axis=1).astype(np.float32)
    frame = int(round(sr * window_s))
    rows: list[dict[str, Any]] = []
    for start in range(0, len(mono), frame):
        end = min(len(mono), start + frame)
        if end - start < int(sr * 0.25):
            break
        chunk = mono[start:end]
        rows.append(
            {
                "start_s": round(start / sr, 3),
                "end_s": round(end / sr, 3),
                "rms_db": round(float(amp_to_db(np.sqrt(np.mean(chunk * chunk) + 1e-12))), 2),
            }
        )
    return rows


def smooth_curve_from_rows(rows: list[dict[str, Any]], gains: np.ndarray, length: int, sr: int, smooth_s: float, min_db: float, max_db: float) -> np.ndarray:
    centers = np.array([(float(row["start_s"]) + float(row["end_s"])) * 0.5 for row in rows], dtype=np.float32)
    times = np.arange(length, dtype=np.float32) / float(sr)
    curve = np.interp(times, centers, gains, left=gains[0], right=gains[-1]).astype(np.float32) if len(centers) > 1 else np.zeros(length, dtype=np.float32)
    smooth = max(1, int(sr * smooth_s))
    if smooth > 1:
        kernel = np.hanning(smooth * 2 + 1).astype(np.float32)
        kernel /= np.sum(kernel)
        curve = base.signal.fftconvolve(curve, kernel, mode="same").astype(np.float32)
    return np.clip(curve, min_db, max_db).astype(np.float32)


def vocal_spread_summary(rows: list[dict[str, Any]], level_key: str, active_key: str = "active_vocal") -> dict[str, Any]:
    active = [row for row in rows if row.get(active_key) and level_key in row]
    levels = np.array([float(row[level_key]) for row in active], dtype=np.float32)
    if not len(levels):
        return {"count": 0}
    p10 = float(np.percentile(levels, 10))
    p90 = float(np.percentile(levels, 90))
    median = float(np.median(levels))
    deviations = levels - median
    return {
        "count": len(levels),
        "p10_rms_db": round(p10, 2),
        "p90_rms_db": round(p90, 2),
        "p10_p90_spread_db": round(p90 - p10, 2),
        "median_rms_db": round(median, 2),
        "outside_plus_minus_3db_count": int(np.sum(np.abs(deviations) > 3.0)),
        "max_positive_deviation_db": round(float(np.max(deviations)), 2),
        "max_negative_deviation_db": round(float(np.min(deviations)), 2),
        "mean_abs_deviation_db": round(float(np.mean(np.abs(deviations))), 2),
    }


def post_reconstruction_vocal_chain(y: np.ndarray, sr: int, target_db: float, peak_db: float) -> np.ndarray:
    x = base.dynamic_band_tame(y, sr, 250, 650, max_cut_db=0.55, percentile=68.0, slope=0.40, smooth_ms=24.0)
    x = base.dynamic_band_tame(x, sr, 1500, 5200, max_cut_db=0.65, percentile=76.0, slope=0.34, smooth_ms=16.0)
    x = base.dynamic_band_tame(x, sr, 5200, 8500, max_cut_db=1.15, percentile=62.0, slope=0.55, smooth_ms=7.0)
    x = base.compressor(x, sr, threshold_db=-22.8, ratio=1.65, attack_ms=5.0, release_ms=70.0, makeup_db=0.35)
    x = base.compressor(x, sr, threshold_db=-25.5, ratio=1.28, attack_ms=28.0, release_ms=240.0, makeup_db=0.2)
    x = base.match_active_rms(x, target_db, max_gain_db=3.5)
    return base.peak_cap(x.astype(np.float32), peak_db)


def reconstruct_vocal_stems(processed: dict[str, np.ndarray], sr: int) -> dict[str, Any]:
    length = len(processed["vocal_center"])
    group_before = processed["vocal_center"] + processed["vocal_wide"]
    rows = frame_levels(group_before, sr, 0.75)
    levels = np.array([float(row["rms_db"]) for row in rows], dtype=np.float32)
    threshold = max(float(np.percentile(levels, 54.0)), -34.0)
    active_levels = levels[levels >= threshold]
    target = float(np.median(active_levels)) if len(active_levels) else -20.0
    gains = np.zeros(len(rows), dtype=np.float32)
    for i, row in enumerate(rows):
        level = float(row["rms_db"])
        active = level >= threshold
        if active:
            gain = float(np.clip(target - level, -2.2, 5.4))
            if abs(gain) < 0.12:
                gain = 0.0
        else:
            gain = 0.0
        gains[i] = gain
        row["active_vocal"] = bool(active)
        row["active_threshold_rms_db"] = round(threshold, 2)
        row["target_vocal_rms_db"] = round(target, 2)
        row["clip_gain_db"] = round(gain, 2)
    curve = smooth_curve_from_rows(rows, gains, length, sr, smooth_s=0.18, min_db=-2.2, max_db=5.4)
    processed["vocal_center"] = processed["vocal_center"] * db_to_amp(curve)[:, None]
    processed["vocal_wide"] = processed["vocal_wide"] * db_to_amp(curve)[:, None]
    processed["backing_vocals"] = processed["backing_vocals"] * db_to_amp(curve * 0.30)[:, None]

    group_mid = processed["vocal_center"] + processed["vocal_wide"]
    mid_rows = frame_levels(group_mid, sr, 0.75)
    active_mid_levels = np.array([float(mid_rows[i]["rms_db"]) for i, row in enumerate(rows) if row["active_vocal"] and i < len(mid_rows)], dtype=np.float32)
    residual_gains = np.zeros(len(rows), dtype=np.float32)
    if len(active_mid_levels):
        residual_median = float(np.median(active_mid_levels))
        residual_floor = residual_median - 0.95
        residual_ceiling = residual_median + 0.95
        for i, row in enumerate(rows):
            if not row["active_vocal"] or i >= len(mid_rows):
                continue
            level = float(mid_rows[i]["rms_db"])
            if level < residual_floor:
                gain = min((residual_floor - level) * 1.08, 3.4)
            elif level > residual_ceiling:
                gain = max((residual_ceiling - level) * 0.62, -1.5)
            else:
                gain = 0.0
            if abs(gain) < 0.10:
                gain = 0.0
            residual_gains[i] = gain
            row["post_first_pass_rms_db"] = mid_rows[i]["rms_db"]
            row["residual_clip_gain_db"] = round(float(gain), 2)
    residual_curve = smooth_curve_from_rows(rows, residual_gains, length, sr, smooth_s=0.12, min_db=-1.5, max_db=3.4)
    processed["vocal_center"] = processed["vocal_center"] * db_to_amp(residual_curve)[:, None]
    processed["vocal_wide"] = processed["vocal_wide"] * db_to_amp(residual_curve)[:, None]
    processed["backing_vocals"] = processed["backing_vocals"] * db_to_amp(residual_curve * 0.25)[:, None]

    processed["vocal_center"] = post_reconstruction_vocal_chain(processed["vocal_center"], sr, -18.6, -1.7)
    processed["vocal_wide"] = post_reconstruction_vocal_chain(processed["vocal_wide"], sr, -17.3, -1.7)
    processed["backing_vocals"] = base.peak_cap(processed["backing_vocals"].astype(np.float32), -5.0)

    group_after = processed["vocal_center"] + processed["vocal_wide"]
    after_rows = frame_levels(group_after, sr, 0.75)
    for i, row in enumerate(rows):
        if i < len(after_rows):
            row["post_reconstruction_rms_db"] = after_rows[i]["rms_db"]
    report = {
        "method": "Detect active vocal phrases from the provided Marunouchi vocal stems, skip gaps/breath/tails, apply phrase clip gain before final vocal dynamic EQ/de-ess/compression/leveller/output guard.",
        "active_threshold_rms_db": round(threshold, 2),
        "target_vocal_rms_db": round(target, 2),
        "max_clip_gain_db": round(float(np.max(gains)), 2),
        "min_clip_gain_db": round(float(np.min(gains)), 2),
        "max_residual_clip_gain_db": round(float(np.max(residual_gains)), 2),
        "min_residual_clip_gain_db": round(float(np.min(residual_gains)), 2),
        "before": vocal_spread_summary(rows, "rms_db"),
        "after": vocal_spread_summary(rows, "post_reconstruction_rms_db"),
        "qc_target": "active vocal p10-p90 <= 2 dB and 3 dB outlier count 0",
        "rows": rows,
    }
    write_json(REPORTS / VOCAL_RECON_JSON, report)
    write_csv(REPORTS / VOCAL_RECON_CSV, rows)
    return report


def band_active_rms_db(y: np.ndarray, sr: int, low: float, high: float, active_mask: np.ndarray | None = None) -> float:
    band = base.butter_filter(y, sr, "bandpass", (low, high), order=3)
    if active_mask is not None and np.any(active_mask):
        band = band[active_mask]
    return base.active_rms_db(band)


def presence_ratio(vocal: np.ndarray, music: np.ndarray, sr: int) -> dict[str, float]:
    mono = np.mean(np.abs(vocal), axis=1)
    frame = 2048
    usable = len(mono) - len(mono) % frame
    mask = np.ones(len(vocal), dtype=bool)
    if usable > 0:
        frames = mono[:usable].reshape(-1, frame)
        levels = np.sqrt(np.mean(frames * frames, axis=1) + 1e-12)
        threshold = np.percentile(levels, 55.0)
        frame_mask = np.repeat(levels >= threshold, frame)
        mask = np.zeros(len(vocal), dtype=bool)
        mask[:usable] = frame_mask
    out: dict[str, float] = {}
    for name, low, high in DYNAMIC_EQ_BANDS:
        vocal_db = band_active_rms_db(vocal, sr, low, high, mask)
        music_db = band_active_rms_db(music, sr, low, high, mask)
        out[f"{name}_vocal_minus_music_db"] = round(vocal_db - music_db, 2)
    return out


def sidechain_dynamic_eq_pocket(
    target: np.ndarray,
    trigger: np.ndarray,
    sr: int,
    low: float,
    high: float,
    max_cut_db: float,
    percentile: float,
    smooth_ms: float,
    slope: float = 0.52,
) -> np.ndarray:
    band = base.butter_filter(target, sr, "bandpass", (low, high), order=3)
    trig_env = base.envelope(np.mean(np.abs(trigger), axis=1), sr, smooth_ms)
    trig_db = amp_to_db(trig_env)
    active = trig_db[trig_db > -90.0]
    threshold = float(np.percentile(active, percentile)) if len(active) else -60.0
    cut = np.minimum(max_cut_db, np.maximum(trig_db - threshold, 0.0) * slope)
    gain = db_to_amp(-cut).astype(np.float32)
    return (target - band + band * gain[:, None]).astype(np.float32)


def reinforce_music_sidechain_pockets(key: str, y: np.ndarray, sr: int, trigger: np.ndarray) -> np.ndarray:
    if key in {"keyboard", "guitar_main", "guitar_support", "synth"}:
        cuts = (0.55, 0.72, 0.48)
    elif key == "drums":
        cuts = (0.28, 0.34, 0.26)
    elif key == "bass":
        cuts = (0.25, 0.22, 0.16)
    else:
        cuts = (0.38, 0.48, 0.34)
    x = sidechain_dynamic_eq_pocket(y, trigger, sr, 250, 650, cuts[0], percentile=48.0, smooth_ms=155.0)
    x = sidechain_dynamic_eq_pocket(x, trigger, sr, 1500, 5200, cuts[1], percentile=47.0, smooth_ms=125.0)
    x = sidechain_dynamic_eq_pocket(x, trigger, sr, 4000, 8500, cuts[2], percentile=49.0, smooth_ms=80.0)
    return base.peak_cap(x.astype(np.float32), -1.7)


def process_music_stem(key: str, y: np.ndarray, sr: int, trigger: np.ndarray) -> np.ndarray:
    if key == "bass":
        x = base.butter_filter(y, sr, "lowpass", 7200, order=2)
        x = base.soft_saturation(x, drive_db=0.65, mix=0.035)
        x = base.rbj_peaking(x, sr, 76, 0.35, 0.8)
        x = base.sidechain_band_duck(x, trigger, sr, 250, 650, max_cut_db=0.45, percentile=64.0, smooth_ms=145.0)
        x = base.sidechain_band_duck(x, trigger, sr, 1500, 5200, max_cut_db=0.55, percentile=64.0, smooth_ms=130.0)
        x = base.sidechain_band_duck(x, trigger, sr, 4000, 8500, max_cut_db=0.30, percentile=68.0, smooth_ms=80.0)
        trim_db = -0.1
    elif key == "drums":
        x = base.dynamic_band_tame(y, sr, 6500, 10500, max_cut_db=0.8, percentile=68.0, slope=0.45, smooth_ms=8.0)
        x = base.soft_saturation(x, drive_db=0.45, mix=0.025)
        x = base.sidechain_band_duck(x, trigger, sr, 250, 650, max_cut_db=0.34, percentile=66.0, smooth_ms=120.0)
        x = base.sidechain_band_duck(x, trigger, sr, 1500, 5200, max_cut_db=0.62, percentile=64.0, smooth_ms=110.0)
        x = base.sidechain_band_duck(x, trigger, sr, 4000, 8500, max_cut_db=0.40, percentile=68.0, smooth_ms=70.0)
        trim_db = -0.35
    elif key in {"keyboard", "guitar_main", "guitar_support", "synth"}:
        x = base.sidechain_band_duck(y, trigger, sr, 250, 650, max_cut_db=0.90, percentile=58.0, smooth_ms=165.0)
        x = base.sidechain_band_duck(x, trigger, sr, 1500, 5200, max_cut_db=1.55, percentile=57.0, smooth_ms=145.0)
        x = base.sidechain_band_duck(x, trigger, sr, 4000, 8500, max_cut_db=1.05, percentile=60.0, smooth_ms=95.0)
        trim_db = 0.0
    else:
        x = base.sidechain_band_duck(y, trigger, sr, 250, 650, max_cut_db=0.65, percentile=62.0, smooth_ms=145.0)
        x = base.sidechain_band_duck(x, trigger, sr, 1500, 5200, max_cut_db=1.05, percentile=60.0, smooth_ms=130.0)
        x = base.sidechain_band_duck(x, trigger, sr, 4000, 8500, max_cut_db=0.72, percentile=64.0, smooth_ms=85.0)
        trim_db = -0.35
    x = x * float(db_to_amp(trim_db))
    return base.peak_cap(x.astype(np.float32), -2.2)


def group_sum(stems: dict[str, np.ndarray], keys: set[str], gains: dict[str, float]) -> np.ndarray:
    length = len(next(iter(stems.values())))
    out = np.zeros((length, 2), dtype=np.float32)
    for key in sorted(keys):
        out += stems[key] * float(db_to_amp(gains.get(key, 0.0)))
    return out.astype(np.float32)


def lock_music_size_to_original(raw: dict[str, np.ndarray], processed: dict[str, np.ndarray], sr: int) -> dict[str, Any]:
    raw_music = group_sum(raw, MUSIC_KEYS, {key: 0.0 for key in MUSIC_KEYS})
    processed_music_before = group_sum(processed, MUSIC_KEYS, {key: 0.0 for key in MUSIC_KEYS})
    raw_active = base.active_rms_db(raw_music)
    processed_active = base.active_rms_db(processed_music_before)
    gain_db = float(np.clip(raw_active - processed_active, -2.0, 2.0))
    for key in MUSIC_KEYS:
        processed[key] = base.peak_cap((processed[key] * float(db_to_amp(gain_db))).astype(np.float32), -1.7)
    processed_music_after = group_sum(processed, MUSIC_KEYS, {key: 0.0 for key in MUSIC_KEYS})
    report = {
        "method": "Lock processed music stem sum to the original provided music stem sum before mastering; do not rely on master LUFS only.",
        "raw_music_active_rms_db": round(raw_active, 2),
        "processed_music_before_active_rms_db": round(processed_active, 2),
        "applied_music_size_gain_db": round(gain_db, 2),
        "processed_music_after_active_rms_db": round(base.active_rms_db(processed_music_after), 2),
    }
    write_json(REPORTS / MUSIC_SIZE_JSON, report)
    return report


def calibrate_front_ratio(
    processed: dict[str, np.ndarray],
    gains: dict[str, float],
    target_ratio_db: float = 0.45,
) -> dict[str, Any]:
    before_vocal = group_sum(processed, VOCAL_KEYS, gains)
    before_mix = group_sum(processed, set(gains), gains)
    before_ratio = base.active_rms_db(before_vocal) - base.active_rms_db(before_mix)
    correction = float(np.clip(target_ratio_db - before_ratio, -1.5, 2.8))
    for key in VOCAL_KEYS:
        gains[key] += correction * 0.68
    gains["backing_vocals"] -= correction * 0.22
    for key in MUSIC_KEYS:
        gains[key] -= correction * 0.20
    after_vocal = group_sum(processed, VOCAL_KEYS, gains)
    after_mix = group_sum(processed, set(gains), gains)
    after_ratio = base.active_rms_db(after_vocal) - base.active_rms_db(after_mix)
    return {
        "target_vocal_group_vs_mix_active_db": target_ratio_db,
        "before_vocal_group_vs_mix_active_db": round(before_ratio, 2),
        "after_vocal_group_vs_mix_active_db": round(after_ratio, 2),
        "applied_ratio_correction_db": round(correction, 2),
        "final_gains_db": {key: round(value, 2) for key, value in sorted(gains.items())},
    }


def window_floor_lock(y: np.ndarray, sr: int, floor_margin_db: float = 2.1) -> tuple[np.ndarray, dict[str, Any]]:
    frame = int(sr * 1.5)
    rows: list[dict[str, Any]] = []
    levels: list[float] = []
    mono = np.mean(y, axis=1).astype(np.float32)
    duration_s = len(y) / float(sr)
    analysis_end_s = max(4.0, duration_s - 1.2)
    for start in range(0, len(y), frame):
        end = min(len(y), start + frame)
        if end - start < int(sr * 0.5):
            break
        chunk = mono[start:end]
        level = float(amp_to_db(np.sqrt(np.mean(chunk * chunk) + 1e-12)))
        rows.append({"start_s": round(start / sr, 3), "end_s": round(end / sr, 3), "rms_db": round(level, 2)})
        if 4.0 <= start / sr and end / sr <= analysis_end_s:
            levels.append(level)
    median = float(np.median(levels)) if levels else -18.0
    floor = median - floor_margin_db
    gains = np.zeros(len(rows), dtype=np.float32)
    for i, row in enumerate(rows):
        start = float(row["start_s"])
        end = float(row["end_s"])
        if start < 4.0 or end > analysis_end_s:
            gain = 0.0
        elif float(row["rms_db"]) < floor:
            gain = min((floor - float(row["rms_db"])) * 1.08, 8.4)
        else:
            gain = 0.0
        if abs(gain) < 0.18:
            gain = 0.0
        gains[i] = gain
        row["floor_target_rms_db"] = round(floor, 2)
        row["applied_floor_gain_db"] = round(float(gain), 2)
    centers = np.array([(row["start_s"] + row["end_s"]) * 0.5 for row in rows], dtype=np.float32)
    times = np.arange(len(y), dtype=np.float32) / float(sr)
    curve = np.interp(times, centers, gains, left=gains[0], right=gains[-1]).astype(np.float32) if len(centers) > 1 else np.zeros(len(y), dtype=np.float32)
    smooth = max(1, int(sr * 0.32))
    if smooth > 1:
        kernel = np.hanning(smooth * 2 + 1).astype(np.float32)
        kernel /= np.sum(kernel)
        curve = base.signal.fftconvolve(curve, kernel, mode="same").astype(np.float32)
    out = y * db_to_amp(curve)[:, None]
    out = base.soft_clip(out.astype(np.float32), ceiling=0.955)
    out = base.peak_cap(out, -2.0)
    after_rows: list[dict[str, Any]] = []
    mono_after = np.mean(out, axis=1).astype(np.float32)
    for i, row in enumerate(rows):
        start = int(round(float(row["start_s"]) * sr))
        end = int(round(float(row["end_s"]) * sr))
        level = float(amp_to_db(np.sqrt(np.mean(mono_after[start:end] * mono_after[start:end]) + 1e-12)))
        after_rows.append({**row, "post_floor_rms_db": round(level, 2), "floor_improvement_db": round(level - float(row["rms_db"]), 2)})
    report = {
        "active_median_rms_db": round(median, 2),
        "floor_target_rms_db": round(floor, 2),
        "analysis_end_s": round(analysis_end_s, 3),
        "max_floor_gain_db": round(float(np.max(gains)), 2),
        "mean_floor_gain_db": round(float(np.mean(gains[gains > 0])) if np.any(gains > 0) else 0.0, 2),
        "rows": after_rows,
    }
    return out.astype(np.float32), report


def write_master(input_path: Path) -> None:
    filt = (
        "highpass=f=24,"
        "equalizer=f=230:t=q:w=0.95:g=-0.18,"
        "equalizer=f=3200:t=q:w=0.9:g=0.15,"
        "equalizer=f=7800:t=q:w=0.85:g=-0.10,"
        "acompressor=threshold=-18.5dB:ratio=1.12:attack=22:release=150:makeup=1.01,"
        "loudnorm=I=-14.0:TP=-1.6:LRA=4.0:linear=false,"
        "alimiter=limit=0.82:attack=2:release=120:level=false"
    )
    subprocess.run(
        [
            base.FFMPEG,
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(input_path),
            "-af",
            filt,
            "-ar",
            "48000",
            "-c:a",
            "pcm_s24le",
            str(FINAL_WAV),
        ],
        check=True,
    )
    subprocess.run(
        [base.FFMPEG, "-y", "-hide_banner", "-loglevel", "error", "-i", str(FINAL_WAV), "-c:a", "libmp3lame", "-b:a", "320k", str(FINAL_MP3)],
        check=True,
    )


def write_ab() -> None:
    temp = REPORTS / "_ab"
    shutil.rmtree(temp, ignore_errors=True)
    temp.mkdir(parents=True, exist_ok=True)
    before = temp / "before.wav"
    after = temp / "after.wav"
    silence = temp / "silence.wav"
    concat = temp / "concat.txt"
    subprocess.run([base.FFMPEG, "-y", "-hide_banner", "-loglevel", "error", "-ss", "20", "-t", "60", "-i", str(STEMS["full_reference"]), "-c:a", "pcm_s16le", str(before)], check=True)
    subprocess.run([base.FFMPEG, "-y", "-hide_banner", "-loglevel", "error", "-ss", "20", "-t", "60", "-i", str(FINAL_WAV), "-c:a", "pcm_s16le", str(after)], check=True)
    subprocess.run([base.FFMPEG, "-y", "-hide_banner", "-loglevel", "error", "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo:d=1", "-c:a", "pcm_s16le", str(silence)], check=True)
    concat.write_text(f"file '{before}'\nfile '{silence}'\nfile '{after}'\n", encoding="utf-8")
    subprocess.run([base.FFMPEG, "-y", "-hide_banner", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(concat), "-c:a", "libmp3lame", "-b:a", "320k", str(AB_MP3)], check=True)
    shutil.rmtree(temp, ignore_errors=True)


def section_rows(path: Path, label: str, window_s: float) -> list[dict[str, Any]]:
    sr, y, _ = base.read_wav(path)
    mono = np.mean(y, axis=1).astype(np.float32)
    frame = int(round(sr * window_s))
    duration_s = len(y) / float(sr)
    analysis_end_s = max(4.0, duration_s - 1.2)
    rows: list[dict[str, Any]] = []
    for start in range(0, len(mono), frame):
        end = min(len(mono), start + frame)
        if end - start < int(sr * 0.5):
            break
        chunk = mono[start:end]
        level = float(amp_to_db(np.sqrt(np.mean(chunk * chunk) + 1e-12)))
        peak = float(amp_to_db(np.max(np.abs(chunk)))) if len(chunk) else -120.0
        rows.append(
            {
                "label": label,
                "file": rel(path),
                "window_s": window_s,
                "start_s": round(start / sr, 3),
                "end_s": round(end / sr, 3),
                "rms_db": round(level, 2),
                "peak_db": round(peak, 2),
                "analysis_window": bool(start / sr >= 4.0 and end / sr <= analysis_end_s),
            }
        )
    active_levels = np.array([row["rms_db"] for row in rows if row["analysis_window"]], dtype=np.float32)
    median = float(np.median(active_levels)) if len(active_levels) else -18.0
    for row in rows:
        dev = float(row["rms_db"]) - median
        row["analysis_active_median_rms_db"] = round(median, 2)
        row["deviation_from_analysis_median_db"] = round(dev, 2)
        row["outside_plus_minus_3db"] = bool(row["analysis_window"] and abs(dev) > 3.0)
    return rows


def write_consistency_report() -> dict[str, Any]:
    paths = {
        "source_full_reference": STEMS["full_reference"],
        "stem_mix_premaster": PREMASTER_WAV,
        "floor_locked_premaster": FLOOR_WAV,
        "final_master_wav": FINAL_WAV,
        "vocal_solo": VOCAL_SOLO,
    }
    rows: list[dict[str, Any]] = []
    summary: dict[str, Any] = {}
    for label, path in paths.items():
        if not path.exists():
            continue
        summary[label] = {}
        for window_s in (1.5, 3.0, 6.0):
            item_rows = section_rows(path, label, window_s)
            rows.extend(item_rows)
            selected = [row for row in item_rows if row["analysis_window"]]
            deviations = np.array([float(row["deviation_from_analysis_median_db"]) for row in selected], dtype=np.float32)
            summary[label][str(window_s)] = {
                "count": len(selected),
                "outside_plus_minus_3db_count": int(np.sum(np.abs(deviations) > 3.0)) if len(deviations) else 0,
                "max_positive_deviation_db": round(float(np.max(deviations)) if len(deviations) else 0.0, 2),
                "max_negative_deviation_db": round(float(np.min(deviations)) if len(deviations) else 0.0, 2),
                "mean_abs_deviation_db": round(float(np.mean(np.abs(deviations))) if len(deviations) else 0.0, 2),
                "lowest_windows": sorted(selected, key=lambda row: row["rms_db"])[:8],
            }
    write_json(REPORTS / WINDOW_REPORT_JSON, {"summary": summary, "rows": rows})
    write_csv(REPORTS / WINDOW_REPORT_CSV, rows)
    return summary


def write_reports(processed_paths: dict[str, Path], ratio_report: dict[str, Any], floor_report: dict[str, Any]) -> dict[str, Any]:
    consistency = write_consistency_report()
    vocal_report_path = REPORTS / VOCAL_RECON_JSON
    music_dyn_eq_path = REPORTS / MUSIC_DYN_EQ_JSON
    vocal_report = json.loads(vocal_report_path.read_text(encoding="utf-8")) if vocal_report_path.exists() else {}
    music_dyn_eq_report = json.loads(music_dyn_eq_path.read_text(encoding="utf-8")) if music_dyn_eq_path.exists() else {}
    rows = [base.audio_metrics(STEMS["full_reference"], "source_full_mix_reference")]
    for key in sorted(processed_paths):
        rows.append(base.audio_metrics(processed_paths[key], f"processed_{key}"))
    rows.extend(
        [
            base.audio_metrics(VOCAL_SOLO, "processed_vocal_solo"),
            base.audio_metrics(PREMASTER_WAV, "stem_mix_premaster"),
            base.audio_metrics(FLOOR_WAV, "floor_locked_premaster"),
            base.audio_metrics(FINAL_WAV, "final_master_wav"),
            base.audio_metrics(FINAL_MP3, "final_master_mp3"),
        ]
    )
    write_json(REPORTS / "qc_metrics.json", rows)
    write_csv(REPORTS / "qc_metrics.csv", rows)
    source = rows[0]
    final = rows[-2]
    mp3 = rows[-1]
    final_consistency = consistency.get("final_master_wav", {})
    vocal_after = vocal_report.get("after", {})
    vocal_reconstruction_passed = (
        vocal_after.get("p10_p90_spread_db", 99) <= 2.0
        and vocal_after.get("outside_plus_minus_3db_count", 99) == 0
    )
    presence_improvement = music_dyn_eq_report.get("improvement_db", {})
    presence_passed = (
        presence_improvement.get("vocal_presence_collision_vocal_minus_music_db", -99) > 0
        and presence_improvement.get("synth_ai_glare_consonants_vocal_minus_music_db", -99) > 0
    )
    qc_passed = (
        (final.get("true_peak_dbfs") or 99) <= -1.0
        and (mp3.get("true_peak_dbfs") or 99) <= -1.0
        and final_consistency.get("1.5", {}).get("outside_plus_minus_3db_count", 99) == 0
        and final_consistency.get("3.0", {}).get("outside_plus_minus_3db_count", 99) == 0
        and vocal_reconstruction_passed
        and presence_passed
    )
    qc = {
        "passed": qc_passed,
        "status": "qc_passed_user_review_required" if qc_passed else "qc_failed_revision_required",
        "delivery_ready": False,
        "source_lufs": source.get("integrated_lufs"),
        "source_true_peak_dbfs": source.get("true_peak_dbfs"),
        "final_lufs": final.get("integrated_lufs"),
        "final_true_peak_dbfs": final.get("true_peak_dbfs"),
        "mp3_true_peak_dbfs": mp3.get("true_peak_dbfs"),
        "vocal_front_ratio": ratio_report,
        "vocal_reconstruction": vocal_after,
        "music_dynamic_eq_presence_improvement_db": presence_improvement,
        "floor_lock": {k: floor_report[k] for k in ("active_median_rms_db", "floor_target_rms_db", "max_floor_gain_db", "mean_floor_gain_db")},
        "final_consistency": final_consistency,
        "note": "This render uses the user-provided Marunouchi stems as the actual source. The original full mix is reference/A-B only.",
    }
    write_json(REPORTS / "qc_summary.json", qc)
    notes = [
        "# Marunouchi v01 Stem Mix Master Report",
        "",
        "## Intent",
        "",
        "- User clarified the supplied Marunouchi zip itself must be mixed/mastered.",
        "- `0 Marunouchi.wav` is used only as source full-mix reference/A-B.",
        "- Stems `1-10` are processed and summed into a new stem mix master.",
        "",
        "## Deliverables",
        "",
        f"- Final WAV: `{rel(FINAL_WAV)}`",
        f"- Final MP3: `{rel(FINAL_MP3)}`",
        f"- Vocal solo: `{rel(VOCAL_SOLO)}`",
        f"- A/B preview: `{rel(AB_MP3)}`",
        f"- Deliverable ZIP: `{rel(ZIP_PATH)}`",
        "",
        "## QC",
        "",
        f"- Source: `{source.get('integrated_lufs')}` LUFS / TP `{source.get('true_peak_dbfs')}` dBFS",
        f"- Final WAV: `{final.get('integrated_lufs')}` LUFS / TP `{final.get('true_peak_dbfs')}` dBFS",
        f"- Final MP3 TP: `{mp3.get('true_peak_dbfs')}` dBFS",
        f"- Vocal front ratio: `{ratio_report['before_vocal_group_vs_mix_active_db']}` -> `{ratio_report['after_vocal_group_vs_mix_active_db']}` dB",
        f"- Vocal active p10-p90 spread: `{vocal_after.get('p10_p90_spread_db')}` dB",
        f"- Vocal active +/-3dB outliers: `{vocal_after.get('outside_plus_minus_3db_count')}`",
        f"- Music dynamic EQ presence improvement: `{presence_improvement}`",
        f"- Final 1.5s outside +/-3dB: `{final_consistency.get('1.5', {}).get('outside_plus_minus_3db_count')}`",
        f"- Final 3.0s outside +/-3dB: `{final_consistency.get('3.0', {}).get('outside_plus_minus_3db_count')}`",
    ]
    (REPORTS / "marunouchi_v01_stem_mix_master_report.md").write_text("\n".join(notes) + "\n", encoding="utf-8")
    return qc


def build_zip() -> None:
    ZIP_PATH.unlink(missing_ok=True)
    files = [
        FINAL_WAV,
        FINAL_MP3,
        VOCAL_SOLO,
        AB_MP3,
        PREMASTER_WAV,
        FLOOR_WAV,
        REPORTS / "qc_summary.json",
        REPORTS / "qc_metrics.json",
        REPORTS / "qc_metrics.csv",
        REPORTS / "stem_processing_report.json",
        REPORTS / "stem_processing_report.csv",
        REPORTS / "vocal_front_ratio_report.json",
        REPORTS / "premaster_floor_lock_report.json",
        REPORTS / "premaster_floor_lock_report.csv",
        REPORTS / WINDOW_REPORT_JSON,
        REPORTS / WINDOW_REPORT_CSV,
        REPORTS / VOCAL_RECON_JSON,
        REPORTS / VOCAL_RECON_CSV,
        REPORTS / MUSIC_DYN_EQ_JSON,
        REPORTS / MUSIC_DYN_EQ_CSV,
        REPORTS / MUSIC_SIZE_JSON,
        REPORTS / "marunouchi_v01_stem_mix_master_report.md",
    ]
    with zipfile.ZipFile(ZIP_PATH, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in files:
            if path.exists():
                archive.write(path, path.relative_to(ROOT).as_posix())


def main() -> int:
    ensure_dirs()
    sr, length, raw = read_all()
    processed: dict[str, np.ndarray] = {}
    rows: list[dict[str, Any]] = []

    center = process_center_vocal(raw["vocal_center"], sr)
    wide = process_wide_vocal(raw["vocal_wide"], sr, center)
    vocal_group_seed = center + wide
    backing = process_backing(raw["backing_vocals"], sr, vocal_group_seed)
    processed["vocal_center"] = center
    processed["vocal_wide"] = wide
    processed["backing_vocals"] = backing
    vocal_report = reconstruct_vocal_stems(processed, sr)
    trigger = processed["vocal_center"] + processed["vocal_wide"] * 0.85
    raw_music_sum = group_sum(raw, MUSIC_KEYS, {key: 0.0 for key in MUSIC_KEYS})
    before_presence_ratio = presence_ratio(trigger, raw_music_sum, sr)

    for key in sorted(MUSIC_KEYS):
        stem = process_music_stem(key, raw[key], sr, trigger)
        processed[key] = reinforce_music_sidechain_pockets(key, stem, sr, trigger)
    music_size_report = lock_music_size_to_original(raw, processed, sr)
    processed_music_sum = group_sum(processed, MUSIC_KEYS, {key: 0.0 for key in MUSIC_KEYS})
    after_presence_ratio = presence_ratio(trigger, processed_music_sum, sr)
    music_dyn_eq_rows: list[dict[str, Any]] = []
    improvement: dict[str, float] = {}
    for name, low, high in DYNAMIC_EQ_BANDS:
        metric = f"{name}_vocal_minus_music_db"
        before = before_presence_ratio.get(metric)
        after = after_presence_ratio.get(metric)
        delta = round((after or 0.0) - (before or 0.0), 2)
        improvement[metric] = delta
        music_dyn_eq_rows.append(
            {
                "band": name,
                "low_hz": low,
                "high_hz": high,
                "before_vocal_minus_music_db": before,
                "after_vocal_minus_music_db": after,
                "improvement_db": delta,
            }
        )
    music_dyn_eq_report = {
        "method": "Use reconstructed vocal as sidechain trigger and carve the music bus in 250-650 Hz, 1.5-5.2 kHz, and 4-8.5 kHz before final level locking.",
        "bands": [{"name": name, "low_hz": low, "high_hz": high} for name, low, high in DYNAMIC_EQ_BANDS],
        "before_vocal_minus_music_db": before_presence_ratio,
        "after_vocal_minus_music_db": after_presence_ratio,
        "improvement_db": improvement,
        "music_size_lock": music_size_report,
        "qc_target": "vocal/music presence ratio improves in active vocal windows after music bus dynamic EQ",
    }
    write_json(REPORTS / MUSIC_DYN_EQ_JSON, music_dyn_eq_report)
    write_csv(REPORTS / MUSIC_DYN_EQ_CSV, music_dyn_eq_rows)

    processed_paths: dict[str, Path] = {}
    for key, y in processed.items():
        path = PROCESSED / f"{key}.wav"
        base.write_wav(path, sr, y)
        processed_paths[key] = path
        side_db, corr = side_mid_db(y)
        rows.append(
            {
                "stem": key,
                "source_active_rms_db": round(base.active_rms_db(raw[key]), 2) if key in raw else None,
                "processed_active_rms_db": round(base.active_rms_db(y), 2),
                "processed_peak_dbfs": round(float(amp_to_db(np.max(np.abs(y)))), 2),
                "side_mid_db": round(side_db, 2),
                "stereo_corr": round(corr, 4),
            }
        )

    gains = dict(BASE_GAINS_DB)
    ratio_report = calibrate_front_ratio(processed, gains, target_ratio_db=0.45)
    write_json(REPORTS / "vocal_front_ratio_report.json", ratio_report)

    mix = group_sum(processed, set(gains), gains)
    mix = base.soft_clip(mix.astype(np.float32), ceiling=0.955)
    mix = base.peak_cap(mix.astype(np.float32), -2.0)
    base.write_wav(PREMASTER_WAV, sr, mix)

    vocal_solo = group_sum(processed, VOCAL_KEYS, gains)
    vocal_solo = base.peak_cap(vocal_solo.astype(np.float32), -1.4)
    base.write_wav(VOCAL_SOLO, sr, vocal_solo)

    floor_mix, floor_report = window_floor_lock(mix, sr, floor_margin_db=1.45)
    base.write_wav(FLOOR_WAV, sr, floor_mix)
    write_json(REPORTS / "premaster_floor_lock_report.json", floor_report)
    write_csv(REPORTS / "premaster_floor_lock_report.csv", floor_report["rows"])

    write_json(
        REPORTS / "stem_processing_report.json",
        {
            "sample_rate": sr,
            "length_samples": length,
            "rows": rows,
            "final_gains_db": ratio_report["final_gains_db"],
            "vocal_reconstruction_qc": vocal_report,
            "music_dynamic_eq_presence_qc": music_dyn_eq_report,
        },
    )
    write_csv(REPORTS / "stem_processing_report.csv", rows)

    write_master(FLOOR_WAV)
    write_ab()
    qc = write_reports(processed_paths, ratio_report, floor_report)
    build_zip()
    print(
        json.dumps(
            {
                "final_wav": rel(FINAL_WAV),
                "final_mp3": rel(FINAL_MP3),
                "ab_mp3": rel(AB_MP3),
                "deliverable_zip": rel(ZIP_PATH),
                "lufs": qc["final_lufs"],
                "true_peak_dbfs": qc["final_true_peak_dbfs"],
                "mp3_true_peak_dbfs": qc["mp3_true_peak_dbfs"],
                "vocal_front_ratio_after_db": ratio_report["after_vocal_group_vs_mix_active_db"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

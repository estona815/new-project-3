#!/usr/bin/env python3
from __future__ import annotations

import csv
import importlib.util
import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

import numpy as np


ROOT = Path("/Users/hantaeheuk/Documents/New project 3")
V05_SCRIPT = ROOT / "tools" / "mwolla_v05_phrase_plateau_master.py"
SLUG = "mwolla_v06_vocal_locked_reference_master"


spec = importlib.util.spec_from_file_location("mwolla_v05_phrase_plateau_master", V05_SCRIPT)
if spec is None or spec.loader is None:
    raise RuntimeError(f"Could not load v05 script: {V05_SCRIPT}")
v5 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v5)
v4 = v5.v4
v3 = v4.v3
v2 = v3.v2
v1 = v2.v1
base = v5.base


PHRASE_PREMASTER_NAME = "mwolla_v06_VOCAL_LOCKED_PREMASTER_24-48.wav"
PLATEAU_PREMASTER_NAME = "mwolla_v06_VOCAL_LOCKED_PLATEAU_PREMASTER_24-48.wav"
FLOOR_PREMASTER_NAME = "mwolla_v06_VOCAL_LOCKED_FLOOR_PREMASTER_24-48.wav"
WINDOW_REPORT_JSON = "section_loudness_consistency_1p5s_3s_6s_report.json"
WINDOW_REPORT_CSV = "section_loudness_consistency_1p5s_3s_6s_report.csv"
WINDOW_REPORT_MD = "section_loudness_consistency_1p5s_3s_6s_report.md"
VOCAL_LOCK_JSON = "vocal_locked_presence_report.json"
VOCAL_LOCK_CSV = "vocal_locked_presence_report.csv"
REFERENCE_JSON = "marunouchi_reference_analysis.json"
VOCAL_FRONT_REPORT_JSON = "vocal_front_ratio_autocalibration_report.json"
VOCAL_FRONT_REPORT_CSV = "vocal_front_ratio_autocalibration_report.csv"
FLOOR_LOCK_REPORT_JSON = "premaster_floor_lock_report.json"
FLOOR_LOCK_REPORT_CSV = "premaster_floor_lock_report.csv"

MUSIC_KEYS = {"woodwinds", "brass", "fx", "synth", "strings", "percussion", "keyboard", "guitar", "bass", "drums"}
VOCAL_KEYS = {"lead_vocal", "female_vocal", "backing_vocals", "vocal_reverb", "vocal_delay"}


def configure_base() -> None:
    v5.configure_base()
    base.SLUG = SLUG
    base.WORK = ROOT / "audio_work" / SLUG
    base.SOURCE = base.WORK / "source_stems"
    base.PROCESSED = base.WORK / "processed_stems"
    base.REAPER_DIR = ROOT / "reaper" / SLUG
    base.RENDERS = ROOT / "renders" / SLUG
    base.REPORTS = ROOT / "reports" / SLUG

    base.RPP = base.REAPER_DIR / "mwolla_v06_VOCAL_LOCKED_REFERENCE_MASTER.rpp"
    base.BUILD_LUA = base.REAPER_DIR / "build_mwolla_v06_vocal_locked_reference_master.lua"
    base.RUN_BUILD_LUA = base.REAPER_DIR / "run_build_mwolla_v06_vocal_locked_reference_master.lua"
    base.RENDER_LUA = base.REAPER_DIR / "render_mwolla_v06_vocal_locked_reference_master.lua"
    base.RUN_RENDER_LUA = base.REAPER_DIR / "run_render_mwolla_v06_vocal_locked_reference_master.lua"
    base.TRACE_JSON = base.REPORTS / "actual_reaper_plugin_trace.json"
    base.TRACE_MD = base.REPORTS / "actual_reaper_plugin_trace.md"

    base.REAPER_PRINT = base.RENDERS / "mwolla_v06_REAPERPRINT_24-48.wav"
    base.FINAL_WAV = base.RENDERS / "mwolla_v06_VOCAL_LOCKED_REFERENCE_MASTER.wav"
    base.FINAL_MP3 = base.RENDERS / "mwolla_v06_VOCAL_LOCKED_REFERENCE_MASTER_320k.mp3"
    base.VOCAL_SOLO = base.RENDERS / "mwolla_v06_VOCAL_SOLO_vocal_locked.wav"
    base.AB_PREVIEW_MP3 = base.RENDERS / "mwolla_v06_AB_original_to_vocal_locked_reference_master_320k.mp3"
    base.DELIVERABLE_ZIP = base.RENDERS / "mwolla_v06_VOCAL_LOCKED_REFERENCE_MASTER_DELIVERABLE.zip"

    base.FEMALE_TARGET_DELTA_DB = -0.35
    base.FEMALE_LAYER_FILENAME = "female_vocal_audible_wide_support_layer.wav"
    base.FEMALE_TRACK_NAME = "13 Female audible wide panned support"
    base.REPORT_FILENAME = "mwolla_v06_vocal_locked_reference_master_report.md"
    base.REPORT_TITLE = "Mwolla v06 Vocal-Locked Reference Master Report"
    base.PROJECT_NOTES = (
        "mwolla v06 vocal-locked reference master: user rejected v05 because the vocal still moved in and out, "
        "female panning was not audible, and the vocal itself was buried. This pass uses Marunouchi stem zip "
        "as the new reference: vocal group forward, audible wide support layer, stronger vocal-band pockets, "
        "and post-stem vocal locking before phrase/premaster leveling. Rev B pushes the vocal group closer to "
        "the Marunouchi front-vocal ratio instead of stopping at only a technical consistency pass."
    )


def db_to_amp(db: float | np.ndarray) -> np.ndarray:
    return np.power(10.0, np.asarray(db) / 20.0)


def amp_to_db(value: float | np.ndarray) -> np.ndarray:
    return 20.0 * np.log10(np.maximum(np.asarray(value), 1e-12))


def rms(y: np.ndarray) -> float:
    return float(np.sqrt(np.mean(np.asarray(y, dtype=np.float64) ** 2) + 1e-12))


def pad_or_trim(y: np.ndarray, length: int) -> np.ndarray:
    if len(y) == length:
        return y.astype(np.float32, copy=False)
    if len(y) > length:
        return y[:length].astype(np.float32)
    out = np.zeros((length, y.shape[1]), dtype=np.float32)
    out[: len(y)] = y
    return out


def read_processed(path: Path, sr: int, length: int) -> np.ndarray:
    stem_sr, y, _ = base.read_wav(path)
    if stem_sr != sr:
        raise RuntimeError(f"Sample-rate mismatch: {path}")
    return pad_or_trim(y, length)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    keys: list[str] = []
    for row in rows:
        for key in row:
            if key not in keys:
                keys.append(key)
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)


def side_mid_db(y: np.ndarray) -> tuple[float, float]:
    left = y[:, 0]
    right = y[:, 1]
    mid = (left + right) * 0.5
    side = (left - right) * 0.5
    corr = float(np.corrcoef(left, right)[0, 1]) if np.std(left) > 1e-8 and np.std(right) > 1e-8 else 1.0
    return float(amp_to_db(rms(side) / (rms(mid) + 1e-12))), corr


def vocal_window_lock(y: np.ndarray, sr: int, *, target_db: float, max_up_db: float, max_down_db: float, smooth_s: float) -> tuple[np.ndarray, list[dict[str, Any]]]:
    mono = np.mean(y, axis=1).astype(np.float32)
    frame = int(round(sr * 1.0))
    rows: list[dict[str, Any]] = []
    levels: list[float] = []
    for start in range(0, len(mono), frame):
        end = min(len(mono), start + frame)
        if end - start < int(sr * 0.35):
            break
        chunk = mono[start:end]
        level = float(amp_to_db(np.sqrt(np.mean(chunk * chunk) + 1e-12)))
        rows.append({"start_s": round(start / sr, 3), "end_s": round(end / sr, 3), "rms_db": round(level, 2)})
        levels.append(level)
    arr = np.array(levels, dtype=np.float32)
    active_threshold = max(float(np.percentile(arr, 42.0)) if len(arr) else -55.0, -48.0)
    gains = np.zeros(len(rows), dtype=np.float32)
    for i, row in enumerate(rows):
        start = float(row["start_s"])
        end = float(row["end_s"])
        level = float(row["rms_db"])
        active = level >= active_threshold and 6.0 <= start and end <= 137.0
        if active:
            gain = np.clip((target_db - level) * 0.78, max_down_db, max_up_db)
            if abs(gain) < 0.20:
                gain = 0.0
        else:
            gain = 0.0
        gains[i] = gain
        row["active_for_lock"] = bool(active)
        row["target_vocal_rms_db"] = target_db
        row["applied_vocal_lock_gain_db"] = round(float(gain), 2)

    centers = np.array([(float(row["start_s"]) + float(row["end_s"])) * 0.5 for row in rows], dtype=np.float32)
    sample_times = np.arange(len(y), dtype=np.float32) / float(sr)
    if len(centers) > 1:
        curve_db = np.interp(sample_times, centers, gains, left=gains[0], right=gains[-1]).astype(np.float32)
    else:
        curve_db = np.zeros(len(y), dtype=np.float32)
    smooth = max(1, int(sr * smooth_s))
    if smooth > 1:
        kernel = np.hanning(smooth * 2 + 1).astype(np.float32)
        kernel /= np.sum(kernel)
        curve_db = base.signal.fftconvolve(curve_db, kernel, mode="same").astype(np.float32)
    curve_db = np.clip(curve_db, max_down_db, max_up_db)
    locked = y * db_to_amp(curve_db)[:, None]
    return locked.astype(np.float32), rows


def make_female_more_audible(layer: np.ndarray, lead: np.ndarray, sr: int) -> np.ndarray:
    mono = np.mean(layer, axis=1).astype(np.float32)
    delay_l = int(round(sr * 0.012))
    delay_r = int(round(sr * 0.024))
    left = mono * 0.58
    right = mono * 0.58
    if delay_l > 0:
        left[delay_l:] += mono[:-delay_l] * 0.34
    if delay_r > 0:
        right[delay_r:] += mono[:-delay_r] * 0.44
    wide = np.column_stack([left, -right]).astype(np.float32)
    presence = base.butter_filter(np.column_stack([mono, mono]).astype(np.float32), sr, "bandpass", (2200, 6200), order=2)
    wide += np.column_stack([presence[:, 0] * 0.18, -presence[:, 1] * 0.18]).astype(np.float32)
    wide = base.sidechain_band_duck(wide, lead, sr, 2450, 5200, max_cut_db=0.08, percentile=60.0, smooth_ms=90.0)
    wide = base.match_active_rms(wide, base.active_rms_db(lead) - 0.15, max_gain_db=13.0)
    return base.peak_cap(wide.astype(np.float32), -1.7)


def apply_music_vocal_pocket(y: np.ndarray, lead: np.ndarray, sr: int, role: str) -> np.ndarray:
    if role in {"synth", "keyboard", "guitar", "woodwinds", "brass", "strings"}:
        out = base.sidechain_band_duck(y, lead, sr, 1550, 5600, max_cut_db=2.45, percentile=45.0, smooth_ms=185.0)
        trim_db = -2.05
    elif role in {"fx", "percussion"}:
        out = base.sidechain_band_duck(y, lead, sr, 2000, 6900, max_cut_db=1.45, percentile=50.0, smooth_ms=160.0)
        trim_db = -1.65
    elif role == "drums":
        out = base.sidechain_band_duck(y, lead, sr, 2100, 6000, max_cut_db=0.85, percentile=54.0, smooth_ms=135.0)
        trim_db = -1.05
    elif role == "bass":
        out = y
        trim_db = -0.55
    else:
        out = y
        trim_db = -0.9
    out = out * float(db_to_amp(trim_db))
    return base.peak_cap(out.astype(np.float32), -2.0)


def approximate_group(processed: dict[str, Path], keys: set[str], sr: int, length: int) -> np.ndarray:
    out = np.zeros((length, 2), dtype=np.float32)
    for key in sorted(keys):
        path = processed.get(key)
        if not path or not path.exists():
            continue
        gain_db = float(v2.TRACK_MIX_DB.get(key, 0.0))
        out += read_processed(path, sr, length) * float(db_to_amp(gain_db))
    return out.astype(np.float32)


def vocal_front_autocalibration(
    processed: dict[str, Path],
    sr: int,
    length: int,
    rows: list[dict[str, Any]],
    target_ratio_db: float = -0.45,
) -> dict[str, Any]:
    before_vocal = approximate_group(processed, VOCAL_KEYS, sr, length)
    before_mix = v2.approximate_mix(processed, sr, length)
    before_ratio = base.active_rms_db(before_vocal) - base.active_rms_db(before_mix)
    correction = float(np.clip(target_ratio_db - before_ratio, 0.0, 3.4))
    vocal_gain_db = correction * 0.76
    female_extra_db = 0.95 if correction > 0.25 else 0.0
    music_trim_db = -correction * 0.32
    applied_rows: list[dict[str, Any]] = []

    for key in sorted(VOCAL_KEYS):
        path = processed.get(key)
        if not path or not path.exists():
            continue
        before = read_processed(path, sr, length)
        gain_db = vocal_gain_db + (female_extra_db if key == "female_vocal" else 0.0)
        after = before * float(db_to_amp(gain_db))
        if key in {"lead_vocal", "female_vocal"}:
            after = base.soft_clip(after.astype(np.float32), ceiling=0.94)
            after = base.peak_cap(after.astype(np.float32), -1.15)
        elif key == "backing_vocals":
            after = base.peak_cap(after.astype(np.float32), -2.2)
        else:
            after = base.peak_cap(after.astype(np.float32), -4.2)
        base.write_wav(path, sr, after)
        row = {
            "stem": key,
            "autocalibration_gain_db": round(gain_db, 2),
            "before_active_rms_db": round(base.active_rms_db(before), 2),
            "after_active_rms_db": round(base.active_rms_db(after), 2),
        }
        rows.append({**row, "target_db": "vocal_front_autocalibration"})
        applied_rows.append(row)

    for key in sorted(MUSIC_KEYS):
        path = processed.get(key)
        if not path or not path.exists():
            continue
        before = read_processed(path, sr, length)
        after = before * float(db_to_amp(music_trim_db))
        after = base.peak_cap(after.astype(np.float32), -2.0)
        base.write_wav(path, sr, after)
        row = {
            "stem": key,
            "autocalibration_gain_db": round(music_trim_db, 2),
            "before_active_rms_db": round(base.active_rms_db(before), 2),
            "after_active_rms_db": round(base.active_rms_db(after), 2),
        }
        rows.append({**row, "target_db": "vocal_front_autocalibration"})
        applied_rows.append(row)

    after_vocal = approximate_group(processed, VOCAL_KEYS, sr, length)
    after_mix = v2.approximate_mix(processed, sr, length)
    after_ratio = base.active_rms_db(after_vocal) - base.active_rms_db(after_mix)
    payload = {
        "target_vocal_group_vs_approx_mix_active_db": target_ratio_db,
        "before_vocal_group_vs_approx_mix_active_db": round(before_ratio, 2),
        "after_vocal_group_vs_approx_mix_active_db": round(after_ratio, 2),
        "requested_correction_db": round(correction, 2),
        "vocal_group_gain_db": round(vocal_gain_db, 2),
        "female_extra_gain_db": round(female_extra_db, 2),
        "music_group_trim_db": round(music_trim_db, 2),
        "reference_context": "Marunouchi vocal group is +0.56 dB versus full active RMS; target here is slightly under that to keep this song's beat intact while making the vocal unmistakably front.",
        "rows": applied_rows,
    }
    write_json(base.REPORTS / VOCAL_FRONT_REPORT_JSON, payload)
    write_csv(base.REPORTS / VOCAL_FRONT_REPORT_CSV, applied_rows)
    return payload


def analyze_marunouchi_reference() -> dict[str, Any]:
    ref_dir = Path("/Users/hantaeheuk/Downloads/마루노우치")
    files = {
        "full": ref_dir / "0 마루노우치.wav",
        "fx": ref_dir / "1 FX.wav",
        "synth": ref_dir / "2 Synth.wav",
        "keyboard": ref_dir / "3 Keyboard.wav",
        "guitar1": ref_dir / "4 Guitar.wav",
        "bass": ref_dir / "5 Bass.wav",
        "drums": ref_dir / "6 Drums.wav",
        "backing": ref_dir / "7 Backing_Vocals.wav",
        "voc8": ref_dir / "8 Vocals.wav",
        "voc9": ref_dir / "9 Vocals.wav",
        "guitar2": ref_dir / "10 Guitar.wav",
    }
    sr, full, _ = base.read_wav(files["full"])
    length = len(full)
    loaded = {key: pad_or_trim(base.read_wav(path)[1], length) for key, path in files.items()}
    vocal_group = loaded["voc8"] + loaded["voc9"] + loaded["backing"]
    music = sum((loaded[key] for key in ("fx", "synth", "keyboard", "guitar1", "bass", "drums", "guitar2")), np.zeros_like(full))
    payload: dict[str, Any] = {"source_zip": "/Users/hantaeheuk/Downloads/마루노우치.zip"}
    for label, y in {"full": full, "vocal_group": vocal_group, "voc8": loaded["voc8"], "voc9": loaded["voc9"], "backing": loaded["backing"], "music_sum": music}.items():
        side_db, corr = side_mid_db(y)
        payload[label] = {
            "active_rms_db": round(base.active_rms_db(y), 2),
            "rms_db": round(float(amp_to_db(rms(y))), 2),
            "peak_db": round(float(amp_to_db(np.max(np.abs(y)))), 2),
            "side_mid_db": round(side_db, 2),
            "stereo_corr": round(corr, 4),
        }
    payload["ratios"] = {
        "vocal_group_vs_full_active_db": round(payload["vocal_group"]["active_rms_db"] - payload["full"]["active_rms_db"], 2),
        "music_vs_full_active_db": round(payload["music_sum"]["active_rms_db"] - payload["full"]["active_rms_db"], 2),
        "voc9_vs_voc8_active_db": round(payload["voc9"]["active_rms_db"] - payload["voc8"]["active_rms_db"], 2),
        "backing_vs_voc8_active_db": round(payload["backing"]["active_rms_db"] - payload["voc8"]["active_rms_db"], 2),
    }
    write_json(base.REPORTS / REFERENCE_JSON, payload)
    return payload


def write_processed(paths: dict[str, Path]) -> tuple[dict[str, Path], int, float, dict[str, float]]:
    processed, sr, duration, vocal_balance = v4.write_processed(paths)
    length = int(round(duration * sr))
    rows: list[dict[str, Any]] = []

    lead_path = processed["lead_vocal"]
    lead_before = read_processed(lead_path, sr, length)
    lead_locked, lead_rows = vocal_window_lock(lead_before, sr, target_db=-17.9, max_up_db=8.3, max_down_db=-1.2, smooth_s=0.58)
    lead_locked = base.compressor(lead_locked, sr, threshold_db=-22.6, ratio=1.85, attack_ms=7.0, release_ms=105.0, makeup_db=1.25)
    lead_locked = base.match_active_rms(lead_locked, -17.9, max_gain_db=5.2)
    lead_locked = base.peak_cap(lead_locked.astype(np.float32), -1.75)
    base.write_wav(lead_path, sr, lead_locked)
    rows.append({"stem": "lead_vocal", "before_active_rms_db": round(base.active_rms_db(lead_before), 2), "after_active_rms_db": round(base.active_rms_db(lead_locked), 2), "target_db": -17.9})

    female_path = processed["female_vocal"]
    female_before = read_processed(female_path, sr, length)
    female_wide = make_female_more_audible(female_before, lead_locked, sr)
    female_locked, female_rows = vocal_window_lock(female_wide, sr, target_db=base.active_rms_db(lead_locked) - 0.15, max_up_db=7.0, max_down_db=-0.9, smooth_s=0.60)
    female_locked = base.compressor(female_locked, sr, threshold_db=-24.0, ratio=1.45, attack_ms=10.0, release_ms=115.0, makeup_db=0.9)
    female_locked = base.match_active_rms(female_locked, base.active_rms_db(lead_locked) - 0.15, max_gain_db=6.2)
    female_locked = base.peak_cap(female_locked.astype(np.float32), -1.75)
    base.write_wav(female_path, sr, female_locked)
    rows.append({"stem": "female_vocal", "before_active_rms_db": round(base.active_rms_db(female_before), 2), "after_active_rms_db": round(base.active_rms_db(female_locked), 2), "target_db": round(base.active_rms_db(lead_locked) - 0.15, 2)})

    for key in sorted(MUSIC_KEYS):
        path = processed.get(key)
        if not path or not path.exists():
            continue
        before = read_processed(path, sr, length)
        after = apply_music_vocal_pocket(before, lead_locked, sr, key)
        base.write_wav(path, sr, after)
        rows.append({"stem": key, "before_active_rms_db": round(base.active_rms_db(before), 2), "after_active_rms_db": round(base.active_rms_db(after), 2), "target_db": "vocal_pocket"})

    for key, gain_db in {"backing_vocals": 3.0, "vocal_reverb": 0.35, "vocal_delay": 0.55}.items():
        path = processed.get(key)
        if not path or not path.exists():
            continue
        before = read_processed(path, sr, length)
        after = before * float(db_to_amp(gain_db))
        after = base.peak_cap(after.astype(np.float32), -3.2 if key == "backing_vocals" else -5.0)
        base.write_wav(path, sr, after)
        rows.append({"stem": key, "before_active_rms_db": round(base.active_rms_db(before), 2), "after_active_rms_db": round(base.active_rms_db(after), 2), "target_db": f"{gain_db:+.2f}dB print lift"})

    front_report = vocal_front_autocalibration(processed, sr, length, rows)
    lead_locked = read_processed(processed["lead_vocal"], sr, length)
    female_locked = read_processed(processed["female_vocal"], sr, length)

    vocal_solo = (
        lead_locked
        + female_locked
        + read_processed(processed["backing_vocals"], sr, length) * float(db_to_amp(-0.8))
        + read_processed(processed["vocal_reverb"], sr, length)
        + read_processed(processed["vocal_delay"], sr, length)
    )
    vocal_solo = base.peak_cap(vocal_solo.astype(np.float32), -1.2)
    base.write_wav(base.VOCAL_SOLO, sr, vocal_solo)

    vocal_group = approximate_group(processed, VOCAL_KEYS, sr, length)
    mix_approx = v2.approximate_mix(processed, sr, length)
    side_db, corr = side_mid_db(female_locked)
    vocal_balance.update(
        {
            "lead_active_rms_db": round(base.active_rms_db(lead_locked), 2),
            "female_layer_active_rms_db": round(base.active_rms_db(female_locked), 2),
            "female_vs_lead_db": round(base.active_rms_db(female_locked) - base.active_rms_db(lead_locked), 2),
            "female_side_mid_db": round(side_db, 2),
            "female_stereo_corr": round(corr, 4),
            "vocal_group_vs_approx_mix_active_db": round(base.active_rms_db(vocal_group) - base.active_rms_db(mix_approx), 2),
            "vocal_front_autocalibration_before_db": front_report["before_vocal_group_vs_approx_mix_active_db"],
            "vocal_front_autocalibration_after_db": front_report["after_vocal_group_vs_approx_mix_active_db"],
            "vocal_front_autocalibration_target_db": front_report["target_vocal_group_vs_approx_mix_active_db"],
            "vocal_front_autocalibration_vocal_gain_db": front_report["vocal_group_gain_db"],
            "vocal_front_autocalibration_female_extra_db": front_report["female_extra_gain_db"],
            "vocal_front_autocalibration_music_trim_db": front_report["music_group_trim_db"],
            "vocal_lock_target": "Marunouchi reference vocal-forward target; v05 was about -10 dB vocal group vs final, so v06 raises vocal group and ducks music.",
        }
    )
    write_json(
        base.REPORTS / VOCAL_LOCK_JSON,
        {
            "summary": vocal_balance,
            "stem_changes": rows,
            "lead_window_lock": lead_rows,
            "female_window_lock": female_rows,
        },
    )
    write_csv(base.REPORTS / VOCAL_LOCK_CSV, rows)
    return processed, sr, duration, vocal_balance


def phrase_premaster_path() -> Path:
    return base.RENDERS / PHRASE_PREMASTER_NAME


def plateau_premaster_path() -> Path:
    return base.RENDERS / PLATEAU_PREMASTER_NAME


def floor_premaster_path() -> Path:
    return base.RENDERS / FLOOR_PREMASTER_NAME


def apply_premaster_floor_lock(input_path: Path, output_path: Path, floor_margin_db: float = 2.35) -> dict[str, Any]:
    sr, y, _ = base.read_wav(input_path)
    rows = v4.window_rows(y, sr, 1.5)
    active_levels = np.array([row["rms_db"] for row in rows if row["start_s"] >= 6.0 and row["end_s"] <= 137.0], dtype=np.float32)
    median = float(np.median(active_levels)) if len(active_levels) else -18.0
    floor_target = median - floor_margin_db
    window_gains = np.zeros(len(rows), dtype=np.float32)
    out_rows: list[dict[str, Any]] = []
    for i, row in enumerate(rows):
        start = float(row["start_s"])
        end = float(row["end_s"])
        rms_db = float(row["rms_db"])
        label = v4.range_label(start, end) or ""
        if start < 6.0 or end > 137.0:
            gain = 0.0
        elif rms_db < floor_target:
            gain = min((floor_target - rms_db) * 0.96, 4.4)
        else:
            gain = 0.0
        if abs(gain) < 0.16:
            gain = 0.0
        window_gains[i] = gain
        out_rows.append(
            {
                **row,
                "forced_window": label,
                "active_median_rms_db": round(median, 2),
                "floor_target_rms_db": round(floor_target, 2),
                "applied_floor_gain_db": round(float(gain), 2),
            }
        )

    curve = v4.smooth_curve_from_window_gains(rows, window_gains, len(y), sr, smooth_s=0.42, min_db=0.0, max_db=4.4)
    locked = y * db_to_amp(curve)[:, None]
    locked = base.soft_clip(locked.astype(np.float32), ceiling=0.955)
    locked = base.peak_cap(locked.astype(np.float32), -1.35)
    base.write_wav(output_path, sr, locked)
    after_rows = v4.window_rows(locked, sr, 1.5)
    for i, row in enumerate(out_rows):
        if i < len(after_rows):
            row["post_floor_rms_db"] = after_rows[i]["rms_db"]
            row["floor_improvement_db"] = round(after_rows[i]["rms_db"] - row["rms_db"], 2)
    report = {
        "input": base.rel(input_path),
        "output": base.rel(output_path),
        "window_s": 1.5,
        "active_median_rms_db": round(median, 2),
        "floor_target_rms_db": round(floor_target, 2),
        "max_upward_floor_gain_db": round(float(np.max(window_gains)), 2),
        "mean_abs_upward_floor_gain_db": round(float(np.mean(window_gains[window_gains > 0])) if np.any(window_gains > 0) else 0.0, 2),
        "method": "Upward-only premaster floor lock after plateau leveling, added because user reported perceived vocal/sound dropouts in short windows.",
        "windows": out_rows,
    }
    write_json(base.REPORTS / FLOOR_LOCK_REPORT_JSON, report)
    write_csv(base.REPORTS / FLOOR_LOCK_REPORT_CSV, out_rows)
    return report


def final_master() -> None:
    v4.premaster_bus_leveling(base.REAPER_PRINT, phrase_premaster_path())
    v5.apply_plateau_leveling(phrase_premaster_path(), plateau_premaster_path(), target_rms_db=-19.6)
    apply_premaster_floor_lock(plateau_premaster_path(), floor_premaster_path(), floor_margin_db=2.35)
    filter_graph = (
        "highpass=f=24,"
        "equalizer=f=230:t=q:w=0.95:g=-0.25,"
        "equalizer=f=1850:t=q:w=1.05:g=-0.22,"
        "equalizer=f=3200:t=q:w=0.95:g=0.20,"
        "equalizer=f=7600:t=q:w=0.85:g=-0.10,"
        "volume=3.1dB,"
        "alimiter=limit=0.84:attack=2:release=115:level=false"
    )
    subprocess.run(
        [
            base.FFMPEG,
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(floor_premaster_path()),
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
    subprocess.run(
        [base.FFMPEG, "-y", "-hide_banner", "-loglevel", "error", "-i", str(base.FINAL_WAV), "-c:a", "libmp3lame", "-b:a", "320k", str(base.FINAL_MP3)],
        check=True,
    )


def write_consistency_reports(paths: dict[str, Path]) -> dict[str, Any]:
    compare_paths = {
        "source_full_mix": paths["full_reference"],
        "v05_final_rejected": ROOT / "renders/mwolla_v05_phrase_plateau_master/mwolla_v05_PHRASE_PLATEAU_MASTER.wav",
        "v06_vocal_locked_premaster": phrase_premaster_path(),
        "v06_plateau_premaster": plateau_premaster_path(),
        "v06_floor_locked_premaster": floor_premaster_path(),
        "v06_final": base.FINAL_WAV,
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
    lines = ["# v06 Vocal-Locked Loudness Consistency Report", ""]
    for label, values in summary.items():
        lines.extend([f"## {label}", "", "| window | outside +/-3 dB | max + | max - | mean abs |", "| ---: | ---: | ---: | ---: | ---: |"])
        for window_s, row in values.items():
            lines.append(f"| {window_s}s | {row['outside_plus_minus_3db_count']} | {row['max_positive_deviation_db']} | {row['max_negative_deviation_db']} | {row['mean_abs_deviation_db']} |")
        lines.append("")
    (base.REPORTS / WINDOW_REPORT_MD).write_text("\n".join(lines) + "\n", encoding="utf-8")
    return summary


def write_reports(paths: dict[str, Path], processed: dict[str, Path], vocal_balance: dict[str, float], gate: dict[str, Any]) -> None:
    reference = analyze_marunouchi_reference()
    consistency = write_consistency_reports(paths)
    rows = [
        base.audio_metrics(paths["full_reference"], "source_full_reference"),
        base.audio_metrics(ROOT / "renders/mwolla_v05_phrase_plateau_master/mwolla_v05_PHRASE_PLATEAU_MASTER.wav", "v05_rejected_final"),
        base.audio_metrics(processed["lead_vocal"], "v06_processed_lead_vocal_locked"),
        base.audio_metrics(processed["female_vocal"], "v06_processed_female_audible_wide"),
        base.audio_metrics(base.VOCAL_SOLO, "v06_vocal_solo"),
        base.audio_metrics(base.REAPER_PRINT, "v06_reaper_print"),
        base.audio_metrics(phrase_premaster_path(), "v06_vocal_locked_premaster"),
        base.audio_metrics(plateau_premaster_path(), "v06_plateau_premaster"),
        base.audio_metrics(floor_premaster_path(), "v06_floor_locked_premaster"),
        base.audio_metrics(base.FINAL_WAV, "v06_final_master_wav"),
        base.audio_metrics(base.FINAL_MP3, "v06_final_master_mp3"),
    ]
    write_csv(base.REPORTS / "qc_metrics.csv", rows)
    write_json(base.REPORTS / "qc_metrics.json", rows)
    final = rows[-2]
    mp3 = rows[-1]
    qc_passed = bool(gate.get("passed")) and (final.get("true_peak_dbfs") or 99) <= -1.0 and (mp3.get("true_peak_dbfs") or 99) <= -1.0
    qc = {
        "passed": qc_passed,
        "status": "qc_passed_user_review_required" if qc_passed else "blocked",
        "delivery_ready": False,
        "user_feedback_addressed": [
            "v05 vocal group was measured about -9.94 dB below final active RMS; v06 raises/locks lead and female support.",
            "female layer is rebuilt as audible wide side support instead of hidden noise-mask only.",
            "music stems receive stronger vocal-band pockets and light level trims.",
        ],
        "marunouchi_reference_ratios": reference["ratios"],
        "gate": gate,
        "vocal_balance": vocal_balance,
        "final_lufs": final.get("integrated_lufs"),
        "final_true_peak_dbfs": final.get("true_peak_dbfs"),
        "mp3_true_peak_dbfs": mp3.get("true_peak_dbfs"),
        "v06_final_phrase_summary": consistency.get("v06_final", {}),
    }
    write_json(base.REPORTS / "qc_summary.json", qc)
    notes = [
        f"# {base.REPORT_TITLE}",
        "",
        "## User Rejection Addressed",
        "",
        "- User rejected v05: vocal still moved small/large, female pan not audible, and vocal itself was buried.",
        "- Marunouchi reference analysis shows vocal group active RMS is `+0.56 dB` versus full mix active RMS.",
        "- v05 measured vocal group was about `-9.94 dB` versus the final active RMS, so v06 intentionally moves vocals forward.",
        "",
        "## Deliverables",
        "",
        f"- Final WAV: `{base.rel(base.FINAL_WAV)}`",
        f"- Final MP3: `{base.rel(base.FINAL_MP3)}`",
        f"- REAPER project: `{base.rel(base.RPP)}`",
        f"- Vocal solo check: `{base.rel(base.VOCAL_SOLO)}`",
        f"- A/B preview: `{base.rel(base.AB_PREVIEW_MP3)}`",
        f"- Deliverable ZIP: `{base.rel(base.DELIVERABLE_ZIP)}`",
        "",
        "## Vocal Lock Result",
        "",
        f"- Lead active RMS: `{vocal_balance.get('lead_active_rms_db')}` dB",
        f"- Female active RMS: `{vocal_balance.get('female_layer_active_rms_db')}` dB",
        f"- Female vs lead: `{vocal_balance.get('female_vs_lead_db')}` dB",
        f"- Female side/mid: `{vocal_balance.get('female_side_mid_db')}` dB",
        f"- Vocal group vs approximate mix active: `{vocal_balance.get('vocal_group_vs_approx_mix_active_db')}` dB",
        f"- Vocal front autocalibration: `{vocal_balance.get('vocal_front_autocalibration_before_db')}` -> `{vocal_balance.get('vocal_front_autocalibration_after_db')}` dB",
        "",
        "## QC",
        "",
        f"- Final WAV loudness: `{final.get('integrated_lufs')}` LUFS / TP `{final.get('true_peak_dbfs')}` dBFS",
        f"- Final MP3 TP: `{mp3.get('true_peak_dbfs')}` dBFS",
        f"- Vocal chain gate passed: `{gate.get('passed')}`",
        "",
        "## Evidence",
        "",
        f"- Marunouchi reference: `{base.rel(base.REPORTS / REFERENCE_JSON)}`",
        f"- Vocal lock report: `{base.rel(base.REPORTS / VOCAL_LOCK_JSON)}`",
        f"- Vocal front autocalibration: `{base.rel(base.REPORTS / VOCAL_FRONT_REPORT_JSON)}`",
        f"- Premaster floor lock: `{base.rel(base.REPORTS / FLOOR_LOCK_REPORT_JSON)}`",
        f"- Consistency report: `{base.rel(base.REPORTS / WINDOW_REPORT_JSON)}`",
        f"- Problem window report: `{base.rel(base.REPORTS / v4.PROBLEM_REPORT_JSON)}`",
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
        phrase_premaster_path(),
        plateau_premaster_path(),
        floor_premaster_path(),
        base.RPP,
        base.BUILD_LUA,
        base.RENDER_LUA,
        base.TRACE_JSON,
        base.TRACE_MD,
        base.REPORTS / "vocal_chain_gate.json",
        base.REPORTS / "qc_metrics.json",
        base.REPORTS / "qc_metrics.csv",
        base.REPORTS / "qc_summary.json",
        base.REPORTS / "source_selection.json",
        base.REPORTS / base.REPORT_FILENAME,
        base.REPORTS / REFERENCE_JSON,
        base.REPORTS / VOCAL_LOCK_JSON,
        base.REPORTS / VOCAL_LOCK_CSV,
        base.REPORTS / VOCAL_FRONT_REPORT_JSON,
        base.REPORTS / VOCAL_FRONT_REPORT_CSV,
        base.REPORTS / FLOOR_LOCK_REPORT_JSON,
        base.REPORTS / FLOOR_LOCK_REPORT_CSV,
        base.REPORTS / WINDOW_REPORT_JSON,
        base.REPORTS / WINDOW_REPORT_CSV,
        base.REPORTS / WINDOW_REPORT_MD,
        base.REPORTS / v4.PROBLEM_REPORT_JSON,
        base.REPORTS / v4.PROBLEM_REPORT_MD,
        base.REPORTS / v4.VOCAL_CURVE_JSON,
        base.REPORTS / v4.VOCAL_CURVE_CSV,
        base.REPORTS / v4.MUSIC_CURVE_JSON,
        base.REPORTS / v4.MUSIC_CURVE_CSV,
        base.REPORTS / v4.PHRASE_BUS_REPORT_JSON,
        base.REPORTS / v4.PHRASE_BUS_REPORT_CSV,
        base.REPORTS / v5.PLATEAU_REPORT_JSON,
        base.REPORTS / v5.PLATEAU_REPORT_CSV,
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

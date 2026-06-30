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
V06_SCRIPT = ROOT / "tools" / "mwolla_v06_vocal_locked_reference_master.py"
SLUG = "mwolla_v07_suno_dynamic_eq_locked_master"

spec = importlib.util.spec_from_file_location("mwolla_v06_vocal_locked_reference_master", V06_SCRIPT)
if spec is None or spec.loader is None:
    raise RuntimeError(f"Could not load v06 script: {V06_SCRIPT}")
v6 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v6)
v5 = v6.v5
v4 = v6.v4
v3 = v6.v3
v2 = v6.v2
v1 = v6.v1
base = v6.base


DYNAMIC_EQ_JSON = "suno_stem_dynamic_eq_music_bus_report.json"
DYNAMIC_EQ_CSV = "suno_stem_dynamic_eq_music_bus_report.csv"
MUSIC_CONSTANT_JSON = "suno_music_constant_level_report.json"
MUSIC_CONSTANT_CSV = "suno_music_constant_level_report.csv"
WINDOW_REPORT_JSON = "section_loudness_consistency_1p5s_3s_6s_report.json"
WINDOW_REPORT_CSV = "section_loudness_consistency_1p5s_3s_6s_report.csv"
WINDOW_REPORT_MD = "section_loudness_consistency_1p5s_3s_6s_report.md"
PREMASTER_NAME = "mwolla_v07_SUNO_DYNAMIC_EQ_PREMASTER_24-48.wav"
PLATEAU_NAME = "mwolla_v07_SUNO_DYNAMIC_EQ_PLATEAU_PREMASTER_24-48.wav"
FLOOR_NAME = "mwolla_v07_SUNO_DYNAMIC_EQ_FLOOR_PREMASTER_24-48.wav"

MUSIC_KEYS = {"woodwinds", "brass", "fx", "synth", "strings", "percussion", "keyboard", "guitar", "bass", "drums"}
VOCAL_KEYS = {"lead_vocal", "female_vocal", "backing_vocals", "vocal_reverb", "vocal_delay"}


def configure_base() -> None:
    v6.configure_base()
    base.SLUG = SLUG
    base.WORK = ROOT / "audio_work" / SLUG
    base.SOURCE = base.WORK / "source_stems"
    base.PROCESSED = base.WORK / "processed_stems"
    base.REAPER_DIR = ROOT / "reaper" / SLUG
    base.RENDERS = ROOT / "renders" / SLUG
    base.REPORTS = ROOT / "reports" / SLUG

    base.RPP = base.REAPER_DIR / "mwolla_v07_SUNO_DYNAMIC_EQ_LOCKED_MASTER.rpp"
    base.BUILD_LUA = base.REAPER_DIR / "build_mwolla_v07_suno_dynamic_eq_locked_master.lua"
    base.RUN_BUILD_LUA = base.REAPER_DIR / "run_build_mwolla_v07_suno_dynamic_eq_locked_master.lua"
    base.RENDER_LUA = base.REAPER_DIR / "render_mwolla_v07_suno_dynamic_eq_locked_master.lua"
    base.RUN_RENDER_LUA = base.REAPER_DIR / "run_render_mwolla_v07_suno_dynamic_eq_locked_master.lua"
    base.TRACE_JSON = base.REPORTS / "actual_reaper_plugin_trace.json"
    base.TRACE_MD = base.REPORTS / "actual_reaper_plugin_trace.md"

    base.REAPER_PRINT = base.RENDERS / "mwolla_v07_REAPERPRINT_24-48.wav"
    base.FINAL_WAV = base.RENDERS / "mwolla_v07_SUNO_DYNAMIC_EQ_LOCKED_MASTER.wav"
    base.FINAL_MP3 = base.RENDERS / "mwolla_v07_SUNO_DYNAMIC_EQ_LOCKED_MASTER_320k.mp3"
    base.VOCAL_SOLO = base.RENDERS / "mwolla_v07_VOCAL_SOLO_suno_dynamic_eq.wav"
    base.AB_PREVIEW_MP3 = base.RENDERS / "mwolla_v07_AB_original_suno_to_dynamic_eq_master_320k.mp3"
    base.DELIVERABLE_ZIP = base.RENDERS / "mwolla_v07_SUNO_DYNAMIC_EQ_LOCKED_MASTER_DELIVERABLE.zip"

    base.FEMALE_TARGET_DELTA_DB = -0.9
    base.FEMALE_LAYER_FILENAME = "female_vocal_audible_suno_dynamic_eq_wide.wav"
    base.FEMALE_TRACK_NAME = "13 Female audible panned support -0.9dB"
    base.REPORT_FILENAME = "mwolla_v07_suno_dynamic_eq_locked_master_report.md"
    base.REPORT_TITLE = "Mwolla v07 Suno Dynamic EQ Locked Master Report"
    base.PROJECT_NOTES = (
        "mwolla v07: user correction pass. Overall sound and music size reference the original Suno full/stem export. "
        "Music level consistency is handled before mastering, and vocal clarity is handled with printed dynamic EQ "
        "sidechain pockets on the music stems rather than broad music-volume collapse."
    )


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


def apply_dynamic_eq_music_pocket(y: np.ndarray, lead: np.ndarray, vocal_group: np.ndarray, sr: int, role: str) -> tuple[np.ndarray, list[dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    out = y.astype(np.float32)
    moves: list[tuple[str, float, float, float, float, float]] = [
        ("low_mid_body_space", 260, 760, 0.65, 58.0, 155.0),
        ("vocal_presence_pocket", 1500, 5200, 2.15, 48.0, 135.0),
        ("sibilance_air_guard", 6200, 9700, 0.95, 55.0, 70.0),
    ]
    if role in {"bass", "drums"}:
        moves = [
            ("low_mid_body_space", 300, 820, 0.35, 60.0, 130.0),
            ("vocal_presence_pocket", 1900, 5200, 0.95, 54.0, 110.0),
            ("sibilance_air_guard", 6500, 9500, 0.55, 60.0, 65.0),
        ]
    elif role in {"fx", "percussion"}:
        moves = [
            ("vocal_presence_pocket", 1800, 6200, 1.35, 52.0, 120.0),
            ("sibilance_air_guard", 6500, 11000, 0.9, 56.0, 70.0),
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
                "note": "printed dynamic EQ sidechain pocket, not static volume-only automation",
            }
        )
    return base.peak_cap(out.astype(np.float32), -1.7), rows


def window_rows(y: np.ndarray, sr: int, window_s: float) -> list[dict[str, Any]]:
    mono = np.mean(y, axis=1).astype(np.float32)
    frame = int(round(sr * window_s))
    rows: list[dict[str, Any]] = []
    for start in range(0, len(mono), frame):
        end = min(len(mono), start + frame)
        if end - start < int(sr * 0.5):
            break
        chunk = mono[start:end]
        rows.append({"start_s": round(start / sr, 3), "end_s": round(end / sr, 3), "rms_db": round(float(amp_to_db(np.sqrt(np.mean(chunk * chunk) + 1e-12))), 2)})
    return rows


def apply_music_constant_curve(processed: dict[str, Path], paths: dict[str, Path], sr: int, length: int) -> dict[str, Any]:
    source_sr, source, _ = base.read_wav(paths["full_reference"])
    if source_sr != sr:
        raise RuntimeError("Source full reference sample-rate mismatch")
    source = v6.pad_or_trim(source, length)
    music = group_mix(processed, MUSIC_KEYS, sr, length)
    source_rows = window_rows(source, sr, 3.0)
    music_rows = window_rows(music, sr, 3.0)
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
            target = music_median + (float(source_ref) - source_median) * 0.28
            delta = target - float(row["rms_db"])
            gain = float(np.clip(delta * 0.62, -1.2, 1.7))
            if abs(gain) < 0.18:
                gain = 0.0
        gains[i] = gain
        rows.append({**row, "source_reference_rms_db": source_rows[i]["rms_db"] if i < len(source_rows) else None, "applied_music_constant_gain_db": round(gain, 2)})
    centers = np.array([(row["start_s"] + row["end_s"]) * 0.5 for row in music_rows], dtype=np.float32)
    times = np.arange(length, dtype=np.float32) / float(sr)
    curve = np.interp(times, centers, gains, left=gains[0], right=gains[-1]).astype(np.float32) if len(centers) > 1 else np.zeros(length, dtype=np.float32)
    smooth = max(1, int(sr * 1.05))
    if smooth > 1:
        kernel = np.hanning(smooth * 2 + 1).astype(np.float32)
        kernel /= np.sum(kernel)
        curve = base.signal.fftconvolve(curve, kernel, mode="same").astype(np.float32)
    curve = np.clip(curve, -1.2, 1.7)
    for key in sorted(MUSIC_KEYS):
        path = processed.get(key)
        if not path or not path.exists():
            continue
        y = read_processed(path, sr, length)
        adjusted = y * db_to_amp(curve)[:, None]
        adjusted = base.peak_cap(adjusted.astype(np.float32), -1.7)
        base.write_wav(path, sr, adjusted)
    after_music = group_mix(processed, MUSIC_KEYS, sr, length)
    after_rows = window_rows(after_music, sr, 3.0)
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
        "method": "Music bus level is kept consistent relative to the original Suno full mix; vocal room is carved with dynamic EQ, not broad music drops.",
        "rows": rows,
    }
    write_json(base.REPORTS / MUSIC_CONSTANT_JSON, payload)
    write_csv(base.REPORTS / MUSIC_CONSTANT_CSV, rows)
    return payload


def write_processed(paths: dict[str, Path]) -> tuple[dict[str, Path], int, float, dict[str, float]]:
    processed, sr, duration, vocal_balance = v4.write_processed(paths)
    length = int(round(duration * sr))

    lead_path = processed["lead_vocal"]
    female_path = processed["female_vocal"]
    lead_before = read_processed(lead_path, sr, length)
    lead, lead_rows = v6.vocal_window_lock(lead_before, sr, target_db=-18.35, max_up_db=7.2, max_down_db=-1.0, smooth_s=0.58)
    lead = base.compressor(lead, sr, threshold_db=-22.4, ratio=1.65, attack_ms=8.0, release_ms=105.0, makeup_db=0.85)
    lead = base.match_active_rms(lead, -18.35, max_gain_db=4.5)
    lead = base.peak_cap(lead.astype(np.float32), -1.8)
    base.write_wav(lead_path, sr, lead)

    female_before = read_processed(female_path, sr, length)
    female = v6.make_female_more_audible(female_before, lead, sr)
    female, female_rows = v6.vocal_window_lock(female, sr, target_db=base.active_rms_db(lead) - 0.9, max_up_db=6.0, max_down_db=-0.8, smooth_s=0.62)
    female = base.match_active_rms(female, base.active_rms_db(lead) - 0.9, max_gain_db=5.5)
    female = base.peak_cap(female.astype(np.float32), -1.8)
    base.write_wav(female_path, sr, female)

    vocal_group = group_mix(processed, VOCAL_KEYS, sr, length)
    dynamic_rows: list[dict[str, Any]] = []
    for key in sorted(MUSIC_KEYS):
        path = processed.get(key)
        if not path or not path.exists():
            continue
        before = read_processed(path, sr, length)
        after, rows = apply_dynamic_eq_music_pocket(before, lead, vocal_group, sr, key)
        base.write_wav(path, sr, after)
        dynamic_rows.extend(rows)
    write_json(base.REPORTS / DYNAMIC_EQ_JSON, {"method": "Printed dynamic EQ sidechain pockets on music stems using lead/vocal group trigger.", "rows": dynamic_rows})
    write_csv(base.REPORTS / DYNAMIC_EQ_CSV, dynamic_rows)
    music_report = apply_music_constant_curve(processed, paths, sr, length)

    vocal_group_after = group_mix(processed, VOCAL_KEYS, sr, length)
    music_after = group_mix(processed, MUSIC_KEYS, sr, length)
    vocal_solo = base.peak_cap(vocal_group_after.astype(np.float32), -1.2)
    base.write_wav(base.VOCAL_SOLO, sr, vocal_solo)

    vocal_balance.update(
        {
            "lead_active_rms_db": round(base.active_rms_db(read_processed(lead_path, sr, length)), 2),
            "female_layer_active_rms_db": round(base.active_rms_db(read_processed(female_path, sr, length)), 2),
            "female_vs_lead_db": round(base.active_rms_db(read_processed(female_path, sr, length)) - base.active_rms_db(read_processed(lead_path, sr, length)), 2),
            "vocal_group_vs_music_active_db": round(base.active_rms_db(vocal_group_after) - base.active_rms_db(music_after), 2),
            "dynamic_eq_music_stem_band_count": len(dynamic_rows),
            "music_constant_max_gain_db": music_report["max_gain_db"],
            "music_constant_min_gain_db": music_report["min_gain_db"],
            "reference_priority": "original Suno full/stem export, not Marunouchi overall tone",
        }
    )
    write_json(
        base.REPORTS / "suno_vocal_lock_report.json",
        {
            "summary": vocal_balance,
            "lead_window_lock": lead_rows,
            "female_window_lock": female_rows,
        },
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
    v5.apply_plateau_leveling(premaster_path(), plateau_path(), target_rms_db=-19.85)
    v6.apply_premaster_floor_lock(plateau_path(), floor_path(), floor_margin_db=2.42)
    filter_graph = (
        "highpass=f=24,"
        "equalizer=f=230:t=q:w=0.95:g=-0.12,"
        "equalizer=f=3150:t=q:w=0.95:g=0.08,"
        "equalizer=f=7600:t=q:w=0.85:g=-0.08,"
        "volume=3.35dB,"
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
        "v07_dynamic_eq_premaster": premaster_path(),
        "v07_floor_premaster": floor_path(),
        "v07_final": base.FINAL_WAV,
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
    lines = ["# v07 Suno Dynamic EQ Loudness Consistency Report", ""]
    for label, values in summary.items():
        lines.extend([f"## {label}", "", "| window | outside +/-3 dB | max + | max - | mean abs |", "| ---: | ---: | ---: | ---: | ---: |"])
        for window_s, row in values.items():
            lines.append(f"| {window_s}s | {row['outside_plus_minus_3db_count']} | {row['max_positive_deviation_db']} | {row['max_negative_deviation_db']} | {row['mean_abs_deviation_db']} |")
        lines.append("")
    (base.REPORTS / WINDOW_REPORT_MD).write_text("\n".join(lines) + "\n", encoding="utf-8")
    return summary


def write_reports(paths: dict[str, Path], processed: dict[str, Path], vocal_balance: dict[str, float], gate: dict[str, Any]) -> None:
    consistency = write_consistency_reports(paths)
    rows = [
        base.audio_metrics(paths["full_reference"], "source_suno_full_mix"),
        base.audio_metrics(processed["lead_vocal"], "processed_lead_vocal_dynamic_locked"),
        base.audio_metrics(processed["female_vocal"], "processed_female_vocal_audible_pan"),
        base.audio_metrics(base.VOCAL_SOLO, "processed_vocal_solo"),
        base.audio_metrics(base.REAPER_PRINT, "v07_reaper_print"),
        base.audio_metrics(premaster_path(), "v07_dynamic_eq_premaster"),
        base.audio_metrics(plateau_path(), "v07_plateau_premaster"),
        base.audio_metrics(floor_path(), "v07_floor_premaster"),
        base.audio_metrics(base.FINAL_WAV, "v07_final_master_wav"),
        base.audio_metrics(base.FINAL_MP3, "v07_final_master_mp3"),
    ]
    write_json(base.REPORTS / "qc_metrics.json", rows)
    write_csv(base.REPORTS / "qc_metrics.csv", rows)
    source = rows[0]
    final = rows[-2]
    mp3 = rows[-1]
    qc_passed = bool(gate.get("passed")) and (final.get("true_peak_dbfs") or 99) <= -1.0 and (mp3.get("true_peak_dbfs") or 99) <= -1.0
    qc = {
        "passed": qc_passed,
        "status": "qc_passed_user_review_required" if qc_passed else "blocked",
        "delivery_ready": False,
        "source_lufs": source.get("integrated_lufs"),
        "final_lufs": final.get("integrated_lufs"),
        "final_true_peak_dbfs": final.get("true_peak_dbfs"),
        "mp3_true_peak_dbfs": mp3.get("true_peak_dbfs"),
        "vocal_balance": vocal_balance,
        "v07_final_phrase_summary": consistency.get("v07_final", {}),
        "correction": "Overall sound references original Suno full/stem export; music consistency uses a music-bus constant curve; vocal masking uses printed dynamic EQ sidechain pockets.",
        "gate": gate,
    }
    write_json(base.REPORTS / "qc_summary.json", qc)
    notes = [
        f"# {base.REPORT_TITLE}",
        "",
        "## Correction",
        "",
        "- User clarified that the overall sound must reference the original Suno basic full/stem export.",
        "- Music level consistency is handled on the music bus before mastering.",
        "- Vocal clarity is handled with printed dynamic EQ sidechain pockets on music stems, not only broad gain automation.",
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
        f"- Vocal chain gate passed: `{gate.get('passed')}`",
        f"- 1.5s final outside +/-3dB: `{qc['v07_final_phrase_summary'].get('1.5', {}).get('outside_plus_minus_3db_count')}`",
        "",
        "## Evidence",
        "",
        f"- Dynamic EQ music report: `{base.rel(base.REPORTS / DYNAMIC_EQ_JSON)}`",
        f"- Music constant report: `{base.rel(base.REPORTS / MUSIC_CONSTANT_JSON)}`",
        f"- Consistency report: `{base.rel(base.REPORTS / WINDOW_REPORT_JSON)}`",
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
        base.REPORTS / DYNAMIC_EQ_JSON,
        base.REPORTS / DYNAMIC_EQ_CSV,
        base.REPORTS / MUSIC_CONSTANT_JSON,
        base.REPORTS / MUSIC_CONSTANT_CSV,
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

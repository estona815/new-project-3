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
SLUG = "mwolla_v04_phrase_level_consistent_master"


spec = importlib.util.spec_from_file_location("mwolla_v03_premaster_consistent_master", V03_SCRIPT)
if spec is None or spec.loader is None:
    raise RuntimeError(f"Could not load v03 script: {V03_SCRIPT}")
v3 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v3)
base = v3.base


PHRASE_PREMASTER_NAME = "mwolla_v04_PHRASE_LEVELED_PREMASTER_24-48.wav"
PHRASE_BUS_REPORT_JSON = "premaster_bus_leveling_report.json"
PHRASE_BUS_REPORT_CSV = "premaster_bus_leveling_report.csv"
PROBLEM_REPORT_JSON = "problem_window_cause_classification_report.json"
PROBLEM_REPORT_MD = "problem_window_cause_classification_report.md"
VOCAL_CURVE_JSON = "vocal_riding_curve_report.json"
VOCAL_CURVE_CSV = "vocal_riding_curve_report.csv"
MUSIC_CURVE_JSON = "music_stem_riding_curve_report.json"
MUSIC_CURVE_CSV = "music_stem_riding_curve_report.csv"
WINDOW_REPORT_JSON = "section_loudness_consistency_1p5s_3s_6s_report.json"
WINDOW_REPORT_CSV = "section_loudness_consistency_1p5s_3s_6s_report.csv"
WINDOW_REPORT_MD = "section_loudness_consistency_1p5s_3s_6s_report.md"
SOURCE_COMPARE_JSON = "source_v03_v04_window_loudness_report.json"
SOURCE_COMPARE_CSV = "source_v03_v04_window_loudness_report.csv"

LOW_RANGES = [
    (12.0, 13.5, "forced_low_12p0_13p5"),
    (19.5, 21.0, "forced_low_19p5_21p0"),
    (27.0, 28.5, "forced_low_27p0_28p5"),
    (70.5, 72.0, "forced_low_70p5_72p0"),
    (90.0, 91.5, "forced_low_90p0_91p5"),
]
HIGH_RANGES = [
    (64.5, 69.0, "forced_high_64p5_69p0"),
]
VOCAL_KEYS = {"lead_vocal", "female_vocal", "backing_vocals", "vocal_reverb", "vocal_delay"}
MUSIC_KEYS = {"woodwinds", "brass", "fx", "synth", "strings", "percussion", "keyboard", "guitar", "bass", "drums"}
ALL_RIDE_KEYS = VOCAL_KEYS | MUSIC_KEYS


def configure_base() -> None:
    v3.configure_base()
    base.SLUG = SLUG
    base.WORK = ROOT / "audio_work" / SLUG
    base.SOURCE = base.WORK / "source_stems"
    base.PROCESSED = base.WORK / "processed_stems"
    base.REAPER_DIR = ROOT / "reaper" / SLUG
    base.RENDERS = ROOT / "renders" / SLUG
    base.REPORTS = ROOT / "reports" / SLUG

    base.RPP = base.REAPER_DIR / "mwolla_v04_PHRASE_LEVEL_CONSISTENT_MASTER.rpp"
    base.BUILD_LUA = base.REAPER_DIR / "build_mwolla_v04_phrase_level_consistent_master.lua"
    base.RUN_BUILD_LUA = base.REAPER_DIR / "run_build_mwolla_v04_phrase_level_consistent_master.lua"
    base.RENDER_LUA = base.REAPER_DIR / "render_mwolla_v04_phrase_level_consistent_master.lua"
    base.RUN_RENDER_LUA = base.REAPER_DIR / "run_render_mwolla_v04_phrase_level_consistent_master.lua"
    base.TRACE_JSON = base.REPORTS / "actual_reaper_plugin_trace.json"
    base.TRACE_MD = base.REPORTS / "actual_reaper_plugin_trace.md"

    base.REAPER_PRINT = base.RENDERS / "mwolla_v04_REAPERPRINT_24-48.wav"
    base.FINAL_WAV = base.RENDERS / "mwolla_v04_PHRASE_LEVEL_CONSISTENT_MASTER.wav"
    base.FINAL_MP3 = base.RENDERS / "mwolla_v04_PHRASE_LEVEL_CONSISTENT_MASTER_320k.mp3"
    base.VOCAL_SOLO = base.RENDERS / "mwolla_v04_VOCAL_SOLO_phrase_level_consistent.wav"
    base.AB_PREVIEW_MP3 = base.RENDERS / "mwolla_v04_AB_original_to_phrase_level_consistent_master_320k.mp3"
    base.DELIVERABLE_ZIP = base.RENDERS / "mwolla_v04_PHRASE_LEVEL_CONSISTENT_MASTER_DELIVERABLE.zip"

    base.REPORT_FILENAME = "mwolla_v04_phrase_level_consistent_master_report.md"
    base.REPORT_TITLE = "Mwolla v04 Phrase-Level Consistent Master Report"
    base.PROJECT_NOTES = (
        "mwolla v04 phrase-level consistent master: rebuild from original stem zip, retain v03 vocal cleanup, "
        "then add 1.5s phrase-level bidirectional riding. Small specified dips are lifted by source-cause "
        "classification, the 64.5-69.0s loud hook is reduced, and premaster bus correction is applied before "
        "final limiter. The limiter is for peak safety and light release-review loudness only."
    )


def phrase_premaster_path() -> Path:
    return base.RENDERS / PHRASE_PREMASTER_NAME


def db_to_amp(db: float | np.ndarray) -> np.ndarray:
    return np.power(10.0, np.asarray(db) / 20.0)


def amp_to_db(value: float | np.ndarray) -> np.ndarray:
    return 20.0 * np.log10(np.maximum(np.asarray(value), 1e-12))


def pad_or_trim(y: np.ndarray, length: int) -> np.ndarray:
    if len(y) == length:
        return y.astype(np.float32, copy=False)
    if len(y) > length:
        return y[:length].astype(np.float32)
    out = np.zeros((length, y.shape[1]), dtype=np.float32)
    out[: len(y)] = y
    return out


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


def window_rows(y: np.ndarray, sr: int, window_s: float) -> list[dict[str, float]]:
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
                "lufs_proxy_db": round(float(amp_to_db(rms)) - 0.7, 2),
            }
        )
    return rows


def active_median(rows: list[dict[str, Any]], start_s: float = 6.0, end_s: float = 137.0) -> float:
    levels = np.array(
        [
            float(row["rms_db"])
            for row in rows
            if float(row["start_s"]) >= start_s and float(row["end_s"]) <= end_s
        ],
        dtype=np.float32,
    )
    if len(levels) == 0:
        levels = np.array([float(row["rms_db"]) for row in rows], dtype=np.float32)
    active = levels[levels > np.percentile(levels, 20.0)]
    return float(np.median(active)) if len(active) else float(np.median(levels))


def range_label(start_s: float, end_s: float) -> str | None:
    center = (start_s + end_s) * 0.5
    for low, high, label in LOW_RANGES:
        if low <= center < high:
            return label
    for low, high, label in HIGH_RANGES:
        if low <= center < high:
            return label
    return None


def load_processed(path: Path, sr: int, length: int) -> np.ndarray:
    stem_sr, y, _ = base.read_wav(path)
    if stem_sr != sr:
        raise RuntimeError(f"Sample-rate mismatch: {path}")
    return pad_or_trim(y, length)


def approximate_group_mix(processed: dict[str, Path], keys: set[str], sr: int, length: int) -> np.ndarray:
    mix = np.zeros((length, 2), dtype=np.float32)
    for key in sorted(keys):
        path = processed.get(key)
        if not path or not path.exists():
            continue
        gain_db = float(v3.v2.TRACK_MIX_DB.get(key, 0.0))
        mix += load_processed(path, sr, length) * float(db_to_amp(gain_db))
    return mix.astype(np.float32)


def smooth_curve_from_window_gains(
    rows: list[dict[str, Any]],
    window_gains_db: np.ndarray,
    sample_count: int,
    sr: int,
    smooth_s: float,
    min_db: float,
    max_db: float,
) -> np.ndarray:
    centers = np.array([(float(row["start_s"]) + float(row["end_s"])) * 0.5 for row in rows], dtype=np.float32)
    sample_times = np.arange(sample_count, dtype=np.float32) / float(sr)
    if len(centers) > 1:
        curve_db = np.interp(sample_times, centers, window_gains_db, left=window_gains_db[0], right=window_gains_db[-1]).astype(np.float32)
    else:
        curve_db = np.zeros(sample_count, dtype=np.float32)
    smooth = max(1, int(sr * smooth_s))
    if smooth > 1:
        kernel = np.hanning(smooth * 2 + 1).astype(np.float32)
        kernel /= np.sum(kernel)
        curve_db = base.signal.fftconvolve(curve_db, kernel, mode="same").astype(np.float32)
    return np.clip(curve_db, min_db, max_db)


def classify_window(
    mix_row: dict[str, Any],
    vocal_row: dict[str, Any],
    music_row: dict[str, Any],
    target_db: float,
    vocal_target_db: float,
    music_target_db: float,
) -> tuple[str, float]:
    start = float(mix_row["start_s"])
    end = float(mix_row["end_s"])
    label = range_label(start, end)
    delta = target_db - float(mix_row["rms_db"])
    vocal_delta = vocal_target_db - float(vocal_row["rms_db"])
    music_delta = music_target_db - float(music_row["rms_db"])
    if label and label.startswith("forced_low"):
        correction = min(max(delta * 0.88, 0.0), 4.5)
    elif label and label.startswith("forced_high"):
        correction = max(min(delta * 0.82, 0.0), -3.0)
    elif delta > 2.55:
        correction = min((delta - 0.75) * 0.56, 3.2)
    elif delta < -3.0:
        correction = max((delta + 1.0) * 0.48, -2.2)
    else:
        correction = 0.0

    if correction > 0:
        if vocal_delta > music_delta + 0.85:
            cause = "vocal_low"
        elif music_delta > vocal_delta + 0.85:
            cause = "music_low"
        else:
            cause = "full_mix_low"
    elif correction < 0:
        vocal_rise = -vocal_delta
        music_rise = -music_delta
        if music_rise > vocal_rise + 0.85:
            cause = "music_bass_drums_too_loud"
        elif vocal_rise > music_rise + 0.85:
            cause = "vocal_too_loud"
        else:
            cause = "master_premaster_imbalance"
    else:
        cause = "within_tolerance"
    return cause, round(float(correction), 3)


def write_phrase_analysis(
    label: str,
    path: Path,
    windows: tuple[float, ...] = (1.5, 3.0, 6.0),
) -> list[dict[str, Any]]:
    sr, y, _ = base.read_wav(path)
    rows: list[dict[str, Any]] = []
    for window_s in windows:
        wrows = window_rows(y, sr, window_s)
        median = active_median(wrows)
        for row in wrows:
            deviation = float(row["rms_db"]) - median
            rows.append(
                {
                    "label": label,
                    "file": base.rel(path),
                    "window_s": window_s,
                    **row,
                    "active_median_rms_db": round(median, 2),
                    "deviation_from_active_median_db": round(deviation, 2),
                    "forced_window": range_label(float(row["start_s"]), float(row["end_s"])) or "",
                    "outside_plus_minus_3db": bool(abs(deviation) > 3.0 and float(row["start_s"]) >= 6.0 and float(row["end_s"]) <= 137.0),
                }
            )
    return rows


def apply_phrase_stem_riding(
    processed: dict[str, Path],
    paths: dict[str, Path],
    sr: int,
    length: int,
    vocal_balance: dict[str, float],
) -> None:
    source_sr, source_mix, _ = base.read_wav(paths["full_reference"])
    if source_sr != sr:
        raise RuntimeError("Source full-mix sample-rate mismatch")
    source_mix = pad_or_trim(source_mix, length)
    before_mix = v3.v2.approximate_mix(processed, sr, length)
    vocal_mix = approximate_group_mix(processed, VOCAL_KEYS, sr, length)
    music_mix = approximate_group_mix(processed, MUSIC_KEYS, sr, length)

    mix_rows = window_rows(before_mix, sr, 1.5)
    vocal_rows = window_rows(vocal_mix, sr, 1.5)
    music_rows = window_rows(music_mix, sr, 1.5)
    source_rows = window_rows(source_mix, sr, 1.5)
    target = active_median(mix_rows)
    vocal_target = active_median(vocal_rows)
    music_target = active_median(music_rows)

    vocal_gains = np.zeros(len(mix_rows), dtype=np.float32)
    music_gains = np.zeros(len(mix_rows), dtype=np.float32)
    problem_rows: list[dict[str, Any]] = []
    for i, row in enumerate(mix_rows):
        cause, correction = classify_window(row, vocal_rows[i], music_rows[i], target, vocal_target, music_target)
        vocal_gain = 0.0
        music_gain = 0.0
        if correction > 0:
            if cause == "vocal_low":
                vocal_gain = correction
                music_gain = correction * 0.12
            elif cause == "music_low":
                music_gain = correction
                vocal_gain = correction * 0.10
            elif cause == "full_mix_low":
                vocal_gain = correction * 0.50
                music_gain = correction * 0.58
        elif correction < 0:
            if cause == "vocal_too_loud":
                vocal_gain = correction
                music_gain = correction * 0.12
            elif cause == "music_bass_drums_too_loud":
                music_gain = correction
                vocal_gain = correction * 0.12
            elif cause == "master_premaster_imbalance":
                vocal_gain = correction * 0.36
                music_gain = correction * 0.62
        vocal_gains[i] = vocal_gain
        music_gains[i] = music_gain
        if correction != 0 or range_label(float(row["start_s"]), float(row["end_s"])):
            problem_rows.append(
                {
                    "start_s": row["start_s"],
                    "end_s": row["end_s"],
                    "forced_window": range_label(float(row["start_s"]), float(row["end_s"])) or "",
                    "cause": cause,
                    "mix_rms_db": row["rms_db"],
                    "source_full_mix_rms_db": source_rows[i]["rms_db"] if i < len(source_rows) else None,
                    "vocal_group_rms_db": vocal_rows[i]["rms_db"],
                    "music_group_rms_db": music_rows[i]["rms_db"],
                    "target_active_median_rms_db": round(target, 2),
                    "recommended_total_correction_db": correction,
                    "printed_vocal_gain_db": round(float(vocal_gain), 2),
                    "printed_music_gain_db": round(float(music_gain), 2),
                }
            )

    vocal_curve = smooth_curve_from_window_gains(mix_rows, vocal_gains, length, sr, smooth_s=0.82, min_db=-3.0, max_db=4.5)
    music_curve = smooth_curve_from_window_gains(mix_rows, music_gains, length, sr, smooth_s=0.82, min_db=-3.0, max_db=4.5)

    for key in sorted(ALL_RIDE_KEYS):
        path = processed.get(key)
        if not path or not path.exists():
            continue
        y = load_processed(path, sr, length)
        curve = vocal_curve if key in VOCAL_KEYS else music_curve
        adjusted = y * db_to_amp(curve)[:, None]
        adjusted = base.peak_cap(adjusted.astype(np.float32), -1.25 if key in MUSIC_KEYS else -3.2)
        base.write_wav(path, sr, adjusted)

    after_mix = v3.v2.approximate_mix(processed, sr, length)
    after_rows = window_rows(after_mix, sr, 1.5)
    for i, row in enumerate(problem_rows):
        idx = int(round(float(row["start_s"]) / 1.5))
        if idx < len(after_rows):
            row["post_stem_riding_rms_db"] = after_rows[idx]["rms_db"]
            row["stem_riding_improvement_db"] = round(after_rows[idx]["rms_db"] - float(row["mix_rms_db"]), 2)

    vocal_curve_rows = [
        {
            "time_s": round(i / sr, 3),
            "vocal_gain_db": round(float(vocal_curve[i]), 3),
        }
        for i in range(0, length, max(1, int(sr * 0.25)))
    ]
    music_curve_rows = [
        {
            "time_s": round(i / sr, 3),
            "music_stem_gain_db": round(float(music_curve[i]), 3),
        }
        for i in range(0, length, max(1, int(sr * 0.25)))
    ]
    curve_summary = {
        "window_s": 1.5,
        "smoothing_s": 0.82,
        "target_active_median_rms_db": round(target, 2),
        "vocal_curve_min_db": round(float(np.min(vocal_curve)), 2),
        "vocal_curve_max_db": round(float(np.max(vocal_curve)), 2),
        "music_curve_min_db": round(float(np.min(music_curve)), 2),
        "music_curve_max_db": round(float(np.max(music_curve)), 2),
        "forced_low_ranges": LOW_RANGES,
        "forced_high_ranges": HIGH_RANGES,
        "vocal_balance": vocal_balance,
    }
    write_json(base.REPORTS / PROBLEM_REPORT_JSON, {"summary": curve_summary, "windows": problem_rows})
    write_json(base.REPORTS / VOCAL_CURVE_JSON, {"summary": curve_summary, "points": vocal_curve_rows})
    write_json(base.REPORTS / MUSIC_CURVE_JSON, {"summary": curve_summary, "points": music_curve_rows})
    write_csv(base.REPORTS / VOCAL_CURVE_CSV, vocal_curve_rows)
    write_csv(base.REPORTS / MUSIC_CURVE_CSV, music_curve_rows)

    lines = [
        "# Problem Window Cause Classification",
        "",
        f"- 1.5s active median before stem riding: `{round(target, 2)}` dB RMS",
        f"- Vocal curve range: `{curve_summary['vocal_curve_min_db']}` to `{curve_summary['vocal_curve_max_db']}` dB",
        f"- Music curve range: `{curve_summary['music_curve_min_db']}` to `{curve_summary['music_curve_max_db']}` dB",
        "",
        "| start | end | forced | cause | total | vocal | music | before | after |",
        "| ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in problem_rows:
        lines.append(
            f"| {row['start_s']} | {row['end_s']} | {row['forced_window']} | {row['cause']} | "
            f"{row['recommended_total_correction_db']} | {row['printed_vocal_gain_db']} | "
            f"{row['printed_music_gain_db']} | {row['mix_rms_db']} | {row.get('post_stem_riding_rms_db')} |"
        )
    (base.REPORTS / PROBLEM_REPORT_MD).write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_processed(paths: dict[str, Path]) -> tuple[dict[str, Path], int, float, dict[str, float]]:
    processed, sr, duration, vocal_balance = v3.v2.write_processed(paths)
    length = int(round(duration * sr))
    apply_phrase_stem_riding(processed, paths, sr, length, vocal_balance)
    return processed, sr, duration, vocal_balance


def premaster_bus_leveling(input_path: Path, output_path: Path) -> dict[str, Any]:
    sr, y, _ = base.read_wav(input_path)
    rows = window_rows(y, sr, 1.5)
    median = active_median(rows)
    window_gains = np.zeros(len(rows), dtype=np.float32)
    out_rows: list[dict[str, Any]] = []
    for i, row in enumerate(rows):
        start = float(row["start_s"])
        end = float(row["end_s"])
        label = range_label(start, end) or ""
        delta = median - float(row["rms_db"])
        if label.startswith("forced_low"):
            gain = min(max(delta * 0.86, 0.0), 4.5)
        elif label.startswith("forced_high"):
            gain = max(min(delta * 0.86, 0.0), -3.0)
        elif start < 6.0 or end > 137.0:
            gain = 0.0
        elif delta > 2.25:
            gain = min((delta - 0.65) * 0.62, 3.4)
        elif delta < -2.75:
            gain = max((delta + 0.85) * 0.58, -2.5)
        else:
            gain = 0.0
        if abs(gain) < 0.25 and not label:
            gain = 0.0
        window_gains[i] = gain
        out_rows.append(
            {
                **row,
                "forced_window": label,
                "drop_or_rise_vs_premaster_active_median_db": round(float(delta), 2),
                "applied_premaster_bus_gain_db": round(float(gain), 2),
            }
        )
    curve = smooth_curve_from_window_gains(rows, window_gains, len(y), sr, smooth_s=0.9, min_db=-3.0, max_db=4.5)
    leveled = y * db_to_amp(curve)[:, None]
    leveled = base.soft_clip(leveled.astype(np.float32), ceiling=0.958)
    leveled = base.peak_cap(leveled, -1.25)
    base.write_wav(output_path, sr, leveled)
    after_rows = window_rows(leveled, sr, 1.5)
    for i, row in enumerate(out_rows):
        if i < len(after_rows):
            row["post_bus_leveling_rms_db"] = after_rows[i]["rms_db"]
            row["premaster_improvement_db"] = round(after_rows[i]["rms_db"] - row["rms_db"], 2)

    gains_nonzero = window_gains[np.abs(window_gains) > 0.001]
    report = {
        "input": base.rel(input_path),
        "output": base.rel(output_path),
        "window_s": 1.5,
        "smoothing_s": 0.9,
        "premaster_active_median_rms_db": round(median, 2),
        "max_applied_premaster_bus_gain_db": round(float(np.max(window_gains)), 2),
        "min_applied_premaster_bus_gain_db": round(float(np.min(window_gains)), 2),
        "mean_abs_applied_gain_db": round(float(np.mean(np.abs(gains_nonzero))) if len(gains_nonzero) else 0.0, 2),
        "method": "Bidirectional 1.5s phrase-level premaster bus automation after stem/vocal/music riding and before final limiter.",
        "windows": out_rows,
    }
    write_json(base.REPORTS / PHRASE_BUS_REPORT_JSON, report)
    write_json(base.REPORTS / v3.BUS_LEVEL_REPORT_JSON, report)
    write_csv(base.REPORTS / PHRASE_BUS_REPORT_CSV, out_rows)
    return report


def final_master() -> None:
    premaster_bus_leveling(base.REAPER_PRINT, phrase_premaster_path())
    filter_graph = (
        "highpass=f=24,"
        "equalizer=f=58:t=q:w=0.75:g=0.22,"
        "equalizer=f=126:t=q:w=0.95:g=-0.16,"
        "equalizer=f=260:t=q:w=1:g=-0.22,"
        "equalizer=f=3450:t=q:w=0.9:g=-0.10,"
        "equalizer=f=7600:t=q:w=0.85:g=-0.08,"
        "equalizer=f=11200:t=q:w=0.8:g=-0.14,"
        "acompressor=threshold=-18dB:ratio=1.10:attack=24:release=150:makeup=1.02,"
        "loudnorm=I=-9.2:TP=-1.45:LRA=3.2:linear=false,"
        "alimiter=limit=0.84:attack=2:release=110:level=false"
    )
    subprocess.run(
        [
            base.FFMPEG,
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(phrase_premaster_path()),
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


def write_consistency_reports(paths: dict[str, Path]) -> None:
    compare_paths = {
        "source_full_mix": paths["full_reference"],
        "v03_premaster": ROOT / "renders/mwolla_v03_premaster_consistent_master/mwolla_v03_SECTION_LEVELED_PREMASTER_24-48.wav",
        "v03_final": ROOT / "renders/mwolla_v03_premaster_consistent_master/mwolla_v03_PREMASTER_CONSISTENT_MASTER.wav",
        "v04_premaster": phrase_premaster_path(),
        "v04_final": base.FINAL_WAV,
    }
    rows: list[dict[str, Any]] = []
    summary: dict[str, Any] = {}
    for label, path in compare_paths.items():
        if not path.exists():
            continue
        item_rows = write_phrase_analysis(label, path)
        rows.extend(item_rows)
        summary[label] = {}
        for window_s in (1.5, 3.0, 6.0):
            selected = [row for row in item_rows if row["window_s"] == window_s and row["start_s"] >= 6.0 and row["end_s"] <= 137.0]
            deviations = np.array([float(row["deviation_from_active_median_db"]) for row in selected], dtype=np.float32)
            forced = [row for row in selected if row["forced_window"]]
            summary[label][str(window_s)] = {
                "count": len(selected),
                "outside_plus_minus_3db_count": int(np.sum(np.abs(deviations) > 3.0)) if len(deviations) else 0,
                "max_positive_deviation_db": round(float(np.max(deviations)) if len(deviations) else 0.0, 2),
                "max_negative_deviation_db": round(float(np.min(deviations)) if len(deviations) else 0.0, 2),
                "mean_abs_deviation_db": round(float(np.mean(np.abs(deviations))) if len(deviations) else 0.0, 2),
                "forced_windows": forced,
            }
    write_json(base.REPORTS / SOURCE_COMPARE_JSON, {"summary": summary, "rows": rows})
    write_csv(base.REPORTS / SOURCE_COMPARE_CSV, rows)
    write_json(base.REPORTS / WINDOW_REPORT_JSON, {"summary": summary, "rows": rows})
    write_csv(base.REPORTS / WINDOW_REPORT_CSV, rows)

    lines = ["# Phrase-Level Loudness Consistency Report", ""]
    for label, window_summary in summary.items():
        lines.append(f"## {label}")
        lines.append("")
        lines.append("| window | outside ±3 dB | max + | max - | mean abs |")
        lines.append("| ---: | ---: | ---: | ---: | ---: |")
        for window_s, values in window_summary.items():
            lines.append(
                f"| {window_s}s | {values['outside_plus_minus_3db_count']} | "
                f"{values['max_positive_deviation_db']} | {values['max_negative_deviation_db']} | "
                f"{values['mean_abs_deviation_db']} |"
            )
        lines.append("")
    (base.REPORTS / WINDOW_REPORT_MD).write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_reports(paths: dict[str, Path], processed: dict[str, Path], vocal_balance: dict[str, float], gate: dict[str, Any]) -> None:
    write_consistency_reports(paths)
    rows = [
        base.audio_metrics(paths["full_reference"], "source_full_reference"),
        base.audio_metrics(ROOT / "renders/mwolla_v03_premaster_consistent_master/mwolla_v03_PREMASTER_CONSISTENT_MASTER.wav", "v03_final_master_wav"),
        base.audio_metrics(ROOT / "renders/mwolla_v03_premaster_consistent_master/mwolla_v03_SECTION_LEVELED_PREMASTER_24-48.wav", "v03_section_leveled_premaster"),
        base.audio_metrics(processed["lead_vocal"], "processed_main_vocal"),
        base.audio_metrics(processed["female_vocal"], "processed_female_layer"),
        base.audio_metrics(base.VOCAL_SOLO, "processed_vocal_solo"),
        base.audio_metrics(base.REAPER_PRINT, "v04_reaper_print"),
        base.audio_metrics(phrase_premaster_path(), "v04_phrase_leveled_premaster"),
        base.audio_metrics(base.FINAL_WAV, "final_master_wav"),
        base.audio_metrics(base.FINAL_MP3, "final_master_mp3"),
    ]
    write_csv(base.REPORTS / "qc_metrics.csv", rows)
    write_json(base.REPORTS / "qc_metrics.json", rows)
    final = rows[-2]
    mp3 = rows[-1]
    window_payload = json.loads((base.REPORTS / WINDOW_REPORT_JSON).read_text(encoding="utf-8"))
    v04_summary = window_payload["summary"].get("v04_final", {})
    qc = {
        "passed": bool(gate.get("passed")) and (final.get("true_peak_dbfs") or 99) <= -1.0 and (mp3.get("true_peak_dbfs") or 99) <= -1.0,
        "status": "qc_passed_review_ready" if bool(gate.get("passed")) and (final.get("true_peak_dbfs") or 99) <= -1.0 and (mp3.get("true_peak_dbfs") or 99) <= -1.0 else "review_copy_or_blocked",
        "delivery_ready": False,
        "delivery_ready_blocker": "User loudness-matched A/B approval and final delivery evidence gates are still required.",
        "gate": gate,
        "vocal_balance": vocal_balance,
        "final_lufs": final.get("integrated_lufs"),
        "final_true_peak_dbfs": final.get("true_peak_dbfs"),
        "mp3_true_peak_dbfs": mp3.get("true_peak_dbfs"),
        "v04_final_phrase_summary": v04_summary,
    }
    write_json(base.REPORTS / "qc_summary.json", qc)

    problem_payload = json.loads((base.REPORTS / PROBLEM_REPORT_JSON).read_text(encoding="utf-8"))
    bus_payload = json.loads((base.REPORTS / PHRASE_BUS_REPORT_JSON).read_text(encoding="utf-8"))
    notes = [
        f"# {base.REPORT_TITLE}",
        "",
        "## Objective",
        "",
        "- Fix phrase-level perceived loudness inconsistency, not overall LUFS.",
        "- Rebuild from the original stem zip and compare source full mix, v03 premaster, v03 final, v04 premaster, and v04 final.",
        "- Use bidirectional leveling: lift short low phrases and reduce the loud 64.5-69.0s hook region.",
        "- Keep the lead vocal centered and clear; female/backing vocals remain panned support/noise-mask layers.",
        "",
        "## Forced Windows",
        "",
        "- Low/dip review: 12.0-13.5s, 19.5-21.0s, 27.0-28.5s, 70.5-72.0s, 90.0-91.5s.",
        "- High/loud review: 64.5-69.0s.",
        "",
        "## Riding Summary",
        "",
        f"- Stem/vocal/music problem windows: `{len(problem_payload.get('windows', []))}`",
        f"- Vocal printed curve range: `{problem_payload['summary']['vocal_curve_min_db']}` to `{problem_payload['summary']['vocal_curve_max_db']}` dB",
        f"- Music printed curve range: `{problem_payload['summary']['music_curve_min_db']}` to `{problem_payload['summary']['music_curve_max_db']}` dB",
        f"- Premaster bus curve range: `{bus_payload['min_applied_premaster_bus_gain_db']}` to `{bus_payload['max_applied_premaster_bus_gain_db']}` dB",
        "",
        "## Deliverables",
        "",
        f"- Final WAV: `{base.rel(base.FINAL_WAV)}`",
        f"- Final MP3: `{base.rel(base.FINAL_MP3)}`",
        f"- REAPER project: `{base.rel(base.RPP)}`",
        f"- Vocal solo check: `{base.rel(base.VOCAL_SOLO)}`",
        f"- Original-to-final A/B preview: `{base.rel(base.AB_PREVIEW_MP3)}`",
        f"- Deliverable ZIP: `{base.rel(base.DELIVERABLE_ZIP)}`",
        "",
        "## Evidence Reports",
        "",
        f"- Plugin trace: `{base.rel(base.TRACE_JSON)}`",
        f"- 1.5s/3s/6s consistency: `{base.rel(base.REPORTS / WINDOW_REPORT_JSON)}`",
        f"- Problem-window cause classification: `{base.rel(base.REPORTS / PROBLEM_REPORT_JSON)}`",
        f"- Vocal riding curve: `{base.rel(base.REPORTS / VOCAL_CURVE_JSON)}`",
        f"- Music/stem riding curve: `{base.rel(base.REPORTS / MUSIC_CURVE_JSON)}`",
        f"- Premaster bus leveling: `{base.rel(base.REPORTS / PHRASE_BUS_REPORT_JSON)}`",
        f"- Vocal gap cleanup: `{base.rel(base.REPORTS / 'vocal_gap_cleanup_decisions.json')}`",
        f"- QC metrics: `{base.rel(base.REPORTS / 'qc_metrics.json')}`",
        f"- QC summary: `{base.rel(base.REPORTS / 'qc_summary.json')}`",
        "",
        "## QC Headline",
        "",
        f"- Final WAV loudness: `{final.get('integrated_lufs')}` LUFS / TP `{final.get('true_peak_dbfs')}` dBFS",
        f"- Final MP3 TP: `{mp3.get('true_peak_dbfs')}` dBFS",
        f"- Vocal chain gate passed: `{gate.get('passed')}`",
        f"- Status: `{qc['status']}`; delivery_ready remains false until user A/B approval and final delivery gates.",
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
        base.REPORTS / PROBLEM_REPORT_JSON,
        base.REPORTS / PROBLEM_REPORT_MD,
        base.REPORTS / VOCAL_CURVE_JSON,
        base.REPORTS / VOCAL_CURVE_CSV,
        base.REPORTS / MUSIC_CURVE_JSON,
        base.REPORTS / MUSIC_CURVE_CSV,
        base.REPORTS / PHRASE_BUS_REPORT_JSON,
        base.REPORTS / PHRASE_BUS_REPORT_CSV,
        base.REPORTS / WINDOW_REPORT_JSON,
        base.REPORTS / WINDOW_REPORT_CSV,
        base.REPORTS / WINDOW_REPORT_MD,
        base.REPORTS / SOURCE_COMPARE_JSON,
        base.REPORTS / SOURCE_COMPARE_CSV,
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
    base.process_lead_vocal = v3.v2.v1.process_lead_vocal
    base.process_female_layer = v3.v2.v1.process_female_mask_layer
    base.process_backing_vocals = v3.v2.v1.process_backing_vocals
    base.process_instrument = v3.v2.v1.process_instrument
    base.write_processed = write_processed
    base.final_master = final_master
    base.write_reports = write_reports
    base.build_zip = build_zip
    return base.main()


if __name__ == "__main__":
    raise SystemExit(main())

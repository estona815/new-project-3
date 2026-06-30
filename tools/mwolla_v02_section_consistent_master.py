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
V01_SCRIPT = ROOT / "tools" / "mwolla_v01_noise_mask_pan_master.py"
SLUG = "mwolla_v02_section_consistent_master"


spec = importlib.util.spec_from_file_location("mwolla_v01_noise_mask_pan_master", V01_SCRIPT)
if spec is None or spec.loader is None:
    raise RuntimeError(f"Could not load v01 script: {V01_SCRIPT}")
v1 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v1)
base = v1.base

BASE_WRITE_PROCESSED = base.write_processed
BASE_WRITE_REPORTS = base.write_reports
BASE_BUILD_ZIP = base.build_zip

SECTION_REPORT_JSON = "section_loudness_consistency_report.json"
SECTION_REPORT_CSV = "section_loudness_consistency_report.csv"
SECTION_REPORT_MD = "section_loudness_consistency_report.md"
SECTION_PRE_RENDER_JSON = "section_leveling_pre_render.json"

TRACK_MIX_DB = {
    "woodwinds": 0.0,
    "brass": 0.0,
    "fx": -4.6,
    "synth": -0.9,
    "strings": 0.0,
    "percussion": 0.0,
    "keyboard": -1.4,
    "guitar": -0.6,
    "bass": 0.2,
    "drums": -0.8,
    "backing_vocals": -1.5,
    "lead_vocal": 0.0,
    "female_vocal": 0.0,
    "vocal_reverb": -1.8,
    "vocal_delay": -2.1,
}

LEVEL_TARGET_KEYS = {
    "woodwinds",
    "brass",
    "fx",
    "synth",
    "strings",
    "percussion",
    "keyboard",
    "guitar",
    "bass",
    "drums",
    "backing_vocals",
    "lead_vocal",
    "female_vocal",
    "vocal_reverb",
    "vocal_delay",
}


def configure_base() -> None:
    v1.configure_base()
    base.SLUG = SLUG
    base.WORK = ROOT / "audio_work" / SLUG
    base.SOURCE = base.WORK / "source_stems"
    base.PROCESSED = base.WORK / "processed_stems"
    base.REAPER_DIR = ROOT / "reaper" / SLUG
    base.RENDERS = ROOT / "renders" / SLUG
    base.REPORTS = ROOT / "reports" / SLUG

    base.RPP = base.REAPER_DIR / "mwolla_v02_SECTION_CONSISTENT_MASTER.rpp"
    base.BUILD_LUA = base.REAPER_DIR / "build_mwolla_v02_section_consistent_master.lua"
    base.RUN_BUILD_LUA = base.REAPER_DIR / "run_build_mwolla_v02_section_consistent_master.lua"
    base.RENDER_LUA = base.REAPER_DIR / "render_mwolla_v02_section_consistent_master.lua"
    base.RUN_RENDER_LUA = base.REAPER_DIR / "run_render_mwolla_v02_section_consistent_master.lua"
    base.TRACE_JSON = base.REPORTS / "actual_reaper_plugin_trace.json"
    base.TRACE_MD = base.REPORTS / "actual_reaper_plugin_trace.md"

    base.REAPER_PRINT = base.RENDERS / "mwolla_v02_REAPERPRINT_24-48.wav"
    base.FINAL_WAV = base.RENDERS / "mwolla_v02_SECTION_CONSISTENT_MASTER.wav"
    base.FINAL_MP3 = base.RENDERS / "mwolla_v02_SECTION_CONSISTENT_MASTER_320k.mp3"
    base.VOCAL_SOLO = base.RENDERS / "mwolla_v02_VOCAL_SOLO_section_consistent.wav"
    base.AB_PREVIEW_MP3 = base.RENDERS / "mwolla_v02_AB_original_to_section_consistent_master_320k.mp3"
    base.DELIVERABLE_ZIP = base.RENDERS / "mwolla_v02_SECTION_CONSISTENT_MASTER_DELIVERABLE.zip"

    base.REPORT_FILENAME = "mwolla_v02_section_consistent_master_report.md"
    base.REPORT_TITLE = "Mwolla v02 Section Consistent Master Report"
    base.PROJECT_NOTES = (
        "mwolla v02 section consistent master: original stem zip source, v01 vocal cleanup retained, "
        "with pre-render section clip-gain leveling across active stems. Main target is consistent "
        "section loudness, especially the 84-90s drop, before master limiting. Codex Vocal AI "
        "Artifact Split Tamer remains first FX slot on the lead vocal."
    )


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


def section_rows(y: np.ndarray, sr: int, window_s: float = 3.0) -> list[dict[str, float]]:
    mono = np.mean(y, axis=1).astype(np.float32)
    frame = int(sr * window_s)
    rows: list[dict[str, float]] = []
    for start in range(0, len(mono), frame):
        end = min(len(mono), start + frame)
        if end - start < int(sr * 0.5):
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


def approximate_mix(processed: dict[str, Path], sr: int, length: int) -> np.ndarray:
    mix = np.zeros((length, 2), dtype=np.float32)
    for key, gain_db in TRACK_MIX_DB.items():
        path = processed.get(key)
        if not path or not path.exists():
            continue
        stem_sr, y, _ = base.read_wav(path)
        if stem_sr != sr:
            raise RuntimeError(f"Sample-rate mismatch in processed stem {key}: {stem_sr} != {sr}")
        mix += pad_or_trim(y, length) * float(db_to_amp(gain_db))
    return mix.astype(np.float32)


def smooth_window_gains(
    source_mix: np.ndarray,
    processed_mix: np.ndarray,
    sr: int,
    window_s: float = 3.0,
) -> tuple[np.ndarray, dict[str, Any]]:
    processed_rows = section_rows(processed_mix, sr, window_s)
    source_rows = section_rows(source_mix, sr, window_s)
    processed_levels = np.array([row["rms_db"] for row in processed_rows], dtype=np.float32)
    source_levels = np.array([row["rms_db"] for row in source_rows[: len(processed_rows)]], dtype=np.float32)
    active = processed_levels[processed_levels > np.percentile(processed_levels, 20.0)]
    source_active = source_levels[source_levels > np.percentile(source_levels, 20.0)]
    target = float(np.median(active)) if len(active) else float(np.median(processed_levels))
    source_target = float(np.median(source_active)) if len(source_active) else float(np.median(source_levels))

    gains_db = np.zeros_like(processed_levels, dtype=np.float32)
    windows: list[dict[str, Any]] = []
    for i, row in enumerate(processed_rows):
        start_s = row["start_s"]
        drop_db = max(0.0, target - processed_levels[i])
        source_drop_db = max(0.0, source_target - source_levels[i]) if i < len(source_levels) else 0.0
        if start_s < 6.0 or start_s > 137.0:
            factor = 0.0
        elif 78.0 <= start_s < 93.0:
            factor = 0.82
        elif drop_db > 3.0:
            factor = 0.58 if source_drop_db > 3.8 else 0.70
        elif drop_db > 1.9:
            factor = 0.38
        else:
            factor = 0.0
        gain = min(drop_db * factor, 4.2)
        if gain < 0.35:
            gain = 0.0
        gains_db[i] = gain
        windows.append(
            {
                "start_s": row["start_s"],
                "end_s": row["end_s"],
                "processed_rms_db": round(float(processed_levels[i]), 2),
                "source_rms_db": round(float(source_levels[i]), 2) if i < len(source_levels) else None,
                "drop_vs_processed_active_median_db": round(float(drop_db), 2),
                "source_drop_vs_source_active_median_db": round(float(source_drop_db), 2),
                "applied_clip_gain_db": round(float(gain), 2),
            }
        )

    centers = np.array([(row["start_s"] + row["end_s"]) * 0.5 for row in processed_rows], dtype=np.float32)
    sample_times = np.arange(len(processed_mix), dtype=np.float32) / float(sr)
    if len(centers) > 1:
        gain_curve_db = np.interp(sample_times, centers, gains_db, left=gains_db[0], right=gains_db[-1]).astype(np.float32)
    else:
        gain_curve_db = np.zeros(len(processed_mix), dtype=np.float32)

    smooth = max(1, int(sr * 1.4))
    if smooth > 1:
        kernel = np.hanning(smooth * 2 + 1).astype(np.float32)
        kernel /= np.sum(kernel)
        gain_curve_db = base.signal.fftconvolve(gain_curve_db, kernel, mode="same").astype(np.float32)
    gain_curve_db = np.clip(gain_curve_db, 0.0, 4.2)
    report = {
        "window_s": window_s,
        "processed_active_median_rms_db": round(target, 2),
        "source_active_median_rms_db": round(source_target, 2),
        "max_applied_clip_gain_db": round(float(np.max(gains_db)), 2),
        "mean_applied_clip_gain_db": round(float(np.mean(gains_db[gains_db > 0])) if np.any(gains_db > 0) else 0.0, 2),
        "primary_detected_problem_region_s": "84.0-90.0",
        "windows": windows,
    }
    return gain_curve_db, report


def apply_curve_to_stems(processed: dict[str, Path], sr: int, length: int, gain_curve_db: np.ndarray) -> None:
    curve = db_to_amp(gain_curve_db).astype(np.float32)
    for key in sorted(LEVEL_TARGET_KEYS):
        path = processed.get(key)
        if not path or not path.exists():
            continue
        stem_sr, y, _ = base.read_wav(path)
        if stem_sr != sr:
            raise RuntimeError(f"Sample-rate mismatch while applying section curve to {key}")
        adjusted = pad_or_trim(y, length) * curve[:, None]
        adjusted = base.peak_cap(adjusted.astype(np.float32), -1.2)
        base.write_wav(path, sr, adjusted)


def write_processed(paths: dict[str, Path]) -> tuple[dict[str, Path], int, float, dict[str, float]]:
    processed, sr, duration, vocal_balance = BASE_WRITE_PROCESSED(paths)
    source_sr, source_mix, _ = base.read_wav(paths["full_reference"])
    if source_sr != sr:
        raise RuntimeError("Source full-mix sample-rate mismatch")
    source_mix = pad_or_trim(source_mix, int(round(duration * sr)))
    before_mix = approximate_mix(processed, sr, len(source_mix))
    gain_curve_db, level_report = smooth_window_gains(source_mix, before_mix, sr)
    apply_curve_to_stems(processed, sr, len(source_mix), gain_curve_db)
    after_mix = approximate_mix(processed, sr, len(source_mix))

    before_rows = section_rows(before_mix, sr)
    after_rows = section_rows(after_mix, sr)
    for i, row in enumerate(level_report["windows"]):
        if i < len(after_rows):
            row["post_clip_gain_approx_rms_db"] = after_rows[i]["rms_db"]
            row["approx_improvement_db"] = round(after_rows[i]["rms_db"] - before_rows[i]["rms_db"], 2)

    level_report["post_leveling_active_median_rms_db"] = round(
        float(np.median([row["rms_db"] for row in after_rows])), 2
    )
    level_report["method"] = (
        "Pre-render clip-gain automation printed into active processed stems before REAPER, "
        "not master-limiter-only loudness chasing."
    )
    base.REPORTS.mkdir(parents=True, exist_ok=True)
    (base.REPORTS / SECTION_PRE_RENDER_JSON).write_text(
        json.dumps(level_report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    vocal_balance["section_leveling_max_gain_db"] = level_report["max_applied_clip_gain_db"]
    vocal_balance["section_leveling_primary_region_s"] = level_report["primary_detected_problem_region_s"]
    return processed, sr, duration, vocal_balance


def final_master() -> None:
    filter_graph = (
        "highpass=f=24,"
        "equalizer=f=260:t=q:w=1:g=-0.18,"
        "equalizer=f=760:t=q:w=1.2:g=-0.08,"
        "equalizer=f=3200:t=q:w=0.9:g=0.08,"
        "equalizer=f=11200:t=q:w=0.8:g=-0.28,"
        "loudnorm=I=-10.65:TP=-1.35:LRA=3.7:linear=false,"
        "alimiter=limit=0.84:attack=2:release=90:level=false"
    )
    subprocess.run(
        [
            base.FFMPEG,
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(base.REAPER_PRINT),
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


def active_median(rows: list[dict[str, Any]]) -> float:
    levels = np.array([row["rms_db"] for row in rows], dtype=np.float32)
    active = levels[levels > np.percentile(levels, 20.0)]
    return float(np.median(active)) if len(active) else float(np.median(levels))


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


def write_section_reports(paths: dict[str, Path]) -> None:
    source_sr, source, _ = base.read_wav(paths["full_reference"])
    final_sr, final, _ = base.read_wav(base.FINAL_WAV)
    print_sr, reaper_print, _ = base.read_wav(base.REAPER_PRINT)
    if source_sr != final_sr or source_sr != print_sr:
        raise RuntimeError("Section report sample-rate mismatch")
    v01_path = ROOT / "renders/mwolla_v01_noise_mask_pan_master/mwolla_v01_NOISE_MASK_PAN_MASTER.wav"
    v01_rows: list[dict[str, Any]] = []
    if v01_path.exists():
        v01_sr, v01, _ = base.read_wav(v01_path)
        if v01_sr == source_sr:
            v01_rows = section_rows(pad_or_trim(v1.base.read_wav(v01_path)[1], len(final)), source_sr)

    source = pad_or_trim(source, len(final))
    reaper_print = pad_or_trim(reaper_print, len(final))
    source_rows = section_rows(source, source_sr)
    print_rows = section_rows(reaper_print, source_sr)
    final_rows = section_rows(final, source_sr)
    source_median = active_median(source_rows)
    print_median = active_median(print_rows)
    final_median = active_median(final_rows)

    pre_render = json.loads((base.REPORTS / SECTION_PRE_RENDER_JSON).read_text(encoding="utf-8"))
    rows: list[dict[str, Any]] = []
    for i, row in enumerate(final_rows):
        item: dict[str, Any] = {
            "start_s": row["start_s"],
            "end_s": row["end_s"],
            "source_rms_db": source_rows[i]["rms_db"] if i < len(source_rows) else None,
            "source_drop_vs_active_median_db": round(source_median - source_rows[i]["rms_db"], 2) if i < len(source_rows) else None,
            "v01_final_rms_db": v01_rows[i]["rms_db"] if i < len(v01_rows) else None,
            "reaper_print_rms_db": print_rows[i]["rms_db"] if i < len(print_rows) else None,
            "reaper_print_drop_vs_active_median_db": round(print_median - print_rows[i]["rms_db"], 2) if i < len(print_rows) else None,
            "v02_final_rms_db": row["rms_db"],
            "v02_final_drop_vs_active_median_db": round(final_median - row["rms_db"], 2),
            "pre_render_applied_clip_gain_db": pre_render["windows"][i]["applied_clip_gain_db"] if i < len(pre_render.get("windows", [])) else 0.0,
        }
        if item["v01_final_rms_db"] is not None:
            item["v02_vs_v01_final_improvement_db"] = round(row["rms_db"] - item["v01_final_rms_db"], 2)
        rows.append(item)

    problem_rows = [
        row for row in rows
        if row["start_s"] >= 6.0 and row["start_s"] <= 137.0 and row["v02_final_drop_vs_active_median_db"] > 3.0
    ]
    region_84_90 = [row for row in rows if 84.0 <= row["start_s"] < 90.0]
    payload = {
        "window_s": 3.0,
        "source_active_median_rms_db": round(source_median, 2),
        "reaper_print_active_median_rms_db": round(print_median, 2),
        "v02_final_active_median_rms_db": round(final_median, 2),
        "v02_remaining_problem_windows_count": len(problem_rows),
        "primary_region_84_90_avg_v02_vs_v01_improvement_db": round(
            float(np.mean([row.get("v02_vs_v01_final_improvement_db", 0.0) for row in region_84_90])) if region_84_90 else 0.0,
            2,
        ),
        "pre_render_leveling": pre_render,
        "windows": rows,
    }
    (base.REPORTS / SECTION_REPORT_JSON).write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    write_csv(base.REPORTS / SECTION_REPORT_CSV, rows)

    lines = [
        "# Mwolla v02 Section Loudness Consistency Report",
        "",
        f"- Primary detected v01 drop region: `{pre_render['primary_detected_problem_region_s']}`",
        f"- Max printed stem clip-gain correction: `{pre_render['max_applied_clip_gain_db']}` dB",
        f"- v02 final active median RMS: `{round(final_median, 2)}` dBFS",
        f"- Remaining >3 dB drop windows between 6s and 137s: `{len(problem_rows)}`",
        f"- 84-90s average v02 vs v01 final improvement: `{payload['primary_region_84_90_avg_v02_vs_v01_improvement_db']}` dB",
        "",
        "| start | end | v01 final | v02 final | gain printed | v02-v01 |",
        "| ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in rows:
        if row["pre_render_applied_clip_gain_db"] > 0 or 84.0 <= row["start_s"] < 90.0:
            lines.append(
                f"| {row['start_s']} | {row['end_s']} | {row.get('v01_final_rms_db')} | "
                f"{row['v02_final_rms_db']} | {row['pre_render_applied_clip_gain_db']} | "
                f"{row.get('v02_vs_v01_final_improvement_db')} |"
            )
    (base.REPORTS / SECTION_REPORT_MD).write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_reports(paths: dict[str, Path], processed: dict[str, Path], vocal_balance: dict[str, float], gate: dict[str, Any]) -> None:
    BASE_WRITE_REPORTS(paths, processed, vocal_balance, gate)
    write_section_reports(paths)
    report_path = base.REPORTS / base.REPORT_FILENAME
    section_payload = json.loads((base.REPORTS / SECTION_REPORT_JSON).read_text(encoding="utf-8"))
    lines = report_path.read_text(encoding="utf-8").rstrip().splitlines()
    lines.extend(
        [
            "",
            "## Section Consistency",
            "",
            f"- Primary v01 drop region corrected: `{section_payload['pre_render_leveling']['primary_detected_problem_region_s']}`",
            f"- Max pre-render stem clip-gain lift: `{section_payload['pre_render_leveling']['max_applied_clip_gain_db']}` dB",
            f"- 84-90s average v02-v01 final RMS improvement: `{section_payload['primary_region_84_90_avg_v02_vs_v01_improvement_db']}` dB",
            f"- Section report: `{base.rel(base.REPORTS / SECTION_REPORT_MD)}`",
        ]
    )
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_zip() -> None:
    BASE_BUILD_ZIP()
    extras = [
        base.REPORTS / SECTION_PRE_RENDER_JSON,
        base.REPORTS / SECTION_REPORT_JSON,
        base.REPORTS / SECTION_REPORT_CSV,
        base.REPORTS / SECTION_REPORT_MD,
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

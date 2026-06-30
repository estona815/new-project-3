#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import subprocess
from pathlib import Path
from typing import Any

import numpy as np


ROOT = Path("/Users/hantaeheuk/Documents/New project 3")
V02_SCRIPT = ROOT / "tools" / "mwolla_v02_section_consistent_master.py"
SLUG = "mwolla_v03_premaster_consistent_master"


spec = importlib.util.spec_from_file_location("mwolla_v02_section_consistent_master", V02_SCRIPT)
if spec is None or spec.loader is None:
    raise RuntimeError(f"Could not load v02 script: {V02_SCRIPT}")
v2 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v2)
base = v2.base

BUS_LEVEL_REPORT_JSON = "premaster_bus_section_leveling_report.json"
BUS_LEVEL_PREMASTER_NAME = "mwolla_v03_SECTION_LEVELED_PREMASTER_24-48.wav"


def configure_base() -> None:
    v2.configure_base()
    base.SLUG = SLUG
    base.WORK = ROOT / "audio_work" / SLUG
    base.SOURCE = base.WORK / "source_stems"
    base.PROCESSED = base.WORK / "processed_stems"
    base.REAPER_DIR = ROOT / "reaper" / SLUG
    base.RENDERS = ROOT / "renders" / SLUG
    base.REPORTS = ROOT / "reports" / SLUG

    base.RPP = base.REAPER_DIR / "mwolla_v03_PREMASTER_CONSISTENT_MASTER.rpp"
    base.BUILD_LUA = base.REAPER_DIR / "build_mwolla_v03_premaster_consistent_master.lua"
    base.RUN_BUILD_LUA = base.REAPER_DIR / "run_build_mwolla_v03_premaster_consistent_master.lua"
    base.RENDER_LUA = base.REAPER_DIR / "render_mwolla_v03_premaster_consistent_master.lua"
    base.RUN_RENDER_LUA = base.REAPER_DIR / "run_render_mwolla_v03_premaster_consistent_master.lua"
    base.TRACE_JSON = base.REPORTS / "actual_reaper_plugin_trace.json"
    base.TRACE_MD = base.REPORTS / "actual_reaper_plugin_trace.md"

    base.REAPER_PRINT = base.RENDERS / "mwolla_v03_REAPERPRINT_24-48.wav"
    base.FINAL_WAV = base.RENDERS / "mwolla_v03_PREMASTER_CONSISTENT_MASTER.wav"
    base.FINAL_MP3 = base.RENDERS / "mwolla_v03_PREMASTER_CONSISTENT_MASTER_320k.mp3"
    base.VOCAL_SOLO = base.RENDERS / "mwolla_v03_VOCAL_SOLO_premaster_consistent.wav"
    base.AB_PREVIEW_MP3 = base.RENDERS / "mwolla_v03_AB_original_to_premaster_consistent_master_320k.mp3"
    base.DELIVERABLE_ZIP = base.RENDERS / "mwolla_v03_PREMASTER_CONSISTENT_MASTER_DELIVERABLE.zip"

    base.REPORT_FILENAME = "mwolla_v03_premaster_consistent_master_report.md"
    base.REPORT_TITLE = "Mwolla v03 Premaster Consistent Master Report"
    base.PROJECT_NOTES = (
        "mwolla v03 premaster consistent master: original stem zip source, v02 stem section leveling retained, "
        "plus premaster bus clip-gain leveling before final loudness. Goal is improved perceived level "
        "consistency without relying on limiter-only loudness."
    )


def premaster_path() -> Path:
    return base.RENDERS / BUS_LEVEL_PREMASTER_NAME


def db_to_amp(db: float | np.ndarray) -> np.ndarray:
    return np.power(10.0, np.asarray(db) / 20.0)


def amp_to_db(value: float | np.ndarray) -> np.ndarray:
    return 20.0 * np.log10(np.maximum(np.asarray(value), 1e-12))


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


def active_median(rows: list[dict[str, Any]]) -> float:
    levels = np.array([row["rms_db"] for row in rows], dtype=np.float32)
    active = levels[levels > np.percentile(levels, 20.0)]
    return float(np.median(active)) if len(active) else float(np.median(levels))


def write_wav(path: Path, sr: int, y: np.ndarray) -> None:
    base.write_wav(path, sr, y.astype(np.float32))


def premaster_bus_leveling(input_path: Path, output_path: Path) -> dict[str, Any]:
    sr, y, _ = base.read_wav(input_path)
    rows = section_rows(y, sr)
    median = active_median(rows)
    window_gains = np.zeros(len(rows), dtype=np.float32)
    out_rows: list[dict[str, Any]] = []
    for i, row in enumerate(rows):
        start = float(row["start_s"])
        drop = max(0.0, median - float(row["rms_db"]))
        if start < 6.0 or start > 137.0:
            factor = 0.0
        elif 84.0 <= start < 90.0:
            factor = 0.96
        elif 9.0 <= start < 21.0:
            factor = 0.78
        elif drop > 3.0:
            factor = 0.70
        elif drop > 2.2:
            factor = 0.45
        else:
            factor = 0.0
        gain = min(max(drop - 0.8, 0.0) * factor, 4.8)
        if gain < 0.35:
            gain = 0.0
        window_gains[i] = gain
        out_rows.append(
            {
                **row,
                "drop_vs_premaster_active_median_db": round(float(drop), 2),
                "applied_premaster_bus_gain_db": round(float(gain), 2),
            }
        )

    centers = np.array([(row["start_s"] + row["end_s"]) * 0.5 for row in rows], dtype=np.float32)
    sample_times = np.arange(len(y), dtype=np.float32) / float(sr)
    gain_curve_db = np.interp(sample_times, centers, window_gains, left=window_gains[0], right=window_gains[-1]).astype(np.float32)
    smooth = max(1, int(sr * 1.0))
    if smooth > 1:
        kernel = np.hanning(smooth * 2 + 1).astype(np.float32)
        kernel /= np.sum(kernel)
        gain_curve_db = base.signal.fftconvolve(gain_curve_db, kernel, mode="same").astype(np.float32)
    gain_curve_db = np.clip(gain_curve_db, 0.0, 4.8)

    leveled = y * db_to_amp(gain_curve_db)[:, None]
    leveled = base.soft_clip(leveled.astype(np.float32), ceiling=0.965)
    leveled = base.peak_cap(leveled, -1.25)
    write_wav(output_path, sr, leveled)
    after_rows = section_rows(leveled, sr)
    for i, row in enumerate(out_rows):
        if i < len(after_rows):
            row["post_bus_leveling_rms_db"] = after_rows[i]["rms_db"]
            row["premaster_improvement_db"] = round(after_rows[i]["rms_db"] - row["rms_db"], 2)

    report = {
        "input": base.rel(input_path),
        "output": base.rel(output_path),
        "window_s": 3.0,
        "premaster_active_median_rms_db": round(median, 2),
        "max_applied_premaster_bus_gain_db": round(float(np.max(window_gains)), 2),
        "mean_applied_premaster_bus_gain_db": round(float(np.mean(window_gains[window_gains > 0])) if np.any(window_gains > 0) else 0.0, 2),
        "method": "Premaster bus clip-gain automation before final loudness, after stem-level section leveling.",
        "windows": out_rows,
    }
    (base.REPORTS / BUS_LEVEL_REPORT_JSON).write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return report


def final_master() -> None:
    bus_report = premaster_bus_leveling(base.REAPER_PRINT, premaster_path())
    filter_graph = (
        "highpass=f=24,"
        "equalizer=f=260:t=q:w=1:g=-0.15,"
        "equalizer=f=760:t=q:w=1.2:g=-0.06,"
        "equalizer=f=3200:t=q:w=0.9:g=0.06,"
        "equalizer=f=11200:t=q:w=0.8:g=-0.26,"
        "loudnorm=I=-10.75:TP=-1.35:LRA=3.5:linear=false,"
        "alimiter=limit=0.84:attack=2:release=92:level=false"
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
    # Keep this variable read in stack traces/tests if future edits inspect final_master.
    _ = bus_report


def write_reports(paths: dict[str, Path], processed: dict[str, Path], vocal_balance: dict[str, float], gate: dict[str, Any]) -> None:
    v2.write_reports(paths, processed, vocal_balance, gate)
    report_path = base.REPORTS / base.REPORT_FILENAME
    section_md_path = base.REPORTS / v2.SECTION_REPORT_MD
    if section_md_path.exists():
        section_text = section_md_path.read_text(encoding="utf-8")
        section_text = section_text.replace("Mwolla v02 Section", "Mwolla v03 Section")
        section_text = section_text.replace("v02 final", "v03 final")
        section_text = section_text.replace("v02 vs v01", "v03 vs v01")
        section_text = section_text.replace("v02-v01", "v03-v01")
        section_text = section_text.replace("v02 final active", "v03 final active")
        section_md_path.write_text(section_text, encoding="utf-8")
    section_payload = json.loads((base.REPORTS / v2.SECTION_REPORT_JSON).read_text(encoding="utf-8"))
    bus_payload = json.loads((base.REPORTS / BUS_LEVEL_REPORT_JSON).read_text(encoding="utf-8"))
    lines = report_path.read_text(encoding="utf-8").rstrip().splitlines()
    lines.extend(
        [
            "",
            "## Premaster Bus Leveling",
            "",
            f"- Section-leveled premaster: `{base.rel(premaster_path())}`",
            f"- Max premaster bus gain: `{bus_payload['max_applied_premaster_bus_gain_db']}` dB",
            f"- 84-90s average final improvement vs v01: `{section_payload['primary_region_84_90_avg_v02_vs_v01_improvement_db']}` dB",
            f"- Bus leveling report: `{base.rel(base.REPORTS / BUS_LEVEL_REPORT_JSON)}`",
        ]
    )
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_zip() -> None:
    v2.build_zip()
    extras = [
        premaster_path(),
        base.REPORTS / BUS_LEVEL_REPORT_JSON,
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
    base.write_processed = v2.write_processed
    base.final_master = final_master
    base.write_reports = write_reports
    base.build_zip = build_zip
    return base.main()


if __name__ == "__main__":
    raise SystemExit(main())

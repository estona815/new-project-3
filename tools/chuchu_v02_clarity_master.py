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

import imageio_ffmpeg
import numpy as np


ROOT = Path("/Users/hantaeheuk/Documents/New project 3")
BASE_SCRIPT = ROOT / "tools" / "sonyeo_luka_v01_clear_master.py"
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()

SOURCE_FULL_MIX = ROOT / "audio_work/chuchu_v01/raw_stems/0 추추.wav"
REAPER_RPP = ROOT / "reaper/chuchu_v01/chuchu_v01_MIX_MASTER.rpp"
REAPER_TRACE = ROOT / "reports/chuchu_v01/actual_reaper_plugin_trace.json"
REAPER_PRINT = ROOT / "renders/chuchu_v01/chuchu_v01_REAPERPRINT_24-48.wav"
V01_FINAL = ROOT / "renders/chuchu_v01/chuchu_v01_MIX_MASTER_FINAL.wav"

SLUG = "chuchu_v02_clarity_master"
RENDERS = ROOT / "renders" / SLUG
REPORTS = ROOT / "reports" / SLUG

CLARITY_PREMASTER = RENDERS / "chuchu_v02_CLARITY_PREMASTER_32f.wav"
FINAL_WAV = RENDERS / "chuchu_v02_CLARITY_MASTER_FINAL.wav"
FINAL_MP3 = RENDERS / "chuchu_v02_CLARITY_MASTER_FINAL_320k.mp3"
AB_V01_TO_V02 = RENDERS / "chuchu_v02_AB_v01_to_v02_320k.mp3"
AB_SOURCE_TO_V02 = RENDERS / "chuchu_v02_AB_source_to_v02_320k.mp3"
DELIVERABLE_ZIP = RENDERS / "chuchu_v02_CLARITY_MASTER_DELIVERABLE.zip"
REPORT_MD = REPORTS / "chuchu_v02_clarity_master_report.md"

spec = importlib.util.spec_from_file_location("sonyeo_luka_v01_clear_master", BASE_SCRIPT)
if spec is None or spec.loader is None:
    raise RuntimeError(f"Could not load helper script: {BASE_SCRIPT}")
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)
base.REPORTS = REPORTS


def ensure_dirs() -> None:
    for path in (RENDERS, REPORTS):
        path.mkdir(parents=True, exist_ok=True)


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
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)


def db_to_amp(db: float) -> float:
    return float(np.power(10.0, db / 20.0))


def clarity_dsp(y: np.ndarray, sr: int) -> np.ndarray:
    y = base.butter_filter(y, sr, "highpass", 28, 2)
    mid = ((y[:, 0] + y[:, 1]) * 0.5).astype(np.float32)
    side = ((y[:, 0] - y[:, 1]) * 0.5).astype(np.float32)
    mid_st = np.column_stack([mid, mid]).astype(np.float32)
    side_st = np.column_stack([side, side]).astype(np.float32)

    mid_st = base.dynamic_band_tame(mid_st, sr, 170, 330, max_cut_db=1.35, percentile=58.0, slope=0.58, smooth_ms=28.0)
    mid_st = base.dynamic_band_tame(mid_st, sr, 390, 880, max_cut_db=1.55, percentile=62.0, slope=0.55, smooth_ms=24.0)
    mid_st = base.rbj_peaking(mid_st, sr, 260, -0.35, 0.85)
    mid_st = base.rbj_peaking(mid_st, sr, 560, -0.45, 0.95)
    mid_st = base.rbj_peaking(mid_st, sr, 2550, 0.55, 0.85)
    mid_st = base.rbj_peaking(mid_st, sr, 4200, 0.30, 0.90)

    side_st = base.butter_filter(side_st, sr, "highpass", 115, 2)
    side_st = base.dynamic_band_tame(side_st, sr, 240, 760, max_cut_db=1.2, percentile=60.0, slope=0.55, smooth_ms=24.0)
    side_st = base.rbj_peaking(side_st, sr, 3200, 0.45, 0.80)
    side_st *= db_to_amp(0.55)

    mid = mid_st[:, 0]
    side = side_st[:, 0]
    out = np.column_stack([mid + side, mid - side]).astype(np.float32)
    out = base.dynamic_band_tame(out, sr, 6100, 9300, max_cut_db=1.85, percentile=56.0, slope=0.76, smooth_ms=6.0)
    out = base.dynamic_band_tame(out, sr, 10200, 17500, max_cut_db=1.10, percentile=60.0, slope=0.64, smooth_ms=8.0)
    out = base.rbj_shelf(out, sr, 9800, 0.18, high=True, slope=0.65)
    out = base.compressor(out, sr, threshold_db=-18.5, ratio=1.12, attack_ms=24.0, release_ms=135.0, makeup_db=0.15)
    return base.peak_cap(out.astype(np.float32), -2.0)


def write_premaster() -> None:
    sr, y, _dtype = base.read_wav(REAPER_PRINT)
    processed = clarity_dsp(y, sr)
    base.write_wav(CLARITY_PREMASTER, sr, processed)


def final_master() -> None:
    filter_graph = (
        "highpass=f=25,"
        "equalizer=f=280:t=q:w=0.9:g=-0.15,"
        "equalizer=f=3100:t=q:w=0.85:g=0.25,"
        "equalizer=f=7200:t=q:w=1.0:g=-0.12,"
        "loudnorm=I=-10.2:TP=-1.35:LRA=4.0:linear=false,"
        "alimiter=limit=0.84:attack=2:release=75:level=false"
    )
    subprocess.run(
        [
            FFMPEG,
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(CLARITY_PREMASTER),
            "-af",
            filter_graph,
            "-ar",
            "48000",
            "-c:a",
            "pcm_s24le",
            str(FINAL_WAV),
        ],
        check=True,
    )
    subprocess.run(
        [FFMPEG, "-y", "-hide_banner", "-loglevel", "error", "-i", str(FINAL_WAV), "-c:a", "libmp3lame", "-b:a", "320k", str(FINAL_MP3)],
        check=True,
    )


def write_ab_preview(first: Path, second: Path, out: Path, start_s: int = 28, length_s: int = 22) -> None:
    temp = REPORTS / f"_ab_{out.stem}"
    temp.mkdir(parents=True, exist_ok=True)
    before = temp / "before.wav"
    after = temp / "after.wav"
    concat = temp / "concat.txt"
    subprocess.run([FFMPEG, "-y", "-hide_banner", "-loglevel", "error", "-ss", str(start_s), "-t", str(length_s), "-i", str(first), "-c:a", "pcm_s16le", str(before)], check=True)
    subprocess.run([FFMPEG, "-y", "-hide_banner", "-loglevel", "error", "-ss", str(start_s), "-t", str(length_s), "-i", str(second), "-c:a", "pcm_s16le", str(after)], check=True)
    concat.write_text(f"file '{before}'\nfile '{after}'\n", encoding="utf-8")
    subprocess.run([FFMPEG, "-y", "-hide_banner", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(concat), "-c:a", "libmp3lame", "-b:a", "320k", str(out)], check=True)
    shutil.rmtree(temp, ignore_errors=True)


def run_gate() -> dict[str, Any]:
    proc = subprocess.run(
        ["python3", "tools/validate_reaper_vocal_chain_gate.py", "--trace", rel(REAPER_TRACE)],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    payload = json.loads(proc.stdout)
    write_json(REPORTS / "vocal_chain_gate.json", payload)
    if proc.returncode != 0:
        raise RuntimeError(proc.stdout + proc.stderr)
    return payload


def write_reports(gate: dict[str, Any]) -> dict[str, Any]:
    rows = [
        base.audio_metrics(SOURCE_FULL_MIX, "source_full_mix"),
        base.audio_metrics(REAPER_PRINT, "v01_reaper_print"),
        base.audio_metrics(V01_FINAL, "v01_final_master"),
        base.audio_metrics(CLARITY_PREMASTER, "v02_clarity_premaster"),
        base.audio_metrics(FINAL_WAV, "v02_final_wav"),
        base.audio_metrics(FINAL_MP3, "v02_final_mp3"),
    ]
    write_json(REPORTS / "qc_metrics.json", rows)
    write_csv(REPORTS / "qc_metrics.csv", rows)
    v01 = next(row for row in rows if row["label"] == "v01_final_master")
    v02 = next(row for row in rows if row["label"] == "v02_final_wav")
    mp3 = next(row for row in rows if row["label"] == "v02_final_mp3")
    summary = {
        "passed": bool(gate.get("passed")) and (v02.get("true_peak_dbfs") or 99) <= -0.8 and (mp3.get("true_peak_dbfs") or 99) <= -0.2,
        "status": "genre_based_draft",
        "source": "v01 REAPER print, with v02 clarity mastering chain",
        "v01_lufs": v01.get("integrated_lufs"),
        "v02_lufs": v02.get("integrated_lufs"),
        "v02_true_peak_dbfs": v02.get("true_peak_dbfs"),
        "v02_mp3_true_peak_dbfs": mp3.get("true_peak_dbfs"),
        "v02_presence_2000_5000_pct": v02.get("presence_2000_5000_pct"),
        "v02_box_350_800_pct": v02.get("box_350_800_pct"),
        "vocal_gate": gate,
    }
    write_json(REPORTS / "qc_summary.json", summary)
    notes = [
        "# Chuchu v02 Clarity Master Report",
        "",
        "## Intent",
        "",
        "- Make the v01 REAPER print cleaner and clearer at the mastering stage.",
        "- Reduce low-mid/box buildup, add controlled vocal/instrument edge, and keep sibilance guarded.",
        "- Preserve the existing REAPER stem mix and verified vocal-chain trace.",
        "",
        "## Deliverables",
        "",
        f"- Final WAV: `{rel(FINAL_WAV)}`",
        f"- Final MP3: `{rel(FINAL_MP3)}`",
        f"- V01-to-v02 A/B MP3: `{rel(AB_V01_TO_V02)}`",
        f"- Source-to-v02 A/B MP3: `{rel(AB_SOURCE_TO_V02)}`",
        f"- Deliverable ZIP: `{rel(DELIVERABLE_ZIP)}`",
        f"- Source REAPER project: `{rel(REAPER_RPP)}`",
        "",
        "## QC",
        "",
        f"- V01 final: `{v01.get('integrated_lufs')}` LUFS / TP `{v01.get('true_peak_dbfs')}` dBFS",
        f"- V02 final: `{v02.get('integrated_lufs')}` LUFS / TP `{v02.get('true_peak_dbfs')}` dBFS",
        f"- V02 MP3 TP: `{mp3.get('true_peak_dbfs')}` dBFS",
        f"- Vocal chain gate: `{gate.get('passed')}`",
        "",
        "## Processing Notes",
        "",
        "- Mid channel: reduced 170-330 Hz and 390-880 Hz buildup, added mild 2.5-4.2 kHz definition.",
        "- Side channel: high-passed side lows, cleaned side low-mid, added light upper-mid width.",
        "- Top end: sibilance/air guard after clarity lift so brightness does not turn brittle.",
        "- No external reference matching was performed; final listening approval is still required.",
    ]
    REPORT_MD.write_text("\n".join(notes) + "\n", encoding="utf-8")
    return summary


def build_zip() -> None:
    DELIVERABLE_ZIP.unlink(missing_ok=True)
    files = [
        FINAL_WAV,
        FINAL_MP3,
        CLARITY_PREMASTER,
        AB_V01_TO_V02,
        AB_SOURCE_TO_V02,
        REAPER_PRINT,
        REAPER_RPP,
        REAPER_TRACE,
        REPORTS / "vocal_chain_gate.json",
        REPORTS / "qc_metrics.json",
        REPORTS / "qc_metrics.csv",
        REPORTS / "qc_summary.json",
        REPORT_MD,
    ]
    with zipfile.ZipFile(DELIVERABLE_ZIP, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in files:
            if path.exists():
                archive.write(path, path.relative_to(ROOT).as_posix())


def main() -> int:
    ensure_dirs()
    write_premaster()
    final_master()
    write_ab_preview(V01_FINAL, FINAL_WAV, AB_V01_TO_V02)
    write_ab_preview(SOURCE_FULL_MIX, FINAL_WAV, AB_SOURCE_TO_V02)
    gate = run_gate()
    summary = write_reports(gate)
    build_zip()
    print(
        json.dumps(
            {
                "final_wav": rel(FINAL_WAV),
                "final_mp3": rel(FINAL_MP3),
                "deliverable_zip": rel(DELIVERABLE_ZIP),
                "v02_lufs": summary.get("v02_lufs"),
                "v02_true_peak_dbfs": summary.get("v02_true_peak_dbfs"),
                "v02_mp3_true_peak_dbfs": summary.get("v02_mp3_true_peak_dbfs"),
                "vocal_gate_passed": summary.get("vocal_gate", {}).get("passed"),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

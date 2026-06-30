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
V04_SCRIPT = ROOT / "tools" / "mwolla_v04_phrase_level_consistent_master.py"
SLUG = "mwolla_v05_phrase_plateau_master"


spec = importlib.util.spec_from_file_location("mwolla_v04_phrase_level_consistent_master", V04_SCRIPT)
if spec is None or spec.loader is None:
    raise RuntimeError(f"Could not load v04 script: {V04_SCRIPT}")
v4 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v4)
base = v4.base


PHRASE_PREMASTER_NAME = "mwolla_v05_PHRASE_LEVELED_PREMASTER_24-48.wav"
PLATEAU_PREMASTER_NAME = "mwolla_v05_PLATEAU_PREMASTER_24-48.wav"
PLATEAU_REPORT_JSON = "plateau_premaster_leveling_report.json"
PLATEAU_REPORT_CSV = "plateau_premaster_leveling_report.csv"
WINDOW_REPORT_JSON = "section_loudness_consistency_1p5s_3s_6s_report.json"
WINDOW_REPORT_CSV = "section_loudness_consistency_1p5s_3s_6s_report.csv"
WINDOW_REPORT_MD = "section_loudness_consistency_1p5s_3s_6s_report.md"
SOURCE_COMPARE_JSON = "source_v03_v04_v05_window_loudness_report.json"
SOURCE_COMPARE_CSV = "source_v03_v04_v05_window_loudness_report.csv"


def configure_base() -> None:
    v4.configure_base()
    v4.PHRASE_PREMASTER_NAME = PHRASE_PREMASTER_NAME
    base.SLUG = SLUG
    base.WORK = ROOT / "audio_work" / SLUG
    base.SOURCE = base.WORK / "source_stems"
    base.PROCESSED = base.WORK / "processed_stems"
    base.REAPER_DIR = ROOT / "reaper" / SLUG
    base.RENDERS = ROOT / "renders" / SLUG
    base.REPORTS = ROOT / "reports" / SLUG

    base.RPP = base.REAPER_DIR / "mwolla_v05_PHRASE_PLATEAU_MASTER.rpp"
    base.BUILD_LUA = base.REAPER_DIR / "build_mwolla_v05_phrase_plateau_master.lua"
    base.RUN_BUILD_LUA = base.REAPER_DIR / "run_build_mwolla_v05_phrase_plateau_master.lua"
    base.RENDER_LUA = base.REAPER_DIR / "render_mwolla_v05_phrase_plateau_master.lua"
    base.RUN_RENDER_LUA = base.REAPER_DIR / "run_render_mwolla_v05_phrase_plateau_master.lua"
    base.TRACE_JSON = base.REPORTS / "actual_reaper_plugin_trace.json"
    base.TRACE_MD = base.REPORTS / "actual_reaper_plugin_trace.md"

    base.REAPER_PRINT = base.RENDERS / "mwolla_v05_REAPERPRINT_24-48.wav"
    base.FINAL_WAV = base.RENDERS / "mwolla_v05_PHRASE_PLATEAU_MASTER.wav"
    base.FINAL_MP3 = base.RENDERS / "mwolla_v05_PHRASE_PLATEAU_MASTER_320k.mp3"
    base.VOCAL_SOLO = base.RENDERS / "mwolla_v05_VOCAL_SOLO_phrase_plateau.wav"
    base.AB_PREVIEW_MP3 = base.RENDERS / "mwolla_v05_AB_original_to_phrase_plateau_master_320k.mp3"
    base.DELIVERABLE_ZIP = base.RENDERS / "mwolla_v05_PHRASE_PLATEAU_MASTER_DELIVERABLE.zip"

    base.REPORT_FILENAME = "mwolla_v05_phrase_plateau_master_report.md"
    base.REPORT_TITLE = "Mwolla v05 Phrase Plateau Master Report"
    base.PROJECT_NOTES = (
        "mwolla v05 phrase plateau master: rebuild from original stem zip, retain v04 stem/vocal/music "
        "phrase riding, then add a plateau premaster that gently lowers active sustained windows so the "
        "1.5s phrase-level median does not rise above sparse phrases. Final master avoids loudnorm and "
        "uses fixed gain plus true-peak limiting to preserve phrase consistency."
    )


def phrase_premaster_path() -> Path:
    return base.RENDERS / PHRASE_PREMASTER_NAME


def plateau_premaster_path() -> Path:
    return base.RENDERS / PLATEAU_PREMASTER_NAME


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
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)


def apply_plateau_leveling(input_path: Path, output_path: Path, target_rms_db: float = -20.4) -> dict[str, Any]:
    sr, y, _ = base.read_wav(input_path)
    rows = v4.window_rows(y, sr, 1.5)
    window_gains = np.zeros(len(rows), dtype=np.float32)
    out_rows: list[dict[str, Any]] = []
    for i, row in enumerate(rows):
        start = float(row["start_s"])
        end = float(row["end_s"])
        center = (start + end) * 0.5
        if start < 6.0 or end > 137.0:
            gain = 0.0
        elif 64.5 <= center < 69.0:
            gain = max(target_rms_db - 0.2 - float(row["rms_db"]), -3.0)
        elif float(row["rms_db"]) > target_rms_db:
            gain = max(target_rms_db - float(row["rms_db"]), -3.0)
        else:
            gain = 0.0
        if abs(gain) < 0.18:
            gain = 0.0
        window_gains[i] = gain
        out_rows.append(
            {
                **row,
                "target_plateau_rms_db": target_rms_db,
                "applied_plateau_gain_db": round(float(gain), 2),
                "forced_window": v4.range_label(start, end) or "",
            }
        )

    curve = v4.smooth_curve_from_window_gains(rows, window_gains, len(y), sr, smooth_s=0.9, min_db=-3.0, max_db=0.0)
    leveled = y * db_to_amp(curve)[:, None]
    leveled = base.peak_cap(leveled.astype(np.float32), -1.4)
    base.write_wav(output_path, sr, leveled)
    after_rows = v4.window_rows(leveled, sr, 1.5)
    for i, row in enumerate(out_rows):
        if i < len(after_rows):
            row["post_plateau_rms_db"] = after_rows[i]["rms_db"]
            row["plateau_delta_db"] = round(after_rows[i]["rms_db"] - row["rms_db"], 2)

    gains_nonzero = window_gains[np.abs(window_gains) > 0.001]
    report = {
        "input": base.rel(input_path),
        "output": base.rel(output_path),
        "window_s": 1.5,
        "smoothing_s": 0.9,
        "target_plateau_rms_db": target_rms_db,
        "max_downward_gain_db": round(float(np.min(window_gains)), 2),
        "mean_abs_downward_gain_db": round(float(np.mean(np.abs(gains_nonzero))) if len(gains_nonzero) else 0.0, 2),
        "method": "Downward-only phrase plateau after v04 bidirectional premaster leveling. This preserves sparse forced-low windows and reduces the active median before final limiting.",
        "windows": out_rows,
    }
    write_json(base.REPORTS / PLATEAU_REPORT_JSON, report)
    write_csv(base.REPORTS / PLATEAU_REPORT_CSV, out_rows)
    return report


def final_master() -> None:
    v4.premaster_bus_leveling(base.REAPER_PRINT, phrase_premaster_path())
    apply_plateau_leveling(phrase_premaster_path(), plateau_premaster_path(), target_rms_db=-20.4)
    filter_graph = (
        "highpass=f=24,"
        "volume=4.0dB,"
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
            str(plateau_premaster_path()),
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
        "v04_final": ROOT / "renders/mwolla_v04_phrase_level_consistent_master/mwolla_v04_PHRASE_LEVEL_CONSISTENT_MASTER.wav",
        "v05_phrase_premaster": phrase_premaster_path(),
        "v05_plateau_premaster": plateau_premaster_path(),
        "v05_final": base.FINAL_WAV,
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
        lines.extend([f"## {label}", "", "| window | outside +/-3 dB | max + | max - | mean abs |", "| ---: | ---: | ---: | ---: | ---: |"])
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
        base.audio_metrics(ROOT / "renders/mwolla_v04_phrase_level_consistent_master/mwolla_v04_PHRASE_LEVEL_CONSISTENT_MASTER.wav", "v04_final_master_wav"),
        base.audio_metrics(processed["lead_vocal"], "processed_main_vocal"),
        base.audio_metrics(processed["female_vocal"], "processed_female_layer"),
        base.audio_metrics(base.VOCAL_SOLO, "processed_vocal_solo"),
        base.audio_metrics(base.REAPER_PRINT, "v05_reaper_print"),
        base.audio_metrics(phrase_premaster_path(), "v05_phrase_leveled_premaster"),
        base.audio_metrics(plateau_premaster_path(), "v05_plateau_premaster"),
        base.audio_metrics(base.FINAL_WAV, "final_master_wav"),
        base.audio_metrics(base.FINAL_MP3, "final_master_mp3"),
    ]
    write_csv(base.REPORTS / "qc_metrics.csv", rows)
    write_json(base.REPORTS / "qc_metrics.json", rows)
    final = rows[-2]
    mp3 = rows[-1]
    window_payload = json.loads((base.REPORTS / WINDOW_REPORT_JSON).read_text(encoding="utf-8"))
    v05_summary = window_payload["summary"].get("v05_final", {})
    qc_passed = bool(gate.get("passed")) and (final.get("true_peak_dbfs") or 99) <= -1.0 and (mp3.get("true_peak_dbfs") or 99) <= -1.0
    qc = {
        "passed": qc_passed,
        "status": "qc_passed_review_ready" if qc_passed else "review_copy_or_blocked",
        "delivery_ready": False,
        "delivery_ready_blocker": "User loudness-matched A/B approval and final delivery evidence gates are still required.",
        "gate": gate,
        "vocal_balance": vocal_balance,
        "final_lufs": final.get("integrated_lufs"),
        "final_true_peak_dbfs": final.get("true_peak_dbfs"),
        "mp3_true_peak_dbfs": mp3.get("true_peak_dbfs"),
        "v05_final_phrase_summary": v05_summary,
    }
    write_json(base.REPORTS / "qc_summary.json", qc)

    problem_payload = json.loads((base.REPORTS / v4.PROBLEM_REPORT_JSON).read_text(encoding="utf-8"))
    bus_payload = json.loads((base.REPORTS / v4.PHRASE_BUS_REPORT_JSON).read_text(encoding="utf-8"))
    plateau_payload = json.loads((base.REPORTS / PLATEAU_REPORT_JSON).read_text(encoding="utf-8"))
    notes = [
        f"# {base.REPORT_TITLE}",
        "",
        "## Objective",
        "",
        "- Continue v04 from the original stem zip, but prioritize 1.5s phrase-level consistency over overall LUFS.",
        "- Preserve v04 stem/vocal/music riding, then lower active sustained windows with a downward-only plateau premaster.",
        "- Avoid loudnorm in the final stage so the phrase-level correction is not undone by limiter pressure.",
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
        "## Phrase-Level Result",
        "",
        f"- v05 final 1.5s outside +/-3 dB count: `{v05_summary.get('1.5', {}).get('outside_plus_minus_3db_count')}`",
        f"- v05 final 1.5s mean abs deviation: `{v05_summary.get('1.5', {}).get('mean_abs_deviation_db')}` dB",
        f"- v05 final 3s outside +/-3 dB count: `{v05_summary.get('3.0', {}).get('outside_plus_minus_3db_count')}`",
        f"- v05 final 6s outside +/-3 dB count: `{v05_summary.get('6.0', {}).get('outside_plus_minus_3db_count')}`",
        "",
        "## Riding And Plateau",
        "",
        f"- Vocal curve range: `{problem_payload['summary']['vocal_curve_min_db']}` to `{problem_payload['summary']['vocal_curve_max_db']}` dB",
        f"- Music curve range: `{problem_payload['summary']['music_curve_min_db']}` to `{problem_payload['summary']['music_curve_max_db']}` dB",
        f"- Premaster bus correction range: `{bus_payload['min_applied_premaster_bus_gain_db']}` to `{bus_payload['max_applied_premaster_bus_gain_db']}` dB",
        f"- Plateau downward range: `{plateau_payload['max_downward_gain_db']}` to `0.0` dB",
        "",
        "## Evidence Reports",
        "",
        f"- Plugin trace: `{base.rel(base.TRACE_JSON)}`",
        f"- 1.5s/3s/6s consistency: `{base.rel(base.REPORTS / WINDOW_REPORT_JSON)}`",
        f"- Problem-window cause classification: `{base.rel(base.REPORTS / v4.PROBLEM_REPORT_JSON)}`",
        f"- Vocal riding curve: `{base.rel(base.REPORTS / v4.VOCAL_CURVE_JSON)}`",
        f"- Music/stem riding curve: `{base.rel(base.REPORTS / v4.MUSIC_CURVE_JSON)}`",
        f"- Premaster bus leveling: `{base.rel(base.REPORTS / v4.PHRASE_BUS_REPORT_JSON)}`",
        f"- Plateau premaster leveling: `{base.rel(base.REPORTS / PLATEAU_REPORT_JSON)}`",
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
        plateau_premaster_path(),
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
        base.REPORTS / v4.PROBLEM_REPORT_JSON,
        base.REPORTS / v4.PROBLEM_REPORT_MD,
        base.REPORTS / v4.VOCAL_CURVE_JSON,
        base.REPORTS / v4.VOCAL_CURVE_CSV,
        base.REPORTS / v4.MUSIC_CURVE_JSON,
        base.REPORTS / v4.MUSIC_CURVE_CSV,
        base.REPORTS / v4.PHRASE_BUS_REPORT_JSON,
        base.REPORTS / v4.PHRASE_BUS_REPORT_CSV,
        base.REPORTS / PLATEAU_REPORT_JSON,
        base.REPORTS / PLATEAU_REPORT_CSV,
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
    base.process_lead_vocal = v4.v3.v2.v1.process_lead_vocal
    base.process_female_layer = v4.v3.v2.v1.process_female_mask_layer
    base.process_backing_vocals = v4.v3.v2.v1.process_backing_vocals
    base.process_instrument = v4.v3.v2.v1.process_instrument
    base.write_processed = v4.write_processed
    base.final_master = final_master
    base.write_reports = write_reports
    base.build_zip = build_zip
    return base.main()


if __name__ == "__main__":
    raise SystemExit(main())

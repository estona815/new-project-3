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
V16B_SCRIPT = ROOT / "tools" / "mwolla_v16b_source_stem_repair_reference_density_master.py"
SLUG = "mwolla_v19_louder_clear_vocal_ott_saturation_master"
ZIP_SOURCE = Path("/Users/hantaeheuk/Downloads/몰라.zip")


spec = importlib.util.spec_from_file_location("mwolla_v16b_source_stem_repair_reference_density_master", V16B_SCRIPT)
if spec is None or spec.loader is None:
    raise RuntimeError(f"Could not load v16B script: {V16B_SCRIPT}")
v16b = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v16b)

base = v16b.base
v11 = v16b.v11


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
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)


def write_wav(path: Path, sr: int, y: np.ndarray) -> None:
    base.write_wav(path, sr, y.astype(np.float32))


def db_to_amp(db: float | np.ndarray) -> np.ndarray:
    return np.power(10.0, np.asarray(db) / 20.0)


def amp_to_db(value: float | np.ndarray) -> np.ndarray:
    return 20.0 * np.log10(np.maximum(np.asarray(value), 1e-12))


def pad_or_trim(y: np.ndarray, length: int) -> np.ndarray:
    return v16b.pad_or_trim(y, length)


def configure_base() -> None:
    v16b.SLUG = SLUG
    v16b.ZIP_SOURCE = ZIP_SOURCE
    v16b.configure_base()

    base.ZIP_SOURCE = ZIP_SOURCE
    base.SLUG = SLUG
    base.WORK = ROOT / "audio_work" / SLUG
    base.SOURCE = base.WORK / "source_stems"
    base.PROCESSED = base.WORK / "processed_stems"
    base.REAPER_DIR = ROOT / "reaper" / SLUG
    base.RENDERS = ROOT / "renders" / SLUG
    base.REPORTS = ROOT / "reports" / SLUG

    base.RPP = base.REAPER_DIR / "mwolla_v19_LOUDER_CLEAR_VOCAL_OTT_SATURATION_MASTER.rpp"
    base.BUILD_LUA = base.REAPER_DIR / "build_mwolla_v19_louder_clear_vocal_ott_saturation_master.lua"
    base.RUN_BUILD_LUA = base.REAPER_DIR / "run_build_mwolla_v19_louder_clear_vocal_ott_saturation_master.lua"
    base.RENDER_LUA = base.REAPER_DIR / "render_mwolla_v19_louder_clear_vocal_ott_saturation_master.lua"
    base.RUN_RENDER_LUA = base.REAPER_DIR / "run_render_mwolla_v19_louder_clear_vocal_ott_saturation_master.lua"
    base.TRACE_JSON = base.REPORTS / "actual_reaper_plugin_trace.json"
    base.TRACE_MD = base.REPORTS / "actual_reaper_plugin_trace.md"

    base.REAPER_PRINT = base.RENDERS / "mwolla_v19_REAPERPRINT_24-48.wav"
    base.FINAL_WAV = base.RENDERS / "mwolla_v19_LOUDER_CLEAR_VOCAL_OTT_SATURATION_MASTER.wav"
    base.FINAL_MP3 = base.RENDERS / "mwolla_v19_LOUDER_CLEAR_VOCAL_OTT_SATURATION_MASTER_320k.mp3"
    base.VOCAL_SOLO = base.RENDERS / "mwolla_v19_VOCAL_SOLO_louder_clear_vocal_ott_saturation.wav"
    base.AB_PREVIEW_MP3 = base.RENDERS / "mwolla_v19_AB_v18_to_louder_clear_vocal_ott_saturation_320k.mp3"
    base.DELIVERABLE_ZIP = base.RENDERS / "mwolla_v19_LOUDER_CLEAR_VOCAL_OTT_SATURATION_MASTER_DELIVERABLE.zip"

    base.REPORT_FILENAME = "mwolla_v19_louder_clear_vocal_ott_saturation_master_report.md"
    base.REPORT_TITLE = "Mwolla v19 Louder Clear Vocal OTT Saturation Master Report"
    base.PROJECT_NOTES = (
        "mwolla v19: v18 clean vocal pocket preserved, with a controlled loudness lift and printed lead-vocal "
        "OTT-style parallel density plus subtle saturation. Post-OTT anti-fizz is printed on the lead vocal. "
        "No external OTT plugin parameter writes and no new Ozone/OTT/clipper insert automation."
    )

    v11.PHRASE_PREMASTER_NAME = "mwolla_v19_PHRASE_SAFE_LOUDER_CLEAR_VOCAL_PREMASTER_24-48.wav"
    v11.FINAL_LOCKED_NAME = "mwolla_v19_POST_FINAL_LOUDER_CLEAR_VOCAL_TRUE_PEAK_SAFE_24-48.wav"


def band_rms_db(y: np.ndarray, sr: int, low: float, high: float) -> float:
    band = base.butter_filter(y.astype(np.float32), sr, "bandpass", (low, high), order=3)
    return round(float(amp_to_db(base.rms(band))), 2)


def vocal_metrics(y: np.ndarray, sr: int) -> dict[str, Any]:
    return {
        "active_rms_db": round(base.active_rms_db(y), 2),
        "rms_dbfs": round(float(amp_to_db(base.rms(y))), 2),
        "peak_dbfs": round(float(amp_to_db(np.max(np.abs(y)) if len(y) else 0.0)), 2),
        "crest_factor_db": round(float(amp_to_db(np.max(np.abs(y)) if len(y) else 0.0) - amp_to_db(base.rms(y))), 2),
        "mud_250_500_db": band_rms_db(y, sr, 250, 500),
        "presence_1500_5000_db": band_rms_db(y, sr, 1500, 5000),
        "sibilance_5000_9000_db": band_rms_db(y, sr, 5000, 9000),
        "air_10000_16000_db": band_rms_db(y, sr, 10000, 16000),
    }


def ott_style_vocal_parallel(y: np.ndarray, sr: int) -> tuple[np.ndarray, dict[str, Any]]:
    dry = y.astype(np.float32)
    low = base.butter_filter(dry, sr, "lowpass", 170.0, order=2)
    mid = base.butter_filter(dry, sr, "bandpass", (170.0, 5000.0), order=3)
    high = base.butter_filter(dry, sr, "bandpass", (5000.0, 12000.0), order=3)
    top = base.butter_filter(dry, sr, "highpass", 10000.0, order=2)

    mid_dense = base.compressor(mid, sr, threshold_db=-33.0, ratio=2.15, attack_ms=3.0, release_ms=86.0, makeup_db=0.42)
    high_dense = base.compressor(high, sr, threshold_db=-38.0, ratio=1.75, attack_ms=2.0, release_ms=68.0, makeup_db=0.18)
    parallel = dry + (mid_dense - mid) * 0.11 + (high_dense - high) * 0.065 + top * 0.018
    saturated = base.soft_saturation(parallel, drive_db=0.62, mix=0.035)
    guarded = base.dynamic_band_tame(saturated, sr, 5200, 9200, max_cut_db=0.46, percentile=63.0, slope=0.42, smooth_ms=7.0)
    guarded = base.rbj_peaking(guarded, sr, 3100.0, 0.16, 0.95)
    guarded = base.rbj_shelf(guarded, sr, 10600.0, 0.12, high=True, slope=0.70)
    guarded = base.match_active_rms(guarded, base.active_rms_db(dry) + 0.22, max_gain_db=0.35)
    guarded = base.peak_cap(guarded.astype(np.float32), -5.35)
    report = {
        "style": "printed OTT-style parallel vocal density, not an external OTT parameter write",
        "mid_band_hz": [170.0, 5000.0],
        "high_band_hz": [5000.0, 12000.0],
        "parallel_mid_delta_mix": 0.11,
        "parallel_high_delta_mix": 0.065,
        "saturation_drive_db": 0.62,
        "saturation_mix": 0.035,
        "post_ott_anti_fizz_hz": [5200.0, 9200.0],
        "post_ott_anti_fizz_max_cut_db": 0.46,
        "presence_lift_3100_hz_db": 0.16,
        "air_shelf_10600_hz_db": 0.12,
        "target_active_rms_lift_db": 0.22,
        "peak_cap_dbfs": -5.35,
    }
    return guarded.astype(np.float32), report


def apply_v19_vocal_polish(processed: dict[str, Path], sr: int, length: int) -> dict[str, Any]:
    lead_path = processed["lead_vocal"]
    lead_sr, lead, _ = base.read_wav(lead_path)
    if lead_sr != sr:
        raise RuntimeError("Sample-rate mismatch in v19 lead vocal polish")
    lead = pad_or_trim(lead, length)
    before = vocal_metrics(lead, sr)
    polished, settings = ott_style_vocal_parallel(lead, sr)
    polished = pad_or_trim(polished, length)
    write_wav(lead_path, sr, polished)
    after = vocal_metrics(polished, sr)
    report = {
        "schema": "mwolla-v19-vocal-ott-style-saturation-v1",
        "target": "subtle vocal density and clarity without phrase chopping or extra external plugin writes",
        "lead_vocal_path": rel(lead_path),
        "before": before,
        "after": after,
        "settings": settings,
        "guards": {
            "first_slot_vocal_rescue_preserved_in_reaper": True,
            "post_ott_anti_fizz_printed": True,
            "external_plugin_parameter_writes": "none_added",
        },
    }
    write_json(base.REPORTS / "v19_vocal_ott_saturation_report.json", report)
    write_csv(
        base.REPORTS / "v19_vocal_ott_saturation_report.csv",
        [
            {
                "metric": key,
                "before": before.get(key),
                "after": after.get(key),
                "delta": round(float(after[key]) - float(before[key]), 2) if isinstance(before.get(key), (int, float)) and isinstance(after.get(key), (int, float)) else "",
            }
            for key in before
        ],
    )
    return report


def write_processed(paths: dict[str, Path]) -> tuple[dict[str, Path], int, float, dict[str, float]]:
    processed, sr, duration, vocal_balance = v16b.write_processed(paths)
    length = int(round(duration * sr))
    polish = apply_v19_vocal_polish(processed, sr, length)
    v16b.v13.rewrite_vocal_solo(processed, sr, length)
    vocal_balance["v19_vocal_ott_style_saturation"] = True
    vocal_balance["v19_lead_active_rms_before_db"] = polish["before"]["active_rms_db"]
    vocal_balance["v19_lead_active_rms_after_db"] = polish["after"]["active_rms_db"]
    vocal_balance["v19_lead_presence_delta_db"] = round(polish["after"]["presence_1500_5000_db"] - polish["before"]["presence_1500_5000_db"], 2)
    vocal_balance["v19_lead_sibilance_delta_db"] = round(polish["after"]["sibilance_5000_9000_db"] - polish["before"]["sibilance_5000_9000_db"], 2)
    return processed, sr, duration, vocal_balance


def write_reaper_scripts(processed: dict[str, Path], duration: float) -> None:
    v16b.write_reaper_scripts(processed, duration)
    build_text = base.BUILD_LUA.read_text(encoding="utf-8")
    build_text = build_text.replace("mwolla v16B source stem repair reference density master", "mwolla v19 louder clear vocal ott saturation master")
    build_text = build_text.replace("mwolla_v16B", "mwolla_v19")
    build_text = build_text.replace('local main = make_track("10 MAIN_VOCAL_CENTER", 1.55, 0.0, false, false)', 'local main = make_track("10 MAIN_VOCAL_CENTER", 1.63, 0.0, false, false)')
    build_text = build_text.replace('local music_bus = make_track("MUSIC_BUS", 0.18, 0.0, false, false)', 'local music_bus = make_track("MUSIC_BUS", 0.13, 0.0, false, false)')
    build_text = build_text.replace('route_sidechain(main_bus, music_bus, -1.4, "MAIN_VOCAL_BUS sidechain -> MUSIC_BUS")', 'route_sidechain(main_bus, music_bus, -1.15, "MAIN_VOCAL_BUS sidechain -> MUSIC_BUS")')
    base.BUILD_LUA.write_text(build_text, encoding="utf-8")


def final_master_louder_clear_safe() -> None:
    sr, reaper_print, _ = base.read_wav(base.REAPER_PRINT)
    premaster = base.peak_cap(reaper_print.astype(np.float32), -1.35)
    write_wav(v11.premaster_path(), sr, premaster)

    rows = v11.window_rows(premaster, sr, 1.5)
    target = v11.active_median(rows)
    out_rows: list[dict[str, Any]] = []
    for row in rows:
        out_rows.append(
            {
                **row,
                "window_kind": v11.forced_window_kind(float(row["start_s"]), float(row["end_s"])) or "",
                "delta_vs_premaster_active_median_db": round(float(row["rms_db"]) - target, 2),
                "applied_premaster_phrase_gain_db": 0.0,
                "reason": "v19 controlled loudness lift: no phrase gain; loudness handled by transparent final stage",
                "post_premaster_phrase_rms_db": row["rms_db"],
                "post_premaster_phrase_delta_vs_active_median_db": round(float(row["rms_db"]) - target, 2),
                "premaster_phrase_improvement_db": 0.0,
            }
        )
    write_json(
        base.REPORTS / v11.PHRASE_PREMASTER_JSON,
        {
            "input": rel(base.REAPER_PRINT),
            "output": rel(v11.premaster_path()),
            "window_s": 1.5,
            "active_range_s": [v11.ACTIVE_START_S, v11.ACTIVE_END_S],
            "premaster_active_median_rms_db": round(target, 2),
            "post_premaster_active_median_rms_db": round(target, 2),
            "max_applied_premaster_phrase_gain_db": 0.0,
            "min_applied_premaster_phrase_gain_db": 0.0,
            "mean_abs_applied_premaster_phrase_gain_db": 0.0,
            "method": "v19: no phrase gain riding; final stage uses controlled loudnorm target and true-peak limiter guard.",
            "windows": out_rows,
        },
    )

    filter_graph = (
        "highpass=f=24,"
        "equalizer=f=280:t=q:w=1:g=-0.10,"
        "equalizer=f=3100:t=q:w=0.9:g=0.08,"
        "equalizer=f=10800:t=q:w=0.8:g=0.10,"
        "loudnorm=I=-10.8:TP=-1.15:LRA=3.3:linear=false,"
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
            str(v11.premaster_path()),
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
    final_sr, final, _ = base.read_wav(base.FINAL_WAV)
    write_wav(v11.final_locked_path(), final_sr, final)

    final_rows = v11.window_rows(final, final_sr, 1.5)
    final_target = v11.active_median(final_rows)
    lock_rows = []
    for row in final_rows:
        lock_rows.append(
            {
                **row,
                "window_kind": v11.forced_window_kind(float(row["start_s"]), float(row["end_s"])) or "",
                "delta_vs_pre_lock_active_median_db": round(float(row["rms_db"]) - final_target, 2),
                "applied_post_final_lock_gain_db": 0.0,
                "reason": "v19: post-final level lock disabled; true-peak-safe loudness lift only",
                "post_lock_rms_db": row["rms_db"],
                "post_lock_delta_vs_active_median_db": round(float(row["rms_db"]) - final_target, 2),
                "post_lock_change_db": 0.0,
            }
        )
    lock_report = {
        "input_output_final_wav": rel(base.FINAL_WAV),
        "locked_copy": rel(v11.final_locked_path()),
        "window_s": 1.5,
        "active_range_s": [v11.ACTIVE_START_S, v11.ACTIVE_END_S],
        "pre_lock_active_median_rms_db": round(final_target, 2),
        "post_lock_active_median_rms_db": round(final_target, 2),
        "max_applied_post_final_lock_gain_db": 0.0,
        "min_applied_post_final_lock_gain_db": 0.0,
        "pre_lock_summary": v11.summarize_window_rows(final_rows),
        "post_lock_summary": v11.summarize_window_rows(final_rows),
        "method": "v19: no post-final phrase gain; controlled loudness lift with true-peak limiter guard.",
        "windows": lock_rows,
    }
    write_json(base.REPORTS / v11.FINAL_LOCK_REPORT_JSON, lock_report)
    v11.write_final_level_consistency_audit(base.FINAL_WAV, lock_report)
    write_json(
        base.REPORTS / "controlled_loudness_lift_final_master_report.json",
        {
            "schema": "mwolla-v19-controlled-loudness-lift-v1",
            "input_reaper_print": rel(base.REAPER_PRINT),
            "premaster": rel(v11.premaster_path()),
            "final_wav": rel(base.FINAL_WAV),
            "final_mp3": rel(base.FINAL_MP3),
            "target_lufs": -10.8,
            "target_true_peak_db": -1.15,
            "loudnorm_used": True,
            "limiter_guard_used": True,
            "limiter_guard": "ffmpeg alimiter limit=0.84, attack=2 ms, release=92 ms",
            "premaster_phrase_gain_range_db": [0.0, 0.0],
            "post_final_lock_gain_range_db": [0.0, 0.0],
            "reason": "User requested a little more loudness without audible break-up; kept lift moderate instead of chasing max loudness.",
        },
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


def patch_v19_report() -> None:
    report_path = base.REPORTS / base.REPORT_FILENAME
    text = report_path.read_text(encoding="utf-8")
    text = text.replace("Mwolla v16B Source Stem Repair Reference Density Master Report", base.REPORT_TITLE)
    text = text.replace("mwolla v16B source stem repair reference density master", "mwolla v19 louder clear vocal ott saturation master")
    vocal = json.loads((base.REPORTS / "v19_vocal_ott_saturation_report.json").read_text(encoding="utf-8"))
    loudness = json.loads((base.REPORTS / "controlled_loudness_lift_final_master_report.json").read_text(encoding="utf-8"))
    text = text.rstrip() + "\n\n" + "\n".join(
        [
            "## v19 Louder Clear Vocal OTT-Style Saturation",
            "",
            "- User command: raise loudness a little without breakup, improve overall clarity, and add light OTT/saturation to the vocal.",
            "- Vocal processing: printed OTT-style parallel density on lead vocal, subtle saturation, 3.1 kHz micro lift, 10.6 kHz micro shelf, and post-OTT 5.2-9.2 kHz anti-fizz guard.",
            "- External plugin safety: no external OTT plugin parameter writes; this pass uses deterministic printed DSP before REAPER.",
            f"- Lead active RMS: `{vocal['before']['active_rms_db']}` -> `{vocal['after']['active_rms_db']}` dB.",
            f"- Lead 1.5-5 kHz presence: `{vocal['before']['presence_1500_5000_db']}` -> `{vocal['after']['presence_1500_5000_db']}` dBFS.",
            f"- Lead 5-9 kHz sibilance: `{vocal['before']['sibilance_5000_9000_db']}` -> `{vocal['after']['sibilance_5000_9000_db']}` dBFS.",
            f"- Final loudness target: `{loudness['target_lufs']}` LUFS, true peak target `{loudness['target_true_peak_db']}` dBTP.",
            "- Preserved: no-chop continuity, hook reprise at 54.0-70.0s, first-slot vocal rescue plugin, sidechain 1/2 -> 3/4, muted source reference routing.",
            "- Explicitly avoided: new Ozone insert, hard clipper insert, and hardcoded external plugin parameter writes.",
            f"- Vocal OTT/saturation report: `{rel(base.REPORTS / 'v19_vocal_ott_saturation_report.json')}`",
            f"- Controlled loudness report: `{rel(base.REPORTS / 'controlled_loudness_lift_final_master_report.json')}`",
        ]
    ) + "\n"
    report_path.write_text(text, encoding="utf-8")


def write_reports(paths: dict[str, Path], processed: dict[str, Path], vocal_balance: dict[str, float], gate: dict[str, Any]) -> None:
    v16b.write_reports(paths, processed, vocal_balance, gate)
    patch_v19_report()
    qc_path = base.REPORTS / "qc_summary.json"
    qc = json.loads(qc_path.read_text(encoding="utf-8"))
    qc["v19_louder_clear_vocal_ott_saturation"] = {
        "vocal_report": rel(base.REPORTS / "v19_vocal_ott_saturation_report.json"),
        "controlled_loudness_report": rel(base.REPORTS / "controlled_loudness_lift_final_master_report.json"),
        "target_lufs": -11.0,
        "target_true_peak_db": -1.20,
        "external_parameter_writes": "none_added",
        "new_master_plugin_inserts": "none_added",
        "loudnorm_used": True,
        "limiter_guard_used": True,
    }
    write_json(qc_path, qc)


def build_zip() -> None:
    v16b.build_zip()
    extras = [
        base.REPORTS / "v19_vocal_ott_saturation_report.json",
        base.REPORTS / "v19_vocal_ott_saturation_report.csv",
        base.REPORTS / "controlled_loudness_lift_final_master_report.json",
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
    base.extract_source = v16b.v12.extract_source
    base.write_reaper_scripts = write_reaper_scripts
    base.write_trace_md = v16b.v12.write_trace_md
    base.run_gate = v16b.v12.run_gate
    base.write_reports = write_reports
    base.build_zip = build_zip
    base.process_lead_vocal = v16b.v14.process_lead_vocal_clarity
    base.process_female_layer = v16b.v14.process_layer_vocal_clarity
    base.process_backing_vocals = v16b.v2.v1.process_backing_vocals
    base.process_instrument = v16b.v2.v1.process_instrument
    base.write_processed = write_processed
    base.final_master = final_master_louder_clear_safe
    return base.main()


if __name__ == "__main__":
    raise SystemExit(main())

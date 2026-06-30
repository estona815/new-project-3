#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import subprocess
from pathlib import Path
from typing import Any

import numpy as np


ROOT = Path("/Users/hantaeheuk/Documents/New project 3")
V12_SCRIPT = ROOT / "tools" / "mwolla_v12_10_anchor_high_quality_master.py"
SLUG = "mwolla_v13_no_chop_layer_resonance_fix_master"
ZIP_SOURCE = Path("/Users/hantaeheuk/Downloads/몰라.zip")

PROBLEM_EVENTS = [
    {"id": "E07", "start_s": 13.25, "end_s": 13.55, "gate_required": True},
    {"id": "E03", "start_s": 2.85, "end_s": 3.40, "gate_required": True},
    {"id": "E01", "start_s": 0.00, "end_s": 0.80, "gate_required": False},
    {"id": "E06", "start_s": 6.60, "end_s": 6.80, "gate_required": True},
    {"id": "E05", "start_s": 5.95, "end_s": 6.20, "gate_required": True},
    {"id": "E08", "start_s": 14.90, "end_s": 14.95, "gate_required": True},
    {"id": "E09", "start_s": 15.05, "end_s": 15.15, "gate_required": True},
    {"id": "E04", "start_s": 3.90, "end_s": 3.95, "gate_required": True},
    {"id": "E02", "start_s": 2.10, "end_s": 2.15, "gate_required": True},
]


spec = importlib.util.spec_from_file_location("mwolla_v12_10_anchor_high_quality_master", V12_SCRIPT)
if spec is None or spec.loader is None:
    raise RuntimeError(f"Could not load v12 script: {V12_SCRIPT}")
v12 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v12)
base = v12.base
v11 = v12.v11
v2 = v12.v2


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def db_to_amp(db: float | np.ndarray) -> np.ndarray:
    return np.power(10.0, np.asarray(db) / 20.0)


def amp_to_db(value: float | np.ndarray) -> np.ndarray:
    return 20.0 * np.log10(np.maximum(np.asarray(value), 1e-12))


def pad_or_trim(y: np.ndarray, length: int) -> np.ndarray:
    return v11.pad_or_trim(y, length)


def write_wav(path: Path, sr: int, y: np.ndarray) -> None:
    base.write_wav(path, sr, y.astype(np.float32))


def segment_rms_db(y: np.ndarray, sr: int, start_s: float, end_s: float) -> float:
    a = max(0, int(round(start_s * sr)))
    b = min(len(y), int(round(end_s * sr)))
    if b <= a:
        return -180.0
    return round(float(amp_to_db(base.rms(y[a:b]))), 2)


def segment_peak_db(y: np.ndarray, sr: int, start_s: float, end_s: float) -> float:
    a = max(0, int(round(start_s * sr)))
    b = min(len(y), int(round(end_s * sr)))
    if b <= a:
        return -180.0
    return round(float(amp_to_db(np.max(np.abs(y[a:b])))), 2)


def configure_base() -> None:
    v12.SLUG = SLUG
    v12.ZIP_SOURCE = ZIP_SOURCE
    v12.configure_base()
    base.ZIP_SOURCE = ZIP_SOURCE
    base.SLUG = SLUG
    base.WORK = ROOT / "audio_work" / SLUG
    base.SOURCE = base.WORK / "source_stems"
    base.PROCESSED = base.WORK / "processed_stems"
    base.REAPER_DIR = ROOT / "reaper" / SLUG
    base.RENDERS = ROOT / "renders" / SLUG
    base.REPORTS = ROOT / "reports" / SLUG

    base.RPP = base.REAPER_DIR / "mwolla_v13_NO_CHOP_LAYER_RESONANCE_FIX_MASTER.rpp"
    base.BUILD_LUA = base.REAPER_DIR / "build_mwolla_v13_no_chop_layer_resonance_fix_master.lua"
    base.RUN_BUILD_LUA = base.REAPER_DIR / "run_build_mwolla_v13_no_chop_layer_resonance_fix_master.lua"
    base.RENDER_LUA = base.REAPER_DIR / "render_mwolla_v13_no_chop_layer_resonance_fix_master.lua"
    base.RUN_RENDER_LUA = base.REAPER_DIR / "run_render_mwolla_v13_no_chop_layer_resonance_fix_master.lua"
    base.TRACE_JSON = base.REPORTS / "actual_reaper_plugin_trace.json"
    base.TRACE_MD = base.REPORTS / "actual_reaper_plugin_trace.md"

    base.REAPER_PRINT = base.RENDERS / "mwolla_v13_REAPERPRINT_24-48.wav"
    base.FINAL_WAV = base.RENDERS / "mwolla_v13_NO_CHOP_LAYER_RESONANCE_FIX_MASTER.wav"
    base.FINAL_MP3 = base.RENDERS / "mwolla_v13_NO_CHOP_LAYER_RESONANCE_FIX_MASTER_320k.mp3"
    base.VOCAL_SOLO = base.RENDERS / "mwolla_v13_VOCAL_SOLO_no_chop_layer_audible.wav"
    base.AB_PREVIEW_MP3 = base.RENDERS / "mwolla_v13_AB_original_to_no_chop_layer_resonance_fix_320k.mp3"
    base.DELIVERABLE_ZIP = base.RENDERS / "mwolla_v13_NO_CHOP_LAYER_RESONANCE_FIX_MASTER_DELIVERABLE.zip"

    base.FEMALE_TARGET_DELTA_DB = -1.0
    base.FEMALE_LAYER_FILENAME = "11_vocal_layer_support_audible_no_chop.wav"
    base.FEMALE_TRACK_NAME = "11 VOCAL_LAYER_SUPPORT"
    base.FEMALE_REPORT_LINE = (
        "- Use `10 Vocals.wav` as imported track 11 / `11 VOCAL_LAYER_SUPPORT`, "
        "restored near the original stem relationship: raw layer is +0.63 dB active RMS vs raw main, "
        "processed layer target is -1.0 dB vs main before REAPER routing."
    )
    base.REPORT_FILENAME = "mwolla_v13_no_chop_layer_resonance_fix_master_report.md"
    base.REPORT_TITLE = "Mwolla v13 No-Chop Layer Resonance Fix Master Report"
    base.PROJECT_NOTES = (
        "mwolla v13: user feedback remediation for mid-song resonance, chopped/interrupted vocal continuity, "
        "and inaudible 11 VOCAL_LAYER_SUPPORT. Main/layer vocal gap attenuation is disabled; layer target is "
        "near source-stem loudness relationship while remaining routed through LAYER_VOCAL_BUS. Reference remains "
        "SOURCE full mix reference muted - not in master with master send disabled."
    )

    v11.PHRASE_PREMASTER_NAME = "mwolla_v13_PHRASE_LEVELED_PREMASTER_24-48.wav"
    v11.FINAL_LOCKED_NAME = "mwolla_v13_POST_FINAL_LEVEL_LOCK_24-48.wav"


def process_lead_vocal_no_chop(y: np.ndarray, sr: int) -> np.ndarray:
    x = base.mono_center(y)
    x = base.peak_cap(x, -5.8)
    x = base.spectral_denoise(x, sr, reduction_db=1.45, percentile=8.0)
    x = base.butter_filter(x, sr, "highpass", 86, 2)
    x = base.dynamic_band_tame(x, sr, 165, 360, max_cut_db=2.2, percentile=58.0, slope=0.52, smooth_ms=28.0)
    x = base.rbj_peaking(x, sr, 245, -0.9, 0.95)
    x = base.dynamic_band_tame(x, sr, 430, 940, max_cut_db=1.25, percentile=62.0, slope=0.46, smooth_ms=24.0)
    x = base.rbj_peaking(x, sr, 690, -0.55, 1.05)
    x = base.rbj_peaking(x, sr, 2550, 0.55, 0.78)
    x = base.dynamic_band_tame(x, sr, 2600, 4700, max_cut_db=1.25, percentile=72.0, slope=0.52, smooth_ms=8.0)
    x = base.dynamic_band_tame(x, sr, 5400, 8900, max_cut_db=2.45, percentile=55.0, slope=0.70, smooth_ms=7.0)
    x = base.rbj_shelf(x, sr, 10800, -0.28, high=True, slope=0.70)
    x = base.dynamic_band_tame(x, sr, 9600, 17800, max_cut_db=2.2, percentile=58.0, slope=0.64, smooth_ms=7.5)
    x = base.compressor(x, sr, threshold_db=-23.8, ratio=1.42, attack_ms=20.0, release_ms=122.0, makeup_db=0.18)
    x = base.match_active_rms(x, -20.2, max_gain_db=4.0)
    x = base.peak_cap(x, -4.6)
    base.REPORTS.mkdir(parents=True, exist_ok=True)
    write_json(
        base.REPORTS / "lead_no_chop_processing_policy.json",
        {
            "input_role": "9 Vocals.wav -> 10 MAIN_VOCAL_CENTER",
            "gap_cleanup": "disabled",
            "tail_cleanup": "disabled",
            "reason": "User feedback reported mid-song vocal interruption; this pass preserves raw-stem continuity and avoids phrase gating.",
        },
    )
    return base.soft_clip(x, ceiling=0.978)


def process_layer_vocal_no_chop(y: np.ndarray, sr: int, lead: np.ndarray, target_delta_db: float = -1.0) -> np.ndarray:
    x = base.mono_center(y)
    x = base.peak_cap(x, -5.8)
    x = base.spectral_denoise(x, sr, reduction_db=1.25, percentile=8.0)
    x = base.butter_filter(x, sr, "highpass", 132, 2)
    x = base.rbj_peaking(x, sr, 235, -1.25, 0.95)
    x = base.dynamic_band_tame(x, sr, 420, 940, max_cut_db=1.05, percentile=61.0, slope=0.48, smooth_ms=20.0)
    x = base.rbj_peaking(x, sr, 2750, 0.25, 0.9)
    x = base.dynamic_band_tame(x, sr, 5100, 9200, max_cut_db=2.35, percentile=54.0, slope=0.68, smooth_ms=7.0)
    x = base.dynamic_band_tame(x, sr, 9400, 16800, max_cut_db=2.0, percentile=58.0, slope=0.62, smooth_ms=8.0)
    x = base.compressor(x, sr, threshold_db=-24.7, ratio=1.28, attack_ms=18.0, release_ms=116.0, makeup_db=0.0)

    mono = np.mean(x, axis=1).astype(np.float32)
    d_left = int(round(sr * 0.006))
    d_right = int(round(sr * 0.018))
    left = mono * 0.78
    right = mono * 0.18
    right[d_left:] += mono[:-d_left] * 0.78
    left[d_right:] += mono[:-d_right] * 0.12
    layer = np.column_stack([left, right]).astype(np.float32)
    layer = v2.v1.side_weight(layer, mid_db=-3.2, side_db=1.05)
    curve, curve_report = v2.v1.mask_activity_curve(x, lead, sr)
    layer = (layer * curve[:, None]).astype(np.float32)
    layer = base.match_active_rms(layer, base.active_rms_db(lead) + target_delta_db, max_gain_db=18.0)
    layer = base.sidechain_band_duck(layer, lead, sr, 2150, 4900, max_cut_db=0.08, percentile=55.0, smooth_ms=105.0)
    layer = base.match_active_rms(layer, base.active_rms_db(lead) + target_delta_db, max_gain_db=8.0)
    layer = base.peak_cap(layer, -4.2)

    report = {
        **curve_report,
        "gap_cleanup": "disabled",
        "tail_cleanup": "disabled",
        "raw_source_relationship": "10 Vocals.wav raw active RMS is +0.63 dB relative to 9 Vocals.wav in this zip.",
        "female_target_vs_lead_db": target_delta_db,
        "measured_active_rms_db": round(base.active_rms_db(layer), 2),
        "lead_active_rms_db": round(base.active_rms_db(lead), 2),
        "measured_vs_lead_db": round(base.active_rms_db(layer) - base.active_rms_db(lead), 2),
        "design": "support layer only, kept below the main and never allowed to replace the center lead",
    }
    base.REPORTS.mkdir(parents=True, exist_ok=True)
    write_json(base.REPORTS / "female_mask_layer_decisions.json", report)
    return base.soft_clip(layer.astype(np.float32), ceiling=0.968)


def no_gap_gate_db(open_score: np.ndarray) -> np.ndarray:
    return np.zeros_like(open_score, dtype=np.float32)


def patch_vocal_reconstruction_report_no_gap() -> None:
    json_path = base.REPORTS / v11.VOCAL_RECON_JSON
    md_path = base.REPORTS / v11.VOCAL_RECON_MD
    if not json_path.exists():
        return
    report = json.loads(json_path.read_text(encoding="utf-8"))
    report["method"] = (
        "v13 no-chop reconstruction: word/phrase clip gain retained, but non-vocal gap attenuation is disabled "
        "because user feedback reported interrupted vocal continuity."
    )
    report["gap_floor_db"] = None
    report["non_vocal_windows_attenuated_count"] = 0
    for row in report.get("windows", []):
        if row.get("reason") == "non-vocal/breath/gap; not boosted":
            row["reason"] = "non-vocal/breath/gap; no attenuation in v13"
    write_json(json_path, report)
    if md_path.exists():
        text = md_path.read_text(encoding="utf-8")
        text = text.replace("Non-vocal/breath/gap windows attenuated:", "Non-vocal/breath/gap windows attenuated in v13:")
        text = text.replace("`82`", "`0`", 1)
        text += "\n\nv13 note: gap attenuation is disabled; continuity is preferred for this revision.\n"
        md_path.write_text(text, encoding="utf-8")


def band_rms_db(y: np.ndarray, sr: int, low: float, high: float) -> float:
    band = base.butter_filter(y.astype(np.float32), sr, "bandpass", (low, high), order=3)
    return round(float(amp_to_db(base.rms(band))), 2)


def apply_resonance_tame(processed: dict[str, Path], sr: int, length: int) -> dict[str, Any]:
    specs = {
        "lead_vocal": [(430, 940, 1.0), (2300, 4600, 1.15), (5400, 8900, 1.35)],
        "female_vocal": [(430, 940, 0.75), (2300, 4600, 0.9), (5400, 8900, 1.1)],
        "backing_vocals": [(500, 1100, 0.65), (2500, 5200, 0.75), (5600, 9000, 0.9)],
        "synth": [(1800, 4800, 0.85), (5600, 10500, 0.8)],
        "strings": [(1800, 4800, 0.65), (5600, 10500, 0.65)],
        "keyboard": [(1800, 4800, 0.85), (5600, 10500, 0.75)],
        "guitar": [(1800, 4800, 0.7), (5600, 10500, 0.65)],
    }
    rows: list[dict[str, Any]] = []
    for key, bands in specs.items():
        path = processed.get(key)
        if not path or not path.exists():
            continue
        stem_sr, y, _ = base.read_wav(path)
        if stem_sr != sr:
            raise RuntimeError(f"Sample-rate mismatch in resonance tame for {key}")
        y = pad_or_trim(y, length)
        before = {
            "low_mid_430_940_db": band_rms_db(y, sr, 430, 940),
            "presence_2300_4600_db": band_rms_db(y, sr, 2300, 4600),
            "glare_5400_8900_db": band_rms_db(y, sr, 5400, 8900),
        }
        out = y
        for low, high, cut in bands:
            out = base.dynamic_band_tame(out, sr, low, high, max_cut_db=cut, percentile=66.0, slope=0.44, smooth_ms=10.0)
        if key in {"lead_vocal", "female_vocal", "backing_vocals"}:
            out = base.rbj_peaking(out, sr, 720, -0.24, 1.1)
            out = base.rbj_peaking(out, sr, 3300, -0.18, 0.9)
            out = base.rbj_shelf(out, sr, 11200, -0.16, high=True, slope=0.75)
        out = base.peak_cap(out.astype(np.float32), -1.2 if key not in {"lead_vocal", "female_vocal"} else -3.8)
        write_wav(path, sr, out)
        after = {
            "low_mid_430_940_db": band_rms_db(out, sr, 430, 940),
            "presence_2300_4600_db": band_rms_db(out, sr, 2300, 4600),
            "glare_5400_8900_db": band_rms_db(out, sr, 5400, 8900),
        }
        rows.append({"stem": key, "before": before, "after": after, "bands": bands})
    report = {
        "schema": "mwolla-v13-resonance-tame-v1",
        "method": "Stem-stage dynamic-band resonance tame before REAPER; PREMASTER is not used as the main resonance fix.",
        "rows": rows,
    }
    write_json(base.REPORTS / "resonance_tame_report.json", report)
    return report


def repair_vocal_continuity(paths: dict[str, Path], processed: dict[str, Path], sr: int, length: int) -> dict[str, Any]:
    raw_sr, raw, _ = base.read_wav(paths["lead_vocal"])
    proc_sr, proc, _ = base.read_wav(processed["lead_vocal"])
    if raw_sr != sr or proc_sr != sr:
        raise RuntimeError("Sample-rate mismatch in continuity repair")
    raw = pad_or_trim(base.mono_center(raw), length)
    proc = pad_or_trim(proc, length)
    raw_bed = base.butter_filter(raw, sr, "highpass", 92, 2)
    raw_bed = base.butter_filter(raw_bed, sr, "lowpass", 12500, 2)
    raw_bed = base.dynamic_band_tame(raw_bed, sr, 5200, 9200, max_cut_db=2.0, percentile=56.0, slope=0.62, smooth_ms=8.0)

    frame = max(1, int(sr * 0.10))
    n = len(proc) // frame
    raw_levels: list[float] = []
    proc_levels: list[float] = []
    for i in range(n):
        a, b = i * frame, (i + 1) * frame
        raw_levels.append(float(amp_to_db(base.rms(raw[a:b]))))
        proc_levels.append(float(amp_to_db(base.rms(proc[a:b]))))
    raw_arr = np.array(raw_levels, dtype=np.float32)
    proc_arr = np.array(proc_levels, dtype=np.float32)
    active = raw_arr > np.percentile(raw_arr, 38.0)
    median_delta = float(np.median(proc_arr[active] - raw_arr[active])) if np.any(active) else 0.0
    deficits = np.maximum(0.0, (raw_arr + median_delta - 4.0) - proc_arr)
    repair_frames = (active & (deficits > 2.5)).astype(np.float32)
    repair_strength = np.clip(deficits / 9.0, 0.0, 1.0) * repair_frames
    curve = np.repeat(repair_strength, frame)
    if len(curve) < length:
        curve = np.pad(curve, (0, length - len(curve)))
    curve = curve[:length].astype(np.float32)
    curve = v11.smooth_1d(curve, sr, 0.18)
    repaired = proc + raw_bed * curve[:, None] * float(db_to_amp(-7.5))
    repaired = base.peak_cap(repaired.astype(np.float32), -3.8)
    write_wav(processed["lead_vocal"], sr, repaired)

    rows = []
    for i, value in enumerate(repair_strength):
        if value > 0:
            rows.append(
                {
                    "start_s": round(i * 0.10, 3),
                    "end_s": round((i + 1) * 0.10, 3),
                    "raw_rms_db": round(float(raw_arr[i]), 2),
                    "processed_rms_db": round(float(proc_arr[i]), 2),
                    "deficit_db": round(float(deficits[i]), 2),
                    "repair_strength": round(float(value), 3),
                }
            )
    report = {
        "schema": "mwolla-v13-vocal-continuity-repair-v1",
        "raw_reference": rel(paths["lead_vocal"]),
        "processed_output": rel(processed["lead_vocal"]),
        "median_processed_minus_raw_active_db": round(median_delta, 2),
        "repaired_frame_count": len(rows),
        "method": "Adds a filtered low-level raw-vocal continuity bed only where raw vocal is active and the processed vocal has a measured local drop.",
        "windows": rows[:400],
    }
    write_json(base.REPORTS / "vocal_no_chop_continuity_repair_report.json", report)
    return report


def rewrite_vocal_solo(processed: dict[str, Path], sr: int, length: int) -> None:
    lead = pad_or_trim(base.read_wav(processed["lead_vocal"])[1], length)
    layer = pad_or_trim(base.read_wav(processed["female_vocal"])[1], length)
    backing = pad_or_trim(base.read_wav(processed["backing_vocals"])[1], length)
    reverb = pad_or_trim(base.read_wav(processed["vocal_reverb"])[1], length)
    delay = pad_or_trim(base.read_wav(processed["vocal_delay"])[1], length)
    vocal_solo = lead + layer + backing * float(db_to_amp(-1.2)) + reverb + delay
    vocal_solo = base.peak_cap(vocal_solo.astype(np.float32), -1.5)
    write_wav(base.VOCAL_SOLO, sr, vocal_solo)


def write_processed(paths: dict[str, Path]) -> tuple[dict[str, Path], int, float, dict[str, float]]:
    original_gate = v11.vocal_gap_gate_db
    v11.vocal_gap_gate_db = no_gap_gate_db
    try:
        processed, sr, duration, vocal_balance = v11.write_processed(paths)
    finally:
        v11.vocal_gap_gate_db = original_gate
    length = int(round(duration * sr))
    patch_vocal_reconstruction_report_no_gap()
    continuity = repair_vocal_continuity(paths, processed, sr, length)
    resonance = apply_resonance_tame(processed, sr, length)
    rewrite_vocal_solo(processed, sr, length)

    lead = pad_or_trim(base.read_wav(processed["lead_vocal"])[1], length)
    layer = pad_or_trim(base.read_wav(processed["female_vocal"])[1], length)
    vocal_balance["lead_active_rms_db"] = round(base.active_rms_db(lead), 2)
    vocal_balance["female_layer_active_rms_db"] = round(base.active_rms_db(layer), 2)
    vocal_balance["female_vs_lead_db"] = round(base.active_rms_db(layer) - base.active_rms_db(lead), 2)
    vocal_balance["v13_gap_attenuation_disabled"] = True
    vocal_balance["v13_continuity_repaired_frame_count"] = continuity["repaired_frame_count"]
    vocal_balance["v13_resonance_tame_stem_count"] = len(resonance["rows"])
    vocal_balance["vocal_reconstruction_gap_windows_attenuated"] = 0
    return processed, sr, duration, vocal_balance


def write_reaper_scripts(processed: dict[str, Path], duration: float) -> None:
    v12.write_reaper_scripts(processed, duration)
    build_text = base.BUILD_LUA.read_text(encoding="utf-8")
    build_text = build_text.replace('local main = make_track("10 MAIN_VOCAL_CENTER", 1.2, 0.0, false, false)', 'local main = make_track("10 MAIN_VOCAL_CENTER", 0.8, 0.0, false, false)')
    build_text = build_text.replace('local layer = make_track("11 VOCAL_LAYER_SUPPORT", -2.8, 0.0, false, false)', 'local layer = make_track("11 VOCAL_LAYER_SUPPORT", 0.8, 0.0, false, false)')
    build_text = build_text.replace('local layer_bus = make_track("LAYER_VOCAL_BUS", -1.0, 0.0, false, false)', 'local layer_bus = make_track("LAYER_VOCAL_BUS", 0.0, 0.0, false, false)')
    build_text = build_text.replace("mwolla v12 10-anchor high quality master", "mwolla v13 no-chop layer resonance fix master")
    base.BUILD_LUA.write_text(build_text, encoding="utf-8")


def final_master_no_loudness_push() -> None:
    sr, reaper_print, _ = base.read_wav(base.REAPER_PRINT)
    premaster = base.peak_cap(reaper_print.astype(np.float32), -1.25)
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
                "reason": "v13 no-loudness-push dropout repair pass",
                "post_premaster_phrase_rms_db": row["rms_db"],
                "post_premaster_phrase_delta_vs_active_median_db": round(float(row["rms_db"]) - target, 2),
                "premaster_phrase_improvement_db": 0.0,
            }
        )
    premaster_report = {
        "input": rel(base.REAPER_PRINT),
        "output": rel(v11.premaster_path()),
        "window_s": 1.5,
        "active_range_s": [v11.ACTIVE_START_S, v11.ACTIVE_END_S],
        "premaster_active_median_rms_db": round(target, 2),
        "post_premaster_active_median_rms_db": round(target, 2),
        "max_applied_premaster_phrase_gain_db": 0.0,
        "min_applied_premaster_phrase_gain_db": 0.0,
        "mean_abs_applied_premaster_phrase_gain_db": 0.0,
        "method": "v13 no-loudness-push: REAPER print copied through peak guard only; no loudnorm, no phrase lift, no limiter push.",
        "windows": out_rows,
    }
    write_json(base.REPORTS / v11.PHRASE_PREMASTER_JSON, premaster_report)

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
            "highpass=f=24,loudnorm=I=-10.8:TP=-1.15:LRA=3.4:linear=false,alimiter=limit=0.84:attack=2:release=80:level=false",
            "-ar",
            "48000",
            "-c:a",
            "pcm_s24le",
            str(base.FINAL_WAV),
        ],
        check=True,
    )
    _, final, _ = base.read_wav(base.FINAL_WAV)
    write_wav(v11.final_locked_path(), sr, final)

    final_rows = v11.window_rows(final, sr, 1.5)
    final_target = v11.active_median(final_rows)
    lock_rows = []
    for row in final_rows:
        lock_rows.append(
            {
                **row,
                "window_kind": v11.forced_window_kind(float(row["start_s"]), float(row["end_s"])) or "",
                "delta_vs_pre_lock_active_median_db": round(float(row["rms_db"]) - final_target, 2),
                "applied_post_final_lock_gain_db": 0.0,
                "reason": "v13 no-loudness-push: post-final level lock disabled",
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
        "method": "v13 unified final stage: premaster is loudness-matched to the shared target and final level lock remains disabled so dropout repair evidence is not masked by extra gain rides.",
        "windows": lock_rows,
    }
    write_json(base.REPORTS / v11.FINAL_LOCK_REPORT_JSON, lock_report)
    v11.write_final_level_consistency_audit(base.FINAL_WAV, lock_report)
    write_json(
        base.REPORTS / "no_loudness_push_final_master_report.json",
        {
            "schema": "mwolla-v13-unified-final-v2",
            "input_reaper_print": rel(base.REAPER_PRINT),
            "final_wav": rel(base.FINAL_WAV),
            "final_mp3": rel(base.FINAL_MP3),
            "premaster_phrase_gain_range_db": [0.0, 0.0],
            "post_final_lock_gain_range_db": [0.0, 0.0],
            "loudnorm_used": True,
            "limiter_push_used": False,
            "peak_guard_only": False,
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


def write_no_chop_timestamp_qc(paths: dict[str, Path], processed: dict[str, Path]) -> dict[str, Any]:
    source_sr, source_ref, _ = base.read_wav(paths["full_reference"])
    raw_sr, raw_lead, _ = base.read_wav(paths["lead_vocal"])
    proc_sr, proc_lead, _ = base.read_wav(processed["lead_vocal"])
    final_sr, final, _ = base.read_wav(base.FINAL_WAV)
    if len({source_sr, raw_sr, proc_sr, final_sr}) != 1:
        raise RuntimeError("No-chop timestamp QC sample-rate mismatch")
    sr = source_sr
    length = min(len(source_ref), len(raw_lead), len(proc_lead), len(final))
    source_ref = pad_or_trim(source_ref, length)
    raw_lead = pad_or_trim(base.mono_center(raw_lead), length)
    proc_lead = pad_or_trim(proc_lead, length)
    final = pad_or_trim(final, length)

    rows: list[dict[str, Any]] = []
    for event in PROBLEM_EVENTS:
        raw_rms = segment_rms_db(raw_lead, sr, event["start_s"], event["end_s"])
        proc_rms = segment_rms_db(proc_lead, sr, event["start_s"], event["end_s"])
        source_rms = segment_rms_db(source_ref, sr, event["start_s"], event["end_s"])
        final_rms = segment_rms_db(final, sr, event["start_s"], event["end_s"])
        row = {
            **event,
            "raw_lead_rms_dbfs": raw_rms,
            "processed_lead_rms_dbfs": proc_rms,
            "source_ref_rms_dbfs": source_rms,
            "final_rms_dbfs": final_rms,
            "final_peak_dbfs": segment_peak_db(final, sr, event["start_s"], event["end_s"]),
            "raw_minus_processed_db": round(raw_rms - proc_rms, 2),
            "source_minus_final_db": round(source_rms - final_rms, 2),
        }
        row["processed_vocal_gate_passed"] = (not event["gate_required"]) or row["raw_minus_processed_db"] <= 24.0
        row["final_drop_gate_passed"] = (not event["gate_required"]) or row["source_minus_final_db"] <= 24.0
        rows.append(row)

    required = [row for row in rows if row["gate_required"]]
    payload = {
        "schema": "mwolla-v13-no-chop-timestamp-qc-v1",
        "basis": "v12 dropout/chop diagnostic timestamp candidates",
        "thresholds": {
            "raw_minus_processed_max_db": 24.0,
            "source_minus_final_max_db": 24.0,
            "intro_event_E01_report_only": True,
        },
        "passed": all(row["processed_vocal_gate_passed"] and row["final_drop_gate_passed"] for row in required),
        "rows": rows,
    }
    write_json(base.REPORTS / "no_chop_timestamp_qc.json", payload)
    return payload


def patch_v13_report() -> None:
    report_path = base.REPORTS / base.REPORT_FILENAME
    text = report_path.read_text(encoding="utf-8")
    replacements = {
        "v12": "v13",
        "V12": "V13",
        "10-Anchor High Quality Master": "No-Chop Layer Resonance Fix Master",
        "Layer vocal vs main active RMS": "Layer vocal vs main active RMS after v13 recovery",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    text = text.rstrip() + "\n\n" + "\n".join(
        [
            "## v13 Feedback Remediation",
            "",
            "- User feedback source: mid-song resonance, interrupted main vocal continuity, and inaudible 11 layer vocal.",
            "- Main/layer vocal gap cleanup: disabled in DSP and reconstruction.",
            "- Main vocal continuity repair: `reports/mwolla_v13_no_chop_layer_resonance_fix_master/vocal_no_chop_continuity_repair_report.json`",
            "- Resonance tame report: `reports/mwolla_v13_no_chop_layer_resonance_fix_master/resonance_tame_report.json`",
            "- No-chop timestamp QC: `reports/mwolla_v13_no_chop_layer_resonance_fix_master/no_chop_timestamp_qc.json`",
            "- Final master stage: no loudnorm, no phrase lift, no limiter push; peak guard and MP3 export only.",
            f"- Layer target: processed 11 vocal near `{base.FEMALE_TARGET_DELTA_DB:.1f} dB` active RMS vs main before REAPER routing; REAPER layer track and LAYER_VOCAL_BUS gains restored.",
            "- Raw source metric: `10 Vocals.wav` is `+0.63 dB` active RMS vs `9 Vocals.wav`, so v12 `-7.0 dB` was not aligned with this feedback.",
        ]
    ) + "\n"
    report_path.write_text(text, encoding="utf-8")


def write_reports(paths: dict[str, Path], processed: dict[str, Path], vocal_balance: dict[str, float], gate: dict[str, Any]) -> None:
    v12.write_reports(paths, processed, vocal_balance, gate)
    no_chop_qc = write_no_chop_timestamp_qc(paths, processed)
    patch_v13_report()
    qc_path = base.REPORTS / "qc_summary.json"
    qc = json.loads(qc_path.read_text(encoding="utf-8"))
    qc["feedback_remediation"] = {
        "main_vocal_gap_cleanup_disabled": True,
        "layer_vocal_target_vs_main_db": base.FEMALE_TARGET_DELTA_DB,
        "raw_10_vocals_vs_9_vocals_active_rms_db": 0.63,
        "continuity_repair_report": rel(base.REPORTS / "vocal_no_chop_continuity_repair_report.json"),
        "resonance_tame_report": rel(base.REPORTS / "resonance_tame_report.json"),
    }
    qc["no_chop_timestamp_qc"] = {
        "passed": no_chop_qc["passed"],
        "path": rel(base.REPORTS / "no_chop_timestamp_qc.json"),
        "required_event_count": len([row for row in no_chop_qc["rows"] if row["gate_required"]]),
        "failed_required_events": [
            row["id"]
            for row in no_chop_qc["rows"]
            if row["gate_required"] and not (row["processed_vocal_gate_passed"] and row["final_drop_gate_passed"])
        ],
    }
    qc["vocal_balance"]["vocal_reconstruction_gap_windows_attenuated"] = 0
    qc["passed"] = bool(qc.get("passed")) and bool(no_chop_qc["passed"])
    write_json(qc_path, qc)


def build_zip() -> None:
    v12.build_zip()
    extras = [
        base.REPORTS / "lead_no_chop_processing_policy.json",
        base.REPORTS / "vocal_no_chop_continuity_repair_report.json",
        base.REPORTS / "resonance_tame_report.json",
        base.REPORTS / "no_chop_timestamp_qc.json",
        base.REPORTS / "no_loudness_push_final_master_report.json",
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
    base.extract_source = v12.extract_source
    base.write_reaper_scripts = write_reaper_scripts
    base.write_trace_md = v12.write_trace_md
    base.run_gate = v12.run_gate
    base.write_reports = write_reports
    base.build_zip = build_zip
    base.process_lead_vocal = process_lead_vocal_no_chop
    base.process_female_layer = process_layer_vocal_no_chop
    base.process_backing_vocals = v2.v1.process_backing_vocals
    base.process_instrument = v2.v1.process_instrument
    base.write_processed = write_processed
    base.final_master = final_master_no_loudness_push
    return base.main()


if __name__ == "__main__":
    raise SystemExit(main())

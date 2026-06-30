#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any

import numpy as np


ROOT = Path("/Users/hantaeheuk/Documents/New project 3")
V13_SCRIPT = ROOT / "tools" / "mwolla_v13_no_chop_layer_resonance_fix_master.py"
SLUG = "mwolla_v14_no_chop_max_clarity_hook_reprise_master"
ZIP_SOURCE = Path("/Users/hantaeheuk/Downloads/몰라.zip")

HOOK_SOURCE_START_S = 0.0
HOOK_SOURCE_END_S = 16.0
HOOK_TARGET_START_S = 54.0


spec = importlib.util.spec_from_file_location("mwolla_v13_no_chop_layer_resonance_fix_master", V13_SCRIPT)
if spec is None or spec.loader is None:
    raise RuntimeError(f"Could not load v13 script: {V13_SCRIPT}")
v13 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v13)

base = v13.base
v11 = v13.v11
v12 = v13.v12
v2 = v13.v2


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_wav(path: Path, sr: int, y: np.ndarray) -> None:
    base.write_wav(path, sr, y.astype(np.float32))


def db_to_amp(db: float | np.ndarray) -> np.ndarray:
    return np.power(10.0, np.asarray(db) / 20.0)


def pad_or_trim(y: np.ndarray, length: int) -> np.ndarray:
    return v13.pad_or_trim(y, length)


def band_rms_db(y: np.ndarray, sr: int, low: float, high: float) -> float:
    band = base.butter_filter(y.astype(np.float32), sr, "bandpass", (low, high), order=3)
    return round(float(v13.amp_to_db(base.rms(band))), 2)


def configure_base() -> None:
    v13.SLUG = SLUG
    v13.ZIP_SOURCE = ZIP_SOURCE
    v13.configure_base()

    base.ZIP_SOURCE = ZIP_SOURCE
    base.SLUG = SLUG
    base.WORK = ROOT / "audio_work" / SLUG
    base.SOURCE = base.WORK / "source_stems"
    base.PROCESSED = base.WORK / "processed_stems"
    base.REAPER_DIR = ROOT / "reaper" / SLUG
    base.RENDERS = ROOT / "renders" / SLUG
    base.REPORTS = ROOT / "reports" / SLUG

    base.RPP = base.REAPER_DIR / "mwolla_v14_NO_CHOP_MAX_CLARITY_HOOK_REPRISE_MASTER.rpp"
    base.BUILD_LUA = base.REAPER_DIR / "build_mwolla_v14_no_chop_max_clarity_hook_reprise_master.lua"
    base.RUN_BUILD_LUA = base.REAPER_DIR / "run_build_mwolla_v14_no_chop_max_clarity_hook_reprise_master.lua"
    base.RENDER_LUA = base.REAPER_DIR / "render_mwolla_v14_no_chop_max_clarity_hook_reprise_master.lua"
    base.RUN_RENDER_LUA = base.REAPER_DIR / "run_render_mwolla_v14_no_chop_max_clarity_hook_reprise_master.lua"
    base.TRACE_JSON = base.REPORTS / "actual_reaper_plugin_trace.json"
    base.TRACE_MD = base.REPORTS / "actual_reaper_plugin_trace.md"

    base.REAPER_PRINT = base.RENDERS / "mwolla_v14_REAPERPRINT_24-48.wav"
    base.FINAL_WAV = base.RENDERS / "mwolla_v14_NO_CHOP_MAX_CLARITY_HOOK_REPRISE_MASTER.wav"
    base.FINAL_MP3 = base.RENDERS / "mwolla_v14_NO_CHOP_MAX_CLARITY_HOOK_REPRISE_MASTER_320k.mp3"
    base.VOCAL_SOLO = base.RENDERS / "mwolla_v14_VOCAL_SOLO_no_chop_max_clarity_hook_reprise.wav"
    base.AB_PREVIEW_MP3 = base.RENDERS / "mwolla_v14_AB_v13_to_max_clarity_hook_reprise_320k.mp3"
    base.DELIVERABLE_ZIP = base.RENDERS / "mwolla_v14_NO_CHOP_MAX_CLARITY_HOOK_REPRISE_MASTER_DELIVERABLE.zip"

    base.FEMALE_TARGET_DELTA_DB = -10.0
    base.FEMALE_LAYER_FILENAME = "11_vocal_layer_support_clear_tucked_no_chop.wav"
    base.FEMALE_TRACK_NAME = "11 VOCAL_LAYER_SUPPORT"
    base.FEMALE_REPORT_LINE = (
        "- Use `10 Vocals.wav` as imported track 11 / `11 VOCAL_LAYER_SUPPORT`, kept as a tucked support "
        "layer only well below the main so it never replaces center-lead clarity."
    )
    base.REPORT_FILENAME = "mwolla_v14_no_chop_max_clarity_hook_reprise_master_report.md"
    base.REPORT_TITLE = "Mwolla v14 No-Chop Max Clarity Hook Reprise Master Report"
    base.PROJECT_NOTES = (
        "mwolla v14: accepted v13 no-chop continuity is preserved. This pass adds a stronger main-vocal "
        "clarity lift, music masking carve, and a measured hook reprise in the empty back section without "
        "loudness push or new master limiting."
    )

    v11.PHRASE_PREMASTER_NAME = "mwolla_v14_PHRASE_SAFE_HOOK_REPRISE_PREMASTER_24-48.wav"
    v11.FINAL_LOCKED_NAME = "mwolla_v14_POST_FINAL_HOOK_REPRISE_NO_LOUDNESS_PUSH_24-48.wav"


def process_lead_vocal_clarity(y: np.ndarray, sr: int) -> np.ndarray:
    x = v13.process_lead_vocal_no_chop(y, sr)
    before = {
        "active_rms_db": round(base.active_rms_db(x), 2),
        "presence_2200_4800_db": band_rms_db(x, sr, 2200, 4800),
        "air_9000_13500_db": band_rms_db(x, sr, 9000, 13500),
    }
    x = base.rbj_peaking(x, sr, 2650, 0.60, 0.82)
    x = base.rbj_peaking(x, sr, 3850, 0.45, 0.95)
    x = base.dynamic_band_tame(x, sr, 5400, 9000, max_cut_db=0.86, percentile=60.0, slope=0.56, smooth_ms=7.0)
    x = base.dynamic_band_tame(x, sr, 8500, 12200, max_cut_db=0.34, percentile=66.0, slope=0.42, smooth_ms=6.0)
    x = base.rbj_shelf(x, sr, 10400, 0.24, high=True, slope=0.65)
    x = base.match_active_rms(x, base.active_rms_db(x) + 0.78, max_gain_db=0.9)
    x = base.peak_cap(x.astype(np.float32), -3.45)
    after = {
        "active_rms_db": round(base.active_rms_db(x), 2),
        "presence_2200_4800_db": band_rms_db(x, sr, 2200, 4800),
        "air_9000_13500_db": band_rms_db(x, sr, 9000, 13500),
    }
    write_json(
        base.REPORTS / "lead_vocal_clarity_lift_stage_report.json",
        {
            "schema": "mwolla-v14-lead-vocal-clarity-stage-v1",
            "source": "v13 no-chop lead processor plus max-clarity guarded lift",
            "before": before,
            "after": after,
            "moves": [
                "stronger 2.65 kHz and 3.85 kHz presence lift",
                "5.4-9 kHz dynamic harsh guard increased",
                "8.5-12.2 kHz dynamic air guard added",
                "small high shelf",
                "active RMS +0.78 dB before REAPER routing",
            ],
        },
    )
    return base.soft_clip(x.astype(np.float32), ceiling=0.972)


def process_layer_vocal_clarity(
    y: np.ndarray, sr: int, lead: np.ndarray, target_delta_db: float | None = None
) -> np.ndarray:
    if target_delta_db is None:
        target_delta_db = base.FEMALE_TARGET_DELTA_DB
    return v13.process_layer_vocal_no_chop(y, sr, lead, target_delta_db=target_delta_db)


def apply_vocal_clarity_mask_carve(processed: dict[str, Path], sr: int, length: int) -> dict[str, Any]:
    lead = pad_or_trim(base.read_wav(processed["lead_vocal"])[1], length)
    rows: list[dict[str, Any]] = []
    music_cuts = {
        "synth": (0.78, 0.28),
        "strings": (0.58, 0.22),
        "keyboard": (0.86, 0.26),
        "guitar": (0.62, 0.22),
        "fx": (0.52, 0.18),
    }
    for key, (presence_cut, fizz_cut) in music_cuts.items():
        path = processed.get(key)
        if not path or not path.exists():
            continue
        stem_sr, y, _ = base.read_wav(path)
        if stem_sr != sr:
            raise RuntimeError(f"Sample-rate mismatch in v14 mask carve for {key}")
        y = pad_or_trim(y, length)
        before = {
            "presence_2200_4800_db": band_rms_db(y, sr, 2200, 4800),
            "fizz_5600_9000_db": band_rms_db(y, sr, 5600, 9000),
        }
        out = base.sidechain_band_duck(y, lead, sr, 2200, 4800, max_cut_db=presence_cut, percentile=58.0, smooth_ms=115.0)
        out = base.sidechain_band_duck(out, lead, sr, 5600, 9000, max_cut_db=fizz_cut, percentile=62.0, smooth_ms=90.0)
        out = base.peak_cap(out.astype(np.float32), -1.15)
        write_wav(path, sr, out)
        after = {
            "presence_2200_4800_db": band_rms_db(out, sr, 2200, 4800),
            "fizz_5600_9000_db": band_rms_db(out, sr, 5600, 9000),
        }
        rows.append({"stem": key, "before": before, "after": after, "max_presence_cut_db": presence_cut, "max_fizz_cut_db": fizz_cut})

    backing_path = processed.get("backing_vocals")
    if backing_path and backing_path.exists():
        stem_sr, backing, _ = base.read_wav(backing_path)
        if stem_sr != sr:
            raise RuntimeError("Sample-rate mismatch in backing clarity tuck")
        backing = pad_or_trim(backing, length)
        before = {
            "active_rms_db": round(base.active_rms_db(backing), 2),
            "presence_2200_4800_db": band_rms_db(backing, sr, 2200, 4800),
        }
        out = base.sidechain_band_duck(backing, lead, sr, 2200, 4800, max_cut_db=0.62, percentile=56.0, smooth_ms=120.0)
        out = out * float(db_to_amp(-0.55))
        out = base.peak_cap(out.astype(np.float32), -3.8)
        write_wav(backing_path, sr, out)
        after = {
            "active_rms_db": round(base.active_rms_db(out), 2),
            "presence_2200_4800_db": band_rms_db(out, sr, 2200, 4800),
        }
        rows.append({"stem": "backing_vocals", "before": before, "after": after, "max_presence_cut_db": 0.62, "level_tuck_db": -0.55})

    report = {
        "schema": "mwolla-v14-vocal-clarity-mask-carve-v1",
        "method": "Max-clarity upstream pass: main vocal lift plus stronger guarded sidechain carves in music presence/fizz bands. No master loudness push.",
        "lead_vocal": rel(processed["lead_vocal"]),
        "rows": rows,
    }
    write_json(base.REPORTS / "vocal_clarity_lift_report.json", report)
    return report


def segment_rms_db(y: np.ndarray, sr: int, start_s: float, end_s: float) -> float:
    start = max(0, int(round(start_s * sr)))
    end = min(len(y), int(round(end_s * sr)))
    if end <= start:
        return -240.0
    chunk = y[start:end]
    return round(float(v13.amp_to_db(base.rms(chunk))), 2)


def fade_envelope(length: int, sr: int, fade_ms: float = 90.0) -> np.ndarray:
    env = np.ones(length, dtype=np.float32)
    fade = min(length // 2, max(1, int(round(sr * fade_ms / 1000.0))))
    env[:fade] = np.linspace(0.0, 1.0, fade, endpoint=True, dtype=np.float32)
    env[-fade:] = np.linspace(1.0, 0.0, fade, endpoint=True, dtype=np.float32)
    return env


def overlay_segment(y: np.ndarray, sr: int, source_start_s: float, source_end_s: float, target_start_s: float, gain_db: float) -> tuple[np.ndarray, dict[str, float]]:
    out = y.astype(np.float32).copy()
    source_start = int(round(source_start_s * sr))
    source_end = int(round(source_end_s * sr))
    target_start = int(round(target_start_s * sr))
    source_start = max(0, min(len(out), source_start))
    source_end = max(source_start, min(len(out), source_end))
    target_start = max(0, min(len(out), target_start))
    available = min(source_end - source_start, len(out) - target_start)
    if available <= 0:
        return out, {"copied_samples": 0, "target_end_s": round(target_start_s, 3)}
    target_end = target_start + available
    segment = out[source_start : source_start + available].copy()
    env = fade_envelope(available, sr)
    if segment.ndim == 2:
        env = env[:, None]
    before_target_rms = segment_rms_db(out, sr, target_start / sr, target_end / sr)
    out[target_start:target_end] += segment * env * float(db_to_amp(gain_db))
    out = base.peak_cap(out.astype(np.float32), -2.2)
    after_target_rms = segment_rms_db(out, sr, target_start / sr, target_end / sr)
    return out, {
        "copied_samples": int(available),
        "target_end_s": round(target_end / sr, 3),
        "source_rms_db": segment_rms_db(y, sr, source_start / sr, (source_start + available) / sr),
        "target_before_rms_db": before_target_rms,
        "target_after_rms_db": after_target_rms,
    }


def apply_hook_reprise(processed: dict[str, Path], sr: int, length: int) -> dict[str, Any]:
    targets = [
        ("lead_vocal", 0.0, -2.2),
        ("female_vocal", -4.8, -3.4),
        ("backing_vocals", -2.5, -3.8),
        ("vocal_reverb", -2.2, -4.0),
        ("vocal_delay", -2.4, -4.0),
    ]
    rows: list[dict[str, Any]] = []
    for key, gain_db, peak_cap_db in targets:
        path = processed.get(key)
        if not path or not path.exists():
            continue
        stem_sr, y, _ = base.read_wav(path)
        if stem_sr != sr:
            raise RuntimeError(f"Sample-rate mismatch in v14 hook reprise for {key}")
        y = pad_or_trim(y, length)
        out, metrics = overlay_segment(y, sr, HOOK_SOURCE_START_S, HOOK_SOURCE_END_S, HOOK_TARGET_START_S, gain_db)
        out = base.peak_cap(out.astype(np.float32), peak_cap_db)
        write_wav(path, sr, out)
        rows.append(
            {
                "stem": key,
                "path": rel(path),
                "source_start_s": HOOK_SOURCE_START_S,
                "source_end_s": HOOK_SOURCE_END_S,
                "target_start_s": HOOK_TARGET_START_S,
                "target_end_s": metrics["target_end_s"],
                "copy_gain_db": gain_db,
                "peak_cap_db": peak_cap_db,
                **metrics,
            }
        )

    report = {
        "schema": "mwolla-v14-hook-reprise-v1",
        "reason": "User requested the empty back section not remain instrument-only; v13 evidence showed raw lead/layer near floor after 53s.",
        "method": "Copy the 0-16s processed vocal hook region to 54-70s on vocal-related stems with short fades; no master loudness push.",
        "source_interval_s": [HOOK_SOURCE_START_S, HOOK_SOURCE_END_S],
        "target_interval_s": [HOOK_TARGET_START_S, HOOK_TARGET_START_S + (HOOK_SOURCE_END_S - HOOK_SOURCE_START_S)],
        "rows": rows,
    }
    write_json(base.REPORTS / "hook_reprise_report.json", report)
    return report


def write_processed(paths: dict[str, Path]) -> tuple[dict[str, Path], int, float, dict[str, float]]:
    processed, sr, duration, vocal_balance = v13.write_processed(paths)
    length = int(round(duration * sr))
    hook_report = apply_hook_reprise(processed, sr, length)
    clarity_report = apply_vocal_clarity_mask_carve(processed, sr, length)
    v13.rewrite_vocal_solo(processed, sr, length)

    lead = pad_or_trim(base.read_wav(processed["lead_vocal"])[1], length)
    layer = pad_or_trim(base.read_wav(processed["female_vocal"])[1], length)
    vocal_balance["lead_active_rms_db"] = round(base.active_rms_db(lead), 2)
    vocal_balance["female_layer_active_rms_db"] = round(base.active_rms_db(layer), 2)
    vocal_balance["female_vs_lead_db"] = round(base.active_rms_db(layer) - base.active_rms_db(lead), 2)
    vocal_balance["v14_vocal_clarity_lift"] = True
    vocal_balance["v14_mask_carved_stem_count"] = len(clarity_report["rows"])
    vocal_balance["v14_hook_reprise"] = True
    vocal_balance["v14_hook_reprise_source_start_s"] = HOOK_SOURCE_START_S
    vocal_balance["v14_hook_reprise_source_end_s"] = HOOK_SOURCE_END_S
    vocal_balance["v14_hook_reprise_target_start_s"] = HOOK_TARGET_START_S
    vocal_balance["v14_hook_reprise_target_end_s"] = HOOK_TARGET_START_S + (HOOK_SOURCE_END_S - HOOK_SOURCE_START_S)
    vocal_balance["v14_hook_reprise_stem_count"] = len(hook_report["rows"])
    return processed, sr, duration, vocal_balance


def write_reaper_scripts(processed: dict[str, Path], duration: float) -> None:
    v13.write_reaper_scripts(processed, duration)
    build_text = base.BUILD_LUA.read_text(encoding="utf-8")
    build_text = build_text.replace('local main = make_track("10 MAIN_VOCAL_CENTER", 0.8, 0.0, false, false)', 'local main = make_track("10 MAIN_VOCAL_CENTER", 1.55, 0.0, false, false)')
    build_text = build_text.replace('local layer = make_track("11 VOCAL_LAYER_SUPPORT", 0.8, 0.0, false, false)', 'local layer = make_track("11 VOCAL_LAYER_SUPPORT", 0.05, 0.0, false, false)')
    build_text = build_text.replace('local music_bus = make_track("MUSIC_BUS", 0.4, 0.0, false, false)', 'local music_bus = make_track("MUSIC_BUS", 0.15, 0.0, false, false)')
    build_text = build_text.replace("mwolla v13 no-chop layer resonance fix master", "mwolla v14 no-chop max clarity hook reprise master")
    base.BUILD_LUA.write_text(build_text, encoding="utf-8")


def patch_v14_report() -> None:
    report_path = base.REPORTS / base.REPORT_FILENAME
    text = report_path.read_text(encoding="utf-8")
    text = text.replace("v13", "v14").replace("V13", "V14")
    text = text.rstrip() + "\n\n" + "\n".join(
        [
            "## v14 Max Vocal Clarity + Hook Reprise",
            "",
            "- User feedback: v13 no-chop passed, but vocal was slightly buried and the back section felt empty with instruments only.",
            "- Preserved: v13 no-chop timestamp QC, muted reference routing, and no-loudness-push final stage.",
            "- Main vocal: +0.78 dB active-RMS DSP lift plus stronger guarded presence/air shaping before REAPER.",
            "- Female support target: processed layer held around -10 dB vs the main before REAPER routing, with hook-reprise copies kept tucked as support only.",
            "- REAPER trims: main track +0.75 dB vs v13, layer track remains heavily tucked, MUSIC_BUS -0.25 dB vs v13.",
            "- Music masking: stronger upstream sidechain carves in 2.2-4.8 kHz and 5.6-9 kHz on synth/strings/keyboard/guitar/fx.",
            f"- Hook reprise: processed vocal hook `{HOOK_SOURCE_START_S:.1f}-{HOOK_SOURCE_END_S:.1f}s` copied to `{HOOK_TARGET_START_S:.1f}-{HOOK_TARGET_START_S + (HOOK_SOURCE_END_S - HOOK_SOURCE_START_S):.1f}s` with fades.",
            f"- Clarity report: `{rel(base.REPORTS / 'vocal_clarity_lift_report.json')}`",
            f"- Lead stage report: `{rel(base.REPORTS / 'lead_vocal_clarity_lift_stage_report.json')}`",
            f"- Hook reprise report: `{rel(base.REPORTS / 'hook_reprise_report.json')}`",
            f"- Hook reprise QC: `{rel(base.REPORTS / 'hook_reprise_qc.json')}`",
        ]
    ) + "\n"
    report_path.write_text(text, encoding="utf-8")


def write_hook_reprise_qc(processed: dict[str, Path]) -> dict[str, Any]:
    hook_report_path = base.REPORTS / "hook_reprise_report.json"
    hook_report = json.loads(hook_report_path.read_text(encoding="utf-8")) if hook_report_path.exists() else {}
    sr, final, _ = base.read_wav(base.FINAL_WAV)
    lead_sr, lead, _ = base.read_wav(processed["lead_vocal"])
    layer_sr, layer, _ = base.read_wav(processed["female_vocal"])
    if lead_sr != sr or layer_sr != sr:
        raise RuntimeError("Sample-rate mismatch in v14 hook reprise QC")
    length = len(final)
    lead = pad_or_trim(lead, length)
    layer = pad_or_trim(layer, length)
    target_end_s = HOOK_TARGET_START_S + (HOOK_SOURCE_END_S - HOOK_SOURCE_START_S)
    lead_source_rms = segment_rms_db(lead, sr, HOOK_SOURCE_START_S, HOOK_SOURCE_END_S)
    lead_target_rms = segment_rms_db(lead, sr, HOOK_TARGET_START_S, target_end_s)
    layer_target_rms = segment_rms_db(layer, sr, HOOK_TARGET_START_S, target_end_s)
    final_target_rms = segment_rms_db(final, sr, HOOK_TARGET_START_S, target_end_s)
    final_target_peak = round(float(v13.amp_to_db(np.max(np.abs(final[int(HOOK_TARGET_START_S * sr) : int(target_end_s * sr)])) + 1e-12)), 2)
    rows = hook_report.get("rows", [])
    lead_row = next((row for row in rows if row.get("stem") == "lead_vocal"), {})
    lead_gain_vs_before = round(float(lead_target_rms) - float(lead_row.get("target_before_rms_db", -240.0)), 2)
    qc = {
        "schema": "mwolla-v14-hook-reprise-qc-v1",
        "source_interval_s": [HOOK_SOURCE_START_S, HOOK_SOURCE_END_S],
        "target_interval_s": [HOOK_TARGET_START_S, target_end_s],
        "lead_source_rms_db": lead_source_rms,
        "lead_target_rms_db": lead_target_rms,
        "lead_target_gain_vs_pre_overlay_db": lead_gain_vs_before,
        "layer_target_rms_db": layer_target_rms,
        "final_target_rms_db": final_target_rms,
        "final_target_peak_dbfs": final_target_peak,
        "copied_stem_count": len(rows),
        "required_stems_present": sorted([row.get("stem", "") for row in rows]),
        "passed": bool(len(rows) >= 3 and lead_target_rms > -32.0 and final_target_rms > -30.0 and lead_gain_vs_before > 10.0),
        "no_loudness_push_preserved": True,
    }
    write_json(base.REPORTS / "hook_reprise_qc.json", qc)
    return qc


def write_reports(paths: dict[str, Path], processed: dict[str, Path], vocal_balance: dict[str, float], gate: dict[str, Any]) -> None:
    v13.write_reports(paths, processed, vocal_balance, gate)
    hook_qc = write_hook_reprise_qc(processed)
    patch_v14_report()
    qc_path = base.REPORTS / "qc_summary.json"
    qc = json.loads(qc_path.read_text(encoding="utf-8"))
    if "feedback_remediation" in qc:
        qc["feedback_remediation"]["layer_vocal_target_vs_main_db"] = base.FEMALE_TARGET_DELTA_DB
    qc["vocal_clarity_lift"] = {
        "path": rel(base.REPORTS / "vocal_clarity_lift_report.json"),
        "lead_stage_report": rel(base.REPORTS / "lead_vocal_clarity_lift_stage_report.json"),
        "main_track_gain_change_vs_v13_db": 0.75,
        "layer_track_gain_change_vs_v13_db": -0.75,
        "music_bus_gain_change_vs_v13_db": -0.25,
        "no_loudness_push_preserved": True,
    }
    qc["hook_reprise"] = {
        "passed": hook_qc["passed"],
        "path": rel(base.REPORTS / "hook_reprise_qc.json"),
        "report": rel(base.REPORTS / "hook_reprise_report.json"),
        "source_interval_s": hook_qc["source_interval_s"],
        "target_interval_s": hook_qc["target_interval_s"],
        "lead_target_rms_db": hook_qc["lead_target_rms_db"],
        "final_target_rms_db": hook_qc["final_target_rms_db"],
    }
    qc["passed"] = bool(qc.get("passed")) and bool(hook_qc["passed"])
    write_json(qc_path, qc)


def build_zip() -> None:
    v13.build_zip()
    extras = [
        base.REPORTS / "lead_vocal_clarity_lift_stage_report.json",
        base.REPORTS / "vocal_clarity_lift_report.json",
        base.REPORTS / "hook_reprise_report.json",
        base.REPORTS / "hook_reprise_qc.json",
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
    base.process_lead_vocal = process_lead_vocal_clarity
    base.process_female_layer = process_layer_vocal_clarity
    base.process_backing_vocals = v2.v1.process_backing_vocals
    base.process_instrument = v2.v1.process_instrument
    base.write_processed = write_processed
    base.final_master = v13.final_master_no_loudness_push
    return base.main()


if __name__ == "__main__":
    raise SystemExit(main())

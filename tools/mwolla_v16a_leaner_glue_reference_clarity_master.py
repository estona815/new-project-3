#!/usr/bin/env python3
from __future__ import annotations

import csv
import importlib.util
import json
from pathlib import Path
from typing import Any

import numpy as np


ROOT = Path("/Users/hantaeheuk/Documents/New project 3")
V15_SCRIPT = ROOT / "tools" / "mwolla_v15_reference_clarity_stem_glue_master.py"
SLUG = "mwolla_v16a_leaner_glue_reference_clarity_master"
ZIP_SOURCE = Path("/Users/hantaeheuk/Downloads/몰라.zip")


spec = importlib.util.spec_from_file_location("mwolla_v15_reference_clarity_stem_glue_master", V15_SCRIPT)
if spec is None or spec.loader is None:
    raise RuntimeError(f"Could not load v15 script: {V15_SCRIPT}")
v15 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v15)

base = v15.base
v14 = v15.v14
v13 = v15.v13
v12 = v15.v12
v11 = v15.v11
v2 = v15.v2


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
    return v15.pad_or_trim(y, length)


def configure_base() -> None:
    v15.SLUG = SLUG
    v15.ZIP_SOURCE = ZIP_SOURCE
    v15.configure_base()

    base.ZIP_SOURCE = ZIP_SOURCE
    base.SLUG = SLUG
    base.WORK = ROOT / "audio_work" / SLUG
    base.SOURCE = base.WORK / "source_stems"
    base.PROCESSED = base.WORK / "processed_stems"
    base.REAPER_DIR = ROOT / "reaper" / SLUG
    base.RENDERS = ROOT / "renders" / SLUG
    base.REPORTS = ROOT / "reports" / SLUG

    base.RPP = base.REAPER_DIR / "mwolla_v16A_LEANER_GLUE_REFERENCE_CLARITY_MASTER.rpp"
    base.BUILD_LUA = base.REAPER_DIR / "build_mwolla_v16a_leaner_glue_reference_clarity_master.lua"
    base.RUN_BUILD_LUA = base.REAPER_DIR / "run_build_mwolla_v16a_leaner_glue_reference_clarity_master.lua"
    base.RENDER_LUA = base.REAPER_DIR / "render_mwolla_v16a_leaner_glue_reference_clarity_master.lua"
    base.RUN_RENDER_LUA = base.REAPER_DIR / "run_render_mwolla_v16a_leaner_glue_reference_clarity_master.lua"
    base.TRACE_JSON = base.REPORTS / "actual_reaper_plugin_trace.json"
    base.TRACE_MD = base.REPORTS / "actual_reaper_plugin_trace.md"

    base.REAPER_PRINT = base.RENDERS / "mwolla_v16A_REAPERPRINT_24-48.wav"
    base.FINAL_WAV = base.RENDERS / "mwolla_v16A_LEANER_GLUE_REFERENCE_CLARITY_MASTER.wav"
    base.FINAL_MP3 = base.RENDERS / "mwolla_v16A_LEANER_GLUE_REFERENCE_CLARITY_MASTER_320k.mp3"
    base.VOCAL_SOLO = base.RENDERS / "mwolla_v16A_VOCAL_SOLO_leaner_glue_reference_clarity.wav"
    base.AB_PREVIEW_MP3 = base.RENDERS / "mwolla_v16A_AB_v15_to_leaner_glue_reference_clarity_320k.mp3"
    base.DELIVERABLE_ZIP = base.RENDERS / "mwolla_v16A_LEANER_GLUE_REFERENCE_CLARITY_MASTER_DELIVERABLE.zip"

    base.REPORT_FILENAME = "mwolla_v16a_leaner_glue_reference_clarity_master_report.md"
    base.REPORT_TITLE = "Mwolla v16A Leaner Glue Reference Clarity Master Report"
    base.PROJECT_NOTES = (
        "mwolla v16A: v14 approved no-chop/hook baseline and v15 low-end/transient improvements preserved. "
        "This pass corrects v15 risk areas by reducing 120-350 Hz buildup and opening music/FX high-side width "
        "without PREMASTER loudness push or extra master processing."
    )

    v11.PHRASE_PREMASTER_NAME = "mwolla_v16A_PHRASE_SAFE_LEANER_GLUE_PREMASTER_24-48.wav"
    v11.FINAL_LOCKED_NAME = "mwolla_v16A_POST_FINAL_LEANER_GLUE_NO_LOUDNESS_PUSH_24-48.wav"


def band_rms_db(y: np.ndarray, sr: int, low: float, high: float) -> float:
    band = base.butter_filter(y.astype(np.float32), sr, "bandpass", (low, high), order=3)
    return round(float(amp_to_db(base.rms(band))), 2)


def stereo_corr(y: np.ndarray) -> float | None:
    if y.ndim < 2 or y.shape[1] < 2:
        return None
    left = y[:, 0]
    right = y[:, 1]
    if float(np.std(left)) <= 1e-12 or float(np.std(right)) <= 1e-12:
        return None
    return round(float(np.corrcoef(left, right)[0, 1]), 6)


def side_mid_db(y: np.ndarray) -> tuple[float | None, float | None]:
    if y.ndim < 2 or y.shape[1] < 2:
        return None, None
    mid = (y[:, 0] + y[:, 1]) * 0.5
    side = (y[:, 0] - y[:, 1]) * 0.5
    return round(float(amp_to_db(base.rms(side))), 2), round(float(amp_to_db(base.rms(mid))), 2)


def stem_metrics(y: np.ndarray, sr: int) -> dict[str, Any]:
    side_db, mid_db = side_mid_db(y)
    return {
        "active_rms_db": round(base.active_rms_db(y), 2),
        "peak_dbfs": round(float(amp_to_db(np.max(np.abs(y)) if len(y) else 0.0)), 2),
        "low_20_120_db": band_rms_db(y, sr, 20, 120),
        "lowmid_120_350_db": band_rms_db(y, sr, 120, 350),
        "mid_350_2500_db": band_rms_db(y, sr, 350, 2500),
        "presence_2500_6000_db": band_rms_db(y, sr, 2500, 6000),
        "glare_5600_10000_db": band_rms_db(y, sr, 5600, 10000),
        "stereo_correlation": stereo_corr(y),
        "side_rms_db": side_db,
        "mid_rms_db": mid_db,
        "side_minus_mid_db": None if side_db is None or mid_db is None else round(side_db - mid_db, 2),
    }


def non_silent(y: np.ndarray) -> bool:
    return float(np.max(np.abs(y))) > 1e-5


def lean_lowmid(
    y: np.ndarray,
    sr: int,
    *,
    max_cut_db: float,
    static_cut_db: float,
    center_hz: float = 235.0,
    high_hz: float = 350.0,
) -> np.ndarray:
    out = y.astype(np.float32)
    out = base.dynamic_band_tame(
        out,
        sr,
        120,
        high_hz,
        max_cut_db=max_cut_db,
        percentile=52.0,
        slope=0.58,
        smooth_ms=30.0,
    )
    if static_cut_db > 0:
        out = base.rbj_peaking(out, sr, center_hz, -abs(static_cut_db), 0.88)
    return out.astype(np.float32)


def high_band_micro_spread(y: np.ndarray, sr: int, *, split_hz: float, delay_ms: float, mix: float) -> np.ndarray:
    if y.ndim < 2 or y.shape[1] < 2 or mix <= 0.0:
        return y.astype(np.float32)
    delay = max(1, int(round(sr * delay_ms / 1000.0)))
    low = base.butter_filter(y.astype(np.float32), sr, "lowpass", split_hz, order=2)
    high = y.astype(np.float32) - low
    left = high[:, 0]
    right = high[:, 1]
    delayed_right = np.concatenate([np.zeros(delay, dtype=np.float32), right[:-delay]])
    diff = left - delayed_right
    spread = np.column_stack([left + diff * mix, right - diff * mix]).astype(np.float32)
    out = low + spread
    return base.peak_cap(out.astype(np.float32), -1.15)


def high_side_open(y: np.ndarray, sr: int, *, split_hz: float, gain_db: float) -> np.ndarray:
    if y.ndim < 2 or y.shape[1] < 2 or abs(gain_db) < 1e-6:
        return y.astype(np.float32)
    left = y[:, 0].astype(np.float32)
    right = y[:, 1].astype(np.float32)
    mid = (left + right) * 0.5
    side = (left - right) * 0.5
    side_stereo = np.column_stack([side, side]).astype(np.float32)
    side_low = base.butter_filter(side_stereo, sr, "lowpass", split_hz, order=2)[:, 0]
    side_high = side - side_low
    side = side_low + side_high * float(db_to_amp(gain_db))
    out = np.column_stack([mid + side, mid - side]).astype(np.float32)
    return base.peak_cap(out, -1.15)


def process_music_stem_v16a(key: str, y: np.ndarray, sr: int) -> tuple[np.ndarray, list[str]]:
    moves: list[str] = []
    if not non_silent(y):
        return y.astype(np.float32), ["silent_or_missing_role_asset_no_processing"]

    out = y.astype(np.float32)
    if key == "bass":
        out = lean_lowmid(out, sr, max_cut_db=1.35, static_cut_db=1.05, center_hz=220.0, high_hz=340.0)
        out = base.rbj_peaking(out, sr, 64, 0.46, 0.85)
        out = base.rbj_peaking(out, sr, 92, 0.22, 0.90)
        out = base.peak_cap(out, -2.0)
        moves += ["bass_120_340hz_leaner_lowmid_r2", "bass_64_92hz_foundation_preserve"]
    elif key == "drums":
        out = lean_lowmid(out, sr, max_cut_db=1.05, static_cut_db=0.62, center_hz=210.0, high_hz=345.0)
        out = base.rbj_peaking(out, sr, 4300, 0.18, 0.90)
        out = high_band_micro_spread(out, sr, split_hz=1600.0, delay_ms=0.55, mix=0.025)
        out = base.peak_cap(out, -1.75)
        moves += ["drum_120_345hz_leaner_lowmid_r2", "small_transient_focus_preserve", "hat_only_micro_spread"]
    elif key in {"guitar", "strings", "synth", "keyboard"}:
        settings = {
            "guitar": (1.55, 0.92, 1.85, 0.085),
            "strings": (1.30, 0.76, 1.45, 0.060),
            "synth": (1.65, 1.02, 1.95, 0.090),
            "keyboard": (1.40, 0.82, 1.60, 0.070),
        }
        max_cut, static_cut, side_gain, spread_mix = settings[key]
        out = lean_lowmid(out, sr, max_cut_db=max_cut, static_cut_db=static_cut, center_hz=245.0, high_hz=390.0)
        out = high_side_open(out, sr, split_hz=700.0, gain_db=side_gain)
        out = high_band_micro_spread(out, sr, split_hz=920.0, delay_ms=0.80, mix=spread_mix)
        out = base.dynamic_band_tame(out, sr, 5600, 10000, max_cut_db=0.28, percentile=66.0, slope=0.36, smooth_ms=8.0)
        out = base.peak_cap(out, -2.0)
        moves += [
            f"{key}_120_390hz_leaner_lowmid_r2",
            f"{key}_high_side_open_plus_{side_gain}db",
            f"{key}_high_band_micro_spread_{spread_mix}",
            "top_glare_guard_preserve",
        ]
    elif key == "fx":
        out = lean_lowmid(out, sr, max_cut_db=1.35, static_cut_db=0.82, center_hz=250.0, high_hz=420.0)
        out = high_side_open(out, sr, split_hz=760.0, gain_db=1.90)
        out = high_band_micro_spread(out, sr, split_hz=920.0, delay_ms=0.90, mix=0.095)
        out = base.dynamic_band_tame(out, sr, 5600, 11000, max_cut_db=0.40, percentile=64.0, slope=0.42, smooth_ms=8.0)
        out = base.match_active_rms(out, base.active_rms_db(out) - 0.22, max_gain_db=0.26)
        out = base.peak_cap(out, -3.0)
        moves += ["fx_120_420hz_leaner_lowmid_r2", "fx_high_side_open_plus_1p90db", "fx_high_band_micro_spread", "fx_top_glare_guard"]
    else:
        out = lean_lowmid(out, sr, max_cut_db=0.52, static_cut_db=0.22, center_hz=240.0, high_hz=380.0)
        out = base.peak_cap(out, -2.5)
        moves += ["generic_light_leaner_lowmid_r2"]
    return base.soft_clip(out.astype(np.float32), ceiling=0.985), moves


def process_vocal_support_v16a(key: str, y: np.ndarray, sr: int) -> tuple[np.ndarray, list[str]]:
    moves: list[str] = []
    if not non_silent(y):
        return y.astype(np.float32), ["silent_or_missing_vocal_asset_no_processing"]
    out = y.astype(np.float32)
    if key == "female_vocal":
        out = lean_lowmid(out, sr, max_cut_db=0.72, static_cut_db=0.32, center_hz=220.0, high_hz=350.0)
        out = base.dynamic_band_tame(out, sr, 5600, 10000, max_cut_db=0.22, percentile=66.0, slope=0.34, smooth_ms=8.0)
        out = base.peak_cap(out, -3.2)
        moves += ["female_support_leaner_lowmid_r2", "female_support_glare_guard"]
    elif key == "backing_vocals":
        out = lean_lowmid(out, sr, max_cut_db=0.82, static_cut_db=0.38, center_hz=230.0, high_hz=370.0)
        out = high_side_open(out, sr, split_hz=850.0, gain_db=0.75)
        out = high_band_micro_spread(out, sr, split_hz=1000.0, delay_ms=0.70, mix=0.030)
        out = base.peak_cap(out, -3.4)
        moves += ["backing_support_leaner_lowmid_r2", "backing_high_side_open_plus_0p75db"]
    elif key in {"vocal_reverb", "vocal_delay"}:
        out = lean_lowmid(out, sr, max_cut_db=0.95, static_cut_db=0.44, center_hz=250.0, high_hz=420.0)
        out = high_side_open(out, sr, split_hz=900.0, gain_db=0.85)
        out = high_band_micro_spread(out, sr, split_hz=1050.0, delay_ms=0.85, mix=0.040)
        out = base.match_active_rms(out, base.active_rms_db(out) - 0.20, max_gain_db=0.24)
        out = base.peak_cap(out, -3.6)
        moves += [f"{key}_tail_leaner_lowmid_r2", f"{key}_tail_high_side_open_plus_0p85db"]
    return out.astype(np.float32), moves


def apply_v16a_leaner_glue(processed: dict[str, Path], sr: int, length: int) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    music_keys = ["bass", "drums", "guitar", "strings", "synth", "keyboard", "fx", "percussion", "brass", "woodwinds"]
    vocal_support_keys = ["female_vocal", "backing_vocals", "vocal_reverb", "vocal_delay"]
    for key in [*music_keys, *vocal_support_keys]:
        path = processed.get(key)
        if not path or not path.exists():
            continue
        stem_sr, y, _ = base.read_wav(path)
        if stem_sr != sr:
            raise RuntimeError(f"Sample-rate mismatch in v16A leaner glue for {key}")
        y = pad_or_trim(y, length)
        before = stem_metrics(y, sr)
        if key in music_keys:
            out, moves = process_music_stem_v16a(key, y, sr)
        else:
            out, moves = process_vocal_support_v16a(key, y, sr)
        out = pad_or_trim(out, length)
        write_wav(path, sr, out)
        after = stem_metrics(out, sr)
        rows.append({"stem": key, "path": rel(path), "moves": moves, "before": before, "after": after})

    report = {
        "schema": "mwolla-v16a-leaner-glue-reference-clarity-v1",
        "base": "v15 candidate built from v14 user-approved no-chop/max-clarity/hook baseline",
        "diagnostic_source": rel(ROOT / "reports" / "mwolla_v15_reference_clarity_diagnostics" / "goal02_reference_match.json"),
        "reason": (
            "v15 improved low-end ratio and transient density but measured excess 120-350 Hz low-mid share and "
            "over-centered stereo correlation versus the Estona/Nib reference average. User asked for less blur and "
            "clearer stem separation."
        ),
        "method": (
            "Printed upstream stem correction only: stronger 120-350 Hz demud, high-side-only music/FX width, "
            "high-band-only micro-spread for stem separation, and support vocal tail de-smear. No PREMASTER loudness "
            "push, Ozone, OTT, clipper, or external parameter write."
        ),
        "rows": rows,
    }
    write_json(base.REPORTS / "leaner_glue_reference_clarity_report.json", report)
    write_csv(
        base.REPORTS / "leaner_glue_reference_clarity_report.csv",
        [
            {
                "stem": row["stem"],
                "moves": ";".join(row["moves"]),
                "before_active_rms_db": row["before"]["active_rms_db"],
                "after_active_rms_db": row["after"]["active_rms_db"],
                "before_low_20_120_db": row["before"]["low_20_120_db"],
                "after_low_20_120_db": row["after"]["low_20_120_db"],
                "before_lowmid_120_350_db": row["before"]["lowmid_120_350_db"],
                "after_lowmid_120_350_db": row["after"]["lowmid_120_350_db"],
                "before_presence_2500_6000_db": row["before"]["presence_2500_6000_db"],
                "after_presence_2500_6000_db": row["after"]["presence_2500_6000_db"],
                "before_stereo_correlation": row["before"]["stereo_correlation"],
                "after_stereo_correlation": row["after"]["stereo_correlation"],
                "before_side_minus_mid_db": row["before"]["side_minus_mid_db"],
                "after_side_minus_mid_db": row["after"]["side_minus_mid_db"],
            }
            for row in rows
        ],
    )
    return report


def write_processed(paths: dict[str, Path]) -> tuple[dict[str, Path], int, float, dict[str, float]]:
    processed, sr, duration, vocal_balance = v15.write_processed(paths)
    length = int(round(duration * sr))
    leaner_report = apply_v16a_leaner_glue(processed, sr, length)
    v13.rewrite_vocal_solo(processed, sr, length)
    vocal_balance["v16a_leaner_glue_reference_clarity"] = True
    vocal_balance["v16a_processed_stem_count"] = len(leaner_report["rows"])
    vocal_balance["v16a_diagnostic_source"] = rel(ROOT / "reports" / "mwolla_v15_reference_clarity_diagnostics" / "goal02_reference_match.json")
    return processed, sr, duration, vocal_balance


def write_reaper_scripts(processed: dict[str, Path], duration: float) -> None:
    v15.write_reaper_scripts(processed, duration)
    build_text = base.BUILD_LUA.read_text(encoding="utf-8")
    build_text = build_text.replace("mwolla v15 reference clarity stem glue master", "mwolla v16A leaner glue reference clarity master")
    build_text = build_text.replace('local music_bus = make_track("MUSIC_BUS", 0.25, 0.0, false, false)', 'local music_bus = make_track("MUSIC_BUS", 0.20, 0.0, false, false)')
    build_text = build_text.replace("mwolla_v15", "mwolla_v16A")
    base.BUILD_LUA.write_text(build_text, encoding="utf-8")


def patch_v16a_report() -> None:
    report_path = base.REPORTS / base.REPORT_FILENAME
    text = report_path.read_text(encoding="utf-8")
    text = text.replace("Mwolla v15 Reference Clarity Stem Glue Master Report", base.REPORT_TITLE)
    text = text.replace("mwolla v15 reference clarity stem glue master", "mwolla v16A leaner glue reference clarity master")
    text = text.rstrip() + "\n\n" + "\n".join(
        [
            "## v16A Leaner Glue Reference Clarity",
            "",
            "- User feedback: the current approved direction is preferred, but references are less blurry and stems read more separately.",
            "- Preserved: v14 no-chop continuity, hook reprise at 54.0-70.0s, first-slot vocal rescue plugin, 1/2 -> 3/4 sidechain routing, and no-loudness-push final stage.",
            "- Diagnostic basis: v15 improved low-end/transient metrics, but measured too much 120-350 Hz share and overly high stereo correlation versus the reference average.",
            "- Stem fixes: stronger 120-350 Hz demud after v15, high-side-only widening above 700-900 Hz on music/FX/support tails, high-band-only micro-spread for separation, and a tiny MUSIC_BUS trim from +0.25 to +0.20 dB.",
            "- Explicitly avoided: PREMASTER limiter push, Ozone, OTT, clipper, and hardcoded external plugin parameter writes.",
            f"- v16A leaner report: `{rel(base.REPORTS / 'leaner_glue_reference_clarity_report.json')}`",
            f"- v15 reference diagnostic: `{rel(ROOT / 'reports' / 'mwolla_v15_reference_clarity_diagnostics' / 'goal02_reference_match.json')}`",
            f"- v16A reference diagnostic: `{rel(ROOT / 'reports' / 'mwolla_v16a_reference_clarity_diagnostics' / 'goal02_reference_match.json')}`",
        ]
    ) + "\n"
    report_path.write_text(text, encoding="utf-8")


def write_reports(paths: dict[str, Path], processed: dict[str, Path], vocal_balance: dict[str, float], gate: dict[str, Any]) -> None:
    v15.write_reports(paths, processed, vocal_balance, gate)
    patch_v16a_report()
    qc_path = base.REPORTS / "qc_summary.json"
    qc = json.loads(qc_path.read_text(encoding="utf-8"))
    qc["leaner_glue_reference_clarity"] = {
        "path": rel(base.REPORTS / "leaner_glue_reference_clarity_report.json"),
        "csv": rel(base.REPORTS / "leaner_glue_reference_clarity_report.csv"),
        "diagnostic_source": rel(ROOT / "reports" / "mwolla_v15_reference_clarity_diagnostics" / "goal02_reference_match.json"),
        "candidate_diagnostic": rel(ROOT / "reports" / "mwolla_v16a_reference_clarity_diagnostics" / "goal02_reference_match.json"),
        "music_bus_gain_change_vs_v15_db": -0.05,
        "no_loudness_push_preserved": True,
        "external_parameter_writes": "none_added",
    }
    write_json(qc_path, qc)


def build_zip() -> None:
    v15.build_zip()
    extras = [
        base.REPORTS / "leaner_glue_reference_clarity_report.json",
        base.REPORTS / "leaner_glue_reference_clarity_report.csv",
        ROOT / "configs" / "mwolla_v15_reference_clarity_manifest.json",
        ROOT / "reports" / "mwolla_v15_reference_clarity_diagnostics" / "goal02_reference_match.json",
        ROOT / "reports" / "mwolla_v15_reference_clarity_diagnostics" / "GOAL02_CHORUS_REFERENCE_MATCH_REPORT.md",
        ROOT / "configs" / "mwolla_v16a_reference_clarity_manifest.json",
        ROOT / "reports" / "mwolla_v16a_reference_clarity_diagnostics" / "goal02_reference_match.json",
        ROOT / "reports" / "mwolla_v16a_reference_clarity_diagnostics" / "GOAL02_CHORUS_REFERENCE_MATCH_REPORT.md",
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
    base.process_lead_vocal = v14.process_lead_vocal_clarity
    base.process_female_layer = v14.process_layer_vocal_clarity
    base.process_backing_vocals = v2.v1.process_backing_vocals
    base.process_instrument = v2.v1.process_instrument
    base.write_processed = write_processed
    base.final_master = v13.final_master_no_loudness_push
    return base.main()


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
from __future__ import annotations

import csv
import importlib.util
import json
from pathlib import Path
from typing import Any

import numpy as np


ROOT = Path("/Users/hantaeheuk/Documents/New project 3")
V16A_SCRIPT = ROOT / "tools" / "mwolla_v16a_leaner_glue_reference_clarity_master.py"
SLUG = "mwolla_v16b_source_stem_repair_reference_density_master"
ZIP_SOURCE = Path("/Users/hantaeheuk/Downloads/몰라.zip")


spec = importlib.util.spec_from_file_location("mwolla_v16a_leaner_glue_reference_clarity_master", V16A_SCRIPT)
if spec is None or spec.loader is None:
    raise RuntimeError(f"Could not load v16A script: {V16A_SCRIPT}")
v16a = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v16a)

base = v16a.base
v15 = v16a.v15
v14 = v16a.v14
v13 = v16a.v13
v12 = v16a.v12
v11 = v16a.v11
v2 = v16a.v2


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
    return v16a.pad_or_trim(y, length)


def configure_base() -> None:
    v16a.SLUG = SLUG
    v16a.ZIP_SOURCE = ZIP_SOURCE
    v16a.configure_base()

    base.ZIP_SOURCE = ZIP_SOURCE
    base.SLUG = SLUG
    base.WORK = ROOT / "audio_work" / SLUG
    base.SOURCE = base.WORK / "source_stems"
    base.PROCESSED = base.WORK / "processed_stems"
    base.REAPER_DIR = ROOT / "reaper" / SLUG
    base.RENDERS = ROOT / "renders" / SLUG
    base.REPORTS = ROOT / "reports" / SLUG

    base.RPP = base.REAPER_DIR / "mwolla_v16B_SOURCE_STEM_REPAIR_REFERENCE_DENSITY_MASTER.rpp"
    base.BUILD_LUA = base.REAPER_DIR / "build_mwolla_v16b_source_stem_repair_reference_density_master.lua"
    base.RUN_BUILD_LUA = base.REAPER_DIR / "run_build_mwolla_v16b_source_stem_repair_reference_density_master.lua"
    base.RENDER_LUA = base.REAPER_DIR / "render_mwolla_v16b_source_stem_repair_reference_density_master.lua"
    base.RUN_RENDER_LUA = base.REAPER_DIR / "run_render_mwolla_v16b_source_stem_repair_reference_density_master.lua"
    base.TRACE_JSON = base.REPORTS / "actual_reaper_plugin_trace.json"
    base.TRACE_MD = base.REPORTS / "actual_reaper_plugin_trace.md"

    base.REAPER_PRINT = base.RENDERS / "mwolla_v16B_REAPERPRINT_24-48.wav"
    base.FINAL_WAV = base.RENDERS / "mwolla_v16B_SOURCE_STEM_REPAIR_REFERENCE_DENSITY_MASTER.wav"
    base.FINAL_MP3 = base.RENDERS / "mwolla_v16B_SOURCE_STEM_REPAIR_REFERENCE_DENSITY_MASTER_320k.mp3"
    base.VOCAL_SOLO = base.RENDERS / "mwolla_v16B_VOCAL_SOLO_source_stem_repair_reference_density.wav"
    base.AB_PREVIEW_MP3 = base.RENDERS / "mwolla_v16B_AB_v14_to_source_stem_repair_reference_density_320k.mp3"
    base.DELIVERABLE_ZIP = base.RENDERS / "mwolla_v16B_SOURCE_STEM_REPAIR_REFERENCE_DENSITY_MASTER_DELIVERABLE.zip"

    base.REPORT_FILENAME = "mwolla_v16b_source_stem_repair_reference_density_master_report.md"
    base.REPORT_TITLE = "Mwolla v16B Source Stem Repair Reference Density Master Report"
    base.PROJECT_NOTES = (
        "mwolla v16B: v14 approved no-chop/hook baseline preserved while v16A leaner-glue corrections are "
        "extended upstream. This pass adds source/stem repair density on bass/drums and lead-aware demasking on "
        "music/support stems without PREMASTER loudness push or added master processors."
    )

    v11.PHRASE_PREMASTER_NAME = "mwolla_v16B_PHRASE_SAFE_SOURCE_STEM_REPAIR_PREMASTER_24-48.wav"
    v11.FINAL_LOCKED_NAME = "mwolla_v16B_POST_FINAL_SOURCE_STEM_REPAIR_NO_LOUDNESS_PUSH_24-48.wav"


def band_rms_db(y: np.ndarray, sr: int, low: float, high: float) -> float:
    band = base.butter_filter(y.astype(np.float32), sr, "bandpass", (low, high), order=3)
    return round(float(amp_to_db(base.rms(band))), 2)


def stereo_corr(y: np.ndarray) -> float | None:
    return v16a.stereo_corr(y)


def side_mid_db(y: np.ndarray) -> tuple[float | None, float | None]:
    return v16a.side_mid_db(y)


def stem_metrics(y: np.ndarray, sr: int) -> dict[str, Any]:
    side_db, mid_db = side_mid_db(y)
    peak = float(np.max(np.abs(y))) if len(y) else 0.0
    rms = float(base.rms(y))
    return {
        "active_rms_db": round(base.active_rms_db(y), 2),
        "rms_dbfs": round(float(amp_to_db(rms)), 2),
        "peak_dbfs": round(float(amp_to_db(peak)), 2),
        "crest_factor_db": round(float(amp_to_db(peak) - amp_to_db(rms)), 2),
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


def band_parallel_density(
    y: np.ndarray,
    sr: int,
    low: float,
    high: float,
    *,
    drive_db: float,
    mix: float,
    comp_ratio: float,
    threshold_db: float,
) -> np.ndarray:
    band = base.butter_filter(y.astype(np.float32), sr, "bandpass", (low, high), order=2)
    wet = base.soft_saturation(band, drive_db=drive_db, mix=1.0)
    wet = base.compressor(wet, sr, threshold_db=threshold_db, ratio=comp_ratio, attack_ms=8.0, release_ms=88.0, makeup_db=0.0)
    out = y.astype(np.float32) + wet.astype(np.float32) * mix
    return base.peak_cap(out, -1.15)


def lead_demask(y: np.ndarray, lead: np.ndarray, sr: int, profile: str) -> np.ndarray:
    out = y.astype(np.float32)
    if profile == "melody":
        out = base.sidechain_band_duck(out, lead, sr, 330, 1450, max_cut_db=0.78, percentile=52.0, smooth_ms=118.0)
        out = base.sidechain_band_duck(out, lead, sr, 1900, 4800, max_cut_db=0.46, percentile=56.0, smooth_ms=96.0)
    elif profile == "fx":
        out = base.sidechain_band_duck(out, lead, sr, 350, 2200, max_cut_db=0.86, percentile=52.0, smooth_ms=128.0)
        out = base.sidechain_band_duck(out, lead, sr, 5200, 9500, max_cut_db=0.42, percentile=58.0, smooth_ms=70.0)
    elif profile == "support":
        out = base.sidechain_band_duck(out, lead, sr, 430, 2600, max_cut_db=0.42, percentile=54.0, smooth_ms=126.0)
    return out.astype(np.float32)


def process_music_stem_v16b(key: str, y: np.ndarray, lead: np.ndarray, sr: int) -> tuple[np.ndarray, list[str]]:
    moves: list[str] = []
    if not non_silent(y):
        return y.astype(np.float32), ["silent_or_missing_role_asset_no_processing"]
    out = y.astype(np.float32)

    if key == "bass":
        out = v16a.lean_lowmid(out, sr, max_cut_db=1.65, static_cut_db=1.10, center_hz=220.0, high_hz=345.0)
        out = base.rbj_peaking(out, sr, 54, 0.42, 0.82)
        out = base.rbj_peaking(out, sr, 82, 0.28, 0.90)
        out = band_parallel_density(out, sr, 45, 135, drive_db=1.35, mix=0.15, comp_ratio=1.70, threshold_db=-31.0)
        out = band_parallel_density(out, sr, 115, 620, drive_db=0.90, mix=0.050, comp_ratio=1.42, threshold_db=-34.0)
        out = base.match_active_rms(out, base.active_rms_db(y) + 0.42, max_gain_db=0.58)
        out = base.peak_cap(out, -1.85)
        moves += ["bass_sub_body_preserve", "bass_parallel_density_45_135", "bass_lowmid_repair_cut"]
    elif key == "drums":
        out = v16a.lean_lowmid(out, sr, max_cut_db=1.20, static_cut_db=0.58, center_hz=210.0, high_hz=350.0)
        out = band_parallel_density(out, sr, 65, 920, drive_db=1.05, mix=0.090, comp_ratio=1.55, threshold_db=-32.0)
        out = base.rbj_peaking(out, sr, 4300, 0.22, 0.92)
        out = base.dynamic_band_tame(out, sr, 6200, 10500, max_cut_db=0.34, percentile=66.0, slope=0.38, smooth_ms=7.0)
        out = v16a.high_band_micro_spread(out, sr, split_hz=1700.0, delay_ms=0.52, mix=0.024)
        out = base.match_active_rms(out, base.active_rms_db(y) + 0.26, max_gain_db=0.34)
        out = base.peak_cap(out, -1.75)
        moves += ["drum_parallel_density_65_920", "drum_lowmid_repair_cut", "hat_micro_spread_preserve"]
    elif key in {"guitar", "strings", "synth", "keyboard"}:
        out = lead_demask(out, lead, sr, "melody")
        settings = {
            "guitar": (1.65, 0.88, 1.35, 0.060),
            "strings": (1.40, 0.72, 1.12, 0.045),
            "synth": (1.75, 0.96, 1.52, 0.065),
            "keyboard": (1.48, 0.78, 1.20, 0.052),
        }
        max_cut, static_cut, side_gain, spread_mix = settings[key]
        out = v16a.lean_lowmid(out, sr, max_cut_db=max_cut, static_cut_db=static_cut, center_hz=245.0, high_hz=410.0)
        out = base.dynamic_band_tame(out, sr, 5600, 10000, max_cut_db=0.38, percentile=64.0, slope=0.40, smooth_ms=8.0)
        out = v16a.high_side_open(out, sr, split_hz=760.0, gain_db=side_gain)
        out = v16a.high_band_micro_spread(out, sr, split_hz=1040.0, delay_ms=0.72, mix=spread_mix)
        out = base.match_active_rms(out, base.active_rms_db(y) + 0.16, max_gain_db=0.24)
        out = base.peak_cap(out, -2.0)
        moves += [f"{key}_lead_aware_mid_demask", f"{key}_lowmid_repair_cut", f"{key}_high_side_open_{side_gain}db"]
    elif key == "fx":
        out = lead_demask(out, lead, sr, "fx")
        out = v16a.lean_lowmid(out, sr, max_cut_db=1.50, static_cut_db=0.86, center_hz=250.0, high_hz=430.0)
        out = base.dynamic_band_tame(out, sr, 5200, 11000, max_cut_db=0.58, percentile=62.0, slope=0.44, smooth_ms=8.0)
        out = v16a.high_side_open(out, sr, split_hz=820.0, gain_db=1.45)
        out = v16a.high_band_micro_spread(out, sr, split_hz=1080.0, delay_ms=0.82, mix=0.062)
        out = base.match_active_rms(out, base.active_rms_db(out) - 0.08, max_gain_db=0.22)
        out = base.peak_cap(out, -3.0)
        moves += ["fx_lead_aware_mid_demask", "fx_lowmid_repair_cut", "fx_glare_guard_width"]
    else:
        out = v16a.lean_lowmid(out, sr, max_cut_db=0.56, static_cut_db=0.22, center_hz=240.0, high_hz=390.0)
        out = base.peak_cap(out, -2.5)
        moves += ["generic_source_repair_lowmid_cut"]
    return base.soft_clip(out.astype(np.float32), ceiling=0.985), moves


def process_vocal_support_v16b(key: str, y: np.ndarray, lead: np.ndarray, sr: int) -> tuple[np.ndarray, list[str]]:
    moves: list[str] = []
    if not non_silent(y):
        return y.astype(np.float32), ["silent_or_missing_vocal_asset_no_processing"]
    out = y.astype(np.float32)
    if key == "female_vocal":
        out = lead_demask(out, lead, sr, "support")
        out = v16a.lean_lowmid(out, sr, max_cut_db=0.62, static_cut_db=0.22, center_hz=220.0, high_hz=360.0)
        out = base.dynamic_band_tame(out, sr, 5600, 10000, max_cut_db=0.25, percentile=66.0, slope=0.34, smooth_ms=8.0)
        out = base.peak_cap(out, -3.2)
        moves += ["female_support_lead_demask", "female_support_lowmid_tail_repair"]
    elif key == "backing_vocals":
        out = lead_demask(out, lead, sr, "support")
        out = v16a.lean_lowmid(out, sr, max_cut_db=0.72, static_cut_db=0.30, center_hz=230.0, high_hz=380.0)
        out = v16a.high_side_open(out, sr, split_hz=920.0, gain_db=0.55)
        out = base.peak_cap(out, -3.4)
        moves += ["backing_support_lead_demask", "backing_width_without_lead_mask"]
    elif key in {"vocal_reverb", "vocal_delay"}:
        out = lead_demask(out, lead, sr, "support")
        out = v16a.lean_lowmid(out, sr, max_cut_db=0.86, static_cut_db=0.38, center_hz=250.0, high_hz=430.0)
        out = v16a.high_side_open(out, sr, split_hz=960.0, gain_db=0.72)
        out = v16a.high_band_micro_spread(out, sr, split_hz=1100.0, delay_ms=0.78, mix=0.030)
        out = base.match_active_rms(out, base.active_rms_db(out) - 0.16, max_gain_db=0.20)
        out = base.peak_cap(out, -3.6)
        moves += [f"{key}_lead_demask_tail_repair", f"{key}_side_tail_preserve"]
    return out.astype(np.float32), moves


def group_mix(processed: dict[str, Path], keys: list[str], sr: int, length: int) -> np.ndarray:
    mix = np.zeros((length, 2), dtype=np.float32)
    for key in keys:
        path = processed.get(key)
        if not path or not path.exists():
            continue
        stem_sr, y, _ = base.read_wav(path)
        if stem_sr != sr:
            raise RuntimeError(f"Sample-rate mismatch in v16B group mix for {key}")
        mix += pad_or_trim(y, length)
    return base.peak_cap(mix, -1.15)


def apply_v16b_source_stem_repair(processed: dict[str, Path], sr: int, length: int) -> dict[str, Any]:
    lead = pad_or_trim(base.read_wav(processed["lead_vocal"])[1], length)
    music_keys = ["bass", "drums", "guitar", "strings", "synth", "keyboard", "fx", "percussion", "brass", "woodwinds"]
    vocal_support_keys = ["female_vocal", "backing_vocals", "vocal_reverb", "vocal_delay"]
    before_music = group_mix(processed, music_keys, sr, length)
    rows: list[dict[str, Any]] = []
    for key in [*music_keys, *vocal_support_keys]:
        path = processed.get(key)
        if not path or not path.exists():
            continue
        stem_sr, y, _ = base.read_wav(path)
        if stem_sr != sr:
            raise RuntimeError(f"Sample-rate mismatch in v16B source repair for {key}")
        y = pad_or_trim(y, length)
        before = stem_metrics(y, sr)
        if key in music_keys:
            out, moves = process_music_stem_v16b(key, y, lead, sr)
        else:
            out, moves = process_vocal_support_v16b(key, y, lead, sr)
        out = pad_or_trim(out, length)
        write_wav(path, sr, out)
        after = stem_metrics(out, sr)
        rows.append({"stem": key, "path": rel(path), "moves": moves, "before": before, "after": after})
    after_music = group_mix(processed, music_keys, sr, length)
    report = {
        "schema": "mwolla-v16b-source-stem-repair-reference-density-v1",
        "base": "v14 approved no-chop/hook baseline with v15/v16A upstream reference-clarity processing regenerated in this slug",
        "reason": (
            "v16A moved the measurements safely, but remaining reference gap suggested source/stem density and lead-aware "
            "demasking were the next useful actions. This pass avoids master-bus problem solving."
        ),
        "method": (
            "Bass/drums receive printed band-limited parallel density and low-mid repair. Melody/FX/support stems receive "
            "lead-aware mid/presence demasking plus high-side-only separation. No PREMASTER loudness push, Ozone, OTT, "
            "clipper, or external parameter write."
        ),
        "music_group_before": stem_metrics(before_music, sr),
        "music_group_after": stem_metrics(after_music, sr),
        "lead_vocal_reference": rel(processed["lead_vocal"]),
        "rows": rows,
    }
    write_json(base.REPORTS / "source_stem_repair_reference_density_report.json", report)
    write_csv(
        base.REPORTS / "source_stem_repair_reference_density_report.csv",
        [
            {
                "stem": row["stem"],
                "moves": ";".join(row["moves"]),
                "before_active_rms_db": row["before"]["active_rms_db"],
                "after_active_rms_db": row["after"]["active_rms_db"],
                "before_crest_factor_db": row["before"]["crest_factor_db"],
                "after_crest_factor_db": row["after"]["crest_factor_db"],
                "before_low_20_120_db": row["before"]["low_20_120_db"],
                "after_low_20_120_db": row["after"]["low_20_120_db"],
                "before_lowmid_120_350_db": row["before"]["lowmid_120_350_db"],
                "after_lowmid_120_350_db": row["after"]["lowmid_120_350_db"],
                "before_mid_350_2500_db": row["before"]["mid_350_2500_db"],
                "after_mid_350_2500_db": row["after"]["mid_350_2500_db"],
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
    processed, sr, duration, vocal_balance = v16a.write_processed(paths)
    length = int(round(duration * sr))
    repair_report = apply_v16b_source_stem_repair(processed, sr, length)
    v13.rewrite_vocal_solo(processed, sr, length)
    vocal_balance["v16b_source_stem_repair_reference_density"] = True
    vocal_balance["v16b_processed_stem_count"] = len(repair_report["rows"])
    return processed, sr, duration, vocal_balance


def write_reaper_scripts(processed: dict[str, Path], duration: float) -> None:
    v16a.write_reaper_scripts(processed, duration)
    build_text = base.BUILD_LUA.read_text(encoding="utf-8")
    build_text = build_text.replace("mwolla v16A leaner glue reference clarity master", "mwolla v16B source stem repair reference density master")
    build_text = build_text.replace('local music_bus = make_track("MUSIC_BUS", 0.20, 0.0, false, false)', 'local music_bus = make_track("MUSIC_BUS", 0.18, 0.0, false, false)')
    build_text = build_text.replace("mwolla_v16A", "mwolla_v16B")
    base.BUILD_LUA.write_text(build_text, encoding="utf-8")


def patch_v16b_report() -> None:
    report_path = base.REPORTS / base.REPORT_FILENAME
    text = report_path.read_text(encoding="utf-8")
    text = text.replace("Mwolla v16A Leaner Glue Reference Clarity Master Report", base.REPORT_TITLE)
    text = text.replace("mwolla v16A leaner glue reference clarity master", "mwolla v16B source stem repair reference density master")
    text = text.rstrip() + "\n\n" + "\n".join(
        [
            "## v16B Source Stem Repair Reference Density",
            "",
            "- User command: proceed beyond v16A and delete prior candidate outputs before creating the next render.",
            "- Deleted before this pass: v15/v16A render/report/reaper/audio_work/config candidate outputs. v14 approved baseline and original/source files were preserved.",
            "- Preserved in this pass: v14 no-chop continuity, hook reprise at 54.0-70.0s, first-slot vocal rescue plugin, 1/2 -> 3/4 sidechain routing, and no-loudness-push final stage.",
            "- Source/stem fixes: bass/drum band-limited parallel density, stronger low-mid repair, lead-aware melody/FX/support demasking, and high-side-only separation above the low band.",
            "- Explicitly avoided: PREMASTER limiter push, Ozone, OTT, clipper, and hardcoded external plugin parameter writes.",
            f"- v16B source repair report: `{rel(base.REPORTS / 'source_stem_repair_reference_density_report.json')}`",
            f"- v16B reference diagnostic: `{rel(ROOT / 'reports' / 'mwolla_v16b_reference_density_diagnostics' / 'goal02_reference_match.json')}`",
        ]
    ) + "\n"
    report_path.write_text(text, encoding="utf-8")


def write_reports(paths: dict[str, Path], processed: dict[str, Path], vocal_balance: dict[str, float], gate: dict[str, Any]) -> None:
    v16a.write_reports(paths, processed, vocal_balance, gate)
    patch_v16b_report()
    qc_path = base.REPORTS / "qc_summary.json"
    qc = json.loads(qc_path.read_text(encoding="utf-8"))
    qc["deleted_prior_candidate_outputs"] = {
        "deleted_slugs": [
            "mwolla_v15_reference_clarity_stem_glue_master",
            "mwolla_v16a_leaner_glue_reference_clarity_master",
        ],
        "preserved": [
            "mwolla_v14_no_chop_max_clarity_hook_reprise_master",
            "source zip",
            "reference audio",
            "automation scripts",
        ],
    }
    qc["source_stem_repair_reference_density"] = {
        "path": rel(base.REPORTS / "source_stem_repair_reference_density_report.json"),
        "csv": rel(base.REPORTS / "source_stem_repair_reference_density_report.csv"),
        "candidate_diagnostic": rel(ROOT / "reports" / "mwolla_v16b_reference_density_diagnostics" / "goal02_reference_match.json"),
        "music_bus_gain_change_vs_v16a_db": -0.02,
        "no_loudness_push_preserved": True,
        "external_parameter_writes": "none_added",
    }
    write_json(qc_path, qc)


def build_zip() -> None:
    v16a.build_zip()
    extras = [
        base.REPORTS / "source_stem_repair_reference_density_report.json",
        base.REPORTS / "source_stem_repair_reference_density_report.csv",
        ROOT / "configs" / "mwolla_v16b_reference_density_manifest.json",
        ROOT / "reports" / "mwolla_v16b_reference_density_diagnostics" / "goal02_reference_match.json",
        ROOT / "reports" / "mwolla_v16b_reference_density_diagnostics" / "GOAL02_CHORUS_REFERENCE_MATCH_REPORT.md",
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

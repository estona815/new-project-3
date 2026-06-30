#!/usr/bin/env python3
from __future__ import annotations

import csv
import importlib.util
import json
from pathlib import Path
from typing import Any

import numpy as np


ROOT = Path("/Users/hantaeheuk/Documents/New project 3")
V14_SCRIPT = ROOT / "tools" / "mwolla_v14_no_chop_vocal_clarity_lift_master.py"
SLUG = "mwolla_v15_reference_clarity_stem_glue_master"
ZIP_SOURCE = Path("/Users/hantaeheuk/Downloads/몰라.zip")


spec = importlib.util.spec_from_file_location("mwolla_v14_no_chop_vocal_clarity_lift_master", V14_SCRIPT)
if spec is None or spec.loader is None:
    raise RuntimeError(f"Could not load v14 script: {V14_SCRIPT}")
v14 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v14)

base = v14.base
v13 = v14.v13
v12 = v14.v12
v11 = v14.v11
v2 = v14.v2


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
    return v14.pad_or_trim(y, length)


def configure_base() -> None:
    v14.SLUG = SLUG
    v14.ZIP_SOURCE = ZIP_SOURCE
    v14.configure_base()

    base.ZIP_SOURCE = ZIP_SOURCE
    base.SLUG = SLUG
    base.WORK = ROOT / "audio_work" / SLUG
    base.SOURCE = base.WORK / "source_stems"
    base.PROCESSED = base.WORK / "processed_stems"
    base.REAPER_DIR = ROOT / "reaper" / SLUG
    base.RENDERS = ROOT / "renders" / SLUG
    base.REPORTS = ROOT / "reports" / SLUG

    base.RPP = base.REAPER_DIR / "mwolla_v15_REFERENCE_CLARITY_STEM_GLUE_MASTER.rpp"
    base.BUILD_LUA = base.REAPER_DIR / "build_mwolla_v15_reference_clarity_stem_glue_master.lua"
    base.RUN_BUILD_LUA = base.REAPER_DIR / "run_build_mwolla_v15_reference_clarity_stem_glue_master.lua"
    base.RENDER_LUA = base.REAPER_DIR / "render_mwolla_v15_reference_clarity_stem_glue_master.lua"
    base.RUN_RENDER_LUA = base.REAPER_DIR / "run_render_mwolla_v15_reference_clarity_stem_glue_master.lua"
    base.TRACE_JSON = base.REPORTS / "actual_reaper_plugin_trace.json"
    base.TRACE_MD = base.REPORTS / "actual_reaper_plugin_trace.md"

    base.REAPER_PRINT = base.RENDERS / "mwolla_v15_REAPERPRINT_24-48.wav"
    base.FINAL_WAV = base.RENDERS / "mwolla_v15_REFERENCE_CLARITY_STEM_GLUE_MASTER.wav"
    base.FINAL_MP3 = base.RENDERS / "mwolla_v15_REFERENCE_CLARITY_STEM_GLUE_MASTER_320k.mp3"
    base.VOCAL_SOLO = base.RENDERS / "mwolla_v15_VOCAL_SOLO_reference_clarity_stem_glue.wav"
    base.AB_PREVIEW_MP3 = base.RENDERS / "mwolla_v15_AB_original_to_reference_clarity_stem_glue_320k.mp3"
    base.DELIVERABLE_ZIP = base.RENDERS / "mwolla_v15_REFERENCE_CLARITY_STEM_GLUE_MASTER_DELIVERABLE.zip"

    base.REPORT_FILENAME = "mwolla_v15_reference_clarity_stem_glue_master_report.md"
    base.REPORT_TITLE = "Mwolla v15 Reference Clarity Stem Glue Master Report"
    base.PROJECT_NOTES = (
        "mwolla v15: v14 approved no-chop/hook baseline preserved. This pass targets reference-informed "
        "music-bed clarity, low-end foundation, drum transient density, and low-mid stereo glue without "
        "PREMASTER loudness push."
    )

    v11.PHRASE_PREMASTER_NAME = "mwolla_v15_PHRASE_SAFE_REFERENCE_CLARITY_PREMASTER_24-48.wav"
    v11.FINAL_LOCKED_NAME = "mwolla_v15_POST_FINAL_REFERENCE_CLARITY_NO_LOUDNESS_PUSH_24-48.wav"


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


def stem_metrics(y: np.ndarray, sr: int) -> dict[str, Any]:
    return {
        "active_rms_db": round(base.active_rms_db(y), 2),
        "peak_dbfs": round(float(amp_to_db(np.max(np.abs(y)) if len(y) else 0.0)), 2),
        "low_20_120_db": band_rms_db(y, sr, 20, 120),
        "lowmid_120_350_db": band_rms_db(y, sr, 120, 350),
        "mid_350_2500_db": band_rms_db(y, sr, 350, 2500),
        "presence_2500_6000_db": band_rms_db(y, sr, 2500, 6000),
        "glare_5600_10000_db": band_rms_db(y, sr, 5600, 10000),
        "stereo_correlation": stereo_corr(y),
    }


def low_mono(y: np.ndarray, sr: int, cutoff_hz: float) -> np.ndarray:
    low = base.butter_filter(y.astype(np.float32), sr, "lowpass", cutoff_hz, order=3)
    high = y.astype(np.float32) - low
    mono_low = np.mean(low, axis=1, keepdims=True)
    return (high + np.repeat(mono_low, 2, axis=1)).astype(np.float32)


def lowmid_side_tighten(y: np.ndarray, sr: int, low_hz: float, high_hz: float, cut_db: float) -> np.ndarray:
    left = y[:, 0].astype(np.float32)
    right = y[:, 1].astype(np.float32)
    mid = (left + right) * 0.5
    side = (left - right) * 0.5
    side_stereo = np.column_stack([side, side]).astype(np.float32)
    side_band = base.butter_filter(side_stereo, sr, "bandpass", (low_hz, high_hz), order=2)[:, 0]
    side = side - side_band * (1.0 - float(db_to_amp(-abs(cut_db))))
    out = np.column_stack([mid + side, mid - side]).astype(np.float32)
    return base.peak_cap(out, -1.15)


def gain_active(y: np.ndarray, db: float, max_gain_db: float = 1.5) -> np.ndarray:
    return base.match_active_rms(y, base.active_rms_db(y) + db, max_gain_db=max_gain_db)


def non_silent(y: np.ndarray) -> bool:
    return float(np.max(np.abs(y))) > 1e-5


def process_music_stem_for_reference_clarity(key: str, y: np.ndarray, sr: int) -> tuple[np.ndarray, list[str]]:
    moves: list[str] = []
    if not non_silent(y):
        return y.astype(np.float32), ["silent_or_missing_role_asset_no_processing"]

    out = y.astype(np.float32)
    if key == "bass":
        out = low_mono(out, sr, 145.0)
        out = base.dynamic_band_tame(out, sr, 170, 340, max_cut_db=0.55, percentile=58.0, slope=0.46, smooth_ms=28.0)
        out = base.soft_saturation(out, drive_db=0.85, mix=0.055)
        out = base.rbj_peaking(out, sr, 760, 0.34, 0.95)
        out = gain_active(out, 1.15, max_gain_db=1.25)
        out = base.peak_cap(out, -2.0)
        moves += ["low_mono_below_145hz", "controlled_bass_saturation", "bass_active_rms_plus_1p15db"]
    elif key == "drums":
        out = low_mono(out, sr, 120.0)
        out = base.dynamic_band_tame(out, sr, 170, 360, max_cut_db=0.75, percentile=58.0, slope=0.50, smooth_ms=20.0)
        out = base.rbj_peaking(out, sr, 4300, 0.46, 0.85)
        out = base.rbj_shelf(out, sr, 9200, 0.24, high=True, slope=0.55)
        out = base.dynamic_band_tame(out, sr, 6200, 10500, max_cut_db=0.42, percentile=66.0, slope=0.40, smooth_ms=7.0)
        out = gain_active(out, 0.78, max_gain_db=0.9)
        out = base.peak_cap(out, -1.75)
        moves += ["drum_lowmid_demud", "small_attack_presence_lift", "drum_active_rms_plus_0p78db"]
    elif key in {"guitar", "strings", "synth", "keyboard"}:
        side_cut = {"guitar": 2.4, "strings": 1.7, "synth": 2.0, "keyboard": 1.4}[key]
        out = lowmid_side_tighten(out, sr, 120, 650, cut_db=side_cut)
        out = base.dynamic_band_tame(out, sr, 170, 430, max_cut_db=0.65, percentile=58.0, slope=0.44, smooth_ms=32.0)
        if key == "guitar":
            out = base.rbj_peaking(out, sr, 2300, 0.28, 0.90)
            out = gain_active(out, 0.24, max_gain_db=0.35)
        elif key == "strings":
            out = base.rbj_peaking(out, sr, 2600, 0.22, 0.85)
            out = gain_active(out, 0.16, max_gain_db=0.25)
        elif key == "synth":
            out = base.rbj_peaking(out, sr, 1750, 0.18, 0.90)
        elif key == "keyboard":
            out = base.rbj_peaking(out, sr, 1900, 0.18, 0.90)
        out = base.dynamic_band_tame(out, sr, 5600, 10000, max_cut_db=0.48, percentile=66.0, slope=0.42, smooth_ms=8.0)
        out = base.peak_cap(out, -2.0)
        moves += [f"lowmid_side_tighten_{side_cut}db", "music_lowmid_demud", "guarded_presence_focus"]
    elif key == "fx":
        out = lowmid_side_tighten(out, sr, 120, 850, cut_db=3.0)
        out = base.dynamic_band_tame(out, sr, 420, 1800, max_cut_db=0.55, percentile=60.0, slope=0.44, smooth_ms=28.0)
        out = base.dynamic_band_tame(out, sr, 5600, 11000, max_cut_db=0.82, percentile=62.0, slope=0.52, smooth_ms=8.0)
        out = gain_active(out, -0.45, max_gain_db=0.55)
        out = base.peak_cap(out, -3.0)
        moves += ["fx_lowmid_side_tighten", "fx_glare_guard", "fx_tuck_for_stem_readability"]
    else:
        out = base.dynamic_band_tame(out, sr, 170, 430, max_cut_db=0.35, percentile=58.0, slope=0.35, smooth_ms=32.0)
        out = base.peak_cap(out, -2.5)
        moves += ["generic_light_lowmid_demud"]
    return base.soft_clip(out.astype(np.float32), ceiling=0.985), moves


def process_vocal_support_for_glue(key: str, y: np.ndarray, sr: int) -> tuple[np.ndarray, list[str]]:
    moves: list[str] = []
    if not non_silent(y):
        return y.astype(np.float32), ["silent_or_missing_vocal_asset_no_processing"]
    out = y.astype(np.float32)
    if key in {"female_vocal", "backing_vocals", "vocal_reverb", "vocal_delay"}:
        out = lowmid_side_tighten(out, sr, 120, 800, cut_db=1.4 if key == "female_vocal" else 2.0)
        out = base.dynamic_band_tame(out, sr, 140, 350, max_cut_db=0.75, percentile=58.0, slope=0.42, smooth_ms=28.0)
        if key in {"vocal_reverb", "vocal_delay"}:
            out = gain_active(out, -0.28, max_gain_db=0.35)
            moves.append("vocal_fx_tuck_0p28db")
        out = base.dynamic_band_tame(out, sr, 5600, 10000, max_cut_db=0.44, percentile=66.0, slope=0.40, smooth_ms=8.0)
        out = base.peak_cap(out, -3.2)
        moves += ["support_lowmid_side_tighten", "support_lowmid_demud", "support_glare_guard"]
    return out.astype(np.float32), moves


def apply_reference_clarity_stem_glue(processed: dict[str, Path], sr: int, length: int) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    music_keys = ["bass", "drums", "guitar", "strings", "synth", "keyboard", "fx", "percussion", "brass", "woodwinds"]
    vocal_support_keys = ["female_vocal", "backing_vocals", "vocal_reverb", "vocal_delay"]
    for key in [*music_keys, *vocal_support_keys]:
        path = processed.get(key)
        if not path or not path.exists():
            continue
        stem_sr, y, _ = base.read_wav(path)
        if stem_sr != sr:
            raise RuntimeError(f"Sample-rate mismatch in v15 stem clarity for {key}")
        y = pad_or_trim(y, length)
        before = stem_metrics(y, sr)
        if key in music_keys:
            out, moves = process_music_stem_for_reference_clarity(key, y, sr)
        else:
            out, moves = process_vocal_support_for_glue(key, y, sr)
        out = pad_or_trim(out, length)
        write_wav(path, sr, out)
        after = stem_metrics(out, sr)
        rows.append({"stem": key, "path": rel(path), "moves": moves, "before": before, "after": after})

    report = {
        "schema": "mwolla-v15-reference-clarity-stem-glue-v1",
        "base": "v14 user-approved no-chop/max-clarity/hook baseline",
        "diagnostic_source": rel(ROOT / "reports" / "mwolla_v14_reference_clarity_diagnostics" / "goal02_reference_match.json"),
        "reason": (
            "Reference comparison showed v14 has lower low-end ratio and transient density than the Estona/Nib reference set, "
            "with excess low-mid/mid share. User also reported music/stems feel blurry and detached."
        ),
        "method": "Printed upstream stem fixes: low-end foundation, drum transient focus, low-mid side tightening, and support FX de-smear. No PREMASTER loudness push.",
        "rows": rows,
    }
    write_json(base.REPORTS / "reference_clarity_stem_glue_report.json", report)
    write_csv(
        base.REPORTS / "reference_clarity_stem_glue_report.csv",
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
            }
            for row in rows
        ],
    )
    return report


def write_processed(paths: dict[str, Path]) -> tuple[dict[str, Path], int, float, dict[str, float]]:
    processed, sr, duration, vocal_balance = v14.write_processed(paths)
    length = int(round(duration * sr))
    glue_report = apply_reference_clarity_stem_glue(processed, sr, length)
    v13.rewrite_vocal_solo(processed, sr, length)
    vocal_balance["v15_reference_clarity_stem_glue"] = True
    vocal_balance["v15_processed_stem_count"] = len(glue_report["rows"])
    vocal_balance["v15_diagnostic_source"] = rel(ROOT / "reports" / "mwolla_v14_reference_clarity_diagnostics" / "goal02_reference_match.json")
    return processed, sr, duration, vocal_balance


def write_reaper_scripts(processed: dict[str, Path], duration: float) -> None:
    v14.write_reaper_scripts(processed, duration)
    build_text = base.BUILD_LUA.read_text(encoding="utf-8")
    build_text = build_text.replace("mwolla v14 no-chop max clarity hook reprise master", "mwolla v15 reference clarity stem glue master")
    build_text = build_text.replace('local music_bus = make_track("MUSIC_BUS", 0.15, 0.0, false, false)', 'local music_bus = make_track("MUSIC_BUS", 0.25, 0.0, false, false)')
    build_text = build_text.replace("mwolla_v14", "mwolla_v15")
    base.BUILD_LUA.write_text(build_text, encoding="utf-8")


def patch_v15_report() -> None:
    report_path = base.REPORTS / base.REPORT_FILENAME
    text = report_path.read_text(encoding="utf-8")
    text = text.replace("v14", "v15").replace("V14", "V15")
    text = text.rstrip() + "\n\n" + "\n".join(
        [
            "## v15 Reference Clarity Stem Glue",
            "",
            "- User feedback: approved v14 is preferred, but compared with references the music bed/stems feel blurry and detached.",
            "- Preserved: v14 no-chop continuity, hook reprise at 54.0-70.0s, first-slot vocal rescue plugin, and no-loudness-push final stage.",
            "- Diagnostic basis: v14 vs eight Estona/Nib references measured lower low-end energy ratio, lower transient density, higher low-mid/mid share, and lower peak density.",
            "- Stem fixes: bass low foundation/harmonics, drum transient focus, music low-mid side tightening, support vocal FX de-smear.",
            "- REAPER trim: MUSIC_BUS +0.10 dB vs v14 after printed stem fixes; main vocal/layer trims remain v14-compatible.",
            f"- Stem glue report: `{rel(base.REPORTS / 'reference_clarity_stem_glue_report.json')}`",
            f"- v14 reference diagnostic: `{rel(ROOT / 'reports' / 'mwolla_v14_reference_clarity_diagnostics' / 'goal02_reference_match.json')}`",
        ]
    ) + "\n"
    report_path.write_text(text, encoding="utf-8")


def write_reports(paths: dict[str, Path], processed: dict[str, Path], vocal_balance: dict[str, float], gate: dict[str, Any]) -> None:
    v14.write_reports(paths, processed, vocal_balance, gate)
    patch_v15_report()
    qc_path = base.REPORTS / "qc_summary.json"
    qc = json.loads(qc_path.read_text(encoding="utf-8"))
    qc["reference_clarity_stem_glue"] = {
        "path": rel(base.REPORTS / "reference_clarity_stem_glue_report.json"),
        "csv": rel(base.REPORTS / "reference_clarity_stem_glue_report.csv"),
        "diagnostic_source": rel(ROOT / "reports" / "mwolla_v14_reference_clarity_diagnostics" / "goal02_reference_match.json"),
        "music_bus_gain_change_vs_v14_db": 0.10,
        "no_loudness_push_preserved": True,
    }
    write_json(qc_path, qc)


def build_zip() -> None:
    v14.build_zip()
    extras = [
        base.REPORTS / "reference_clarity_stem_glue_report.json",
        base.REPORTS / "reference_clarity_stem_glue_report.csv",
        ROOT / "configs" / "mwolla_v14_reference_clarity_manifest.json",
        ROOT / "reports" / "mwolla_v14_reference_clarity_diagnostics" / "goal02_reference_match.json",
        ROOT / "reports" / "mwolla_v14_reference_clarity_diagnostics" / "GOAL02_CHORUS_REFERENCE_MATCH_REPORT.md",
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

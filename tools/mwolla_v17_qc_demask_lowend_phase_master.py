#!/usr/bin/env python3
from __future__ import annotations

import csv
import importlib.util
import json
from pathlib import Path
from typing import Any

import numpy as np


ROOT = Path("/Users/hantaeheuk/Documents/New project 3")
V16B_SCRIPT = ROOT / "tools" / "mwolla_v16b_source_stem_repair_reference_density_master.py"
SLUG = "mwolla_v17_qc_demask_lowend_phase_master"
ZIP_SOURCE = Path("/Users/hantaeheuk/Downloads/몰라.zip")


spec = importlib.util.spec_from_file_location("mwolla_v16b_source_stem_repair_reference_density_master", V16B_SCRIPT)
if spec is None or spec.loader is None:
    raise RuntimeError(f"Could not load v16B script: {V16B_SCRIPT}")
v16b = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v16b)

base = v16b.base


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

    base.RPP = base.REAPER_DIR / "mwolla_v17_QC_DEMASK_LOWEND_PHASE_MASTER.rpp"
    base.BUILD_LUA = base.REAPER_DIR / "build_mwolla_v17_qc_demask_lowend_phase_master.lua"
    base.RUN_BUILD_LUA = base.REAPER_DIR / "run_build_mwolla_v17_qc_demask_lowend_phase_master.lua"
    base.RENDER_LUA = base.REAPER_DIR / "render_mwolla_v17_qc_demask_lowend_phase_master.lua"
    base.RUN_RENDER_LUA = base.REAPER_DIR / "run_render_mwolla_v17_qc_demask_lowend_phase_master.lua"
    base.TRACE_JSON = base.REPORTS / "actual_reaper_plugin_trace.json"
    base.TRACE_MD = base.REPORTS / "actual_reaper_plugin_trace.md"

    base.REAPER_PRINT = base.RENDERS / "mwolla_v17_REAPERPRINT_24-48.wav"
    base.FINAL_WAV = base.RENDERS / "mwolla_v17_QC_DEMASK_LOWEND_PHASE_MASTER.wav"
    base.FINAL_MP3 = base.RENDERS / "mwolla_v17_QC_DEMASK_LOWEND_PHASE_MASTER_320k.mp3"
    base.VOCAL_SOLO = base.RENDERS / "mwolla_v17_VOCAL_SOLO_qc_demask_lowend_phase.wav"
    base.AB_PREVIEW_MP3 = base.RENDERS / "mwolla_v17_AB_v16b_to_qc_demask_lowend_phase_320k.mp3"
    base.DELIVERABLE_ZIP = base.RENDERS / "mwolla_v17_QC_DEMASK_LOWEND_PHASE_MASTER_DELIVERABLE.zip"

    base.REPORT_FILENAME = "mwolla_v17_qc_demask_lowend_phase_master_report.md"
    base.REPORT_TITLE = "Mwolla v17 QC Demask Low-End Phase Master Report"
    base.PROJECT_NOTES = (
        "mwolla v17: v14 approved no-chop/hook baseline and v16B reference-density candidate are preserved. "
        "This pass applies the measured QC work order: stronger 1.5-5 kHz lead-vocal demasking, 40-120 Hz "
        "bass/drum separation, and low-band stereo safety on non-low-end stems. No PREMASTER loudness push."
    )

    v16b.v11.PHRASE_PREMASTER_NAME = "mwolla_v17_PHRASE_SAFE_QC_DEMASK_LOWEND_PHASE_PREMASTER_24-48.wav"
    v16b.v11.FINAL_LOCKED_NAME = "mwolla_v17_POST_FINAL_QC_DEMASK_LOWEND_PHASE_NO_LOUDNESS_PUSH_24-48.wav"


def band_rms_db(y: np.ndarray, sr: int, low: float, high: float) -> float:
    band = base.butter_filter(y.astype(np.float32), sr, "bandpass", (low, high), order=3)
    return round(float(amp_to_db(base.rms(band))), 2)


def side_mid_db(y: np.ndarray) -> tuple[float | None, float | None]:
    if y.ndim < 2 or y.shape[1] < 2:
        return None, None
    mid = (y[:, 0] + y[:, 1]) * 0.5
    side = (y[:, 0] - y[:, 1]) * 0.5
    return round(float(amp_to_db(base.rms(side))), 2), round(float(amp_to_db(base.rms(mid))), 2)


def low_side_mid_db(y: np.ndarray, sr: int, cutoff_hz: float = 140.0) -> float | None:
    low = base.butter_filter(y.astype(np.float32), sr, "lowpass", cutoff_hz, order=3)
    side_db, mid_db = side_mid_db(low)
    if side_db is None or mid_db is None:
        return None
    return round(side_db - mid_db, 2)


def lr_imbalance_db(y: np.ndarray) -> float:
    if y.ndim < 2 or y.shape[1] < 2:
        return 0.0
    left = float(base.rms(y[:, 0]))
    right = float(base.rms(y[:, 1]))
    return round(float(amp_to_db(left) - amp_to_db(right)), 2)


def extended_metrics(y: np.ndarray, sr: int) -> dict[str, Any]:
    m = v16b.stem_metrics(y, sr)
    m.update(
        {
            "mud_250_500_db": band_rms_db(y, sr, 250, 500),
            "presence_1500_5000_db": band_rms_db(y, sr, 1500, 5000),
            "sibilance_5000_9000_db": band_rms_db(y, sr, 5000, 9000),
            "air_10000_16000_db": band_rms_db(y, sr, 10000, 16000),
            "low_side_mid_140_db": low_side_mid_db(y, sr, 140),
            "lr_imbalance_db": lr_imbalance_db(y),
        }
    )
    return m


def mono_below(y: np.ndarray, sr: int, cutoff_hz: float = 130.0, amount: float = 1.0) -> np.ndarray:
    if y.ndim < 2 or y.shape[1] < 2 or amount <= 0.0:
        return y.astype(np.float32)
    low = base.butter_filter(y.astype(np.float32), sr, "lowpass", cutoff_hz, order=3)
    high = y.astype(np.float32) - low
    mono = np.mean(low, axis=1, keepdims=True)
    mono_low = np.repeat(mono, 2, axis=1).astype(np.float32)
    safe_low = low * (1.0 - amount) + mono_low * amount
    return base.peak_cap((high + safe_low).astype(np.float32), -1.15)


def correct_lr_balance(y: np.ndarray, max_correction_db: float = 1.2) -> np.ndarray:
    if y.ndim < 2 or y.shape[1] < 2:
        return y.astype(np.float32)
    imbalance = lr_imbalance_db(y)
    if abs(imbalance) <= 1.0:
        return y.astype(np.float32)
    correction = max(-max_correction_db, min(max_correction_db, imbalance * 0.5))
    out = y.astype(np.float32).copy()
    out[:, 0] *= float(db_to_amp(-correction))
    out[:, 1] *= float(db_to_amp(correction))
    return base.peak_cap(out, -1.15)


def lead_pocket_duck(y: np.ndarray, lead: np.ndarray, sr: int, profile: str) -> tuple[np.ndarray, list[str]]:
    out = y.astype(np.float32)
    moves: list[str] = []
    if profile == "melody":
        out = base.sidechain_band_duck(out, lead, sr, 1500, 5000, max_cut_db=1.18, percentile=54.0, smooth_ms=105.0)
        out = base.sidechain_band_duck(out, lead, sr, 250, 500, max_cut_db=0.55, percentile=55.0, smooth_ms=135.0)
        moves += ["lead_sidechain_music_pocket_1500_5000_max1p18db", "lead_sidechain_mud_pocket_250_500_max0p55db"]
    elif profile == "fx":
        out = base.sidechain_band_duck(out, lead, sr, 1500, 5000, max_cut_db=1.35, percentile=53.0, smooth_ms=115.0)
        out = base.sidechain_band_duck(out, lead, sr, 5000, 9000, max_cut_db=0.55, percentile=59.0, smooth_ms=75.0)
        moves += ["lead_sidechain_fx_pocket_1500_5000_max1p35db", "fx_harsh_guard_5000_9000_max0p55db"]
    elif profile == "support":
        out = base.sidechain_band_duck(out, lead, sr, 1500, 5000, max_cut_db=0.75, percentile=55.0, smooth_ms=125.0)
        moves += ["lead_sidechain_support_pocket_1500_5000_max0p75db"]
    return out.astype(np.float32), moves


def bass_kick_separate(bass: np.ndarray, drums: np.ndarray, sr: int) -> tuple[np.ndarray, list[str]]:
    out = bass.astype(np.float32)
    out = base.sidechain_band_duck(out, drums, sr, 45, 118, max_cut_db=1.35, percentile=55.0, smooth_ms=72.0)
    out = base.dynamic_band_tame(out, sr, 120, 260, max_cut_db=0.55, percentile=55.0, slope=0.45, smooth_ms=35.0)
    out = base.rbj_peaking(out, sr, 185, -0.28, 0.90)
    return base.peak_cap(out.astype(np.float32), -1.85), ["drum_keyed_bass_duck_45_118_max1p35db", "bass_lowmid_tame_120_260"]


def process_v17_stem(
    key: str,
    y: np.ndarray,
    lead: np.ndarray,
    sr: int,
    drums_for_bass: np.ndarray | None,
) -> tuple[np.ndarray, list[str]]:
    if not v16b.non_silent(y):
        return y.astype(np.float32), ["silent_or_missing_asset_no_v17_processing"]
    out = y.astype(np.float32)
    moves: list[str] = []

    if key == "bass" and drums_for_bass is not None:
        out, bass_moves = bass_kick_separate(out, drums_for_bass, sr)
        moves += bass_moves
    elif key in {"guitar", "strings", "synth", "keyboard"}:
        out, pocket_moves = lead_pocket_duck(out, lead, sr, "melody")
        out = base.dynamic_band_tame(out, sr, 250, 500, max_cut_db=0.65, percentile=58.0, slope=0.42, smooth_ms=32.0)
        out = mono_below(out, sr, 130.0, amount=0.88)
        out = correct_lr_balance(out)
        moves += pocket_moves + ["non_lowend_stem_mono_below_130hz_88pct", "lr_balance_correction_if_gt1db"]
    elif key == "fx":
        out, pocket_moves = lead_pocket_duck(out, lead, sr, "fx")
        out = mono_below(out, sr, 140.0, amount=1.0)
        out = correct_lr_balance(out)
        moves += pocket_moves + ["fx_full_mono_below_140hz", "fx_lr_balance_correction_if_gt1db"]
    elif key in {"backing_vocals", "female_vocal", "vocal_reverb", "vocal_delay"}:
        out, pocket_moves = lead_pocket_duck(out, lead, sr, "support")
        out = mono_below(out, sr, 130.0, amount=0.82)
        out = base.dynamic_band_tame(out, sr, 5000, 9000, max_cut_db=0.30, percentile=64.0, slope=0.34, smooth_ms=8.0)
        moves += pocket_moves + ["support_vocal_lowband_width_guard_130hz", "support_harsh_guard_5000_9000"]
    elif key in {"percussion", "brass", "woodwinds"}:
        out, pocket_moves = lead_pocket_duck(out, lead, sr, "support")
        out = mono_below(out, sr, 130.0, amount=0.90)
        moves += pocket_moves + ["silent_or_support_lowband_width_guard"]

    return base.soft_clip(out.astype(np.float32), ceiling=0.985), moves or ["v17_no_extra_processing_needed"]


def group_mix(processed: dict[str, Path], keys: list[str], sr: int, length: int) -> np.ndarray:
    mix = np.zeros((length, 2), dtype=np.float32)
    for key in keys:
        path = processed.get(key)
        if not path or not path.exists():
            continue
        stem_sr, y, _ = base.read_wav(path)
        if stem_sr != sr:
            raise RuntimeError(f"Sample-rate mismatch in v17 group mix for {key}")
        mix += pad_or_trim(y, length)
    return base.peak_cap(mix, -1.15)


def masking_snapshot(processed: dict[str, Path], sr: int, length: int) -> dict[str, Any]:
    music_keys = ["bass", "drums", "guitar", "strings", "synth", "keyboard", "fx", "percussion", "brass", "woodwinds"]
    lead = pad_or_trim(base.read_wav(processed["lead_vocal"])[1], length)
    music = group_mix(processed, music_keys, sr, length)
    bass = group_mix(processed, ["bass"], sr, length)
    drums = group_mix(processed, ["drums"], sr, length)
    lead_presence = band_rms_db(lead, sr, 1500, 5000)
    music_presence = band_rms_db(music, sr, 1500, 5000)
    bass_low = band_rms_db(bass, sr, 40, 120)
    drums_low = band_rms_db(drums, sr, 40, 120)
    return {
        "lead_presence_1500_5000_db": lead_presence,
        "music_presence_1500_5000_db": music_presence,
        "lead_over_music_presence_db": round(lead_presence - music_presence, 2),
        "bass_40_120_db": bass_low,
        "drums_40_120_db": drums_low,
        "bass_minus_drums_40_120_db": round(bass_low - drums_low, 2),
        "music_low_side_mid_140_db": low_side_mid_db(music, sr, 140),
        "music_metrics": extended_metrics(music, sr),
    }


def apply_v17_qc_demask_lowend_phase(processed: dict[str, Path], sr: int, length: int) -> dict[str, Any]:
    lead = pad_or_trim(base.read_wav(processed["lead_vocal"])[1], length)
    drums_path = processed.get("drums")
    drums = None
    if drums_path and drums_path.exists():
        drum_sr, drum_y, _ = base.read_wav(drums_path)
        if drum_sr != sr:
            raise RuntimeError("Sample-rate mismatch in v17 drums sidechain")
        drums = pad_or_trim(drum_y, length)

    target_keys = [
        "bass",
        "guitar",
        "strings",
        "synth",
        "keyboard",
        "fx",
        "backing_vocals",
        "female_vocal",
        "vocal_reverb",
        "vocal_delay",
        "percussion",
        "brass",
        "woodwinds",
    ]
    before_masking = masking_snapshot(processed, sr, length)
    rows: list[dict[str, Any]] = []
    for key in target_keys:
        path = processed.get(key)
        if not path or not path.exists():
            continue
        stem_sr, y, _ = base.read_wav(path)
        if stem_sr != sr:
            raise RuntimeError(f"Sample-rate mismatch in v17 processing for {key}")
        y = pad_or_trim(y, length)
        before = extended_metrics(y, sr)
        out, moves = process_v17_stem(key, y, lead, sr, drums)
        out = pad_or_trim(out, length)
        write_wav(path, sr, out)
        after = extended_metrics(out, sr)
        rows.append({"stem": key, "path": rel(path), "moves": moves, "before": before, "after": after})

    after_masking = masking_snapshot(processed, sr, length)
    report = {
        "schema": "mwolla-v17-qc-demask-lowend-phase-v1",
        "base": "v16B source-stem-repair reference-density candidate, preserving v14 approved no-chop/hook baseline",
        "reason": (
            "Fresh stem QC measured lead-over-music 1.5-5 kHz margin at +1.66 dB, bass/drum 40-120 Hz delta at "
            "+1.83 dB, and low-band stereo width warnings on FX/melody/support stems."
        ),
        "method": (
            "Apply printed upstream processing only: lead-keyed Music Bus/stem pockets in 1.5-5 kHz, drum-keyed "
            "bass ducking in 45-118 Hz, low-band mono safety below 130-140 Hz on non-low-end stereo stems, and "
            "LR balance correction where imbalance exceeds 1 dB. No Ozone, OTT, new clipper, or PREMASTER limiter push."
        ),
        "before_masking": before_masking,
        "after_masking": after_masking,
        "target_thresholds": {
            "lead_over_music_presence_db_min": 3.0,
            "bass_drums_40_120_delta_abs_min_db": 3.0,
            "non_lowend_low_side_mid_max_db": -12.0,
        },
        "rows": rows,
    }
    write_json(base.REPORTS / "v17_qc_demask_lowend_phase_report.json", report)
    write_csv(
        base.REPORTS / "v17_qc_demask_lowend_phase_report.csv",
        [
            {
                "stem": row["stem"],
                "moves": ";".join(row["moves"]),
                "before_presence_1500_5000_db": row["before"]["presence_1500_5000_db"],
                "after_presence_1500_5000_db": row["after"]["presence_1500_5000_db"],
                "before_mud_250_500_db": row["before"]["mud_250_500_db"],
                "after_mud_250_500_db": row["after"]["mud_250_500_db"],
                "before_low_side_mid_140_db": row["before"]["low_side_mid_140_db"],
                "after_low_side_mid_140_db": row["after"]["low_side_mid_140_db"],
                "before_lr_imbalance_db": row["before"]["lr_imbalance_db"],
                "after_lr_imbalance_db": row["after"]["lr_imbalance_db"],
                "before_peak_dbfs": row["before"]["peak_dbfs"],
                "after_peak_dbfs": row["after"]["peak_dbfs"],
            }
            for row in rows
        ],
    )
    return report


def write_processed(paths: dict[str, Path]) -> tuple[dict[str, Path], int, float, dict[str, float]]:
    processed, sr, duration, vocal_balance = v16b.write_processed(paths)
    length = int(round(duration * sr))
    report = apply_v17_qc_demask_lowend_phase(processed, sr, length)
    v16b.v13.rewrite_vocal_solo(processed, sr, length)
    vocal_balance["v17_qc_demask_lowend_phase"] = True
    vocal_balance["v17_processed_stem_count"] = len(report["rows"])
    vocal_balance["v17_presence_delta_before_db"] = report["before_masking"]["lead_over_music_presence_db"]
    vocal_balance["v17_presence_delta_after_db"] = report["after_masking"]["lead_over_music_presence_db"]
    vocal_balance["v17_bass_drums_delta_before_db"] = report["before_masking"]["bass_minus_drums_40_120_db"]
    vocal_balance["v17_bass_drums_delta_after_db"] = report["after_masking"]["bass_minus_drums_40_120_db"]
    return processed, sr, duration, vocal_balance


def write_reaper_scripts(processed: dict[str, Path], duration: float) -> None:
    v16b.write_reaper_scripts(processed, duration)
    build_text = base.BUILD_LUA.read_text(encoding="utf-8")
    build_text = build_text.replace("mwolla v16B source stem repair reference density master", "mwolla v17 qc demask lowend phase master")
    build_text = build_text.replace("mwolla_v16B", "mwolla_v17")
    build_text = build_text.replace('local music_bus = make_track("MUSIC_BUS", 0.18, 0.0, false, false)', 'local music_bus = make_track("MUSIC_BUS", 0.16, 0.0, false, false)')
    base.BUILD_LUA.write_text(build_text, encoding="utf-8")


def patch_v17_report() -> None:
    report_path = base.REPORTS / base.REPORT_FILENAME
    text = report_path.read_text(encoding="utf-8")
    text = text.replace("Mwolla v16B Source Stem Repair Reference Density Master Report", base.REPORT_TITLE)
    text = text.replace("mwolla v16B source stem repair reference density master", "mwolla v17 qc demask lowend phase master")
    report = json.loads((base.REPORTS / "v17_qc_demask_lowend_phase_report.json").read_text(encoding="utf-8"))
    before = report["before_masking"]
    after = report["after_masking"]
    text = text.rstrip() + "\n\n" + "\n".join(
        [
            "## v17 QC Demask Low-End Phase Pass",
            "",
            "- User command: proceed with measured remix/master fixes from the stem QC work order.",
            "- Preserved from v14/v16B: no-chop continuity, hook reprise at 54.0-70.0s, first-slot vocal rescue plugin, 1/2 -> 3/4 sidechain routing, and no-loudness-push final stage.",
            "- v17 printed fixes: lead-keyed 1.5-5 kHz pockets, drum-keyed 45-118 Hz bass ducking, non-low-end mono below 130-140 Hz, and LR balance correction when needed.",
            "- Explicitly avoided: PREMASTER limiter push, Ozone, OTT, new clipper, and hardcoded external plugin parameter writes.",
            f"- Lead-over-music 1.5-5 kHz delta: `{before['lead_over_music_presence_db']}` dB -> `{after['lead_over_music_presence_db']}` dB.",
            f"- Bass-minus-drums 40-120 Hz delta: `{before['bass_minus_drums_40_120_db']}` dB -> `{after['bass_minus_drums_40_120_db']}` dB.",
            f"- v17 repair report: `{rel(base.REPORTS / 'v17_qc_demask_lowend_phase_report.json')}`",
        ]
    ) + "\n"
    report_path.write_text(text, encoding="utf-8")


def write_reports(paths: dict[str, Path], processed: dict[str, Path], vocal_balance: dict[str, float], gate: dict[str, Any]) -> None:
    v16b.write_reports(paths, processed, vocal_balance, gate)
    patch_v17_report()
    qc_path = base.REPORTS / "qc_summary.json"
    qc = json.loads(qc_path.read_text(encoding="utf-8"))
    report = json.loads((base.REPORTS / "v17_qc_demask_lowend_phase_report.json").read_text(encoding="utf-8"))
    qc["v17_qc_demask_lowend_phase"] = {
        "path": rel(base.REPORTS / "v17_qc_demask_lowend_phase_report.json"),
        "csv": rel(base.REPORTS / "v17_qc_demask_lowend_phase_report.csv"),
        "before_masking": report["before_masking"],
        "after_masking": report["after_masking"],
        "music_bus_gain_change_vs_v16b_db": -0.02,
        "no_loudness_push_preserved": True,
        "external_parameter_writes": "none_added",
        "new_master_processors": "none_added",
    }
    write_json(qc_path, qc)


def build_zip() -> None:
    v16b.build_zip()
    extras = [
        base.REPORTS / "v17_qc_demask_lowend_phase_report.json",
        base.REPORTS / "v17_qc_demask_lowend_phase_report.csv",
        ROOT / "reports" / "QC_REPORT.md",
        ROOT / "reports" / "masking_report.md",
        ROOT / "reports" / "plugin_chain_recommendation.md",
        ROOT / "reports" / "mastering_plan.md",
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
    base.final_master = v16b.v13.final_master_no_loudness_push
    return base.main()


if __name__ == "__main__":
    raise SystemExit(main())

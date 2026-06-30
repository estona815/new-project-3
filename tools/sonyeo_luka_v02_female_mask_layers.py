#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import numpy as np


ROOT = Path("/Users/hantaeheuk/Documents/New project 3")
BASE_SCRIPT = ROOT / "tools" / "sonyeo_luka_v01_clear_master.py"
SLUG = "sonyeo_luka_v02_female_mask_layers"


spec = importlib.util.spec_from_file_location("sonyeo_luka_v01_clear_master", BASE_SCRIPT)
if spec is None or spec.loader is None:
    raise RuntimeError(f"Could not load base script: {BASE_SCRIPT}")
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)


def configure_base() -> None:
    base.SLUG = SLUG
    base.WORK = ROOT / "audio_work" / SLUG
    base.SOURCE = base.WORK / "source_stems"
    base.PROCESSED = base.WORK / "processed_stems"
    base.REAPER_DIR = ROOT / "reaper" / SLUG
    base.RENDERS = ROOT / "renders" / SLUG
    base.REPORTS = ROOT / "reports" / SLUG

    base.RPP = base.REAPER_DIR / "sonyeo_luka_v02_FEMALE_MASK_LAYERS.rpp"
    base.BUILD_LUA = base.REAPER_DIR / "build_sonyeo_luka_v02_female_mask_layers.lua"
    base.RUN_BUILD_LUA = base.REAPER_DIR / "run_build_sonyeo_luka_v02_female_mask_layers.lua"
    base.RENDER_LUA = base.REAPER_DIR / "render_sonyeo_luka_v02_female_mask_layers.lua"
    base.RUN_RENDER_LUA = base.REAPER_DIR / "run_render_sonyeo_luka_v02_female_mask_layers.lua"
    base.TRACE_JSON = base.REPORTS / "actual_reaper_plugin_trace.json"
    base.TRACE_MD = base.REPORTS / "actual_reaper_plugin_trace.md"

    base.REAPER_PRINT = base.RENDERS / "sonyeo_luka_v02_REAPERPRINT_24-48.wav"
    base.FINAL_WAV = base.RENDERS / "sonyeo_luka_v02_FEMALE_MASK_LAYERS.wav"
    base.FINAL_MP3 = base.RENDERS / "sonyeo_luka_v02_FEMALE_MASK_LAYERS_320k.mp3"
    base.VOCAL_SOLO = base.RENDERS / "sonyeo_luka_v02_VOCAL_SOLO_female_mask_layers.wav"
    base.AB_PREVIEW_MP3 = base.RENDERS / "sonyeo_luka_v02_AB_v01_to_v02_320k.mp3"
    base.DELIVERABLE_ZIP = base.RENDERS / "sonyeo_luka_v02_FEMALE_MASK_LAYERS_DELIVERABLE.zip"

    base.FEMALE_TARGET_DELTA_DB = -10.0
    base.FEMALE_LAYER_FILENAME = "female_vocal_side_mask_layer_tucked.wav"
    base.FEMALE_TRACK_NAME = "13 Female side mask hook/double layer tucked"
    base.FEMALE_REPORT_LINE = (
        "- Use `13 Vocals.wav` only as a wider side-mask hook/double layer, tucked clearly under "
        "the centered main vocal."
    )
    base.REPORT_FILENAME = "sonyeo_luka_v02_female_mask_layers_report.md"
    base.REPORT_TITLE = "Sonyeo Luka v02 Female Mask Layers Report"
    base.PROJECT_NOTES = (
        "sonyeo luka v02 female mask layers: original full mix is muted reference only. "
        "12 Vocals remains the clean centered main. 13 Vocals is kept as a tucked "
        "wider panned hook/double/side-mask layer so main-vocal AI noise "
        "is less exposed without replacing the lead. Codex Vocal AI Artifact Split Tamer "
        "is first FX slot on the main vocal. No pitch/tune inserts and no heavy main-vocal saturation."
    )


def mask_activity_curve(cleaned_female: np.ndarray, lead: np.ndarray, sr: int) -> tuple[np.ndarray, dict[str, float]]:
    female_env = base.envelope(np.mean(np.abs(cleaned_female), axis=1), sr, 170.0)
    lead_env = base.envelope(np.mean(np.abs(lead), axis=1), sr, 120.0)
    female_db = base.amp_to_db(female_env)
    lead_db = base.amp_to_db(lead_env)

    active_female = female_db[female_db > -80.0]
    active_lead = lead_db[lead_db > -80.0]
    f_low = float(np.percentile(active_female, 48.0)) if len(active_female) else -45.0
    f_high = float(np.percentile(active_female, 83.0)) if len(active_female) else -25.0
    l_low = float(np.percentile(active_lead, 45.0)) if len(active_lead) else -45.0
    l_high = float(np.percentile(active_lead, 78.0)) if len(active_lead) else -25.0

    female_score = np.clip((female_db - f_low) / max(f_high - f_low, 1e-6), 0.0, 1.0)
    lead_score = np.clip((lead_db - l_low) / max(l_high - l_low, 1e-6), 0.0, 1.0)
    hook_score = np.clip((female_score ** 0.85) * (0.35 + 0.65 * lead_score), 0.0, 1.0)

    smooth = max(1, int(sr * 1.05))
    if smooth > 1:
        kernel = np.hanning(smooth * 2 + 1).astype(np.float32)
        kernel /= np.sum(kernel)
        hook_score = np.convolve(hook_score, kernel, mode="same")
    hook_score = np.clip(hook_score, 0.0, 1.0)

    # Lower quiet/non-hook moments so the female layer reads as hook/double support
    # rather than a full-time competing lead.
    gain_db = -3.6 + 1.8 * hook_score
    curve = base.db_to_amp(gain_db).astype(np.float32)
    report = {
        "quiet_gain_db": -3.6,
        "max_hook_gain_db": -1.8,
        "seconds_above_plus_1db": 0.0,
        "seconds_above_0db": 0.0,
        "female_target_vs_lead_db": base.FEMALE_TARGET_DELTA_DB,
    }
    return curve, report


def side_weight(layer: np.ndarray, mid_db: float = -5.2, side_db: float = 1.2) -> np.ndarray:
    left = layer[:, 0]
    right = layer[:, 1]
    mid = (left + right) * 0.5 * float(base.db_to_amp(mid_db))
    side = (left - right) * 0.5 * float(base.db_to_amp(side_db))
    return np.column_stack([mid + side, mid - side]).astype(np.float32)


def process_female_mask_layer(
    y: np.ndarray,
    sr: int,
    lead: np.ndarray,
    target_delta_db: float = -10.0,
) -> np.ndarray:
    x = base.mono_center(y)
    x = base.peak_cap(x, -5.8)
    x = base.spectral_denoise(x, sr, reduction_db=2.05, percentile=11.0)
    x = base.butter_filter(x, sr, "highpass", 145, 2)
    x = base.rbj_peaking(x, sr, 235, -2.2, 0.95)
    x = base.rbj_peaking(x, sr, 620, -1.35, 1.05)
    x = base.dynamic_band_tame(x, sr, 420, 900, max_cut_db=1.65, percentile=62.0, slope=0.54, smooth_ms=20.0)
    x = base.rbj_peaking(x, sr, 2850, 0.55, 0.9)
    x = base.dynamic_band_tame(x, sr, 5600, 9300, max_cut_db=4.0, percentile=54.0, slope=0.78, smooth_ms=6.0)
    x = base.dynamic_band_tame(x, sr, 9500, 16500, max_cut_db=2.8, percentile=60.0, slope=0.70, smooth_ms=8.0)
    x = base.compressor(x, sr, threshold_db=-24.5, ratio=1.48, attack_ms=16.0, release_ms=110.0, makeup_db=0.05)

    mono = np.mean(x, axis=1).astype(np.float32)
    d_left = int(round(sr * 0.010))
    d_right = int(round(sr * 0.019))
    left = np.zeros_like(mono)
    right = np.zeros_like(mono)
    left[:] = mono * 0.78
    right[d_left:] += mono[:-d_left] * 0.82
    left[d_right:] += mono[:-d_right] * 0.16
    right[:] += mono * 0.10
    layer = np.column_stack([left, right]).astype(np.float32)

    mask_band = base.butter_filter(layer, sr, "bandpass", (2200, 6500), order=2) * 0.16
    layer = (layer + side_weight(mask_band, mid_db=-7.0, side_db=0.8)).astype(np.float32)
    layer = side_weight(layer, mid_db=-5.2, side_db=1.2)

    curve, report = mask_activity_curve(x, lead, sr)
    layer = (layer * curve[:, None]).astype(np.float32)
    layer = base.match_active_rms(layer, base.active_rms_db(lead) + target_delta_db, max_gain_db=18.0)

    # Keep it from fighting the lead diction while still covering noise from the sides.
    layer = base.sidechain_band_duck(layer, lead, sr, 2100, 4800, max_cut_db=0.32, percentile=56.0, smooth_ms=100.0)
    layer = base.peak_cap(layer, -4.4)

    base.REPORTS.mkdir(parents=True, exist_ok=True)
    report.update(
        {
            "measured_active_rms_db": round(base.active_rms_db(layer), 2),
            "lead_active_rms_db": round(base.active_rms_db(lead), 2),
            "measured_vs_lead_db": round(base.active_rms_db(layer) - base.active_rms_db(lead), 2),
            "design": "side-heavy female hook/double mask layer; support only and de-centered with micro-delay/M-S weighting",
        }
    )
    (base.REPORTS / "female_mask_layer_decisions.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return layer.astype(np.float32)


def main() -> int:
    configure_base()
    base.process_female_layer = process_female_mask_layer
    return base.main()


if __name__ == "__main__":
    raise SystemExit(main())

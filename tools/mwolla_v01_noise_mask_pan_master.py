#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import subprocess
from pathlib import Path

import numpy as np


ROOT = Path("/Users/hantaeheuk/Documents/New project 3")
BASE_SCRIPT = ROOT / "tools" / "sonyeo_luka_v01_clear_master.py"
SLUG = "mwolla_v01_noise_mask_pan_master"


spec = importlib.util.spec_from_file_location("sonyeo_luka_v01_clear_master", BASE_SCRIPT)
if spec is None or spec.loader is None:
    raise RuntimeError(f"Could not load base script: {BASE_SCRIPT}")
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)

BASE_PROCESS_INSTRUMENT = base.process_instrument
BASE_PROCESS_BACKING_VOCALS = base.process_backing_vocals
BASE_WRITE_REPORTS = base.write_reports
BASE_BUILD_ZIP = base.build_zip


def configure_base() -> None:
    base.ZIP_SOURCE = Path("/Users/hantaeheuk/Downloads/뭘라.zip")
    base.SLUG = SLUG
    base.WORK = ROOT / "audio_work" / SLUG
    base.SOURCE = base.WORK / "source_stems"
    base.PROCESSED = base.WORK / "processed_stems"
    base.REAPER_DIR = ROOT / "reaper" / SLUG
    base.RENDERS = ROOT / "renders" / SLUG
    base.REPORTS = ROOT / "reports" / SLUG

    base.RPP = base.REAPER_DIR / "mwolla_v01_NOISE_MASK_PAN_MASTER.rpp"
    base.BUILD_LUA = base.REAPER_DIR / "build_mwolla_v01_noise_mask_pan_master.lua"
    base.RUN_BUILD_LUA = base.REAPER_DIR / "run_build_mwolla_v01_noise_mask_pan_master.lua"
    base.RENDER_LUA = base.REAPER_DIR / "render_mwolla_v01_noise_mask_pan_master.lua"
    base.RUN_RENDER_LUA = base.REAPER_DIR / "run_render_mwolla_v01_noise_mask_pan_master.lua"
    base.TRACE_JSON = base.REPORTS / "actual_reaper_plugin_trace.json"
    base.TRACE_MD = base.REPORTS / "actual_reaper_plugin_trace.md"

    base.REAPER_PRINT = base.RENDERS / "mwolla_v01_REAPERPRINT_24-48.wav"
    base.FINAL_WAV = base.RENDERS / "mwolla_v01_NOISE_MASK_PAN_MASTER.wav"
    base.FINAL_MP3 = base.RENDERS / "mwolla_v01_NOISE_MASK_PAN_MASTER_320k.mp3"
    base.VOCAL_SOLO = base.RENDERS / "mwolla_v01_VOCAL_SOLO_noise_mask_pan.wav"
    base.AB_PREVIEW_MP3 = base.RENDERS / "mwolla_v01_AB_original_to_noise_mask_master_320k.mp3"
    base.DELIVERABLE_ZIP = base.RENDERS / "mwolla_v01_NOISE_MASK_PAN_MASTER_DELIVERABLE.zip"

    base.FEMALE_TARGET_DELTA_DB = -1.1
    base.FEMALE_LAYER_FILENAME = "female_vocal_wide_noise_mask_layer.wav"
    base.FEMALE_TRACK_NAME = "13 Female wide panned noise-mask double"
    base.FEMALE_REPORT_LINE = (
        "- Use `13 Vocals.wav` as a wide panned support layer, roughly 1 dB under the lead in active RMS "
        "but de-centered and side-weighted so it masks AI/noise texture without becoming the lead."
    )
    base.REPORT_FILENAME = "mwolla_v01_noise_mask_pan_master_report.md"
    base.REPORT_TITLE = "Mwolla v01 Noise Mask Pan Master Report"
    base.PROJECT_NOTES = (
        "mwolla v01 noise mask pan master: original full mix is muted reference only. "
        "12 Vocals remains the clean centered lead. 13 Vocals is processed as a wide "
        "side-weighted female double/noise-mask layer. Codex Vocal AI Artifact Split Tamer "
        "is first FX slot on the lead vocal. No pitch/tune inserts and no heavy lead saturation."
    )


def process_lead_vocal(y: np.ndarray, sr: int) -> np.ndarray:
    x = base.mono_center(y)
    x = base.peak_cap(x, -6.0)
    x = base.spectral_denoise(x, sr, reduction_db=2.85, percentile=9.0)
    x = base.butter_filter(x, sr, "highpass", 92, 2)
    x = base.dynamic_band_tame(x, sr, 165, 360, max_cut_db=2.9, percentile=56.0, slope=0.62, smooth_ms=30.0)
    x = base.rbj_peaking(x, sr, 245, -1.25, 0.95)
    x = base.dynamic_band_tame(x, sr, 430, 920, max_cut_db=1.95, percentile=61.0, slope=0.52, smooth_ms=24.0)
    x = base.rbj_peaking(x, sr, 690, -0.85, 1.05)
    x = base.rbj_peaking(x, sr, 2550, 0.95, 0.78)
    x = base.rbj_peaking(x, sr, 3650, 0.35, 0.9)
    x = base.dynamic_band_tame(x, sr, 3300, 5350, max_cut_db=1.25, percentile=72.0, slope=0.60, smooth_ms=8.0)
    x = base.dynamic_band_tame(x, sr, 5750, 9300, max_cut_db=3.85, percentile=53.0, slope=0.82, smooth_ms=6.0)
    x = base.rbj_shelf(x, sr, 10800, -0.35, high=True, slope=0.70)
    x = base.dynamic_band_tame(x, sr, 9600, 17800, max_cut_db=3.15, percentile=55.0, slope=0.72, smooth_ms=7.0)
    x = base.compressor(x, sr, threshold_db=-23.8, ratio=1.58, attack_ms=20.0, release_ms=122.0, makeup_db=0.35)
    density = base.compressor(x, sr, threshold_db=-29.5, ratio=2.05, attack_ms=6.0, release_ms=96.0, makeup_db=0.18)
    x = (x * 0.975 + density * 0.025).astype(np.float32)
    x = base.soft_saturation(x, drive_db=0.22, mix=0.010)
    x, gate_report = vocal_gap_cleanup(x, sr, floor_db=-78.0, threshold_percentile=47.0, knee_db=9.0)
    write_gate_report("lead_vocal_gap_cleanup", gate_report)
    x = base.match_active_rms(x, -20.15, max_gain_db=5.0)
    x = base.peak_cap(x, -4.6)
    return base.soft_clip(x, ceiling=0.978)


def write_gate_report(name: str, report: dict[str, float]) -> None:
    base.REPORTS.mkdir(parents=True, exist_ok=True)
    path = base.REPORTS / "vocal_gap_cleanup_decisions.json"
    existing: dict[str, dict[str, float]] = {}
    if path.exists():
        existing = json.loads(path.read_text(encoding="utf-8"))
    existing[name] = report
    path.write_text(json.dumps(existing, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def vocal_gap_cleanup(
    y: np.ndarray,
    sr: int,
    floor_db: float,
    threshold_percentile: float,
    knee_db: float,
) -> tuple[np.ndarray, dict[str, float]]:
    mono = np.mean(y, axis=1).astype(np.float32)
    band = base.butter_filter(np.column_stack([mono, mono]).astype(np.float32), sr, "bandpass", (135, 6800), order=2)
    env = base.envelope(np.mean(np.abs(band), axis=1), sr, 42.0)
    env_db = base.amp_to_db(env)
    active = env_db[env_db > -88.0]
    threshold = float(np.percentile(active, threshold_percentile)) if len(active) else -58.0
    threshold = max(threshold, -55.5)
    open_score = np.clip((env_db - threshold) / max(knee_db, 1e-6), 0.0, 1.0)
    open_score = np.sqrt(open_score)

    smooth = max(1, int(sr * 0.36))
    if smooth > 1:
        kernel = np.hanning(smooth * 2 + 1).astype(np.float32)
        kernel /= np.sum(kernel)
        open_score = base.signal.fftconvolve(open_score, kernel, mode="same").astype(np.float32)

    tail_cleanup_start_s = None
    tail_cleanup_fade_s = 0.0
    frame = max(1, int(sr * 0.1))
    frames_n = len(mono) // frame
    if frames_n >= 80:
        framed = mono[: frames_n * frame].reshape(frames_n, frame)
        frame_rms = np.sqrt(np.mean(framed * framed, axis=1) + 1e-12)
        frame_db = base.amp_to_db(frame_rms)
        frame_active = frame_db[frame_db > -90.0]
        strong_threshold = max(float(np.percentile(frame_active, 68.0)) if len(frame_active) else -55.0, -45.0)
        window = 50
        hop = 10
        last_sustained_end = None
        for start in range(0, max(1, frames_n - window + 1), hop):
            stop = min(frames_n, start + window)
            chunk = frame_db[start:stop]
            duty = float(np.mean(chunk > strong_threshold))
            median_db = float(np.median(chunk))
            if duty >= 0.32 or median_db >= strong_threshold - 8.0:
                last_sustained_end = stop * 0.1
        if last_sustained_end is not None and (len(mono) / sr - last_sustained_end) >= 3.0:
            tail_start = int(min(len(open_score), (last_sustained_end + 1.0) * sr))
            fade_len = int(sr * 1.35)
            if tail_start < len(open_score):
                end = min(len(open_score), tail_start + fade_len)
                fade = np.linspace(1.0, 0.0, max(1, end - tail_start), dtype=np.float32)
                open_score[tail_start:end] *= fade
                open_score[end:] = 0.0
                tail_cleanup_start_s = round(float(tail_start / sr), 3)
                tail_cleanup_fade_s = round(float((end - tail_start) / sr), 3)
        final_window = min(frames_n, 50)
        if final_window >= 30:
            final_chunk = frame_db[frames_n - final_window : frames_n]
            final_duty = float(np.mean(final_chunk > strong_threshold))
            final_median = float(np.median(final_chunk))
            if final_median < strong_threshold - 18.0 and final_duty < 0.24:
                candidate_start = max(0.0, len(mono) / sr - final_window * 0.1 + 0.35)
                candidate_sample = int(candidate_start * sr)
                current_sample = int((tail_cleanup_start_s or 1e9) * sr)
                if candidate_sample < len(open_score) and candidate_sample < current_sample:
                    fade_len = int(sr * 0.95)
                    end = min(len(open_score), candidate_sample + fade_len)
                    fade = np.linspace(1.0, 0.0, max(1, end - candidate_sample), dtype=np.float32)
                    open_score[candidate_sample:end] *= fade
                    open_score[end:] = 0.0
                    tail_cleanup_start_s = round(float(candidate_sample / sr), 3)
                    tail_cleanup_fade_s = round(float((end - candidate_sample) / sr), 3)

    floor = float(base.db_to_amp(floor_db))
    gain = floor + (1.0 - floor) * np.clip(open_score, 0.0, 1.0)
    cleaned = (y * gain[:, None]).astype(np.float32)
    open_samples = int(np.sum(gain > float(base.db_to_amp(-8.0))))
    partial_samples = int(np.sum((gain > float(base.db_to_amp(-50.0))) & (gain <= float(base.db_to_amp(-8.0)))))
    last_open = np.flatnonzero(gain > float(base.db_to_amp(-18.0)))
    last_vocal_time = round(float(last_open[-1] / sr), 3) if len(last_open) else 0.0
    report = {
        "threshold_db": round(threshold, 2),
        "floor_db": floor_db,
        "open_seconds": round(open_samples / sr, 3),
        "transition_seconds": round(partial_samples / sr, 3),
        "muted_or_near_muted_seconds": round((len(gain) - open_samples - partial_samples) / sr, 3),
        "last_vocal_activity_s": last_vocal_time,
        "tail_cleanup_start_s": tail_cleanup_start_s,
        "tail_cleanup_fade_s": tail_cleanup_fade_s,
    }
    return cleaned, report


def mask_activity_curve(cleaned_female: np.ndarray, lead: np.ndarray, sr: int) -> tuple[np.ndarray, dict[str, float]]:
    female_env = base.envelope(np.mean(np.abs(cleaned_female), axis=1), sr, 165.0)
    lead_env = base.envelope(np.mean(np.abs(lead), axis=1), sr, 120.0)
    female_db = base.amp_to_db(female_env)
    lead_db = base.amp_to_db(lead_env)

    active_female = female_db[female_db > -80.0]
    active_lead = lead_db[lead_db > -80.0]
    f_low = float(np.percentile(active_female, 43.0)) if len(active_female) else -45.0
    f_high = float(np.percentile(active_female, 84.0)) if len(active_female) else -25.0
    l_low = float(np.percentile(active_lead, 42.0)) if len(active_lead) else -45.0
    l_high = float(np.percentile(active_lead, 77.0)) if len(active_lead) else -25.0

    female_score = np.clip((female_db - f_low) / max(f_high - f_low, 1e-6), 0.0, 1.0)
    lead_score = np.clip((lead_db - l_low) / max(l_high - l_low, 1e-6), 0.0, 1.0)
    mask_score = np.clip((female_score ** 0.78) * (lead_score ** 0.52), 0.0, 1.0)

    smooth = max(1, int(sr * 0.92))
    if smooth > 1:
        kernel = np.hanning(smooth * 2 + 1).astype(np.float32)
        kernel /= np.sum(kernel)
        mask_score = base.signal.fftconvolve(mask_score, kernel, mode="same").astype(np.float32)
    mask_score = np.clip(mask_score, 0.0, 1.0)

    gain_db = -1.05 + 3.25 * mask_score
    curve = base.db_to_amp(gain_db).astype(np.float32)
    report = {
        "quiet_gain_db": -1.05,
        "max_mask_gain_db": 2.2,
        "seconds_above_plus_1db": round(float(np.sum(gain_db > 1.0) / sr), 3),
        "seconds_above_0db": round(float(np.sum(gain_db > 0.0) / sr), 3),
        "female_target_vs_lead_db": base.FEMALE_TARGET_DELTA_DB,
    }
    return curve, report


def side_weight(layer: np.ndarray, mid_db: float = -6.2, side_db: float = 1.75) -> np.ndarray:
    left = layer[:, 0]
    right = layer[:, 1]
    mid = (left + right) * 0.5 * float(base.db_to_amp(mid_db))
    side = (left - right) * 0.5 * float(base.db_to_amp(side_db))
    return np.column_stack([mid + side, mid - side]).astype(np.float32)


def process_female_mask_layer(
    y: np.ndarray,
    sr: int,
    lead: np.ndarray,
    target_delta_db: float = -1.1,
) -> np.ndarray:
    x = base.mono_center(y)
    x = base.peak_cap(x, -6.0)
    x = base.spectral_denoise(x, sr, reduction_db=2.45, percentile=10.0)
    x = base.butter_filter(x, sr, "highpass", 150, 2)
    x = base.rbj_peaking(x, sr, 235, -2.35, 0.95)
    x = base.rbj_peaking(x, sr, 610, -1.45, 1.05)
    x = base.dynamic_band_tame(x, sr, 420, 940, max_cut_db=1.85, percentile=60.0, slope=0.56, smooth_ms=20.0)
    x = base.rbj_peaking(x, sr, 2750, 0.45, 0.9)
    x = base.dynamic_band_tame(x, sr, 5200, 9200, max_cut_db=4.4, percentile=52.0, slope=0.82, smooth_ms=6.0)
    x = base.dynamic_band_tame(x, sr, 9400, 16800, max_cut_db=3.1, percentile=58.0, slope=0.72, smooth_ms=8.0)
    x = base.compressor(x, sr, threshold_db=-24.7, ratio=1.42, attack_ms=17.0, release_ms=116.0, makeup_db=0.0)

    mono = np.mean(x, axis=1).astype(np.float32)
    d_left = int(round(sr * 0.008))
    d_right = int(round(sr * 0.020))
    left = mono * 0.72
    right = np.zeros_like(mono)
    right[d_left:] += mono[:-d_left] * 0.84
    left[d_right:] += mono[:-d_right] * 0.18
    right += mono * 0.12
    layer = np.column_stack([left, right]).astype(np.float32)

    mask_band = base.butter_filter(layer, sr, "bandpass", (2100, 6400), order=2) * 0.20
    layer = (layer + side_weight(mask_band, mid_db=-7.5, side_db=1.25)).astype(np.float32)
    layer = side_weight(layer, mid_db=-6.2, side_db=1.75)

    curve, report = mask_activity_curve(x, lead, sr)
    layer = (layer * curve[:, None]).astype(np.float32)
    layer = base.match_active_rms(layer, base.active_rms_db(lead) + target_delta_db, max_gain_db=18.0)
    layer = base.sidechain_band_duck(layer, lead, sr, 2150, 4900, max_cut_db=0.22, percentile=55.0, smooth_ms=105.0)
    layer, gap_report = vocal_gap_cleanup(layer, sr, floor_db=-82.0, threshold_percentile=43.0, knee_db=7.0)
    write_gate_report("female_side_mask_gap_cleanup", gap_report)
    layer = base.match_active_rms(layer, base.active_rms_db(lead) + target_delta_db, max_gain_db=8.0)
    layer = base.peak_cap(layer, -4.2)

    base.REPORTS.mkdir(parents=True, exist_ok=True)
    report.update(
        {
            "measured_active_rms_db": round(base.active_rms_db(layer), 2),
            "lead_active_rms_db": round(base.active_rms_db(lead), 2),
            "measured_vs_lead_db": round(base.active_rms_db(layer) - base.active_rms_db(lead), 2),
            "design": "wide side-heavy female double used as an active noise-mask support layer; lead remains centered and un-tuned",
        }
    )
    (base.REPORTS / "female_mask_layer_decisions.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return layer.astype(np.float32)


def process_backing_vocals(y: np.ndarray, sr: int, lead: np.ndarray) -> np.ndarray:
    x = BASE_PROCESS_BACKING_VOCALS(y, sr, lead)
    if float(base.amp_to_db(base.rms(x))) < -80.0:
        return x.astype(np.float32)
    x, gap_report = vocal_gap_cleanup(x, sr, floor_db=-82.0, threshold_percentile=45.0, knee_db=8.0)
    write_gate_report("backing_vocals_gap_cleanup", gap_report)
    return base.peak_cap(x, -7.2)


def process_instrument(role: str, y: np.ndarray, sr: int, lead: np.ndarray) -> np.ndarray:
    x = BASE_PROCESS_INSTRUMENT(role, y, sr, lead)
    if float(base.amp_to_db(base.rms(x))) < -80.0:
        return x.astype(np.float32)
    if role in {"synth", "keyboard", "guitar"}:
        x = base.sidechain_band_duck(x, lead, sr, 1800, 4800, max_cut_db=0.28, percentile=52.0, smooth_ms=120.0)
    elif role == "fx":
        x = base.dynamic_band_tame(x, sr, 7200, 13500, max_cut_db=0.65, percentile=72.0, smooth_ms=10.0)
    elif role == "drums":
        x = base.rbj_peaking(x, sr, 7200, -0.25, 0.85)
    return base.peak_cap(x, -2.5)


def final_master() -> None:
    filter_graph = (
        "highpass=f=24,"
        "equalizer=f=260:t=q:w=1:g=-0.25,"
        "equalizer=f=760:t=q:w=1.2:g=-0.12,"
        "equalizer=f=3150:t=q:w=0.9:g=0.10,"
        "equalizer=f=11200:t=q:w=0.8:g=-0.32,"
        "loudnorm=I=-10.55:TP=-1.30:LRA=4.0:linear=false,"
        "alimiter=limit=0.85:attack=2:release=85:level=false"
    )
    subprocess.run(
        [
            base.FFMPEG,
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(base.REAPER_PRINT),
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


def write_reports(paths: dict[str, Path], processed: dict[str, Path], vocal_balance: dict[str, float], gate: dict[str, object]) -> None:
    BASE_WRITE_REPORTS(paths, processed, vocal_balance, gate)
    report_path = base.REPORTS / base.REPORT_FILENAME
    gap_path = base.REPORTS / "vocal_gap_cleanup_decisions.json"
    gap_payload = json.loads(gap_path.read_text(encoding="utf-8")) if gap_path.exists() else {}
    lines = report_path.read_text(encoding="utf-8").rstrip().splitlines()
    lines.extend(
        [
            "",
            "## Vocal Gap Cleanup",
            "",
            "- Lead, backing, and female support layers were gated down in non-vocal gaps so residual AI/noise texture does not sit over instrumental-only moments.",
            "- The female layer is lead-gated and side-weighted; it covers noisy lead-vocal texture while the lead is active, then gets out of the way.",
            "- The late instrumental section was left as an instrumental transition; only short vocal ambience tails are allowed to decay into it.",
            f"- Gap cleanup report: `{base.rel(gap_path)}`",
            "",
            "```json",
            json.dumps(gap_payload, ensure_ascii=False, indent=2),
            "```",
        ]
    )
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_zip() -> None:
    BASE_BUILD_ZIP()
    extra_files = [
        base.REPORTS / "vocal_gap_cleanup_decisions.json",
        base.REPORTS / "female_mask_layer_decisions.json",
    ]
    with base.zipfile.ZipFile(base.DELIVERABLE_ZIP, "a", compression=base.zipfile.ZIP_DEFLATED) as archive:
        existing = set(archive.namelist())
        for path in extra_files:
            if path.exists():
                arcname = path.relative_to(ROOT).as_posix()
                if arcname not in existing:
                    archive.write(path, arcname)


def main() -> int:
    configure_base()
    base.process_lead_vocal = process_lead_vocal
    base.process_female_layer = process_female_mask_layer
    base.process_backing_vocals = process_backing_vocals
    base.process_instrument = process_instrument
    base.final_master = final_master
    base.write_reports = write_reports
    base.build_zip = build_zip
    return base.main()


if __name__ == "__main__":
    raise SystemExit(main())

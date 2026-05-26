#!/usr/bin/env python3
"""Source, reverb/delay, and plugin-trace proxy analysis.

This script is for final inspection preparation. It does not identify exact
commercial plugins from audio, remove provenance, or bypass metadata. It creates
evidence-based trace categories that can be reviewed in REAPER.
"""

from __future__ import annotations

import csv
import json
import math
import os
import shutil
import subprocess
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

import numpy as np
import pyloudnorm as pyln
import soundfile as sf
from scipy import signal


PROJECT_ROOT = Path("/Users/hantaeheuk/Documents/New project 3")
EXPECTED_INPUT_DIR = PROJECT_ROOT / "00_AUDIO_INPUT"
MENTIONED_INPUT_DIR = Path("/Users/hantaeheuk/Desktop/Estona-4dium_MASTER_24-48.")
REPORTS_DIR = PROJECT_ROOT / "reports"
AUDIO_EXTENSIONS = {".wav", ".wave", ".aif", ".aiff", ".flac", ".mp3", ".m4a"}
EPS = 1e-12


def db_amp(x: float) -> float:
    return 20.0 * math.log10(max(abs(float(x)), EPS))


def db_power(x: float) -> float:
    return 10.0 * math.log10(max(float(x), EPS))


def clamp(x: float, low: float = 0.0, high: float = 1.0) -> float:
    return float(max(low, min(high, x)))


def dist(values: Iterable[float]) -> dict:
    arr = np.asarray([v for v in values if isinstance(v, (int, float)) and np.isfinite(v)], dtype=float)
    if arr.size == 0:
        return {"median": None, "low": None, "high": None, "min": None, "max": None}
    return {
        "median": float(np.median(arr)),
        "low": float(np.percentile(arr, 25)),
        "high": float(np.percentile(arr, 75)),
        "min": float(np.min(arr)),
        "max": float(np.max(arr)),
    }


def ffmpeg_binary() -> str:
    env = os.environ.get("FFMPEG_PATH")
    if env and Path(env).exists():
        return env
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return "ffmpeg"


def ffprobe_binary() -> Optional[str]:
    return shutil.which("ffprobe")


def metadata_probe(path: Path) -> dict:
    probe = ffprobe_binary()
    if probe:
        try:
            out = subprocess.check_output(
                [
                    probe,
                    "-hide_banner",
                    "-v",
                    "error",
                    "-print_format",
                    "json",
                    "-show_format",
                    "-show_streams",
                    str(path),
                ],
                text=True,
            )
            return {"backend": "ffprobe", "data": json.loads(out)}
        except Exception as exc:
            return {"backend": "ffprobe", "error": str(exc)}
    try:
        proc = subprocess.run(
            [ffmpeg_binary(), "-hide_banner", "-i", str(path), "-f", "null", "-"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )
        return {"backend": "ffmpeg_stderr_fallback", "summary": proc.stderr[:4000]}
    except Exception as exc:
        return {"backend": "metadata_unavailable", "error": str(exc)}


def input_files() -> Tuple[List[Path], List[str]]:
    files: List[Path] = []
    missing: List[str] = []
    if EXPECTED_INPUT_DIR.exists():
        files.extend(p for p in EXPECTED_INPUT_DIR.iterdir() if p.is_file() and p.suffix.lower() in AUDIO_EXTENSIONS)
    else:
        missing.append(str(EXPECTED_INPUT_DIR))
    if MENTIONED_INPUT_DIR.exists():
        files.extend(p for p in MENTIONED_INPUT_DIR.iterdir() if p.is_file() and p.suffix.lower() in AUDIO_EXTENSIONS)
    unique = {}
    for p in files:
        unique[str(p.resolve())] = p
    return sorted(unique.values()), missing


def classify(path: Path) -> str:
    name = path.name.lower()
    if name == "current_mix.wav" or "current_mix" in name:
        return "current_mix"
    if "vocal_stem" in name or ("vocal" in name and "stem" in name):
        return "vocal_stem"
    if "instrumental_stem" in name or "instrumental" in name:
        return "instrumental_stem"
    if name.startswith("reference_") or "reference" in name or ("estona,nib" in name and "master" in name):
        return "reference"
    return "unknown_audio"


def frame_rms(x: np.ndarray, sr: int, window_ms: float = 30.0, hop_ms: float = 10.0) -> Tuple[np.ndarray, float]:
    win = max(64, int(sr * window_ms / 1000.0))
    hop = max(16, int(sr * hop_ms / 1000.0))
    if len(x) <= win:
        return np.asarray([math.sqrt(float(np.mean(x * x)) + EPS)]), hop / sr
    frames = np.lib.stride_tricks.sliding_window_view(x, win)[::hop]
    rms = np.sqrt(np.mean(frames * frames, axis=1) + EPS)
    return rms, hop / sr


def bandpass(x: np.ndarray, sr: int, low: float, high: float) -> np.ndarray:
    nyq = sr / 2.0
    low = max(5.0, low)
    high = min(high, nyq * 0.95)
    if high <= low:
        return x.copy()
    sos = signal.butter(4, [low / nyq, high / nyq], btype="bandpass", output="sos")
    try:
        return signal.sosfiltfilt(sos, x)
    except Exception:
        return signal.sosfilt(sos, x)


def lowpass(x: np.ndarray, sr: int, cutoff: float) -> np.ndarray:
    nyq = sr / 2.0
    sos = signal.butter(4, min(cutoff / nyq, 0.95), btype="lowpass", output="sos")
    try:
        return signal.sosfiltfilt(sos, x)
    except Exception:
        return signal.sosfilt(sos, x)


def welch(x: np.ndarray, sr: int) -> Tuple[np.ndarray, np.ndarray]:
    nperseg = min(16384, max(2048, int(sr * 0.25)))
    return signal.welch(x, fs=sr, nperseg=nperseg, noverlap=nperseg // 2)


def band_power(freqs: np.ndarray, pxx: np.ndarray, low: float, high: float) -> float:
    mask = (freqs >= low) & (freqs < high)
    if not np.any(mask):
        center = math.sqrt(low * high)
        return float(np.interp(center, freqs, pxx) * max(high - low, 1.0) + EPS)
    return float(np.sum(pxx[mask]) + EPS)


def loudness_pack(audio: np.ndarray, mono: np.ndarray, sr: int) -> dict:
    meter = pyln.Meter(sr, block_size=0.400)
    try:
        lufs = float(meter.integrated_loudness(audio if audio.shape[1] > 1 else mono))
    except Exception:
        lufs = db_amp(np.sqrt(np.mean(mono * mono) + EPS)) - 0.691
    peak = float(np.max(np.abs(audio)) + EPS)
    rms = float(np.sqrt(np.mean(mono * mono) + EPS))
    tp = float(np.max(np.abs(signal.resample_poly(audio, up=4, down=1, axis=0))) + EPS)
    return {
        "integrated_lufs": lufs,
        "peak_dbfs": db_amp(peak),
        "approx_true_peak_dbfs": db_amp(tp),
        "rms_dbfs": db_amp(rms),
        "crest_factor_db": db_amp(peak / max(rms, EPS)),
        "near_full_scale_sample_ratio": float(np.mean(np.abs(audio) > 0.999)),
    }


def source_trace(audio: np.ndarray, mono: np.ndarray, sr: int, info: sf.SoundFile) -> dict:
    freqs, pxx = welch(mono, sr)
    total = float(np.sum(pxx) + EPS)
    top12 = band_power(freqs, pxx, 12000, min(20000, sr / 2 * 0.95)) / total
    top16 = band_power(freqs, pxx, 16000, min(22000, sr / 2 * 0.95)) / total
    high_flat = spectral_flatness(freqs, pxx, 8000, min(20000, sr / 2 * 0.95))
    dc = float(np.mean(mono))
    low_level = mono[np.abs(mono) < np.percentile(np.abs(mono), 20)]
    noise_floor_db = db_amp(float(np.sqrt(np.mean(low_level * low_level) + EPS))) if low_level.size else -120.0
    cutoff_score = clamp((0.004 - top16) / 0.004)
    hash_score = clamp(high_flat * 1.05 + top12 * 2.75)
    lossy_container_mismatch = bool(info.format == "WAV" and cutoff_score > 0.6 and top12 < 0.01)
    return {
        "format": info.format,
        "subtype": info.subtype,
        "sample_rate": sr,
        "channels": int(audio.shape[1]),
        "dc_offset": dc,
        "noise_floor_proxy_dbfs": noise_floor_db,
        "top_12k_20k_ratio": float(top12),
        "top_16k_22k_ratio": float(top16),
        "high_band_flatness": float(high_flat),
        "sudden_hf_cutoff_score": cutoff_score,
        "ai_or_lossy_high_hash_score": hash_score,
        "lossy_source_suspicion_in_wav_container": lossy_container_mismatch,
        "source_trace_warning": "These are source-quality proxies, not proof of provenance or generation method.",
    }


def spectral_flatness(freqs: np.ndarray, pxx: np.ndarray, low: float, high: float) -> float:
    mask = (freqs >= low) & (freqs < high)
    if not np.any(mask):
        return 0.0
    mag = np.sqrt(pxx[mask] + EPS)
    return float(np.exp(np.mean(np.log(mag + EPS))) / (np.mean(mag) + EPS))


def envelope_autocorr_lags(env: np.ndarray, hop_s: float, low_ms: float, high_ms: float, max_items: int = 8) -> List[dict]:
    x = env.astype(float)
    x = x - np.median(x)
    if np.std(x) < EPS:
        return []
    x = x / (np.std(x) + EPS)
    ac = signal.correlate(x, x, mode="full")[len(x) - 1 :]
    ac = ac / (ac[0] + EPS)
    low = max(1, int(low_ms / 1000.0 / hop_s))
    high = min(len(ac) - 1, int(high_ms / 1000.0 / hop_s))
    if high <= low:
        return []
    region = ac[low:high]
    peaks, props = signal.find_peaks(region, height=0.05, distance=max(1, int(0.045 / hop_s)))
    rows = []
    for p in peaks:
        lag_frames = low + int(p)
        lag_ms = lag_frames * hop_s * 1000.0
        rows.append({
            "lag_ms": float(lag_ms),
            "strength": float(ac[lag_frames]),
            "tempo_quarter_bpm_candidate": float(60000.0 / lag_ms) if lag_ms > 0 else None,
            "tempo_eighth_bpm_candidate": float(30000.0 / lag_ms) if lag_ms > 0 else None,
        })
    return sorted(rows, key=lambda r: r["strength"], reverse=True)[:max_items]


def reverb_delay_trace(audio: np.ndarray, mono: np.ndarray, sr: int) -> dict:
    env, hop_s = frame_rms(mono, sr, 20.0, 10.0)
    env_db = 20 * np.log10(env + EPS)
    smooth_env = signal.medfilt(env, kernel_size=9 if len(env) >= 9 else max(3, len(env) // 2 * 2 + 1))
    peaks, props = signal.find_peaks(
        smooth_env,
        height=np.percentile(smooth_env, 75),
        distance=max(1, int(0.18 / hop_s)),
        prominence=max(np.std(smooth_env) * 0.35, EPS),
    )
    tail_ratios = []
    decay_slopes = []
    early_ratios = []
    for p in peaks[:350]:
        attack = smooth_env[p] + EPS
        early = smooth_env[p + int(0.025 / hop_s) : p + int(0.120 / hop_s)]
        tail = smooth_env[p + int(0.180 / hop_s) : p + int(0.900 / hop_s)]
        if early.size:
            early_ratios.append(float(np.mean(early) / attack))
        if tail.size >= 6:
            tail_ratios.append(float(np.mean(tail) / attack))
            y = 20 * np.log10(tail + EPS)
            t = np.arange(len(y)) * hop_s
            slope = np.polyfit(t, y, 1)[0]
            decay_slopes.append(float(slope))

    mid = mono
    side = np.zeros_like(mono)
    if audio.shape[1] > 1:
        mid = (audio[:, 0] + audio[:, 1]) * 0.5
        side = (audio[:, 0] - audio[:, 1]) * 0.5
    mid_env, _ = frame_rms(mid, sr, 30.0, 10.0)
    side_env, _ = frame_rms(side, sr, 30.0, 10.0)
    n = min(len(mid_env), len(side_env), len(smooth_env))
    loud_mask = smooth_env[:n] >= np.percentile(smooth_env[:n], 80)
    tail_mask = (smooth_env[:n] < np.percentile(smooth_env[:n], 60)) & (smooth_env[:n] > np.percentile(smooth_env[:n], 25))
    side_mid_loud = db_amp(np.mean(side_env[:n][loud_mask] + EPS) / max(np.mean(mid_env[:n][loud_mask] + EPS), EPS)) if np.any(loud_mask) else None
    side_mid_tail = db_amp(np.mean(side_env[:n][tail_mask] + EPS) / max(np.mean(mid_env[:n][tail_mask] + EPS), EPS)) if np.any(tail_mask) else None

    high = bandpass(mono, sr, 6500, min(12000, sr * 0.45))
    body = bandpass(mono, sr, 500, 2500)
    high_env, _ = frame_rms(high, sr, 30.0, 10.0)
    body_env, _ = frame_rms(body, sr, 30.0, 10.0)
    m = min(len(high_env), len(body_env), n)
    high_body_loud = db_amp(np.mean(high_env[:m][loud_mask[:m]] + EPS) / max(np.mean(body_env[:m][loud_mask[:m]] + EPS), EPS)) if np.any(loud_mask[:m]) else None
    high_body_tail = db_amp(np.mean(high_env[:m][tail_mask[:m]] + EPS) / max(np.mean(body_env[:m][tail_mask[:m]] + EPS), EPS)) if np.any(tail_mask[:m]) else None

    predelay = envelope_autocorr_lags(env, hop_s, 18, 120, 4)
    delay = envelope_autocorr_lags(env, hop_s, 120, 950, 8)
    tail_mean = float(np.median(tail_ratios)) if tail_ratios else 0.0
    early_mean = float(np.median(early_ratios)) if early_ratios else 0.0
    slope_med = float(np.median(decay_slopes)) if decay_slopes else 0.0
    tail_width_lift = (side_mid_tail - side_mid_loud) if side_mid_tail is not None and side_mid_loud is not None else 0.0
    high_damping = (high_body_tail - high_body_loud) if high_body_tail is not None and high_body_loud is not None else 0.0

    reverb_score = clamp(
        max(0.0, tail_mean - 0.55) / 0.35 * 0.45
        + max(0.0, early_mean - 0.55) / 0.40 * 0.20
        + max(0.0, tail_width_lift) / 18.0 * 0.25
        + max(0.0, slope_med + 2.0) / 8.0 * 0.10
    )
    best_delay_strength = max([d["strength"] for d in delay] or [0.0])
    delay_score = clamp((best_delay_strength - 0.25) / 0.55)
    if reverb_score < 0.25:
        rev_type = "dry_or_short_room_proxy"
    elif tail_width_lift > 3 and high_damping > -2:
        rev_type = "wide_bright_plate_or_shimmer_proxy"
    elif slope_med > -9:
        rev_type = "long_hall_or_washy_tail_proxy"
    elif high_damping < -5:
        rev_type = "dark_room_or_damped_plate_proxy"
    else:
        rev_type = "short_plate_room_proxy"

    return {
        "onset_count_used": int(len(peaks)),
        "early_reflection_ratio_proxy": early_mean,
        "tail_ratio_180_900ms_proxy": tail_mean,
        "tail_decay_slope_db_per_sec_proxy": slope_med,
        "tail_side_mid_db": side_mid_tail,
        "attack_side_mid_db": side_mid_loud,
        "tail_width_lift_db": tail_width_lift,
        "tail_high_body_db": high_body_tail,
        "attack_high_body_db": high_body_loud,
        "high_damping_tail_minus_attack_db": high_damping,
        "predelay_candidates_ms": predelay,
        "delay_repeat_candidates_ms": delay,
        "reverb_trace_score": reverb_score,
        "delay_trace_score": delay_score,
        "reverb_type_proxy": rev_type,
        "trace_limit": "Full-mix trace only. Exact reverb/delay plugin and send settings require stems/session data.",
    }


def plugin_trace_scores(audio: np.ndarray, mono: np.ndarray, sr: int, loud: dict, source: dict, rev: dict) -> dict:
    freqs, pxx = welch(mono, sr)
    total = float(np.sum(pxx) + EPS)
    low_side_risk = 0.0
    high_side_risk = 0.0
    if audio.shape[1] > 1:
        mid = (audio[:, 0] + audio[:, 1]) * 0.5
        side = (audio[:, 0] - audio[:, 1]) * 0.5
        fm, pm = welch(mid, sr)
        fs, ps = welch(side, sr)
        low_side_risk = clamp(band_power(fs, ps, 20, 120) / max(band_power(fm, pm, 20, 120), EPS) * 3.0)
        high_side_risk = clamp(band_power(fs, ps, 8000, 20000) / max(band_power(fm, pm, 8000, 20000), EPS))
    harsh = band_power(freqs, pxx, 5000, 8000) / total
    air = band_power(freqs, pxx, 8000, min(20000, sr / 2 * 0.95)) / total
    flat_high = spectral_flatness(freqs, pxx, 8000, min(20000, sr / 2 * 0.95))
    limiter = clamp((-6.0 - loud["integrated_lufs"]) / 4.0 + (8.0 - loud["crest_factor_db"]) / 5.0 + loud["near_full_scale_sample_ratio"] * 10.0)
    clipper = clamp((loud["approx_true_peak_dbfs"] + 1.0) / 3.0 + loud["near_full_scale_sample_ratio"] * 50.0)
    saturation = clamp(flat_high * 0.6 + harsh * 12.0 + air * 4.0 + (8.0 - loud["crest_factor_db"]) / 12.0)
    high_exciter = clamp(source["ai_or_lossy_high_hash_score"] * 0.7 + air * 4.0)
    pitch_artifact_proxy = clamp(flat_high * 0.5 + harsh * 10.0 + max(0.0, rev["tail_high_body_db"] or -99) / 20.0)
    return {
        "limiter_or_loudness_maximizer_trace": {"score": limiter, "confidence": "medium", "evidence": "LUFS, crest factor, near-full-scale sample ratio"},
        "clipper_trace": {"score": clipper, "confidence": "medium", "evidence": "sample peak and 4x true-peak proxy"},
        "saturation_or_exciter_trace": {"score": saturation, "confidence": "low_to_medium", "evidence": "high-band flatness, harsh/air ratios, crest"},
        "bright_exciter_or_ai_hash_trace": {"score": high_exciter, "confidence": "low", "evidence": "high-band flatness and 8-20 kHz energy"},
        "stereo_widener_trace": {"score": high_side_risk, "confidence": "medium", "evidence": "side/mid high-band energy"},
        "low_end_stereo_problem_trace": {"score": low_side_risk, "confidence": "medium", "evidence": "20-120 Hz side/mid energy"},
        "reverb_processor_trace": {"score": rev["reverb_trace_score"], "confidence": "low_to_medium", "evidence": "tail/early reflection/side width proxy"},
        "delay_processor_trace": {"score": rev["delay_trace_score"], "confidence": "low_to_medium", "evidence": "envelope autocorrelation repeat lags"},
        "pitch_tune_artifact_trace": {"score": pitch_artifact_proxy, "confidence": "low_without_vocal_stem", "evidence": "full-mix high-band proxy only; vocal stem required"},
        "trace_policy": "Scores are review clues, not proof of exact plugins.",
    }


def analyze(path: Path) -> dict:
    audio, sr = sf.read(str(path), always_2d=True, dtype="float64")
    info = sf.info(str(path))
    mono = audio.mean(axis=1)
    loud = loudness_pack(audio, mono, sr)
    source = source_trace(audio, mono, sr, info)
    rev = reverb_delay_trace(audio, mono, sr)
    plugin = plugin_trace_scores(audio, mono, sr, loud, source, rev)
    return {
        "filename": path.name,
        "path": str(path),
        "role": classify(path),
        "inventory": {
            "duration_sec": float(len(mono) / sr),
            "sample_rate": sr,
            "channels": int(audio.shape[1]),
            "format": info.format,
            "subtype": info.subtype,
            "file_size_bytes": path.stat().st_size,
        },
        "metadata": metadata_probe(path),
        "loudness": loud,
        "source_trace": source,
        "reverb_delay_trace": rev,
        "plugin_trace_scores": plugin,
    }


def aggregate(items: List[dict]) -> dict:
    plugin_keys = [
        "limiter_or_loudness_maximizer_trace",
        "clipper_trace",
        "saturation_or_exciter_trace",
        "bright_exciter_or_ai_hash_trace",
        "stereo_widener_trace",
        "low_end_stereo_problem_trace",
        "reverb_processor_trace",
        "delay_processor_trace",
        "pitch_tune_artifact_trace",
    ]
    return {
        "loudness_target": dist(i["loudness"]["integrated_lufs"] for i in items),
        "crest_target": dist(i["loudness"]["crest_factor_db"] for i in items),
        "true_peak_proxy_target": dist(i["loudness"]["approx_true_peak_dbfs"] for i in items),
        "reverb_trace_target": {
            "early_reflection_ratio": dist(i["reverb_delay_trace"]["early_reflection_ratio_proxy"] for i in items),
            "tail_ratio_180_900ms": dist(i["reverb_delay_trace"]["tail_ratio_180_900ms_proxy"] for i in items),
            "tail_decay_slope_db_per_sec": dist(i["reverb_delay_trace"]["tail_decay_slope_db_per_sec_proxy"] for i in items),
            "tail_width_lift_db": dist(i["reverb_delay_trace"]["tail_width_lift_db"] for i in items),
            "high_damping_tail_minus_attack_db": dist(i["reverb_delay_trace"]["high_damping_tail_minus_attack_db"] for i in items),
        },
        "source_trace_target": {
            "hf_cutoff_score": dist(i["source_trace"]["sudden_hf_cutoff_score"] for i in items),
            "high_hash_score": dist(i["source_trace"]["ai_or_lossy_high_hash_score"] for i in items),
            "noise_floor_proxy_dbfs": dist(i["source_trace"]["noise_floor_proxy_dbfs"] for i in items),
        },
        "plugin_trace_target_scores": {
            key: dist(i["plugin_trace_scores"][key]["score"] for i in items) for key in plugin_keys
        },
    }


def safe_score_label(score: Optional[float]) -> str:
    if score is None:
        return "n/a"
    if score >= 0.75:
        return "high"
    if score >= 0.45:
        return "medium"
    return "low"


def write_reports(data: dict) -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    (REPORTS_DIR / "source_reverb_plugin_trace_analysis.json").write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    with (REPORTS_DIR / "final_inspection_trace_table.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["filename", "role", "lufs", "crest_db", "reverb_score", "delay_score", "limiter_score", "clipper_score", "widener_score", "hash_score", "review_action"])
        for item in data["files"]:
            scores = item["plugin_trace_scores"]
            writer.writerow([
                item["filename"],
                item["role"],
                f"{item['loudness']['integrated_lufs']:.2f}",
                f"{item['loudness']['crest_factor_db']:.2f}",
                f"{scores['reverb_processor_trace']['score']:.3f}",
                f"{scores['delay_processor_trace']['score']:.3f}",
                f"{scores['limiter_or_loudness_maximizer_trace']['score']:.3f}",
                f"{scores['clipper_trace']['score']:.3f}",
                f"{scores['stereo_widener_trace']['score']:.3f}",
                f"{scores['bright_exciter_or_ai_hash_trace']['score']:.3f}",
                "review in final inspection, do not treat as exact plugin ID",
            ])

    lines = [
        "# Source/Reverb/Plugin Trace Analysis",
        "",
        "이 보고서는 플러그인 흔적을 확정하지 않습니다. 오디오에서 관찰되는 기술적 흔적을 REAPER 최후검수 후보로 코드화한 것입니다.",
        "",
        f"- Files analyzed: {len(data['files'])}",
        f"- Mode: `{data['status']}`",
        "",
        "## Aggregate Trace Targets",
    ]
    agg = data["aggregate"]
    lines += [
        f"- Loudness target: {fmt_range(agg['loudness_target'], ' LUFS')}",
        f"- Crest target: {fmt_range(agg['crest_target'], ' dB')}",
        f"- Reverb early reflection ratio: {fmt_range(agg['reverb_trace_target']['early_reflection_ratio'])}",
        f"- Reverb tail 180-900ms ratio: {fmt_range(agg['reverb_trace_target']['tail_ratio_180_900ms'])}",
        f"- Tail width lift: {fmt_range(agg['reverb_trace_target']['tail_width_lift_db'], ' dB')}",
        f"- High damping tail-attack: {fmt_range(agg['reverb_trace_target']['high_damping_tail_minus_attack_db'], ' dB')}",
        "",
        "## Per File Trace Summary",
    ]
    for item in data["files"]:
        scores = item["plugin_trace_scores"]
        rev = item["reverb_delay_trace"]
        lines += [
            f"### {item['filename']}",
            f"- Reverb proxy: {rev['reverb_type_proxy']} score {rev['reverb_trace_score']:.2f}; delay score {rev['delay_trace_score']:.2f}.",
            f"- Tail: early {rev['early_reflection_ratio_proxy']:.3f}, tail {rev['tail_ratio_180_900ms_proxy']:.3f}, slope {rev['tail_decay_slope_db_per_sec_proxy']:.2f} dB/sec, width lift {rev['tail_width_lift_db']:.2f} dB.",
            f"- Delay candidates: {format_lags(rev['delay_repeat_candidates_ms'][:4])}",
            f"- Plugin traces: limiter {scores['limiter_or_loudness_maximizer_trace']['score']:.2f}, clipper {scores['clipper_trace']['score']:.2f}, saturation/exciter {scores['saturation_or_exciter_trace']['score']:.2f}, widener {scores['stereo_widener_trace']['score']:.2f}, high hash {scores['bright_exciter_or_ai_hash_trace']['score']:.2f}.",
        ]
    (REPORTS_DIR / "source_reverb_plugin_trace_analysis.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    inspection = [
        "# Final Inspection Entry Mode",
        "",
        "목적: 레퍼런스 마스터에서 추출한 기술적 흔적을 기준으로, REAPER 자동화/렌더 전 최후검수 항목을 기입한다.",
        "",
        "## 0. Safety",
        "- [ ] 레퍼런스의 멜로디/훅/리듬/편곡/보컬 정체성을 복제하지 않는다.",
        "- [ ] provenance, watermark, metadata를 기만적으로 제거하지 않는다.",
        "- [ ] Antares 사용 없음.",
        "- [ ] 유료 플러그인은 사용자가 명시 허용한 것만 사용.",
        "",
        "## 1. Source/Codec/Container",
        f"- Target noise floor proxy: {fmt_range(agg['source_trace_target']['noise_floor_proxy_dbfs'], ' dBFS')}",
        f"- Target high hash score: {fmt_range(agg['source_trace_target']['high_hash_score'])}",
        "- [ ] 현재 믹스가 reference보다 HF cutoff/hash가 과한지 확인",
        "- [ ] clipping/true-peak proxy가 안전한지 확인",
        "- Notes:",
        "",
        "## 2. EQ Static 후보",
        "- [ ] 20-120 Hz: mono sub/808 weight 확인",
        "- [ ] 120-350 Hz: mud/boxiness 확인",
        "- [ ] 350-1000 Hz: body/readability 확인",
        "- [ ] 2-5 kHz: vocal/presence 과밀 확인",
        "- [ ] 5-8 kHz: harshness 확인",
        "- [ ] 8-20 kHz: air/hash/fizz 확인",
        "- Notes:",
        "",
        "## 3. Dynamic EQ 후보",
        "- [ ] ReaXcomp/TDR Nova 후보 band를 dense control map에서 확인",
        "- [ ] p90/burstiness가 높은 대역만 dynamic cut",
        "- [ ] 보컬 stem 없을 때는 full-mix de-harsh만 보수적으로",
        "- Notes:",
        "",
        "## 4. Reverb/Delay Trace",
        f"- Reference early reflection ratio: {fmt_range(agg['reverb_trace_target']['early_reflection_ratio'])}",
        f"- Reference tail ratio: {fmt_range(agg['reverb_trace_target']['tail_ratio_180_900ms'])}",
        f"- Reference tail width lift: {fmt_range(agg['reverb_trace_target']['tail_width_lift_db'], ' dB')}",
        "- [ ] 현재 보컬이 dry/detached이면 short room or plate send 추가",
        "- [ ] delay repeat 후보가 곡 groove와 충돌하지 않는지 확인",
        "- [ ] high damping이 부족하면 reverb return LPF/De-ess",
        "- Notes:",
        "",
        "## 5. Saturation/Clip/Limiter",
        f"- Limiter trace target: {fmt_range(agg['plugin_trace_target_scores']['limiter_or_loudness_maximizer_trace'])}",
        f"- Clipper trace target: {fmt_range(agg['plugin_trace_target_scores']['clipper_trace'])}",
        f"- Saturation/exciter trace target: {fmt_range(agg['plugin_trace_target_scores']['saturation_or_exciter_trace'])}",
        "- [ ] loudness를 올리기 전에 5-8 kHz harshness를 먼저 제어",
        "- [ ] clipper는 drum/beat/mix bus에 소량, master는 ceiling 안전",
        "- Notes:",
        "",
        "## 6. M/S EQ and Width",
        f"- Stereo widener trace target: {fmt_range(agg['plugin_trace_target_scores']['stereo_widener_trace'])}",
        "- [ ] 20-120 Hz side가 reference보다 크면 MonoSub/side cut",
        "- [ ] 8-20 kHz side가 과하면 high-side hash cut",
        "- Notes:",
        "",
        "## 7. Final Decision",
        "- [ ] PASS: current mix matches broad technical target and listening check passes.",
        "- [ ] REVISE: specific issue remains.",
        "- [ ] HOLD: missing current/stem material prevents honest decision.",
        "- Decision notes:",
    ]
    (REPORTS_DIR / "final_inspection_entry_mode.md").write_text("\n".join(inspection) + "\n", encoding="utf-8")


def fmt_range(r: dict, unit: str = "") -> str:
    if not isinstance(r, dict) or r.get("median") is None:
        return "n/a"
    return f"{r['median']:.3f}{unit} (IQR {r['low']:.3f} to {r['high']:.3f}{unit})"


def format_lags(lags: List[dict]) -> str:
    if not lags:
        return "none"
    return ", ".join(f"{x['lag_ms']:.0f}ms/{x['strength']:.2f}" for x in lags)


def main() -> None:
    files, missing = input_files()
    analyzed = [analyze(path) for path in files]
    data = {
        "status": "reference_only_trace_mode" if not any(i["role"] == "current_mix" for i in analyzed) else "current_trace_mode",
        "missing_expected_inputs": missing + [str(EXPECTED_INPUT_DIR / n) for n in ["current_mix.wav", "vocal_stem.wav", "instrumental_stem.wav"] if not (EXPECTED_INPUT_DIR / n).exists()],
        "policy": {
            "technical_traces_only": True,
            "exact_plugin_identification_not_claimed": True,
            "do_not_remove_provenance_or_metadata_for_deception": True,
        },
        "files": analyzed,
        "aggregate": aggregate(analyzed),
    }
    write_reports(data)
    print(json.dumps({"status": data["status"], "files": len(analyzed), "reports": ["source_reverb_plugin_trace_analysis.md", "final_inspection_entry_mode.md"]}, indent=2))


if __name__ == "__main__":
    main()

from __future__ import annotations

import csv
import json
import math
import os
import shutil
import subprocess
import sys
import uuid
import zipfile
from pathlib import Path

import numpy as np
from scipy import signal

ROOT = Path("/Users/hantaeheuk/Documents/New project 3")
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.mgmg_v03_human_vocal_dynamic_fx import (  # noqa: E402
    FFMPEG,
    amp_db,
    audio_metrics,
    bandpass,
    biquad_peaking,
    biquad_shelf,
    butter_filter,
    compressor,
    convert_mp3,
    db_amp,
    delay_samples,
    dynamic_band_tame,
    ffmpeg_loudnorm,
    limiter,
    ms_width,
    normalize_to_rms,
    pan_stereo,
    read_wav,
    reverb_send,
    rms,
    saturate,
    sidechain_duck_full,
    soft_clip,
    stem_metrics,
    write_float_wav,
)
from tools.mgmg_v11_female_70_mseq_layers import (  # noqa: E402
    bass_stable_grit,
    drums_stable_punch,
    stable_master_tone,
    static_music_space,
)


SLUG = os.environ.get("S0101_DUAL_SLUG", "0101_suno_dual_voice_v08_male_clear_strict_female_timing")
BPM = 135
BASE_SLUG = "0101_suno_studio_v01"
WORK = ROOT / "audio_work" / SLUG
STEMS = WORK / "stems"
PROCESSED = WORK / "processed"
INTERMEDIATE = WORK / "intermediate"
SOURCE_NEW = WORK / "source_new_dual_voice"
SOURCE_ZIP = Path("/Users/hantaeheuk/Downloads/숨 참는 거리 Stems.zip")
BASE_STEMS = ROOT / "audio_work" / BASE_SLUG / "stems"
RENDERS = ROOT / "renders" / SLUG
REPORTS = ROOT / "reports" / SLUG
REAPER_DIR = ROOT / "reaper" / SLUG
RPP = REAPER_DIR / "0101_REAPER_DUAL_VOICE_MIX_MASTER_PROJECT.rpp"
MIX_POLISH_MOVES: dict[str, list[dict[str, object]]] = {}

BASE_REQUIRED = [
    "0101_original_reference.wav",
    "0101_vocal_raw.wav",
    "0101_instrumental_raw.wav",
    "0101_drums_raw.wav",
    "0101_bass808_raw.wav",
    "0101_melody_raw.wav",
    "0101_keyboard_raw.wav",
    "0101_synth_raw.wav",
    "0101_fx_raw.wav",
    "0101_percussion_raw.wav",
    "0101_backing_vocals_raw.wav",
]


def ensure_dirs() -> None:
    for directory in (WORK, STEMS, PROCESSED, INTERMEDIATE, SOURCE_NEW, RENDERS, REPORTS, REAPER_DIR):
        directory.mkdir(parents=True, exist_ok=True)


def extract_new_zip_if_needed() -> None:
    lead = SOURCE_NEW / "0 Lead Vocals.wav"
    inst = SOURCE_NEW / "1 Instrumental.wav"
    if lead.exists() and inst.exists():
        return
    if not SOURCE_ZIP.exists():
        raise FileNotFoundError(SOURCE_ZIP)
    with zipfile.ZipFile(SOURCE_ZIP) as zf:
        for member in zf.infolist():
            name = Path(member.filename)
            if "__MACOSX" in name.parts or name.name.startswith("._"):
                continue
            zf.extract(member, SOURCE_NEW)


def copy_sources() -> dict[str, Path]:
    copied: dict[str, Path] = {}
    for name in BASE_REQUIRED:
        src = BASE_STEMS / name
        if not src.exists():
            raise FileNotFoundError(src)
        dst = STEMS / name
        shutil.copy2(src, dst)
        copied[name] = dst
    new_map = {
        "0 Lead Vocals.wav": "0101_new_suno_dual_voice_raw.wav",
        "1 Instrumental.wav": "0101_new_suno_instrumental_reference.wav",
    }
    for source, dest in new_map.items():
        src = SOURCE_NEW / source
        if not src.exists():
            raise FileNotFoundError(src)
        dst = STEMS / dest
        shutil.copy2(src, dst)
        copied[dest] = dst
    return copied


def pad_or_trim(y: np.ndarray, length: int) -> np.ndarray:
    if len(y) == length:
        return y.astype(np.float32)
    if len(y) > length:
        return y[:length].astype(np.float32)
    return np.vstack([y.astype(np.float32), np.zeros((length - len(y), 2), dtype=np.float32)])


def safe_normalize_to_rms(y: np.ndarray, target_db: float) -> np.ndarray:
    if rms(y) < 1e-9:
        return y.astype(np.float32)
    return normalize_to_rms(y, target_db).astype(np.float32)


def safe_sum(parts: list[tuple[np.ndarray, float]], length: int, ceiling_db: float = -1.4) -> np.ndarray:
    out = np.zeros((length, 2), dtype=np.float32)
    for y, gain_db in parts:
        out += pad_or_trim(y, length) * float(amp_db(gain_db))
    return limiter(out, ceiling_db)


def fade_window(length: int, fade_samples: int) -> np.ndarray:
    env = np.ones(length, dtype=np.float32)
    fade_samples = min(max(int(fade_samples), 1), max(length // 2, 1))
    if fade_samples > 1:
        ramp = np.linspace(0.0, 1.0, fade_samples, dtype=np.float32)
        env[:fade_samples] *= ramp
        env[-fade_samples:] *= ramp[::-1]
    return env


def edge_fade(y: np.ndarray, sr: int, fade_ms: float = 24.0) -> np.ndarray:
    out = y.copy()
    n = min(max(int(sr * fade_ms / 1000.0), 1), max(len(out) // 2, 1))
    if n > 1:
        ramp = np.linspace(0.0, 1.0, n, dtype=np.float32)
        out[:n] *= ramp[:, None]
        out[-n:] *= ramp[::-1, None]
    return out.astype(np.float32)


def frame_env(y: np.ndarray, sr: int, kind: str, rate: int = 50) -> np.ndarray:
    mono = np.mean(y, axis=1).astype(np.float32)
    if kind == "low":
        mono = np.mean(bandpass(y, sr, 35, 170, 3), axis=1).astype(np.float32)
    elif kind == "mid":
        mono = np.mean(bandpass(y, sr, 180, 4500, 3), axis=1).astype(np.float32)
    win = max(int(sr / rate), 1)
    frames = len(mono) // win
    mono = mono[: frames * win]
    if frames <= 0:
        return np.zeros(0, dtype=np.float32)
    env = np.sqrt(np.mean(mono.reshape(frames, win) ** 2, axis=1) + 1e-12).astype(np.float32)
    env = np.log1p(env * 80.0)
    return ((env - np.mean(env)) / (np.std(env) + 1e-8)).astype(np.float32)


def best_offset(ref: np.ndarray, cand: np.ndarray, rate: int = 50, max_shift_s: float = 80.0) -> list[dict[str, float]]:
    if len(ref) == 0 or len(cand) == 0:
        return []
    max_shift = int(max_shift_s * rate)
    corr = signal.correlate(ref, cand, mode="full", method="fft")
    lags = np.arange(-len(cand) + 1, len(ref))
    mask = (lags >= -max_shift) & (lags <= max_shift)
    corr_m = corr[mask]
    lags_m = lags[mask]
    if len(corr_m) == 0:
        return []
    top = min(24, len(corr_m))
    idxs = np.argpartition(corr_m, -top)[-top:]
    rows: list[dict[str, float]] = []
    for idx in idxs:
        lag = int(lags_m[idx])
        if lag >= 0:
            a = ref[lag : min(len(ref), lag + len(cand))]
            b = cand[: len(a)]
        else:
            b = cand[-lag : min(len(cand), len(ref) - lag)]
            a = ref[: len(b)]
        if len(a) < rate * 8:
            continue
        score = float(np.dot(a, b) / ((np.linalg.norm(a) * np.linalg.norm(b)) + 1e-9))
        rows.append({"score": score, "offset_s": lag / rate, "overlap_s": len(a) / rate})
    rows = sorted(rows, key=lambda row: row["score"], reverse=True)
    deduped: list[dict[str, float]] = []
    for row in rows:
        if all(abs(row["offset_s"] - old["offset_s"]) > 0.16 for old in deduped):
            deduped.append(row)
        if len(deduped) >= 6:
            break
    return deduped


def detect_alignment(audio: dict[str, np.ndarray], sr: int) -> dict[str, object]:
    checks = []
    pairs = [
        ("vocal_full", audio["0101_vocal_raw.wav"], audio["0101_new_suno_dual_voice_raw.wav"], "full", 1.0),
        ("vocal_mid", audio["0101_vocal_raw.wav"], audio["0101_new_suno_dual_voice_raw.wav"], "mid", 0.9),
        ("instrumental_low", audio["0101_instrumental_raw.wav"], audio["0101_new_suno_instrumental_reference.wav"], "low", 0.55),
        ("instrumental_mid", audio["0101_instrumental_raw.wav"], audio["0101_new_suno_instrumental_reference.wav"], "mid", 0.4),
        ("instrumental_full", audio["0101_instrumental_raw.wav"], audio["0101_new_suno_instrumental_reference.wav"], "full", 0.25),
    ]
    vocal_offsets: list[float] = []
    vocal_weights: list[float] = []
    instrumental_offsets: list[float] = []
    instrumental_weights: list[float] = []
    for name, ref, cand, kind, base_weight in pairs:
        found = best_offset(frame_env(ref, sr, kind), frame_env(cand, sr, kind), rate=50, max_shift_s=80.0)
        best = found[0] if found else {"score": 0.0, "offset_s": 0.0, "overlap_s": 0.0}
        checks.append({"check": name, "kind": kind, "best": best, "candidates": found})
        if name.startswith("vocal") and best["score"] >= 0.20:
            vocal_offsets.append(float(best["offset_s"]))
            vocal_weights.append(max(float(best["score"]), 0.05) * base_weight)
        elif best["score"] >= 0.15:
            instrumental_offsets.append(float(best["offset_s"]))
            instrumental_weights.append(max(float(best["score"]), 0.05) * base_weight)
    if vocal_offsets:
        # The new file is used as a vocal layer, so phrase alignment beats
        # low-end/instrumental correlation when those disagree.
        offset_s = float(np.average(np.array(vocal_offsets), weights=np.array(vocal_weights)))
    elif instrumental_offsets:
        offset_s = float(np.average(np.array(instrumental_offsets), weights=np.array(instrumental_weights)))
    else:
        offset_s = 0.0
    vocal_score = float(checks[0]["best"]["score"])
    instrumental_score = max(float(row["best"]["score"]) for row in checks if str(row["check"]).startswith("instrumental"))
    accepted = bool(vocal_score >= 0.24 and instrumental_score >= 0.15)
    return {
        "offset_s": round(offset_s, 3),
        "accepted": accepted,
        "vocal_score": round(vocal_score, 4),
        "instrumental_score": round(instrumental_score, 4),
        "checks": checks,
        "decision": "use_new_dual_voice_layer" if accepted else "reference_only_do_not_layer",
    }


def place_at(source: np.ndarray, length: int, sr: int, offset_s: float) -> tuple[np.ndarray, dict[str, float]]:
    out = np.zeros((length, 2), dtype=np.float32)
    offset = int(round(offset_s * sr))
    src_start = max(-offset, 0)
    dst_start = max(offset, 0)
    usable = min(len(source) - src_start, length - dst_start)
    if usable > 0:
        segment = source[src_start : src_start + usable].copy()
        segment *= fade_window(usable, int(sr * 0.018))[:, None]
        out[dst_start : dst_start + usable] = segment
    return out, {
        "offset_s": round(offset_s, 3),
        "dst_start_s": round(dst_start / sr, 3),
        "src_start_s": round(src_start / sr, 3),
        "placed_duration_s": round(max(usable, 0) / sr, 3),
    }


def activity_envelope(y: np.ndarray, sr: int, low: float = 170.0, high: float = 5200.0, smooth_ms: float = 55.0) -> np.ndarray:
    band = bandpass(y, sr, low, high, 3)
    mono = np.mean(band, axis=1)
    rectified = np.abs(mono).astype(np.float32)
    kernel_len = max(int(sr * smooth_ms / 1000.0), 3)
    kernel = np.hanning(kernel_len).astype(np.float32)
    kernel /= max(float(np.sum(kernel)), 1e-9)
    return signal.fftconvolve(rectified, kernel, mode="same").astype(np.float32)


def frame_local_similarity(a: np.ndarray, b: np.ndarray, frame: int, hop: int) -> tuple[np.ndarray, np.ndarray]:
    values: list[float] = []
    centers: list[int] = []
    for start in range(0, max(len(a) - frame, 1), hop):
        aa = a[start : start + frame]
        bb = b[start : start + frame]
        if len(aa) < max(frame // 2, 1) or len(bb) < max(frame // 2, 1):
            continue
        aa = aa - float(np.mean(aa))
        bb = bb - float(np.mean(bb))
        denom = float(np.linalg.norm(aa) * np.linalg.norm(bb)) + 1e-9
        values.append(float(np.dot(aa, bb) / denom))
        centers.append(start + len(aa) // 2)
    if not values:
        return np.zeros(1, dtype=np.float32), np.zeros(1, dtype=np.int64)
    return np.array(values, dtype=np.float32), np.array(centers, dtype=np.int64)


def downsample_envelope(env: np.ndarray, sr: int, rate: int = 100) -> np.ndarray:
    win = max(int(sr / rate), 1)
    frames = len(env) // win
    if frames <= 0:
        return np.zeros(0, dtype=np.float32)
    clipped = env[: frames * win].reshape(frames, win)
    out = np.mean(clipped, axis=1).astype(np.float32)
    out = out / (float(np.percentile(out[out > 1e-10], 95)) + 1e-10) if np.any(out > 1e-10) else out
    return np.clip(out, 0.0, 3.0).astype(np.float32)


def local_timing_confidence_mask(
    male: np.ndarray,
    female: np.ndarray,
    sr: int,
    rate: int = 100,
    frame_s: float = 0.62,
    hop_s: float = 0.045,
    max_lag_s: float = 0.16,
) -> tuple[np.ndarray, dict[str, object]]:
    male_env_full = activity_envelope(male, sr, 180, 5200, 48)
    female_env_full = activity_envelope(female, sr, 180, 5200, 48)
    male_env = downsample_envelope(male_env_full, sr, rate)
    female_env = downsample_envelope(female_env_full, sr, rate)
    n = min(len(male_env), len(female_env))
    male_env = male_env[:n]
    female_env = female_env[:n]
    if n == 0:
        return np.zeros(len(male), dtype=np.float32), {"stage": "strict_local_timing_mask", "coverage_pct": 0.0, "events": 0}

    active_male = male_env[male_env > 1e-6]
    active_female = female_env[female_env > 1e-6]
    male_thr = max(float(np.percentile(active_male, 35)) if len(active_male) else 0.02, 0.045)
    female_thr = max(float(np.percentile(active_female, 37)) if len(active_female) else 0.02, 0.040)
    frame = max(int(frame_s * rate), 8)
    hop = max(int(hop_s * rate), 1)
    max_lag = max(int(max_lag_s * rate), 1)
    mask_points = np.zeros(n, dtype=np.float32)
    score_values: list[float] = []
    lag_values: list[float] = []
    valid_count = 0

    for start in range(0, max(n - frame, 1), hop):
        end = min(start + frame, n)
        if end - start < frame // 2:
            continue
        m = male_env[start:end]
        if float(np.max(m)) < male_thr:
            continue
        best_score = -1.0
        best_lag = 999
        for lag in range(-max_lag, max_lag + 1):
            fs = start + lag
            fe = end + lag
            if fs < 0 or fe > n:
                continue
            f = female_env[fs:fe]
            if float(np.max(f)) < female_thr:
                continue
            mm = m - float(np.mean(m))
            ff = f - float(np.mean(f))
            denom = float(np.linalg.norm(mm) * np.linalg.norm(ff)) + 1e-9
            score = float(np.dot(mm, ff) / denom)
            if score > best_score:
                best_score = score
                best_lag = lag
        if best_score < -0.5:
            continue
        score_values.append(best_score)
        lag_values.append(best_lag / rate)
        # Be strict: if the best local match is too far from the current grid, mute it.
        if best_score >= 0.24 and abs(best_lag / rate) <= 0.055:
            mask_points[start:end] = np.maximum(mask_points[start:end], min(1.0, 0.35 + best_score * 1.25))
            valid_count += 1

    if not np.any(mask_points > 0):
        return np.zeros(len(male), dtype=np.float32), {
            "stage": "strict_local_timing_mask",
            "coverage_pct": 0.0,
            "events": 0,
            "valid_windows": 0,
            "score_median": round(float(np.median(score_values)), 4) if score_values else None,
            "abs_lag_median_s": round(float(np.median(np.abs(lag_values))), 4) if lag_values else None,
        }

    close = max(int(0.030 * rate), 1)
    mask_points = np.convolve(mask_points, np.ones(close, dtype=np.float32), mode="same")
    mask_points = np.clip(mask_points, 0.0, 1.0)
    mask_full = np.interp(
        np.arange(len(male)),
        np.arange(n) * (sr / rate),
        mask_points,
        left=0.0,
        right=0.0,
    ).astype(np.float32)
    fade = max(int(sr * 0.070), 3)
    kernel = np.hanning(fade).astype(np.float32)
    kernel /= max(float(np.sum(kernel)), 1e-9)
    mask_full = np.clip(signal.fftconvolve(mask_full, kernel, mode="same"), 0.0, 1.0).astype(np.float32)
    events = int(np.sum(np.diff((mask_full > 0.08).astype(np.int8), prepend=0) == 1))
    return mask_full, {
        "stage": "strict_local_timing_mask",
        "coverage_pct": round(float(np.mean(mask_full > 0.08) * 100.0), 2),
        "events": events,
        "valid_windows": valid_count,
        "score_median": round(float(np.median(score_values)), 4) if score_values else None,
        "score_p75": round(float(np.percentile(score_values, 75)), 4) if score_values else None,
        "abs_lag_median_s": round(float(np.median(np.abs(lag_values))), 4) if lag_values else None,
        "max_allowed_abs_lag_s": 0.055,
        "note": "female layer is only opened when local phrase envelope is close to the male vocal grid",
    }


def make_male_matched_female_layer(female: np.ndarray, male: np.ndarray, sr: int) -> tuple[np.ndarray, dict[str, object]]:
    """Keep the Suno female/dual layer only where it follows the male lead phrasing."""
    female = pad_or_trim(female, len(male))
    female = butter_filter(female, sr, "highpass", 170, 3)
    female, fizz1 = dynamic_band_tame(female, sr, 2500, 5200, 2.0, 66, 70)
    female, fizz2 = dynamic_band_tame(female, sr, 5400, 9200, 4.0, 58, 42)
    female, fizz3 = dynamic_band_tame(female, sr, 9000, 13200, 3.8, 60, 38)
    female = biquad_peaking(female, sr, 760, -0.6, 1.15)
    female = biquad_shelf(female, sr, 9200, -1.1, True)
    mask, timing = local_timing_confidence_mask(male, female, sr)
    center_shadow = female * mask[:, None] * float(amp_db(-12.5))
    wide = (
        pan_stereo(delay_samples(female, int(sr * 0.010)), -0.58)
        + pan_stereo(delay_samples(female, int(sr * 0.021)), 0.58)
    ) * (mask[:, None] * float(amp_db(-7.3)))
    layer = ms_width(wide + center_shadow, 1.25)
    layer, tame = dynamic_band_tame(layer.astype(np.float32), sr, 5400, 11800, 4.2, 58, 44)
    layer = safe_normalize_to_rms(layer, -27.8)
    layer = limiter(layer, -2.4)
    return layer.astype(np.float32), {
        "stage": "male_matched_female_layer",
        "coverage_pct": timing.get("coverage_pct", 0.0),
        "events": timing.get("events", 0),
        "timing": timing,
        "note": "dirty/off-beat female regions are muted; only strict male-matched timing windows remain",
        "female_pre_layer_cleanup": [fizz1, fizz2, fizz3],
        "high_tame": tame,
    }


def suppress_sip_breaths(y: np.ndarray, sr: int, label: str) -> tuple[np.ndarray, dict[str, object]]:
    high = bandpass(y, sr, 5200, 12000, 3)
    mid = bandpass(y, sr, 260, 2600, 2)
    high_env = np.abs(np.mean(high, axis=1))
    mid_env = np.abs(np.mean(mid, axis=1))
    smooth = max(int(sr * 0.018), 1)
    kernel = np.ones(smooth, dtype=np.float32) / smooth
    high_env = np.convolve(high_env, kernel, mode="same")
    mid_env = np.convolve(mid_env, kernel, mode="same")
    active_high = high_env[high_env > 1e-8]
    if not len(active_high):
        return y.astype(np.float32), {"stage": "sip_breath_suppress", "label": label, "events": 0}
    threshold = max(float(np.percentile(active_high, 97.0)), float(np.max(active_high) * 0.32))
    ratio = high_env / (mid_env + 1e-8)
    mask = (high_env > threshold) & (ratio > 1.55)
    width = max(int(sr * 0.058), 1)
    mask = np.convolve(mask.astype(np.float32), np.ones(width, dtype=np.float32), mode="same") > 0
    fade = max(int(sr * 0.040), 3)
    fade_kernel = np.hanning(fade).astype(np.float32)
    fade_kernel /= max(float(np.sum(fade_kernel)), 1e-9)
    mask_f = np.clip(np.convolve(mask.astype(np.float32), fade_kernel, mode="same"), 0.0, 1.0)
    out = y - high * (mask_f[:, None] * 0.76)
    out, stats = dynamic_band_tame(out.astype(np.float32), sr, 5600, 11800, 3.2, 63, 55)
    return out.astype(np.float32), {
        "stage": "sip_breath_suppress",
        "label": label,
        "events": int(np.sum(np.diff(mask.astype(np.int8), prepend=0) == 1)),
        "dynamic_tame": stats,
    }


def suppress_beep_artifacts(y: np.ndarray, sr: int, label: str, strength: float = 0.92) -> tuple[np.ndarray, dict[str, object]]:
    high = bandpass(y, sr, 3500, 15500, 4)
    low_mid = bandpass(y, sr, 150, 2600, 2)
    high_env = np.abs(np.mean(high, axis=1))
    low_env = np.abs(np.mean(low_mid, axis=1))
    smooth = max(int(sr * 0.006), 1)
    kernel = np.ones(smooth, dtype=np.float32) / smooth
    high_env = np.convolve(high_env, kernel, mode="same")
    low_env = np.convolve(low_env, kernel, mode="same")
    active = high_env[high_env > 1e-8]
    if not len(active):
        return y.astype(np.float32), {"stage": "beep_artifact_suppress", "label": label, "events": 0}
    threshold = max(float(np.percentile(active, 96.0)), float(np.max(active) * 0.22))
    ratio = high_env / (low_env + 1e-8)
    mask = (high_env > threshold) & (ratio > 0.72)
    mask[: int(sr * 0.16)] = True
    width = max(int(sr * 0.045), 1)
    mask = np.convolve(mask.astype(np.float32), np.ones(width, dtype=np.float32), mode="same") > 0
    fade_len = max(int(sr * 0.060), 3)
    fade = np.hanning(fade_len).astype(np.float32)
    fade /= max(float(np.sum(fade)), 1e-9)
    mask_f = np.clip(np.convolve(mask.astype(np.float32), fade, mode="same"), 0.0, 1.0)
    out = y - high * (mask_f[:, None] * strength)
    out, dyn = dynamic_band_tame(out.astype(np.float32), sr, 3600, 12500, 2.8, 60, 42)
    return out.astype(np.float32), {
        "stage": "beep_artifact_suppress",
        "label": label,
        "events": int(np.sum(np.diff(mask.astype(np.int8), prepend=0) == 1)),
        "strength": strength,
        "dynamic_tame": dyn,
    }


def vocal_level_ride(
    y: np.ndarray,
    sr: int,
    target_db: float,
    max_cut_db: float = -7.0,
    max_boost_db: float = 1.0,
    label: str = "vocal",
) -> tuple[np.ndarray, dict[str, object]]:
    mono = np.mean(y, axis=1)
    frame = max(int(sr * 0.060), 1)
    hop = max(int(sr * 0.020), 1)
    values: list[float] = []
    centers: list[int] = []
    for start in range(0, max(len(mono) - frame, 1), hop):
        seg = mono[start : start + frame]
        if len(seg):
            values.append(math.sqrt(float(np.mean(seg * seg)) + 1e-12))
            centers.append(start + len(seg) // 2)
    if not values:
        return y.astype(np.float32), {"stage": "vocal_level_ride", "label": label, "active_windows": 0}
    vals = np.array(values, dtype=np.float32)
    active = vals > max(1e-5, float(np.percentile(vals, 42)) * 0.56)
    gain_points = np.zeros_like(vals)
    if np.any(active):
        current_db = db_amp(vals[active])
        desired = np.clip(target_db - current_db, max_cut_db, max_boost_db)
        gain_points[active] = desired
    sample_gain = np.interp(np.arange(len(mono)), centers, gain_points, left=0.0, right=0.0).astype(np.float32)
    kernel_len = max(int(sr * 0.220), 3)
    kernel = np.hanning(kernel_len).astype(np.float32)
    kernel /= max(float(np.sum(kernel)), 1e-9)
    sample_gain = np.convolve(sample_gain, kernel, mode="same").astype(np.float32)
    return (y * amp_db(sample_gain)[:, None]).astype(np.float32), {
        "stage": "vocal_level_ride",
        "label": label,
        "target_db": target_db,
        "active_windows": int(np.sum(active)),
        "min_gain_db": round(float(np.min(sample_gain)), 3),
        "median_gain_db": round(float(np.median(sample_gain)), 3),
        "max_gain_db": round(float(np.max(sample_gain)), 3),
    }


def vocal_clarity_without_loudness(y: np.ndarray, sr: int, label: str) -> tuple[np.ndarray, list[dict[str, object]]]:
    out = y.copy()
    out, mud = dynamic_band_tame(out, sr, 210, 430, 1.8, 70, 135)
    out, box = dynamic_band_tame(out, sr, 720, 1280, 1.2, 72, 120)
    presence = bandpass(out, sr, 1800, 4200, 3)
    diction = bandpass(out, sr, 2600, 5200, 3)
    out = out + presence * float(amp_db(-11.5)) + diction * float(amp_db(-15.5))
    out, harsh = dynamic_band_tame(out, sr, 3900, 7800, 2.7, 66, 60)
    out, hiss = dynamic_band_tame(out, sr, 7600, 13000, 3.1, 64, 50)
    out = biquad_peaking(out, sr, 2850, 0.35, 1.0)
    out = biquad_shelf(out, sr, 11200, -0.55, True)
    return out.astype(np.float32), [
        {"stage": "vocal_clarity_without_loudness", "label": label},
        {"stage": "clarity_mud_control", **mud},
        {"stage": "clarity_box_control", **box},
        {"stage": "clarity_harsh_control", **harsh},
        {"stage": "clarity_hiss_control", **hiss},
    ]


def spectral_denoise_vocal(
    y: np.ndarray,
    sr: int,
    label: str,
    reduction: float = 0.52,
    high_reduction: float = 0.72,
    floor: float = 0.50,
    high_floor: float = 0.38,
) -> tuple[np.ndarray, dict[str, object]]:
    nperseg = 2048
    noverlap = 1024
    out_channels = []
    noise_frame_counts = []
    mean_gain_values = []
    high_gain_values = []
    for ch in range(2):
        freq, _, zxx = signal.stft(
            y[:, ch],
            fs=sr,
            window="hann",
            nperseg=nperseg,
            noverlap=noverlap,
            boundary="zeros",
            padded=True,
        )
        mag = np.abs(zxx).astype(np.float32)
        phase = np.exp(1j * np.angle(zxx))
        frame_energy = np.mean(mag, axis=0)
        if frame_energy.size == 0:
            out_channels.append(y[:, ch])
            continue
        noise_mask = frame_energy <= np.percentile(frame_energy, 24)
        if int(np.sum(noise_mask)) < 8:
            noise_mask = frame_energy <= np.percentile(frame_energy, 34)
        noise_profile = np.percentile(mag[:, noise_mask], 58, axis=1)[:, None] if np.any(noise_mask) else np.percentile(mag, 18, axis=1)[:, None]
        high_weight = np.clip((freq[:, None] - 3800.0) / 6200.0, 0.0, 1.0).astype(np.float32)
        reduction_curve = reduction + (high_reduction - reduction) * high_weight
        floor_curve = floor + (high_floor - floor) * high_weight
        ratio = noise_profile / (mag + 1e-8)
        gain = 1.0 - reduction_curve * np.power(np.clip(ratio, 0.0, 4.0), 0.82)
        gain = np.clip(gain, floor_curve, 1.0).astype(np.float32)
        cleaned_mag = mag * gain
        _, cleaned = signal.istft(cleaned_mag * phase, fs=sr, window="hann", nperseg=nperseg, noverlap=noverlap, input_onesided=True, boundary=True)
        cleaned = cleaned.astype(np.float32)
        if len(cleaned) < len(y):
            cleaned = np.pad(cleaned, (0, len(y) - len(cleaned)))
        out_channels.append(cleaned[: len(y)].astype(np.float32))
        noise_frame_counts.append(int(np.sum(noise_mask)))
        mean_gain_values.append(float(np.mean(gain)))
        high_band = freq >= 5500
        high_gain_values.append(float(np.mean(gain[high_band])) if np.any(high_band) else float(np.mean(gain)))
    out = np.column_stack(out_channels).astype(np.float32)
    return out, {
        "stage": "spectral_denoise_vocal",
        "label": label,
        "reduction": reduction,
        "high_reduction": high_reduction,
        "floor": floor,
        "high_floor": high_floor,
        "noise_frames_per_channel": noise_frame_counts,
        "mean_gain": round(float(np.mean(mean_gain_values)), 4) if mean_gain_values else 1.0,
        "mean_high_band_gain": round(float(np.mean(high_gain_values)), 4) if high_gain_values else 1.0,
    }


def male_dynamic_resonance_eq(y: np.ndarray, sr: int, label: str) -> tuple[np.ndarray, list[dict[str, object]]]:
    out = y.copy()
    moves: list[dict[str, object]] = []
    bands = [
        (250, 390, 1.7, 66, 145, "low_mud_ring"),
        (430, 620, 1.2, 72, 130, "box_resonance"),
        (690, 930, 1.9, 64, 115, "nasal_plastic_ring"),
        (980, 1320, 1.7, 66, 105, "formant_honk"),
        (1550, 2180, 1.0, 73, 95, "forward_resonance"),
        (2850, 3850, 2.2, 62, 70, "hard_attack_edge"),
        (4100, 5600, 1.8, 64, 62, "scratch_presence"),
        (6100, 8500, 3.4, 58, 45, "sibilance_hash"),
        (8800, 12800, 2.8, 61, 42, "ai_air_fizz"),
    ]
    for low, high, cut, pct, smooth, name in bands:
        out, stats = dynamic_band_tame(out, sr, low, high, cut, pct, smooth)
        moves.append({"stage": f"male_dynamic_eq_{name}", "label": label, **stats})
    out = biquad_peaking(out, sr, 315, -0.35, 1.2)
    out = biquad_peaking(out, sr, 880, -0.45, 1.3)
    out = biquad_peaking(out, sr, 3250, 0.30, 0.9)
    out = biquad_shelf(out, sr, 11800, -0.35, True)
    moves.append({"stage": "male_static_finish_eq", "low_mid_db": -0.35, "nasal_db": -0.45, "presence_restore_db": 0.30, "air_trim_db": -0.35})
    return out.astype(np.float32), moves


def male_presence_restore(y: np.ndarray, sr: int, label: str) -> tuple[np.ndarray, dict[str, object]]:
    presence = bandpass(y, sr, 1350, 4300, 3)
    presence = compressor(presence, sr, threshold_db=-29.0, ratio=2.2, smooth_ms=38, makeup_db=0.0)
    presence, tame = dynamic_band_tame(presence, sr, 3300, 5600, 1.4, 70, 46)
    presence = saturate(presence, drive_db=0.7, mix=0.055)
    out = y + presence * float(amp_db(-13.4))
    return out.astype(np.float32), {
        "stage": "male_presence_restore_without_level_push",
        "label": label,
        "presence_return_db": -13.4,
        "dynamic_tame": tame,
    }


def full_mix_resonance_polish(y: np.ndarray, sr: int) -> tuple[np.ndarray, list[dict[str, object]]]:
    out = y.copy()
    moves: list[dict[str, object]] = []
    for low, high, cut, pct, smooth, name in [
        (230, 420, 0.9, 76, 170, "mix_low_mid_resonance"),
        (680, 1120, 0.75, 78, 145, "mix_nasal_resonance"),
        (2450, 4200, 0.85, 76, 105, "mix_presence_spike"),
        (5400, 9200, 1.0, 74, 72, "mix_sibilance_hash"),
    ]:
        out, stats = dynamic_band_tame(out, sr, low, high, cut, pct, smooth)
        moves.append({"stage": name, **stats})
    out = biquad_peaking(out, sr, 760, -0.12, 0.9)
    out = biquad_shelf(out, sr, 12000, -0.10, True)
    moves.append({"stage": "full_mix_static_resonance_finish", "nasal_db": -0.12, "air_trim_db": -0.10})
    return out.astype(np.float32), moves


def process_voice(y: np.ndarray, sr: int, label: str, target_rms_db: float, hpf: float) -> tuple[np.ndarray, list[dict[str, object]]]:
    moves: list[dict[str, object]] = []
    out = edge_fade(y, sr, 26.0)
    out = butter_filter(out, sr, "highpass", hpf, 3)
    moves.append({"stage": "highpass", "label": label, "hz": hpf})
    out, beep = suppress_beep_artifacts(out, sr, label, strength=0.94)
    out, breath = suppress_sip_breaths(out, sr, label)
    moves.extend([beep, breath])
    is_male = label == "original_male_vocal"
    is_new_dual_voice = label == "new_suno_dual_voice"
    if is_male:
        out, denoise = spectral_denoise_vocal(out, sr, label, reduction=0.52, high_reduction=0.72, floor=0.50, high_floor=0.38)
        moves.append(denoise)
    elif is_new_dual_voice:
        out, denoise = spectral_denoise_vocal(out, sr, label, reduction=0.64, high_reduction=0.82, floor=0.43, high_floor=0.28)
        moves.append(denoise)
    for low, high, cut, pct, smooth, name in [
        (185, 370, 1.8, 70, 130, "mud_cleanup"),
        (700, 1250, 1.5, 72, 120, "nasal_plastic_cleanup"),
        (2500, 4800, 2.5, 67, 78, "harsh_attack_cleanup"),
        (5450, 8450, 3.8, 62, 52, "de_ess"),
        (8500, 12500, 3.0, 66, 48, "metallic_ai_fizz_cleanup"),
    ]:
        out, stats = dynamic_band_tame(out, sr, low, high, cut, pct, smooth)
        moves.append({"stage": name, **stats})
    if is_male:
        out, resonance_moves = male_dynamic_resonance_eq(out, sr, label)
        moves.extend(resonance_moves)
    out, clarity = vocal_clarity_without_loudness(out, sr, label)
    moves.extend(clarity)
    if is_male:
        out, presence_restore = male_presence_restore(out, sr, label)
        moves.append(presence_restore)
    out = saturate(out, drive_db=1.2, mix=0.06)
    out = compressor(out, sr, threshold_db=-25.5, ratio=1.9, smooth_ms=95, makeup_db=0.1)
    out, ride = vocal_level_ride(out, sr, target_db=-23.8, max_cut_db=-7.0, max_boost_db=0.75, label=label)
    moves.append(ride)
    out = safe_normalize_to_rms(out, target_rms_db)
    out = limiter(out, -2.0)
    moves.append({"stage": "final_vocal_gain_stage", "label": label, "target_rms_dbfs": target_rms_db})
    return out.astype(np.float32), moves


def detect_drum_onsets(drums: np.ndarray, sr: int, max_count: int = 180) -> list[int]:
    mono = np.mean(bandpass(drums, sr, 35, 180, 3), axis=1)
    frame = int(sr * 0.012)
    hop = int(sr * 0.01)
    if len(mono) < frame * 2:
        return []
    env = np.array(
        [math.sqrt(float(np.mean(mono[i : i + frame] ** 2)) + 1e-12) for i in range(0, len(mono) - frame, hop)],
        dtype=np.float32,
    )
    diff = np.maximum(0.0, env - np.roll(env, 1))
    threshold = max(float(np.percentile(diff, 93.3)), float(np.max(diff) * 0.17))
    min_gap = max(int(0.18 / (hop / sr)), 1)
    onsets: list[int] = []
    last = -min_gap
    for idx, value in enumerate(diff):
        if value < threshold or idx - last < min_gap:
            continue
        if value >= float(np.max(diff[max(0, idx - 2) : min(len(diff), idx + 3)])):
            onsets.append(idx * hop)
            last = idx
    return onsets[:max_count]


def make_round_kick_support(length: int, sr: int, onsets: list[int]) -> np.ndarray:
    support = np.zeros((length, 2), dtype=np.float32)
    dur = int(sr * 0.22)
    t = np.arange(dur, dtype=np.float32) / sr
    sweep = 64.0 - 18.0 * np.clip(t / 0.18, 0.0, 1.0)
    phase = 2.0 * np.pi * np.cumsum(sweep) / sr
    body = np.sin(phase) * np.exp(-t * 18.0)
    click = np.sin(2.0 * np.pi * 118.0 * t) * np.exp(-t * 52.0)
    shape = (body * 0.82 + click * 0.14).astype(np.float32)
    shape *= fade_window(len(shape), int(sr * 0.004))
    for onset in onsets:
        end = min(onset + dur, length)
        if end > onset:
            seg = shape[: end - onset]
            support[onset:end, 0] += seg
            support[onset:end, 1] += seg
    support = butter_filter(support, sr, "lowpass", 760, 3)
    support = saturate(support, drive_db=1.0, mix=0.10)
    return safe_normalize_to_rms(support, -26.2) if np.max(np.abs(support)) > 1e-8 else support


def process_instrumental(audio: dict[str, np.ndarray], sr: int, vocal_trigger: np.ndarray) -> tuple[dict[str, np.ndarray], dict[str, object]]:
    length = len(audio["0101_original_reference.wav"])
    inst_raw = audio["0101_instrumental_raw.wav"]
    drums_raw = audio["0101_drums_raw.wav"]
    bass_raw = audio["0101_bass808_raw.wav"]
    melody_raw = safe_sum(
        [
            (audio["0101_melody_raw.wav"], 0.0),
            (audio["0101_keyboard_raw.wav"], 1.0),
            (audio["0101_synth_raw.wav"], -0.8),
        ],
        length,
        -1.8,
    )
    fx_raw = safe_sum([(audio["0101_fx_raw.wav"], -2.0), (audio["0101_percussion_raw.wav"], -4.0)], length, -2.2)

    inst_clean = butter_filter(inst_raw, sr, "highpass", 24, 3)
    inst_clean, inst_mud = dynamic_band_tame(inst_clean, sr, 210, 520, 1.5, 73, 145)
    inst_clean, inst_nasal = dynamic_band_tame(inst_clean, sr, 650, 1180, 0.9, 78, 150)
    inst_clean, inst_presence_ring = dynamic_band_tame(inst_clean, sr, 1700, 3300, 0.65, 80, 130)
    inst_clean, inst_harsh = dynamic_band_tame(inst_clean, sr, 2800, 6200, 1.0, 75, 95)
    inst_clean = biquad_shelf(inst_clean, sr, 10800, -0.20, True)
    inst_clean = ms_width(inst_clean, 0.35)

    drums_proc, drum_moves = drums_stable_punch(drums_raw, sr)
    onsets = detect_drum_onsets(drums_proc, sr)
    kick_support = make_round_kick_support(length, sr, onsets)
    drums_final = limiter(drums_proc * float(amp_db(0.35)) + kick_support * float(amp_db(-8.0)), -1.8)

    bass_proc, bass_moves = bass_stable_grit(bass_raw, drums_final, sr)
    sub = butter_filter(bass_proc, sr, "lowpass", 98, 4)
    sub = np.column_stack([np.mean(sub, axis=1), np.mean(sub, axis=1)]).astype(np.float32)
    bass_final = limiter(bass_proc * float(amp_db(0.6)) + sub * float(amp_db(-2.9)), -1.9)

    melody = butter_filter(melody_raw, sr, "highpass", 95, 3)
    melody, melody_mud = dynamic_band_tame(melody, sr, 220, 640, 1.5, 72, 145)
    melody, melody_nasal = dynamic_band_tame(melody, sr, 760, 1280, 0.8, 78, 135)
    melody, melody_glass = dynamic_band_tame(melody, sr, 3600, 7800, 0.7, 80, 90)
    melody = biquad_peaking(melody, sr, 1550, 0.45, 0.9)
    melody = biquad_peaking(melody, sr, 3200, 0.45, 1.0)
    melody = biquad_shelf(melody, sr, 9800, -0.12, True)
    melody = static_music_space(melody, sr)
    melody = safe_normalize_to_rms(melody, -20.8)
    melody = sidechain_duck_full(melody, vocal_trigger, sr, amount_db=0.18, release_ms=125, threshold_percentile=70)

    fx = butter_filter(fx_raw, sr, "highpass", 140, 2)
    fx, fx_mud = dynamic_band_tame(fx, sr, 220, 700, 2.0, 73, 150)
    fx = ms_width(fx, 0.9)

    instrumental = safe_sum(
        [
            (inst_clean, -1.2),
            (drums_final, -8.8),
            (bass_final, -8.7),
            (melody, 3.8),
            (fx, -11.5),
        ],
        length,
        -1.4,
    )
    instrumental = sidechain_duck_full(instrumental, vocal_trigger, sr, amount_db=0.10, release_ms=145, threshold_percentile=72)
    instrumental = limiter(instrumental, -1.5)
    return {
        "instrumental": instrumental,
        "drums": drums_final,
        "bass": bass_final,
        "melody": melody,
        "fx": fx,
        "kick_support": kick_support,
    }, {
        "instrumental": [
            {"stage": "raw_instrumental_cleanup", **inst_mud},
            {"stage": "instrumental_nasal_resonance_cleanup", **inst_nasal},
            {"stage": "instrumental_presence_ring_cleanup", **inst_presence_ring},
            {"stage": "instrumental_harsh_tame", **inst_harsh},
        ],
        "drums": drum_moves + [{"stage": "round_kick_support", "detected_onsets": len(onsets), "gain_db": -8.0}],
        "bass": bass_moves + [{"stage": "mono_sub_reinforcement", "lowpass_hz": 98, "gain_db": -2.9}],
        "melody": [
            {"stage": "melody_forward_overlay", "rms_target_dbfs": -20.8, "mix_gain_db": 3.8},
            {"stage": "melody_mud_control", **melody_mud},
            {"stage": "melody_nasal_resonance_control", **melody_nasal},
            {"stage": "melody_glass_resonance_control", **melody_glass},
        ],
        "fx": [{"stage": "fx_tucked", **fx_mud}],
    }


def render_mix_versions(sr: int, processed: dict[str, np.ndarray]) -> dict[str, Path]:
    inst = processed["instrumental"]
    melody = processed["melody"]
    male = processed["male_vocal"]
    dual = processed["new_dual_voice"]
    length = len(inst)

    vocal_reverb = (
        reverb_send(male, sr, decay_s=0.58, wet_db=-23.0, predelay_ms=24, hp_hz=380, lp_hz=7200, seed=61)
        + reverb_send(dual, sr, decay_s=0.66, wet_db=-25.0, predelay_ms=32, hp_hz=430, lp_hz=7000, seed=62)
    )

    versions = {
        "dual_voice_layer": safe_sum(
            [
                (inst, -0.5),
                (melody, 2.4),
                (male, -1.5),
                (dual, -7.0),
                (vocal_reverb, -1.0),
            ],
            length,
            -1.6,
        ),
        "new_dual_voice_alt": safe_sum(
            [
                (inst, -0.6),
                (melody, 2.2),
                (male, -3.1),
                (dual, -6.0),
                (vocal_reverb, -0.8),
            ],
            length,
            -1.6,
        ),
        "male_lead_new_voice_support": safe_sum(
            [
                (inst, -0.5),
                (melody, 2.5),
                (male, -0.5),
                (dual, -12.0),
                (vocal_reverb, -1.2),
            ],
            length,
            -1.6,
        ),
    }
    targets = {
        "dual_voice_layer": (
            RENDERS / "0101_mix_male_ref_female_overlap_premaster.wav",
            RENDERS / "0101_FINAL_male_ref_female_overlap.wav",
            RENDERS / "0101_FINAL_male_ref_female_overlap_320.mp3",
            -11.2,
        ),
        "new_dual_voice_alt": (
            RENDERS / "0101_mix_overlap_layer_louder_check_premaster.wav",
            RENDERS / "0101_FINAL_overlap_layer_louder_check.wav",
            RENDERS / "0101_FINAL_overlap_layer_louder_check_320.mp3",
            -11.4,
        ),
        "male_lead_new_voice_support": (
            RENDERS / "0101_mix_male_lead_reference_balance_premaster.wav",
            RENDERS / "0101_FINAL_male_lead_reference_balance.wav",
            RENDERS / "0101_FINAL_male_lead_reference_balance_320.mp3",
            -11.4,
        ),
    }
    rendered: dict[str, Path] = {}
    for name, mix in versions.items():
        mix = edge_fade(mix, sr, 22.0)
        mix = stable_master_tone(mix, sr)
        mix = compressor(mix, sr, threshold_db=-11.8, ratio=1.08, smooth_ms=260, makeup_db=0.0)
        mix = soft_clip(mix, drive_db=0.30, ceiling=0.88)
        mix = limiter(mix, -2.2)
        premaster, final_wav, final_mp3, target_lufs = targets[name]
        write_float_wav(premaster, sr, mix)
        ffmpeg_loudnorm(premaster, final_wav, target_lufs, -1.25, 4.0)
        convert_mp3(final_wav, final_mp3)
        rendered[f"{name}_premaster"] = premaster
        rendered[f"{name}_wav"] = final_wav
        rendered[f"{name}_mp3"] = final_mp3
    return rendered


def write_processed_stems(sr: int, processed: dict[str, np.ndarray]) -> dict[str, Path]:
    outputs = {
        "processed_male_vocal_stem.wav": processed["male_vocal"],
        "processed_new_dual_voice_stem.wav": processed["new_dual_voice"],
        "processed_female_vocal_stem.wav": processed["new_dual_voice"],
        "processed_instrumental_stem.wav": processed["instrumental"],
        "drums_stem.wav": processed["drums"],
        "bass808_stem.wav": processed["bass"],
        "melody_stem.wav": processed["melody"],
    }
    paths: dict[str, Path] = {}
    for name, audio in outputs.items():
        path = RENDERS / name
        write_float_wav(path, sr, limiter(audio, -1.8))
        paths[name] = path
    return paths


def collect_metrics(path_rows: dict[str, Path]) -> list[dict[str, object]]:
    rows = []
    for label, path in path_rows.items():
        if path.exists():
            rows.append(audio_metrics(path, label))
    return rows


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        return
    keys: list[str] = []
    for row in rows:
        for key in row:
            if key not in keys:
                keys.append(key)
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)


def markdown_table(rows: list[dict[str, object]], columns: list[str]) -> str:
    out = ["| " + " | ".join(columns) + " |", "| " + " | ".join(["---"] * len(columns)) + " |"]
    for row in rows:
        out.append("| " + " | ".join(str(row.get(col, "")) for col in columns) + " |")
    return "\n".join(out)


def write_stem_report(sr: int, audio: dict[str, np.ndarray], dtypes: dict[str, str]) -> list[dict[str, object]]:
    roles = {
        "0101_original_reference.wav": "muted_reference",
        "0101_vocal_raw.wav": "original_male_vocal",
        "0101_instrumental_raw.wav": "base_instrumental",
        "0101_drums_raw.wav": "drums",
        "0101_bass808_raw.wav": "bass_808",
        "0101_melody_raw.wav": "melody",
        "0101_keyboard_raw.wav": "keyboard_melody_support",
        "0101_synth_raw.wav": "synth_melody_support",
        "0101_fx_raw.wav": "fx",
        "0101_percussion_raw.wav": "percussion",
        "0101_backing_vocals_raw.wav": "old_backing_reference",
        "0101_new_suno_dual_voice_raw.wav": "new_suno_dual_voice",
        "0101_new_suno_instrumental_reference.wav": "new_suno_instrumental_reference_muted",
    }
    rows = []
    for name, y in sorted(audio.items()):
        role = roles.get(name, "source")
        row = stem_metrics(name, role, y, sr, dtypes[name])
        if role.endswith("reference") or "reference" in role:
            status = "reference only / muted"
        elif "vocal" in role or role in {"drums", "bass_808", "melody", "base_instrumental"}:
            status = "usable with cleanup"
        else:
            status = "support"
        row["status"] = status
        row["phase_note"] = "wide/phase-check" if float(row["stereo_corr"]) < 0.12 else "stable"
        rows.append(row)
    write_csv(REPORTS / "source_stem_metrics.csv", rows)
    summary = [
        {
            "stem": row["file"],
            "role": row["role"],
            "duration_s": row["duration_s"],
            "peak_dbfs": row["peak_dbfs"],
            "rms_dbfs": row["rms_dbfs"],
            "stereo_corr": row["stereo_corr"],
            "status": row["status"],
        }
        for row in rows
    ]
    (REPORTS / "source_stem_report.md").write_text(
        "\n".join(
            [
                "# Source Stem Report",
                "",
                markdown_table(summary, ["stem", "role", "duration_s", "peak_dbfs", "rms_dbfs", "stereo_corr", "status"]),
                "",
                "## Notes",
                "",
                "- 새 Suno zip은 `0 Lead Vocals.wav`와 `1 Instrumental.wav` 두 파일만 포함했다.",
                "- 새 Instrumental은 정렬 검사용으로만 사용했고, 기존 반주를 덮는 새 베드는 활성화하지 않았다.",
                "- 새 Lead Vocals는 두목소리 레이어 소스로 채택했다. 단, 길이가 기존 0101보다 짧아서 끝 13.9초는 기존 보컬/반주 중심으로 유지된다.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return rows


def write_reports(
    sr: int,
    audio: dict[str, np.ndarray],
    dtypes: dict[str, str],
    alignment: dict[str, object],
    placement: dict[str, float],
    decisions: dict[str, object],
    rendered: dict[str, Path],
    processed_paths: dict[str, Path],
) -> None:
    overlap = decisions.get("overlap_layer", {}) if isinstance(decisions, dict) else {}
    stem_rows = write_stem_report(sr, audio, dtypes)
    final_rows = collect_metrics({label: path for label, path in rendered.items() if label.endswith("_wav")})
    mp3_rows = collect_metrics({label: path for label, path in rendered.items() if label.endswith("_mp3")})
    write_csv(REPORTS / "final_render_metrics.csv", final_rows + mp3_rows)
    (REPORTS / "processing_decisions.json").write_text(json.dumps(decisions, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (REPORTS / "alignment_analysis.json").write_text(json.dumps(alignment, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    duration = len(audio["0101_original_reference.wav"]) / sr
    new_duration = len(audio["0101_new_suno_dual_voice_raw.wav"]) / sr
    (REPORTS / "alignment_report.md").write_text(
        "\n".join(
            [
                "# Alignment Report",
                "",
                f"- Base 0101 duration: {duration:.3f}s.",
                f"- New Suno dual-voice duration: {new_duration:.3f}s.",
                f"- Accepted: {alignment['accepted']}.",
                f"- Chosen offset: +{alignment['offset_s']}s on the base 0101 timeline.",
                f"- Placed duration: {placement['placed_duration_s']}s.",
                f"- Vocal alignment score: {alignment['vocal_score']}.",
                f"- Instrumental alignment score: {alignment['instrumental_score']}.",
                "- Decision: 새 보컬은 박자 기준 통과권이라 최종 레이어에 사용했다.",
                "- Limitation: 새 파일이 더 짧기 때문에 마지막 아웃트로 구간은 새 두목소리 레이어 없이 기존 0101 중심으로 유지된다.",
                "",
            ]
        ),
        encoding="utf-8",
    )

    final_summary = [
        {
            "version": row["label"],
            "duration_s": row.get("duration_s"),
            "integrated_lufs": row.get("integrated_lufs"),
            "true_peak_dbfs": row.get("true_peak_dbfs"),
            "peak_dbfs": row.get("peak_dbfs"),
            "rms_dbfs": row.get("rms_dbfs"),
            "stereo_corr": row.get("stereo_corr"),
        }
        for row in final_rows
    ]

    (REPORTS / "reaper_mix_decision_log.md").write_text(
        "\n".join(
            [
                "# REAPER Mix Decision Log",
                "",
                "## Version",
                "",
                f"- Slug: `{SLUG}`.",
                "- Source: 기존 0101 Studio stems + 새 Suno two-voice 2-stem zip.",
                "- Routing: reference/full-mix/new instrumental tracks are muted; active final print is the dual-voice layer mix.",
                "",
                "## Decisions",
                "",
                f"- 새 보컬은 +{alignment['offset_s']}s 오프셋으로 정렬했다.",
                "- 이전 로컬 피치업 여자보컬 레이어는 사용하지 않았다.",
                "- 새 Instrumental은 길이 차이 때문에 반주 베드로 쓰지 않고 정렬 reference로만 사용했다.",
                "- 보컬은 지직/삑 시작음, 스읍성 고역 흡입음, 5.5-12kHz AI fizz를 먼저 줄인 뒤 선명도만 소량 보강했다.",
                "- v08에서는 기존 만족 음량을 크게 바꾸지 않고 남자 보컬 노이즈/레조넌스만 더 정리했다.",
                "- 여자/두목소리 보컬은 더 강하게 denoise했고, 박자/phrase가 남자 보컬과 맞는 local timing window에서만 열리게 만들었다.",
                f"- 여자/두목소리 overlap layer coverage: {overlap.get('coverage_pct', 'n/a')}%, detected regions: {overlap.get('events', 'n/a')}.",
                "- 여자/두목소리 레이어는 center lead가 아니라 wide support/double 역할이며, 더러운/엇박 구간은 mute했다.",
                "- 멜로디는 keyboard/synth/melody stem을 따로 정리해 약간 더 앞으로 올렸다.",
                "- 킥/808은 새 베드 추가 없이 기존 drums/bass stem에 round kick support와 mono sub reinforcement만 얹었다.",
                "- Antares 제품, 랜덤 애드립, vocal chop hook, 새 EDM/K-pop식 베드는 사용하지 않았다.",
                "",
                f"Detailed DSP log: `{REPORTS / 'processing_decisions.json'}`",
                "",
            ]
        ),
        encoding="utf-8",
    )

    (REPORTS / "final_qc_report.md").write_text(
        "\n".join(
            [
                "# Final QC Report",
                "",
                markdown_table(final_summary, ["version", "duration_s", "integrated_lufs", "true_peak_dbfs", "peak_dbfs", "rms_dbfs", "stereo_corr"]),
                "",
                "## QC Notes",
                "",
                "- 메인 추천본은 `0101_FINAL_male_ref_female_overlap.wav`이다.",
                "- 새 두목소리 보컬은 실제 Suno 생성 보컬을 사용했고, 이전 피치변환식 여자 레이어는 제외했다.",
                "- 남자 보컬은 lead/reference 역할을 유지했고, 추가 dynamic EQ와 spectral denoise로 노이즈/레조넌스를 더 정리했다.",
                "- 여자/두목소리 레이어는 남자 보컬과 박자/phrase가 맞는 local timing window에서만 열린다.",
                f"- 여자/두목소리 overlap layer coverage: {overlap.get('coverage_pct', 'n/a')}%, detected regions: {overlap.get('events', 'n/a')}.",
                "- 보컬 음량감은 v07과 크게 달라지지 않게 유지하고, 선명도는 presence restore와 dynamic EQ로 보강했다.",
                "- 멜로디는 별도 overlay로 더 앞으로 뺐다.",
                "- 초반 지직/삑과 중간 스읍성 고역 transient는 vocal/source 단계에서 억제했다.",
                "- 새 보컬 길이가 짧아 마지막 아웃트로 일부에는 새 두목소리 레이어가 없다.",
                "- 최종 판단은 감정선 보존 우선이다. 기술적으로 가장 깨끗한 무보컬/저보컬 버전보다 새 보컬 감정이 살아있는 레이어 버전을 메인으로 선택했다.",
                "",
                "## Deliverables",
                "",
            ]
            + [f"- `{path}`" for path in sorted(rendered.values(), key=lambda p: p.name)]
            + [f"- `{path}`" for path in sorted(processed_paths.values(), key=lambda p: p.name)]
            + [f"- `{RPP}`", ""]
        ),
        encoding="utf-8",
    )

    (REPORTS / "suno_0101_initial_analysis.md").write_text(
        "\n".join(
            [
                "# Suno 0101 Initial Analysis",
                "",
                f"- BPM: {BPM}.",
                "- Key: not asserted from this pass; no trusted key metadata was present in the provided stems.",
                f"- Base duration: {duration:.3f}s.",
                f"- New dual voice duration: {new_duration:.3f}s.",
                "- Arrangement estimate: intro 0:00-0:14, verse 0:14-0:43, hook/lift 0:43-1:12, second vocal/lift 1:12-1:41, outro/final lift after 1:41.",
                "- Strengths: sad melody and vocal contour are still the emotional center; new Suno vocal gives a real dual-voice layer.",
                "- Weaknesses addressed: previous vocal-forward balance, weak audible female/two-voice layer, melody being too small, uneven vocal level, breath/sip transient, and early click/beep risk.",
                "",
            ]
        ),
        encoding="utf-8",
    )


def rpp_item(file_path: Path, length: float, iid: int, position: float = 0.0, muted: bool = False) -> str:
    return f"""    <ITEM
      POSITION {position:.12f}
      SNAPOFFS 0
      LENGTH {length:.12f}
      LOOP 1
      ALLTAKES 0
      FADEIN 1 0.018 0 1 0 0 0
      FADEOUT 1 0.018 0 1 0 0 0
      MUTE {1 if muted else 0} 0
      SEL 0
      IGUID {{{uuid.uuid4()}}}
      IID {iid}
      NAME {file_path.name}
      VOLPAN 1 0 1 -1
      SOFFS 0
      PLAYRATE 1 1 0 -1 0 0.0025
      CHANMODE 0
      GUID {{{uuid.uuid4()}}}
      <SOURCE WAVE
        FILE "{file_path}"
      >
    >"""


def rpp_track(
    name: str,
    file_path: Path | None,
    length: float,
    iid: int,
    position: float = 0.0,
    muted: bool = False,
    mainsend: bool = True,
) -> str:
    item = rpp_item(file_path, length, iid, position=position, muted=muted) if file_path else ""
    vol = "0.70794578438414" if muted else "1"
    return f"""  <TRACK {{{uuid.uuid4()}}}
    NAME "{name}"
    PEAKCOL 16576
    BEAT -1
    AUTOMODE 0
    PANLAWFLAGS 3
    VOLPAN {vol} 0 -1 -1 1
    MUTESOLO {1 if muted else 0} 0 0
    IPHASE 0
    PLAYOFFS 0 1
    ISBUS 0 0
    BUSCOMP 0 0 0 0 0
    SHOWINMIX 1 0.6667 0.5 1 0.5 0 0 0 0
    SEL 0
    REC 0 0 1 0 0 0 0 0
    VU 64
    TRACKHEIGHT 0 0 0 0 0 0 0
    INQ 0 0 0 0.5 100 0 0 100
    NCHAN 2
    FX 1
    TRACKID {{{uuid.uuid4()}}}
    PERF 0
    MIDIOUT -1
    MAINSEND {1 if mainsend else 0} 0
{item}
  >"""


def write_reaper_project(sr: int, audio: dict[str, np.ndarray], alignment: dict[str, object], rendered: dict[str, Path], processed_paths: dict[str, Path]) -> None:
    length = len(audio["0101_original_reference.wav"]) / sr
    new_length = len(audio["0101_new_suno_dual_voice_raw.wav"]) / sr
    offset = float(alignment["offset_s"])
    track_defs = [
        ("ORIGINAL_REFERENCE muted", STEMS / "0101_original_reference.wav", length, 0.0, True, False),
        ("BASE_INSTRUMENTAL_RAW muted", STEMS / "0101_instrumental_raw.wav", length, 0.0, True, False),
        ("NEW_SUNO_INSTRUMENTAL_REFERENCE muted", STEMS / "0101_new_suno_instrumental_reference.wav", new_length, offset, True, False),
        ("MALE_VOCAL_RAW muted", STEMS / "0101_vocal_raw.wav", length, 0.0, True, False),
        ("NEW_DUAL_VOICE_RAW aligned muted", STEMS / "0101_new_suno_dual_voice_raw.wav", new_length, offset, True, False),
        ("MALE_VOCAL_PROCESSED muted", processed_paths["processed_male_vocal_stem.wav"], length, 0.0, True, False),
        ("NEW_DUAL_VOICE_PROCESSED muted", processed_paths["processed_new_dual_voice_stem.wav"], length, 0.0, True, False),
        ("DRUM_BUS print muted", processed_paths["drums_stem.wav"], length, 0.0, True, False),
        ("BASS_BUS print muted", processed_paths["bass808_stem.wav"], length, 0.0, True, False),
        ("MELODY_BUS print muted", processed_paths["melody_stem.wav"], length, 0.0, True, False),
        ("MIX_BUS main dual voice ACTIVE", rendered["dual_voice_layer_wav"], length, 0.0, False, True),
        ("ALT new dual voice muted", rendered["new_dual_voice_alt_wav"], length, 0.0, True, False),
        ("ALT male lead support muted", rendered["male_lead_new_voice_support_wav"], length, 0.0, True, False),
    ]
    tracks = [
        rpp_track(name, path, item_length, pos, position, muted=muted, mainsend=mainsend)
        for pos, (name, path, item_length, position, muted, mainsend) in enumerate(track_defs, start=1)
    ]
    marker_times = [0, 14.2, 42.7, 72.0, 101.3, length]
    marker_names = ["intro", "verse", "hook lift", "second section", "final lift/outro", "render end"]
    markers = [
        f'  MARKER {i} {time:.6f} "{name}" 0 0 1 B {{{uuid.uuid4()}}} 0 2'
        for i, (time, name) in enumerate(zip(marker_times, marker_names), start=1)
    ]
    project = f"""<REAPER_PROJECT 0.1 "7.73/macOS-arm64" 1779750000 0
  <NOTES 0 2
    |0101 dual voice mix. New Suno vocal aligned at +{offset:.3f}s. Reference tracks muted; active playback is MIX_BUS main dual voice.
  >
  RIPPLE 0 0
  AUTOXFADE 129
  PEAKGAIN 1
  PANLAW 1
  PROJOFFS 0 0 0
  GRID 3199 8 1 8 1 0 0 0
  TIMEMODE 1 5 -1 30 0 0 -1 0
  ITEMMIX 1
  SAMPLERATE 48000 1 0
  RENDER_FILE "{RENDERS / '0101_REAPER_project_sum.wav'}"
  RENDER_FMT 0 2 48000
  RENDER_RANGE 0 0 {length:.12f} 0 1000
  TEMPO {BPM}.000000 4 4 0
  PLAYRATE 1 0 0.25 4
  MASTER_NCH 2 2
  MASTER_VOLUME 1 0 -1 -1 1
{chr(10).join(markers)}
{chr(10).join(tracks)}
>
"""
    RPP.write_text(project, encoding="utf-8")


def create_delivery_zip(rendered: dict[str, Path], processed_paths: dict[str, Path]) -> Path:
    zip_path = RENDERS / f"{SLUG}_DELIVERABLES.zip"
    include = [
        *rendered.values(),
        *processed_paths.values(),
        RPP,
        REPORTS / "alignment_report.md",
        REPORTS / "source_stem_report.md",
        REPORTS / "reaper_mix_decision_log.md",
        REPORTS / "final_qc_report.md",
        REPORTS / "suno_0101_initial_analysis.md",
        REPORTS / "final_render_metrics.csv",
    ]
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        seen: set[Path] = set()
        for path in include:
            if path.exists() and path not in seen:
                zf.write(path, arcname=path.name)
                seen.add(path)
    return zip_path


def convert_for_metrics(path: Path) -> Path:
    return path


def main() -> None:
    ensure_dirs()
    extract_new_zip_if_needed()
    copied = copy_sources()

    audio: dict[str, np.ndarray] = {}
    dtypes: dict[str, str] = {}
    sample_rates = set()
    for name, path in copied.items():
        sr, y, dtype_name = read_wav(path)
        sample_rates.add(sr)
        audio[name] = y
        dtypes[name] = dtype_name
    if sample_rates != {48000}:
        raise RuntimeError(f"Expected 48 kHz sources, got {sorted(sample_rates)}")
    sr = 48000
    length = len(audio["0101_original_reference.wav"])
    for name in list(audio):
        if name not in {"0101_new_suno_dual_voice_raw.wav", "0101_new_suno_instrumental_reference.wav"}:
            audio[name] = pad_or_trim(audio[name], length)

    alignment = detect_alignment(audio, sr)
    if not alignment["accepted"]:
        raise RuntimeError(f"New Suno dual voice did not pass alignment: {alignment}")

    new_vocal_clean, new_moves = process_voice(
        audio["0101_new_suno_dual_voice_raw.wav"],
        sr,
        label="new_suno_dual_voice",
        target_rms_db=-22.3,
        hpf=118,
    )
    new_vocal_aligned, placement = place_at(new_vocal_clean, length, sr, float(alignment["offset_s"]))
    new_vocal_aligned = edge_fade(new_vocal_aligned, sr, 18.0)

    male_proc, male_moves = process_voice(
        audio["0101_vocal_raw.wav"],
        sr,
        label="original_male_vocal",
        target_rms_db=-21.6,
        hpf=96,
    )
    male_proc = edge_fade(male_proc, sr, 18.0)
    new_vocal_overlap, overlap_stats = make_male_matched_female_layer(new_vocal_aligned, male_proc, sr)
    write_float_wav(PROCESSED / "0101_new_suno_dual_voice_aligned_clean.wav", sr, new_vocal_aligned)
    write_float_wav(PROCESSED / "0101_new_suno_dual_voice_male_matched_overlap.wav", sr, new_vocal_overlap)

    vocal_trigger = limiter(male_proc * float(amp_db(-2.0)) + new_vocal_overlap * float(amp_db(-5.0)), -2.5)
    inst_processed, inst_moves = process_instrumental(audio, sr, vocal_trigger)
    processed = {
        **inst_processed,
        "male_vocal": male_proc,
        "new_dual_voice": new_vocal_overlap,
    }
    processed_paths = write_processed_stems(sr, processed)
    rendered = render_mix_versions(sr, processed)

    decisions = {
        "alignment": alignment,
        "placement": placement,
        "overlap_layer": overlap_stats,
        "new_suno_dual_voice": new_moves,
        "original_male_vocal": male_moves,
        "instrumental": inst_moves,
        "mix_versions": {
            "main": "0101_FINAL_male_ref_female_overlap.wav",
            "alt_overlap_layer_louder_check": "0101_FINAL_overlap_layer_louder_check.wav",
            "alt_male_lead_reference_balance": "0101_FINAL_male_lead_reference_balance.wav",
        },
    }
    write_reaper_project(sr, audio, alignment, rendered, processed_paths)
    write_reports(sr, audio, dtypes, alignment, placement, decisions, rendered, processed_paths)
    delivery_zip = create_delivery_zip(rendered, processed_paths)

    print(
        json.dumps(
            {
                "slug": SLUG,
                "alignment": alignment,
                "placement": placement,
                "renders": str(RENDERS),
                "reports": str(REPORTS),
                "reaper_project": str(RPP),
                "delivery_zip": str(delivery_zip),
                "main_final": str(rendered["dual_voice_layer_wav"]),
                "main_mp3": str(rendered["dual_voice_layer_mp3"]),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()

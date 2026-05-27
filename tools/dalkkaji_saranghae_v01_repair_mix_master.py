from __future__ import annotations

import csv
import json
import math
import os
import shutil
import sys
import uuid
from pathlib import Path

import numpy as np
from scipy import signal

ROOT = Path(os.environ.get("DALKK_ROOT", "/Users/hantaeheuk/Documents/New project 3"))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.mgmg_v03_human_vocal_dynamic_fx import (  # noqa: E402
    amp_db,
    audio_metrics,
    bandpass,
    biquad_peaking,
    biquad_shelf,
    butter_filter,
    compressor,
    convert_mp3,
    convert_wav_24,
    db_amp,
    delay_samples,
    dynamic_band_tame,
    ffmpeg_loudnorm,
    limiter,
    normalize_to_rms,
    pan_stereo,
    peak,
    read_wav,
    reverb_send,
    rms,
    saturate,
    sidechain_duck_full,
    soft_clip,
    spectral_balance,
    stem_metrics,
    write_float_wav,
)


SLUG = os.environ.get("DALKK_SLUG", "dalkkaji_saranghae_v01_repair_mix_master")
SOURCE_DIR = Path(os.environ.get("DALKK_SOURCE_DIR", "/Users/hantaeheuk/Downloads/달까지 사랑해"))
BPM = 120
SR_EXPECTED = 48000

WORK = ROOT / "audio_work" / SLUG
SRC_COPY = WORK / "source"
PROCESSED = WORK / "processed_stems"
ANALYSIS = WORK / "analysis"
RENDERS = ROOT / "renders" / SLUG
REPORTS = ROOT / "reports" / SLUG
REAPER_DIR = ROOT / "reaper" / SLUG
RPP = REAPER_DIR / "FEMALE_TAKE_REPAIR_AND_DOUBLE_COMP_V01.rpp"

SOURCE_MAP = {
    "full_mix": "0 달까지 사랑해.wav",
    "woodwinds": "1 Woodwinds.wav",
    "brass": "2 Brass.wav",
    "fx": "3 FX.wav",
    "synth": "4 Synth.wav",
    "strings": "5 Strings.wav",
    "percussion": "6 Percussion.wav",
    "keyboard": "7 Keyboard.wav",
    "guitar": "8 Guitar.wav",
    "bass": "9 Bass.wav",
    "drums": "10 Drums.wav",
    "backing_vocals": "11 Backing_Vocals.wav",
    "main_male_vocal": "12 Vocals.wav",
    "female_take_01": "13 여자목소리1.wav",
    "female_take_02": "14 달까지 사랑해 (Vocals) (Add Instrumental).wav",
    "female_take_03": "15 달까지 사랑해 (Vocals) (Add Instrumental).wav",
    "female_take_04": "16 달까지 사랑해 (Vocals) (Add Instrumental).wav",
}

FEMALE_KEYS = [
    "backing_vocals",
    "female_take_01",
    "female_take_02",
    "female_take_03",
    "female_take_04",
]


def ensure_dirs() -> None:
    for directory in (WORK, SRC_COPY, PROCESSED, ANALYSIS, RENDERS, REPORTS, REAPER_DIR):
        directory.mkdir(parents=True, exist_ok=True)


def copy_sources() -> dict[str, Path]:
    copied: dict[str, Path] = {}
    for key, name in SOURCE_MAP.items():
        src = SOURCE_DIR / name
        if not src.exists():
            raise FileNotFoundError(src)
        dst = SRC_COPY / name
        shutil.copy2(src, dst)
        copied[key] = dst
    return copied


def edge_fade(y: np.ndarray, sr: int, ms: float = 12.0) -> np.ndarray:
    out = y.copy().astype(np.float32)
    n = min(int(sr * ms / 1000.0), len(out) // 2)
    if n > 2:
        fade = np.linspace(0.0, 1.0, n, dtype=np.float32)
        out[:n] *= fade[:, None]
        out[-n:] *= fade[::-1, None]
    return out


def pad_or_trim(y: np.ndarray, length: int) -> np.ndarray:
    if len(y) == length:
        return y.astype(np.float32)
    if len(y) > length:
        return y[:length].astype(np.float32)
    out = np.zeros((length, 2), dtype=np.float32)
    out[: len(y)] = y.astype(np.float32)
    return out


def scale_peak(y: np.ndarray, peak_db: float) -> np.ndarray:
    p = peak(y)
    if p < 1e-10:
        return y.astype(np.float32)
    return (y * float(amp_db(peak_db - float(db_amp(p))))).astype(np.float32)


def blend_soft_clip(y: np.ndarray, drive_db: float, ceiling: float, mix: float, target_peak_db: float) -> np.ndarray:
    driven = y * float(amp_db(drive_db))
    clipped = soft_clip(driven, drive_db=0.0, ceiling=ceiling)
    out = y * (1.0 - mix) + clipped * mix
    return scale_peak(out.astype(np.float32), target_peak_db)


def ms_eq_separate(y: np.ndarray, sr: int, mid_gain_db: float = -4.0, side_gain_db: float = 2.2) -> np.ndarray:
    """Tuck female support out of the center while keeping a usable mono trace."""
    mid = ((y[:, 0] + y[:, 1]) * 0.5)[:, None]
    side = ((y[:, 0] - y[:, 1]) * 0.5)[:, None]
    mid_st = np.repeat(mid, 2, axis=1)
    side_st = np.column_stack([side[:, 0], -side[:, 0]]).astype(np.float32)
    mid_st = biquad_peaking(mid_st, sr, 2600, -0.7, 0.9)
    mid_st = biquad_shelf(mid_st, sr, 9000, -0.9, True)
    side_st = butter_filter(side_st, sr, "highpass", 240, 2)
    side_st = biquad_peaking(side_st, sr, 3200, 0.65, 0.9)
    side_st = biquad_shelf(side_st, sr, 10800, -0.55, True)
    out = mid_st * float(amp_db(mid_gain_db)) + side_st * float(amp_db(side_gain_db))
    return out.astype(np.float32)


def stereo_pan_delay_layer(y: np.ndarray, sr: int, left_ms: float = 12.0, right_ms: float = 24.0) -> np.ndarray:
    left = pan_stereo(delay_samples(y, int(sr * left_ms / 1000.0)), -0.42)
    right = pan_stereo(delay_samples(y, int(sr * right_ms / 1000.0)), 0.42)
    center = y * float(amp_db(-8.0))
    return (left * float(amp_db(-3.0)) + right * float(amp_db(-3.0)) + center).astype(np.float32)


def safe_rms_norm(y: np.ndarray, target_db: float) -> np.ndarray:
    if rms(y) < 1e-10:
        return y.astype(np.float32)
    return normalize_to_rms(y, target_db).astype(np.float32)


def safe_sum(parts: list[tuple[np.ndarray, float]], length: int, ceiling_db: float = -2.5) -> np.ndarray:
    out = np.zeros((length, 2), dtype=np.float32)
    for y, gain_db in parts:
        out += pad_or_trim(y, length) * float(amp_db(gain_db))
    p = peak(out)
    ceiling = float(amp_db(ceiling_db))
    if p > ceiling and p > 1e-9:
        out *= ceiling / p
    return out.astype(np.float32)


def write_24(path: Path, sr: int, y: np.ndarray) -> None:
    tmp = path.with_suffix(".float.tmp.wav")
    write_float_wav(tmp, sr, np.nan_to_num(y.astype(np.float32)))
    convert_wav_24(tmp, path)
    tmp.unlink(missing_ok=True)


def frame_env(y: np.ndarray, sr: int, low: float = 160.0, high: float = 5200.0, rate: int = 100) -> np.ndarray:
    mono = np.mean(bandpass(y, sr, low, high, 3), axis=1).astype(np.float32)
    win = max(int(sr / rate), 1)
    frames = len(mono) // win
    if frames <= 0:
        return np.zeros(0, dtype=np.float32)
    env = np.sqrt(np.mean(mono[: frames * win].reshape(frames, win) ** 2, axis=1) + 1e-12)
    env = np.log1p(env * 80.0)
    return ((env - np.mean(env)) / (np.std(env) + 1e-8)).astype(np.float32)


def downsample_energy(y: np.ndarray, sr: int, rate: int = 50) -> np.ndarray:
    mono = np.abs(np.mean(y, axis=1)).astype(np.float32)
    win = max(int(sr / rate), 1)
    frames = len(mono) // win
    if frames <= 0:
        return np.zeros(0, dtype=np.float32)
    out = np.mean(mono[: frames * win].reshape(frames, win), axis=1).astype(np.float32)
    active = out[out > 1e-10]
    if len(active):
        out = out / (float(np.percentile(active, 95)) + 1e-10)
    return np.clip(out, 0.0, 3.0).astype(np.float32)


def best_offset(ref: np.ndarray, cand: np.ndarray, rate: int = 100, max_shift_s: float = 4.0) -> dict[str, float] | None:
    if len(ref) == 0 or len(cand) == 0:
        return None
    max_shift = int(max_shift_s * rate)
    corr = signal.correlate(ref, cand, mode="full", method="fft")
    lags = np.arange(-len(cand) + 1, len(ref))
    mask = (lags >= -max_shift) & (lags <= max_shift)
    if not np.any(mask):
        return None
    idx = int(np.argmax(corr[mask]))
    lag = int(lags[mask][idx])
    if lag >= 0:
        a = ref[lag : min(len(ref), lag + len(cand))]
        b = cand[: len(a)]
    else:
        b = cand[-lag : min(len(cand), len(ref) - lag)]
        a = ref[: len(b)]
    if len(a) < rate * 3:
        return None
    score = float(np.dot(a, b) / ((np.linalg.norm(a) * np.linalg.norm(b)) + 1e-9))
    return {"score": round(score, 4), "offset_s": round(lag / rate, 4), "overlap_s": round(len(a) / rate, 3)}


def place_at(source: np.ndarray, length: int, sr: int, offset_s: float) -> np.ndarray:
    out = np.zeros((length, 2), dtype=np.float32)
    offset = int(round(offset_s * sr))
    src_start = max(-offset, 0)
    dst_start = max(offset, 0)
    usable = min(len(source) - src_start, length - dst_start)
    if usable > 0:
        out[dst_start : dst_start + usable] = edge_fade(source[src_start : src_start + usable], sr, 10.0)
    return out


def f0_track(y: np.ndarray, sr: int, rate: int = 50) -> tuple[np.ndarray, np.ndarray]:
    mono = np.mean(bandpass(y, sr, 75, 900, 2), axis=1).astype(np.float32)
    hop = max(int(sr / rate), 1)
    frame = max(int(sr * 0.046), hop * 2)
    min_lag = max(int(sr / 760), 1)
    max_lag = min(int(sr / 70), frame - 2)
    n = max((len(mono) - frame) // hop + 1, 0)
    logs = np.full(n, np.nan, dtype=np.float32)
    conf = np.zeros(n, dtype=np.float32)
    if n <= 0 or max_lag <= min_lag:
        return logs, conf
    for i in range(n):
        seg = mono[i * hop : i * hop + frame]
        seg = seg - float(np.mean(seg))
        energy = float(np.dot(seg, seg))
        if energy < 1e-6:
            continue
        corr = np.correlate(seg, seg, mode="full")[frame - 1 :]
        window = corr[min_lag:max_lag]
        if len(window) == 0:
            continue
        lag = int(np.argmax(window) + min_lag)
        c = float(corr[lag] / (corr[0] + 1e-9))
        if c < 0.22:
            continue
        logs[i] = math.log2(sr / lag)
        conf[i] = min(1.0, max(0.0, c))
    return logs, conf


def chroma_match_score(
    male_log: np.ndarray,
    female_log: np.ndarray,
    male_conf: np.ndarray,
    female_conf: np.ndarray,
) -> float | None:
    n = min(len(male_log), len(female_log), len(male_conf), len(female_conf))
    if n <= 0:
        return None
    valid = (
        np.isfinite(male_log[:n])
        & np.isfinite(female_log[:n])
        & (male_conf[:n] > 0.26)
        & (female_conf[:n] > 0.24)
    )
    if int(np.sum(valid)) < 6:
        return None
    diff = np.abs(((female_log[:n][valid] - male_log[:n][valid] + 0.5) % 1.0) - 0.5)
    return round(float(np.mean(diff < 0.18)), 4)


def local_qc_mask(male: np.ndarray, female: np.ndarray, sr: int, rate: int = 50) -> tuple[np.ndarray, dict[str, object]]:
    male_env = downsample_energy(bandpass(male, sr, 180, 5200, 3), sr, rate)
    female_env = downsample_energy(bandpass(female, sr, 180, 6200, 3), sr, rate)
    n = min(len(male_env), len(female_env))
    male_env = male_env[:n]
    female_env = female_env[:n]
    male_log, male_conf = f0_track(male, sr, rate)
    female_log, female_conf = f0_track(female, sr, rate)
    pitch_global = chroma_match_score(male_log, female_log, male_conf, female_conf)
    mask_points = np.zeros(n, dtype=np.float32)
    score_values: list[float] = []
    pitch_values: list[float] = []
    lag_values: list[float] = []
    accepted = 0
    frame = max(int(0.62 * rate), 8)
    hop = max(int(0.04 * rate), 1)
    max_lag = max(int(0.10 * rate), 1)
    male_thr = max(float(np.percentile(male_env[male_env > 1e-8], 36)) if np.any(male_env > 1e-8) else 0.04, 0.04)
    female_thr = max(float(np.percentile(female_env[female_env > 1e-8], 40)) if np.any(female_env > 1e-8) else 0.035, 0.035)

    for start in range(0, max(n - frame, 1), hop):
        end = min(start + frame, n)
        if end - start < frame // 2:
            continue
        m = male_env[start:end]
        if float(np.max(m)) < male_thr:
            continue
        best_score = -1.0
        best_lag = 999
        best_pitch: float | None = None
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
            score = float(np.dot(mm, ff) / (float(np.linalg.norm(mm) * np.linalg.norm(ff)) + 1e-9))
            if score > best_score:
                best_score = score
                best_lag = lag
                ml = male_log[start:end] if end <= len(male_log) else np.array([], dtype=np.float32)
                fl = female_log[fs:fe] if fe <= len(female_log) else np.array([], dtype=np.float32)
                mc = male_conf[start:end] if end <= len(male_conf) else np.array([], dtype=np.float32)
                fc = female_conf[fs:fe] if fe <= len(female_conf) else np.array([], dtype=np.float32)
                best_pitch = chroma_match_score(ml, fl, mc, fc)
        if best_score < -0.5:
            continue
        pitch_ok = True if best_pitch is None else best_pitch >= 0.34
        score_values.append(best_score)
        lag_values.append(best_lag / rate)
        if best_pitch is not None:
            pitch_values.append(best_pitch)
        if best_score >= 0.27 and abs(best_lag / rate) <= 0.060 and pitch_ok:
            strength = min(1.0, 0.25 + best_score * 1.1 + ((best_pitch or 0.45) - 0.34) * 0.30)
            mask_points[start:end] = np.maximum(mask_points[start:end], strength)
            accepted += 1

    if not np.any(mask_points > 0):
        return np.zeros(len(male), dtype=np.float32), {
            "coverage_pct": 0.0,
            "events": 0,
            "accepted_windows": 0,
            "score_median": round(float(np.median(score_values)), 4) if score_values else None,
            "pitch_global_match": pitch_global,
            "pitch_window_median": round(float(np.median(pitch_values)), 4) if pitch_values else None,
            "abs_lag_median_s": round(float(np.median(np.abs(lag_values))), 4) if lag_values else None,
        }

    close = max(int(0.035 * rate), 1)
    mask_points = np.convolve(mask_points, np.ones(close, dtype=np.float32), mode="same")
    mask_points = np.clip(mask_points, 0.0, 1.0)
    sample_positions = np.arange(n) * (sr / rate)
    mask_full = np.interp(np.arange(len(male)), sample_positions, mask_points, left=0.0, right=0.0).astype(np.float32)
    fade = max(int(sr * 0.075), 3)
    kernel = np.hanning(fade).astype(np.float32)
    kernel /= max(float(np.sum(kernel)), 1e-9)
    mask_full = np.clip(signal.fftconvolve(mask_full, kernel, mode="same"), 0.0, 1.0).astype(np.float32)
    events = int(np.sum(np.diff((mask_full > 0.08).astype(np.int8), prepend=0) == 1))
    return mask_full, {
        "coverage_pct": round(float(np.mean(mask_full > 0.08) * 100.0), 2),
        "events": events,
        "accepted_windows": accepted,
        "score_median": round(float(np.median(score_values)), 4) if score_values else None,
        "score_p75": round(float(np.percentile(score_values, 75)), 4) if score_values else None,
        "abs_lag_median_s": round(float(np.median(np.abs(lag_values))), 4) if lag_values else None,
        "pitch_global_match": pitch_global,
        "pitch_window_median": round(float(np.median(pitch_values)), 4) if pitch_values else None,
    }


def mask_segments(mask: np.ndarray, sr: int, threshold: float = 0.08, min_dur: float = 0.12) -> list[dict[str, float]]:
    active = mask > threshold
    changes = np.diff(active.astype(np.int8), prepend=0, append=0)
    starts = np.where(changes == 1)[0]
    ends = np.where(changes == -1)[0]
    out = []
    for s, e in zip(starts, ends):
        dur = (e - s) / sr
        if dur >= min_dur:
            out.append({"start_s": round(s / sr, 3), "end_s": round(e / sr, 3), "duration_s": round(dur, 3)})
    return out


def endpoint_mask_from_audio(y: np.ndarray, sr: int, max_total_pct: float = 4.5) -> np.ndarray:
    env = downsample_energy(bandpass(y, sr, 220, 6500, 2), sr, 50)
    if len(env) == 0:
        return np.zeros(len(y), dtype=np.float32)
    active = env > max(float(np.percentile(env[env > 1e-8], 62)) if np.any(env > 1e-8) else 0.05, 0.05)
    changes = np.diff(active.astype(np.int8), prepend=0, append=0)
    starts = np.where(changes == 1)[0]
    ends = np.where(changes == -1)[0]
    out = np.zeros(len(y), dtype=np.float32)
    max_total = int(len(y) * max_total_pct / 100.0)
    total = 0
    keep_frames = int(0.34 * 50)
    min_gap_frames = int(0.82 * 50)
    last_end = -10**9
    for start, end in zip(starts, ends):
        if end - start < int(0.28 * 50):
            continue
        if end - last_end < min_gap_frames:
            continue
        use_start = max(start, end - keep_frames)
        sample_start = int(use_start * sr / 50)
        sample_end = int(end * sr / 50)
        if sample_end <= sample_start:
            continue
        if total + (sample_end - sample_start) > max_total:
            sample_start = sample_end - max(0, max_total - total)
        if sample_end - sample_start < int(0.12 * sr):
            continue
        n = sample_end - sample_start
        fade = min(int(0.05 * sr), n // 2)
        piece = np.ones(n, dtype=np.float32)
        if fade > 2:
            piece[:fade] = np.linspace(0.0, 1.0, fade, dtype=np.float32)
            piece[-fade:] = np.linspace(1.0, 0.0, fade, dtype=np.float32)
        out[sample_start:sample_end] = np.maximum(out[sample_start:sample_end], piece)
        total += n
        last_end = end
        if total >= max_total:
            break
    return out.astype(np.float32)


def make_endpoint_reverb_throw(layer: np.ndarray, main_clean: np.ndarray, sr: int) -> np.ndarray:
    mask = endpoint_mask_from_audio(layer, sr, max_total_pct=4.8)
    if not np.any(mask > 0.01):
        return np.zeros_like(layer, dtype=np.float32)
    source = butter_filter(layer * mask[:, None], sr, "highpass", 360, 2)
    verb_a = reverb_send(source, sr, decay_s=1.18, wet_db=-16.5, predelay_ms=48, hp_hz=520, lp_hz=6200, seed=912)
    verb_b = reverb_send(source, sr, decay_s=0.48, wet_db=-19.0, predelay_ms=18, hp_hz=620, lp_hz=7600, seed=913)
    slap = (
        pan_stereo(delay_samples(source, int(sr * 0.145)), -0.50)
        + pan_stereo(delay_samples(source, int(sr * 0.215)), 0.50)
    ) * float(amp_db(-22.0))
    throw = verb_a + verb_b + slap
    throw = sidechain_duck_full(throw, main_clean, sr, amount_db=4.2, release_ms=220, threshold_percentile=58)
    throw = biquad_shelf(throw, sr, 9000, -1.2, True)
    return scale_peak(throw, -12.0).astype(np.float32)


def short_support_mask(
    mask: np.ndarray,
    sr: int,
    max_piece_s: float,
    min_gap_s: float,
    max_total_pct: float,
) -> np.ndarray:
    """Keep only short phrase-end pieces from a broad timing/pitch mask."""
    out = np.zeros_like(mask, dtype=np.float32)
    active = mask > 0.10
    changes = np.diff(active.astype(np.int8), prepend=0, append=0)
    starts = np.where(changes == 1)[0]
    ends = np.where(changes == -1)[0]
    last_end = -10**9
    max_total = int(len(mask) * max_total_pct / 100.0)
    total = 0
    max_piece = int(max_piece_s * sr)
    min_gap = int(min_gap_s * sr)
    fade = max(int(0.045 * sr), 8)
    for start, end in zip(starts, ends):
        dur = end - start
        if dur < int(0.16 * sr):
            continue
        keep = min(dur, max_piece)
        use_end = end
        use_start = max(start, use_end - keep)
        if use_start - last_end < min_gap:
            continue
        if total + (use_end - use_start) > max_total:
            remaining = max_total - total
            if remaining < int(0.18 * sr):
                break
            use_start = use_end - remaining
        piece = mask[use_start:use_end].copy()
        n = len(piece)
        if n > fade * 2:
            ramp = np.ones(n, dtype=np.float32)
            ramp[:fade] = np.linspace(0.0, 1.0, fade, dtype=np.float32)
            ramp[-fade:] = np.linspace(1.0, 0.0, fade, dtype=np.float32)
            piece *= ramp
        out[use_start:use_end] = np.maximum(out[use_start:use_end], piece)
        total += use_end - use_start
        last_end = use_end
        if total >= max_total:
            break
    return np.clip(out, 0.0, 1.0).astype(np.float32)


def rough_source_metrics(y: np.ndarray, sr: int) -> dict[str, float]:
    mono = np.mean(y, axis=1)
    n = 2048
    hop = sr // 2
    freqs = np.fft.rfftfreq(n, 1 / sr)
    lows: list[float] = []
    highs: list[float] = []
    cents: list[float] = []
    for start in range(0, len(mono) - n, hop):
        frame = mono[start : start + n] * np.hanning(n)
        mag = np.abs(np.fft.rfft(frame)) + 1e-12
        power = mag * mag
        total = float(np.sum(power))
        lows.append(float(np.sum(power[(freqs >= 20) & (freqs < 180)]) / total))
        highs.append(float(np.sum(power[freqs >= 8000]) / total))
        cents.append(float(np.sum(freqs * power) / total))
    return {
        "peak_dbfs": round(float(db_amp(peak(y))), 2),
        "rms_dbfs": round(float(db_amp(rms(y))), 2),
        "low_ratio": round(float(np.median(lows)), 4) if lows else 0.0,
        "high_ratio": round(float(np.median(highs)), 4) if highs else 0.0,
        "centroid_hz": round(float(np.median(cents)), 1) if cents else 0.0,
    }


def clean_main_vocal(y: np.ndarray, sr: int) -> tuple[np.ndarray, list[dict[str, object]]]:
    moves: list[dict[str, object]] = []
    out = edge_fade(y, sr, 18.0)
    out = butter_filter(out, sr, "highpass", 92, 3)
    moves.append({"stage": "ReaEQ-style HPF", "freq_hz": 92})
    for low, high, cut, pct, smooth, name in [
        (170, 360, 1.9, 72, 130, "mud/body control"),
        (650, 1250, 1.4, 72, 120, "box/nasal control"),
        (2450, 5100, 2.2, 66, 80, "AI/presence control"),
        (5500, 8500, 3.4, 62, 55, "de-ess"),
        (8500, 13200, 2.2, 66, 50, "top fizz control"),
    ]:
        out, stats = dynamic_band_tame(out, sr, low, high, cut, pct, smooth)
        moves.append({"stage": name, **stats})
    out = biquad_peaking(out, sr, 2700, 0.35, 0.8)
    out = biquad_shelf(out, sr, 10500, -0.5, True)
    out = compressor(out, sr, threshold_db=-25.5, ratio=1.8, smooth_ms=95, makeup_db=0.0)
    out = saturate(out, drive_db=0.45, mix=0.035)
    out = safe_rms_norm(out, -21.8)
    out = scale_peak(out, -5.0)
    return out.astype(np.float32), moves


def clean_female_take(y: np.ndarray, sr: int, bleed: bool) -> tuple[np.ndarray, list[dict[str, object]]]:
    moves: list[dict[str, object]] = []
    hpf = 220 if bleed else 170
    out = edge_fade(y, sr, 12.0)
    out = butter_filter(out, sr, "highpass", hpf, 3)
    moves.append({"stage": "ReaEQ-style HPF", "freq_hz": hpf})
    for low, high, cut, pct, smooth, name in [
        (240, 700, 2.5 if bleed else 1.7, 70, 120, "instrument bleed low-mid control"),
        (720, 1350, 1.5, 70, 110, "box/nasal control"),
        (2500, 5000, 2.0, 66, 80, "presence/AI edge control"),
        (5500, 8600, 3.6, 62, 55, "de-ess"),
        (8600, 13500, 2.8, 66, 48, "metallic fizz control"),
    ]:
        out, stats = dynamic_band_tame(out, sr, low, high, cut, pct, smooth)
        moves.append({"stage": name, **stats})
    out = biquad_peaking(out, sr, 360, -0.8 if bleed else -0.35, 0.9)
    out = biquad_shelf(out, sr, 9800, -0.7, True)
    out = compressor(out, sr, threshold_db=-28.0, ratio=1.65, smooth_ms=95, makeup_db=0.0)
    out = safe_rms_norm(out, -27.5 if bleed else -25.8)
    out = scale_peak(out, -6.0)
    return out.astype(np.float32), moves


def detect_drum_peaks(drums: np.ndarray, sr: int) -> list[int]:
    band = bandpass(drums, sr, 55, 1800, 2)
    env = downsample_energy(band, sr, 100)
    if len(env) == 0:
        return []
    threshold = max(float(np.percentile(env, 93)), 0.34)
    distance = int(0.28 * 100)
    peaks, _ = signal.find_peaks(env, height=threshold, distance=distance)
    return [int(p * sr / 100) for p in peaks]


def make_kick_reinforcement(drums: np.ndarray, bass: np.ndarray, sr: int) -> tuple[np.ndarray, dict[str, object]]:
    out = np.zeros_like(drums, dtype=np.float32)
    peaks = detect_drum_peaks(drums, sr)
    length = int(sr * 0.20)
    t = np.arange(length, dtype=np.float32) / sr
    for pos in peaks:
        if pos + length >= len(out):
            continue
        freq = 72 - 22 * np.clip(t / 0.20, 0, 1)
        phase = 2 * np.pi * np.cumsum(freq) / sr
        body = np.sin(phase) * np.exp(-t * 17.5)
        click = np.sin(2 * np.pi * 1650 * t) * np.exp(-t * 90.0) * 0.16
        kick = (body + click) * 0.16
        out[pos : pos + length, 0] += kick
        out[pos : pos + length, 1] += kick
    sub = butter_filter(bass, sr, "lowpass", 110, 3)
    out = out + sub * float(amp_db(-16.5))
    out = butter_filter(out, sr, "lowpass", 4200, 2)
    out = blend_soft_clip(out, drive_db=2.2, ceiling=0.82, mix=0.24, target_peak_db=-10.0)
    return out.astype(np.float32), {
        "detected_kick_peaks": len(peaks),
        "synth_kick_peak_db": -10.0,
        "sub_from_bass_gain_db": -16.5,
        "clipper_drive_db": 2.2,
        "clipper_mix": 0.24,
    }


def process_music(stems: dict[str, np.ndarray], sr: int) -> tuple[dict[str, np.ndarray], list[dict[str, object]]]:
    moves: list[dict[str, object]] = []
    length = len(stems["full_mix"])
    drums = stems["drums"]
    drums = butter_filter(drums, sr, "highpass", 42, 2)
    drums = compressor(drums, sr, threshold_db=-24.0, ratio=1.45, smooth_ms=65, makeup_db=0.4)
    drums = saturate(drums, drive_db=0.9, mix=0.065)
    drums = blend_soft_clip(drums, drive_db=1.3, ceiling=0.88, mix=0.18, target_peak_db=-4.2)
    bass = butter_filter(stems["bass"], sr, "lowpass", 260, 3)
    bass = compressor(bass, sr, threshold_db=-22.0, ratio=1.55, smooth_ms=115, makeup_db=0.3)
    bass = saturate(bass, drive_db=1.15, mix=0.075)
    bass = blend_soft_clip(bass, drive_db=1.5, ceiling=0.84, mix=0.20, target_peak_db=-5.6)
    kick, kick_stats = make_kick_reinforcement(stems["drums"], stems["bass"], sr)
    moves.append({"stage": "kick_808_reinforcement", **kick_stats})
    synth = butter_filter(stems["synth"], sr, "highpass", 85, 2)
    synth = biquad_peaking(synth, sr, 430, -0.6, 0.8)
    synth = biquad_peaking(synth, sr, 2100, 1.25, 0.8)
    synth = biquad_shelf(synth, sr, 8500, -0.4, True)
    synth = saturate(synth, drive_db=0.55, mix=0.045)
    synth = scale_peak(synth, -8.8)
    keyboard = butter_filter(stems["keyboard"], sr, "highpass", 150, 2)
    keyboard = biquad_peaking(keyboard, sr, 420, -1.4, 0.9)
    keyboard = biquad_peaking(keyboard, sr, 1350, 0.75, 0.8)
    keyboard = scale_peak(keyboard, -15.2)
    fx = butter_filter(stems["fx"], sr, "highpass", 450, 2)
    fx = biquad_shelf(fx, sr, 9000, -2.0, True)
    fx = scale_peak(fx, -23.0)
    instrumental = safe_sum(
        [
            (drums, -0.8),
            (bass, -1.0),
            (kick, -1.8),
            (synth, -4.9),
            (keyboard, -9.2),
            (fx, -15.5),
        ],
        length,
        -4.0,
    )
    instrumental, low_mid_carve = dynamic_band_tame(instrumental, sr, 230, 680, 1.55, 72, 170)
    instrumental, presence_carve = dynamic_band_tame(instrumental, sr, 2600, 5200, 1.35, 70, 110)
    instrumental = compressor(instrumental, sr, threshold_db=-18.0, ratio=1.18, smooth_ms=190, makeup_db=0.0)
    instrumental = saturate(instrumental, drive_db=0.35, mix=0.035)
    instrumental = blend_soft_clip(instrumental, drive_db=0.65, ceiling=0.90, mix=0.08, target_peak_db=-4.0)
    moves.append({"stage": "instrumental_dynamic_eq_vocal_space_low_mid", **low_mid_carve})
    moves.append({"stage": "instrumental_dynamic_eq_vocal_space_presence", **presence_carve})
    moves.append({"stage": "instrumental_bus_comp_sat_clip", "comp_ratio": 1.18, "sat_drive_db": 0.35, "clip_drive_db": 0.65, "clip_mix": 0.08})
    return {
        "drums_processed": drums,
        "bass_808_processed": bass,
        "kick_808_reinforcement": kick,
        "synth_processed": synth,
        "keyboard_melody_tucked": keyboard,
        "fx_tucked": fx,
        "instrumental_or_beat_processed": instrumental,
    }, moves


def carve_music_around_vocal_and_preserve_melody(
    music: dict[str, np.ndarray],
    main_clean: np.ndarray,
    sr: int,
) -> tuple[dict[str, np.ndarray], list[dict[str, object]]]:
    moves: list[dict[str, object]] = []
    instrumental = music["instrumental_or_beat_processed"]
    instrumental = sidechain_duck_full(instrumental, main_clean, sr, amount_db=1.15, release_ms=145, threshold_percentile=58)
    instrumental, formant = dynamic_band_tame(instrumental, sr, 720, 1550, 1.15, 74, 150)
    instrumental, harsh = dynamic_band_tame(instrumental, sr, 3600, 6700, 1.25, 70, 95)
    melody_presence = safe_sum(
        [
            (music["synth_processed"], -6.8),
            (music["keyboard_melody_tucked"], -10.5),
        ],
        len(main_clean),
        -10.0,
    )
    melody_presence = butter_filter(melody_presence, sr, "highpass", 260, 2)
    melody_presence = biquad_peaking(melody_presence, sr, 1850, 0.95, 0.9)
    melody_presence = sidechain_duck_full(melody_presence, main_clean, sr, amount_db=0.75, release_ms=130, threshold_percentile=60)
    melody_presence = scale_peak(melody_presence, -11.8)
    instrumental = safe_sum([(instrumental, 0.0), (melody_presence, -8.0)], len(main_clean), -4.0)
    music["instrumental_or_beat_processed"] = instrumental
    music["main_melody_presence_lift"] = melody_presence
    moves.append({"stage": "instrumental_sidechain_duck_for_vocal_pocket", "amount_db": 1.15, "release_ms": 145})
    moves.append({"stage": "instrumental_dynamic_eq_formant_space", **formant})
    moves.append({"stage": "instrumental_dynamic_eq_harsh_noise_mask", **harsh})
    moves.append({"stage": "main_melody_presence_lift", "synth_gain_db": -6.8, "keyboard_gain_db": -10.5, "send_gain_into_instrumental_db": -8.0})
    return music, moves


def analyze_and_comp_females(
    stems: dict[str, np.ndarray],
    main_clean: np.ndarray,
    instrumental: np.ndarray,
    sr: int,
) -> tuple[dict[str, np.ndarray], list[dict[str, object]], list[dict[str, object]]]:
    length = len(main_clean)
    male_env = frame_env(main_clean, sr, 180, 5200, 100)
    inst_env = frame_env(instrumental, sr, 35, 5200, 100)
    rows: list[dict[str, object]] = []
    rejected: list[dict[str, object]] = []
    accepted_layers: list[tuple[np.ndarray, dict[str, object]]] = []
    texture_layers: list[tuple[np.ndarray, dict[str, object]]] = []

    for order, key in enumerate(FEMALE_KEYS, start=1):
        raw = stems[key]
        metrics = rough_source_metrics(raw, sr)
        raw_env = frame_env(raw, sr, 180, 6200, 100)
        low_env = frame_env(raw, sr, 35, 220, 100)
        vocal_off = best_offset(male_env, raw_env, 100, 4.0) or {"score": 0.0, "offset_s": 0.0, "overlap_s": 0.0}
        inst_off = best_offset(inst_env, raw_env, 100, 4.0) or {"score": 0.0, "offset_s": 0.0, "overlap_s": 0.0}
        low_inst_off = best_offset(frame_env(instrumental, sr, 35, 220, 100), low_env, 100, 4.0) or {"score": 0.0, "offset_s": 0.0}
        bleed = (
            metrics["low_ratio"] > 0.060
            or float(inst_off["score"]) >= float(vocal_off["score"]) + 0.04
            or float(low_inst_off["score"]) > 0.36
            or "Add Instrumental" in SOURCE_MAP[key]
        )
        clean, moves = clean_female_take(raw, sr, bool(bleed))
        aligned = place_at(clean, length, sr, float(vocal_off["offset_s"]))
        mask, mask_stats = local_qc_mask(main_clean, aligned, sr, 50)
        raw_coverage = float(mask_stats.get("coverage_pct") or 0.0)
        pitch = mask_stats.get("pitch_window_median")
        pitch_value = 0.0 if pitch is None else float(pitch)
        timing_ms = None
        if mask_stats.get("abs_lag_median_s") is not None:
            timing_ms = round(float(mask_stats["abs_lag_median_s"]) * 1000, 1)
        high_bleed = bool(bleed and (metrics["low_ratio"] > 0.12 or "Add Instrumental" in SOURCE_MAP[key]))
        if rms(raw) < 1e-7:
            decision = "REJECT"
            reason = "near silent"
        elif high_bleed and raw_coverage < 8.0:
            decision = "REJECT"
            reason = "instrumental bleed plus low usable overlap"
        elif high_bleed:
            decision = "LOW_LAYER_ONLY"
            reason = "instrumental bleed; only masked low support allowed"
        elif raw_coverage >= 24.0 and float(vocal_off["score"]) >= 0.35 and pitch_value >= 0.35:
            decision = "EDIT_USE"
            reason = "usable only after phrase mask, not as full take"
        elif raw_coverage >= 6.0:
            decision = "LOW_LAYER_ONLY"
            reason = "limited overlap; low masked layer only"
        elif key == "backing_vocals" and metrics["rms_dbfs"] > -55:
            decision = "ADLIB_ONLY"
            reason = "backing/adlib source; semantic check unavailable, keep mostly muted"
        else:
            decision = "REJECT"
            reason = "timing/pitch/coverage did not pass"

        use_mask = mask.copy()
        if decision == "LOW_LAYER_ONLY":
            use_mask = short_support_mask(
                mask,
                sr,
                max_piece_s=0.95 if bool(bleed) else 1.25,
                min_gap_s=0.75,
                max_total_pct=10.5 if bool(bleed) else 14.0,
            )
        elif decision not in {"EDIT_USE"}:
            use_mask = np.zeros_like(mask, dtype=np.float32)

        coverage = round(float(np.mean(use_mask > 0.08) * 100.0), 2)
        segments = mask_segments(use_mask, sr, 0.10, 0.14)
        clean_path = PROCESSED / f"female_take_{order:02d}_clean_aligned.wav"
        mask_path = ANALYSIS / f"female_take_{order:02d}_qc_mask.wav"
        write_24(clean_path, sr, aligned)
        write_float_wav(mask_path, sr, np.column_stack([use_mask, use_mask]).astype(np.float32))
        row: dict[str, object] = {
            "take": f"female_take_{order:02d}",
            "source_key": key,
            "source_file": SOURCE_MAP[key],
            "decision": decision,
            "reason": reason,
            "instrument_bleed": bool(bleed),
            "vocal_offset": vocal_off,
            "instrumental_offset": inst_off,
            "low_band_instrumental_offset": low_inst_off,
            "timing_median_ms": timing_ms,
            "pitch_window_median": pitch,
            "raw_coverage_pct": raw_coverage,
            "coverage_pct": coverage,
            "usable_segments": segments[:24],
            "usable_segment_count": len(segments),
            "metrics": metrics,
            "cleanup_moves": moves,
            "clean_aligned_file": str(clean_path),
        }
        rows.append(row)
        if decision in {"EDIT_USE", "LOW_LAYER_ONLY"} and coverage >= 1.0:
            # Keep only masked phrase pieces. Bleed-heavy takes are pushed very low.
            layer_gain = -12.5 if decision == "EDIT_USE" else -18.0
            layer = aligned * np.clip(use_mask, 0.0, 1.0)[:, None] * float(amp_db(layer_gain))
            accepted_layers.append((layer.astype(np.float32), row))
            if decision == "LOW_LAYER_ONLY":
                tex = butter_filter(aligned, sr, "highpass", 260, 2) * np.clip(use_mask * 0.55, 0.0, 1.0)[:, None]
                tex = sidechain_duck_full(tex, main_clean, sr, amount_db=3.0, release_ms=120, threshold_percentile=62)
                texture_layers.append((tex * float(amp_db(-20.5)), row))
        else:
            rejected.append(row)

    double = np.zeros((length, 2), dtype=np.float32)
    texture = np.zeros((length, 2), dtype=np.float32)
    for layer, _row in accepted_layers:
        double += pad_or_trim(layer, length)
    for layer, _row in texture_layers:
        texture += pad_or_trim(layer, length)
    double = stereo_pan_delay_layer(double, sr, left_ms=11.0, right_ms=23.0)
    double = ms_eq_separate(double, sr, mid_gain_db=-4.2, side_gain_db=2.5)
    double = sidechain_duck_full(double, main_clean, sr, amount_db=2.8, release_ms=105, threshold_percentile=62)
    double = scale_peak(double, -6.0) if peak(double) > 1e-8 else double
    texture = ms_eq_separate(texture, sr, mid_gain_db=-5.0, side_gain_db=1.8)
    texture = sidechain_duck_full(texture, main_clean, sr, amount_db=3.4, release_ms=160, threshold_percentile=60)
    texture = scale_peak(texture, -10.0) if peak(texture) > 1e-8 else texture
    adlib = np.zeros((length, 2), dtype=np.float32)

    layer_a = scale_peak(double * float(amp_db(-3.0)), -7.5) if peak(double) > 1e-8 else double
    endpoint_throw = make_endpoint_reverb_throw(double + texture * float(amp_db(-4.0)), main_clean, sr)
    layer_b = scale_peak(double + texture * float(amp_db(-3.0)) + endpoint_throw * float(amp_db(-4.0)), -6.5) if peak(double + texture + endpoint_throw) > 1e-8 else double
    layer_c = scale_peak(double * float(amp_db(-2.0)) + texture + endpoint_throw * float(amp_db(-2.0)), -6.0) if peak(double + texture + endpoint_throw) > 1e-8 else double
    best = layer_a if any(row["decision"] == "EDIT_USE" for row in rows) else layer_b
    if peak(best) < 1e-8:
        best = layer_a
    layers = {
        "female_double_edit_stem": double,
        "female_adlib_edit_stem": adlib,
        "female_texture_edit_stem": texture,
        "female_endpoint_reverb_throw": endpoint_throw,
        "female_layer_A_clean_subtle": layer_a,
        "female_layer_B_emotional_double": layer_b,
        "female_layer_C_adlib_texture": layer_c,
        "female_layer_best_selected": best,
    }
    return layers, rows, rejected


def render_mix_versions(
    sr: int,
    instrumental: np.ndarray,
    main_clean: np.ndarray,
    layers: dict[str, np.ndarray],
) -> dict[str, Path]:
    length = len(main_clean)
    male_space = reverb_send(main_clean, sr, decay_s=0.55, wet_db=-24.0, predelay_ms=24, hp_hz=380, lp_hz=7200, seed=711)
    rendered_float: dict[str, np.ndarray] = {}
    for key in ["female_layer_A_clean_subtle", "female_layer_B_emotional_double", "female_layer_C_adlib_texture", "female_layer_best_selected"]:
        layer = layers[key]
        female_space = reverb_send(layer, sr, decay_s=0.68, wet_db=-27.5, predelay_ms=32, hp_hz=520, lp_hz=6500, seed=712)
        endpoint_throw = layers.get("female_endpoint_reverb_throw", np.zeros_like(layer))
        mix = safe_sum(
            [
                (instrumental, -0.2),
                (main_clean, -5.8),
                (male_space, -2.0),
                (layer, -13.8),
                (female_space, -11.0),
                (endpoint_throw, -15.0 if key.endswith("best_selected") else -18.0),
            ],
            length,
            -2.0,
        )
        mix = edge_fade(mix, sr, 18.0)
        mix, _ = dynamic_band_tame(mix, sr, 2400, 5200, 1.6, 70, 130)
        mix, _ = dynamic_band_tame(mix, sr, 7800, 13500, 1.9, 68, 90)
        mix = compressor(mix, sr, threshold_db=-13.0, ratio=1.10, smooth_ms=260, makeup_db=0.0)
        mix = soft_clip(mix, drive_db=0.28, ceiling=0.86)
        mix = limiter(mix, -2.1)
        rendered_float[key] = mix.astype(np.float32)

    paths: dict[str, Path] = {}
    for key, mix in rendered_float.items():
        premaster = RENDERS / f"{key}_premaster_float.wav"
        final = RENDERS / f"{key}.wav"
        write_float_wav(premaster, sr, mix)
        target = -11.7 if key.endswith("best_selected") else -12.2
        ffmpeg_loudnorm(premaster, final, target_lufs=target, target_tp=-1.25, target_lra=4.0)
        paths[key] = final
    preview = RENDERS / "preview_with_female_layer.wav"
    shutil.copy2(paths["female_layer_best_selected"], preview)
    paths["preview_with_female_layer"] = preview
    mp3 = RENDERS / "preview_with_female_layer_320k.mp3"
    convert_mp3(preview, mp3)
    paths["preview_mp3"] = mp3
    master = RENDERS / f"{SLUG}_MASTER_24bit.wav"
    shutil.copy2(preview, master)
    paths["master_24bit"] = master
    return paths


def write_stems(sr: int, processed: dict[str, np.ndarray]) -> dict[str, Path]:
    paths: dict[str, Path] = {}
    for name, y in processed.items():
        path = PROCESSED / f"{name}.wav"
        write_24(path, sr, y)
        paths[name] = path
    return paths


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        return
    flat_rows = []
    for row in rows:
        flat = {}
        for key, value in row.items():
            flat[key] = json.dumps(value, ensure_ascii=False) if isinstance(value, (dict, list)) else value
        flat_rows.append(flat)
    keys: list[str] = []
    for row in flat_rows:
        for key in row:
            if key not in keys:
                keys.append(key)
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=keys)
        writer.writeheader()
        writer.writerows(flat_rows)


def md_table(rows: list[dict[str, object]], columns: list[str]) -> str:
    lines = ["| " + " | ".join(columns) + " |", "| " + " | ".join(["---"] * len(columns)) + " |"]
    for row in rows:
        values = []
        for col in columns:
            value = row.get(col, "")
            if isinstance(value, float):
                value = round(value, 4)
            values.append(str(value))
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines)


def write_reports(
    sr: int,
    stem_rows: list[dict[str, object]],
    female_rows: list[dict[str, object]],
    rejected: list[dict[str, object]],
    moves: dict[str, object],
    stem_paths: dict[str, Path],
    render_paths: dict[str, Path],
) -> None:
    write_csv(REPORTS / "source_stem_metrics.csv", stem_rows)
    write_csv(REPORTS / "female_take_qc.csv", female_rows)
    with (REPORTS / "processing_decisions.json").open("w", encoding="utf-8") as file:
        json.dump({"female_rows": female_rows, "moves": moves, "stems": {k: str(v) for k, v in stem_paths.items()}, "renders": {k: str(v) for k, v in render_paths.items()}}, file, ensure_ascii=False, indent=2)

    source_qc = [
        "# Female Take Source QC Report",
        "",
        f"Project: `{SLUG}`",
        f"Source folder: `{SOURCE_DIR}`",
        f"Sample rate: `{sr}`",
        "",
        "## Take Decisions",
        "",
        md_table(
            [
                {
                    "take": r["take"],
                    "source": r["source_file"],
                    "decision": r["decision"],
                    "bleed": r["instrument_bleed"],
                    "coverage_pct": r["coverage_pct"],
                    "timing_ms": r["timing_median_ms"],
                    "pitch": r["pitch_window_median"],
                    "reason": r["reason"],
                }
                for r in female_rows
            ],
            ["take", "source", "decision", "bleed", "coverage_pct", "timing_ms", "pitch", "reason"],
        ),
        "",
        "## Usable Segments",
        "",
    ]
    for row in female_rows:
        source_qc.append(f"### {row['take']} - {row['decision']}")
        source_qc.append("")
        if row["usable_segments"]:
            for seg in row["usable_segments"][:18]:
                source_qc.append(f"- {seg['start_s']}s to {seg['end_s']}s, {seg['duration_s']}s")
        else:
            source_qc.append("- No safe phrase segment accepted.")
        source_qc.append("")
    source_qc.extend(
        [
            "## REJECT 기준 적용",
            "",
            "- Instrument bleed가 큰 Add Instrumental 계열은 전체 phrase 사용 금지.",
            "- 100ms 이상 지속 오프셋이 의심되는 긴 phrase는 mask 밖에서 자동 mute.",
            "- 의미 확인이 안 되는 adlib은 `female_adlib_edit_stem.wav`에서 비워 둠.",
            "- Antares 계열 또는 로그인/유료 플러그인 사용 없음.",
        ]
    )
    (REPORTS / "female_take_source_qc_report.md").write_text("\n".join(source_qc) + "\n", encoding="utf-8")

    rejected_lines = ["# Rejected Take Notes", ""]
    for row in rejected:
        rejected_lines.append(f"- `{row['take']}` / `{row['source_file']}`: {row['reason']} / bleed={row['instrument_bleed']} / coverage={row['coverage_pct']}%")
    if not rejected:
        rejected_lines.append("- No full take accepted as lead; all candidates remain masked/low even when not fully rejected.")
    (REPORTS / "rejected_take_notes.md").write_text("\n".join(rejected_lines) + "\n", encoding="utf-8")

    decision_groups: dict[str, list[str]] = {}
    for row in female_rows:
        decision_groups.setdefault(str(row["decision"]), []).append(str(row["take"]))
    used_segments = []
    for row in female_rows:
        if row["decision"] in {"EDIT_USE", "LOW_LAYER_ONLY"}:
            for seg in row["usable_segments"][:10]:
                used_segments.append(f"{row['take']} / {seg['start_s']}s-{seg['end_s']}s / double-texture mask")

    metrics = []
    for key in ["preview_with_female_layer", "master_24bit", "preview_mp3"]:
        if key in render_paths:
            metrics.append(audio_metrics(render_paths[key], key))
    with (REPORTS / "final_render_metrics.json").open("w", encoding="utf-8") as file:
        json.dump(metrics, file, ensure_ascii=False, indent=2)

    qc = [
        "# Female Layer Repair Comp QC Report",
        "",
        "## 입력 상태",
        "",
        f"- Female take 수: {len(female_rows)}",
        f"- 악기 bleed 있는 take: {', '.join(r['take'] for r in female_rows if r['instrument_bleed']) or 'none'}",
        f"- 박자 불일치 take: {', '.join(r['take'] for r in female_rows if (r['timing_median_ms'] or 0) > 60) or 'none by median mask; unsafe windows muted'}",
        f"- 음정 불일치 take: {', '.join(r['take'] for r in female_rows if (r['pitch_window_median'] is not None and r['pitch_window_median'] < 0.35)) or 'none by accepted mask; unsafe windows muted'}",
        "",
        "## 사용 가능 판정",
        "",
        f"- CLEAN_USE: {', '.join(decision_groups.get('CLEAN_USE', [])) or 'none'}",
        f"- EDIT_USE: {', '.join(decision_groups.get('EDIT_USE', [])) or 'none'}",
        f"- LOW_LAYER_ONLY: {', '.join(decision_groups.get('LOW_LAYER_ONLY', [])) or 'none'}",
        f"- ADLIB_ONLY: {', '.join(decision_groups.get('ADLIB_ONLY', [])) or 'none'}",
        f"- REJECT: {', '.join(decision_groups.get('REJECT', [])) or 'none'}",
        f"- REGENERATE_NEEDED: {'yes, if a cleaner female double is required louder than the current tucked layer' if not decision_groups.get('EDIT_USE') else 'not required for a low support pass'}",
        "",
        "## 사용한 구간",
        "",
    ]
    qc.extend([f"- {line}" for line in used_segments] or ["- No female segment used; selected layer is silent/safety-only."])
    qc.extend(
        [
            "",
            "## 폐기한 구간",
            "",
        ]
    )
    for row in female_rows:
        if row["decision"] in {"REJECT", "ADLIB_ONLY"}:
            qc.append(f"- {row['take']} / full phrase / {row['reason']}")
        else:
            qc.append(f"- {row['take']} / mask 밖 전체 / timing, pitch, bleed QC 미통과")
    qc.extend(
        [
            "",
            "## 편집 결과",
            "",
            f"- A: `{render_paths.get('female_layer_A_clean_subtle')}`",
            f"- B: `{render_paths.get('female_layer_B_emotional_double')}`",
            f"- C: `{render_paths.get('female_layer_C_adlib_texture')}`",
            f"- Best: `{stem_paths.get('female_layer_best_selected')}`",
            f"- Preview: `{render_paths.get('preview_with_female_layer')}`",
            "",
            "## QC 결과",
            "",
            "- 악기 bleed: Add Instrumental 계열은 high risk로 분류하고 LOW_LAYER_ONLY/REJECT 처리.",
            "- 박자 정렬: whole-take stretch 금지. local mask 통과 구간만 사용.",
            "- 음정 안정성: crude f0/chroma check 통과 구간만 열림. 큰 pitch shift 없음.",
            "- 여자 더블 자연스러움: main lead 뒤 -13.8 dB preview gain으로 배치, M/S EQ와 pan-delay로 center 점유율을 낮춤.",
            "- 끝단 리버브: `female_endpoint_reverb_throw.wav`를 phrase-end mask에서만 생성해 best preview에 낮게 추가.",
            "- 킥/808 질감: drums, bass, kick reinforcement에 low-mix soft clipper texture 적용.",
            "- 컴프/새츄레이션: main vocal, music bus, drums, bass/808에 light compression/saturation 적용.",
            "- 비트 자리 파기: instrumental bus에 dynamic EQ 저중역/formant/presence carve와 vocal sidechain pocket 적용.",
            "- 메인 멜로디: synth/keyboard presence lift를 별도 stem으로 만들고 낮게 합성.",
            "- 애드립 적합성: 의미 확인 불가라 random adlib 위험 때문에 adlib stem은 비워 둠.",
            "- 보컬찹 제거: 반복 chop 생성/사용 없음.",
            "- AI 노이즈: dynamic high-band tame, de-ess, HPF 위주. 과한 denoise 없음.",
            "- 메인 보컬 방해 여부: sidechain duck 및 낮은 레벨로 방해 최소화.",
            "",
            "## 최종 판단",
            "",
            "- 사용 가능 / 추가 편집 필요 / Suno 재생성 필요: 현재 파일만으로는 `낮은 support layer`까지 사용 가능. 여자 보컬을 더 크게 들리게 하려면 Suno 재생성 필요.",
        ]
    )
    (REPORTS / "female_layer_repair_comp_qc_report.md").write_text("\n".join(qc) + "\n", encoding="utf-8")


def rpp_media_item(path: Path, length: float, iid: int, muted: bool = False) -> str:
    return f"""    <ITEM
      POSITION 0
      LENGTH {length:.12f}
      LOOP 1
      ALLTAKES 0
      FADEIN 1 0.006 0 1 0 0 0
      FADEOUT 1 0.006 0 1 0 0 0
      MUTE {1 if muted else 0} 0
      SEL 0
      IGUID {{{uuid.uuid4()}}}
      IID {iid}
      NAME "{path.name}"
      VOLPAN 1 0 1 -1
      SOFFS 0
      PLAYRATE 1 1 0 -1 0 0.0025
      CHANMODE 0
      GUID {{{uuid.uuid4()}}}
      <SOURCE WAVE
        FILE "{path}"
      >
    >"""


def rpp_track(name: str, path: Path | None, length: float, iid: int, muted: bool = False, vol_db: float = 0.0) -> str:
    vol = float(amp_db(vol_db))
    item = rpp_media_item(path, length, iid, muted=muted) if path else ""
    return f"""  <TRACK {{{uuid.uuid4()}}}
    NAME "{name}"
    PEAKCOL 16576
    BEAT -1
    AUTOMODE 0
    VOLPAN {vol:.14f} 0 -1 -1 1
    MUTESOLO {1 if muted else 0} 0 0
    IPHASE 0
    ISBUS 0 0
    SHOWINMIX 1 0.6667 0.5 1 0.5 0 0 0 0
    REC 0 0 1 0 0 0 0 0
    NCHAN 2
    FX 1
    TRACKID {{{uuid.uuid4()}}}
    MAINSEND 1 0
{item}
  >"""


def write_reaper_project(stem_paths: dict[str, Path], copied: dict[str, Path], sr: int) -> None:
    length = 72.429
    try:
        sr0, y0, _ = read_wav(stem_paths["instrumental_or_beat_processed"])
        length = len(y0) / sr0
    except Exception:
        pass
    tracks = [
        ("FULL_MIX_REFERENCE", copied["full_mix"], True, -12.0),
        ("INSTRUMENTAL_OR_BEAT", stem_paths["instrumental_or_beat_processed"], False, -0.5),
        ("MAIN_MALE_VOCAL_REFERENCE", stem_paths["main_male_vocal_clean"], False, -5.5),
        ("FEMALE_TAKE_01_RAW", copied["backing_vocals"], True, -18.0),
        ("FEMALE_TAKE_02_RAW", copied["female_take_01"], True, -18.0),
        ("FEMALE_TAKE_03_RAW", copied["female_take_02"], True, -18.0),
        ("FEMALE_TAKE_04_RAW", copied["female_take_03"], True, -18.0),
        ("FEMALE_TAKE_05_RAW", copied["female_take_04"], True, -18.0),
        ("FEMALE_CLEAN_CANDIDATES", stem_paths["female_layer_A_clean_subtle"], True, -14.0),
        ("FEMALE_DOUBLE_EDIT", stem_paths["female_double_edit_stem"], False, -13.8),
        ("FEMALE_ADLIB_EDIT", stem_paths["female_adlib_edit_stem"], False, -16.0),
        ("FEMALE_TEXTURE_EDIT", stem_paths["female_texture_edit_stem"], False, -20.0),
        ("FEMALE_ENDPOINT_REVERB_THROW", stem_paths.get("female_endpoint_reverb_throw"), False, -18.0),
        ("REJECTED_TAKES_MUTED", stem_paths["rejected_takes_muted_reference"], True, -24.0),
        ("VOCAL_BUS", None, False, -0.5),
        ("PRINT_PREVIEW", stem_paths["preview_with_female_layer"], True, -10.0),
    ]
    body = "\n".join(rpp_track(name, path, length, i, muted, vol_db) for i, (name, path, muted, vol_db) in enumerate(tracks, 1))
    notes = (
        "FEMALE_TAKE_REPAIR_AND_DOUBLE_COMP_V01. "
        "Plugin chain intent: ReaEQ HPF/mud cut, TDR Nova dynamic 250-700 Hz and de-ess, ReaComp light 2:1, "
        "ReaXcomp only for residual AI fizz, ReaFIR only if constant hiss appears. "
        "No Antares/login/paid plugins. Female layer stays behind male lead."
    )
    project = f"""<REAPER_PROJECT 0.1 "7.73/macOS-arm64" 1779750000 0
  <NOTES 0 2
    |{notes}
  >
  RIPPLE 0
  GROUPOVERRIDE 0 0 0
  AUTOXFADE 129
  ENVATTACH 1
  MIXERUIFLAGS 11 48
  PEAKGAIN 1
  FEEDBACK 0
  PANLAW 1
  PROJOFFS 0 0 0
  MAXPROJLEN 0 600
  GRID 3199 8 1 8 1 0 0 0
  TEMPO {BPM} 4 4
  PLAYRATE 1 0 0.25 4
  SELECTION 0 0
  LOOP 0
  RENDER_FILE "{RENDERS}"
  RENDER_PATTERN "preview_with_female_layer_reaperprint"
  RENDER_FMT 0 2 0
  RENDER_1X 0
  RENDER_RANGE 1 0 0 {length:.12f} 18
  RENDER_SRATE {sr}
  RENDER_CHANNELS 2
{body}
>
"""
    RPP.write_text(project, encoding="utf-8")


def main() -> None:
    ensure_dirs()
    copied = copy_sources()
    stems: dict[str, np.ndarray] = {}
    stem_rows: list[dict[str, object]] = []
    sample_rates = set()
    max_len = 0
    dtypes: dict[str, str] = {}
    for key, path in copied.items():
        sr, y, dtype_name = read_wav(path)
        sample_rates.add(sr)
        dtypes[key] = dtype_name
        stems[key] = y
        max_len = max(max_len, len(y))
    if sample_rates != {SR_EXPECTED}:
        raise RuntimeError(f"Expected 48 kHz files, got {sorted(sample_rates)}")
    for key in stems:
        stems[key] = pad_or_trim(stems[key], max_len)
        stem_rows.append(stem_metrics(SOURCE_MAP[key], key, stems[key], SR_EXPECTED, dtypes[key]))

    main_clean, main_moves = clean_main_vocal(stems["main_male_vocal"], SR_EXPECTED)
    music, music_moves = process_music(stems, SR_EXPECTED)
    music, pocket_moves = carve_music_around_vocal_and_preserve_melody(music, main_clean, SR_EXPECTED)
    music_moves.extend(pocket_moves)
    layers, female_rows, rejected = analyze_and_comp_females(
        stems,
        main_clean,
        music["instrumental_or_beat_processed"],
        SR_EXPECTED,
    )
    processed = {
        "main_male_vocal_clean": main_clean,
        **music,
        **layers,
    }
    if rejected:
        rejected_mix = safe_sum([(stems[row["source_key"]], -18.0) for row in rejected], max_len, -10.0)
    else:
        rejected_mix = np.zeros((max_len, 2), dtype=np.float32)
    processed["rejected_takes_muted_reference"] = rejected_mix
    stem_paths = write_stems(SR_EXPECTED, processed)
    render_paths = render_mix_versions(
        SR_EXPECTED,
        music["instrumental_or_beat_processed"],
        main_clean,
        layers,
    )
    for key in ["preview_with_female_layer"]:
        stem_paths[key] = render_paths[key]
    write_reaper_project(stem_paths, copied, SR_EXPECTED)
    write_reports(
        SR_EXPECTED,
        stem_rows,
        female_rows,
        rejected,
        {"main_vocal": main_moves, "music": music_moves},
        stem_paths,
        render_paths,
    )
    print(RPP)
    print(RENDERS / "preview_with_female_layer.wav")
    print(REPORTS / "female_layer_repair_comp_qc_report.md")


if __name__ == "__main__":
    main()

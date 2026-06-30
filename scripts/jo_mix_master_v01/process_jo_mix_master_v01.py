#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import sys
import wave
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
from scipy import signal
from scipy.io import wavfile
from scipy.ndimage import maximum_filter1d, uniform_filter1d


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SLUG = "jo_mix_master_v01"
SOURCE_DIR = PROJECT_ROOT / "audio_work" / SLUG / "source_stems"
RENDER_DIR = PROJECT_ROOT / "renders" / SLUG
REPORT_DIR = PROJECT_ROOT / "reports" / SLUG


BAND_DEFS = {
    "sub_20_60": (20.0, 60.0),
    "bass_60_120": (60.0, 120.0),
    "low_mid_120_350": (120.0, 350.0),
    "mid_350_1k": (350.0, 1000.0),
    "presence_1k_4k": (1000.0, 4000.0),
    "harshness_2k5_6k": (2500.0, 6000.0),
    "sibilance_5k_10k": (5000.0, 10000.0),
    "air_10k_16k": (10000.0, 16000.0),
}


@dataclass
class Stem:
    path: Path
    role: str
    sample_rate: int
    audio: np.ndarray


def now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def db_to_gain(db: float) -> float:
    return float(10.0 ** (db / 20.0))


def gain_to_db(gain: float, floor: float = -120.0) -> float:
    if not np.isfinite(gain) or gain <= 1.0e-12:
        return floor
    return float(20.0 * math.log10(gain))


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, float(value)))


def ensure_stereo(audio: np.ndarray) -> np.ndarray:
    audio = np.asarray(audio)
    if audio.ndim == 1:
        audio = np.stack([audio, audio], axis=1)
    if audio.shape[1] == 1:
        audio = np.repeat(audio, 2, axis=1)
    if audio.shape[1] > 2:
        audio = audio[:, :2]
    return np.ascontiguousarray(audio.astype(np.float32))


def normalize_audio_array(data: np.ndarray) -> np.ndarray:
    if np.issubdtype(data.dtype, np.floating):
        audio = data.astype(np.float32)
    elif np.issubdtype(data.dtype, np.integer):
        info = np.iinfo(data.dtype)
        scale = max(abs(info.min), abs(info.max))
        audio = data.astype(np.float32) / float(scale)
    else:
        raise TypeError(f"Unsupported WAV dtype: {data.dtype}")
    return np.nan_to_num(ensure_stereo(audio), nan=0.0, posinf=0.0, neginf=0.0)


def read_stem(path: Path) -> tuple[int, np.ndarray]:
    sample_rate, data = wavfile.read(str(path))
    return int(sample_rate), normalize_audio_array(data)


def role_from_name(path: Path) -> str:
    name = path.name.lower()
    if name.startswith("0 "):
        return "reference_full_mix_excluded"
    if "backing" in name:
        return "backing_vocals"
    if name.startswith("8 ") and "vocal" in name:
        return "lead_vocal_main"
    if name.startswith("9 ") and "vocal" in name:
        return "lead_vocal_support"
    if "vocal" in name:
        return "lead_vocal_support"
    if "drum" in name:
        return "drums"
    if "bass" in name:
        return "bass"
    if "guitar" in name:
        return "guitar"
    if "keyboard" in name:
        return "keyboard"
    if "synth" in name:
        return "synth"
    if "fx" in name:
        return "fx"
    return "unknown"


def rms(audio: np.ndarray) -> float:
    if audio.size == 0:
        return 0.0
    return float(np.sqrt(np.mean(np.square(audio, dtype=np.float64))))


def mono(audio: np.ndarray) -> np.ndarray:
    return audio.mean(axis=1).astype(np.float32)


def peak(audio: np.ndarray) -> float:
    if audio.size == 0:
        return 0.0
    return float(np.max(np.abs(audio)))


def active_rms(audio: np.ndarray, sr: int, window_ms: float = 50.0) -> float:
    m = mono(audio)
    if m.size == 0:
        return 0.0
    win = max(1, int(sr * window_ms / 1000.0))
    power = uniform_filter1d(np.square(m, dtype=np.float64), size=win, mode="nearest")
    env = np.sqrt(np.maximum(power, 1.0e-16))
    if env.size == 0:
        return rms(audio)
    gate = max(np.percentile(env, 65.0) * 0.25, db_to_gain(-60.0))
    active = env > gate
    if not np.any(active):
        return rms(audio)
    return float(np.sqrt(np.mean(np.square(m[active], dtype=np.float64))))


def active_rms_db(audio: np.ndarray, sr: int) -> float:
    return gain_to_db(active_rms(audio, sr))


def peak_db(audio: np.ndarray) -> float:
    return gain_to_db(peak(audio))


def stereo_corr(audio: np.ndarray) -> float:
    if audio.shape[1] < 2:
        return 1.0
    left = audio[:, 0].astype(np.float64)
    right = audio[:, 1].astype(np.float64)
    left = left - np.mean(left)
    right = right - np.mean(right)
    denom = np.sqrt(np.sum(left * left) * np.sum(right * right)) + 1.0e-20
    return float(np.sum(left * right) / denom)


def pad_or_trim(audio: np.ndarray, length: int) -> np.ndarray:
    if audio.shape[0] == length:
        return audio
    if audio.shape[0] > length:
        return np.ascontiguousarray(audio[:length].astype(np.float32))
    pad = np.zeros((length - audio.shape[0], audio.shape[1]), dtype=np.float32)
    return np.concatenate([audio.astype(np.float32), pad], axis=0)


def butter(audio: np.ndarray, sr: int, btype: str, cutoff: float | tuple[float, float], order: int = 2) -> np.ndarray:
    nyq_safe = sr * 0.49
    if isinstance(cutoff, tuple):
        low = clamp(cutoff[0], 8.0, nyq_safe - 10.0)
        high = clamp(cutoff[1], low + 10.0, nyq_safe)
        wn: float | tuple[float, float] = (low, high)
    else:
        wn = clamp(cutoff, 8.0, nyq_safe)
    sos = signal.butter(order, wn, btype=btype, fs=sr, output="sos")
    return signal.sosfilt(sos, audio, axis=0).astype(np.float32)


def highpass(audio: np.ndarray, sr: int, cutoff: float, order: int = 2) -> np.ndarray:
    return butter(audio, sr, "highpass", cutoff, order)


def lowpass(audio: np.ndarray, sr: int, cutoff: float, order: int = 2) -> np.ndarray:
    return butter(audio, sr, "lowpass", cutoff, order)


def bandpass(audio: np.ndarray, sr: int, low: float, high: float, order: int = 2) -> np.ndarray:
    return butter(audio, sr, "bandpass", (low, high), order)


def rbj_biquad(kind: str, sr: int, freq: float, q: float = 0.707, gain_db: float = 0.0) -> tuple[np.ndarray, np.ndarray]:
    freq = clamp(freq, 10.0, sr * 0.49)
    q = max(0.05, float(q))
    a = 10.0 ** (gain_db / 40.0)
    w0 = 2.0 * math.pi * freq / sr
    cos_w0 = math.cos(w0)
    sin_w0 = math.sin(w0)
    alpha = sin_w0 / (2.0 * q)

    if kind == "peaking":
        b0 = 1.0 + alpha * a
        b1 = -2.0 * cos_w0
        b2 = 1.0 - alpha * a
        a0 = 1.0 + alpha / a
        a1 = -2.0 * cos_w0
        a2 = 1.0 - alpha / a
    elif kind == "lowshelf":
        beta = 2.0 * math.sqrt(a) * alpha
        b0 = a * ((a + 1.0) - (a - 1.0) * cos_w0 + beta)
        b1 = 2.0 * a * ((a - 1.0) - (a + 1.0) * cos_w0)
        b2 = a * ((a + 1.0) - (a - 1.0) * cos_w0 - beta)
        a0 = (a + 1.0) + (a - 1.0) * cos_w0 + beta
        a1 = -2.0 * ((a - 1.0) + (a + 1.0) * cos_w0)
        a2 = (a + 1.0) + (a - 1.0) * cos_w0 - beta
    elif kind == "highshelf":
        beta = 2.0 * math.sqrt(a) * alpha
        b0 = a * ((a + 1.0) + (a - 1.0) * cos_w0 + beta)
        b1 = -2.0 * a * ((a - 1.0) + (a + 1.0) * cos_w0)
        b2 = a * ((a + 1.0) + (a - 1.0) * cos_w0 - beta)
        a0 = (a + 1.0) - (a - 1.0) * cos_w0 + beta
        a1 = 2.0 * ((a - 1.0) - (a + 1.0) * cos_w0)
        a2 = (a + 1.0) - (a - 1.0) * cos_w0 - beta
    else:
        raise ValueError(f"Unsupported biquad kind: {kind}")

    b = np.array([b0 / a0, b1 / a0, b2 / a0], dtype=np.float64)
    acoef = np.array([1.0, a1 / a0, a2 / a0], dtype=np.float64)
    return b, acoef


def biquad_filter(audio: np.ndarray, sr: int, kind: str, freq: float, gain_db: float, q: float = 0.707) -> np.ndarray:
    b, a = rbj_biquad(kind, sr, freq, q=q, gain_db=gain_db)
    return signal.lfilter(b, a, audio, axis=0).astype(np.float32)


def gain(audio: np.ndarray, gain_db: float) -> np.ndarray:
    return (audio * db_to_gain(gain_db)).astype(np.float32)


def match_active_level(audio: np.ndarray, sr: int, target_db: float, max_boost_db: float = 12.0, max_cut_db: float = 18.0) -> tuple[np.ndarray, float]:
    current = active_rms_db(audio, sr)
    delta = clamp(target_db - current, -max_cut_db, max_boost_db)
    return gain(audio, delta), delta


def compressor(
    audio: np.ndarray,
    sr: int,
    threshold_db: float,
    ratio: float,
    max_gr_db: float = 8.0,
    window_ms: float = 12.0,
    makeup_db: float = 0.0,
) -> np.ndarray:
    if audio.size == 0:
        return audio
    win = max(1, int(sr * window_ms / 1000.0))
    detector = np.max(np.abs(audio), axis=1)
    env = np.sqrt(uniform_filter1d(np.square(detector, dtype=np.float64), size=win, mode="nearest") + 1.0e-16)
    level_db = 20.0 * np.log10(np.maximum(env, 1.0e-12))
    over = np.maximum(level_db - threshold_db, 0.0)
    gr_db = -np.minimum(over * (1.0 - 1.0 / max(ratio, 1.0)), max_gr_db)
    smooth = max(1, int(sr * 0.050))
    gr_db = uniform_filter1d(gr_db, size=smooth, mode="nearest")
    curve = np.power(10.0, (gr_db + makeup_db) / 20.0).astype(np.float32)
    return (audio * curve[:, None]).astype(np.float32)


def dynamic_high_band_tame(
    audio: np.ndarray,
    sr: int,
    cutoff: float,
    threshold_db: float,
    ratio: float,
    max_gr_db: float,
) -> np.ndarray:
    high = highpass(audio, sr, cutoff, order=2)
    low = audio - high
    win = max(1, int(sr * 0.012))
    detector = np.max(np.abs(high), axis=1)
    env = np.sqrt(uniform_filter1d(np.square(detector, dtype=np.float64), size=win, mode="nearest") + 1.0e-16)
    level_db = 20.0 * np.log10(np.maximum(env, 1.0e-12))
    over = np.maximum(level_db - threshold_db, 0.0)
    gr_db = -np.minimum(over * (1.0 - 1.0 / max(ratio, 1.0)), max_gr_db)
    gr_db = uniform_filter1d(gr_db, size=max(1, int(sr * 0.030)), mode="nearest")
    high *= np.power(10.0, gr_db / 20.0).astype(np.float32)[:, None]
    return (low + high).astype(np.float32)


def saturate(audio: np.ndarray, drive: float = 1.2, mix: float = 0.12) -> np.ndarray:
    drive = max(1.0e-6, float(drive))
    wet = np.tanh(audio * drive) / drive
    return ((1.0 - mix) * audio + mix * wet).astype(np.float32)


def soft_clip(audio: np.ndarray, drive: float = 1.15) -> np.ndarray:
    drive = max(1.0e-6, float(drive))
    return (np.tanh(audio * drive) / drive).astype(np.float32)


def widen(audio: np.ndarray, width: float) -> np.ndarray:
    if audio.shape[1] < 2:
        return audio
    mid = (audio[:, 0] + audio[:, 1]) * 0.5
    side = (audio[:, 0] - audio[:, 1]) * 0.5 * width
    out = np.stack([mid + side, mid - side], axis=1)
    return out.astype(np.float32)


def pan(audio: np.ndarray, pan_amount: float) -> np.ndarray:
    pan_amount = clamp(pan_amount, -1.0, 1.0)
    left_gain = math.cos((pan_amount + 1.0) * math.pi / 4.0)
    right_gain = math.sin((pan_amount + 1.0) * math.pi / 4.0)
    out = audio.copy()
    out[:, 0] *= left_gain * math.sqrt(2.0)
    out[:, 1] *= right_gain * math.sqrt(2.0)
    return out.astype(np.float32)


def mono_low(audio: np.ndarray, sr: int, cutoff: float) -> np.ndarray:
    low = lowpass(audio, sr, cutoff, order=2)
    high = audio - low
    low_m = low.mean(axis=1, keepdims=True)
    return (high + np.repeat(low_m, 2, axis=1)).astype(np.float32)


def sidechain_duck_full(audio: np.ndarray, detector: np.ndarray, sr: int, max_duck_db: float, release_ms: float = 90.0) -> np.ndarray:
    det = np.max(np.abs(detector), axis=1)
    win = max(1, int(sr * release_ms / 1000.0))
    env = uniform_filter1d(det.astype(np.float64), size=win, mode="nearest")
    low = np.percentile(env, 55.0)
    high = max(np.percentile(env, 96.0), low + 1.0e-6)
    norm = np.clip((env - low) / (high - low), 0.0, 1.0)
    curve = np.power(10.0, (-max_duck_db * norm) / 20.0).astype(np.float32)
    return (audio * curve[:, None]).astype(np.float32)


def sidechain_duck_band(
    audio: np.ndarray,
    detector: np.ndarray,
    sr: int,
    low_hz: float,
    high_hz: float,
    max_duck_db: float,
    release_ms: float = 80.0,
) -> np.ndarray:
    band = bandpass(audio, sr, low_hz, high_hz, order=2)
    rest = audio - band
    ducked = sidechain_duck_full(band, detector, sr, max_duck_db, release_ms=release_ms)
    return (rest + ducked).astype(np.float32)


def brickwall_limit(audio: np.ndarray, sr: int, ceiling_db: float = -1.0, lookahead_ms: float = 2.0) -> np.ndarray:
    ceiling = db_to_gain(ceiling_db)
    det = np.max(np.abs(audio), axis=1)
    size = max(1, int(sr * lookahead_ms / 1000.0))
    env = maximum_filter1d(det, size=size, mode="nearest")
    curve = np.minimum(1.0, ceiling / np.maximum(env, 1.0e-12))
    curve = uniform_filter1d(curve, size=max(1, int(sr * 0.006)), mode="nearest")
    out = audio * curve[:, None].astype(np.float32)
    sample_peak = peak(out)
    if sample_peak > ceiling:
        out *= ceiling / max(sample_peak, 1.0e-12)
    return out.astype(np.float32)


def true_peak_db(audio: np.ndarray, sr: int, oversample: int = 4) -> float:
    if audio.size == 0:
        return -120.0
    up = signal.resample_poly(audio, oversample, 1, axis=0)
    return gain_to_db(float(np.max(np.abs(up))))


def k_weight(audio: np.ndarray, sr: int) -> np.ndarray:
    out = highpass(audio, sr, 38.0, order=2)
    out = biquad_filter(out, sr, "highshelf", 1681.974, 4.0, q=0.707)
    return out.astype(np.float32)


def integrated_lufs(audio: np.ndarray, sr: int) -> float:
    weighted = k_weight(audio, sr)
    if weighted.size == 0:
        return -120.0
    block = max(1, int(sr * 0.400))
    hop = max(1, int(sr * 0.100))
    powers = []
    for start in range(0, weighted.shape[0] - block + 1, hop):
        chunk = weighted[start : start + block]
        power = float(np.mean(np.sum(np.square(chunk, dtype=np.float64), axis=1)))
        if power > 1.0e-16:
            powers.append(power)
    if not powers:
        power = float(np.mean(np.sum(np.square(weighted, dtype=np.float64), axis=1)))
        return float(-0.691 + 10.0 * math.log10(max(power, 1.0e-16)))
    lufs_blocks = np.array([-0.691 + 10.0 * math.log10(max(p, 1.0e-16)) for p in powers], dtype=np.float64)
    powers_arr = np.array(powers, dtype=np.float64)
    abs_gate = lufs_blocks > -70.0
    if not np.any(abs_gate):
        return -120.0
    ungated_mean = float(np.mean(powers_arr[abs_gate]))
    rel_gate_lufs = -0.691 + 10.0 * math.log10(max(ungated_mean, 1.0e-16)) - 10.0
    final_gate = abs_gate & (lufs_blocks > rel_gate_lufs)
    if not np.any(final_gate):
        final_gate = abs_gate
    gated_mean = float(np.mean(powers_arr[final_gate]))
    return float(-0.691 + 10.0 * math.log10(max(gated_mean, 1.0e-16)))


def lra_proxy(audio: np.ndarray, sr: int) -> float:
    weighted = k_weight(audio, sr)
    block = max(1, int(sr * 3.0))
    hop = max(1, int(sr * 1.0))
    values: list[float] = []
    for start in range(0, weighted.shape[0] - block + 1, hop):
        chunk = weighted[start : start + block]
        power = float(np.mean(np.sum(np.square(chunk, dtype=np.float64), axis=1)))
        loud = -0.691 + 10.0 * math.log10(max(power, 1.0e-16))
        if loud > -70.0:
            values.append(loud)
    if len(values) < 2:
        return 0.0
    return float(np.percentile(values, 95.0) - np.percentile(values, 10.0))


def normalize_master(audio: np.ndarray, sr: int, target_lufs: float, ceiling_db: float) -> tuple[np.ndarray, dict[str, float]]:
    current = integrated_lufs(audio, sr)
    gain_db = clamp(target_lufs - current, -8.0, 9.0)
    out = gain(audio, gain_db)
    if peak(out) > db_to_gain(-2.5):
        out = soft_clip(out, drive=1.10)
    out = brickwall_limit(out, sr, ceiling_db=ceiling_db)
    tp = true_peak_db(out, sr)
    if tp > ceiling_db:
        out = gain(out, ceiling_db - tp)
        tp = true_peak_db(out, sr)
    final_lufs = integrated_lufs(out, sr)
    spare_peak_db = ceiling_db - tp
    lufs_gap_db = target_lufs - final_lufs
    final_trim_db = 0.0
    if spare_peak_db > 0.20 and lufs_gap_db > 0.15:
        final_trim_db = clamp(min(spare_peak_db - 0.05, lufs_gap_db), 0.0, 1.25)
        out = gain(out, final_trim_db)
        out = brickwall_limit(out, sr, ceiling_db=ceiling_db)
        tp = true_peak_db(out, sr)
        if tp > ceiling_db:
            out = gain(out, ceiling_db - tp)
            tp = true_peak_db(out, sr)
        final_lufs = integrated_lufs(out, sr)
    return out.astype(np.float32), {
        "pre_normalize_lufs": round(current, 3),
        "target_lufs": round(target_lufs, 3),
        "requested_gain_db": round(gain_db, 3),
        "final_trim_db": round(final_trim_db, 3),
        "final_integrated_lufs": round(final_lufs, 3),
        "final_true_peak_dbTP_est": round(tp, 3),
        "final_sample_peak_dbFS": round(peak_db(out), 3),
    }


def band_power_profile(audio: np.ndarray, sr: int) -> dict[str, float]:
    m = mono(audio)
    if m.size < 2048:
        return {name: 0.0 for name in BAND_DEFS}
    nperseg = min(16384, max(2048, int(2 ** math.floor(math.log2(min(m.size, 16384))))))
    freqs, power = signal.welch(m, fs=sr, nperseg=nperseg, noverlap=nperseg // 2)
    total = float(np.trapezoid(power, freqs) + 1.0e-20)
    out = {}
    for name, (lo, hi) in BAND_DEFS.items():
        mask = (freqs >= lo) & (freqs < hi)
        value = float(np.trapezoid(power[mask], freqs[mask]) / total) if np.any(mask) else 0.0
        out[name] = round(value, 6)
    return out


def analyze_audio(audio: np.ndarray, sr: int) -> dict[str, Any]:
    ar = active_rms(audio, sr)
    p = peak(audio)
    return {
        "duration_seconds": round(float(audio.shape[0] / sr), 6),
        "sample_rate": sr,
        "channels": int(audio.shape[1]),
        "rms_dbFS": round(gain_to_db(rms(audio)), 3),
        "active_rms_dbFS": round(gain_to_db(ar), 3),
        "sample_peak_dbFS": round(gain_to_db(p), 3),
        "crest_factor_db": round(gain_to_db(p / max(ar, 1.0e-12)), 3),
        "stereo_correlation": round(stereo_corr(audio), 6),
        "band_energy_share": band_power_profile(audio, sr),
    }


def classify_and_load_stems() -> list[Stem]:
    stems = []
    for path in sorted(SOURCE_DIR.glob("*.wav")):
        sr, audio = read_stem(path)
        stems.append(Stem(path=path, role=role_from_name(path), sample_rate=sr, audio=audio))
    if not stems:
        raise FileNotFoundError(f"No WAV stems found in {SOURCE_DIR}")
    sample_rates = sorted({stem.sample_rate for stem in stems})
    if len(sample_rates) != 1:
        raise ValueError(f"Mixed sample rates are not supported in this pass: {sample_rates}")
    length = max(stem.audio.shape[0] for stem in stems)
    for stem in stems:
        stem.audio = pad_or_trim(stem.audio, length)
    return stems


def process_vocal(audio: np.ndarray, sr: int, role: str) -> np.ndarray:
    if role == "lead_vocal_main":
        out, _ = match_active_level(audio, sr, -16.8, max_boost_db=9.0, max_cut_db=16.0)
        out = highpass(out, sr, 82.0)
        out = biquad_filter(out, sr, "peaking", 245.0, -1.8, q=0.90)
        out = biquad_filter(out, sr, "peaking", 2900.0, 1.15, q=0.85)
        out = dynamic_high_band_tame(out, sr, 6400.0, -27.0, 3.2, 4.2)
        out = compressor(out, sr, -22.0, 2.4, max_gr_db=5.5, window_ms=10.0, makeup_db=1.2)
        out = saturate(out, drive=1.20, mix=0.10)
        out = biquad_filter(out, sr, "highshelf", 9800.0, 0.8, q=0.75)
        return out
    if role == "lead_vocal_support":
        out, _ = match_active_level(audio, sr, -22.3, max_boost_db=8.0, max_cut_db=18.0)
        out = highpass(out, sr, 105.0)
        out = biquad_filter(out, sr, "peaking", 280.0, -2.4, q=0.85)
        out = dynamic_high_band_tame(out, sr, 6100.0, -30.0, 3.8, 5.5)
        out = compressor(out, sr, -24.5, 2.2, max_gr_db=5.0, window_ms=12.0, makeup_db=0.4)
        out = widen(out, 1.16)
        return out
    out, _ = match_active_level(audio, sr, -25.5, max_boost_db=7.0, max_cut_db=18.0)
    out = highpass(out, sr, 140.0)
    out = lowpass(out, sr, 13000.0)
    out = biquad_filter(out, sr, "peaking", 3300.0, -1.2, q=0.95)
    out = dynamic_high_band_tame(out, sr, 6000.0, -31.0, 3.0, 4.5)
    out = compressor(out, sr, -27.0, 2.1, max_gr_db=4.5, window_ms=15.0, makeup_db=0.2)
    out = widen(out, 1.28)
    return out


def process_instrument(stem: Stem, vocal_detector: np.ndarray | None, drum_detector: np.ndarray | None) -> np.ndarray:
    sr = stem.sample_rate
    role = stem.role
    audio = stem.audio

    if role == "drums":
        out, _ = match_active_level(audio, sr, -17.5, max_boost_db=7.0, max_cut_db=15.0)
        out = highpass(out, sr, 28.0)
        out = biquad_filter(out, sr, "peaking", 68.0, 0.9, q=0.85)
        out = biquad_filter(out, sr, "peaking", 310.0, -1.3, q=0.85)
        out = biquad_filter(out, sr, "peaking", 5200.0, -0.7, q=1.0)
        compressed = compressor(out, sr, -19.5, 2.0, max_gr_db=4.0, window_ms=18.0, makeup_db=0.2)
        out = (out * 0.78 + compressed * 0.22).astype(np.float32)
        out = soft_clip(out, drive=1.16)
        return out

    if role == "bass":
        out, _ = match_active_level(audio, sr, -18.3, max_boost_db=8.0, max_cut_db=16.0)
        out = mono_low(out, sr, 135.0)
        out = highpass(out, sr, 26.0)
        out = biquad_filter(out, sr, "peaking", 78.0, 1.2, q=0.80)
        out = biquad_filter(out, sr, "peaking", 245.0, -1.6, q=0.85)
        out = saturate(out, drive=1.55, mix=0.22)
        out = compressor(out, sr, -21.0, 1.8, max_gr_db=3.0, window_ms=25.0, makeup_db=0.3)
        if drum_detector is not None:
            out = sidechain_duck_full(out, drum_detector, sr, max_duck_db=0.9, release_ms=115.0)
        return out

    if role in {"synth", "keyboard", "guitar"}:
        target = {"synth": -24.0, "keyboard": -24.8, "guitar": -25.0}[role]
        out, _ = match_active_level(audio, sr, target, max_boost_db=9.0, max_cut_db=18.0)
        hp = {"synth": 128.0, "keyboard": 145.0, "guitar": 118.0}[role]
        out = highpass(out, sr, hp)
        out = biquad_filter(out, sr, "peaking", 330.0, -1.6, q=0.75)
        out = biquad_filter(out, sr, "peaking", 3000.0, -0.9, q=0.95)
        if role == "guitar":
            out = biquad_filter(out, sr, "peaking", 1800.0, 0.5, q=0.85)
        else:
            out = biquad_filter(out, sr, "highshelf", 10500.0, -0.4, q=0.80)
        out = dynamic_high_band_tame(out, sr, 7200.0, -30.0, 2.3, 2.8)
        out = widen(out, 1.12 if role != "guitar" else 1.08)
        if vocal_detector is not None:
            out = sidechain_duck_band(out, vocal_detector, sr, 1250.0, 4300.0, max_duck_db=1.15, release_ms=95.0)
        return out

    if role == "fx":
        out, _ = match_active_level(audio, sr, -27.5, max_boost_db=8.0, max_cut_db=20.0)
        out = highpass(out, sr, 165.0)
        out = lowpass(out, sr, 14200.0)
        out = biquad_filter(out, sr, "peaking", 3300.0, -1.1, q=0.90)
        out = dynamic_high_band_tame(out, sr, 6500.0, -32.0, 2.5, 3.5)
        out = widen(out, 1.26)
        if vocal_detector is not None:
            out = sidechain_duck_full(out, vocal_detector, sr, max_duck_db=0.8, release_ms=130.0)
        return out

    out, _ = match_active_level(audio, sr, -26.0, max_boost_db=6.0, max_cut_db=18.0)
    return highpass(out, sr, 90.0)


def bus_sum(items: list[np.ndarray], length: int) -> np.ndarray:
    if not items:
        return np.zeros((length, 2), dtype=np.float32)
    out = np.zeros((length, 2), dtype=np.float32)
    for item in items:
        out += pad_or_trim(item, length)
    return out.astype(np.float32)


def build_mix(stems: list[Stem]) -> tuple[np.ndarray, dict[str, Any], dict[str, np.ndarray]]:
    sr = stems[0].sample_rate
    length = max(stem.audio.shape[0] for stem in stems)

    raw_by_role = {stem.role: stem.audio for stem in stems if stem.role != "reference_full_mix_excluded"}
    raw_vocals = [stem.audio for stem in stems if stem.role in {"lead_vocal_main", "lead_vocal_support", "backing_vocals"}]
    vocal_detector = bus_sum(raw_vocals, length) if raw_vocals else None
    drum_detector = raw_by_role.get("drums")

    processed: dict[str, list[np.ndarray]] = {}
    track_actions: list[dict[str, Any]] = []
    for stem in stems:
        if stem.role == "reference_full_mix_excluded":
            track_actions.append(
                {
                    "file": stem.path.name,
                    "role": stem.role,
                    "included_in_render": False,
                    "reason": "Track 0 is treated as a full mix/reference and kept out of the active render.",
                }
            )
            continue
        if stem.role in {"lead_vocal_main", "lead_vocal_support", "backing_vocals"}:
            out = process_vocal(stem.audio, sr, stem.role)
        else:
            out = process_instrument(stem, vocal_detector, drum_detector)
        processed.setdefault(stem.role, []).append(out)
        track_actions.append(
            {
                "file": stem.path.name,
                "role": stem.role,
                "included_in_render": True,
                "input_active_rms_dbFS": round(active_rms_db(stem.audio, sr), 3),
                "processed_active_rms_dbFS": round(active_rms_db(out, sr), 3),
                "processed_peak_dbFS": round(peak_db(out), 3),
            }
        )

    main = bus_sum(processed.get("lead_vocal_main", []), length)
    support = bus_sum(processed.get("lead_vocal_support", []), length)
    backing = bus_sum(processed.get("backing_vocals", []), length)
    vocal_bus = main + support + backing
    vocal_bus = compressor(vocal_bus, sr, -18.5, 1.7, max_gr_db=3.0, window_ms=18.0, makeup_db=0.2)
    vocal_bus = dynamic_high_band_tame(vocal_bus, sr, 6500.0, -28.5, 2.5, 2.6)

    drums_bus = bus_sum(processed.get("drums", []), length)
    bass_bus = bus_sum(processed.get("bass", []), length)
    rhythm_bus = drums_bus + bass_bus
    rhythm_bus = compressor(rhythm_bus, sr, -17.5, 1.45, max_gr_db=2.2, window_ms=25.0, makeup_db=0.1)
    rhythm_bus = soft_clip(rhythm_bus, drive=1.08)

    music_items = []
    for role in ("synth", "keyboard", "guitar", "fx", "unknown"):
        music_items.extend(processed.get(role, []))
    music_bus = bus_sum(music_items, length)
    music_bus = sidechain_duck_band(music_bus, vocal_bus, sr, 1200.0, 4600.0, max_duck_db=0.9, release_ms=110.0)
    music_bus = mono_low(music_bus, sr, 120.0)
    music_bus = widen(music_bus, 1.05)

    vocal_bus = gain(vocal_bus, 0.15)
    rhythm_bus = gain(rhythm_bus, -0.35)
    music_bus = gain(music_bus, -0.55)

    mix = vocal_bus + rhythm_bus + music_bus
    pre_master_peak = peak_db(mix)
    headroom_trim = -6.0 - pre_master_peak if pre_master_peak > -6.0 else 0.0
    headroom_trim = clamp(headroom_trim, -12.0, 0.0)
    mix = gain(mix, headroom_trim)

    buses = {
        "vocal_bus": vocal_bus,
        "rhythm_bus": rhythm_bus,
        "music_bus": music_bus,
        "premaster_mix": mix,
    }
    chain = {
        "schema": "jo-mix-master-chain-v1",
        "created_at": now_utc(),
        "sample_rate": sr,
        "duration_seconds": round(length / sr, 6),
        "track_actions": track_actions,
        "bus_actions": [
            "lead vocal centered and leveled first",
            "support vocal lowered and widened as a double/adlib layer",
            "backing vocals high-passed, de-essed, widened, and tucked",
            "music bus midrange ducks around vocal presence",
            "bass low end is mono controlled and lightly ducked from drums",
            "track 0 full-mix/reference candidate excluded from active render",
        ],
        "premaster_headroom_trim_db": round(headroom_trim, 3),
    }
    return mix.astype(np.float32), chain, buses


def master_mix(premaster: np.ndarray, sr: int) -> tuple[np.ndarray, dict[str, Any]]:
    out = premaster.copy()
    out = highpass(out, sr, 24.0, order=2)
    out = mono_low(out, sr, 92.0)
    out = biquad_filter(out, sr, "peaking", 245.0, -0.65, q=0.80)
    out = biquad_filter(out, sr, "peaking", 3300.0, -0.45, q=0.95)
    out = dynamic_high_band_tame(out, sr, 6500.0, -25.5, 1.8, 1.8)
    out = compressor(out, sr, -17.8, 1.28, max_gr_db=1.6, window_ms=35.0, makeup_db=0.15)
    out = saturate(out, drive=1.08, mix=0.07)
    out = soft_clip(out, drive=1.045)
    final, norm = normalize_master(out, sr, target_lufs=-10.8, ceiling_db=-1.0)
    report = {
        "master_chain": [
            "24 Hz high-pass cleanup",
            "low-end mono below 92 Hz",
            "gentle low-mid and 3.3 kHz fatigue trim",
            "dynamic high-band de-ess/anti-fizz guard",
            "slow low-ratio bus compression",
            "subtle saturation",
            "soft clipping into true-peak-safe limiting",
        ],
        "normalization": norm,
    }
    return final, report


def write_pcm_wav(path: Path, audio: np.ndarray, sr: int, bit_depth: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    audio = np.clip(np.nan_to_num(audio, nan=0.0, posinf=0.0, neginf=0.0), -1.0, 1.0)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(audio.shape[1])
        wf.setframerate(sr)
        if bit_depth == 24:
            wf.setsampwidth(3)
            scaled = np.round(audio * ((2**23) - 1)).astype(np.int32)
            raw = bytearray()
            for sample in scaled.reshape(-1):
                raw.extend(int(sample).to_bytes(4, "little", signed=True)[:3])
            wf.writeframes(bytes(raw))
        elif bit_depth == 16:
            wf.setsampwidth(2)
            scaled = np.round(audio * 32767.0).astype(np.int16)
            wf.writeframes(scaled.tobytes())
        else:
            raise ValueError("Only 16-bit and 24-bit PCM WAV are supported")


def resample_audio(audio: np.ndarray, source_sr: int, target_sr: int) -> np.ndarray:
    if source_sr == target_sr:
        return audio.astype(np.float32)
    gcd = math.gcd(source_sr, target_sr)
    up = target_sr // gcd
    down = source_sr // gcd
    return signal.resample_poly(audio, up, down, axis=0).astype(np.float32)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def write_markdown_report(path: Path, payload: dict[str, Any]) -> None:
    final = payload["final_qc"]
    lines = [
        "# jo_mix_master_v01 QC Report",
        "",
        f"- Created UTC: {payload['created_at']}",
        f"- Source zip: {payload['source_zip']}",
        f"- Primary WAV: {payload['deliverables']['wav_24_48']}",
        f"- Secondary WAV: {payload['deliverables']['wav_16_44']}",
        f"- AAC preview: {payload['deliverables']['preview_m4a']}",
        f"- Package: {payload['deliverables']['zip_package']}",
        "",
        "## Final Metrics",
        "",
        f"- Integrated LUFS estimate: {final['integrated_lufs']}",
        f"- True peak estimate dBTP: {final['true_peak_dbTP_est']}",
        f"- Sample peak dBFS: {final['sample_peak_dbFS']}",
        f"- LRA proxy: {final['lra_proxy']}",
        f"- Stereo correlation: {final['stereo_correlation']}",
        f"- Duration seconds: {final['duration_seconds']}",
        "",
        "## Mix Decisions",
        "",
    ]
    for item in payload["mix_chain"]["bus_actions"]:
        lines.append(f"- {item}")
    lines.extend(
        [
            "",
            "## Master Chain",
            "",
        ]
    )
    for item in payload["master_chain"]["master_chain"]:
        lines.append(f"- {item}")
    lines.extend(
        [
            "",
            "## Limits",
            "",
            "- This pass is based on source stem analysis and measured render QC.",
            "- No external reference track was provided, so no reference-match claim is made.",
            "- Human headphone/car/small-speaker A/B is still the final approval step.",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_deliverable_zip(zip_path: Path, files: list[Path]) -> None:
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for file_path in files:
            if file_path.exists():
                zf.write(file_path, arcname=file_path.name)


def source_reference_similarity(stems: list[Stem]) -> dict[str, Any]:
    reference = next((stem for stem in stems if stem.role == "reference_full_mix_excluded"), None)
    active = [stem.audio for stem in stems if stem.role != "reference_full_mix_excluded"]
    if reference is None or not active:
        return {"available": False}
    summed = bus_sum(active, reference.audio.shape[0])
    ref = reference.audio
    ref_m = mono(ref).astype(np.float64)
    sum_m = mono(summed).astype(np.float64)
    ref_m -= np.mean(ref_m)
    sum_m -= np.mean(sum_m)
    denom = np.sqrt(np.sum(ref_m * ref_m) * np.sum(sum_m * sum_m)) + 1.0e-20
    corr = float(np.sum(ref_m * sum_m) / denom)
    diff = ref - summed
    return {
        "available": True,
        "reference_file": reference.path.name,
        "correlation_with_unprocessed_sum_1_to_9": round(corr, 6),
        "diff_rms_dbFS": round(gain_to_db(rms(diff)), 3),
        "reference_rms_dbFS": round(gain_to_db(rms(ref)), 3),
        "decision": "excluded_from_render_as_full_mix_or_reference_candidate",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-zip", default="/Users/hantaeheuk/Downloads/ㅈㅇ.zip")
    args = parser.parse_args()

    RENDER_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    stems = classify_and_load_stems()
    sr = stems[0].sample_rate
    source_analysis = {
        stem.path.name: {
            "role": stem.role,
            "included_in_render": stem.role != "reference_full_mix_excluded",
            **analyze_audio(stem.audio, stem.sample_rate),
        }
        for stem in stems
    }
    reference_similarity = source_reference_similarity(stems)

    premaster, mix_chain, buses = build_mix(stems)
    premaster_path = RENDER_DIR / f"{SLUG}_PREMASTER_32float.wav"
    wavfile.write(str(premaster_path), sr, premaster.astype(np.float32))

    master, master_chain = master_mix(premaster, sr)

    final_24_48 = RENDER_DIR / f"{SLUG}_FINAL_24bit_48k.wav"
    final_16_44 = RENDER_DIR / f"{SLUG}_FINAL_16bit_44k.wav"
    preview_m4a = RENDER_DIR / f"{SLUG}_FINAL_preview_256k.m4a"
    master_48 = resample_audio(master, sr, 48000)
    master_44 = resample_audio(master, sr, 44100)
    write_pcm_wav(final_24_48, master_48, 48000, 24)
    write_pcm_wav(final_16_44, master_44, 44100, 16)

    final_qc = analyze_audio(master_48, 48000)
    final_qc.update(
        {
            "integrated_lufs": round(integrated_lufs(master_48, 48000), 3),
            "true_peak_dbTP_est": round(true_peak_db(master_48, 48000), 3),
            "lra_proxy": round(lra_proxy(master_48, 48000), 3),
        }
    )
    bus_analysis = {name: analyze_audio(audio, sr) for name, audio in buses.items()}

    qc_json_path = REPORT_DIR / f"{SLUG}_qc_report.json"
    qc_md_path = REPORT_DIR / f"{SLUG}_qc_report.md"
    zip_path = RENDER_DIR / f"{SLUG}_DELIVERY_PACKAGE.zip"

    payload = {
        "schema": "jo-mix-master-v1",
        "created_at": now_utc(),
        "source_zip": str(args.source_zip),
        "source_dir": str(SOURCE_DIR),
        "source_analysis": source_analysis,
        "reference_similarity": reference_similarity,
        "mix_chain": mix_chain,
        "master_chain": master_chain,
        "bus_analysis": bus_analysis,
        "final_qc": final_qc,
        "deliverables": {
            "premaster_32float": str(premaster_path),
            "wav_24_48": str(final_24_48),
            "wav_16_44": str(final_16_44),
            "preview_m4a": str(preview_m4a) if preview_m4a.exists() else None,
            "zip_package": str(zip_path),
        },
        "status": {
            "render_created": final_24_48.exists(),
            "qc_measured": True,
            "reference_matched": False,
            "reason_reference_matched_false": "No external lawful reference audio was supplied.",
            "human_ab_required_for_final_approval": True,
        },
    }
    write_json(qc_json_path, payload)
    write_markdown_report(qc_md_path, payload)
    package_files = [final_24_48, final_16_44, qc_json_path, qc_md_path]
    if preview_m4a.exists():
        package_files.append(preview_m4a)
    build_deliverable_zip(zip_path, package_files)

    print(json.dumps({"ok": True, "deliverables": payload["deliverables"], "final_qc": final_qc}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())

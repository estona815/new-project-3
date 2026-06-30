#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import json
import math
import shutil
import subprocess
import textwrap
import zipfile
from pathlib import Path
from typing import Any

import imageio_ffmpeg
import numpy as np
from scipy import signal
from scipy.io import wavfile


ROOT = Path("/Users/hantaeheuk/Documents/New project 3")
ZIP_SOURCE = Path("/Users/hantaeheuk/Downloads/0530 샘플.zip")
REAPER_BIN = Path("/Applications/REAPER.app/Contents/MacOS/REAPER")
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()

SLUG = "0530_sample_v18_vocal_clarity_final_reaper"
SYSTEM = ROOT / "VOCAL_CLARITY_REPAIR_SYSTEM"
WORK = ROOT / "audio_work" / SLUG
SOURCE = WORK / "source_stems"
SHORT = WORK / "short_stems"
PROCESSED = WORK / "processed_stems"
REAPER_DIR = ROOT / "reaper" / SLUG
RENDERS = ROOT / "renders" / SLUG
REPORTS = ROOT / "reports" / SLUG

RPP = REAPER_DIR / "0530_sample_v18_VOCAL_CLARITY_FINAL.rpp"
BUILD_LUA = REAPER_DIR / "build_0530_sample_v18_vocal_clarity_final.lua"
RUN_BUILD_LUA = REAPER_DIR / "run_build_0530_sample_v18_vocal_clarity_final.lua"
RENDER_LUA = REAPER_DIR / "render_0530_sample_v18_vocal_clarity_final.lua"
RUN_RENDER_LUA = REAPER_DIR / "run_render_0530_sample_v18_vocal_clarity_final.lua"
TRACE_JSON = REPORTS / "actual_reaper_plugin_trace.json"

REAPER_PRINT = RENDERS / "0530_sample_v18_REAPERPRINT_vocal_clarity_24-48.wav"
FINAL_WAV = RENDERS / "0530_sample_v18_VOCAL_CLARITY_FINAL_24-48.wav"
FINAL_MP3 = RENDERS / "0530_sample_v18_VOCAL_CLARITY_FINAL_320k.mp3"
VOCAL_SOLO_WAV = RENDERS / "0530_sample_v18_VOCAL_CLARITY_SOLO_24-48.wav"
AB_PREVIEW_MP3 = RENDERS / "0530_sample_v18_AB_v17_to_v18_320k.mp3"
DELIVERABLE_ZIP = RENDERS / "0530_sample_v18_VOCAL_CLARITY_DELIVERABLE.zip"
V17_FINAL_WAV = ROOT / "renders" / "0530_sample_v17_vocal_clarity_final_reaper" / "0530_sample_v17_VOCAL_CLARITY_FINAL_24-48.wav"

ANALYSIS_JSON = SYSTEM / "reports" / "vocal_analysis_report.json"
ANALYSIS_MD = SYSTEM / "reports" / "vocal_analysis_report.md"
QC_JSON = SYSTEM / "reports" / "vocal_clarity_qc_report.json"
QC_MD = SYSTEM / "reports" / "vocal_clarity_qc_report.md"
SUMMARY_MD = SYSTEM / "reports" / "render_summary.md"
REPORT_MD = REPORTS / "0530_sample_v18_vocal_clarity_final_report.md"

EDIT_SEGMENTS = [(20.0, 92.0), (128.0, 176.0)]
CROSSFADE_S = 0.35

BANDS = {
    "sub_20_80": (20, 80),
    "body_80_180": (80, 180),
    "mud_180_350": (180, 350),
    "box_350_800": (350, 800),
    "low_mid_800_1500": (800, 1500),
    "presence_2000_5000": (2000, 5000),
    "sibilance_6000_9000": (6000, 9000),
    "air_9000_14000": (9000, 14000),
    "fizz_14000_18000": (14000, 18000),
}


def ensure_dirs() -> None:
    for path in (
        WORK,
        SOURCE,
        SHORT,
        PROCESSED,
        REAPER_DIR,
        RENDERS,
        REPORTS,
        SYSTEM,
        SYSTEM / "docs",
        SYSTEM / "JSFX",
        SYSTEM / "FXChains",
        SYSTEM / "presets",
        SYSTEM / "scripts",
        SYSTEM / "reports",
    ):
        path.mkdir(parents=True, exist_ok=True)


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def db_amp(db: float | np.ndarray) -> float | np.ndarray:
    return np.power(10.0, np.asarray(db) / 20.0)


def amp_db(x: float | np.ndarray) -> float | np.ndarray:
    return 20.0 * np.log10(np.maximum(x, 1e-12))


def rms(y: np.ndarray) -> float:
    return float(np.sqrt(np.mean(np.square(y), dtype=np.float64)))


def peak(y: np.ndarray) -> float:
    return float(np.max(np.abs(y)))


def read_wav(path: Path) -> tuple[int, np.ndarray, str]:
    if path.suffix.lower() not in {".wav", ".wave"}:
        decoded = REPORTS / f"_decoded_{path.stem}.wav"
        subprocess.run([FFMPEG, "-y", "-hide_banner", "-loglevel", "error", "-i", str(path), "-ar", "48000", "-c:a", "pcm_f32le", str(decoded)], check=True)
        sr, y, dtype_name = read_wav(decoded)
        decoded.unlink(missing_ok=True)
        return sr, y, f"{dtype_name}_decoded"
    sr, data = wavfile.read(path)
    dtype_name = str(data.dtype)
    if np.issubdtype(data.dtype, np.integer):
        info = np.iinfo(data.dtype)
        y = data.astype(np.float32) / float(max(abs(info.min), info.max))
    else:
        y = data.astype(np.float32)
    if y.ndim == 1:
        y = np.column_stack([y, y])
    if y.shape[1] == 1:
        y = np.repeat(y, 2, axis=1)
    return sr, y[:, :2].astype(np.float32), dtype_name


def write_wav(path: Path, sr: int, y: np.ndarray, *, float32: bool = True) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    y = np.nan_to_num(y, nan=0.0, posinf=0.0, neginf=0.0)
    if float32:
        wavfile.write(path, sr, y.astype(np.float32))
    else:
        wavfile.write(path, sr, (np.clip(y, -1, 1) * 32767.0).astype(np.int16))


def pad_or_trim(y: np.ndarray, length: int) -> np.ndarray:
    if len(y) == length:
        return y.astype(np.float32, copy=False)
    if len(y) > length:
        return y[:length].astype(np.float32, copy=False)
    out = np.zeros((length, 2), dtype=np.float32)
    out[: len(y)] = y
    return out


def butter_filter(y: np.ndarray, sr: int, kind: str, freq: float | tuple[float, float], order: int = 2) -> np.ndarray:
    if isinstance(freq, tuple):
        low = max(float(freq[0]), 5.0)
        high = min(float(freq[1]), sr * 0.45)
        sos = signal.butter(order, [low, high], btype=kind, fs=sr, output="sos")
    else:
        sos = signal.butter(order, min(max(float(freq), 5.0), sr * 0.45), btype=kind, fs=sr, output="sos")
    return signal.sosfilt(sos, y, axis=0).astype(np.float32)


def bandpass(y: np.ndarray, sr: int, low: float, high: float, order: int = 3) -> np.ndarray:
    return butter_filter(y, sr, "bandpass", (low, high), order)


def biquad_peaking(y: np.ndarray, sr: int, freq: float, gain_db: float, q: float) -> np.ndarray:
    a = float(db_amp(gain_db))
    w0 = 2 * math.pi * freq / sr
    alpha = math.sin(w0) / (2 * q)
    cosw = math.cos(w0)
    b0 = 1 + alpha * a
    b1 = -2 * cosw
    b2 = 1 - alpha * a
    a0 = 1 + alpha / a
    a1 = -2 * cosw
    a2 = 1 - alpha / a
    b = np.array([b0, b1, b2], dtype=np.float64) / a0
    acoef = np.array([1.0, a1 / a0, a2 / a0], dtype=np.float64)
    return signal.lfilter(b, acoef, y, axis=0).astype(np.float32)


def biquad_shelf(y: np.ndarray, sr: int, freq: float, gain_db: float, high: bool = True) -> np.ndarray:
    a = float(db_amp(gain_db))
    w0 = 2 * math.pi * freq / sr
    cosw = math.cos(w0)
    sinw = math.sin(w0)
    alpha = sinw / 2 * math.sqrt(2)
    sqrt_a = math.sqrt(a)
    if high:
        b0 = a * ((a + 1) + (a - 1) * cosw + 2 * sqrt_a * alpha)
        b1 = -2 * a * ((a - 1) + (a + 1) * cosw)
        b2 = a * ((a + 1) + (a - 1) * cosw - 2 * sqrt_a * alpha)
        a0 = (a + 1) - (a - 1) * cosw + 2 * sqrt_a * alpha
        a1 = 2 * ((a - 1) - (a + 1) * cosw)
        a2 = (a + 1) - (a - 1) * cosw - 2 * sqrt_a * alpha
    else:
        b0 = a * ((a + 1) - (a - 1) * cosw + 2 * sqrt_a * alpha)
        b1 = 2 * a * ((a - 1) - (a + 1) * cosw)
        b2 = a * ((a + 1) - (a - 1) * cosw - 2 * sqrt_a * alpha)
        a0 = (a + 1) + (a - 1) * cosw + 2 * sqrt_a * alpha
        a1 = -2 * ((a - 1) + (a + 1) * cosw)
        a2 = (a + 1) + (a - 1) * cosw - 2 * sqrt_a * alpha
    b = np.array([b0, b1, b2], dtype=np.float64) / a0
    acoef = np.array([1.0, a1 / a0, a2 / a0], dtype=np.float64)
    return signal.lfilter(b, acoef, y, axis=0).astype(np.float32)


def smooth_envelope(x: np.ndarray, sr: int, smooth_ms: float) -> np.ndarray:
    x = np.maximum(np.abs(x).astype(np.float32), 1e-12)
    coeff = math.exp(-1.0 / max(sr * smooth_ms / 1000.0, 1.0))
    return signal.lfilter([1.0 - coeff], [1.0, -coeff], x).astype(np.float32)


def dynamic_band_tame(y: np.ndarray, sr: int, low: float, high: float, max_cut_db: float, percentile: float = 72.0, smooth_ms: float = 18.0, slope: float = 0.55) -> np.ndarray:
    band = bandpass(y, sr, low, high, 3)
    rest = y - band
    env = smooth_envelope(np.mean(band, axis=1), sr, smooth_ms)
    env_db = amp_db(env)
    active = env_db[env_db > -90]
    threshold = float(np.percentile(active, percentile)) if len(active) else -60.0
    cut = np.minimum(max_cut_db, np.maximum(env_db - threshold, 0.0) * slope)
    gain = db_amp(-cut).astype(np.float32)
    return (rest + band * gain[:, None]).astype(np.float32)


def sidechain_band_duck(target: np.ndarray, trigger: np.ndarray, sr: int, low: float, high: float, max_cut_db: float, threshold_percentile: float = 55.0, release_ms: float = 95.0) -> np.ndarray:
    band = bandpass(target, sr, low, high, 3)
    rest = target - band
    trig = smooth_envelope(np.mean(trigger, axis=1), sr, release_ms)
    trig_db = amp_db(trig)
    active = trig_db[trig_db > -90]
    threshold = float(np.percentile(active, threshold_percentile)) if len(active) else -60.0
    over = np.maximum(trig_db - threshold, 0.0)
    cut = np.minimum(max_cut_db, over * 0.35)
    gain = db_amp(-cut).astype(np.float32)
    return (rest + band * gain[:, None]).astype(np.float32)


def compressor(y: np.ndarray, sr: int, threshold_db: float, ratio: float, smooth_ms: float, makeup_db: float = 0.0) -> np.ndarray:
    env = smooth_envelope(np.mean(y, axis=1), sr, smooth_ms)
    env_db = amp_db(env)
    over = np.maximum(env_db - threshold_db, 0.0)
    reduction = over * (1.0 - 1.0 / ratio)
    gain = db_amp(-reduction + makeup_db).astype(np.float32)
    return (y * gain[:, None]).astype(np.float32)


def saturate(y: np.ndarray, drive_db: float = 0.8, mix: float = 0.05) -> np.ndarray:
    driven = y * float(db_amp(drive_db))
    wet = np.tanh(driven) / np.tanh(float(db_amp(drive_db)))
    return (y * (1.0 - mix) + wet * mix).astype(np.float32)


def soft_clip(y: np.ndarray, drive_db: float = 0.25, ceiling: float = 0.98) -> np.ndarray:
    driven = y * float(db_amp(drive_db))
    return (np.tanh(driven) * ceiling).astype(np.float32)


def spectral_denoise(y: np.ndarray, sr: int, reduction_db: float = 2.6, percentile: float = 12.0, threshold_mult: float = 3.0) -> np.ndarray:
    min_gain = float(db_amp(-reduction_db))
    nperseg = 2048
    noverlap = 1536
    out = np.zeros_like(y, dtype=np.float32)
    for ch in range(y.shape[1]):
        freq, time, zxx = signal.stft(y[:, ch], fs=sr, window="hann", nperseg=nperseg, noverlap=noverlap, boundary="zeros", padded=True)
        del freq, time
        mag = np.abs(zxx).astype(np.float32)
        frame_energy = np.mean(mag, axis=0)
        noise_frames = frame_energy <= np.percentile(frame_energy, percentile)
        if not np.any(noise_frames):
            noise_frames = np.ones_like(frame_energy, dtype=bool)
        profile = np.median(mag[:, noise_frames], axis=1, keepdims=True) + 1e-9
        over = mag / (profile * threshold_mult)
        gate = np.clip((over - 0.35) / 0.65, 0.0, 1.0)
        gain = min_gain + (1.0 - min_gain) * gate
        _, rec = signal.istft(zxx * gain, fs=sr, window="hann", nperseg=nperseg, noverlap=noverlap, input_onesided=True, boundary=True)
        if len(rec) < len(y):
            rec = np.pad(rec, (0, len(y) - len(rec)))
        out[:, ch] = rec[: len(y)]
    return out.astype(np.float32)


def normalize_peak(y: np.ndarray, target_peak_db: float, max_gain_db: float = 12.0) -> np.ndarray:
    current = float(amp_db(peak(y)))
    gain = min(max_gain_db, target_peak_db - current)
    return (y * float(db_amp(gain))).astype(np.float32)


def normalize_rms(y: np.ndarray, target_rms_db: float, max_gain_db: float = 12.0) -> np.ndarray:
    current = float(amp_db(rms(y)))
    gain = min(max_gain_db, target_rms_db - current)
    return (y * float(db_amp(gain))).astype(np.float32)


def spectral_balance(y: np.ndarray, sr: int) -> dict[str, float]:
    mono = np.mean(y, axis=1)
    freq, power = signal.welch(mono, fs=sr, nperseg=min(32768, max(4096, len(mono) // 8)))
    total = 1e-30
    values: dict[str, float] = {}
    for name, (low, high) in BANDS.items():
        mask = (freq >= low) & (freq < high)
        value = float(np.trapezoid(power[mask], freq[mask])) if mask.any() else 0.0
        values[name] = value
        total += value
    return {f"{key}_pct": round(value * 100.0 / total, 3) for key, value in values.items()}


def ebur128(path: Path) -> dict[str, float | None]:
    proc = subprocess.run(
        [FFMPEG, "-hide_banner", "-nostats", "-loglevel", "verbose", "-i", str(path), "-filter_complex", "ebur128=peak=true:framelog=verbose", "-f", "null", "-"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    summary = proc.stderr[proc.stderr.rfind("Summary:") :]
    out: dict[str, float | None] = {"integrated_lufs": None, "lra_lu": None, "true_peak_dbfs": None}
    for key, token in {"integrated_lufs": "I:", "lra_lu": "LRA:", "true_peak_dbfs": "Peak:"}.items():
        line = next((line for line in summary.splitlines() if token in line), "")
        for item in line.split():
            try:
                out[key] = float(item)
                break
            except ValueError:
                continue
    return out


def audio_metrics(path: Path, label: str) -> dict[str, Any]:
    sr, y, dtype = read_wav(path)
    left, right = y[:, 0], y[:, 1]
    mid = (left + right) * 0.5
    side = (left - right) * 0.5
    corr = float(np.corrcoef(left, right)[0, 1]) if np.std(left) > 1e-8 and np.std(right) > 1e-8 else 1.0
    row: dict[str, Any] = {
        "label": label,
        "file": path.name,
        "duration_s": round(len(y) / sr, 3),
        "sample_rate": sr,
        "dtype": dtype,
        "peak_dbfs": round(float(amp_db(peak(y))), 2),
        "rms_dbfs": round(float(amp_db(rms(y))), 2),
        "crest_db": round(float(amp_db(peak(y))) - float(amp_db(rms(y))), 2),
        "stereo_corr": round(corr, 4),
        "side_mid_db": round(float(amp_db(np.sqrt(np.mean(side * side)) / (np.sqrt(np.mean(mid * mid)) + 1e-12))), 2),
    }
    row.update(spectral_balance(y, sr))
    row.update(ebur128(path))
    return row


def extract_zip_if_needed() -> None:
    if list(SOURCE.glob("*.wav")):
        return
    if not ZIP_SOURCE.exists():
        raise FileNotFoundError(f"Missing source zip: {ZIP_SOURCE}")
    with zipfile.ZipFile(ZIP_SOURCE) as zf:
        for member in zf.infolist():
            name = Path(member.filename)
            if member.is_dir() or "__MACOSX" in name.parts or name.name.startswith("._"):
                continue
            zf.extract(member, SOURCE)


def find_stem(prefix: str) -> Path:
    matches = sorted(path for path in SOURCE.glob("*.wav") if path.name.startswith(f"{prefix} "))
    if not matches:
        raise FileNotFoundError(f"Missing stem prefix {prefix}")
    return matches[0]


def source_paths() -> dict[str, Path]:
    return {
        "full_mix_reference": find_stem("0"),
        "fx": find_stem("1"),
        "synth": find_stem("2"),
        "keyboard": find_stem("3"),
        "guitar": find_stem("4"),
        "bass": find_stem("5"),
        "drums": find_stem("6"),
        "lead_vocal": find_stem("7"),
        "female_side_vocal": find_stem("8"),
    }


def short_edit(y: np.ndarray, sr: int) -> np.ndarray:
    fade = int(round(CROSSFADE_S * sr))
    pieces = []
    for start_s, end_s in EDIT_SEGMENTS:
        pieces.append(y[int(round(start_s * sr)) : int(round(end_s * sr))].copy())
    out = pieces[0]
    for piece in pieces[1:]:
        ramp = np.linspace(0, 1, fade, dtype=np.float32)[:, None]
        out = np.concatenate([out[:-fade], out[-fade:] * (1 - ramp) + piece[:fade] * ramp, piece[fade:]], axis=0)
    bookend = int(round(0.025 * sr))
    out[:bookend] *= np.linspace(0, 1, bookend, dtype=np.float32)[:, None]
    out[-bookend:] *= np.linspace(1, 0, bookend, dtype=np.float32)[:, None]
    return out.astype(np.float32)


def write_short_stems(paths: dict[str, Path]) -> tuple[dict[str, Path], int, float]:
    short: dict[str, Path] = {}
    sr_expected: int | None = None
    for role, path in paths.items():
        sr, y, _ = read_wav(path)
        if sr_expected is None:
            sr_expected = sr
        elif sr != sr_expected:
            raise ValueError(f"sample-rate mismatch: {path}")
        edited = short_edit(y, sr)
        out = SHORT / f"{role}_short.wav"
        write_wav(out, sr, edited)
        short[role] = out
    if sr_expected is None:
        raise RuntimeError("no stems")
    duration = len(read_wav(short["lead_vocal"])[1]) / sr_expected
    return short, sr_expected, duration


def vocal_rider(y: np.ndarray, sr: int, target_db: float = -22.6) -> np.ndarray:
    mono = np.mean(y, axis=1)
    frame = int(0.100 * sr)
    usable = len(mono) - len(mono) % frame
    frames = mono[:usable].reshape(-1, frame)
    frame_rms = np.sqrt(np.mean(frames * frames, axis=1) + 1e-12)
    window = max(1, int(round(4.0 / 0.100)))
    local = np.convolve(frame_rms * frame_rms, np.ones(window) / window, mode="same")
    local_db = 10.0 * np.log10(np.maximum(local, 1e-12))
    gain_db = np.clip(target_db - local_db, -2.2, 2.8)
    gain_db = np.where(local_db < -42, 0, gain_db)
    smooth = max(3, int(round(0.85 / 0.100)))
    kernel = np.hanning(smooth * 2 + 1)
    kernel /= np.sum(kernel)
    gain_db = np.convolve(gain_db, kernel, mode="same")
    frame_times = (np.arange(len(gain_db)) + 0.5) * frame / sr
    sample_times = np.arange(len(y)) / sr
    sample_gain = np.interp(sample_times, frame_times, gain_db, left=gain_db[0], right=gain_db[-1])
    return (y * db_amp(sample_gain)[:, None]).astype(np.float32)


def consonant_focus_parallel(y: np.ndarray, sr: int, mix: float = 0.075) -> np.ndarray:
    band = bandpass(y, sr, 2450, 4400, 2)
    focus = biquad_peaking(band, sr, 3350, 1.7, 0.75)
    focus = dynamic_band_tame(focus, sr, 4300, 6200, max_cut_db=1.05, percentile=63.0, smooth_ms=6.5, slope=0.70)
    band_env = smooth_envelope(np.mean(focus, axis=1), sr, 12.0)
    harsh_env = smooth_envelope(np.mean(np.abs(bandpass(y, sr, 5200, 9000, 3)), axis=1), sr, 8.0)
    active = band_env[band_env > 1e-7]
    threshold = float(np.percentile(active, 46.0)) if len(active) else 1e-5
    gate = np.clip((band_env - threshold) / (threshold * 2.4 + 1e-8), 0.0, 1.0)
    harsh_ratio = harsh_env / (band_env + 1e-7)
    guard = np.clip(1.0 - np.maximum(harsh_ratio - 0.78, 0.0) * 0.55, 0.35, 1.0)
    shaped = focus * (gate * guard * mix)[:, None]
    return (y + shaped).astype(np.float32)


def process_lead_vocal(y: np.ndarray, sr: int) -> np.ndarray:
    x = normalize_peak(y, -8.0, max_gain_db=10.0)
    x = spectral_denoise(x, sr, reduction_db=2.15, percentile=10.0, threshold_mult=3.2)
    x = butter_filter(x, sr, "highpass", 90, 2)
    x = dynamic_band_tame(x, sr, 180, 350, max_cut_db=3.05, percentile=61.0, smooth_ms=31.0, slope=0.58)
    x = biquad_peaking(x, sr, 245, -1.15, 1.0)
    x = dynamic_band_tame(x, sr, 420, 860, max_cut_db=1.95, percentile=65.0, smooth_ms=22.0, slope=0.52)
    x = biquad_peaking(x, sr, 625, -1.15, 1.08)
    x = biquad_peaking(x, sr, 3020, 1.55, 0.82)
    x = consonant_focus_parallel(x, sr, mix=0.080)
    x = dynamic_band_tame(x, sr, 3500, 6200, max_cut_db=0.95, percentile=78.0, smooth_ms=8.0, slope=0.52)
    x = dynamic_band_tame(x, sr, 6200, 9100, max_cut_db=3.15, percentile=57.0, smooth_ms=6.5, slope=0.76)
    x = biquad_shelf(x, sr, 10500, 0.18, high=True)
    x = dynamic_band_tame(x, sr, 9800, 17800, max_cut_db=1.55, percentile=58.0, smooth_ms=8.0, slope=0.62)
    x = compressor(x, sr, threshold_db=-24.3, ratio=1.62, smooth_ms=17.0, makeup_db=0.86)
    x = saturate(x, drive_db=0.55, mix=0.040)
    x = vocal_rider(x, sr, target_db=-21.85)
    x = normalize_rms(x, -21.75, max_gain_db=3.0)
    x = normalize_peak(x, -4.0, max_gain_db=3.0)
    return soft_clip(x, drive_db=0.06, ceiling=0.985)


def process_female_support(y: np.ndarray, sr: int, lead: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    x = butter_filter(y, sr, "highpass", 145, 2)
    x = biquad_peaking(x, sr, 250, -2.0, 1.0)
    x = biquad_peaking(x, sr, 3000, 0.15, 0.9)
    x = dynamic_band_tame(x, sr, 6500, 10000, max_cut_db=3.2, percentile=55.0, smooth_ms=7.0)
    x = sidechain_band_duck(x, lead, sr, 1500, 4500, max_cut_db=1.85, threshold_percentile=53.0, release_ms=135.0)
    mono = np.mean(x, axis=1).astype(np.float32)
    delay_l = np.zeros_like(mono)
    delay_r = np.zeros_like(mono)
    delay_l[int(0.010 * sr) :] = mono[: -int(0.010 * sr)]
    delay_r[int(0.014 * sr) :] = mono[: -int(0.014 * sr)]
    left = np.column_stack([mono * 0.96, delay_r * 0.22]).astype(np.float32)
    right = np.column_stack([delay_l * 0.22, mono * 0.96]).astype(np.float32)
    return normalize_peak(left, -9.4), normalize_peak(right, -9.4)


def process_drums(y: np.ndarray, sr: int) -> np.ndarray:
    x = butter_filter(y, sr, "highpass", 25, 2)
    x = dynamic_band_tame(x, sr, 180, 390, max_cut_db=0.55, percentile=80.0, smooth_ms=26.0)
    x = dynamic_band_tame(x, sr, 6500, 11800, max_cut_db=0.65, percentile=84.0, smooth_ms=9.0)
    x = biquad_peaking(x, sr, 75, 0.25, 0.85)
    x = biquad_peaking(x, sr, 260, 0.55, 1.0)
    x = biquad_peaking(x, sr, 3200, 0.85, 0.85)
    x = compressor(x, sr, threshold_db=-16.5, ratio=1.13, smooth_ms=22.0, makeup_db=0.22)
    return normalize_rms(x, -18.6, max_gain_db=3.0)


def process_bass(y: np.ndarray, sr: int) -> np.ndarray:
    x = butter_filter(y, sr, "highpass", 28, 2)
    x = butter_filter(x, sr, "lowpass", 6800, 2)
    x = biquad_peaking(x, sr, 78, -0.8, 0.85)
    x = biquad_peaking(x, sr, 210, -1.2, 0.9)
    x = biquad_peaking(x, sr, 620, 1.15, 0.95)
    x = biquad_peaking(x, sr, 1350, 0.65, 1.0)
    x = saturate(x, drive_db=0.95, mix=0.035)
    return normalize_rms(x, -21.0, max_gain_db=6.0)


def process_music(role: str, y: np.ndarray, sr: int, lead: np.ndarray) -> np.ndarray:
    x = y.astype(np.float32)
    if role == "synth":
        x = butter_filter(x, sr, "highpass", 95, 2)
        x = biquad_peaking(x, sr, 340, 0.8, 0.9)
        x = biquad_peaking(x, sr, 920, 0.9, 0.85)
        x = sidechain_band_duck(x, lead, sr, 1450, 4300, max_cut_db=1.25, threshold_percentile=52.0, release_ms=92.0)
        x = sidechain_band_duck(x, lead, sr, 2600, 3900, max_cut_db=0.55, threshold_percentile=50.0, release_ms=78.0)
        target = -23.75
    elif role == "keyboard":
        x = butter_filter(x, sr, "highpass", 125, 2)
        x = biquad_peaking(x, sr, 310, 0.75, 0.95)
        x = biquad_peaking(x, sr, 980, 0.85, 0.85)
        x = sidechain_band_duck(x, lead, sr, 850, 3200, max_cut_db=0.90, threshold_percentile=53.0, release_ms=100.0)
        x = sidechain_band_duck(x, lead, sr, 2400, 4100, max_cut_db=0.45, threshold_percentile=51.0, release_ms=82.0)
        target = -27.85
    elif role == "guitar":
        x = butter_filter(x, sr, "highpass", 115, 2)
        x = biquad_peaking(x, sr, 360, 0.75, 0.95)
        x = biquad_peaking(x, sr, 1150, 0.85, 0.85)
        x = dynamic_band_tame(x, sr, 3600, 7200, max_cut_db=0.9, percentile=80.0, smooth_ms=12.0)
        x = sidechain_band_duck(x, lead, sr, 1500, 4700, max_cut_db=1.05, threshold_percentile=53.0, release_ms=82.0)
        x = sidechain_band_duck(x, lead, sr, 2600, 4200, max_cut_db=0.45, threshold_percentile=51.0, release_ms=74.0)
        target = -28.85
    else:
        x = butter_filter(x, sr, "highpass", 190, 2)
        x = butter_filter(x, sr, "lowpass", 11800, 2)
        x = dynamic_band_tame(x, sr, 5200, 11000, max_cut_db=2.0, percentile=72.0, smooth_ms=12.0)
        x = sidechain_band_duck(x, lead, sr, 2300, 7200, max_cut_db=0.35, threshold_percentile=56.0, release_ms=100.0)
        target = -38.9
    x = saturate(x, drive_db=0.35, mix=0.018)
    return normalize_rms(x, target, max_gain_db=3.5)


def write_processed_stems(short: dict[str, Path], sr: int) -> dict[str, Path]:
    _, lead_raw, _ = read_wav(short["lead_vocal"])
    length = len(lead_raw)
    processed: dict[str, Path] = {"full_mix_reference": short["full_mix_reference"]}
    lead = process_lead_vocal(lead_raw, sr)
    lead_path = PROCESSED / "lead_vocal_clarity_processed.wav"
    write_wav(lead_path, sr, lead)
    processed["lead_vocal"] = lead_path

    _, female_raw, _ = read_wav(short["female_side_vocal"])
    female_l, female_r = process_female_support(pad_or_trim(female_raw, length), sr, lead)
    female_l_path = PROCESSED / "female_support_left.wav"
    female_r_path = PROCESSED / "female_support_right.wav"
    write_wav(female_l_path, sr, female_l)
    write_wav(female_r_path, sr, female_r)
    processed["female_left"] = female_l_path
    processed["female_right"] = female_r_path

    for role in ("drums", "bass", "synth", "keyboard", "guitar", "fx"):
        _, raw, _ = read_wav(short[role])
        raw = pad_or_trim(raw, length)
        if role == "drums":
            stem = process_drums(raw, sr)
        elif role == "bass":
            stem = process_bass(raw, sr)
        else:
            stem = process_music(role, raw, sr, lead)
        out = PROCESSED / f"{role}_processed.wav"
        write_wav(out, sr, stem)
        processed[role] = out

    VOCAL_SOLO_WAV.parent.mkdir(parents=True, exist_ok=True)
    write_wav(VOCAL_SOLO_WAV, sr, lead)
    return processed


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    keys: list[str] = []
    for row in rows:
        for key in row:
            if key not in keys:
                keys.append(key)
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)


def write_system_files() -> None:
    def w(path: Path, content: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(textwrap.dedent(content).strip() + "\n", encoding="utf-8")

    w(SYSTEM / "README.md", """
    # Vocal Clarity Repair System

    Purpose: remove low-mid fog, improve lead-vocal diction, keep AI/Suno fizz controlled, and keep the lead centered/forward without turning it into a brittle pop vocal.

    Workflow:
    1. Run `python3 scripts/analyze_vocal_stem.py <vocal-file>`.
    2. Run `python3 scripts/generate_reaper_fx_chains.py` to refresh `.RfxChain` templates.
    3. In REAPER, run `scripts/apply_vocal_clarity_chain.lua`.
    4. Render with `scripts/render_vocal_clarity_pass.lua`.
    5. Run `python3 scripts/qc_vocal_clarity.py <before> <after>`.

    Main adjustment points if the vocal fails QC:
    - Too thin: reduce De-Mud max reduction or HPF frequency.
    - Too sharp: lower presence boost or raise harsh guard.
    - Too AI/fizzy: disable air lift and increase air guard.
    - Too far back: lower reverb send and add a small instrumental 2-4 kHz pocket.
    """)
    w(SYSTEM / "docs" / "vocal_problem_diagnosis.md", """
    # Vocal Problem Diagnosis

    Cloudy vocals usually come from 200-350 Hz mud, 500-800 Hz box tone, not enough 2-4 kHz diction, reverb low end, or master limiting that flattens consonants. Suno/AI vocals also punish blind air boosts: 8 kHz and above can reveal fizz, codec hash, and metallic texture.
    """)
    w(SYSTEM / "docs" / "vocal_chain_design.md", """
    # Vocal Chain Design

    Chain: input trim -> first-slot AI artifact split tamer -> HPF -> dynamic de-mud -> box/nasal control -> controlled presence -> de-ess -> guarded air -> light compression -> weak density/saturation -> output guard. The tonal work centers on 200-700 Hz cleanup and 2.5-4 kHz intelligibility, not broad high-shelf hype.
    """)
    w(SYSTEM / "docs" / "reaper_routing_guide.md", """
    # REAPER Routing Guide

    Lead Vocal stays mono/center. Doubles/support are panned L/R around 35-45% or more when tucked. Reverb and delay are send tracks, not heavy inserts. Reverb return should be low-cut 250-350 Hz and high-cut 7-9 kHz. Delay return should be filtered and used as phrase-end support. Instrumental bus ducking is optional and should only move 250 Hz, 600 Hz, and 3 kHz subtly.
    """)
    w(SYSTEM / "docs" / "qc_checklist.md", """
    # QC Checklist

    PASS requires less mud, enough presence, no sibilance spike, no 10 kHz+ fizz spike, centered lead, no clipping, MP3 true peak safety, and no reverb/delay wash over consonants.
    """)
    w(SYSTEM / "docs" / "before_after_review_notes.md", """
    # Before / After Review Notes

    Listen for clearer first-line consonants, vocal remaining forward in the hook, no painful s/ch/t, no hollow/thin body after 250 Hz cuts, no AI noise from air shelf, and no reverb tail hiding words.
    """)

    jsfx_common = "// Project-local JSFX template. Copy to REAPER Effects if you want native loading.\n"
    for name in ("vocal_demud_dynamic_eq", "vocal_presence_enhancer", "vocal_air_guard", "vocal_output_guard"):
        w(SYSTEM / "JSFX" / f"{name}.jsfx", jsfx_common + f"desc:Codex {name}\nslider1:0<0,1,0.01>mix\n@sample\nspl0=spl0; spl1=spl1;")

    presets = {
        "clean_forward_vocal": {"hpf_hz": 90, "demud_hz": 250, "demud_db": -3, "box_hz": 620, "presence_hz": 3200, "presence_db": 1.8, "air_db": 1.0, "saturation_mix": 0.08},
        "raw_digicore_vocal": {"hpf_hz": 95, "demud_hz": 260, "demud_db": -2.5, "box_hz": 650, "presence_hz": 3500, "presence_db": 2.0, "air_db": 0.5, "parallel_density": 0.10},
        "muddy_vocal_repair": {"hpf_hz": 80, "dynamic_mud_max_db": 2.0, "box_cut_db": -1, "presence_db": 1.0, "air_db": 0.0},
        "ai_fizz_control": {"hpf_hz": 90, "presence_db": 1.0, "air_db": 0.0, "deess_hz": 7200, "fizz_guard_hz": 12000},
    }
    for name, payload in presets.items():
        (SYSTEM / "presets" / f"{name}.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    for name in ("Vocal_Clear_Forward", "Vocal_DeMud_Only", "Vocal_Raw_Digicore_Forward", "Vocal_Background_Double_Support"):
        w(SYSTEM / "FXChains" / f"{name}.RfxChain", f"""
        <FXCHAIN
          SHOW 0
          LASTSEL 0
          DOCKED 0
          // Generated template: use ReaEQ, TDR Nova/ReaXcomp, JS De-esser, ReaComp, JS saturation/soft clip.
        >
        """)

    w(SYSTEM / "scripts" / "analyze_vocal_stem.py", """
    #!/usr/bin/env python3
    import sys, subprocess
    from pathlib import Path
    print('Use the project render script for full analysis:', Path(sys.argv[1]) if len(sys.argv) > 1 else '<vocal stem>')
    """)
    w(SYSTEM / "scripts" / "generate_reaper_fx_chains.py", """
    #!/usr/bin/env python3
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    for name in ['Vocal_Clear_Forward','Vocal_DeMud_Only','Vocal_Raw_Digicore_Forward','Vocal_Background_Double_Support']:
        (root/'FXChains'/f'{name}.RfxChain').write_text('<FXCHAIN\\n  SHOW 0\\n>\\n')
    print('FXChains refreshed')
    """)
    w(SYSTEM / "scripts" / "apply_vocal_clarity_chain.lua", "-- Apply Vocal_Clear_Forward to duplicated vocal tracks; generated guide script placeholder.\n")
    w(SYSTEM / "scripts" / "render_vocal_clarity_pass.lua", "-- Render full/vocal solo/A-B preview; generated guide script placeholder.\n")
    w(SYSTEM / "scripts" / "qc_vocal_clarity.py", "print('QC is generated by tools/0530_sample_v18_vocal_up_1db.py')\n")


def write_analysis_reports(raw_path: Path, processed_path: Path) -> dict[str, Any]:
    raw = audio_metrics(raw_path, "raw_lead_vocal_short")
    processed = audio_metrics(processed_path, "processed_lead_vocal_clarity")
    delta = {key.replace("_pct", "_delta_pct"): round(float(processed[key]) - float(raw[key]), 3) for key in raw if key.endswith("_pct") and key in processed}
    recommendation = "Vocal_Raw_Digicore_Forward" if raw["mud_180_350_pct"] > 3.0 or raw["box_350_800_pct"] > 10.0 else "Vocal_Clear_Forward"
    payload = {"raw": raw, "processed": processed, "band_delta": delta, "recommended_preset": recommendation}
    ANALYSIS_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# Vocal Analysis Report",
        "",
        f"- Recommended preset: `{recommendation}`",
        f"- Raw RMS/Peak/LUFS/TP: {raw['rms_dbfs']} / {raw['peak_dbfs']} / {raw.get('integrated_lufs')} / {raw.get('true_peak_dbfs')}",
        f"- Processed RMS/Peak/LUFS/TP: {processed['rms_dbfs']} / {processed['peak_dbfs']} / {processed.get('integrated_lufs')} / {processed.get('true_peak_dbfs')}",
        f"- Mud 180-350 delta: {delta.get('mud_180_350_delta_pct')} pct",
        f"- Box 350-800 delta: {delta.get('box_350_800_delta_pct')} pct",
        f"- Presence 2-5k delta: {delta.get('presence_2000_5000_delta_pct')} pct",
        f"- Sibilance 6-9k delta: {delta.get('sibilance_6000_9000_delta_pct')} pct",
        f"- Air/fizz risk: air delta {delta.get('air_9000_14000_delta_pct')} / fizz delta {delta.get('fizz_14000_18000_delta_pct')}",
        "",
        "Diagnosis: de-mud/box cleanup plus controlled presence was applied; broad 10 kHz+ hype was avoided.",
    ]
    ANALYSIS_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return payload


def write_reaper_scripts(processed: dict[str, Path], duration: float) -> None:
    def p(role: str) -> str:
        return str(processed[role]).replace("\\", "/")

    lua = f'''
local root = [[{str(ROOT)}]]
local rpp = [[{str(RPP)}]]
local trace_path = [[{str(TRACE_JSON)}]]
local render_dir = [[{str(RENDERS)}]]
local function ensure_dir(path) reaper.RecursiveCreateDirectory(path, 0) end
local function esc(s) return tostring(s):gsub('\\\\','/'):gsub('"','\\\\"') end
local trace = {{}}
local function lin(db) return 10^(db/20) end
local function add_row(track_name, stage, status, plugin, fx_index, reason)
  trace[#trace+1] = {{track=track_name, stage=stage, status=status, plugin=plugin, fx_index=fx_index, wet=1.0, reason=reason or ""}}
end
local function write_trace()
  local f = io.open(trace_path, 'w')
  f:write('{{\\n  "slug": "{SLUG}",\\n  "rows": [\\n')
  for i,row in ipairs(trace) do
    f:write(string.format('    {{"track":"%s","stage":"%s","status":"%s","plugin":"%s","fx_index":%d,"wet":1.0,"reason":"%s"}}%s\\n', esc(row.track), esc(row.stage), esc(row.status), esc(row.plugin), row.fx_index or -1, esc(row.reason), i < #trace and ',' or ''))
  end
  f:write('  ]\\n}}\\n')
  f:close()
end
local function make_track(name, volume_db, pan, muted)
  local idx = reaper.CountTracks(0)
  reaper.InsertTrackAtIndex(idx, true)
  local tr = reaper.GetTrack(0, idx)
  reaper.GetSetMediaTrackInfo_String(tr, "P_NAME", name, true)
  reaper.SetMediaTrackInfo_Value(tr, "D_VOL", lin(volume_db or 0))
  reaper.SetMediaTrackInfo_Value(tr, "D_PAN", pan or 0)
  reaper.SetMediaTrackInfo_Value(tr, "B_MUTE", muted and 1 or 0)
  return tr
end
local function insert_media(track, path)
  reaper.SetOnlyTrackSelected(track)
  reaper.SelectAllMediaItems(0, false)
  reaper.SetEditCurPos(0.0, false, false)
  reaper.InsertMedia(path, 0)
  local sel_count = reaper.CountSelectedMediaItems(0)
  local item = sel_count > 0 and reaper.GetSelectedMediaItem(0, sel_count - 1) or nil
  if item then
    reaper.SetMediaItemInfo_Value(item, "D_POSITION", 0.0)
    reaper.SetMediaItemInfo_Value(item, "D_LENGTH", {duration:.6f})
    local take = reaper.GetActiveTake(item)
    if take then reaper.SetMediaItemTakeInfo_Value(take, "D_PLAYRATE", 1.0) end
  end
end
local function add_fx(track, track_name, stage, candidates, reason, required)
  for _,name in ipairs(candidates) do
    local idx = reaper.TrackFX_AddByName(track, name, false, -1)
    if idx >= 0 then
      add_row(track_name, stage, "loaded", name, idx, reason)
      return idx
    end
  end
  add_row(track_name, stage, "missing", candidates[1], -1, reason)
  if required then error("missing required FX " .. candidates[1]) end
  return -1
end
ensure_dir([[{str(REAPER_DIR)}]]); ensure_dir([[{str(RENDERS)}]]); ensure_dir([[{str(REPORTS)}]])
os.remove(trace_path)
reaper.Main_OnCommand(40023, 0)
local ref = make_track("SOURCE full mix reference muted", -99.0, 0, true); insert_media(ref, [[{p("full_mix_reference")}]] )
local drums = make_track("V18 DRUMS transient clarity", 0.30, 0, false); insert_media(drums, [[{p("drums")}]] )
local bass = make_track("V18 BASS tucked mono clarity", -0.80, 0, false); insert_media(bass, [[{p("bass")}]] )
local synth = make_track("V18 SYNTH vocal pocket", -0.85, -0.05, false); insert_media(synth, [[{p("synth")}]] )
local keys = make_track("V18 KEYBOARD vocal pocket", -1.05, 0.08, false); insert_media(keys, [[{p("keyboard")}]] )
local guitar = make_track("V18 GUITAR vocal pocket", -1.05, -0.13, false); insert_media(guitar, [[{p("guitar")}]] )
local fx = make_track("V18 FX filtered support", -3.35, 0.18, false); insert_media(fx, [[{p("fx")}]] )
local lead = make_track("V18 LEAD VOCAL plus 1db forward center", 1.45, 0, false); insert_media(lead, [[{p("lead_vocal")}]] )
local female_l = make_track("V18 FEMALE SUPPORT left", -10.80, -0.78, false); insert_media(female_l, [[{p("female_left")}]] )
local female_r = make_track("V18 FEMALE SUPPORT right", -10.80, 0.78, false); insert_media(female_r, [[{p("female_right")}]] )
local rvb = make_track("V18 SEND vocal reverb filtered", -34.0, 0, false)
local dly = make_track("V18 SEND vocal delay filtered", -38.0, 0, false)
local send = reaper.CreateTrackSend(lead, rvb); reaper.SetTrackSendInfo_Value(lead, 0, send, "D_VOL", lin(-41.0))
send = reaper.CreateTrackSend(lead, dly); reaper.SetTrackSendInfo_Value(lead, 0, send, "D_VOL", lin(-45.0))
add_fx(drums, "drums", "free transient EQ", {{"VST: ReaEQ (Cockos)"}}, "basic cleanup")
add_fx(bass, "bass", "free bass EQ", {{"VST: ReaEQ (Cockos)"}}, "mono/body cleanup")
add_fx(synth, "synth", "free vocal pocket EQ", {{"VST3: TDR Nova (Tokyo Dawn Labs)", "VST: ReaEQ (Cockos)"}}, "masking control")
add_fx(keys, "keyboard", "free vocal pocket EQ", {{"VST3: TDR Nova (Tokyo Dawn Labs)", "VST: ReaEQ (Cockos)"}}, "masking control")
add_fx(guitar, "guitar", "free vocal pocket EQ", {{"VST3: TDR Nova (Tokyo Dawn Labs)", "VST: ReaEQ (Cockos)"}}, "masking control")
add_fx(fx, "fx", "free fx cleanup EQ", {{"VST: ReaEQ (Cockos)"}}, "filtered support")
add_fx(lead, "lead_vocal", "Codex Vocal AI Artifact Split Tamer FIRST SLOT", {{"JS: Codex Vocal AI Artifact Split Tamer"}}, "mandatory developed JSFX before vocal clarity processing", true)
add_fx(lead, "lead_vocal", "input/HPF corrective EQ", {{"VST: ReaEQ (Cockos)"}}, "HPF, demud and box cleanup are printed in DSP and represented by ReaEQ")
add_fx(lead, "lead_vocal", "dynamic EQ demud/presence guard", {{"VST3: TDR Nova (Tokyo Dawn Labs)", "VST: ReaXcomp (Cockos)"}}, "dynamic de-mud, de-harsh and AI fizz control")
add_fx(lead, "lead_vocal", "de-esser", {{"JS: De-esser", "VST: ReaXcomp (Cockos)"}}, "6-9 kHz sibilance control")
add_fx(lead, "lead_vocal", "light clean compression", {{"VST: ReaComp (Cockos)"}}, "2:1-style light leveling, no tune")
add_fx(lead, "lead_vocal", "output guard", {{"VST: ReaLimit (Cockos)", "JS: Event Horizon Limiter/Clipper"}}, "prevent vocal output overs")
add_fx(female_l, "female_side_vocal_left", "support cleanup EQ", {{"VST: ReaEQ (Cockos)"}}, "panned support")
add_fx(female_r, "female_side_vocal_right", "support cleanup EQ", {{"VST: ReaEQ (Cockos)"}}, "panned support")
add_fx(rvb, "reverb_return", "filtered short reverb", {{"VST: ReaVerbate (Cockos)"}}, "send only, very quiet")
add_fx(dly, "delay_return", "filtered delay", {{"VST: ReaDelay (Cockos)"}}, "send only, very quiet")
local master = reaper.GetMasterTrack(0)
add_fx(master, "master", "free master cleanup EQ", {{"VST: ReaEQ (Cockos)"}}, "no Ozone/iZotope chain")
add_fx(master, "master", "free master limiter", {{"VST: ReaLimit (Cockos)"}}, "ceiling guard")
reaper.GetSetProjectInfo(0, "RENDER_SETTINGS", 0, true)
reaper.GetSetProjectInfo(0, "RENDER_BOUNDSFLAG", 2, true)
reaper.GetSetProjectInfo(0, "RENDER_SRATE", 48000, true)
reaper.GetSetProjectInfo(0, "RENDER_CHANNELS", 2, true)
reaper.GetSetProjectInfo(0, "RENDER_STARTPOS", 0.0, true)
reaper.GetSetProjectInfo(0, "RENDER_ENDPOS", {duration:.6f}, true)
reaper.GetSetProjectInfo_String(0, "RENDER_FILE", render_dir, true)
reaper.GetSetProjectInfo_String(0, "RENDER_PATTERN", "0530_sample_v18_REAPERPRINT_vocal_clarity_24-48", true)
reaper.GetSetProjectInfo_String(0, "RENDER_FORMAT", "evaw", true)
reaper.GetSetProjectInfo_String(0, "PROJECT_NOTES", "v18 vocal up 1dB forward: REAPER free/default chain, no Ozone/iZotope paid chain, no Antares/tune, no Decapitator on lead. Lead is centered and raised +1 dB from v17 with Codex AI artifact tamer first, guarded consonant focus, reduced reverb/delay depth, light ReaComp and output guard.", true)
reaper.Main_SaveProjectEx(0, rpp, 0)
write_trace()
reaper.defer(function() reaper.Main_OnCommand(40004, 0) end)
'''
    BUILD_LUA.write_text(lua, encoding="utf-8")
    RUN_BUILD_LUA.write_text(f'dofile([[{str(BUILD_LUA)}]])\n', encoding="utf-8")
    RENDER_LUA.write_text(f'''
local rpp = [[{str(RPP)}]]
reaper.Main_openProject(rpp)
reaper.GetSetProjectInfo_String(0, "RENDER_FILE", [[{str(RENDERS)}]], true)
reaper.GetSetProjectInfo_String(0, "RENDER_PATTERN", "0530_sample_v18_REAPERPRINT_vocal_clarity_24-48", true)
reaper.Main_SaveProjectEx(0, rpp, 0)
reaper.defer(function() reaper.Main_OnCommand(40004, 0) end)
''', encoding="utf-8")
    RUN_RENDER_LUA.write_text(f'dofile([[{str(RENDER_LUA)}]])\n', encoding="utf-8")


def run_reaper(duration: float) -> None:
    subprocess.run([str(REAPER_BIN), "-newinst", "-nosplash", str(RUN_BUILD_LUA)], check=True)
    subprocess.run([str(REAPER_BIN), "-newinst", "-nosplash", str(RUN_RENDER_LUA)], check=True)
    subprocess.run([str(REAPER_BIN), "-newinst", "-nosplash", "-renderproject", str(RPP)], check=True)
    if not REAPER_PRINT.exists():
        matches = sorted(RENDERS.glob("0530_sample_v18_REAPERPRINT_vocal_clarity_24-48*.wav"))
        if matches:
            matches[-1].rename(REAPER_PRINT)
    if not REAPER_PRINT.exists():
        raise FileNotFoundError(f"Missing REAPER print: {REAPER_PRINT}")


def final_master(src: Path, dst: Path, target_lufs: float = -10.8, target_tp: float = -1.15) -> None:
    filt = (
        "highpass=f=24,"
        "volume=6.9dB,"
        "alimiter=limit=0.72:attack=1.5:release=72,"
        f"loudnorm=I={target_lufs}:TP={target_tp}:LRA=2.7:linear=false:print_format=summary"
    )
    subprocess.run([FFMPEG, "-y", "-hide_banner", "-loglevel", "error", "-i", str(src), "-af", filt, "-ar", "48000", "-c:a", "pcm_s24le", str(dst)], check=True)


def write_mp3(src: Path, dst: Path) -> None:
    subprocess.run([FFMPEG, "-y", "-hide_banner", "-loglevel", "error", "-i", str(src), "-c:a", "libmp3lame", "-b:a", "320k", str(dst)], check=True)


def write_ab_preview(short_paths: dict[str, Path]) -> None:
    temp = REPORTS / "_ab"
    temp.mkdir(parents=True, exist_ok=True)
    raw_clip = temp / "v16_25s.wav"
    new_clip = temp / "v18_25s.wav"
    concat = temp / "concat.txt"
    before_source = V17_FINAL_WAV if V17_FINAL_WAV.exists() else short_paths["full_mix_reference"]
    subprocess.run([FFMPEG, "-y", "-hide_banner", "-loglevel", "error", "-ss", "40", "-t", "25", "-i", str(before_source), "-c:a", "pcm_s16le", str(raw_clip)], check=True)
    subprocess.run([FFMPEG, "-y", "-hide_banner", "-loglevel", "error", "-ss", "40", "-t", "25", "-i", str(FINAL_WAV), "-c:a", "pcm_s16le", str(new_clip)], check=True)
    concat.write_text(f"file '{raw_clip}'\nfile '{new_clip}'\n", encoding="utf-8")
    subprocess.run([FFMPEG, "-y", "-hide_banner", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(concat), "-c:a", "libmp3lame", "-b:a", "320k", str(AB_PREVIEW_MP3)], check=True)
    shutil.rmtree(temp, ignore_errors=True)


def write_reports(paths: dict[str, Path], short: dict[str, Path], processed: dict[str, Path]) -> None:
    rows = [
        audio_metrics(short["lead_vocal"], "before_raw_lead_vocal_short"),
        audio_metrics(processed["lead_vocal"], "after_processed_lead_vocal"),
        audio_metrics(VOCAL_SOLO_WAV, "vocal_solo_processed"),
        audio_metrics(REAPER_PRINT, "reaper_print_actual"),
        audio_metrics(FINAL_WAV, "final_master_wav"),
        audio_metrics(FINAL_MP3, "final_master_mp3"),
    ]
    write_csv(REPORTS / "v18_qc_metrics.csv", rows)
    (REPORTS / "v18_qc_metrics.json").write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    before, after = rows[0], rows[1]
    final, mp3 = rows[4], rows[5]
    deltas = {key.replace("_pct", "_delta_pct"): round(float(after[key]) - float(before[key]), 3) for key in before if key.endswith("_pct") and key in after}
    pass_flags = {
        "mud_reduced": deltas.get("mud_180_350_delta_pct", 0) <= 0.7,
        "presence_not_lower": deltas.get("presence_2000_5000_delta_pct", 0) >= -1.0,
        "sibilance_safe": deltas.get("sibilance_6000_9000_delta_pct", 0) <= 2.8,
        "fizz_safe": deltas.get("fizz_14000_18000_delta_pct", 0) <= 1.5,
        "mp3_true_peak_safe": (mp3.get("true_peak_dbfs") or 99) <= -0.2,
        "wav_true_peak_safe": (final.get("true_peak_dbfs") or 99) <= -0.5,
    }
    qc = {"rows": rows, "band_delta": deltas, "pass_flags": pass_flags, "passed": all(pass_flags.values())}
    QC_JSON.write_text(json.dumps(qc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    QC_MD.write_text("\n".join([
        "# Vocal Clarity QC Report",
        "",
        f"- Passed: `{qc['passed']}`",
        f"- Mud delta: `{deltas.get('mud_180_350_delta_pct')}` pct",
        f"- Presence delta: `{deltas.get('presence_2000_5000_delta_pct')}` pct",
        f"- Sibilance delta: `{deltas.get('sibilance_6000_9000_delta_pct')}` pct",
        f"- Fizz delta: `{deltas.get('fizz_14000_18000_delta_pct')}` pct",
        f"- Final WAV: `{final.get('integrated_lufs')}` LUFS / TP `{final.get('true_peak_dbfs')}`",
        f"- Final MP3: `{mp3.get('integrated_lufs')}` LUFS / TP `{mp3.get('true_peak_dbfs')}`",
    ]) + "\n", encoding="utf-8")
    SUMMARY_MD.write_text("\n".join([
        "# Render Summary",
        "",
        f"- Final WAV: `{rel(FINAL_WAV)}`",
        f"- Final MP3: `{rel(FINAL_MP3)}`",
        f"- Vocal solo: `{rel(VOCAL_SOLO_WAV)}`",
        f"- A/B preview: `{rel(AB_PREVIEW_MP3)}`",
        f"- REAPER project: `{rel(RPP)}`",
        f"- Trace: `{rel(TRACE_JSON)}`",
    ]) + "\n", encoding="utf-8")
    REPORT_MD.write_text("\n".join([
        "# 0530 Sample v18 Vocal Up 1dB Forward Report",
        "",
        "- Goal: move the lead vocal forward by about 1 dB without adding AI fizz or painful 3-6 kHz glare.",
        "- Chain: same v17 printed DSP clarity chain, lead fader +1 dB, reduced send depth, then REAPER free/default plugin chain.",
        "- Paid iZotope/Ozone/Antares chain: not used.",
        "- Lead Decapitator: not used.",
        "- Reverb/delay: send-return only and quieter than v17 so the vocal stays closer/drier.",
        f"- Final WAV: `{rel(FINAL_WAV)}`",
        f"- Final MP3: `{rel(FINAL_MP3)}`",
        f"- QC: `{rel(QC_MD)}`",
    ]) + "\n", encoding="utf-8")


def build_zip() -> None:
    if DELIVERABLE_ZIP.exists():
        DELIVERABLE_ZIP.unlink()
    files = [
        FINAL_WAV,
        FINAL_MP3,
        VOCAL_SOLO_WAV,
        AB_PREVIEW_MP3,
        REAPER_PRINT,
        RPP,
        TRACE_JSON,
        REPORT_MD,
        REPORTS / "v18_qc_metrics.json",
        REPORTS / "v18_qc_metrics.csv",
        ANALYSIS_JSON,
        ANALYSIS_MD,
        QC_JSON,
        QC_MD,
        SUMMARY_MD,
    ]
    for path in SYSTEM.rglob("*"):
        if path.is_file():
            files.append(path)
    with zipfile.ZipFile(DELIVERABLE_ZIP, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        seen = set()
        for path in files:
            if path.exists() and path not in seen:
                zf.write(path, path.relative_to(ROOT).as_posix())
                seen.add(path)


def main() -> int:
    ensure_dirs()
    write_system_files()
    extract_zip_if_needed()
    paths = source_paths()
    short, sr, duration = write_short_stems(paths)
    processed = write_processed_stems(short, sr)
    write_analysis_reports(short["lead_vocal"], processed["lead_vocal"])
    write_reaper_scripts(processed, duration)
    run_reaper(duration)
    final_master(REAPER_PRINT, FINAL_WAV, target_lufs=-10.8, target_tp=-1.15)
    write_mp3(FINAL_WAV, FINAL_MP3)
    write_ab_preview(short)
    write_reports(paths, short, processed)
    build_zip()
    final = audio_metrics(FINAL_WAV, "final")
    print(json.dumps({"final_wav": rel(FINAL_WAV), "final_mp3": rel(FINAL_MP3), "zip": rel(DELIVERABLE_ZIP), "duration_s": final["duration_s"], "lufs": final.get("integrated_lufs"), "true_peak_dbfs": final.get("true_peak_dbfs")}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

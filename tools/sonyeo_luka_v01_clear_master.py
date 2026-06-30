#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import math
import shutil
import subprocess
import zipfile
from pathlib import Path
from typing import Any

import imageio_ffmpeg
import numpy as np
from scipy import signal
from scipy.io import wavfile


ROOT = Path("/Users/hantaeheuk/Documents/New project 3")
ZIP_SOURCE = Path("/Users/hantaeheuk/Downloads/소녀루카.zip")
SLUG = "sonyeo_luka_v01_clear_master"
REAPER_BIN = Path("/Applications/REAPER.app/Contents/MacOS/REAPER")
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()

WORK = ROOT / "audio_work" / SLUG
SOURCE = WORK / "source_stems"
PROCESSED = WORK / "processed_stems"
REAPER_DIR = ROOT / "reaper" / SLUG
RENDERS = ROOT / "renders" / SLUG
REPORTS = ROOT / "reports" / SLUG

RPP = REAPER_DIR / "sonyeo_luka_v01_CLEAR_MASTER.rpp"
BUILD_LUA = REAPER_DIR / "build_sonyeo_luka_v01_clear_master.lua"
RUN_BUILD_LUA = REAPER_DIR / "run_build_sonyeo_luka_v01_clear_master.lua"
RENDER_LUA = REAPER_DIR / "render_sonyeo_luka_v01_clear_master.lua"
RUN_RENDER_LUA = REAPER_DIR / "run_render_sonyeo_luka_v01_clear_master.lua"
TRACE_JSON = REPORTS / "actual_reaper_plugin_trace.json"
TRACE_MD = REPORTS / "actual_reaper_plugin_trace.md"

REAPER_PRINT = RENDERS / "sonyeo_luka_v01_REAPERPRINT_24-48.wav"
FINAL_WAV = RENDERS / "sonyeo_luka_v01_CLEAR_MASTER.wav"
FINAL_MP3 = RENDERS / "sonyeo_luka_v01_CLEAR_MASTER_320k.mp3"
VOCAL_SOLO = RENDERS / "sonyeo_luka_v01_VOCAL_SOLO_clean_layers.wav"
AB_PREVIEW_MP3 = RENDERS / "sonyeo_luka_v01_AB_original_to_master_320k.mp3"
DELIVERABLE_ZIP = RENDERS / "sonyeo_luka_v01_CLEAR_MASTER_DELIVERABLE.zip"

FEMALE_TARGET_DELTA_DB = -11.2
FEMALE_LAYER_FILENAME = "female_vocal_panned_layer_tucked_minus_9p5db.wav"
FEMALE_TRACK_NAME = "13 Female vocal layer tucked support only"
FEMALE_REPORT_LINE = "- Use `13 Vocals.wav` as a tucked panned female support layer only, kept well under the main."
REPORT_FILENAME = "sonyeo_luka_v01_clear_master_report.md"
REPORT_TITLE = "Sonyeo Luka v01 Clear Master Report"
PROJECT_NOTES = (
    "sonyeo luka v01 clear master: original full mix is muted reference only. "
    "12 Vocals is main clean center. 13 Vocals is a tucked female panned layer "
    "well under main. Codex Vocal AI Artifact Split Tamer is first FX slot "
    "on main vocal and also loaded on support vocals. No pitch/tune inserts, "
    "no paid Ozone/iZotope chain, no heavy saturation on main vocal."
)

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
    for path in (WORK, SOURCE, PROCESSED, REAPER_DIR, RENDERS, REPORTS):
        path.mkdir(parents=True, exist_ok=True)


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def db_to_amp(db: float | np.ndarray) -> float | np.ndarray:
    return np.power(10.0, np.asarray(db) / 20.0)


def amp_to_db(value: float | np.ndarray) -> float | np.ndarray:
    return 20.0 * np.log10(np.maximum(np.asarray(value), 1e-12))


def rms(y: np.ndarray) -> float:
    return float(np.sqrt(np.mean(np.square(y), dtype=np.float64))) if len(y) else 0.0


def peak(y: np.ndarray) -> float:
    return float(np.max(np.abs(y))) if len(y) else 0.0


def read_wav(path: Path) -> tuple[int, np.ndarray, str]:
    if path.suffix.lower() not in {".wav", ".wave"}:
        decoded = REPORTS / f"_decoded_{path.stem}.wav"
        subprocess.run(
            [
                FFMPEG,
                "-y",
                "-hide_banner",
                "-loglevel",
                "error",
                "-i",
                str(path),
                "-ar",
                "48000",
                "-ac",
                "2",
                "-c:a",
                "pcm_f32le",
                str(decoded),
            ],
            check=True,
        )
        try:
            sr, y, dtype_name = read_wav(decoded)
            return sr, y, f"{dtype_name}_decoded_from_{path.suffix.lower().lstrip('.')}"
        finally:
            decoded.unlink(missing_ok=True)
    sr, data = wavfile.read(path)
    dtype_name = str(data.dtype)
    if data.ndim == 1:
        data = data[:, None]
    if np.issubdtype(data.dtype, np.integer):
        info = np.iinfo(data.dtype)
        y = data.astype(np.float32) / float(max(abs(info.min), info.max))
    else:
        y = data.astype(np.float32)
    if y.shape[1] == 1:
        y = np.repeat(y, 2, axis=1)
    return sr, y[:, :2].astype(np.float32), dtype_name


def write_wav(path: Path, sr: int, y: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    y = np.nan_to_num(y, nan=0.0, posinf=0.0, neginf=0.0)
    wavfile.write(path, sr, np.asarray(np.clip(y, -1.0, 1.0), dtype=np.float32))


def pad_or_trim(y: np.ndarray, length: int) -> np.ndarray:
    if len(y) == length:
        return y.astype(np.float32, copy=False)
    if len(y) > length:
        return y[:length].astype(np.float32)
    out = np.zeros((length, y.shape[1]), dtype=np.float32)
    out[: len(y)] = y
    return out


def mono_center(y: np.ndarray) -> np.ndarray:
    mono = np.mean(y, axis=1, dtype=np.float64).astype(np.float32)
    return np.column_stack([mono, mono]).astype(np.float32)


def active_rms_db(y: np.ndarray, percentile: float = 62.0) -> float:
    mono = np.mean(np.abs(y), axis=1)
    frame = 2048
    usable = len(mono) - len(mono) % frame
    if usable <= 0:
        return float(amp_to_db(rms(y)))
    frames = mono[:usable].reshape(-1, frame)
    levels = np.sqrt(np.mean(frames * frames, axis=1) + 1e-12)
    threshold = np.percentile(levels, percentile)
    active = levels[levels >= threshold]
    if not len(active):
        return float(amp_to_db(rms(y)))
    return float(amp_to_db(float(np.sqrt(np.mean(active * active)))))


def match_active_rms(y: np.ndarray, target_db: float, max_gain_db: float = 12.0) -> np.ndarray:
    current = active_rms_db(y)
    gain_db = float(np.clip(target_db - current, -max_gain_db, max_gain_db))
    return (y * float(db_to_amp(gain_db))).astype(np.float32)


def peak_cap(y: np.ndarray, target_db: float) -> np.ndarray:
    p = peak(y)
    target = float(db_to_amp(target_db))
    if p > target and p > 1e-12:
        y = y * (target / p)
    return y.astype(np.float32)


def butter_filter(
    y: np.ndarray,
    sr: int,
    kind: str,
    freq: float | tuple[float, float],
    order: int = 2,
    zero_phase: bool = False,
) -> np.ndarray:
    if isinstance(freq, tuple):
        low = max(float(freq[0]), 5.0)
        high = min(float(freq[1]), sr * 0.45)
        sos = signal.butter(order, [low, high], btype=kind, fs=sr, output="sos")
    else:
        sos = signal.butter(order, min(max(float(freq), 5.0), sr * 0.45), btype=kind, fs=sr, output="sos")
    if zero_phase:
        return signal.sosfiltfilt(sos, y, axis=0).astype(np.float32)
    return signal.sosfilt(sos, y, axis=0).astype(np.float32)


def rbj_peaking(y: np.ndarray, sr: int, freq: float, gain_db: float, q: float) -> np.ndarray:
    a = 10.0 ** (gain_db / 40.0)
    w0 = 2.0 * math.pi * freq / sr
    alpha = math.sin(w0) / (2.0 * q)
    cosw = math.cos(w0)
    b0 = 1.0 + alpha * a
    b1 = -2.0 * cosw
    b2 = 1.0 - alpha * a
    a0 = 1.0 + alpha / a
    a1 = -2.0 * cosw
    a2 = 1.0 - alpha / a
    b = np.array([b0 / a0, b1 / a0, b2 / a0], dtype=np.float64)
    acoef = np.array([1.0, a1 / a0, a2 / a0], dtype=np.float64)
    return signal.lfilter(b, acoef, y, axis=0).astype(np.float32)


def rbj_shelf(y: np.ndarray, sr: int, freq: float, gain_db: float, high: bool, slope: float = 0.75) -> np.ndarray:
    a = 10.0 ** (gain_db / 40.0)
    w0 = 2.0 * math.pi * freq / sr
    cosw = math.cos(w0)
    sinw = math.sin(w0)
    alpha = sinw / 2.0 * math.sqrt((a + 1 / a) * (1 / slope - 1) + 2)
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
    b = np.array([b0 / a0, b1 / a0, b2 / a0], dtype=np.float64)
    acoef = np.array([1.0, a1 / a0, a2 / a0], dtype=np.float64)
    return signal.lfilter(b, acoef, y, axis=0).astype(np.float32)


def envelope(x: np.ndarray, sr: int, ms: float) -> np.ndarray:
    x = np.abs(x).astype(np.float32)
    coeff = math.exp(-1.0 / max(1.0, sr * ms / 1000.0))
    return signal.lfilter([1.0 - coeff], [1.0, -coeff], x).astype(np.float32)


def dynamic_band_tame(
    y: np.ndarray,
    sr: int,
    low: float,
    high: float,
    max_cut_db: float,
    percentile: float = 65.0,
    slope: float = 0.55,
    smooth_ms: float = 18.0,
) -> np.ndarray:
    band = butter_filter(y, sr, "bandpass", (low, high), order=3)
    env = envelope(np.mean(band, axis=1), sr, smooth_ms)
    env_db = amp_to_db(env)
    active = env_db[env_db > -90.0]
    threshold = float(np.percentile(active, percentile)) if len(active) else -60.0
    cut = np.minimum(max_cut_db, np.maximum(env_db - threshold, 0.0) * slope)
    gain = db_to_amp(-cut).astype(np.float32)
    return (y - band + band * gain[:, None]).astype(np.float32)


def sidechain_band_duck(
    target: np.ndarray,
    trigger: np.ndarray,
    sr: int,
    low: float,
    high: float,
    max_cut_db: float,
    percentile: float = 56.0,
    smooth_ms: float = 90.0,
) -> np.ndarray:
    band = butter_filter(target, sr, "bandpass", (low, high), order=3)
    trig_env = envelope(np.mean(np.abs(trigger), axis=1), sr, smooth_ms)
    trig_db = amp_to_db(trig_env)
    active = trig_db[trig_db > -90.0]
    threshold = float(np.percentile(active, percentile)) if len(active) else -60.0
    over = np.maximum(trig_db - threshold, 0.0)
    cut = np.minimum(max_cut_db, over * 0.35)
    gain = db_to_amp(-cut).astype(np.float32)
    return (target - band + band * gain[:, None]).astype(np.float32)


def compressor(
    y: np.ndarray,
    sr: int,
    threshold_db: float = -23.0,
    ratio: float = 1.7,
    attack_ms: float = 14.0,
    release_ms: float = 110.0,
    makeup_db: float = 0.0,
) -> np.ndarray:
    mono = np.mean(y, axis=1)
    env = envelope(mono, sr, attack_ms)
    level_db = amp_to_db(env)
    over = np.maximum(level_db - threshold_db, 0.0)
    reduction = over * (1.0 - 1.0 / ratio)
    smooth = max(1, int(sr * release_ms / 1000.0))
    if smooth > 1:
        reduction = np.convolve(reduction, np.ones(smooth, dtype=np.float32) / smooth, mode="same")
    gain = db_to_amp(-reduction + makeup_db).astype(np.float32)
    return (y * gain[:, None]).astype(np.float32)


def soft_saturation(y: np.ndarray, drive_db: float = 0.5, mix: float = 0.03) -> np.ndarray:
    drive = float(db_to_amp(drive_db))
    wet = np.tanh(y * drive) / max(np.tanh(drive), 1e-12)
    return (y * (1.0 - mix) + wet * mix).astype(np.float32)


def soft_clip(y: np.ndarray, ceiling: float = 0.96) -> np.ndarray:
    return (np.tanh(y / ceiling) * ceiling).astype(np.float32)


def spectral_denoise(y: np.ndarray, sr: int, reduction_db: float, percentile: float = 10.0) -> np.ndarray:
    min_gain = float(db_to_amp(-reduction_db))
    nperseg = 2048
    noverlap = 1536
    out = np.zeros_like(y, dtype=np.float32)
    for ch in range(y.shape[1]):
        _, _, zxx = signal.stft(
            y[:, ch],
            fs=sr,
            window="hann",
            nperseg=nperseg,
            noverlap=noverlap,
            boundary="zeros",
            padded=True,
        )
        mag = np.abs(zxx).astype(np.float32)
        energy = np.mean(mag, axis=0)
        noise_frames = energy <= np.percentile(energy, percentile)
        if not np.any(noise_frames):
            noise_frames = np.ones_like(energy, dtype=bool)
        profile = np.median(mag[:, noise_frames], axis=1, keepdims=True) + 1e-9
        over = mag / (profile * 3.1)
        gate = np.clip((over - 0.32) / 0.68, 0.0, 1.0)
        gain = min_gain + (1.0 - min_gain) * gate
        _, rec = signal.istft(
            zxx * gain,
            fs=sr,
            window="hann",
            nperseg=nperseg,
            noverlap=noverlap,
            input_onesided=True,
            boundary=True,
        )
        if len(rec) < len(y):
            rec = np.pad(rec, (0, len(y) - len(rec)))
        out[:, ch] = rec[: len(y)]
    return out.astype(np.float32)


def equal_power_pan(mono: np.ndarray, pan: float) -> np.ndarray:
    angle = (float(np.clip(pan, -1.0, 1.0)) + 1.0) * math.pi / 4.0
    return np.column_stack([mono * math.cos(angle), mono * math.sin(angle)]).astype(np.float32)


def haas_layer(mono: np.ndarray, sr: int, pan: float, delay_ms: float) -> np.ndarray:
    base = equal_power_pan(mono, pan)
    delay = int(round(sr * delay_ms / 1000.0))
    if delay > 0:
        if pan < 0:
            base[delay:, 1] += mono[:-delay] * 0.16
        else:
            base[delay:, 0] += mono[:-delay] * 0.16
    return base.astype(np.float32)


def extract_source() -> dict[str, Path]:
    if not ZIP_SOURCE.exists():
        raise FileNotFoundError(ZIP_SOURCE)
    if not any(SOURCE.glob("*.wav")):
        with zipfile.ZipFile(ZIP_SOURCE) as archive:
            for member in archive.infolist():
                name = Path(member.filename)
                if member.is_dir() or "__MACOSX" in name.parts or name.name.startswith("._"):
                    continue
                if not name.name.lower().endswith(".wav"):
                    continue
                with archive.open(member) as src, (SOURCE / name.name).open("wb") as dst:
                    shutil.copyfileobj(src, dst)

    def stem(prefix: int) -> Path:
        matches = sorted(SOURCE.glob(f"{prefix} *.wav"))
        if not matches:
            raise FileNotFoundError(f"Missing stem prefix {prefix}")
        return matches[0]

    paths = {
        "full_reference": stem(0),
        "woodwinds": stem(1),
        "brass": stem(2),
        "fx": stem(3),
        "synth": stem(4),
        "strings": stem(5),
        "percussion": stem(6),
        "keyboard": stem(7),
        "guitar": stem(8),
        "bass": stem(9),
        "drums": stem(10),
        "backing_vocals": stem(11),
        "lead_vocal": stem(12),
        "female_vocal": stem(13),
    }
    (REPORTS / "source_selection.json").write_text(
        json.dumps({key: rel(path) for key, path in paths.items()}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return paths


def process_lead_vocal(y: np.ndarray, sr: int) -> np.ndarray:
    x = mono_center(y)
    x = peak_cap(x, -5.8)
    x = spectral_denoise(x, sr, reduction_db=2.2, percentile=10.0)
    x = butter_filter(x, sr, "highpass", 88, 2)
    x = dynamic_band_tame(x, sr, 175, 360, max_cut_db=2.6, percentile=58.0, slope=0.58, smooth_ms=28.0)
    x = rbj_peaking(x, sr, 245, -1.0, 0.95)
    x = dynamic_band_tame(x, sr, 420, 850, max_cut_db=1.7, percentile=64.0, slope=0.50, smooth_ms=22.0)
    x = rbj_peaking(x, sr, 620, -0.9, 1.05)
    x = rbj_peaking(x, sr, 2850, 1.28, 0.82)
    x = rbj_peaking(x, sr, 3800, 0.72, 0.85)
    x = dynamic_band_tame(x, sr, 3600, 5900, max_cut_db=1.0, percentile=77.0, slope=0.55, smooth_ms=7.0)
    x = dynamic_band_tame(x, sr, 6200, 9300, max_cut_db=3.2, percentile=55.0, slope=0.78, smooth_ms=6.0)
    x = rbj_shelf(x, sr, 10500, -0.15, high=True, slope=0.7)
    x = dynamic_band_tame(x, sr, 9800, 17500, max_cut_db=2.4, percentile=58.0, slope=0.68, smooth_ms=7.5)
    x = compressor(x, sr, threshold_db=-24.2, ratio=1.72, attack_ms=18.0, release_ms=112.0, makeup_db=0.55)
    density = compressor(x, sr, threshold_db=-29.0, ratio=2.35, attack_ms=5.0, release_ms=88.0, makeup_db=0.30)
    x = (x * 0.95 + density * 0.05).astype(np.float32)
    x = soft_saturation(x, drive_db=0.35, mix=0.018)
    x = match_active_rms(x, -19.2, max_gain_db=5.0)
    x = peak_cap(x, -4.0)
    return soft_clip(x, ceiling=0.975)


def process_female_layer(y: np.ndarray, sr: int, lead: np.ndarray, target_delta_db: float = -5.0) -> np.ndarray:
    x = mono_center(y)
    x = peak_cap(x, -5.8)
    x = spectral_denoise(x, sr, reduction_db=2.4, percentile=11.0)
    x = butter_filter(x, sr, "highpass", 118, 2)
    x = rbj_peaking(x, sr, 240, -1.8, 0.95)
    x = dynamic_band_tame(x, sr, 420, 900, max_cut_db=1.2, percentile=66.0, slope=0.50, smooth_ms=20.0)
    x = rbj_peaking(x, sr, 3000, 0.35, 0.9)
    x = dynamic_band_tame(x, sr, 5600, 9300, max_cut_db=3.8, percentile=55.0, slope=0.76, smooth_ms=6.0)
    x = dynamic_band_tame(x, sr, 9500, 16500, max_cut_db=2.6, percentile=60.0, slope=0.68, smooth_ms=8.0)
    x = compressor(x, sr, threshold_db=-24.0, ratio=1.5, attack_ms=15.0, release_ms=105.0, makeup_db=0.1)

    mono = np.mean(x, axis=1)
    left = haas_layer(mono, sr, pan=-0.58, delay_ms=11.0)
    right = haas_layer(mono, sr, pan=0.58, delay_ms=15.0)
    panned = (left * 0.50 + right * 0.50).astype(np.float32)
    lead_active = active_rms_db(lead)
    panned = match_active_rms(panned, lead_active + target_delta_db, max_gain_db=18.0)
    panned = sidechain_band_duck(panned, lead, sr, 1800, 4600, max_cut_db=1.05, percentile=54.0, smooth_ms=115.0)
    return peak_cap(panned, -5.6)


def process_backing_vocals(y: np.ndarray, sr: int, lead: np.ndarray) -> np.ndarray:
    if float(amp_to_db(rms(y))) < -80.0:
        return y.astype(np.float32)
    x = mono_center(y)
    x = spectral_denoise(x, sr, reduction_db=1.7, percentile=12.0)
    x = butter_filter(x, sr, "highpass", 145, 2)
    x = rbj_peaking(x, sr, 260, -2.0, 1.0)
    x = dynamic_band_tame(x, sr, 5800, 9600, max_cut_db=3.0, percentile=58.0, smooth_ms=7.0)
    mono = np.mean(x, axis=1)
    panned = haas_layer(mono, sr, pan=-0.36, delay_ms=9.0) * 0.50 + haas_layer(mono, sr, pan=0.36, delay_ms=14.0) * 0.50
    panned = match_active_rms(panned, active_rms_db(lead) - 10.6, max_gain_db=18.0)
    panned = sidechain_band_duck(panned, lead, sr, 1800, 4500, max_cut_db=1.25, percentile=53.0, smooth_ms=130.0)
    return peak_cap(panned, -7.5)


def process_instrument(role: str, y: np.ndarray, sr: int, lead: np.ndarray) -> np.ndarray:
    if float(amp_to_db(rms(y))) < -80.0:
        return y.astype(np.float32)
    x = y.astype(np.float32)
    if role == "drums":
        x = butter_filter(x, sr, "highpass", 24, 2)
        x = rbj_peaking(x, sr, 70, 0.25, 0.85)
        x = rbj_peaking(x, sr, 235, -0.45, 1.0)
        x = rbj_peaking(x, sr, 3300, 0.35, 0.8)
        x = dynamic_band_tame(x, sr, 6600, 11500, max_cut_db=0.75, percentile=82.0, smooth_ms=8.0)
        x = compressor(x, sr, threshold_db=-20.0, ratio=1.18, attack_ms=14.0, release_ms=90.0, makeup_db=0.18)
        x = soft_saturation(x, drive_db=0.45, mix=0.025)
    elif role == "bass":
        x = mono_center(x)
        x = butter_filter(x, sr, "highpass", 26, 2)
        x = rbj_peaking(x, sr, 78, 0.45, 0.9)
        x = rbj_peaking(x, sr, 210, -0.55, 1.0)
        x = rbj_peaking(x, sr, 760, 0.45, 0.95)
        x = soft_saturation(x, drive_db=0.65, mix=0.04)
    elif role == "synth":
        x = butter_filter(x, sr, "highpass", 60, 2)
        x = rbj_peaking(x, sr, 310, -0.35, 1.0)
        x = rbj_peaking(x, sr, 1250, 0.35, 0.9)
        x = rbj_peaking(x, sr, 5200, -0.35, 0.85)
        x = sidechain_band_duck(x, lead, sr, 1600, 4500, max_cut_db=0.65, percentile=54.0, smooth_ms=100.0)
    elif role == "keyboard":
        x = butter_filter(x, sr, "highpass", 110, 2)
        x = rbj_peaking(x, sr, 320, -0.25, 1.0)
        x = rbj_peaking(x, sr, 950, 0.35, 0.9)
        x = rbj_peaking(x, sr, 3050, -0.45, 1.0)
        x = sidechain_band_duck(x, lead, sr, 1400, 4300, max_cut_db=0.85, percentile=53.0, smooth_ms=95.0)
    elif role == "fx":
        x = butter_filter(x, sr, "highpass", 95, 2)
        x = butter_filter(x, sr, "lowpass", 13500, 2)
        x = dynamic_band_tame(x, sr, 5600, 11500, max_cut_db=1.7, percentile=70.0, smooth_ms=10.0)
    else:
        x = butter_filter(x, sr, "highpass", 40, 2)
        x = dynamic_band_tame(x, sr, 5500, 12000, max_cut_db=0.8, percentile=75.0, smooth_ms=10.0)
    role_rms_offsets = {
        "woodwinds": 0.12,
        "brass": 0.12,
        "fx": -0.10,
        "synth": 0.22,
        "strings": 0.18,
        "percussion": 0.16,
        "keyboard": 0.20,
        "guitar": 0.18,
        "bass": 0.24,
        "drums": 0.28,
    }
    x = match_active_rms(x, active_rms_db(y) + role_rms_offsets.get(role, 0.14), max_gain_db=0.75)
    return peak_cap(x, -2.5)


def make_space(lead: np.ndarray, sr: int) -> tuple[np.ndarray, np.ndarray]:
    mono = np.mean(lead, axis=1)
    delay = np.zeros_like(lead)
    delay_samp = int(round(0.245 * sr))
    delayed = np.zeros_like(mono)
    delayed[delay_samp:] = mono[:-delay_samp]
    delay[:, 0] = delayed * float(db_to_amp(-17.5))
    d2 = int(round(0.012 * sr))
    delay[d2:, 1] = delayed[:-d2] * float(db_to_amp(-18.0))
    delay = butter_filter(delay, sr, "highpass", 280, 2)
    delay = butter_filter(delay, sr, "lowpass", 6500, 2)

    reverb = np.zeros_like(lead)
    taps = [(0.042, -24.5), (0.069, -27.5), (0.112, -31.0), (0.178, -34.0)]
    for seconds, gain_db in taps:
        d = int(round(seconds * sr))
        tap = np.zeros_like(mono)
        tap[d:] = mono[:-d]
        reverb[:, 0] += tap * float(db_to_amp(gain_db))
        d_side = int(round(0.006 * sr))
        reverb[d_side:, 1] += tap[:-d_side] * float(db_to_amp(gain_db - 0.4))
    reverb = butter_filter(reverb, sr, "highpass", 320, 2)
    reverb = butter_filter(reverb, sr, "lowpass", 7600, 2)
    return reverb.astype(np.float32), delay.astype(np.float32)


def write_processed(paths: dict[str, Path]) -> tuple[dict[str, Path], int, float, dict[str, float]]:
    sr, ref, _ = read_wav(paths["full_reference"])
    length = len(ref)
    sr_lead, lead_raw, _ = read_wav(paths["lead_vocal"])
    if sr_lead != sr:
        raise RuntimeError("Sample-rate mismatch")
    lead_raw = pad_or_trim(lead_raw, length)
    lead = process_lead_vocal(lead_raw, sr)

    processed: dict[str, Path] = {
        "full_reference": PROCESSED / "source_full_mix_reference.wav",
        "lead_raw_center": PROCESSED / "lead_vocal_raw_center_reference.wav",
        "lead_vocal": PROCESSED / "lead_vocal_clean_center.wav",
    }
    write_wav(processed["full_reference"], sr, ref)
    write_wav(processed["lead_raw_center"], sr, mono_center(lead_raw))
    write_wav(processed["lead_vocal"], sr, lead)

    _, female_raw, _ = read_wav(paths["female_vocal"])
    female = process_female_layer(pad_or_trim(female_raw, length), sr, lead, target_delta_db=FEMALE_TARGET_DELTA_DB)
    processed["female_vocal"] = PROCESSED / FEMALE_LAYER_FILENAME
    write_wav(processed["female_vocal"], sr, female)

    _, backing_raw, _ = read_wav(paths["backing_vocals"])
    backing = process_backing_vocals(pad_or_trim(backing_raw, length), sr, lead)
    processed["backing_vocals"] = PROCESSED / "backing_vocals_tucked_panned.wav"
    write_wav(processed["backing_vocals"], sr, backing)

    for role in (
        "woodwinds",
        "brass",
        "fx",
        "synth",
        "strings",
        "percussion",
        "keyboard",
        "guitar",
        "bass",
        "drums",
    ):
        stem_sr, raw, _ = read_wav(paths[role])
        if stem_sr != sr:
            raise RuntimeError(f"Sample-rate mismatch for {role}")
        out = process_instrument(role, pad_or_trim(raw, length), sr, lead)
        processed[role] = PROCESSED / f"{role}_processed.wav"
        write_wav(processed[role], sr, out)

    reverb, delay = make_space(lead, sr)
    processed["vocal_reverb"] = PROCESSED / "vocal_reverb_print_tucked.wav"
    processed["vocal_delay"] = PROCESSED / "vocal_delay_print_tucked.wav"
    write_wav(processed["vocal_reverb"], sr, reverb)
    write_wav(processed["vocal_delay"], sr, delay)

    vocal_solo = lead + female + backing * float(db_to_amp(-1.2)) + reverb + delay
    vocal_solo = peak_cap(vocal_solo, -1.5)
    write_wav(VOCAL_SOLO, sr, vocal_solo)

    deltas = {
        "lead_active_rms_db": round(active_rms_db(lead), 2),
        "female_layer_active_rms_db": round(active_rms_db(female), 2),
        "female_vs_lead_db": round(active_rms_db(female) - active_rms_db(lead), 2),
    }
    return processed, sr, length / sr, deltas


def spectral_balance(y: np.ndarray, sr: int) -> dict[str, float]:
    mono = np.mean(y, axis=1)
    nperseg = min(32768, max(4096, len(mono) // 8))
    freq, power = signal.welch(mono, fs=sr, nperseg=nperseg)
    total = 1e-30
    values: dict[str, float] = {}
    for key, (low, high) in BANDS.items():
        mask = (freq >= low) & (freq < high)
        value = float(np.trapezoid(power[mask], freq[mask])) if mask.any() else 0.0
        values[key] = value
        total += value
    return {f"{key}_pct": round(value * 100.0 / total, 3) for key, value in values.items()}


def ebur128(path: Path) -> dict[str, float | None]:
    proc = subprocess.run(
        [
            FFMPEG,
            "-hide_banner",
            "-nostats",
            "-loglevel",
            "verbose",
            "-i",
            str(path),
            "-filter_complex",
            "ebur128=peak=true:framelog=verbose",
            "-f",
            "null",
            "-",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
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
    sr, y, dtype_name = read_wav(path)
    left, right = y[:, 0], y[:, 1]
    corr = float(np.corrcoef(left, right)[0, 1]) if np.std(left) > 1e-8 and np.std(right) > 1e-8 else 1.0
    mid = (left + right) * 0.5
    side = (left - right) * 0.5
    row: dict[str, Any] = {
        "label": label,
        "file": rel(path),
        "duration_s": round(len(y) / sr, 3),
        "sample_rate": sr,
        "dtype": dtype_name,
        "peak_dbfs": round(float(amp_to_db(peak(y))), 2),
        "rms_dbfs": round(float(amp_to_db(rms(y))), 2),
        "active_rms_dbfs": round(active_rms_db(y), 2),
        "stereo_corr": round(corr, 4),
        "side_mid_db": round(float(amp_to_db(rms(side) / (rms(mid) + 1e-12))), 2),
    }
    row.update(spectral_balance(y, sr))
    row.update(ebur128(path))
    return row


def lua_path(path: Path) -> str:
    return str(path).replace("\\", "/")


def write_reaper_scripts(processed: dict[str, Path], duration: float) -> None:
    track_plan = [
        ("SOURCE full mix reference muted", "full_reference", -99.0, 0.0, True, "reference", []),
        ("01 Woodwinds retained processed", "woodwinds", 0.1, -0.18, False, "woodwinds", ["VST: ReaEQ (Cockos)"]),
        ("02 Brass retained processed", "brass", 0.1, 0.16, False, "brass", ["VST: ReaEQ (Cockos)"]),
        ("03 FX filtered support", "fx", -4.9, 0.18, False, "fx", ["VST: ReaEQ (Cockos)"]),
        ("04 Synth vocal pocket", "synth", -0.55, -0.08, False, "synth", ["VST3: TDR Nova (Tokyo Dawn Labs)", "VST: ReaEQ (Cockos)"]),
        ("05 Strings retained processed", "strings", 0.15, 0.12, False, "strings", ["VST: ReaEQ (Cockos)"]),
        ("06 Percussion retained processed", "percussion", 0.12, 0.0, False, "percussion", ["VST: ReaEQ (Cockos)"]),
        ("07 Keyboard vocal pocket", "keyboard", -0.95, 0.08, False, "keyboard", ["VST3: TDR Nova (Tokyo Dawn Labs)", "VST: ReaEQ (Cockos)"]),
        ("08 Guitar retained processed", "guitar", -0.35, -0.12, False, "guitar", ["VST: ReaEQ (Cockos)"]),
        ("09 Bass mono body", "bass", 0.35, 0.0, False, "bass", ["VST: ReaEQ (Cockos)"]),
        ("10 Drums transient balanced", "drums", -0.35, 0.0, False, "drums", ["VST: ReaEQ (Cockos)"]),
        ("11 Backing vocals tucked panned", "backing_vocals", -3.8, 0.0, False, "backing_vocals", ["JS: Codex Vocal AI Artifact Split Tamer", "VST: ReaEQ (Cockos)", "JS: De-esser"]),
        ("12 Lead vocal clean center", "lead_vocal", 0.65, 0.0, False, "lead_vocal", ["JS: Codex Vocal AI Artifact Split Tamer", "VST: ReaEQ (Cockos)", "VST3: TDR Nova (Tokyo Dawn Labs)", "JS: De-esser", "VST: ReaComp (Cockos)", "JS: Codex Vocal AI Artifact Split Tamer", "VST: ReaLimit (Cockos)"]),
        (FEMALE_TRACK_NAME, "female_vocal", -1.4, 0.0, False, "female_side_vocal", ["JS: Codex Vocal AI Artifact Split Tamer", "VST: ReaEQ (Cockos)", "JS: De-esser"]),
        ("Vocal reverb print dark", "vocal_reverb", -2.4, 0.0, False, "vocal_reverb", ["VST: ReaEQ (Cockos)"]),
        ("Vocal delay print dark", "vocal_delay", -2.6, 0.0, False, "vocal_delay", ["VST: ReaEQ (Cockos)"]),
    ]
    def lua_long_string(value: str) -> str:
        return "[[" + value.replace("]", "] ]") + "]]"

    def lua_array(values: list[str]) -> str:
        return "{" + ", ".join(lua_long_string(value) for value in values) + "}"

    lua_tracks = "{\n" + "\n".join(
        "  {"
        + f"name={lua_long_string(name)}, "
        + f"path={lua_long_string(lua_path(processed[key]))}, "
        + f"volume_db={volume:.6f}, "
        + f"pan={pan:.6f}, "
        + f"muted={'true' if muted else 'false'}, "
        + f"trace_label={lua_long_string(trace_label)}, "
        + f"fx={lua_array(fx)}"
        + "},"
        for name, key, volume, pan, muted, trace_label, fx in track_plan
    ) + "\n}"
    build = f'''
local rpp = [[{lua_path(RPP)}]]
local render_dir = [[{lua_path(RENDERS)}]]
local trace_path = [[{lua_path(TRACE_JSON)}]]
local log_path = [[{lua_path(REPORTS / "build_reaper.log")}]]
local duration = {duration:.9f}
local tracks = {lua_tracks}
local rows = {{}}
local function lin(db) return 10 ^ ((db or 0) / 20) end
local function esc(s) s=tostring(s or ""); return s:gsub("\\\\","\\\\\\\\"):gsub('"','\\\\"'):gsub("\\n","\\\\n") end
local function q(s) return string.format("%q", s) end
local function log(s) local f=io.open(log_path,"a"); if f then f:write(os.date("%F %T")," ",tostring(s),"\\n"); f:close() end end
local function add_row(track, stage, status, plugin, fx_index, wet, reason)
  rows[#rows+1] = string.format('{{"track":"%s","stage":"%s","status":"%s","plugin":"%s","fx_index":%d,"wet":%s,"reason":"%s"}}', esc(track), esc(stage), esc(status), esc(plugin), tonumber(fx_index or -1), wet and tostring(wet) or "null", esc(reason))
  log(track .. " | " .. stage .. " | " .. status .. " | " .. tostring(plugin))
end
local function write_trace()
  local f = assert(io.open(trace_path, "w"))
  f:write('{{\\n  "slug": "{SLUG}",\\n  "rows": [\\n')
  for i,row in ipairs(rows) do f:write("    " .. row .. (i == #rows and "\\n" or ",\\n")) end
  f:write("  ]\\n}}\\n")
  f:close()
end
local function make_track(spec)
  local idx = reaper.CountTracks(0)
  reaper.InsertTrackAtIndex(idx, true)
  local tr = reaper.GetTrack(0, idx)
  reaper.GetSetMediaTrackInfo_String(tr, "P_NAME", spec.name, true)
  reaper.SetMediaTrackInfo_Value(tr, "D_VOL", lin(spec.volume_db or 0))
  reaper.SetMediaTrackInfo_Value(tr, "D_PAN", spec.pan or 0)
  reaper.SetMediaTrackInfo_Value(tr, "B_MUTE", spec.muted and 1 or 0)
  return tr
end
local function insert_media(tr, path)
  local src = reaper.PCM_Source_CreateFromFile(path)
  if not src then error("source failed: " .. path) end
  local item = reaper.AddMediaItemToTrack(tr)
  local take = reaper.AddTakeToMediaItem(item)
  reaper.SetMediaItemTake_Source(take, src)
  reaper.SetMediaItemInfo_Value(item, "D_POSITION", 0)
  reaper.SetMediaItemInfo_Value(item, "D_LENGTH", duration)
end
local function add_fx(tr, label, plugin, fx_order)
  local idx = reaper.TrackFX_AddByName(tr, plugin, false, -1)
  if idx and idx >= 0 then
    add_row(label, fx_order == 1 and "first-slot cleanup/processing" or "mix processing", "loaded", plugin, idx, 1.0, "")
    return idx
  end
  add_row(label, fx_order == 1 and "first-slot cleanup/processing" or "mix processing", "missing", plugin, -1, 1.0, "")
  if label == "lead_vocal" and fx_order == 1 then write_trace(); error("required first-slot Codex vocal artifact tamer missing") end
  return -1
end
os.execute("mkdir -p " .. q(render_dir))
os.execute("mkdir -p " .. q([[{lua_path(REPORTS)}]]))
os.remove(log_path)
os.remove(trace_path)
reaper.Main_OnCommand(40023, 0)
for _,spec in ipairs(tracks) do
  local tr = make_track(spec)
  insert_media(tr, spec.path)
  for i,plugin in ipairs(spec.fx) do
    add_fx(tr, spec.trace_label, plugin, i)
  end
end
local master = reaper.GetMasterTrack(0)
local master_fx = {{"VST: ReaEQ (Cockos)", "VST3: TDR Nova (Tokyo Dawn Labs)", "VST: ReaLimit (Cockos)"}}
for i,plugin in ipairs(master_fx) do
  local idx = reaper.TrackFX_AddByName(master, plugin, false, -1)
  if idx and idx >= 0 then add_row("master", "master bus clean guard", "loaded", plugin, idx, 1.0, "") else add_row("master", "master bus clean guard", "missing", plugin, -1, 1.0, "") end
end
reaper.GetSetProjectInfo(0, "RENDER_SETTINGS", 0, true)
reaper.GetSetProjectInfo(0, "RENDER_BOUNDSFLAG", 2, true)
reaper.GetSetProjectInfo(0, "RENDER_SRATE", 48000, true)
reaper.GetSetProjectInfo(0, "RENDER_CHANNELS", 2, true)
reaper.GetSetProjectInfo(0, "RENDER_STARTPOS", 0, true)
reaper.GetSetProjectInfo(0, "RENDER_ENDPOS", duration, true)
reaper.GetSetProjectInfo_String(0, "RENDER_FILE", render_dir, true)
reaper.GetSetProjectInfo_String(0, "RENDER_PATTERN", "sonyeo_luka_v01_REAPERPRINT_24-48", true)
reaper.GetSetProjectInfo_String(0, "RENDER_FORMAT", "evaw", true)
reaper.GetSetProjectInfo_String(0, "PROJECT_NOTES", [[{PROJECT_NOTES}]], true)
reaper.Main_SaveProjectEx(0, rpp, 0)
write_trace()
log("wrapper ok")
reaper.defer(function() reaper.Main_OnCommand(40004, 0) end)
'''
    render = f'''
local rpp = [[{lua_path(RPP)}]]
local log_path = [[{lua_path(REPORTS / "render_prepare.log")}]]
local function log(s) local f=io.open(log_path,"a"); if f then f:write(os.date("%F %T")," ",tostring(s),"\\n"); f:close() end end
os.remove(log_path)
local ok, err = xpcall(function()
  reaper.Main_openProject(rpp)
  reaper.GetSetProjectInfo_String(0, "RENDER_FILE", [[{lua_path(RENDERS)}]], true)
  reaper.GetSetProjectInfo_String(0, "RENDER_PATTERN", "sonyeo_luka_v01_REAPERPRINT_24-48", true)
  reaper.Main_SaveProjectEx(0, rpp, 0)
  log("wrapper ok")
end, debug.traceback)
if not ok then log("wrapper error: " .. tostring(err)) end
reaper.defer(function() reaper.Main_OnCommand(40004, 0) end)
'''
    BUILD_LUA.write_text(build, encoding="utf-8")
    RUN_BUILD_LUA.write_text(f"dofile([[{lua_path(BUILD_LUA)}]])\n", encoding="utf-8")
    RENDER_LUA.write_text(render, encoding="utf-8")
    RUN_RENDER_LUA.write_text(f"dofile([[{lua_path(RENDER_LUA)}]])\n", encoding="utf-8")


def run_reaper() -> None:
    if not REAPER_BIN.exists():
        raise FileNotFoundError(REAPER_BIN)
    REAPER_PRINT.unlink(missing_ok=True)
    subprocess.run([str(REAPER_BIN), "-newinst", "-nosplash", str(RUN_BUILD_LUA)], check=True)
    build_log = REPORTS / "build_reaper.log"
    if "wrapper ok" not in build_log.read_text(encoding="utf-8", errors="ignore"):
        raise RuntimeError(f"REAPER build wrapper failed: {build_log}")
    subprocess.run([str(REAPER_BIN), "-newinst", "-nosplash", str(RUN_RENDER_LUA)], check=True)
    render_log = REPORTS / "render_prepare.log"
    if "wrapper ok" not in render_log.read_text(encoding="utf-8", errors="ignore"):
        raise RuntimeError(f"REAPER render wrapper failed: {render_log}")
    subprocess.run([str(REAPER_BIN), "-newinst", "-nosplash", "-renderproject", str(RPP)], check=True)
    if not REAPER_PRINT.exists():
        matches = sorted(RENDERS.glob("sonyeo_luka_v01_REAPERPRINT_24-48*.wav"))
        if matches:
            matches[-1].rename(REAPER_PRINT)
    if not REAPER_PRINT.exists():
        raise FileNotFoundError(REAPER_PRINT)


def run_gate() -> dict[str, Any]:
    proc = subprocess.run(
        ["python3", "tools/validate_reaper_vocal_chain_gate.py", "--trace", rel(TRACE_JSON)],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    payload = json.loads(proc.stdout)
    (REPORTS / "vocal_chain_gate.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if proc.returncode != 0:
        raise RuntimeError(proc.stdout + proc.stderr)
    return payload


def final_master() -> None:
    filter_graph = (
        "highpass=f=24,"
        "equalizer=f=280:t=q:w=1:g=-0.20,"
        "equalizer=f=3200:t=q:w=0.9:g=0.20,"
        "equalizer=f=11800:t=q:w=0.8:g=-0.25,"
        "loudnorm=I=-10.8:TP=-1.15:LRA=3.8:linear=false,"
        "alimiter=limit=0.84:attack=2:release=80:level=false"
    )
    subprocess.run(
        [
            FFMPEG,
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(REAPER_PRINT),
            "-af",
            filter_graph,
            "-ar",
            "48000",
            "-c:a",
            "pcm_s24le",
            str(FINAL_WAV),
        ],
        check=True,
    )
    subprocess.run(
        [FFMPEG, "-y", "-hide_banner", "-loglevel", "error", "-i", str(FINAL_WAV), "-c:a", "libmp3lame", "-b:a", "320k", str(FINAL_MP3)],
        check=True,
    )


def write_ab_preview(source_ref: Path) -> None:
    temp = REPORTS / "_ab_preview"
    temp.mkdir(parents=True, exist_ok=True)
    before = temp / "before.wav"
    after = temp / "after.wav"
    concat = temp / "concat.txt"
    subprocess.run([FFMPEG, "-y", "-hide_banner", "-loglevel", "error", "-ss", "45", "-t", "28", "-i", str(source_ref), "-c:a", "pcm_s16le", str(before)], check=True)
    subprocess.run([FFMPEG, "-y", "-hide_banner", "-loglevel", "error", "-ss", "45", "-t", "28", "-i", str(FINAL_WAV), "-c:a", "pcm_s16le", str(after)], check=True)
    concat.write_text(f"file '{before}'\nfile '{after}'\n", encoding="utf-8")
    subprocess.run([FFMPEG, "-y", "-hide_banner", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(concat), "-c:a", "libmp3lame", "-b:a", "320k", str(AB_PREVIEW_MP3)], check=True)
    shutil.rmtree(temp, ignore_errors=True)


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


def write_trace_md() -> None:
    payload = json.loads(TRACE_JSON.read_text(encoding="utf-8"))
    lines = ["# Actual REAPER Plugin Trace", "", "| track | fx | status | plugin | stage |", "| --- | ---: | --- | --- | --- |"]
    for row in payload.get("rows", []):
        lines.append(f"| {row.get('track')} | {row.get('fx_index')} | {row.get('status')} | {row.get('plugin')} | {row.get('stage')} |")
    TRACE_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_reports(paths: dict[str, Path], processed: dict[str, Path], vocal_balance: dict[str, float], gate: dict[str, Any]) -> None:
    rows = [
        audio_metrics(paths["full_reference"], "source_full_reference"),
        audio_metrics(paths["lead_vocal"], "raw_12_lead_vocal"),
        audio_metrics(paths["female_vocal"], "raw_13_female_vocal"),
        audio_metrics(processed["lead_vocal"], "processed_main_vocal"),
        audio_metrics(processed["female_vocal"], "processed_female_layer"),
        audio_metrics(VOCAL_SOLO, "processed_vocal_solo"),
        audio_metrics(REAPER_PRINT, "reaper_print"),
        audio_metrics(FINAL_WAV, "final_master_wav"),
        audio_metrics(FINAL_MP3, "final_master_mp3"),
    ]
    write_csv(REPORTS / "qc_metrics.csv", rows)
    (REPORTS / "qc_metrics.json").write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    source, final, mp3 = rows[0], rows[7], rows[8]
    qc = {
        "passed": bool(gate.get("passed")) and (final.get("true_peak_dbfs") or 99) <= -0.8 and (mp3.get("true_peak_dbfs") or 99) <= -0.2,
        "gate": gate,
        "vocal_balance": vocal_balance,
        "source_lufs": source.get("integrated_lufs"),
        "final_lufs": final.get("integrated_lufs"),
        "final_true_peak_dbfs": final.get("true_peak_dbfs"),
        "mp3_true_peak_dbfs": mp3.get("true_peak_dbfs"),
    }
    (REPORTS / "qc_summary.json").write_text(json.dumps(qc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    notes = [
        f"# {REPORT_TITLE}",
        "",
        "## Intent",
        "",
        "- Keep the source full-mix feeling instead of over-crushing the master.",
        "- Use `12 Vocals.wav` as the centered main vocal.",
        FEMALE_REPORT_LINE,
        "- Keep the original beat stem balance readable while carving vocal pockets stem by stem.",
        "- Use the developed `JS: Codex Vocal AI Artifact Split Tamer` as the first main-vocal FX slot.",
        "",
        "## Deliverables",
        "",
        f"- Final WAV: `{rel(FINAL_WAV)}`",
        f"- Final MP3: `{rel(FINAL_MP3)}`",
        f"- Vocal solo check: `{rel(VOCAL_SOLO)}`",
        f"- Original-to-master A/B MP3: `{rel(AB_PREVIEW_MP3)}`",
        f"- REAPER project: `{rel(RPP)}`",
        "",
        "## QC",
        "",
        f"- Source loudness: `{source.get('integrated_lufs')}` LUFS / TP `{source.get('true_peak_dbfs')}` dBFS",
        f"- Final WAV loudness: `{final.get('integrated_lufs')}` LUFS / TP `{final.get('true_peak_dbfs')}` dBFS",
        f"- Final MP3 true peak: `{mp3.get('true_peak_dbfs')}` dBFS",
        f"- Vocal gate passed: `{gate.get('passed')}`",
        f"- Female layer vs lead active RMS: `{vocal_balance.get('female_vs_lead_db')}` dB",
        "",
        "## Notes",
        "",
        "- Near-silent stems such as woodwinds/brass/strings/percussion/guitar were retained as tracks so the stem layout remains intact.",
        "- No pitch/tune inserts were used on the main vocal.",
        "- The original full mix is present only as a muted reference track, not routed into the master.",
        "- This is measured/rendered QC, but final headphone A/B acceptance is still the listening gate.",
    ]
    (REPORTS / REPORT_FILENAME).write_text("\n".join(notes) + "\n", encoding="utf-8")


def build_zip() -> None:
    DELIVERABLE_ZIP.unlink(missing_ok=True)
    files = [
        FINAL_WAV,
        FINAL_MP3,
        VOCAL_SOLO,
        AB_PREVIEW_MP3,
        REAPER_PRINT,
        RPP,
        BUILD_LUA,
        RENDER_LUA,
        TRACE_JSON,
        TRACE_MD,
        REPORTS / "vocal_chain_gate.json",
        REPORTS / "qc_metrics.json",
        REPORTS / "qc_metrics.csv",
        REPORTS / "qc_summary.json",
        REPORTS / "source_selection.json",
        REPORTS / REPORT_FILENAME,
    ]
    with zipfile.ZipFile(DELIVERABLE_ZIP, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        seen: set[Path] = set()
        for path in files:
            if path.exists() and path not in seen:
                archive.write(path, path.relative_to(ROOT).as_posix())
                seen.add(path)


def main() -> int:
    ensure_dirs()
    paths = extract_source()
    processed, _sr, duration, vocal_balance = write_processed(paths)
    write_reaper_scripts(processed, duration)
    run_reaper()
    write_trace_md()
    gate = run_gate()
    final_master()
    write_ab_preview(paths["full_reference"])
    write_reports(paths, processed, vocal_balance, gate)
    build_zip()
    final = audio_metrics(FINAL_WAV, "final")
    print(
        json.dumps(
            {
                "final_wav": rel(FINAL_WAV),
                "final_mp3": rel(FINAL_MP3),
                "deliverable_zip": rel(DELIVERABLE_ZIP),
                "reaper_project": rel(RPP),
                "trace": rel(TRACE_JSON),
                "duration_s": final["duration_s"],
                "lufs": final.get("integrated_lufs"),
                "true_peak_dbfs": final.get("true_peak_dbfs"),
                "female_vs_lead_db": vocal_balance.get("female_vs_lead_db"),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

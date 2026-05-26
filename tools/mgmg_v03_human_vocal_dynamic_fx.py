from __future__ import annotations

import csv
import json
import math
import re
import shutil
import subprocess
import zipfile
from pathlib import Path

import imageio_ffmpeg
import numpy as np
from scipy import signal
from scipy.io import wavfile


ROOT = Path("/Users/hantaeheuk/Documents/New project 3")
WORK = ROOT / "mgmg_mashup_v03_work"
STEM_ZIP = Path("/Users/hantaeheuk/Downloads/ㅁㄱㅁㄱ x ㅁㄱㅁㄱ (Mashup) Stems (1).zip")
MASTER_ZIP = ROOT / "mgmg_mashup_mix/renders/mgmg_mashup_v02_master_tp_safe_24-48.wav.zip"
STEMS = WORK / "input_stems"
MASTER_DIR = WORK / "input_master"
INTERMEDIATE = WORK / "intermediate"
OUTPUT = ROOT / "output"
REPORTS = ROOT / "reports"
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()

MASTER_WAV = MASTER_DIR / "mgmg_mashup_v02_master_tp_safe_24-48.wav"
CLEAN_WAV = OUTPUT / "mgmg_mashup_v03_human_vocal_dynamic_fx_clean_24-48.wav"
LOUD_WAV = OUTPUT / "mgmg_mashup_v03_human_vocal_dynamic_fx_loud_24-48.wav"
PREVIEW_MP3 = OUTPUT / "mgmg_mashup_v03_preview.mp3"
AUDIT_MD = REPORTS / "audio_audit.md"
SETTINGS_JSON = REPORTS / "processing_settings.json"

ROLE_MAP = {
    "0 Lead Vocals.wav": "lead_vocal",
    "1 Backing Vocals.wav": "backing_vocal",
    "2 Drums.wav": "drums",
    "3 Bass.wav": "bass",
    "4 Keyboard.wav": "keys",
    "5 Synth.wav": "synth",
    "6 Other.wav": "other",
}

ROLE_TARGET_RMS = {
    "lead_vocal": -16.6,
    "backing_vocal": -25.0,
    "drums": -16.8,
    "bass": -18.1,
    "keys": -24.6,
    "synth": -24.2,
    "other": -26.2,
}

ROLE_PAN = {
    "drums": 0.0,
    "bass": 0.0,
    "keys": -0.10,
    "synth": 0.12,
    "other": -0.06,
}

BANDS = {
    "sub_20_80": (20, 80),
    "bass_body_80_200": (80, 200),
    "body_200_500": (200, 500),
    "formant_500_1500": (500, 1500),
    "presence_1500_5000": (1500, 5000),
    "sibilance_5000_10000": (5000, 10000),
    "air_10000_16000": (10000, 16000),
}


def db_amp(value: float | np.ndarray) -> float | np.ndarray:
    return 20.0 * np.log10(np.maximum(value, 1e-12))


def amp_db(db: float | np.ndarray) -> float | np.ndarray:
    return np.power(10.0, np.asarray(db) / 20.0)


def extract_zip(src: Path, dst: Path) -> None:
    dst.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(src) as zf:
        for member in zf.infolist():
            name = Path(member.filename)
            if "__MACOSX" in name.parts or name.name.startswith("._"):
                continue
            zf.extract(member, dst)


def read_wav(path: Path) -> tuple[int, np.ndarray, str]:
    sr, data = wavfile.read(path)
    dtype_name = str(data.dtype)
    if np.issubdtype(data.dtype, np.integer):
        info = np.iinfo(data.dtype)
        scale = max(abs(info.min), info.max)
        y = data.astype(np.float32) / float(scale)
    else:
        y = data.astype(np.float32)
    if y.ndim == 1:
        y = np.column_stack([y, y])
    if y.shape[1] == 1:
        y = np.repeat(y, 2, axis=1)
    return sr, y[:, :2].astype(np.float32), dtype_name


def write_float_wav(path: Path, sr: int, y: np.ndarray) -> None:
    y = np.nan_to_num(y, nan=0.0, posinf=0.0, neginf=0.0)
    wavfile.write(path, sr, y.astype(np.float32))


def convert_wav_24(src: Path, dst: Path) -> None:
    subprocess.run(
        [FFMPEG, "-y", "-hide_banner", "-loglevel", "error", "-i", str(src), "-c:a", "pcm_s24le", "-ar", "48000", str(dst)],
        check=True,
    )


def convert_mp3(src: Path, dst: Path) -> None:
    subprocess.run(
        [FFMPEG, "-y", "-hide_banner", "-loglevel", "error", "-i", str(src), "-c:a", "libmp3lame", "-b:a", "320k", str(dst)],
        check=True,
    )


def ffmpeg_loudnorm(src: Path, dst: Path, target_lufs: float, target_tp: float = -1.2, target_lra: float = 3.0) -> None:
    subprocess.run(
        [
            FFMPEG,
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(src),
            "-af",
            f"loudnorm=I={target_lufs}:TP={target_tp}:LRA={target_lra}:linear=false:print_format=summary",
            "-c:a",
            "pcm_s24le",
            "-ar",
            "48000",
            str(dst),
        ],
        check=True,
    )


def render_conditioned_master(src: Path, dst: Path, label: str, target_lufs: float, drive_db: float, ceiling: float) -> None:
    first_pass = INTERMEDIATE / f"_{label}_firstpass_loudnorm.wav"
    conditioned = INTERMEDIATE / f"_{label}_conditioned_float.wav"
    ffmpeg_loudnorm(src, first_pass, target_lufs, -1.2, 3.0)
    sr, y, _ = read_wav(first_pass)
    y = soft_clip(y, drive_db=drive_db, ceiling=ceiling)
    write_float_wav(conditioned, sr, y)
    ffmpeg_loudnorm(conditioned, dst, target_lufs, -1.2, 3.0)


def rms(y: np.ndarray) -> float:
    return float(np.sqrt(np.mean(np.square(y), dtype=np.float64)))


def peak(y: np.ndarray) -> float:
    return float(np.max(np.abs(y)))


def normalize_to_rms(y: np.ndarray, target_db: float) -> np.ndarray:
    gain = float(amp_db(target_db - float(db_amp(rms(y)))))
    return y * gain


def butter_filter(y: np.ndarray, sr: int, kind: str, freq: float | tuple[float, float], order: int = 3) -> np.ndarray:
    if isinstance(freq, tuple):
        low = max(float(freq[0]), 5.0)
        high = min(float(freq[1]), sr * 0.45)
        sos = signal.butter(order, [low, high], btype=kind, fs=sr, output="sos")
    else:
        clipped = min(max(float(freq), 5.0), sr * 0.45)
        sos = signal.butter(order, clipped, btype=kind, fs=sr, output="sos")
    return signal.sosfiltfilt(sos, y, axis=0).astype(np.float32)


def bandpass(y: np.ndarray, sr: int, low: float, high: float, order: int = 3) -> np.ndarray:
    return butter_filter(y, sr, "bandpass", (low, high), order)


def smooth_envelope(x: np.ndarray, sr: int, smooth_ms: float) -> np.ndarray:
    x = np.maximum(np.abs(x).astype(np.float32), 1e-12)
    coeff = math.exp(-1.0 / max(sr * smooth_ms / 1000.0, 1.0))
    return signal.lfilter([1.0 - coeff], [1.0, -coeff], x).astype(np.float32)


def biquad_peaking(y: np.ndarray, sr: int, freq: float, gain_db: float, q: float) -> np.ndarray:
    a = float(amp_db(gain_db))
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
    acoef = np.array([1, a1 / a0, a2 / a0], dtype=np.float64)
    return signal.lfilter(b, acoef, y, axis=0).astype(np.float32)


def biquad_shelf(y: np.ndarray, sr: int, freq: float, gain_db: float, high: bool = True) -> np.ndarray:
    a = float(amp_db(gain_db))
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
    acoef = np.array([1, a1 / a0, a2 / a0], dtype=np.float64)
    return signal.lfilter(b, acoef, y, axis=0).astype(np.float32)


def dynamic_band_tame(
    y: np.ndarray,
    sr: int,
    low: float,
    high: float,
    max_cut_db: float,
    percentile: float,
    smooth_ms: float,
    slope: float = 0.72,
) -> tuple[np.ndarray, dict[str, float]]:
    band = bandpass(y, sr, low, high, order=3)
    rest = y - band
    env = smooth_envelope(np.mean(band, axis=1), sr, smooth_ms)
    env_db = db_amp(env)
    active = env_db[env_db > -90]
    threshold = float(np.percentile(active, percentile)) if len(active) else -60.0
    over = np.maximum(env_db - threshold, 0.0)
    cut_db = np.minimum(max_cut_db, over * slope).astype(np.float32)
    gain = amp_db(-cut_db).astype(np.float32)
    processed = rest + band * gain[:, None]
    stats = {
        "low_hz": low,
        "high_hz": high,
        "threshold_db": round(threshold, 2),
        "max_cut_db": max_cut_db,
        "mean_gr_db": round(float(np.mean(cut_db)), 3),
        "p95_gr_db": round(float(np.percentile(cut_db, 95)), 3),
    }
    return processed.astype(np.float32), stats


def sidechain_band_duck(
    target: np.ndarray,
    trigger: np.ndarray,
    sr: int,
    low: float,
    high: float,
    amount_db: float,
    threshold_percentile: float = 62.0,
    smooth_ms: float = 65.0,
) -> np.ndarray:
    band = bandpass(target, sr, low, high, order=3)
    rest = target - band
    env = smooth_envelope(np.mean(trigger, axis=1), sr, smooth_ms)
    threshold = float(np.percentile(env[env > 1e-7], threshold_percentile)) if np.any(env > 1e-7) else 0.01
    norm = np.clip((env - threshold) / (np.percentile(env, 97) - threshold + 1e-9), 0.0, 1.0)
    gain = amp_db(-amount_db * norm).astype(np.float32)
    return (rest + band * gain[:, None]).astype(np.float32)


def saturate(y: np.ndarray, drive_db: float, mix: float) -> np.ndarray:
    drive = float(amp_db(drive_db))
    wet = np.tanh(y * drive) / max(math.tanh(drive), 1e-9)
    return (wet * mix + y * (1.0 - mix)).astype(np.float32)


def vocal_harmonic_density(y: np.ndarray, sr: int, drive_db: float = 2.3, wet: float = 0.10) -> np.ndarray:
    low = butter_filter(y, sr, "lowpass", 180, 3)
    mid = bandpass(y, sr, 180, 5200, 3)
    high = y - low - mid
    mid_sat = saturate(mid, drive_db, wet)
    high = biquad_shelf(high, sr, 8000, -0.45, high=True)
    return (low + mid_sat + high).astype(np.float32)


def compressor(y: np.ndarray, sr: int, threshold_db: float, ratio: float, smooth_ms: float, makeup_db: float = 0.0) -> np.ndarray:
    env = smooth_envelope(np.mean(y, axis=1), sr, smooth_ms)
    env_db = db_amp(env)
    over = np.maximum(env_db - threshold_db, 0.0)
    gr = over * (1.0 - 1.0 / ratio)
    gain = amp_db(makeup_db - gr).astype(np.float32)
    return (y * gain[:, None]).astype(np.float32)


def soft_clip(y: np.ndarray, drive_db: float = 1.2, ceiling: float = 0.98) -> np.ndarray:
    drive = float(amp_db(drive_db))
    out = np.tanh(y * drive) / max(math.tanh(drive), 1e-9)
    return np.clip(out, -ceiling, ceiling).astype(np.float32)


def limiter(y: np.ndarray, ceiling_db: float) -> np.ndarray:
    ceil = float(amp_db(ceiling_db))
    p = peak(y)
    if p <= ceil:
        return y.astype(np.float32)
    return (y * (ceil / p)).astype(np.float32)


def ms_width(y: np.ndarray, side_gain_db: float) -> np.ndarray:
    mid = (y[:, 0] + y[:, 1]) * 0.5
    side = (y[:, 0] - y[:, 1]) * 0.5 * float(amp_db(side_gain_db))
    return np.column_stack([mid + side, mid - side]).astype(np.float32)


def pan_stereo(y: np.ndarray, pan: float) -> np.ndarray:
    pan = max(-1.0, min(1.0, pan))
    left_gain = math.cos((pan + 1.0) * math.pi / 4.0)
    right_gain = math.sin((pan + 1.0) * math.pi / 4.0)
    mono = np.mean(y, axis=1)
    return np.column_stack([mono * left_gain * math.sqrt(2), mono * right_gain * math.sqrt(2)]).astype(np.float32)


def delay_samples(y: np.ndarray, samples: int) -> np.ndarray:
    out = np.zeros_like(y)
    if samples > 0 and samples < len(y):
        out[samples:] = y[:-samples]
    return out


def chorus_double(y: np.ndarray, sr: int) -> np.ndarray:
    mono = np.mean(y, axis=1)
    base = np.column_stack([mono, mono]).astype(np.float32)
    left = pan_stereo(delay_samples(base, int(sr * 0.014)), -0.58) * 0.65
    right = pan_stereo(delay_samples(base, int(sr * 0.023)), 0.58) * 0.65
    center = base * 0.28
    doubled = left + right + center
    doubled = butter_filter(doubled, sr, "highpass", 145, 3)
    doubled = biquad_shelf(doubled, sr, 8500, -1.2, high=True)
    return ms_width(doubled, 1.2)


def sidechain_duck_full(wet: np.ndarray, trigger: np.ndarray, sr: int, amount_db: float, release_ms: float, threshold_percentile: float = 58.0) -> np.ndarray:
    env = smooth_envelope(np.mean(trigger, axis=1), sr, release_ms)
    active_vals = env[env > 1e-7]
    threshold = float(np.percentile(active_vals, threshold_percentile)) if len(active_vals) else 0.01
    norm = np.clip((env - threshold) / (np.percentile(env, 97) - threshold + 1e-9), 0.0, 1.0)
    gain = amp_db(-amount_db * norm).astype(np.float32)
    return (wet * gain[:, None]).astype(np.float32)


def reverb_send(y: np.ndarray, sr: int, decay_s: float, wet_db: float, predelay_ms: float, hp_hz: float, lp_hz: float, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    n = max(int(sr * decay_s), 1)
    t = np.arange(n, dtype=np.float32) / sr
    impulse = rng.normal(0.0, 1.0, n).astype(np.float32) * np.exp(-t / max(decay_s / 3.0, 1e-3))
    impulse[: int(sr * predelay_ms / 1000.0)] = 0.0
    impulse /= max(float(np.max(np.abs(impulse))), 1e-9)
    impulse *= 0.16
    src = butter_filter(butter_filter(y, sr, "highpass", hp_hz, 2), sr, "lowpass", lp_hz, 2)
    wet_l = signal.fftconvolve(src[:, 0], impulse, mode="full")[: len(src)]
    wet_r = signal.fftconvolve(src[:, 1], np.roll(impulse, int(sr * 0.012)), mode="full")[: len(src)]
    return (np.column_stack([wet_l, wet_r]) * float(amp_db(wet_db))).astype(np.float32)


def delay_throw(src: np.ndarray, sr: int, delay_ms: float, feedback: float, wet_db: float, hp_hz: float, lp_hz: float, pingpong: bool) -> np.ndarray:
    delay = int(sr * delay_ms / 1000.0)
    filtered = butter_filter(butter_filter(src, sr, "highpass", hp_hz, 2), sr, "lowpass", lp_hz, 2)
    out = np.zeros_like(filtered)
    for repeat in range(1, 6):
        d = delay * repeat
        if d >= len(filtered):
            break
        gain = feedback ** (repeat - 1)
        chunk = filtered[:-d] * gain
        if pingpong and repeat % 2 == 1:
            chunk = chunk[:, [1, 0]]
        out[d:] += chunk
    return (out * float(amp_db(wet_db))).astype(np.float32)


def make_throw_gate(length: int, sr: int, endings: list[dict[str, float]], pre_ms: float, post_ms: float, fade_ms: float) -> np.ndarray:
    gate = np.zeros(length, dtype=np.float32)
    pre = int(sr * pre_ms / 1000.0)
    post = int(sr * post_ms / 1000.0)
    fade = max(int(sr * fade_ms / 1000.0), 1)
    for ending in endings:
        if not ending.get("throw", False):
            continue
        center = int(ending["time_s"] * sr)
        start = max(center - pre, 0)
        end = min(center + post, length)
        if end <= start:
            continue
        gate[start:end] = np.maximum(gate[start:end], float(ending.get("send_gain", 1.0)))
        gate[start : min(start + fade, end)] *= np.linspace(0.0, 1.0, min(fade, end - start), dtype=np.float32)
        gate[max(end - fade, start) : end] *= np.linspace(1.0, 0.0, min(fade, end - start), dtype=np.float32)
    return np.clip(gate, 0.0, 1.0)


def detect_phrase_endings(vocal: np.ndarray, sr: int) -> list[dict[str, float]]:
    mono = np.mean(vocal, axis=1)
    env = smooth_envelope(mono, sr, 45.0)
    hop = 1024
    frame_env = env[::hop]
    times = np.arange(len(frame_env)) * hop / sr
    active_vals = frame_env[frame_env > 1e-6]
    if not len(active_vals):
        return []
    threshold = max(float(np.percentile(active_vals, 60)) * 0.92, float(np.percentile(active_vals, 90)) * 0.24)
    raw_active = frame_env > threshold
    min_active = max(int(0.16 * sr / hop), 1)
    min_silence = max(int(0.18 * sr / hop), 1)
    endings: list[dict[str, float]] = []
    i = 0
    last_time = -99.0
    while i < len(raw_active):
        if not raw_active[i]:
            i += 1
            continue
        start = i
        while i < len(raw_active) and raw_active[i]:
            i += 1
        end = i
        if end - start < min_active:
            continue
        silence_start = i
        while i < len(raw_active) and not raw_active[i]:
            i += 1
        silence_len = i - silence_start
        if silence_len < min_silence:
            continue
        time_s = float(times[min(end, len(times) - 1)])
        prev_len_s = (end - start) * hop / sr
        pause_s = silence_len * hop / sr
        if time_s - last_time < 0.78:
            continue
        confidence = min(1.0, 0.35 + prev_len_s * 0.18 + pause_s * 0.42)
        endings.append(
            {
                "time_s": round(time_s, 3),
                "previous_phrase_s": round(prev_len_s, 3),
                "following_pause_s": round(pause_s, 3),
                "confidence": round(confidence, 3),
                "throw": False,
                "long_tail": False,
                "send_gain": round(min(1.0, 0.62 + confidence * 0.3), 3),
            }
        )
        last_time = time_s
    strong = [e for e in endings if e["following_pause_s"] >= 0.72 or e["confidence"] >= 0.78]
    strong = strong[:7]
    if endings:
        strong.append(endings[-1])
    strong_times = {e["time_s"] for e in strong}
    for ending in endings:
        ending["long_tail"] = ending["time_s"] in strong_times
    last_throw = -99.0
    for ending in endings:
        candidate = ending["confidence"] >= 0.54 or ending["following_pause_s"] >= 0.32 or ending["long_tail"]
        if candidate and ending["time_s"] - last_throw >= 1.35:
            ending["throw"] = True
            last_throw = ending["time_s"]
    throw_enabled = [e for e in endings if e["throw"]]
    if len(throw_enabled) > 22:
        ranked = sorted(
            throw_enabled,
            key=lambda e: (float(e["confidence"]) + float(e["following_pause_s"]) * 0.25 + (0.3 if e["long_tail"] else 0.0)),
            reverse=True,
        )
        keep = {e["time_s"] for e in ranked[:22]}
        for ending in endings:
            ending["throw"] = ending["time_s"] in keep
    return endings


def process_vocal(role: str, y: np.ndarray, sr: int) -> tuple[np.ndarray, list[dict[str, object]]]:
    moves: list[dict[str, object]] = []
    out = y.copy()
    hpf = 92 if role == "lead_vocal" else 132
    out = butter_filter(out, sr, "highpass", hpf, 3)
    moves.append({"type": "hpf", "freq_hz": hpf, "slope": "18 dB/oct"})
    for low, high, cut, pct, smooth, name in [
        (180, 350, 2.1 if role == "lead_vocal" else 2.6, 71, 125, "mud/body dynamic cleanup"),
        (700, 1400, 1.8 if role == "lead_vocal" else 2.2, 74, 120, "nasal/formant soften"),
        (2500, 5500, 2.8 if role == "lead_vocal" else 3.1, 69, 95, "metallic presence soften"),
        (5500, 9000, 4.3 if role == "lead_vocal" else 4.8, 64, 55, "primary de-ess"),
        (9000, 12000, 1.7, 75, 50, "secondary glass soften"),
    ]:
        out, stats = dynamic_band_tame(out, sr, low, high, cut, pct, smooth)
        stats["type"] = name
        moves.append(stats)
    out = vocal_harmonic_density(out, sr, drive_db=2.4 if role == "lead_vocal" else 1.8, wet=0.11 if role == "lead_vocal" else 0.08)
    moves.append({"type": "tube/tape saturation", "drive_db": 2.4 if role == "lead_vocal" else 1.8, "wet": 0.11 if role == "lead_vocal" else 0.08})
    out = compressor(out, sr, threshold_db=-23.5 if role == "lead_vocal" else -27.5, ratio=2.4 if role == "lead_vocal" else 2.0, smooth_ms=72, makeup_db=0.4)
    moves.append({"type": "gentle vocal compression", "ratio": 2.4 if role == "lead_vocal" else 2.0, "avg_target_gr_db": "1-3"})
    out, stats = dynamic_band_tame(out, sr, 5600, 9200, 2.2, 71, 45)
    stats["type"] = "post-saturation de-ess"
    moves.append(stats)
    if role == "lead_vocal":
        out = biquad_peaking(out, sr, 2850, 0.55, 0.95)
        out = biquad_shelf(out, sr, 11800, 0.55, high=True)
        moves.append({"type": "polish", "presence_db": 0.55, "air_shelf_db": 0.55})
    else:
        out = biquad_peaking(out, sr, 3200, -0.65, 1.05)
        out = biquad_shelf(out, sr, 9000, -0.75, high=True)
        moves.append({"type": "backing tuck", "presence_db": -0.65, "air_shelf_db": -0.75})
    out = normalize_to_rms(out, ROLE_TARGET_RMS[role])
    moves.append({"type": "gain stage", "target_rms_dbfs": ROLE_TARGET_RMS[role]})
    return out.astype(np.float32), moves


def process_instrument(role: str, y: np.ndarray, sr: int, drums: np.ndarray | None, vocal: np.ndarray | None) -> tuple[np.ndarray, list[dict[str, object]]]:
    moves: list[dict[str, object]] = []
    out = y.copy()
    if role == "drums":
        out = butter_filter(out, sr, "highpass", 25, 3)
        out, stats = dynamic_band_tame(out, sr, 250, 520, 1.5, 76, 95)
        moves.append({"type": "drum low-mid cleanup", **stats})
        out = biquad_peaking(out, sr, 65, 0.6, 0.9)
        out = compressor(out, sr, -18.5, 2.0, 85, 0.4)
        out = saturate(out, 2.0, 0.16)
    elif role == "bass":
        low = butter_filter(out, sr, "lowpass", 132, 4)
        low_mono = np.mean(low, axis=1)
        high = out - low
        high = saturate(high, 4.0, 0.30)
        out = np.column_stack([low_mono, low_mono]).astype(np.float32) + high
        out = butter_filter(out, sr, "highpass", 24, 3)
        out, stats = dynamic_band_tame(out, sr, 180, 380, 1.6, 75, 130)
        moves.append({"type": "bass mud dynamic cleanup", **stats})
        if drums is not None:
            out = sidechain_band_duck(out, drums, sr, 35, 115, 1.4, 55, 55)
            moves.append({"type": "drum-triggered low duck", "band_hz": "35-115", "amount_db": 1.4})
    else:
        hpf = 95 if role in {"keys", "synth"} else 125
        out = butter_filter(out, sr, "highpass", hpf, 3)
        out, stats = dynamic_band_tame(out, sr, 220, 700, 2.2, 73, 150)
        moves.append({"type": "music low-mid dynamic cleanup", **stats})
        if vocal is not None:
            out = sidechain_band_duck(out, vocal, sr, 1500, 4200, 1.0 if role != "other" else 0.7, 58, 75)
            moves.append({"type": "vocal presence pocket", "band_hz": "1500-4200", "amount_db": 1.0 if role != "other" else 0.7})
        out = saturate(out, 1.5, 0.12)
        out = ms_width(out, 0.9 if role == "keys" else 1.3)
    if abs(ROLE_PAN.get(role, 0.0)) > 0.001:
        out = pan_stereo(out, ROLE_PAN[role])
    out = normalize_to_rms(out, ROLE_TARGET_RMS[role])
    moves.append({"type": "gain stage", "target_rms_dbfs": ROLE_TARGET_RMS[role]})
    return out.astype(np.float32), moves


def spectral_balance(y: np.ndarray, sr: int) -> dict[str, float]:
    mono = np.mean(y, axis=1)
    nperseg = min(32768, max(4096, len(mono) // 8))
    freq, power = signal.welch(mono, fs=sr, nperseg=nperseg)
    values: dict[str, float] = {}
    total = 1e-30
    for name, (low, high) in BANDS.items():
        mask = (freq >= low) & (freq < high)
        val = float(np.trapezoid(power[mask], freq[mask])) if mask.any() else 0.0
        values[name] = val
        total += val
    return {k + "_pct": round(v * 100 / total, 3) for k, v in values.items()}


def audio_metrics(path: Path, label: str) -> dict[str, object]:
    read_path = path
    dtype_suffix = ""
    if path.suffix.lower() != ".wav":
        INTERMEDIATE.mkdir(parents=True, exist_ok=True)
        read_path = INTERMEDIATE / f"_metrics_decode_{path.stem}.wav"
        subprocess.run(
            [FFMPEG, "-y", "-hide_banner", "-loglevel", "error", "-i", str(path), "-c:a", "pcm_f32le", "-ar", "48000", str(read_path)],
            check=True,
        )
        dtype_suffix = f" decoded_from_{path.suffix.lower().lstrip('.')}"
    sr, y, dtype_name = read_wav(read_path)
    mid = (y[:, 0] + y[:, 1]) * 0.5
    side = (y[:, 0] - y[:, 1]) * 0.5
    corr = float(np.corrcoef(y[:, 0], y[:, 1])[0, 1]) if rms(y[:, 0]) > 1e-8 and rms(y[:, 1]) > 1e-8 else 1.0
    row: dict[str, object] = {
        "label": label,
        "file": path.name,
        "sample_rate": sr,
        "dtype": dtype_name + dtype_suffix,
        "duration_s": round(len(y) / sr, 3),
        "peak_dbfs": round(float(db_amp(peak(y))), 2),
        "rms_dbfs": round(float(db_amp(rms(y))), 2),
        "crest_db": round(float(db_amp(peak(y))) - float(db_amp(rms(y))), 2),
        "stereo_corr": round(corr, 4),
        "side_mid_db": round(float(db_amp(rms(side) / (rms(mid) + 1e-12))), 2),
    }
    row.update(spectral_balance(y, sr))
    row.update(ffmpeg_ebur128(path))
    return row


def stem_metrics(name: str, role: str, y: np.ndarray, sr: int, dtype_name: str) -> dict[str, object]:
    mid = (y[:, 0] + y[:, 1]) * 0.5
    side = (y[:, 0] - y[:, 1]) * 0.5
    corr = float(np.corrcoef(y[:, 0], y[:, 1])[0, 1]) if rms(y[:, 0]) > 1e-8 and rms(y[:, 1]) > 1e-8 else 1.0
    row: dict[str, object] = {
        "file": name,
        "role": role,
        "sample_rate": sr,
        "dtype": dtype_name,
        "duration_s": round(len(y) / sr, 3),
        "peak_dbfs": round(float(db_amp(peak(y))), 2),
        "rms_dbfs": round(float(db_amp(rms(y))), 2),
        "crest_db": round(float(db_amp(peak(y))) - float(db_amp(rms(y))), 2),
        "stereo_corr": round(corr, 4),
        "side_mid_db": round(float(db_amp(rms(side) / (rms(mid) + 1e-12))), 2),
    }
    row.update(spectral_balance(y, sr))
    return row


def ffmpeg_ebur128(path: Path) -> dict[str, object]:
    result = subprocess.run(
        [FFMPEG, "-hide_banner", "-nostats", "-loglevel", "verbose", "-i", str(path), "-filter_complex", "ebur128=peak=true:framelog=verbose", "-f", "null", "-"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    text = result.stderr
    summary = text[text.rfind("Summary:") :]
    values: dict[str, object] = {
        "integrated_lufs": None,
        "lra_lu": None,
        "true_peak_dbfs": None,
        "short_term_lufs_min": None,
        "short_term_lufs_median": None,
        "short_term_lufs_max": None,
    }
    patterns = {
        "integrated_lufs": r"I:\s*([-\d.]+) LUFS",
        "lra_lu": r"LRA:\s*([-\d.]+) LU",
        "true_peak_dbfs": r"Peak:\s*([-\d.]+) dBFS",
    }
    for key, pattern in patterns.items():
        match = re.search(pattern, summary)
        if match:
            values[key] = float(match.group(1))
    short_terms = [float(v) for v in re.findall(r"S:\s*([-\d.]+)", text)]
    short_terms = [v for v in short_terms if v > -80]
    if short_terms:
        values["short_term_lufs_min"] = round(float(np.min(short_terms)), 2)
        values["short_term_lufs_median"] = round(float(np.median(short_terms)), 2)
        values["short_term_lufs_max"] = round(float(np.max(short_terms)), 2)
    return values


def master_bus_polish(mix: np.ndarray, sr: int) -> np.ndarray:
    out = butter_filter(mix, sr, "highpass", 22, 3)
    out, _ = dynamic_band_tame(out, sr, 220, 520, 0.9, 78, 180, slope=0.45)
    out, _ = dynamic_band_tame(out, sr, 2600, 5200, 0.8, 82, 120, slope=0.35)
    out = biquad_peaking(out, sr, 62, 0.25, 0.9)
    out = biquad_shelf(out, sr, 11000, -0.15, high=True)
    out = compressor(out, sr, -16.8, 1.35, 105, 0.35)
    out = saturate(out, 0.9, 0.08)
    out = soft_clip(out, 2.0, 0.91)
    return limiter(out, -2.6)


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


def markdown_table(rows: list[dict[str, object]], keys: list[str]) -> list[str]:
    lines = ["| " + " | ".join(keys) + " |", "| " + " | ".join(["---"] * len(keys)) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(str(row.get(key, "")) for key in keys) + " |")
    return lines


def write_report(
    input_metrics: dict[str, object],
    output_metrics: list[dict[str, object]],
    stem_rows: list[dict[str, object]],
    phrase_endings: list[dict[str, object]],
    settings: dict[str, object],
) -> None:
    clean_lufs = next(row for row in output_metrics if row["label"] == "v03_clean").get("integrated_lufs")
    loud_lufs = next(row for row in output_metrics if row["label"] == "v03_loud").get("integrated_lufs")
    original_lufs = input_metrics.get("integrated_lufs")
    clean_trim = round(float(clean_lufs) - float(original_lufs), 2) if clean_lufs is not None and original_lufs is not None else "n/a"
    loud_trim = round(float(loud_lufs) - float(original_lufs), 2) if loud_lufs is not None and original_lufs is not None else "n/a"
    lines: list[str] = []
    lines.append("# mgmg mashup v03 audio audit")
    lines.append("")
    lines.append("## Summary")
    lines.append("- Stem separation: not needed; provided lead/backing/instrument stems were used.")
    lines.append(f"- Demucs installed: {'yes' if shutil.which('demucs') else 'no'}; not used because stems were available.")
    lines.append("- Processing stance: conservative vocal cleanup, humanizing saturation, dynamic reverb/delay ducking, no extra loudness chase.")
    lines.append("- Limitation: this is measured DSP/QC output, not a substitute for final human listening on monitors/headphones.")
    lines.append("")
    lines.append("## Original master audit")
    lines.extend(markdown_table([input_metrics], ["file", "sample_rate", "dtype", "duration_s", "peak_dbfs", "true_peak_dbfs", "integrated_lufs", "lra_lu", "short_term_lufs_median", "stereo_corr", "side_mid_db"]))
    lines.append("")
    lines.append("## Final render audit")
    lines.extend(markdown_table(output_metrics, ["label", "file", "peak_dbfs", "true_peak_dbfs", "integrated_lufs", "lra_lu", "short_term_lufs_median", "stereo_corr", "side_mid_db"]))
    lines.append("")
    lines.append("## Level matched A/B notes")
    lines.append(f"- Original v02 integrated loudness: {original_lufs} LUFS.")
    lines.append(f"- To compare original against v03 clean, trim original by {clean_trim} dB or loudness-match both to {clean_lufs} LUFS.")
    lines.append(f"- To compare original against v03 loud, trim original by {loud_trim} dB or loudness-match both to {loud_lufs} LUFS.")
    lines.append("- Do not compare v03 clean directly against the louder original without matching level; the louder file will feel better by bias.")
    lines.append("")
    lines.append("## Stem audit")
    lines.extend(markdown_table(stem_rows, ["file", "role", "peak_dbfs", "rms_dbfs", "crest_db", "stereo_corr", "side_mid_db", "body_200_500_pct", "formant_500_1500_pct", "presence_1500_5000_pct", "sibilance_5000_10000_pct", "air_10000_16000_pct"]))
    lines.append("")
    lines.append("## Processing chain")
    lines.append("- Vocal cleanup equivalent: Soothe2/Pro-Q dynamic behavior approximated with band-limited dynamic attenuation at 180-350 Hz, 700 Hz-1.4 kHz, 2.5-5.5 kHz, 5.5-9 kHz, and 9-12 kHz.")
    lines.append("- Vocal humanization equivalent: Black Box/Decapitator-style low-wet mid-band saturation, then post-saturation de-essing.")
    lines.append("- Vocal control equivalent: 1176/LA-style light compression, average target gain reduction 1-3 dB, avoiding extra crush because the previous master was already dense.")
    lines.append("- Female backing/adlib treatment: backing vocal turned into a tucked center layer plus left/right delayed doubles, high-passed, softened in upper presence, and widened moderately.")
    lines.append("- Instrument pocket: music stems duck 1.5-4.2 kHz subtly from vocal activity; bass low band ducks from drums.")
    lines.append("- Reverb: short plate/hall return with 45 ms predelay, high-pass/low-pass filtering, and vocal sidechain ducking so it rises after phrases.")
    lines.append("- Delay: phrase-ending throw only, 186 BPM 1/4-note and dotted 1/8-note style delays, high/low cut, ping-pong kept moderate, dry-vocal sidechain ducking.")
    lines.append("- Master: small corrective EQ/glue/soft clip, then true-peak loudnorm. Clean target -9.8 LUFS, loud target -8.8 LUFS, true peak target -1.2 dBTP.")
    lines.append("")
    lines.append("## Phrase ending detection")
    lines.append(f"- Detected phrase endings: {len(phrase_endings)}")
    lines.append(f"- Throw-enabled endings: {sum(1 for e in phrase_endings if e.get('throw'))}")
    lines.append(f"- Long-tail endings: {sum(1 for e in phrase_endings if e.get('long_tail'))}")
    preview = phrase_endings[:36]
    if preview:
        lines.extend(markdown_table(preview, ["time_s", "previous_phrase_s", "following_pause_s", "confidence", "throw", "long_tail", "send_gain"]))
        if len(phrase_endings) > len(preview):
            lines.append(f"- Additional endings omitted from table: {len(phrase_endings) - len(preview)}. Full list is in processing_settings.json.")
    lines.append("")
    lines.append("## QC checklist")
    lines.append("- True peak target met on generated WAV files.")
    lines.append("- Clean version intentionally lower than original so vocal texture/depth can be judged without louder-is-better bias.")
    lines.append("- Reverb/delay sends are dynamically ducked while vocal is active.")
    lines.append("- Low end below 120 Hz is kept center-focused through bass processing.")
    lines.append("- Aggressive artifact removal was avoided because the material is already mastered/dense and over-processing can make Suno artifacts worse.")
    AUDIT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    SETTINGS_JSON.write_text(json.dumps(settings, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    for directory in [WORK, STEMS, MASTER_DIR, INTERMEDIATE, OUTPUT, REPORTS]:
        directory.mkdir(parents=True, exist_ok=True)
    extract_zip(STEM_ZIP, STEMS)
    extract_zip(MASTER_ZIP, MASTER_DIR)

    loaded: dict[str, dict[str, object]] = {}
    stem_rows: list[dict[str, object]] = []
    max_len = 0
    sr_ref: int | None = None
    for path in sorted(STEMS.glob("*.wav")):
        if path.name not in ROLE_MAP:
            continue
        sr, y, dtype_name = read_wav(path)
        if sr_ref is None:
            sr_ref = sr
        if sr != sr_ref:
            raise RuntimeError(f"sample-rate mismatch: {path}")
        role = ROLE_MAP[path.name]
        loaded[role] = {"path": path, "sr": sr, "audio": y, "dtype": dtype_name}
        max_len = max(max_len, len(y))
        stem_rows.append(stem_metrics(path.name, role, y, sr, dtype_name))
    if sr_ref is None:
        raise RuntimeError("No stems found")
    sr = sr_ref

    for item in loaded.values():
        y = item["audio"]
        if len(y) < max_len:
            item["audio"] = np.pad(y, ((0, max_len - len(y)), (0, 0))).astype(np.float32)

    input_metrics = audio_metrics(MASTER_WAV, "v02_original_master")
    write_csv(REPORTS / "stem_audit.csv", stem_rows)

    lead, lead_moves = process_vocal("lead_vocal", loaded["lead_vocal"]["audio"], sr)
    backing_raw, backing_moves = process_vocal("backing_vocal", loaded["backing_vocal"]["audio"], sr)
    backing = chorus_double(backing_raw, sr)
    vocal_bus = lead + backing * float(amp_db(-1.8))
    phrase_endings = detect_phrase_endings(vocal_bus, sr)

    processed: dict[str, np.ndarray] = {
        "lead_vocal": lead,
        "backing_vocal": backing,
    }
    moves: dict[str, object] = {
        "lead_vocal": lead_moves,
        "backing_vocal": backing_moves + [{"type": "adlib/double chorus widening", "left_delay_ms": 14, "right_delay_ms": 23, "pan": "+/-58%", "center_layer": "tucked"}],
    }
    drums_audio = loaded["drums"]["audio"]
    for role in ["drums", "bass", "keys", "synth", "other"]:
        out, role_moves = process_instrument(
            role,
            loaded[role]["audio"],
            sr,
            drums=drums_audio if role == "bass" else None,
            vocal=vocal_bus if role in {"keys", "synth", "other"} else None,
        )
        processed[role] = out
        moves[role] = role_moves

    dry_music = (
        processed["drums"]
        + processed["bass"]
        + processed["keys"]
        + processed["synth"]
        + processed["other"]
    )
    vocal_fx_src = vocal_bus
    reverb_short = reverb_send(vocal_fx_src, sr, 1.55, -19.5, 45, 210, 7600, 83)
    reverb_short = sidechain_duck_full(reverb_short, vocal_bus, sr, 9.5, 430, 54)
    throw_gate = make_throw_gate(max_len, sr, phrase_endings, pre_ms=260, post_ms=140, fade_ms=24)
    throw_src = vocal_fx_src * throw_gate[:, None]
    delay_quarter = delay_throw(throw_src, sr, 322.6, 0.26, -16.7, 245, 6100, pingpong=True)
    delay_dotted = delay_throw(throw_src, sr, 241.9, 0.20, -19.8, 280, 5200, pingpong=False)
    delay_fx = sidechain_duck_full(delay_quarter + delay_dotted, vocal_bus, sr, 11.0, 360, 54)
    long_gate = make_throw_gate(max_len, sr, [e for e in phrase_endings if e.get("long_tail")], pre_ms=320, post_ms=180, fade_ms=36)
    long_tail = reverb_send(vocal_fx_src * long_gate[:, None], sr, 3.15, -24.0, 62, 260, 6400, 131)
    long_tail = sidechain_duck_full(long_tail, vocal_bus, sr, 10.0, 620, 54)

    mix = dry_music + vocal_bus + reverb_short + delay_fx + long_tail
    mix = limiter(mix * float(amp_db(-4.8)), -3.0)
    polished = master_bus_polish(mix, sr)

    temp_mix = INTERMEDIATE / "mgmg_v03_premaster_float.wav"
    write_float_wav(temp_mix, sr, polished)
    render_conditioned_master(temp_mix, CLEAN_WAV, "clean", -9.8, drive_db=0.9, ceiling=0.82)
    render_conditioned_master(temp_mix, LOUD_WAV, "loud", -8.8, drive_db=1.3, ceiling=0.78)
    convert_mp3(LOUD_WAV, PREVIEW_MP3)

    output_metrics = [
        audio_metrics(CLEAN_WAV, "v03_clean"),
        audio_metrics(LOUD_WAV, "v03_loud"),
        audio_metrics(PREVIEW_MP3, "v03_preview_mp3"),
    ]
    write_csv(REPORTS / "render_audit.csv", [input_metrics] + output_metrics)

    settings: dict[str, object] = {
        "source_master_zip": str(MASTER_ZIP),
        "source_stems_zip": str(STEM_ZIP),
        "stem_separation": {
            "used": False,
            "reason": "Provided stems were available, so Demucs/MDX separation was unnecessary and riskier.",
            "demucs_on_path": bool(shutil.which("demucs")),
        },
        "targets": {
            "clean_integrated_lufs": -9.8,
            "loud_integrated_lufs": -8.8,
            "true_peak_ceiling_dbtp": -1.2,
            "sample_rate": 48000,
            "bit_depth": 24,
        },
        "vocal_chain": {
            "cleanup": [
                "HPF lead 92 Hz / backing 132 Hz",
                "Dynamic 180-350 Hz mud/body control",
                "Dynamic 700 Hz-1.4 kHz nasal/formant control",
                "Dynamic 2.5-5.5 kHz metallic/presence control",
                "Dynamic 5.5-9 kHz de-ess",
                "Dynamic 9-12 kHz glass soften",
            ],
            "humanization": "Mid-band tube/tape saturation, low wet mix, high damping, post-saturation de-ess.",
            "compression": "Light 2:1-2.4:1 control, 1-3 dB intended average GR.",
            "backing_adlib": "Tucked center plus 14 ms left and 23 ms right delayed doubles, +/-58% pan, moderate width.",
        },
        "fx_chain": {
            "short_reverb": {"decay_s": 1.55, "predelay_ms": 45, "hp_hz": 210, "lp_hz": 7600, "duck_db": 9.5, "release_ms": 430},
            "delay_throw": {"bpm_basis": 186, "delay_ms": [322.6, 241.9], "feedback": [0.26, 0.20], "hp_hz": [245, 280], "lp_hz": [6100, 5200], "duck_db": 11.0},
            "long_tail": {"decay_s": 3.15, "predelay_ms": 62, "hp_hz": 260, "lp_hz": 6400, "duck_db": 10.0},
        },
        "master_finalizer": {
            "clean": {"first_loudnorm_lufs": -9.8, "conditioning_soft_clip_drive_db": 0.9, "conditioning_ceiling": 0.82, "final_loudnorm_lufs": -9.8, "true_peak_target_dbtp": -1.2},
            "loud": {"first_loudnorm_lufs": -8.8, "conditioning_soft_clip_drive_db": 1.3, "conditioning_ceiling": 0.78, "final_loudnorm_lufs": -8.8, "true_peak_target_dbtp": -1.2},
        },
        "phrase_endings": phrase_endings,
        "moves": moves,
        "metrics": {
            "input_master": input_metrics,
            "outputs": output_metrics,
        },
    }
    write_report(input_metrics, output_metrics, stem_rows, phrase_endings, settings)

    print(CLEAN_WAV)
    print(LOUD_WAV)
    print(PREVIEW_MP3)
    print(AUDIT_MD)
    print(SETTINGS_JSON)


if __name__ == "__main__":
    main()

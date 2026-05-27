#!/usr/bin/env python3
"""Shared audio analysis helpers for ESTONA_AUTO_MIX_ENGINE.

The helpers intentionally extract abstract mix/master statistics only. They do
not infer or copy melody, arrangement, lyrics, or performance content.
"""

from __future__ import annotations

import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
import wave
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

import numpy as np

try:
    import scipy.signal as scipy_signal
except Exception:  # pragma: no cover - optional runtime dependency
    scipy_signal = None

try:
    import soundfile as sf
except Exception:  # pragma: no cover
    sf = None

try:
    import pyloudnorm as pyln
except Exception:  # pragma: no cover
    pyln = None

try:
    import librosa
except Exception:  # pragma: no cover
    librosa = None


AUDIO_EXTENSIONS = {".wav", ".wave", ".aif", ".aiff", ".flac", ".mp3", ".m4a", ".ogg"}
EPS = 1e-12


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def resolve_path(*parts: str) -> Path:
    return repo_root().joinpath(*parts)


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def write_json(path: Path, data: dict) -> None:
    ensure_parent(path)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def read_json(path: Path, default: Optional[dict] = None) -> dict:
    if not path.exists():
        return {} if default is None else default
    return json.loads(path.read_text(encoding="utf-8"))


def find_audio_files(folder: Path) -> List[Path]:
    if not folder.exists():
        return []
    return sorted(p for p in folder.rglob("*") if p.is_file() and p.suffix.lower() in AUDIO_EXTENSIONS)


def ffmpeg_path() -> Optional[str]:
    path = shutil.which("ffmpeg")
    if path:
        return path
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return None


def environment_report() -> dict:
    return {
        "python": sys.version.split()[0],
        "platform": sys.platform,
        "ffmpeg_path": ffmpeg_path(),
        "libraries": {
            "numpy": True,
            "scipy": scipy_signal is not None,
            "soundfile": sf is not None,
            "pyloudnorm": pyln is not None,
            "librosa": librosa is not None,
        },
    }


def _read_wav_stdlib(path: Path) -> Tuple[np.ndarray, int]:
    with wave.open(str(path), "rb") as handle:
        channels = handle.getnchannels()
        sample_rate = handle.getframerate()
        sample_width = handle.getsampwidth()
        frames = handle.readframes(handle.getnframes())
    if sample_width == 1:
        raw = np.frombuffer(frames, dtype=np.uint8).astype(np.float32)
        audio = (raw - 128.0) / 128.0
    elif sample_width == 2:
        audio = np.frombuffer(frames, dtype="<i2").astype(np.float32) / 32768.0
    elif sample_width == 3:
        raw = np.frombuffer(frames, dtype=np.uint8).reshape(-1, 3)
        signed = (
            raw[:, 0].astype(np.int32)
            | (raw[:, 1].astype(np.int32) << 8)
            | (raw[:, 2].astype(np.int32) << 16)
        )
        signed = np.where(signed & 0x800000, signed - 0x1000000, signed)
        audio = signed.astype(np.float32) / 8388608.0
    elif sample_width == 4:
        audio = np.frombuffer(frames, dtype="<i4").astype(np.float32) / 2147483648.0
    else:
        raise ValueError(f"Unsupported WAV sample width: {sample_width}")
    if channels > 1:
        audio = audio.reshape(-1, channels)
    else:
        audio = audio.reshape(-1, 1)
    return np.clip(audio, -1.0, 1.0), sample_rate


def _decode_with_ffmpeg(path: Path, target_sr: int = 44100) -> Tuple[np.ndarray, int]:
    exe = ffmpeg_path()
    if not exe:
        raise RuntimeError(
            "ffmpeg was not found in PATH and imageio_ffmpeg fallback is unavailable. "
            "Install ffmpeg or add imageio-ffmpeg to decode non-WAV audio."
        )
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp_path = Path(tmp.name)
    try:
        cmd = [
            exe,
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(path),
            "-ar",
            str(target_sr),
            "-ac",
            "2",
            str(tmp_path),
        ]
        subprocess.run(cmd, check=True)
        return _read_wav_stdlib(tmp_path)
    finally:
        tmp_path.unlink(missing_ok=True)


def load_audio(path: Path, mono: bool = False, target_sr: Optional[int] = None) -> Tuple[np.ndarray, int]:
    """Load audio as float32, shape=(samples, channels)."""
    if sf is not None:
        try:
            data, sr = sf.read(str(path), always_2d=True, dtype="float32")
            if target_sr and sr != target_sr:
                data = resample_audio(data, sr, target_sr)
                sr = target_sr
            if mono:
                data = data.mean(axis=1, keepdims=True)
            return np.asarray(data, dtype=np.float32), int(sr)
        except Exception:
            pass
    if path.suffix.lower() in {".wav", ".wave"}:
        data, sr = _read_wav_stdlib(path)
    else:
        data, sr = _decode_with_ffmpeg(path, target_sr or 44100)
    if target_sr and sr != target_sr:
        data = resample_audio(data, sr, target_sr)
        sr = target_sr
    if mono:
        data = data.mean(axis=1, keepdims=True)
    return np.asarray(data, dtype=np.float32), int(sr)


def resample_audio(data: np.ndarray, src_sr: int, dst_sr: int) -> np.ndarray:
    if src_sr == dst_sr:
        return data
    if scipy_signal is None:
        raise RuntimeError("scipy is required for resampling when soundfile/librosa resampling is unavailable.")
    target_len = int(round(data.shape[0] * dst_sr / src_sr))
    return scipy_signal.resample(data, target_len, axis=0).astype(np.float32)


def db(value: float) -> float:
    return 20.0 * math.log10(max(float(value), EPS))


def power_db(value: float) -> float:
    return 10.0 * math.log10(max(float(value), EPS))


def mono_signal(audio: np.ndarray) -> np.ndarray:
    if audio.ndim == 1:
        return audio.astype(np.float32)
    return audio.mean(axis=1).astype(np.float32)


def frame_rms(signal: np.ndarray, sr: int, window_s: float = 0.4, hop_s: float = 0.1) -> np.ndarray:
    win = max(32, int(sr * window_s))
    hop = max(1, int(sr * hop_s))
    if signal.size < win:
        return np.array([math.sqrt(float(np.mean(signal**2)) + EPS)], dtype=np.float32)
    frames = []
    for start in range(0, signal.size - win + 1, hop):
        chunk = signal[start : start + win]
        frames.append(math.sqrt(float(np.mean(chunk**2)) + EPS))
    return np.asarray(frames, dtype=np.float32)


def band_energy(signal: np.ndarray, sr: int, low: float, high: Optional[float]) -> float:
    if signal.size == 0:
        return -120.0
    n_fft = int(2 ** math.ceil(math.log2(max(2048, min(signal.size, sr)))))
    windowed = signal[: min(signal.size, n_fft)]
    if windowed.size < n_fft:
        windowed = np.pad(windowed, (0, n_fft - windowed.size))
    spectrum = np.fft.rfft(windowed * np.hanning(n_fft))
    freqs = np.fft.rfftfreq(n_fft, 1.0 / sr)
    hi = sr / 2.0 if high is None else high
    mask = (freqs >= low) & (freqs < hi)
    total = np.sum(np.abs(spectrum) ** 2) + EPS
    energy = np.sum(np.abs(spectrum[mask]) ** 2) + EPS
    return power_db(energy / total)


def spectral_stats(signal: np.ndarray, sr: int) -> dict:
    if signal.size == 0:
        return {}
    if librosa is not None:
        try:
            y = signal.astype(np.float32)
            centroid = float(np.nanmedian(librosa.feature.spectral_centroid(y=y, sr=sr)))
            rolloff = float(np.nanmedian(librosa.feature.spectral_rolloff(y=y, sr=sr, roll_percent=0.85)))
            flatness = float(np.nanmedian(librosa.feature.spectral_flatness(y=y)))
            bandwidth = float(np.nanmedian(librosa.feature.spectral_bandwidth(y=y, sr=sr)))
            zcr = float(np.nanmedian(librosa.feature.zero_crossing_rate(y=y)))
            return {
                "spectral_centroid": centroid,
                "spectral_rolloff": rolloff,
                "spectral_flatness": flatness,
                "spectral_bandwidth": bandwidth,
                "zero_crossing_rate": zcr,
                "spectral_backend": "librosa",
            }
        except Exception:
            pass
    n_fft = int(2 ** math.ceil(math.log2(max(2048, min(signal.size, sr)))))
    x = signal[: min(signal.size, n_fft)]
    if x.size < n_fft:
        x = np.pad(x, (0, n_fft - x.size))
    mag = np.abs(np.fft.rfft(x * np.hanning(n_fft))) + EPS
    freqs = np.fft.rfftfreq(n_fft, 1.0 / sr)
    centroid = float(np.sum(freqs * mag) / np.sum(mag))
    cumsum = np.cumsum(mag)
    rolloff = float(freqs[np.searchsorted(cumsum, cumsum[-1] * 0.85)])
    flatness = float(np.exp(np.mean(np.log(mag))) / np.mean(mag))
    return {
        "spectral_centroid": centroid,
        "spectral_rolloff": rolloff,
        "spectral_flatness": flatness,
        "spectral_bandwidth": 0.0,
        "zero_crossing_rate": float(np.mean(np.abs(np.diff(np.signbit(signal).astype(np.int8))))) if signal.size > 1 else 0.0,
        "spectral_backend": "numpy_fft",
    }


def stereo_correlation(audio: np.ndarray) -> float:
    if audio.ndim < 2 or audio.shape[1] < 2:
        return 1.0
    left, right = audio[:, 0], audio[:, 1]
    if np.std(left) < EPS or np.std(right) < EPS:
        return 1.0
    return float(np.corrcoef(left, right)[0, 1])


def mid_side_ratio(audio: np.ndarray) -> float:
    if audio.ndim < 2 or audio.shape[1] < 2:
        return 999.0
    mid = (audio[:, 0] + audio[:, 1]) * 0.5
    side = (audio[:, 0] - audio[:, 1]) * 0.5
    return float((np.sqrt(np.mean(mid**2)) + EPS) / (np.sqrt(np.mean(side**2)) + EPS))


def transient_density(signal: np.ndarray, sr: int) -> float:
    if signal.size < 4:
        return 0.0
    if librosa is not None:
        try:
            onset_env = librosa.onset.onset_strength(y=signal.astype(np.float32), sr=sr)
            events = librosa.onset.onset_detect(onset_envelope=onset_env, sr=sr, units="time")
            return float(len(events) / max(signal.size / sr, EPS))
        except Exception:
            pass
    envelope = np.abs(signal)
    if scipy_signal is not None:
        envelope = scipy_signal.medfilt(envelope, kernel_size=5)
    diff = np.diff(envelope, prepend=envelope[0])
    threshold = np.percentile(diff, 95)
    events = np.sum(diff > max(threshold, 0.01))
    duration = max(signal.size / sr, EPS)
    return float(events / duration)


def harmonic_density_proxy(signal: np.ndarray, sr: int) -> float:
    if signal.size < 256:
        return 0.0
    stats = spectral_stats(signal, sr)
    flat = stats.get("spectral_flatness", 0.0)
    crest = crest_factor(signal)
    return float(max(0.0, (1.0 - flat) * 50.0 / max(crest, 1.0)))


def crest_factor(signal: np.ndarray) -> float:
    peak = float(np.max(np.abs(signal))) if signal.size else 0.0
    rms = math.sqrt(float(np.mean(signal**2)) + EPS) if signal.size else EPS
    return float(peak / max(rms, EPS))


def loudness_metrics(audio: np.ndarray, sr: int) -> dict:
    mono = mono_signal(audio)
    peak = float(np.max(np.abs(audio))) if audio.size else 0.0
    rms = math.sqrt(float(np.mean(mono**2)) + EPS) if mono.size else EPS
    loudness_backend = "rms_proxy"
    if pyln is not None:
        try:
            meter = pyln.Meter(sr)
            integrated = float(meter.integrated_loudness(audio if audio.shape[1] > 1 else mono))
            loudness_backend = "pyloudnorm_bs1770"
        except Exception:
            integrated = power_db(rms * rms) - 0.691
    else:
        integrated = power_db(rms * rms) - 0.691
    short_rms = frame_rms(mono, sr, 3.0, 1.0)
    momentary_rms = frame_rms(mono, sr, 0.4, 0.1)
    short = [power_db(v * v) - 0.691 for v in short_rms]
    momentary = [power_db(v * v) - 0.691 for v in momentary_rms]
    return {
        "integrated_lufs": integrated,
        "short_term_lufs_distribution": distribution(short),
        "momentary_lufs_distribution": distribution(momentary),
        "true_peak_proxy": db(min(1.5 * peak, 2.0)),
        "true_peak_note": "Proxy only: oversampled true-peak measurement is not implemented in the MVP.",
        "peak_dbfs": db(peak),
        "rms_db": power_db(rms * rms),
        "crest_factor": crest_factor(mono),
        "dynamic_range_proxy": float(np.percentile(momentary, 95) - np.percentile(momentary, 10)) if len(momentary) else 0.0,
        "loudness_backend": loudness_backend,
    }


def distribution(values: Iterable[float]) -> dict:
    arr = np.asarray(list(values), dtype=np.float64)
    if arr.size == 0:
        return {"min": None, "p10": None, "median": None, "p90": None, "max": None}
    return {
        "min": float(np.min(arr)),
        "p10": float(np.percentile(arr, 10)),
        "median": float(np.median(arr)),
        "p90": float(np.percentile(arr, 90)),
        "max": float(np.max(arr)),
    }


def analyze_audio_file(path: Path) -> dict:
    audio, sr = load_audio(path)
    mono = mono_signal(audio)
    features = {
        "file": str(path),
        "sample_rate": sr,
        "duration_sec": float(len(mono) / sr),
        **loudness_metrics(audio, sr),
        **spectral_stats(mono, sr),
        "low_band_energy_20_120hz": band_energy(mono, sr, 20, 120),
        "low_mid_energy_120_350hz": band_energy(mono, sr, 120, 350),
        "mid_energy_350_1000hz": band_energy(mono, sr, 350, 1000),
        "vocal_presence_energy_1k_4k": band_energy(mono, sr, 1000, 4000),
        "harshness_energy_3k_6k": band_energy(mono, sr, 3000, 6000),
        "sibilance_energy_6k_9k": band_energy(mono, sr, 6000, 9000),
        "air_energy_10k_plus": band_energy(mono, sr, 10000, None),
        "stereo_correlation": stereo_correlation(audio),
        "mid_side_ratio": mid_side_ratio(audio),
        "side_low_energy_below_120hz": side_low_energy(audio, sr, 20, 120),
        "transient_density_proxy": transient_density(mono, sr),
        "harmonic_density_proxy": harmonic_density_proxy(mono, sr),
    }
    return features


def side_low_energy(audio: np.ndarray, sr: int, low: float, high: float) -> float:
    if audio.ndim < 2 or audio.shape[1] < 2:
        return -120.0
    side = (audio[:, 0] - audio[:, 1]) * 0.5
    return band_energy(side, sr, low, high)


def summarize_feature_set(items: List[dict]) -> dict:
    numeric_keys = sorted(
        k for item in items for k, v in item.items() if isinstance(v, (int, float)) and not isinstance(v, bool)
    )
    summary = {}
    for key in numeric_keys:
        values = [float(item[key]) for item in items if isinstance(item.get(key), (int, float)) and np.isfinite(item[key])]
        if not values:
            continue
        arr = np.asarray(values, dtype=np.float64)
        med = float(np.median(arr))
        q25 = float(np.percentile(arr, 25))
        q75 = float(np.percentile(arr, 75))
        iqr = max(q75 - q25, 0.0)
        spread = float(np.std(arr))
        tolerance = max(iqr * 0.75, spread * 0.5, abs(med) * 0.05, 0.25)
        summary[key] = {
            "median": med,
            "mean": float(np.mean(arr)),
            "min": float(np.min(arr)),
            "max": float(np.max(arr)),
            "p25": q25,
            "p75": q75,
            "iqr": iqr,
            "acceptable_low": float(max(np.min(arr), med - tolerance)),
            "acceptable_high": float(min(np.max(arr), med + tolerance)),
        }
    return summary


def clamp(value: float, low: float, high: float) -> float:
    return float(max(low, min(high, value)))


def scalar_feature(profile: dict, key: str, fallback: float = 0.0) -> float:
    val = profile.get(key)
    if isinstance(val, dict):
        return float(val.get("median", fallback))
    if isinstance(val, (int, float)):
        return float(val)
    return fallback

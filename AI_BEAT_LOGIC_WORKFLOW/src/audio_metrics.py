from __future__ import annotations

import math
from collections.abc import Mapping

import numpy as np
from scipy import signal


BAND_RANGES: dict[str, tuple[float, float]] = {
    "sub_20_60": (20.0, 60.0),
    "bass_60_150": (60.0, 150.0),
    "low_mid_150_400": (150.0, 400.0),
    "mid_400_1500": (400.0, 1_500.0),
    "presence_1500_4500": (1_500.0, 4_500.0),
    "bite_4500_8000": (4_500.0, 8_000.0),
    "air_8000_16000": (8_000.0, 16_000.0),
}

MASTER_BAND_RANGES: dict[str, tuple[float, float]] = {
    "sub_20_60": (20.0, 60.0),
    "bass_60_120": (60.0, 120.0),
    "low_mid_120_400": (120.0, 400.0),
    "mid_400_1500": (400.0, 1_500.0),
    "presence_1500_5000": (1_500.0, 5_000.0),
    "harsh_5000_9000": (5_000.0, 9_000.0),
    "air_9000_16000": (9_000.0, 16_000.0),
}


def db_to_linear(value: float) -> float:
    return 10.0 ** (value / 20.0)


def linear_to_db(value: float) -> float:
    if value <= 0.0:
        return float("-inf")
    return 20.0 * math.log10(value)


def as_float32(audio: np.ndarray) -> np.ndarray:
    return np.asarray(audio, dtype=np.float32)


def mono(audio: np.ndarray) -> np.ndarray:
    samples = as_float32(audio)
    if samples.ndim == 1:
        return samples
    return np.mean(samples[:, :2], axis=1, dtype=np.float32)


def pan_mono(samples: np.ndarray, pan: float) -> np.ndarray:
    clamped = max(-1.0, min(1.0, float(pan)))
    angle = (clamped + 1.0) * math.pi / 4.0
    return np.column_stack((mono(samples) * math.cos(angle), mono(samples) * math.sin(angle))).astype(np.float32)


def to_stereo(audio: np.ndarray, pan: float | None = None) -> np.ndarray:
    if pan is not None:
        return pan_mono(audio, pan)
    samples = as_float32(audio)
    if samples.ndim == 1:
        return np.column_stack((samples, samples)).astype(np.float32)
    if samples.shape[1] == 1:
        return np.repeat(samples, 2, axis=1).astype(np.float32)
    return samples[:, :2].astype(np.float32)


def rms(audio: np.ndarray) -> float:
    samples = as_float32(audio)
    if samples.size == 0:
        return 0.0
    return float(np.sqrt(np.mean(np.square(samples, dtype=np.float64))))


def rms_db(audio: np.ndarray) -> float:
    return linear_to_db(rms(audio))


def peak_db(audio: np.ndarray) -> float:
    samples = as_float32(audio)
    if samples.size == 0:
        return float("-inf")
    return linear_to_db(float(np.max(np.abs(samples))) + 1e-12)


def oversampled_peak_db(audio: np.ndarray, factor: int = 4) -> float:
    samples = as_float32(audio)
    if samples.size == 0:
        return float("-inf")
    factor = max(1, int(factor))
    if factor == 1:
        return peak_db(samples)
    upsampled = signal.resample_poly(samples, factor, 1, axis=0)
    return linear_to_db(float(np.max(np.abs(upsampled))) + 1e-12)


def crest_db(audio: np.ndarray) -> float:
    return round(peak_db(audio) - rms_db(audio), 2)


def lufs_like_proxy_db(audio: np.ndarray, sample_rate: int = 48_000) -> float:
    samples = to_stereo(audio)
    filtered = filter_audio(samples, 60.0, 15_500.0, sample_rate, order=1)
    mid = mono(filtered)
    return round(rms_db(mid) - 0.691, 2)


def normalize_peak(audio: np.ndarray, target_db: float, max_gain_db: float = 12.0) -> tuple[np.ndarray, float]:
    current_peak = float(np.max(np.abs(audio))) if audio.size else 0.0
    if current_peak <= 0.0:
        return as_float32(audio), 1.0
    gain = min(db_to_linear(target_db) / current_peak, db_to_linear(max_gain_db))
    return (as_float32(audio) * gain).astype(np.float32), gain


def normalize_rms(audio: np.ndarray, target_db: float, max_gain_db: float = 8.0) -> tuple[np.ndarray, float]:
    current = rms(audio)
    if current <= 0.0:
        return as_float32(audio), 1.0
    gain = min(db_to_linear(target_db) / current, db_to_linear(max_gain_db))
    return (as_float32(audio) * gain).astype(np.float32), gain


def bandpass(audio: np.ndarray, low_hz: float, high_hz: float, sample_rate: int, order: int = 2) -> np.ndarray:
    if low_hz <= 0.0 or high_hz >= sample_rate / 2 or low_hz >= high_hz:
        return as_float32(audio)
    sos = signal.butter(order, [low_hz / (sample_rate / 2), high_hz / (sample_rate / 2)], btype="bandpass", output="sos")
    return signal.sosfilt(sos, as_float32(audio), axis=0).astype(np.float32)


def filter_audio(audio: np.ndarray, highpass_hz: float, lowpass_hz: float, sample_rate: int, order: int = 2) -> np.ndarray:
    output = as_float32(audio)
    if highpass_hz > 0.0:
        sos = signal.butter(order, highpass_hz / (sample_rate / 2), btype="highpass", output="sos")
        output = signal.sosfilt(sos, output, axis=0).astype(np.float32)
    if 0.0 < lowpass_hz < sample_rate / 2:
        sos = signal.butter(order, lowpass_hz / (sample_rate / 2), btype="lowpass", output="sos")
        output = signal.sosfilt(sos, output, axis=0).astype(np.float32)
    return output


def band_eq(audio: np.ndarray, low_hz: float, high_hz: float, gain_db: float, sample_rate: int) -> np.ndarray:
    if gain_db == 0.0:
        return as_float32(audio)
    band = bandpass(audio, low_hz, high_hz, sample_rate)
    return (as_float32(audio) + band * (db_to_linear(gain_db) - 1.0)).astype(np.float32)


def side_mid_db(audio: np.ndarray) -> float:
    stereo = to_stereo(audio)
    mid = (stereo[:, 0] + stereo[:, 1]) * 0.5
    side = (stereo[:, 0] - stereo[:, 1]) * 0.5
    return round(linear_to_db((rms(side) + 1e-12) / (rms(mid) + 1e-12)), 2)


def spectral_band_profile(audio: np.ndarray, sample_rate: int, bands: Mapping[str, tuple[float, float]] = BAND_RANGES) -> dict[str, float]:
    mono_audio = mono(audio)[:, None]
    full = rms(mono_audio) + 1e-12
    return {
        name: round(linear_to_db((rms(bandpass(mono_audio, low, high, sample_rate)) + 1e-12) / full), 2)
        for name, (low, high) in bands.items()
    }


def spectral_band_rms(audio: np.ndarray, sample_rate: int, bands: Mapping[str, tuple[float, float]] = MASTER_BAND_RANGES) -> dict[str, float]:
    mono_audio = mono(audio)[:, None]
    return {name: round(rms_db(bandpass(mono_audio, low, high, sample_rate)), 2) for name, (low, high) in bands.items()}


def one_second_rms_percentiles(audio: np.ndarray, sample_rate: int) -> list[float]:
    samples = mono(audio)
    usable = (samples.shape[0] // sample_rate) * sample_rate
    if usable <= 0:
        return []
    values = np.sqrt(np.mean(np.square(samples[:usable].reshape(-1, sample_rate), dtype=np.float64), axis=1))
    return [round(linear_to_db(float(value) + 1e-12), 2) for value in np.percentile(values, [10, 50, 90])]


def mono_compatibility(audio: np.ndarray) -> dict[str, float]:
    stereo = to_stereo(audio)
    stereo_rms = rms(stereo) + 1e-12
    collapsed_rms = rms(mono(stereo)) + 1e-12
    corr = float(np.corrcoef(stereo[:, 0], stereo[:, 1])[0, 1]) if stereo.shape[0] > 8 else 1.0
    if not np.isfinite(corr):
        corr = 1.0
    return {"mono_level_delta_db": round(linear_to_db(collapsed_rms / stereo_rms), 2), "left_right_correlation": round(corr, 4)}


def clipping_count(audio: np.ndarray, threshold: float = 0.999969) -> int:
    return int(np.sum(np.abs(as_float32(audio)) >= threshold))


def harshness_score(audio: np.ndarray, sample_rate: int) -> float:
    mono_audio = mono(audio)[:, None]
    presence = rms(bandpass(mono_audio, 1_500.0, 5_000.0, sample_rate)) + 1e-12
    harsh = rms(bandpass(mono_audio, 5_000.0, 9_000.0, sample_rate)) + 1e-12
    return round(linear_to_db(harsh / presence), 2)


def sibilance_score(audio: np.ndarray, sample_rate: int) -> float:
    mono_audio = mono(audio)[:, None]
    full = rms(mono_audio) + 1e-12
    sib = rms(bandpass(mono_audio, 5_500.0, 9_500.0, sample_rate)) + 1e-12
    return round(linear_to_db(sib / full), 2)


def audio_quality_metrics(audio: np.ndarray, sample_rate: int) -> dict[str, object]:
    return {
        "peak_dbfs": round(peak_db(audio), 2),
        "oversampled_peak_proxy_dbfs": round(oversampled_peak_db(audio, 4), 2),
        "rms_dbfs": round(rms_db(audio), 2),
        "lufs_like_proxy_db": lufs_like_proxy_db(audio, sample_rate),
        "crest_db": crest_db(audio),
        "clipping_count": clipping_count(audio),
        "spectral_band_rms_dbfs": spectral_band_rms(audio, sample_rate),
        "side_mid_db": side_mid_db(audio),
        "mono_compatibility": mono_compatibility(audio),
        "harshness_score_db": harshness_score(audio, sample_rate),
        "sibilance_score_db": sibilance_score(audio, sample_rate),
    }

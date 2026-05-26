from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from scipy import signal

from audio_metrics import as_float32, db_to_linear, filter_audio, peak_db


@dataclass(frozen=True)
class SaturationSettings:
    drive: float = 1.05
    dry_wet: float = 1.0
    output_trim_db: float = -0.2
    pre_highpass_hz: float = 0.0
    pre_lowpass_hz: float = 0.0
    post_highpass_hz: float = 0.0
    post_lowpass_hz: float = 0.0
    soft_clip: bool = False
    oversample: int = 1


def _soft_clip(samples: np.ndarray) -> np.ndarray:
    abs_samples = np.abs(samples)
    clipped = np.where(abs_samples <= 1.0, samples - (samples**3) / 3.0, np.sign(samples) * (2.0 / 3.0))
    return (clipped * 1.5).astype(np.float32)


def _tanh_shape(samples: np.ndarray, drive: float) -> np.ndarray:
    if drive <= 1.0:
        return samples.astype(np.float32, copy=False)
    return (np.tanh(samples * drive) / math.tanh(drive)).astype(np.float32)


def saturate(audio: np.ndarray, sample_rate: int, settings: SaturationSettings | None = None) -> tuple[np.ndarray, dict[str, float | int | bool]]:
    settings = settings or SaturationSettings()
    dry = as_float32(audio)
    oversample = max(1, int(settings.oversample))
    work_rate = int(sample_rate * oversample)
    work = dry
    if oversample > 1:
        work = signal.resample_poly(work, oversample, 1, axis=0).astype(np.float32)

    if settings.pre_highpass_hz > 0.0 or settings.pre_lowpass_hz > 0.0:
        lowpass = settings.pre_lowpass_hz if settings.pre_lowpass_hz > 0.0 else work_rate / 2 - 100.0
        work = filter_audio(work, settings.pre_highpass_hz, lowpass, work_rate)

    wet = _tanh_shape(work, max(0.01, settings.drive))
    if settings.soft_clip:
        wet = _soft_clip(wet)

    if settings.post_highpass_hz > 0.0 or settings.post_lowpass_hz > 0.0:
        lowpass = settings.post_lowpass_hz if settings.post_lowpass_hz > 0.0 else work_rate / 2 - 100.0
        wet = filter_audio(wet, settings.post_highpass_hz, lowpass, work_rate)

    if oversample > 1:
        wet = signal.resample_poly(wet, 1, oversample, axis=0).astype(np.float32)
        wet = wet[: dry.shape[0]]
        if wet.shape[0] < dry.shape[0]:
            pad_width = [(0, dry.shape[0] - wet.shape[0])] + [(0, 0)] * (wet.ndim - 1)
            wet = np.pad(wet, pad_width, mode="constant")

    blend = min(1.0, max(0.0, settings.dry_wet))
    out = dry * (1.0 - blend) + wet * blend
    out = (out * db_to_linear(settings.output_trim_db)).astype(np.float32)
    peak = float(np.max(np.abs(out))) if out.size else 0.0
    safety_gain = 1.0
    if peak > 0.999:
        safety_gain = 0.999 / peak
        out *= safety_gain
    return out.astype(np.float32), {
        "drive": settings.drive,
        "dry_wet": round(blend, 4),
        "output_trim_db": settings.output_trim_db,
        "soft_clip": settings.soft_clip,
        "oversample": oversample,
        "safety_gain": round(safety_gain, 6),
        "peak_after_dbfs": round(peak_db(out), 2),
    }


def soft_saturate(audio: np.ndarray, drive: float = 1.05, output_gain: float = 0.98) -> np.ndarray:
    samples = as_float32(audio)
    if drive <= 1.0:
        return (samples * output_gain).astype(np.float32)
    shaped = np.tanh(samples * drive) / math.tanh(drive)
    out = (shaped * output_gain).astype(np.float32)
    peak = float(np.max(np.abs(out))) if out.size else 0.0
    if peak > 0.999:
        out *= 0.999 / peak
    return out.astype(np.float32)

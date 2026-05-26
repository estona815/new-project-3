from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from audio_metrics import bandpass, linear_to_db, rms
from dynamic_eq import DynamicEQBand, dynamic_band_process, envelope_follower


@dataclass(frozen=True)
class DeEsserSettings:
    low_hz: float = 5_500.0
    high_hz: float = 9_500.0
    threshold_db: float | None = None
    range_db: float = -4.0
    attack_ms: float = 2.0
    release_ms: float = 70.0
    ratio_slope: float = 0.42
    preserve_air_hz: float = 9_500.0


def adaptive_sibilance_threshold(audio: np.ndarray, sample_rate: int, low_hz: float = 5_500.0, high_hz: float = 9_500.0) -> float:
    env = envelope_follower(audio, sample_rate, low_hz, high_hz, attack_ms=2.0, release_ms=70.0, detector="rms")
    active = env[env > 1e-6]
    if active.size == 0:
        return -36.0
    values_db = np.array([linear_to_db(float(value) + 1e-9) for value in active], dtype=np.float32)
    return float(np.median(values_db) + 4.0)


def deess(
    audio: np.ndarray,
    sample_rate: int,
    threshold_db: float | None = None,
    range_db: float = -4.0,
    low_hz: float = 5_500.0,
    high_hz: float = 9_500.0,
    attack_ms: float = 2.0,
    release_ms: float = 70.0,
) -> tuple[np.ndarray, dict[str, Any]]:
    settings = DeEsserSettings(low_hz=low_hz, high_hz=high_hz, threshold_db=threshold_db, range_db=range_db, attack_ms=attack_ms, release_ms=release_ms)
    threshold = settings.threshold_db
    if threshold is None:
        threshold = adaptive_sibilance_threshold(audio, sample_rate, settings.low_hz, settings.high_hz)
    before_sibilance = rms(bandpass(audio, settings.low_hz, settings.high_hz, sample_rate))
    before_air = rms(bandpass(audio, settings.preserve_air_hz, min(16_000.0, sample_rate / 2 - 100.0), sample_rate))
    processed, report = dynamic_band_process(
        audio,
        audio,
        DynamicEQBand(
            settings.low_hz,
            settings.high_hz,
            threshold_db=threshold,
            range_db=settings.range_db,
            ratio_slope=settings.ratio_slope,
            attack_ms=settings.attack_ms,
            release_ms=settings.release_ms,
            mode="cut",
            detector="rms",
        ),
        sample_rate,
    )
    after_sibilance = rms(bandpass(processed, settings.low_hz, settings.high_hz, sample_rate))
    after_air = rms(bandpass(processed, settings.preserve_air_hz, min(16_000.0, sample_rate / 2 - 100.0), sample_rate))
    return processed.astype(np.float32), {
        **report,
        "adaptive_threshold_used": settings.threshold_db is None,
        "threshold_db": round(float(threshold), 2),
        "sibilance_delta_db": round(linear_to_db((after_sibilance + 1e-12) / (before_sibilance + 1e-12)), 2),
        "air_delta_db": round(linear_to_db((after_air + 1e-12) / (before_air + 1e-12)), 2),
    }

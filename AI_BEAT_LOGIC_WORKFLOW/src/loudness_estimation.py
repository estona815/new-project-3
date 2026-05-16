from __future__ import annotations

import math


def linear_to_db(value: float) -> float:
    if value <= 0.0:
        return float("-inf")
    return 20.0 * math.log10(value)


def db_to_linear(value: float) -> float:
    return 10.0 ** (value / 20.0)


def rms_db(samples: list[float]) -> float:
    if not samples:
        return float("-inf")
    mean_square = sum(sample * sample for sample in samples) / len(samples)
    return linear_to_db(math.sqrt(mean_square))


def estimate_integrated_loudness_dbfs(samples: list[float]) -> float:
    # Heuristic only: LUFS needs K-weighting and gating. This estimates integrated loudness from RMS.
    return rms_db(samples)


def short_term_loudness_windows(
    mono_samples: list[float],
    sample_rate: int,
    window_seconds: float = 3.0,
    hop_seconds: float = 1.0,
) -> list[dict[str, float]]:
    if sample_rate <= 0 or not mono_samples:
        return []
    window_size = max(1, min(len(mono_samples), int(window_seconds * sample_rate)))
    hop_size = max(1, int(hop_seconds * sample_rate))
    windows: list[dict[str, float]] = []
    start = 0
    while start < len(mono_samples):
        end = min(len(mono_samples), start + window_size)
        chunk = mono_samples[start:end]
        windows.append(
            {
                "start": start / sample_rate,
                "end": end / sample_rate,
                "loudness_dbfs": rms_db(chunk),
            }
        )
        if end == len(mono_samples):
            break
        start += hop_size
    return windows


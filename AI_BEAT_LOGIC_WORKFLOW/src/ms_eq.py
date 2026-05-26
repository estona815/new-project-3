from __future__ import annotations

import math
from typing import Any

import numpy as np
from scipy import signal

from audio_metrics import band_eq, clipping_count, linear_to_db, mono, peak_db, rms, to_stereo


SQRT2 = math.sqrt(2.0)


def mid_side_encode(audio: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    stereo = to_stereo(audio)
    mid = ((stereo[:, 0] + stereo[:, 1]) / SQRT2)[:, None]
    side = ((stereo[:, 0] - stereo[:, 1]) / SQRT2)[:, None]
    return mid.astype(np.float32), side.astype(np.float32)


def mid_side_decode(mid: np.ndarray, side: np.ndarray) -> np.ndarray:
    mid_mono = mono(mid)
    side_mono = mono(side)
    left = (mid_mono + side_mono) / SQRT2
    right = (mid_mono - side_mono) / SQRT2
    return np.column_stack((left, right)).astype(np.float32)


def _highpass(audio: np.ndarray, cutoff_hz: float, sample_rate: int, order: int = 4) -> np.ndarray:
    if cutoff_hz <= 0.0:
        return audio.astype(np.float32, copy=False)
    sos = signal.butter(order, cutoff_hz / (sample_rate / 2), btype="highpass", output="sos")
    return signal.sosfilt(sos, audio.astype(np.float32, copy=False), axis=0).astype(np.float32)


def _lowpass(audio: np.ndarray, cutoff_hz: float, sample_rate: int, order: int = 4) -> np.ndarray:
    sos = signal.butter(order, cutoff_hz / (sample_rate / 2), btype="lowpass", output="sos")
    return signal.sosfilt(sos, audio.astype(np.float32, copy=False), axis=0).astype(np.float32)


def _high_shelf_like(audio: np.ndarray, cutoff_hz: float, gain_db: float, sample_rate: int) -> np.ndarray:
    if gain_db == 0.0:
        return audio.astype(np.float32, copy=False)
    high = _highpass(audio, cutoff_hz, sample_rate, order=2)
    return (audio + high * (10.0 ** (gain_db / 20.0) - 1.0)).astype(np.float32)


def side_mid_ratio_db(mid: np.ndarray, side: np.ndarray) -> float:
    return round(linear_to_db((rms(side) + 1e-12) / (rms(mid) + 1e-12)), 2)


def mono_compatibility_metrics(audio: np.ndarray, sample_rate: int) -> dict[str, float | int]:
    stereo = to_stereo(audio)
    mid, side = mid_side_encode(stereo)
    low_mid = _lowpass(mid, 150.0, sample_rate)
    low_side = _lowpass(side, 150.0, sample_rate)
    folded = mono(stereo)
    stereo_peak = float(np.max(np.abs(stereo))) + 1e-12
    folded_peak = float(np.max(np.abs(folded))) + 1e-12
    stereo_rms = rms(stereo) + 1e-12
    folded_rms = rms(folded) + 1e-12
    corr = float(np.corrcoef(stereo[:, 0], stereo[:, 1])[0, 1]) if stereo.shape[0] > 8 else 1.0
    if not np.isfinite(corr):
        corr = 1.0
    return {
        "left_right_correlation": round(corr, 4),
        "side_mid_ratio_db": side_mid_ratio_db(mid, side),
        "low_side_mid_ratio_below_150hz_db": side_mid_ratio_db(low_mid, low_side),
        "mono_fold_peak_change_db": round(linear_to_db(folded_peak / stereo_peak), 2),
        "mono_fold_rms_change_db": round(linear_to_db(folded_rms / stereo_rms), 2),
        "clipping_count": clipping_count(stereo),
    }


def side_low_cut(audio: np.ndarray, sample_rate: int, cutoff_hz: float = 140.0) -> np.ndarray:
    mid, side = mid_side_encode(audio)
    side = _highpass(side, cutoff_hz, sample_rate, order=4)
    return mid_side_decode(mid, side)


def mid_side_eq(audio: np.ndarray, sample_rate: int, mid_moves: list[tuple[float, float, float]], side_moves: list[tuple[float, float, float]]) -> np.ndarray:
    mid, side = mid_side_encode(audio)
    for low_hz, high_hz, gain_db in mid_moves:
        mid = band_eq(mid, low_hz, high_hz, gain_db, sample_rate)
    for low_hz, high_hz, gain_db in side_moves:
        side = band_eq(side, low_hz, high_hz, gain_db, sample_rate)
    return mid_side_decode(mid, side)


def safe_mid_side_process(
    audio: np.ndarray,
    sample_rate: int,
    *,
    side_low_cut_hz: float = 140.0,
    side_upper_width_db: float = 0.0,
    side_air_lift_db: float = 0.0,
    max_side_lift_db: float = 2.0,
    mid_moves: list[tuple[float, float, float]] | None = None,
    min_correlation: float = 0.1,
    max_low_side_mid_db: float = -18.0,
) -> tuple[np.ndarray, dict[str, Any]]:
    before = mono_compatibility_metrics(audio, sample_rate)
    cutoff = side_low_cut_hz
    mid, side = mid_side_encode(audio)
    for low_hz, high_hz, gain_db in mid_moves or []:
        mid = band_eq(mid, low_hz, high_hz, gain_db, sample_rate)
    side = _highpass(side, cutoff, sample_rate, order=4)
    side = _high_shelf_like(side, 2_000.0, min(side_upper_width_db, max_side_lift_db), sample_rate)
    side = _high_shelf_like(side, 8_000.0, min(side_air_lift_db, max_side_lift_db), sample_rate)
    processed = mid_side_decode(mid, side)
    safety_actions: list[str] = []
    metrics = mono_compatibility_metrics(processed, sample_rate)
    if metrics["low_side_mid_ratio_below_150hz_db"] > max_low_side_mid_db:
        cutoff = max(cutoff, 180.0)
        side = _highpass(side, cutoff, sample_rate, order=4)
        processed = mid_side_decode(mid, side)
        metrics = mono_compatibility_metrics(processed, sample_rate)
        safety_actions.append("increased_side_low_cut_to_180hz")
    side_trim_db = 0.0
    while metrics["left_right_correlation"] < min_correlation and side_trim_db > -6.0:
        side_trim_db -= 1.0
        side *= 10.0 ** (-1.0 / 20.0)
        processed = mid_side_decode(mid, side)
        metrics = mono_compatibility_metrics(processed, sample_rate)
        safety_actions.append("reduced_side_gain_1db")
    if clipping_count(processed) > 0:
        peak = float(np.max(np.abs(processed))) + 1e-12
        processed = (processed / peak * 0.98).astype(np.float32)
        metrics = mono_compatibility_metrics(processed, sample_rate)
        safety_actions.append("peak_safety_normalized")
    return processed.astype(np.float32), {
        "side_low_cut_hz": cutoff,
        "side_upper_width_db": min(side_upper_width_db, max_side_lift_db),
        "side_air_lift_db": min(side_air_lift_db, max_side_lift_db),
        "side_trim_db": side_trim_db,
        "before": before,
        "after": metrics,
        "safety_actions": safety_actions,
        "peak_dbfs": round(peak_db(processed), 2),
    }

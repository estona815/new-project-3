from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from audio_metrics import bandpass, clipping_count, linear_to_db, mono, to_stereo
from masking_analysis import vocal_to_beat_masking_score


@dataclass(frozen=True)
class DynamicEQBand:
    low_hz: float
    high_hz: float
    threshold_db: float
    range_db: float
    ratio_slope: float = 0.35
    attack_ms: float = 8.0
    release_ms: float = 120.0
    mode: str = "cut"
    detector: str = "rms"
    sidechain: np.ndarray | None = None


DynamicBand = DynamicEQBand


def _smooth_detector(values: np.ndarray, sample_rate: int, attack_ms: float, release_ms: float) -> np.ndarray:
    attack = math.exp(-1.0 / max(1.0, (attack_ms / 1000.0) * sample_rate))
    release = math.exp(-1.0 / max(1.0, (release_ms / 1000.0) * sample_rate))
    out = np.zeros_like(values, dtype=np.float32)
    state = 0.0
    for index, value in enumerate(values):
        coeff = attack if value > state else release
        state = coeff * state + (1.0 - coeff) * float(value)
        out[index] = state
    return out


def envelope_follower(
    detector_signal: np.ndarray,
    sample_rate: int,
    low_hz: float | None = None,
    high_hz: float | None = None,
    attack_ms: float = 8.0,
    release_ms: float = 85.0,
    detector: str = "rms",
) -> np.ndarray:
    source = to_stereo(detector_signal)
    if low_hz is not None and high_hz is not None:
        source = bandpass(source, low_hz, high_hz, sample_rate, order=2)
    values = mono(source)
    if detector == "rms":
        smoothed_power = _smooth_detector(np.square(values, dtype=np.float32), sample_rate, attack_ms, release_ms)
        return np.sqrt(np.maximum(smoothed_power, 0.0)).astype(np.float32)
    if detector == "peak":
        return _smooth_detector(np.abs(values).astype(np.float32), sample_rate, attack_ms, release_ms)
    raise ValueError(f"Unsupported detector mode: {detector}")


def gain_envelope_for_band(
    detector_signal: np.ndarray,
    band: DynamicEQBand,
    sample_rate: int,
) -> dict[str, np.ndarray]:
    sidechain = band.sidechain if band.sidechain is not None else detector_signal
    env = envelope_follower(sidechain, sample_rate, band.low_hz, band.high_hz, band.attack_ms, band.release_ms, band.detector)
    env_db = np.array([linear_to_db(float(value) + 1e-9) for value in env], dtype=np.float32)
    over_db = np.maximum(env_db - band.threshold_db, 0.0)
    depth_db = np.minimum(abs(band.range_db), over_db * max(band.ratio_slope, 0.0))
    if band.mode == "cut":
        gain_db = -depth_db
    elif band.mode == "boost":
        gain_db = depth_db
    else:
        raise ValueError(f"Unsupported dynamic EQ mode: {band.mode}")
    gain_linear = np.power(10.0, gain_db / 20.0).astype(np.float32)
    return {"envelope_linear": env, "envelope_db": env_db, "gain_db": gain_db.astype(np.float32), "gain_linear": gain_linear}


def dynamic_band_process(audio: np.ndarray, detector_signal: np.ndarray, band: DynamicEQBand, sample_rate: int) -> tuple[np.ndarray, dict[str, float | str]]:
    if audio.size == 0:
        return audio.astype(np.float32, copy=False), {"max_gain_reduction_db": 0.0, "average_gain_reduction_db": 0.0}
    target_band = bandpass(audio, band.low_hz, band.high_hz, sample_rate, order=2)
    residual = audio.astype(np.float32, copy=False) - target_band
    envelopes = gain_envelope_for_band(detector_signal, band, sample_rate)
    gain = envelopes["gain_linear"]
    if gain.shape[0] < audio.shape[0]:
        gain = np.pad(gain, (0, audio.shape[0] - gain.shape[0]), constant_values=1.0)
    gain = gain[: audio.shape[0]]
    output = residual + target_band * gain[:, None]
    gain_db = envelopes["gain_db"]
    active_cut = gain_db[gain_db < -0.01]
    return output.astype(np.float32), {
        "low_hz": band.low_hz,
        "high_hz": band.high_hz,
        "threshold_db": band.threshold_db,
        "range_db": band.range_db,
        "ratio_slope": band.ratio_slope,
        "attack_ms": band.attack_ms,
        "release_ms": band.release_ms,
        "mode": band.mode,
        "detector": band.detector,
        "average_gain_reduction_db": round(float(np.mean(active_cut)) if active_cut.size else 0.0, 2),
        "max_gain_reduction_db": round(float(np.min(gain_db)) if gain_db.size else 0.0, 2),
        "peak_output_dbfs": round(linear_to_db(float(np.max(np.abs(output))) + 1e-12), 2),
        "clipping_count": clipping_count(output),
    }


def adaptive_harsh_threshold(vocal_bus: np.ndarray, sample_rate: int) -> float:
    env = envelope_follower(vocal_bus, sample_rate, 5_000.0, 8_000.0, attack_ms=4.0, release_ms=90.0, detector="rms")
    active = env[env > 1e-5]
    if active.size == 0:
        return -36.0
    return float(np.percentile([linear_to_db(float(value) + 1e-9) for value in active], 72))


def apply_vocal_triggered_beat_ducking(
    beat_bus: np.ndarray,
    vocal_bus: np.ndarray,
    sample_rate: int,
    *,
    include_harsh_band: bool = True,
) -> tuple[np.ndarray, dict[str, object]]:
    before = vocal_to_beat_masking_score(vocal_bus, beat_bus, sample_rate)
    processed = beat_bus.astype(np.float32, copy=True)
    band_reports: list[dict[str, float | str]] = []
    bands = [
        DynamicEQBand(200.0, 400.0, -32.0, -2.3, ratio_slope=0.32, attack_ms=20.0, release_ms=160.0, mode="cut", detector="rms"),
        DynamicEQBand(1_000.0, 4_000.0, -34.0, -3.2, ratio_slope=0.36, attack_ms=8.0, release_ms=120.0, mode="cut", detector="rms"),
    ]
    if include_harsh_band:
        bands.append(
            DynamicEQBand(6_000.0, 10_000.0, adaptive_harsh_threshold(vocal_bus, sample_rate), -1.6, ratio_slope=0.28, attack_ms=2.0, release_ms=80.0, mode="cut", detector="rms")
        )
    for band in bands:
        processed, report = dynamic_band_process(processed, vocal_bus, band, sample_rate)
        band_reports.append(report)
    after = vocal_to_beat_masking_score(vocal_bus, processed, sample_rate)
    return processed.astype(np.float32), {
        "type": "vocal_triggered_beat_ducking",
        "bands_applied": band_reports,
        "masking_score_before": before,
        "masking_score_after": after,
    }


def apply_harshness_triggered_vocal_cut(vocal_bus: np.ndarray, sample_rate: int) -> tuple[np.ndarray, dict[str, object]]:
    band = DynamicEQBand(3_000.0, 6_000.0, -31.0, -2.8, ratio_slope=0.34, attack_ms=2.0, release_ms=70.0, mode="cut", detector="rms")
    processed, report = dynamic_band_process(vocal_bus, vocal_bus, band, sample_rate)
    return processed, {"type": "self_triggered_vocal_harshness_cut", "bands_applied": [report]}

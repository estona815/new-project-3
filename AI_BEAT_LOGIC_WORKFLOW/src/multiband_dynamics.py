from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from audio_metrics import MASTER_BAND_RANGES, bandpass, db_to_linear, linear_to_db, peak_db, rms_db
from dynamic_eq import envelope_follower


@dataclass(frozen=True)
class CompressorBand:
    low_hz: float
    high_hz: float
    threshold_db: float
    ratio: float
    attack_ms: float
    release_ms: float
    makeup_db: float = 0.0
    min_gain_db: float = -10.0
    max_gain_db: float = 4.0
    upward_density_db: float = 0.0


DEFAULT_MASTER_BANDS: tuple[CompressorBand, ...] = (
    CompressorBand(20.0, 60.0, -22.5, 1.65, 35.0, 180.0, 0.2, -4.5, 2.0, 0.5),
    CompressorBand(60.0, 120.0, -23.0, 1.9, 28.0, 160.0, 0.15, -5.5, 2.0, 0.4),
    CompressorBand(120.0, 400.0, -25.0, 1.75, 18.0, 140.0, 0.15, -4.5, 2.0, 0.7),
    CompressorBand(400.0, 1_500.0, -26.5, 1.65, 12.0, 120.0, 0.1, -4.0, 2.0, 0.8),
    CompressorBand(1_500.0, 5_000.0, -28.0, 1.55, 6.0, 90.0, 0.1, -3.5, 1.8, 0.7),
    CompressorBand(5_000.0, 9_000.0, -30.0, 1.45, 3.0, 70.0, -0.05, -3.0, 1.2, 0.2),
    CompressorBand(9_000.0, 16_000.0, -32.0, 1.35, 2.0, 65.0, 0.0, -2.5, 1.2, 0.2),
)


def _gain_envelope_db(audio: np.ndarray, sample_rate: int, band: CompressorBand) -> np.ndarray:
    env = envelope_follower(audio, sample_rate, attack_ms=band.attack_ms, release_ms=band.release_ms)
    env_db = np.array([linear_to_db(float(value) + 1e-9) for value in env], dtype=np.float32)
    over_db = np.maximum(env_db - band.threshold_db, 0.0)
    reduction_db = -(over_db - over_db / max(band.ratio, 1.0))
    if band.upward_density_db > 0.0:
        under = np.maximum(band.threshold_db - env_db, 0.0)
        lift = np.minimum(under * 0.08, band.upward_density_db)
        reduction_db += lift
    gain_db = np.clip(reduction_db + band.makeup_db, band.min_gain_db, band.max_gain_db)
    if gain_db.shape[0] < audio.shape[0]:
        gain_db = np.pad(gain_db, (0, audio.shape[0] - gain_db.shape[0]), constant_values=band.makeup_db)
    return gain_db[: audio.shape[0]].astype(np.float32)


def envelope_compress(
    audio: np.ndarray,
    sample_rate: int,
    threshold_db: float,
    ratio: float,
    attack_ms: float,
    release_ms: float,
    makeup_db: float = 0.0,
) -> tuple[np.ndarray, dict[str, float]]:
    band = CompressorBand(0.0, sample_rate / 2 - 1.0, threshold_db, ratio, attack_ms, release_ms, makeup_db)
    gain_db = _gain_envelope_db(audio, sample_rate, band)
    gain = np.power(10.0, gain_db / 20.0).astype(np.float32)
    out = audio.astype(np.float32, copy=False) * gain[:, None]
    reduction = gain_db - makeup_db
    active = reduction[reduction < -0.05]
    return out.astype(np.float32), {
        "threshold_db": threshold_db,
        "ratio": ratio,
        "attack_ms": attack_ms,
        "release_ms": release_ms,
        "makeup_db": makeup_db,
        "max_gain_reduction_db": round(float(np.min(reduction)) if reduction.size else 0.0, 2),
        "mean_active_gain_reduction_db": round(float(np.mean(active)) if active.size else 0.0, 2),
    }


def split_bands(audio: np.ndarray, sample_rate: int, bands: list[CompressorBand] | tuple[CompressorBand, ...]) -> tuple[list[np.ndarray], np.ndarray]:
    samples = audio.astype(np.float32, copy=False)
    splits = [bandpass(samples, band.low_hz, band.high_hz, sample_rate) for band in bands]
    band_sum = np.sum(np.stack(splits, axis=0), axis=0) if splits else np.zeros_like(samples)
    residual = (samples - band_sum).astype(np.float32)
    return splits, residual


def process_band(audio: np.ndarray, sample_rate: int, band: CompressorBand) -> tuple[np.ndarray, dict[str, float]]:
    gain_db = _gain_envelope_db(audio, sample_rate, band)
    gain = np.power(10.0, gain_db / 20.0).astype(np.float32)
    processed = audio.astype(np.float32, copy=False) * gain[:, None]
    reduction = gain_db - band.makeup_db
    active = reduction[reduction < -0.05]
    return processed.astype(np.float32), {
        "low_hz": band.low_hz,
        "high_hz": band.high_hz,
        "threshold_db": band.threshold_db,
        "ratio": band.ratio,
        "attack_ms": band.attack_ms,
        "release_ms": band.release_ms,
        "makeup_db": band.makeup_db,
        "min_gain_db": band.min_gain_db,
        "max_gain_db": band.max_gain_db,
        "upward_density_db": band.upward_density_db,
        "max_gain_reduction_db": round(float(np.min(reduction)) if reduction.size else 0.0, 2),
        "mean_active_gain_reduction_db": round(float(np.mean(active)) if active.size else 0.0, 2),
        "peak_after_dbfs": round(peak_db(processed), 2),
        "rms_after_dbfs": round(rms_db(processed), 2),
    }


def multiband_compress(audio: np.ndarray, sample_rate: int, bands: list[CompressorBand]) -> tuple[np.ndarray, list[dict[str, float]]]:
    samples = audio.astype(np.float32, copy=False)
    splits, residual = split_bands(samples, sample_rate, bands)
    output = residual.copy()
    reports: list[dict[str, float]] = []
    for split, band in zip(splits, bands):
        processed, report = process_band(split, sample_rate, band)
        output += processed
        reports.append(report)
    peak = float(np.max(np.abs(output))) if output.size else 0.0
    if peak > 1.0:
        output *= 0.999 / peak
    return output.astype(np.float32), reports


def multiband_glue(
    audio: np.ndarray,
    sample_rate: int,
    bands: list[CompressorBand] | tuple[CompressorBand, ...] | None = None,
    parallel_density: float = 0.18,
) -> tuple[np.ndarray, dict[str, object]]:
    bands = tuple(bands or DEFAULT_MASTER_BANDS)
    compressed, band_reports = multiband_compress(audio, sample_rate, list(bands))
    density_bands = [
        CompressorBand(
            band.low_hz,
            band.high_hz,
            band.threshold_db + 3.5,
            max(1.2, band.ratio * 0.85),
            band.attack_ms,
            band.release_ms,
            band.makeup_db,
            band.min_gain_db,
            band.max_gain_db,
            max(band.upward_density_db, 0.6),
        )
        for band in bands
    ]
    density, density_reports = multiband_compress(audio, sample_rate, density_bands)
    blend = min(0.45, max(0.0, parallel_density))
    out = compressed * (1.0 - blend) + density * blend
    peak = float(np.max(np.abs(out))) if out.size else 0.0
    safety_gain = 1.0
    if peak > 1.0:
        safety_gain = 0.999 / peak
        out *= safety_gain
    return out.astype(np.float32), {
        "bands": [f"{name}:{low:g}-{high:g}Hz" for name, (low, high) in MASTER_BAND_RANGES.items()],
        "parallel_density": round(blend, 4),
        "band_reports": band_reports,
        "density_reports": density_reports,
        "safety_gain": round(safety_gain, 6),
        "peak_after_dbfs": round(peak_db(out), 2),
        "rms_after_dbfs": round(rms_db(out), 2),
    }

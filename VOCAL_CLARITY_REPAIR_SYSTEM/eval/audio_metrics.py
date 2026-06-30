from __future__ import annotations

from dataclasses import dataclass
import json
import math
from pathlib import Path
from typing import Any

import numpy as np
from scipy.io import wavfile


BANDS: dict[str, tuple[float, float | None]] = {
    "low": (20.0, 120.0),
    "sub": (20.0, 120.0),
    "low_mid": (120.0, 350.0),
    "body": (350.0, 1000.0),
    "nasal": (1000.0, 2000.0),
    "presence": (2000.0, 5000.0),
    "clarity": (4000.0, 8000.0),
    "air": (8000.0, 16000.0),
    "full": (20.0, None),
}


DEFAULT_THRESHOLDS: dict[str, dict[str, float]] = {
    "Bypass": {
        "presence_loss_fail_db": 0.50,
        "clarity_loss_fail_db": 0.50,
        "air_loss_fail_db": 0.75,
        "transient_loss_fail_db": 0.75,
        "residual_leakage_fail": 8.0,
        "stereo_width_loss_fail_db": 0.75,
    },
    "DSP Only": {
        "presence_loss_fail_db": 1.50,
        "clarity_loss_fail_db": 1.75,
        "air_loss_fail_db": 2.50,
        "transient_loss_fail_db": 1.50,
        "residual_leakage_fail": 35.0,
        "stereo_width_loss_fail_db": 2.00,
    },
    "Preserve": {
        "presence_loss_fail_db": 2.00,
        "clarity_loss_fail_db": 2.00,
        "air_loss_fail_db": 3.00,
        "transient_loss_fail_db": 2.00,
        "residual_leakage_fail": 40.0,
        "stereo_width_loss_fail_db": 2.00,
    },
    "Balanced": {
        "presence_loss_fail_db": 3.00,
        "clarity_loss_fail_db": 3.00,
        "air_loss_fail_db": 4.00,
        "transient_loss_fail_db": 3.00,
        "residual_leakage_fail": 50.0,
        "stereo_width_loss_fail_db": 3.00,
    },
    "Surgical AI Artifact": {
        "presence_loss_fail_db": 3.00,
        "clarity_loss_fail_db": 3.00,
        "air_loss_fail_db": 4.00,
        "transient_loss_fail_db": 3.00,
        "residual_leakage_fail": 55.0,
        "stereo_width_loss_fail_db": 3.00,
    },
    "Strong Test": {
        "presence_loss_fail_db": 6.00,
        "clarity_loss_fail_db": 6.00,
        "air_loss_fail_db": 8.00,
        "transient_loss_fail_db": 6.00,
        "residual_leakage_fail": 70.0,
        "stereo_width_loss_fail_db": 6.00,
    },
}

DEFAULT_THRESHOLDS["DSP Only Safe"] = DEFAULT_THRESHOLDS["DSP Only"]
DEFAULT_THRESHOLDS["AI Metallic Surgical"] = DEFAULT_THRESHOLDS["Surgical AI Artifact"]
DEFAULT_THRESHOLDS["Hiss / Room Tone Gentle"] = DEFAULT_THRESHOLDS["Preserve"]
DEFAULT_THRESHOLDS["Voiceover Clean"] = DEFAULT_THRESHOLDS["Balanced"]
DEFAULT_THRESHOLDS["Strong Test / Repair"] = DEFAULT_THRESHOLDS["Strong Test"]
DEFAULT_THRESHOLDS["Side Noise Cleanup"] = DEFAULT_THRESHOLDS["Balanced"]
DEFAULT_THRESHOLDS["Artifact Focus Low Denoise"] = DEFAULT_THRESHOLDS["Preserve"]


@dataclass(frozen=True)
class AudioBuffer:
    sample_rate: int
    samples: np.ndarray


def read_wav(path: Path) -> AudioBuffer:
    sample_rate, data = wavfile.read(path)
    data = np.asarray(data)
    if data.ndim == 1:
        data = data[:, None]
    if np.issubdtype(data.dtype, np.integer):
        scale = float(np.iinfo(data.dtype).max)
        samples = data.astype(np.float32) / max(scale, 1.0)
    else:
        samples = data.astype(np.float32)
    return AudioBuffer(sample_rate=int(sample_rate), samples=np.nan_to_num(samples, copy=False))


def write_wav(path: Path, audio: AudioBuffer) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = np.nan_to_num(audio.samples, copy=True)
    data = np.clip(data, -1.0, 1.0)
    wavfile.write(path, audio.sample_rate, (data * 32767.0).astype(np.int16))


def align_pair(a: np.ndarray, b: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    length = min(len(a), len(b))
    if length <= 0:
        return a[:0], b[:0]
    channels = min(a.shape[1], b.shape[1])
    return a[:length, :channels], b[:length, :channels]


def rms(samples: np.ndarray) -> float:
    if samples.size == 0:
        return 0.0
    return float(np.sqrt(np.mean(np.square(samples.astype(np.float64)))))


def db(value: float, floor: float = 1.0e-12) -> float:
    return 20.0 * math.log10(max(float(value), floor))


def energy_db(value: float, floor: float = 1.0e-24) -> float:
    return 10.0 * math.log10(max(float(value), floor))


def ratio_db(numerator: float, denominator: float) -> float:
    return db(numerator) - db(denominator)


def energy_ratio_db(numerator: float, denominator: float) -> float:
    return energy_db(numerator) - energy_db(denominator)


def finite_counts(samples: np.ndarray) -> dict[str, int]:
    if samples.size == 0:
        return {"nan_count": 0, "inf_count": 0, "non_finite_count": 0}
    nan_count = int(np.count_nonzero(np.isnan(samples)))
    inf_count = int(np.count_nonzero(np.isinf(samples)))
    return {
        "nan_count": nan_count,
        "inf_count": inf_count,
        "non_finite_count": nan_count + inf_count,
    }


def sanitize_for_metrics(samples: np.ndarray) -> np.ndarray:
    return np.nan_to_num(samples.astype(np.float64), copy=True, nan=0.0, posinf=0.0, neginf=0.0)


def peak(samples: np.ndarray) -> float:
    if samples.size == 0:
        return 0.0
    return float(np.max(np.abs(samples)))


def dc_offset(samples: np.ndarray) -> float:
    if samples.size == 0:
        return 0.0
    return float(np.mean(samples))


def clipping_count(samples: np.ndarray, threshold: float = 0.999) -> int:
    if samples.size == 0:
        return 0
    return int(np.count_nonzero(np.abs(samples) >= threshold))


def mono(samples: np.ndarray) -> np.ndarray:
    if samples.ndim == 1:
        return samples.astype(np.float64)
    return np.mean(samples.astype(np.float64), axis=1)


def frame_rms(samples: np.ndarray, frame_size: int = 1024, hop_size: int = 512) -> np.ndarray:
    x = mono(samples)
    if len(x) == 0:
        return np.zeros(0, dtype=np.float64)
    if len(x) < frame_size:
        return np.array([rms(x)], dtype=np.float64)
    frames = []
    for start in range(0, len(x) - frame_size + 1, hop_size):
        frames.append(rms(x[start : start + frame_size]))
    return np.asarray(frames, dtype=np.float64)


def active_frame_mask(samples: np.ndarray, frame_size: int = 1024, hop_size: int = 512) -> tuple[np.ndarray, float]:
    levels = frame_rms(samples, frame_size, hop_size)
    if levels.size == 0:
        return np.zeros(0, dtype=bool), 0.0
    noise_floor = float(np.percentile(levels, 20))
    max_level = float(np.max(levels))
    if max_level <= 1.0e-8:
        return np.zeros_like(levels, dtype=bool), 1.0e-8
    if noise_floor > 1.0e-8 and max_level / noise_floor < 3.0:
        threshold = max(max_level * 0.50, 1.0e-5)
    else:
        threshold = max(noise_floor * 4.0, max_level * 0.08, 1.0e-5)
    return levels >= threshold, threshold


def samples_from_frame_mask(samples: np.ndarray, mask: np.ndarray, frame_size: int = 1024, hop_size: int = 512) -> np.ndarray:
    if mask.size == 0:
        return samples[:0]
    keep = np.zeros(len(samples), dtype=bool)
    for idx, is_active in enumerate(mask):
        if is_active:
            start = idx * hop_size
            keep[start : min(start + frame_size, len(samples))] = True
    return samples[keep]


def band_energy(samples: np.ndarray, sample_rate: int, low_hz: float, high_hz: float | None) -> float:
    x = mono(samples)
    if len(x) < 2:
        return 0.0
    window = np.hanning(len(x))
    spectrum = np.fft.rfft(x * window)
    freqs = np.fft.rfftfreq(len(x), 1.0 / sample_rate)
    hi = sample_rate * 0.5 if high_hz is None else min(high_hz, sample_rate * 0.5)
    mask = (freqs >= low_hz) & (freqs < hi)
    if not np.any(mask):
        return 0.0
    return float(np.mean(np.square(np.abs(spectrum[mask]))))


def band_energies(samples: np.ndarray, sample_rate: int) -> dict[str, float]:
    return {name: band_energy(samples, sample_rate, lo, hi) for name, (lo, hi) in BANDS.items()}


def band_metric_report(input_bands: dict[str, float], processed_bands: dict[str, float], residual_bands: dict[str, float]) -> dict[str, dict[str, float | None]]:
    report: dict[str, dict[str, float | None]] = {}
    for name in BANDS:
        input_energy = input_bands[name]
        processed_energy = processed_bands[name]
        residual_energy = residual_bands[name]
        unavailable = input_energy <= 0.0 and processed_energy <= 0.0 and residual_energy <= 0.0
        report[name] = {
            "input_band_energy_db": None if unavailable else energy_db(input_energy),
            "processed_band_energy_db": None if unavailable else energy_db(processed_energy),
            "residual_band_energy_db": None if unavailable else energy_db(residual_energy),
            "processed_delta_db": None if unavailable else energy_ratio_db(processed_energy, input_energy),
            "residual_to_input_ratio_db": None if unavailable else energy_ratio_db(residual_energy, input_energy),
        }
    return report


def stereo_width(samples: np.ndarray) -> dict[str, float]:
    if samples.ndim != 2 or samples.shape[1] < 2 or len(samples) == 0:
        return {"mid_rms": rms(samples), "side_rms": 0.0, "side_mid_ratio_db": -120.0, "lr_correlation": 1.0}
    left = samples[:, 0].astype(np.float64)
    right = samples[:, 1].astype(np.float64)
    mid = 0.5 * (left + right)
    side = 0.5 * (left - right)
    mid_r = rms(mid)
    side_r = rms(side)
    corr = float(np.corrcoef(left, right)[0, 1]) if rms(left) > 1.0e-8 and rms(right) > 1.0e-8 else 1.0
    if not math.isfinite(corr):
        corr = 1.0
    return {
        "mid_rms": mid_r,
        "side_rms": side_r,
        "side_mid_ratio_db": ratio_db(side_r, mid_r),
        "lr_correlation": corr,
    }


def transient_features(samples: np.ndarray, sample_rate: int) -> dict[str, float]:
    levels = frame_rms(samples, frame_size=max(128, sample_rate // 200), hop_size=max(64, sample_rate // 400))
    if levels.size < 2:
        return {"count": 0.0, "peak": float(levels[0]) if levels.size else 0.0, "flux": 0.0}
    diff = np.maximum(np.diff(levels), 0.0)
    threshold = max(float(np.percentile(diff, 90)), 1.0e-7)
    return {
        "count": float(np.count_nonzero(diff > threshold)),
        "peak": float(np.max(levels)),
        "flux": float(np.sum(diff)),
    }


def loudness_match(original: np.ndarray, processed: np.ndarray, max_gain_db: float = 18.0) -> tuple[np.ndarray, float]:
    original_rms = rms(original)
    processed_rms = rms(processed)
    if original_rms <= 1.0e-10 or processed_rms <= 1.0e-10:
        return processed.copy(), 0.0
    gain = original_rms / processed_rms
    gain_db = float(np.clip(db(gain), -max_gain_db, max_gain_db))
    safe_gain = 10.0 ** (gain_db / 20.0)
    return np.clip(processed * safe_gain, -1.0, 1.0), gain_db


def compute_residual(original: np.ndarray, processed: np.ndarray, latency_samples: int = 0) -> np.ndarray:
    x, y = align_pair(original, processed)
    latency = int(latency_samples)
    if latency > 0:
        if latency >= len(x) or latency >= len(y):
            return x[:0] - y[:0]
        x = x[latency:]
        y = y[:-latency]
    elif latency < 0:
        shift = abs(latency)
        if shift >= len(x) or shift >= len(y):
            return x[:0] - y[:0]
        x = x[:-shift]
        y = y[shift:]
    x, y = align_pair(x, y)
    return sanitize_for_metrics(x) - sanitize_for_metrics(y)


def _score_from_loss(loss_db: float, fail_db: float) -> float:
    if fail_db <= 0:
        return 0.0
    return float(np.clip(100.0 * (1.0 - max(0.0, loss_db) / fail_db), 0.0, 100.0))


def evaluate_pair(
    original: AudioBuffer,
    processed: AudioBuffer,
    *,
    preset: str,
    expected_behavior: str = "mixed",
) -> dict[str, Any]:
    if original.sample_rate != processed.sample_rate:
        raise ValueError("sample rates must match for evaluation")
    x_raw, y_raw = align_pair(original.samples, processed.samples)
    input_finite = finite_counts(x_raw)
    processed_finite = finite_counts(y_raw)
    x = sanitize_for_metrics(x_raw)
    y = sanitize_for_metrics(y_raw)
    residual = compute_residual(x, y)
    active_mask, active_threshold = active_frame_mask(x)
    x_active = samples_from_frame_mask(x, active_mask)
    y_active = samples_from_frame_mask(y, active_mask)
    residual_active = samples_from_frame_mask(residual, active_mask)
    x_gap = x if active_mask.size == 0 else samples_from_frame_mask(x, ~active_mask)
    y_gap = y if active_mask.size == 0 else samples_from_frame_mask(y, ~active_mask)

    input_bands = band_energies(x, original.sample_rate)
    processed_bands = band_energies(y, original.sample_rate)
    residual_bands = band_energies(residual, original.sample_rate)
    band_report = band_metric_report(input_bands, processed_bands, residual_bands)
    active_input_bands = band_energies(x_active if len(x_active) else x[:0], original.sample_rate)
    active_processed_bands = band_energies(y_active if len(y_active) else y[:0], original.sample_rate)

    band_delta_db = {
        name: ratio_db(processed_bands[name], input_bands[name])
        for name in BANDS
    }
    active_band_delta_db = {
        name: ratio_db(active_processed_bands[name], active_input_bands[name])
        for name in BANDS
    }

    presence_loss = max(0.0, -active_band_delta_db["presence"])
    clarity_loss = max(0.0, -active_band_delta_db["clarity"])
    air_loss = max(0.0, -active_band_delta_db["air"])
    input_tilt = ratio_db(input_bands["presence"] + input_bands["clarity"], input_bands["body"])
    processed_tilt = ratio_db(processed_bands["presence"] + processed_bands["clarity"], processed_bands["body"])
    tilt_loss = max(0.0, input_tilt - processed_tilt)

    input_trans = transient_features(x, original.sample_rate)
    processed_trans = transient_features(y, original.sample_rate)
    residual_trans = transient_features(residual, original.sample_rate)
    transient_loss = max(0.0, ratio_db(input_trans["peak"], processed_trans["peak"]))
    transient_preservation_ratio = processed_trans["flux"] / max(input_trans["flux"], 1.0e-12)

    protected_input = input_bands["presence"] + input_bands["clarity"] + input_bands["air"] + 1.0e-12
    protected_residual = residual_bands["presence"] + residual_bands["clarity"] + residual_bands["air"]
    residual_presence_ratio_db = energy_ratio_db(residual_bands["presence"], input_bands["presence"])
    residual_clarity_ratio_db = energy_ratio_db(residual_bands["clarity"], input_bands["clarity"])
    residual_air_ratio_db = energy_ratio_db(residual_bands["air"], input_bands["air"])
    corr = 0.0
    if x.size and residual.size and rms(x) > 1.0e-8 and rms(residual) > 1.0e-8:
        corr = float(np.corrcoef(mono(x), mono(residual))[0, 1])
        if not math.isfinite(corr):
            corr = 0.0
    residual_source_leakage = float(np.clip(100.0 * protected_residual / protected_input + 25.0 * max(corr, 0.0), 0.0, 100.0))

    gap_noise_reduction_db = max(0.0, ratio_db(rms(x_gap), rms(y_gap))) if len(x_gap) else 0.0
    width_in = stereo_width(x)
    width_out = stereo_width(y)
    stereo_width_change_db = width_out["side_mid_ratio_db"] - width_in["side_mid_ratio_db"]
    stereo_width_loss_db = max(0.0, -stereo_width_change_db)

    thresholds = DEFAULT_THRESHOLDS.get(preset, DEFAULT_THRESHOLDS["Preserve"])
    warnings: list[str] = []
    failures: list[str] = []

    def check(metric: float, key: str, tag: str) -> None:
        limit = thresholds[key]
        if metric > limit:
            failures.append(tag)
        elif metric > limit * 0.70:
            warnings.append(tag)

    check(presence_loss, "presence_loss_fail_db", "vocal_presence_loss")
    check(clarity_loss, "clarity_loss_fail_db", "consonant_loss")
    check(air_loss, "air_loss_fail_db", "air_loss")
    check(transient_loss, "transient_loss_fail_db", "transient_smear")
    check(residual_source_leakage, "residual_leakage_fail", "residual_ghost_vocal")
    check(stereo_width_loss_db, "stereo_width_loss_fail_db", "stereo_collapse")

    input_clips = clipping_count(x)
    processed_clips = clipping_count(y)
    if processed_clips > input_clips:
        failures.append("clipping")
    if processed_finite["non_finite_count"] > 0 or input_finite["non_finite_count"] > 0 or not np.all(np.isfinite(residual)):
        failures.append("nan_inf")
    if expected_behavior == "do_no_harm" and rms(residual_active) > max(rms(x_active) * 0.12, 1.0e-5):
        warnings.append("clean_input_damage")

    scores = {
        "noise_reduction": float(np.clip(gap_noise_reduction_db * 12.0, 0.0, 100.0)),
        "source_preservation": min(
            _score_from_loss(presence_loss, thresholds["presence_loss_fail_db"]),
            _score_from_loss(clarity_loss, thresholds["clarity_loss_fail_db"]),
        ),
        "clarity": _score_from_loss(clarity_loss, thresholds["clarity_loss_fail_db"]),
        "air": _score_from_loss(air_loss, thresholds["air_loss_fail_db"]),
        "transient": _score_from_loss(transient_loss, thresholds["transient_loss_fail_db"]),
        "residual_cleanliness": float(np.clip(100.0 - residual_source_leakage, 0.0, 100.0)),
        "stereo": _score_from_loss(stereo_width_loss_db, thresholds["stereo_width_loss_fail_db"]),
        "safety": 0.0 if ("nan_inf" in failures or "clipping" in failures) else 100.0,
    }
    scores["overall"] = (
        0.15 * scores["noise_reduction"]
        + 0.25 * scores["source_preservation"]
        + 0.15 * scores["clarity"]
        + 0.10 * scores["air"]
        + 0.10 * scores["transient"]
        + 0.15 * scores["residual_cleanliness"]
        + 0.05 * scores["stereo"]
        + 0.05 * scores["safety"]
    )

    status = "fail" if failures and preset != "Strong Test" else "warning" if warnings or failures else "pass"
    return {
        "duration_sec": float(len(x) / original.sample_rate) if original.sample_rate else 0.0,
        "active_region": {
            "frame_count": int(active_mask.size),
            "active_frame_count": int(np.count_nonzero(active_mask)),
            "threshold_rms": active_threshold,
        },
        "level": {
            "input_rms": rms(x),
            "processed_rms": rms(y),
            "input_rms_db": db(rms(x)),
            "processed_rms_db": db(rms(y)),
            "rms_delta_db": ratio_db(rms(y), rms(x)),
            "input_peak": peak(x),
            "processed_peak": peak(y),
            "input_peak_db": db(peak(x)),
            "processed_peak_db": db(peak(y)),
            "input_clipping_count": input_clips,
            "processed_clipping_count": processed_clips,
            "clipping_count_input": input_clips,
            "clipping_count_processed": processed_clips,
            "input_dc_offset": dc_offset(x),
            "processed_dc_offset": dc_offset(y),
        },
        "bands": {
            "input_energy": input_bands,
            "processed_energy": processed_bands,
            "residual_energy": residual_bands,
            "report": band_report,
            "delta_db": band_delta_db,
            "active_delta_db": active_band_delta_db,
        },
        "preservation": {
            "presence_loss_db": presence_loss,
            "clarity_loss_db": clarity_loss,
            "air_loss_db": air_loss,
            "spectral_tilt_loss_db": tilt_loss,
            "transient_preservation_ratio": transient_preservation_ratio,
        },
        "residual": {
            "residual_rms": rms(residual),
            "residual_rms_db": db(rms(residual)),
            "residual_presence_ratio_db": residual_presence_ratio_db,
            "residual_clarity_ratio_db": residual_clarity_ratio_db,
            "residual_air_ratio_db": residual_air_ratio_db,
            "residual_transient_score": residual_trans["flux"],
            "source_leakage_score": residual_source_leakage,
            "definition": "inputAligned - processedAligned",
        },
        "safety": {
            "input_nan_count": input_finite["nan_count"],
            "input_inf_count": input_finite["inf_count"],
            "processed_nan_count": processed_finite["nan_count"],
            "processed_inf_count": processed_finite["inf_count"],
            "nan_count": input_finite["nan_count"] + processed_finite["nan_count"],
            "inf_count": input_finite["inf_count"] + processed_finite["inf_count"],
            "clipping_count": max(0, processed_clips - input_clips),
            "clipping_count_input": input_clips,
            "clipping_count_processed": processed_clips,
        },
        "metrics": {
            "presence_loss_db": presence_loss,
            "clarity_loss_db": clarity_loss,
            "air_loss_db": air_loss,
            "tilt_loss_db": tilt_loss,
            "spectral_tilt_loss_db": tilt_loss,
            "low_mid_change_db": band_delta_db["low_mid"],
            "transient_count_input": input_trans["count"],
            "transient_count_processed": processed_trans["count"],
            "transient_peak_loss_db": transient_loss,
            "transient_preservation_ratio": transient_preservation_ratio,
            "onset_flux_ratio": transient_preservation_ratio,
            "residual_transient_score": residual_trans["flux"],
            "residual_source_leakage_score": residual_source_leakage,
            "residual_presence_ratio_db": residual_presence_ratio_db,
            "residual_clarity_ratio_db": residual_clarity_ratio_db,
            "residual_air_ratio_db": residual_air_ratio_db,
            "residual_to_input_correlation": corr,
            "noise_reduction_db": gap_noise_reduction_db,
            "stereo_width_change_db": stereo_width_change_db,
            "stereo_width_loss_db": stereo_width_loss_db,
        },
        "stereo": {
            "input": width_in,
            "processed": width_out,
        },
        "scores": scores,
        "status": status,
        "warnings": sorted(set(warnings)),
        "failures": sorted(set(failures)),
    }


def save_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

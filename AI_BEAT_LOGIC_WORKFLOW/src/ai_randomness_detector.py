from __future__ import annotations

from typing import Any

import numpy as np
from scipy import signal

from section_detector import detect_sections, frame_energy_features
from transition_detector import detect_abrupt_transitions


def _rms(values: np.ndarray) -> float:
    if values.size == 0:
        return 0.0
    return float(np.sqrt(np.mean(np.square(values, dtype=np.float64))))


def _bandpass(samples: np.ndarray, sample_rate: int, low: float, high: float) -> np.ndarray:
    if sample_rate <= 0 or samples.size == 0 or high >= sample_rate / 2 or low >= high:
        return samples.astype(np.float32)
    sos = signal.butter(2, [low, high], fs=sample_rate, btype="bandpass", output="sos")
    return signal.sosfilt(sos, samples).astype(np.float32)


def _boundary_times(sections: list[dict[str, Any]]) -> list[float]:
    return [float(section.get("start", 0.0)) for section in sections[1:]]


def _near_boundary(time: float, boundaries: list[float], tolerance: float = 1.25) -> bool:
    return any(abs(time - boundary) <= tolerance for boundary in boundaries)


def _high_band_windows(samples: np.ndarray, sample_rate: int, window_seconds: float = 1.0) -> list[dict[str, float]]:
    window = max(1, int(window_seconds * sample_rate))
    high = _bandpass(samples, sample_rate, 5_500.0, min(12_000.0, sample_rate / 2 - 100.0))
    full = samples.astype(np.float32)
    rows: list[dict[str, float]] = []
    for start in range(0, samples.size, window):
        end = min(samples.size, start + window)
        if end - start < max(64, int(sample_rate * 0.2)):
            continue
        high_rms = _rms(high[start:end])
        full_rms = _rms(full[start:end]) + 1e-12
        rows.append({"start": start / sample_rate, "end": end / sample_rate, "ratio": high_rms / full_rms, "full_rms": full_rms})
    return rows


def detect_ai_randomness(mono_samples: list[float] | np.ndarray, sample_rate: int) -> dict[str, Any]:
    samples = np.asarray(mono_samples, dtype=np.float32)
    features = frame_energy_features(samples.tolist(), sample_rate)
    duration = float(samples.size / sample_rate) if sample_rate > 0 else 0.0
    sections = detect_sections(features, duration)
    boundaries = _boundary_times(sections)
    abrupt = detect_abrupt_transitions(features)
    high_rows = _high_band_windows(samples, sample_rate)

    random_risers: list[dict[str, Any]] = []
    for left, mid, right in zip(high_rows, high_rows[1:], high_rows[2:]):
        if left["ratio"] < mid["ratio"] < right["ratio"] and right["ratio"] > 0.33 and not _near_boundary(float(right["start"]), boundaries):
            random_risers.append(
                {
                    "start": round(float(left["start"]), 3),
                    "end": round(float(right["end"]), 3),
                    "confidence": "low",
                    "reason": "high-band ramp is not close to a detected section boundary",
                }
            )

    glitch_bursts: list[dict[str, Any]] = []
    for row in high_rows:
        if row["ratio"] > 0.42 and row["full_rms"] > 0.015 and not _near_boundary(float(row["start"]), boundaries):
            glitch_bursts.append(
                {
                    "start": round(float(row["start"]), 3),
                    "end": round(float(row["end"]), 3),
                    "confidence": "medium",
                    "reason": "bright/noisy burst away from section boundary",
                }
            )

    sudden_texture_swaps = [
        item
        for item in abrupt
        if not _near_boundary(float(item.get("start", 0.0)), boundaries)
    ]

    overly_long_static_regions: list[dict[str, Any]] = []
    if len(features) >= 3:
        run_start: float | None = None
        previous_energy: float | None = None
        max_energy = max(float(item.get("energy", 0.0)) for item in features) + 1e-12
        for frame in features:
            energy = float(frame.get("energy", 0.0))
            is_static = previous_energy is not None and abs(energy - previous_energy) / max_energy < 0.02
            if is_static and run_start is None:
                run_start = float(frame.get("start", 0.0))
            elif not is_static and run_start is not None:
                if float(frame.get("start", 0.0)) - run_start >= 8.0:
                    overly_long_static_regions.append(
                        {"start": round(run_start, 3), "end": round(float(frame.get("start", 0.0)), 3), "confidence": "medium"}
                    )
                run_start = None
            previous_energy = energy

    call_response_missing = len(sections) < 3 or len({section.get("name") for section in sections}) <= 1
    raw_risk = (
        min(0.35, len(random_risers) * 0.10)
        + min(0.35, len(glitch_bursts) * 0.09)
        + min(0.25, len(sudden_texture_swaps) * 0.08)
        + min(0.25, len(overly_long_static_regions) * 0.12)
        + (0.15 if call_response_missing else 0.0)
    )
    risk_score = max(0.0, min(1.0, raw_risk))
    risk = "high" if risk_score >= 0.58 else "medium" if risk_score >= 0.28 else "low"
    return {
        "randomness_risk": risk,
        "randomness_score": round(risk_score, 4),
        "random_risers": random_risers[:12],
        "glitch_bursts_not_tied_to_sections": glitch_bursts[:12],
        "sudden_texture_swaps": sudden_texture_swaps[:12],
        "overly_long_static_regions": overly_long_static_regions[:12],
        "no_call_response": bool(call_response_missing),
        "section_boundaries": [round(value, 3) for value in boundaries],
        "limitations": ["AI randomness detection is heuristic and should be confirmed by listening."],
    }

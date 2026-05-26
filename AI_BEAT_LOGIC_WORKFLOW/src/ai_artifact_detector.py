from __future__ import annotations

from typing import Any


def detect_repeated_ai_loops(features: list[dict[str, Any]], limit: int = 12) -> list[dict[str, Any]]:
    repeated: list[dict[str, Any]] = []
    for left, right in zip(features, features[1:]):
        energy_delta = abs(float(left["energy"]) - float(right["energy"]))
        onset_delta = abs(float(left["onset_density"]) - float(right["onset_density"]))
        if energy_delta < 0.002 and onset_delta < 0.002:
            repeated.append(
                {
                    "start": round(float(left["start"]), 3),
                    "end": round(float(right["end"]), 3),
                    "confidence": "low",
                    "reason": "adjacent windows have nearly identical energy/onset contour; possible repeated AI loop",
                }
            )
    return repeated[:limit]


def detect_over_compressed_sections(features: list[dict[str, Any]], limit: int = 12) -> list[dict[str, Any]]:
    if not features:
        return []
    energies = [float(item["energy"]) for item in features]
    high = max(energies) or 1.0
    candidates = []
    for frame in features:
        if float(frame["energy"]) / high >= 0.85 and float(frame["novelty"]) < high * 0.02:
            candidates.append(
                {
                    "start": round(float(frame["start"]), 3),
                    "end": round(float(frame["end"]), 3),
                    "confidence": "low",
                    "reason": "high energy with low novelty; possible flat/over-compressed section",
                }
            )
    return candidates[:limit]


def detect_low_end_excess_proxy(samples: list[float], sample_rate: int, window_seconds: float = 2.0) -> list[dict[str, Any]]:
    if sample_rate <= 0 or not samples:
        return []
    window = max(1, int(sample_rate * window_seconds))
    candidates: list[dict[str, Any]] = []
    for start in range(0, len(samples), window):
        end = min(len(samples), start + window)
        chunk = samples[start:end]
        if len(chunk) < 2:
            continue
        smoothness = sum(abs(right - left) for left, right in zip(chunk, chunk[1:])) / max(1, len(chunk) - 1)
        energy = sum(sample * sample for sample in chunk) / len(chunk)
        if energy > 0.02 and smoothness < 0.025:
            candidates.append({"start": round(start / sample_rate, 3), "end": round(end / sample_rate, 3), "confidence": "low", "reason": "low-delta high-energy proxy; possible low-end excess"})
    return candidates[:12]

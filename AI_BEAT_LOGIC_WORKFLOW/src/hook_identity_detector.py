from __future__ import annotations

import math
from typing import Any

import numpy as np

from lead_melody_presence import _dominant_band_frequency


def _score_1_to_5(value: float) -> int:
    return max(1, min(5, int(round(1.0 + 4.0 * max(0.0, min(1.0, value))))))


def _rms(values: np.ndarray) -> float:
    if values.size == 0:
        return 0.0
    return float(np.sqrt(np.mean(np.square(values, dtype=np.float64))))


def _chunk_signature(chunk: np.ndarray, sample_rate: int, steps: int = 8) -> dict[str, Any]:
    if chunk.size == 0:
        return {"energy": 0.0, "pitches": [], "contour_strength": 0.0}
    sub_size = max(1, chunk.size // steps)
    energies: list[float] = []
    pitches: list[int] = []
    confidences: list[float] = []
    for index in range(steps):
        frame = chunk[index * sub_size : min(chunk.size, (index + 1) * sub_size)]
        if frame.size == 0:
            continue
        energies.append(_rms(frame))
        frequency, confidence = _dominant_band_frequency(frame, sample_rate)
        if frequency:
            pitches.append(int(round(69 + 12 * math.log2(frequency / 440.0))))
            confidences.append(float(confidence))
    energy_norm = np.asarray(energies, dtype=np.float32)
    if energy_norm.size and float(np.max(energy_norm)) > 0:
        energy_norm = energy_norm / float(np.max(energy_norm))
    contour_changes = sum(1 for left, right in zip(pitches, pitches[1:]) if left != right)
    contour_strength = min(1.0, contour_changes / max(1, len(pitches) - 1)) * (sum(confidences) / max(1, len(confidences)))
    return {
        "energy": _rms(chunk),
        "energy_shape": [round(float(value), 4) for value in energy_norm.tolist()],
        "pitches": pitches,
        "contour_strength": round(float(contour_strength), 4),
    }


def _shape_similarity(left: list[float], right: list[float]) -> float:
    if not left or not right:
        return 0.0
    n = min(len(left), len(right))
    a = np.asarray(left[:n], dtype=np.float32)
    b = np.asarray(right[:n], dtype=np.float32)
    denom = float(np.linalg.norm(a) * np.linalg.norm(b))
    if denom <= 1e-12:
        return 0.0
    return max(0.0, min(1.0, float(np.dot(a, b) / denom)))


def _pitch_similarity(left: list[int], right: list[int]) -> float:
    if not left or not right:
        return 0.0
    n = min(len(left), len(right))
    matches = sum(1 for a, b in zip(left[:n], right[:n]) if abs(a - b) <= 1)
    return matches / max(1, n)


def _best_non_adjacent_return(signatures: list[dict[str, Any]]) -> float:
    if len(signatures) < 2:
        return 0.0
    best = 0.0
    for index, left in enumerate(signatures):
        for other_index, right in enumerate(signatures[index + 1 :], start=index + 1):
            if abs(other_index - index) <= 1:
                continue
            shape = _shape_similarity(left["energy_shape"], right["energy_shape"])
            pitch = _pitch_similarity(left["pitches"], right["pitches"])
            best = max(best, 0.55 * shape + 0.45 * pitch)
    return best


def detect_hook_identity(mono_samples: list[float] | np.ndarray, sample_rate: int, segment_seconds: float = 4.0) -> dict[str, Any]:
    samples = np.asarray(mono_samples, dtype=np.float32)
    if sample_rate <= 0 or samples.size < int(sample_rate * segment_seconds * 2):
        return {
            "hook_identity": 1,
            "motif_repetition_quality": 1,
            "call_response_quality": 1,
            "energy_melody_peak": 1,
            "score": 1.0,
            "diagnosis": "weak_or_absent",
            "hook_candidates": [],
            "reason": "Audio is too short for repeated hook identity detection.",
        }

    segment_size = max(1, int(segment_seconds * sample_rate))
    signatures: list[dict[str, Any]] = []
    for start in range(0, samples.size - segment_size + 1, segment_size):
        chunk = samples[start : start + segment_size]
        signature = _chunk_signature(chunk, sample_rate)
        signature["start"] = round(start / sample_rate, 3)
        signature["end"] = round((start + segment_size) / sample_rate, 3)
        signatures.append(signature)

    energies = [float(item["energy"]) for item in signatures]
    max_energy = max(energies) if energies else 0.0
    median_energy = float(np.median(energies)) if energies else 0.0
    energy_peak_clarity = 0.0 if max_energy <= 1e-12 else max(0.0, min(1.0, (max_energy - median_energy) / max_energy))
    motif_return = _best_non_adjacent_return(signatures)
    contour_strength = max((float(item["contour_strength"]) for item in signatures), default=0.0)
    call_response = min(1.0, 0.55 * motif_return + 0.45 * contour_strength)

    combined = 0.38 * motif_return + 0.30 * energy_peak_clarity + 0.22 * contour_strength + 0.10 * call_response
    if energy_peak_clarity < 0.12 and contour_strength < 0.18:
        combined = min(combined, 0.30)
    if motif_return < 0.25:
        combined = min(combined, 0.42)
    hook_score = _score_1_to_5(combined)
    motif_score = _score_1_to_5(motif_return)
    call_score = _score_1_to_5(call_response)
    peak_score = _score_1_to_5(energy_peak_clarity)
    diagnosis = "present" if hook_score >= 4 else "unclear" if hook_score == 3 else "weak_or_absent"
    candidates = sorted(
        [
            {
                "start": item["start"],
                "end": item["end"],
                "energy": round(float(item["energy"]), 6),
                "contour_strength": item["contour_strength"],
            }
            for item in signatures
        ],
        key=lambda item: item["energy"],
        reverse=True,
    )[:5]
    return {
        "hook_identity": hook_score,
        "motif_repetition_quality": motif_score,
        "call_response_quality": call_score,
        "energy_melody_peak": peak_score,
        "score": round(float(hook_score), 2),
        "diagnosis": diagnosis,
        "motif_return_score": round(motif_return, 4),
        "energy_peak_clarity": round(energy_peak_clarity, 4),
        "contour_strength": round(contour_strength, 4),
        "hook_candidates": candidates,
        "reason": "Repeated 4-second energy/pitch signatures with energy contrast and melodic contour heuristic.",
    }

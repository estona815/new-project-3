from __future__ import annotations

import math
from statistics import mean
from typing import Any

import numpy as np
from scipy import signal


def _rms(values: np.ndarray) -> float:
    if values.size == 0:
        return 0.0
    return float(np.sqrt(np.mean(np.square(values, dtype=np.float64))))


def _score_1_to_5(value: float) -> int:
    return max(1, min(5, int(round(1.0 + 4.0 * max(0.0, min(1.0, value))))))


def _bandpass(samples: np.ndarray, sample_rate: int, low: float, high: float) -> np.ndarray:
    if sample_rate <= 0 or samples.size == 0 or low >= high or high >= sample_rate / 2:
        return samples.astype(np.float32)
    sos = signal.butter(2, [low, high], fs=sample_rate, btype="bandpass", output="sos")
    return signal.sosfilt(sos, samples).astype(np.float32)


def _dominant_band_frequency(frame: np.ndarray, sample_rate: int, low: float = 800.0, high: float = 6_000.0) -> tuple[float | None, float]:
    if sample_rate <= 0 or frame.size < 128 or _rms(frame) < 1e-5:
        return None, 0.0
    windowed = frame * np.hanning(frame.size)
    spectrum = np.abs(np.fft.rfft(windowed))
    freqs = np.fft.rfftfreq(frame.size, 1.0 / sample_rate)
    mask = (freqs >= low) & (freqs <= high)
    if not bool(np.any(mask)):
        return None, 0.0
    band = spectrum[mask]
    band_freqs = freqs[mask]
    if band.size == 0:
        return None, 0.0
    peak_idx = int(np.argmax(band))
    peak = float(band[peak_idx])
    floor = float(np.median(band) + 1e-12)
    confidence = max(0.0, min(1.0, math.log10((peak / floor) + 1.0) / 2.2))
    return float(band_freqs[peak_idx]), confidence


def _pitch_contour(samples: np.ndarray, sample_rate: int, frame_seconds: float = 0.5) -> list[dict[str, float]]:
    frame_size = max(512, int(frame_seconds * sample_rate))
    if sample_rate <= 0 or samples.size < frame_size:
        return []
    contour: list[dict[str, float]] = []
    for start in range(0, samples.size - frame_size + 1, frame_size):
        frame = samples[start : start + frame_size]
        frequency, confidence = _dominant_band_frequency(frame, sample_rate)
        if frequency is None:
            continue
        contour.append(
            {
                "time": round(start / sample_rate, 3),
                "frequency": round(frequency, 2),
                "confidence": round(confidence, 4),
            }
        )
    return contour


def _quantized_contour(contour: list[dict[str, float]]) -> list[int]:
    values: list[int] = []
    for item in contour:
        frequency = float(item["frequency"])
        if frequency <= 0:
            continue
        midi = round(69 + 12 * math.log2(frequency / 440.0))
        values.append(int(midi))
    return values


def _contour_activity_score(quantized: list[int]) -> float:
    if len(quantized) < 3:
        return 0.0
    changes = sum(1 for left, right in zip(quantized, quantized[1:]) if left != right)
    change_ratio = changes / max(1, len(quantized) - 1)
    unique_ratio = len(set(quantized)) / max(1, len(quantized))
    if change_ratio < 0.08:
        return 0.05
    if change_ratio > 0.85:
        return 0.35
    return max(0.0, min(1.0, 0.68 * change_ratio + 0.32 * min(1.0, unique_ratio * 3.0)))


def _motif_recurrence_score(quantized: list[int], motif_size: int = 4) -> float:
    if len(quantized) < motif_size * 2:
        return 0.0
    motifs = [tuple(quantized[index : index + motif_size]) for index in range(0, len(quantized) - motif_size + 1, motif_size)]
    if len(motifs) < 2:
        return 0.0
    best = 0.0
    for index, motif in enumerate(motifs):
        for other in motifs[index + 1 :]:
            matches = sum(1 for left, right in zip(motif, other) if abs(left - right) <= 1)
            best = max(best, matches / motif_size)
    return best


def analyze_lead_melody_presence(mono_samples: list[float] | np.ndarray, sample_rate: int) -> dict[str, Any]:
    """Estimate whether the full mix contains a clear, repeated lead line.

    This is deliberately heuristic. It looks for 800 Hz-6 kHz prominence,
    stable pitch peaks, changing-but-repeatable contour, and motif recurrence.
    """
    samples = np.asarray(mono_samples, dtype=np.float32)
    if sample_rate <= 0 or samples.size < max(1024, int(sample_rate * 1.0)):
        return {
            "lead_melody_presence": 1,
            "spectral_prominence": 0.0,
            "repeated_contour": 0.0,
            "pitch_stability_proxy": 0.0,
            "motif_recurrence": 0.0,
            "score": 1.0,
            "diagnosis": "weak_or_absent",
            "limitations": ["Audio is too short for reliable lead melody detection."],
        }

    full_rms = _rms(samples) + 1e-12
    lead_band = _bandpass(samples, sample_rate, 800.0, min(6_000.0, sample_rate / 2 - 100.0))
    noise_band = _bandpass(samples, sample_rate, 6_000.0, min(12_000.0, sample_rate / 2 - 100.0))
    lead_ratio = _rms(lead_band) / full_rms
    noise_ratio = _rms(noise_band) / full_rms
    spectral_prominence = max(0.0, min(1.0, (lead_ratio - 0.10) / 0.42))
    if noise_ratio > lead_ratio * 0.85:
        spectral_prominence *= 0.72

    contour = _pitch_contour(samples, sample_rate)
    confidences = [float(item["confidence"]) for item in contour]
    pitch_stability = max(0.0, min(1.0, mean(confidences) if confidences else 0.0))
    quantized = _quantized_contour(contour)
    contour_activity = _contour_activity_score(quantized)
    motif_recurrence = _motif_recurrence_score(quantized)

    combined = 0.28 * spectral_prominence + 0.24 * pitch_stability + 0.24 * contour_activity + 0.24 * motif_recurrence
    if contour_activity < 0.12 or motif_recurrence < 0.20:
        combined = min(combined, 0.36)
    integer_score = _score_1_to_5(combined)
    diagnosis = "present" if integer_score >= 4 else "unclear" if integer_score == 3 else "weak_or_absent"
    return {
        "lead_melody_presence": integer_score,
        "spectral_prominence": round(spectral_prominence, 4),
        "repeated_contour": round(contour_activity, 4),
        "pitch_stability_proxy": round(pitch_stability, 4),
        "motif_recurrence": round(motif_recurrence, 4),
        "score": round(float(integer_score), 2),
        "diagnosis": diagnosis,
        "contour_points": len(contour),
        "limitations": ["Lead melody detection is heuristic and may confuse bright vocal chops, synth leads, or dense mixes."],
    }

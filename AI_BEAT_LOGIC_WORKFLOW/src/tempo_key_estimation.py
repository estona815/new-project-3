from __future__ import annotations

import math
from statistics import median, pstdev
from typing import Any

from audio_confidence import cap_short_sample_confidence, confidence_label


NOTE_NAMES = ("C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B")


def normalize_bpm(bpm: float) -> float:
    while bpm < 70.0:
        bpm *= 2.0
    while bpm > 180.0:
        bpm /= 2.0
    return bpm


def estimate_bpm(onset_times: list[float], duration_seconds: float) -> dict[str, Any]:
    intervals = [
        right - left
        for left, right in zip(onset_times, onset_times[1:])
        if 0.18 <= right - left <= 1.4
    ]
    if len(intervals) < 2:
        return {
            "bpm": None,
            "bpm_candidates": [],
            "half_time_bpm": None,
            "double_time_bpm": None,
            "half_double_ambiguity": True,
            "confidence": "low",
            "method": "Not enough repeated onset intervals for stable BPM estimation.",
        }
    base = normalize_bpm(60.0 / median(intervals))
    spread = pstdev(intervals) if len(intervals) > 1 else 0.0
    mean_interval = sum(intervals) / len(intervals)
    periodicity = 1.0 - min(1.0, spread / mean_interval) if mean_interval > 0 else 0.0
    ambiguity = len(intervals) < 8 or periodicity < 0.78
    confidence = confidence_label(periodicity)
    if ambiguity and confidence == "high":
        confidence = "medium"
    confidence = cap_short_sample_confidence(confidence, duration_seconds)
    candidates = sorted({round(base / 2.0, 1), round(base, 1), round(base * 2.0, 1)})
    candidates = [value for value in candidates if 45.0 <= value <= 220.0]
    return {
        "bpm": round(base, 1),
        "bpm_candidates": candidates,
        "half_time_bpm": round(base / 2.0, 1) if 45.0 <= base / 2.0 <= 220.0 else None,
        "double_time_bpm": round(base * 2.0, 1) if 45.0 <= base * 2.0 <= 220.0 else None,
        "half_double_ambiguity": ambiguity,
        "periodicity_score": round(periodicity, 4),
        "confidence": confidence,
        "method": "Median spacing between onset candidates with half/double-time ambiguity reporting.",
    }


def _rms(samples: list[float]) -> float:
    if not samples:
        return 0.0
    return math.sqrt(sum(sample * sample for sample in samples) / len(samples))


def dominant_frequency(samples: list[float], sample_rate: int) -> tuple[float | None, float]:
    if sample_rate <= 0 or len(samples) < 64 or _rms(samples) < 0.001:
        return None, 0.0
    frame_size = min(len(samples), max(1024, int(sample_rate * 0.15)))
    hop = max(1, frame_size // 2)
    best_frame: list[float] = []
    best_rms = 0.0
    for start in range(0, max(1, len(samples) - frame_size + 1), hop):
        frame = samples[start : start + frame_size]
        energy = _rms(frame)
        if energy > best_rms:
            best_rms = energy
            best_frame = frame
    if not best_frame:
        return None, 0.0
    min_lag = max(1, int(sample_rate / 900.0))
    max_lag = min(len(best_frame) - 2, int(sample_rate / 45.0))
    if max_lag <= min_lag:
        return None, 0.0
    energy = sum(sample * sample for sample in best_frame) or 1.0
    best_lag = 0
    best_score = 0.0
    for lag in range(min_lag, max_lag + 1):
        score = sum(best_frame[index] * best_frame[index + lag] for index in range(len(best_frame) - lag)) / energy
        if score > best_score:
            best_score = score
            best_lag = lag
    if best_lag <= 0 or best_score < 0.16:
        return None, best_score
    return sample_rate / best_lag, best_score


def note_from_frequency(frequency: float | None) -> tuple[str | None, int | None, float | None]:
    if not frequency or frequency <= 0:
        return None, None, None
    midi = 69 + 12 * math.log2(frequency / 440.0)
    rounded = int(round(midi))
    deviation = (midi - rounded) * 100.0
    return f"{NOTE_NAMES[rounded % 12]}{rounded // 12 - 1}", rounded % 12, deviation


def estimate_key(samples: list[float], sample_rate: int, duration_seconds: float) -> dict[str, Any]:
    frequency, score = dominant_frequency(samples, sample_rate)
    note, pitch_class, deviation = note_from_frequency(frequency)
    confidence = confidence_label(score)
    if duration_seconds < 2.0:
        confidence = "low"
    if not note:
        confidence = "low"
    candidates = []
    if note:
        candidates.append({"tonic_or_pitch_center": note, "pitch_class": pitch_class, "score": round(score, 4)})
    return {
        "estimated_key": note if confidence != "low" else None,
        "estimated_tonic_or_pitch_center": note,
        "key_candidates": candidates,
        "tuning_deviation_cents": round(deviation, 2) if deviation is not None else None,
        "confidence": confidence,
        "method": "stdlib autocorrelation pitch-center heuristic; polyphonic/full-mix key should be treated as low/medium confidence.",
    }

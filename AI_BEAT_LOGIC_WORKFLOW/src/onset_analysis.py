from __future__ import annotations

import math
from typing import Any

from loudness_estimation import linear_to_db


def rms(samples: list[float]) -> float:
    if not samples:
        return 0.0
    return math.sqrt(sum(sample * sample for sample in samples) / len(samples))


def frame_features(samples: list[float], sample_rate: int, window_seconds: float = 0.05) -> list[dict[str, Any]]:
    if sample_rate <= 0 or not samples:
        return []
    window = max(1, int(sample_rate * window_seconds))
    frames: list[dict[str, Any]] = []
    for start in range(0, len(samples), window):
        end = min(len(samples), start + window)
        chunk = samples[start:end]
        energy = rms(chunk)
        peak = max((abs(sample) for sample in chunk), default=0.0)
        derivative = rms([right - left for left, right in zip(chunk, chunk[1:])])
        zero_crossings = sum(1 for left, right in zip(chunk, chunk[1:]) if (left < 0 <= right) or (right < 0 <= left))
        frames.append(
            {
                "start": start / sample_rate,
                "end": end / sample_rate,
                "rms": energy,
                "peak": peak,
                "brightness_ratio": derivative / energy if energy > 0 else 0.0,
                "zero_crossing_rate": zero_crossings / max(1, len(chunk) - 1),
            }
        )
    return frames


def detect_onsets(frames: list[dict[str, Any]], duration_seconds: float, limit: int = 128) -> list[dict[str, Any]]:
    if len(frames) < 3:
        return []
    flux = [max(0.0, frames[index]["rms"] - frames[index - 1]["rms"]) for index in range(1, len(frames))]
    if not flux:
        return []
    ordered = sorted(flux)
    threshold = max(ordered[int(len(ordered) * 0.75)], max(flux) * 0.28, 0.0005)
    onsets: list[dict[str, Any]] = []
    last_time = -1.0
    for index, value in enumerate(flux, start=1):
        current = frames[index]
        time = float(current["start"])
        if value < threshold or time - last_time < 0.08:
            continue
        onsets.append(
            {
                "time": round(time, 3),
                "strength": round(value, 6),
                "peak_dbfs": round(linear_to_db(float(current["peak"])), 2),
                "brightness_ratio": round(float(current["brightness_ratio"]), 4),
                "reason": "positive short-window RMS flux; transient/onset heuristic",
            }
        )
        last_time = time
        if len(onsets) >= limit:
            break
    return [item for item in onsets if 0.0 <= item["time"] <= duration_seconds]


def analyze_transients(samples: list[float], sample_rate: int) -> dict[str, Any]:
    duration = len(samples) / sample_rate if sample_rate > 0 else 0.0
    frames = frame_features(samples, sample_rate)
    onsets = detect_onsets(frames, duration)
    strengths = [float(item["strength"]) for item in onsets]
    density = len(onsets) / duration if duration > 0 else 0.0
    sharpness = sum(strengths) / len(strengths) if strengths else 0.0
    drum_like = [
        {
            "start": round(float(frame["start"]), 3),
            "end": round(float(frame["end"]), 3),
            "reason": "high transient peak and short-window brightness; drum-like heuristic",
            "confidence": "medium" if frame["peak"] > 0.35 else "low",
        }
        for frame in frames
        if frame["peak"] > 0.25 and frame["brightness_ratio"] > 0.25
    ][:16]
    return {
        "onset_times": [item["time"] for item in onsets],
        "onsets": onsets,
        "onset_count": len(onsets),
        "onset_density_per_second": round(density, 4),
        "transient_sharpness": round(sharpness, 6),
        "drum_like_regions": drum_like,
        "method": "stdlib short-window RMS flux and derivative heuristics; not a drum transcription.",
    }

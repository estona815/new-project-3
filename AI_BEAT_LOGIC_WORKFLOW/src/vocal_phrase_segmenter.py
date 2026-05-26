from __future__ import annotations

import math
from typing import Any

from loudness_estimation import linear_to_db


def rms(samples: list[float]) -> float:
    if not samples:
        return 0.0
    return math.sqrt(sum(sample * sample for sample in samples) / len(samples))


def vocal_activity_frames(samples: list[float], sample_rate: int, frame_seconds: float = 0.08, hop_seconds: float = 0.08) -> list[dict[str, Any]]:
    if sample_rate <= 0 or not samples:
        return []
    frame_size = max(64, int(sample_rate * frame_seconds))
    hop = max(1, int(sample_rate * hop_seconds))
    frames: list[dict[str, Any]] = []
    for start in range(0, max(1, len(samples) - frame_size + 1), hop):
        frame = samples[start : start + frame_size]
        level = rms(frame)
        peak = max((abs(sample) for sample in frame), default=0.0)
        derivative = rms([right - left for left, right in zip(frame, frame[1:])])
        frames.append(
            {
                "start": round(start / sample_rate, 3),
                "end": round((start + len(frame)) / sample_rate, 3),
                "rms": level,
                "rms_dbfs": linear_to_db(level),
                "peak": peak,
                "brightness_ratio": derivative / level if level > 0 else 0.0,
            }
        )
    return frames


def _energy_label(value: float) -> str:
    if value >= 0.18:
        return "high"
    if value >= 0.045:
        return "medium"
    return "low"


def segment_vocal_phrases(frames: list[dict[str, Any]], *, mode: str = "separate_vocal") -> list[dict[str, Any]]:
    if not frames:
        return []
    levels = sorted(float(frame["rms"]) for frame in frames)
    threshold = max(0.0035, levels[int(len(levels) * 0.55)] * 0.55)
    phrases: list[dict[str, Any]] = []
    current: list[dict[str, Any]] = []
    for frame in frames:
        active = float(frame["rms"]) >= threshold
        if active:
            current.append(frame)
            continue
        if current and float(frame["start"]) - float(current[-1]["end"]) <= 0.12:
            continue
        if current:
            phrases.append(_summarize_phrase(current, len(phrases) + 1, mode))
            current = []
    if current:
        phrases.append(_summarize_phrase(current, len(phrases) + 1, mode))
    return phrases


def _summarize_phrase(frames: list[dict[str, Any]], index: int, mode: str) -> dict[str, Any]:
    start = float(frames[0]["start"])
    end = float(frames[-1]["end"])
    avg_rms = sum(float(frame["rms"]) for frame in frames) / len(frames)
    phrase_type = "unknown"
    if mode in {"separate_vocal", "vocal_plus_beat"}:
        phrase_type = "lead" if avg_rms >= 0.04 else "unknown"
    return {
        "phrase_id": f"vocal_phrase_{index:03d}",
        "start": round(start, 3),
        "end": round(end, 3),
        "duration": round(max(0.0, end - start), 3),
        "phrase_type": phrase_type,
        "energy": _energy_label(avg_rms),
        "average_rms": round(avg_rms, 6),
        "frames": frames,
        "limitations": ["full stereo phrase segmentation is heuristic"] if mode == "full_song_stereo" else [],
    }

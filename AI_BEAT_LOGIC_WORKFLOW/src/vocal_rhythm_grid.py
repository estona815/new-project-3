from __future__ import annotations

from typing import Any


def estimate_vocal_bpm(phrases: list[dict[str, Any]], duration_seconds: float) -> dict[str, Any]:
    starts = [float(phrase["start"]) for phrase in phrases]
    intervals = [right - left for left, right in zip(starts, starts[1:]) if 0.25 <= right - left <= 2.0]
    if len(intervals) < 2:
        return {"estimated_bpm": None, "bpm_confidence": "low", "method": "Not enough phrase starts for reliable vocal timing BPM."}
    median_interval = sorted(intervals)[len(intervals) // 2]
    bpm = 60.0 / median_interval
    while bpm < 70.0:
        bpm *= 2.0
    while bpm > 180.0:
        bpm /= 2.0
    confidence = "medium" if len(intervals) >= 4 and duration_seconds >= 4.0 else "low"
    return {"estimated_bpm": round(bpm, 1), "bpm_confidence": confidence, "method": "Phrase-start spacing heuristic; verify against beat grid."}


def rhythm_grid_for_phrase(phrase: dict[str, Any], bpm: float | None) -> list[dict[str, Any]]:
    if not bpm:
        return [
            {
                "position": "unknown",
                "duration": "unknown",
                "confidence": "low",
            }
        ]
    beat_seconds = 60.0 / bpm
    start_beats = float(phrase["start"]) / beat_seconds
    duration_beats = max(0.0, float(phrase["duration"]) / beat_seconds)
    bar = int(start_beats // 4) + 1
    beat = int(start_beats % 4) + 1
    if duration_beats <= 0.75:
        duration = "1/8"
    elif duration_beats <= 1.5:
        duration = "1/4"
    elif duration_beats <= 3.0:
        duration = "1/2"
    else:
        duration = "bar_or_longer"
    return [
        {
            "position": f"bar{bar}.beat{beat}",
            "duration": duration,
            "confidence": "medium",
        }
    ]


def timing_for_phrase(phrase: dict[str, Any], bpm: float | None) -> dict[str, Any]:
    if not bpm:
        return {"grid_alignment": "loose", "timing_confidence": "low"}
    beat_seconds = 60.0 / bpm
    beat_fraction = (float(phrase["start"]) / beat_seconds) % 1.0
    if beat_fraction < 0.12 or beat_fraction > 0.88:
        alignment = "on_grid"
    elif beat_fraction < 0.5:
        alignment = "behind"
    else:
        alignment = "ahead"
    return {"grid_alignment": alignment, "timing_confidence": "medium"}

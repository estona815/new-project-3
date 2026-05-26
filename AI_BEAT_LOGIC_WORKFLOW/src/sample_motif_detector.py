from __future__ import annotations

from typing import Any


def detect_motif_candidates(frames: list[dict[str, Any]], duration_seconds: float, limit: int = 6) -> dict[str, Any]:
    if not frames:
        return {
            "hook_motif_candidates": [],
            "repeated_energy_spectral_contour_regions": [],
            "method": "No frame features available.",
        }
    ranked = sorted(frames, key=lambda item: (item.get("rms", 0.0), item.get("brightness_ratio", 0.0)), reverse=True)
    candidates: list[dict[str, Any]] = []
    used: list[float] = []
    for frame in ranked:
        start = float(frame["start"])
        if any(abs(start - existing) < 1.0 for existing in used):
            continue
        confidence = "medium" if duration_seconds >= 2.0 and frame.get("rms", 0.0) > 0.08 else "low"
        candidates.append(
            {
                "start": round(start, 3),
                "end": round(float(frame["end"]), 3),
                "confidence": confidence,
                "reason": "high-energy/high-texture window; hook or motif listening cue",
                "role_hint": "hook_candidate" if len(candidates) == 0 else "motif_or_variation",
            }
        )
        used.append(start)
        if len(candidates) >= limit:
            break

    repeated: list[dict[str, Any]] = []
    for left, right in zip(frames, frames[1:]):
        energy_delta = abs(float(left.get("rms", 0.0)) - float(right.get("rms", 0.0)))
        bright_delta = abs(float(left.get("brightness_ratio", 0.0)) - float(right.get("brightness_ratio", 0.0)))
        if energy_delta < 0.015 and bright_delta < 0.15:
            repeated.append(
                {
                    "start": round(float(left["start"]), 3),
                    "end": round(float(right["end"]), 3),
                    "confidence": "low",
                    "reason": "adjacent frames have similar energy and spectral contour; possible repeated loop feel",
                }
            )
    return {
        "hook_motif_candidates": sorted(candidates, key=lambda item: item["start"]),
        "repeated_energy_spectral_contour_regions": repeated[:12],
        "strong_melodic_or_rhythmic_regions": sorted(candidates[:3], key=lambda item: item["start"]),
        "method": "Short-window RMS and brightness ranking; not melody transcription.",
    }

from __future__ import annotations

from typing import Any


def detect_hook_candidates(features: list[dict[str, Any]], duration_seconds: float, limit: int = 5) -> list[dict[str, Any]]:
    if not features:
        return []
    max_energy = max(float(item["energy"]) for item in features) or 1.0
    max_onset = max(float(item["onset_density"]) for item in features) or 1.0
    candidates: list[dict[str, Any]] = []
    for frame in features:
        energy_score = float(frame["energy"]) / max_energy
        onset_score = float(frame["onset_density"]) / max_onset if max_onset > 0 else 0.0
        early_bonus = 0.08 if 4.0 <= float(frame["start"]) <= 40.0 else 0.0
        score = min(1.0, 0.62 * energy_score + 0.3 * onset_score + early_bonus)
        if score < 0.42:
            continue
        confidence = "high" if score >= 0.78 and duration_seconds >= 16.0 else "medium" if score >= 0.55 else "low"
        candidates.append(
            {
                "start": round(float(frame["start"]), 3),
                "end": round(float(frame["end"]), 3),
                "score": round(score, 4),
                "reason": "strong motif, high energy, repeated contour/onset heuristic",
                "confidence": confidence,
            }
        )
    return sorted(candidates, key=lambda item: item["score"], reverse=True)[:limit]


def reels_hook_region(candidates: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not candidates:
        return None
    best = candidates[0]
    return {
        "start": best["start"],
        "end": min(float(best["start"]) + 15.0, float(best["end"])),
        "source": "best hook candidate",
        "confidence": best["confidence"],
    }

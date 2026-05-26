from __future__ import annotations

from typing import Any


def detect_abrupt_transitions(features: list[dict[str, Any]], limit: int = 12) -> list[dict[str, Any]]:
    if len(features) < 2:
        return []
    novelties = [float(item["novelty"]) for item in features]
    threshold = max(novelties) * 0.72 if novelties else 0.0
    transitions: list[dict[str, Any]] = []
    for frame in features[1:]:
        novelty = float(frame["novelty"])
        if novelty >= threshold and novelty > 0:
            transitions.append(
                {
                    "start": round(float(frame["start"]), 3),
                    "end": round(float(frame["end"]), 3),
                    "novelty_score": round(novelty, 6),
                    "confidence": "medium",
                    "reason": "abrupt energy/novelty change; audition transition manually",
                }
            )
    return transitions[:limit]


def weak_intro_candidates(features: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not features:
        return []
    first = features[0]
    max_energy = max(float(item["energy"]) for item in features) or 1.0
    if float(first["energy"]) / max_energy <= 0.18:
        return [{"start": round(float(first["start"]), 3), "end": round(float(first["end"]), 3), "confidence": "medium", "reason": "intro energy is much lower than song peak"}]
    return []


def dead_outro_candidates(features: list[dict[str, Any]], duration_seconds: float) -> list[dict[str, Any]]:
    if not features:
        return []
    last = features[-1]
    max_energy = max(float(item["energy"]) for item in features) or 1.0
    if duration_seconds > 4.0 and float(last["energy"]) / max_energy <= 0.16:
        return [{"start": round(float(last["start"]), 3), "end": round(float(last["end"]), 3), "confidence": "medium", "reason": "outro energy drops near silence/low activity"}]
    return []

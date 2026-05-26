from __future__ import annotations


def confidence_label(score: float) -> str:
    if score >= 0.75:
        return "high"
    if score >= 0.45:
        return "medium"
    return "low"


def cap_short_sample_confidence(confidence: str, duration_seconds: float, threshold_seconds: float = 2.0) -> str:
    if duration_seconds < threshold_seconds and confidence == "high":
        return "medium"
    if duration_seconds < threshold_seconds and confidence == "medium":
        return "low"
    return confidence


def combine_confidence(*labels: str) -> str:
    values = {"unknown": 0, "low": 1, "medium": 2, "high": 3}
    inverse = {0: "unknown", 1: "low", 2: "medium", 3: "high"}
    if not labels:
        return "unknown"
    return inverse[min(values.get(label, 1) for label in labels)]

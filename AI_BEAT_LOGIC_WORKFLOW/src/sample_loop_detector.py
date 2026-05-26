from __future__ import annotations

from typing import Any


def _boundary_click_risk(samples: list[float], sample_rate: int, start: float, end: float) -> dict[str, Any]:
    if sample_rate <= 0 or not samples:
        return {"risk": "unknown", "score": None, "method": "No samples available."}
    start_index = max(0, min(len(samples) - 1, int(start * sample_rate)))
    end_index = max(0, min(len(samples) - 1, int(end * sample_rate) - 1))
    delta = abs(samples[end_index] - samples[start_index])
    if delta > 0.18:
        risk = "high"
    elif delta > 0.06:
        risk = "medium"
    else:
        risk = "low"
    return {
        "risk": risk,
        "score": round(delta, 6),
        "method": "Absolute waveform jump between proposed loop end and start.",
    }


def detect_loop_candidates(
    samples: list[float],
    sample_rate: int,
    duration_seconds: float,
    tempo: dict[str, Any],
) -> list[dict[str, Any]]:
    if duration_seconds <= 0:
        return []
    bpm = tempo.get("bpm")
    candidates: list[dict[str, Any]] = []
    if bpm:
        beat = 60.0 / float(bpm)
        for bars in (1, 2, 4, 8):
            length = beat * 4.0 * bars
            if 0.35 <= length <= duration_seconds + 0.05:
                end = min(duration_seconds, length)
                boundary = _boundary_click_risk(samples, sample_rate, 0.0, end)
                click_penalty = {"low": 0.0, "medium": 0.18, "high": 0.35, "unknown": 0.25}[boundary["risk"]]
                loop_score = max(0.0, 0.78 - click_penalty - (0.08 if tempo.get("half_double_ambiguity") else 0.0))
                confidence = "medium" if loop_score >= 0.55 and duration_seconds >= 2.0 else "low"
                candidates.append(
                    {
                        "start": 0.0,
                        "end": round(end, 3),
                        "estimated_bars": bars,
                        "bpm": round(float(bpm), 1),
                        "loop_score": round(loop_score, 4),
                        "boundary_click_risk": boundary,
                        "confidence": confidence,
                        "reason": "bar-aligned loop candidate from estimated BPM; audition loop boundary manually",
                    }
                )
    if not candidates:
        end = min(duration_seconds, 4.0)
        candidates.append(
            {
                "start": 0.0,
                "end": round(end, 3),
                "estimated_bars": None,
                "bpm": None,
                "loop_score": 0.25 if duration_seconds >= 2.0 else 0.1,
                "boundary_click_risk": _boundary_click_risk(samples, sample_rate, 0.0, end),
                "confidence": "low",
                "reason": "fixed early-region fallback because BPM estimate is weak",
            }
        )
    return candidates[:6]

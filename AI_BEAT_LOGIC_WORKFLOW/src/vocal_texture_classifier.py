from __future__ import annotations

from typing import Any


CONFIDENCE_ORDER = {"low": 1, "medium": 2, "high": 3}


def _confidence(value: Any, fallback: str = "low") -> str:
    text = str(value or fallback).lower()
    return text if text in CONFIDENCE_ORDER else fallback


def _max_confidence(*values: Any) -> str:
    ranked = [_confidence(value) for value in values if value is not None]
    if not ranked:
        return "low"
    return max(ranked, key=lambda item: CONFIDENCE_ORDER[item])


def _duration_from_diagnosis(rescue_diagnosis: dict[str, Any] | None) -> float | None:
    if not rescue_diagnosis:
        return None
    value = (rescue_diagnosis.get("basic_metrics") or {}).get("duration_seconds")
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _diagnosis_vocal_texture(rescue_diagnosis: dict[str, Any] | None) -> dict[str, Any]:
    return dict((rescue_diagnosis or {}).get("vocal_texture") or {})


def _diagnosis_missing_lead(rescue_diagnosis: dict[str, Any] | None) -> bool:
    decision = (rescue_diagnosis or {}).get("rescue_decision") or {}
    musical = (rescue_diagnosis or {}).get("musical_identity") or {}
    try:
        lead_score = float(musical.get("lead_melody_presence", 5))
    except (TypeError, ValueError):
        lead_score = 5.0
    return bool(decision.get("lead_melody_required") or lead_score <= 2.0)


def _issue_from_candidate(candidate: dict[str, Any], diagnosis_texture: dict[str, Any], missing_lead: bool) -> str:
    reason = " ".join(
        str(candidate.get(key, ""))
        for key in ("issue", "reason", "label", "description")
    ).lower()
    if diagnosis_texture.get("vocal_chop_as_unwanted_lead") or "fake" in reason or "chop" in reason:
        return "fake_vocal_chop_dominates_lead"
    if _confidence(diagnosis_texture.get("pitch_instability")) == "high" or "unstable" in reason or "pitch" in reason:
        return "unstable_vocal_lead"
    if "glitch" in reason or "random" in reason or "riser" in reason:
        return "ai_glitch_vocal_texture"
    if missing_lead and ("formant" in reason or "mono-centered" in reason or "modulated" in reason):
        return "fake_vocal_chop_dominates_lead"
    return "weird_vocal_like_texture"


def _issue_reason(issue: str) -> str:
    return {
        "fake_vocal_chop_dominates_lead": "vocal-like texture is likely acting as an unwanted lead",
        "unstable_vocal_lead": "vocal-like lead has pitch or phrasing instability risk",
        "ai_glitch_vocal_texture": "glitch/vocal artifact appears unmotivated by arrangement",
        "phrasing_confusion": "vocal phrasing reads confusing or random",
        "global_weird_vocal_texture_risk": "diagnosis reports elevated weird vocal texture risk",
    }.get(issue, "vocal-like texture needs manual listening review")


def classify_vocal_texture_candidates(
    vocal_like_texture_candidates: list[dict[str, Any]] | None = None,
    *,
    rescue_diagnosis: dict[str, Any] | None = None,
    creative_brief: dict[str, Any] | None = None,
    mode: str | None = None,
) -> list[dict[str, Any]]:
    candidates = list(vocal_like_texture_candidates or [])
    diagnosis_texture = _diagnosis_vocal_texture(rescue_diagnosis)
    weird_risk = _confidence(diagnosis_texture.get("weird_vocal_texture_risk"), "low")
    pitch_risk = _confidence(diagnosis_texture.get("pitch_instability"), "low")
    phrase_risk = _confidence(diagnosis_texture.get("phrasing_confusion"), "low")
    missing_lead = _diagnosis_missing_lead(rescue_diagnosis)
    duration = _duration_from_diagnosis(rescue_diagnosis)
    issues: list[dict[str, Any]] = []

    for candidate in candidates[:24]:
        issue = _issue_from_candidate(candidate, diagnosis_texture, missing_lead)
        start = float(candidate.get("start", 0.0) or 0.0)
        end = float(candidate.get("end", start + 2.0) or start + 2.0)
        confidence = _max_confidence(candidate.get("confidence"), weird_risk, pitch_risk if issue == "unstable_vocal_lead" else None)
        if confidence == "low" and (missing_lead or diagnosis_texture.get("vocal_chop_as_unwanted_lead")):
            confidence = "medium"
        issues.append(
            {
                "start": round(start, 3),
                "end": round(max(end, start), 3),
                "issue": issue,
                "confidence": confidence,
                "reason": candidate.get("reason") or _issue_reason(issue),
                "source": "candidate_window",
                "mode": mode or (rescue_diagnosis or {}).get("input", {}).get("mode", "unknown"),
            }
        )

    if not issues and weird_risk in {"medium", "high"}:
        end = duration if duration and duration > 0 else 8.0
        issue = "fake_vocal_chop_dominates_lead" if diagnosis_texture.get("vocal_chop_as_unwanted_lead") else "global_weird_vocal_texture_risk"
        issues.append(
            {
                "start": 0.0,
                "end": round(float(end), 3),
                "issue": issue,
                "confidence": weird_risk,
                "reason": _issue_reason(issue),
                "source": "diagnosis_summary",
                "mode": mode or (rescue_diagnosis or {}).get("input", {}).get("mode", "unknown"),
            }
        )

    if phrase_risk == "high":
        issues.append(
            {
                "start": 0.0,
                "end": round(float(duration or 8.0), 3),
                "issue": "phrasing_confusion",
                "confidence": "high",
                "reason": _issue_reason("phrasing_confusion"),
                "source": "diagnosis_summary",
                "mode": mode or (rescue_diagnosis or {}).get("input", {}).get("mode", "unknown"),
            }
        )

    brief_text = " ".join(str(value) for value in (creative_brief or {}).values()).lower()
    if "vocal chop" in brief_text and "lead" in brief_text and not issues:
        issues.append(
            {
                "start": 0.0,
                "end": round(float(duration or 8.0), 3),
                "issue": "fake_vocal_chop_dominates_lead",
                "confidence": "medium",
                "reason": "creative brief warns that vocal chop should not own the lead role",
                "source": "creative_brief",
                "mode": mode or (rescue_diagnosis or {}).get("input", {}).get("mode", "unknown"),
            }
        )

    return issues[:16]


def has_bad_vocal_lead_role(issues: list[dict[str, Any]]) -> bool:
    return any(
        issue.get("issue") in {
            "fake_vocal_chop_dominates_lead",
            "unstable_vocal_lead",
            "phrasing_confusion",
            "global_weird_vocal_texture_risk",
        }
        for issue in issues
    )

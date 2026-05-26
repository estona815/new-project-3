from __future__ import annotations

from typing import Any


STYLE_CHORD_FLAVORS = {
    "commercial_digicore_hyperpop": "bright digital tension with minor/major ambiguity",
    "commercial_digicore": "bright digital tension with minor/major ambiguity",
    "hyperpop": "bright suspended color with emotional lift",
    "hip_hop": "simple strong pocket that leaves room for vocal",
    "internet_underground": "melancholic loop color with controlled surprise",
    "system_seoul_adjacent": "playful digital motif color without exact sample or melody copy",
    "custom": "safe original hook harmony",
}


def normalize_key_payload(key: dict[str, Any] | None = None, sample_analysis: dict[str, Any] | None = None) -> dict[str, Any]:
    tonal = key or (sample_analysis or {}).get("tonal") or {}
    estimated = tonal.get("estimated_key") or tonal.get("estimated_tonic_or_pitch_center")
    confidence = tonal.get("confidence") or tonal.get("key_confidence") or "low"
    alternatives = tonal.get("alternatives") or tonal.get("key_candidates") or []
    cleaned_alternatives: list[Any] = []
    for item in alternatives:
        if isinstance(item, dict):
            value = item.get("estimated_key") or item.get("tonic_or_pitch_center")
            if value:
                cleaned_alternatives.append(value)
        elif item:
            cleaned_alternatives.append(item)
    if estimated and estimated not in cleaned_alternatives:
        cleaned_alternatives.insert(0, estimated)
    if confidence not in {"low", "medium", "high"}:
        confidence = "low"
    return {
        "estimated_key": estimated,
        "confidence": confidence,
        "alternatives": list(dict.fromkeys(cleaned_alternatives))[:4],
    }


def generate_chord_options(
    *,
    key: dict[str, Any] | None = None,
    sample_analysis: dict[str, Any] | None = None,
    style_target: str = "commercial_digicore_hyperpop",
) -> list[dict[str, Any]]:
    key_payload = normalize_key_payload(key, sample_analysis)
    estimated_key = key_payload["estimated_key"]
    confidence = key_payload["confidence"]
    style_note = STYLE_CHORD_FLAVORS.get(style_target, STYLE_CHORD_FLAVORS["custom"])
    key_label = estimated_key or "confirm_by_ear"
    options = [
        {
            "name": "early hook lift",
            "key": key_label,
            "roman": ["i", "VI", "III", "VII"],
            "section_use": "hook or first drop",
            "feel": style_note,
            "confidence": "medium" if confidence in {"medium", "high"} else "low",
            "notes": [
                "Keep the top note simple enough for a bright hook melody.",
                "Use as an original harmonic sketch, not a copied reference progression.",
            ],
        },
        {
            "name": "two-chord pressure",
            "key": key_label,
            "roman": ["i", "VII"],
            "section_use": "verse, intro, or rap pocket",
            "feel": "loopable tension that leaves space for vocal and 808",
            "confidence": confidence,
            "notes": [
                "Move energy with rhythm, counterline, and drum density instead of adding too many chords.",
                "Confirm bass root by ear when key confidence is low.",
            ],
        },
        {
            "name": "ambiguous major lift",
            "key": key_label,
            "roman": ["VI", "VII", "i", "III"],
            "section_use": "pre-hook or post-hook variation",
            "feel": "minor/major ambiguity for bright melancholic color",
            "confidence": "low" if confidence == "low" else "medium",
            "notes": [
                "Works best when the melody chooses one strong landing note.",
                "Avoid recreating any known reference melody or exact chord voicing.",
            ],
        },
    ]
    if confidence == "low":
        for option in options:
            option["confirm_by_ear"] = True
            option["notes"].append("Key confidence is low; provide multiple options and confirm by ear before committing.")
    return options


def build_chord_progression_guide(
    *,
    key: dict[str, Any] | None = None,
    sample_analysis: dict[str, Any] | None = None,
    style_target: str = "commercial_digicore_hyperpop",
) -> dict[str, Any]:
    key_payload = normalize_key_payload(key, sample_analysis)
    return {
        "schema_version": "chord_progression_guide.v1",
        "status": "COMPOSITION_GUIDE_READY",
        "style_target": style_target,
        "key": key_payload,
        "options": generate_chord_options(key=key_payload, sample_analysis=sample_analysis, style_target=style_target),
        "safety": {
            "exact_reference_copy": False,
            "notes": [
                "Do not copy exact reference progressions, melodies, voicings, or recordings.",
                "Chord options are original guide sketches and must be confirmed by ear.",
            ],
        },
        "limitations": [
            "Key and harmony are guide-only when source confidence is low.",
            "No MIDI import or Logic execution is claimed by this guide.",
        ],
    }

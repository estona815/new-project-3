from __future__ import annotations

from typing import Any


def generate_topline_ideas(
    *,
    rough_request: str = "",
    vocal_to_code: dict[str, Any] | None = None,
    style_target: str = "commercial_digicore_hyperpop",
    key: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    phrases = (vocal_to_code or {}).get("phrases", [])
    phrase_hints = [
        {
            "phrase_id": phrase.get("phrase_id") or f"phrase_{index:02d}",
            "start": phrase.get("start"),
            "end": phrase.get("end"),
            "placement_use": "support hook placement; not exact transcription",
        }
        for index, phrase in enumerate(phrases[:4], start=1)
    ]
    tuning = "stronger_tuning_guide" if style_target in {"hyperpop", "commercial_digicore_hyperpop", "commercial_digicore"} else "natural_clear"
    return [
        {
            "idea_id": "topline_01",
            "role": "lead_vocal_hook",
            "placement": "hook early; keep vocal/melody forward",
            "phrase_hints": phrase_hints,
            "tuning_direction": tuning,
            "lyric_policy": "write original lyrics only; do not copy reference lyrics",
            "confidence": "medium" if phrase_hints else "low",
            "safety_notes": [
                "Use vocal_to_code for placement and contour hints only.",
                "No living artist vocal identity clone is allowed.",
            ],
        },
        {
            "idea_id": "topline_02",
            "role": "adlib_or_answer",
            "placement": "after hook call or bar-end gaps",
            "phrase_hints": [],
            "tuning_direction": "wider adlibs if style calls for hyperpop; keep sub and lead center clean",
            "lyric_policy": "new adlib text or non-lexical texture only",
            "confidence": "low" if (key or {}).get("confidence") == "low" else "medium",
            "safety_notes": ["Do not imitate a living artist voice or exact delivery."],
        },
    ]


def build_topline_guide(**kwargs: Any) -> dict[str, Any]:
    return {
        "schema_version": "topline_guide.v1",
        "status": "COMPOSITION_GUIDE_READY",
        "ideas": generate_topline_ideas(**kwargs),
        "safety": {
            "voice_clone": False,
            "exact_reference_copy": False,
            "notes": [
                "Topline guide does not claim exact vocal transcription.",
                "No voice cloning, lyric copying, or living artist impersonation is allowed.",
            ],
        },
        "limitations": ["Guide-only topline planning; no AutoTune, recording, or Logic processing is claimed."],
    }

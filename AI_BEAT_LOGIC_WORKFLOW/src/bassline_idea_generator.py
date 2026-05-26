from __future__ import annotations

from typing import Any


def generate_bassline_ideas(
    *,
    style_target: str = "commercial_digicore_hyperpop",
    chord_options: list[dict[str, Any]] | None = None,
    rough_request: str = "",
    key: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    text = rough_request.lower()
    strong_808 = "808" in text or "베이스" in text or style_target in {"commercial_digicore_hyperpop", "commercial_digicore", "hyperpop"}
    root_source = (chord_options or [{}])[0].get("roman", ["i"])
    confidence = "medium" if (key or {}).get("confidence") in {"medium", "high"} else "low"
    return [
        {
            "idea_id": "bassline_01",
            "role": "main_808",
            "pattern": "root-weighted hits with short fills into hook downbeats",
            "root_reference": root_source,
            "tone": "strong_controlled_808" if strong_808 else "simple_sub_bass",
            "mono_center_required": True,
            "upper_harmonics_width": "allowed only above the sub range",
            "confidence": confidence,
            "safety_notes": [
                "Do not copy exact reference basslines or kick/bass samples.",
                "Stereo-only source does not prove true kick/bass replacement.",
            ],
        },
        {
            "idea_id": "bassline_02",
            "role": "contrast",
            "pattern": "half-time held root notes for verse or breakdown contrast",
            "root_reference": root_source[:2],
            "tone": "clean_sub_with_light_saturation",
            "mono_center_required": True,
            "upper_harmonics_width": "narrow unless hook needs extra lift",
            "confidence": confidence,
            "safety_notes": ["Confirm roots by ear when key confidence is low."],
        },
    ]


def build_bassline_guide(**kwargs: Any) -> dict[str, Any]:
    return {
        "schema_version": "bassline_guide.v1",
        "status": "COMPOSITION_GUIDE_READY",
        "ideas": generate_bassline_ideas(**kwargs),
        "safety": {
            "exact_reference_copy": False,
            "notes": [
                "Bassline ideas are original MIDI/programming guidance only.",
                "Sub, kick, and 808 should remain mono-centered unless a verified stem/manual mix supports otherwise.",
            ],
        },
        "limitations": ["No true 808 replacement, stem separation, or rendered bass audio is claimed."],
    }

from __future__ import annotations

from typing import Any


STYLE_DRUM_DEFAULTS = {
    "commercial_digicore_hyperpop": ("energetic", "tight hats with 4-8 bar controlled variation"),
    "commercial_digicore": ("energetic", "tight hats with 4-8 bar controlled variation"),
    "hyperpop": ("energetic", "bright hats and controlled distortion"),
    "hip_hop": ("pocket", "less excessive width, rap-forward space"),
    "internet_underground": ("pocket_to_energetic", "humanized microtiming with digital color"),
    "system_seoul_adjacent": ("playful", "game-like rhythmic color as high-level trait only"),
    "custom": ("balanced", "simple groove with clear hook lift"),
}


def generate_drum_ideas(
    *,
    style_target: str = "commercial_digicore_hyperpop",
    rough_request: str = "",
    sample_analysis: dict[str, Any] | None = None,
    tempo: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    feel, note = STYLE_DRUM_DEFAULTS.get(style_target, STYLE_DRUM_DEFAULTS["custom"])
    onset_density = ((sample_analysis or {}).get("transient_onset") or {}).get("onset_density")
    confidence = "medium" if onset_density is not None or (tempo or {}).get("confidence") in {"medium", "high"} else "low"
    text = rough_request.lower()
    hook_early = any(item in text for item in ("릴스", "훅", "hook", "15"))
    return [
        {
            "idea_id": "drum_01",
            "role": "main_pattern",
            "feel": feel,
            "kick": "short punchy kick supporting 808 without clipping",
            "snare_clap": "bright tight center hit",
            "hats": note,
            "variation": "micro-fill before hook" if hook_early else "4-8 bar fill cycle",
            "confidence": confidence,
            "safety_notes": [
                "Do not copy exact reference drum patterns.",
                "Avoid random AI glitch and cheap rage clipping.",
            ],
        },
        {
            "idea_id": "drum_02",
            "role": "breakdown_pattern",
            "feel": "space_for_vocal_or_topline",
            "kick": "reduced kick density",
            "snare_clap": "alternate clap or rim layer",
            "hats": "half-density or filtered hats",
            "variation": "remove one drum lane before hook return",
            "confidence": confidence,
            "safety_notes": ["Use as programming guidance only; no true drum rewrite is claimed."],
        },
    ]


def build_drum_pattern_guide(**kwargs: Any) -> dict[str, Any]:
    return {
        "schema_version": "drum_pattern_guide.v1",
        "status": "COMPOSITION_GUIDE_READY",
        "ideas": generate_drum_ideas(**kwargs),
        "safety": {
            "exact_reference_copy": False,
            "notes": ["Drum ideas are high-level programming guidance and must not clone exact reference patterns."],
        },
        "limitations": ["No rendered drums, Logic import, or stereo-to-stem drum rewrite is claimed."],
    }

from __future__ import annotations

from typing import Any


def generate_drum_programming_guide(
    *,
    genre_mode: str = "digicore",
    length_mode: str = "under_2min",
    sample_analysis: dict[str, Any] | None = None,
    reference_profile: dict[str, Any] | None = None,
) -> dict[str, Any]:
    transient = (sample_analysis or {}).get("transient_onset") or {}
    onset_density = transient.get("onset_density")
    style = (reference_profile or {}).get("style_targets") or {}
    density_hint = style.get("drum_density")
    hat_density = "busy" if density_hint and density_hint >= 4 else "medium_fast" if genre_mode in {"hyperpop", "digicore", "commercial_digicore_hyperpop"} else "pocket"
    return {
        "schema_version": "drum_programming_guide.v1",
        "genre_mode": genre_mode,
        "length_mode": length_mode,
        "kick_character": "short punchy controlled transient",
        "snare_clap_character": "bright tight clap/snare with stable center",
        "hat_density": hat_density,
        "fill_amount": "controlled_4_to_8_bar" if length_mode != "reels_15sec" else "one_micro_fill_max",
        "swing": "light_humanized" if genre_mode in {"hip_hop", "internet_underground"} else "tight_with_micro_variation",
        "transient_target": "clear attack without cheap clipping",
        "programming_notes": [
            "Avoid generic trap unless specifically requested.",
            "Avoid random AI glitch; use fills as section punctuation.",
            "Leave space for vocal and hook motif.",
            "Do not copy exact reference drum patterns.",
        ],
        "analysis_hints": {"onset_density": onset_density, "dependency": "sample_analysis.transient_onset"},
        "limitations": ["Drum guide is MIDI/programming instruction only; no true drum rewrite is claimed."],
    }

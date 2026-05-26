from __future__ import annotations


SUPPORTED_INPUT_MODES = {
    "instrumental_beat",
    "full_song_stereo",
    "vocal_plus_beat",
    "stems",
    "sample_arrangement_plan_only",
}


def normalize_input_mode(mode: str | None) -> str:
    return mode if mode in SUPPORTED_INPUT_MODES else "instrumental_beat"


def default_mix_priorities(style_target: str = "commercial_digicore_hyperpop") -> list[str]:
    base = [
        "vocal_forwardness",
        "melody_preservation",
        "controlled_808",
        "hook_impact",
        "width_without_phase_issues",
    ]
    if style_target in {"hip_hop", "instrumental"}:
        return ["groove_pocket", "controlled_808", "melody_preservation", "width_without_phase_issues"]
    return base


def commercial_style_notes() -> list[str]:
    return [
        "hook clarity",
        "vocal/melody front",
        "808 strong but controlled",
        "width without phase issues",
        "no random AI harshness",
        "no overcompressed loudness-war result",
    ]

from __future__ import annotations

from typing import Any


def build_instrumental_mix_chain(input_mode: str, *, style_target: str = "commercial_digicore_hyperpop") -> dict[str, Any]:
    stereo_only = input_mode in {"instrumental_beat", "full_song_stereo"}
    return {
        "active": input_mode in {"instrumental_beat", "full_song_stereo", "vocal_plus_beat", "sample_arrangement_plan_only"},
        "scope": "stereo_only" if stereo_only else "beat_or_stem_bus",
        "high_pass_sub_rumble_only": True,
        "broad_eq": "broad tonal balance only; avoid surgical claims without stems",
        "controlled_saturation": "light to medium, checked for harshness",
        "width_plan": "width only on high-passed upper content",
        "sub_kick_808_center": True,
        "limiter_position": "final only",
        "clipping_policy": "no clipping",
        "style_target": style_target,
        "false_claim_guard": {
            "stem_level_rebalance_claimed": False,
            "kick_replacement_claimed": False,
            "drum_rewrite_claimed": False,
            "vocal_removal_claimed": False,
        },
        "limitations": [
            "Stereo-only input cannot provide true kick/bass replacement, true drum rewrite, or guaranteed vocal removal."
        ]
        if stereo_only
        else [],
    }

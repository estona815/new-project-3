from __future__ import annotations

from typing import Any


def build_stem_mix_plan(stems_available: bool = False) -> dict[str, Any]:
    return {
        "active": bool(stems_available),
        "scope": "stem_bus_direct_balancing" if stems_available else "unavailable",
        "drum_bus": "kick/snare/hat balance, transient shaping, parallel crush only if controlled",
        "bass_808_bus": "mono sub, saturation on upper harmonics, sidechain only when masking occurs",
        "melody_synth_bus": "mid cleanup, high-passed width layers, hook clarity rides",
        "vocal_bus": "lead/adlib/backing balance if vocal stems are present",
        "fx_sends": "shared reverb/delay sends with automation",
        "pre_master_bus": "headroom, no clipping, broad glue only",
        "master_bus": "target-specific chain from master_targets",
        "more_direct_balancing_allowed": bool(stems_available),
        "false_claim_guard": {
            "stem_level_changes_claimed_without_stems": False,
            "plugin_processing_verified": False,
        },
        "limitations": [] if stems_available else ["Stem mix plan becomes manual guidance until stems are provided."],
    }

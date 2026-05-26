from __future__ import annotations

from typing import Any


def build_vocal_mix_chain(
    *,
    input_mode: str,
    pitch_guide: dict[str, Any] | None = None,
    plugin_capabilities: dict[str, Any] | None = None,
    requested_style: str = "polished",
) -> dict[str, Any]:
    plugins = plugin_capabilities or {}
    decap = plugins.get("soundtoys_decapitator", {})
    autotune = plugins.get("autotune_like", {})
    isolated = input_mode in {"vocal_plus_beat", "stems"}
    return {
        "active": input_mode in {"vocal_plus_beat", "full_song_stereo", "stems"},
        "scope": "direct_vocal_bus" if isolated else "heuristic_full_mix_vocal_regions" if input_mode == "full_song_stereo" else "not_available",
        "clip_gain": "manual phrase-level clip gain before inserts",
        "cleanup_eq": "high-pass vocal rumble, subtract mud/resonances before brightness",
        "pitch_correction_guide": pitch_guide or {
            "recommended_mode": "subtle",
            "manual_logic_required": True,
            "claim_language": "recommended, not applied",
        },
        "compression": "serial leveling then tone/glue if needed",
        "saturation": _saturation_plan(decap),
        "de_ess": "after saturation/brightness; target S/T/SH without dulling the whole vocal",
        "tone_eq": "presence/air only after de-ess is stable",
        "reverb_delay_sends": "plate/room plus tempo delay throws at phrase endings",
        "vocal_bus_trim": "trim final vocal bus into beat/master bus without clipping",
        "false_claim_guard": {
            "auto_tune_applied": False,
            "pitch_correction_performed": False,
            "decapitator_applied": False,
            "plugin_processing_verified": False,
            "analysis_isolated": isolated,
            "autotune_plugin_available_hint": autotune.get("status", "manual_required"),
        },
        "limitations": [] if isolated else ["Full stereo vocal treatment is heuristic; no isolated vocal control is claimed."],
        "style": requested_style,
    }


def _saturation_plan(decap: dict[str, Any]) -> dict[str, Any]:
    detected = decap.get("status") in {"available", "detected"}
    return {
        "target": "controlled density before de-ess/tone checks",
        "decapitator_available_hint": detected,
        "plan": "manual Soundtoys Decapitator or equivalent" if detected else "generic saturation approximation or manual Logic instruction",
        "claim_language": "manual/available hint only; not applied",
    }

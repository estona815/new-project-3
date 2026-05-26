from __future__ import annotations

from typing import Any

from plugin_availability import decapitator_availability
from plugin_request_parser import parse_plugin_requests


def build_vocal_fx_intent(
    request_text: str | None,
    plugin_availability: dict[str, Any] | None = None,
    automation_can_insert_plugins: bool = False,
) -> dict[str, Any]:
    parsed = parse_plugin_requests(request_text)
    decapitator = plugin_availability or decapitator_availability()
    saturation = parsed["saturation"]
    requested_plugin = saturation.get("requested_plugin")
    plugin_detected = bool(decapitator.get("detected")) if requested_plugin == "Soundtoys Decapitator" else False

    if requested_plugin == "Soundtoys Decapitator" and plugin_detected and automation_can_insert_plugins:
        plugin_status = "verified_insert_possible"
        claim = "verified plugin application may be claimed only after render/log verification"
        fallback = None
    elif requested_plugin == "Soundtoys Decapitator" and plugin_detected:
        plugin_status = "manual_required"
        claim = "do not claim Decapitator applied; manual Logic insertion is required"
        fallback = "generic saturation approximation"
    elif requested_plugin == "Soundtoys Decapitator":
        plugin_status = "fallback_generic"
        claim = "do not claim Decapitator applied; plugin was not detected"
        fallback = "generic saturation approximation"
    elif saturation.get("requested"):
        plugin_status = "generic_saturation"
        claim = "generic saturation approximation only"
        fallback = "generic saturation approximation"
    else:
        plugin_status = "not_requested"
        claim = "no saturation plugin requested"
        fallback = None

    pitch = parsed["pitch_correction"]
    deess_required = bool(
        saturation.get("requested")
        or saturation.get("tone") == "bright"
        or pitch.get("intensity") in {"medium", "hard_effect"}
    )
    return {
        "raw_text": parsed["raw_text"],
        "vocal_target_active": parsed["vocal_target_active"],
        "pitch_correction": pitch,
        "saturation": saturation,
        "plugin_availability": decapitator if requested_plugin == "Soundtoys Decapitator" else {},
        "plugin_application": {
            "requested_plugin": requested_plugin,
            "status": plugin_status,
            "plugin_exact_application_allowed": bool(plugin_status == "verified_insert_possible"),
            "claim_language": claim,
            "fallback": fallback,
            "manual_logic_instruction": "Insert Soundtoys Decapitator on the vocal bus if installed."
            if requested_plugin == "Soundtoys Decapitator"
            else None,
        },
        "chain_rules": [
            "tuning before saturation in most cases",
            "de-ess after brightening/saturation if sibilance risk increases",
            "use compression before and/or after saturation depending on the vocal",
            "preserve the user's voice identity",
            "artist references become production targets only",
        ],
        "deess_required": deess_required,
        "preserve_user_voice_identity": True,
        "identity_clone_allowed": False,
        "artist_voice_clone_allowed": False,
        "qc_checks": [
            "harshness/sibilance risk after saturation or bright tuning",
            "no Decapitator application claim unless plugin insertion/render is verified",
            "fallback processing is labelled generic saturation approximation",
        ],
    }

from __future__ import annotations

from typing import Any


def limitations_for_mode(options: dict[str, Any]) -> list[str]:
    mode = options.get("mode", "instrumental_beat")
    if mode in {"full_song_stereo", "instrumental_beat"}:
        return [
            "No real vocal removal from stereo is claimed.",
            "No professional stem-level vocal mixing is claimed from a full stereo file.",
            "No stem-level drum/808 changes are claimed without stems.",
        ]
    if mode == "vocal_plus_beat":
        return [
            "Separate vocal processing is limited to user-provided vocal files.",
            "Autotune is only available if a pitch tool is installed.",
            "Reference text/audio guides broad taste translation, not exact copying.",
        ]
    return [
        "Stem-level changes are limited to stems explicitly provided by the user.",
        "No exact artist, producer, or reference-song clone is claimed.",
        "Manual Logic Pro steps may still be required for detailed automation.",
    ]


def processing_scope(options: dict[str, Any]) -> str:
    mode = options.get("mode", "instrumental_beat")
    if mode == "vocal_plus_beat":
        return "separate vocal plus beat processing" if options.get("vocal_file") or options.get("lead_vocal_file") else "missing separate vocal file"
    if mode == "stems":
        return "provided-stem planning" if any(options.get(key) for key in ("lead_vocal_file", "adlib_file", "backing_vocal_file", "beat_file")) else "stems mode without provided stems"
    if mode == "full_song_stereo":
        return "stereo-only broad mastering and heuristic vocal-region analysis"
    return "instrumental beat processing"


def build_processing_log(
    options: dict[str, Any],
    pitch_available: bool,
    pitch_note: str,
    vocal_analysis: dict[str, Any],
    processing_result: dict[str, Any] | None = None,
) -> str:
    mode = options.get("mode", "instrumental_beat")
    if mode in {"vocal_plus_beat", "stems"} and (options.get("vocal_file") or options.get("lead_vocal_file")):
        actual = "actual separate vocal processing: direct vocal analysis and mix planning"
    elif mode == "full_song_stereo":
        actual = "stereo-only broad processing and heuristic vocal-region analysis"
    else:
        actual = "instrumental or planning-only processing"
    lines = [
        "# Vocal Processing Log",
        "",
        f"- actual processing category: {actual}",
        f"- pitch tool available: {str(pitch_available).lower()}",
        f"- pitch tool note: {pitch_note}",
        f"- analysis mode: {vocal_analysis.get('mode', mode)}",
        "",
        "## Processing Render Results",
    ]
    if processing_result:
        for label, item in processing_result.get("processed_vocals", {}).items():
            if item.get("created"):
                lines.append(f"- {label}: rendered {item.get('output_path')}")
            else:
                lines.append(f"- {label}: not rendered; {item.get('reason', 'reason unavailable')}")
        pre_master = processing_result.get("pre_master", {})
        if pre_master.get("created"):
            lines.append(f"- pre_master.wav: rendered {pre_master.get('path')}")
        else:
            lines.append(f"- pre_master.wav: not rendered; {pre_master.get('reason', 'not enough separate inputs to mix')}")
        for instruction in processing_result.get("manual_logic_instructions", []):
            lines.append(f"- manual Logic: {instruction}")
        vocal_fx = processing_result.get("vocal_fx_intent", {})
        if vocal_fx:
            saturation = vocal_fx.get("saturation", {})
            plugin = vocal_fx.get("plugin_application", {})
            lines.append(f"- vocal FX pitch correction: {vocal_fx.get('pitch_correction', {}).get('intensity', 'none')}")
            lines.append(f"- vocal FX saturation: {saturation.get('intensity', 'none')} via {saturation.get('requested_plugin') or 'generic saturation'}")
            lines.append(f"- vocal FX plugin status: {plugin.get('status', 'not_requested')}; {plugin.get('claim_language', '')}")
        for limitation in processing_result.get("limitations", []):
            lines.append(f"- limitation: {limitation}")
    else:
        lines.append("- No processing render result was provided.")
    lines.extend(
        [
            "",
            "## Honesty Rules",
        ]
    )
    lines.extend(f"- {item}" for item in limitations_for_mode(options))
    if mode == "full_song_stereo":
        lines.append("- Full stereo findings are likely/heuristic candidates only, not isolated vocal measurements.")
    return "\n".join(lines) + "\n"


def build_reference_translation(options: dict[str, Any]) -> str:
    brief = options.get("creative_brief") or {}
    avoid = brief.get("avoid", [])
    return (
        "# Style Translation\n\n"
        f"- reference audio: {options.get('reference_audio') or 'not provided'}\n"
        f"- reference text: {options.get('reference_text') or 'not provided'}\n"
        f"- creative target: {brief.get('creative_target') or options.get('creative_target') or 'not provided'}\n"
        f"- priority: {brief.get('priority') or options.get('priority') or 'not provided'}\n"
        f"- avoid list: {', '.join(avoid) if avoid else options.get('avoid_list') or 'not provided'}\n"
        "- This is a broad production target translation only.\n"
        "- It does not copy an exact reference song, artist, producer, melody, mix, or master.\n"
    )


def build_mix_session_plan(options: dict[str, Any], processing_result: dict[str, Any] | None = None) -> str:
    pre_master = (processing_result or {}).get("pre_master", {})
    brief = options.get("creative_brief") or {}
    pre_master_line = (
        f"- pre_master.wav: rendered at {pre_master.get('path')}"
        if pre_master.get("created")
        else f"- pre_master.wav: not rendered ({pre_master.get('reason', 'reserved for future rendered mix stage')})"
    )
    lines = [
        "# Mix / Master Session Plan",
        "",
        f"- mode: {options.get('mode', 'instrumental_beat')}",
        f"- master loudness target: {options.get('master_loudness', 'master_ready_headroom')}",
        f"- mix intensity: {options.get('mix_intensity', 'standard')}",
        f"- creative target: {brief.get('creative_target') or options.get('creative_target') or 'not provided'}",
        f"- priority: {brief.get('priority') or options.get('priority') or 'not provided'}",
        f"- vocal direction: {brief.get('vocal_direction') or options.get('vocal_direction') or 'not provided'}",
        f"- drum/808 direction: {brief.get('drum_808_direction') or options.get('drum_808_direction') or options.get('drum_808', 'not provided')}",
        f"- master direction: {brief.get('master_direction') or options.get('master_direction') or 'not provided'}",
        pre_master_line,
        "- final_mix_master.wav: reserved for future rendered mix/master stage",
        "",
        "## Manual Logic Pro Steps",
        "- Use Logic for detailed vocal rides, region edits, breath cleanup, doubles/adlibs balance, throws, and automation.",
        "- Use the existing final export/QC stage before claiming completion.",
        "",
        "## Limits",
    ]
    lines.extend(f"- {item}" for item in limitations_for_mode(options))
    return "\n".join(lines) + "\n"

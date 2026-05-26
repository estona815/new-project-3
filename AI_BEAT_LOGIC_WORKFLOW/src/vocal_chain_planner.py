from __future__ import annotations

from typing import Any

from vocal_fx_intent import build_vocal_fx_intent
from vocal_mix_autopilot import build_vocal_mix_chain


def _analysis_notes(vocal_analysis: dict[str, Any]) -> list[str]:
    mode = vocal_analysis.get("mode", "instrumental_beat")
    vocal_code = vocal_analysis.get("vocal_to_code", {})
    code_lines = []
    if vocal_code:
        code_lines = [
            f"- vocal-to-code phrases: {len(vocal_code.get('phrases', []))}",
            f"- vocal-to-code isolated: {str(bool(vocal_code.get('input', {}).get('analysis_isolated'))).lower()}",
            f"- pitch guide claim: {vocal_code.get('pitch_correction_guide', {}).get('claim_language', 'recommended, not applied')}",
        ]
    if mode == "full_song_stereo":
        full_song = vocal_analysis.get("full_stereo_song", {})
        return [
            "- Treat all vocal-region findings as heuristic full-mix listening targets.",
            f"- likely vocal-forward sections: {len(full_song.get('likely_vocal_forward_sections', []))}",
            f"- likely vocal-masked sections: {len(full_song.get('likely_vocal_masked_sections', []))}",
            f"- sibilance-like high-frequency candidates: {len(full_song.get('sibilance_like_high_frequency_candidates', []))}",
            *code_lines,
        ]

    lead = vocal_analysis.get("files", {}).get("lead_vocal", {})
    metrics = lead.get("metrics", {})
    if not metrics:
        return ["- No separate lead vocal metrics were available; prepare manual gain and cleanup checks."]
    noise_floor = metrics.get("noise_floor_estimate", {}).get("estimated_noise_floor_dbfs")
    density = metrics.get("vocal_density", {}).get("active_ratio")
    return [
        f"- lead duration: {metrics.get('duration_seconds', 0):.2f}s",
        f"- lead sample rate/channels: {metrics.get('sample_rate')} Hz / {metrics.get('channels')}",
        f"- lead peak/RMS: {metrics.get('peak_dbfs'):.2f} dBFS / {metrics.get('rms_dbfs'):.2f} dBFS",
        f"- clipping samples: {metrics.get('clipping_count')}",
        f"- noise floor estimate: {noise_floor if noise_floor is not None else 'unavailable'} dBFS",
        f"- vocal density: {density if density is not None else 'unavailable'}",
        f"- plosive/sibilance/harshness candidates: {len(lead.get('plosive_candidates', []))}/{len(lead.get('sibilance_candidates', []))}/{len(lead.get('harshness_candidates', []))}",
        *code_lines,
    ]


def _style_notes(options: dict[str, Any]) -> list[str]:
    style = options.get("vocal_style", "polished")
    if style == "rap_forward":
        return [
            "- Keep the lead upfront with firmer leveling compression.",
            "- Use less reverb and keep delay throws mostly at phrase ends.",
            "- Control sibilance before adding presence so consonants stay sharp but not piercing.",
        ]
    if style in {"hyperpop", "digicore"}:
        return [
            "- Push brighter vocal presence after subtractive cleanup.",
            "- Use controlled hard tuning only when selected and available.",
            "- Keep adlibs wider and more stylized than the lead.",
            "- Use wider delay/reverb textures without masking lyric intelligibility.",
        ]
    if style == "airy_pop":
        return [
            "- Add air only after de-essing is stable.",
            "- Favor plate or hall sends at a low level with pre-delay.",
            "- Keep compression smooth enough to preserve breath and intimacy.",
        ]
    if style == "aggressive":
        return [
            "- Use stronger serial compression and saturation, then trim harshness.",
            "- Keep ambience short unless throws are automated.",
            "- Watch 2-5 kHz buildup from saturation and presence boosts.",
        ]
    if style == "intimate":
        return [
            "- Preserve close-mic detail and avoid heavy widening on the lead.",
            "- Use light room/plate ambience at low send levels.",
            "- Manually ride breaths rather than deleting all texture.",
        ]
    if style == "natural":
        return [
            "- Favor transparent cleanup, modest compression, and minimal effects.",
            "- Avoid obvious tuning artifacts unless requested.",
            "- Keep EQ moves broad and conservative.",
        ]
    return [
        "- Use a polished modern vocal chain with controlled dynamics and tasteful ambience.",
        "- Make cleanup decisions before adding saturation, air, or sends.",
    ]


def build_vocal_chain_plan(options: dict[str, Any], vocal_analysis: dict[str, Any], pitch_available: bool, pitch_note: str) -> str:
    mode = options.get("mode", "instrumental_beat")
    autotune = options.get("autotune", "subtle")
    brief = options.get("creative_brief") or {}
    avoid = brief.get("avoid", [])
    request_text = " ".join(
        str(item)
        for item in (
            options.get("vocal_fx_request"),
            options.get("reference_text"),
            options.get("creative_target"),
            options.get("vocal_direction"),
            brief.get("creative_target"),
            brief.get("vocal_direction"),
        )
        if item
    )
    vocal_fx = options.get("vocal_fx_intent") if isinstance(options.get("vocal_fx_intent"), dict) else build_vocal_fx_intent(request_text)
    if mode == "full_song_stereo":
        process_scope = (
            "Only broad full-mix mastering moves and heuristic vocal-region checks can be processed. "
            "The embedded vocal cannot be isolated or controlled as a separate stem."
        )
    elif mode in {"vocal_plus_beat", "stems"}:
        process_scope = (
            "Separate user-provided vocal files can receive direct gain, cleanup, EQ, dynamics, de-essing, "
            "saturation, ambience planning, and manual Logic automation."
        )
    else:
        process_scope = "No vocal file was provided; vocal processing is not active for instrumental beat mode."

    pitch_line = (
        f"Autotune requested: {autotune}. Pitch-capable tool available at {pitch_note}."
        if autotune != "none" and pitch_available
        else f"Autotune requested: {autotune}. Unavailable or bypassed: {pitch_note}."
    )
    saturation = vocal_fx.get("saturation", {})
    plugin_app = vocal_fx.get("plugin_application", {})
    autopilot_chain = build_vocal_mix_chain(
        input_mode=mode,
        pitch_guide=(vocal_analysis.get("vocal_to_code") or {}).get("pitch_correction_guide"),
        requested_style=options.get("vocal_style", "polished"),
    )

    lines = [
        "# Vocal Chain Plan",
        "",
        "## 1. Input Mode",
        f"- mode: {mode}",
        f"- vocal style: {options.get('vocal_style', 'polished')}",
        f"- mix intensity: {options.get('mix_intensity', 'standard')}",
        f"- creative target: {brief.get('creative_target') or options.get('creative_target') or 'not provided'}",
        f"- requested vocal direction: {brief.get('vocal_direction') or options.get('vocal_direction') or 'not provided'}",
        f"- requested avoid list: {', '.join(avoid) if avoid else options.get('avoid_list') or 'not provided'}",
        "",
        "## 2. What Can Actually Be Processed",
        f"- {process_scope}",
        f"- vocal mix autopilot scope: {autopilot_chain.get('scope')}",
        f"- AutoTune applied claim: {str(bool(autopilot_chain.get('false_claim_guard', {}).get('auto_tune_applied'))).lower()}",
        f"- Decapitator applied claim: {str(bool(autopilot_chain.get('false_claim_guard', {}).get('decapitator_applied'))).lower()}",
        *_analysis_notes(vocal_analysis),
        "",
        "## 3. Vocal Cleanup Plan",
        "- Start with clip gain and gain staging before inserts.",
        "- Remove or turn down obvious silent gaps, headphone bleed, clicks, and breath/noise-heavy regions only after listening.",
        "- If plosive candidates are present, use clip gain, short fades, or high-pass automation before compression.",
        "- Lead vocal remains the priority; adlibs should be thinner, lower, wider, and should not fight the lead.",
        "- Backing vocals should have controlled low end, softer presence, wider placement, and group compression if needed.",
        "",
        "## 4. EQ Plan",
        "- High-pass the lead vocal, usually 70-120 Hz depending on voice and proximity effect.",
        "- Cut mud around 150-400 Hz only where the analysis/listening check supports it.",
        "- Control resonances before adding presence or air.",
        "- Add presence/air only after de-essing is stable.",
        "",
        "## 5. Compression Plan",
        "- Compression stage 1: leveling, slow enough to keep consonants natural and fast enough to hold phrases steady.",
        "- Compression stage 2: optional tone/glue after de-essing if the vocal still moves too much.",
        "- Finish with final vocal bus trim so the vocal lands in the beat without clipping the mix bus.",
        "",
        "## 6. De-Essing Plan",
        f"- De-ess strength: {options.get('deess', 'medium')}.",
        "- Target S/T/SH candidates manually; do not dull the whole vocal just to fix a few consonants.",
        "- For rap-forward mixes, control sibilance before upfront compression makes it feel louder.",
        "",
        "## 7. Saturation Plan",
        f"- Saturation request: {str(bool(saturation.get('requested'))).lower()}.",
        f"- Requested plugin: {saturation.get('requested_plugin') or 'not provided'}.",
        f"- Saturation target: {saturation.get('intensity', 'none')} intensity, {saturation.get('parallel_mix', 'none')} parallel mix, {saturation.get('tone', 'neutral')} tone, apply to {saturation.get('apply_to', 'lead_vocal')}.",
        f"- Plugin status: {plugin_app.get('status', 'not_requested')}. {plugin_app.get('claim_language', '')}".rstrip(),
        *([f"- Manual Logic instruction: {plugin_app.get('manual_logic_instruction')}"] if plugin_app.get("manual_logic_instruction") else []),
        *([f"- Fallback: {plugin_app.get('fallback')} only; do not label it as Decapitator."] if plugin_app.get("fallback") else []),
        "- Add gentle saturation after dynamics for density, then check harshness again.",
        "- For aggressive/hyperpop settings, saturation can be more audible, but harsh upper mids still need control.",
        "",
        "## 8. Reverb/Delay Plan",
        f"- Reverb space: {options.get('reverb_space', 'plate')}.",
        f"- Delay style: {options.get('delay_style', 'throw_only')}.",
        "- Keep lead reverb lower than adlibs/backings unless the style intentionally calls for washed vocals.",
        "- Automate delay throws at phrase ends so words stay intelligible.",
        "",
        "## 9. Autotune/Pitch Plan",
        f"- {pitch_line}",
        f"- Parsed pitch correction request: {vocal_fx.get('pitch_correction', {}).get('intensity', autotune)}.",
        "- Keep tuning before saturation in most cases.",
        "- Preserve the user's formant and vocal identity; do not clone 2hollis, Nate Sib, ycs, or any artist voice.",
        "- Creative formant or pitch effects should be manual decisions, especially for hyperpop/digicore.",
        "",
        "## 10. Manual Logic Pro Checklist",
        "- Import lead, adlibs, backing vocals, and beat into clearly named tracks.",
        "- Confirm all files start at the intended bar/time and check phase against the beat.",
        "- Do clip gain rides before compressors.",
        "- Automate lead vocal level through hooks, verses, and phrase endings.",
        "- Automate delay throws and reverb sends only where they serve the arrangement.",
        "- Bounce a pre-master and run final export/QC before any completion claim.",
        "",
        "## 11. Limitations",
        "- No real vocal removal from stereo is claimed unless a real separation model is installed and used.",
        "- No exact reference song, artist, or producer clone is claimed.",
        "- No stem-level drum, 808, or vocal control is claimed without separate stems.",
    ]
    lines.extend(_style_notes(options))
    return "\n".join(lines) + "\n"

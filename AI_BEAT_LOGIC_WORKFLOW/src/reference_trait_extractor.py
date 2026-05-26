from __future__ import annotations

from typing import Any

from reference_intent_parser import clamp


DEFAULT_AVOID = [
    "exact copying",
    "artist vocal identity cloning",
    "muddy sub",
    "random AI glitch",
    "generic trap loop",
    "cheap rage clipping",
]


def _has(text: str, *terms: str) -> bool:
    return any(term in text for term in terms)


def _claims_text(web_research: dict[str, Any] | None) -> str:
    if web_research and not web_research.get("trait_inference_allowed", False):
        return ""
    claims: list[str] = []
    for source in (web_research or {}).get("sources", []):
        claims.extend(str(item) for item in source.get("relevant_claims", []))
    return " ".join(claims).lower()


def _target_elements(parsed: dict[str, Any], text: str) -> list[str]:
    raw = text.lower()
    elements = set()
    for request in parsed.get("reference_requests", []):
        element = request.get("target_element")
        if element in {"bass", "808"}:
            elements.add("bass_808")
        elif element == "whole_song":
            elements.add("whole_style")
        elif element:
            elements.add(str(element))
    if _has(raw, "드럼", "drum", "kick", "snare", "hat", "디지코어"):
        elements.add("drums")
    if _has(raw, "808", "베이스", "bass", "서브", "sub"):
        elements.add("bass_808")
    if _has(raw, "신스", "신디", "synth", "pan", "panning", "좌우", "벌리", "공간감", "wide", "stereo", "넓"):
        elements.add("synth_width")
    if _has(raw, "목소리", "보컬", "voice", "vocal", "2hollis", "nate sib"):
        elements.add("vocal")
    if _has(raw, "멜로디", "melody"):
        elements.add("melody")
    if _has(raw, "릴스", "hook", "훅", "15초", "15 sec"):
        elements.add("arrangement")
    return sorted(elements) or ["whole_song"]


def _confidence(parsed: dict[str, Any], web_research: dict[str, Any] | None, audio_analysis: dict[str, Any] | None) -> str:
    if (audio_analysis or {}).get("available"):
        return "high"
    if (web_research or {}).get("web_reference_research_unavailable"):
        return "low"
    if web_research and not web_research.get("trait_inference_allowed", False):
        return "low"
    web_confidence = (web_research or {}).get("combined_confidence")
    if web_confidence in {"medium", "high"}:
        return "medium"
    return "low"


def _contains_any(items: list[str], *needles: str) -> bool:
    haystack = " ".join(str(item).lower() for item in items)
    return any(needle in haystack for needle in needles)


def _evidence_mode(web_research: dict[str, Any] | None, audio_analysis: dict[str, Any] | None) -> str:
    if (audio_analysis or {}).get("available"):
        return "audio_informed"
    if (web_research or {}).get("trait_inference_allowed"):
        return "web_informed"
    return "text_only"


def extract_reference_traits(
    *,
    user_phrase: str | None,
    parsed_intent: dict[str, Any],
    web_research: dict[str, Any] | None = None,
    audio_analysis: dict[str, Any] | None = None,
) -> dict[str, Any]:
    text = (user_phrase or parsed_intent.get("raw_text") or "").lower()
    claims = _claims_text(web_research)
    combined = f"{text} {claims}"
    explicit = parsed_intent.get("explicit_targets", {})
    style = parsed_intent.get("style_targets", {})
    parsed_avoid = parsed_intent.get("avoid", [])
    processing = explicit.get("processing", {})
    target_elements = _target_elements(parsed_intent, text)
    active_targets = set(target_elements)

    drum_density = explicit.get("drums", {}).get("density", style.get("drum_density", 3))
    scene_style = _has(combined, "2hollis", "투홀리스", "2홀리스", "system seoul", "시스템서울", "시스템 서울", "ycs", "와이씨에스", "ss-pop", "디지코어", "digicore", "hyperpop")
    if scene_style:
        drum_density = max(int(drum_density), 4)
    hat_density = style.get("hat_density", drum_density)
    kick = "short_punchy" if _has(combined, "punchy", "킥", "kick", "따와", "love blur", "디지코어", "digicore") else "distorted" if _has(combined, "rage", "distorted") else "soft"
    snare = "digital" if _has(combined, "digital", "digicore", "love blur", "디지코어") else "wide" if _has(combined, "wide", "넓") else "tight"
    swing = explicit.get("drums", {}).get("swing")
    if not swing or swing == "unknown":
        swing = "light" if int(drum_density) >= 4 else "straight"
    fill_amount = explicit.get("drums", {}).get("fill_amount", 3)
    transient = explicit.get("drums", {}).get("transient_sharpness", 3)

    bass = explicit.get("bass_808", {})
    glide = bass.get("glide", 1)
    if _has(combined, "glide", "글라이드"):
        glide = 5
    sub_weight = bass.get("sub_weight", style.get("low_end_weight", 3))
    if _has(combined, "단단", "strong", "hard", "808"):
        sub_weight = max(int(sub_weight), 4)
    melody_preserve = bool(explicit.get("melody", {}).get("preserve") or _has(combined, "멜로디는 살리고", "멜로디는 살려", "멜로디 덮지", "keep melody", "do not cover melody", "melody center", "중앙"))
    more_808 = bool(_has(combined, "808은 더 세게", "808 더 세게", "more 808", "stronger 808", "808만 더 세게"))
    if more_808 and melody_preserve:
        sub_weight = clamp(int(sub_weight) + 1)
    tone = bass.get("tone")
    if not tone or tone == "unknown":
        tone = "gliding" if int(glide) >= 4 else "saturated" if _has(combined, "saturated", "rage") else "clean"
    movement = bass.get("movement")
    if not movement or movement == "unknown":
        movement = "melodic" if _has(combined, "melodic", "글라이드", "glide") else "simple"
    distortion = bass.get("distortion", style.get("808_distortion", 2))
    if _has(combined, "싸게 클리핑", "cheap clipping", "not clipped", "않게"):
        distortion = min(int(distortion), 3)

    pan_motion = "none"
    if _has(combined, "auto pan", "오토팬"):
        pan_motion = "auto_pan"
    elif _has(combined, "좌우", "벌리", "panning", "pan", "공간감"):
        pan_motion = "medium"
    stereo_width = 4 if pan_motion in {"medium", "wide", "auto_pan"} or _has(combined, "wide", "넓") else 2
    mid_side = "keep_melody_center_widen_layers" if _has(combined, "멜로디", "melody", "center", "중앙") else "wide_pads_only" if "synth_width" in target_elements else "unknown"

    vocal = explicit.get("vocal", {})
    vocal_forward = vocal.get("forwardness", style.get("vocal_forwardness", 3))
    lead_position = "very_front" if int(vocal_forward) >= 5 else "front" if int(vocal_forward) >= 4 else "natural"
    processing_autotune = processing.get("autotune")
    vocal_active = "vocal" in active_targets
    tuning = vocal.get("tuning") if vocal.get("tuning") != "unknown" else processing_autotune if processing_autotune and processing_autotune != "unknown" else "medium" if vocal_active and _has(combined, "오토튠", "2hollis", "nate sib", "hyperpop", "디지코어") else "none" if not vocal_active else "subtle"
    brightness = vocal.get("brightness", style.get("brightness", 3))
    compression = "strong" if lead_position == "very_front" else "medium"
    requested_plugin = "Soundtoys Decapitator" if _has(combined, "디카페이터", "데카피테이터", "decapitator", "soundtoys", "사운드토이즈") else None
    if requested_plugin:
        saturation = "subtle" if _has(combined, "살짝") else "strong" if _has(combined, "빡세게") else "medium"
    else:
        saturation = "strong" if processing.get("saturation_style") == "decapitator_style_saturation" else "medium" if _has(combined, "rage", "distorted", "saturated", "hyperpop", "digicore") else "none" if not vocal_active else "subtle"
    reverb_space = "plate" if _has(combined, "pop", "hyperpop", "2hollis", "nate sib") else "small_room"
    delay_style = "throw_only" if _has(combined, "rap", "nate sib", "2hollis") else "none"

    hook_early = explicit.get("arrangement", {}).get("hook_early", False) or scene_style or _has(combined, "릴스", "15초", "15 sec", "hook", "훅")
    target_hook_seconds = explicit.get("arrangement", {}).get("target_hook_seconds")
    if hook_early and target_hook_seconds is None:
        target_hook_seconds = 15 if _has(combined, "15", "15초") else None
    if target_hook_seconds not in {15, None}:
        target_hook_seconds = 15 if _has(combined, "15", "15초") else None

    avoid = list(dict.fromkeys(DEFAULT_AVOID + parsed_avoid))
    evidence = []
    if web_research:
        evidence.append(f"web confidence: {web_research.get('combined_confidence', 'low')}")
        evidence.append(f"web trait inference allowed: {str(bool(web_research.get('trait_inference_allowed'))).lower()}")
        for source in web_research.get("sources", [])[:3]:
            claims_text = "; ".join(source.get("relevant_claims", [])[:2])
            existence_text = "; ".join(source.get("existence_claims", [])[:1])
            if claims_text:
                evidence.append(f"{source.get('source_type')}: {claims_text}")
            elif existence_text:
                evidence.append(f"{source.get('source_type')}: existence only - {existence_text}")
        for limitation in web_research.get("source_limitations", [])[:3]:
            evidence.append(f"source limitation: {limitation}")
    if (audio_analysis or {}).get("available"):
        evidence.append("reference audio analysis available; broad audio heuristics used")
    if not evidence:
        evidence.append("text-only prompt interpretation; low-confidence high-level production target")

    copying_risk = str(parsed_intent.get("copying_risk", "none"))
    requires_owned_source = bool(parsed_intent.get("requires_user_owned_source_for_sampling") or copying_risk == "high")
    confidence = _confidence(parsed_intent, web_research, audio_analysis)
    evidence_mode = _evidence_mode(web_research, audio_analysis)
    avoid_generic_trap = bool("generic trap loop" in avoid or scene_style)
    avoid_uncontrolled_rage = bool("cheap rage clipping" in avoid or _has(combined, "cheap rage clipping", "피하라", "덜 싸게"))
    drums_active = bool(active_targets & {"drums", "kick", "snare", "hats"} or scene_style)
    bass_active = bool("bass_808" in active_targets or scene_style)
    synth_active = bool("synth_width" in active_targets or scene_style)
    arrangement_active = bool("arrangement" in active_targets or hook_early)
    reduce_random_ai_glitch = bool("random AI glitch" in avoid or scene_style or _has(combined, "random ai glitch", "랜덤", "난잡"))
    sidechain_needed = bool((bass_active and melody_preserve) or _has(combined, "sidechain", "사이드체인", "덮지"))
    if scene_style:
        sub_weight = max(int(sub_weight), 4)
        stereo_width = max(int(stereo_width), 4)
        hat_density = max(int(hat_density), 4)
        fill_amount = max(int(fill_amount), 3)
    return {
        "target_elements": target_elements,
        "drums": {
            "active": drums_active,
            "density": clamp(int(drum_density)),
            "kick_character": kick,
            "kick_low_weight": clamp(int(sub_weight if drums_active else 3)),
            "kick_transient": clamp(int(transient)),
            "snare_clap_character": snare,
            "hat_density": clamp(int(hat_density)),
            "swing": swing,
            "fill_amount": clamp(int(fill_amount)),
            "avoid_generic_trap": avoid_generic_trap,
            "avoid_uncontrolled_rage_clipping": avoid_uncontrolled_rage,
            "transient_sharpness": clamp(int(transient)),
            "copying_risk": "low" if "drums" in target_elements else "none",
        },
        "bass_808": {
            "active": bass_active,
            "sub_weight": clamp(int(sub_weight)),
            "tone": tone,
            "glide": clamp(int(glide)),
            "movement": movement,
            "distortion": clamp(int(distortion)),
            "sidechain_needed": sidechain_needed,
            "must_not_mask_melody": melody_preserve,
            "mono_sub_required": True,
            "wide_upper_harmonics_allowed": True,
        },
        "synth_width": {
            "active": synth_active,
            "pan_motion": pan_motion,
            "stereo_width": clamp(int(stereo_width)),
            "widen_upper_layers_only": True,
            "mid_side_approach": mid_side,
            "mono_compatibility_required": True,
            "low_frequency_mono_cutoff_hz": 120,
        },
        "vocal": {
            "active": vocal_active or scene_style,
            "preserve_user_identity": True,
            "identity_clone_allowed": False,
            "identity_preserve": bool(vocal.get("identity_preserve") or _has(combined, "내 목소리 유지", "내 목소리는 유지", "own voice", "keep my voice")),
            "lead_position": lead_position,
            "pitch_correction": tuning,
            "brightness": clamp(int(brightness)),
            "tuning": tuning,
            "compression": compression,
            "saturation": saturation,
            "requested_plugin": requested_plugin,
            "deess_required": bool(requested_plugin or saturation in {"medium", "strong"} or clamp(int(brightness)) >= 4),
            "reverb_space": reverb_space,
            "delay_style": delay_style,
            "plugin_style_reference": processing.get("plugin_style_reference"),
        },
        "arrangement": {
            "active": arrangement_active,
            "hook_early": bool(hook_early),
            "target_hook_seconds": target_hook_seconds,
            "variation_frequency_bars": explicit.get("arrangement", {}).get("variation_frequency_bars") or (4 if hook_early else 8),
            "reduce_random_ai_glitch": reduce_random_ai_glitch,
        },
        "master": {
            "target": "loud_demo" if _has(combined, "loud demo", "loud_demo") else "streaming_safe" if _has(combined, "streaming", "스트리밍") else "master_ready_headroom",
            "avoid_overcompression": True,
            "peak_target_dbfs": -1.0,
        },
        "melody": {
            "preserve": melody_preserve,
            "center_priority": bool(_has(combined, "멜로디", "melody", "중앙", "center")),
        },
        "avoid": avoid,
        "safety": {
            "exact_copy_allowed": bool(parsed_intent.get("exact_copy_allowed", False)),
            "copying_risk": copying_risk,
            "requires_user_owned_source_for_sampling": requires_owned_source,
            "confidence": confidence,
            "evidence_mode": evidence_mode,
        },
        "confidence": confidence,
        "evidence_summary": evidence,
        "source_limitations": list((web_research or {}).get("source_limitations", [])),
        "trait_inference_allowed": bool((web_research or {}).get("trait_inference_allowed", False) or (audio_analysis or {}).get("available")),
    }

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from commercial_digicore_autopilot import build_commercial_digicore_autopilot
from reference_audio_analysis import analyze_reference_audio
from reference_copying_policy import evaluate_copying_request
from reference_intent_parser import clamp, parse_reference_intent
from reference_trait_extractor import extract_reference_traits


def _scale(value: float, thresholds: tuple[float, float, float, float]) -> int:
    score = 1
    for threshold in thresholds:
        if value >= threshold:
            score += 1
    return clamp(score)


def _source_mode(reference_text: str | None, reference_audio: str | None) -> str:
    has_text = bool(reference_text)
    has_audio = bool(reference_audio)
    if has_text and has_audio:
        return "text_and_audio"
    if has_audio:
        return "audio_only"
    return "text_only"


LEGAL_AND_ACCURACY_NOTES = [
    "Reference is used for high-level production attributes only.",
    "Exact melody, sample, drum pattern, lyrics, or sound recording copying is not performed.",
    "Korean '따와라' requests require licensed or owned user-provided samples/stems; otherwise they become production-trait targets only.",
    "Voice identity cloning or impersonation is not performed; artist-style vocal prompts become production-trait targets only.",
    "Text-only references are lower confidence unless reference audio is provided.",
]


def _priority(value: str | None) -> str:
    mapping = {
        "808/bass": "808_bass",
        "808": "808_bass",
        "bass": "808_bass",
        "reels impact": "reels_impact",
    }
    normalized = (value or "").strip().lower()
    return mapping.get(normalized, normalized.replace(" ", "_") or "melody")


def _confidence(parsed: dict[str, Any], audio_available: bool, reference_text: str | None) -> str:
    if audio_available:
        return "high"
    requests = parsed.get("reference_requests", [])
    if requests and all(item.get("confidence") == "low" for item in requests):
        return "low"
    if any(item.get("confidence") == "medium" for item in requests):
        return "medium"
    if reference_text and len(reference_text.split()) >= 4:
        return "medium"
    return "low"


def _reference_support(reference_text: str | None, reference_audio: str | None, web_research: dict[str, Any] | None) -> str:
    if reference_audio:
        return "audio-informed"
    if web_research and web_research.get("sources"):
        return "web-informed" if web_research.get("trait_inference_allowed") else "web-metadata-only"
    if reference_text:
        return "text-only"
    return "not provided"


def _parsed_intent(parsed: dict[str, Any], priority: str | None, avoid: list[str]) -> dict[str, Any]:
    requests = parsed.get("reference_requests", [])
    explicit = parsed.get("explicit_targets", {})
    targets = {item.get("target_element", "whole_song") for item in requests}
    synth_width = explicit.get("synth_width", {})
    if synth_width.get("stereo_width", 2) > 2 or synth_width.get("pan_motion") not in {None, "none"}:
        targets.add("synth_width")
    if explicit.get("melody", {}).get("preserve"):
        targets.add("melody")
    if explicit.get("arrangement", {}).get("hook_early"):
        targets.add("arrangement")
    return {
        "target_elements": sorted(targets) or ["whole_song"],
        "reference_titles": sorted({item.get("reference_title", "unknown title") for item in requests}),
        "priority": _priority(priority),
        "avoid": avoid,
        "reference_requests": requests,
        "language": parsed.get("language", "unknown"),
        "raw_text": parsed.get("raw_text", ""),
        "explicit_targets": parsed.get("explicit_targets", {}),
        "processing_targets": parsed.get("explicit_targets", {}).get("processing", {}),
        "actions": parsed.get("actions", []),
        "copying_risk": parsed.get("copying_risk", "none"),
        "production_traits": parsed.get("production_traits", {}),
        "safety_note": parsed.get("safety_note", ""),
    }


def _provided_files(brief: dict[str, Any], reference_audio: str | None) -> dict[str, Any]:
    files = dict(brief.get("input_files", {}) or {})
    if reference_audio:
        files.setdefault("reference_audio", reference_audio)
    if brief.get("provided_files"):
        files["provided_files"] = brief.get("provided_files")
    return files


def _ownership_flags(brief: dict[str, Any]) -> dict[str, Any]:
    flags = dict(brief.get("ownership_flags", {}) or {})
    for key in (
        "user_owned_sample",
        "user_owned_stem",
        "owned",
        "licensed",
        "cleared",
        "user_confirms_owned_or_licensed",
        "sample_cleared",
        "stem_cleared",
    ):
        if key in brief:
            flags[key] = brief.get(key)
    return flags


def _drum_targets(style: dict[str, Any], explicit: dict[str, Any]) -> dict[str, Any]:
    drums = explicit.get("drums", {})
    hats = "rolled" if style["hat_density"] >= 4 else "medium"
    if drums.get("density", 3) >= 5:
        hats = "busy"
    return {
        "kick": "short_punchy" if style["energy"] >= 4 else "soft",
        "snare_or_clap": "digital" if "digicore" in style["genre_family"] else "tight",
        "hats": hats,
        "percussion": "glitchy" if style["glitch_amount"] >= 4 else "minimal",
        "swing": drums.get("swing") if drums.get("swing") != "unknown" else "light" if style["drum_density"] >= 4 else "straight",
        "fills": "controlled" if style["arrangement_variation"] >= 4 else "rare",
        "manual_logic_notes": [
            "Use drum targets as broad feel references only; do not copy exact reference drum patterns.",
            "For '따와라' kick requests, use only licensed/owned user-provided samples; otherwise translate to punch, transient sharpness, and layer choice.",
            "Keep fills intentional and avoid random AI glitch transitions.",
            "Balance drum aggression against melody/vocal clarity.",
        ],
    }


def _bass_targets(style: dict[str, Any], explicit: dict[str, Any]) -> dict[str, Any]:
    bass = explicit.get("bass_808", {})
    distortion = style["808_distortion"]
    return {
        "tone": bass.get("tone") if bass.get("tone") != "unknown" else "clean" if distortion <= 2 else "saturated" if distortion == 3 else "distorted",
        "sub_weight": bass.get("sub_weight", style["low_end_weight"]),
        "distortion": bass.get("distortion", distortion),
        "glide": bass.get("glide", 1),
        "movement": bass.get("movement") if bass.get("movement") != "unknown" else "melodic" if "digicore" in style["genre_family"] else "simple",
        "rhythmic_density": bass.get("rhythmic_density", 3),
        "priority": bass.get("priority") if bass.get("priority") != "unknown" else "balanced" if style["low_end_weight"] >= 4 else "support_melody",
        "manual_logic_notes": [
            "Shape bass/808 around reference-inspired tone only; do not recreate exact reference sound design.",
            "For '따와라' bass requests, do not copy a protected bassline or exact bass recording without a licensed/owned source.",
            "Keep sub controlled and check small-speaker translation.",
            "Use slides/glides only when requested or musically supportive.",
        ],
    }


def _vocal_targets(style: dict[str, Any], explicit: dict[str, Any]) -> dict[str, str]:
    vocal = explicit.get("vocal", {})
    forwardness = vocal.get("forwardness", style["vocal_forwardness"])
    return {
        "lead_position": "front" if forwardness >= 4 else "natural",
        "tuning": vocal.get("tuning") if vocal.get("tuning") != "unknown" else "medium" if "hyperpop" in style["genre_family"] else "subtle",
        "texture": "bright" if vocal.get("brightness", style["brightness"]) >= 5 else "airy" if style["brightness"] >= 4 else "clean",
        "adlib_width": "wide" if style["reverb_wetness"] >= 4 else "medium",
    }


def _arrangement_targets(style: dict[str, Any], explicit: dict[str, Any]) -> dict[str, Any]:
    arrangement = explicit.get("arrangement", {})
    hook_seconds = arrangement.get("target_hook_seconds")
    return {
        "hook_entrance_seconds": hook_seconds if hook_seconds is not None else 12 if style["energy"] >= 4 else 24,
        "intro_length": "short" if style["energy"] >= 4 else "medium",
        "drop_style": "instant" if style["energy"] >= 4 else "filtered",
        "variation_frequency_bars": arrangement.get("variation_frequency_bars") or (4 if style["arrangement_variation"] >= 4 else 8),
    }


def build_reference_target_profile(
    reference_text: str | None,
    reference_audio: str | None,
    creative_brief: dict[str, Any] | None = None,
    web_research: dict[str, Any] | None = None,
) -> dict[str, Any]:
    brief = creative_brief or {}
    brief_length = brief.get("length", {})
    reference_text = reference_text or brief.get("creative_target")
    reference_audio = reference_audio or brief.get("input_files", {}).get("reference_audio")
    parsed = parse_reference_intent(
        reference_text,
        avoid_text=", ".join(brief.get("avoid", [])) if isinstance(brief.get("avoid"), list) else brief.get("avoid_text"),
        priority=brief.get("priority") or brief.get("most_important"),
        drum_direction=brief.get("drum_808_direction") or brief.get("drum_808"),
        vocal_direction=brief.get("vocal_direction"),
        master_direction=brief.get("master_direction"),
        reference_audio_available=bool(reference_audio),
    )
    style = parsed["style_targets"]
    audio_path = Path(reference_audio).expanduser() if reference_audio else None
    audio = analyze_reference_audio(audio_path)
    if audio.get("available"):
        style["drum_density"] = max(style["drum_density"], _scale(float(audio["onset_density"]), (0.01, 0.03, 0.06, 0.1)))
        style["hat_density"] = max(style["hat_density"], style["drum_density"])
        style["brightness"] = max(style["brightness"], _scale(float(audio["spectral_brightness_heuristic"]), (0.005, 0.015, 0.03, 0.06)))
        style["low_end_weight"] = max(style["low_end_weight"], _scale(float(audio["low_end_weight_heuristic"]), (0.5, 0.8, 1.2, 1.6)))
        style["arrangement_variation"] = max(style["arrangement_variation"], _scale(float(audio["dynamic_range_heuristic"]), (0.001, 0.005, 0.015, 0.03)))
        style["notes"].append("Reference audio translated into broad target ranges only; no exact rhythm or melody copied.")
    elif reference_text:
        style["notes"].append("Text-only reference request treated as low-confidence high-level production direction; no exact bass, melody, or mix inferred.")
        style["notes"].append("Provide reference audio or a clearer artist/title for accurate sonic trait matching.")
    avoid = parsed["avoid"]
    explicit = parsed.get("explicit_targets", {})
    traits = extract_reference_traits(
        user_phrase=reference_text,
        parsed_intent=parsed,
        web_research=web_research,
        audio_analysis=audio,
    )
    confidence = traits.get("confidence") or _confidence(parsed, bool(audio.get("available")), reference_text)
    priority = brief.get("priority") or brief.get("most_important")
    copying_policy = evaluate_copying_request(parsed, _provided_files(brief, reference_audio), _ownership_flags(brief))
    autopilot = parsed.get("commercial_digicore_autopilot") or build_commercial_digicore_autopilot(reference_text, parsed)
    if autopilot.get("active"):
        traits["commercial_digicore_autopilot"] = autopilot
        for item in autopilot.get("avoid", []):
            if item not in avoid:
                avoid.append(item)
    traits.setdefault("safety", {})
    traits["safety"].update(
        {
            "exact_copy_allowed": bool(copying_policy.get("exact_copy_allowed")),
            "copying_risk": parsed.get("copying_risk", traits["safety"].get("copying_risk", "none")),
            "requires_user_owned_source_for_sampling": bool(copying_policy.get("requires_user_owned_source") or traits["safety"].get("requires_user_owned_source_for_sampling")),
            "confidence": confidence,
            "evidence_mode": "owned_sample"
            if copying_policy.get("exact_copy_allowed")
            else "audio_informed"
            if audio.get("available")
            else "web_informed"
            if (web_research or {}).get("trait_inference_allowed")
            else "text_only",
        }
    )
    return {
        "source": {
            "reference_text": reference_text or "",
            "reference_audio_path": reference_audio or "",
            "mode": _source_mode(reference_text, reference_audio),
            "confidence": confidence,
            "support": _reference_support(reference_text, reference_audio, web_research),
            "web_combined_confidence": (web_research or {}).get("combined_confidence", "low"),
            "web_trait_inference_allowed": bool((web_research or {}).get("trait_inference_allowed", False)),
            "creative_brief_used": bool(creative_brief),
            "reference_confidence": confidence,
            "length_mode": brief_length.get("mode", ""),
            "specific_section_start": brief_length.get("start"),
            "specific_section_end": brief_length.get("end"),
        },
        "style_targets": {key: style[key] for key in (
            "genre_family",
            "energy",
            "brightness",
            "low_end_weight",
            "drum_density",
            "hat_density",
            "808_distortion",
            "glitch_amount",
            "vocal_forwardness",
            "reverb_wetness",
            "arrangement_variation",
        )},
        "bass_808_targets": _bass_targets(style, explicit),
        "drum_targets": _drum_targets(style, explicit),
        "vocal_targets": _vocal_targets(style, explicit),
        "arrangement_targets": _arrangement_targets(style, explicit),
        "reference_traits": traits,
        "copying_policy": copying_policy,
        "avoid": avoid,
        "parsed_intent": _parsed_intent(parsed, priority, avoid),
        "legal_and_accuracy_notes": LEGAL_AND_ACCURACY_NOTES,
        "web_reference_research": web_research or {},
        "notes": style["notes"] + audio.get("safety_note", "").splitlines(),
        "audio_analysis": audio,
        "commercial_digicore_autopilot": autopilot,
    }


def write_reference_profile(profile: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(profile, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

from __future__ import annotations

import re
from typing import Any

from commercial_digicore_autopilot import build_commercial_digicore_autopilot

SAFETY_NOTE = "Reference is used for high-level production attributes only, not exact copying."
VOICE_IDENTITY_SAFETY_NOTE = (
    "Vocal artist references are translated to production traits only; voice identity cloning is not performed."
)
SAFE_SAMPLE_USE_NOTE = (
    "If the user provides a licensed or owned sample/stem it may be used; otherwise this is translated "
    "to high-level production traits only."
)


def clamp(value: int, low: int = 1, high: int = 5) -> int:
    return max(low, min(high, value))


def empty_profile(reference_text: str | None = None) -> dict[str, Any]:
    return {
        "genre_family": [],
        "energy": 3,
        "brightness": 3,
        "low_end_weight": 3,
        "drum_density": 3,
        "hat_density": 3,
        "808_distortion": 2,
        "glitch_amount": 2,
        "vocal_forwardness": 3,
        "reverb_wetness": 2,
        "arrangement_variation": 3,
        "emotional_descriptors": [],
        "notes": [f"Parsed from reference text: {reference_text}"] if reference_text else [],
    }


def _has(text: str, *words: str) -> bool:
    return any(word in text for word in words)


def _compact(text: str) -> str:
    return re.sub(r"[\s._/-]+", "", text.lower())


def detect_language(text: str) -> str:
    has_ko = bool(re.search(r"[가-힣ㅇ]", text))
    has_en = bool(re.search(r"[A-Za-z]", text))
    if has_ko and has_en:
        return "mixed"
    if has_ko:
        return "ko"
    if has_en:
        return "en"
    return "unknown"


def empty_explicit_targets() -> dict[str, Any]:
    return {
        "bass_808": {
            "tone": "unknown",
            "movement": "unknown",
            "priority": "unknown",
            "distortion": 2,
            "sub_weight": 3,
            "glide": 1,
            "rhythmic_density": 3,
        },
        "drums": {
            "density": 3,
            "transient_sharpness": 3,
            "swing": "unknown",
            "fill_amount": 3,
            "avoid_random_glitch": False,
        },
        "vocal": {
            "forwardness": 3,
            "tuning": "unknown",
            "brightness": 3,
            "identity_preserve": False,
            "saturation": 2,
        },
        "processing": {
            "autotune": "unknown",
            "saturation_style": "unknown",
            "plugin_style_reference": None,
        },
        "synth_width": {
            "pan_motion": "none",
            "stereo_width": 2,
            "mid_side_approach": "unknown",
            "mono_compatibility_required": True,
            "low_frequency_mono_cutoff_hz": 120,
        },
        "arrangement": {
            "hook_early": False,
            "target_hook_seconds": None,
            "variation_frequency_bars": None,
        },
        "melody": {
            "preserve": False,
            "avoid_covering": True,
        },
    }


def _confidence(reference_title: str | None, text: str, reference_audio_available: bool) -> str:
    if reference_audio_available and reference_title:
        return "high"
    cleaned_title = (reference_title or "").strip()
    placeholder_title = bool(re.fullmatch(r"[ㅇoO0]{2,}", cleaned_title))
    if not reference_title or placeholder_title or reference_title in {"ㅇㅇㅇ", "OOO", "unknown title", "this song"}:
        return "low"
    if len(text.split()) >= 3 or re.search(r"[가-힣]", text):
        return "medium"
    return "low"


def _request(
    *,
    reference_title: str | None,
    target_element: str,
    action: str,
    confidence: str,
    requires_reference_audio_for_accuracy: bool,
) -> dict[str, Any]:
    return {
        "reference_title": reference_title or "unknown title",
        "target_element": target_element,
        "action": action,
        "confidence": confidence,
        "requires_reference_audio_for_accuracy": requires_reference_audio_for_accuracy,
        "safety_note": SAFETY_NOTE,
    }


def _safe_take_request(
    *,
    reference_title: str | None,
    target_element: str,
    confidence: str,
    requires_reference_audio_for_accuracy: bool,
) -> dict[str, Any]:
    request = _request(
        reference_title=reference_title,
        target_element=target_element,
        action="reference_inspired_trait_match",
        confidence=confidence,
        requires_reference_audio_for_accuracy=requires_reference_audio_for_accuracy,
    )
    request["sample_use_policy"] = "licensed_or_owned_source_required"
    request["sample_use_safety_note"] = SAFE_SAMPLE_USE_NOTE
    return request


def _vocal_style_request(
    *,
    reference_title: str,
    confidence: str,
    requires_reference_audio_for_accuracy: bool,
) -> dict[str, Any]:
    request = _request(
        reference_title=reference_title,
        target_element="vocal",
        action="match_vocal_production_traits",
        confidence=confidence,
        requires_reference_audio_for_accuracy=requires_reference_audio_for_accuracy,
    )
    request["identity_clone_allowed"] = False
    request["identity_safety_note"] = VOICE_IDENTITY_SAFETY_NOTE
    return request


def _clean_title(value: str) -> str:
    cleaned = re.sub(r"\s+", " ", value).strip(" .,;:!?'\"")
    cleaned = re.split(r"[,;]|\n", cleaned)[-1].strip(" .,;:!?'\"")
    cleaned = re.sub(r"^(?:보컬|목소리|드럼|킥|베이스|808)(?:은|는|을|를)?\s*", "", cleaned).strip()
    cleaned = re.sub(r"^(?:좀\s*더|더)\s+", "", cleaned).strip()
    return cleaned


def _infer_take_title(text: str) -> str | None:
    match = re.search(r"(.+?)\s*(?:베이스|808|킥|kick|드럼|snare|스네어).{0,20}따와", text, re.IGNORECASE)
    if not match:
        return None
    return _clean_title(match.group(1).replace("랑", " ").replace("하고", " "))


def _style_reference_titles(text: str) -> list[str]:
    titles: list[str] = []
    for match in re.finditer(r"([A-Za-z0-9][A-Za-z0-9 ._/-]*?)\s*(?:처럼|같이|느낌|스타일)", text, re.IGNORECASE):
        title = _clean_title(match.group(1))
        if title and title.lower() not in {"my voice", "voice", "vocal"}:
            titles.append(title)
    lowered = text.lower()
    for known in ("2hollis", "ycs", "system seoul", "slayr", "jane remover"):
        if known in lowered and all(item.lower() != known for item in titles):
            titles.append("SYSTEM SEOUL" if known == "system seoul" else "Jane Remover" if known == "jane remover" else known)
    return list(dict.fromkeys(titles))


def _has_westwood_jtd(text: str, compacted: str) -> bool:
    lowered = text.lower()
    return bool(
        ("westwood" in lowered and ("just touched down" in lowered or "just touchdown" in lowered))
        or ("웨스트우드" in compacted and ("저스트터치다운" in compacted or "justtoucheddown" in compacted))
        or ("웨스트우드" in compacted and "곡" in compacted)
        or "저스트터치다운" in compacted
        or "justtouchdown" in compacted
        or "justtoucheddown" in compacted
    )


def _has_scene_style(text: str, compacted: str) -> bool:
    lowered = text.lower()
    return any(
        token in lowered
        for token in ("2hollis", "ycs", "system seoul", "ss-pop", "ss pop", "hyperpop", "slayr", "jane remover", "internet underground")
    ) or any(
        token in compacted
        for token in (
            "투홀리스",
            "2홀리스",
            "와이씨에스",
            "시스템서울",
            "국내디지코어",
            "인터넷감성",
            "2000년대온라인",
            "게임사운드트랙",
            "하이퍼팝",
            "덜싸게",
            "슬레이어",
            "제인리무버",
            "인터넷언더",
        )
    )


def _copying_words(normalized: str) -> bool:
    return _has(normalized, "따와", "가져와", "똑같이", "그대로", "same exact", "copy")


def _target_elements_for_output(text: str, normalized: str, explicit: dict[str, Any], requests: list[dict[str, Any]]) -> list[str]:
    compacted = _compact(text)
    elements: set[str] = set()
    for request in requests:
        element = request.get("target_element")
        if element in {"bass", "808"}:
            elements.add("bass_808")
        elif element == "drums":
            elements.update({"drums", "kick"})
        elif element == "whole_song":
            elements.add("whole_style")
        elif element:
            elements.add(str(element))
    if _has_westwood_jtd(text, compacted):
        elements.update({"kick", "bass_808"})
    if _has(normalized, "킥", "kick"):
        elements.add("kick")
    if _has(normalized, "베이스", "808", "bass", "서브", "sub"):
        elements.add("bass_808")
    if _has(normalized, "드럼", "drum", "하이햇", "hat"):
        elements.add("drums")
    if _has(normalized, "보컬", "목소리", "오토튠", "autotune", "하드튠", "디카페이터", "데카피테이터", "decapitator", "saturation", "밝게", "세게", "nate sib") or _has_scene_style(text, compacted):
        elements.add("vocal")
    if explicit.get("synth_width", {}).get("stereo_width", 2) > 2 or _has(normalized, "신스", "신디", "공간감", "와이드", "스테레오", "패닝", "panning", "하모닉"):
        elements.add("synth_width")
    if explicit.get("arrangement", {}).get("hook_early") or _has(normalized, "릴스", "훅", "hook"):
        elements.add("arrangement")
    if explicit.get("melody", {}).get("preserve") or _has(normalized, "멜로디"):
        elements.add("melody")
    scene_vocal_context = _has(normalized, "보컬", "목소리", "voice", "vocal")
    identity_preserve_context = _has(normalized, "내 목소리", "목소리 유지", "내껄", "복제 말고", "my voice")
    if _has_scene_style(text, compacted) and not (scene_vocal_context and identity_preserve_context):
        elements.update({"whole_style", "drums", "bass_808", "synth_width", "vocal", "arrangement"})
    if elements == {"synth_width"}:
        elements.add("bass_808")
    return sorted(elements) or ["whole_style"]


def _vocal_intensity(normalized: str, compacted: str) -> str:
    if _has(normalized, "하드튠", "hard tune", "hardtune", "autotune 더 세게", "오토튠 더 세게", "빡세게") or "하드튠" in compacted:
        return "hard_effect"
    if _has(normalized, "살짝", "따뜻하게", "찢어지게 말고"):
        return "subtle"
    if _has(normalized, "오토튠", "autotune", "auto-tune", "디카페이터", "데카피테이터", "decapitator", "saturation"):
        return "medium"
    return "subtle"


def _build_production_traits(
    *,
    text: str,
    normalized: str,
    explicit: dict[str, Any],
    requests: list[dict[str, Any]],
    target_elements: list[str],
) -> dict[str, Any]:
    compacted = _compact(text)
    copying = _copying_words(normalized)
    scene_style = _has_scene_style(text, compacted)
    westwood = _has_westwood_jtd(text, compacted)
    processing = explicit.get("processing", {})
    vocal = explicit.get("vocal", {})
    drums = explicit.get("drums", {})
    bass = explicit.get("bass_808", {})
    synth = explicit.get("synth_width", {})

    traits: dict[str, Any] = {
        "user_requested_copying": copying,
        "reference_artist": "Westwood" if westwood else None,
        "reference_title": "JUST TOUCHED DOWN" if westwood else None,
        "kick_punch": "strong" if "kick" in target_elements else "not_requested",
        "kick_transient_sharpness": max(int(drums.get("transient_sharpness", 3)), 4 if "kick" in target_elements else 3),
        "kick_low_end_weight": max(int(bass.get("sub_weight", 3)), 4 if "kick" in target_elements else 3),
        "bass_sub_weight": max(int(bass.get("sub_weight", 3)), 4 if "bass_808" in target_elements else 3),
        "bass_tone": bass.get("tone") if bass.get("tone") != "unknown" else "saturated" if westwood else "clean",
        "bass_distortion_saturation": max(int(bass.get("distortion", 2)), 3 if westwood else 2),
        "glide_amount": bass.get("glide", 1),
        "bass_rhythmic_density": bass.get("rhythmic_density", 3),
        "melody_masking_risk": "medium" if "bass_808" in target_elements else "low",
        "sidechain_or_automation_recommendation": "duck bass/kick under melody or vocal when masking appears",
        "pitch_correction_intensity": _vocal_intensity(normalized, compacted),
        "retune_speed_target": "fast" if _vocal_intensity(normalized, compacted) == "hard_effect" else "medium" if _vocal_intensity(normalized, compacted) == "medium" else "slow/subtle",
        "formant_preservation_note": "preserve the user's formant and vocal identity; do not clone another singer",
        "vocal_saturation_amount": "strong" if _has(normalized, "빡세게") else "subtle" if _has(normalized, "살짝", "따뜻하게", "찢어지게 말고") else "medium" if _has(normalized, "디카페이터", "데카피테이터", "decapitator", "saturation") else "subtle",
        "parallel_mix_amount": "low" if _has(normalized, "살짝", "따뜻하게") else "medium",
        "deessing_after_saturation": True,
        "compression_amount": "strong" if int(vocal.get("forwardness", 3)) >= 5 else "medium",
        "brightness_harshness_balance": "bright but de-essed; avoid harsh tearing",
        "logic_plugin_detection_manual_checklist": "Check whether Decapitator is installed in Logic; if not, use generic saturation and mark it as approximation.",
        "saturation_plugin_request": "Decapitator" if _has(normalized, "디카페이터", "데카피테이터", "decapitator") else "generic saturation" if _has(normalized, "saturation", "새츄레이션") else None,
        "plugin_exact_application_allowed": False,
        "fallback_plugin_note": "fallback approximation only; do not claim Decapitator applied unless the plugin was detected and actually used",
        "preserve_user_voice_identity": True if "vocal" in target_elements or _has(normalized, "내 목소리", "목소리", "보컬") else False,
        "identity_clone_allowed": False,
        "lead_vocal_position": "very_front" if int(vocal.get("forwardness", 3)) >= 5 else "front" if "vocal" in target_elements else "natural",
        "brightness": "controlled_high" if _has(normalized, "밝게", "밝고") else "high" if scene_style else "medium",
        "compression": "strong" if _has(normalized, "세게", "앞으로") else "medium",
        "saturation": "medium" if _has(normalized, "디카페이터", "데카피테이터", "decapitator", "saturation", "세게") else "subtle",
        "autotune": processing.get("autotune") if processing.get("autotune") != "unknown" else _vocal_intensity(normalized, compacted),
        "sub_mono_required": True,
        "mono_sub_cutoff_hz": synth.get("low_frequency_mono_cutoff_hz", 120),
        "wide_upper_harmonics_allowed": True,
        "avoid_panning_sub": True,
        "mono_compatibility_check_required": True,
        "high_pass_widened_duplicate_hz": "120-180",
        "keep_kick_sub_808_fundamental_center": True,
        "widen_synth_layers_pads_upper_harmonics_only": True,
        "conservative_mid_side_eq_allowed": True,
        "pan_automation_allowed_for_high_passed_layer": True,
        "stereo_only_limitation_warning": "stereo-only source has limited control; stem-level panning requires stems or manual Logic layers",
        "style_direction": "energetic_internet_digicore_hyperpop_direction" if scene_style else "reference_inspired_modern_hiphop",
        "bright_digital_synth_layers": scene_style,
        "strong_but_controlled_808": scene_style or "bass_808" in target_elements,
        "sharp_but_not_harsh_drums": scene_style or "drums" in target_elements or "kick" in target_elements,
        "active_hats_if_appropriate": scene_style,
        "hook_forward_arrangement": scene_style or "arrangement" in target_elements,
        "vocal_forward_if_vocal_mode": scene_style or "vocal" in target_elements,
        "controlled_pitch_correction": scene_style or "vocal" in target_elements,
        "artist_identity_clone_allowed": False,
        "exact_copy_allowed": False,
    }
    if not traits["preserve_user_voice_identity"] and _has(normalized, "밝게", "세게", "nate sib", "투홀리스", "2hollis"):
        traits["preserve_user_voice_identity"] = True
    return traits


def _actions_for_output(text: str, normalized: str, target_elements: list[str], requests: list[dict[str, Any]]) -> list[str]:
    compacted = _compact(text)
    actions = {str(item.get("action")) for item in requests if item.get("action")}
    if _has_westwood_jtd(text, compacted) or target_elements and {"kick", "bass_808"} <= set(target_elements):
        actions.add("reference_inspired_trait_match")
    if "vocal" in target_elements and _has(normalized, "오토튠", "autotune", "하드튠", "디카페이터", "데카피테이터", "decapitator", "saturation"):
        actions.add("vocal_processing")
    scene_vocal_context = _has(normalized, "보컬", "목소리", "voice", "vocal")
    identity_preserve_context = _has(normalized, "내 목소리", "목소리 유지", "내껄", "복제 말고", "my voice")
    if _has_scene_style(text, compacted) and not (scene_vocal_context and identity_preserve_context):
        actions.add("style_translation")
    if "synth_width" in target_elements:
        actions.add("stereo_width_planning")
    if "arrangement" in target_elements:
        actions.add("arrangement_hook_planning")
    if "vocal" in target_elements and not actions:
        actions.add("vocal_processing")
    return sorted(actions) or ["style_translation"]


def _copying_risk(normalized: str, requests: list[dict[str, Any]]) -> str:
    if _copying_words(normalized):
        return "high"
    if requests:
        return "medium"
    return "low" if _has(normalized, "처럼", "느낌", "스타일") else "none"


def _overall_confidence(reference_audio_available: bool, requests: list[dict[str, Any]]) -> str:
    if reference_audio_available:
        return "high"
    if requests and any(item.get("confidence") == "medium" for item in requests):
        return "low"
    return "low"


def _extract_reference_requests(text: str, normalized: str, reference_audio_available: bool) -> list[dict[str, Any]]:
    requests: list[dict[str, Any]] = []
    compacted = _compact(text)

    if "따와" in normalized:
        title = _infer_take_title(text)
        confidence = _confidence(title, text, reference_audio_available)
        if _has(normalized, "베이스", "808", "bass"):
            requests.append(
                _safe_take_request(
                    reference_title=title,
                    target_element="bass",
                    confidence=confidence,
                    requires_reference_audio_for_accuracy=not reference_audio_available,
                )
            )
        if _has(normalized, "킥", "kick", "드럼"):
            requests.append(
                _safe_take_request(
                    reference_title=title,
                    target_element="drums",
                    confidence=confidence,
                    requires_reference_audio_for_accuracy=not reference_audio_available,
                )
            )

    if _has_westwood_jtd(text, compacted):
        confidence = "high" if reference_audio_available else "low"
        if _has(normalized, "베이스", "808", "bass") or "베이스" in compacted:
            requests.append(
                _safe_take_request(
                    reference_title="JUST TOUCHED DOWN",
                    target_element="bass",
                    confidence=confidence,
                    requires_reference_audio_for_accuracy=not reference_audio_available,
                )
            )
            requests[-1]["reference_artist"] = "Westwood"
        if _has(normalized, "킥", "kick") or "킥" in compacted:
            requests.append(
                _safe_take_request(
                    reference_title="JUST TOUCHED DOWN",
                    target_element="drums",
                    confidence=confidence,
                    requires_reference_audio_for_accuracy=not reference_audio_available,
                )
            )
            requests[-1]["reference_artist"] = "Westwood"

    korean_vocal_style_match = re.search(
        r"(?:내\s*)?(?:목소리|보컬)(?:를|을|은|이|는)?\s*([A-Za-z][A-Za-z0-9 ._-]*?)(?:처럼|같이|느낌|스타일)",
        text,
        re.IGNORECASE,
    )
    if korean_vocal_style_match:
        title = _clean_title(korean_vocal_style_match.group(1))
        requests.append(
            _vocal_style_request(
                reference_title=title,
                confidence=_confidence(title, text, reference_audio_available),
                requires_reference_audio_for_accuracy=not reference_audio_available,
            )
        )

    english_vocal_style_match = re.search(
        r"(?:make\s+)?(?:my\s+)?(?:voice|vocals?)\s+(?:like|as|in the style of)\s+([A-Za-z][A-Za-z0-9 ._-]*?)(?:$|[,.!?;]|처럼|같이)",
        text,
        re.IGNORECASE,
    )
    if english_vocal_style_match:
        title = _clean_title(english_vocal_style_match.group(1))
        requests.append(
            _vocal_style_request(
                reference_title=title,
                confidence=_confidence(title, text, reference_audio_available),
                requires_reference_audio_for_accuracy=not reference_audio_available,
            )
        )

    korean_vocal_group_match = re.search(
        r"(?:보컬|목소리)(?:은|을|를|이|는)?\s*([A-Za-z0-9][A-Za-z0-9 ._/-]*?)\s*(?:쪽\s*)?(?:느낌|스타일)",
        text,
        re.IGNORECASE,
    )
    if korean_vocal_group_match:
        title = _clean_title(korean_vocal_group_match.group(1))
        if title:
            requests.append(
                _vocal_style_request(
                    reference_title=title,
                    confidence=_confidence(title, text, reference_audio_available),
                    requires_reference_audio_for_accuracy=not reference_audio_available,
                )
            )

    feeling_match = re.search(r"([A-Za-z0-9가-힣ㅇ ._/-]+?)\s*(?:느낌|스타일)\s*(드럼|베이스|808|보컬|목소리|신스|신디)?", text, re.IGNORECASE)
    if feeling_match:
        title = _clean_title(feeling_match.group(1))
        if title.lower() == "love blur":
            title = "Love Blur"
        element_word = feeling_match.group(2) or "whole_song"
        element = (
            "drums"
            if element_word == "드럼"
            else "bass"
            if element_word in {"베이스", "808"}
            else "vocal"
            if element_word in {"보컬", "목소리"}
            else "synth_width"
            if element_word in {"신스", "신디"}
            else "whole_song"
        )
        if title and not title.startswith(("내 목소리", "보컬은", "목소리")) and "쪽" not in title and "이라는 곡" not in title and "라는 곡" not in title:
            requests.append(
                _request(
                    reference_title=title,
                    target_element=element,
                    action="make_like_reference",
                    confidence=_confidence(title, text, reference_audio_available),
                    requires_reference_audio_for_accuracy=not reference_audio_available,
                )
            )

    title_element_like_match = re.search(r"([A-Za-z0-9가-힣ㅇ ._/-]+?)\s*(베이스|808|드럼|보컬|목소리|신스|신디)(?:처럼|같이)", text, re.IGNORECASE)
    if title_element_like_match:
        title = _clean_title(title_element_like_match.group(1))
        title = title.replace("이라는 곡", "").replace("라는 곡", "").strip()
        if title.lower() == "love blur":
            title = "Love Blur"
        element_word = title_element_like_match.group(2)
        element = "bass" if element_word in {"베이스", "808"} else "drums" if element_word == "드럼" else "vocal" if element_word in {"보컬", "목소리"} else "synth_width"
        if title:
            requests.append(
                _request(
                    reference_title=title,
                    target_element=element,
                    action="make_like_reference",
                    confidence=_confidence(title, text, reference_audio_available),
                    requires_reference_audio_for_accuracy=not reference_audio_available,
                )
            )

    title_match = re.search(r"(.+?)(?:이라는|라는)\s*곡\s*(베이스|808|드럼|보컬|멜로디)?(?:처럼|같이)?", text)
    if title_match:
        title = title_match.group(1).strip()
        element_word = title_match.group(2) or "whole_song"
        element = "bass" if element_word in {"베이스", "808"} else "drums" if element_word == "드럼" else "vocal" if element_word == "보컬" else "melody" if element_word == "멜로디" else "whole_song"
        requests.append(
            _request(
                reference_title=title,
                target_element=element,
                action="make_like_reference",
                confidence=_confidence(title, text, reference_audio_available),
                requires_reference_audio_for_accuracy=not reference_audio_available,
            )
        )

    english_title_match = re.search(r"\b([A-Za-z0-9 ._-]+?)\s+song\s+(bass|808|drums?|vocal|melody)(?:처럼| like)?", text, re.IGNORECASE)
    if english_title_match:
        title = english_title_match.group(1).strip()
        element_word = english_title_match.group(2).lower()
        element = "bass" if element_word in {"bass", "808"} else "drums" if element_word.startswith("drum") else element_word
        requests.append(
            _request(
                reference_title=title,
                target_element=element,
                action="make_like_reference",
                confidence=_confidence(title, text, reference_audio_available),
                requires_reference_audio_for_accuracy=not reference_audio_available,
            )
        )

    if _has(normalized, "love blur", "loveblur"):
        target = "drums" if _has(normalized, "drum", "드럼") else "whole_song"
        requests.append(
            _request(
                reference_title="Love Blur",
                target_element=target,
                action="make_like_reference",
                confidence="high" if reference_audio_available else "medium",
                requires_reference_audio_for_accuracy=not reference_audio_available,
            )
        )

    scene_vocal_context = _has(normalized, "보컬", "목소리", "voice", "vocal")
    identity_preserve_context = _has(normalized, "내 목소리", "목소리 유지", "내껄", "복제 말고", "my voice")
    if _has_scene_style(text, compacted) and not (scene_vocal_context and identity_preserve_context):
        for title in _style_reference_titles(text):
            requests.append(
                _request(
                    reference_title=title,
                    target_element="whole_song",
                    action="match_production_traits",
                    confidence=_confidence(title, text, reference_audio_available),
                    requires_reference_audio_for_accuracy=not reference_audio_available,
                )
            )
        if not any(item.get("reference_title", "").lower() == "2hollis" for item in requests) and _has(normalized, "투홀리스", "2홀리스"):
            requests.append(
                _request(
                    reference_title="2hollis",
                    target_element="whole_song",
                    action="match_production_traits",
                    confidence="low",
                    requires_reference_audio_for_accuracy=not reference_audio_available,
                )
            )
        if not any(item.get("reference_title", "").lower() == "ycs" for item in requests) and _has(normalized, "와이씨에스", "ycs"):
            requests.append(
                _request(
                    reference_title="ycs",
                    target_element="whole_song",
                    action="match_production_traits",
                    confidence="low",
                    requires_reference_audio_for_accuracy=not reference_audio_available,
                )
            )
        if not any(item.get("reference_title", "").lower() == "system seoul" for item in requests) and ("시스템서울" in compacted or _has(normalized, "system seoul")):
            requests.append(
                _request(
                    reference_title="SYSTEM SEOUL",
                    target_element="whole_song",
                    action="match_production_traits",
                    confidence="low",
                    requires_reference_audio_for_accuracy=not reference_audio_available,
                )
            )

    if _has(normalized, "이 곡처럼", "저 곡처럼", "그 곡처럼", "this song like", "this track like", "that song like"):
        target = "808" if "808" in normalized else "bass" if _has(normalized, "베이스", "bass", "서브", "sub") else "whole_song"
        requests.append(
            _request(
                reference_title="this song",
                target_element=target,
                action="make_like_reference",
                confidence="high" if reference_audio_available else "low",
                requires_reference_audio_for_accuracy=not reference_audio_available,
            )
        )

    if not requests and _has(normalized, "베이스처럼", "bass처럼", "bass like"):
        requests.append(
            _request(
                reference_title="unknown title",
                target_element="bass",
                action="make_like_reference",
                confidence="low",
                requires_reference_audio_for_accuracy=True,
            )
        )

    if _has(normalized, "랩 보컬 앞으로", "보컬 앞으로", "보컬은 랩 앞으로", "vocal upfront", "rap vocal upfront"):
        requests.append(
            _request(
                reference_title=None,
                target_element="vocal",
                action="make_more_forward",
                confidence="medium",
                requires_reference_audio_for_accuracy=False,
            )
        )

    if _has(normalized, "첫 15초", "15초", "15 sec", "15 seconds"):
        requests.append(
            _request(
                reference_title=None,
                target_element="arrangement",
                action="reels_hook_early",
                confidence="medium",
                requires_reference_audio_for_accuracy=False,
            )
        )

    unique: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    for item in requests:
        key = (item["reference_title"], item["target_element"], item["action"])
        if key not in seen:
            unique.append(item)
            seen.add(key)
    return unique


def parse_reference_intent(
    reference_text: str | None,
    avoid_text: str | None = None,
    priority: str | None = None,
    drum_direction: str | None = None,
    vocal_direction: str | None = None,
    master_direction: str | None = None,
    reference_audio_available: bool = False,
) -> dict[str, Any]:
    text = (reference_text or "").strip()
    lower = text.lower()
    normalized = re.sub(r"\s+", " ", lower)
    compacted = _compact(text)
    targets = empty_profile(text)
    explicit = empty_explicit_targets()
    reference_requests = _extract_reference_requests(text, normalized, reference_audio_available)
    avoid = ["generic trap loop", "random AI glitch", "cheap rage clipping", "vocal chop dominating melody"]

    if _has_westwood_jtd(text, compacted):
        targets["genre_family"].extend(["modern_hiphop", "underground_hiphop"])
        targets["energy"] = max(targets["energy"], 4)
        targets["low_end_weight"] = max(targets["low_end_weight"], 4)
        targets["drum_density"] = max(targets["drum_density"], 4)
        explicit["drums"].update({"density": 4, "transient_sharpness": 5, "fill_amount": 3, "avoid_random_glitch": True})
        explicit["bass_808"].update({"tone": "saturated", "sub_weight": 4, "distortion": 3, "priority": "support_melody"})
        targets["notes"].append("Westwood JUST TOUCHED DOWN request translated to kick punch and bass/808 production traits only.")

    if _has(normalized, "love blur", "loveblur"):
        targets["genre_family"].extend(["digicore", "underground_hiphop"])
        targets.update(
            {
                "energy": 4,
                "brightness": 4,
                "drum_density": 4,
                "hat_density": 4,
                "808_distortion": 3,
                "glitch_amount": 3,
                "arrangement_variation": 4,
            }
        )
        explicit["drums"].update({"density": 4, "transient_sharpness": 4, "swing": "light", "fill_amount": 3, "avoid_random_glitch": True})
        explicit["bass_808"].update({"priority": "support_melody", "sub_weight": 4, "distortion": 3})
        targets["notes"].append("Love Blur-style request interpreted as reference-inspired digital underground drum feel, not exact copying.")
    if _has(normalized, "hyperpop"):
        targets["genre_family"].append("hyperpop")
        targets["brightness"] = clamp(targets["brightness"] + 1)
        targets["energy"] = clamp(targets["energy"] + 1)
        targets["glitch_amount"] = clamp(targets["glitch_amount"] + 1)
    if _has(normalized, "digicore", "디지코어"):
        targets["genre_family"].append("digicore")
        targets["brightness"] = clamp(targets["brightness"] + 1)
        targets["arrangement_variation"] = clamp(targets["arrangement_variation"] + 1)
    if _has(normalized, "underground", "rap"):
        targets["genre_family"].append("underground_hiphop")
    if _has(normalized, "emotional", "sad", "melancholy", "감성"):
        targets["emotional_descriptors"].append("emotional")
        targets["reverb_wetness"] = clamp(targets["reverb_wetness"] + 1)
    if _has(normalized, "bright", "airy", "반짝"):
        targets["brightness"] = clamp(targets["brightness"] + 1)
    if _has(normalized, "clean"):
        targets["808_distortion"] = clamp(targets["808_distortion"] - 1)
        explicit["bass_808"]["tone"] = "clean"
    if _has(normalized, "hard 808", "strong 808", "808", "bass") or "베이스" in compacted:
        targets["low_end_weight"] = clamp(targets["low_end_weight"] + 1)
        explicit["bass_808"]["sub_weight"] = clamp(explicit["bass_808"]["sub_weight"] + 1)
    if _has(normalized, "더 세게", "stronger", "more 808"):
        targets["low_end_weight"] = clamp(targets["low_end_weight"] + 1)
        explicit["bass_808"]["sub_weight"] = clamp(explicit["bass_808"]["sub_weight"] + 1)
        explicit["bass_808"]["priority"] = "support_melody"
    if _copying_words(normalized):
        avoid.extend(["unlicensed sample use", "exact kick sample copying", "exact bassline copying"])
        targets["notes"].append(
            "Korean '따와라' request is interpreted safely: use licensed/owned user-provided samples or translate to kick punch, bass tone, transient sharpness, saturation, and arrangement energy."
        )
        if _has(normalized, "킥", "kick"):
            explicit["drums"].update({"density": 4, "transient_sharpness": 5, "fill_amount": 3, "avoid_random_glitch": True})
        if _has(normalized, "베이스", "808", "bass"):
            explicit["bass_808"].update({"tone": "saturated", "sub_weight": 4, "distortion": 3, "priority": "support_melody"})
    if _has(normalized, "멜로디는 살리고", "멜로디 덮지", "멜로디를 덮지", "melody preserve", "keep melody", "do not cover melody"):
        explicit["melody"]["preserve"] = True
        explicit["bass_808"]["priority"] = "support_melody"
        avoid.append("melody-covering 808")
        targets["notes"].append("Melody preservation request keeps 808/bass stronger but melody-supportive.")
    if _has(normalized, "멜로디", "melody", "중앙", "center"):
        explicit["melody"]["preserve"] = True
    if _has(normalized, "베이스처럼", "베이스", "bass like") or "베이스처럼" in compacted:
        targets["low_end_weight"] = clamp(targets["low_end_weight"] + 1)
        explicit["bass_808"].update({"tone": "clean" if explicit["bass_808"]["tone"] == "unknown" else explicit["bass_808"]["tone"], "movement": "melodic", "priority": "support_melody", "sub_weight": 4})
        avoid.extend(["muddy low-end", "overpowering melody"])
        targets["notes"].append("Korean bass reference request interpreted as a generic reference-inspired bass target unless reference audio is provided.")
    if _has(normalized, "808 글라이드", "808 glide", "글라이드"):
        explicit["bass_808"].update({"tone": "gliding", "movement": "melodic", "glide": 5})
        targets["low_end_weight"] = clamp(targets["low_end_weight"] + 1)
    if _has(normalized, "서브", "sub", "단단"):
        explicit["bass_808"]["sub_weight"] = max(explicit["bass_808"]["sub_weight"], 4)
        explicit["bass_808"]["priority"] = "support_melody"
        avoid.append("muddy sub")
    if _has(normalized, "신스", "신디", "synth", "좌우", "벌리", "패닝", "panning", "공간감", "wide", "넓", "와이드", "스테레오", "하모닉"):
        explicit["synth_width"].update(
            {
                "pan_motion": "medium" if _has(normalized, "패닝", "panning", "좌우", "벌리") else "subtle",
                "stereo_width": 4,
                "mid_side_approach": "keep_melody_center_widen_layers" if _has(normalized, "멜로디", "melody", "중앙", "center", "서브는 중앙") else "wide_pads_only",
            }
        )
        avoid.extend(["phase problems", "mono incompatibility", "wide sub bass"])
        targets["notes"].append("Synth width request keeps sub/fundamental low-end centered and widens only high-passed layers or upper harmonics.")
    if _has(normalized, "rage"):
        targets["energy"] = clamp(targets["energy"] + 1)
        targets["808_distortion"] = clamp(targets["808_distortion"] + 1)
        explicit["bass_808"]["distortion"] = clamp(explicit["bass_808"]["distortion"] + 1)
    if _has(normalized, "not too rage", "less rage", "너무 rage", "overclipped", "cheap rage clipping", "싸구려 rage clipping", "피하라"):
        targets["808_distortion"] = clamp(targets["808_distortion"] - 1)
        explicit["bass_808"]["distortion"] = clamp(explicit["bass_808"]["distortion"] - 1)
        avoid.append("overclipped rage distortion")
    if _has(normalized, "덜 난잡", "less busy", "less chaotic"):
        explicit["drums"]["density"] = clamp(explicit["drums"]["density"] - 1)
        explicit["drums"]["fill_amount"] = clamp(explicit["drums"]["fill_amount"] - 1)
        explicit["drums"]["avoid_random_glitch"] = True
        avoid.append("overly busy drums")
    if _has(normalized, "드럼은 강", "드럼 강", "드럼은 더 세게", "드럼 더 세게", "강하지만", "strong drums", "drums strong", "energetic drums"):
        targets["drum_density"] = max(targets["drum_density"], 4)
        targets["hat_density"] = max(targets["hat_density"], 4)
        explicit["drums"]["density"] = max(explicit["drums"]["density"], 4)
        explicit["drums"]["transient_sharpness"] = max(explicit["drums"]["transient_sharpness"], 4)
        explicit["drums"]["fill_amount"] = max(explicit["drums"]["fill_amount"], 3)
    if _has(normalized, "less generic", "not generic", "generic trap"):
        targets["arrangement_variation"] = clamp(targets["arrangement_variation"] + 1)
        avoid.append("predictable generic trap cadence")
    if _has(normalized, "vocal upfront", "vocal front", "보컬 앞으로", "보컬은 랩 앞으로", "목소리 앞으로", "앞으로 나오", "upfront"):
        targets["vocal_forwardness"] = 4
        explicit["vocal"]["forwardness"] = 5
    if _has(normalized, "랩 보컬", "rap vocal"):
        explicit["vocal"]["forwardness"] = 5
    if any(item.get("action") == "match_vocal_production_traits" for item in reference_requests):
        targets["vocal_forwardness"] = 4
        targets["brightness"] = clamp(targets["brightness"] + 1)
        targets["reverb_wetness"] = clamp(targets["reverb_wetness"] + 1)
        explicit["vocal"].update({"forwardness": 4, "tuning": "medium", "brightness": 4})
        avoid.append("voice identity cloning")
        targets["notes"].append(
            "Vocal artist-style request translated to production traits only: forwardness, tuning amount, "
            "brightness, compression/saturation feel, ambience, and adlib width; no voice identity cloning."
        )
    if _has(normalized, "내 목소리는 유지", "내 목소리 유지", "목소리는 유지", "목소리 복제 말고", "목소리는 내껄로", "own voice", "keep my voice"):
        explicit["vocal"]["identity_preserve"] = True
        avoid.append("voice identity replacement")
        targets["notes"].append("User voice identity must be preserved; changes are limited to production traits.")
    if _has(normalized, "오토튠", "autotune", "auto-tune", "tune", "하드튠"):
        explicit["vocal"]["tuning"] = _vocal_intensity(normalized, compacted)
        explicit["processing"]["autotune"] = _vocal_intensity(normalized, compacted)
        targets["vocal_forwardness"] = max(targets["vocal_forwardness"], 4)
    if _has(normalized, "디카페이터", "데카피테이터", "decapitator", "saturation"):
        explicit["vocal"]["saturation"] = 4
        explicit["processing"]["saturation_style"] = "decapitator_style_saturation"
        explicit["processing"]["plugin_style_reference"] = (
            "Decapitator-style saturation if available; otherwise generic saturation approximation only"
            if _has(normalized, "디카페이터", "데카피테이터", "decapitator")
            else "generic saturation approximation only"
        )
        avoid.append("harsh vocal distortion")
    if _has(normalized, "찢어지게 말고", "따뜻하게"):
        explicit["vocal"]["saturation"] = 2
        explicit["processing"]["saturation_style"] = "warm_saturation"
        avoid.append("torn harsh vocal distortion")
    if _has(normalized, "밝고", "밝게", "bright", "세게", "stronger vocal", "보컬 앞으로", "랩 보컬 앞으로"):
        targets["brightness"] = clamp(targets["brightness"] + 1)
        explicit["vocal"]["brightness"] = max(explicit["vocal"]["brightness"], 4)
        explicit["vocal"]["forwardness"] = max(explicit["vocal"]["forwardness"], 4)
    if _has_scene_style(text, compacted):
        targets["genre_family"].extend(["digicore", "hyperpop", "underground_hiphop"])
        targets["energy"] = max(targets["energy"], 4)
        targets["brightness"] = max(targets["brightness"], 4)
        targets["glitch_amount"] = max(targets["glitch_amount"], 3)
        targets["drum_density"] = max(targets["drum_density"], 4)
        targets["hat_density"] = max(targets["hat_density"], 4)
        targets["arrangement_variation"] = max(targets["arrangement_variation"], 4)
        explicit["drums"].update({"density": 4, "transient_sharpness": 4, "swing": "light", "fill_amount": 3, "avoid_random_glitch": True})
        explicit["bass_808"].update({"priority": "support_melody", "sub_weight": 4, "distortion": min(max(explicit["bass_808"].get("distortion", 2), 3), 4)})
        explicit["synth_width"].update({"pan_motion": "subtle", "stereo_width": 4, "mid_side_approach": "wide_pads_only"})
        explicit["arrangement"].update({"hook_early": True, "target_hook_seconds": 30, "variation_frequency_bars": 4})
        explicit["vocal"]["tuning"] = "medium" if explicit["vocal"]["tuning"] == "unknown" else explicit["vocal"]["tuning"]
        avoid.extend(["artist vocal identity cloning", "exact producer clone", "exact song copying"])
        targets["notes"].append("Scene/style request translated to broad internet digicore/hyperpop production traits only.")
    if _has(normalized, "airy adlib", "airy adlibs", "wide adlib"):
        targets["reverb_wetness"] = clamp(targets["reverb_wetness"] + 1)
    if _has(normalized, "hyperpop"):
        explicit["vocal"]["tuning"] = "medium"
        explicit["vocal"]["brightness"] = 4
    if _has(normalized, "hook", "훅", "릴스", "reels"):
        explicit["arrangement"]["hook_early"] = True
        explicit["arrangement"]["target_hook_seconds"] = 15 if _has(normalized, "15", "15초") else 30
        explicit["arrangement"]["variation_frequency_bars"] = 4
    if _has(normalized, "상업 음악", "상업음악", "상업 퀄", "상업퀄", "commercial", "프로처럼", "프로 퀄", "발매", "릴리즈"):
        targets["energy"] = max(targets["energy"], 4)
        targets["brightness"] = max(targets["brightness"], 4)
        targets["arrangement_variation"] = max(targets["arrangement_variation"], 4)
        explicit["arrangement"].update({"hook_early": True, "target_hook_seconds": 30, "variation_frequency_bars": 4})
        avoid.extend(["overcompression", "muddy 808", "harsh vocal", "chart-level success promise"])
        targets["notes"].append("Commercial quality request translated to technical readiness, mix clarity, arrangement intentionality, and QC discipline; no chart-level success is promised.")
    if _has(normalized, "suno 느낌 줄", "suno티", "ai 느낌 줄", "ai티", "사람이 찍은", "사람이 만든", "less ai", "human"):
        targets["arrangement_variation"] = max(targets["arrangement_variation"], 4)
        explicit["drums"]["avoid_random_glitch"] = True
        avoid.extend(["suno loop feel", "random AI transition", "meaningless repeated blocks"])
        targets["notes"].append("Suno/AI-feel reduction request translated to humanized arrangement variation and intentional section changes.")
    if _has(normalized, "스템 없으면", "stems 없으면", "stem 없으면", "가능한 선", "수동 플랜", "manual plan", "logic 수동"):
        avoid.extend(["fake stem-level rewrite claim", "fake Logic automation success"])
        targets["notes"].append("Stem-limited request keeps automatic fallback stereo-only and requires a manual Logic plan for stem-level edits.")
    if priority == "drums":
        targets["drum_density"] = clamp(targets["drum_density"] + 1)
    if priority == "808":
        targets["low_end_weight"] = clamp(targets["low_end_weight"] + 1)
    if priority == "vocal":
        targets["vocal_forwardness"] = 4
    if priority == "reels impact":
        targets["energy"] = clamp(targets["energy"] + 1)
        targets["arrangement_variation"] = clamp(targets["arrangement_variation"] + 1)
    if drum_direction and "love_blur" in drum_direction:
        targets["drum_density"] = 4
        targets["hat_density"] = 4
        targets["arrangement_variation"] = 4
        explicit["drums"].update({"density": 4, "transient_sharpness": 4, "swing": "light", "fill_amount": 3, "avoid_random_glitch": True})
        targets["notes"].append("Drum direction requested Love Blur-inspired energetic digital drums.")
    if vocal_direction in {"rap_forward", "rap upfront"}:
        targets["vocal_forwardness"] = 4
        explicit["vocal"]["forwardness"] = 5
    if vocal_direction in {"airy_pop", "hyperpop"}:
        targets["brightness"] = clamp(targets["brightness"] + 1)
        targets["reverb_wetness"] = clamp(targets["reverb_wetness"] + 1)
    if master_direction == "loud_demo":
        targets["energy"] = clamp(targets["energy"] + 1)
        targets["notes"].append("Master direction requests a loud demo; preserve clipping warnings.")
    if avoid_text:
        for item in re.split(r"[,/;]+", avoid_text):
            cleaned = item.strip()
            if cleaned:
                avoid.append(cleaned)

    targets["genre_family"] = sorted(set(targets["genre_family"])) or ["modern_hiphop"]
    target_elements = _target_elements_for_output(text, normalized, explicit, reference_requests)
    actions = _actions_for_output(text, normalized, target_elements, reference_requests)
    production_traits = _build_production_traits(
        text=text,
        normalized=normalized,
        explicit=explicit,
        requests=reference_requests,
        target_elements=target_elements,
    )
    autopilot = build_commercial_digicore_autopilot(text, {"target_elements": target_elements})
    if autopilot["active"]:
        production_traits["commercial_digicore_autopilot"] = autopilot
        actions.append("commercial_digicore_autopilot")
        for item in autopilot["avoid"]:
            avoid.append(item)
        if autopilot["style_cluster"]["active"]:
            for item in ("whole_style", "drums", "bass_808", "synth_width", "arrangement"):
                if item not in target_elements:
                    target_elements.append(item)
            target_elements = sorted(set(target_elements))
    copying_risk = _copying_risk(normalized, reference_requests)
    requires_owned_source = bool(copying_risk == "high" or any(item.get("sample_use_policy") == "licensed_or_owned_source_required" for item in reference_requests))
    safety_notes = [
        SAFETY_NOTE,
        "Exact copying is not allowed unless the user provides a licensed or owned sample/stem and the workflow explicitly uses it.",
        "No voice clone or living artist vocal identity cloning is allowed.",
        "Plugin requests are manual/detection targets; fallback processing may only approximate unavailable plugins.",
    ]
    if requires_owned_source:
        safety_notes.append(SAFE_SAMPLE_USE_NOTE)
    zero_clarification_requested = _has(normalized, "마음대로", "제로 판단", "알아서", "상업 음악 퀄", "상업음악 퀄", "상업 퀄")
    release_ready_requested = _has(normalized, "상업 음악", "상업음악", "상업 퀄", "상업퀄", "발매", "릴리즈", "release", "믹마", "믹스마스터")
    return {
        "raw_text": text,
        "language": detect_language(text),
        "reference_requests": reference_requests,
        "target_elements": target_elements,
        "actions": actions,
        "copying_risk": copying_risk,
        "exact_copy_allowed": False,
        "requires_user_owned_source_for_sampling": requires_owned_source,
        "vocal_identity_clone_allowed": False,
        "confidence": _overall_confidence(reference_audio_available, reference_requests),
        "production_traits": production_traits,
        "explicit_targets": explicit,
        "style_targets": targets,
        "avoid": sorted(set(avoid)),
        "safety_note": SAFETY_NOTE,
        "safety_notes": safety_notes,
        "release_ready_requested": release_ready_requested,
        "zero_clarification_requested": zero_clarification_requested,
        "no_unnecessary_questions": zero_clarification_requested,
        "missing_detail_policy": "document assumptions instead of hallucinating reference sound",
        "commercial_digicore_autopilot": autopilot,
    }

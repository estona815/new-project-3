from __future__ import annotations

import re
from typing import Any


def _compact(text: str) -> str:
    return re.sub(r"[\s._/-]+", "", text.lower())


def _has_any(text: str, compacted: str, phrases: tuple[str, ...]) -> bool:
    return any(phrase in text or phrase in compacted for phrase in phrases)


def _pitch_intensity(text: str, compacted: str) -> str:
    if _has_any(
        text,
        compacted,
        (
            "하드튠",
            "hardtune",
            "hard tune",
            "튠세게",
            "튠 세게",
            "오토튠세게",
            "autotune세게",
            "auto tune세게",
            "로봇틱하게",
            "robotic",
        ),
    ):
        return "hard_effect"
    if _has_any(text, compacted, ("자연스럽게튠", "자연스럽게 튠", "natural tune", "subtle tune")):
        return "subtle"
    if _has_any(text, compacted, ("오토튠더", "오토튠 더", "autotune더", "auto tune 더", "피치보정", "피치 보정", "autotune", "auto tune", "오토튠")):
        return "medium"
    return "none"


def _saturation_intensity(text: str, compacted: str) -> str:
    if _has_any(text, compacted, ("빡세게", "거칠게", "찢어지게", "strong", "heavy", "hard distortion")):
        return "strong"
    if _has_any(text, compacted, ("살짝", "따뜻하게", "warm", "light", "조금")):
        return "subtle"
    return "medium"


def _saturation_tone(text: str, compacted: str) -> str:
    if _has_any(text, compacted, ("따뜻하게", "warm", "dark")):
        return "dark"
    if _has_any(text, compacted, ("밝게", "bright", "찢어지게")):
        return "bright"
    return "neutral"


def _parallel_mix(intensity: str) -> str:
    return {"subtle": "low", "medium": "medium", "strong": "high"}.get(intensity, "medium")


def _apply_to(text: str, compacted: str) -> str:
    if _has_any(text, compacted, ("adlib", "adlibs", "애드립", "백킹", "backing")):
        return "adlibs"
    if _has_any(text, compacted, ("보컬버스", "vocal bus", "목소리버스")):
        return "vocal_bus"
    if _has_any(text, compacted, ("beat bus", "비트버스")):
        return "beat_bus"
    if _has_any(text, compacted, ("master bus", "마스터버스")):
        return "master_bus"
    return "lead_vocal"


def parse_plugin_requests(text: str | None) -> dict[str, Any]:
    raw_text = text or ""
    lowered = raw_text.lower()
    compacted = _compact(raw_text)
    pitch_requested = _has_any(
        lowered,
        compacted,
        ("오토튠", "autotune", "auto tune", "하드튠", "튠세게", "튠 세게", "피치보정", "피치 보정", "로봇틱하게", "자연스럽게튠"),
    )
    decapitator_requested = _has_any(
        lowered,
        compacted,
        ("디카페이터", "데카피테이터", "decapitator", "soundtoys", "사운드토이즈"),
    )
    saturation_requested = decapitator_requested or _has_any(
        lowered,
        compacted,
        ("saturation", "새츄레이션", "따뜻하게", "거칠게", "찢어지게", "살짝디스토션", "살짝 디스토션", "distortion"),
    )

    pitch = {
        "requested": pitch_requested,
        "effect": "pitch_correction",
        "intensity": _pitch_intensity(lowered, compacted) if pitch_requested else "none",
        "terms": [],
    }
    saturation: dict[str, Any] = {
        "requested": saturation_requested,
        "effect": "saturation" if saturation_requested else None,
        "requested_plugin": "Soundtoys Decapitator" if decapitator_requested else None,
        "intensity": "none",
        "parallel_mix": "none",
        "tone": "neutral",
        "apply_to": _apply_to(lowered, compacted),
    }
    if saturation_requested:
        intensity = _saturation_intensity(lowered, compacted)
        saturation.update(
            {
                "intensity": intensity,
                "parallel_mix": _parallel_mix(intensity),
                "tone": _saturation_tone(lowered, compacted),
            }
        )
    return {
        "raw_text": raw_text,
        "pitch_correction": pitch,
        "saturation": saturation,
        "requested_plugins": [saturation["requested_plugin"]] if saturation.get("requested_plugin") else [],
        "vocal_target_active": bool(pitch_requested or saturation_requested or _has_any(lowered, compacted, ("보컬", "목소리", "vocal", "voice"))),
    }

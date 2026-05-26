from __future__ import annotations

import re
from typing import Any


STYLE_TERMS = (
    "2hollis",
    "투홀리스",
    "2홀리스",
    "ycs",
    "와이씨에스",
    "system seoul",
    "시스템서울",
    "시스템 서울",
    "slayr",
    "슬레이어",
    "jane remover",
    "제인 리무버",
    "digicore",
    "디지코어",
    "hyperpop",
    "하이퍼팝",
    "internet underground",
    "인터넷 언더",
)

COMMERCIAL_TERMS = (
    "상업 음악",
    "상업음악",
    "상업 퀄",
    "상업퀄",
    "commercial",
    "commercial quality",
    "프로처럼",
    "프로 퀄",
    "발매",
    "릴리즈",
)

HUMANIZE_TERMS = (
    "suno 느낌 줄",
    "suno티",
    "ai 느낌 줄",
    "ai티",
    "사람이 찍은",
    "사람이 만든",
    "human",
    "less ai",
)

STEM_LIMIT_TERMS = (
    "스템 없으면",
    "stems 없으면",
    "stem 없으면",
    "가능한 선",
    "수동 플랜",
    "manual plan",
    "logic 수동",
)


def _compact(text: str) -> str:
    return re.sub(r"[\s._/-]+", "", text.lower())


def _has_any(text: str, compacted: str, terms: tuple[str, ...]) -> bool:
    return any(term in text or _compact(term) in compacted for term in terms)


def build_commercial_digicore_autopilot(raw_text: str | None, parsed_intent: dict[str, Any] | None = None) -> dict[str, Any]:
    text = (raw_text or "").lower()
    compacted = _compact(raw_text or "")
    parsed = parsed_intent or {}
    targets = set(str(item) for item in parsed.get("target_elements", []) if item)

    style_active = _has_any(text, compacted, STYLE_TERMS)
    commercial_requested = _has_any(text, compacted, COMMERCIAL_TERMS)
    humanize_requested = _has_any(text, compacted, HUMANIZE_TERMS)
    stem_limit_requested = _has_any(text, compacted, STEM_LIMIT_TERMS)
    reels_hook = bool("릴스" in text or "15초" in text or "hook" in text or "훅" in text)
    active = bool(style_active or commercial_requested or humanize_requested or stem_limit_requested or reels_hook)

    arrangement = {
        "hook_early": bool(reels_hook or style_active or commercial_requested),
        "target_hook_seconds": 15 if reels_hook else 30 if style_active or commercial_requested else None,
        "intro_max_seconds": 8 if reels_hook or commercial_requested else 12,
        "variation_frequency_bars": 4 if style_active or commercial_requested else 8,
        "drop_energy": "high_controlled" if style_active or commercial_requested else "medium",
        "humanized_section_changes": bool(humanize_requested or commercial_requested),
        "reduce_suno_loop_feel": bool(humanize_requested),
    }
    mix = {
        "target": "commercial_ready_demo" if commercial_requested else "digicore_reference_ready",
        "clarity_priority": "lead_melody_vocal_and_hook",
        "low_end": "strong_controlled_centered_sub",
        "drums": "sharp_controlled_no_cheap_clipping",
        "vocal": "front_bright_deessed_identity_preserved",
        "master": "streaming_safe_headroom",
        "promise_limit": "technical readiness and mix clarity only; no chart-level success promised",
    }
    logic_manual = [
        "If stems are missing, perform only broad stereo EQ, gain, trim, fade, conservative width, saturation, and mastering polish automatically.",
        "Write manual Logic steps for kick/bass replacement, drum rewrite, vocal tuning, plugin insertion, and arrangement edits.",
        "Mark true stem-level changes as manual_required unless stems, MIDI, or owned/cleared samples are provided.",
    ]
    style_cluster = {
        "active": style_active,
        "labels": [
            label
            for label, terms in (
                ("2hollis", ("2hollis", "투홀리스", "2홀리스")),
                ("slayr", ("slayr", "슬레이어")),
                ("Jane Remover", ("jane remover", "제인 리무버")),
                ("ycs", ("ycs", "와이씨에스")),
                ("SYSTEM SEOUL", ("system seoul", "시스템서울", "시스템 서울")),
            )
            if _has_any(text, compacted, terms)
        ],
        "translation": [
            "bright digital hooks",
            "internet underground/digicore/hyperpop energy",
            "strong controlled 808",
            "sharp but controlled drums",
            "hook-forward arrangement",
            "intentional chaos, not random AI glitch",
        ],
        "copying_allowed": False,
        "artist_voice_clone_allowed": False,
    }
    qc = {
        "commercial_readiness_required": bool(commercial_requested),
        "arrangement_intent_required": bool(active),
        "manual_logic_plan_required": bool(stem_limit_requested or targets & {"kick", "drums", "bass_808", "vocal"}),
        "stereo_only_warning_required": bool(stem_limit_requested),
        "score_dimensions": [
            "hook arrival",
            "humanized arrangement",
            "mix clarity",
            "low-end control",
            "vocal/plugin honesty",
            "manual Logic coverage",
        ],
    }
    avoid = [
        "chart-level success promise",
        "exact artist/song copying",
        "living artist vocal identity clone",
        "cheap rage clipping",
        "random AI glitch",
        "muddy 808",
        "overcompression",
        "fake stem-level rewrite claim",
    ]
    return {
        "active": active,
        "style_cluster": style_cluster,
        "commercial_requested": commercial_requested,
        "humanize_suno_requested": humanize_requested,
        "stem_limit_requested": stem_limit_requested,
        "arrangement_defaults": arrangement,
        "mix_targets": mix,
        "logic_manual_requirements": logic_manual,
        "qc_requirements": qc,
        "avoid": avoid,
        "safety_notes": [
            "Commercial quality means technical readiness, mix clarity, arrangement intentionality, and QC discipline.",
            "No chart-level success is promised.",
            "References are translated to high-level production targets only.",
        ],
    }

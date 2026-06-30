from __future__ import annotations

import hashlib
import re
from typing import Any

from automix.plugins.plugin_adapter_schema import now_utc


FEEDBACK_INTAKE_SCHEMA = "automix-feedback-intake-v1"


CATEGORY_RULES: dict[str, dict[str, Any]] = {
    "vocal_clarity": {
        "area": "vocal",
        "severity": "high",
        "terms": [
            "cloudy",
            "muddy vocal",
            "muffled",
            "unclear",
            "blurred",
            "smeared consonants",
            "intelligibility",
            "보컬이 뿌옇",
            "보컬이 뭉개",
            "가사 전달",
            "선명하지",
            "발음",
        ],
    },
    "vocal_presence": {
        "area": "vocal",
        "severity": "high",
        "terms": [
            "buried vocal",
            "vocal is buried",
            "vocal too low",
            "behind the beat",
            "too far back",
            "보컬이 뒤",
            "뒤로 빠",
            "보컬이 작",
            "보컬이 묻",
            "리드가 안 들",
        ],
    },
    "masking_balance": {
        "area": "balance",
        "severity": "medium",
        "terms": [
            "masking",
            "piano covers",
            "synth covers",
            "guitar covers",
            "instrument covers",
            "피아노가 보컬",
            "신스가 보컬",
            "기타가 보컬",
            "악기가 보컬",
            "보컬과 싸",
        ],
    },
    "sibilance_harshness": {
        "area": "high_end",
        "severity": "medium",
        "terms": [
            "sibilance",
            "lispy",
            "harsh",
            "metallic",
            "3k",
            "4k",
            "5k",
            "치찰음",
            "쇳소리",
            "거칠",
            "쏘",
            "날카",
        ],
    },
    "ai_artifact": {
        "area": "ai_artifact",
        "severity": "high",
        "terms": [
            "suno",
            "ai fizz",
            "fizz",
            "watery",
            "water",
            "plastic",
            "fake stereo",
            "halo",
            "artifact",
            "source separated",
            "mp3 swirl",
            "수노",
            "ai 노이즈",
            "ai 느낌",
            "고역 모래",
            "워터리",
            "물먹",
            "플라스틱",
            "페이즈",
            "번짐",
        ],
    },
    "reverb_delay_space": {
        "area": "space",
        "severity": "medium",
        "terms": [
            "too wet",
            "too much reverb",
            "delay clutter",
            "tail noise",
            "reverb distance",
            "리버브",
            "딜레이",
            "공간계",
            "잔향",
            "뒤로 빠",
        ],
    },
    "low_end": {
        "area": "low_end",
        "severity": "medium",
        "terms": [
            "808",
            "kick",
            "bass",
            "low-end",
            "low end",
            "boomy",
            "mud",
            "저역",
            "킥",
            "베이스",
            "저음",
            "뭉친",
        ],
    },
    "mastering_dynamics": {
        "area": "mastering",
        "severity": "high",
        "terms": [
            "flat master",
            "too flat",
            "overlimited",
            "over-limited",
            "limiter",
            "lufs",
            "crest",
            "no punch",
            "납작",
            "힘이 없",
            "과압축",
            "리미터",
            "크기만",
        ],
    },
    "stereo_mono": {
        "area": "stereo",
        "severity": "medium",
        "terms": [
            "mono",
            "phase",
            "correlation",
            "too wide",
            "stereo collapses",
            "모노",
            "스테레오",
            "위상",
            "무너",
            "너무 넓",
        ],
    },
    "tuning_formant": {
        "area": "pitch",
        "severity": "high",
        "terms": [
            "robotic",
            "autotune",
            "auto-tune",
            "formant",
            "tune artifact",
            "pitch artifact",
            "로봇",
            "오토튠",
            "튜닝",
            "포먼트",
            "음정 보정",
        ],
    },
    "female_support_layer": {
        "area": "vocal_layer",
        "severity": "medium",
        "terms": [
            "female lead",
            "female too loud",
            "adlib too loud",
            "backing too loud",
            "여성 보컬",
            "여보컬",
            "더블",
            "애드립",
            "하모니",
        ],
    },
}

TOTAL_REMOVAL_PATTERNS = [
    "100%",
    "completely remove",
    "remove all ai",
    "perfectly clean",
    "완전 제거",
    "전부 제거",
    "완벽하게 제거",
]


def _normalize_text(text: str) -> str:
    value = re.sub(r"\s+", " ", str(text or "")).strip()
    return value


def _feedback_id(text: str, *, pass_id: str = "", track_name: str = "") -> str:
    digest = hashlib.sha1(f"{pass_id}|{track_name}|{text}".encode("utf-8")).hexdigest()[:12]
    return f"feedback_{digest}"


def _term_matches(text_lc: str, terms: list[str]) -> list[str]:
    return [term for term in terms if term.lower() in text_lc]


def classify_feedback(
    text: str,
    *,
    project_name: str = "",
    pass_id: str = "",
    track_name: str = "",
    source: str = "user",
    received_at: str | None = None,
) -> dict[str, Any]:
    normalized = _normalize_text(text)
    text_lc = normalized.lower()
    categories: list[dict[str, Any]] = []
    for category, rule in CATEGORY_RULES.items():
        matches = _term_matches(text_lc, list(rule.get("terms", [])))
        if not matches:
            continue
        confidence = min(1.0, 0.55 + 0.12 * len(matches))
        categories.append(
            {
                "category": category,
                "area": rule.get("area", category),
                "severity": rule.get("severity", "medium"),
                "confidence": round(confidence, 3),
                "matched_terms": sorted(set(matches)),
            }
        )
    if not categories and normalized:
        categories.append(
            {
                "category": "general_mix_feedback",
                "area": "general",
                "severity": "medium",
                "confidence": 0.35,
                "matched_terms": [],
            }
        )
    safety_flags = []
    if any(pattern.lower() in text_lc for pattern in TOTAL_REMOVAL_PATTERNS):
        safety_flags.append("do_not_claim_total_artifact_removal")
    if "final" in text_lc or "deliver" in text_lc or "납품" in text_lc:
        safety_flags.append("final_claim_requires_qc_and_human_review")
    primary = max(categories, key=lambda item: item.get("confidence", 0.0)) if categories else None
    return {
        "schema": FEEDBACK_INTAKE_SCHEMA,
        "feedback_id": _feedback_id(normalized, pass_id=pass_id, track_name=track_name),
        "project_name": project_name,
        "pass_id": pass_id,
        "track_name": track_name,
        "source": source,
        "received_at": received_at or now_utc(),
        "raw_text": str(text or ""),
        "normalized_text": normalized,
        "primary_category": primary.get("category") if primary else "none",
        "categories": categories,
        "safety_flags": sorted(set(safety_flags)),
        "requires_human_review": True,
    }


def classify_feedback_batch(
    feedback_items: list[str],
    *,
    project_name: str = "",
    pass_id: str = "",
    track_name: str = "",
    source: str = "user",
) -> list[dict[str, Any]]:
    return [
        classify_feedback(
            item,
            project_name=project_name,
            pass_id=pass_id,
            track_name=track_name,
            source=source,
        )
        for item in feedback_items
        if str(item or "").strip()
    ]

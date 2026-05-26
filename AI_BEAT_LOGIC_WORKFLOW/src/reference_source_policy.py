from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


SOURCE_PRIORITY = {
    "official_artist": 7,
    "label": 6,
    "official_streaming": 5,
    "interview": 4,
    "review": 4,
    "tutorial": 2,
    "social": 1,
    "unknown": 0,
}

ALLOWED_SOURCE_TYPES = set(SOURCE_PRIORITY)

HIGH_LEVEL_TERMS = {
    "bright",
    "dark",
    "energetic",
    "distorted",
    "clean",
    "glitchy",
    "wide",
    "dry",
    "wet",
    "punchy",
    "subby",
    "digital",
    "digicore",
    "hyperpop",
    "underground",
    "rap",
    "808",
    "bass",
    "drums",
    "hats",
    "snare",
    "kick",
    "melodic",
    "aggressive",
    "compressed",
    "saturated",
    "ambient",
    "airy",
    "forward",
    "vocal",
    "hook",
    "internet-driven",
    "internet",
    "rage rap",
    "rage",
    "off-kilter",
    "club",
    "futuristic",
    "korean internet",
    "nostalgia",
    "2000s",
    "online",
    "game",
    "meme",
    "digital pop",
    "playful",
    "controlled chaos",
    "투홀리스",
    "시스템서울",
    "시스템 서울",
    "와이씨에스",
    "온라인",
    "게임",
    "밈",
    "노스탤지어",
    "향수",
    "드럼",
    "베이스",
    "보컬",
    "신스",
    "서브",
    "공간감",
    "디지코어",
    "클리핑",
}

EXISTENCE_TERMS = {
    "exists",
    "track exists",
    "song exists",
    "available on",
    "streaming profile",
    "artist profile",
    "discography",
    "release",
    "released",
    "곡 존재",
    "발매",
}


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def classify_source(url_or_id: str = "", title: str = "", declared_type: str | None = None) -> str:
    if declared_type in ALLOWED_SOURCE_TYPES:
        return declared_type
    text = f"{url_or_id} {title}".lower()
    if any(token in text for token in ("official", "artist site", ".com/official")):
        return "official_artist"
    if any(token in text for token in ("label", "records", "interscope", "atlantic", "columbia")):
        return "label"
    if any(token in text for token in ("spotify", "apple music", "soundcloud artist", "bandcamp")):
        return "official_streaming"
    if any(token in text for token in ("interview", "q&a")):
        return "interview"
    if any(token in text for token in ("review", "pitchfork", "stereogum", "complex", "the fader", "billboard")):
        return "review"
    if any(token in text for token in ("tutorial", "remake", "type beat", "how to")):
        return "tutorial"
    if any(token in text for token in ("instagram", "tiktok", "twitter", "x.com", "reddit")):
        return "social"
    if "youtube" in text or "youtu.be" in text:
        return "official_artist" if "official" in text else "social"
    return "unknown"


def confidence_for_source(source_type: str, claims: list[str] | None = None) -> str:
    claims_text = " ".join(claims or []).lower()
    if source_type in {"official_artist", "label", "official_streaming", "interview", "review"}:
        confidence = "medium"
    elif source_type in {"tutorial", "social"}:
        confidence = "low"
    else:
        confidence = "low"
    if any(token in claims_text for token in ("remake", "tutorial", "exact pattern", "drum pattern", "bassline")):
        return "medium" if confidence == "high" else "low"
    return confidence


def sanitize_existence_claim(claim: str) -> str | None:
    cleaned = " ".join(str(claim).strip().split())
    if not cleaned:
        return None
    lower = cleaned.lower()
    if any(term in lower for term in EXISTENCE_TERMS):
        return cleaned[:180]
    return None


def sanitize_claim(claim: str) -> str | None:
    cleaned = " ".join(str(claim).strip().split())
    if not cleaned:
        return None
    lower = cleaned.lower()
    if "lyrics" in lower or "lyric" in lower or len(cleaned) > 180:
        return None
    if not any(term in lower for term in HIGH_LEVEL_TERMS):
        return None
    blocked_phrases = ("copy this pattern", "same melody", "exact bassline", "exact drum pattern", "sample this")
    if any(phrase in lower for phrase in blocked_phrases):
        return None
    return cleaned


def trait_inference_allowed_from_sources(sources: list[dict[str, Any]], audio_available: bool = False) -> bool:
    if audio_available:
        return True
    return any(
        bool(source.get("relevant_claims"))
        and not source.get("existence_only")
        and source.get("confidence") in {"medium", "high"}
        for source in sources
    )


def source_limitations(sources: list[dict[str, Any]], trait_inference_allowed: bool | None = None) -> list[str]:
    limitations: list[str] = []
    for source in sources:
        limitations.extend(str(item) for item in source.get("limitations", []))
    if trait_inference_allowed is False:
        limitations.append("web sources do not provide enough broad style descriptors for sonic trait inference")
    if any(source.get("existence_only") for source in sources):
        limitations.append("one or more sources only prove artist/track existence")
    return list(dict.fromkeys(limitations))


def normalize_source(candidate: dict[str, Any], retrieved_at: str | None = None) -> dict[str, Any]:
    title = str(candidate.get("title") or "untitled source")
    url_or_id = str(candidate.get("url_or_id") or candidate.get("url") or "")
    source_type = classify_source(url_or_id, title, candidate.get("source_type"))
    raw_claims = candidate.get("relevant_claims") or candidate.get("claims") or []
    claims = [claim for claim in (sanitize_claim(str(item)) for item in raw_claims) if claim]
    existence_claims = [claim for claim in (sanitize_existence_claim(str(item)) for item in raw_claims) if claim]
    confidence = confidence_for_source(source_type, claims)
    limitations = list(candidate.get("limitations") or [])
    limitations.extend(["not a direct audio analysis", "not enough evidence for exact sound"])
    if source_type == "tutorial":
        limitations.append("tutorial/remake source is not canonical")
    existence_only = bool(existence_claims and not claims)
    if existence_only:
        limitations.append("source only proves artist/track existence; no sonic traits inferred")
    return {
        "title": title,
        "url_or_id": url_or_id or title,
        "source_type": source_type,
        "confidence": confidence,
        "retrieved_at": retrieved_at or utc_timestamp(),
        "relevant_claims": claims,
        "existence_claims": existence_claims,
        "existence_only": existence_only,
        "limitations": list(dict.fromkeys(limitations)),
    }


def combined_confidence(sources: list[dict[str, Any]], audio_available: bool = False) -> str:
    if audio_available:
        return "high"
    if any(source.get("confidence") == "medium" for source in sources):
        return "medium"
    return "low"


def policy_notes(sources: list[dict[str, Any]]) -> list[str]:
    notes = [
        "Web text is used only for high-level production descriptors.",
        "No copyrighted audio is downloaded from the web.",
        "No lyrics, exact drum patterns, exact basslines, samples, melodies, or recordings are copied.",
    ]
    if any(source.get("source_type") == "tutorial" for source in sources):
        notes.append("Tutorial/remake sources are lower-confidence and non-canonical.")
    if any(source.get("source_type") == "social" for source in sources):
        notes.append("Social sources are lower-confidence context only.")
    return notes

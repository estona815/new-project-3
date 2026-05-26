from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from reference_source_policy import (
    SOURCE_PRIORITY,
    combined_confidence,
    normalize_source,
    policy_notes,
    source_limitations,
    trait_inference_allowed_from_sources,
    utc_timestamp,
)


CONFIDENCE_PRIORITY = {"low": 0, "medium": 1, "high": 2}


def _placeholder_query(query: str | None) -> bool:
    text = (query or "").strip().lower()
    compacted = "".join(text.split())
    placeholders = {"ㅇㅇㅇ", "ㅇㅇㅇㅇ", "ooo", "oooo", "unknown title", "this song"}
    return compacted in placeholders or any(token in compacted for token in ("ㅇㅇㅇ느낌", "ㅇㅇㅇㅇ베이스"))


def collect_web_reference_sources(
    query: str | None,
    *,
    web_access_available: bool = False,
    source_candidates: list[dict[str, Any]] | None = None,
    reference_audio_available: bool = False,
    retrieved_at: str | None = None,
) -> dict[str, Any]:
    timestamp = retrieved_at or utc_timestamp()
    candidates = source_candidates or []
    if not web_access_available:
        return {
            "query": query or "",
            "web_access_available": False,
            "web_reference_research_unavailable": True,
            "sources": [],
            "combined_confidence": "low",
            "source_limitations": ["web access unavailable; reference remains text-only low confidence"],
            "trait_inference_allowed": False,
            "notes": [
                "web_reference_research_unavailable: true",
                "Web access was unavailable or disabled; using text-only low-confidence reference interpretation unless reference audio is provided.",
                "User-provided reference audio remains preferred over web text.",
            ],
        }
    if _placeholder_query(query):
        return {
            "query": query or "",
            "web_access_available": True,
            "web_reference_research_unavailable": False,
            "sources": [],
            "combined_confidence": "low",
            "source_limitations": ["placeholder reference has no actionable artist/title for web lookup"],
            "trait_inference_allowed": False,
            "notes": [
                "Unknown placeholder reference such as ㅇㅇㅇ is not looked up as an actual title.",
                "Ask for reference audio or a clearer artist/title before raising confidence.",
            ],
        }

    sources = [normalize_source(candidate, timestamp) for candidate in candidates]
    sources = [source for source in sources if source.get("relevant_claims") or source.get("existence_claims")]
    sources.sort(
        key=lambda item: (
            CONFIDENCE_PRIORITY.get(item["confidence"], 0),
            SOURCE_PRIORITY.get(item["source_type"], 0),
            item["title"],
        ),
        reverse=True,
    )
    notes = policy_notes(sources)
    if not sources:
        notes.append("No usable web source claims were provided by the source collection adapter.")
    if reference_audio_available:
        notes.append("User-provided reference audio takes priority over web text.")
    trait_allowed = trait_inference_allowed_from_sources(sources, reference_audio_available)
    limitations = source_limitations(sources, trait_allowed)
    return {
        "query": query or "",
        "web_access_available": True,
        "web_reference_research_unavailable": False,
        "sources": sources,
        "combined_confidence": combined_confidence(sources, reference_audio_available),
        "source_limitations": limitations,
        "trait_inference_allowed": trait_allowed,
        "notes": notes,
    }


def render_web_reference_summary(research: dict[str, Any]) -> str:
    lines = [
        "# Web Reference Summary",
        "",
        f"- query: {research.get('query', '') or 'not provided'}",
        f"- web access available: {str(bool(research.get('web_access_available'))).lower()}",
        f"- web_reference_research_unavailable: {str(bool(research.get('web_reference_research_unavailable'))).lower()}",
        f"- combined confidence: {research.get('combined_confidence', 'low')}",
        f"- trait inference allowed: {str(bool(research.get('trait_inference_allowed'))).lower()}",
        "",
        "## Source Policy",
        "- User-provided reference audio is preferred over web text.",
        "- Web sources are used only for high-level production traits.",
        "- No copyrighted audio, lyrics, exact patterns, samples, melodies, or recordings are downloaded or copied.",
        "",
        "## Sources",
    ]
    sources = research.get("sources", [])
    if not sources:
        lines.append("- none")
    for source in sources:
        lines.extend(
            [
                f"- {source.get('title')} ({source.get('source_type')}, {source.get('confidence')})",
                f"  - id/url: {source.get('url_or_id')}",
                f"  - claims: {'; '.join(source.get('relevant_claims', [])) or 'none'}",
                f"  - existence: {'; '.join(source.get('existence_claims', [])) or 'none'}",
                f"  - limitations: {'; '.join(source.get('limitations', [])) or 'none'}",
            ]
        )
    lines.extend(["", "## Source Limitations"])
    limitations = research.get("source_limitations", [])
    if not limitations:
        lines.append("- none")
    else:
        lines.extend(f"- {item}" for item in limitations)
    lines.extend(["", "## Notes"])
    notes = research.get("notes", [])
    if not notes:
        lines.append("- none")
    else:
        lines.extend(f"- {note}" for note in notes)
    return "\n".join(lines) + "\n"


def write_web_reference_outputs(research: dict[str, Any], output_dir: Path) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "web_reference_sources.json"
    summary_path = output_dir / "web_reference_summary.md"
    json_path.write_text(json.dumps(research, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    summary_path.write_text(render_web_reference_summary(research), encoding="utf-8")
    return {"web_reference_sources": json_path, "web_reference_summary": summary_path}

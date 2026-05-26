from __future__ import annotations

import json
from pathlib import Path
from typing import Any


METADATA_FIELDS = (
    "title",
    "artist",
    "version",
    "genre",
    "language",
    "explicit",
    "isrc",
    "upc",
    "copyright_year",
    "copyright_owner",
    "producer",
    "composer",
    "lyricist",
    "featured_artists",
)

REQUIRED_METADATA_FIELDS = (
    "title",
    "artist",
    "genre",
    "language",
    "explicit",
    "copyright_year",
    "copyright_owner",
    "producer",
    "composer",
)


def normalize_release_metadata(metadata: dict[str, Any] | None = None) -> dict[str, Any]:
    source = metadata or {}
    normalized = {
        "title": str(source.get("title") or ""),
        "artist": str(source.get("artist") or ""),
        "version": str(source.get("version") or ""),
        "genre": str(source.get("genre") or ""),
        "language": str(source.get("language") or ""),
        "explicit": source.get("explicit") if source.get("explicit") in {True, False} else None,
        "isrc": str(source.get("isrc") or ""),
        "upc": str(source.get("upc") or ""),
        "copyright_year": str(source.get("copyright_year") or ""),
        "copyright_owner": str(source.get("copyright_owner") or ""),
        "producer": str(source.get("producer") or ""),
        "composer": str(source.get("composer") or ""),
        "lyricist": str(source.get("lyricist") or ""),
        "featured_artists": list(source.get("featured_artists") or []),
    }
    return normalized


def missing_metadata_fields(metadata: dict[str, Any]) -> list[str]:
    missing: list[str] = []
    for field in REQUIRED_METADATA_FIELDS:
        value = metadata.get(field)
        if value is None or value == "":
            missing.append(field)
    return missing


def metadata_complete(metadata: dict[str, Any]) -> bool:
    return not missing_metadata_fields(metadata)


def build_release_metadata_payload(metadata: dict[str, Any] | None = None) -> dict[str, Any]:
    normalized = normalize_release_metadata(metadata)
    missing = missing_metadata_fields(normalized)
    return {
        "schema_version": "release_metadata.v1",
        "metadata": normalized,
        "complete": not missing,
        "missing_fields": missing,
        "notes": [
            "ISRC and UPC are left blank unless supplied; they are never invented.",
            "A draft release package may be generated with incomplete metadata, but release_ready remains false.",
        ],
    }


def render_release_metadata_markdown(payload: dict[str, Any]) -> str:
    metadata = payload.get("metadata", {})
    lines = [
        "# Release Metadata",
        "",
        f"- complete: {str(bool(payload.get('complete'))).lower()}",
        f"- missing fields: {', '.join(payload.get('missing_fields', [])) or 'none'}",
        "",
        "## Fields",
    ]
    for field in METADATA_FIELDS:
        value = metadata.get(field)
        if isinstance(value, list):
            value = ", ".join(str(item) for item in value)
        lines.append(f"- {field}: {value if value not in {None, ''} else 'not provided'}")
    lines.extend(["", "## Notes", *[f"- {item}" for item in payload.get("notes", [])]])
    return "\n".join(lines).rstrip() + "\n"


def write_release_metadata_files(output_dir: str | Path, payload: dict[str, Any]) -> dict[str, Path]:
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    json_path = root / "release_metadata.json"
    md_path = root / "release_metadata.md"
    json_path.write_text(json.dumps(payload.get("metadata", {}), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    md_path.write_text(render_release_metadata_markdown(payload), encoding="utf-8")
    return {"json": json_path, "markdown": md_path}

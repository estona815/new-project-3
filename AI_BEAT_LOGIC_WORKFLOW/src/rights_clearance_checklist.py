from __future__ import annotations

from typing import Any


def build_rights_payload(
    *,
    contains_samples: bool = False,
    all_samples_owned_or_cleared: bool | None = None,
    source_ownership_confirmed: bool | None = None,
    vocal_performer_consent: bool | None = None,
    featured_artist_metadata_complete: bool | None = None,
    explicit_content_flag_set: bool | None = None,
    exact_copy_risk_unresolved: bool = False,
) -> dict[str, Any]:
    blocking: list[str] = []
    if contains_samples and all_samples_owned_or_cleared is not True:
        blocking.append("samples are used but ownership/clearance is not confirmed")
    if source_ownership_confirmed is not True:
        blocking.append("stem/source ownership is not confirmed")
    if vocal_performer_consent is not True:
        blocking.append("vocal performer consent is not confirmed")
    if featured_artist_metadata_complete is False:
        blocking.append("featured artist metadata is incomplete")
    if explicit_content_flag_set is not True:
        blocking.append("explicit content flag is not confirmed")
    if exact_copy_risk_unresolved:
        blocking.append("exact-copy risk is unresolved")
    return {
        "schema_version": "rights_clearance.v1",
        "rights": {
            "contains_samples": bool(contains_samples),
            "all_samples_owned_or_cleared": all_samples_owned_or_cleared if contains_samples else True,
            "uses_reference_style_only": True,
            "web_audio_downloaded": False,
            "voice_clone_used": False,
            "exact_copy_claim": False,
            "source_ownership_confirmed": source_ownership_confirmed,
            "vocal_performer_consent": vocal_performer_consent,
            "featured_artist_metadata_complete": featured_artist_metadata_complete,
            "explicit_content_flag_set": explicit_content_flag_set,
        },
        "release_ready": not blocking,
        "blocking_issues": blocking,
    }


def render_rights_clearance_checklist(payload: dict[str, Any]) -> str:
    rights = payload.get("rights", {})
    rows = [
        ("sample ownership", rights.get("all_samples_owned_or_cleared")),
        ("stem/source ownership", rights.get("source_ownership_confirmed")),
        ("vocal performer consent", rights.get("vocal_performer_consent")),
        ("featured artist metadata", rights.get("featured_artist_metadata_complete")),
        ("explicit content flag", rights.get("explicit_content_flag_set")),
        ("reference style only note", rights.get("uses_reference_style_only")),
        ("no web audio download", not rights.get("web_audio_downloaded")),
        ("no voice clone", not rights.get("voice_clone_used")),
        ("no exact copy", not rights.get("exact_copy_claim")),
    ]
    lines = [
        "# Rights Clearance Checklist",
        "",
        f"- rights ready: {str(bool(payload.get('release_ready'))).lower()}",
        "",
        "## Checklist",
    ]
    for label, value in rows:
        status = "confirmed" if value is True else "not applicable" if value is None else "blocked"
        lines.append(f"- {label}: {status}")
    lines.extend(
        [
            "",
            "## Blocking Issues",
            *([f"- {item}" for item in payload.get("blocking_issues", [])] or ["- none"]),
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def render_distribution_checklist(metadata: dict[str, Any], *, cover_art_present: bool = False, final_audio_verified: bool = False) -> str:
    fields = {
        "title": metadata.get("title") or "",
        "artist": metadata.get("artist") or "",
        "release version": metadata.get("version") or "",
        "genre": metadata.get("genre") or "",
        "mood": metadata.get("mood") or "",
        "language": metadata.get("language") or "",
        "explicit flag": metadata.get("explicit"),
        "ISRC if available": metadata.get("isrc") or "",
        "UPC if available": metadata.get("upc") or "",
        "songwriter/composer": metadata.get("composer") or "",
        "producer": metadata.get("producer") or "",
        "copyright owner": metadata.get("copyright_owner") or "",
        "cover art ready": cover_art_present,
        "final audio verified": final_audio_verified,
        "lyrics if applicable": metadata.get("lyrics_status") or "",
        "splits if applicable": metadata.get("splits_status") or "",
    }
    lines = [
        "# Distribution Checklist",
        "",
        "- This package does not mean actual distributor submission occurred.",
        "",
        "## Placeholders",
    ]
    for label, value in fields.items():
        lines.append(f"- {label}: {value if value not in {None, ''} else 'not provided'}")
    return "\n".join(lines).rstrip() + "\n"


def render_cover_art_requirements() -> str:
    return "\n".join(
        [
            "# Cover Art Requirements",
            "",
            "- Cover art is not present.",
            "- Include square artwork that meets distributor requirements before actual submission.",
            "- Missing cover art does not block local audio completion unless release package policy requires artwork.",
        ]
    ).rstrip() + "\n"

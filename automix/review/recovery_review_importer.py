from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from automix.review.recovery_review_schema import ALLOWED_REVIEW_DECISIONS


def load_review_decisions_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {"reviewer": "user", "decisions": [], "errors": [f"decision_json_unreadable:{type(exc).__name__}"]}
    decisions = data.get("decisions", []) if isinstance(data.get("decisions"), list) else []
    return {"reviewer": data.get("reviewer", "user"), "decisions": decisions, "errors": []}


def decision_from_cli(
    *,
    draft_track_name: str | None,
    decision: str | None,
    notes: str = "",
    acknowledge_warnings: bool = False,
    reviewer: str = "user",
) -> dict[str, Any]:
    if not draft_track_name or not decision:
        return {"reviewer": reviewer, "decisions": [], "errors": []}
    return {
        "reviewer": reviewer,
        "decisions": [
            {
                "draft_track_name": draft_track_name,
                "decision": decision,
                "notes": notes,
                "warnings_acknowledged": ["cli_acknowledged"] if acknowledge_warnings else [],
            }
        ],
        "errors": [],
    }


def parse_markdown_review_form(path: Path) -> dict[str, Any]:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        return {"reviewer": "user", "decisions": [], "errors": [f"markdown_form_unreadable:{type(exc).__name__}"]}
    decisions = []
    sections = re.split(r"(?m)^### Track:\s*", text)
    for section in sections[1:]:
        track_name = section.splitlines()[0].strip()
        draft_match = re.search(r"Recovery Draft:\s*`([^`]+)`", section)
        checked = re.findall(r"(?m)^\[x\]\s+([a-z_]+)\s*$", section, flags=re.IGNORECASE)
        if not draft_match or not checked:
            continue
        decision = checked[0].lower()
        if decision not in ALLOWED_REVIEW_DECISIONS - {"needs_review"}:
            continue
        ack = bool(re.search(r"Warnings acknowledged:\s*\n\[x\]\s+yes", section, flags=re.IGNORECASE))
        decisions.append(
            {
                "track_name": track_name,
                "draft_track_name": draft_match.group(1),
                "decision": decision,
                "notes": "",
                "warnings_acknowledged": ["markdown_acknowledged"] if ack else [],
            }
        )
    return {"reviewer": "user", "decisions": decisions, "errors": []}


def validate_import_payload(payload: dict[str, Any]) -> list[str]:
    errors = list(payload.get("errors", []))
    for item in payload.get("decisions", []) or []:
        if item.get("decision") not in ALLOWED_REVIEW_DECISIONS:
            errors.append(f"invalid_decision:{item.get('draft_track_name')}:{item.get('decision')}")
        if not item.get("draft_track_name"):
            errors.append("draft_track_name_missing")
    return errors


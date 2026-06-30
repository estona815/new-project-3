from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from automix.plugins.plugin_adapter_schema import now_utc, write_json


ROLLBACK_REGISTRY_SCHEMA = "automix-global-rollback-registry-v1"

STAGE_HINTS = {
    "recovery": "vocal_recovery",
    "pitch": "pitch_correction",
    "placement": "vocal_placement",
    "reference": "reference_matching",
    "premaster": "premaster",
    "final": "final_export",
}


def _stage_from_path(path: Path) -> str:
    lower = path.name.lower()
    for hint, stage in STAGE_HINTS.items():
        if hint in lower:
            return stage
    return "unknown"


def _load_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def build_global_rollback_registry(
    *,
    project_name: str,
    output_dir: Path,
    applied_stages: list[str] | None = None,
) -> dict[str, Any]:
    entries: list[dict[str, Any]] = []
    warnings: list[str] = []
    for path in sorted((output_dir / "rollback").glob("*.json")):
        data = _load_json(path)
        stage = str(data.get("stage") or data.get("source_stage") or _stage_from_path(path))
        entries.append(
            {
                "stage": stage,
                "rollback_file": str(path),
                "original_tracks": data.get("original_tracks", []),
                "draft_tracks": data.get("draft_tracks", data.get("created_tracks", [])),
                "created_sends": data.get("created_sends", []),
                "plugins_inserted": data.get("plugins_inserted", []),
                "safe_to_rollback": bool(data.get("safe_to_rollback", True)),
            }
        )
    registry = {
        "schema": ROLLBACK_REGISTRY_SCHEMA,
        "project_name": project_name,
        "created_at": now_utc(),
        "rollback_entries": entries,
        "original_tracks_protected": True,
        "original_master_protected": True,
        "warnings": warnings,
        "applied_stages": applied_stages or [],
    }
    validation = validate_global_rollback_integrity(registry, applied_stages=applied_stages or [])
    registry["validation"] = validation
    write_json(output_dir / "rollback" / "global_rollback_registry.json", registry)
    return registry


def validate_global_rollback_integrity(registry: dict[str, Any], *, applied_stages: list[str] | None = None) -> dict[str, Any]:
    applied = applied_stages or registry.get("applied_stages", [])
    entries = registry.get("rollback_entries", [])
    stages_with_rollback = {entry.get("stage") for entry in entries}
    failures: list[str] = []
    warnings: list[str] = []
    for stage in applied:
        if stage not in stages_with_rollback:
            failures.append(f"{stage}_applied_without_rollback_file")
    for entry in entries:
        path = Path(str(entry.get("rollback_file", "")))
        if not path.exists():
            failures.append(f"{entry.get('stage')}_rollback_file_missing")
        if not entry.get("safe_to_rollback", False):
            failures.append(f"{entry.get('stage')}_not_safe_to_rollback")
        for draft in entry.get("draft_tracks", []):
            if isinstance(draft, dict) and draft.get("path") and not Path(str(draft["path"])).exists():
                failures.append(f"{entry.get('stage')}_draft_track_reference_missing")
    if not registry.get("original_tracks_protected", False):
        failures.append("original_track_protection_failed")
    if not registry.get("original_master_protected", False):
        failures.append("original_master_protection_failed")
    if not entries and applied:
        warnings.append("applied_stage_list_present_but_no_rollback_entries")
    return {
        "passed": not failures,
        "failures": sorted(set(failures)),
        "warnings": sorted(set(warnings)),
    }

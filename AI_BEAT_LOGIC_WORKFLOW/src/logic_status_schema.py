from __future__ import annotations

import json
from pathlib import Path
from typing import Any


VALID_STATUSES = {"unavailable", "available", "partial_success", "manual_required", "failed", "success"}


def build_logic_autopilot_status(
    *,
    status: str = "manual_required",
    reason: str = "Manual Logic plan generated; no verified Logic project automation was performed.",
    project_path: str | Path | None = None,
    final_wav_path: str | Path | None = None,
) -> dict[str, Any]:
    normalized = status if status in VALID_STATUSES else "manual_required"
    project_exists = bool(project_path and Path(project_path).expanduser().exists())
    final_exists = bool(final_wav_path and Path(final_wav_path).expanduser().exists())
    success_allowed = normalized == "success" and project_exists and final_exists
    if normalized == "success" and not success_allowed:
        normalized = "failed"
        reason = "Success was requested but required .logicx/project and final WAV verification artifacts were not found."
    return {
        "schema_version": "logic_autopilot_status.v1",
        "status": normalized,
        "project_created": project_exists,
        "audio_imported": False,
        "regions_created": False,
        "automation_written": False,
        "plugins_inserted": False,
        "bounce_exported": False,
        "verified_output_exists": final_exists,
        "success_allowed": success_allowed,
        "reason": reason,
        "claim_guard": {
            "logic_project_success_claimed": success_allowed,
            "midi_imported_into_logic": False,
            "plugin_insertion_verified": False,
            "bounce_export_verified": final_exists,
        },
    }


def write_logic_autopilot_status(path: str | Path, status: dict[str, Any]) -> Path:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(status, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return output

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from automix.plugins.plugin_adapter_schema import now_utc, write_json


RESUME_STATE_SCHEMA = "automix-resume-state-v1"


def _load(path: Path) -> dict[str, Any] | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def build_resume_state(
    *,
    project_path: str | Path | None,
    output_dir: Path,
    force_rerun: bool = False,
) -> dict[str, Any]:
    manifest_path = output_dir / "orchestrator" / "automix_orchestration_manifest.json"
    previous = _load(manifest_path)
    project = Path(project_path).expanduser() if project_path else Path("")
    warnings: list[str] = []
    reusable: list[str] = []
    stale: list[str] = []
    conflicts: list[str] = []

    if previous:
        for result in previous.get("stage_results", []):
            stage = result.get("stage")
            if result.get("status") in {"passed", "passed_with_warnings", "skipped"}:
                reusable.append(stage)
    if force_rerun:
        stale.extend(reusable)
        reusable = []
        warnings.append("force_rerun_requested")
    if previous and project and project.exists():
        project_mtime = project.stat().st_mtime
        previous_finished = previous.get("finished_at", "")
        manifest_mtime = manifest_path.stat().st_mtime if manifest_path.exists() else 0.0
        if project_mtime > manifest_mtime:
            stale.extend(reusable)
            reusable = []
            warnings.append(f"project_changed_after_previous_manifest:{previous_finished}")
    if previous and not (output_dir / "rollback" / "global_rollback_registry.json").exists():
        warnings.append("rollback_registry_missing_rebuild_required")
    if previous and previous.get("global_status") in {"final_delivery_created", "drafts_created_review_required"}:
        warnings.append("accepted_or_reviewable_draft_may_exist_do_not_overwrite")

    state = {
        "schema": RESUME_STATE_SCHEMA,
        "created_at": now_utc(),
        "previous_state_found": bool(previous),
        "reusable_stage_outputs": sorted(set(item for item in reusable if item)),
        "stale_stage_outputs": sorted(set(item for item in stale if item)),
        "conflicts": sorted(set(conflicts)),
        "resume_allowed": not conflicts,
        "warnings": sorted(set(warnings)),
    }
    write_json(output_dir / "orchestrator" / "resume_state.json", state)
    return state

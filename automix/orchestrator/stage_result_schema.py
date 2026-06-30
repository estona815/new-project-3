from __future__ import annotations

import time
from typing import Any

from automix.plugins.plugin_adapter_schema import now_utc
from automix.orchestrator.stage_status import StageStatus, normalize_status


STAGE_RESULT_SCHEMA = "automix-stage-result-v1"

MANUAL_ACTION_TYPES = {
    "provide_isolated_vocal_stem",
    "validate_plugin_mapping",
    "approve_human_review",
    "fix_project_routing",
    "rerun_ab_render",
    "manual_mix_revision",
    "manual_mastering_required",
    "review_recovery_drafts",
    "acknowledge_warnings",
}


def start_stage(stage: str, inputs: list[str] | None = None) -> dict[str, Any]:
    return {
        "schema": STAGE_RESULT_SCHEMA,
        "stage": stage,
        "status": StageStatus.RUNNING.value,
        "started_at": now_utc(),
        "_started_monotonic": time.monotonic(),
        "finished_at": "",
        "duration_seconds": 0.0,
        "inputs": inputs or [],
        "outputs": [],
        "reports": [],
        "warnings": [],
        "failures": [],
        "blockers": [],
        "requires_manual_action": False,
        "manual_action_type": None,
        "safe_to_continue": True,
        "summary": "",
    }


def finish_stage(
    result: dict[str, Any],
    *,
    status: str | StageStatus,
    outputs: list[str] | None = None,
    reports: list[str] | None = None,
    warnings: list[str] | None = None,
    failures: list[str] | None = None,
    blockers: list[str] | None = None,
    requires_manual_action: bool = False,
    manual_action_type: str | None = None,
    safe_to_continue: bool | None = None,
    summary: str = "",
) -> dict[str, Any]:
    value = normalize_status(status)
    result["status"] = value
    result["finished_at"] = now_utc()
    started = result.pop("_started_monotonic", None)
    result["duration_seconds"] = round(max(0.0, time.monotonic() - float(started or time.monotonic())), 6)
    result["outputs"] = list(dict.fromkeys(result.get("outputs", []) + (outputs or [])))
    result["reports"] = list(dict.fromkeys(result.get("reports", []) + (reports or [])))
    result["warnings"] = sorted(set(result.get("warnings", []) + (warnings or [])))
    result["failures"] = sorted(set(result.get("failures", []) + (failures or [])))
    result["blockers"] = sorted(set(result.get("blockers", []) + (blockers or [])))
    if manual_action_type and manual_action_type not in MANUAL_ACTION_TYPES:
        result["warnings"].append(f"unknown_manual_action_type:{manual_action_type}")
    result["requires_manual_action"] = bool(requires_manual_action or manual_action_type)
    result["manual_action_type"] = manual_action_type
    if safe_to_continue is None:
        safe_to_continue = value in {
            StageStatus.PASSED.value,
            StageStatus.PASSED_WITH_WARNINGS.value,
            StageStatus.SKIPPED.value,
        }
    result["safe_to_continue"] = bool(safe_to_continue)
    result["summary"] = summary
    return result


def skipped_stage(stage: str, reason: str, *, manual_action_type: str | None = None) -> dict[str, Any]:
    return finish_stage(
        start_stage(stage),
        status=StageStatus.SKIPPED,
        warnings=[reason],
        requires_manual_action=bool(manual_action_type),
        manual_action_type=manual_action_type,
        safe_to_continue=True,
        summary=reason,
    )


def validate_stage_result(result: dict[str, Any]) -> list[str]:
    required = {
        "stage",
        "status",
        "started_at",
        "finished_at",
        "duration_seconds",
        "inputs",
        "outputs",
        "reports",
        "warnings",
        "failures",
        "blockers",
        "requires_manual_action",
        "manual_action_type",
        "safe_to_continue",
    }
    missing = sorted(required - set(result))
    errors = [f"missing_{key}" for key in missing]
    if normalize_status(result.get("status", "")) != result.get("status"):
        errors.append("invalid_status")
    return errors

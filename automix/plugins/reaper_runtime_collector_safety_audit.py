from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from automix.plugins.plugin_adapter_schema import now_utc, write_json
from automix.plugins.plugin_semantic_validation_runtime_collector_package import (
    PLUGIN_SEMANTIC_VALIDATION_RUNTIME_COLLECTOR_PACKAGE_SCHEMA,
    REAPER_RUNTIME_QUEUE_SCHEMA,
)


REAPER_RUNTIME_COLLECTOR_SAFETY_AUDIT_SCHEMA = "automix-reaper-runtime-collector-safety-audit-v1"

AUDIT_REL_PATH = Path("eval_reports/reaper_runtime_collector_safety_audit.json")
AUDIT_REPORT_REL_PATH = Path("eval_reports/reaper_runtime_collector_safety_audit.md")
COLLECTOR_PACKAGE_REL_PATH = Path("eval_reports/plugin_semantic_validation_runtime_collector_package.json")
LUA_COLLECTOR_REL_PATH = Path("reaper_scripts/collect_plugin_semantic_validation_runtime.lua")
QUEUE_PAYLOAD_REL_PATH = Path("reaper_scripts/plugin_semantic_validation_runtime_queue.json")

REAPER_CALL_RE = re.compile(r"\breaper\.([A-Za-z_][A-Za-z0-9_]*)\s*\(")

DISALLOWED_REAPER_CALLS = {
    "ApplyNudge",
    "GetSetProjectInfo",
    "GetSetProjectInfo_String",
    "GetSetProjectNotes",
    "InsertMedia",
    "InsertMediaSection",
    "Main_OnCommand",
    "Main_SaveProject",
    "RenderFileSection",
    "SaveProject",
    "SetProjExtState",
    "SetProjectMarker",
    "SetProjectMarker2",
    "SetProjectMarker3",
    "SetRegionRenderMatrix",
    "SetTrackSendInfo_Value",
    "TrackFX_SetEQBandEnabled",
    "TrackFX_SetEQParam",
    "TrackFX_SetNamedConfigParm",
    "TrackFX_SetParam",
    "TrackFX_SetParamNormalized",
    "UpdateTimeline",
}

ALLOWED_PROBE_MUTATION_CALLS = {
    "DeleteTrack",
    "GetSetMediaTrackInfo_String",
    "InsertTrackAtIndex",
    "SetMediaTrackInfo_Value",
    "TrackFX_AddByName",
    "TrackFX_Delete",
    "Undo_BeginBlock",
    "Undo_EndBlock",
}

REQUIRED_REAPER_CALLS = {
    "DeleteTrack",
    "InsertTrackAtIndex",
    "TrackFX_AddByName",
    "TrackFX_Delete",
    "TrackFX_GetNumParams",
    "TrackFX_GetParamName",
}

REQUIRED_LUA_MARKERS = {
    "__AUTOMIX_SEMANTIC_VALIDATION_TEMP_DO_NOT_USE__": "temp_probe_track_name",
    '"B_MUTE"': "temp_probe_track_muted",
    '"B_MAINSEND"': "temp_probe_main_send_disabled",
    "safe_to_write_parameters = false": "safe_write_false",
    "writes_parameters = false": "writes_parameters_false",
    "renders_audio = false": "renders_audio_false",
    "saves_project = false": "saves_project_false",
    "creates_validation_reports = false": "creates_validation_reports_false",
}

QUEUE_FALSE_FLAGS = ["safe_to_write_parameters", "creates_validation_reports", "renders_audio", "saves_project"]


def _load_json(path: Path) -> tuple[dict[str, Any], bool]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}, False
    return (data, True) if isinstance(data, dict) else ({}, False)


def _read_text(path: Path) -> tuple[str, bool]:
    try:
        return path.read_text(encoding="utf-8"), True
    except OSError:
        return "", False


def _reaper_calls(lua_text: str) -> list[str]:
    return sorted(set(REAPER_CALL_RE.findall(lua_text)))


def _job_id(job: dict[str, Any], index: int) -> str:
    return str(job.get("job_id") or job.get("plugin_name") or f"job_{index + 1}")


def _audit_queue_payload(queue_payload: dict[str, Any], valid: bool) -> tuple[list[str], list[str], dict[str, Any]]:
    blockers: list[str] = []
    warnings: list[str] = []
    if not queue_payload or not valid:
        return ["queue_payload_missing_or_invalid_json"], warnings, {}
    if queue_payload.get("schema") != REAPER_RUNTIME_QUEUE_SCHEMA:
        blockers.append("queue_payload_schema_invalid")
    jobs = [job for job in queue_payload.get("jobs", []) or [] if isinstance(job, dict)]
    safety = queue_payload.get("safety", {}) if isinstance(queue_payload.get("safety", {}), dict) else {}
    if int(queue_payload.get("jobs_total", 0) or 0) != len(jobs):
        blockers.append("queue_jobs_total_mismatch")
    if not safety.get("temporary_muted_probe_track_only", False) and jobs:
        blockers.append("queue_temporary_muted_probe_track_only_missing")
    if not safety.get("requires_saved_test_copy_or_temporary_muted_context", False) and jobs:
        blockers.append("queue_saved_test_copy_requirement_missing")
    for flag in QUEUE_FALSE_FLAGS:
        if bool(safety.get(flag, False)):
            blockers.append(f"queue_safety_flag_not_false:{flag}")
    for index, job in enumerate(jobs):
        job_name = _job_id(job, index)
        if not job.get("requires_reaper_runtime", False):
            blockers.append(f"queue_job_requires_reaper_runtime_missing:{job_name}")
        if not job.get("requires_saved_test_copy_or_temporary_muted_context", False):
            blockers.append(f"queue_job_saved_test_copy_requirement_missing:{job_name}")
        if not str(job.get("raw_observation_output_path", "")).strip():
            blockers.append(f"queue_job_raw_observation_path_missing:{job_name}")
        disallowed = " ".join(str(item).lower() for item in job.get("disallowed_actions", []) or [])
        if "write parameters" not in disallowed:
            blockers.append(f"queue_job_write_parameter_ban_missing:{job_name}")
    blocked_jobs = queue_payload.get("blocked_queue_jobs", []) or []
    if blocked_jobs:
        warnings.append(f"blocked_queue_jobs_remain:{len(blocked_jobs)}")
    summary = {
        "schema": queue_payload.get("schema", ""),
        "jobs_total": len(jobs),
        "blocked_queue_jobs_total": len(blocked_jobs) if isinstance(blocked_jobs, list) else 0,
        "safety": safety,
    }
    return blockers, warnings, summary


def _audit_collector_package(package: dict[str, Any], valid: bool) -> tuple[list[str], list[str], dict[str, Any]]:
    blockers: list[str] = []
    warnings: list[str] = []
    if not package or not valid:
        return ["collector_package_missing_or_invalid_json"], warnings, {}
    if package.get("schema") != PLUGIN_SEMANTIC_VALIDATION_RUNTIME_COLLECTOR_PACKAGE_SCHEMA:
        blockers.append("collector_package_schema_invalid")
    if bool(package.get("safe_to_write_parameters", False)):
        blockers.append("collector_package_safe_to_write_parameters_not_false")
    if bool(package.get("creates_validation_reports", False)):
        blockers.append("collector_package_creates_validation_reports_not_false")
    if bool(package.get("ready_for_runtime_evidence_gate", False)):
        blockers.append("collector_package_ready_for_runtime_evidence_gate_must_remain_false")
    if not package.get("ready_for_reaper_runtime_collection", False):
        warnings.append("collector_package_not_ready_for_runtime_collection")
    summary = {
        "schema": package.get("schema", ""),
        "status": package.get("status", ""),
        "collector_jobs_total": package.get("collector_jobs_total", 0),
        "blocked_queue_jobs_total": package.get("blocked_queue_jobs_total", 0),
    }
    return blockers, warnings, summary


def build_reaper_runtime_collector_safety_audit(
    *,
    project_name: str,
    output_dir: Path,
    lua_collector_path: Path | None = None,
    queue_payload_path: Path | None = None,
    collector_package_path: Path | None = None,
    output_path: Path | None = None,
) -> dict[str, Any]:
    output_dir = Path(output_dir)
    lua_collector_path = lua_collector_path or output_dir / LUA_COLLECTOR_REL_PATH
    queue_payload_path = queue_payload_path or output_dir / QUEUE_PAYLOAD_REL_PATH
    collector_package_path = collector_package_path or output_dir / COLLECTOR_PACKAGE_REL_PATH

    blockers: list[str] = []
    warnings: list[str] = []

    lua_text, lua_readable = _read_text(lua_collector_path)
    if not lua_collector_path.exists():
        blockers.append("lua_collector_missing")
    elif not lua_readable:
        blockers.append("lua_collector_unreadable")

    calls = _reaper_calls(lua_text)
    disallowed_calls = sorted(set(calls) & DISALLOWED_REAPER_CALLS)
    blockers.extend(f"lua_disallowed_reaper_call:{call}" for call in disallowed_calls)
    missing_calls = sorted(REQUIRED_REAPER_CALLS - set(calls)) if lua_text else sorted(REQUIRED_REAPER_CALLS)
    blockers.extend(f"lua_required_reaper_call_missing:{call}" for call in missing_calls)
    missing_markers = [label for marker, label in REQUIRED_LUA_MARKERS.items() if marker not in lua_text]
    blockers.extend(f"lua_required_marker_missing:{label}" for label in missing_markers)
    allowed_probe_mutations = sorted(set(calls) & ALLOWED_PROBE_MUTATION_CALLS)
    if allowed_probe_mutations:
        warnings.append("temporary_probe_track_mutation_detected")
    if "io.open" in lua_text:
        warnings.append("collector_writes_raw_observation_files")

    queue_payload, queue_valid = _load_json(queue_payload_path)
    queue_blockers, queue_warnings, queue_summary = _audit_queue_payload(queue_payload, queue_valid)
    blockers.extend(queue_blockers)
    warnings.extend(queue_warnings)

    collector_package, package_valid = _load_json(collector_package_path)
    package_blockers, package_warnings, package_summary = _audit_collector_package(collector_package, package_valid)
    blockers.extend(package_blockers)
    warnings.extend(package_warnings)

    unique_blockers = sorted(set(blockers))
    unique_warnings = sorted(set(warnings))
    passed = not unique_blockers
    audit = {
        "schema": REAPER_RUNTIME_COLLECTOR_SAFETY_AUDIT_SCHEMA,
        "project_name": project_name,
        "created_at": now_utc(),
        "output_dir": str(output_dir),
        "lua_collector_path": str(lua_collector_path),
        "queue_payload_path": str(queue_payload_path),
        "collector_package_path": str(collector_package_path),
        "status": "collector_safety_passed" if passed else "collector_safety_blocked",
        "passed": passed,
        "safe_for_operator_runtime_collection": bool(passed and queue_summary.get("jobs_total", 0)),
        "reaper_calls": calls,
        "disallowed_reaper_calls": disallowed_calls,
        "allowed_probe_mutation_calls": allowed_probe_mutations,
        "mutation_model": {
            "in_memory_temporary_probe_track_mutation": bool(allowed_probe_mutations),
            "requires_saved_test_copy_or_temporary_muted_context": True,
            "writes_parameters": False,
            "renders_audio": False,
            "saves_project": False,
            "creates_validation_reports": False,
            "approves_audio_delivery": False,
        },
        "queue_payload_summary": queue_summary,
        "collector_package_summary": package_summary,
        "blockers": unique_blockers,
        "warnings": unique_warnings,
        "limits": [
            "This is a static safety audit of the generated collector package.",
            "A passing audit does not prove plugin semantic write safety or audio quality.",
            "The collector still requires a saved test copy or temporary muted REAPER context because it creates and removes a probe track in memory.",
            "The collector writes raw observation JSON only; raw observations are not validation reports.",
        ],
    }
    target = output_path or output_dir / AUDIT_REL_PATH
    write_json(target, audit)
    write_reaper_runtime_collector_safety_audit_report(audit, output_dir)
    return audit


def write_reaper_runtime_collector_safety_audit_report(audit: dict[str, Any], output_dir: Path) -> Path:
    mutation = audit.get("mutation_model", {}) if isinstance(audit.get("mutation_model", {}), dict) else {}
    lines = [
        "# REAPER Runtime Collector Safety Audit",
        "",
        f"- Project: `{audit.get('project_name')}`",
        f"- Created UTC: `{audit.get('created_at')}`",
        f"- Status: `{audit.get('status')}`",
        f"- Passed: `{audit.get('passed')}`",
        f"- Safe for operator runtime collection: `{audit.get('safe_for_operator_runtime_collection')}`",
        f"- In-memory temporary probe mutation: `{mutation.get('in_memory_temporary_probe_track_mutation')}`",
        f"- Writes parameters: `{mutation.get('writes_parameters')}`",
        f"- Renders audio: `{mutation.get('renders_audio')}`",
        f"- Saves project: `{mutation.get('saves_project')}`",
        "",
        "This audit is static. It does not run REAPER or approve semantic parameter writes.",
        "",
        "## Blockers",
        "",
    ]
    lines.extend([f"- `{item}`" for item in audit.get("blockers", [])] or ["- none"])
    lines.extend(["", "## Warnings", ""])
    lines.extend([f"- `{item}`" for item in audit.get("warnings", [])] or ["- none"])
    lines.extend(["", "## REAPER Calls", ""])
    lines.extend([f"- `{item}`" for item in audit.get("reaper_calls", [])] or ["- none"])
    lines.extend(["", "## Limits", ""])
    lines.extend([f"- {item}" for item in audit.get("limits", [])])
    path = Path(output_dir) / AUDIT_REPORT_REL_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return path

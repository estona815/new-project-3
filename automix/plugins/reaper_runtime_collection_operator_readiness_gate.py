from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from automix.plugins.plugin_adapter_schema import now_utc, write_json


REAPER_RUNTIME_COLLECTION_OPERATOR_READINESS_SCHEMA = "automix-reaper-runtime-collection-operator-readiness-v1"

GATE_REL_PATH = Path("eval_reports/reaper_runtime_collection_operator_readiness.json")
GATE_REPORT_REL_PATH = Path("eval_reports/reaper_runtime_collection_operator_readiness.md")

LOCAL_DEVICE_QC_REL_PATH = Path("eval_reports/local_device_qc.json")
COLLECTOR_PACKAGE_REL_PATH = Path("eval_reports/plugin_semantic_validation_runtime_collector_package.json")
SAFETY_AUDIT_REL_PATH = Path("eval_reports/reaper_runtime_collector_safety_audit.json")
AVAILABILITY_DECISION_REL_PATH = Path("eval_reports/plugin_availability_decision_gate.json")
QUEUE_PAYLOAD_REL_PATH = Path("reaper_scripts/plugin_semantic_validation_runtime_queue.json")


def _load_json(path: Path) -> tuple[dict[str, Any], bool]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}, False
    return (data, True) if isinstance(data, dict) else ({}, False)


def _as_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if value is None:
        return []
    return [value]


def _resolve_path(value: Any, output_dir: Path) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    path = Path(text)
    if path.is_absolute():
        return str(path)
    if path.parts and path.parts[0] == output_dir.name:
        return str(output_dir.parent / path)
    return str(output_dir / path)


def _unique_strings(values: list[Any]) -> list[str]:
    return sorted({str(item) for item in values if str(item).strip()})


def build_reaper_runtime_collection_operator_readiness_gate(
    *,
    project_name: str,
    output_dir: Path,
    local_device_qc_path: Path | None = None,
    collector_package_path: Path | None = None,
    safety_audit_path: Path | None = None,
    availability_decision_path: Path | None = None,
    queue_payload_path: Path | None = None,
    output_path: Path | None = None,
) -> dict[str, Any]:
    output_dir = Path(output_dir)
    local_device_qc_path = local_device_qc_path or output_dir / LOCAL_DEVICE_QC_REL_PATH
    collector_package_path = collector_package_path or output_dir / COLLECTOR_PACKAGE_REL_PATH
    safety_audit_path = safety_audit_path or output_dir / SAFETY_AUDIT_REL_PATH
    availability_decision_path = availability_decision_path or output_dir / AVAILABILITY_DECISION_REL_PATH
    queue_payload_path = queue_payload_path or output_dir / QUEUE_PAYLOAD_REL_PATH

    local_qc, local_qc_valid = _load_json(local_device_qc_path)
    collector_package, collector_valid = _load_json(collector_package_path)
    safety_audit, safety_valid = _load_json(safety_audit_path)
    availability_decision, availability_valid = _load_json(availability_decision_path)
    queue_payload, queue_valid = _load_json(queue_payload_path)

    blockers: list[str] = []
    warnings: list[str] = []
    review_items: list[str] = []

    if not local_qc or not local_qc_valid:
        blockers.append("local_device_qc_missing_or_invalid")
    local_readiness = local_qc.get("readiness", {}) if isinstance(local_qc.get("readiness", {}), dict) else {}
    if not local_readiness.get("local_device_qc_ready", False):
        blockers.append("local_device_qc_not_ready")
    if not local_readiness.get("ready_for_reaper_runtime_collection", False):
        blockers.append("local_device_qc_runtime_collection_not_ready")

    if not collector_package or not collector_valid:
        blockers.append("runtime_collector_package_missing_or_invalid")
    if not collector_package.get("ready_for_reaper_runtime_collection", False):
        blockers.append("runtime_collector_package_not_ready")
    if collector_package.get("safe_to_write_parameters", False):
        blockers.append("collector_package_safe_to_write_parameters_must_be_false")
    if collector_package.get("creates_validation_reports", False):
        blockers.append("collector_package_creates_validation_reports_must_be_false")
    if not collector_package.get("requires_collector_safety_audit", False):
        blockers.append("collector_package_does_not_require_safety_audit")

    if not safety_audit or not safety_valid:
        blockers.append("collector_safety_audit_missing_or_invalid")
    if not safety_audit.get("passed", False):
        blockers.append("collector_safety_audit_not_passed")
    if not safety_audit.get("safe_for_operator_runtime_collection", False):
        blockers.append("collector_safety_audit_not_safe_for_operator_runtime_collection")
    if safety_audit.get("disallowed_reaper_calls"):
        blockers.append("collector_safety_audit_disallowed_reaper_calls_present")

    if not queue_payload or not queue_valid:
        blockers.append("runtime_queue_payload_missing_or_invalid")
    queue_jobs = [job for job in queue_payload.get("jobs", []) or [] if isinstance(job, dict)]
    if not queue_jobs:
        blockers.append("runtime_queue_has_no_collectable_jobs")

    collector_jobs = [job for job in collector_package.get("collector_jobs", []) or [] if isinstance(job, dict)]
    collector_jobs_total = len(collector_jobs)
    queue_jobs_total = len(queue_jobs)
    blocked_queue_jobs = [job for job in collector_package.get("blocked_queue_jobs", []) or [] if isinstance(job, dict)]
    blocked_queue_jobs_total = len(blocked_queue_jobs)
    if collector_jobs_total != queue_jobs_total and (collector_jobs_total or queue_jobs_total):
        blockers.append("collector_job_count_mismatch_with_queue_payload")

    availability_missing_decisions = []
    availability_required_total = 0
    availability_ready = False
    if availability_valid and availability_decision:
        availability_missing_decisions = _unique_strings(_as_list(availability_decision.get("missing_decisions", [])))
        availability_required_total = int(availability_decision.get("required_decisions_total", 0) or 0)
        availability_ready = bool(availability_decision.get("availability_decisions_ready", False))
    elif blocked_queue_jobs_total:
        warnings.append("availability_decision_gate_missing_while_queue_jobs_blocked")

    if blocked_queue_jobs_total:
        warnings.append(f"complete_operator_collection_blocked_by_queue_jobs:{blocked_queue_jobs_total}")
        review_items.extend(f"blocked_queue_job:{job.get('plugin_name', job.get('job_id', 'unknown'))}" for job in blocked_queue_jobs)
    if availability_missing_decisions:
        warnings.append(f"availability_operator_decisions_missing:{len(availability_missing_decisions)}")
        review_items.extend(f"availability_decision_missing:{item}" for item in availability_missing_decisions)
    if availability_required_total and not availability_ready:
        warnings.append("availability_decisions_not_ready_for_complete_collection")

    expected_observation_paths = [
        _resolve_path(job.get("raw_observation_output_path", ""), output_dir)
        for job in collector_jobs
        if str(job.get("raw_observation_output_path", "")).strip()
    ]
    missing_observation_paths = [
        str(job.get("job_id", job.get("plugin_name", "unknown")))
        for job in collector_jobs
        if not str(job.get("raw_observation_output_path", "")).strip()
    ]
    if missing_observation_paths:
        blockers.extend(f"collector_job_raw_observation_path_missing:{item}" for item in missing_observation_paths)

    partial_ready = bool(not blockers and collector_jobs_total > 0)
    complete_ready = bool(
        partial_ready
        and blocked_queue_jobs_total == 0
        and not availability_missing_decisions
        and (availability_ready or availability_required_total == 0)
    )
    if partial_ready and not complete_ready:
        status = "partial_operator_runtime_collection_ready"
    elif complete_ready:
        status = "complete_operator_runtime_collection_ready"
    else:
        status = "operator_runtime_collection_blocked"

    gate = {
        "schema": REAPER_RUNTIME_COLLECTION_OPERATOR_READINESS_SCHEMA,
        "project_name": project_name,
        "created_at": now_utc(),
        "output_dir": str(output_dir),
        "status": status,
        "passed": partial_ready,
        "ready_for_partial_operator_runtime_collection": partial_ready,
        "ready_for_complete_operator_runtime_collection": complete_ready,
        "safe_to_run_lua_collector": partial_ready,
        "safe_to_write_parameters": False,
        "creates_validation_reports": False,
        "renders_audio": False,
        "saves_project": False,
        "requires_reaper_runtime": bool(collector_jobs_total),
        "requires_saved_test_copy_or_temporary_muted_context": True,
        "requires_operator_review": True,
        "collector_jobs_total": collector_jobs_total,
        "queue_jobs_total": queue_jobs_total,
        "blocked_queue_jobs_total": blocked_queue_jobs_total,
        "availability_required_decisions_total": availability_required_total,
        "availability_missing_decisions": availability_missing_decisions,
        "expected_observation_paths": expected_observation_paths,
        "lua_collector_script_path": _resolve_path(collector_package.get("lua_collector_script_path", ""), output_dir),
        "queue_payload_path": str(queue_payload_path),
        "operator_runbook_path": _resolve_path(collector_package.get("operator_runbook_path", ""), output_dir),
        "safety_audit_path": str(safety_audit_path),
        "local_device_qc_path": str(local_device_qc_path),
        "collector_package_path": str(collector_package_path),
        "availability_decision_path": str(availability_decision_path),
        "blockers": sorted(set(blockers)),
        "warnings": sorted(set(warnings)),
        "review_items": sorted(set(review_items)),
        "next_operator_actions": [
            "Open a saved REAPER test copy or a temporary muted test context before running the Lua collector.",
            "Run the Lua collector only for raw plugin parameter observations.",
            "Do not promote raw observations to validation reports without manual semantic review.",
            "Resolve missing availability decisions before claiming complete runtime collection readiness.",
        ],
        "limits": [
            "This gate does not open REAPER, run the collector, write parameters, render, save, or approve delivery.",
            "Partial readiness means collectable jobs can be observed; it does not resolve unavailable plugin decisions.",
            "Raw observations are not plugin semantic validation reports.",
            "A passing gate does not prove audio quality or delivery readiness.",
        ],
    }
    target = output_path or output_dir / GATE_REL_PATH
    write_json(target, gate)
    write_reaper_runtime_collection_operator_readiness_report(gate, output_dir)
    return gate


def write_reaper_runtime_collection_operator_readiness_report(gate: dict[str, Any], output_dir: Path) -> Path:
    lines = [
        "# REAPER Runtime Collection Operator Readiness",
        "",
        f"- Project: `{gate.get('project_name')}`",
        f"- Created UTC: `{gate.get('created_at')}`",
        f"- Status: `{gate.get('status')}`",
        f"- Partial collection ready: `{gate.get('ready_for_partial_operator_runtime_collection')}`",
        f"- Complete collection ready: `{gate.get('ready_for_complete_operator_runtime_collection')}`",
        f"- Safe to run Lua collector: `{gate.get('safe_to_run_lua_collector')}`",
        f"- Safe to write parameters: `{gate.get('safe_to_write_parameters')}`",
        f"- Collector jobs: `{gate.get('collector_jobs_total')}`",
        f"- Blocked queue jobs: `{gate.get('blocked_queue_jobs_total')}`",
        "",
        "This gate is pre-run only. It does not open REAPER or execute the collector.",
        "",
        "## Blockers",
        "",
    ]
    lines.extend([f"- `{item}`" for item in gate.get("blockers", [])] or ["- none"])
    lines.extend(["", "## Warnings", ""])
    lines.extend([f"- `{item}`" for item in gate.get("warnings", [])] or ["- none"])
    lines.extend(["", "## Review Items", ""])
    lines.extend([f"- `{item}`" for item in gate.get("review_items", [])] or ["- none"])
    lines.extend(["", "## Required Paths", ""])
    for key in ["lua_collector_script_path", "operator_runbook_path", "safety_audit_path", "local_device_qc_path"]:
        lines.append(f"- `{key}`: `{gate.get(key, '')}`")
    lines.extend(["", "## Expected Observation Outputs", ""])
    lines.extend([f"- `{item}`" for item in gate.get("expected_observation_paths", [])] or ["- none"])
    lines.extend(["", "## Next Operator Actions", ""])
    lines.extend([f"- {item}" for item in gate.get("next_operator_actions", [])])
    lines.extend(["", "## Limits", ""])
    lines.extend([f"- {item}" for item in gate.get("limits", [])])
    path = Path(output_dir) / GATE_REPORT_REL_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return path

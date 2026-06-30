from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from automix.plugins.plugin_adapter_schema import now_utc, write_json
from automix.plugins.plugin_semantic_validation_runtime_collection_package import (
    PLUGIN_PARAMETER_VALIDATION_REPORT_TEMPLATE_SCHEMA,
    PLUGIN_SEMANTIC_VALIDATION_RUNTIME_COLLECTION_PACKAGE_SCHEMA,
    RUNTIME_MANIFEST_SCHEMA,
)
from automix.plugins.plugin_semantic_validation_runtime_collector_package import (
    PLUGIN_SEMANTIC_VALIDATION_RUNTIME_COLLECTOR_PACKAGE_SCHEMA,
    REAPER_RUNTIME_QUEUE_SCHEMA,
    RUNTIME_OBSERVATION_TEMPLATE_SCHEMA,
)


PLUGIN_SEMANTIC_VALIDATION_RUNTIME_HANDOFF_PACKET_GATE_SCHEMA = (
    "automix-plugin-semantic-validation-runtime-handoff-packet-gate-v1"
)

GATE_REL_PATH = Path("eval_reports/plugin_semantic_validation_runtime_handoff_packet_gate.json")
GATE_REPORT_REL_PATH = Path("eval_reports/plugin_semantic_validation_runtime_handoff_packet_gate.md")
REQUIRED_OPERATOR_FILE_MISSING_PREFIX = "required_operator_file_missing"

LOCAL_DEVICE_QC_REL_PATH = Path("eval_reports/local_device_qc.json")
QUEUE_REL_PATH = Path("eval_reports/plugin_semantic_validation_queue.json")
COLLECTION_PACKAGE_REL_PATH = Path("eval_reports/plugin_semantic_validation_runtime_collection_package.json")
COLLECTOR_PACKAGE_REL_PATH = Path("eval_reports/plugin_semantic_validation_runtime_collector_package.json")
SAFETY_AUDIT_REL_PATH = Path("eval_reports/reaper_runtime_collector_safety_audit.json")
OPERATOR_READINESS_REL_PATH = Path("eval_reports/reaper_runtime_collection_operator_readiness.json")
AVAILABILITY_DECISION_REL_PATH = Path("eval_reports/plugin_availability_decision_gate.json")
RUNTIME_EVIDENCE_GATE_REL_PATH = Path("eval_reports/plugin_semantic_validation_runtime_evidence_gate.json")


def _load_json(path: Path) -> tuple[dict[str, Any], bool]:
    try:
        loaded = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return {}, False
    return (loaded, True) if isinstance(loaded, dict) else ({}, False)


def _resolve_path(value: Any, output_dir: Path) -> Path:
    text = str(value or "").strip()
    if not text:
        return Path("")
    path = Path(text)
    if path.is_absolute():
        return path
    if path.parts and path.parts[0] == output_dir.name:
        return output_dir.parent / path
    return output_dir / path


def _norm_path(value: Any, output_dir: Path) -> str:
    path = _resolve_path(value, output_dir)
    return str(path.resolve()).replace("\\", "/") if str(value or "").strip() else ""


def _load_artifact(path: Path, expected_schema: str | None = None) -> dict[str, Any]:
    if expected_schema is None:
        return {
            "path": str(path),
            "exists": path.exists(),
            "json_valid": None,
            "schema": "",
            "blockers": [] if path.exists() else ["missing"],
            "data": {},
        }
    data, valid = _load_json(path) if path.exists() else ({}, False)
    blockers: list[str] = []
    if not path.exists():
        blockers.append("missing")
    elif not valid:
        blockers.append("invalid_json")
    elif expected_schema and data.get("schema") != expected_schema:
        blockers.append(f"schema_mismatch:{data.get('schema', '')}")
    return {
        "path": str(path),
        "exists": path.exists(),
        "json_valid": bool(valid and data),
        "schema": data.get("schema", ""),
        "blockers": blockers,
        "data": data,
    }


def _job_lookup(items: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for item in items:
        job_id = str(item.get("job_id", "")).strip()
        if job_id:
            out[job_id] = item
    return out


def _target_report_under_analysis(path_text: str, output_dir: Path) -> bool:
    resolved = _resolve_path(path_text, output_dir).resolve()
    normalized = str(resolved).replace("\\", "/")
    return "/analysis_reports/plugin_parameter_validation_" in normalized and normalized.endswith(".json")


def _template_result(*, job_id: str, template_path: Path) -> dict[str, Any]:
    artifact = _load_artifact(template_path, PLUGIN_PARAMETER_VALIDATION_REPORT_TEMPLATE_SCHEMA)
    data = artifact.pop("data", {})
    blockers = list(artifact.get("blockers", []))
    if data:
        if data.get("job_id") != job_id:
            blockers.append("template_job_id_mismatch")
        if data.get("safe_for_automix", True):
            blockers.append("template_safe_for_automix_must_be_false")
        if data.get("no_fake_success", True):
            blockers.append("template_no_fake_success_must_be_false")
        if data.get("status") != "template_not_runtime_observed":
            blockers.append("template_status_must_not_claim_runtime_observed")
    return {
        **artifact,
        "blockers": sorted(set(blockers)),
        "safe_for_automix": bool(data.get("safe_for_automix", False)),
        "no_fake_success": bool(data.get("no_fake_success", False)),
        "status": data.get("status", ""),
    }


def _job_result(
    *,
    job_id: str,
    queue_job: dict[str, Any] | None,
    collection_job: dict[str, Any] | None,
    collector_job: dict[str, Any] | None,
    output_dir: Path,
) -> dict[str, Any]:
    blockers: list[str] = []
    warnings: list[str] = []
    if not queue_job:
        blockers.append("queue_job_missing")
        queue_job = {}
    if not collection_job:
        blockers.append("collection_job_missing")
        collection_job = {}
    if not collector_job:
        blockers.append("collector_job_missing")
        collector_job = {}

    queue_target = _norm_path(queue_job.get("target_report_path", ""), output_dir)
    collection_target = _norm_path(collection_job.get("target_report_path", ""), output_dir)
    collector_target = _norm_path(collector_job.get("target_report_path", ""), output_dir)
    targets = sorted({item for item in [queue_target, collection_target, collector_target] if item})
    if len(targets) > 1:
        blockers.append("target_report_path_mismatch")
    target_report_path = targets[0] if targets else ""
    if not target_report_path:
        blockers.append("target_report_path_missing")
    elif not _target_report_under_analysis(target_report_path, output_dir):
        blockers.append("target_report_path_not_plugin_validation_analysis_report")

    observation_path = _norm_path(collector_job.get("raw_observation_output_path", ""), output_dir)
    if not observation_path:
        blockers.append("raw_observation_output_path_missing")

    if not collection_job.get("requires_temporary_muted_test_context", False):
        blockers.append("collection_job_missing_temporary_muted_context_requirement")
    if not collector_job.get("requires_saved_test_copy_or_temporary_muted_context", False):
        blockers.append("collector_job_missing_saved_copy_or_muted_context_requirement")

    template_path = _resolve_path(collection_job.get("report_template_path", ""), output_dir)
    template = _template_result(job_id=job_id, template_path=template_path) if str(template_path) else {
        "path": "",
        "exists": False,
        "json_valid": False,
        "schema": "",
        "status": "",
        "safe_for_automix": False,
        "no_fake_success": False,
        "blockers": ["missing"],
    }
    blockers.extend(f"report_template_{item}" for item in template.get("blockers", []))

    if target_report_path and Path(target_report_path).exists():
        warnings.append("target_validation_report_already_exists_rerun_runtime_evidence_gate")
    if observation_path and Path(observation_path).exists():
        warnings.append("raw_observation_already_exists_review_for_staleness")

    return {
        "job_id": job_id,
        "plugin_name": queue_job.get("plugin_name") or collection_job.get("plugin_name") or collector_job.get("plugin_name", ""),
        "target_report_path": target_report_path,
        "raw_observation_output_path": observation_path,
        "report_template": template,
        "present_in_queue": bool(queue_job),
        "present_in_collection_package": bool(collection_job),
        "present_in_collector_package": bool(collector_job),
        "safe_to_write_parameters": False,
        "creates_validation_reports": False,
        "blockers": sorted(set(blockers)),
        "warnings": sorted(set(warnings)),
        "status": "handoff_job_ready" if not blockers else "handoff_job_blocked",
    }


def build_plugin_semantic_validation_runtime_handoff_packet_gate(
    *,
    project_name: str,
    output_dir: Path,
    local_device_qc_path: Path | None = None,
    queue_path: Path | None = None,
    collection_package_path: Path | None = None,
    collector_package_path: Path | None = None,
    safety_audit_path: Path | None = None,
    operator_readiness_path: Path | None = None,
    availability_decision_path: Path | None = None,
    runtime_evidence_gate_path: Path | None = None,
    output_path: Path | None = None,
) -> dict[str, Any]:
    output_dir = Path(output_dir)
    local_device_qc_path = local_device_qc_path or output_dir / LOCAL_DEVICE_QC_REL_PATH
    queue_path = queue_path or output_dir / QUEUE_REL_PATH
    collection_package_path = collection_package_path or output_dir / COLLECTION_PACKAGE_REL_PATH
    collector_package_path = collector_package_path or output_dir / COLLECTOR_PACKAGE_REL_PATH
    safety_audit_path = safety_audit_path or output_dir / SAFETY_AUDIT_REL_PATH
    operator_readiness_path = operator_readiness_path or output_dir / OPERATOR_READINESS_REL_PATH
    availability_decision_path = availability_decision_path or output_dir / AVAILABILITY_DECISION_REL_PATH
    runtime_evidence_gate_path = runtime_evidence_gate_path or output_dir / RUNTIME_EVIDENCE_GATE_REL_PATH

    local_qc, local_valid = _load_json(local_device_qc_path) if local_device_qc_path.exists() else ({}, False)
    queue, queue_valid = _load_json(queue_path) if queue_path.exists() else ({}, False)
    collection_package, collection_valid = (
        _load_json(collection_package_path) if collection_package_path.exists() else ({}, False)
    )
    collector_package, collector_valid = _load_json(collector_package_path) if collector_package_path.exists() else ({}, False)
    safety_audit, safety_valid = _load_json(safety_audit_path) if safety_audit_path.exists() else ({}, False)
    operator_readiness, operator_valid = (
        _load_json(operator_readiness_path) if operator_readiness_path.exists() else ({}, False)
    )
    availability_decision, availability_valid = (
        _load_json(availability_decision_path) if availability_decision_path.exists() else ({}, False)
    )
    runtime_evidence_gate, runtime_evidence_valid = (
        _load_json(runtime_evidence_gate_path) if runtime_evidence_gate_path.exists() else ({}, False)
    )

    blockers: list[str] = []
    warnings: list[str] = []
    review_items: list[str] = []

    local_readiness = local_qc.get("readiness", {}) if isinstance(local_qc.get("readiness", {}), dict) else {}
    if not local_qc or not local_valid:
        blockers.append("local_device_qc_missing_or_invalid")
    if local_qc and not local_readiness.get("local_device_qc_ready", False):
        blockers.append("local_device_qc_not_ready")
    if local_qc and not local_readiness.get("ready_for_reaper_runtime_collection", False):
        blockers.append("local_device_qc_runtime_collection_not_ready")

    if not queue or not queue_valid or queue.get("schema") != "automix-plugin-semantic-validation-queue-v1":
        blockers.append("plugin_semantic_validation_queue_missing_or_invalid")
        queue = queue if isinstance(queue, dict) else {}
    if not collection_package or not collection_valid or collection_package.get("schema") != PLUGIN_SEMANTIC_VALIDATION_RUNTIME_COLLECTION_PACKAGE_SCHEMA:
        blockers.append("runtime_collection_package_missing_or_invalid")
        collection_package = collection_package if isinstance(collection_package, dict) else {}
    if not collector_package or not collector_valid or collector_package.get("schema") != PLUGIN_SEMANTIC_VALIDATION_RUNTIME_COLLECTOR_PACKAGE_SCHEMA:
        blockers.append("runtime_collector_package_missing_or_invalid")
        collector_package = collector_package if isinstance(collector_package, dict) else {}
    if not safety_audit or not safety_valid:
        blockers.append("collector_safety_audit_missing_or_invalid")
    if not operator_readiness or not operator_valid:
        blockers.append("operator_readiness_gate_missing_or_invalid")

    if collection_package and not collection_package.get("ready_for_runtime_collection", False):
        blockers.append("runtime_collection_package_not_ready")
    if collector_package and not collector_package.get("ready_for_reaper_runtime_collection", False):
        blockers.append("runtime_collector_package_not_ready")
    if collector_package and not collector_package.get("requires_collector_safety_audit", False):
        blockers.append("runtime_collector_package_does_not_require_safety_audit")
    if safety_audit and not safety_audit.get("passed", False):
        blockers.append("collector_safety_audit_not_passed")
    if safety_audit and not safety_audit.get("safe_for_operator_runtime_collection", False):
        blockers.append("collector_safety_audit_not_safe_for_operator_runtime_collection")
    if operator_readiness and not operator_readiness.get("ready_for_partial_operator_runtime_collection", False):
        blockers.append("operator_readiness_not_partial_ready")

    for label, report in [
        ("collection_package", collection_package),
        ("collector_package", collector_package),
        ("operator_readiness", operator_readiness),
    ]:
        if report.get("safe_to_write_parameters", False):
            blockers.append(f"{label}_safe_to_write_parameters_must_be_false")
        if report.get("creates_validation_reports", False):
            blockers.append(f"{label}_creates_validation_reports_must_be_false")
        if report.get("renders_audio", False):
            blockers.append(f"{label}_renders_audio_must_be_false")
        if report.get("saves_project", False):
            blockers.append(f"{label}_saves_project_must_be_false")

    required_artifacts: list[dict[str, Any]] = []
    for key, expected_schema in [
        ("lua_collector_script_path", None),
        ("operator_runbook_path", None),
        ("queue_payload_path", REAPER_RUNTIME_QUEUE_SCHEMA),
        ("observation_template_path", RUNTIME_OBSERVATION_TEMPLATE_SCHEMA),
        ("manifest_candidate_path", RUNTIME_MANIFEST_SCHEMA),
        ("checklist_path", None),
    ]:
        if key in {"lua_collector_script_path", "operator_runbook_path", "queue_payload_path", "observation_template_path"}:
            source = collector_package
        else:
            source = collection_package
        raw_path = source.get(key, "")
        path = _resolve_path(raw_path, output_dir)
        artifact = _load_artifact(path, expected_schema) if str(raw_path or "").strip() else {
            "path": "",
            "exists": False,
            "json_valid": False,
            "schema": "",
            "blockers": ["missing"],
            "data": {},
        }
        data = artifact.pop("data", {})
        if key == "manifest_candidate_path" and data:
            if not data.get("candidate_only", False):
                artifact["blockers"].append("manifest_candidate_only_flag_missing")
            if data.get("operator_ready_to_run", False):
                artifact["blockers"].append("manifest_candidate_must_not_be_operator_ready")
            if data.get("safe_to_write_parameters", False):
                artifact["blockers"].append("manifest_candidate_safe_to_write_parameters_must_be_false")
        for blocker in artifact.get("blockers", []):
            if blocker == "missing":
                blockers.append(f"{REQUIRED_OPERATOR_FILE_MISSING_PREFIX}:{key}")
            else:
                blockers.append(f"required_operator_file_{blocker}:{key}")
        required_artifacts.append({"id": key, **artifact})

    queue_jobs = [job for job in queue.get("queue_jobs", []) or [] if isinstance(job, dict)]
    collection_jobs = [job for job in collection_package.get("collection_jobs", []) or [] if isinstance(job, dict)]
    collector_jobs = [job for job in collector_package.get("collector_jobs", []) or [] if isinstance(job, dict)]
    blocked_queue_jobs = [job for job in queue.get("blocked_jobs", []) or [] if isinstance(job, dict)]
    blocked_queue_jobs_total = len(blocked_queue_jobs)
    if blocked_queue_jobs_total:
        warnings.append(f"blocked_unavailable_queue_jobs_remain:{blocked_queue_jobs_total}")
        review_items.extend(f"blocked_queue_job:{job.get('plugin_name', job.get('job_id', 'unknown'))}" for job in blocked_queue_jobs)

    availability_missing_decisions: list[str] = []
    availability_ready = False
    if availability_decision and availability_valid:
        availability_missing_decisions = [str(item) for item in availability_decision.get("missing_decisions", []) or []]
        availability_ready = bool(availability_decision.get("availability_decisions_ready", False))
    elif blocked_queue_jobs_total:
        warnings.append("availability_decision_gate_missing_while_queue_jobs_blocked")
    if availability_missing_decisions:
        warnings.append(f"availability_operator_decisions_missing:{len(availability_missing_decisions)}")
        review_items.extend(f"availability_decision_missing:{item}" for item in availability_missing_decisions)

    queue_by_id = _job_lookup(queue_jobs)
    collection_by_id = _job_lookup(collection_jobs)
    collector_by_id = _job_lookup(collector_jobs)
    all_job_ids = sorted(set(queue_by_id) | set(collection_by_id) | set(collector_by_id))
    job_results = [
        _job_result(
            job_id=job_id,
            queue_job=queue_by_id.get(job_id),
            collection_job=collection_by_id.get(job_id),
            collector_job=collector_by_id.get(job_id),
            output_dir=output_dir,
        )
        for job_id in all_job_ids
    ]
    for item in job_results:
        blockers.extend(f"{item['job_id']}:{blocker}" for blocker in item.get("blockers", []))
        warnings.extend(f"{item['job_id']}:{warning}" for warning in item.get("warnings", []))

    if not all_job_ids:
        blockers.append("runtime_handoff_packet_has_no_collectable_jobs")
    if len(queue_jobs) != len(collection_jobs) and (queue_jobs or collection_jobs):
        blockers.append("queue_job_count_mismatch_with_collection_package")
    if len(queue_jobs) != len(collector_jobs) and (queue_jobs or collector_jobs):
        blockers.append("queue_job_count_mismatch_with_collector_package")

    runtime_evidence_ready_seen = bool(runtime_evidence_gate.get("runtime_evidence_ready", False)) if runtime_evidence_valid else False
    if runtime_evidence_ready_seen:
        warnings.append("runtime_evidence_ready_already_seen_rerun_semantic_validation_gate")

    job_ready_total = sum(1 for item in job_results if item.get("status") == "handoff_job_ready")
    unique_blockers = sorted(set(blockers))
    unique_warnings = sorted(set(warnings))
    partial_ready = bool(not unique_blockers and job_results and job_ready_total == len(job_results))
    complete_ready = bool(
        partial_ready
        and operator_readiness.get("ready_for_complete_operator_runtime_collection", False)
        and blocked_queue_jobs_total == 0
        and not availability_missing_decisions
        and (availability_ready or not availability_decision.get("required_decisions_total", 0))
    )
    if complete_ready:
        status = "complete_operator_runtime_handoff_packet_ready"
    elif partial_ready:
        status = "partial_operator_runtime_handoff_packet_ready"
    else:
        status = "operator_runtime_handoff_packet_blocked"

    gate = {
        "schema": PLUGIN_SEMANTIC_VALIDATION_RUNTIME_HANDOFF_PACKET_GATE_SCHEMA,
        "project_name": project_name,
        "created_at": now_utc(),
        "output_dir": str(output_dir),
        "status": status,
        "passed": partial_ready,
        "readiness": {
            "operator_runtime_handoff_packet_ready": partial_ready,
            "complete_operator_runtime_handoff_packet_ready": complete_ready,
            "safe_to_run_lua_collector": partial_ready,
            "safe_to_write_parameters": False,
            "creates_validation_reports": False,
            "runtime_evidence_ready": runtime_evidence_ready_seen,
            "safe_to_claim_final_audio_or_delivery": False,
            "report_only": True,
        },
        "sources": {
            "local_device_qc_path": str(local_device_qc_path),
            "queue_path": str(queue_path),
            "collection_package_path": str(collection_package_path),
            "collector_package_path": str(collector_package_path),
            "safety_audit_path": str(safety_audit_path),
            "operator_readiness_path": str(operator_readiness_path),
            "availability_decision_path": str(availability_decision_path),
            "runtime_evidence_gate_path": str(runtime_evidence_gate_path),
        },
        "counts": {
            "queue_jobs_total": len(queue_jobs),
            "collection_jobs_total": len(collection_jobs),
            "collector_jobs_total": len(collector_jobs),
            "handoff_jobs_ready_total": job_ready_total,
            "blocked_queue_jobs_total": blocked_queue_jobs_total,
            "availability_missing_decisions_total": len(availability_missing_decisions),
            "required_operator_artifacts_total": len(required_artifacts),
        },
        "availability_missing_decisions": sorted(set(availability_missing_decisions)),
        "required_operator_artifacts": required_artifacts,
        "job_results": job_results,
        "blockers": unique_blockers,
        "warnings": unique_warnings,
        "review_items": sorted(set(review_items)),
        "limits": [
            "This gate does not open REAPER, execute Lua, write parameters, render, save, or approve delivery.",
            "Report templates and manifest candidates are not runtime evidence.",
            "Raw observations must be manually converted into validation reports and rerun through runtime and semantic evidence gates.",
            "A partial-ready packet may still have blocked unavailable plugin decisions.",
        ],
    }
    target = output_path or output_dir / GATE_REL_PATH
    write_json(target, gate)
    write_plugin_semantic_validation_runtime_handoff_packet_report(gate, output_dir)
    return gate


def write_plugin_semantic_validation_runtime_handoff_packet_report(gate: dict[str, Any], output_dir: Path) -> Path:
    readiness = gate.get("readiness", {})
    counts = gate.get("counts", {})
    lines = [
        "# Plugin Semantic Validation Runtime Handoff Packet Gate",
        "",
        f"- Project: `{gate.get('project_name')}`",
        f"- Created UTC: `{gate.get('created_at')}`",
        f"- Status: `{gate.get('status')}`",
        f"- Passed: `{gate.get('passed')}`",
        f"- Packet ready: `{readiness.get('operator_runtime_handoff_packet_ready')}`",
        f"- Complete packet ready: `{readiness.get('complete_operator_runtime_handoff_packet_ready')}`",
        f"- Safe to run Lua collector: `{readiness.get('safe_to_run_lua_collector')}`",
        f"- Safe to write parameters: `{readiness.get('safe_to_write_parameters')}`",
        "",
        "This report checks operator handoff packet completeness only. It does not grant parameter write safety.",
        "",
        "## Counts",
        "",
    ]
    for key, value in counts.items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(["", "## Blockers", ""])
    lines.extend([f"- `{item}`" for item in gate.get("blockers", [])] or ["- none"])
    lines.extend(["", "## Warnings", ""])
    lines.extend([f"- `{item}`" for item in gate.get("warnings", [])] or ["- none"])
    lines.extend(["", "## Required Operator Artifacts", ""])
    for item in gate.get("required_operator_artifacts", []):
        lines.append(
            f"- `{item.get('id')}` exists `{item.get('exists')}` valid `{item.get('json_valid')}` "
            f"schema `{item.get('schema')}` blockers `{item.get('blockers', [])}`"
        )
    lines.extend(["", "## Jobs", ""])
    if not gate.get("job_results"):
        lines.append("- none")
    for item in gate.get("job_results", []):
        lines.extend(
            [
                f"### {item.get('job_id')}",
                "",
                f"- Plugin: `{item.get('plugin_name')}`",
                f"- Status: `{item.get('status')}`",
                f"- Target report: `{item.get('target_report_path')}`",
                f"- Raw observation: `{item.get('raw_observation_output_path')}`",
                f"- Template: `{item.get('report_template', {}).get('path', '')}`",
                f"- Blockers: `{item.get('blockers', [])}`",
                "",
            ]
        )
    lines.extend(["## Review Items", ""])
    lines.extend([f"- `{item}`" for item in gate.get("review_items", [])] or ["- none"])
    lines.extend(["", "## Limits", ""])
    lines.extend([f"- {item}" for item in gate.get("limits", [])])
    path = Path(output_dir) / GATE_REPORT_REL_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return path

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from automix.plugins.plugin_adapter_schema import now_utc, write_json


PLUGIN_SEMANTIC_VALIDATION_RUNTIME_EVIDENCE_GATE_SCHEMA = "automix-plugin-semantic-validation-runtime-evidence-gate-v1"
PLUGIN_SEMANTIC_VALIDATION_RUNTIME_MANIFEST_SCHEMA = "automix-plugin-semantic-validation-runtime-manifest-v1"
PLUGIN_SEMANTIC_VALIDATION_RUNTIME_MANIFEST_TEMPLATE_SCHEMA = "automix-plugin-semantic-validation-runtime-manifest-template-v1"

GATE_REL_PATH = Path("eval_reports/plugin_semantic_validation_runtime_evidence_gate.json")
GATE_REPORT_REL_PATH = Path("eval_reports/plugin_semantic_validation_runtime_evidence_gate.md")
REQUEST_REL_PATH = Path("review/plugin_semantic_validation_runtime_evidence_request.md")
QUEUE_REL_PATH = Path("eval_reports/plugin_semantic_validation_queue.json")
RUNTIME_MANIFEST_REL_PATH = Path("review/plugin_semantic_validation_runtime_manifest.json")


def _load_json(path: Path) -> tuple[dict[str, Any], bool]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}, False
    return (data, True) if isinstance(data, dict) else ({}, False)


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _resolve_report_path(value: Any, output_dir: Path) -> Path:
    path = Path(str(value or ""))
    if path.is_absolute():
        return path
    if path.parts and path.parts[0] == output_dir.name:
        return output_dir.parent / path
    return output_dir / path


def _write_safe_controls(report: dict[str, Any]) -> dict[str, dict[str, Any]]:
    controls = report.get("controls", {}) if isinstance(report.get("controls", {}), dict) else {}
    safe: dict[str, dict[str, Any]] = {}
    for semantic, control in controls.items():
        if not isinstance(control, dict):
            continue
        confidence = _safe_float(control.get("confidence"), 0.0)
        if bool(control.get("validated")) and bool(control.get("write_allowed")) and confidence >= 0.85 and control.get("target_name"):
            safe[str(semantic)] = control
    return safe


def _runtime_manifest_jobs(manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    jobs: dict[str, dict[str, Any]] = {}
    for item in manifest.get("queue_jobs", []) or []:
        if not isinstance(item, dict):
            continue
        job_id = str(item.get("job_id", "")).strip()
        if job_id:
            jobs[job_id] = item
    return jobs


def _validate_report(*, job_id: str, target_report_path: str, output_dir: Path) -> dict[str, Any]:
    path = _resolve_report_path(target_report_path, output_dir)
    blockers: list[str] = []
    warnings: list[str] = []
    report, json_valid = _load_json(path)
    if not path.exists():
        blockers.append(f"runtime_validation_report_missing:{job_id}")
        json_valid = False
    elif not json_valid:
        blockers.append(f"runtime_validation_report_invalid_json:{job_id}")

    safe_controls: dict[str, dict[str, Any]] = {}
    if report:
        safe_controls = _write_safe_controls(report)
        if report.get("schema") != "automix-plugin-parameter-validation-report-v1":
            blockers.append(f"runtime_validation_report_schema_mismatch:{job_id}")
        if report.get("status") != "passed":
            blockers.append(f"runtime_validation_report_not_passed:{job_id}:{report.get('status', 'unknown')}")
        if not report.get("safe_for_automix", False):
            blockers.append(f"runtime_validation_report_not_safe_for_automix:{job_id}")
        if not report.get("no_fake_success", False):
            blockers.append(f"runtime_validation_report_no_fake_success_missing:{job_id}")
        if not safe_controls:
            blockers.append(f"runtime_validation_report_has_no_write_safe_controls:{job_id}")
        controls = report.get("controls", {}) if isinstance(report.get("controls", {}), dict) else {}
        if controls and len(safe_controls) < len(controls):
            warnings.append(f"runtime_validation_report_some_controls_remain_write_blocked:{job_id}")

    return {
        "target_report_path": str(path),
        "report_exists": path.exists(),
        "json_valid": bool(json_valid and report),
        "report_schema": report.get("schema", ""),
        "report_status": report.get("status", ""),
        "report_plugin_name": report.get("plugin_name", ""),
        "adapter_id": report.get("adapter_id", ""),
        "safe_for_automix": bool(report.get("safe_for_automix", False)),
        "no_fake_success": bool(report.get("no_fake_success", False)),
        "safe_controls": sorted(safe_controls),
        "safe_control_count": len(safe_controls),
        "blockers": sorted(set(blockers)),
        "warnings": sorted(set(warnings)),
        "passed": not blockers,
    }


def _validate_job(*, job: dict[str, Any], manifest_jobs: dict[str, dict[str, Any]], output_dir: Path) -> dict[str, Any]:
    job_id = str(job.get("job_id", "")).strip()
    manifest_job = manifest_jobs.get(job_id, {})
    blockers: list[str] = []
    if not manifest_job:
        blockers.append(f"runtime_manifest_job_missing:{job_id}")
    else:
        if not manifest_job.get("operator_acknowledged", False):
            blockers.append(f"runtime_job_operator_acknowledgement_missing:{job_id}")
        if not manifest_job.get("runtime_observed", False):
            blockers.append(f"runtime_observation_missing:{job_id}")
        if not manifest_job.get("report_written", False):
            blockers.append(f"runtime_report_not_marked_written:{job_id}")
        if not manifest_job.get("report_reaudited_by_semantic_gate", False):
            blockers.append(f"runtime_report_reaudit_missing:{job_id}")

    report_result = _validate_report(
        job_id=job_id,
        target_report_path=str(job.get("target_report_path", "")),
        output_dir=output_dir,
    )
    blockers.extend(report_result.get("blockers", []))
    return {
        "job_id": job_id,
        "plugin_name": job.get("plugin_name", ""),
        "collection_action": job.get("collection_action", ""),
        "target_report_path": report_result.get("target_report_path", ""),
        "manifest_entry_present": bool(manifest_job),
        "operator_acknowledged": bool(manifest_job.get("operator_acknowledged", False)),
        "runtime_observed": bool(manifest_job.get("runtime_observed", False)),
        "report_written": bool(manifest_job.get("report_written", False)),
        "report_reaudited_by_semantic_gate": bool(manifest_job.get("report_reaudited_by_semantic_gate", False)),
        "report_result": report_result,
        "blockers": sorted(set(blockers)),
        "warnings": sorted(set(report_result.get("warnings", []))),
        "job_status": "accepted" if not blockers else "blocked",
    }


def build_plugin_semantic_validation_runtime_evidence_gate(
    *,
    project_name: str,
    output_dir: Path,
    queue: dict[str, Any] | None = None,
    runtime_manifest: dict[str, Any] | None = None,
    queue_path: Path | None = None,
    runtime_manifest_path: Path | None = None,
    output_path: Path | None = None,
) -> dict[str, Any]:
    output_dir = Path(output_dir)
    queue_path = queue_path or output_dir / QUEUE_REL_PATH
    runtime_manifest_path = runtime_manifest_path or output_dir / RUNTIME_MANIFEST_REL_PATH
    queue_valid = True
    manifest_valid = True
    manifest_supplied = runtime_manifest is not None
    manifest_exists = runtime_manifest_path.exists()
    if queue is None:
        queue, queue_valid = _load_json(queue_path)
    if runtime_manifest is None and manifest_exists:
        runtime_manifest, manifest_valid = _load_json(runtime_manifest_path)
    runtime_manifest = runtime_manifest or {}

    blockers: list[str] = []
    warnings: list[str] = []
    if not queue or not queue_valid or queue.get("schema") != "automix-plugin-semantic-validation-queue-v1":
        blockers.append("plugin_semantic_validation_queue_missing_or_invalid")
        queue = queue if isinstance(queue, dict) else {}

    queue_jobs = [job for job in queue.get("queue_jobs", []) or [] if isinstance(job, dict)]
    blocked_queue_jobs = [job for job in queue.get("blocked_jobs", []) or [] if isinstance(job, dict)]
    if blocked_queue_jobs:
        warnings.append(f"blocked_queue_jobs_remain:{len(blocked_queue_jobs)}")

    manifest_schema = runtime_manifest.get("schema", "")
    if queue_jobs and not manifest_exists and not manifest_supplied:
        blockers.append("plugin_semantic_validation_runtime_manifest_missing")
    elif queue_jobs and manifest_exists and not manifest_valid and not runtime_manifest:
        blockers.append("plugin_semantic_validation_runtime_manifest_invalid_json")
    elif runtime_manifest:
        if manifest_schema == PLUGIN_SEMANTIC_VALIDATION_RUNTIME_MANIFEST_TEMPLATE_SCHEMA:
            blockers.append("plugin_semantic_validation_runtime_manifest_is_template")
        elif manifest_schema != PLUGIN_SEMANTIC_VALIDATION_RUNTIME_MANIFEST_SCHEMA:
            blockers.append("plugin_semantic_validation_runtime_manifest_schema_invalid")

    manifest_jobs = _runtime_manifest_jobs(runtime_manifest) if runtime_manifest else {}
    job_results = [
        _validate_job(job=job, manifest_jobs=manifest_jobs, output_dir=output_dir)
        for job in queue_jobs
    ]
    blockers.extend(blocker for result in job_results for blocker in result.get("blockers", []))
    warnings.extend(warning for result in job_results for warning in result.get("warnings", []))

    accepted_jobs = [item for item in job_results if item.get("job_status") == "accepted"]
    unique_blockers = sorted(set(blockers))
    unique_warnings = sorted(set(warnings))
    if unique_blockers:
        status = "runtime_evidence_blocked"
        if "plugin_semantic_validation_runtime_manifest_missing" in unique_blockers:
            status = "runtime_manifest_missing"
    elif not queue_jobs:
        status = "no_queue_jobs_to_validate"
    else:
        status = "runtime_evidence_ready"
    runtime_evidence_ready = bool(not unique_blockers and (not queue_jobs or len(accepted_jobs) == len(queue_jobs)))
    gate = {
        "schema": PLUGIN_SEMANTIC_VALIDATION_RUNTIME_EVIDENCE_GATE_SCHEMA,
        "project_name": project_name,
        "created_at": now_utc(),
        "output_dir": str(output_dir),
        "source_queue": str(queue_path),
        "runtime_manifest_path": str(runtime_manifest_path),
        "runtime_manifest_schema": manifest_schema,
        "status": status,
        "runtime_evidence_ready": runtime_evidence_ready,
        "ready_for_semantic_gate_rerun": bool(queue_jobs and runtime_evidence_ready),
        "safe_to_write_parameters": False,
        "requires_reaper_runtime": bool(queue.get("requires_reaper_runtime", False) or runtime_manifest.get("requires_reaper_runtime", False)),
        "requires_operator_review": bool(queue_jobs or blocked_queue_jobs),
        "queue_jobs_total": len(queue_jobs),
        "accepted_jobs_total": len(accepted_jobs),
        "blocked_jobs_total": len(job_results) - len(accepted_jobs),
        "blocked_queue_jobs_total": len(blocked_queue_jobs),
        "next_blocked_job": next((item for item in job_results if item.get("job_status") == "blocked"), {}),
        "job_results": job_results,
        "blocked_queue_jobs": blocked_queue_jobs,
        "blockers": unique_blockers,
        "warnings": unique_warnings,
        "limits": [
            "This gate does not open REAPER, insert FX, write parameters, render, or approve audio.",
            "This gate validates operator/runtime evidence for queued semantic validation reports only.",
            "safe_to_write_parameters remains false; rerun plugin_semantic_validation_gate before any automatic write decision.",
        ],
    }
    target = output_path or output_dir / GATE_REL_PATH
    write_json(target, gate)
    write_plugin_semantic_validation_runtime_evidence_report(gate, output_dir)
    write_plugin_semantic_validation_runtime_evidence_request(gate, output_dir)
    return gate


def write_plugin_semantic_validation_runtime_evidence_report(gate: dict[str, Any], output_dir: Path) -> Path:
    lines = [
        "# Plugin Semantic Validation Runtime Evidence Gate",
        "",
        f"- Project: `{gate.get('project_name')}`",
        f"- Created UTC: `{gate.get('created_at')}`",
        f"- Status: `{gate.get('status')}`",
        f"- Runtime evidence ready: `{gate.get('runtime_evidence_ready')}`",
        f"- Ready for semantic gate rerun: `{gate.get('ready_for_semantic_gate_rerun')}`",
        f"- Queue jobs: `{gate.get('queue_jobs_total')}`",
        f"- Accepted jobs: `{gate.get('accepted_jobs_total')}`",
        f"- Blocked jobs: `{gate.get('blocked_jobs_total')}`",
        f"- Blocked queue jobs: `{gate.get('blocked_queue_jobs_total')}`",
        f"- Safe to write parameters: `{gate.get('safe_to_write_parameters')}`",
        "",
        "This report checks queued REAPER runtime evidence. It does not grant parameter write safety.",
        "",
        "## Blockers",
        "",
    ]
    lines.extend([f"- `{item}`" for item in gate.get("blockers", [])] or ["- none"])
    lines.extend(["", "## Warnings", ""])
    lines.extend([f"- `{item}`" for item in gate.get("warnings", [])] or ["- none"])
    lines.extend(["", "## Next Blocked Job", ""])
    next_job = gate.get("next_blocked_job", {})
    if next_job:
        lines.append(f"- `{next_job.get('job_id')}` `{next_job.get('plugin_name')}`")
        lines.append(f"- Blockers: `{next_job.get('blockers', [])}`")
    else:
        lines.append("- none")
    lines.extend(["", "## Queue Job Evidence", ""])
    if not gate.get("job_results"):
        lines.append("- none")
    for item in gate.get("job_results", []):
        report = item.get("report_result", {})
        lines.extend(
            [
                f"### {item.get('job_id')}",
                "",
                f"- Plugin: `{item.get('plugin_name')}`",
                f"- Status: `{item.get('job_status')}`",
                f"- Runtime observed: `{item.get('runtime_observed')}`",
                f"- Report written: `{item.get('report_written')}`",
                f"- Reaudited by semantic gate: `{item.get('report_reaudited_by_semantic_gate')}`",
                f"- Target report: `{item.get('target_report_path')}`",
                f"- Report status: `{report.get('report_status', '')}`",
                f"- Safe controls: `{report.get('safe_control_count', 0)}`",
                f"- Blockers: `{item.get('blockers', [])}`",
                "",
            ]
        )
    lines.extend(["", "## Blocked Queue Jobs", ""])
    if not gate.get("blocked_queue_jobs"):
        lines.append("- none")
    for item in gate.get("blocked_queue_jobs", []):
        lines.append(f"- `{item.get('plugin_name')}`: `{item.get('blockers', [])}`")
    path = Path(output_dir) / GATE_REPORT_REL_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return path


def write_plugin_semantic_validation_runtime_evidence_request(gate: dict[str, Any], output_dir: Path) -> Path:
    lines = [
        "# Plugin Semantic Validation Runtime Evidence Request",
        "",
        f"- Project: `{gate.get('project_name')}`",
        f"- Runtime manifest: `{gate.get('runtime_manifest_path')}`",
        f"- Runtime manifest schema required: `{PLUGIN_SEMANTIC_VALIDATION_RUNTIME_MANIFEST_SCHEMA}`",
        f"- Queue jobs: `{gate.get('queue_jobs_total')}`",
        f"- Runtime evidence ready: `{gate.get('runtime_evidence_ready')}`",
        f"- Safe to write parameters: `{gate.get('safe_to_write_parameters')}`",
        "",
        "Fill the runtime manifest only after the queued jobs ran in a saved test copy or temporary muted test context. Then rerun this gate and rerun the semantic validation gate.",
        "",
        "## Required Manifest Fields Per Job",
        "",
        "- `operator_acknowledged=true`",
        "- `runtime_observed=true`",
        "- `report_written=true`",
        "- `report_reaudited_by_semantic_gate=true`",
        "",
        "## Open Job Evidence",
        "",
    ]
    open_jobs = [item for item in gate.get("job_results", []) if item.get("job_status") == "blocked"]
    if not open_jobs:
        lines.append("- none")
    for item in open_jobs:
        lines.append(f"- `{item.get('job_id')}` `{item.get('plugin_name')}` -> `{item.get('target_report_path')}` blockers=`{item.get('blockers', [])}`")
    lines.extend(["", "## Blocked Queue Jobs", ""])
    if not gate.get("blocked_queue_jobs"):
        lines.append("- none")
    for item in gate.get("blocked_queue_jobs", []):
        lines.append(f"- `{item.get('plugin_name')}`: `{item.get('blockers', [])}`")
    path = Path(output_dir) / REQUEST_REL_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return path

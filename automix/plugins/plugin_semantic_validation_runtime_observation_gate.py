from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from automix.plugins.plugin_adapter_schema import now_utc, write_json
from automix.plugins.plugin_semantic_validation_runtime_collector_package import (
    PLUGIN_SEMANTIC_VALIDATION_RUNTIME_COLLECTOR_PACKAGE_SCHEMA,
    RUNTIME_OBSERVATION_SCHEMA,
)


PLUGIN_SEMANTIC_VALIDATION_RUNTIME_OBSERVATION_GATE_SCHEMA = "automix-plugin-semantic-validation-runtime-observation-gate-v1"

GATE_REL_PATH = Path("eval_reports/plugin_semantic_validation_runtime_observation_gate.json")
GATE_REPORT_REL_PATH = Path("eval_reports/plugin_semantic_validation_runtime_observation_gate.md")
OBSERVATION_REQUEST_REL_PATH = Path("review/plugin_semantic_validation_runtime_observation_request.md")
REPORT_AUTHORING_REQUEST_REL_PATH = Path("review/plugin_semantic_validation_runtime_report_authoring_request.md")
COLLECTOR_PACKAGE_REL_PATH = Path("eval_reports/plugin_semantic_validation_runtime_collector_package.json")


def _load_json(path: Path) -> tuple[dict[str, Any], bool]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}, False
    return (data, True) if isinstance(data, dict) else ({}, False)


def _resolve_path(value: Any, output_dir: Path) -> Path:
    path = Path(str(value or ""))
    if path.is_absolute():
        return path
    if path.parts and path.parts[0] == output_dir.name:
        return output_dir.parent / path
    return output_dir / path


def _parameters_are_raw(parameters: Any) -> bool:
    if not isinstance(parameters, list):
        return False
    for item in parameters:
        if not isinstance(item, dict):
            return False
        if item.get("write_allowed", False) or item.get("semantic_validated", False):
            return False
    return True


def _validate_observation(job: dict[str, Any], *, output_dir: Path) -> dict[str, Any]:
    job_id = str(job.get("job_id", "")).strip()
    plugin_name = str(job.get("plugin_name", "")).strip()
    observation_path = _resolve_path(job.get("raw_observation_output_path", ""), output_dir)
    blockers: list[str] = []
    warnings: list[str] = []
    observation, json_valid = _load_json(observation_path)

    if not observation_path.exists():
        blockers.append(f"runtime_observation_missing:{job_id}")
        json_valid = False
    elif not json_valid:
        blockers.append(f"runtime_observation_invalid_json:{job_id}")

    parameters = observation.get("parameters", []) if isinstance(observation.get("parameters", []), list) else []
    add_result = observation.get("add_result", {}) if isinstance(observation.get("add_result", {}), dict) else {}

    if observation:
        if observation.get("schema") != RUNTIME_OBSERVATION_SCHEMA:
            blockers.append(f"runtime_observation_schema_mismatch:{job_id}")
        if str(observation.get("job_id", "")).strip() != job_id:
            blockers.append(f"runtime_observation_job_id_mismatch:{job_id}")
        if str(observation.get("plugin_name", "")).strip() != plugin_name:
            blockers.append(f"runtime_observation_plugin_name_mismatch:{job_id}")
        if observation.get("status") != "raw_observation_collected":
            blockers.append(f"runtime_observation_not_collected:{job_id}:{observation.get('status', 'unknown')}")
        if observation.get("safe_to_write_parameters", False):
            blockers.append(f"runtime_observation_claims_write_safety:{job_id}")
        if observation.get("creates_validation_reports", False):
            blockers.append(f"runtime_observation_claims_validation_report_creation:{job_id}")
        if observation.get("writes_parameters", False):
            blockers.append(f"runtime_observation_claims_parameter_writes:{job_id}")
        if observation.get("renders_audio", False):
            blockers.append(f"runtime_observation_claims_audio_render:{job_id}")
        if observation.get("saves_project", False):
            blockers.append(f"runtime_observation_claims_project_save:{job_id}")
        if observation.get("parameter_indexes_assumed", False):
            blockers.append(f"runtime_observation_assumes_parameter_indexes:{job_id}")
        if not observation.get("temporary_muted_probe_track_used", False):
            blockers.append(f"runtime_observation_temp_probe_track_not_used:{job_id}")
        if not observation.get("temporary_muted_probe_track_deleted", False):
            blockers.append(f"runtime_observation_temp_probe_track_not_deleted:{job_id}")
        if not add_result.get("inserted", False):
            blockers.append(f"runtime_observation_plugin_insert_failed:{job_id}")
        if int(observation.get("param_count", 0) or 0) <= 0 or not parameters:
            blockers.append(f"runtime_observation_parameters_missing:{job_id}")
        if not _parameters_are_raw(parameters):
            blockers.append(f"runtime_observation_parameters_claim_write_safety:{job_id}")
        if observation.get("errors"):
            blockers.append(f"runtime_observation_has_errors:{job_id}")
        if not observation.get("actual_fx_name"):
            warnings.append(f"runtime_observation_actual_fx_name_missing:{job_id}")

    passed = not blockers
    return {
        "job_id": job_id,
        "plugin_name": plugin_name,
        "raw_observation_output_path": str(observation_path),
        "observation_exists": observation_path.exists(),
        "json_valid": bool(json_valid and observation),
        "observation_schema": observation.get("schema", ""),
        "observation_status": observation.get("status", ""),
        "actual_fx_name": observation.get("actual_fx_name", ""),
        "add_inserted": bool(add_result.get("inserted", False)),
        "param_count": int(observation.get("param_count", 0) or 0),
        "parameters_observed_total": len(parameters),
        "raw_parameters_only": _parameters_are_raw(parameters),
        "safe_to_write_parameters": False,
        "creates_validation_reports": False,
        "ready_for_manual_report_authoring": bool(passed),
        "blockers": sorted(set(blockers)),
        "warnings": sorted(set(warnings)),
        "job_status": "accepted_for_manual_report_authoring" if passed else "blocked",
    }


def build_plugin_semantic_validation_runtime_observation_gate(
    *,
    project_name: str,
    output_dir: Path,
    collector_package: dict[str, Any] | None = None,
    collector_package_path: Path | None = None,
    output_path: Path | None = None,
) -> dict[str, Any]:
    output_dir = Path(output_dir)
    collector_package_path = collector_package_path or output_dir / COLLECTOR_PACKAGE_REL_PATH
    collector_valid = True
    if collector_package is None:
        collector_package, collector_valid = _load_json(collector_package_path)
    collector_package = collector_package or {}

    blockers: list[str] = []
    warnings: list[str] = []
    if not collector_package or not collector_valid or collector_package.get("schema") != PLUGIN_SEMANTIC_VALIDATION_RUNTIME_COLLECTOR_PACKAGE_SCHEMA:
        blockers.append("plugin_semantic_validation_runtime_collector_package_missing_or_invalid")
        collector_package = collector_package if isinstance(collector_package, dict) else {}

    collector_jobs = [job for job in collector_package.get("collector_jobs", []) or [] if isinstance(job, dict)]
    blocked_queue_jobs = [job for job in collector_package.get("blocked_queue_jobs", []) or [] if isinstance(job, dict)]
    if blocked_queue_jobs:
        warnings.append(f"blocked_queue_jobs_remain:{len(blocked_queue_jobs)}")

    job_results = [_validate_observation(job, output_dir=output_dir) for job in collector_jobs]
    blockers.extend(blocker for result in job_results for blocker in result.get("blockers", []))
    warnings.extend(warning for result in job_results for warning in result.get("warnings", []))
    accepted_jobs = [item for item in job_results if item.get("job_status") == "accepted_for_manual_report_authoring"]

    unique_blockers = sorted(set(blockers))
    unique_warnings = sorted(set(warnings))
    if unique_blockers:
        status = "runtime_observation_gate_blocked"
        if any(str(item).startswith("runtime_observation_missing:") for item in unique_blockers):
            status = "runtime_observations_missing"
    elif not collector_jobs:
        status = "no_runtime_observation_jobs"
    else:
        status = "runtime_observations_ready_for_manual_report_authoring"

    ready = bool(collector_jobs and not unique_blockers and len(accepted_jobs) == len(collector_jobs))
    gate = {
        "schema": PLUGIN_SEMANTIC_VALIDATION_RUNTIME_OBSERVATION_GATE_SCHEMA,
        "project_name": project_name,
        "created_at": now_utc(),
        "output_dir": str(output_dir),
        "collector_package_path": str(collector_package_path),
        "status": status,
        "runtime_observations_ready": ready,
        "ready_for_manual_report_authoring": ready,
        "ready_for_runtime_evidence_gate": False,
        "safe_to_write_parameters": False,
        "creates_validation_reports": False,
        "requires_reaper_runtime": bool(collector_jobs),
        "requires_operator_review": bool(collector_jobs or blocked_queue_jobs),
        "collector_jobs_total": len(collector_jobs),
        "accepted_observations_total": len(accepted_jobs),
        "blocked_observations_total": len(job_results) - len(accepted_jobs),
        "blocked_queue_jobs_total": len(blocked_queue_jobs),
        "next_blocked_observation": next((item for item in job_results if item.get("job_status") == "blocked"), {}),
        "job_results": job_results,
        "blocked_queue_jobs": blocked_queue_jobs,
        "observation_request_path": str(output_dir / OBSERVATION_REQUEST_REL_PATH),
        "report_authoring_request_path": str(output_dir / REPORT_AUTHORING_REQUEST_REL_PATH),
        "blockers": unique_blockers,
        "warnings": unique_warnings,
        "limits": [
            "This gate validates raw collector observations only.",
            "Raw observations are not passing plugin parameter validation reports.",
            "safe_to_write_parameters remains false; report authoring, runtime evidence, and semantic validation gates must pass later.",
        ],
    }
    target = output_path or output_dir / GATE_REL_PATH
    write_json(target, gate)
    write_plugin_semantic_validation_runtime_observation_report(gate, output_dir)
    write_plugin_semantic_validation_runtime_observation_request(gate, output_dir)
    write_plugin_semantic_validation_runtime_report_authoring_request(gate, output_dir)
    return gate


def write_plugin_semantic_validation_runtime_observation_report(gate: dict[str, Any], output_dir: Path) -> Path:
    lines = [
        "# Plugin Semantic Validation Runtime Observation Gate",
        "",
        f"- Project: `{gate.get('project_name')}`",
        f"- Created UTC: `{gate.get('created_at')}`",
        f"- Status: `{gate.get('status')}`",
        f"- Runtime observations ready: `{gate.get('runtime_observations_ready')}`",
        f"- Ready for manual report authoring: `{gate.get('ready_for_manual_report_authoring')}`",
        f"- Ready for runtime evidence gate: `{gate.get('ready_for_runtime_evidence_gate')}`",
        f"- Collector jobs: `{gate.get('collector_jobs_total')}`",
        f"- Accepted observations: `{gate.get('accepted_observations_total')}`",
        f"- Blocked observations: `{gate.get('blocked_observations_total')}`",
        f"- Safe to write parameters: `{gate.get('safe_to_write_parameters')}`",
        f"- Creates validation reports: `{gate.get('creates_validation_reports')}`",
        "",
        "This gate checks raw REAPER collector output only. It does not create validation reports or approve parameter writes.",
        "",
        "## Blockers",
        "",
    ]
    lines.extend([f"- `{item}`" for item in gate.get("blockers", [])] or ["- none"])
    lines.extend(["", "## Warnings", ""])
    lines.extend([f"- `{item}`" for item in gate.get("warnings", [])] or ["- none"])
    lines.extend(["", "## Observation Jobs", ""])
    if not gate.get("job_results"):
        lines.append("- none")
    for job in gate.get("job_results", []):
        lines.extend(
            [
                f"### {job.get('job_id')}",
                "",
                f"- Plugin: `{job.get('plugin_name')}`",
                f"- Status: `{job.get('job_status')}`",
                f"- Observation: `{job.get('raw_observation_output_path')}`",
                f"- Actual FX name: `{job.get('actual_fx_name')}`",
                f"- Parameters observed: `{job.get('parameters_observed_total')}`",
                f"- Blockers: `{job.get('blockers', [])}`",
                "",
            ]
        )
    path = output_dir / GATE_REPORT_REL_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return path


def write_plugin_semantic_validation_runtime_observation_request(gate: dict[str, Any], output_dir: Path) -> Path:
    lines = [
        "# Plugin Semantic Validation Runtime Observation Request",
        "",
        "Run the generated REAPER collector in a saved test copy or temporary muted test context, then rerun this gate.",
        "",
        f"- Runtime observations ready: `{gate.get('runtime_observations_ready')}`",
        f"- Safe to write parameters: `{gate.get('safe_to_write_parameters')}`",
        "",
        "## Missing Or Blocked Observations",
        "",
    ]
    blocked = [item for item in gate.get("job_results", []) if item.get("job_status") == "blocked"]
    if not blocked:
        lines.append("- none")
    for item in blocked:
        lines.append(f"- `{item.get('job_id')}` `{item.get('plugin_name')}` -> `{item.get('raw_observation_output_path')}` blockers `{item.get('blockers', [])}`")
    lines.extend(
        [
            "",
            "## Limits",
            "",
            "- Raw observations are not passing validation reports.",
            "- Do not infer write safety from insertability or parameter names alone.",
            "- Keep generated validation reports out of `automix/analysis_reports/` until manually reviewed.",
        ]
    )
    path = output_dir / OBSERVATION_REQUEST_REL_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return path


def write_plugin_semantic_validation_runtime_report_authoring_request(gate: dict[str, Any], output_dir: Path) -> Path:
    lines = [
        "# Plugin Semantic Validation Runtime Report Authoring Request",
        "",
        f"- Ready for manual report authoring: `{gate.get('ready_for_manual_report_authoring')}`",
        f"- Creates validation reports: `{gate.get('creates_validation_reports')}`",
        f"- Safe to write parameters: `{gate.get('safe_to_write_parameters')}`",
        "",
        "Only accepted raw observations may be used as source material for manually authored `automix-plugin-parameter-validation-report-v1` reports.",
        "",
        "## Accepted Observations",
        "",
    ]
    accepted = [item for item in gate.get("job_results", []) if item.get("job_status") == "accepted_for_manual_report_authoring"]
    if not accepted:
        lines.append("- none")
    for item in accepted:
        lines.append(f"- `{item.get('job_id')}` `{item.get('plugin_name')}` -> `{item.get('raw_observation_output_path')}`")
    lines.extend(
        [
            "",
            "## Required Follow-Up",
            "",
            "- Manually map semantic controls by observed parameter name and safe bounds.",
            "- Write real validation reports only after review.",
            "- Update `automix/review/plugin_semantic_validation_runtime_manifest.json` after reports exist.",
            "- Rerun runtime evidence gate and then semantic validation gate before any write-safety decision.",
        ]
    )
    path = output_dir / REPORT_AUTHORING_REQUEST_REL_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return path

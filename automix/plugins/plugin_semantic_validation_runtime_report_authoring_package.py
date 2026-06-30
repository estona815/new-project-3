from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from automix.plugins.plugin_adapter_schema import now_utc, slugify, write_json
from automix.plugins.plugin_semantic_validation_runtime_collector_package import (
    PLUGIN_SEMANTIC_VALIDATION_RUNTIME_COLLECTOR_PACKAGE_SCHEMA,
    RUNTIME_OBSERVATION_SCHEMA,
)
from automix.plugins.plugin_semantic_validation_runtime_observation_gate import (
    PLUGIN_SEMANTIC_VALIDATION_RUNTIME_OBSERVATION_GATE_SCHEMA,
)


PLUGIN_SEMANTIC_VALIDATION_RUNTIME_REPORT_AUTHORING_PACKAGE_SCHEMA = (
    "automix-plugin-semantic-validation-runtime-report-authoring-package-v1"
)
PLUGIN_PARAMETER_VALIDATION_REPORT_AUTHORING_TEMPLATE_SCHEMA = (
    "automix-plugin-parameter-validation-report-authoring-template-v1"
)

PACKAGE_REL_PATH = Path("eval_reports/plugin_semantic_validation_runtime_report_authoring_package.json")
PACKAGE_REPORT_REL_PATH = Path("eval_reports/plugin_semantic_validation_runtime_report_authoring_package.md")
OBSERVATION_GATE_REL_PATH = Path("eval_reports/plugin_semantic_validation_runtime_observation_gate.json")
CHECKLIST_REL_PATH = Path("review/plugin_semantic_validation_runtime_report_authoring_checklist.md")
REQUEST_REL_PATH = Path("review/plugin_semantic_validation_runtime_report_authoring_package_request.md")
TEMPLATE_DIR_REL_PATH = Path("review/plugin_semantic_validation_runtime_report_authoring_templates")


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


def _collector_jobs_by_id(gate: dict[str, Any], output_dir: Path) -> dict[str, dict[str, Any]]:
    collector_path = _resolve_path(gate.get("collector_package_path", ""), output_dir)
    collector, valid = _load_json(collector_path)
    if not valid or collector.get("schema") != PLUGIN_SEMANTIC_VALIDATION_RUNTIME_COLLECTOR_PACKAGE_SCHEMA:
        return {}
    out: dict[str, dict[str, Any]] = {}
    for item in collector.get("collector_jobs", []) or []:
        if not isinstance(item, dict):
            continue
        job_id = str(item.get("job_id", "")).strip()
        if job_id:
            out[job_id] = item
    return out


def _observed_parameters(observation: dict[str, Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    parameters = observation.get("parameters", [])
    if not isinstance(parameters, list):
        return out
    for item in parameters:
        if not isinstance(item, dict):
            continue
        try:
            index = int(item.get("index", len(out)))
        except (TypeError, ValueError):
            index = len(out)
        out.append(
            {
                "index": index,
                "name": str(item.get("name", "")).strip(),
                "write_allowed": False,
                "semantic_validated": False,
                "source": "runtime_raw_observation",
            }
        )
    return out


def _control_review_candidates(parameters: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    controls: dict[str, dict[str, Any]] = {}
    for item in parameters:
        key = f"review_candidate_param_{item.get('index', len(controls))}"
        controls[key] = {
            "semantic": key,
            "category": "review_required",
            "target_name": "",
            "source_parameter_name": item.get("name", ""),
            "observed_parameter_index": item.get("index"),
            "parameter_index_authoritative": False,
            "confidence": 0.0,
            "write_allowed": False,
            "validated": False,
            "safe_min": None,
            "safe_max": None,
            "notes": "Human author must map this observed parameter to a semantic control before any write-safe report can exist.",
        }
    return controls


def _template_path(job_id: str, output_dir: Path) -> Path:
    return output_dir / TEMPLATE_DIR_REL_PATH / f"{slugify(job_id)}_authoring_template.json"


def _target_report_path(job: dict[str, Any], collector_job: dict[str, Any], output_dir: Path) -> str:
    value = job.get("target_report_path") or collector_job.get("target_report_path") or ""
    if value:
        return str(_resolve_path(value, output_dir))
    return str(output_dir / "analysis_reports" / f"plugin_parameter_validation_{slugify(job.get('job_id', 'unknown'))}.json")


def _build_template(
    *,
    project_name: str,
    output_dir: Path,
    job: dict[str, Any],
    collector_job: dict[str, Any],
    observation: dict[str, Any],
    observation_path: Path,
) -> dict[str, Any]:
    parameters = _observed_parameters(observation)
    return {
        "schema": PLUGIN_PARAMETER_VALIDATION_REPORT_AUTHORING_TEMPLATE_SCHEMA,
        "target_report_schema": "automix-plugin-parameter-validation-report-v1",
        "project_name": project_name,
        "created_at": now_utc(),
        "status": "authoring_template_not_validation_evidence",
        "job_id": str(job.get("job_id", "")).strip(),
        "plugin_name": str(job.get("plugin_name", "")).strip(),
        "actual_fx_name": str(observation.get("actual_fx_name", "")).strip(),
        "source_observation_path": str(observation_path),
        "target_report_path": _target_report_path(job, collector_job, output_dir),
        "safe_for_automix": False,
        "no_fake_success": False,
        "safe_to_write_parameters": False,
        "creates_validation_reports": False,
        "writes_analysis_reports": False,
        "raw_observation_schema": observation.get("schema", ""),
        "raw_observation_status": observation.get("status", ""),
        "param_count": int(observation.get("param_count", 0) or 0),
        "observed_parameters_total": len(parameters),
        "observed_parameters": parameters,
        "controls": _control_review_candidates(parameters),
        "required_manual_authoring": [
            "Confirm actual FX identity and parameter names in REAPER.",
            "Map only reviewed parameters to semantic controls.",
            "Set no_fake_success=true only in the final authored validation report, not this template.",
            "Keep write_allowed=false until confidence, safe bounds, and semantic validation are proven.",
        ],
        "limits": [
            "This file is review material only.",
            "This file is not a passing plugin parameter validation report.",
            "Do not copy this template into automix/analysis_reports as evidence.",
        ],
    }


def _template_for_job(
    *,
    project_name: str,
    output_dir: Path,
    job: dict[str, Any],
    collector_job: dict[str, Any],
) -> dict[str, Any]:
    job_id = str(job.get("job_id", "")).strip()
    observation_path = _resolve_path(job.get("raw_observation_output_path", ""), output_dir)
    blockers: list[str] = []
    warnings: list[str] = []
    observation, valid = _load_json(observation_path)
    if not observation_path.exists():
        blockers.append(f"accepted_runtime_observation_missing:{job_id}")
    elif not valid:
        blockers.append(f"accepted_runtime_observation_invalid_json:{job_id}")
    if observation:
        if observation.get("schema") != RUNTIME_OBSERVATION_SCHEMA:
            blockers.append(f"accepted_runtime_observation_schema_mismatch:{job_id}")
        if observation.get("status") != "raw_observation_collected":
            blockers.append(f"accepted_runtime_observation_not_raw_collected:{job_id}")
        if observation.get("safe_to_write_parameters", False):
            blockers.append(f"accepted_runtime_observation_claims_write_safety:{job_id}")
        if observation.get("creates_validation_reports", False):
            blockers.append(f"accepted_runtime_observation_claims_validation_report_creation:{job_id}")
        if observation.get("writes_parameters", False):
            blockers.append(f"accepted_runtime_observation_claims_parameter_writes:{job_id}")
        if not observation.get("actual_fx_name"):
            warnings.append(f"accepted_runtime_observation_actual_fx_name_missing:{job_id}")

    template_path = _template_path(job_id, output_dir)
    template: dict[str, Any] = {}
    if not blockers:
        template = _build_template(
            project_name=project_name,
            output_dir=output_dir,
            job=job,
            collector_job=collector_job,
            observation=observation,
            observation_path=observation_path,
        )
        write_json(template_path, template)

    return {
        "job_id": job_id,
        "plugin_name": job.get("plugin_name", ""),
        "actual_fx_name": observation.get("actual_fx_name", ""),
        "source_observation_path": str(observation_path),
        "target_report_path": _target_report_path(job, collector_job, output_dir),
        "template_path": str(template_path),
        "template_written": bool(template and not blockers),
        "observed_parameters_total": int(template.get("observed_parameters_total", 0) or 0),
        "safe_to_write_parameters": False,
        "creates_validation_reports": False,
        "writes_analysis_reports": False,
        "blockers": sorted(set(blockers)),
        "warnings": sorted(set(warnings)),
        "job_status": "template_ready_for_manual_authoring" if not blockers else "blocked",
    }


def build_plugin_semantic_validation_runtime_report_authoring_package(
    *,
    project_name: str,
    output_dir: Path,
    observation_gate: dict[str, Any] | None = None,
    observation_gate_path: Path | None = None,
    output_path: Path | None = None,
) -> dict[str, Any]:
    output_dir = Path(output_dir)
    (output_dir / TEMPLATE_DIR_REL_PATH).mkdir(parents=True, exist_ok=True)
    observation_gate_path = observation_gate_path or output_dir / OBSERVATION_GATE_REL_PATH
    gate_valid = True
    if observation_gate is None:
        observation_gate, gate_valid = _load_json(observation_gate_path)
    observation_gate = observation_gate or {}

    blockers: list[str] = []
    warnings: list[str] = []
    if (
        not observation_gate
        or not gate_valid
        or observation_gate.get("schema") != PLUGIN_SEMANTIC_VALIDATION_RUNTIME_OBSERVATION_GATE_SCHEMA
    ):
        blockers.append("plugin_semantic_validation_runtime_observation_gate_missing_or_invalid")
        observation_gate = observation_gate if isinstance(observation_gate, dict) else {}

    accepted_jobs = [
        item
        for item in observation_gate.get("job_results", []) or []
        if isinstance(item, dict) and item.get("job_status") == "accepted_for_manual_report_authoring"
    ]
    if not accepted_jobs and not blockers:
        blockers.append("accepted_runtime_observations_missing")

    collector_jobs = _collector_jobs_by_id(observation_gate, output_dir) if observation_gate else {}
    template_results = [
        _template_for_job(
            project_name=project_name,
            output_dir=output_dir,
            job=job,
            collector_job=collector_jobs.get(str(job.get("job_id", "")).strip(), {}),
        )
        for job in accepted_jobs
    ]
    blockers.extend(blocker for result in template_results for blocker in result.get("blockers", []))
    warnings.extend(warning for result in template_results for warning in result.get("warnings", []))
    unique_blockers = sorted(set(blockers))
    unique_warnings = sorted(set(warnings))
    ready = bool(accepted_jobs and not unique_blockers and all(item.get("template_written") for item in template_results))
    if ready:
        status = "runtime_report_authoring_package_ready"
    elif "accepted_runtime_observations_missing" in unique_blockers:
        status = "no_accepted_runtime_observations"
    else:
        status = "runtime_report_authoring_package_blocked"

    package = {
        "schema": PLUGIN_SEMANTIC_VALIDATION_RUNTIME_REPORT_AUTHORING_PACKAGE_SCHEMA,
        "project_name": project_name,
        "created_at": now_utc(),
        "output_dir": str(output_dir),
        "observation_gate_path": str(observation_gate_path),
        "observation_gate_status": observation_gate.get("status", ""),
        "status": status,
        "runtime_report_authoring_package_ready": ready,
        "ready_for_manual_report_authoring": ready,
        "ready_for_runtime_evidence_gate": False,
        "safe_to_write_parameters": False,
        "creates_validation_reports": False,
        "writes_analysis_reports": False,
        "accepted_observations_total": len(accepted_jobs),
        "blocked_observations_total": int(observation_gate.get("blocked_observations_total", 0) or 0),
        "templates_total": len([item for item in template_results if item.get("template_written")]),
        "template_dir": str(output_dir / TEMPLATE_DIR_REL_PATH),
        "checklist_path": str(output_dir / CHECKLIST_REL_PATH),
        "request_path": str(output_dir / REQUEST_REL_PATH),
        "template_results": template_results,
        "blockers": unique_blockers,
        "warnings": unique_warnings,
        "limits": [
            "This package writes review-only authoring templates, not validation reports.",
            "No files are written under automix/analysis_reports by this package.",
            "safe_to_write_parameters remains false until authored reports pass runtime evidence and semantic validation gates.",
        ],
    }
    target = output_path or output_dir / PACKAGE_REL_PATH
    write_json(target, package)
    write_plugin_semantic_validation_runtime_report_authoring_report(package, output_dir)
    write_plugin_semantic_validation_runtime_report_authoring_checklist(package, output_dir)
    write_plugin_semantic_validation_runtime_report_authoring_request(package, output_dir)
    return package


def write_plugin_semantic_validation_runtime_report_authoring_report(package: dict[str, Any], output_dir: Path) -> Path:
    lines = [
        "# Plugin Semantic Validation Runtime Report Authoring Package",
        "",
        f"- Project: `{package.get('project_name')}`",
        f"- Created UTC: `{package.get('created_at')}`",
        f"- Status: `{package.get('status')}`",
        f"- Ready for manual report authoring: `{package.get('ready_for_manual_report_authoring')}`",
        f"- Ready for runtime evidence gate: `{package.get('ready_for_runtime_evidence_gate')}`",
        f"- Accepted observations: `{package.get('accepted_observations_total')}`",
        f"- Templates: `{package.get('templates_total')}`",
        f"- Safe to write parameters: `{package.get('safe_to_write_parameters')}`",
        f"- Creates validation reports: `{package.get('creates_validation_reports')}`",
        f"- Writes analysis reports: `{package.get('writes_analysis_reports')}`",
        "",
        "This package prepares review-only authoring templates from accepted raw runtime observations. It does not create passing validation reports.",
        "",
        "## Blockers",
        "",
    ]
    lines.extend([f"- `{item}`" for item in package.get("blockers", [])] or ["- none"])
    lines.extend(["", "## Warnings", ""])
    lines.extend([f"- `{item}`" for item in package.get("warnings", [])] or ["- none"])
    lines.extend(["", "## Templates", ""])
    if not package.get("template_results"):
        lines.append("- none")
    for item in package.get("template_results", []):
        lines.append(
            f"- `{item.get('job_id')}` `{item.get('plugin_name')}` -> `{item.get('template_path')}` "
            f"status `{item.get('job_status')}`"
        )
    path = output_dir / PACKAGE_REPORT_REL_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return path


def write_plugin_semantic_validation_runtime_report_authoring_checklist(package: dict[str, Any], output_dir: Path) -> Path:
    lines = [
        "# Plugin Semantic Validation Runtime Report Authoring Checklist",
        "",
        f"- Package ready: `{package.get('runtime_report_authoring_package_ready')}`",
        f"- Safe to write parameters: `{package.get('safe_to_write_parameters')}`",
        f"- Templates directory: `{package.get('template_dir')}`",
        "",
        "## Required Checks",
        "",
        "- Confirm every source observation came from the raw runtime collector.",
        "- Confirm each template status is `authoring_template_not_validation_evidence`.",
        "- Keep templates under `automix/review/`; do not copy them into `automix/analysis_reports/` as passing reports.",
        "- Manually author real `automix-plugin-parameter-validation-report-v1` reports only after mapping semantic controls, confidence, and safe bounds.",
        "- Rerun runtime evidence and semantic validation gates after real reports exist.",
        "",
        "## Template Jobs",
        "",
    ]
    if not package.get("template_results"):
        lines.append("- none")
    for item in package.get("template_results", []):
        lines.append(f"- `{item.get('job_id')}` -> `{item.get('template_path')}` observed params `{item.get('observed_parameters_total')}`")
    path = output_dir / CHECKLIST_REL_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return path


def write_plugin_semantic_validation_runtime_report_authoring_request(package: dict[str, Any], output_dir: Path) -> Path:
    lines = [
        "# Plugin Semantic Validation Runtime Report Authoring Package Request",
        "",
        f"- Status: `{package.get('status')}`",
        f"- Ready for manual report authoring: `{package.get('ready_for_manual_report_authoring')}`",
        f"- Accepted observations: `{package.get('accepted_observations_total')}`",
        f"- Templates: `{package.get('templates_total')}`",
        "",
        "Use this request only to prepare human-authored validation reports from accepted raw observations. It is not report evidence itself.",
        "",
        "## Next Action",
        "",
    ]
    if package.get("ready_for_manual_report_authoring"):
        lines.append("- Review the generated templates and author real validation reports outside this package.")
    else:
        lines.append("- Collect and accept raw runtime observations before manual report authoring.")
    lines.extend(["", "## Blockers", ""])
    lines.extend([f"- `{item}`" for item in package.get("blockers", [])] or ["- none"])
    path = output_dir / REQUEST_REL_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return path

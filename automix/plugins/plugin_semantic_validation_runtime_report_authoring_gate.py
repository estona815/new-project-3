from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from automix.plugins.plugin_adapter_schema import compact_plugin_name, now_utc, slugify, write_json
from automix.plugins.plugin_semantic_validation_runtime_report_authoring_package import (
    PLUGIN_PARAMETER_VALIDATION_REPORT_AUTHORING_TEMPLATE_SCHEMA,
    PLUGIN_SEMANTIC_VALIDATION_RUNTIME_REPORT_AUTHORING_PACKAGE_SCHEMA,
)


PLUGIN_SEMANTIC_VALIDATION_RUNTIME_REPORT_AUTHORING_GATE_SCHEMA = (
    "automix-plugin-semantic-validation-runtime-report-authoring-gate-v1"
)
RUNTIME_MANIFEST_SCHEMA = "automix-plugin-semantic-validation-runtime-manifest-v1"

GATE_REL_PATH = Path("eval_reports/plugin_semantic_validation_runtime_report_authoring_gate.json")
GATE_REPORT_REL_PATH = Path("eval_reports/plugin_semantic_validation_runtime_report_authoring_gate.md")
AUTHORING_PACKAGE_REL_PATH = Path("eval_reports/plugin_semantic_validation_runtime_report_authoring_package.json")
CANDIDATE_DIR_REL_PATH = Path("review/plugin_semantic_validation_runtime_report_authoring_candidates")
PROMOTION_CHECKLIST_REL_PATH = Path("review/plugin_semantic_validation_runtime_report_promotion_checklist.md")
PROMOTION_REQUEST_REL_PATH = Path("review/plugin_semantic_validation_runtime_report_promotion_request.md")
MANIFEST_CANDIDATE_REL_PATH = Path("review/plugin_semantic_validation_runtime_manifest_candidate_from_authoring.json")


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


def _resolve_path(value: Any, output_dir: Path) -> Path:
    path = Path(str(value or ""))
    if path.is_absolute():
        return path
    if path.parts and path.parts[0] == output_dir.name:
        return output_dir.parent / path
    return output_dir / path


def _candidate_path(job_id: str, output_dir: Path) -> Path:
    return output_dir / CANDIDATE_DIR_REL_PATH / f"{slugify(job_id)}_validation_report_candidate.json"


def _safe_controls(report: dict[str, Any]) -> dict[str, dict[str, Any]]:
    controls = report.get("controls", {}) if isinstance(report.get("controls", {}), dict) else {}
    safe: dict[str, dict[str, Any]] = {}
    for semantic, control in controls.items():
        if not isinstance(control, dict):
            continue
        confidence = _safe_float(control.get("confidence"), 0.0)
        if (
            bool(control.get("validated"))
            and bool(control.get("write_allowed"))
            and confidence >= 0.85
            and control.get("target_name")
            and control.get("safe_min") is not None
            and control.get("safe_max") is not None
        ):
            safe[str(semantic)] = control
    return safe


def _load_template(template_path: Path) -> tuple[dict[str, Any], list[str]]:
    template, valid = _load_json(template_path)
    blockers: list[str] = []
    if not template_path.exists():
        blockers.append("authoring_template_missing")
    elif not valid:
        blockers.append("authoring_template_invalid_json")
    elif template.get("schema") != PLUGIN_PARAMETER_VALIDATION_REPORT_AUTHORING_TEMPLATE_SCHEMA:
        blockers.append("authoring_template_schema_mismatch")
    return template, blockers


def _validate_candidate(
    *,
    job: dict[str, Any],
    output_dir: Path,
) -> dict[str, Any]:
    job_id = str(job.get("job_id", "")).strip()
    plugin_name = str(job.get("plugin_name", "")).strip()
    template_path = _resolve_path(job.get("template_path", ""), output_dir)
    candidate_path = _candidate_path(job_id, output_dir)
    blockers: list[str] = []
    warnings: list[str] = []
    template, template_blockers = _load_template(template_path)
    blockers.extend(f"{item}:{job_id}" for item in template_blockers)

    candidate, candidate_valid = _load_json(candidate_path)
    if not candidate_path.exists():
        blockers.append(f"authoring_candidate_missing:{job_id}")
    elif not candidate_valid:
        blockers.append(f"authoring_candidate_invalid_json:{job_id}")

    safe_controls: dict[str, dict[str, Any]] = {}
    if candidate:
        safe_controls = _safe_controls(candidate)
        if candidate.get("schema") != "automix-plugin-parameter-validation-report-v1":
            blockers.append(f"authoring_candidate_schema_mismatch:{job_id}")
        if candidate.get("status") != "passed":
            blockers.append(f"authoring_candidate_not_passed:{job_id}:{candidate.get('status', 'unknown')}")
        if not candidate.get("safe_for_automix", False):
            blockers.append(f"authoring_candidate_not_safe_for_automix:{job_id}")
        if not candidate.get("no_fake_success", False):
            blockers.append(f"authoring_candidate_no_fake_success_missing:{job_id}")
        if str(candidate.get("job_id", "")).strip() != job_id:
            blockers.append(f"authoring_candidate_job_id_mismatch:{job_id}")
        if plugin_name and compact_plugin_name(candidate.get("plugin_name", "")) != compact_plugin_name(plugin_name):
            blockers.append(f"authoring_candidate_plugin_name_mismatch:{job_id}")
        if template and str(candidate.get("source_observation_path", "")).strip() != str(template.get("source_observation_path", "")).strip():
            blockers.append(f"authoring_candidate_source_observation_mismatch:{job_id}")
        if not safe_controls:
            blockers.append(f"authoring_candidate_has_no_write_safe_controls:{job_id}")
        controls = candidate.get("controls", {}) if isinstance(candidate.get("controls", {}), dict) else {}
        if controls and len(safe_controls) < len(controls):
            warnings.append(f"authoring_candidate_some_controls_remain_write_blocked:{job_id}")

    target_report_path = template.get("target_report_path") or job.get("target_report_path", "")
    return {
        "job_id": job_id,
        "plugin_name": plugin_name,
        "template_path": str(template_path),
        "candidate_report_path": str(candidate_path),
        "candidate_exists": candidate_path.exists(),
        "candidate_schema": candidate.get("schema", ""),
        "candidate_status": candidate.get("status", ""),
        "target_report_path": str(_resolve_path(target_report_path, output_dir)) if target_report_path else "",
        "safe_controls": sorted(safe_controls),
        "safe_control_count": len(safe_controls),
        "safe_to_write_parameters": False,
        "candidate_reports_are_validation_evidence": False,
        "writes_analysis_reports": False,
        "blockers": sorted(set(blockers)),
        "warnings": sorted(set(warnings)),
        "job_status": "candidate_ready_for_operator_promotion" if not blockers else "blocked",
    }


def _manifest_candidate(candidate_results: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "schema": RUNTIME_MANIFEST_SCHEMA,
        "candidate_only": True,
        "from_authoring_gate": True,
        "operator_ready_to_run": False,
        "safe_to_write_parameters": False,
        "queue_jobs": [
            {
                "job_id": item.get("job_id", ""),
                "plugin_name": item.get("plugin_name", ""),
                "candidate_report_path": item.get("candidate_report_path", ""),
                "target_report_path": item.get("target_report_path", ""),
                "operator_acknowledged": False,
                "runtime_observed": False,
                "report_written": False,
                "report_reaudited_by_semantic_gate": False,
            }
            for item in candidate_results
            if item.get("job_status") == "candidate_ready_for_operator_promotion"
        ],
        "limits": [
            "This manifest candidate is not runtime evidence.",
            "Copy or write real reports to target paths only after operator review.",
            "Rerun semantic validation before report_reaudited_by_semantic_gate can become true.",
        ],
    }


def build_plugin_semantic_validation_runtime_report_authoring_gate(
    *,
    project_name: str,
    output_dir: Path,
    authoring_package: dict[str, Any] | None = None,
    authoring_package_path: Path | None = None,
    output_path: Path | None = None,
) -> dict[str, Any]:
    output_dir = Path(output_dir)
    (output_dir / CANDIDATE_DIR_REL_PATH).mkdir(parents=True, exist_ok=True)
    authoring_package_path = authoring_package_path or output_dir / AUTHORING_PACKAGE_REL_PATH
    package_valid = True
    if authoring_package is None:
        authoring_package, package_valid = _load_json(authoring_package_path)
    authoring_package = authoring_package or {}

    blockers: list[str] = []
    warnings: list[str] = []
    if (
        not authoring_package
        or not package_valid
        or authoring_package.get("schema") != PLUGIN_SEMANTIC_VALIDATION_RUNTIME_REPORT_AUTHORING_PACKAGE_SCHEMA
    ):
        blockers.append("plugin_semantic_validation_runtime_report_authoring_package_missing_or_invalid")
        authoring_package = authoring_package if isinstance(authoring_package, dict) else {}
    elif not authoring_package.get("runtime_report_authoring_package_ready", False):
        status = authoring_package.get("status", "unknown")
        blockers.append(f"runtime_report_authoring_package_not_ready:{status}")

    template_jobs = [
        item
        for item in authoring_package.get("template_results", []) or []
        if isinstance(item, dict) and item.get("template_written")
    ]
    if not template_jobs and not any(str(item).startswith("runtime_report_authoring_package_not_ready:") for item in blockers):
        blockers.append("authoring_templates_missing")

    candidate_results = [_validate_candidate(job=job, output_dir=output_dir) for job in template_jobs]
    blockers.extend(blocker for result in candidate_results for blocker in result.get("blockers", []))
    warnings.extend(warning for result in candidate_results for warning in result.get("warnings", []))

    ready_candidates = [item for item in candidate_results if item.get("job_status") == "candidate_ready_for_operator_promotion"]
    unique_blockers = sorted(set(blockers))
    unique_warnings = sorted(set(warnings))
    if not unique_blockers and template_jobs and len(ready_candidates) == len(template_jobs):
        status = "runtime_report_authoring_candidates_ready_for_operator_promotion"
    elif any(str(item).startswith("runtime_report_authoring_package_not_ready:") for item in unique_blockers):
        status = "runtime_report_authoring_package_not_ready"
    elif any(str(item).startswith("authoring_candidate_missing:") for item in unique_blockers):
        status = "runtime_report_authoring_candidates_missing"
    else:
        status = "runtime_report_authoring_gate_blocked"

    manifest_candidate = _manifest_candidate(candidate_results)
    write_json(output_dir / MANIFEST_CANDIDATE_REL_PATH, manifest_candidate)

    gate = {
        "schema": PLUGIN_SEMANTIC_VALIDATION_RUNTIME_REPORT_AUTHORING_GATE_SCHEMA,
        "project_name": project_name,
        "created_at": now_utc(),
        "output_dir": str(output_dir),
        "authoring_package_path": str(authoring_package_path),
        "authoring_package_status": authoring_package.get("status", ""),
        "status": status,
        "authoring_candidates_ready": bool(not unique_blockers and template_jobs and len(ready_candidates) == len(template_jobs)),
        "ready_for_operator_promotion": bool(not unique_blockers and ready_candidates),
        "ready_for_runtime_evidence_gate": False,
        "safe_to_write_parameters": False,
        "creates_validation_reports": False,
        "writes_analysis_reports": False,
        "candidate_reports_are_validation_evidence": False,
        "templates_total": len(template_jobs),
        "candidate_reports_total": len([item for item in candidate_results if item.get("candidate_exists")]),
        "accepted_candidates_total": len(ready_candidates),
        "blocked_candidates_total": len(candidate_results) - len(ready_candidates),
        "candidate_dir": str(output_dir / CANDIDATE_DIR_REL_PATH),
        "promotion_checklist_path": str(output_dir / PROMOTION_CHECKLIST_REL_PATH),
        "promotion_request_path": str(output_dir / PROMOTION_REQUEST_REL_PATH),
        "manifest_candidate_path": str(output_dir / MANIFEST_CANDIDATE_REL_PATH),
        "candidate_results": candidate_results,
        "blockers": unique_blockers,
        "warnings": unique_warnings,
        "limits": [
            "This gate validates review-only candidate reports and writes no analysis_reports files.",
            "Candidate reports are not runtime evidence until promoted, reaudited, and recorded in the runtime manifest.",
            "safe_to_write_parameters remains false.",
        ],
    }
    target = output_path or output_dir / GATE_REL_PATH
    write_json(target, gate)
    write_plugin_semantic_validation_runtime_report_authoring_gate_report(gate, output_dir)
    write_plugin_semantic_validation_runtime_report_promotion_checklist(gate, output_dir)
    write_plugin_semantic_validation_runtime_report_promotion_request(gate, output_dir)
    return gate


def write_plugin_semantic_validation_runtime_report_authoring_gate_report(gate: dict[str, Any], output_dir: Path) -> Path:
    lines = [
        "# Plugin Semantic Validation Runtime Report Authoring Gate",
        "",
        f"- Project: `{gate.get('project_name')}`",
        f"- Created UTC: `{gate.get('created_at')}`",
        f"- Status: `{gate.get('status')}`",
        f"- Authoring candidates ready: `{gate.get('authoring_candidates_ready')}`",
        f"- Ready for operator promotion: `{gate.get('ready_for_operator_promotion')}`",
        f"- Ready for runtime evidence gate: `{gate.get('ready_for_runtime_evidence_gate')}`",
        f"- Templates: `{gate.get('templates_total')}`",
        f"- Candidates: `{gate.get('candidate_reports_total')}`",
        f"- Accepted candidates: `{gate.get('accepted_candidates_total')}`",
        f"- Safe to write parameters: `{gate.get('safe_to_write_parameters')}`",
        f"- Writes analysis reports: `{gate.get('writes_analysis_reports')}`",
        "",
        "This gate checks human-authored candidate reports under review. It does not promote them or grant write safety.",
        "",
        "## Blockers",
        "",
    ]
    lines.extend([f"- `{item}`" for item in gate.get("blockers", [])] or ["- none"])
    lines.extend(["", "## Warnings", ""])
    lines.extend([f"- `{item}`" for item in gate.get("warnings", [])] or ["- none"])
    lines.extend(["", "## Candidate Reports", ""])
    if not gate.get("candidate_results"):
        lines.append("- none")
    for item in gate.get("candidate_results", []):
        lines.append(
            f"- `{item.get('job_id')}` `{item.get('plugin_name')}` -> `{item.get('candidate_report_path')}` "
            f"status `{item.get('job_status')}` safe controls `{item.get('safe_control_count')}`"
        )
    path = output_dir / GATE_REPORT_REL_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return path


def write_plugin_semantic_validation_runtime_report_promotion_checklist(gate: dict[str, Any], output_dir: Path) -> Path:
    lines = [
        "# Plugin Semantic Validation Runtime Report Promotion Checklist",
        "",
        f"- Ready for operator promotion: `{gate.get('ready_for_operator_promotion')}`",
        f"- Candidate dir: `{gate.get('candidate_dir')}`",
        f"- Manifest candidate: `{gate.get('manifest_candidate_path')}`",
        f"- Safe to write parameters: `{gate.get('safe_to_write_parameters')}`",
        "",
        "## Required Promotion Steps",
        "",
        "1. Review every accepted candidate report manually.",
        "2. Copy or author the accepted report into its target `automix/analysis_reports/` path.",
        "3. Rerun `scripts/run_plugin_semantic_validation_gate.py`.",
        "4. Fill `automix/review/plugin_semantic_validation_runtime_manifest.json` only after semantic validation sees the promoted reports.",
        "5. Rerun `scripts/run_plugin_semantic_validation_runtime_evidence_gate.py`.",
        "",
        "## Candidate Jobs",
        "",
    ]
    if not gate.get("candidate_results"):
        lines.append("- none")
    for item in gate.get("candidate_results", []):
        lines.append(f"- `{item.get('job_id')}` candidate `{item.get('candidate_report_path')}` target `{item.get('target_report_path')}`")
    path = output_dir / PROMOTION_CHECKLIST_REL_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return path


def write_plugin_semantic_validation_runtime_report_promotion_request(gate: dict[str, Any], output_dir: Path) -> Path:
    lines = [
        "# Plugin Semantic Validation Runtime Report Promotion Request",
        "",
        f"- Status: `{gate.get('status')}`",
        f"- Ready for operator promotion: `{gate.get('ready_for_operator_promotion')}`",
        f"- Ready for runtime evidence gate: `{gate.get('ready_for_runtime_evidence_gate')}`",
        "",
        "Candidate reports remain review-only until an operator promotes them and reruns the semantic validation gate.",
        "",
        "## Blockers",
        "",
    ]
    lines.extend([f"- `{item}`" for item in gate.get("blockers", [])] or ["- none"])
    path = output_dir / PROMOTION_REQUEST_REL_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return path

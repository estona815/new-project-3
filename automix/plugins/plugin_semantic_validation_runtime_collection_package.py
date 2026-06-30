from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from automix.plugins.plugin_adapter_schema import now_utc, slugify, write_json


PLUGIN_SEMANTIC_VALIDATION_RUNTIME_COLLECTION_PACKAGE_SCHEMA = "automix-plugin-semantic-validation-runtime-collection-package-v1"
PLUGIN_PARAMETER_VALIDATION_REPORT_TEMPLATE_SCHEMA = "automix-plugin-parameter-validation-report-template-v1"
RUNTIME_MANIFEST_SCHEMA = "automix-plugin-semantic-validation-runtime-manifest-v1"

PACKAGE_REL_PATH = Path("eval_reports/plugin_semantic_validation_runtime_collection_package.json")
PACKAGE_REPORT_REL_PATH = Path("eval_reports/plugin_semantic_validation_runtime_collection_package.md")
CHECKLIST_REL_PATH = Path("review/plugin_semantic_validation_runtime_collection_checklist.md")
MANIFEST_CANDIDATE_REL_PATH = Path("review/plugin_semantic_validation_runtime_manifest_candidate.json")
REPORT_TEMPLATE_DIR_REL_PATH = Path("review/plugin_semantic_validation_runtime_report_templates")
QUEUE_REL_PATH = Path("eval_reports/plugin_semantic_validation_queue.json")


def _load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _resolve_report_path(value: Any, output_dir: Path) -> Path:
    path = Path(str(value or ""))
    if path.is_absolute():
        return path
    if path.parts and path.parts[0] == output_dir.name:
        return output_dir.parent / path
    return output_dir / path


def _template_filename(job_id: str, plugin_name: str) -> str:
    base = slugify(job_id or plugin_name)
    return f"{base}_validation_report_template.json"


def _report_template(job: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": PLUGIN_PARAMETER_VALIDATION_REPORT_TEMPLATE_SCHEMA,
        "target_runtime_report_schema": "automix-plugin-parameter-validation-report-v1",
        "job_id": job.get("job_id", ""),
        "plugin_name": job.get("plugin_name", ""),
        "adapter_id": "",
        "status": "template_not_runtime_observed",
        "safe_for_automix": False,
        "no_fake_success": False,
        "controls": {
            "example_semantic_control": {
                "target_name": "",
                "confidence": 0.0,
                "write_allowed": False,
                "validated": False,
                "notes": "Replace this template control only after REAPER runtime response is observed by parameter name or verified helper.",
            }
        },
        "required_fields_for_real_report": [
            "schema=automix-plugin-parameter-validation-report-v1",
            "status=passed only after observed parameter response",
            "safe_for_automix=true only when at least one semantic control is validated and write-safe",
            "no_fake_success=true only when the report is not claiming success without safe controls",
            "controls.<semantic>.target_name",
            "controls.<semantic>.confidence>=0.85",
            "controls.<semantic>.write_allowed=true",
            "controls.<semantic>.validated=true",
        ],
        "limits": [
            "This template is not a validation report.",
            "Do not place this template in automix/analysis_reports as passing evidence.",
            "Do not write parameters from this template.",
        ],
    }


def _manifest_candidate(queue_jobs: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "schema": RUNTIME_MANIFEST_SCHEMA,
        "candidate_only": True,
        "operator_ready_to_run": False,
        "safe_to_write_parameters": False,
        "queue_jobs": [
            {
                "job_id": job.get("job_id", ""),
                "plugin_name": job.get("plugin_name", ""),
                "target_report_path": job.get("target_report_path", ""),
                "operator_acknowledged": False,
                "runtime_observed": False,
                "report_written": False,
                "report_reaudited_by_semantic_gate": False,
            }
            for job in queue_jobs
        ],
        "limits": [
            "This candidate is not operator evidence until every queued job is actually observed in REAPER.",
            "Keep this file as a draft or copy it to plugin_semantic_validation_runtime_manifest.json only after completing the runtime collection.",
            "safe_to_write_parameters must remain false.",
        ],
    }


def _collection_job(job: dict[str, Any], *, output_dir: Path) -> dict[str, Any]:
    target_report_path = _resolve_report_path(job.get("target_report_path", ""), output_dir)
    template_rel = REPORT_TEMPLATE_DIR_REL_PATH / _template_filename(str(job.get("job_id", "")), str(job.get("plugin_name", "")))
    return {
        "job_id": job.get("job_id", ""),
        "plugin_name": job.get("plugin_name", ""),
        "category": job.get("category", "unknown"),
        "priority": int(job.get("priority", 999) or 999),
        "target_report_path": str(target_report_path),
        "target_report_exists": target_report_path.exists(),
        "report_template_path": str(output_dir / template_rel),
        "manifest_candidate_path": str(output_dir / MANIFEST_CANDIDATE_REL_PATH),
        "requires_reaper_runtime": True,
        "requires_temporary_muted_test_context": True,
        "requires_operator_review": True,
        "required_observations": job.get("required_observations", []),
        "acceptance_criteria": job.get("acceptance_criteria", []),
        "disallowed_actions": sorted(set(job.get("disallowed_actions", []) or [])),
        "runtime_collection_steps": [
            "Open a saved test copy or temporary muted REAPER test context.",
            "Insert or locate only the target plugin for this validation job.",
            "Observe parameter names and semantic response without writing to the user's production mix.",
            "Write the real validation report to the target_report_path using schema automix-plugin-parameter-validation-report-v1.",
            "Rerun plugin_semantic_validation_gate.py and record report_reaudited_by_semantic_gate=true only after that gate sees the report.",
        ],
        "job_status": "target_report_present_needs_manifest_review" if target_report_path.exists() else "awaiting_reaper_runtime_collection",
    }


def build_plugin_semantic_validation_runtime_collection_package(
    *,
    project_name: str,
    output_dir: Path,
    queue: dict[str, Any] | None = None,
    queue_path: Path | None = None,
    output_path: Path | None = None,
) -> dict[str, Any]:
    output_dir = Path(output_dir)
    queue_path = queue_path or output_dir / QUEUE_REL_PATH
    queue = queue or _load_json(queue_path)
    blockers: list[str] = []
    warnings: list[str] = []
    if not queue or queue.get("schema") != "automix-plugin-semantic-validation-queue-v1":
        blockers.append("plugin_semantic_validation_queue_missing_or_invalid")
        queue = queue if isinstance(queue, dict) else {}

    queue_jobs = [job for job in queue.get("queue_jobs", []) or [] if isinstance(job, dict)]
    blocked_queue_jobs = [job for job in queue.get("blocked_jobs", []) or [] if isinstance(job, dict)]
    if blocked_queue_jobs:
        warnings.append(f"blocked_queue_jobs_remain:{len(blocked_queue_jobs)}")

    collection_jobs = [
        _collection_job(job, output_dir=output_dir)
        for job in sorted(queue_jobs, key=lambda item: (int(item.get("priority", 999) or 999), str(item.get("plugin_name", "")).lower()))
    ]
    template_dir = output_dir / REPORT_TEMPLATE_DIR_REL_PATH
    template_dir.mkdir(parents=True, exist_ok=True)
    for job, source_job in zip(collection_jobs, sorted(queue_jobs, key=lambda item: (int(item.get("priority", 999) or 999), str(item.get("plugin_name", "")).lower()))):
        write_json(Path(job["report_template_path"]), _report_template(source_job))

    manifest_candidate = _manifest_candidate(collection_jobs)
    write_json(output_dir / MANIFEST_CANDIDATE_REL_PATH, manifest_candidate)

    target_reports_existing = sum(1 for job in collection_jobs if job.get("target_report_exists"))
    target_reports_missing = len(collection_jobs) - target_reports_existing
    status = "runtime_collection_package_ready"
    if blockers:
        status = "runtime_collection_package_blocked"
    elif not collection_jobs:
        status = "no_runtime_collection_jobs"
    elif target_reports_existing == len(collection_jobs):
        status = "runtime_reports_present_manifest_review_required"

    package = {
        "schema": PLUGIN_SEMANTIC_VALIDATION_RUNTIME_COLLECTION_PACKAGE_SCHEMA,
        "project_name": project_name,
        "created_at": now_utc(),
        "output_dir": str(output_dir),
        "source_queue": str(queue_path),
        "status": status,
        "ready_for_runtime_collection": bool(collection_jobs and not blockers),
        "ready_for_runtime_evidence_gate": bool(collection_jobs and target_reports_existing == len(collection_jobs) and not blockers),
        "safe_to_write_parameters": False,
        "requires_reaper_runtime": bool(collection_jobs),
        "requires_operator_review": bool(collection_jobs or blocked_queue_jobs),
        "queue_jobs_total": len(queue_jobs),
        "collection_jobs_total": len(collection_jobs),
        "report_templates_total": len(collection_jobs),
        "target_reports_existing_total": target_reports_existing,
        "target_reports_missing_total": target_reports_missing,
        "blocked_queue_jobs_total": len(blocked_queue_jobs),
        "collection_jobs": collection_jobs,
        "blocked_queue_jobs": blocked_queue_jobs,
        "manifest_candidate_path": str(output_dir / MANIFEST_CANDIDATE_REL_PATH),
        "report_template_dir": str(template_dir),
        "checklist_path": str(output_dir / CHECKLIST_REL_PATH),
        "blockers": sorted(set(blockers)),
        "warnings": sorted(set(warnings)),
        "limits": [
            "This package does not open REAPER, insert FX, write parameters, render, or approve audio.",
            "Report templates use plugin_parameter_validation_report_template schema and are not passing validation evidence.",
            "Only real runtime reports under automix/analysis_reports can satisfy the semantic validation gate.",
        ],
    }
    target = output_path or output_dir / PACKAGE_REL_PATH
    write_json(target, package)
    write_plugin_semantic_validation_runtime_collection_package_report(package, output_dir)
    write_plugin_semantic_validation_runtime_collection_checklist(package, output_dir)
    return package


def write_plugin_semantic_validation_runtime_collection_package_report(package: dict[str, Any], output_dir: Path) -> Path:
    lines = [
        "# Plugin Semantic Validation Runtime Collection Package",
        "",
        f"- Project: `{package.get('project_name')}`",
        f"- Created UTC: `{package.get('created_at')}`",
        f"- Status: `{package.get('status')}`",
        f"- Ready for runtime collection: `{package.get('ready_for_runtime_collection')}`",
        f"- Ready for runtime evidence gate: `{package.get('ready_for_runtime_evidence_gate')}`",
        f"- Collection jobs: `{package.get('collection_jobs_total')}`",
        f"- Target reports existing: `{package.get('target_reports_existing_total')}`",
        f"- Target reports missing: `{package.get('target_reports_missing_total')}`",
        f"- Safe to write parameters: `{package.get('safe_to_write_parameters')}`",
        "",
        "This package prepares runtime collection materials only. It does not grant write safety.",
        "",
        "## Blockers",
        "",
    ]
    lines.extend([f"- `{item}`" for item in package.get("blockers", [])] or ["- none"])
    lines.extend(["", "## Warnings", ""])
    lines.extend([f"- `{item}`" for item in package.get("warnings", [])] or ["- none"])
    lines.extend(["", "## Collection Jobs", ""])
    if not package.get("collection_jobs"):
        lines.append("- none")
    for job in package.get("collection_jobs", []):
        lines.extend(
            [
                f"### {job.get('job_id')}",
                "",
                f"- Plugin: `{job.get('plugin_name')}`",
                f"- Status: `{job.get('job_status')}`",
                f"- Target report: `{job.get('target_report_path')}`",
                f"- Template: `{job.get('report_template_path')}`",
                f"- Target report exists: `{job.get('target_report_exists')}`",
                "",
            ]
        )
    path = Path(output_dir) / PACKAGE_REPORT_REL_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return path


def write_plugin_semantic_validation_runtime_collection_checklist(package: dict[str, Any], output_dir: Path) -> Path:
    lines = [
        "# Plugin Semantic Validation Runtime Collection Checklist",
        "",
        f"- Manifest candidate: `{package.get('manifest_candidate_path')}`",
        f"- Report template directory: `{package.get('report_template_dir')}`",
        f"- Safe to write parameters: `{package.get('safe_to_write_parameters')}`",
        "",
        "Use only a saved test copy or temporary muted REAPER test context. Do not validate on the user's production mix path.",
        "",
        "## Jobs",
        "",
    ]
    if not package.get("collection_jobs"):
        lines.append("- none")
    for job in package.get("collection_jobs", []):
        lines.append(f"### {job.get('job_id')} - {job.get('plugin_name')}")
        lines.append("")
        lines.append(f"- Target report: `{job.get('target_report_path')}`")
        lines.append(f"- Template: `{job.get('report_template_path')}`")
        lines.append("- Steps:")
        lines.extend([f"  - {step}" for step in job.get("runtime_collection_steps", [])])
        lines.append("- Acceptance criteria:")
        lines.extend([f"  - {criterion}" for criterion in job.get("acceptance_criteria", [])] or ["  - none"])
        lines.append("- Disallowed actions:")
        lines.extend([f"  - {action}" for action in job.get("disallowed_actions", [])] or ["  - none"])
        lines.append("")
    lines.extend(
        [
            "## After Collection",
            "",
            "1. Copy or write real validation reports into the listed target report paths.",
            "2. Rerun `python3 scripts/run_plugin_semantic_validation_gate.py --project-name project --output-dir automix`.",
            "3. Fill `automix/review/plugin_semantic_validation_runtime_manifest.json` only after the semantic gate reaudit observes the reports.",
            "4. Rerun `python3 scripts/run_plugin_semantic_validation_runtime_evidence_gate.py --project-name project --output-dir automix`.",
        ]
    )
    path = Path(output_dir) / CHECKLIST_REL_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return path

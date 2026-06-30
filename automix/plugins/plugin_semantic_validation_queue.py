from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from automix.plugins.plugin_adapter_schema import now_utc, slugify, write_json


PLUGIN_SEMANTIC_VALIDATION_QUEUE_SCHEMA = "automix-plugin-semantic-validation-queue-v1"

QUEUE_REL_PATH = Path("eval_reports/plugin_semantic_validation_queue.json")
QUEUE_REPORT_REL_PATH = Path("eval_reports/plugin_semantic_validation_queue.md")
QUEUE_REQUEST_REL_PATH = Path("review/plugin_semantic_validation_queue_request.md")
RUNTIME_MANIFEST_TEMPLATE_REL_PATH = Path("review/plugin_semantic_validation_runtime_manifest_template.json")


def _load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _job_id(plugin_name: str, index: int) -> str:
    return f"semantic_validation_{index:02d}_{slugify(plugin_name)}"


def _queue_job(job: dict[str, Any], *, index: int) -> dict[str, Any]:
    plugin_name = str(job.get("plugin_name", "")).strip()
    return {
        "job_id": _job_id(plugin_name, index),
        "plugin_name": plugin_name,
        "priority": int(job.get("priority", 999) or 999),
        "category": job.get("category", "unknown"),
        "available": bool(job.get("available", False)),
        "collection_action": job.get("collection_action", ""),
        "source_action_id": job.get("source_action_id", ""),
        "target_report_path": job.get("target_report_path", ""),
        "expected_report_glob": job.get("expected_report_glob", ""),
        "matching_reports_total": int(job.get("matching_reports_total", 0) or 0),
        "passed_reports_total": int(job.get("passed_reports_total", 0) or 0),
        "safe_control_count": int(job.get("safe_control_count", 0) or 0),
        "requires_reaper_runtime": True,
        "requires_temporary_muted_test_context": True,
        "requires_operator_review": True,
        "report_must_be_reaudited_by_semantic_gate": True,
        "required_observations": job.get("required_observations", []),
        "acceptance_criteria": job.get("acceptance_criteria", []),
        "source_blockers": job.get("source_blockers", []),
        "warnings": job.get("warnings", []),
        "disallowed_actions": [
            "do not validate on a production track without a saved test copy or temporary muted test context",
            "do not write parameters to the user's mix from this queue",
            "do not mark a report passed from plugin availability alone",
            "do not use fixed parameter indexes unless observed in the target REAPER runtime",
        ],
    }


def _blocked_job(job: dict[str, Any]) -> dict[str, Any]:
    return {
        "plugin_name": job.get("plugin_name", ""),
        "collection_action": job.get("collection_action", ""),
        "blockers": job.get("blockers", []),
        "operator_resolution": job.get("operator_resolution", ""),
        "operator_acknowledged": bool(job.get("operator_acknowledged", False)),
    }


def _runtime_manifest_template(queue: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": "automix-plugin-semantic-validation-runtime-manifest-template-v1",
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
            for job in queue.get("queue_jobs", [])
        ],
        "limits": [
            "This manifest is not a validation report.",
            "Runtime observation must be converted into plugin_parameter_validation_*.json reports.",
            "Do not write parameters before semantic validation gate passes after report collection.",
        ],
    }


def build_plugin_semantic_validation_queue(
    *,
    project_name: str,
    output_dir: Path,
    collection_plan: dict[str, Any] | None = None,
    collection_plan_path: Path | None = None,
    output_path: Path | None = None,
) -> dict[str, Any]:
    output_dir = Path(output_dir)
    collection_plan_path = collection_plan_path or output_dir / "eval_reports/plugin_semantic_validation_collection_plan.json"
    collection_plan = collection_plan or _load_json(collection_plan_path)
    jobs = [
        job
        for job in collection_plan.get("validation_jobs", []) or []
        if isinstance(job, dict)
    ]
    collectable = sorted(
        [job for job in jobs if job.get("collectable_in_reaper")],
        key=lambda item: (int(item.get("priority", 999) or 999), str(item.get("plugin_name", "")).lower()),
    )
    queue_jobs = [_queue_job(job, index=index + 1) for index, job in enumerate(collectable)]
    blocked = [
        _blocked_job(job)
        for job in jobs
        if not job.get("collectable_in_reaper") and not job.get("resolved_without_collection") and job.get("collection_action") != "already_write_safe"
    ]
    blockers: list[str] = []
    if not collection_plan:
        blockers.append("plugin_semantic_validation_collection_plan_missing_or_invalid")
    blockers.extend(
        f"collection_job_blocked:{item.get('plugin_name')}:{blocker}"
        for item in blocked
        for blocker in item.get("blockers", [])
    )
    status = "no_collectable_semantic_validation_jobs"
    if queue_jobs and blocked:
        status = "queue_ready_with_blocked_unavailable_decisions"
    elif queue_jobs:
        status = "queue_ready"
    elif blockers:
        status = "queue_blocked"
    queue = {
        "schema": PLUGIN_SEMANTIC_VALIDATION_QUEUE_SCHEMA,
        "project_name": project_name,
        "created_at": now_utc(),
        "output_dir": str(output_dir),
        "source_collection_plan": str(collection_plan_path),
        "collection_plan_status": collection_plan.get("status", ""),
        "queue_jobs_total": len(queue_jobs),
        "blocked_jobs_total": len(blocked),
        "ready_to_run_reaper_collection": bool(queue_jobs),
        "all_collection_jobs_queued": bool(jobs and len(queue_jobs) + sum(1 for job in jobs if job.get("resolved_without_collection") or job.get("collection_action") == "already_write_safe") == len(jobs)),
        "safe_to_write_parameters": False,
        "requires_reaper_runtime": bool(queue_jobs),
        "requires_operator_review": bool(queue_jobs or blocked),
        "queue_jobs": queue_jobs,
        "blocked_jobs": blocked,
        "next_queue_job": queue_jobs[0] if queue_jobs else {},
        "blockers": sorted(set(blockers)),
        "warnings": sorted({warning for job in queue_jobs for warning in job.get("warnings", [])}),
        "status": status,
        "limits": [
            "This queue does not open REAPER, insert FX, write parameters, render, or approve audio.",
            "Queue jobs must write plugin_parameter_validation reports that are audited again by plugin_semantic_validation_gate.",
            "Do not write parameters before semantic validation gate passes and the collection queue has no open jobs.",
        ],
    }
    write_json(output_dir / RUNTIME_MANIFEST_TEMPLATE_REL_PATH, _runtime_manifest_template(queue))
    target = output_path or output_dir / QUEUE_REL_PATH
    write_json(target, queue)
    write_plugin_semantic_validation_queue_report(queue, output_dir)
    write_plugin_semantic_validation_queue_request(queue, output_dir)
    return queue


def write_plugin_semantic_validation_queue_report(queue: dict[str, Any], output_dir: Path) -> Path:
    lines = [
        "# Plugin Semantic Validation Queue",
        "",
        f"- Project: `{queue.get('project_name')}`",
        f"- Created UTC: `{queue.get('created_at')}`",
        f"- Status: `{queue.get('status')}`",
        f"- Queue jobs: `{queue.get('queue_jobs_total')}`",
        f"- Blocked jobs: `{queue.get('blocked_jobs_total')}`",
        f"- Ready to run REAPER collection: `{queue.get('ready_to_run_reaper_collection')}`",
        f"- Safe to write parameters: `{queue.get('safe_to_write_parameters')}`",
        "",
        "This queue packages REAPER-observed semantic validation jobs. It does not grant write safety.",
        "",
        "## Blockers",
        "",
    ]
    lines.extend([f"- `{item}`" for item in queue.get("blockers", [])] or ["- none"])
    lines.extend(["", "## Next Queue Job", ""])
    next_job = queue.get("next_queue_job", {})
    if next_job:
        lines.append(f"- `{next_job.get('job_id')}` `{next_job.get('plugin_name')}` -> `{next_job.get('target_report_path')}`")
    else:
        lines.append("- none")
    lines.extend(["", "## Queue Jobs", ""])
    if not queue.get("queue_jobs"):
        lines.append("- none")
    for job in queue.get("queue_jobs", []):
        lines.extend(
            [
                f"### {job.get('job_id')}",
                "",
                f"- Plugin: `{job.get('plugin_name')}`",
                f"- Action: `{job.get('collection_action')}`",
                f"- Target report: `{job.get('target_report_path')}`",
                f"- Requires temporary muted test context: `{job.get('requires_temporary_muted_test_context')}`",
                f"- Disallowed actions: `{job.get('disallowed_actions', [])}`",
                "",
            ]
        )
    lines.extend(["", "## Blocked Jobs", ""])
    if not queue.get("blocked_jobs"):
        lines.append("- none")
    for job in queue.get("blocked_jobs", []):
        lines.append(f"- `{job.get('plugin_name')}`: `{job.get('blockers', [])}`")
    path = Path(output_dir) / QUEUE_REPORT_REL_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return path


def write_plugin_semantic_validation_queue_request(queue: dict[str, Any], output_dir: Path) -> Path:
    lines = [
        "# Plugin Semantic Validation Queue Request",
        "",
        f"- Project: `{queue.get('project_name')}`",
        f"- Runtime manifest template: `{Path(output_dir) / RUNTIME_MANIFEST_TEMPLATE_REL_PATH}`",
        f"- Queue jobs: `{queue.get('queue_jobs_total')}`",
        f"- Blocked jobs: `{queue.get('blocked_jobs_total')}`",
        "",
        "Run these only in a saved test copy or temporary muted test context. Convert observations into validation reports, then rerun the semantic validation gate.",
        "",
        "## Queue",
        "",
    ]
    if not queue.get("queue_jobs"):
        lines.append("- none")
    for job in queue.get("queue_jobs", []):
        lines.append(f"- `{job.get('job_id')}` `{job.get('plugin_name')}` -> `{job.get('target_report_path')}`")
    lines.extend(["", "## Blocked Jobs", ""])
    if not queue.get("blocked_jobs"):
        lines.append("- none")
    for job in queue.get("blocked_jobs", []):
        lines.append(f"- `{job.get('plugin_name')}`: `{job.get('blockers', [])}`")
    path = Path(output_dir) / QUEUE_REQUEST_REL_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return path

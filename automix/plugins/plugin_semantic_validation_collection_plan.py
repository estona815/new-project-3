from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from automix.plugins.plugin_adapter_schema import compact_plugin_name, now_utc, slugify, write_json


PLUGIN_SEMANTIC_VALIDATION_COLLECTION_PLAN_SCHEMA = "automix-plugin-semantic-validation-collection-plan-v1"

PLAN_REL_PATH = Path("eval_reports/plugin_semantic_validation_collection_plan.json")
PLAN_REPORT_REL_PATH = Path("eval_reports/plugin_semantic_validation_collection_plan.md")
REQUEST_REL_PATH = Path("review/plugin_semantic_validation_collection_request.md")
MANIFEST_TEMPLATE_REL_PATH = Path("review/plugin_semantic_validation_collection_manifest_template.json")


def _load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _decision_by_plugin(decision_gate: dict[str, Any]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for item in decision_gate.get("decisions", []) or []:
        if not isinstance(item, dict):
            continue
        name = str(item.get("plugin_name", "")).strip()
        if name:
            out[compact_plugin_name(name)] = item
    return out


def _target_report_path(output_dir: Path, plugin_name: str, suffix: str = "reaper_observed") -> str:
    return str(output_dir / "analysis_reports" / f"plugin_parameter_validation_{slugify(plugin_name)}_{suffix}.json")


def _semantic_job(plugin_action: dict[str, Any], *, output_dir: Path, decision_gate: dict[str, Any]) -> dict[str, Any]:
    plugin_name = str(plugin_action.get("plugin_name", "")).strip()
    action_id = str(plugin_action.get("action_id", ""))
    source_blockers = sorted(set(plugin_action.get("source_blockers", []) or []))
    source_warnings = sorted(set(plugin_action.get("source_warnings", []) or []))
    blockers: list[str] = []
    warnings: list[str] = []
    decision_lookup = _decision_by_plugin(decision_gate)
    decision = decision_lookup.get(compact_plugin_name(plugin_name), {})

    if action_id == "plugin_write_safe_ready":
        collection_action = "already_write_safe"
        target_report = str(plugin_action.get("expected_report_glob", ""))
        collectable = False
        resolved = True
    elif action_id == "install_or_disable_unavailable_plugin":
        operator_resolution = str(decision.get("operator_resolution", ""))
        if not decision.get("operator_acknowledged", False):
            blockers.append(f"availability_decision_missing:{plugin_name}")
            collection_action = "operator_availability_decision_required"
        elif operator_resolution in {"disable_for_automatic_drafts", "manual_review_only", "keep_unavailable_blocked"}:
            collection_action = "skip_disabled_or_manual_review_unavailable_plugin"
        elif operator_resolution == "install_and_rerun_preflight":
            blockers.append(f"installed_plugin_requires_preflight_rerun:{plugin_name}")
            collection_action = "rerun_preflight_after_install"
        else:
            blockers.append(f"availability_resolution_unknown:{plugin_name}")
            collection_action = "operator_availability_decision_required"
        target_report = _target_report_path(output_dir, plugin_name, "after_install_reaper_observed")
        collectable = False
        resolved = collection_action == "skip_disabled_or_manual_review_unavailable_plugin" and not blockers
    elif action_id == "collect_reaper_observed_semantic_validation":
        collection_action = "collect_missing_reaper_observed_semantic_report"
        target_report = _target_report_path(output_dir, plugin_name)
        collectable = True
        resolved = False
    elif action_id in {"rerun_or_keep_plugin_read_only", "safe_controls_missing"}:
        collection_action = "rerun_failed_semantic_report_or_keep_read_only"
        target_report = _target_report_path(output_dir, plugin_name, "rerun_reaper_observed")
        collectable = True
        resolved = False
    elif action_id == "collect_plugin_availability_preflight":
        blockers.append(f"plugin_availability_preflight_missing:{plugin_name}")
        collection_action = "collect_plugin_availability_preflight_first"
        target_report = _target_report_path(output_dir, plugin_name)
        collectable = False
        resolved = False
    else:
        blockers.append(f"semantic_collection_action_unknown:{plugin_name}:{action_id}")
        collection_action = "manual_review_required"
        target_report = _target_report_path(output_dir, plugin_name)
        collectable = False
        resolved = False

    if source_warnings:
        warnings.extend(item if str(item).startswith(f"{plugin_name}:") else f"{plugin_name}:{item}" for item in source_warnings)

    return {
        "plugin_name": plugin_name,
        "source_action_id": action_id,
        "collection_action": collection_action,
        "priority": int(plugin_action.get("priority", 999) or 999),
        "category": plugin_action.get("category", "unknown"),
        "available": bool(plugin_action.get("available", False)),
        "collectable_in_reaper": collectable,
        "resolved_without_collection": resolved,
        "expected_report_glob": plugin_action.get("expected_report_glob", ""),
        "target_report_path": target_report,
        "matching_reports_total": int(plugin_action.get("matching_reports_total", 0) or 0),
        "passed_reports_total": int(plugin_action.get("passed_reports_total", 0) or 0),
        "safe_control_count": int(plugin_action.get("safe_control_count", 0) or 0),
        "operator_resolution": decision.get("operator_resolution", ""),
        "operator_acknowledged": bool(decision.get("operator_acknowledged", False)),
        "required_observations": [
            "REAPER runtime observed the exact plugin or accepted installed substitute",
            "semantic parameter response observed by name or verified helper, not guessed from index order",
            "status=passed only when the report has at least one validated write-safe semantic control",
            "safe_for_automix=true and no_fake_success=true only after observed response evidence",
            "safe min/max bounds recorded for every write_allowed semantic control",
        ],
        "acceptance_criteria": [
            "report schema is automix-plugin-parameter-validation-report-v1",
            "status=passed",
            "safe_for_automix=true",
            "no_fake_success=true",
            "at least one control has validated=true, write_allowed=true, confidence>=0.85, and target_name",
        ],
        "source_blockers": source_blockers,
        "source_warnings": source_warnings,
        "blockers": sorted(set(blockers)),
        "warnings": sorted(set(warnings)),
        "disallowed_actions": [
            "Do not write parameters before this collection plan has no open jobs.",
            "Do not mark validation passed from plugin availability alone.",
            "Do not use fixed parameter indexes unless observed in the target REAPER runtime.",
            "Do not treat a fallback candidate as proof that the unavailable plugin loaded.",
        ],
    }


def _manifest_template(plan: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": "automix-plugin-semantic-validation-collection-manifest-template-v1",
        "operator_ready_to_run": False,
        "validation_jobs": [
            {
                "plugin_name": job.get("plugin_name", ""),
                "collection_action": job.get("collection_action", ""),
                "target_report_path": job.get("target_report_path", ""),
                "collectable_in_reaper": job.get("collectable_in_reaper", False),
                "required_observations": job.get("required_observations", []),
                "operator_acknowledged": False,
            }
            for job in plan.get("validation_jobs", [])
            if job.get("collectable_in_reaper")
        ],
        "limits": [
            "This template is a checklist for REAPER-observed semantic validation collection, not a validation report.",
            "Do not write parameters before this collection plan has no open jobs.",
            "Generated validation reports must be audited again by plugin_semantic_validation_gate.",
        ],
    }


def build_plugin_semantic_validation_collection_plan(
    *,
    project_name: str,
    output_dir: Path,
    action_plan: dict[str, Any] | None = None,
    semantic_gate: dict[str, Any] | None = None,
    decision_gate: dict[str, Any] | None = None,
    action_plan_path: Path | None = None,
    semantic_gate_path: Path | None = None,
    decision_gate_path: Path | None = None,
    output_path: Path | None = None,
) -> dict[str, Any]:
    output_dir = Path(output_dir)
    action_plan_path = action_plan_path or output_dir / "eval_reports/plugin_validation_action_plan.json"
    semantic_gate_path = semantic_gate_path or output_dir / "eval_reports/plugin_semantic_validation_gate.json"
    decision_gate_path = decision_gate_path or output_dir / "eval_reports/plugin_availability_decision_gate.json"
    action_plan = action_plan or _load_json(action_plan_path)
    semantic_gate = semantic_gate or _load_json(semantic_gate_path)
    decision_gate = decision_gate or _load_json(decision_gate_path)

    jobs = [
        _semantic_job(item, output_dir=output_dir, decision_gate=decision_gate)
        for item in action_plan.get("plugin_actions", []) or []
        if isinstance(item, dict)
    ]
    open_jobs = [
        job
        for job in jobs
        if job.get("collection_action") not in {"already_write_safe", "skip_disabled_or_manual_review_unavailable_plugin"}
    ]
    collectable_jobs = [job for job in open_jobs if job.get("collectable_in_reaper")]
    decision_blocked = [job for job in open_jobs if job.get("collection_action") == "operator_availability_decision_required"]
    blockers = sorted({blocker for job in jobs for blocker in job.get("blockers", [])})
    if not action_plan:
        blockers.append("plugin_validation_action_plan_missing_or_invalid")
    if not semantic_gate:
        blockers.append("plugin_semantic_validation_gate_missing_or_invalid")
    if decision_blocked and not decision_gate:
        blockers.append("plugin_availability_decision_gate_missing_or_invalid")
    status = "semantic_validation_collection_not_required" if not open_jobs and not blockers else "semantic_validation_collection_required"
    if decision_blocked:
        status = "availability_decisions_required_before_full_collection"

    plan = {
        "schema": PLUGIN_SEMANTIC_VALIDATION_COLLECTION_PLAN_SCHEMA,
        "project_name": project_name,
        "created_at": now_utc(),
        "output_dir": str(output_dir),
        "source_action_plan": str(action_plan_path),
        "source_semantic_gate": str(semantic_gate_path),
        "source_decision_gate": str(decision_gate_path),
        "semantic_validation_ready": bool(semantic_gate.get("semantic_validation_ready", False)),
        "safe_to_write_parameters": False,
        "required_plugins_total": int(action_plan.get("required_plugins_total", 0) or len(jobs)),
        "validation_jobs_total": len(jobs),
        "open_jobs_total": len(open_jobs),
        "collectable_jobs_total": len(collectable_jobs),
        "decision_blocked_jobs_total": len(decision_blocked),
        "ready_plugins_total": sum(1 for job in jobs if job.get("collection_action") == "already_write_safe"),
        "resolved_without_collection_total": sum(1 for job in jobs if job.get("resolved_without_collection")),
        "ready_to_collect_some_in_reaper": bool(collectable_jobs),
        "all_jobs_resolved": bool(jobs and not open_jobs and not blockers),
        "next_collection_job": sorted(open_jobs, key=lambda item: (0 if item.get("collectable_in_reaper") else 1, int(item.get("priority", 999) or 999), item.get("plugin_name", "")))[0] if open_jobs else {},
        "validation_jobs": jobs,
        "blockers": sorted(set(blockers)),
        "warnings": sorted({warning for job in jobs for warning in job.get("warnings", [])}),
        "status": status,
        "limits": [
            "This plan does not open REAPER, insert FX, write parameters, render, or approve audio.",
            "REAPER-observed semantic validation is still required before automatic parameter writes.",
            "Do not write parameters before this collection plan has no open jobs.",
        ],
    }
    write_json(output_dir / MANIFEST_TEMPLATE_REL_PATH, _manifest_template(plan))
    target = output_path or output_dir / PLAN_REL_PATH
    write_json(target, plan)
    write_plugin_semantic_validation_collection_report(plan, output_dir)
    write_plugin_semantic_validation_collection_request(plan, output_dir)
    return plan


def write_plugin_semantic_validation_collection_report(plan: dict[str, Any], output_dir: Path) -> Path:
    lines = [
        "# Plugin Semantic Validation Collection Plan",
        "",
        f"- Project: `{plan.get('project_name')}`",
        f"- Created UTC: `{plan.get('created_at')}`",
        f"- Status: `{plan.get('status')}`",
        f"- Open jobs: `{plan.get('open_jobs_total')}`",
        f"- Collectable in REAPER: `{plan.get('collectable_jobs_total')}`",
        f"- Decision-blocked jobs: `{plan.get('decision_blocked_jobs_total')}`",
        f"- Safe to write parameters: `{plan.get('safe_to_write_parameters')}`",
        "",
        "This report sequences REAPER-observed semantic validation collection. It does not grant write safety.",
        "",
        "## Blockers",
        "",
    ]
    lines.extend([f"- `{item}`" for item in plan.get("blockers", [])] or ["- none"])
    lines.extend(["", "## Next Job", ""])
    next_job = plan.get("next_collection_job", {})
    if next_job:
        lines.append(f"- `{next_job.get('plugin_name')}`: `{next_job.get('collection_action')}` -> `{next_job.get('target_report_path')}`")
    else:
        lines.append("- none")
    lines.extend(["", "## Jobs", ""])
    if not plan.get("validation_jobs"):
        lines.append("- none")
    for job in plan.get("validation_jobs", []):
        lines.extend(
            [
                f"### {job.get('plugin_name')}",
                "",
                f"- Action: `{job.get('collection_action')}`",
                f"- Collectable in REAPER: `{job.get('collectable_in_reaper')}`",
                f"- Target report: `{job.get('target_report_path')}`",
                f"- Source blockers: `{job.get('source_blockers', [])}`",
                f"- Blockers: `{job.get('blockers', [])}`",
                "",
            ]
        )
    path = Path(output_dir) / PLAN_REPORT_REL_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return path


def write_plugin_semantic_validation_collection_request(plan: dict[str, Any], output_dir: Path) -> Path:
    lines = [
        "# Plugin Semantic Validation Collection Request",
        "",
        f"- Project: `{plan.get('project_name')}`",
        f"- Manifest template: `{Path(output_dir) / MANIFEST_TEMPLATE_REL_PATH}`",
        f"- Open jobs: `{plan.get('open_jobs_total')}`",
        f"- Collectable jobs: `{plan.get('collectable_jobs_total')}`",
        "",
        "Collect only REAPER-observed semantic validation evidence. Availability alone is not write safety.",
        "",
        "## Collectable Jobs",
        "",
    ]
    collectable = [job for job in plan.get("validation_jobs", []) if job.get("collectable_in_reaper")]
    if not collectable:
        lines.append("- none")
    for job in collectable:
        lines.append(f"- `{job.get('plugin_name')}` -> `{job.get('target_report_path')}`")
    lines.extend(["", "## Blocked Jobs", ""])
    blocked = [job for job in plan.get("validation_jobs", []) if job.get("blockers")]
    if not blocked:
        lines.append("- none")
    for job in blocked:
        lines.append(f"- `{job.get('plugin_name')}`: `{job.get('blockers', [])}`")
    path = Path(output_dir) / REQUEST_REL_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return path

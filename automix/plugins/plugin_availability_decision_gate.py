from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from automix.plugins.plugin_adapter_schema import compact_plugin_name, now_utc, write_json


PLUGIN_AVAILABILITY_DECISION_GATE_SCHEMA = "automix-plugin-availability-decision-gate-v1"
ACCEPTED_DISABLE_MANIFEST_SCHEMA = "automix-plugin-availability-disable-manifest-v1"

GATE_REL_PATH = Path("eval_reports/plugin_availability_decision_gate.json")
GATE_REPORT_REL_PATH = Path("eval_reports/plugin_availability_decision_gate.md")
REQUEST_REL_PATH = Path("review/plugin_availability_decision_request.md")
DEFAULT_DECISION_MANIFEST_REL_PATH = Path("review/plugin_availability_disable_manifest.json")

ALLOWED_RESOLUTIONS = {
    "disable_for_automatic_drafts",
    "manual_review_only",
    "keep_unavailable_blocked",
    "install_and_rerun_preflight",
}


def _load_json(path: Path) -> tuple[dict[str, Any], str | None]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        return {}, f"read_error:{exc}"
    except json.JSONDecodeError as exc:
        return {}, f"json_decode_error:{exc}"
    if not isinstance(data, dict):
        return {}, "json_type_error:expected_object"
    return data, None


def _required_decisions(plan: dict[str, Any]) -> list[str]:
    names: dict[str, str] = {}
    for raw in plan.get("pending_operator_decisions", []) or []:
        name = str(raw).strip()
        if name:
            names.setdefault(compact_plugin_name(name), name)
    for item in plan.get("resolutions", []) or []:
        if not isinstance(item, dict) or not item.get("operator_decision_required", False):
            continue
        name = str(item.get("plugin_name", "")).strip()
        if name:
            names.setdefault(compact_plugin_name(name), name)
    return sorted(names.values(), key=lambda value: value.lower())


def _resolution_lookup(plan: dict[str, Any]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for item in plan.get("resolutions", []) or []:
        if not isinstance(item, dict):
            continue
        name = str(item.get("plugin_name", "")).strip()
        if name:
            out[compact_plugin_name(name)] = item
    return out


def _manifest_lookup(manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for item in manifest.get("disabled_plugins", []) or []:
        if not isinstance(item, dict):
            continue
        name = str(item.get("plugin_name", "")).strip()
        if name:
            out[compact_plugin_name(name)] = item
    return out


def _decision_for(plugin_name: str, *, expected: dict[str, Any], manifest_entry: dict[str, Any] | None) -> dict[str, Any]:
    blockers: list[str] = []
    warnings: list[str] = []
    entry = manifest_entry or {}
    resolution = str(entry.get("resolution", "")).strip()
    fallback_candidate = str(entry.get("fallback_candidate", "") or expected.get("fallback_candidate", "") or "")
    fallback_requires_validation = bool(entry.get("fallback_requires_validation", False))
    operator_acknowledged = bool(entry.get("operator_acknowledged", False))
    automatic_writes = bool(entry.get("automatic_parameter_writes_allowed", False))

    if not manifest_entry:
        blockers.append(f"operator_decision_missing:{plugin_name}")
    if manifest_entry:
        if not resolution:
            blockers.append(f"operator_resolution_missing:{plugin_name}")
        if resolution and resolution not in ALLOWED_RESOLUTIONS:
            blockers.append(f"operator_resolution_unsupported:{plugin_name}:{resolution}")
        if not operator_acknowledged:
            blockers.append(f"operator_acknowledgement_missing:{plugin_name}")
        if automatic_writes:
            blockers.append(f"unavailable_plugin_parameter_write_not_allowed:{plugin_name}")
        if fallback_candidate and not fallback_requires_validation:
            blockers.append(f"fallback_validation_requirement_missing:{plugin_name}")
        if resolution == "install_and_rerun_preflight":
            blockers.append(f"installed_plugin_requires_preflight_rerun:{plugin_name}")
    recommended = str(expected.get("recommended_resolution", ""))
    if manifest_entry and resolution and recommended in {"disable_for_automatic_drafts", "manual_review_only"} and resolution != recommended:
        warnings.append(f"operator_resolution_differs_from_recommendation:{plugin_name}:{recommended}->{resolution}")

    return {
        "plugin_name": plugin_name,
        "recommended_resolution": recommended,
        "operator_resolution": resolution,
        "fallback_candidate": fallback_candidate,
        "fallback_requires_validation": fallback_requires_validation,
        "operator_acknowledged": operator_acknowledged,
        "automatic_parameter_writes_allowed": automatic_writes,
        "status": "accepted" if not blockers else "blocked",
        "blockers": sorted(set(blockers)),
        "warnings": sorted(set(warnings)),
    }


def build_plugin_availability_decision_gate(
    *,
    project_name: str,
    output_dir: Path,
    resolution_plan: dict[str, Any] | None = None,
    resolution_plan_path: Path | None = None,
    decision_manifest_path: Path | None = None,
    output_path: Path | None = None,
) -> dict[str, Any]:
    output_dir = Path(output_dir)
    resolution_plan_path = resolution_plan_path or output_dir / "eval_reports/plugin_availability_resolution_plan.json"
    decision_manifest_path = decision_manifest_path or output_dir / DEFAULT_DECISION_MANIFEST_REL_PATH
    resolution_plan = resolution_plan or {}

    plan_error: str | None = None
    if not resolution_plan:
        resolution_plan, plan_error = _load_json(resolution_plan_path)

    manifest: dict[str, Any] = {}
    manifest_error: str | None = None
    manifest_exists = decision_manifest_path.exists()
    if manifest_exists:
        manifest, manifest_error = _load_json(decision_manifest_path)

    required = _required_decisions(resolution_plan)
    expected_by_name = _resolution_lookup(resolution_plan)
    manifest_by_name = _manifest_lookup(manifest)

    blockers: list[str] = []
    warnings: list[str] = []
    if plan_error or not resolution_plan:
        blockers.append("plugin_availability_resolution_plan_missing_or_invalid")
    if manifest_error:
        blockers.append("plugin_availability_decision_manifest_invalid_json")
    if manifest.get("schema") == "automix-plugin-availability-disable-manifest-template-v1":
        blockers.append("plugin_availability_decision_manifest_is_template")
    if required and not manifest_exists:
        blockers.append("plugin_availability_decision_manifest_missing")
    if required and manifest_exists and manifest.get("schema") != ACCEPTED_DISABLE_MANIFEST_SCHEMA:
        blockers.append("plugin_availability_decision_manifest_schema_invalid")

    decisions = [
        _decision_for(
            plugin_name,
            expected=expected_by_name.get(compact_plugin_name(plugin_name), {}),
            manifest_entry=manifest_by_name.get(compact_plugin_name(plugin_name)),
        )
        for plugin_name in required
    ]
    for decision in decisions:
        blockers.extend(decision.get("blockers", []))
        warnings.extend(decision.get("warnings", []))

    missing_decisions = [item["plugin_name"] for item in decisions if any(str(blocker).startswith("operator_decision_missing:") for blocker in item.get("blockers", []))]
    blockers = sorted(set(blockers))
    warnings = sorted(set(warnings))
    if plan_error or not resolution_plan:
        status = "resolution_plan_missing"
    elif not required and not blockers:
        status = "no_unavailable_plugins_to_resolve"
    elif not manifest_exists:
        status = "operator_decision_manifest_missing"
    elif blockers:
        status = "operator_decision_blocked"
    else:
        status = "operator_decisions_ready"
    ready = status in {"no_unavailable_plugins_to_resolve", "operator_decisions_ready"}

    gate = {
        "schema": PLUGIN_AVAILABILITY_DECISION_GATE_SCHEMA,
        "project_name": project_name,
        "created_at": now_utc(),
        "output_dir": str(output_dir),
        "source_resolution_plan": str(resolution_plan_path),
        "decision_manifest": str(decision_manifest_path),
        "decision_manifest_exists": manifest_exists,
        "decision_manifest_schema": manifest.get("schema", ""),
        "required_decisions_total": len(required),
        "required_decisions": required,
        "accepted_decisions_total": sum(1 for item in decisions if item.get("status") == "accepted"),
        "missing_decisions": missing_decisions,
        "decisions": decisions,
        "availability_decisions_ready": ready,
        "ready_for_plugin_preflight_rerun": ready,
        "safe_to_write_parameters": False,
        "status": status,
        "blockers": blockers,
        "warnings": warnings,
        "limits": [
            "This gate does not install plugins, open REAPER, write parameters, render, or approve audio.",
            "Fallback writes remain blocked until semantic validation reports pass.",
            "A disabled unavailable plugin is not evidence that a fallback plugin was used.",
        ],
    }
    target = output_path or output_dir / GATE_REL_PATH
    write_json(target, gate)
    write_plugin_availability_decision_report(gate, output_dir)
    write_plugin_availability_decision_request(gate, output_dir)
    return gate


def write_plugin_availability_decision_report(gate: dict[str, Any], output_dir: Path) -> Path:
    lines = [
        "# Plugin Availability Decision Gate",
        "",
        f"- Project: `{gate.get('project_name')}`",
        f"- Created UTC: `{gate.get('created_at')}`",
        f"- Status: `{gate.get('status')}`",
        f"- Availability decisions ready: `{gate.get('availability_decisions_ready')}`",
        f"- Safe to write parameters: `{gate.get('safe_to_write_parameters')}`",
        f"- Decision manifest: `{gate.get('decision_manifest')}`",
        "",
        "Fallback writes remain blocked until semantic validation reports pass.",
        "",
        "## Blockers",
        "",
    ]
    lines.extend([f"- `{item}`" for item in gate.get("blockers", [])] or ["- none"])
    lines.extend(["", "## Decisions", ""])
    if not gate.get("decisions"):
        lines.append("- none")
    for item in gate.get("decisions", []):
        lines.extend(
            [
                f"### {item.get('plugin_name')}",
                "",
                f"- Status: `{item.get('status')}`",
                f"- Operator resolution: `{item.get('operator_resolution')}`",
                f"- Operator acknowledged: `{item.get('operator_acknowledged')}`",
                f"- Automatic parameter writes allowed: `{item.get('automatic_parameter_writes_allowed')}`",
                f"- Fallback candidate: `{item.get('fallback_candidate')}`",
                f"- Fallback requires validation: `{item.get('fallback_requires_validation')}`",
                f"- Blockers: `{item.get('blockers', [])}`",
                "",
            ]
        )
    path = Path(output_dir) / GATE_REPORT_REL_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return path


def write_plugin_availability_decision_request(gate: dict[str, Any], output_dir: Path) -> Path:
    lines = [
        "# Plugin Availability Decision Request",
        "",
        f"- Project: `{gate.get('project_name')}`",
        f"- Required decisions: `{gate.get('required_decisions_total')}`",
        f"- Accepted manifest path: `{gate.get('decision_manifest')}`",
        "",
        "Create an accepted manifest at the path above with schema `automix-plugin-availability-disable-manifest-v1`.",
        "Each unavailable plugin needs `operator_acknowledged=true`, `automatic_parameter_writes_allowed=false`, and fallback validation still required when a fallback candidate is listed.",
        "",
        "## Required Plugins",
        "",
    ]
    if not gate.get("required_decisions"):
        lines.append("- none")
    else:
        lines.extend([f"- `{name}`" for name in gate.get("required_decisions", [])])
    lines.extend(["", "## Current Blockers", ""])
    lines.extend([f"- `{item}`" for item in gate.get("blockers", [])] or ["- none"])
    path = Path(output_dir) / REQUEST_REL_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return path

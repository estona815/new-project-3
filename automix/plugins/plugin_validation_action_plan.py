from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from automix.plugins.plugin_adapter_schema import compact_plugin_name, now_utc, slugify, write_json


PLUGIN_VALIDATION_ACTION_PLAN_SCHEMA = "automix-plugin-validation-action-plan-v1"

ACTION_PLAN_REL_PATH = Path("eval_reports/plugin_validation_action_plan.json")
ACTION_PLAN_REPORT_REL_PATH = Path("eval_reports/plugin_validation_action_plan.md")
ACTION_REQUEST_REL_PATH = Path("review/plugin_validation_action_request.md")


def _load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _severity_rank(severity: str) -> int:
    return {"blocker": 0, "warning": 1, "review": 2, "info": 3}.get(str(severity), 9)


def _availability_by_plugin(preflight: dict[str, Any]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for item in preflight.get("availability", []) or []:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name", "")).strip()
        if name:
            out[compact_plugin_name(name)] = item
    return out


def _semantic_by_plugin(gate: dict[str, Any]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for item in gate.get("plugin_results", []) or []:
        if not isinstance(item, dict):
            continue
        name = str(item.get("plugin_name", "")).strip()
        if name:
            out[compact_plugin_name(name)] = item
    return out


def _required_plugin_names(preflight: dict[str, Any], gate: dict[str, Any]) -> list[str]:
    names: dict[str, str] = {}
    for raw in preflight.get("required_plugins", []) or []:
        name = str(raw).strip()
        if name:
            names.setdefault(compact_plugin_name(name), name)
    for raw in gate.get("required_plugins", []) or []:
        name = str(raw).strip()
        if name:
            names.setdefault(compact_plugin_name(name), name)
    for item in gate.get("plugin_results", []) or []:
        if isinstance(item, dict):
            name = str(item.get("plugin_name", "")).strip()
            if name:
                names.setdefault(compact_plugin_name(name), name)
    return sorted(names.values(), key=lambda value: value.lower())


def _expected_report_glob(plugin_name: str) -> str:
    return f"automix/analysis_reports/plugin_parameter_validation_{slugify(plugin_name)}*.json"


def _plugin_action(plugin_name: str, availability: dict[str, Any], semantic: dict[str, Any]) -> dict[str, Any]:
    available = bool(availability.get("available", False)) if availability else False
    category = availability.get("category", "unknown") if availability else "unknown"
    matching_reports = int(semantic.get("matching_reports_total", 0) or 0) if semantic else 0
    passed_reports = int(semantic.get("passed_reports_total", 0) or 0) if semantic else 0
    safe_controls = int(semantic.get("safe_control_count", 0) or 0) if semantic else 0
    semantic_passed = bool(semantic.get("semantic_validation_passed", False)) if semantic else False

    if not availability:
        severity = "blocker"
        priority = 5
        action_id = "collect_plugin_availability_preflight"
        title = "Plugin is missing from the preflight availability report"
        recommended_next_action = "Rerun plugin validation preflight so availability and category evidence are recorded."
    elif not available:
        severity = "blocker"
        priority = 10
        action_id = "install_or_disable_unavailable_plugin"
        title = "Plugin is unavailable on disk"
        recommended_next_action = "Install the plugin, map a validated substitute, or disable this plugin for automatic drafts."
    elif matching_reports == 0:
        severity = "blocker"
        priority = 20
        action_id = "collect_reaper_observed_semantic_validation"
        title = "Plugin is available but has no semantic validation report"
        recommended_next_action = "Collect a REAPER-observed parameter validation report before allowing parameter writes."
    elif not semantic_passed or passed_reports == 0:
        severity = "blocker"
        priority = 30
        action_id = "rerun_or_keep_plugin_read_only"
        title = "Plugin validation report is present but not write-safe"
        recommended_next_action = "Rerun semantic validation with observed parameter response, or keep this plugin read-only/manual-review only."
    elif safe_controls <= 0:
        severity = "blocker"
        priority = 40
        action_id = "safe_controls_missing"
        title = "Plugin validation passed without write-safe controls"
        recommended_next_action = "Record at least one validated write-safe semantic control before using this adapter."
    else:
        severity = "info"
        priority = 90
        action_id = "plugin_write_safe_ready"
        title = "Plugin has availability and write-safe semantic validation evidence"
        recommended_next_action = "Keep the validated semantic bounds and avoid writing unknown parameters."

    blockers = [f"{plugin_name}:{action_id}"] if severity == "blocker" else []
    warnings = [f"{plugin_name}:availability_only_not_write_safety"] if available and not semantic_passed else []
    return {
        "plugin_name": plugin_name,
        "action_id": action_id,
        "priority": priority,
        "title": title,
        "severity": severity,
        "category": category,
        "available": available,
        "candidate_paths": availability.get("candidate_paths", []) if availability else [],
        "matching_reports_total": matching_reports,
        "passed_reports_total": passed_reports,
        "safe_control_count": safe_controls,
        "semantic_validation_passed": semantic_passed,
        "expected_report_glob": _expected_report_glob(plugin_name),
        "source_blockers": sorted(set((semantic.get("blockers", []) if semantic else []) or [])),
        "source_warnings": sorted(set((semantic.get("warnings", []) if semantic else []) or [])),
        "recommended_next_action": recommended_next_action,
        "required_evidence": [
            "plugin availability evidence from plugin_validation_preflight",
            "REAPER-observed semantic parameter validation report",
            "status=passed, safe_for_automix=true, no_fake_success=true",
            "at least one validated write_allowed semantic control with confidence>=0.85 and safe bounds",
        ],
        "disallowed_actions": [
            "write parameters based on plugin availability alone",
            "use fixed parameter indexes without observed semantic validation",
            "treat fallback EQ/dynamics as proof that a developed rescue plugin loaded",
        ],
        "blockers": blockers,
        "warnings": warnings,
    }


def build_plugin_validation_action_plan(
    *,
    project_name: str,
    output_dir: Path,
    preflight: dict[str, Any] | None = None,
    semantic_gate: dict[str, Any] | None = None,
    preflight_path: Path | None = None,
    semantic_gate_path: Path | None = None,
    output_path: Path | None = None,
) -> dict[str, Any]:
    output_dir = Path(output_dir)
    preflight = preflight or _load_json(preflight_path or output_dir / "eval_reports/plugin_validation_preflight.json")
    semantic_gate = semantic_gate or _load_json(semantic_gate_path or output_dir / "eval_reports/plugin_semantic_validation_gate.json")
    availability = _availability_by_plugin(preflight)
    semantic = _semantic_by_plugin(semantic_gate)
    required_plugins = _required_plugin_names(preflight, semantic_gate)

    plugin_actions = []
    for plugin_name in required_plugins:
        key = compact_plugin_name(plugin_name)
        plugin_actions.append(_plugin_action(plugin_name, availability.get(key, {}), semantic.get(key, {})))
    plugin_actions = sorted(
        plugin_actions,
        key=lambda item: (_severity_rank(item.get("severity", "")), int(item.get("priority", 999) or 999), item.get("plugin_name", "").lower()),
    )
    blockers = sorted({blocker for item in plugin_actions for blocker in item.get("blockers", [])})
    warnings = sorted(
        set(preflight.get("warnings", []) or [])
        | set(semantic_gate.get("warnings", []) or [])
        | {warning for item in plugin_actions for warning in item.get("warnings", [])}
    )
    if not required_plugins:
        warnings.append("required_plugin_list_missing")
    preflight_summary = preflight.get("summary", {}) if isinstance(preflight.get("summary", {}), dict) else {}
    semantic_ready = bool(semantic_gate.get("semantic_validation_ready", False))
    safe_to_write = bool(preflight_summary.get("safe_to_write_parameters", False) and semantic_ready and not blockers)
    plan = {
        "schema": PLUGIN_VALIDATION_ACTION_PLAN_SCHEMA,
        "project_name": project_name,
        "created_at": now_utc(),
        "output_dir": str(output_dir),
        "source_preflight": str(preflight_path or output_dir / "eval_reports/plugin_validation_preflight.json"),
        "source_semantic_gate": str(semantic_gate_path or output_dir / "eval_reports/plugin_semantic_validation_gate.json"),
        "required_plugins_total": len(required_plugins),
        "plugin_actions_total": len(plugin_actions),
        "plugin_actions": plugin_actions,
        "next_plugin_action": plugin_actions[0] if plugin_actions else {},
        "summary": {
            "available_plugins_total": sum(1 for item in plugin_actions if item.get("available")),
            "unavailable_plugins_total": sum(1 for item in plugin_actions if not item.get("available")),
            "plugins_with_matching_reports_total": sum(1 for item in plugin_actions if int(item.get("matching_reports_total", 0) or 0) > 0),
            "plugins_with_passed_reports_total": sum(1 for item in plugin_actions if int(item.get("passed_reports_total", 0) or 0) > 0),
            "plugins_with_safe_controls_total": sum(1 for item in plugin_actions if int(item.get("safe_control_count", 0) or 0) > 0),
            "preflight_safe_to_write_parameters": bool(preflight_summary.get("safe_to_write_parameters", False)),
            "semantic_validation_ready": semantic_ready,
            "safe_to_write_parameters": safe_to_write,
        },
        "status": "write_safe_ready" if safe_to_write else "plugin_validation_actions_open",
        "blockers": blockers,
        "warnings": sorted(set(warnings)),
        "limits": [
            "This plan turns plugin validation blockers into plugin-level next actions; it does not open REAPER, insert FX, write parameters, render, or approve audio.",
            "Plugin availability is not semantic write safety.",
            "A plugin becomes write-safe only when preflight and semantic validation evidence both pass.",
        ],
    }
    target = output_path or output_dir / ACTION_PLAN_REL_PATH
    write_json(target, plan)
    write_plugin_validation_action_plan_report(plan, output_dir)
    write_plugin_validation_action_request(plan, output_dir)
    return plan


def write_plugin_validation_action_plan_report(plan: dict[str, Any], output_dir: Path) -> Path:
    summary = plan.get("summary", {})
    lines = [
        "# Plugin Validation Action Plan",
        "",
        f"- Project: `{plan.get('project_name')}`",
        f"- Created UTC: `{plan.get('created_at')}`",
        f"- Status: `{plan.get('status')}`",
        f"- Safe to write parameters: `{summary.get('safe_to_write_parameters', False)}`",
        f"- Required plugins: `{plan.get('required_plugins_total', 0)}`",
        f"- Plugin actions: `{plan.get('plugin_actions_total', 0)}`",
        f"- Plugins with safe controls: `{summary.get('plugins_with_safe_controls_total', 0)}`",
        "",
        "This report sequences plugin validation evidence. It does not approve plugin parameter writes from availability alone.",
        "",
        "## Blockers",
        "",
    ]
    lines.extend([f"- `{item}`" for item in plan.get("blockers", [])] or ["- none"])
    lines.extend(["", "## Next Plugin Action", ""])
    next_action = plan.get("next_plugin_action", {})
    if next_action:
        lines.append(f"- `{next_action.get('plugin_name')}` `{next_action.get('action_id')}`: {next_action.get('recommended_next_action')}")
    else:
        lines.append("- none")
    lines.extend(["", "## Plugin Actions", ""])
    for item in plan.get("plugin_actions", []):
        lines.extend(
            [
                f"### {item.get('plugin_name')}",
                "",
                f"- Severity: `{item.get('severity')}`",
                f"- Action: `{item.get('action_id')}`",
                f"- Available: `{item.get('available')}`",
                f"- Matching reports: `{item.get('matching_reports_total')}`",
                f"- Passed reports: `{item.get('passed_reports_total')}`",
                f"- Safe controls: `{item.get('safe_control_count')}`",
                f"- Expected report: `{item.get('expected_report_glob')}`",
                f"- Recommended next action: {item.get('recommended_next_action')}",
                "",
            ]
        )
    if not plan.get("plugin_actions"):
        lines.append("- none")
    path = Path(output_dir) / ACTION_PLAN_REPORT_REL_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return path


def write_plugin_validation_action_request(plan: dict[str, Any], output_dir: Path) -> Path:
    lines = [
        "# Plugin Validation Action Request",
        "",
        f"- Project: `{plan.get('project_name')}`",
        f"- Status: `{plan.get('status')}`",
        "",
        "Collect or repair this evidence before automatic parameter writes:",
        "",
    ]
    for item in plan.get("plugin_actions", []):
        if item.get("severity") != "blocker":
            continue
        lines.extend(
            [
                f"## {item.get('plugin_name')}",
                "",
                f"- Action: `{item.get('action_id')}`",
                f"- Expected report glob: `{item.get('expected_report_glob')}`",
                f"- Next action: {item.get('recommended_next_action')}",
                "- Required evidence:",
            ]
        )
        lines.extend([f"  - {evidence}" for evidence in item.get("required_evidence", [])])
        lines.append("")
    if not any(item.get("severity") == "blocker" for item in plan.get("plugin_actions", [])):
        lines.append("- none")
    path = Path(output_dir) / ACTION_REQUEST_REL_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return path

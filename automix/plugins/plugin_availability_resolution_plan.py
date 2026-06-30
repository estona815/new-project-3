from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from automix.plugins.plugin_adapter_schema import compact_plugin_name, now_utc, write_json
from automix.plugins.third_party_plugin_policy import plugin_family


PLUGIN_AVAILABILITY_RESOLUTION_PLAN_SCHEMA = "automix-plugin-availability-resolution-plan-v1"

PLAN_REL_PATH = Path("eval_reports/plugin_availability_resolution_plan.json")
PLAN_REPORT_REL_PATH = Path("eval_reports/plugin_availability_resolution_plan.md")
REQUEST_REL_PATH = Path("review/plugin_availability_resolution_request.md")
DISABLE_TEMPLATE_REL_PATH = Path("review/plugin_availability_disable_manifest_template.json")


def _load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _load_catalog(catalog_path: Path) -> dict[str, Any]:
    data = _load_json(catalog_path)
    return data if data.get("schema") == "automix-plugin-capability-catalog-v1" else {}


def _catalog_entry(plugin_name: str, catalog: dict[str, Any]) -> dict[str, Any]:
    target = compact_plugin_name(plugin_name)
    for entry in catalog.get("target_families", []) or []:
        if not isinstance(entry, dict):
            continue
        names = [entry.get("display_name", ""), *(entry.get("aliases", []) or [])]
        if any(compact_plugin_name(name) and (compact_plugin_name(name) in target or target in compact_plugin_name(name)) for name in names):
            return entry
    return {}


def _is_required_artifact_rescue(plugin_name: str) -> bool:
    lowered = plugin_name.lower()
    return "vocal_ai_artifact_split_tamer.jsfx" in lowered or "codex vocal ai artifact split tamer" in lowered


def _resolution_for(plugin_action: dict[str, Any], catalog: dict[str, Any]) -> dict[str, Any]:
    plugin_name = str(plugin_action.get("plugin_name", ""))
    entry = _catalog_entry(plugin_name, catalog)
    family = plugin_family(plugin_name) or str(entry.get("id", "") or "unknown")
    fallback = str(entry.get("fallback", "") or "")
    category = str(plugin_action.get("category", "unknown"))
    if _is_required_artifact_rescue(plugin_name):
        recommended = "repair_required_jsfx_path"
        severity = "blocker"
        install_or_disable_allowed = False
        rationale = "The developed Suno/AI artifact rescue plugin is required for clean-main-vocal rescue and cannot be replaced by generic fallbacks."
    elif category == "stock":
        recommended = "repair_reaper_stock_install_or_keep_manual_review"
        severity = "blocker"
        install_or_disable_allowed = False
        rationale = "A missing stock plugin indicates the local REAPER install or resource scan needs repair; do not replace it with guessed parameters."
    elif category == "jsfx":
        recommended = "repair_jsfx_path_or_keep_manual_review"
        severity = "blocker"
        install_or_disable_allowed = False
        rationale = "A missing JSFX path must be repaired or kept manual-review only before automation."
    elif category == "third_party_or_unknown" or family != "unknown":
        recommended = "disable_for_automatic_drafts"
        severity = "review"
        install_or_disable_allowed = True
        rationale = "Optional third-party plugins are not required for safe automation; disable them unless the user installs and validates them."
    else:
        recommended = "manual_review_only"
        severity = "review"
        install_or_disable_allowed = True
        rationale = "Unknown unavailable plugins must stay out of automatic drafts until explicitly resolved."
    return {
        "plugin_name": plugin_name,
        "family": family,
        "category": category,
        "available": bool(plugin_action.get("available", False)),
        "source_action_id": plugin_action.get("action_id", ""),
        "recommended_resolution": recommended,
        "severity": severity,
        "install_or_disable_allowed": install_or_disable_allowed,
        "fallback_candidate": fallback,
        "fallback_requires_validation": bool(fallback),
        "automatic_parameter_writes_allowed": False,
        "operator_decision_required": True,
        "rationale": rationale,
        "required_evidence": [
            "explicit operator choice to install, disable, or keep manual-review only",
            "updated plugin validation preflight after installation or disable decision",
            "semantic validation report before any fallback or installed plugin parameter writes",
        ],
        "disallowed_actions": [
            "claim this plugin was used while unavailable",
            "replace it with a fallback without semantic validation evidence",
            "write parameters to any substitute based on catalog fallback text alone",
        ],
    }


def _disable_manifest_template(resolutions: list[dict[str, Any]]) -> dict[str, Any]:
    disabled = [
        {
            "plugin_name": item["plugin_name"],
            "resolution": item["recommended_resolution"],
            "fallback_candidate": item.get("fallback_candidate", ""),
            "fallback_requires_validation": item.get("fallback_requires_validation", False),
            "automatic_parameter_writes_allowed": False,
            "operator_acknowledged": False,
        }
        for item in resolutions
        if item.get("recommended_resolution") in {"disable_for_automatic_drafts", "manual_review_only"}
    ]
    return {
        "schema": "automix-plugin-availability-disable-manifest-template-v1",
        "disabled_plugins": disabled,
        "operator_acknowledgement_required": True,
        "limits": [
            "This template is not accepted evidence until operator_acknowledged is true for each disabled plugin.",
            "Disabled plugins are not proof that fallback plugins are safe to write.",
            "Fallback parameter writes still require semantic validation reports.",
        ],
    }


def build_plugin_availability_resolution_plan(
    *,
    project_name: str,
    output_dir: Path,
    action_plan: dict[str, Any] | None = None,
    action_plan_path: Path | None = None,
    catalog_path: Path | None = None,
    output_path: Path | None = None,
) -> dict[str, Any]:
    output_dir = Path(output_dir)
    action_plan_path = action_plan_path or output_dir / "eval_reports/plugin_validation_action_plan.json"
    catalog_path = catalog_path or Path("automix/plugin_capability_catalog.json")
    action_plan = action_plan or _load_json(action_plan_path)
    catalog = _load_catalog(catalog_path)
    unavailable = [
        item
        for item in action_plan.get("plugin_actions", []) or []
        if isinstance(item, dict) and item.get("action_id") == "install_or_disable_unavailable_plugin"
    ]
    resolutions = [_resolution_for(item, catalog) for item in unavailable]
    required_blockers = [f"{item['plugin_name']}:{item['recommended_resolution']}" for item in resolutions if item.get("severity") == "blocker"]
    pending_decisions = [item["plugin_name"] for item in resolutions if item.get("operator_decision_required")]
    disable_manifest = _disable_manifest_template(resolutions)
    write_json(output_dir / DISABLE_TEMPLATE_REL_PATH, disable_manifest)
    plan = {
        "schema": PLUGIN_AVAILABILITY_RESOLUTION_PLAN_SCHEMA,
        "project_name": project_name,
        "created_at": now_utc(),
        "output_dir": str(output_dir),
        "source_action_plan": str(action_plan_path),
        "source_capability_catalog": str(catalog_path),
        "unavailable_plugins_total": len(unavailable),
        "resolutions": resolutions,
        "pending_operator_decisions": pending_decisions,
        "disable_manifest_template": str(output_dir / DISABLE_TEMPLATE_REL_PATH),
        "disable_manifest_plugins_total": len(disable_manifest.get("disabled_plugins", [])),
        "status": "no_unavailable_plugins_detected" if not unavailable else "operator_resolution_required",
        "safe_to_write_parameters": False,
        "safe_to_continue_report_only": True,
        "blockers": sorted(required_blockers),
        "warnings": [
            "operator_disable_or_install_decision_required"
        ] if pending_decisions else [],
        "limits": [
            "This plan does not install plugins, open REAPER, write parameters, render, or approve audio.",
            "Disabling an unavailable plugin only removes it from automatic drafts after explicit operator acknowledgement.",
            "Fallback candidates require their own semantic validation before parameter writes.",
        ],
    }
    target = output_path or output_dir / PLAN_REL_PATH
    write_json(target, plan)
    write_plugin_availability_resolution_report(plan, output_dir)
    write_plugin_availability_resolution_request(plan, output_dir)
    return plan


def write_plugin_availability_resolution_report(plan: dict[str, Any], output_dir: Path) -> Path:
    lines = [
        "# Plugin Availability Resolution Plan",
        "",
        f"- Project: `{plan.get('project_name')}`",
        f"- Created UTC: `{plan.get('created_at')}`",
        f"- Status: `{plan.get('status')}`",
        f"- Unavailable plugins: `{plan.get('unavailable_plugins_total')}`",
        f"- Disable manifest plugins: `{plan.get('disable_manifest_plugins_total')}`",
        "",
        "This report resolves unavailable plugin choices only. It does not approve fallback parameter writes.",
        "",
        "## Blockers",
        "",
    ]
    lines.extend([f"- `{item}`" for item in plan.get("blockers", [])] or ["- none"])
    lines.extend(["", "## Resolutions", ""])
    for item in plan.get("resolutions", []):
        lines.extend(
            [
                f"### {item.get('plugin_name')}",
                "",
                f"- Severity: `{item.get('severity')}`",
                f"- Recommended resolution: `{item.get('recommended_resolution')}`",
                f"- Fallback candidate: `{item.get('fallback_candidate', '')}`",
                f"- Fallback requires validation: `{item.get('fallback_requires_validation')}`",
                f"- Automatic parameter writes allowed: `{item.get('automatic_parameter_writes_allowed')}`",
                f"- Rationale: {item.get('rationale')}",
                "",
            ]
        )
    if not plan.get("resolutions"):
        lines.append("- none")
    path = Path(output_dir) / PLAN_REPORT_REL_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return path


def write_plugin_availability_resolution_request(plan: dict[str, Any], output_dir: Path) -> Path:
    lines = [
        "# Plugin Availability Resolution Request",
        "",
        f"- Project: `{plan.get('project_name')}`",
        f"- Disable manifest template: `{plan.get('disable_manifest_template')}`",
        "",
        "Operator choices needed:",
        "",
    ]
    if not plan.get("resolutions"):
        lines.append("- none")
    for item in plan.get("resolutions", []):
        lines.extend(
            [
                f"## {item.get('plugin_name')}",
                "",
                f"- Recommended resolution: `{item.get('recommended_resolution')}`",
                f"- Fallback candidate: `{item.get('fallback_candidate', '')}`",
                f"- Next evidence: {', '.join(item.get('required_evidence', []))}",
                "",
            ]
        )
    path = Path(output_dir) / REQUEST_REL_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return path

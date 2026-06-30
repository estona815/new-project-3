from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from automix.plugins.plugin_adapter_schema import compact_plugin_name, now_utc, slugify, write_json


PLUGIN_SEMANTIC_VALIDATION_SCHEMA = "automix-plugin-semantic-validation-gate-v1"

GATE_REL_PATH = Path("eval_reports/plugin_semantic_validation_gate.json")
GATE_REPORT_REL_PATH = Path("eval_reports/plugin_semantic_validation_gate.md")
TEMPLATE_REL_PATH = Path("review/plugin_semantic_validation_manifest_template.json")
REQUEST_REL_PATH = Path("review/plugin_semantic_validation_request.md")


def _load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        out = float(value)
    except (TypeError, ValueError):
        return default
    return out


def _required_plugin_names(output_dir: Path, preflight_path: Path | None, plugin_readiness_path: Path | None) -> list[str]:
    preflight = _load_json(preflight_path or output_dir / "eval_reports/plugin_validation_preflight.json")
    readiness = _load_json(plugin_readiness_path or output_dir / "eval_reports/real_project_plugin_readiness.json")
    names = set(str(item) for item in preflight.get("required_plugins", []) if str(item).strip())
    for key in ("missing_or_unsafe_mappings", "stock_fallbacks_available", "jsfx_fallbacks_available"):
        value = readiness.get(key, [])
        if isinstance(value, list):
            names.update(str(item) for item in value if str(item).strip())
    return sorted(name for name in names if not name.startswith("validated "))


def _load_validation_reports(validation_reports_dir: Path) -> list[dict[str, Any]]:
    reports: list[dict[str, Any]] = []
    for path in sorted(Path(validation_reports_dir).glob("plugin_parameter_validation_*.json")):
        data = _load_json(path)
        if not data:
            reports.append({"path": str(path), "json_valid": False, "plugin_name": "", "adapter_id": "", "status": "invalid_json"})
        else:
            reports.append({**data, "path": str(path), "json_valid": True})
    return reports


def _report_matches_plugin(report: dict[str, Any], plugin_name: str) -> bool:
    report_names = [
        str(report.get("plugin_name", "")),
        str(report.get("adapter_id", "")),
    ]
    target = compact_plugin_name(plugin_name)
    for name in report_names:
        compact = compact_plugin_name(name)
        if compact and target and (compact in target or target in compact):
            return True
    return False


def _write_safe_controls(report: dict[str, Any]) -> dict[str, dict[str, Any]]:
    controls = report.get("controls", {}) if isinstance(report.get("controls", {}), dict) else {}
    safe: dict[str, dict[str, Any]] = {}
    for semantic, control in controls.items():
        if not isinstance(control, dict):
            continue
        confidence = _safe_float(control.get("confidence"), 0.0)
        if bool(control.get("write_allowed")) and bool(control.get("validated")) and confidence >= 0.85 and control.get("target_name"):
            safe[str(semantic)] = control
    return safe


def _report_result(report: dict[str, Any]) -> dict[str, Any]:
    safe_controls = _write_safe_controls(report)
    blockers: list[str] = []
    warnings: list[str] = []
    if not report.get("json_valid", True):
        blockers.append("validation_report_invalid_json")
    if report.get("schema") != "automix-plugin-parameter-validation-report-v1":
        blockers.append("validation_report_schema_mismatch")
    if report.get("status") != "passed":
        blockers.append(f"validation_report_not_passed:{report.get('status', 'unknown')}")
    if not report.get("safe_for_automix", False):
        blockers.append("validation_report_not_safe_for_automix")
    if report.get("schema_errors"):
        blockers.append("validation_report_has_schema_errors")
    if not report.get("no_fake_success", False):
        blockers.append("validation_report_no_fake_success_missing")
    if not safe_controls:
        blockers.append("validation_report_has_no_write_safe_controls")
    controls = report.get("controls", {}) if isinstance(report.get("controls", {}), dict) else {}
    if controls and len(safe_controls) < len(controls):
        warnings.append("some_semantic_controls_remain_write_blocked")
    return {
        "path": report.get("path", ""),
        "plugin_name": report.get("plugin_name", ""),
        "adapter_id": report.get("adapter_id", ""),
        "status": report.get("status", ""),
        "safe_for_automix": bool(report.get("safe_for_automix", False)),
        "safe_controls": sorted(safe_controls),
        "safe_control_count": len(safe_controls),
        "blockers": sorted(set(blockers)),
        "warnings": sorted(set(warnings)),
        "passed": not blockers,
    }


def _plugin_result(plugin_name: str, reports: list[dict[str, Any]]) -> dict[str, Any]:
    matching = [report for report in reports if _report_matches_plugin(report, plugin_name)]
    report_results = [_report_result(report) for report in matching]
    passed = [item for item in report_results if item.get("passed")]
    blockers: list[str] = []
    warnings: list[str] = []
    if not matching:
        blockers.append(f"validation_report_missing:{plugin_name}")
    if matching and not passed:
        blockers.append(f"no_passed_semantic_validation_report:{plugin_name}")
    for result in report_results:
        blockers.extend(f"{plugin_name}:{blocker}" for blocker in result.get("blockers", []))
        warnings.extend(f"{plugin_name}:{warning}" for warning in result.get("warnings", []))
    return {
        "plugin_name": plugin_name,
        "matching_reports_total": len(matching),
        "passed_reports_total": len(passed),
        "safe_control_count": sum(int(item.get("safe_control_count", 0) or 0) for item in passed),
        "report_results": report_results,
        "semantic_validation_passed": bool(passed),
        "blockers": sorted(set(blockers)),
        "warnings": sorted(set(warnings)),
    }


def _template(required_plugins: list[str]) -> dict[str, Any]:
    return {
        "schema": "automix-plugin-semantic-validation-manifest-template-v1",
        "required_reports": [
            {
                "plugin_name": name,
                "expected_report_glob": f"automix/analysis_reports/plugin_parameter_validation_{slugify(name)}*.json",
                "required_fields": [
                    "schema=automix-plugin-parameter-validation-report-v1",
                    "status=passed",
                    "safe_for_automix=true",
                    "no_fake_success=true",
                    "controls.<semantic>.validated=true",
                    "controls.<semantic>.write_allowed=true",
                    "controls.<semantic>.confidence>=0.85",
                    "controls.<semantic>.target_name present",
                ],
            }
            for name in required_plugins
        ],
        "limits": [
            "Do not mark reports passed unless REAPER runtime validation observed the parameter response.",
            "Plugin availability alone is not semantic write safety.",
            "Unknown or preset/license/random/quality parameters must remain skipped.",
        ],
    }


def build_plugin_semantic_validation_gate(
    *,
    project_name: str,
    output_dir: Path,
    validation_reports_dir: Path | None = None,
    preflight_path: Path | None = None,
    plugin_readiness_path: Path | None = None,
    output_path: Path | None = None,
) -> dict[str, Any]:
    output_dir = Path(output_dir)
    validation_reports_dir = Path(validation_reports_dir or output_dir / "analysis_reports")
    required_plugins = _required_plugin_names(output_dir, preflight_path, plugin_readiness_path)
    reports = _load_validation_reports(validation_reports_dir)
    plugin_results = [_plugin_result(name, reports) for name in required_plugins]
    passed_plugins = [item for item in plugin_results if item.get("semantic_validation_passed")]
    blockers = sorted({blocker for item in plugin_results for blocker in item.get("blockers", [])})
    warnings = sorted({warning for item in plugin_results for warning in item.get("warnings", [])})
    if required_plugins and not passed_plugins:
        blockers.append("semantic_validation_passed_reports_missing")
    if not required_plugins:
        warnings.append("required_plugin_list_missing")
    if not reports:
        blockers.append("semantic_validation_reports_missing")

    template = _template(required_plugins)
    write_json(output_dir / TEMPLATE_REL_PATH, template)

    gate = {
        "schema": PLUGIN_SEMANTIC_VALIDATION_SCHEMA,
        "project_name": project_name,
        "created_at": now_utc(),
        "output_dir": str(output_dir),
        "validation_reports_dir": str(validation_reports_dir),
        "required_plugins": required_plugins,
        "required_plugins_total": len(required_plugins),
        "validation_reports_total": len(reports),
        "semantic_validation_ready": bool(required_plugins and len(passed_plugins) == len(required_plugins) and not blockers),
        "plugins_with_passed_semantic_validation": [item.get("plugin_name") for item in passed_plugins],
        "safe_controls_total": sum(int(item.get("safe_control_count", 0) or 0) for item in passed_plugins),
        "plugin_results": plugin_results,
        "blockers": sorted(set(blockers)),
        "warnings": sorted(set(warnings)),
        "template_path": str(output_dir / TEMPLATE_REL_PATH),
        "limits": [
            "This gate audits validation reports only; it does not open REAPER, insert FX, write parameters, or render.",
            "A validation report passes only when it includes observed write-safe semantic controls.",
            "This gate does not make third-party plugins required or bypass source/approval gates.",
        ],
    }
    target = output_path or output_dir / GATE_REL_PATH
    write_json(target, gate)
    write_plugin_semantic_validation_report(gate, output_dir)
    write_plugin_semantic_validation_request(gate, output_dir)
    return gate


def write_plugin_semantic_validation_report(gate: dict[str, Any], output_dir: Path) -> Path:
    lines = [
        "# Plugin Semantic Validation Gate",
        "",
        f"- Project: `{gate.get('project_name')}`",
        f"- Created UTC: `{gate.get('created_at')}`",
        f"- Semantic validation ready: `{gate.get('semantic_validation_ready')}`",
        f"- Required plugins: `{gate.get('required_plugins_total')}`",
        f"- Validation reports: `{gate.get('validation_reports_total')}`",
        f"- Safe controls: `{gate.get('safe_controls_total')}`",
        "",
        "This report checks semantic parameter validation evidence. It does not grant write safety from availability alone.",
        "",
        "## Blockers",
        "",
    ]
    lines.extend([f"- `{item}`" for item in gate.get("blockers", [])] or ["- none"])
    lines.extend(["", "## Warnings", ""])
    lines.extend([f"- `{item}`" for item in gate.get("warnings", [])] or ["- none"])
    lines.extend(["", "## Plugins", ""])
    for item in gate.get("plugin_results", []):
        lines.extend(
            [
                f"### {item.get('plugin_name')}",
                "",
                f"- Passed reports: `{item.get('passed_reports_total')}`",
                f"- Matching reports: `{item.get('matching_reports_total')}`",
                f"- Safe controls: `{item.get('safe_control_count')}`",
                f"- Blockers: `{item.get('blockers', [])}`",
                "",
            ]
        )
    if not gate.get("plugin_results"):
        lines.append("- none")
    path = Path(output_dir) / GATE_REPORT_REL_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return path


def write_plugin_semantic_validation_request(gate: dict[str, Any], output_dir: Path) -> Path:
    lines = [
        "# Plugin Semantic Validation Request",
        "",
        f"- Project: `{gate.get('project_name')}`",
        f"- Template: `{gate.get('template_path')}`",
        "",
        "Required REAPER-side evidence for each plugin:",
        "",
        "- Runtime plugin availability observed.",
        "- Semantic parameter response observed, not guessed from index order.",
        "- Safe min/max bounds recorded.",
        "- `status=passed`, `safe_for_automix=true`, and `no_fake_success=true` only when at least one semantic control is validated and write-safe.",
        "",
        "Current blockers:",
        "",
    ]
    lines.extend([f"- `{item}`" for item in gate.get("blockers", [])] or ["- none"])
    path = Path(output_dir) / REQUEST_REL_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return path

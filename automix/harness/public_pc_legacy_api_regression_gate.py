from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from automix.plugins.plugin_adapter_schema import now_utc, write_json
from automix.plugins.reaper_runtime_collector_safety_audit import DISALLOWED_REAPER_CALLS


PUBLIC_PC_LEGACY_API_REGRESSION_GATE_SCHEMA = "automix-public-pc-legacy-api-regression-gate-v1"

JSON_REL_PATH = Path("eval_reports/public_pc_legacy_api_regression_gate.json")
MD_REL_PATH = Path("eval_reports/public_pc_legacy_api_regression_gate.md")
LEGACY_FIXTURE_PLAN_REL_PATH = Path("eval_reports/public_pc_legacy_fixture_plan.json")

REQUIRED_DIRECT_MERGE_BLOCKERS = {
    "legacy_runtime_code_requires_manual_review",
    "current_fail_closed_gates_must_remain_authoritative",
}


def _load_json(path: Path) -> dict[str, Any]:
    try:
        loaded = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return {}
    return loaded if isinstance(loaded, dict) else {}


def _iter_fixture_records(plan: dict[str, Any]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for group in plan.get("fixture_groups", []) or []:
        if not isinstance(group, dict):
            continue
        for record in group.get("files", []) or []:
            if isinstance(record, dict):
                enriched = dict(record)
                enriched.setdefault("fixture_group_id", group.get("id", ""))
                enriched.setdefault("fixture_group_role", group.get("fixture_role", ""))
                records.append(enriched)
    return records


def _record_id(record: dict[str, Any]) -> str:
    return str(record.get("relative_path") or record.get("path") or "unknown")


def _record_has_required_blockers(record: dict[str, Any]) -> bool:
    blockers = set(str(item) for item in record.get("direct_merge_blockers", []) or [])
    return REQUIRED_DIRECT_MERGE_BLOCKERS.issubset(blockers)


def build_public_pc_legacy_api_regression_gate(
    *,
    project_name: str,
    output_dir: Path,
    legacy_fixture_plan_path: Path | None = None,
) -> dict[str, Any]:
    output_dir = Path(output_dir)
    legacy_fixture_plan_path = legacy_fixture_plan_path or output_dir / LEGACY_FIXTURE_PLAN_REL_PATH
    plan = _load_json(legacy_fixture_plan_path) if legacy_fixture_plan_path.exists() else {}
    records = _iter_fixture_records(plan)

    blockers: list[str] = []
    warnings: list[str] = []
    if not plan:
        blockers.append("legacy_fixture_plan_missing_or_invalid")
    elif not plan.get("passed", False):
        blockers.append("legacy_fixture_plan_not_passed")
    if not records:
        blockers.append("legacy_fixture_records_missing")

    summary = plan.get("summary", {}) if isinstance(plan.get("summary", {}), dict) else {}
    plan_disallowed_calls = sorted(str(call) for call in summary.get("unique_disallowed_reaper_calls", []) or [])
    uncovered_policy_calls = sorted(set(plan_disallowed_calls) - set(DISALLOWED_REAPER_CALLS))
    if uncovered_policy_calls:
        blockers.extend(f"legacy_disallowed_call_not_in_current_policy:{call}" for call in uncovered_policy_calls)

    unsafe_runtime_records: list[str] = []
    unsafe_merge_records: list[str] = []
    missing_required_blocker_records: list[str] = []
    parameter_write_records: list[str] = []
    mutation_records: list[str] = []
    disallowed_records: list[dict[str, Any]] = []
    credential_marker_records: list[str] = []

    for record in records:
        rel = _record_id(record)
        calls = [str(call) for call in record.get("disallowed_reaper_calls", []) or []]
        if calls:
            disallowed_records.append({"relative_path": rel, "disallowed_reaper_calls": calls})
        if bool(record.get("safe_to_execute_in_user_project", False)):
            unsafe_runtime_records.append(rel)
        if bool(record.get("safe_to_merge_runtime_code", False)):
            unsafe_merge_records.append(rel)
        if not _record_has_required_blockers(record):
            missing_required_blocker_records.append(rel)
        if bool(record.get("contains_parameter_writes", False)):
            parameter_write_records.append(rel)
            if "legacy_lua_contains_parameter_write_calls" not in set(record.get("direct_merge_blockers", []) or []):
                blockers.append(f"parameter_write_record_missing_blocker:{rel}")
        if bool(record.get("contains_media_import_or_track_creation", False)) or bool(record.get("contains_render_or_save_setup", False)):
            mutation_records.append(rel)
        if record.get("secret_markers"):
            credential_marker_records.append(rel)

    blockers.extend(f"legacy_record_safe_to_execute_true:{rel}" for rel in unsafe_runtime_records)
    blockers.extend(f"legacy_record_safe_to_merge_true:{rel}" for rel in unsafe_merge_records)
    blockers.extend(f"legacy_record_missing_required_direct_merge_blockers:{rel}" for rel in missing_required_blocker_records)
    blockers.extend(f"legacy_record_high_confidence_secret_marker:{rel}" for rel in credential_marker_records)

    if disallowed_records:
        warnings.append(f"legacy_disallowed_reaper_api_records:{len(disallowed_records)}")
    if parameter_write_records:
        warnings.append(f"legacy_parameter_write_records:{len(parameter_write_records)}")
    if mutation_records:
        warnings.append(f"legacy_project_mutation_records:{len(mutation_records)}")

    unique_blockers = sorted(set(blockers))
    unique_warnings = sorted(set(warnings))
    passed = not unique_blockers
    gate = {
        "schema": PUBLIC_PC_LEGACY_API_REGRESSION_GATE_SCHEMA,
        "project_name": project_name,
        "created_at": now_utc(),
        "status": "legacy_api_regression_covered" if passed else "legacy_api_regression_blocked",
        "passed": passed,
        "legacy_fixture_plan_path": str(legacy_fixture_plan_path),
        "records_total": len(records),
        "policy": {
            "current_disallowed_reaper_calls": sorted(DISALLOWED_REAPER_CALLS),
            "plan_disallowed_reaper_calls": plan_disallowed_calls,
            "uncovered_policy_calls": uncovered_policy_calls,
            "required_direct_merge_blockers": sorted(REQUIRED_DIRECT_MERGE_BLOCKERS),
        },
        "coverage": {
            "disallowed_api_records": disallowed_records,
            "parameter_write_records": sorted(set(parameter_write_records)),
            "project_mutation_records": sorted(set(mutation_records)),
            "unsafe_runtime_records": sorted(set(unsafe_runtime_records)),
            "unsafe_merge_records": sorted(set(unsafe_merge_records)),
            "records_missing_required_direct_merge_blockers": sorted(set(missing_required_blocker_records)),
            "credential_marker_records": sorted(set(credential_marker_records)),
        },
        "readiness": {
            "legacy_api_regression_covered": passed,
            "ready_to_use_negative_safety_fixtures": bool(passed and disallowed_records),
            "safe_to_merge_legacy_runtime_code": False,
            "safe_to_execute_legacy_lua_in_user_project": False,
            "safe_to_write_parameters": False,
            "safe_to_render_or_save": False,
            "safe_to_claim_final_audio_or_delivery": False,
            "report_only": True,
        },
        "blockers": unique_blockers,
        "warnings": unique_warnings,
        "limits": [
            "This gate proves only static regression coverage for legacy public-PC APIs.",
            "It does not execute legacy Lua, approve parameter writes, render audio, or validate sonic quality.",
            "Legacy files with disallowed REAPER calls are negative fixtures for safety gates, not approved automation code.",
        ],
    }
    write_json(output_dir / JSON_REL_PATH, gate)
    write_public_pc_legacy_api_regression_report(gate, output_dir)
    return gate


def write_public_pc_legacy_api_regression_report(gate: dict[str, Any], output_dir: Path) -> Path:
    readiness = gate.get("readiness", {})
    policy = gate.get("policy", {})
    coverage = gate.get("coverage", {})
    lines = [
        "# Public PC Legacy API Regression Gate",
        "",
        f"- Project: `{gate.get('project_name')}`",
        f"- Created UTC: `{gate.get('created_at')}`",
        f"- Status: `{gate.get('status')}`",
        f"- Passed: `{gate.get('passed')}`",
        f"- Records reviewed: `{gate.get('records_total')}`",
        "",
        "## Readiness",
        "",
    ]
    for key, value in readiness.items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(
        [
            "",
            "## Policy Coverage",
            "",
            f"- Plan disallowed calls: `{policy.get('plan_disallowed_reaper_calls')}`",
            f"- Uncovered policy calls: `{policy.get('uncovered_policy_calls')}`",
            f"- Required direct-merge blockers: `{policy.get('required_direct_merge_blockers')}`",
            "",
            "## Risk Records",
            "",
            f"- Disallowed API records: `{len(coverage.get('disallowed_api_records', []))}`",
            f"- Parameter write records: `{coverage.get('parameter_write_records')}`",
            f"- Project mutation records: `{coverage.get('project_mutation_records')}`",
            f"- Unsafe runtime records: `{coverage.get('unsafe_runtime_records')}`",
            f"- Unsafe merge records: `{coverage.get('unsafe_merge_records')}`",
            "",
        ]
    )
    for item in coverage.get("disallowed_api_records", []):
        lines.append(f"- `{item.get('relative_path')}` calls `{item.get('disallowed_reaper_calls')}`")
    lines.extend(["", "## Blockers", ""])
    lines.extend([f"- `{item}`" for item in gate.get("blockers", [])] or ["- none"])
    lines.extend(["", "## Warnings", ""])
    lines.extend([f"- `{item}`" for item in gate.get("warnings", [])] or ["- none"])
    lines.extend(["", "## Limits", ""])
    lines.extend([f"- {item}" for item in gate.get("limits", [])])
    path = Path(output_dir) / MD_REL_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return path

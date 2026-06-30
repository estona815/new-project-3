from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from automix.plugins.plugin_adapter_schema import now_utc, write_json


PUBLIC_PC_LEGACY_SEMANTIC_FIREWALL_GATE_SCHEMA = "automix-public-pc-legacy-semantic-firewall-gate-v1"

JSON_REL_PATH = Path("eval_reports/public_pc_legacy_semantic_firewall_gate.json")
MD_REL_PATH = Path("eval_reports/public_pc_legacy_semantic_firewall_gate.md")
LEGACY_FIXTURE_PLAN_REL_PATH = Path("eval_reports/public_pc_legacy_fixture_plan.json")
LEGACY_API_REGRESSION_GATE_REL_PATH = Path("eval_reports/public_pc_legacy_api_regression_gate.json")
VALIDATION_REPORTS_REL_DIR = Path("analysis_reports")

DEFAULT_SEMANTIC_REPORT_REL_PATHS = [
    Path("eval_reports/plugin_semantic_validation_gate.json"),
    Path("eval_reports/plugin_semantic_validation_runtime_evidence_gate.json"),
    Path("eval_reports/plugin_semantic_validation_runtime_report_authoring_gate.json"),
    Path("eval_reports/plugin_semantic_validation_queue.json"),
    Path("eval_reports/plugin_semantic_validation_runtime_collection_package.json"),
    Path("eval_reports/plugin_semantic_validation_runtime_collector_package.json"),
    Path("eval_reports/plugin_semantic_validation_runtime_observation_gate.json"),
]


def _load_json(path: Path) -> tuple[dict[str, Any], bool]:
    try:
        loaded = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return {}, False
    return (loaded, True) if isinstance(loaded, dict) else ({}, False)


def _iter_fixture_records(plan: dict[str, Any]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for group in plan.get("fixture_groups", []) or []:
        if not isinstance(group, dict):
            continue
        for record in group.get("files", []) or []:
            if not isinstance(record, dict):
                continue
            enriched = dict(record)
            enriched.setdefault("fixture_group_id", group.get("id", ""))
            enriched.setdefault("fixture_group_role", group.get("fixture_role", ""))
            records.append(enriched)
    return records


def _normalise_text(value: Any) -> str:
    return str(value or "").replace("\\", "/").strip().lower()


def _legacy_match_tokens(record: dict[str, Any]) -> list[str]:
    tokens: list[str] = []
    for key in ("path", "relative_path"):
        value = _normalise_text(record.get(key, ""))
        if value:
            tokens.append(value)
    return sorted(set(tokens), key=len, reverse=True)


def _token_in_value(token: str, value: str) -> bool:
    if not token:
        return False
    if "/" in token:
        return token in value
    return value == token or value.endswith(f"/{token}")


def _record_id(record: dict[str, Any]) -> str:
    return str(record.get("relative_path") or record.get("path") or "unknown")


def _record_is_negative_fixture(record: dict[str, Any]) -> bool:
    return bool(
        record.get("disallowed_reaper_calls")
        or record.get("contains_parameter_writes")
        or record.get("contains_render_or_save_setup")
        or record.get("contains_media_import_or_track_creation")
    )


def _iter_strings(value: Any, json_path: str = "$") -> list[tuple[str, str]]:
    strings: list[tuple[str, str]] = []
    if isinstance(value, dict):
        for key, child in value.items():
            strings.extend(_iter_strings(child, f"{json_path}.{key}"))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            strings.extend(_iter_strings(child, f"{json_path}[{index}]"))
    elif isinstance(value, str):
        strings.append((json_path, value))
    return strings


def _short(value: Any, limit: int = 240) -> str:
    text = str(value or "")
    return text if len(text) <= limit else text[: limit - 3] + "..."


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _scan_semantic_report(
    *,
    report_path: Path,
    records: list[dict[str, Any]],
) -> dict[str, Any]:
    report, valid = _load_json(report_path) if report_path.exists() else ({}, False)
    references: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    if report and valid:
        for json_path, raw_value in _iter_strings(report):
            value = _normalise_text(raw_value)
            for record in records:
                for token in _legacy_match_tokens(record):
                    if not _token_in_value(token, value):
                        continue
                    key = (_record_id(record), json_path, str(raw_value))
                    if key in seen:
                        continue
                    seen.add(key)
                    references.append(
                        {
                            "legacy_relative_path": _record_id(record),
                            "legacy_path": str(record.get("path", "")),
                            "semantic_report_path": str(report_path),
                            "json_path": json_path,
                            "value": _short(raw_value),
                            "negative_safety_fixture": _record_is_negative_fixture(record),
                            "contains_parameter_writes": bool(record.get("contains_parameter_writes", False)),
                            "disallowed_reaper_calls": record.get("disallowed_reaper_calls", []) or [],
                        }
                    )
    return {
        "path": str(report_path),
        "exists": report_path.exists(),
        "json_valid": bool(valid and report),
        "schema": report.get("schema", ""),
        "semantic_validation_ready": bool(report.get("semantic_validation_ready", False)),
        "runtime_evidence_ready": bool(report.get("runtime_evidence_ready", False)),
        "authoring_candidates_ready": bool(report.get("authoring_candidates_ready", False)),
        "candidate_reports_are_validation_evidence": bool(report.get("candidate_reports_are_validation_evidence", False)),
        "strings_scanned": len(_iter_strings(report)) if report and valid else 0,
        "legacy_references": references,
    }


def _scan_validation_report_hashes(
    *,
    validation_reports_dir: Path,
    records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    legacy_by_sha = {
        str(record.get("sha256")): record
        for record in records
        if str(record.get("sha256", "")).strip()
    }
    if not validation_reports_dir.is_dir() or not legacy_by_sha:
        return []

    conflicts: list[dict[str, Any]] = []
    for path in sorted(validation_reports_dir.glob("plugin_parameter_validation_*.json")):
        digest = _sha256(path)
        record = legacy_by_sha.get(digest)
        if not record:
            continue
        conflicts.append(
            {
                "validation_report_path": str(path),
                "legacy_relative_path": _record_id(record),
                "legacy_path": str(record.get("path", "")),
                "sha256": digest,
                "negative_safety_fixture": _record_is_negative_fixture(record),
            }
        )
    return conflicts


def build_public_pc_legacy_semantic_firewall_gate(
    *,
    project_name: str,
    output_dir: Path,
    legacy_fixture_plan_path: Path | None = None,
    legacy_api_regression_gate_path: Path | None = None,
    semantic_report_paths: list[Path] | None = None,
    validation_reports_dir: Path | None = None,
) -> dict[str, Any]:
    output_dir = Path(output_dir)
    legacy_fixture_plan_path = legacy_fixture_plan_path or output_dir / LEGACY_FIXTURE_PLAN_REL_PATH
    legacy_api_regression_gate_path = legacy_api_regression_gate_path or output_dir / LEGACY_API_REGRESSION_GATE_REL_PATH
    semantic_report_paths = semantic_report_paths or [output_dir / rel for rel in DEFAULT_SEMANTIC_REPORT_REL_PATHS]
    validation_reports_dir = validation_reports_dir or output_dir / VALIDATION_REPORTS_REL_DIR

    plan, plan_valid = _load_json(legacy_fixture_plan_path) if legacy_fixture_plan_path.exists() else ({}, False)
    api_gate, api_valid = (
        _load_json(legacy_api_regression_gate_path) if legacy_api_regression_gate_path.exists() else ({}, False)
    )
    records = _iter_fixture_records(plan) if plan else []

    blockers: list[str] = []
    warnings: list[str] = []
    if not plan or not plan_valid:
        blockers.append("legacy_fixture_plan_missing_or_invalid")
    elif not plan.get("passed", False):
        blockers.append("legacy_fixture_plan_not_passed")
    if not records:
        blockers.append("legacy_fixture_records_missing")
    if not api_gate or not api_valid:
        blockers.append("legacy_api_regression_gate_missing_or_invalid")
    elif not api_gate.get("passed", False):
        blockers.append("legacy_api_regression_gate_not_passed")
    elif not api_gate.get("readiness", {}).get("legacy_api_regression_covered", False):
        blockers.append("legacy_api_regression_not_covered")

    unsafe_merge_records = [_record_id(record) for record in records if bool(record.get("safe_to_merge_runtime_code", False))]
    unsafe_execute_records = [_record_id(record) for record in records if bool(record.get("safe_to_execute_in_user_project", False))]
    unsafe_delivery_records = [_record_id(record) for record in records if bool(record.get("safe_to_use_for_delivery_claims", False))]
    blockers.extend(f"legacy_record_safe_to_merge_true:{rel}" for rel in unsafe_merge_records)
    blockers.extend(f"legacy_record_safe_to_execute_true:{rel}" for rel in unsafe_execute_records)
    blockers.extend(f"legacy_record_safe_for_delivery_claims_true:{rel}" for rel in unsafe_delivery_records)

    semantic_reports = [_scan_semantic_report(report_path=path, records=records) for path in semantic_report_paths]
    missing_semantic_reports = [item["path"] for item in semantic_reports if not item["exists"]]
    invalid_semantic_reports = [item["path"] for item in semantic_reports if item["exists"] and not item["json_valid"]]
    legacy_references = [
        reference
        for report in semantic_reports
        for reference in report.get("legacy_references", []) or []
    ]
    hash_conflicts = _scan_validation_report_hashes(validation_reports_dir=validation_reports_dir, records=records)

    if missing_semantic_reports:
        warnings.append(f"semantic_validation_reports_missing:{len(missing_semantic_reports)}")
    blockers.extend(f"semantic_validation_report_invalid_json:{Path(path).name}" for path in invalid_semantic_reports)
    blockers.extend(
        "legacy_path_referenced_by_semantic_validation_report:"
        f"{Path(item['semantic_report_path']).name}:{item['legacy_relative_path']}:{item['json_path']}"
        for item in legacy_references
    )
    blockers.extend(
        "legacy_fixture_hash_present_in_analysis_validation_reports:"
        f"{item['legacy_relative_path']}:{Path(item['validation_report_path']).name}"
        for item in hash_conflicts
    )

    negative_records = [record for record in records if _record_is_negative_fixture(record)]
    parameter_write_records = [_record_id(record) for record in records if bool(record.get("contains_parameter_writes", False))]
    project_mutation_records = [
        _record_id(record)
        for record in records
        if bool(record.get("contains_media_import_or_track_creation", False))
        or bool(record.get("contains_render_or_save_setup", False))
    ]
    if negative_records:
        warnings.append(f"legacy_negative_safety_fixture_records:{len(negative_records)}")
    if parameter_write_records:
        warnings.append(f"legacy_parameter_write_records:{len(parameter_write_records)}")
    if project_mutation_records:
        warnings.append(f"legacy_project_mutation_records:{len(project_mutation_records)}")

    semantic_validation_ready = any(item.get("semantic_validation_ready", False) for item in semantic_reports)
    runtime_evidence_ready = any(item.get("runtime_evidence_ready", False) for item in semantic_reports)
    authoring_candidates_ready = any(item.get("authoring_candidates_ready", False) for item in semantic_reports)
    if legacy_references and semantic_validation_ready:
        blockers.append("semantic_validation_ready_with_legacy_fixture_reference")
    if legacy_references and runtime_evidence_ready:
        blockers.append("runtime_evidence_ready_with_legacy_fixture_reference")
    if legacy_references and authoring_candidates_ready:
        blockers.append("authoring_candidates_ready_with_legacy_fixture_reference")

    unique_blockers = sorted(set(blockers))
    unique_warnings = sorted(set(warnings))
    passed = not unique_blockers
    gate = {
        "schema": PUBLIC_PC_LEGACY_SEMANTIC_FIREWALL_GATE_SCHEMA,
        "project_name": project_name,
        "created_at": now_utc(),
        "status": "legacy_semantic_firewall_clear" if passed else "legacy_semantic_firewall_blocked",
        "passed": passed,
        "legacy_fixture_plan_path": str(legacy_fixture_plan_path),
        "legacy_api_regression_gate_path": str(legacy_api_regression_gate_path),
        "validation_reports_dir": str(validation_reports_dir),
        "semantic_reports_scanned_total": len(semantic_reports),
        "legacy_records_total": len(records),
        "legacy_negative_records_total": len(negative_records),
        "semantic_validation_ready_seen": semantic_validation_ready,
        "runtime_evidence_ready_seen": runtime_evidence_ready,
        "authoring_candidates_ready_seen": authoring_candidates_ready,
        "readiness": {
            "legacy_fixtures_firewalled_from_semantic_validation": passed,
            "legacy_fixtures_count_as_validation_evidence": False,
            "semantic_validation_inputs_clean": bool(not legacy_references and not hash_conflicts),
            "safe_to_merge_legacy_runtime_code": False,
            "safe_to_execute_legacy_lua_in_user_project": False,
            "safe_to_write_parameters": False,
            "safe_to_claim_final_audio_or_delivery": False,
            "report_only": True,
        },
        "coverage": {
            "legacy_parameter_write_records": sorted(set(parameter_write_records)),
            "legacy_project_mutation_records": sorted(set(project_mutation_records)),
            "unsafe_merge_records": sorted(set(unsafe_merge_records)),
            "unsafe_execute_records": sorted(set(unsafe_execute_records)),
            "unsafe_delivery_records": sorted(set(unsafe_delivery_records)),
            "legacy_semantic_references": legacy_references,
            "legacy_hash_conflicts_in_analysis_reports": hash_conflicts,
            "missing_semantic_reports": missing_semantic_reports,
            "invalid_semantic_reports": invalid_semantic_reports,
        },
        "semantic_reports": semantic_reports,
        "blockers": unique_blockers,
        "warnings": unique_warnings,
        "limits": [
            "This gate does not execute legacy Lua, open REAPER, write parameters, render, or approve audio.",
            "Public-PC legacy files may be used as read-only or negative safety fixtures only.",
            "Legacy fixture paths or hashes must not appear as accepted semantic validation evidence.",
            "Passing this firewall does not make plugin semantic validation ready.",
        ],
    }
    write_json(output_dir / JSON_REL_PATH, gate)
    write_public_pc_legacy_semantic_firewall_report(gate, output_dir)
    return gate


def write_public_pc_legacy_semantic_firewall_report(gate: dict[str, Any], output_dir: Path) -> Path:
    readiness = gate.get("readiness", {})
    coverage = gate.get("coverage", {})
    lines = [
        "# Public PC Legacy Semantic Firewall Gate",
        "",
        f"- Project: `{gate.get('project_name')}`",
        f"- Created UTC: `{gate.get('created_at')}`",
        f"- Status: `{gate.get('status')}`",
        f"- Passed: `{gate.get('passed')}`",
        f"- Legacy records: `{gate.get('legacy_records_total')}`",
        f"- Negative records: `{gate.get('legacy_negative_records_total')}`",
        f"- Semantic reports scanned: `{gate.get('semantic_reports_scanned_total')}`",
        "",
        "## Readiness",
        "",
    ]
    for key, value in readiness.items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(
        [
            "",
            "## Coverage",
            "",
            f"- Legacy semantic references: `{len(coverage.get('legacy_semantic_references', []))}`",
            f"- Hash conflicts in analysis reports: `{len(coverage.get('legacy_hash_conflicts_in_analysis_reports', []))}`",
            f"- Parameter-write legacy records: `{coverage.get('legacy_parameter_write_records')}`",
            f"- Project-mutation legacy records: `{coverage.get('legacy_project_mutation_records')}`",
            f"- Missing semantic reports: `{len(coverage.get('missing_semantic_reports', []))}`",
            "",
        ]
    )
    for item in coverage.get("legacy_semantic_references", []):
        lines.append(
            f"- `{item.get('legacy_relative_path')}` referenced by "
            f"`{Path(str(item.get('semantic_report_path', ''))).name}` at `{item.get('json_path')}`"
        )
    for item in coverage.get("legacy_hash_conflicts_in_analysis_reports", []):
        lines.append(
            f"- `{item.get('legacy_relative_path')}` hash matches "
            f"`{Path(str(item.get('validation_report_path', ''))).name}`"
        )
    lines.extend(["", "## Semantic Reports", ""])
    for item in gate.get("semantic_reports", []):
        lines.append(
            f"- `{Path(str(item.get('path', ''))).name}` exists `{item.get('exists')}` "
            f"valid `{item.get('json_valid')}` legacy refs `{len(item.get('legacy_references', []))}`"
        )
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

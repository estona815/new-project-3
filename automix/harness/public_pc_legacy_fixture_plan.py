from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from automix.plugins.plugin_adapter_schema import now_utc, write_json
from automix.plugins.reaper_runtime_collector_safety_audit import DISALLOWED_REAPER_CALLS, REAPER_CALL_RE


PUBLIC_PC_LEGACY_FIXTURE_PLAN_SCHEMA = "automix-public-pc-legacy-fixture-plan-v1"

JSON_REL_PATH = Path("eval_reports/public_pc_legacy_fixture_plan.json")
MD_REL_PATH = Path("eval_reports/public_pc_legacy_fixture_plan.md")
HANDOFF_AUDIT_REL_PATH = Path("eval_reports/public_pc_handoff_package_audit.json")

MAX_FIXTURE_BYTES = 512 * 1024

LOW_CONFIDENCE_SECRET_MARKERS = [
    "api key",
    "api_key",
    "authorization",
    "bearer",
    "client_secret",
    "credentials",
    "password",
    "private_key",
    "refresh_token",
    "secret",
    "sk-",
    "token",
]

HIGH_CONFIDENCE_SECRET_PATTERNS = [
    re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
    re.compile(r"(?i)\b(?:api[_-]?key|client_secret|refresh_token|private_key|password)\s*[:=]\s*['\"]?[^'\"\s]{8,}"),
    re.compile(r"(?i)\bauthorization\s*:\s*(?:bearer|basic)\s+[A-Za-z0-9._~+/=-]{12,}"),
]

LEGACY_FIXTURE_GROUPS: list[dict[str, Any]] = [
    {
        "id": "legacy_reaper_lua_safety_fixtures",
        "kind": "lua",
        "fixture_role": "reaper_api_safety_regression",
        "paths": [
            "scripts/plugin_registry.lua",
            "scripts/apply_mix_recipe.lua",
            "scripts/fx_chain_builder.lua",
            "scripts/render_setup.lua",
            "scripts/routing_builder.lua",
            "scripts/utils.lua",
            "scripts/validate_project_routing.lua",
            "scripts/import_and_mix_stems.lua",
            "scripts/apply_revision_actions.lua",
        ],
    },
    {
        "id": "legacy_recipe_schema_fixtures",
        "kind": "json_or_lua_recipe",
        "fixture_role": "recipe_schema_regression",
        "paths": [
            "recipes/schemas/mix_recipe.schema.json",
            "recipes/schemas/qc_actions.schema.json",
            "recipes/schemas/arrangement_recipe.schema.json",
            "recipes/json/target_mix_recipe.json",
            "recipes/json/default_target_arrangement_recipe.json",
            "recipes/lua/target_mix_recipe.lua",
        ],
    },
    {
        "id": "legacy_review_evidence_fixtures",
        "kind": "review_evidence",
        "fixture_role": "historical_red_team_regression",
        "paths": [
            "review/handoff_validation_actual_targets_20260605.json",
            "review/handoff_validation_20260605.json",
            "review/red_team_report.md",
            "review/mix_risk_report.md",
            "review/api_risk_report.md",
        ],
    },
    {
        "id": "legacy_handoff_doc_fixtures",
        "kind": "handoff_docs",
        "fixture_role": "intent_and_restore_context",
        "paths": [
            "HANDOFF.md",
            "PROJECT_STATE.md",
            "NEXT_CODEX_PROMPT.md",
            "RESTORE_ON_OTHER_COMPUTER.md",
            "PACKAGE_WARNINGS.md",
            "FINAL_DECISIONS.md",
        ],
    },
]


def _load_json(path: Path) -> dict[str, Any]:
    try:
        loaded = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return {}
    return loaded if isinstance(loaded, dict) else {}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_text_for_scan(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _json_scan(path: Path) -> dict[str, Any]:
    if path.suffix.lower() != ".json":
        return {"json_valid": None, "json_top_level_keys": []}
    try:
        loaded = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        return {"json_valid": False, "json_error": exc.__class__.__name__, "json_top_level_keys": []}
    keys = sorted(loaded.keys())[:40] if isinstance(loaded, dict) else []
    return {"json_valid": True, "json_error": "", "json_top_level_keys": keys}


def _lua_scan(path: Path, text: str) -> dict[str, Any]:
    if path.suffix.lower() != ".lua":
        return {
            "reaper_calls": [],
            "disallowed_reaper_calls": [],
            "contains_parameter_writes": False,
            "contains_render_or_save_setup": False,
            "contains_media_import_or_track_creation": False,
        }
    calls = sorted(set(REAPER_CALL_RE.findall(text)))
    disallowed = sorted(set(calls) & DISALLOWED_REAPER_CALLS)
    return {
        "reaper_calls": calls,
        "disallowed_reaper_calls": disallowed,
        "contains_parameter_writes": any(call in calls for call in ["TrackFX_SetParam", "TrackFX_SetParamNormalized", "TrackFX_SetEQParam"]),
        "contains_render_or_save_setup": any(call in calls for call in ["GetSetProjectInfo", "GetSetProjectInfo_String", "Main_SaveProject", "SaveProject"]),
        "contains_media_import_or_track_creation": any(call in calls for call in ["InsertMedia", "InsertTrackAtIndex", "CreateTrackSend"]),
    }


def _secret_scan(text: str) -> dict[str, list[str]]:
    lower = text.lower()
    low = sorted(marker for marker in LOW_CONFIDENCE_SECRET_MARKERS if marker in lower)
    high = sorted({pattern.pattern for pattern in HIGH_CONFIDENCE_SECRET_PATTERNS if pattern.search(text)})
    return {"low_confidence": low, "high_confidence": high}


def _file_record(path: Path, rel: str, *, kind: str, fixture_role: str) -> dict[str, Any]:
    exists = path.is_file()
    text = _read_text_for_scan(path) if exists else ""
    stat = path.stat() if exists else None
    line_count = text.count("\n") + (1 if text and not text.endswith("\n") else 0)
    lua = _lua_scan(path, text)
    secret_scan = _secret_scan(text)
    high_confidence_secrets = secret_scan["high_confidence"]
    json_scan = _json_scan(path) if exists else {"json_valid": None, "json_top_level_keys": []}
    too_large = bool(stat and stat.st_size > MAX_FIXTURE_BYTES)
    eligible = bool(exists and not too_large and not high_confidence_secrets)
    direct_merge_blockers = [
        "legacy_runtime_code_requires_manual_review",
        "current_fail_closed_gates_must_remain_authoritative",
    ]
    if lua["disallowed_reaper_calls"]:
        direct_merge_blockers.append("legacy_lua_contains_disallowed_runtime_mutation_calls")
    if lua["contains_parameter_writes"]:
        direct_merge_blockers.append("legacy_lua_contains_parameter_write_calls")
    if lua["contains_media_import_or_track_creation"]:
        direct_merge_blockers.append("legacy_lua_mutates_project_structure")
    if high_confidence_secrets:
        direct_merge_blockers.append("credential_like_marker_detected")
    if too_large:
        direct_merge_blockers.append("fixture_file_exceeds_size_cap")
    return {
        "relative_path": rel,
        "path": str(path),
        "kind": kind,
        "fixture_role": fixture_role,
        "exists": exists,
        "size_bytes": stat.st_size if stat else 0,
        "line_count": line_count,
        "sha256": _sha256(path) if exists else "",
        "eligible_as_read_only_fixture": eligible,
        "safe_to_merge_runtime_code": False,
        "safe_to_execute_in_user_project": False,
        "safe_to_use_for_delivery_claims": False,
        "secret_markers": high_confidence_secrets,
        "low_confidence_secret_markers": secret_scan["low_confidence"],
        "direct_merge_blockers": sorted(set(direct_merge_blockers)),
        **json_scan,
        **lua,
    }


def _find_reaper_auto_mix_root(bundle_path: Path, audit: dict[str, Any]) -> Path:
    audit_root = audit.get("reaper_auto_mix_root")
    if audit_root:
        return Path(str(audit_root))
    return Path(bundle_path).expanduser() / "source_workspaces" / "tttt" / "reaper-auto-mix"


def build_public_pc_legacy_fixture_plan(
    *,
    project_name: str,
    output_dir: Path,
    bundle_path: Path | None = None,
    handoff_audit_path: Path | None = None,
) -> dict[str, Any]:
    output_dir = Path(output_dir)
    handoff_audit_path = handoff_audit_path or output_dir / HANDOFF_AUDIT_REL_PATH
    audit = _load_json(handoff_audit_path) if handoff_audit_path.exists() else {}
    bundle_root = Path(bundle_path).expanduser() if bundle_path else Path(str(audit.get("bundle_path", ""))).expanduser()
    reaper_auto_mix_root = _find_reaper_auto_mix_root(bundle_root, audit)

    blockers: list[str] = []
    warnings: list[str] = []
    if not audit:
        blockers.append("public_pc_handoff_package_audit_missing_or_invalid")
    elif not audit.get("readiness", {}).get("ready_for_targeted_fixture_import", False):
        blockers.append("public_pc_handoff_package_not_ready_for_fixture_import")
    if not reaper_auto_mix_root.is_dir():
        blockers.append("reaper_auto_mix_root_missing")

    groups: list[dict[str, Any]] = []
    all_records: list[dict[str, Any]] = []
    for group in LEGACY_FIXTURE_GROUPS:
        records = [
            _file_record(reaper_auto_mix_root / rel, rel, kind=group["kind"], fixture_role=group["fixture_role"])
            for rel in group["paths"]
        ]
        missing = [record["relative_path"] for record in records if not record["exists"]]
        unsafe_merge = [record["relative_path"] for record in records if record["direct_merge_blockers"]]
        eligible = [record["relative_path"] for record in records if record["eligible_as_read_only_fixture"]]
        if missing:
            warnings.append(f"legacy_fixture_group_missing_files:{group['id']}:{len(missing)}")
        groups.append(
            {
                "id": group["id"],
                "kind": group["kind"],
                "fixture_role": group["fixture_role"],
                "ready": bool(eligible),
                "eligible_fixture_count": len(eligible),
                "missing_files": missing,
                "unsafe_direct_merge_files": unsafe_merge,
                "files": records,
            }
        )
        all_records.extend(records)

    total_disallowed_calls = sorted({call for record in all_records for call in record.get("disallowed_reaper_calls", [])})
    records_with_secrets = [record["relative_path"] for record in all_records if record["secret_markers"]]
    records_with_low_confidence_markers = [
        record["relative_path"] for record in all_records if record.get("low_confidence_secret_markers")
    ]
    if records_with_secrets:
        blockers.append(f"high_confidence_credential_patterns_in_legacy_files:{len(records_with_secrets)}")
    if records_with_low_confidence_markers:
        warnings.append(f"low_confidence_secret_words_for_review:{len(records_with_low_confidence_markers)}")
    if total_disallowed_calls:
        warnings.append(f"legacy_lua_disallowed_calls_detected:{len(total_disallowed_calls)}")

    eligible_total = sum(1 for record in all_records if record["eligible_as_read_only_fixture"])
    status = "legacy_fixture_plan_ready" if eligible_total and not blockers else "legacy_fixture_plan_blocked"
    plan = {
        "schema": PUBLIC_PC_LEGACY_FIXTURE_PLAN_SCHEMA,
        "project_name": project_name,
        "created_at": now_utc(),
        "status": status,
        "passed": not blockers,
        "handoff_audit_path": str(handoff_audit_path),
        "bundle_path": str(bundle_root) if str(bundle_root) != "." else "",
        "reaper_auto_mix_root": str(reaper_auto_mix_root),
        "fixture_groups": groups,
        "summary": {
            "groups_total": len(groups),
            "files_total": len(all_records),
            "eligible_read_only_fixture_files": eligible_total,
            "lua_files_with_disallowed_calls": sum(1 for record in all_records if record.get("disallowed_reaper_calls")),
            "unique_disallowed_reaper_calls": total_disallowed_calls,
            "files_with_secret_markers": records_with_secrets,
            "files_with_low_confidence_secret_words": records_with_low_confidence_markers,
        },
        "readiness": {
            "ready_to_materialize_read_only_fixtures": bool(eligible_total and not blockers),
            "safe_to_merge_legacy_runtime_code": False,
            "safe_to_execute_legacy_lua_in_user_project": False,
            "safe_to_write_parameters": False,
            "safe_to_render_or_save": False,
            "safe_to_claim_final_audio_or_delivery": False,
            "report_only": True,
        },
        "blockers": sorted(set(blockers)),
        "warnings": sorted(set(warnings)),
        "limits": [
            "This plan does not copy or execute public-PC code.",
            "Eligible files may be used only as read-only regression fixtures or manual-review evidence.",
            "Legacy Lua with REAPER mutation calls is useful as a negative safety fixture, not as approved runtime automation.",
            "Current fail-closed plugin semantic validation gates remain authoritative.",
        ],
    }
    write_json(output_dir / JSON_REL_PATH, plan)
    write_public_pc_legacy_fixture_plan_report(plan, output_dir)
    return plan


def write_public_pc_legacy_fixture_plan_report(plan: dict[str, Any], output_dir: Path) -> Path:
    summary = plan.get("summary", {})
    readiness = plan.get("readiness", {})
    lines = [
        "# Public PC Legacy Fixture Plan",
        "",
        f"- Project: `{plan.get('project_name')}`",
        f"- Created UTC: `{plan.get('created_at')}`",
        f"- Status: `{plan.get('status')}`",
        f"- Passed: `{plan.get('passed')}`",
        f"- REAPER AutoMix root: `{plan.get('reaper_auto_mix_root')}`",
        "",
        "## Summary",
        "",
        f"- Fixture groups: `{summary.get('groups_total')}`",
        f"- Files reviewed: `{summary.get('files_total')}`",
        f"- Eligible read-only fixture files: `{summary.get('eligible_read_only_fixture_files')}`",
        f"- Lua files with disallowed calls: `{summary.get('lua_files_with_disallowed_calls')}`",
        f"- Unique disallowed REAPER calls: `{summary.get('unique_disallowed_reaper_calls')}`",
        "",
        "## Readiness",
        "",
    ]
    for key, value in readiness.items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(["", "## Groups", ""])
    for group in plan.get("fixture_groups", []):
        lines.extend(
            [
                f"### {group.get('id')}",
                "",
                f"- Ready: `{group.get('ready')}`",
                f"- Role: `{group.get('fixture_role')}`",
                f"- Eligible files: `{group.get('eligible_fixture_count')}`",
                f"- Missing files: `{group.get('missing_files')}`",
                "",
            ]
        )
        for record in group.get("files", []):
            calls = record.get("disallowed_reaper_calls") or []
            lines.append(
                f"- `{record.get('relative_path')}` eligible `{record.get('eligible_as_read_only_fixture')}` "
                f"merge `{record.get('safe_to_merge_runtime_code')}` sha `{str(record.get('sha256', ''))[:12]}`"
            )
            if calls:
                lines.append(f"  - disallowed calls: `{calls}`")
        lines.append("")
    lines.extend(["## Blockers", ""])
    lines.extend([f"- `{item}`" for item in plan.get("blockers", [])] or ["- none"])
    lines.extend(["", "## Warnings", ""])
    lines.extend([f"- `{item}`" for item in plan.get("warnings", [])] or ["- none"])
    lines.extend(["", "## Limits", ""])
    lines.extend([f"- {item}" for item in plan.get("limits", [])])
    path = Path(output_dir) / MD_REL_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return path

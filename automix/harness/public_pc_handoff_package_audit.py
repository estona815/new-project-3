from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from automix.plugins.plugin_adapter_schema import now_utc, write_json


PUBLIC_PC_HANDOFF_PACKAGE_AUDIT_SCHEMA = "automix-public-pc-handoff-package-audit-v1"

JSON_REL_PATH = Path("eval_reports/public_pc_handoff_package_audit.json")
MD_REL_PATH = Path("eval_reports/public_pc_handoff_package_audit.md")

TOP_LEVEL_REQUIRED = [
    "README_FIRST.md",
    "SCAN_AND_SCOPE_REPORT.md",
    "PACKAGE_MANIFEST.json",
]

REAPER_AUTOMIX_REQUIRED = [
    "README.md",
    "HANDOFF.md",
    "PROJECT_STATE.md",
    "NEXT_CODEX_PROMPT.md",
    "project_manifest.json",
    "review/handoff_validation_actual_targets_20260605.json",
    "review/red_team_report.md",
    "scripts/apply_mix_recipe.lua",
    "scripts/plugin_registry.lua",
    "scripts/validate_project_routing.lua",
    "tools/validate_recipe.py",
    "recipes/schemas/mix_recipe.schema.json",
    "recipes/schemas/qc_actions.schema.json",
]

IMPORT_CANDIDATES = [
    {
        "id": "legacy_reaper_lua_as_regression_fixtures",
        "summary": "Use legacy REAPER Lua scripts as read-only fixtures for API safety and routing regression tests.",
        "required_paths": [
            "scripts/apply_mix_recipe.lua",
            "scripts/plugin_registry.lua",
            "scripts/validate_project_routing.lua",
        ],
    },
    {
        "id": "recipe_schema_regression",
        "summary": "Use legacy mix/qc schemas and recipes as schema-compatibility fixtures.",
        "required_paths": [
            "recipes/schemas/mix_recipe.schema.json",
            "recipes/schemas/qc_actions.schema.json",
            "recipes/json/target_mix_recipe.json",
        ],
    },
    {
        "id": "historical_validation_evidence_review",
        "summary": "Review historical handoff validation and red-team notes before merging any legacy behavior.",
        "required_paths": [
            "review/handoff_validation_actual_targets_20260605.json",
            "review/red_team_report.md",
            "review/mix_risk_report.md",
        ],
    },
    {
        "id": "public_pc_handoff_docs",
        "summary": "Use handoff docs to preserve intent, restore notes, and next-step prompts without importing secrets or caches.",
        "required_paths": [
            "HANDOFF.md",
            "PROJECT_STATE.md",
            "NEXT_CODEX_PROMPT.md",
            "RESTORE_ON_OTHER_COMPUTER.md",
        ],
    },
]

AUDIO_EXTENSIONS = {".wav", ".mp3", ".flac", ".aif", ".aiff"}
REAPER_PROJECT_EXTENSIONS = {".rpp", ".rpp-bak"}
CODE_EXTENSIONS = {".py", ".lua", ".jsfx", ".json", ".md", ".ps1", ".yaml", ".yml", ".toml"}


def _load_json_utf8_or_sig(path: Path) -> tuple[dict[str, Any], str]:
    try:
        raw = path.read_text(encoding="utf-8-sig")
    except OSError as exc:
        return {}, f"read_error:{exc.__class__.__name__}"
    try:
        loaded = json.loads(raw)
    except json.JSONDecodeError as exc:
        return {}, f"json_decode_error:{exc.msg}"
    return (loaded if isinstance(loaded, dict) else {}), ""


def _relative(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return str(path)


def _exists_record(root: Path, rel: str) -> dict[str, Any]:
    path = root / rel
    return {
        "relative_path": rel,
        "path": str(path),
        "exists": path.exists(),
        "is_file": path.is_file(),
        "size_bytes": path.stat().st_size if path.is_file() else 0,
    }


def _find_source_workspace(bundle_root: Path) -> Path:
    default = bundle_root / "source_workspaces" / "tttt"
    if default.exists():
        return default
    source_roots = sorted((bundle_root / "source_workspaces").glob("*")) if (bundle_root / "source_workspaces").exists() else []
    for candidate in source_roots:
        if candidate.is_dir():
            return candidate
    return default


def _file_inventory(bundle_root: Path) -> dict[str, Any]:
    files = [path for path in bundle_root.rglob("*") if path.is_file()]
    by_extension: dict[str, int] = {}
    for path in files:
        ext = path.suffix.lower() or "<none>"
        by_extension[ext] = by_extension.get(ext, 0) + 1
    audio_files = [path for path in files if path.suffix.lower() in AUDIO_EXTENSIONS]
    reaper_projects = [path for path in files if path.suffix.lower() in REAPER_PROJECT_EXTENSIONS]
    code_files = [path for path in files if path.suffix.lower() in CODE_EXTENSIONS]
    return {
        "total_files": len(files),
        "by_extension": dict(sorted(by_extension.items())),
        "audio_files": [_relative(path, bundle_root) for path in sorted(audio_files)],
        "audio_file_count": len(audio_files),
        "reaper_project_files": [_relative(path, bundle_root) for path in sorted(reaper_projects)],
        "reaper_project_file_count": len(reaper_projects),
        "code_like_file_count": len(code_files),
    }


def _candidate_records(reaper_auto_mix_root: Path) -> list[dict[str, Any]]:
    records = []
    for candidate in IMPORT_CANDIDATES:
        required = [_exists_record(reaper_auto_mix_root, rel) for rel in candidate["required_paths"]]
        records.append(
            {
                "id": candidate["id"],
                "summary": candidate["summary"],
                "ready": all(item["exists"] and item["is_file"] for item in required),
                "required_paths": required,
                "safe_import_mode": "read_only_fixture_or_manual_review",
            }
        )
    return records


def build_public_pc_handoff_package_audit(
    *,
    project_name: str,
    output_dir: Path,
    bundle_path: Path,
) -> dict[str, Any]:
    output_dir = Path(output_dir)
    bundle_root = Path(bundle_path).expanduser()
    source_workspace = _find_source_workspace(bundle_root)
    reaper_auto_mix_root = source_workspace / "reaper-auto-mix"

    blockers: list[str] = []
    warnings: list[str] = []
    if not bundle_root.is_dir():
        blockers.append("bundle_path_missing_or_not_directory")

    top_level = [_exists_record(bundle_root, rel) for rel in TOP_LEVEL_REQUIRED]
    for item in top_level:
        if not item["exists"]:
            blockers.append(f"top_level_required_file_missing:{item['relative_path']}")

    manifest_data: dict[str, Any] = {}
    manifest_error = ""
    manifest_path = bundle_root / "PACKAGE_MANIFEST.json"
    if manifest_path.is_file():
        manifest_data, manifest_error = _load_json_utf8_or_sig(manifest_path)
        if manifest_error:
            blockers.append(f"package_manifest_unreadable:{manifest_error}")
    if manifest_data.get("bundle_root", "").startswith("C:\\"):
        warnings.append("windows_origin_paths_detected")

    reaper_required = [_exists_record(reaper_auto_mix_root, rel) for rel in REAPER_AUTOMIX_REQUIRED]
    for item in reaper_required:
        if not item["exists"]:
            warnings.append(f"reaper_auto_mix_expected_file_missing:{item['relative_path']}")

    inventory = _file_inventory(bundle_root) if bundle_root.exists() else {
        "total_files": 0,
        "by_extension": {},
        "audio_files": [],
        "audio_file_count": 0,
        "reaper_project_files": [],
        "reaper_project_file_count": 0,
        "code_like_file_count": 0,
    }
    if inventory["reaper_project_file_count"] == 0:
        warnings.append("no_rpp_project_file_in_bundle")
    if inventory["audio_file_count"] <= 1:
        warnings.append("limited_audio_evidence_in_bundle")

    import_candidates = _candidate_records(reaper_auto_mix_root) if reaper_auto_mix_root.exists() else []
    ready_import_candidates = [item["id"] for item in import_candidates if item["ready"]]
    if not reaper_auto_mix_root.is_dir():
        blockers.append("reaper_auto_mix_workspace_missing")
    elif not ready_import_candidates:
        blockers.append("no_ready_import_candidates")

    readiness = {
        "usable_for_development_planning": bool(bundle_root.is_dir() and reaper_auto_mix_root.is_dir() and not blockers),
        "ready_for_targeted_fixture_import": bool(ready_import_candidates and not blockers),
        "safe_to_merge_code_without_review": False,
        "usable_for_runtime_audio_qc": inventory["reaper_project_file_count"] > 0 and inventory["audio_file_count"] > 1,
        "safe_to_claim_final_audio_or_delivery": False,
        "report_only": True,
        "opens_reaper": False,
        "writes_parameters": False,
        "renders_audio": False,
    }

    status = "handoff_package_ready_for_targeted_development" if readiness["ready_for_targeted_fixture_import"] else "handoff_package_review_required"
    audit = {
        "schema": PUBLIC_PC_HANDOFF_PACKAGE_AUDIT_SCHEMA,
        "project_name": project_name,
        "created_at": now_utc(),
        "status": status,
        "passed": len(blockers) == 0,
        "bundle_path": str(bundle_root),
        "source_workspace": str(source_workspace),
        "reaper_auto_mix_root": str(reaper_auto_mix_root),
        "manifest": {
            "path": str(manifest_path),
            "loaded": bool(manifest_data),
            "error": manifest_error,
            "created_at": manifest_data.get("created_at", ""),
            "included_source_file_count": manifest_data.get("included_source_file_count"),
            "excluded_source_file_count": manifest_data.get("excluded_source_file_count"),
            "collected_archive_count": manifest_data.get("collected_archive_count"),
        },
        "top_level_required_files": top_level,
        "reaper_auto_mix_required_files": reaper_required,
        "inventory": inventory,
        "import_candidates": import_candidates,
        "ready_import_candidates": ready_import_candidates,
        "readiness": readiness,
        "blockers": blockers,
        "warnings": warnings,
        "limits": [
            "This audit only evaluates the public-PC handoff package as development evidence.",
            "The package does not prove final audio quality, REAPER runtime behavior, or user approval.",
            "Legacy code from this bundle must remain read-only fixture material until reviewed against current fail-closed gates.",
        ],
    }
    write_json(output_dir / JSON_REL_PATH, audit)
    write_public_pc_handoff_package_report(audit, output_dir)
    return audit


def write_public_pc_handoff_package_report(audit: dict[str, Any], output_dir: Path) -> Path:
    readiness = audit.get("readiness", {})
    manifest = audit.get("manifest", {})
    inventory = audit.get("inventory", {})
    lines = [
        "# Public PC Handoff Package Audit",
        "",
        f"- Project: `{audit.get('project_name')}`",
        f"- Created UTC: `{audit.get('created_at')}`",
        f"- Status: `{audit.get('status')}`",
        f"- Passed: `{audit.get('passed')}`",
        f"- Bundle: `{audit.get('bundle_path')}`",
        f"- Source workspace: `{audit.get('source_workspace')}`",
        f"- REAPER AutoMix root: `{audit.get('reaper_auto_mix_root')}`",
        "",
        "## Readiness",
        "",
    ]
    for key, value in readiness.items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(
        [
            "",
            "## Manifest",
            "",
            f"- Loaded: `{manifest.get('loaded')}`",
            f"- Created at: `{manifest.get('created_at')}`",
            f"- Included source files: `{manifest.get('included_source_file_count')}`",
            f"- Excluded source files: `{manifest.get('excluded_source_file_count')}`",
            f"- Collected archives: `{manifest.get('collected_archive_count')}`",
            "",
            "## Inventory",
            "",
            f"- Total files: `{inventory.get('total_files')}`",
            f"- Code-like files: `{inventory.get('code_like_file_count')}`",
            f"- Audio files: `{inventory.get('audio_file_count')}`",
            f"- REAPER project files: `{inventory.get('reaper_project_file_count')}`",
            "",
        ]
    )
    if inventory.get("audio_files"):
        lines.append("### Audio Files")
        lines.append("")
        lines.extend(f"- `{item}`" for item in inventory.get("audio_files", []))
        lines.append("")
    lines.extend(["## Import Candidates", ""])
    for item in audit.get("import_candidates", []):
        lines.extend(
            [
                f"### {item.get('id')}",
                "",
                f"- Ready: `{item.get('ready')}`",
                f"- Mode: `{item.get('safe_import_mode')}`",
                f"- Summary: {item.get('summary')}",
                "",
            ]
        )
    lines.extend(["## Blockers", ""])
    lines.extend([f"- `{item}`" for item in audit.get("blockers", [])] or ["- none"])
    lines.extend(["", "## Warnings", ""])
    lines.extend([f"- `{item}`" for item in audit.get("warnings", [])] or ["- none"])
    lines.extend(["", "## Limits", ""])
    lines.extend([f"- {item}" for item in audit.get("limits", [])])
    path = Path(output_dir) / MD_REL_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return path

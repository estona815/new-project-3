from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from automix.orchestrator.global_rollback_registry import validate_global_rollback_integrity
from automix.plugins.plugin_adapter_schema import now_utc, write_json


ROLLBACK_EVIDENCE_SCHEMA = "automix-rollback-evidence-gate-v1"

GATE_REL_PATH = Path("eval_reports/rollback_evidence_gate.json")
GATE_REPORT_REL_PATH = Path("eval_reports/rollback_evidence_gate.md")
TEMPLATE_REL_PATH = Path("review/rollback_evidence_manifest_template.json")
REQUEST_REL_PATH = Path("review/rollback_evidence_request.md")

DEFAULT_REGISTRY_REL_PATH = Path("rollback/global_rollback_registry.json")


def _load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _resolve_path(path_text: str, output_dir: Path) -> Path:
    path = Path(path_text)
    if path.is_absolute():
        return path
    candidates = [path, output_dir / path, output_dir.parent / path]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return path


def _entry_result(entry: dict[str, Any], output_dir: Path, registry_path: Path) -> dict[str, Any]:
    stage = str(entry.get("stage", "") or "unknown")
    rollback_file = str(entry.get("rollback_file", "") or "")
    safe = bool(entry.get("safe_to_rollback", False))
    resolved = _resolve_path(rollback_file, output_dir) if rollback_file else Path("")
    blockers: list[str] = []
    warnings: list[str] = []
    if not rollback_file:
        blockers.append("rollback_file_path_missing")
    elif not resolved.exists():
        blockers.append("rollback_file_missing")
    elif not resolved.is_file():
        blockers.append("rollback_file_not_file")
    elif resolved.stat().st_size <= 0:
        blockers.append("rollback_file_empty")
    if not safe:
        blockers.append("rollback_entry_not_safe")
    if stage == "unknown":
        warnings.append("rollback_stage_unknown")
    try:
        if rollback_file and resolved.resolve() == registry_path.resolve():
            warnings.append("rollback_entry_points_to_global_registry")
    except OSError:
        pass
    return {
        "stage": stage,
        "rollback_file": rollback_file,
        "resolved_path": str(resolved) if rollback_file else "",
        "exists": bool(rollback_file and resolved.exists()),
        "safe_to_rollback": safe,
        "blockers": sorted(set(blockers)),
        "warnings": sorted(set(warnings)),
    }


def _template() -> dict[str, Any]:
    return {
        "schema": "automix-rollback-evidence-manifest-template-v1",
        "expected_registry": "automix/rollback/global_rollback_registry.json",
        "required_checks": [
            "original_tracks_protected is true",
            "original_master_protected is true",
            "validation.passed is true",
            "each applied stage has a rollback_file",
            "each rollback_file exists and is nonempty",
            "each entry has safe_to_rollback true",
        ],
        "limits": [
            "This template is not final approval.",
            "Rollback evidence does not prove audio quality.",
            "Scan-only/report-only runs may have no applied stages, but must still prove originals are protected.",
        ],
    }


def build_rollback_evidence_gate(
    *,
    project_name: str,
    output_dir: Path,
    registry_path: Path | None = None,
    output_path: Path | None = None,
) -> dict[str, Any]:
    output_dir = Path(output_dir)
    registry_file = Path(registry_path) if registry_path else output_dir / DEFAULT_REGISTRY_REL_PATH
    registry = _load_json(registry_file)
    blockers: list[str] = []
    warnings: list[str] = []

    if not registry_file.exists() or not registry:
        blockers.append("rollback_registry_missing_or_invalid")
    elif registry.get("schema") != "automix-global-rollback-registry-v1":
        blockers.append("rollback_registry_schema_invalid")

    if registry and not registry.get("original_tracks_protected", False):
        blockers.append("original_tracks_not_protected")
    if registry and not registry.get("original_master_protected", False):
        blockers.append("original_master_not_protected")

    entries_raw = registry.get("rollback_entries", []) if isinstance(registry.get("rollback_entries", []), list) else []
    entries = [item for item in entries_raw if isinstance(item, dict)]
    entry_results = [_entry_result(item, output_dir, registry_file) for item in entries]
    for item in entry_results:
        blockers.extend(f"{item.get('stage')}:rollback_entry:{blocker}" for blocker in item.get("blockers", []))
        warnings.extend(f"{item.get('stage')}:rollback_entry:{warning}" for warning in item.get("warnings", []))

    applied_stages = [str(item) for item in registry.get("applied_stages", []) or []] if registry else []
    if registry and not entries and applied_stages:
        blockers.append("applied_stages_present_but_no_rollback_entries")
    if registry and not applied_stages:
        warnings.append("no_applied_stages_declared")

    stored_validation = registry.get("validation", {}) if isinstance(registry.get("validation", {}), dict) else {}
    recomputed_validation = validate_global_rollback_integrity(registry, applied_stages=applied_stages) if registry else {"passed": False, "failures": ["rollback_registry_missing_or_invalid"], "warnings": []}
    for label, validation in (("stored", stored_validation), ("recomputed", recomputed_validation)):
        if validation and not validation.get("passed", False):
            for failure in validation.get("failures", []) or ["rollback_validation_failed"]:
                blockers.append(f"{label}_rollback_validation:{failure}")
            for warning in validation.get("warnings", []) or []:
                warnings.append(f"{label}_rollback_validation:{warning}")
    if registry and not stored_validation:
        blockers.append("rollback_validation_missing")

    blockers = sorted(set(blockers))
    warnings = sorted(set(warnings))
    ready = not blockers
    template_path = output_dir / TEMPLATE_REL_PATH
    write_json(template_path, _template())
    gate = {
        "schema": ROLLBACK_EVIDENCE_SCHEMA,
        "project_name": project_name,
        "created_at": now_utc(),
        "output_dir": str(output_dir),
        "registry_path": str(registry_file),
        "ready_for_delivery_readiness": ready,
        "original_tracks_protected": bool(registry.get("original_tracks_protected", False)),
        "original_master_protected": bool(registry.get("original_master_protected", False)),
        "applied_stages": applied_stages,
        "rollback_entries_total": len(entry_results),
        "safe_entries_total": sum(1 for item in entry_results if item.get("safe_to_rollback") and not item.get("blockers")),
        "entry_results": entry_results,
        "stored_validation": stored_validation,
        "recomputed_validation": recomputed_validation,
        "blockers": blockers,
        "warnings": warnings,
        "template_path": str(template_path),
        "limits": [
            "This gate validates rollback evidence only; it does not approve audio.",
            "Rollback evidence does not replace final QC, A/B review, or human approval.",
            "If a stage was applied without rollback evidence, delivery remains blocked.",
        ],
    }
    target = output_path or output_dir / GATE_REL_PATH
    write_json(target, gate)
    write_rollback_evidence_report(gate, output_dir)
    write_rollback_evidence_request(gate, output_dir)
    return gate


def write_rollback_evidence_report(gate: dict[str, Any], output_dir: Path) -> Path:
    lines = [
        "# Rollback Evidence Gate",
        "",
        f"- Project: `{gate.get('project_name')}`",
        f"- Created UTC: `{gate.get('created_at')}`",
        f"- Ready for delivery readiness: `{gate.get('ready_for_delivery_readiness')}`",
        f"- Original tracks protected: `{gate.get('original_tracks_protected')}`",
        f"- Original master protected: `{gate.get('original_master_protected')}`",
        f"- Applied stages: `{gate.get('applied_stages', [])}`",
        f"- Rollback entries: `{gate.get('rollback_entries_total')}`",
        f"- Safe entries: `{gate.get('safe_entries_total')}`",
        "",
        "This gate does not approve audio. It only checks rollback evidence.",
        "",
        "## Blockers",
        "",
    ]
    lines.extend([f"- `{item}`" for item in gate.get("blockers", [])] or ["- none"])
    lines.extend(["", "## Warnings", ""])
    lines.extend([f"- `{item}`" for item in gate.get("warnings", [])] or ["- none"])
    lines.extend(["", "## Entries", ""])
    for item in gate.get("entry_results", []):
        lines.append(f"- `{item.get('stage')}` file=`{item.get('rollback_file')}` safe=`{item.get('safe_to_rollback')}` blockers=`{item.get('blockers', [])}`")
    if not gate.get("entry_results"):
        lines.append("- none")
    path = Path(output_dir) / GATE_REPORT_REL_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return path


def write_rollback_evidence_request(gate: dict[str, Any], output_dir: Path) -> Path:
    lines = [
        "# Rollback Evidence Request",
        "",
        f"- Project: `{gate.get('project_name')}`",
        f"- Template: `{gate.get('template_path')}`",
        "",
    ]
    if gate.get("ready_for_delivery_readiness"):
        lines.extend(
            [
                "Rollback evidence is ready for delivery-readiness checks. This is not final approval.",
                "",
                "Next checks:",
                "",
                "- Keep rollback files with the review/delivery package.",
                "- Verify final render, QC, A/B preview, and human approval evidence separately.",
            ]
        )
    else:
        lines.extend(["Rollback evidence is not ready. Resolve these blockers first:", ""])
        lines.extend([f"- `{item}`" for item in gate.get("blockers", [])] or ["- none"])
    path = Path(output_dir) / REQUEST_REL_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return path

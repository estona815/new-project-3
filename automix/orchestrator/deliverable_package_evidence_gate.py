from __future__ import annotations

import json
import zipfile
from pathlib import Path
from typing import Any

from automix.plugins.plugin_adapter_schema import now_utc, write_json


DELIVERABLE_PACKAGE_EVIDENCE_SCHEMA = "automix-deliverable-package-evidence-gate-v1"

GATE_REL_PATH = Path("eval_reports/deliverable_package_evidence_gate.json")
GATE_REPORT_REL_PATH = Path("eval_reports/deliverable_package_evidence_gate.md")
TEMPLATE_REL_PATH = Path("review/deliverable_package_evidence_manifest_template.json")
REQUEST_REL_PATH = Path("review/deliverable_package_evidence_request.md")

PACKAGE_MANIFEST_REL_PATH = Path("export/deliverable_package_manifest.json")
PROJECT_STATE_REL_PATH = Path("export/project_state_manifest.json")

REQUIRED_EVIDENCE_REL_PATHS = [
    Path("export/final_render_manifest.json"),
    Path("eval_reports/final_render_evidence_gate.json"),
    Path("eval_reports/final_qc_metrics.json"),
    Path("eval_reports/final_qc_evidence_gate.json"),
    Path("eval_reports/final_ab_preview_manifest.json"),
    Path("eval_reports/ab_preview_evidence_gate.json"),
    Path("review/final_human_approval.json"),
    Path("eval_reports/final_approval_evidence_gate.json"),
    Path("rollback/global_rollback_registry.json"),
    Path("eval_reports/rollback_evidence_gate.json"),
    Path("eval_reports/final_qc_report.md"),
    Path("export/project_state_manifest.json"),
    Path("export/plugin_mapping_summary.md"),
]

SUPPORTING_GATES = [
    (
        Path("eval_reports/final_render_evidence_gate.json"),
        "automix-final-render-evidence-gate-v1",
        "ready_for_approval_readiness",
        "final_render_evidence",
    ),
    (
        Path("eval_reports/final_qc_evidence_gate.json"),
        "automix-final-qc-evidence-gate-v1",
        "ready_for_delivery_qc",
        "final_qc_evidence",
    ),
    (
        Path("eval_reports/ab_preview_evidence_gate.json"),
        "automix-ab-preview-evidence-gate-v1",
        "ready_for_human_ab_review",
        "ab_preview_evidence",
    ),
    (
        Path("eval_reports/final_approval_evidence_gate.json"),
        "automix-final-approval-evidence-gate-v1",
        "ready_for_delivery_request",
        "final_approval_evidence",
    ),
    (
        Path("eval_reports/rollback_evidence_gate.json"),
        "automix-rollback-evidence-gate-v1",
        "ready_for_delivery_readiness",
        "rollback_evidence",
    ),
]

SECRET_PATH_MARKERS = (
    ".env",
    ".pem",
    ".key",
    "api_key",
    "apikey",
    "credential",
    "credentials",
    "secret",
    "token",
)

RAW_AUDIO_PATH_MARKERS = (
    "input_stems/",
    "input-stems/",
    "raw_stems/",
    "raw-stems/",
    "references/",
    "reference_audio/",
    "source_packages/",
)


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
    return output_dir / path


def _path_status(path_text: str, output_dir: Path) -> dict[str, Any]:
    path = _resolve_path(path_text, output_dir)
    return {
        "input_path": path_text,
        "path": str(path),
        "exists": path.exists(),
        "is_file": path.is_file(),
        "size_bytes": path.stat().st_size if path.exists() and path.is_file() else 0,
    }


def _included_paths(manifest: dict[str, Any]) -> list[str]:
    raw = manifest.get("files_included", [])
    if not isinstance(raw, list):
        return []
    return sorted({str(item) for item in raw if str(item)})


def _included_name_index(paths: list[str]) -> set[str]:
    names: set[str] = set()
    for path_text in paths:
        path = Path(path_text)
        names.add(path.name.lower())
        try:
            names.add(str(Path(*path.parts[-2:])).lower())
        except TypeError:
            pass
    return names


def _evidence_file_status(output_dir: Path, manifest: dict[str, Any]) -> list[dict[str, Any]]:
    included = _included_paths(manifest)
    included_names = _included_name_index(included)
    statuses: list[dict[str, Any]] = []
    for rel in REQUIRED_EVIDENCE_REL_PATHS:
        disk_path = output_dir / rel
        filename_present_in_manifest = rel.name.lower() in included_names or str(Path(*rel.parts[-2:])).lower() in included_names
        statuses.append(
            {
                "relative_path": str(rel),
                "disk_path": str(disk_path),
                "exists_on_disk": disk_path.exists(),
                "size_bytes": disk_path.stat().st_size if disk_path.exists() and disk_path.is_file() else 0,
                "present_in_package_manifest": filename_present_in_manifest,
                "satisfied": (disk_path.exists() and disk_path.is_file() and disk_path.stat().st_size > 0) or filename_present_in_manifest,
            }
        )
    return statuses


def _zip_status(zip_path_text: str, output_dir: Path) -> dict[str, Any]:
    status = _path_status(zip_path_text, output_dir) if zip_path_text else {
        "input_path": "",
        "path": "",
        "exists": False,
        "is_file": False,
        "size_bytes": 0,
    }
    failures: list[str] = []
    warnings: list[str] = []
    names: list[str] = []
    if not zip_path_text:
        failures.append("deliverable_zip_path_missing")
    elif not status["exists"]:
        failures.append("deliverable_zip_missing")
    elif not status["is_file"]:
        failures.append("deliverable_zip_path_not_file")
    elif int(status["size_bytes"] or 0) <= 0:
        failures.append("deliverable_zip_empty_on_disk")
    elif Path(str(status["path"])).suffix.lower() != ".zip":
        failures.append("deliverable_zip_not_zip_suffix")
    else:
        try:
            with zipfile.ZipFile(str(status["path"])) as archive:
                bad_member = archive.testzip()
                names = archive.namelist()
        except (OSError, zipfile.BadZipFile) as exc:
            failures.append(f"deliverable_zip_unreadable:{exc}")
        else:
            if bad_member:
                failures.append(f"deliverable_zip_corrupt_member:{bad_member}")
            if not names:
                failures.append("deliverable_zip_has_no_files")
    if names and any(name.endswith("/") for name in names):
        warnings.append("deliverable_zip_contains_directory_entries")
    return {
        **status,
        "valid_zip": not failures,
        "entry_count": len(names),
        "entries": names[:200],
        "failures": sorted(set(failures)),
        "warnings": sorted(set(warnings)),
    }


def _supporting_gate_status(output_dir: Path) -> list[dict[str, Any]]:
    statuses: list[dict[str, Any]] = []
    for rel, schema, ready_key, code in SUPPORTING_GATES:
        path = output_dir / rel
        data = _load_json(path)
        statuses.append(
            {
                "code": code,
                "relative_path": str(rel),
                "path": str(path),
                "exists": path.exists(),
                "schema_valid": bool(data) and data.get("schema") == schema,
                "ready_key": ready_key,
                "ready": bool(data.get(ready_key, False)),
                "blockers": data.get("blockers", []) if isinstance(data.get("blockers", []), list) else [],
                "warnings": data.get("warnings", []) if isinstance(data.get("warnings", []), list) else [],
            }
        )
    return statuses


def _sensitive_path_findings(paths: list[str]) -> list[str]:
    findings: list[str] = []
    for path_text in paths:
        lowered = path_text.replace("\\", "/").lower()
        name = Path(lowered).name
        if any(marker in lowered for marker in SECRET_PATH_MARKERS):
            findings.append(f"sensitive_or_secret_file_included:{path_text}")
        elif any(marker in lowered for marker in RAW_AUDIO_PATH_MARKERS):
            findings.append(f"raw_or_reference_source_path_included:{path_text}")
        elif name.startswith("raw_") or "_raw_" in name or name.startswith("stem_") or "_stem_" in name:
            findings.append(f"raw_or_stem_named_file_included:{path_text}")
    return sorted(set(findings))


def _naming_blockers(manifest: dict[str, Any], zip_status: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    zip_name = Path(str(zip_status.get("path", ""))).name
    manifest_text = json.dumps(manifest, ensure_ascii=False).lower()
    unsafe = bool(manifest.get("unsafe_override", False)) or "unsafe_review_copy" in zip_name.lower() or "unsafe_review_copy" in manifest_text
    final_safe = "final_safe" in zip_name.lower() or "final_safe" in manifest_text
    if unsafe and final_safe:
        blockers.append("unsafe_review_copy_named_final_safe")
    return blockers


def _template() -> dict[str, Any]:
    return {
        "schema": "automix-deliverable-package-evidence-manifest-template-v1",
        "expected_manifest": "automix/export/deliverable_package_manifest.json",
        "required_evidence_files": [f"automix/{rel}" for rel in REQUIRED_EVIDENCE_REL_PATHS],
        "required_checks": [
            "deliverable_package_manifest uses schema automix-deliverable-package-manifest-v1",
            "package_created is true",
            "zip_path exists, is a nonempty .zip file, and zip integrity passes",
            "package_size_bytes matches the actual ZIP size",
            "files_missing is empty and every included file still exists on disk",
            "project_state_manifest proves original tracks are protected and the master is unchanged",
            "supporting render, QC, A/B, approval, and rollback evidence gates are ready",
            "package paths do not include credentials, raw stems, references, or source packages by default",
        ],
        "limits": [
            "This gate validates package evidence only; it does not approve audio.",
            "A valid ZIP does not replace final QC, matched-loudness A/B, or human approval.",
            "Raw stems, references, renders not selected for delivery, and credential-like files remain excluded by default.",
        ],
    }


def build_deliverable_package_evidence_gate(
    *,
    project_name: str,
    output_dir: Path,
    package_manifest_path: Path | None = None,
    output_path: Path | None = None,
) -> dict[str, Any]:
    output_dir = Path(output_dir)
    manifest_path = Path(package_manifest_path) if package_manifest_path else output_dir / PACKAGE_MANIFEST_REL_PATH
    manifest = _load_json(manifest_path)
    blockers: list[str] = []
    warnings: list[str] = []

    if not manifest_path.exists() or not manifest:
        blockers.append("deliverable_package_manifest_missing_or_invalid")
    elif manifest.get("schema") != "automix-deliverable-package-manifest-v1":
        blockers.append("deliverable_package_manifest_schema_invalid")

    if manifest and not manifest.get("package_created", False):
        blockers.append("deliverable_package_not_created")

    zip_status = _zip_status(str(manifest.get("zip_path", "") or ""), output_dir)
    blockers.extend(zip_status.get("failures", []))
    warnings.extend(zip_status.get("warnings", []))

    actual_zip_size = int(zip_status.get("size_bytes", 0) or 0)
    declared_zip_size = int(manifest.get("package_size_bytes", 0) or 0)
    if declared_zip_size <= 0:
        blockers.append("deliverable_package_size_missing_or_zero")
    elif actual_zip_size and declared_zip_size != actual_zip_size:
        blockers.append("deliverable_package_size_mismatch")

    files_missing = [str(item) for item in manifest.get("files_missing", []) or []]
    if files_missing:
        blockers.append("deliverable_package_manifest_has_missing_files")

    included = _included_paths(manifest)
    included_file_statuses = [_path_status(path_text, output_dir) for path_text in included]
    for status in included_file_statuses:
        if not status["exists"]:
            blockers.append(f"included_file_missing:{status['input_path']}")
        elif not status["is_file"]:
            blockers.append(f"included_path_not_file:{status['input_path']}")
        elif int(status["size_bytes"] or 0) <= 0:
            blockers.append(f"included_file_empty:{status['input_path']}")
    if not included:
        blockers.append("deliverable_package_included_files_missing")

    evidence_statuses = _evidence_file_status(output_dir, manifest)
    for status in evidence_statuses:
        if not status["satisfied"]:
            blockers.append(f"required_delivery_evidence_missing:{status['relative_path']}")

    project_state = manifest.get("project_state_manifest", {}) if isinstance(manifest.get("project_state_manifest", {}), dict) else {}
    disk_project_state = _load_json(output_dir / PROJECT_STATE_REL_PATH)
    if not project_state and disk_project_state:
        project_state = disk_project_state
    if not project_state:
        blockers.append("project_state_manifest_missing")
    else:
        if project_state.get("original_tracks_protected") is not True:
            blockers.append("project_state_original_tracks_not_protected")
        if project_state.get("master_unchanged") is not True:
            blockers.append("project_state_master_mutated")

    supporting_gate_statuses = _supporting_gate_status(output_dir)
    for status in supporting_gate_statuses:
        code = status["code"]
        if not status["exists"]:
            blockers.append(f"{code}_gate_missing")
        elif not status["schema_valid"]:
            blockers.append(f"{code}_gate_schema_invalid")
        elif not status["ready"]:
            blockers.append(f"{code}_gate_not_ready")
            blockers.extend(f"{code}:{item}" for item in status.get("blockers", []) or [])

    blockers.extend(_naming_blockers(manifest, zip_status))
    blockers.extend(_sensitive_path_findings(included))

    blockers = sorted(set(blockers))
    warnings = sorted(set(warnings))
    ready = not blockers

    template_path = output_dir / TEMPLATE_REL_PATH
    write_json(template_path, _template())
    gate = {
        "schema": DELIVERABLE_PACKAGE_EVIDENCE_SCHEMA,
        "project_name": project_name,
        "created_at": now_utc(),
        "output_dir": str(output_dir),
        "package_manifest_path": str(manifest_path),
        "ready_for_delivery_package": ready,
        "ready_for_professional_readiness": ready,
        "package_summary": {
            "package_created": bool(manifest.get("package_created", False)),
            "zip_path": str(manifest.get("zip_path", "") or ""),
            "package_size_bytes": declared_zip_size,
            "actual_zip_size_bytes": actual_zip_size,
            "files_included_count": len(included),
            "files_missing": files_missing,
        },
        "zip_status": zip_status,
        "included_file_statuses": included_file_statuses,
        "required_evidence_file_statuses": evidence_statuses,
        "supporting_gate_statuses": supporting_gate_statuses,
        "project_state_summary": {
            "original_tracks_protected": bool(project_state.get("original_tracks_protected", False)),
            "master_unchanged": bool(project_state.get("master_unchanged", False)),
            "accepted_sources": project_state.get("accepted_sources", []) if isinstance(project_state.get("accepted_sources", []), list) else [],
        },
        "blockers": blockers,
        "warnings": warnings,
        "template_path": str(template_path),
        "limits": [
            "This gate validates deliverable package evidence only; it does not approve audio.",
            "A valid package does not replace measured final QC, matched-loudness A/B review, rollback evidence, or final human approval.",
            "Raw stems, references, source packages, and credential-like files remain excluded by default.",
        ],
    }
    target = output_path or output_dir / GATE_REL_PATH
    write_json(target, gate)
    write_deliverable_package_evidence_report(gate, output_dir)
    write_deliverable_package_evidence_request(gate, output_dir)
    return gate


def write_deliverable_package_evidence_report(gate: dict[str, Any], output_dir: Path) -> Path:
    package = gate.get("package_summary", {})
    zip_status = gate.get("zip_status", {})
    project_state = gate.get("project_state_summary", {})
    lines = [
        "# Deliverable Package Evidence Gate",
        "",
        f"- Project: `{gate.get('project_name')}`",
        f"- Created UTC: `{gate.get('created_at')}`",
        f"- Ready for delivery package: `{gate.get('ready_for_delivery_package')}`",
        f"- Ready for professional readiness: `{gate.get('ready_for_professional_readiness')}`",
        f"- Package created: `{package.get('package_created')}`",
        f"- ZIP path: `{package.get('zip_path')}`",
        f"- ZIP valid: `{zip_status.get('valid_zip')}`",
        f"- ZIP entries: `{zip_status.get('entry_count')}`",
        f"- Included files: `{package.get('files_included_count')}`",
        f"- Missing files: `{package.get('files_missing')}`",
        f"- Original tracks protected: `{project_state.get('original_tracks_protected')}`",
        f"- Master unchanged: `{project_state.get('master_unchanged')}`",
        "",
        "This gate validates the deliverable package evidence only. It does not approve audio.",
        "",
        "## Blockers",
        "",
    ]
    lines.extend([f"- `{item}`" for item in gate.get("blockers", [])] or ["- none"])
    lines.extend(["", "## Warnings", ""])
    lines.extend([f"- `{item}`" for item in gate.get("warnings", [])] or ["- none"])
    lines.extend(["", "## Required Evidence Files", ""])
    for status in gate.get("required_evidence_file_statuses", []):
        lines.append(
            f"- `{status.get('relative_path')}`: disk=`{status.get('exists_on_disk')}`, "
            f"manifest=`{status.get('present_in_package_manifest')}`, satisfied=`{status.get('satisfied')}`"
        )
    lines.extend(["", "## Supporting Gates", ""])
    for status in gate.get("supporting_gate_statuses", []):
        lines.append(f"- `{status.get('code')}` ready=`{status.get('ready')}` schema_valid=`{status.get('schema_valid')}`")
    path = Path(output_dir) / GATE_REPORT_REL_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return path


def write_deliverable_package_evidence_request(gate: dict[str, Any], output_dir: Path) -> Path:
    lines = [
        "# Deliverable Package Evidence Request",
        "",
        "Create or repair the final deliverable ZIP only after render, QC, A/B, rollback, and final approval evidence are ready.",
        "",
        "## Current Status",
        "",
        f"- Ready for delivery package: `{gate.get('ready_for_delivery_package')}`",
        f"- Package manifest: `{gate.get('package_manifest_path')}`",
        f"- Template: `{gate.get('template_path')}`",
        "",
        "## Required Evidence",
        "",
    ]
    lines.extend([f"- `automix/{rel}`" for rel in REQUIRED_EVIDENCE_REL_PATHS])
    lines.extend(["", "## Blockers", ""])
    lines.extend([f"- `{item}`" for item in gate.get("blockers", [])] or ["- none"])
    lines.extend(
        [
            "",
            "## Limits",
            "",
            "- Do not include raw stems, references, source packages, credentials, tokens, or secret files in the delivery package by default.",
            "- Do not mark unsafe review copies as final-safe deliverables.",
            "- This request does not replace human listening approval.",
        ]
    )
    path = Path(output_dir) / REQUEST_REL_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return path

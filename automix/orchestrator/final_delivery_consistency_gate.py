from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from automix.plugins.plugin_adapter_schema import now_utc, write_json


FINAL_DELIVERY_CONSISTENCY_SCHEMA = "automix-final-delivery-consistency-gate-v1"

GATE_REL_PATH = Path("eval_reports/final_delivery_consistency_gate.json")
GATE_REPORT_REL_PATH = Path("eval_reports/final_delivery_consistency_gate.md")
TEMPLATE_REL_PATH = Path("review/final_delivery_consistency_manifest_template.json")
REQUEST_REL_PATH = Path("review/final_delivery_consistency_request.md")

EVIDENCE_REL_PATHS = {
    "final_export_state": Path("export/final_export_state.json"),
    "final_render_manifest": Path("export/final_render_manifest.json"),
    "final_render_evidence_gate": Path("eval_reports/final_render_evidence_gate.json"),
    "final_qc_metrics": Path("eval_reports/final_qc_metrics.json"),
    "final_qc_evidence_gate": Path("eval_reports/final_qc_evidence_gate.json"),
    "final_ab_preview_manifest": Path("eval_reports/final_ab_preview_manifest.json"),
    "ab_preview_evidence_gate": Path("eval_reports/ab_preview_evidence_gate.json"),
    "final_human_approval": Path("review/final_human_approval.json"),
    "final_approval_evidence_gate": Path("eval_reports/final_approval_evidence_gate.json"),
    "deliverable_package_manifest": Path("export/deliverable_package_manifest.json"),
    "deliverable_package_evidence_gate": Path("eval_reports/deliverable_package_evidence_gate.json"),
    "project_state_manifest": Path("export/project_state_manifest.json"),
    "rollback_evidence_gate": Path("eval_reports/rollback_evidence_gate.json"),
}

EXPECTED_SCHEMAS = {
    "final_export_state": "automix-final-export-state-v1",
    "final_render_manifest": "automix-final-render-manifest-v1",
    "final_render_evidence_gate": "automix-final-render-evidence-gate-v1",
    "final_qc_metrics": "automix-final-qc-metrics-v1",
    "final_qc_evidence_gate": "automix-final-qc-evidence-gate-v1",
    "final_ab_preview_manifest": "automix-final-ab-preview-v1",
    "ab_preview_evidence_gate": "automix-ab-preview-evidence-gate-v1",
    "final_human_approval": "automix-final-human-approval-v1",
    "final_approval_evidence_gate": "automix-final-approval-evidence-gate-v1",
    "deliverable_package_manifest": "automix-deliverable-package-manifest-v1",
    "deliverable_package_evidence_gate": "automix-deliverable-package-evidence-gate-v1",
    "project_state_manifest": "automix-project-state-manifest-v1",
    "rollback_evidence_gate": "automix-rollback-evidence-gate-v1",
}


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


def _path_key(path_text: str, output_dir: Path) -> str:
    if not path_text:
        return ""
    try:
        return str(_resolve_path(path_text, output_dir).resolve())
    except OSError:
        return str(_resolve_path(path_text, output_dir))


def _path_exists_nonzero(path_text: str, output_dir: Path) -> bool:
    if not path_text:
        return False
    path = _resolve_path(path_text, output_dir)
    return path.exists() and path.is_file() and path.stat().st_size > 0


def _path_text(value: Any) -> str:
    text = str(value or "")
    return "" if text in {"", "."} else text


def _primary_render_path(manifest: dict[str, Any]) -> str:
    for item in manifest.get("renders", []) if isinstance(manifest.get("renders", []), list) else []:
        if not isinstance(item, dict):
            continue
        if item.get("format") == "wav" and item.get("created") and int(item.get("size_bytes", 0) or 0) > 0:
            return str(item.get("path", "") or "")
    return ""


def _included_paths(package_manifest: dict[str, Any]) -> list[str]:
    raw = package_manifest.get("files_included", [])
    if not isinstance(raw, list):
        return []
    return [str(item) for item in raw if str(item)]


def _included_names(package_manifest: dict[str, Any]) -> set[str]:
    return {Path(path).name.lower() for path in _included_paths(package_manifest)}


def _add_mismatch(
    blockers: list[str],
    *,
    code: str,
    left: str,
    right: str,
    output_dir: Path,
) -> None:
    if left and right and _path_key(left, output_dir) != _path_key(right, output_dir):
        blockers.append(code)


def _evidence_status(output_dir: Path) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    status: dict[str, dict[str, Any]] = {}
    data: dict[str, dict[str, Any]] = {}
    for name, rel in EVIDENCE_REL_PATHS.items():
        path = output_dir / rel
        loaded = _load_json(path)
        data[name] = loaded
        status[name] = {
            "relative_path": str(rel),
            "path": str(path),
            "exists": path.exists(),
            "json_valid": bool(loaded) if path.exists() else None,
            "schema": loaded.get("schema", ""),
            "schema_valid": bool(loaded) and loaded.get("schema") == EXPECTED_SCHEMAS[name],
        }
    return status, data


def _template() -> dict[str, Any]:
    return {
        "schema": "automix-final-delivery-consistency-manifest-template-v1",
        "expected_reports": [f"automix/{rel}" for rel in EVIDENCE_REL_PATHS.values()],
        "required_checks": [
            "final export state, render evidence, QC evidence, A/B evidence, final approval, package evidence, project state, and rollback evidence use expected schemas",
            "supporting final render, QC, A/B, approval, package, and rollback gates are ready",
            "final audio path is consistent across render manifest, render evidence, QC metrics, QC evidence, A/B preview, and approval records",
            "A/B preview output path is consistent across preview manifest, A/B evidence, approval evidence, and human approval record",
            "approved source and stage match the final export state",
            "project state records original/master protection and the selected source when a selected source exists",
            "package manifest lists the final audio and A/B preview filenames and matches package evidence ZIP path/size",
        ],
        "limits": [
            "This gate validates cross-report consistency only; it does not approve audio.",
            "A passing consistency gate does not replace measured QC, matched-loudness listening, or human approval.",
            "Missing real audio/source evidence remains a blocker even if report schemas are present.",
        ],
    }


def build_final_delivery_consistency_gate(
    *,
    project_name: str,
    output_dir: Path,
    output_path: Path | None = None,
) -> dict[str, Any]:
    output_dir = Path(output_dir)
    evidence, data = _evidence_status(output_dir)
    blockers: list[str] = []
    warnings: list[str] = []

    for name, status in evidence.items():
        if not status["exists"] or not status["json_valid"]:
            blockers.append(f"{name}_missing_or_invalid")
        elif not status["schema_valid"]:
            blockers.append(f"{name}_schema_invalid")

    export_state = data["final_export_state"]
    render_manifest = data["final_render_manifest"]
    render_evidence = data["final_render_evidence_gate"]
    qc_metrics = data["final_qc_metrics"]
    qc_evidence = data["final_qc_evidence_gate"]
    ab_manifest = data["final_ab_preview_manifest"]
    ab_evidence = data["ab_preview_evidence_gate"]
    approval = data["final_human_approval"]
    approval_evidence = data["final_approval_evidence_gate"]
    package_manifest = data["deliverable_package_manifest"]
    package_evidence = data["deliverable_package_evidence_gate"]
    project_state = data["project_state_manifest"]
    rollback_evidence = data["rollback_evidence_gate"]

    ready_checks = [
        ("final_export_state", export_state.get("safe_to_export", False), "final_export_state_not_safe"),
        ("final_render_evidence", render_evidence.get("ready_for_approval_readiness", False), "final_render_evidence_not_ready"),
        ("final_qc_evidence", qc_evidence.get("ready_for_approval_readiness", False), "final_qc_evidence_not_ready"),
        ("ab_preview_evidence", ab_evidence.get("ready_for_human_ab_review", False), "ab_preview_evidence_not_ready"),
        ("final_approval_evidence", approval_evidence.get("ready_for_delivery_request", False), "final_approval_evidence_not_ready"),
        ("deliverable_package_evidence", package_evidence.get("ready_for_delivery_package", False), "deliverable_package_evidence_not_ready"),
        ("rollback_evidence", rollback_evidence.get("ready_for_delivery_readiness", False), "rollback_evidence_not_ready"),
    ]
    for _, ready, code in ready_checks:
        if not ready:
            blockers.append(code)

    selected_source = _path_text(export_state.get("selected_export_source", ""))
    selected_stage = str(export_state.get("selected_export_stage", "") or "")
    approved_source = _path_text(approval.get("approved_source", ""))
    approved_stage = str(approval.get("approved_stage", "") or "")
    if selected_source and not _path_exists_nonzero(selected_source, output_dir):
        blockers.append("selected_export_source_missing_or_empty")
    if approval.get("approved", False):
        if selected_source and approved_source != selected_source:
            blockers.append("final_approval_source_mismatch_final_export_state")
        if selected_stage and approved_stage != selected_stage:
            blockers.append("final_approval_stage_mismatch_final_export_state")

    accepted_sources = [str(item) for item in project_state.get("accepted_sources", []) or []]
    if selected_source and selected_source not in accepted_sources:
        blockers.append("selected_export_source_not_recorded_in_project_state")
    if project_state.get("original_tracks_protected") is not True:
        blockers.append("project_state_original_tracks_not_protected")
    if project_state.get("master_unchanged") is not True:
        blockers.append("project_state_master_mutated")

    render_primary = _primary_render_path(render_manifest)
    render_evidence_primary = _path_text(render_evidence.get("primary_wav_path", ""))
    qc_metrics_audio = _path_text(qc_metrics.get("final_audio_path", ""))
    qc_evidence_audio = _path_text(qc_evidence.get("final_audio_path", ""))
    ab_final = _path_text(ab_manifest.get("source_final", ""))
    approval_final = _path_text(approval.get("reviewed_final_audio_path", ""))
    approval_evidence_final = _path_text(approval_evidence.get("supporting_gate_summary", {}).get("final_audio_path", ""))

    final_audio = qc_evidence_audio or qc_metrics_audio or render_evidence_primary or render_primary
    if not render_primary:
        blockers.append("final_render_manifest_primary_wav_missing")
    if not render_evidence_primary:
        blockers.append("final_render_evidence_primary_wav_missing")
    if not final_audio:
        blockers.append("final_audio_path_missing")
    elif not _path_exists_nonzero(final_audio, output_dir):
        blockers.append("final_audio_file_missing_or_empty")

    for code, other in (
        ("final_render_manifest_mismatch_render_evidence_primary_wav", render_primary),
        ("final_qc_metrics_audio_mismatch_final_qc_evidence", qc_metrics_audio),
        ("final_qc_audio_mismatch_render_evidence_primary_wav", render_evidence_primary),
        ("ab_preview_final_source_mismatch_final_audio", ab_final),
        ("final_approval_reviewed_audio_mismatch_final_audio", approval_final),
        ("final_approval_evidence_audio_mismatch_final_audio", approval_evidence_final),
    ):
        _add_mismatch(blockers, code=code, left=final_audio, right=other, output_dir=output_dir)

    ab_output = _path_text(ab_manifest.get("output_path", ""))
    ab_evidence_output = _path_text(ab_evidence.get("manifest_summary", {}).get("output_path", ""))
    approval_preview = _path_text(approval.get("reviewed_ab_preview_path", ""))
    approval_evidence_preview = _path_text(approval_evidence.get("supporting_gate_summary", {}).get("ab_preview_output_path", ""))
    preview_path = ab_evidence_output or ab_output
    if not preview_path:
        blockers.append("ab_preview_output_path_missing")
    elif not _path_exists_nonzero(preview_path, output_dir):
        blockers.append("ab_preview_output_file_missing_or_empty")
    for code, other in (
        ("ab_preview_manifest_output_mismatch_ab_evidence", ab_output),
        ("final_approval_reviewed_preview_mismatch_ab_preview", approval_preview),
        ("final_approval_evidence_preview_mismatch_ab_preview", approval_evidence_preview),
    ):
        _add_mismatch(blockers, code=code, left=preview_path, right=other, output_dir=output_dir)

    package_zip = _path_text(package_manifest.get("zip_path", ""))
    package_evidence_zip = _path_text(package_evidence.get("package_summary", {}).get("zip_path", ""))
    _add_mismatch(blockers, code="package_manifest_zip_mismatch_package_evidence", left=package_zip, right=package_evidence_zip, output_dir=output_dir)
    package_size = int(package_manifest.get("package_size_bytes", 0) or 0)
    evidence_size = int(package_evidence.get("package_summary", {}).get("actual_zip_size_bytes", 0) or 0)
    if package_size and evidence_size and package_size != evidence_size:
        blockers.append("package_manifest_size_mismatch_package_evidence")

    included_names = _included_names(package_manifest)
    if final_audio and Path(final_audio).name.lower() not in included_names:
        blockers.append("final_audio_filename_not_listed_in_package_manifest")
    if preview_path and Path(preview_path).name.lower() not in included_names:
        blockers.append("ab_preview_filename_not_listed_in_package_manifest")

    blockers = sorted(set(blockers))
    warnings = sorted(set(warnings))
    ready = not blockers
    template_path = output_dir / TEMPLATE_REL_PATH
    write_json(template_path, _template())
    gate = {
        "schema": FINAL_DELIVERY_CONSISTENCY_SCHEMA,
        "project_name": project_name,
        "created_at": now_utc(),
        "output_dir": str(output_dir),
        "ready_for_delivery_consistency": ready,
        "ready_for_professional_readiness": ready,
        "evidence_files": evidence,
        "source_consistency": {
            "selected_export_source": selected_source,
            "selected_export_stage": selected_stage,
            "approved_source": approved_source,
            "approved_stage": approved_stage,
            "selected_source_exists": _path_exists_nonzero(selected_source, output_dir) if selected_source else False,
            "selected_source_in_project_state": bool(selected_source and selected_source in accepted_sources),
        },
        "final_audio_consistency": {
            "final_audio_path": final_audio,
            "render_manifest_primary_wav": render_primary,
            "render_evidence_primary_wav": render_evidence_primary,
            "qc_metrics_final_audio": qc_metrics_audio,
            "qc_evidence_final_audio": qc_evidence_audio,
            "ab_preview_source_final": ab_final,
            "approval_reviewed_final_audio": approval_final,
            "approval_evidence_final_audio": approval_evidence_final,
            "final_audio_exists": _path_exists_nonzero(final_audio, output_dir) if final_audio else False,
        },
        "ab_preview_consistency": {
            "preview_output_path": preview_path,
            "ab_manifest_output_path": ab_output,
            "ab_evidence_output_path": ab_evidence_output,
            "approval_reviewed_ab_preview_path": approval_preview,
            "approval_evidence_ab_preview_path": approval_evidence_preview,
            "preview_output_exists": _path_exists_nonzero(preview_path, output_dir) if preview_path else False,
        },
        "package_consistency": {
            "package_manifest_zip_path": package_zip,
            "package_evidence_zip_path": package_evidence_zip,
            "package_manifest_size_bytes": package_size,
            "package_evidence_actual_zip_size_bytes": evidence_size,
            "files_included_count": len(_included_paths(package_manifest)),
            "final_audio_filename_included": bool(final_audio and Path(final_audio).name.lower() in included_names),
            "ab_preview_filename_included": bool(preview_path and Path(preview_path).name.lower() in included_names),
        },
        "supporting_gate_readiness": {name: bool(ready) for name, ready, _ in ready_checks},
        "blockers": blockers,
        "warnings": warnings,
        "template_path": str(template_path),
        "limits": [
            "This gate validates final delivery cross-report consistency only; it does not approve audio.",
            "A passing consistency gate does not replace render, QC, A/B, approval, package, rollback, or professional readiness gates.",
            "Human listening at matched loudness remains required before final delivery.",
        ],
    }
    target = output_path or output_dir / GATE_REL_PATH
    write_json(target, gate)
    write_final_delivery_consistency_report(gate, output_dir)
    write_final_delivery_consistency_request(gate, output_dir)
    return gate


def write_final_delivery_consistency_report(gate: dict[str, Any], output_dir: Path) -> Path:
    audio = gate.get("final_audio_consistency", {})
    preview = gate.get("ab_preview_consistency", {})
    package = gate.get("package_consistency", {})
    lines = [
        "# Final Delivery Consistency Gate",
        "",
        f"- Project: `{gate.get('project_name')}`",
        f"- Created UTC: `{gate.get('created_at')}`",
        f"- Ready for delivery consistency: `{gate.get('ready_for_delivery_consistency')}`",
        f"- Ready for professional readiness: `{gate.get('ready_for_professional_readiness')}`",
        f"- Final audio: `{audio.get('final_audio_path')}`",
        f"- Final audio exists: `{audio.get('final_audio_exists')}`",
        f"- A/B preview: `{preview.get('preview_output_path')}`",
        f"- A/B preview exists: `{preview.get('preview_output_exists')}`",
        f"- Package ZIP: `{package.get('package_manifest_zip_path')}`",
        f"- Final audio listed in package: `{package.get('final_audio_filename_included')}`",
        f"- A/B preview listed in package: `{package.get('ab_preview_filename_included')}`",
        "",
        "This gate does not approve audio. It checks that final delivery reports point to the same evidence.",
        "",
        "## Blockers",
        "",
    ]
    lines.extend([f"- `{item}`" for item in gate.get("blockers", [])] or ["- none"])
    lines.extend(["", "## Warnings", ""])
    lines.extend([f"- `{item}`" for item in gate.get("warnings", [])] or ["- none"])
    lines.extend(["", "## Supporting Gate Readiness", ""])
    for name, ready in sorted(gate.get("supporting_gate_readiness", {}).items()):
        lines.append(f"- `{name}`: `{ready}`")
    path = Path(output_dir) / GATE_REPORT_REL_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return path


def write_final_delivery_consistency_request(gate: dict[str, Any], output_dir: Path) -> Path:
    lines = [
        "# Final Delivery Consistency Request",
        "",
        "Resolve these cross-report consistency blockers before professional delivery readiness.",
        "",
        f"- Ready for delivery consistency: `{gate.get('ready_for_delivery_consistency')}`",
        f"- Template: `{gate.get('template_path')}`",
        "",
        "## Blockers",
        "",
    ]
    lines.extend([f"- `{item}`" for item in gate.get("blockers", [])] or ["- none"])
    lines.extend(
        [
            "",
            "## Limits",
            "",
            "- This request does not approve audio.",
            "- Keep measured QC, matched-loudness A/B review, final approval, rollback, and package evidence as separate gates.",
        ]
    )
    path = Path(output_dir) / REQUEST_REL_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return path

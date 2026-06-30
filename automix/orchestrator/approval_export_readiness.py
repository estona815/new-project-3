from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from automix.feedback.revision_memory import summarize_feedback_memory
from automix.plugins.plugin_adapter_schema import now_utc, write_json


APPROVAL_EXPORT_READINESS_SCHEMA = "automix-approval-export-readiness-v1"

AUDIT_REL_PATH = Path("eval_reports/approval_export_readiness.json")
AUDIT_REPORT_REL_PATH = Path("eval_reports/approval_export_readiness.md")
APPROVAL_REQUEST_REL_PATH = Path("review/final_approval_request.md")

EVIDENCE_FILES = {
    "final_export_state": "export/final_export_state.json",
    "final_ab_preview_manifest": "eval_reports/final_ab_preview_manifest.json",
    "ab_preview_evidence_gate": "eval_reports/ab_preview_evidence_gate.json",
    "final_render_manifest": "export/final_render_manifest.json",
    "final_render_evidence_gate": "eval_reports/final_render_evidence_gate.json",
    "final_qc_metrics": "eval_reports/final_qc_metrics.json",
    "final_qc_evidence_gate": "eval_reports/final_qc_evidence_gate.json",
    "final_human_approval": "review/final_human_approval.json",
    "final_approval_evidence_gate": "eval_reports/final_approval_evidence_gate.json",
    "project_state_manifest": "export/project_state_manifest.json",
    "rollback_evidence_gate": "eval_reports/rollback_evidence_gate.json",
    "source_acceptance_gate": "eval_reports/source_acceptance_gate.json",
    "source_handoff_readiness": "eval_reports/source_handoff_readiness.json",
    "artifact_evidence_gate": "eval_reports/artifact_evidence_gate.json",
    "artifact_signal_audit": "eval_reports/artifact_signal_audit.json",
    "plugin_semantic_validation_gate": "eval_reports/plugin_semantic_validation_gate.json",
    "plugin_validation_preflight": "eval_reports/plugin_validation_preflight.json",
}


def _load_json(path: Path) -> tuple[dict[str, Any], str | None]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        return {}, f"read_error:{path}:{exc}"
    except json.JSONDecodeError as exc:
        return {}, f"json_decode_error:{path}:{exc}"
    if not isinstance(data, dict):
        return {}, f"json_type_error:{path}:expected_object"
    return data, None


def _evidence_status(output_dir: Path) -> dict[str, dict[str, Any]]:
    status: dict[str, dict[str, Any]] = {}
    for name, rel in EVIDENCE_FILES.items():
        path = output_dir / rel
        data: dict[str, Any] = {}
        error: str | None = None
        json_valid: bool | None = None
        if path.exists():
            data, error = _load_json(path)
            json_valid = error is None
        status[name] = {
            "relative_path": rel,
            "path": str(path),
            "exists": path.exists(),
            "json_valid": json_valid,
            "json_error": error,
            "size_bytes": path.stat().st_size if path.exists() and path.is_file() else 0,
            "data": data,
        }
    return status


def _add_unique(items: list[str], code: str) -> None:
    if code and code not in items:
        items.append(code)


def _path_nonzero(path_value: str) -> bool:
    if not path_value:
        return False
    path = Path(path_value)
    return path.exists() and path.is_file() and path.stat().st_size > 0


def _source_summary(final_export_state: dict[str, Any], project_state: dict[str, Any], source_handoff: dict[str, Any]) -> dict[str, Any]:
    selected = str(final_export_state.get("selected_export_source", ""))
    blocked_reasons = [str(item) for item in final_export_state.get("blocked_reasons", []) or []]
    accepted_sources = [str(item) for item in project_state.get("accepted_sources", []) or []]
    handoff_summary = source_handoff.get("summary", {}) if isinstance(source_handoff.get("summary", {}), dict) else {}
    source_exists = _path_nonzero(selected) if selected else False
    accepted_export_source_present = bool(selected and source_exists and final_export_state.get("safe_to_export", False))
    if handoff_summary.get("accepted_export_source_present") is False:
        accepted_export_source_present = False
    return {
        "selected_export_source": selected,
        "selected_export_stage": final_export_state.get("selected_export_stage", ""),
        "source_file_exists": source_exists,
        "final_export_safe_to_export": bool(final_export_state.get("safe_to_export", False)),
        "final_export_blocked_reasons": blocked_reasons,
        "project_state_accepted_sources": accepted_sources,
        "accepted_source_recorded_in_project_state": bool(selected and selected in accepted_sources) if selected else False,
        "source_handoff_accepted_export_source_present": bool(handoff_summary.get("accepted_export_source_present", False)),
        "accepted_export_source_present": accepted_export_source_present,
    }


def _render_summary(render_manifest: dict[str, Any]) -> dict[str, Any]:
    renders = render_manifest.get("renders", []) if isinstance(render_manifest.get("renders", []), list) else []
    primary: list[dict[str, Any]] = []
    missing_paths: list[str] = []
    for item in renders:
        if not isinstance(item, dict):
            continue
        if item.get("format") != "wav" or not item.get("created"):
            continue
        if int(item.get("size_bytes", 0) or 0) <= 0:
            continue
        primary.append(item)
        path = str(item.get("path", ""))
        if path and not _path_nonzero(path):
            missing_paths.append(path)
    warnings = [str(item) for item in render_manifest.get("warnings", []) or []]
    diagnostic_only = any("diagnostic/report-only" in item for item in warnings)
    return {
        "render_count": len(renders),
        "primary_wav_count": len(primary),
        "failures": render_manifest.get("failures", []) or [],
        "warnings": warnings,
        "primary_wav_paths_missing_or_empty": missing_paths,
        "diagnostic_or_report_only": diagnostic_only,
        "ready": bool(primary) and not render_manifest.get("failures") and not missing_paths and not diagnostic_only,
    }


def _ab_preview_summary(ab_manifest: dict[str, Any]) -> dict[str, Any]:
    output_path = str(ab_manifest.get("output_path", ""))
    created = bool(ab_manifest.get("created", False))
    loudness_matched = bool(ab_manifest.get("loudness_matched", False))
    file_exists = _path_nonzero(output_path)
    return {
        "created": created,
        "loudness_matched": loudness_matched,
        "output_path": output_path,
        "output_file_exists": file_exists,
        "warnings": ab_manifest.get("warnings", []) or [],
        "ready": created and loudness_matched and file_exists,
    }


def _final_qc_summary(final_qc: dict[str, Any]) -> dict[str, Any]:
    failures = [str(item) for item in final_qc.get("failures", []) or []]
    return {
        "qc_passed": bool(final_qc.get("qc_passed", False)),
        "final_audio_path": final_qc.get("final_audio_path", ""),
        "failures": failures,
        "warnings": final_qc.get("warnings", []) or [],
        "ready": bool(final_qc.get("qc_passed", False)) and not failures,
    }


def _approval_summary(approval: dict[str, Any], source: dict[str, Any]) -> dict[str, Any]:
    selected = source.get("selected_export_source", "")
    approved_source = str(approval.get("approved_source", ""))
    approved_stage = str(approval.get("approved_stage", ""))
    return {
        "approved": bool(approval.get("approved", False)),
        "approved_by": approval.get("approved_by", ""),
        "approved_stage": approved_stage,
        "approved_source": approved_source,
        "approval_time": approval.get("approval_time", ""),
        "warnings_acknowledged": approval.get("warnings_acknowledged", []) or [],
        "unsafe_override": bool(approval.get("unsafe_override", False)),
        "source_matches_selected": bool(not approved_source or approved_source == selected),
        "stage_matches_selected": bool(not approved_stage or approved_stage == source.get("selected_export_stage", "")),
    }


def _project_state_summary(project_state: dict[str, Any], source: dict[str, Any]) -> dict[str, Any]:
    selected = str(source.get("selected_export_source", ""))
    accepted_sources = [str(item) for item in project_state.get("accepted_sources", []) or []]
    return {
        "original_tracks_protected": bool(project_state.get("original_tracks_protected", False)),
        "master_unchanged": bool(project_state.get("master_unchanged", False)),
        "accepted_sources": accepted_sources,
        "selected_source_in_accepted_sources": bool(selected and selected in accepted_sources) if selected else False,
    }


def _collect_supporting_blockers(
    *,
    ab_preview_evidence: dict[str, Any],
    final_render_evidence: dict[str, Any],
    final_qc_evidence: dict[str, Any],
    final_approval_evidence: dict[str, Any],
    rollback_evidence: dict[str, Any],
    source_handoff: dict[str, Any],
    artifact_signal: dict[str, Any],
    plugin_preflight: dict[str, Any],
) -> list[str]:
    blockers: list[str] = []
    for blocker in ab_preview_evidence.get("blockers", []) or []:
        _add_unique(blockers, f"ab_preview_evidence:{blocker}")
    for blocker in final_render_evidence.get("blockers", []) or []:
        _add_unique(blockers, f"final_render_evidence:{blocker}")
    for blocker in final_qc_evidence.get("blockers", []) or []:
        _add_unique(blockers, f"final_qc_evidence:{blocker}")
    for blocker in final_approval_evidence.get("blockers", []) or []:
        if str(blocker) == "final_human_approval_missing":
            continue
        _add_unique(blockers, f"final_approval_evidence:{blocker}")
    for blocker in rollback_evidence.get("blockers", []) or []:
        _add_unique(blockers, f"rollback_evidence:{blocker}")
    for blocker in source_handoff.get("blockers", []) or []:
        code = str(blocker)
        if code == "accepted_export_source_missing":
            _add_unique(blockers, "accepted_export_source_missing")
        else:
            _add_unique(blockers, f"source_handoff:{code}")
    for blocker in artifact_signal.get("blockers", []) or []:
        _add_unique(blockers, f"artifact_signal:{blocker}")
    for blocker in plugin_preflight.get("blockers", []) or []:
        _add_unique(blockers, f"plugin_validation_preflight:{blocker}")
    return blockers


def build_approval_export_readiness(
    *,
    project_name: str,
    output_dir: Path,
    output_path: Path | None = None,
) -> dict[str, Any]:
    output_dir = Path(output_dir)
    evidence = _evidence_status(output_dir)

    final_export_state = evidence["final_export_state"]["data"]
    ab_manifest = evidence["final_ab_preview_manifest"]["data"]
    ab_preview_evidence = evidence["ab_preview_evidence_gate"]["data"]
    render_manifest = evidence["final_render_manifest"]["data"]
    final_render_evidence = evidence["final_render_evidence_gate"]["data"]
    final_qc = evidence["final_qc_metrics"]["data"]
    final_qc_evidence = evidence["final_qc_evidence_gate"]["data"]
    approval = evidence["final_human_approval"]["data"]
    final_approval_evidence = evidence["final_approval_evidence_gate"]["data"]
    project_state = evidence["project_state_manifest"]["data"]
    rollback_evidence = evidence["rollback_evidence_gate"]["data"]
    source_acceptance = evidence["source_acceptance_gate"]["data"]
    source_handoff = evidence["source_handoff_readiness"]["data"]
    artifact_evidence = evidence["artifact_evidence_gate"]["data"]
    artifact_signal = evidence["artifact_signal_audit"]["data"]
    plugin_semantic_validation = evidence["plugin_semantic_validation_gate"]["data"]
    plugin_preflight = evidence["plugin_validation_preflight"]["data"]

    blockers: list[str] = []
    warnings: list[str] = []
    missing_required = [
        key
        for key in (
            "final_export_state",
            "final_ab_preview_manifest",
            "ab_preview_evidence_gate",
            "final_render_manifest",
            "final_render_evidence_gate",
            "final_qc_metrics",
            "final_qc_evidence_gate",
            "final_human_approval",
            "project_state_manifest",
            "rollback_evidence_gate",
        )
        if not evidence[key]["exists"] or evidence[key]["json_valid"] is False
    ]
    for key in missing_required:
        _add_unique(blockers, f"{key}_missing_or_invalid")

    source = _source_summary(final_export_state, project_state, source_handoff)
    render = _render_summary(render_manifest)
    ab_preview = _ab_preview_summary(ab_manifest)
    final_qc_summary = _final_qc_summary(final_qc)
    approval_summary = _approval_summary(approval, source)
    project_state_summary = _project_state_summary(project_state, source)
    feedback_summary = summarize_feedback_memory(output_dir)

    no_source_reasons = {"no_accepted_export_source", "accepted_export_source_missing"}
    final_reasons = set(source["final_export_blocked_reasons"])
    if not source["accepted_export_source_present"] or final_reasons.intersection(no_source_reasons):
        _add_unique(blockers, "accepted_export_source_missing")
    elif source["selected_export_source"] and not source["source_file_exists"]:
        _add_unique(blockers, "accepted_export_source_file_missing")
    unsafe_reasons = sorted(final_reasons.difference(no_source_reasons))
    if unsafe_reasons and not source["final_export_safe_to_export"]:
        _add_unique(blockers, "final_export_state_not_safe")
    if source["selected_export_source"] and not project_state_summary["selected_source_in_accepted_sources"]:
        _add_unique(blockers, "project_state_selected_source_not_accepted")

    if not render["ready"]:
        _add_unique(blockers, "final_render_missing_or_diagnostic_only")
    if not final_render_evidence.get("ready_for_approval_readiness", False):
        _add_unique(blockers, "final_render_evidence_not_ready")
    if not final_qc_summary["ready"]:
        _add_unique(blockers, "final_qc_missing_or_failed")
    if not final_qc_evidence.get("ready_for_approval_readiness", False):
        _add_unique(blockers, "final_qc_evidence_not_ready")
    if not rollback_evidence.get("ready_for_delivery_readiness", False):
        _add_unique(blockers, "rollback_evidence_not_ready")
    if not ab_preview["ready"]:
        _add_unique(blockers, "ab_preview_missing_or_not_loudness_matched")
    if not ab_preview_evidence.get("ready_for_human_ab_review", False):
        _add_unique(blockers, "ab_preview_evidence_not_ready")
    if not approval_summary["approved"]:
        _add_unique(blockers, "final_human_approval_missing")
    elif not evidence["final_approval_evidence_gate"]["exists"] or evidence["final_approval_evidence_gate"]["json_valid"] is False:
        _add_unique(blockers, "final_approval_evidence_gate_missing_or_invalid")
    elif not final_approval_evidence.get("ready_for_delivery_request", False):
        _add_unique(blockers, "final_approval_evidence_not_ready")
    if approval_summary["approved"] and not approval_summary["source_matches_selected"]:
        _add_unique(blockers, "final_human_approval_source_mismatch")
    if approval_summary["approved"] and not approval_summary["stage_matches_selected"]:
        _add_unique(blockers, "final_human_approval_stage_mismatch")
    if not project_state_summary["original_tracks_protected"]:
        _add_unique(blockers, "project_state_original_tracks_not_protected")
    if not project_state_summary["master_unchanged"]:
        _add_unique(blockers, "project_state_master_mutated_or_unproven")
    if int(feedback_summary.get("pending_unresolved_count", 0) or 0) > 0:
        _add_unique(blockers, "user_feedback_unresolved_for_final_approval")

    blockers.extend(
        _collect_supporting_blockers(
            ab_preview_evidence=ab_preview_evidence,
            final_render_evidence=final_render_evidence,
            final_qc_evidence=final_qc_evidence,
            final_approval_evidence=final_approval_evidence if approval_summary["approved"] else {},
            rollback_evidence=rollback_evidence,
            source_handoff=source_handoff,
            artifact_signal=artifact_signal,
            plugin_preflight=plugin_preflight,
        )
    )
    for blocker in source_acceptance.get("blockers", []) or []:
        _add_unique(blockers, f"source_acceptance:{blocker}")
    for blocker in plugin_semantic_validation.get("blockers", []) or []:
        _add_unique(blockers, f"plugin_semantic_validation:{blocker}")
    for blocker in artifact_evidence.get("blockers", []) or []:
        _add_unique(blockers, f"artifact_evidence:{blocker}")

    for key in (
        "ab_preview_evidence_gate",
        "final_render_evidence_gate",
        "final_qc_evidence_gate",
        "final_approval_evidence_gate",
        "rollback_evidence_gate",
        "source_acceptance_gate",
        "source_handoff_readiness",
        "artifact_evidence_gate",
        "artifact_signal_audit",
        "plugin_semantic_validation_gate",
        "plugin_validation_preflight",
    ):
        if not evidence[key]["exists"]:
            _add_unique(warnings, f"{key}_not_available")
        elif evidence[key]["json_valid"] is False:
            _add_unique(warnings, f"{key}_invalid_json")

    blockers = sorted(set(blockers))
    warnings = sorted(set(warnings))
    approval_only = blockers == ["final_human_approval_missing"]
    ready = not blockers
    audit = {
        "schema": APPROVAL_EXPORT_READINESS_SCHEMA,
        "project_name": project_name,
        "created_at": now_utc(),
        "output_dir": str(output_dir),
        "readiness_status": "ready_for_delivery_request" if ready else ("ready_for_human_approval_request" if approval_only else "blocked"),
        "ready_for_delivery_request": ready,
        "ready_for_human_approval_request": approval_only,
        "blockers": blockers,
        "warnings": warnings,
        "evidence_files": {name: {k: v for k, v in item.items() if k != "data"} for name, item in evidence.items()},
        "source_summary": source,
        "final_render_summary": render,
        "ab_preview_summary": ab_preview,
        "final_qc_summary": final_qc_summary,
        "approval_summary": approval_summary,
        "project_state_summary": project_state_summary,
        "feedback_revision_loop": feedback_summary,
        "supporting_gate_summary": {
            "source_acceptance_ready": bool(source_acceptance.get("accepted_export_source_ready", False)),
            "ab_preview_evidence_ready": bool(ab_preview_evidence.get("ready_for_human_ab_review", False)),
            "ab_preview_evidence_blockers": ab_preview_evidence.get("blockers", []) or [],
            "final_render_evidence_ready": bool(final_render_evidence.get("ready_for_approval_readiness", False)),
            "final_render_evidence_blockers": final_render_evidence.get("blockers", []) or [],
            "final_qc_evidence_ready": bool(final_qc_evidence.get("ready_for_approval_readiness", False)),
            "final_qc_evidence_blockers": final_qc_evidence.get("blockers", []) or [],
            "final_approval_evidence_ready": bool(final_approval_evidence.get("ready_for_delivery_request", False)),
            "final_approval_evidence_blockers": final_approval_evidence.get("blockers", []) or [],
            "rollback_evidence_ready": bool(rollback_evidence.get("ready_for_delivery_readiness", False)),
            "rollback_evidence_blockers": rollback_evidence.get("blockers", []) or [],
            "source_acceptance_blockers": source_acceptance.get("blockers", []) or [],
            "source_handoff_blockers": source_handoff.get("blockers", []) or [],
            "artifact_evidence_ready": bool(artifact_evidence.get("ready_for_artifact_review", False)),
            "artifact_evidence_blockers": artifact_evidence.get("blockers", []) or [],
            "artifact_signal_blockers": artifact_signal.get("blockers", []) or [],
            "plugin_semantic_validation_ready": bool(plugin_semantic_validation.get("semantic_validation_ready", False)),
            "plugin_semantic_validation_blockers": plugin_semantic_validation.get("blockers", []) or [],
            "plugin_validation_preflight_blockers": plugin_preflight.get("blockers", []) or [],
        },
        "limits": [
            "This audit does not create or infer approval.",
            "It only checks whether accepted source, A/B preview, render, project-state, feedback, and human approval evidence are present.",
            "User listening review remains required before approving a final export.",
        ],
    }
    target = output_path or output_dir / AUDIT_REL_PATH
    write_json(target, audit)
    write_approval_export_readiness_markdown(audit, output_dir)
    write_final_approval_request(audit, output_dir)
    return audit


def write_approval_export_readiness_markdown(audit: dict[str, Any], output_dir: Path) -> Path:
    lines = [
        "# Approval Export Readiness",
        "",
        f"- Project: `{audit.get('project_name')}`",
        f"- Created UTC: `{audit.get('created_at')}`",
        f"- Status: `{audit.get('readiness_status')}`",
        f"- Ready for delivery request: `{audit.get('ready_for_delivery_request')}`",
        f"- Ready for human approval request: `{audit.get('ready_for_human_approval_request')}`",
        "",
        "This report does not approve audio. It explains which final export approval gates are still missing.",
        "",
        "## Blockers",
        "",
    ]
    lines.extend([f"- `{item}`" for item in audit.get("blockers", [])] or ["- none"])
    lines.extend(["", "## Warnings", ""])
    lines.extend([f"- `{item}`" for item in audit.get("warnings", [])] or ["- none"])
    source = audit.get("source_summary", {})
    render = audit.get("final_render_summary", {})
    ab_preview = audit.get("ab_preview_summary", {})
    final_qc = audit.get("final_qc_summary", {})
    approval = audit.get("approval_summary", {})
    project_state = audit.get("project_state_summary", {})
    feedback = audit.get("feedback_revision_loop", {})
    supporting = audit.get("supporting_gate_summary", {})
    lines.extend(["", "## Gate Summary", ""])
    lines.append(f"- Accepted export source present: `{source.get('accepted_export_source_present', False)}`")
    lines.append(f"- Source acceptance ready: `{supporting.get('source_acceptance_ready', False)}`")
    lines.append(f"- Source acceptance blockers: `{supporting.get('source_acceptance_blockers', [])}`")
    lines.append(f"- Artifact evidence ready: `{supporting.get('artifact_evidence_ready', False)}`")
    lines.append(f"- Artifact evidence blockers: `{supporting.get('artifact_evidence_blockers', [])}`")
    lines.append(f"- Plugin semantic validation ready: `{supporting.get('plugin_semantic_validation_ready', False)}`")
    lines.append(f"- Plugin semantic validation blockers: `{supporting.get('plugin_semantic_validation_blockers', [])}`")
    lines.append(f"- Selected export source: `{source.get('selected_export_source', '')}`")
    lines.append(f"- Final export safe to export: `{source.get('final_export_safe_to_export', False)}`")
    lines.append(f"- Final render ready: `{render.get('ready', False)}`")
    lines.append(f"- Primary WAV count: `{render.get('primary_wav_count', 0)}`")
    lines.append(f"- Final render evidence ready: `{supporting.get('final_render_evidence_ready', False)}`")
    lines.append(f"- Final render evidence blockers: `{supporting.get('final_render_evidence_blockers', [])}`")
    lines.append(f"- Final QC passed: `{final_qc.get('qc_passed', False)}`")
    lines.append(f"- Final QC failures: `{final_qc.get('failures', [])}`")
    lines.append(f"- Final QC evidence ready: `{supporting.get('final_qc_evidence_ready', False)}`")
    lines.append(f"- Final QC evidence blockers: `{supporting.get('final_qc_evidence_blockers', [])}`")
    lines.append(f"- Final approval evidence ready: `{supporting.get('final_approval_evidence_ready', False)}`")
    lines.append(f"- Final approval evidence blockers: `{supporting.get('final_approval_evidence_blockers', [])}`")
    lines.append(f"- Rollback evidence ready: `{supporting.get('rollback_evidence_ready', False)}`")
    lines.append(f"- Rollback evidence blockers: `{supporting.get('rollback_evidence_blockers', [])}`")
    lines.append(f"- A/B preview ready: `{ab_preview.get('ready', False)}`")
    lines.append(f"- A/B preview loudness matched: `{ab_preview.get('loudness_matched', False)}`")
    lines.append(f"- A/B preview evidence ready: `{supporting.get('ab_preview_evidence_ready', False)}`")
    lines.append(f"- A/B preview evidence blockers: `{supporting.get('ab_preview_evidence_blockers', [])}`")
    lines.append(f"- Human approval recorded: `{approval.get('approved', False)}`")
    lines.append(f"- Original tracks protected: `{project_state.get('original_tracks_protected', False)}`")
    lines.append(f"- Master unchanged: `{project_state.get('master_unchanged', False)}`")
    lines.append(f"- Pending feedback items: `{feedback.get('pending_unresolved_count', 0)}`")
    lines.extend(["", "## Evidence Files", ""])
    for name, item in audit.get("evidence_files", {}).items():
        lines.append(f"- `{name}`: exists=`{item.get('exists')}`, json_valid=`{item.get('json_valid')}`")
    path = Path(output_dir) / AUDIT_REPORT_REL_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return path


def write_final_approval_request(audit: dict[str, Any], output_dir: Path) -> Path:
    source = audit.get("source_summary", {})
    ab_preview = audit.get("ab_preview_summary", {})
    lines = [
        "# Final Approval Request",
        "",
        f"- Project: `{audit.get('project_name')}`",
        f"- Status: `{audit.get('readiness_status')}`",
        f"- Selected export source: `{source.get('selected_export_source', '')}`",
        f"- A/B preview: `{ab_preview.get('output_path', '')}`",
        "",
    ]
    if audit.get("ready_for_human_approval_request"):
        lines.extend(
            [
                "The technical evidence is ready for a human approval decision, but no approval is recorded yet.",
                "",
                "Required operator check:",
                "",
                "- Listen to the original/final A/B preview at matched loudness.",
                "- Confirm the selected export source is the intended accepted source.",
                "- Confirm any warnings are acknowledged before running final export.",
            ]
        )
    else:
        lines.extend(["The approval request is not ready. Resolve these blockers first:", ""])
        lines.extend([f"- `{item}`" for item in audit.get("blockers", [])] or ["- none"])
    path = Path(output_dir) / APPROVAL_REQUEST_REL_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return path

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from automix.plugins.plugin_adapter_schema import now_utc, write_json


FINAL_APPROVAL_EVIDENCE_SCHEMA = "automix-final-approval-evidence-gate-v1"

GATE_REL_PATH = Path("eval_reports/final_approval_evidence_gate.json")
GATE_REPORT_REL_PATH = Path("eval_reports/final_approval_evidence_gate.md")
TEMPLATE_REL_PATH = Path("review/final_approval_evidence_manifest_template.json")
REQUEST_REL_PATH = Path("review/final_approval_evidence_request.md")

FINAL_APPROVAL_REL_PATH = Path("review/final_human_approval.json")
FINAL_EXPORT_STATE_REL_PATH = Path("export/final_export_state.json")
AB_PREVIEW_EVIDENCE_REL_PATH = Path("eval_reports/ab_preview_evidence_gate.json")
FINAL_RENDER_EVIDENCE_REL_PATH = Path("eval_reports/final_render_evidence_gate.json")
FINAL_QC_EVIDENCE_REL_PATH = Path("eval_reports/final_qc_evidence_gate.json")

ACCEPTED_REVIEW_DECISIONS = {"accepted", "accepted_with_limitations"}


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


def _path_key(path_text: str, output_dir: Path) -> str:
    if not path_text:
        return ""
    try:
        return str(_resolve_path(path_text, output_dir).resolve())
    except OSError:
        return str(_resolve_path(path_text, output_dir))


def _template() -> dict[str, Any]:
    return {
        "schema": "automix-final-approval-evidence-manifest-template-v1",
        "expected_reports": [
            "automix/review/final_human_approval.json",
            "automix/eval_reports/final_approval_evidence_gate.json",
            "automix/eval_reports/ab_preview_evidence_gate.json",
            "automix/eval_reports/final_qc_evidence_gate.json",
            "automix/eval_reports/final_render_evidence_gate.json",
        ],
        "required_approval_fields": [
            "approved true",
            "review_decision accepted or accepted_with_limitations",
            "loudness_matched_ab_reviewed true",
            "final_audio_accepted_at_matched_loudness true",
            "reviewed_ab_preview_path matches the A/B preview evidence output path",
            "reviewed_final_audio_path matches the final QC evidence audio path",
            "final_qc_evidence_reviewed true",
        ],
        "limits": [
            "This template does not approve audio.",
            "The operator must create the approval record after actual listening.",
            "A matching path is not a listening claim; it only makes the approval auditable.",
        ],
    }


def _supporting_gate_blockers(
    *,
    ab_preview_evidence: dict[str, Any],
    final_render_evidence: dict[str, Any],
    final_qc_evidence: dict[str, Any],
) -> list[str]:
    blockers: list[str] = []
    if not ab_preview_evidence.get("ready_for_human_ab_review", False):
        blockers.append("ab_preview_evidence_not_ready")
        blockers.extend(f"ab_preview_evidence:{item}" for item in ab_preview_evidence.get("blockers", []) or [])
    if not final_render_evidence.get("ready_for_approval_readiness", False):
        blockers.append("final_render_evidence_not_ready")
        blockers.extend(f"final_render_evidence:{item}" for item in final_render_evidence.get("blockers", []) or [])
    if not final_qc_evidence.get("ready_for_approval_readiness", False):
        blockers.append("final_qc_evidence_not_ready")
        blockers.extend(f"final_qc_evidence:{item}" for item in final_qc_evidence.get("blockers", []) or [])
    return sorted(set(blockers))


def build_final_approval_evidence_gate(
    *,
    project_name: str,
    output_dir: Path,
    approval_path: Path | None = None,
    final_export_state_path: Path | None = None,
    ab_preview_evidence_path: Path | None = None,
    final_render_evidence_path: Path | None = None,
    final_qc_evidence_path: Path | None = None,
    output_path: Path | None = None,
) -> dict[str, Any]:
    output_dir = Path(output_dir)
    approval_file = Path(approval_path) if approval_path else output_dir / FINAL_APPROVAL_REL_PATH
    export_state_file = Path(final_export_state_path) if final_export_state_path else output_dir / FINAL_EXPORT_STATE_REL_PATH
    ab_file = Path(ab_preview_evidence_path) if ab_preview_evidence_path else output_dir / AB_PREVIEW_EVIDENCE_REL_PATH
    render_file = Path(final_render_evidence_path) if final_render_evidence_path else output_dir / FINAL_RENDER_EVIDENCE_REL_PATH
    qc_file = Path(final_qc_evidence_path) if final_qc_evidence_path else output_dir / FINAL_QC_EVIDENCE_REL_PATH

    approval = _load_json(approval_file)
    export_state = _load_json(export_state_file)
    ab_preview_evidence = _load_json(ab_file)
    final_render_evidence = _load_json(render_file)
    final_qc_evidence = _load_json(qc_file)
    blockers: list[str] = []
    warnings: list[str] = []

    if not approval_file.exists() or not approval:
        blockers.append("final_human_approval_missing_or_invalid")
    elif approval.get("schema") != "automix-final-human-approval-v1":
        blockers.append("final_human_approval_schema_invalid")
    if not export_state_file.exists() or not export_state:
        blockers.append("final_export_state_missing_or_invalid")
    elif export_state.get("schema") != "automix-final-export-state-v1":
        blockers.append("final_export_state_schema_invalid")
    for path, data, schema, code in (
        (ab_file, ab_preview_evidence, "automix-ab-preview-evidence-gate-v1", "ab_preview_evidence_gate"),
        (render_file, final_render_evidence, "automix-final-render-evidence-gate-v1", "final_render_evidence_gate"),
        (qc_file, final_qc_evidence, "automix-final-qc-evidence-gate-v1", "final_qc_evidence_gate"),
    ):
        if not path.exists() or not data:
            blockers.append(f"{code}_missing_or_invalid")
        elif data.get("schema") != schema:
            blockers.append(f"{code}_schema_invalid")

    blockers.extend(
        _supporting_gate_blockers(
            ab_preview_evidence=ab_preview_evidence,
            final_render_evidence=final_render_evidence,
            final_qc_evidence=final_qc_evidence,
        )
    )

    approved = bool(approval.get("approved", False))
    review_decision = str(approval.get("review_decision", "") or "")
    if not approved:
        blockers.append("final_human_approval_missing")
    else:
        if not approval.get("approval_time"):
            blockers.append("final_human_approval_time_missing")
        if not approval.get("approved_by"):
            blockers.append("final_human_approval_reviewer_missing")
        if review_decision not in ACCEPTED_REVIEW_DECISIONS:
            blockers.append("final_human_approval_review_decision_not_accepted")
        if not approval.get("loudness_matched_ab_reviewed", False):
            blockers.append("loudness_matched_ab_review_not_recorded")
        if not approval.get("final_audio_accepted_at_matched_loudness", False):
            blockers.append("final_audio_not_accepted_at_matched_loudness")
        if not approval.get("final_qc_evidence_reviewed", False):
            blockers.append("final_qc_evidence_not_reviewed_by_human")

    selected_source = str(export_state.get("selected_export_source", "") or "")
    selected_stage = str(export_state.get("selected_export_stage", "") or "")
    approved_source = str(approval.get("approved_source", "") or "")
    approved_stage = str(approval.get("approved_stage", "") or "")
    if approved and selected_source and approved_source != selected_source:
        blockers.append("final_human_approval_source_mismatch")
    if approved and selected_stage and approved_stage != selected_stage:
        blockers.append("final_human_approval_stage_mismatch")

    warnings_to_ack = [str(item) for item in export_state.get("warnings", []) or []]
    acknowledged = set(str(item) for item in approval.get("warnings_acknowledged", []) or [])
    if approved and warnings_to_ack and "all" not in acknowledged and not set(warnings_to_ack).issubset(acknowledged):
        blockers.append("final_human_approval_warnings_not_acknowledged")

    ab_summary = ab_preview_evidence.get("manifest_summary", {}) if isinstance(ab_preview_evidence.get("manifest_summary", {}), dict) else {}
    preview_path = str(ab_summary.get("output_path", "") or "")
    reviewed_preview = str(approval.get("reviewed_ab_preview_path", "") or "")
    if approved:
        if not reviewed_preview:
            blockers.append("reviewed_ab_preview_path_missing")
        elif preview_path and _path_key(reviewed_preview, output_dir) != _path_key(preview_path, output_dir):
            blockers.append("reviewed_ab_preview_path_mismatch")

    final_audio = str(final_qc_evidence.get("final_audio_path", "") or "")
    reviewed_final = str(approval.get("reviewed_final_audio_path", "") or "")
    if approved:
        if not reviewed_final:
            blockers.append("reviewed_final_audio_path_missing")
        elif final_audio and _path_key(reviewed_final, output_dir) != _path_key(final_audio, output_dir):
            blockers.append("reviewed_final_audio_path_mismatch")

    blockers = sorted(set(blockers))
    warnings = sorted(set(warnings))
    approval_pending_only = blockers == ["final_human_approval_missing"]
    ready = not blockers
    template_path = output_dir / TEMPLATE_REL_PATH
    write_json(template_path, _template())
    gate = {
        "schema": FINAL_APPROVAL_EVIDENCE_SCHEMA,
        "project_name": project_name,
        "created_at": now_utc(),
        "output_dir": str(output_dir),
        "approval_path": str(approval_file),
        "final_export_state_path": str(export_state_file),
        "ab_preview_evidence_path": str(ab_file),
        "final_render_evidence_path": str(render_file),
        "final_qc_evidence_path": str(qc_file),
        "ready_for_delivery_request": ready,
        "approval_pending_only": approval_pending_only,
        "approved": approved,
        "review_decision": review_decision,
        "approval_summary": {
            "approved_by": approval.get("approved_by", ""),
            "approval_time": approval.get("approval_time", ""),
            "approved_stage": approved_stage,
            "approved_source": approved_source,
            "loudness_matched_ab_reviewed": bool(approval.get("loudness_matched_ab_reviewed", False)),
            "final_audio_accepted_at_matched_loudness": bool(approval.get("final_audio_accepted_at_matched_loudness", False)),
            "reviewed_ab_preview_path": reviewed_preview,
            "reviewed_final_audio_path": reviewed_final,
            "final_qc_evidence_reviewed": bool(approval.get("final_qc_evidence_reviewed", False)),
            "warnings_acknowledged": approval.get("warnings_acknowledged", []) or [],
        },
        "supporting_gate_summary": {
            "ab_preview_evidence_ready": bool(ab_preview_evidence.get("ready_for_human_ab_review", False)),
            "final_render_evidence_ready": bool(final_render_evidence.get("ready_for_approval_readiness", False)),
            "final_qc_evidence_ready": bool(final_qc_evidence.get("ready_for_approval_readiness", False)),
            "ab_preview_output_path": preview_path,
            "final_audio_path": final_audio,
        },
        "blockers": blockers,
        "warnings": warnings,
        "template_path": str(template_path),
        "limits": [
            "This gate validates final approval evidence only; it does not approve audio.",
            "Human listening must be recorded by the operator after matched-loudness A/B review.",
            "Final approval evidence does not replace source, render, QC, A/B, rollback, or plugin gates.",
        ],
    }
    target = output_path or output_dir / GATE_REL_PATH
    write_json(target, gate)
    write_final_approval_evidence_report(gate, output_dir)
    write_final_approval_evidence_request(gate, output_dir)
    return gate


def write_final_approval_evidence_report(gate: dict[str, Any], output_dir: Path) -> Path:
    approval = gate.get("approval_summary", {})
    supporting = gate.get("supporting_gate_summary", {})
    lines = [
        "# Final Approval Evidence Gate",
        "",
        f"- Project: `{gate.get('project_name')}`",
        f"- Created UTC: `{gate.get('created_at')}`",
        f"- Ready for delivery request: `{gate.get('ready_for_delivery_request')}`",
        f"- Approval pending only: `{gate.get('approval_pending_only')}`",
        f"- Approved: `{gate.get('approved')}`",
        f"- Review decision: `{gate.get('review_decision')}`",
        f"- Loudness-matched A/B reviewed: `{approval.get('loudness_matched_ab_reviewed')}`",
        f"- Final accepted at matched loudness: `{approval.get('final_audio_accepted_at_matched_loudness')}`",
        f"- Final QC evidence reviewed: `{approval.get('final_qc_evidence_reviewed')}`",
        f"- A/B evidence ready: `{supporting.get('ab_preview_evidence_ready')}`",
        f"- Final QC evidence ready: `{supporting.get('final_qc_evidence_ready')}`",
        "",
        "This gate does not approve audio. It checks that the human approval record is auditable.",
        "",
        "## Blockers",
        "",
    ]
    lines.extend([f"- `{item}`" for item in gate.get("blockers", [])] or ["- none"])
    lines.extend(["", "## Warnings", ""])
    lines.extend([f"- `{item}`" for item in gate.get("warnings", [])] or ["- none"])
    path = Path(output_dir) / GATE_REPORT_REL_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return path


def write_final_approval_evidence_request(gate: dict[str, Any], output_dir: Path) -> Path:
    lines = [
        "# Final Approval Evidence Request",
        "",
        f"- Project: `{gate.get('project_name')}`",
        f"- Template: `{gate.get('template_path')}`",
        "",
    ]
    if gate.get("ready_for_delivery_request"):
        lines.extend(
            [
                "Final approval evidence is ready for delivery-readiness checks.",
                "",
                "Keep this approval record with the final QC, A/B preview, render, and rollback evidence.",
            ]
        )
    elif gate.get("approval_pending_only"):
        lines.extend(
            [
                "Technical evidence is ready for a human approval decision, but no approval is recorded yet.",
                "",
                "Required operator record:",
                "",
                "- Listen to the loudness-matched A/B preview.",
                "- Confirm the final audio is accepted at matched loudness.",
                "- Record the reviewed A/B preview path and final audio path in final_human_approval.json.",
            ]
        )
    else:
        lines.extend(["Final approval evidence is not ready. Resolve these blockers first:", ""])
        lines.extend([f"- `{item}`" for item in gate.get("blockers", [])] or ["- none"])
    path = Path(output_dir) / REQUEST_REL_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return path

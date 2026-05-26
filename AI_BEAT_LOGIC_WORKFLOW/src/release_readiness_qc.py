from __future__ import annotations

from pathlib import Path
from typing import Any

from commercial_release_score import build_commercial_release_score


FAILED_TECHNICAL_QC = "FAILED_TECHNICAL_QC"
NEEDS_RIGHTS_CLEARANCE = "NEEDS_RIGHTS_CLEARANCE"
NEEDS_MANUAL_MIX = "NEEDS_MANUAL_MIX"
DRAFT_RELEASE_PACKAGE = "DRAFT_RELEASE_PACKAGE"
RELEASE_PACKAGE_READY = "RELEASE_PACKAGE_READY"


def _exists(path: str | Path | None) -> bool:
    return bool(path) and Path(path).exists() and Path(path).stat().st_size > 0


def _metadata_complete(metadata_payload: dict[str, Any] | None) -> bool:
    return bool((metadata_payload or {}).get("complete"))


def _rights_ready(rights_payload: dict[str, Any] | None) -> bool:
    return bool((rights_payload or {}).get("release_ready"))


def determine_release_readiness_status(
    *,
    final_audio: dict[str, Any],
    score: dict[str, Any],
    metadata_payload: dict[str, Any] | None,
    rights_payload: dict[str, Any] | None,
    required_reports_exist: bool,
) -> str:
    if not bool(final_audio.get("verified") or final_audio.get("ok") or final_audio.get("passed")):
        return FAILED_TECHNICAL_QC
    if score.get("high_safety_issues") or not _rights_ready(rights_payload):
        return NEEDS_RIGHTS_CLEARANCE
    if not _metadata_complete(metadata_payload):
        return DRAFT_RELEASE_PACKAGE
    if not required_reports_exist:
        return DRAFT_RELEASE_PACKAGE
    if float(score.get("average_score", 0.0)) < 4.0:
        return NEEDS_MANUAL_MIX
    return RELEASE_PACKAGE_READY


def build_release_readiness_qc(
    *,
    final_audio: dict[str, Any],
    metadata_payload: dict[str, Any] | None = None,
    rights_payload: dict[str, Any] | None = None,
    deliverable_manifest: dict[str, Any] | None = None,
    mix_master: dict[str, Any] | None = None,
    arrangement: dict[str, Any] | None = None,
    reference_profile: dict[str, Any] | None = None,
    requested_deliverables: list[str] | None = None,
    completion_gate: dict[str, Any] | None = None,
    qc_report_path: str | Path | None = None,
    master_qc_report_path: str | Path | None = None,
    release_qc_report_path: str | Path | None = None,
    release_manifest_path: str | Path | None = None,
    rights_checklist_path: str | Path | None = None,
    qc_report_exists: bool | None = None,
    master_qc_report_exists: bool | None = None,
    release_qc_report_exists: bool | None = None,
    release_manifest_exists: bool | None = None,
    rights_checklist_exists: bool | None = None,
    false_claim_risk: dict[str, Any] | None = None,
) -> dict[str, Any]:
    metadata_complete = _metadata_complete(metadata_payload)
    rights = (rights_payload or {}).get("rights", {})
    required_reports = {
        "qc_report": bool(qc_report_exists) if qc_report_exists is not None else _exists(qc_report_path),
        "master_qc_report": bool(master_qc_report_exists) if master_qc_report_exists is not None else _exists(master_qc_report_path),
        "release_qc_report": bool(release_qc_report_exists) if release_qc_report_exists is not None else _exists(release_qc_report_path),
    }
    score = build_commercial_release_score(
        final_audio=final_audio,
        mix_master=mix_master,
        arrangement=arrangement,
        reference_profile=reference_profile,
        deliverable_manifest=deliverable_manifest,
        requested_deliverables=requested_deliverables,
        metadata_complete=metadata_complete,
        rights=rights,
        rights_checklist_exists=bool(rights_checklist_exists) if rights_checklist_exists is not None else _exists(rights_checklist_path),
        release_manifest_exists=bool(release_manifest_exists) if release_manifest_exists is not None else _exists(release_manifest_path),
        false_claim_risk=false_claim_risk,
        completion_gate=completion_gate,
        qc_report_exists=required_reports["qc_report"],
        master_qc_report_exists=required_reports["master_qc_report"],
        release_qc_report_exists=required_reports["release_qc_report"],
    )
    status = determine_release_readiness_status(
        final_audio=final_audio,
        score=score,
        metadata_payload=metadata_payload,
        rights_payload=rights_payload,
        required_reports_exist=all(required_reports.values()),
    )
    category_issues = list(score.get("blocking_issues", []))
    blocking: list[str] = []
    if not bool(final_audio.get("verified") or final_audio.get("ok") or final_audio.get("passed")):
        blocking.extend(
            issue
            for item in score.get("categories", [])
            if item.get("category") == "final_audio_verification"
            for issue in item.get("blocking_issues", [])
        )
    if not metadata_complete and "required release metadata is incomplete" not in blocking:
        blocking.append("required release metadata is incomplete")
    if not _rights_ready(rights_payload):
        blocking.extend((rights_payload or {}).get("blocking_issues", []))
    blocking.extend(score.get("high_safety_issues", []))
    if not all(required_reports.values()):
        missing = [name for name, exists in required_reports.items() if not exists]
        blocking.append(f"required QC reports missing: {', '.join(missing)}")
    if status == NEEDS_MANUAL_MIX:
        blocking.append("average release readiness score is below 4.0")
    release_ready = status == RELEASE_PACKAGE_READY and not score.get("high_safety_issues") and score.get("release_ready_score_pass")
    return {
        "schema_version": "release_readiness_qc.v1",
        "status": status,
        "release_ready": bool(release_ready),
        "average_score": score["average_score"],
        "categories": score["categories"],
        "blocking_issues": list(dict.fromkeys(blocking)),
        "category_issues": list(dict.fromkeys(category_issues)),
        "required_reports": required_reports,
        "high_safety_issues": score.get("high_safety_issues", []),
        "completion_gate_complete": bool((completion_gate or {}).get("complete")),
        "completion_gate_separate": True,
        "commercial_success_claimed": False,
        "limitations": [
            "Release package readiness is local QC only and does not guarantee distributor approval.",
            "Release package readiness does not claim commercial success.",
            "COMPLETE remains separate and must still pass completion_gate.",
        ],
    }


def render_release_readiness_qc_report(qc: dict[str, Any]) -> str:
    lines = [
        "# Release Readiness QC",
        "",
        f"- status: {qc.get('status')}",
        f"- release ready: {str(bool(qc.get('release_ready'))).lower()}",
        f"- average score: {qc.get('average_score')}",
        f"- completion gate complete: {str(bool(qc.get('completion_gate_complete'))).lower()}",
        f"- completion gate separate: {str(bool(qc.get('completion_gate_separate'))).lower()}",
        "",
        "## Category Scores",
    ]
    lines.extend(f"- {item['category']}: {item['score']}/5" for item in qc.get("categories", []))
    lines.extend(
        [
            "",
            "## Blocking Issues",
            *([f"- {item}" for item in qc.get("blocking_issues", [])] or ["- none"]),
            "",
            "## Limitations",
            *[f"- {item}" for item in qc.get("limitations", [])],
        ]
    )
    return "\n".join(lines).rstrip() + "\n"

from __future__ import annotations

from typing import Any

from release_readiness_qc import build_release_readiness_qc


def build_release_qc(
    *,
    final_master: dict[str, Any],
    metadata_payload: dict[str, Any],
    rights_payload: dict[str, Any],
    deliverable_manifest: dict[str, Any],
    cover_art_present: bool = False,
    artwork_required: bool = False,
    mix_master: dict[str, Any] | None = None,
    arrangement: dict[str, Any] | None = None,
    reference_profile: dict[str, Any] | None = None,
    requested_deliverables: list[str] | None = None,
    completion_gate: dict[str, Any] | None = None,
    qc_report_path: str | None = None,
    master_qc_report_path: str | None = None,
    release_qc_report_path: str | None = None,
    release_manifest_path: str | None = None,
    rights_checklist_path: str | None = None,
    qc_report_exists: bool | None = None,
    master_qc_report_exists: bool | None = None,
    release_qc_report_exists: bool | None = None,
    release_manifest_exists: bool | None = None,
    rights_checklist_exists: bool | None = None,
    false_claim_risk: dict[str, Any] | None = None,
) -> dict[str, Any]:
    blocking: list[str] = []
    if not final_master.get("verified"):
        blocking.append("final master audio is not verified")
    if not metadata_payload.get("complete"):
        blocking.append("required release metadata is incomplete")
    if not rights_payload.get("release_ready"):
        blocking.extend(rights_payload.get("blocking_issues", []))
    final_deliverable = next((item for item in deliverable_manifest.get("deliverables", []) if item.get("type") == "final_master"), {})
    if not final_deliverable.get("available"):
        blocking.append("final master deliverable is missing")
    if artwork_required and not cover_art_present:
        blocking.append("cover art is required but missing")
    readiness = build_release_readiness_qc(
        final_audio=final_master,
        metadata_payload=metadata_payload,
        rights_payload=rights_payload,
        deliverable_manifest=deliverable_manifest,
        mix_master=mix_master,
        arrangement=arrangement,
        reference_profile=reference_profile,
        requested_deliverables=requested_deliverables,
        completion_gate=completion_gate,
        qc_report_path=qc_report_path,
        master_qc_report_path=master_qc_report_path,
        release_qc_report_path=release_qc_report_path,
        release_manifest_path=release_manifest_path,
        rights_checklist_path=rights_checklist_path,
        qc_report_exists=True if qc_report_path is None and qc_report_exists is None else qc_report_exists,
        master_qc_report_exists=True if master_qc_report_path is None and master_qc_report_exists is None else master_qc_report_exists,
        release_qc_report_exists=True if release_qc_report_path is None and release_qc_report_exists is None else release_qc_report_exists,
        release_manifest_exists=True if release_manifest_path is None and release_manifest_exists is None else release_manifest_exists,
        rights_checklist_exists=True if rights_checklist_path is None and rights_checklist_exists is None else rights_checklist_exists,
        false_claim_risk=false_claim_risk,
    )
    blocking.extend(readiness.get("blocking_issues", []))
    return {
        "schema_version": "release_qc.v1",
        "status": readiness["status"],
        "release_ready": bool(readiness["release_ready"] and not blocking),
        "average_score": readiness["average_score"],
        "categories": readiness["categories"],
        "blocking_issues": list(dict.fromkeys(blocking)),
        "category_issues": readiness.get("category_issues", []),
        "high_safety_issues": readiness.get("high_safety_issues", []),
        "completion_gate_separate": True,
        "checks": {
            "final_audio_verified": bool(final_master.get("verified")),
            "metadata_complete": bool(metadata_payload.get("complete")),
            "rights_ready": bool(rights_payload.get("release_ready")),
            "final_master_deliverable_present": bool(final_deliverable.get("available")),
            "cover_art_present": bool(cover_art_present),
            "artwork_required": bool(artwork_required),
        },
        "limitations": [
            *readiness.get("limitations", []),
            "Release package does not mean actual distributor submission occurred.",
            "Release-ready does not guarantee distribution approval, rights clearance by third parties, playlist placement, sales, charting, or commercial success.",
        ],
    }


def render_release_qc_report(qc: dict[str, Any]) -> str:
    checks = qc.get("checks", {})
    return "\n".join(
        [
            "# Release QC Report",
            "",
            f"- status: {qc.get('status')}",
            f"- release ready: {str(bool(qc.get('release_ready'))).lower()}",
            f"- average score: {qc.get('average_score')}",
            f"- completion gate separate: {str(bool(qc.get('completion_gate_separate', True))).lower()}",
            "",
            "## Checks",
            *[f"- {key}: {str(bool(value)).lower()}" for key, value in checks.items()],
            "",
            "## Category Scores",
            *[f"- {item['category']}: {item['score']}/5" for item in qc.get("categories", [])],
            "",
            "## Blocking Issues",
            *([f"- {item}" for item in qc.get("blocking_issues", [])] or ["- none"]),
            "",
            "## Limitations",
            *[f"- {item}" for item in qc.get("limitations", [])],
        ]
    ).rstrip() + "\n"

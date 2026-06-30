from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from automix.feedback.feedback_qc_integration import build_feedback_qc_integration
from automix.feedback.revision_memory import summarize_feedback_memory
from automix.plugins.plugin_adapter_schema import now_utc, write_json
from automix.orchestrator.stage_status import StageStatus
from automix.safety.processing_policy_audit import build_processing_policy_audit


GLOBAL_QC_SCHEMA = "automix-global-qc-summary-v1"

QC_FILES = {
    "github_integration": "eval_reports/github_integration_smoke.json",
    "vocal_recovery": "eval_reports/vocal_recovery_eval_metrics.json",
    "pitch": "eval_reports/pitch_eval_metrics.json",
    "vocal_placement": "eval_reports/vocal_placement_eval_metrics.json",
    "reference_matching": "eval_reports/reference_match_eval_metrics.json",
    "premaster": "eval_reports/project_premaster_eval_metrics.json",
    "translation_check": "eval_reports/project_translation_check.json",
    "final_qc": "eval_reports/final_qc_metrics.json",
}


def _load(path: Path) -> dict[str, Any] | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _evaluation_passed(stage: str, data: dict[str, Any] | None) -> bool:
    if not data:
        return False
    for key in ("evaluation_passed", "qc_passed", "translation_passed", "passed"):
        if key in data:
            return bool(data[key])
    status = str(data.get("status") or data.get("evaluation_status") or data.get("final_recommendation") or "")
    return status in {"ok", "passed", "accept", "accept_light_premaster", "ready_for_delivery"}


def build_global_qc_summary(
    *,
    project_name: str,
    output_dir: Path,
    stage_results: list[dict[str, Any]],
    final_delivery_requested: bool = False,
) -> dict[str, Any]:
    stage_qc: list[dict[str, Any]] = []
    critical_blockers: list[str] = []
    warnings: list[str] = []
    applied_stages = {
        result.get("stage")
        for result in stage_results
        if result.get("stage", "").endswith("_draft") and result.get("status") in {StageStatus.PASSED.value, StageStatus.PASSED_WITH_WARNINGS.value}
    }

    for stage, rel in QC_FILES.items():
        path = output_dir / rel
        data = _load(path)
        passed = _evaluation_passed(stage, data)
        status = "passed" if passed else ("missing" if data is None else "review_required")
        critical_failures = []
        critical_warnings = []
        if stage in applied_stages and not passed:
            critical_failures.append("applied_stage_qc_not_passed")
            critical_blockers.append(f"{stage}_applied_stage_qc_not_passed")
        if stage == "final_qc" and final_delivery_requested and not passed:
            critical_failures.append("final_delivery_qc_not_passed")
            critical_blockers.append("qc_failure_for_final_delivery")
        if data and data.get("warnings"):
            critical_warnings.extend(data.get("warnings", []))
        stage_qc.append(
            {
                "stage": stage,
                "status": status,
                "evaluation_passed": passed,
                "path": str(path),
                "exists": path.exists(),
                "critical_warnings": sorted(set(critical_warnings)),
                "critical_failures": sorted(set(critical_failures)),
            }
        )
    for result in stage_results:
        if result.get("status") == StageStatus.SKIPPED.value:
            continue
        warnings.extend(result.get("warnings", []))
    feedback_summary = summarize_feedback_memory(output_dir)
    feedback_qc_integration = build_feedback_qc_integration(project_name=project_name, output_dir=output_dir)
    processing_policy = build_processing_policy_audit(project_name=project_name, output_dir=output_dir)
    if feedback_summary.get("warnings"):
        warnings.extend(feedback_summary.get("warnings", []))
    if feedback_qc_integration.get("warnings"):
        warnings.extend(feedback_qc_integration.get("warnings", []))
    if processing_policy.get("warnings"):
        warnings.extend(processing_policy.get("warnings", []))
    if final_delivery_requested and feedback_summary.get("pending_unresolved_count", 0) > 0:
        critical_blockers.append("user_feedback_unresolved_for_final_delivery")
    if final_delivery_requested and not processing_policy.get("passed", False):
        critical_blockers.append("processing_policy_audit_failed")
    safe_to_export = final_delivery_requested and not critical_blockers and any(item["stage"] == "final_qc" and item["evaluation_passed"] for item in stage_qc)
    summary = {
        "schema": GLOBAL_QC_SCHEMA,
        "project_name": project_name,
        "created_at": now_utc(),
        "overall_qc_status": "passed" if safe_to_export else "review_required",
        "stage_qc": stage_qc,
        "critical_blockers": sorted(set(critical_blockers)),
        "warnings": sorted(set(warnings)),
        "feedback_revision_loop": feedback_summary,
        "feedback_qc_integration": feedback_qc_integration.get("summary", {}),
        "processing_policy_audit": {
            "passed": bool(processing_policy.get("passed", False)),
            "plans_checked": int(processing_policy.get("plans_checked", 0) or 0),
            "blockers": processing_policy.get("blockers", []),
        },
        "safe_to_export": safe_to_export,
    }
    write_json(output_dir / "eval_reports" / "global_qc_summary.json", summary)
    return summary

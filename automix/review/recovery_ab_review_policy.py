from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from automix.plugins.plugin_adapter_schema import write_json


def _read_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _evaluation_for_track(output_dir: Path, draft_track_name: str, original_track_name: str = "") -> dict[str, Any]:
    candidates = [
        output_dir / "eval_reports" / f"{draft_track_name}_recovery_only_eval_metrics.json",
        output_dir / "eval_reports" / f"{original_track_name}_recovery_only_eval_metrics.json",
    ]
    for path in candidates:
        if path.exists():
            return _read_json(path)
    for path in (output_dir / "eval_reports").glob("*_recovery_only_eval_metrics.json"):
        data = _read_json(path)
        if data.get("track_name") in {draft_track_name, original_track_name}:
            return data
    return {}


def build_recovery_ab_review_status(
    *,
    project_name: str,
    drafts: list[dict[str, Any]],
    output_dir: Path,
) -> dict[str, Any]:
    ab_plan = _read_json(output_dir / "eval_reports" / "recovery_only_ab_render_plan.json")
    plan_tracks = {item.get("draft_track_name"): item for item in ab_plan.get("tracks_to_render", []) + ab_plan.get("tracks_not_rendered", [])}
    tracks = []
    for draft in drafts:
        draft_name = str(draft.get("draft_track_name", ""))
        original = str(draft.get("original_track_name", draft.get("track_name", "")))
        plan = plan_tracks.get(draft_name, {})
        eval_metrics = _evaluation_for_track(output_dir, draft_name, original)
        renders = eval_metrics.get("renders_created", {})
        original_ok = bool(renders.get("original"))
        draft_ok = bool(renders.get("recovery_draft") or renders.get("recovered"))
        matched_ok = bool(renders.get("loudness_matched"))
        diff_ok = bool(renders.get("difference"))
        ab_complete = bool(original_ok and draft_ok and matched_ok)
        evaluation_passed = bool(eval_metrics.get("evaluation_passed"))
        warnings = []
        if not ab_complete:
            warnings.append("A/B render required before final use")
        if not matched_ok:
            warnings.append("loudness_matched_render_missing")
        if not diff_ok:
            warnings.append("difference_render_missing")
        if eval_metrics and not evaluation_passed:
            warnings.append("recovery_evaluation_not_passed")
        tracks.append(
            {
                "draft_track_name": draft_name,
                "original_track_name": original,
                "ab_complete": ab_complete,
                "evaluation_passed": evaluation_passed,
                "can_accept_normally": bool(ab_complete and evaluation_passed),
                "can_accept_provisionally": bool(not ab_complete),
                "final_export_blocked": True,
                "render_plan_status": "to_render" if draft_name in {item.get("draft_track_name") for item in ab_plan.get("tracks_to_render", [])} else "not_rendered",
                "warnings": sorted(set(warnings + list(plan.get("warnings", [])))),
            }
        )
    status = {
        "schema": "automix-recovery-ab-review-status-v1",
        "project_name": project_name,
        "tracks": tracks,
        "warnings": sorted(set(w for track in tracks for w in track.get("warnings", []))),
    }
    write_json(output_dir / "review" / "recovery_ab_review_status.json", status)
    return status


def policy_for_decision(
    *,
    ab_status: dict[str, Any],
    decision: str,
    allow_provisional_without_ab: bool = False,
    unsafe_override: bool = False,
) -> dict[str, Any]:
    warnings = list(ab_status.get("warnings", []))
    if decision not in {"accepted", "accepted_light"}:
        return {"allowed": True, "provisional_acceptance": False, "final_export_blocked": True, "warnings": warnings, "blockers": []}
    if ab_status.get("can_accept_normally"):
        return {"allowed": True, "provisional_acceptance": False, "final_export_blocked": True, "warnings": warnings, "blockers": []}
    if ab_status.get("ab_complete") and not ab_status.get("evaluation_passed"):
        if unsafe_override:
            warnings.append("unsafe_override_review_mode_final_export_blocked")
            return {"allowed": True, "provisional_acceptance": True, "final_export_blocked": True, "warnings": warnings, "blockers": []}
        return {"allowed": False, "provisional_acceptance": False, "final_export_blocked": True, "warnings": warnings, "blockers": ["RECOVERY_EVALUATION_FAILED"]}
    if not ab_status.get("ab_complete"):
        if allow_provisional_without_ab:
            warnings.append("provisional_acceptance_without_ab_final_export_blocked")
            return {"allowed": True, "provisional_acceptance": True, "final_export_blocked": True, "warnings": warnings, "blockers": []}
        return {"allowed": False, "provisional_acceptance": False, "final_export_blocked": True, "warnings": warnings, "blockers": ["AB_REVIEW_REQUIRED_FOR_ACCEPTANCE"]}
    return {"allowed": False, "provisional_acceptance": False, "final_export_blocked": True, "warnings": warnings, "blockers": ["UNKNOWN_AB_REVIEW_STATE"]}


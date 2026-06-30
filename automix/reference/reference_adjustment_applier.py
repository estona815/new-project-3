from __future__ import annotations

from pathlib import Path
from typing import Any

from automix.analyze_ai_pitch_source import write_json
from automix.mastering.premaster_safety_analyzer import now_utc


def build_reference_match_rollback(
    *,
    adjustment_plan_path: Path | str = "automix/chain_plans/project_reference_match_adjustment_plan.json",
    comparison_report_path: Path | str = "automix/eval_reports/reference_match_comparison.json",
    original_tracks: list[str] | None = None,
    draft_tracks: list[str] | None = None,
    created_buses: list[str] | None = None,
    created_sends: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return {
        "schema": "automix-reference-match-rollback-v1",
        "original_tracks": original_tracks or [],
        "draft_tracks": draft_tracks or [],
        "created_buses": created_buses or [],
        "created_sends": created_sends or [],
        "plugins_inserted": [],
        "parameters_written": [],
        "routing_changes": [],
        "adjustment_plan": str(adjustment_plan_path),
        "comparison_report": str(comparison_report_path),
        "created_at": now_utc(),
        "safe_to_delete_draft": True,
        "original_mix_untouched": True,
        "original_master_untouched": True,
        "contains_pitch_correction": False,
        "contains_reference_audio_content": False,
    }


def create_reference_match_draft_metadata(plan: dict[str, Any], output_dir: Path, *, apply_draft: bool = False) -> dict[str, Any]:
    draft_tracks = ["PROJECT_REFERENCE_MATCH_DRAFT"] if apply_draft and plan.get("adjustments") else []
    rollback = build_reference_match_rollback(draft_tracks=draft_tracks)
    write_json(output_dir / "rollback" / "project_reference_match_rollback.json", rollback)
    return rollback


def assert_reference_match_draft_safe(plan: dict[str, Any], rollback: dict[str, Any]) -> None:
    if plan.get("contains_pitch_correction"):
        raise AssertionError("reference matching must not insert pitch correction")
    if plan.get("contains_reference_audio_content"):
        raise AssertionError("reference audio must not be inserted as project content")
    if not rollback.get("original_mix_untouched") or not rollback.get("original_master_untouched"):
        raise AssertionError("reference match draft must preserve original mix and master")


from __future__ import annotations

from pathlib import Path
from typing import Any

from automix.analyze_ai_pitch_source import safe_filename, write_json


def build_vocal_sidechain_routing_plan(
    *,
    track_name: str,
    lead_vocal: str,
    instrumental_bus: str | None = None,
    backing_vocals: list[str] | None = None,
    send_tracks: list[str] | None = None,
    action: str,
    output_dir: Path | None = None,
) -> dict[str, Any]:
    backing_vocals = backing_vocals or []
    send_tracks = send_tracks or []
    created_sends = []
    if action in {"dynamic_space_creation_draft", "sidechain_dynamic_eq_draft", "ms_center_cleanup_draft"} and instrumental_bus:
        created_sends.append(
            {
                "source_track": lead_vocal,
                "destination_track": instrumental_bus,
                "purpose": "vocal_keyed_dynamic_eq_detector",
                "audio_channels": "sidechain_only",
                "dry_run": True,
            }
        )
    if action in {"dynamic_space_creation_draft", "sidechain_dynamic_eq_draft"}:
        for backing in backing_vocals:
            created_sends.append(
                {
                    "source_track": lead_vocal,
                    "destination_track": backing,
                    "purpose": "duck_backing_under_lead",
                    "audio_channels": "sidechain_only",
                    "dry_run": True,
                }
            )
    if action == "send_cleanup_draft" or send_tracks:
        for send in send_tracks:
            created_sends.append(
                {
                    "source_track": lead_vocal,
                    "destination_track": send,
                    "purpose": "duck_reverb_delay_tail_under_words",
                    "audio_channels": "sidechain_only",
                    "dry_run": True,
                }
            )

    plan = {
        "schema": "automix-vocal-sidechain-routing-plan-v1",
        "track_name": track_name,
        "lead_vocal": lead_vocal,
        "instrumental_bus": instrumental_bus,
        "backing_vocals": backing_vocals,
        "send_tracks": send_tracks,
        "action": action,
        "dry_run": True,
        "preserve_existing_sends": True,
        "create_new_sidechain_sends_only_when_required": True,
        "created_sends": created_sends,
        "rollback_required": True,
        "warnings": [] if created_sends or action in {"skip_placement", "minimal_vocal_gain_trim"} else ["no routing target available for sidechain placement"],
    }
    if output_dir is not None:
        write_json(output_dir / "chain_plans" / f"{safe_filename(track_name)}_vocal_sidechain_routing_plan.json", plan)
    return plan


def build_vocal_placement_rollback(
    *,
    original_tracks: list[str],
    draft_tracks: list[str],
    created_sends: list[dict[str, Any]],
    created_buses: list[str],
    chain_plan: Path,
    analysis_report: Path,
    created_at: str,
) -> dict[str, Any]:
    return {
        "schema": "automix-vocal-placement-rollback-v1",
        "original_tracks": original_tracks,
        "draft_tracks": draft_tracks,
        "created_sends": created_sends,
        "created_buses": created_buses,
        "plugins_inserted": [],
        "parameters_written": [],
        "routing_changes": created_sends,
        "chain_plan": str(chain_plan),
        "analysis_report": str(analysis_report),
        "created_at": created_at,
        "safe_to_delete_draft": True,
        "draft_creation_status": "pending_reaper_runtime",
    }


def assert_original_mix_unmodified_for_vocal_placement(before: dict[str, Any], after: dict[str, Any]) -> None:
    checked = (
        "lead_vocal_fx_count",
        "instrumental_bus_fx_count",
        "routing_count",
        "master_fx_count",
        "media_checksum",
        "pitch_plugin_count",
    )
    changed = [key for key in checked if before.get(key) != after.get(key)]
    if changed:
        raise AssertionError(f"Original mix modified during vocal placement: {', '.join(changed)}")

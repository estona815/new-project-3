"""Manifest for GitHub-researched REAPER integration routes."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


REFERENCE_REPOSITORIES = [
    {
        "name": "shiehn/total-reaper-mcp",
        "url": "https://github.com/shiehn/total-reaper-mcp",
        "priority": "high",
        "use_for": [
            "python_mcp_server_shape",
            "lua_bridge_shape",
            "file_based_ipc",
            "tool_profiles",
            "natural_language_command_routing",
        ],
        "do_not_copy": ["full_server", "full_lua_bridge", "vendored_environment", "test_suite"],
    },
    {
        "name": "wegitor/reaper-reapy-mcp",
        "url": "https://github.com/wegitor/reaper-reapy-mcp",
        "priority": "high",
        "use_for": [
            "curated_reaper_tool_surface",
            "fx_management_commands",
            "render_project_command",
            "track_and_item_management_commands",
        ],
        "do_not_copy": ["full_mcp_app", "direct_command_implementations_without_local_safety_gate"],
    },
    {
        "name": "RomeoDespres/reapy",
        "url": "https://github.com/RomeoDespres/reapy",
        "priority": "high",
        "use_for": ["optional_python_reaper_control_layer", "project_and_track_abstractions"],
        "do_not_copy": ["library_internals", "vendored_package_source"],
    },
    {
        "name": "2nist/reaper-bridge",
        "url": "https://github.com/2nist/reaper-bridge",
        "priority": "medium",
        "use_for": ["generated_lua_script_pattern", "lightweight_bridge_fallback", "osc_as_future_option"],
        "do_not_copy": ["entire_bridge", "osc_runtime_until_needed"],
    },
    {
        "name": "X-Raym/REAPER-ReaScripts",
        "url": "https://github.com/X-Raym/REAPER-ReaScripts",
        "priority": "low",
        "use_for": ["reascript_style", "region_marker_item_patterns", "reapack_packaging_conventions"],
        "do_not_copy": ["gpl_script_bodies", "whole_script_folders", "helper_functions"],
    },
    {
        "name": "Buy-One/REAPER-scripts",
        "url": "https://github.com/Buy-One/REAPER-scripts",
        "priority": "low",
        "use_for": ["practical_lua_patterns", "user_configurable_script_shape", "batch_editing_style"],
        "do_not_copy": ["script_bodies", "direct_lua_chunks", "project_specific_utilities"],
    },
]


SAFE_COMMAND_CANDIDATES = [
    {
        "id": "analyze_audio",
        "stage": "analysis",
        "default_mode": "report_only",
        "requires_reaper": False,
        "write_allowed": False,
        "evidence_required": ["audio_path_exists", "claim_limits_written"],
    },
    {
        "id": "test_connection",
        "stage": "environment",
        "default_mode": "dry_run",
        "requires_reaper": False,
        "write_allowed": False,
        "evidence_required": ["adapter_response_json"],
    },
    {
        "id": "list_tracks",
        "stage": "inspection",
        "default_mode": "dry_run",
        "requires_reaper": True,
        "write_allowed": False,
        "evidence_required": ["project_snapshot_or_open_project", "adapter_response_json"],
    },
    {
        "id": "list_available_fx",
        "stage": "plugin_inventory",
        "default_mode": "dry_run",
        "requires_reaper": True,
        "write_allowed": False,
        "evidence_required": ["runtime_inventory_report"],
    },
    {
        "id": "add_fx",
        "stage": "draft_execution",
        "default_mode": "blocked_until_snapshot",
        "requires_reaper": True,
        "write_allowed": False,
        "evidence_required": [
            "validated_plugin_adapter",
            "safe_parameter_ranges",
            "project_snapshot",
            "explicit_draft_approval",
        ],
    },
    {
        "id": "set_fx_param",
        "stage": "draft_execution",
        "default_mode": "blocked_until_semantic_validation",
        "requires_reaper": True,
        "write_allowed": False,
        "evidence_required": [
            "observed_semantic_parameter_validation",
            "safe_parameter_ranges",
            "parameter_write_log",
        ],
    },
    {
        "id": "render_project",
        "stage": "ab_preview",
        "default_mode": "blocked_until_ab_plan",
        "requires_reaper": True,
        "write_allowed": False,
        "evidence_required": ["render_manifest", "rollback_handle", "ab_evaluation_plan"],
    },
]


SAFE_COMMAND_CONTRACT = {
    "default_dry_run": True,
    "project_overwrite_allowed": False,
    "destructive_actions_allowed": False,
    "required_sequence": [
        "analyze_audio_and_project_state",
        "propose_conservative_chain",
        "create_snapshot_or_backup",
        "apply_only_after_explicit_approval",
        "render_ab_preview",
        "evaluate_quality_risk",
        "rollback_if_worse",
    ],
    "blocked_by_default": [
        "delete_tracks_takes_items_regions_or_source_files",
        "overwrite_project_or_render_files",
        "irreversible_pitch_or_formant_changes",
        "heavy_denoise_hard_gate_or_transient_destruction",
        "master_limiting_without_headroom_review",
    ],
}


def build_github_integration_manifest() -> dict[str, Any]:
    """Build a JSON-safe manifest for the isolated integration layer."""

    return {
        "schema": "automix-github-integration-manifest-v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "status": "research_reference_and_dry_run_only",
        "source_pack": {
            "id": "reaper_automix_integration_pack_20260605_1005",
            "path_env_var": "REAPER_AUTOMIX_INTEGRATION_PACK",
            "local_path_recorded_in_source": False,
        },
        "claim_limits": [
            "no_third_party_source_copied",
            "not_a_live_reaper_bridge",
            "not_safe_to_write_parameters",
            "not_final_audio_qc",
        ],
        "architecture": {
            "analysis_layer": "portable audio/project diagnostics without REAPER mutation",
            "planning_layer": "Codex maps user intent to conservative internal commands",
            "execution_layer": "future adapter applies approved commands only after snapshot and A/B gates",
            "preferred_ipc": "file_based_json_ipc_before_socket_or_osc_complexity",
        },
        "reference_repositories": REFERENCE_REPOSITORIES,
        "safe_command_contract": SAFE_COMMAND_CONTRACT,
        "safe_command_candidates": SAFE_COMMAND_CANDIDATES,
    }

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from automix.analyze_ai_pitch_source import safe_filename
from automix.plugins.adapter_confidence_gate import evaluate_adapter_confidence
from automix.plugins.plugin_adapter_schema import adapter_matches_plugin, now_utc, safe_float, slugify, write_json
from automix.plugins.plugin_inventory_audit import load_adapters
from automix.plugins.safe_parameter_writer import safe_parameter_write_operation
from automix.plugins.third_party_plugin_policy import evaluate_third_party_policy
from automix.real_project.read_only_project_guard import compare_project_snapshots, snapshot_project_state
from automix.vocal_recovery.recovery_iteration_engine import build_recovery_iteration_history
from automix.vocal_recovery.recovery_profiles import resolve_recovery_profile
from automix.vocal_recovery.vocal_recovery_analyzer import missing_recovery_eval_metrics


ALLOWED_RECOVERY_ROLES = {"lead_vocal", "backing_vocal", "vocal_double", "adlib", "vocal_bus"}
BLOCKED_RECOVERY_ROLES = {
    "instrumental_bus",
    "drum_bus",
    "bass",
    "guitar",
    "piano",
    "synth",
    "fx",
    "reverb_send",
    "delay_send",
    "full_mix_reference",
    "master_related",
    "unknown",
}
ALLOWED_PROFILES = {
    "minimal_cleanup",
    "conservative_ai_vocal_cleanup",
    "source_separated_rescue",
    "thin_vocal_body_preserve",
    "skip_recovery",
}
PITCH_BLOCKED_CONTROLS = [
    "correction_amount",
    "speed",
    "depth",
    "key",
    "scale",
    "formant_preserve",
    "humanize",
    "vibrato_preserve",
]
PITCH_PLUGIN_HINTS = ["mautopitch", "reapitch", "autotune", "auto-tune", "graillon", "melodyne", "revoice"]
HARD_READINESS_BLOCKERS = {
    "validated_plugin_mapping_required",
    "plugin_mapping_unsafe",
    "unknown_vocal_source",
    "full_mix_only_source",
    "missing_rollback_support",
    "prompt41_validation_required_before_safe_draft",
    "read_only_guard_failed",
}
REQUIRED_PROMPT42_OUTPUTS = {
    "scan_report": "eval_reports/real_project_scan_only_report.md",
    "readiness": "eval_reports/real_project_safe_draft_readiness.json",
    "track_audit": "analysis_reports/real_project_track_audit.json",
    "source_safety_map": "eval_reports/real_project_source_safety_map.json",
    "plugin_readiness": "eval_reports/real_project_plugin_readiness.json",
    "read_only_guard": "real_project/read_only_guard_report.json",
}


def _read_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _status_from_prompt42(readiness: dict[str, Any], guard: dict[str, Any], missing: list[str]) -> dict[str, Any]:
    blockers = []
    warnings = []
    if missing:
        blockers.append("PROMPT42_OUTPUTS_MISSING")
        warnings.extend(missing)
    if guard and not guard.get("safe", False):
        blockers.append("READ_ONLY_GUARD_FAILED")
    readiness_blockers = set(readiness.get("blockers", []))
    if readiness and readiness.get("ready") is False and readiness_blockers & HARD_READINESS_BLOCKERS:
        blockers.extend(sorted(readiness_blockers & HARD_READINESS_BLOCKERS))
    prompt41 = safe_float(readiness.get("readiness_breakdown", {}).get("prompt41_validation"), 0.0)
    if readiness and prompt41 <= 0.0:
        blockers.append("PROMPT41_VALIDATION_FAILED_OR_MISSING")
    return {
        "ok_for_recovery_only": not blockers,
        "blockers": sorted(set(blockers)),
        "warnings": sorted(set(warnings)),
    }


def load_prompt42_state(output_dir: Path, from_scan_report: str | Path | None = None) -> dict[str, Any]:
    missing = []
    paths = {key: output_dir / relative for key, relative in REQUIRED_PROMPT42_OUTPUTS.items()}
    if from_scan_report:
        paths["scan_report"] = Path(from_scan_report)
    for key, path in paths.items():
        if not path.exists():
            missing.append(f"{key}:{path}")
    state = {
        "paths": {key: str(path) for key, path in paths.items()},
        "missing": missing,
        "readiness": _read_json(paths["readiness"]),
        "track_audit": _read_json(paths["track_audit"]),
        "source_safety_map": _read_json(paths["source_safety_map"]),
        "plugin_readiness": _read_json(paths["plugin_readiness"]),
        "read_only_guard": _read_json(paths["read_only_guard"]),
    }
    state["precondition"] = _status_from_prompt42(state["readiness"], state["read_only_guard"], missing)
    return state


def _profile_action(track: dict[str, Any], allow_source_separated_rescue: bool) -> tuple[str, str]:
    source = str(track.get("source_classification", "unknown"))
    name = str(track.get("track_name", "")).lower()
    source_sep = safe_float(track.get("source_separated_likelihood"), 0.0)
    if source_sep > 0.55:
        if allow_source_separated_rescue and source_sep <= 0.75:
            return "source_separated_rescue_draft", "source_separated_rescue"
        return "stem_required", "skip_recovery"
    if "thin" in name or "fragile" in name or "body" in " ".join(track.get("warnings", [])).lower():
        return "conservative_ai_vocal_cleanup_draft", "thin_vocal_body_preserve"
    if source in {"ai_vocal_stem", "mixed_vocal_stem"} or safe_float(track.get("already_mixed_score"), 0.0) > 0.45:
        return "conservative_ai_vocal_cleanup_draft", "conservative_ai_vocal_cleanup"
    return "minimal_cleanup_draft", "minimal_cleanup"


def _track_matches_filter(track: dict[str, Any], track_filter: str | None) -> bool:
    if not track_filter:
        return True
    needle = track_filter.lower()
    return needle in str(track.get("track_name", "")).lower() or needle == str(track.get("index", "")).lower()


def _has_draft_conflict(track: dict[str, Any], all_tracks: list[dict[str, Any]]) -> bool:
    draft_name = f"{track.get('track_name')}_RECOVERY_DRAFT_v01".lower()
    return any(str(item.get("track_name", "")).lower() == draft_name for item in all_tracks)


def select_recovery_tracks(
    *,
    prompt42_state: dict[str, Any],
    allow_source_separated_rescue: bool = False,
    track_filter: str | None = None,
) -> dict[str, Any]:
    track_audit = prompt42_state.get("track_audit", {})
    tracks = list(track_audit.get("tracks", []))
    plugin_ready = prompt42_state.get("plugin_readiness", {})
    plugin_safe = bool(plugin_ready.get("safe_draft_plugin_ready"))
    rollback_ready = safe_float(prompt42_state.get("readiness", {}).get("readiness_breakdown", {}).get("rollback_preparedness"), 0.0) > 0.0
    precondition = prompt42_state.get("precondition", {})
    eligible = []
    blocked = []
    manual_review = []
    for track in tracks:
        if not _track_matches_filter(track, track_filter):
            continue
        role = str(track.get("role", "unknown"))
        source = str(track.get("source_classification", "unknown"))
        full_mix = safe_float(track.get("full_mix_likelihood"), 0.0)
        vocal = safe_float(track.get("vocal_likelihood"), 0.0)
        source_sep = safe_float(track.get("source_separated_likelihood"), 0.0)
        reasons = []
        warnings = list(track.get("warnings", []))
        if role in BLOCKED_RECOVERY_ROLES or role not in ALLOWED_RECOVERY_ROLES:
            reasons.append("ROLE_NOT_RECOVERY_ELIGIBLE")
        if vocal < 0.50:
            reasons.append("VOCAL_LIKELIHOOD_LOW")
        if full_mix > 0.65 or source == "full_mix":
            reasons.append("FULL_MIX_UNSAFE_FOR_VOCAL_RECOVERY")
        if source == "unknown":
            reasons.append("UNKNOWN_SOURCE_BLOCKED")
        if source_sep > 0.75:
            reasons.append("SOURCE_SEPARATED_DAMAGE_TOO_SEVERE")
        elif source_sep > 0.55 and not allow_source_separated_rescue:
            reasons.append("SOURCE_SEPARATED_RESCUE_NOT_AUTHORIZED")
        if not plugin_safe:
            reasons.append("PLUGIN_MAPPING_UNSAFE")
        if not rollback_ready:
            reasons.append("ROLLBACK_NOT_READY")
        if not precondition.get("ok_for_recovery_only", False):
            reasons.extend(precondition.get("blockers", []))
        if _has_draft_conflict(track, tracks):
            reasons.append("UNRESOLVED_RECOVERY_DRAFT_CONFLICT")
        action, profile = _profile_action(track, allow_source_separated_rescue)
        item = {
            "track_name": track.get("track_name"),
            "track_guid": track.get("track_guid", ""),
            "role": role,
            "source_classification": source,
            "recovery_action": action,
            "selected_profile": profile,
            "risk": track.get("recovery_risk", track.get("pitch_risk", "unknown")),
            "approved_for_draft": not reasons and profile in ALLOWED_PROFILES and profile != "skip_recovery",
            "warnings": sorted(set(warnings)),
            "source_metrics": {
                "vocal_likelihood": vocal,
                "full_mix_likelihood": full_mix,
                "source_separated_likelihood": source_sep,
                "already_tuned_score": safe_float(track.get("already_tuned_score"), 0.0),
            },
        }
        if reasons:
            blocked.append(
                {
                    "track_name": track.get("track_name"),
                    "track_guid": track.get("track_guid", ""),
                    "role": role,
                    "source_classification": source,
                    "blocked_reason_codes": sorted(set(reasons)),
                    "recommended_action": "provide_isolated_stem" if "FULL_MIX_UNSAFE_FOR_VOCAL_RECOVERY" in reasons else ("validate_plugins_first" if "PLUGIN_MAPPING_UNSAFE" in reasons else "manual_review_required"),
                    "stem_required": any(reason in reasons for reason in {"FULL_MIX_UNSAFE_FOR_VOCAL_RECOVERY", "SOURCE_SEPARATED_DAMAGE_TOO_SEVERE"}),
                    "warnings": sorted(set(warnings)),
                }
            )
        elif item["approved_for_draft"]:
            eligible.append(item)
        else:
            manual_review.append({**item, "approved_for_draft": False})
    return {
        "schema": "automix-recovery-only-track-selection-v1",
        "project_name": track_audit.get("project_name", "project"),
        "eligible_tracks": eligible,
        "blocked_tracks": blocked,
        "manual_review_tracks": manual_review,
        "summary": {
            "total_tracks_considered": len([track for track in tracks if _track_matches_filter(track, track_filter)]),
            "eligible_count": len(eligible),
            "blocked_count": len(blocked),
            "manual_review_count": len(manual_review),
        },
    }


def _load_plugin_audit(output_dir: Path) -> dict[str, Any]:
    return _read_json(output_dir / "analysis_reports" / "plugin_inventory_audit.json")


def _find_safe_recovery_plugin(output_dir: Path, plugin_audit: dict[str, Any]) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    adapters = load_adapters([output_dir / "plugins" / "builtin_adapters", output_dir / "plugins" / "learned_adapters", Path("automix/plugins/builtin_adapters")])
    for plugin in plugin_audit.get("plugins_detected", []):
        if not plugin.get("safe_for_automix"):
            continue
        name = str(plugin.get("name", ""))
        for adapter in adapters:
            if adapter_matches_plugin(adapter, name):
                return plugin, adapter
    return None, None


def _analysis_for_profile(track: dict[str, Any]) -> dict[str, Any]:
    metrics = track.get("source_metrics", {})
    return {
        "source_classification": track.get("source_classification"),
        "already_mixed_score": metrics.get("already_mixed_score", 0.0),
        "already_tuned_score": metrics.get("already_tuned_score", 0.0),
        "source_separated_likelihood": metrics.get("source_separated_likelihood", 0.0),
        "full_mix_likelihood": metrics.get("full_mix_likelihood", 0.0),
        "artifact_profile": {
            "vocal_thinness_score": 0.65 if track.get("selected_profile") == "thin_vocal_body_preserve" else 0.20,
            "watery_phase_score": metrics.get("source_separated_likelihood", 0.0),
        },
        "processing_profile": {
            "compression_limited_score": 0.0,
            "baked_reverb_score": 0.0,
            "mono_compatibility_risk": 0.0,
        },
    }


def build_recovery_chain_plan(
    *,
    track: dict[str, Any],
    output_dir: Path,
    plugin_entry: dict[str, Any] | None,
    adapter: dict[str, Any] | None,
    dry_run: bool,
) -> dict[str, Any]:
    analysis = _analysis_for_profile(track)
    profile = resolve_recovery_profile(track.get("recovery_action", "minimal_cleanup_draft"), analysis, adapter_status={})
    selected_profile = track.get("selected_profile") or profile.get("profile")
    if selected_profile not in ALLOWED_PROFILES:
        selected_profile = "skip_recovery"
    settings = dict(profile.get("settings", {}))
    plugin_name = plugin_entry.get("name") if plugin_entry else "unmapped"
    semantic_settings = {
        key: value
        for key, value in settings.items()
        if isinstance(value, (int, float)) and key not in {"apply", "compression_amount", "saturation_amount", "stereo_width_change"}
    }
    gate = evaluate_adapter_confidence(
        desired_semantic_controls=semantic_settings,
        adapter=adapter,
        plugin_name=plugin_name,
        plugin_detected=bool(plugin_entry),
        workflow_stage="vocal_recovery",
        source_risk=str(track.get("risk", "normal")),
        fallback="stock_or_jsfx_recovery_fallback",
    )
    third_party = evaluate_third_party_policy(plugin_name, adapter, source_context={"compressed_source": False}, min_confidence=gate.get("required_confidence", 0.85))
    safe_to_apply = bool(gate.get("allowed") and third_party.get("allowed") and selected_profile != "skip_recovery")
    write_log = safe_parameter_write_operation(
        operation="recovery_only_pilot",
        plugin_name=plugin_name,
        track_name=str(track.get("track_name")),
        semantic_settings=semantic_settings,
        adapter=adapter or {},
        output_dir=output_dir,
        dry_run=True,
        min_confidence=gate.get("required_confidence", 0.85),
    )
    chain_plan = {
        "schema": "automix-recovery-only-chain-plan-v1",
        "stage": "recovery_only_pilot",
        "project_name": track.get("project_name", ""),
        "track_name": track.get("track_name"),
        "track_guid": track.get("track_guid", ""),
        "draft_track_name": f"{track.get('track_name')}_RECOVERY_DRAFT_v01",
        "selected_profile": selected_profile,
        "allowed_profiles": sorted(ALLOWED_PROFILES),
        "contains_pitch_correction": False,
        "disallowed_processing": [
            "pitch_correction",
            "aggressive_denoise",
            "heavy_compression",
            "ott_style_compression",
            "strong_saturation",
            "stereo_widening",
            "reverb_addition",
            "master_processing",
            "reference_matching",
        ],
        "plugin_chain": [
            {
                "slot": 1,
                "plugin": plugin_name,
                "category": "conservative_vocal_recovery",
                "semantic_settings": semantic_settings,
                "adapter_confidence_gate_enforced": True,
                "adapter_confidence_gate": gate,
                "third_party_policy": third_party,
                "safe_to_apply": safe_to_apply,
            }
        ],
        "safe_to_apply": safe_to_apply,
        "dry_run": dry_run,
        "parameter_write_log": write_log.get("path"),
        "warnings": sorted(set(profile.get("warnings", []) + gate.get("warnings", []) + third_party.get("warnings", []))),
    }
    path = output_dir / "chain_plans" / f"{safe_filename(str(track.get('track_name')))}_recovery_only_chain_plan.json"
    write_json(path, chain_plan)
    chain_plan["path"] = str(path)
    return chain_plan


def write_pitch_block_report(output_dir: Path) -> dict[str, Any]:
    report = {
        "schema": "automix-recovery-only-pitch-block-v1",
        "pitch_stage_blocked": True,
        "reason": "Recovery-only pilot does not allow pitch correction.",
        "pitch_plugins_inserted": False,
        "pitch_parameters_written": False,
        "blocked_controls": PITCH_BLOCKED_CONTROLS,
        "warnings": [],
    }
    write_json(output_dir / "eval_reports" / "recovery_only_pitch_block_report.json", report)
    return report


def _draft_rollback(
    *,
    output_dir: Path,
    original_track: dict[str, Any],
    draft_track_name: str,
    draft_track_guid: str,
    chain_plan: dict[str, Any],
    plugins_inserted: list[str],
    parameters_written: list[dict[str, Any]],
) -> dict[str, Any]:
    rollback = {
        "schema": "automix-recovery-only-rollback-v1",
        "stage": "recovery_only_pilot",
        "original_track_name": original_track.get("track_name"),
        "original_track_guid": original_track.get("track_guid", ""),
        "draft_track_name": draft_track_name,
        "draft_track_guid": draft_track_guid,
        "plugins_inserted": plugins_inserted,
        "parameters_written": parameters_written,
        "routing_changes": [],
        "chain_plan": chain_plan.get("path"),
        "analysis_report": "automix/analysis_reports/real_project_track_audit.json",
        "created_at": now_utc(),
        "safe_to_delete_draft": True,
        "safe_to_rollback": True,
    }
    path = output_dir / "rollback" / f"{safe_filename(str(original_track.get('track_name')))}_recovery_only_rollback.json"
    write_json(path, rollback)
    rollback["path"] = str(path)
    return rollback


def _copy_json_project_with_drafts(
    *,
    project_path: Path,
    output_dir: Path,
    chain_plans: list[dict[str, Any]],
    track_audit: dict[str, Any],
    mute_drafts: bool,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], str, list[str]]:
    warnings: list[str] = []
    try:
        project = json.loads(project_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return [], [], "", ["json_project_copy_failed"]
    source_tracks = project.get("tracks", []) if isinstance(project.get("tracks"), list) else []
    audit_by_name = {track.get("track_name"): track for track in track_audit.get("tracks", [])}
    created = []
    rollbacks = []
    out_tracks = []
    for track in source_tracks:
        out_tracks.append(dict(track))
        track_name = str(track.get("name", ""))
        matching_plan = next((plan for plan in chain_plans if plan.get("track_name") == track_name and plan.get("safe_to_apply")), None)
        if not matching_plan:
            continue
        draft = dict(track)
        draft["name"] = matching_plan["draft_track_name"]
        draft["track_guid"] = f"{{RECOVERY-DRAFT-{len(created) + 1:04d}}}"
        draft["muted"] = bool(mute_drafts)
        draft["recovery_only_draft"] = True
        draft["fx"] = list(track.get("fx", [])) + [item["plugin"] for item in matching_plan.get("plugin_chain", [])]
        out_tracks.append(draft)
        created.append(
            {
                "original_track_name": track_name,
                "draft_track_name": draft["name"],
                "draft_track_guid": draft["track_guid"],
                "muted": bool(mute_drafts),
                "chain_plan": matching_plan.get("path"),
            }
        )
        original_audit = audit_by_name.get(track_name, {"track_name": track_name, "track_guid": track.get("track_guid", "")})
        rollback = _draft_rollback(
            output_dir=output_dir,
            original_track=original_audit,
            draft_track_name=draft["name"],
            draft_track_guid=draft["track_guid"],
            chain_plan=matching_plan,
            plugins_inserted=[item["plugin"] for item in matching_plan.get("plugin_chain", [])],
            parameters_written=[],
        )
        rollbacks.append(rollback)
    project["tracks"] = [{"track_index": idx + 1, **{k: v for k, v in track.items() if k != "track_index"}} for idx, track in enumerate(out_tracks)]
    path = output_dir / "real_project" / "recovery_only_draft_project.json"
    write_json(path, project)
    return created, rollbacks, str(path), warnings


def apply_recovery_drafts(
    *,
    project_path: Path,
    output_dir: Path,
    chain_plans: list[dict[str, Any]],
    track_audit: dict[str, Any],
    apply_drafts: bool,
    dry_run: bool,
    mute_drafts: bool,
) -> dict[str, Any]:
    if dry_run or not apply_drafts:
        return {
            "drafts_created": [],
            "rollbacks": [],
            "draft_project_path": "",
            "warnings": ["dry_run_no_recovery_tracks_created"],
            "applied": False,
        }
    safe_plans = [plan for plan in chain_plans if plan.get("safe_to_apply")]
    if not safe_plans:
        return {"drafts_created": [], "rollbacks": [], "draft_project_path": "", "warnings": ["no_safe_recovery_chain_plans"], "applied": False}
    if project_path.suffix.lower() == ".json":
        created, rollbacks, draft_project, warnings = _copy_json_project_with_drafts(
            project_path=project_path,
            output_dir=output_dir,
            chain_plans=safe_plans,
            track_audit=track_audit,
            mute_drafts=mute_drafts,
        )
        return {"drafts_created": created, "rollbacks": rollbacks, "draft_project_path": draft_project, "warnings": warnings, "applied": bool(created)}
    if not shutil.which("reaper") and not shutil.which("REAPER"):
        return {
            "drafts_created": [],
            "rollbacks": [],
            "draft_project_path": "",
            "warnings": ["reaper_runtime_unavailable_rpp_draft_creation_blocked"],
            "applied": False,
        }
    return {
        "drafts_created": [],
        "rollbacks": [],
        "draft_project_path": "",
        "warnings": ["reaper_runtime_application_requires_manual_reascript_execution"],
        "applied": False,
    }


def build_ab_render_plan(
    *,
    project_name: str,
    selection: dict[str, Any],
    drafts_created: list[dict[str, Any]],
    render_ab: bool,
    apply_drafts: bool,
    output_dir: Path,
) -> dict[str, Any]:
    draft_by_original = {draft["original_track_name"]: draft for draft in drafts_created}
    tracks_to_render = []
    tracks_not_rendered = []
    for track in selection.get("eligible_tracks", []):
        draft = draft_by_original.get(track.get("track_name"))
        entry = {
            "original_track_name": track.get("track_name"),
            "draft_track_name": draft.get("draft_track_name") if draft else f"{track.get('track_name')}_RECOVERY_DRAFT_v01",
            "render_original": True,
            "render_recovery_draft": True,
            "render_loudness_matched": True,
            "render_difference": True,
            "priority": "high",
        }
        if render_ab and apply_drafts and draft:
            tracks_to_render.append(entry)
        else:
            tracks_not_rendered.append({**entry, "reason": "A/B render required for acceptance" if not render_ab else "draft_not_created"})
    plan = {
        "schema": "automix-recovery-only-ab-render-plan-v1",
        "project_name": project_name,
        "render_enabled": bool(render_ab and apply_drafts),
        "tracks_to_render": tracks_to_render,
        "tracks_not_rendered": tracks_not_rendered,
        "warnings": [] if render_ab and apply_drafts else ["render_disabled_plan_only", "evaluation_cannot_pass_without_ab_renders"],
    }
    write_json(output_dir / "eval_reports" / "recovery_only_ab_render_plan.json", plan)
    return plan


def write_missing_evaluation_reports(output_dir: Path, tracks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    reports = []
    for track in tracks:
        metrics = missing_recovery_eval_metrics(str(track.get("track_name")), {})
        metrics["schema"] = "automix-recovery-only-eval-metrics-v1"
        metrics["recommended_action"] = "manual_review_required"
        metrics["warnings"] = sorted(set(metrics.get("warnings", []) + ["A/B render required for acceptance"]))
        path = output_dir / "eval_reports" / f"{safe_filename(str(track.get('track_name')))}_recovery_only_eval_metrics.json"
        write_json(path, metrics)
        reports.append({**metrics, "path": str(path)})
    return reports


def write_iteration_histories(output_dir: Path, chain_plans: list[dict[str, Any]], evaluations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    eval_by_track = {item.get("track_name"): item for item in evaluations}
    histories = []
    for plan in chain_plans:
        settings = plan.get("plugin_chain", [{}])[0].get("semantic_settings", {})
        metrics = eval_by_track.get(plan.get("track_name"), {})
        history = build_recovery_iteration_history(settings, [metrics] if metrics else [], max_iterations=2)
        path = output_dir / "eval_reports" / f"{safe_filename(str(plan.get('track_name')))}_recovery_only_iteration_history.json"
        write_json(path, history)
        histories.append({**history, "path": str(path), "track_name": plan.get("track_name")})
    return histories


def write_original_protection_report(
    *,
    project_name: str,
    output_dir: Path,
    before_snapshot: dict[str, Any],
    after_snapshot: dict[str, Any],
    pitch_block: dict[str, Any],
    rollbacks: list[dict[str, Any]],
    drafts_created: list[dict[str, Any]],
) -> dict[str, Any]:
    comparison = compare_project_snapshots(before_snapshot, after_snapshot)
    rollback_missing = bool(drafts_created and len(rollbacks) != len(drafts_created))
    report = {
        "schema": "automix-recovery-only-original-protection-v1",
        "project_name": project_name,
        "original_tracks_modified": comparison["modified"],
        "original_master_modified": before_snapshot.get("master_fx_count") != after_snapshot.get("master_fx_count"),
        "original_routing_modified": before_snapshot.get("routing_summary") != after_snapshot.get("routing_summary"),
        "original_media_modified": before_snapshot.get("media_item_counts") != after_snapshot.get("media_item_counts"),
        "unexpected_changes": comparison["modification_detected"],
        "pitch_plugin_inserted_anywhere": bool(pitch_block.get("pitch_plugins_inserted")),
        "rollback_metadata_missing": rollback_missing,
        "safe": not comparison["modified"] and not pitch_block.get("pitch_plugins_inserted") and not rollback_missing,
        "warnings": ["rollback_metadata_missing"] if rollback_missing else [],
    }
    write_json(output_dir / "eval_reports" / "recovery_only_original_protection_report.json", report)
    return report


def write_rollback_registry(output_dir: Path, project_name: str, rollbacks: list[dict[str, Any]]) -> dict[str, Any]:
    entries = [
        {
            "original_track_name": item.get("original_track_name"),
            "draft_track_name": item.get("draft_track_name"),
            "rollback_file": item.get("path"),
            "safe_to_rollback": bool(item.get("safe_to_rollback", True)),
        }
        for item in rollbacks
    ]
    registry = {
        "schema": "automix-recovery-only-rollback-registry-v1",
        "project_name": project_name,
        "created_at": now_utc(),
        "entries": entries,
        "all_entries_valid": all(item.get("safe_to_rollback", True) and item.get("path") for item in rollbacks),
        "warnings": [] if entries else ["no_recovery_drafts_created_no_rollback_entries"],
    }
    write_json(output_dir / "rollback" / "recovery_only_rollback_registry.json", registry)
    return registry


def write_parameter_write_log(output_dir: Path, chain_plans: list[dict[str, Any]]) -> dict[str, Any]:
    individual_paths = [plan.get("parameter_write_log") for plan in chain_plans if plan.get("parameter_write_log")]
    entries = []
    skipped = []
    for raw_path in individual_paths:
        data = _read_json(Path(raw_path))
        entries.extend(data.get("written", []))
        skipped.extend(data.get("skipped", []))
    log = {
        "schema": "automix-recovery-only-parameter-write-log-v1",
        "created_at": now_utc(),
        "individual_logs": individual_paths,
        "parameters_written": entries,
        "parameters_skipped": skipped,
        "unknown_parameters_skipped": True,
        "low_confidence_parameters_skipped": any(item.get("reason") == "SEMANTIC_CONTROL_NOT_WRITE_ALLOWED" for item in skipped),
        "fixed_parameter_indexes_used": False,
        "commercial_plugins_require_validated_adapter": True,
    }
    write_json(output_dir / "logs" / "recovery_only_parameter_write_log.json", log)
    return log


def validate_pitch_block(output_dir: Path, chain_plans: list[dict[str, Any]], drafts_created: list[dict[str, Any]]) -> dict[str, Any]:
    failures = []
    for plan in chain_plans:
        if plan.get("contains_pitch_correction"):
            failures.append("pitch_chain_plan_marked_applied")
        if "pitch" in str(plan.get("draft_track_name", "")).lower():
            failures.append("draft_name_contains_pitch")
        for item in plan.get("plugin_chain", []):
            plugin = str(item.get("plugin", "")).lower()
            if any(hint in plugin for hint in PITCH_PLUGIN_HINTS):
                failures.append("pitch_plugin_in_recovery_chain")
            if any(control in item.get("semantic_settings", {}) for control in PITCH_BLOCKED_CONTROLS):
                failures.append("pitch_semantic_control_in_recovery_chain")
    for draft in drafts_created:
        if "pitch" in str(draft.get("draft_track_name", "")).lower():
            failures.append("draft_name_contains_pitch")
    validation = {
        "schema": "automix-recovery-only-pitch-block-validation-v1",
        "passed": not failures,
        "failures": sorted(set(failures)),
    }
    write_json(output_dir / "eval_reports" / "recovery_only_pitch_block_validation.json", validation)
    return validation


def write_blocker_report(output_dir: Path, project_name: str, blockers: list[str], warnings: list[str]) -> dict[str, Any]:
    report = {
        "schema": "automix-recovery-only-blocker-report-v1",
        "project_name": project_name,
        "recovery_applied": False,
        "blockers": sorted(set(blockers)),
        "warnings": sorted(set(warnings)),
        "recommended_action": "run_prompt42_first" if "PROMPT42_OUTPUTS_MISSING" in blockers else "validate_plugins_first",
    }
    write_json(output_dir / "eval_reports" / "recovery_only_blocker_report.json", report)
    return report


def write_pilot_report(
    *,
    output_dir: Path,
    project_name: str,
    selection: dict[str, Any],
    chain_plans: list[dict[str, Any]],
    drafts_created: list[dict[str, Any]],
    pitch_block: dict[str, Any],
    ab_plan: dict[str, Any],
    evaluations: list[dict[str, Any]],
    protection: dict[str, Any],
    rollback_registry: dict[str, Any],
    precondition: dict[str, Any],
    render_ab: bool,
    final_recommendation: str,
) -> Path:
    plan_by_track = {plan.get("track_name"): plan for plan in chain_plans}
    draft_by_track = {draft.get("original_track_name"): draft for draft in drafts_created}
    lines = [
        "# Recovery-Only Pilot Report",
        "",
        "## Summary",
        "",
        f"- Project: `{project_name}`",
        "- Mode: `recovery_only_pilot`",
        f"- Recovery drafts created: `{len(drafts_created)}`",
        f"- Pitch correction blocked: `{pitch_block.get('pitch_stage_blocked')}`",
        f"- Original tracks untouched: `{not protection.get('original_tracks_modified')}`",
        f"- Original master untouched: `{not protection.get('original_master_modified')}`",
        f"- Render enabled: `{render_ab}`",
        f"- Evaluation status: `{'render_required' if not render_ab else 'not_passed_without_verified_renders'}`",
        "",
        "## Preconditions",
        "",
        f"- Prompt 41 validation: `{precondition.get('prompt41_status', 'see Prompt42 readiness')}`",
        f"- Prompt 42 scan-only report: `{not bool(precondition.get('missing'))}`",
        f"- Read-only guard: `{precondition.get('read_only_guard_safe')}`",
        f"- Safe-draft readiness: `{precondition.get('safe_draft_ready')}`",
        f"- Recovery-only precondition blockers: `{', '.join(precondition.get('blockers', [])) or 'none'}`",
        "",
        "## Track Selection",
        "",
        "| Track | Role | Source Type | Risk | Recovery Action | Draft Created | Blockers | Warnings |",
        "|---|---|---|---|---|---:|---|---|",
    ]
    for track in selection.get("eligible_tracks", []):
        draft = draft_by_track.get(track.get("track_name"))
        lines.append(
            f"| `{track.get('track_name')}` | `{track.get('role')}` | `{track.get('source_classification')}` | `{track.get('risk')}` | `{track.get('recovery_action')}` | `{bool(draft)}` |  | `{', '.join(track.get('warnings', [])[:3])}` |"
        )
    for track in selection.get("blocked_tracks", []):
        lines.append(
            f"| `{track.get('track_name')}` | `{track.get('role')}` | `{track.get('source_classification')}` | `blocked` |  | `False` | `{', '.join(track.get('blocked_reason_codes', []))}` | `{', '.join(track.get('warnings', [])[:3])}` |"
        )
    lines.extend(["", "## Blocked Tracks", ""])
    if not selection.get("blocked_tracks"):
        lines.append("- none")
    for track in selection.get("blocked_tracks", []):
        lines.append(f"- `{track.get('track_name')}`: `{', '.join(track.get('blocked_reason_codes', []))}`; recommended `{track.get('recommended_action')}`; stem required `{track.get('stem_required')}`")
    lines.extend(["", "## Recovery Drafts", ""])
    if not drafts_created:
        lines.append("- none")
    for draft in drafts_created:
        plan = plan_by_track.get(draft.get("original_track_name"), {})
        chain = plan.get("plugin_chain", [])
        lines.append(f"- `{draft.get('draft_track_name')}` from `{draft.get('original_track_name')}`")
        lines.append(f"  - selected profile: `{plan.get('selected_profile')}`")
        lines.append(f"  - plugin chain: `{', '.join(item.get('plugin', '') for item in chain)}`")
        lines.append("  - controls written: `0`")
        lines.append(f"  - controls skipped: `{len(_read_json(Path(plan.get('parameter_write_log', ''))).get('parameters_skipped', [])) if plan.get('parameter_write_log') else 0}`")
        lines.append(f"  - rollback file: `{next((item.get('rollback_file') for item in rollback_registry.get('entries', []) if item.get('draft_track_name') == draft.get('draft_track_name')), '')}`")
    lines.extend(
        [
            "",
            "## Pitch Correction Block",
            "",
            f"- pitch stage blocked: `{pitch_block.get('pitch_stage_blocked')}`",
            f"- pitch plugins inserted: `{pitch_block.get('pitch_plugins_inserted')}`",
            f"- pitch parameters written: `{pitch_block.get('pitch_parameters_written')}`",
            "- status: `blocked`",
            "",
            "## A/B Render Plan",
            "",
            f"- original render: `{bool(ab_plan.get('tracks_to_render'))}`",
            f"- recovery render: `{bool(ab_plan.get('tracks_to_render'))}`",
            f"- loudness matched: `{bool(ab_plan.get('tracks_to_render'))}`",
            f"- difference: `{bool(ab_plan.get('tracks_to_render'))}`",
            f"- status: `{'enabled' if ab_plan.get('render_enabled') else 'plan_only'}`",
            "",
            "## Evaluation",
            "",
        ]
    )
    if not evaluations:
        lines.append("- no rendered recovery draft evaluations")
    for metrics in evaluations:
        lines.append(f"- `{metrics.get('track_name')}`: passed `{metrics.get('evaluation_passed')}`, recommendation `{metrics.get('recommended_action')}`")
    lines.extend(
        [
            "",
            "## Original Protection",
            "",
            f"- original tracks modified: `{protection.get('original_tracks_modified')}`",
            f"- original master modified: `{protection.get('original_master_modified')}`",
            f"- routing modified: `{protection.get('original_routing_modified')}`",
            f"- media modified: `{protection.get('original_media_modified')}`",
            f"- safe: `{protection.get('safe')}`",
            "",
            "## Manual Listening Checklist",
            "",
            "- Does the recovered draft sound less metallic without becoming dull?",
            "- Did sibilance become lispy or watery?",
            "- Did the vocal lose body?",
            "- Did consonants smear?",
            "- Did reverb tails become strange?",
            "- Did phase or stereo image become unstable?",
            "- Does the result sound less AI-like, or just darker/quieter?",
            "",
            "## Final Recommendation",
            "",
            f"`{final_recommendation}`",
            "",
        ]
    )
    path = output_dir / "eval_reports" / "recovery_only_pilot_report.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def run_recovery_only_pilot(
    *,
    project_path: str | Path | None,
    from_scan_report: str | Path | None = None,
    apply_drafts: bool = False,
    render_ab: bool = False,
    track_filter: str | None = None,
    allow_source_separated_rescue: bool = False,
    mute_drafts: bool = True,
    strict_original_protection: bool = True,
    output_dir: str | Path = "automix",
    dry_run: bool = True,
    verbose: bool = False,
) -> dict[str, Any]:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    project = Path(project_path).expanduser() if project_path else Path("")
    effective_dry_run = bool(dry_run or not apply_drafts)
    if render_ab and not apply_drafts:
        render_ab = False
    before = snapshot_project_state(project if strict_original_protection else None)
    prompt42 = load_prompt42_state(output, from_scan_report)
    project_name = prompt42.get("track_audit", {}).get("project_name") or (project.stem if project_path else "project")
    selection = select_recovery_tracks(prompt42_state=prompt42, allow_source_separated_rescue=allow_source_separated_rescue, track_filter=track_filter)
    write_json(output / "eval_reports" / "recovery_only_track_selection.json", selection)
    pitch_block = write_pitch_block_report(output)
    plugin_audit = _load_plugin_audit(output)
    plugin_entry, adapter = _find_safe_recovery_plugin(output, plugin_audit)
    chain_plans: list[dict[str, Any]] = []
    for track in selection.get("eligible_tracks", []):
        track_with_project = {**track, "project_name": project_name}
        chain_plans.append(build_recovery_chain_plan(track=track_with_project, output_dir=output, plugin_entry=plugin_entry, adapter=adapter, dry_run=effective_dry_run))
    parameter_log = write_parameter_write_log(output, chain_plans)
    application = apply_recovery_drafts(
        project_path=project,
        output_dir=output,
        chain_plans=chain_plans,
        track_audit=prompt42.get("track_audit", {}),
        apply_drafts=apply_drafts,
        dry_run=effective_dry_run,
        mute_drafts=mute_drafts,
    )
    after = snapshot_project_state(project if strict_original_protection else None)
    pitch_validation = validate_pitch_block(output, chain_plans, application.get("drafts_created", []))
    evaluations = write_missing_evaluation_reports(output, selection.get("eligible_tracks", []))
    histories = write_iteration_histories(output, chain_plans, evaluations)
    ab_plan = build_ab_render_plan(
        project_name=project_name,
        selection=selection,
        drafts_created=application.get("drafts_created", []),
        render_ab=render_ab,
        apply_drafts=apply_drafts,
        output_dir=output,
    )
    protection = write_original_protection_report(
        project_name=project_name,
        output_dir=output,
        before_snapshot=before,
        after_snapshot=after,
        pitch_block=pitch_block,
        rollbacks=application.get("rollbacks", []),
        drafts_created=application.get("drafts_created", []),
    )
    rollback_registry = write_rollback_registry(output, project_name, application.get("rollbacks", []))
    precondition_summary = {
        "missing": prompt42.get("missing", []),
        "blockers": prompt42.get("precondition", {}).get("blockers", []),
        "warnings": prompt42.get("precondition", {}).get("warnings", []),
        "read_only_guard_safe": prompt42.get("read_only_guard", {}).get("safe", False),
        "safe_draft_ready": prompt42.get("readiness", {}).get("ready", False),
    }
    blockers = list(prompt42.get("precondition", {}).get("blockers", []))
    if not pitch_validation.get("passed"):
        blockers.append("PITCH_BLOCK_VALIDATION_FAILED")
    if not protection.get("safe"):
        blockers.append("ORIGINAL_PROTECTION_FAILED")
    if selection.get("summary", {}).get("eligible_count", 0) == 0:
        if any("PLUGIN_MAPPING_UNSAFE" in item.get("blocked_reason_codes", []) for item in selection.get("blocked_tracks", [])):
            blockers.append("PLUGIN_MAPPING_UNSAFE")
        elif prompt42.get("missing"):
            blockers.append("PROMPT42_OUTPUTS_MISSING")
        else:
            blockers.append("NO_ELIGIBLE_RECOVERY_TRACKS")
    if apply_drafts and not application.get("applied"):
        blockers.extend(application.get("warnings", []))
    write_blocker_report(output, project_name, blockers, prompt42.get("precondition", {}).get("warnings", []) + application.get("warnings", []))
    if blockers:
        if "PROMPT42_OUTPUTS_MISSING" in blockers:
            final_recommendation = "pilot_failed_do_not_continue"
        elif "PLUGIN_MAPPING_UNSAFE" in blockers or "validated_plugin_mapping_required" in blockers:
            final_recommendation = "validate_plugins_first"
        elif any("stem" in str(blocker).lower() or "FULL_MIX" in str(blocker) for blocker in blockers):
            final_recommendation = "provide_better_stems"
        else:
            final_recommendation = "pilot_failed_do_not_continue"
    elif application.get("drafts_created"):
        final_recommendation = "review_recovery_drafts"
    elif selection.get("manual_review_tracks"):
        final_recommendation = "do_not_proceed_to_pitch"
    else:
        final_recommendation = "recovery_not_needed"
    report_path = write_pilot_report(
        output_dir=output,
        project_name=project_name,
        selection=selection,
        chain_plans=chain_plans,
        drafts_created=application.get("drafts_created", []),
        pitch_block=pitch_block,
        ab_plan=ab_plan,
        evaluations=evaluations,
        protection=protection,
        rollback_registry=rollback_registry,
        precondition=precondition_summary,
        render_ab=render_ab,
        final_recommendation=final_recommendation,
    )
    status = "blocked" if blockers else ("drafts_created_review_required" if application.get("drafts_created") else "recovery_only_pilot_complete")
    summary = {
        "schema": "automix-recovery-only-pilot-summary-v1",
        "status": status,
        "project_name": project_name,
        "project_path": str(project) if project_path else "",
        "mode": "recovery_only_pilot",
        "dry_run": effective_dry_run,
        "apply_drafts": apply_drafts,
        "render_ab": render_ab,
        "prompt42_precondition_ok": prompt42.get("precondition", {}).get("ok_for_recovery_only", False),
        "prompt42_blockers": prompt42.get("precondition", {}).get("blockers", []),
        "eligible_recovery_tracks": len(selection.get("eligible_tracks", [])),
        "blocked_tracks": len(selection.get("blocked_tracks", [])),
        "manual_review_tracks": len(selection.get("manual_review_tracks", [])),
        "recovery_drafts_created": len(application.get("drafts_created", [])),
        "pitch_block_status": pitch_block.get("pitch_stage_blocked") and pitch_validation.get("passed"),
        "plugin_safety_status": "safe" if plugin_entry and adapter else "blocked_or_unmapped",
        "ab_render_status": "enabled" if ab_plan.get("render_enabled") else "plan_only",
        "original_protection_safe": protection.get("safe"),
        "rollback_registry_valid": rollback_registry.get("all_entries_valid"),
        "final_recommendation": final_recommendation,
        "reports": {
            "track_selection": str(output / "eval_reports" / "recovery_only_track_selection.json"),
            "pitch_block": str(output / "eval_reports" / "recovery_only_pitch_block_report.json"),
            "parameter_write_log": str(output / "logs" / "recovery_only_parameter_write_log.json"),
            "ab_render_plan": str(output / "eval_reports" / "recovery_only_ab_render_plan.json"),
            "original_protection": str(output / "eval_reports" / "recovery_only_original_protection_report.json"),
            "rollback_registry": str(output / "rollback" / "recovery_only_rollback_registry.json"),
            "pilot_report": str(report_path),
        },
        "warnings": sorted(set(prompt42.get("precondition", {}).get("warnings", []) + application.get("warnings", []))),
        "blockers": sorted(set(blockers)),
    }
    if verbose:
        summary["selection_summary"] = selection.get("summary", {})
        summary["chain_plans"] = [plan.get("path") for plan in chain_plans]
        summary["iteration_histories"] = [item.get("path") for item in histories]
        summary["parameter_write_log_summary"] = {
            "parameters_written": len(parameter_log.get("parameters_written", [])),
            "parameters_skipped": len(parameter_log.get("parameters_skipped", [])),
        }
    write_json(output / "real_project" / "recovery_only_pilot_summary.json", summary)
    return summary

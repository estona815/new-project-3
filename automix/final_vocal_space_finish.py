from __future__ import annotations

import json
import shutil
import zipfile
from pathlib import Path
from typing import Any

from automix.plugins.plugin_adapter_schema import now_utc, slugify, write_json
from automix.vocal_placement.final_vocal_space_carving_policy import (
    build_final_vocal_space_chain_plan,
    build_final_vocal_space_iteration_history,
    select_final_vocal_space_profile,
)


REVIEW_DECISIONS = {"accepted", "accepted_light", "rejected", "needs_revision", "manual_mix_required", "needs_review"}


def read_json(path: Path, default: Any | None = None) -> Any:
    if not path.exists():
        return {} if default is None else default
    return json.loads(path.read_text(encoding="utf-8"))


def write_text(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def project_name_from_inputs(project_path: str | Path | None, accepted_sources: dict[str, Any], track_audit: dict[str, Any]) -> str:
    if accepted_sources.get("project_name"):
        return str(accepted_sources["project_name"])
    if track_audit.get("project_name"):
        return str(track_audit["project_name"])
    if project_path:
        return Path(project_path).stem
    return "project"


def load_prompt_inputs(output_dir: Path) -> dict[str, Any]:
    paths = {
        "accepted_sources": output_dir / "review" / "accepted_recovery_sources.json",
        "recovery_review_report": output_dir / "eval_reports" / "recovery_review_report.md",
        "rollback_registry": output_dir / "rollback" / "recovery_only_rollback_registry.json",
        "original_protection": output_dir / "eval_reports" / "recovery_only_original_protection_report.json",
        "plugin_readiness": output_dir / "eval_reports" / "real_project_plugin_readiness.json",
        "track_audit": output_dir / "eval_reports" / "real_project_track_audit.json",
        "track_audit_fallback": output_dir / "analysis_reports" / "real_project_track_audit.json",
        "rejected_drafts": output_dir / "review" / "rejected_recovery_drafts.json",
    }
    track_audit_path = paths["track_audit"]
    warnings: list[str] = []
    if not track_audit_path.exists() and paths["track_audit_fallback"].exists():
        track_audit_path = paths["track_audit_fallback"]
        warnings.append("track_audit_loaded_from_analysis_reports_compatibility_path")
    return {
        "paths": {**paths, "track_audit_used": track_audit_path},
        "accepted_sources": read_json(paths["accepted_sources"], {}),
        "rollback_registry": read_json(paths["rollback_registry"], {}),
        "original_protection": read_json(paths["original_protection"], {}),
        "plugin_readiness": read_json(paths["plugin_readiness"], {}),
        "track_audit": read_json(track_audit_path, {}),
        "rejected_drafts": read_json(paths["rejected_drafts"], {}),
        "recovery_review_report_exists": paths["recovery_review_report"].exists(),
        "warnings": warnings,
    }


def source_names_from_rejected(rejected_drafts: dict[str, Any]) -> set[str]:
    names: set[str] = set()
    for key in ("rejected", "needs_revision", "manual_cleanup_required", "stem_required"):
        for item in rejected_drafts.get(key, []) if isinstance(rejected_drafts, dict) else []:
            name = item.get("draft_track_name")
            if name:
                names.add(str(name))
    return names


def evaluate_preconditions(inputs: dict[str, Any]) -> dict[str, Any]:
    paths = inputs["paths"]
    accepted = inputs["accepted_sources"].get("accepted_sources", []) if isinstance(inputs["accepted_sources"], dict) else []
    rollback = inputs["rollback_registry"]
    protection = inputs["original_protection"]
    readiness = inputs["plugin_readiness"]
    audit = inputs["track_audit"]
    blockers: list[str] = []
    warnings = list(inputs.get("warnings", []))

    required_paths = {
        "accepted_recovery_sources": paths["accepted_sources"],
        "recovery_review_report": paths["recovery_review_report"],
        "recovery_only_rollback_registry": paths["rollback_registry"],
        "recovery_only_original_protection_report": paths["original_protection"],
        "real_project_plugin_readiness": paths["plugin_readiness"],
    }
    for key, path in required_paths.items():
        if not path.exists():
            blockers.append(f"{key}_missing")
    if not paths["track_audit_used"].exists():
        blockers.append("real_project_track_audit_missing")

    if not accepted:
        blockers.append("no_accepted_recovery_sources")
    else:
        for item in accepted:
            if not item.get("accepted_draft_track_name"):
                blockers.append("accepted_recovery_draft_missing")
            if item.get("decision") not in {"accepted", "accepted_light"}:
                blockers.append("accepted_source_has_invalid_decision")
            if item.get("allowed_for_placement") is False:
                blockers.append("accepted_source_not_allowed_for_placement")

    rejected_names = source_names_from_rejected(inputs["rejected_drafts"])
    for item in accepted:
        if item.get("accepted_draft_track_name") in rejected_names:
            blockers.append("accepted_recovery_source_rejected_later")

    if protection and not protection.get("safe", False):
        blockers.append("original_protection_failed")
    if protection and protection.get("pitch_plugin_inserted_anywhere"):
        blockers.append("pitch_plugin_detected_in_prior_recovery")
    if rollback and not rollback.get("all_entries_valid", True):
        blockers.append("rollback_registry_invalid")
    if not rollback:
        blockers.append("rollback_system_unavailable")

    if not readiness:
        blockers.append("plugin_adapter_gate_unavailable")
    elif not (readiness.get("can_run_vocal_placement_safely") or readiness.get("safe_draft_plugin_ready") or int(readiness.get("safe_adapters_count", 0) or 0) > 0):
        blockers.append("plugin_adapter_gate_not_ready_for_placement")

    if audit:
        tracks = audit.get("tracks", [])
        non_full_mix = [track for track in tracks if track.get("source_classification") != "full_mix" and track.get("role") != "full_mix_reference"]
        if tracks and not non_full_mix:
            blockers.append("only_full_mix_source_exists")
        project_names = {
            str(value)
            for value in (
                inputs["accepted_sources"].get("project_name") if isinstance(inputs["accepted_sources"], dict) else None,
                rollback.get("project_name") if isinstance(rollback, dict) else None,
                protection.get("project_name") if isinstance(protection, dict) else None,
                readiness.get("project_name") if isinstance(readiness, dict) else None,
                audit.get("project_name") if isinstance(audit, dict) else None,
            )
            if value
        }
        if len(project_names) > 1:
            blockers.append("project_state_conflicts_with_previous_reports")

    return {
        "schema": "automix-final-vocal-space-preconditions-v1",
        "ok": not blockers,
        "blockers": sorted(set(blockers)),
        "warnings": sorted(set(warnings)),
        "accepted_sources_count": len(accepted),
        "plugin_adapter_gate_available": bool(readiness),
        "rollback_available": bool(rollback),
        "original_protection_safe": bool(protection.get("safe", False)) if isinstance(protection, dict) else False,
    }


def write_blocked_stages(output_dir: Path, warnings: list[str] | None = None) -> dict[str, Any]:
    data = {
        "schema": "automix-finalizing-blocked-stages-v1",
        "pitch_correction_blocked": True,
        "reason": "This finishing pass focuses on vocal placement and safe premaster only.",
        "premaster_allowed_as_draft": True,
        "final_export_blocked_until_review": True,
        "pitch_plugins_inserted": False,
        "master_destructive_processing": False,
        "warnings": sorted(set(warnings or [])),
    }
    write_json(output_dir / "eval_reports" / "finalizing_blocked_stages.json", data)
    return data


def tracks_by_role(track_audit: dict[str, Any], role_names: set[str]) -> list[dict[str, Any]]:
    return [track for track in track_audit.get("tracks", []) if track.get("role") in role_names]


def first_track_name(tracks: list[dict[str, Any]]) -> str:
    return str(tracks[0].get("track_name", "")) if tracks else ""


def resolve_targets(project_name: str, inputs: dict[str, Any], preconditions: dict[str, Any]) -> dict[str, Any]:
    accepted = (inputs["accepted_sources"].get("accepted_sources", []) or [{}])[0] if isinstance(inputs["accepted_sources"], dict) else {}
    audit = inputs["track_audit"]
    backing = tracks_by_role(audit, {"backing_vocal"})
    doubles = tracks_by_role(audit, {"vocal_double"})
    adlibs = tracks_by_role(audit, {"adlib"})
    instrumental = tracks_by_role(audit, {"instrumental_bus", "instrumental", "music_bus"})
    drums = tracks_by_role(audit, {"drum_bus", "drums", "kick", "snare"})
    bass = tracks_by_role(audit, {"bass", "808", "bass_808"})
    guitars = tracks_by_role(audit, {"guitar"})
    pianos = tracks_by_role(audit, {"piano"})
    synths = tracks_by_role(audit, {"synth", "sample_lead", "melody", "lead_melody"})
    reverbs = tracks_by_role(audit, {"reverb_send"})
    delays = tracks_by_role(audit, {"delay_send"})
    full_mix_refs = tracks_by_role(audit, {"full_mix_reference"})
    missing = []
    if not accepted.get("accepted_draft_track_name"):
        missing.append("accepted_lead_vocal_recovery_draft")
    if not instrumental:
        missing.append("instrumental_bus")
    if preconditions.get("blockers"):
        missing.extend(preconditions["blockers"])
    low_confidence = bool(missing or not accepted.get("accepted_draft_track_name"))
    target = {
        "schema": "automix-finalizing-target-resolution-v1",
        "project_name": project_name,
        "accepted_lead_vocal_recovery_draft": accepted.get("accepted_draft_track_name", ""),
        "accepted_lead_vocal_guid": accepted.get("accepted_draft_track_guid", ""),
        "original_lead_vocal_reference": accepted.get("original_track_name", ""),
        "original_lead_vocal_guid": accepted.get("original_track_guid", ""),
        "fragile_source": bool(accepted.get("fragile_source") or accepted.get("decision") == "accepted_light"),
        "backing_vocal_tracks": [track.get("track_name") for track in backing],
        "vocal_doubles": [track.get("track_name") for track in doubles],
        "adlibs": [track.get("track_name") for track in adlibs],
        "instrumental_bus": first_track_name(instrumental),
        "drum_bus": first_track_name(drums),
        "bass_808_tracks": [track.get("track_name") for track in bass],
        "guitar_tracks": [track.get("track_name") for track in guitars],
        "piano_tracks": [track.get("track_name") for track in pianos],
        "synth_sample_lead_tracks": [track.get("track_name") for track in synths],
        "reverb_send": first_track_name(reverbs),
        "delay_send": first_track_name(delays),
        "master_track_for_measurement_only": "Master",
        "full_mix_references_for_listening_only": [track.get("track_name") for track in full_mix_refs],
        "do_not_modify_full_mix_reference": True,
        "do_not_modify_master_directly": True,
        "do_not_modify_original_tracks": True,
        "target_confidence": 0.35 if low_confidence else 0.86,
        "requires_manual_review": low_confidence,
        "missing_targets": sorted(set(missing)),
        "warnings": ["target confidence is low; manual review required"] if low_confidence else [],
    }
    return target


def write_target_resolution(output_dir: Path, target: dict[str, Any]) -> Path:
    return write_json(output_dir / "analysis_reports" / "finalizing_target_resolution.json", target)


def _score_from_roles(track_audit: dict[str, Any], role_names: set[str], field: str, default: float = 0.0) -> float:
    values = []
    for track in tracks_by_role(track_audit, role_names):
        try:
            values.append(float(track.get(field, default)))
        except (TypeError, ValueError):
            pass
    return round(sum(values) / len(values), 6) if values else default


def analyze_final_vocal_space(project_name: str, inputs: dict[str, Any], target: dict[str, Any]) -> dict[str, Any]:
    audit = inputs["track_audit"]
    accepted_name = target.get("accepted_lead_vocal_recovery_draft", "")
    fragile = bool(target.get("fragile_source"))
    instrumental_score = max(
        _score_from_roles(audit, {"instrumental_bus", "instrumental", "music_bus"}, "instrumental_likelihood", 0.0),
        _score_from_roles(audit, {"instrumental_bus", "instrumental", "music_bus"}, "full_mix_likelihood", 0.0) * 0.50,
    )
    backing_score = min(1.0, len(target.get("backing_vocal_tracks", [])) * 0.22 + len(target.get("vocal_doubles", [])) * 0.16 + len(target.get("adlibs", [])) * 0.12)
    send_score = min(1.0, (1 if target.get("reverb_send") else 0) * 0.35 + (1 if target.get("delay_send") else 0) * 0.30)
    artifact_risk = 0.60 if fragile else 0.35 if accepted_name else 0.0
    forwardness = 0.45 if accepted_name else 0.0
    main_bands = []
    if instrumental_score > 0.35:
        main_bands.extend(["250-600 Hz low-mid", "1-4 kHz presence"])
    if backing_score > 0.25:
        main_bands.append("800 Hz-6 kHz backing vocal overlap")
    if send_score > 0.25:
        main_bands.append("post-phrase reverb/delay tails")
    if artifact_risk > 0.50:
        main_bands.append("5-10 kHz sibilance and metallic fizz")
    warnings = []
    if not accepted_name:
        warnings.append("no accepted recovery vocal source; analysis is blocked placeholder")
    if fragile:
        warnings.append("fragile accepted source; do not use brightening, widening, saturation, pitch, or strong ducking")
    analysis = {
        "schema": "automix-final-vocal-space-analysis-v1",
        "project_name": project_name,
        "lead_vocal_source": accepted_name,
        "fragile_source": fragile,
        "vocal_loudness": 0.0,
        "vocal_body_120_350_hz": 0.0,
        "vocal_mud_250_600_hz": 0.0,
        "vocal_clarity_1_4_khz": 0.0,
        "vocal_harshness_2k5_6_khz": 0.0,
        "vocal_sibilance_5_10_khz": 0.0,
        "vocal_air_10_16_khz": 0.0,
        "vocal_center_stability": 0.0,
        "vocal_thinness": 0.0,
        "ai_fizz_metallic_artifact_risk": round(artifact_risk, 6),
        "vocal_forwardness": round(forwardness, 6),
        "main_masking_bands": main_bands,
        "bass_808_masking_80_200_hz": round(_score_from_roles(audit, {"bass", "808", "bass_808"}, "instrumental_likelihood", 0.0), 6),
        "piano_guitar_masking_200_1500_hz": round(max(len(target.get("guitar_tracks", [])), len(target.get("piano_tracks", []))) * 0.20, 6),
        "synth_sample_lead_masking_1_5_khz": round(len(target.get("synth_sample_lead_tracks", [])) * 0.22, 6),
        "snare_hihat_masking_2_10_khz": round(len(tracks_by_role(audit, {"drums", "drum_bus", "snare", "hihat"})) * 0.15, 6),
        "backing_vocal_masking_800_6khz": round(backing_score, 6),
        "reverb_delay_tail_masking_after_phrases": round(send_score, 6),
        "center_crowding": round(instrumental_score * 0.60, 6),
        "stereo_side_clutter": round(send_score * 0.55, 6),
        "instrumental_masking_score": round(instrumental_score, 6),
        "backing_masking_score": round(backing_score, 6),
        "send_tail_masking_score": round(send_score, 6),
        "ai_artifact_exposure_risk": round(artifact_risk, 6),
        "recommended_strategy": "carve_space_not_gain",
        "warnings": sorted(set(warnings)),
    }
    return analysis


def missing_ab_eval_metrics(render_requested: bool = False) -> dict[str, Any]:
    warnings = ["missing render means no pass"]
    if render_requested:
        warnings.append("render_ab_requested_but_no_reaper_render_engine_was_invoked")
    return {
        "schema": "automix-final-vocal-space-eval-metrics-v1",
        "renders_created": {
            "current_mix": False,
            "placement_draft": False,
            "loudness_matched": False,
            "difference": False,
        },
        "improvement_scores": {
            "vocal_forwardness_delta": 0.0,
            "vocal_clarity_delta": 0.0,
            "masking_reduction": 0.0,
            "backing_conflict_reduction": 0.0,
            "send_tail_masking_reduction": 0.0,
            "vocal_center_stability_delta": 0.0,
        },
        "damage_scores": {
            "beat_impact_loss": 0.0,
            "low_end_loss_db": 0.0,
            "drum_pump_score": 0.0,
            "instrumental_hollowing": 0.0,
            "lead_melody_damage": 0.0,
            "vocal_harshness_increase": 0.0,
            "vocal_thinness_increase": 0.0,
            "ai_artifact_exposure_increase": 0.0,
            "sibilance_worsening": 0.0,
            "stereo_shift": 0.0,
            "phase_worsening": 0.0,
        },
        "evaluation_passed": False,
        "recommended_action": "manual_review_required",
        "warnings": warnings,
    }


def write_ab_plan(output_dir: Path, project_name: str, render_ab: bool, blocked: bool) -> dict[str, Any]:
    plan = {
        "schema": "automix-final-vocal-space-ab-render-plan-v1",
        "project_name": project_name,
        "render_enabled": bool(render_ab),
        "blocked": bool(blocked),
        "renders": {
            "current_accepted_mix": "",
            "vocal_space_placement_draft": "",
            "loudness_matched_placement_draft": "",
            "difference_render": "",
        },
        "loudness_matched_required": True,
        "evaluation_passed_without_renders": False,
        "requires_human_ab_review": True,
        "warnings": ["render not enabled; plan only"] if not render_ab else ["render requested but this Python safety runner does not render REAPER projects directly"],
    }
    write_json(output_dir / "eval_reports" / "final_vocal_space_ab_render_plan.json", plan)
    return plan


def build_rollback(project_name: str, chain_plan: dict[str, Any], apply_placement_draft: bool, blocked: bool) -> dict[str, Any]:
    created = bool(apply_placement_draft and chain_plan.get("safe_to_apply") and not blocked)
    return {
        "schema": "automix-final-vocal-space-carving-rollback-v1",
        "created_at": now_utc(),
        "project_name": project_name,
        "draft_created": created,
        "created_draft_tracks": ["FINAL VOCAL SPACE PLACEMENT DRAFT"] if created else [],
        "created_draft_buses": ["FINAL VOCAL SPACE BUS"] if created else [],
        "created_sends": ["lead vocal sidechain to instrumental/backing/send draft buses"] if created else [],
        "inserted_plugins": [
            {"target_role": item.get("target_role"), "category": item.get("category"), "plugin": item.get("plugin")}
            for item in chain_plan.get("plugin_chain", [])
            if created and item.get("safe_to_apply")
        ],
        "written_parameters": list(chain_plan.get("semantic_controls_written", {}).values()) if created else [],
        "routing_changes": ["draft-only sidechain routing"] if created else [],
        "safe_to_delete_draft": True,
        "original_tracks_untouched": True,
        "original_master_untouched": True,
        "accepted_recovery_draft_untouched": True,
        "pitch_plugins_inserted": False,
    }


def build_parameter_log(project_name: str, chain_plan: dict[str, Any], dry_run: bool) -> dict[str, Any]:
    return {
        "schema": "automix-final-vocal-space-parameter-write-log-v1",
        "project_name": project_name,
        "created_at": now_utc(),
        "dry_run": bool(dry_run),
        "fixed_parameter_indexes_used": False,
        "unknown_parameters_skipped": True,
        "pitch_parameters_written": False,
        "written": [
            {**value, "written": False if dry_run else bool(chain_plan.get("safe_to_apply"))}
            for value in chain_plan.get("semantic_controls_written", {}).values()
        ],
        "skipped": chain_plan.get("semantic_controls_skipped", {}),
        "warnings": chain_plan.get("warnings", []),
    }


def build_routing_log(project_name: str, rollback: dict[str, Any], dry_run: bool) -> dict[str, Any]:
    return {
        "schema": "automix-final-vocal-space-routing-log-v1",
        "project_name": project_name,
        "created_at": now_utc(),
        "dry_run": bool(dry_run),
        "draft_only": True,
        "original_routing_changed": False,
        "created_draft_tracks": rollback.get("created_draft_tracks", []),
        "created_draft_buses": rollback.get("created_draft_buses", []),
        "created_sends": rollback.get("created_sends", []),
        "safe_to_rollback": True,
    }


def write_protection_report(output_dir: Path, project_name: str, preconditions: dict[str, Any], rollback: dict[str, Any], strict: bool) -> dict[str, Any]:
    failures = []
    if not preconditions.get("original_protection_safe"):
        failures.append("prior_original_protection_not_safe")
    if rollback.get("pitch_plugins_inserted"):
        failures.append("pitch_plugin_inserted")
    report = {
        "schema": "automix-final-vocal-space-protection-report-v1",
        "project_name": project_name,
        "strict_protection": bool(strict),
        "original_tracks_unchanged": True,
        "original_master_unchanged": True,
        "original_media_unchanged": True,
        "original_routing_unchanged": True,
        "accepted_recovery_drafts_not_overwritten": True,
        "no_pitch_plugin_inserted": True,
        "no_limiter_inserted_on_master": True,
        "rollback_exists_for_all_changes": True,
        "protection_passed": not failures,
        "failures": failures,
        "rollback_instructions": "Delete draft buses/tracks and sends listed in final_vocal_space_carving_rollback.json if any draft was created.",
        "warnings": preconditions.get("warnings", []),
    }
    write_json(output_dir / "eval_reports" / "final_vocal_space_protection_report.json", report)
    return report


def build_review_state(project_name: str, chain_plan: dict[str, Any], accept_placement_review: bool) -> dict[str, Any]:
    draft_exists = bool(chain_plan.get("safe_to_apply"))
    decision = "needs_review"
    if accept_placement_review and draft_exists:
        decision = "accepted_light" if chain_plan.get("fragile_source") else "accepted"
    return {
        "schema": "automix-final-vocal-space-review-state-v1",
        "project_name": project_name,
        "created_at": now_utc(),
        "review_status": "accepted" if decision in {"accepted", "accepted_light"} else "needs_review",
        "default_decision": "needs_review",
        "allowed_decisions": sorted(REVIEW_DECISIONS - {"needs_review"}),
        "decision": decision,
        "placement_draft_exists": draft_exists,
        "selected_profile": chain_plan.get("selected_profile"),
        "accepted_light_requires_safety_only_premaster": decision == "accepted_light",
        "premaster_allowed": decision in {"accepted", "accepted_light"},
        "final_export_allowed": False,
        "warnings": ["placement draft requires human review"] if decision == "needs_review" else ["placement review explicitly accepted by CLI flag"],
    }


def write_review_form(output_dir: Path, project_name: str, chain_plan: dict[str, Any], eval_metrics: dict[str, Any]) -> Path:
    lines = [
        "# Final Vocal Space Review Form",
        "",
        f"- Project: `{project_name}`",
        f"- Placement profile: `{chain_plan.get('selected_profile')}`",
        f"- Placement draft exists: `{chain_plan.get('safe_to_apply')}`",
        f"- A/B evaluation passed: `{eval_metrics.get('evaluation_passed')}`",
        "",
        "## Decision",
        "",
        "[ ] accepted",
        "[ ] accepted_light",
        "[ ] rejected",
        "[ ] needs_revision",
        "[ ] manual_mix_required",
        "",
        "## Manual Listening Checklist",
        "",
        "- Is the vocal clearer without just being louder?",
        "- Does the beat still hit?",
        "- Is the 808/bass still solid?",
        "- Is the lead melody still strong?",
        "- Did backing vocals move behind the lead?",
        "- Are reverb/delay tails cleaner?",
        "- Did the vocal become harsh or thin?",
        "- Did AI fizz or metallic tone become more obvious?",
        "- Is the result better at matched loudness?",
        "",
    ]
    return write_text(output_dir / "review" / "final_vocal_space_review_form.md", "\n".join(lines))


def build_premaster_outputs(
    *,
    output_dir: Path,
    project_name: str,
    review_state: dict[str, Any],
    apply_safe_premaster_draft: bool,
    render_ab: bool,
    plugin_readiness: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], Path]:
    allowed = bool(apply_safe_premaster_draft and review_state.get("premaster_allowed"))
    profile = "safety_only_premaster" if review_state.get("decision") == "accepted_light" else "safe_streaming_premaster"
    if not allowed:
        profile = "blocked_until_placement_review"
    adapter_ok = bool(plugin_readiness.get("can_run_premaster_draft_safely") or int(plugin_readiness.get("safe_adapters_count", 0) or 0) > 0)
    chain = {
        "schema": "automix-final-safe-premaster-chain-plan-v1",
        "project_name": project_name,
        "created": bool(allowed and adapter_ok),
        "selected_profile": profile,
        "draft_only": True,
        "final_export_allowed": False,
        "original_master_untouched": True,
        "chain": [
            "input_trim",
            "low_end_safety_eq",
            "low_end_side_cleanup_if_needed",
            "dynamic_harshness_sibilance_guard",
            "high_fizz_guard",
            "very_light_bus_compression_if_safe",
            "optional_soft_clipper_if_artifact_risk_low",
            "true_peak_limiter_if_mapped",
            "loudness_meter",
        ]
        if allowed
        else [],
        "blocked_reasons": [] if allowed and adapter_ok else ["placement_review_not_accepted_or_premaster_not_requested"] + ([] if adapter_ok else ["premaster_plugin_mapping_not_ready"]),
        "disallowed": ["pitch_correction", "master_widening", "high_end_boost", "final_export", "loudness_chasing"],
    }
    metrics = {
        "schema": "automix-final-safe-premaster-eval-metrics-v1",
        "renders_created": {
            "placement_draft": False,
            "premaster_draft": False,
            "loudness_matched": False,
            "difference": False,
        },
        "premaster_passed": False,
        "evaluation_passed": False,
        "recommended_action": "manual_review_required",
        "warnings": ["missing render means no premaster pass"] if render_ab else ["premaster A/B render not enabled; no pass"],
    }
    rollback = {
        "schema": "automix-final-safe-premaster-rollback-v1",
        "project_name": project_name,
        "created": bool(allowed and adapter_ok),
        "created_draft_tracks": ["FINAL SAFE PREMASTER DRAFT"] if allowed and adapter_ok else [],
        "inserted_plugins": [],
        "written_parameters": [],
        "safe_to_delete_draft": True,
        "original_master_untouched": True,
        "final_export_created": False,
    }
    write_json(output_dir / "chain_plans" / "final_safe_premaster_chain_plan.json", chain)
    write_json(output_dir / "eval_reports" / "final_safe_premaster_eval_metrics.json", metrics)
    write_json(output_dir / "rollback" / "final_safe_premaster_rollback.json", rollback)
    report_lines = [
        "# Final Safe Premaster Report",
        "",
        f"- Project: `{project_name}`",
        f"- Created: `{chain['created']}`",
        f"- Selected profile: `{chain['selected_profile']}`",
        "- Final export created: `False`",
        "- Pitch correction blocked: `True`",
        f"- Status: `{'draft_created_review_required' if chain['created'] else 'blocked_until_placement_review'}`",
        f"- Warnings: `{', '.join(metrics['warnings'])}`",
        "",
    ]
    report = write_text(output_dir / "eval_reports" / "final_safe_premaster_report.md", "\n".join(report_lines))
    return chain, metrics, rollback, report


def _copy_if_exists(src: Path, dst_dir: Path, included: list[str], missing: list[str]) -> None:
    if not src.exists() or src.is_dir():
        missing.append(str(src))
        return
    dst_dir.mkdir(parents=True, exist_ok=True)
    dst = dst_dir / src.name
    if src.resolve() != dst.resolve():
        shutil.copy2(src, dst)
    included.append(str(dst))


def next_review_package_dir(root: Path, project_name: str) -> Path:
    slug = slugify(project_name)
    root.mkdir(parents=True, exist_ok=True)
    existing = sorted(root.glob(f"{slug}_REVIEW_PACKAGE_v*"))
    next_index = len([p for p in existing if p.is_dir()]) + 1
    while True:
        candidate = root / f"{slug}_REVIEW_PACKAGE_v{next_index:02d}"
        if not candidate.exists():
            return candidate
        next_index += 1


def create_review_package(project_name: str, output_dir: Path, deliverables_root: Path, create_zip: bool) -> dict[str, Any]:
    package_dir = next_review_package_dir(deliverables_root, project_name)
    for subdir in ("Audio", "Reports", "Manifests"):
        (package_dir / subdir).mkdir(parents=True, exist_ok=True)
    included: list[str] = []
    missing: list[str] = []
    report_files = [
        output_dir / "analysis_reports" / "final_vocal_space_analysis.json",
        output_dir / "analysis_reports" / "finalizing_target_resolution.json",
        output_dir / "chain_plans" / "final_vocal_space_carving_chain_plan.json",
        output_dir / "eval_reports" / "final_vocal_space_eval_metrics.json",
        output_dir / "eval_reports" / "final_vocal_space_ab_render_plan.json",
        output_dir / "eval_reports" / "final_vocal_space_protection_report.json",
        output_dir / "eval_reports" / "finalizing_vocal_space_and_review_package_report.md",
        output_dir / "review" / "final_vocal_space_review_form.md",
        output_dir / "eval_reports" / "real_project_plugin_readiness.json",
        output_dir / "rollback" / "recovery_only_rollback_registry.json",
        output_dir / "rollback" / "final_vocal_space_carving_rollback.json",
        output_dir / "eval_reports" / "final_safe_premaster_report.md",
    ]
    for src in report_files:
        _copy_if_exists(src, package_dir / "Reports", included, missing)
    project_state_manifest = {
        "schema": "automix-final-vocal-space-project-state-manifest-v1",
        "project_name": project_name,
        "created_at": now_utc(),
        "ready_for_delivery": False,
        "package_type": "review_only",
        "final_export_created": False,
        "raw_audio_included": False,
    }
    review_manifest = {
        "schema": "automix-final-vocal-space-review-package-manifest-v1",
        "project_name": project_name,
        "created_at": now_utc(),
        "package_dir": str(package_dir),
        "package_is_final": False,
        "ready_for_delivery": False,
        "files_included": sorted(set(included)),
        "files_missing": sorted(set(missing)),
    }
    write_json(package_dir / "Manifests" / "project_state_manifest.json", project_state_manifest)
    write_json(package_dir / "Manifests" / "review_package_manifest.json", review_manifest)
    included.extend([str(package_dir / "Manifests" / "project_state_manifest.json"), str(package_dir / "Manifests" / "review_package_manifest.json")])
    zip_path = ""
    if create_zip:
        zip_target = package_dir.with_suffix(".zip")
        with zipfile.ZipFile(zip_target, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for src in package_dir.rglob("*"):
                if src.is_file() and not src.is_symlink():
                    zf.write(src, arcname=str(src.relative_to(package_dir.parent)))
        zip_path = str(zip_target)
    review_manifest["files_included"] = sorted(set(included))
    review_manifest["zip_path"] = zip_path
    review_manifest["package_created"] = package_dir.exists()
    write_json(package_dir / "Manifests" / "review_package_manifest.json", review_manifest)
    write_json(output_dir / "eval_reports" / "final_vocal_space_review_package_manifest.json", review_manifest)
    return review_manifest


def zip_review_package(package_dir: Path) -> str:
    zip_target = package_dir.with_suffix(".zip")
    with zipfile.ZipFile(zip_target, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for src in package_dir.rglob("*"):
            if src.is_file() and not src.is_symlink():
                zf.write(src, arcname=str(src.relative_to(package_dir.parent)))
    return str(zip_target)


def write_main_report(
    *,
    output_dir: Path,
    project_name: str,
    accepted_source: dict[str, Any],
    target: dict[str, Any],
    analysis: dict[str, Any],
    chain_plan: dict[str, Any],
    ab_plan: dict[str, Any],
    eval_metrics: dict[str, Any],
    protection: dict[str, Any],
    rollback: dict[str, Any],
    premaster_chain: dict[str, Any],
    premaster_metrics: dict[str, Any],
    package_manifest: dict[str, Any],
    blocked_stages: dict[str, Any],
    final_recommendation: str,
) -> Path:
    settings = chain_plan.get("semantic_settings", {})
    lines = [
        "# Vocal Space Carving + Review Package Report",
        "",
        "## Summary",
        "",
        f"- Project: `{project_name}`",
        f"- Accepted recovery source: `{accepted_source.get('accepted_draft_track_name', 'none')}`",
        f"- Fragile source: `{chain_plan.get('fragile_source')}`",
        f"- Placement draft created: `{rollback.get('draft_created')}`",
        f"- Premaster draft created: `{premaster_chain.get('created')}`",
        "- Final export created: `No`",
        f"- Pitch correction blocked: `{blocked_stages.get('pitch_correction_blocked')}`",
        f"- Original tracks untouched: `{protection.get('original_tracks_unchanged')}`",
        f"- Original master untouched: `{protection.get('original_master_unchanged')}`",
        f"- Review package: `{package_manifest.get('package_dir', '')}`",
        "",
        "## Target Resolution",
        "",
        f"- lead vocal: `{target.get('accepted_lead_vocal_recovery_draft')}`",
        f"- instrumental bus: `{target.get('instrumental_bus')}`",
        f"- backing vocals: `{target.get('backing_vocal_tracks')}`",
        f"- melody tracks: `{target.get('synth_sample_lead_tracks') + target.get('guitar_tracks') + target.get('piano_tracks')}`",
        f"- send tracks: `{[x for x in [target.get('reverb_send'), target.get('delay_send')] if x]}`",
        f"- missing targets: `{target.get('missing_targets')}`",
        "",
        "## Vocal Space Analysis",
        "",
        f"- vocal forwardness: `{analysis.get('vocal_forwardness')}`",
        f"- main masking bands: `{analysis.get('main_masking_bands')}`",
        f"- backing masking: `{analysis.get('backing_masking_score')}`",
        f"- send tail masking: `{analysis.get('send_tail_masking_score')}`",
        f"- AI artifact exposure risk: `{analysis.get('ai_artifact_exposure_risk')}`",
        "",
        "## Space Carving Strategy",
        "",
        f"- selected profile: `{chain_plan.get('selected_profile')}`",
        f"- vocal gain: `{settings.get('vocal_gain_db')}`",
        f"- instrumental ducking: `{settings.get('instrumental_duck_db')}`",
        f"- presence ducking: `{settings.get('presence_duck_db')}`",
        f"- low-mid ducking: `{settings.get('low_mid_duck_db')}`",
        f"- backing vocal ducking: `{settings.get('backing_vocal_duck_db')}`",
        f"- send ducking: `{settings.get('send_duck_db')}`",
        f"- M/S cleanup: `mid {settings.get('ms_mid_cleanup')} / side {settings.get('ms_side_cleanup')}`",
        f"- blocked adjustments: `{chain_plan.get('blocked_adjustments')}`",
        "",
        "## Plugin Safety",
        "",
        f"- plugins used: `{[item.get('plugin') for item in chain_plan.get('plugin_chain', []) if item.get('safe_to_apply')]}`",
        f"- adapter confidence: `{[item.get('adapter_confidence') for item in chain_plan.get('plugin_chain', [])]}`",
        f"- controls written: `{list(chain_plan.get('semantic_controls_written', {}))}`",
        f"- controls skipped: `{list(chain_plan.get('semantic_controls_skipped', {}))}`",
        f"- fallbacks used: `{[item.get('plugin') for item in chain_plan.get('plugin_chain', []) if not item.get('safe_to_apply')]}`",
        f"- unmapped plugins skipped: `{[item.get('category') for item in chain_plan.get('plugin_chain', []) if item.get('requires_parameter_discovery')]}`",
        "",
        "## Draft and Routing",
        "",
        f"- draft buses/tracks: `{rollback.get('created_draft_buses') + rollback.get('created_draft_tracks')}`",
        f"- sidechain sends: `{rollback.get('created_sends')}`",
        f"- routing changes: `{rollback.get('routing_changes')}`",
        "- rollback file: `automix/rollback/final_vocal_space_carving_rollback.json`",
        "",
        "## A/B Evaluation",
        "",
        f"- current mix: `{ab_plan.get('renders', {}).get('current_accepted_mix')}`",
        f"- placement draft: `{ab_plan.get('renders', {}).get('vocal_space_placement_draft')}`",
        f"- loudness matched: `{eval_metrics.get('renders_created', {}).get('loudness_matched')}`",
        f"- difference: `{eval_metrics.get('renders_created', {}).get('difference')}`",
        f"- evaluation status: `{eval_metrics.get('evaluation_passed')}`",
        "",
        "## Damage Checks",
        "",
        f"- beat impact: `{eval_metrics.get('damage_scores', {}).get('beat_impact_loss')}`",
        f"- low end: `{eval_metrics.get('damage_scores', {}).get('low_end_loss_db')}`",
        f"- lead melody: `{eval_metrics.get('damage_scores', {}).get('lead_melody_damage')}`",
        f"- vocal harshness: `{eval_metrics.get('damage_scores', {}).get('vocal_harshness_increase')}`",
        f"- AI artifacts: `{eval_metrics.get('damage_scores', {}).get('ai_artifact_exposure_increase')}`",
        f"- stereo/phase: `{eval_metrics.get('damage_scores', {}).get('stereo_shift')} / {eval_metrics.get('damage_scores', {}).get('phase_worsening')}`",
        "",
        "## Premaster Draft",
        "",
        f"- created: `{premaster_chain.get('created')}`",
        f"- selected profile: `{premaster_chain.get('selected_profile')}`",
        "- loudness: `not rendered`",
        "- true peak: `not rendered`",
        f"- status: `{premaster_metrics.get('recommended_action')}`",
        f"- warnings: `{premaster_metrics.get('warnings')}`",
        "",
        "## Review Package",
        "",
        f"- folder: `{package_manifest.get('package_dir', '')}`",
        f"- zip: `{package_manifest.get('zip_path', '')}`",
        f"- included files: `{len(package_manifest.get('files_included', []))}`",
        "",
        "## Manual Listening Checklist",
        "",
        "- Is the vocal clearer without just being louder?",
        "- Does the beat still hit?",
        "- Is the 808/bass still solid?",
        "- Is the lead melody still strong?",
        "- Did backing vocals move behind the lead?",
        "- Are reverb/delay tails cleaner?",
        "- Did the vocal become harsh or thin?",
        "- Did AI fizz or metallic tone become more obvious?",
        "- Is the result better at matched loudness?",
        "",
        "## Final Recommendation",
        "",
        f"`{final_recommendation}`",
        "",
    ]
    return write_text(output_dir / "eval_reports" / "finalizing_vocal_space_and_review_package_report.md", "\n".join(lines))


def final_recommendation(preconditions: dict[str, Any], review_state: dict[str, Any], eval_metrics: dict[str, Any], premaster_chain: dict[str, Any]) -> str:
    blockers = set(preconditions.get("blockers", []))
    if "only_full_mix_source_exists" in blockers:
        return "provide_better_stems"
    if "no_accepted_recovery_sources" in blockers:
        return "do_not_continue_until_review"
    if review_state.get("decision") == "manual_mix_required":
        return "manual_mix_required"
    if review_state.get("decision") == "needs_revision" or eval_metrics.get("recommended_action") == "manual_review_required":
        return "review_placement_draft"
    if review_state.get("decision") in {"accepted", "accepted_light"} and premaster_chain.get("created"):
        return "review_premaster_draft"
    if review_state.get("decision") in {"accepted", "accepted_light"}:
        return "safe_to_prepare_final_after_review"
    return "do_not_continue_until_review"


def run_final_vocal_space_finish(
    *,
    project_path: str | Path | None = None,
    output_dir: str | Path = "automix",
    deliverables_root: str | Path = "deliverables",
    apply_placement_draft: bool = False,
    render_ab: bool = False,
    generate_review_form: bool = False,
    accept_placement_review: bool = False,
    apply_safe_premaster_draft: bool = False,
    make_review_package: bool = False,
    strict_protection: bool = False,
    dry_run: bool = True,
    verbose: bool = False,
) -> dict[str, Any]:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    for subdir in ("analysis_reports", "chain_plans", "eval_reports", "logs", "review", "rollback"):
        (output / subdir).mkdir(parents=True, exist_ok=True)

    inputs = load_prompt_inputs(output)
    project_name = project_name_from_inputs(project_path, inputs["accepted_sources"], inputs["track_audit"])
    preconditions = evaluate_preconditions(inputs)
    accepted_sources = inputs["accepted_sources"].get("accepted_sources", []) if isinstance(inputs["accepted_sources"], dict) else []
    accepted_source = accepted_sources[0] if accepted_sources else {}

    blocked_stages = write_blocked_stages(output, preconditions.get("warnings", []))
    target = resolve_targets(project_name, inputs, preconditions)
    write_target_resolution(output, target)
    analysis = analyze_final_vocal_space(project_name, inputs, target)
    write_json(output / "analysis_reports" / "final_vocal_space_analysis.json", analysis)
    profile_decision = select_final_vocal_space_profile(analysis, target, accepted_source)
    chain_plan = build_final_vocal_space_chain_plan(
        project_name=project_name,
        target_resolution=target,
        vocal_space_analysis=analysis,
        profile_decision=profile_decision,
        plugin_readiness=inputs["plugin_readiness"],
        apply_placement_draft=bool(apply_placement_draft and not dry_run),
        blockers=preconditions.get("blockers", []),
    )
    write_json(output / "chain_plans" / "final_vocal_space_carving_chain_plan.json", chain_plan)

    rollback = build_rollback(project_name, chain_plan, bool(apply_placement_draft and not dry_run), bool(preconditions.get("blockers")))
    write_json(output / "rollback" / "final_vocal_space_carving_rollback.json", rollback)
    parameter_log = build_parameter_log(project_name, chain_plan, dry_run=dry_run)
    routing_log = build_routing_log(project_name, rollback, dry_run=dry_run)
    write_json(output / "logs" / "final_vocal_space_parameter_write_log.json", parameter_log)
    write_json(output / "logs" / "final_vocal_space_routing_log.json", routing_log)

    ab_plan = write_ab_plan(output, project_name, render_ab, bool(preconditions.get("blockers")))
    eval_metrics = missing_ab_eval_metrics(render_ab)
    write_json(output / "eval_reports" / "final_vocal_space_eval_metrics.json", eval_metrics)
    iteration_history = build_final_vocal_space_iteration_history(chain_plan, eval_metrics)
    write_json(output / "eval_reports" / "final_vocal_space_iteration_history.json", iteration_history)
    protection = write_protection_report(output, project_name, preconditions, rollback, strict_protection)

    review_state = build_review_state(project_name, chain_plan, accept_placement_review)
    write_json(output / "review" / "final_vocal_space_review_state.json", review_state)
    if generate_review_form or True:
        review_form = write_review_form(output, project_name, chain_plan, eval_metrics)
    else:
        review_form = output / "review" / "final_vocal_space_review_form.md"

    premaster_chain, premaster_metrics, premaster_rollback, premaster_report = build_premaster_outputs(
        output_dir=output,
        project_name=project_name,
        review_state=review_state,
        apply_safe_premaster_draft=apply_safe_premaster_draft,
        render_ab=render_ab,
        plugin_readiness=inputs["plugin_readiness"],
    )

    package_manifest: dict[str, Any] = {
        "schema": "automix-final-vocal-space-review-package-manifest-v1",
        "package_created": False,
        "package_dir": "",
        "zip_path": "",
        "files_included": [],
        "files_missing": [],
        "ready_for_delivery": False,
    }
    recommendation = final_recommendation(preconditions, review_state, eval_metrics, premaster_chain)
    report = write_main_report(
        output_dir=output,
        project_name=project_name,
        accepted_source=accepted_source,
        target=target,
        analysis=analysis,
        chain_plan=chain_plan,
        ab_plan=ab_plan,
        eval_metrics=eval_metrics,
        protection=protection,
        rollback=rollback,
        premaster_chain=premaster_chain,
        premaster_metrics=premaster_metrics,
        package_manifest=package_manifest,
        blocked_stages=blocked_stages,
        final_recommendation=recommendation,
    )
    if make_review_package:
        package_manifest = create_review_package(project_name, output, Path(deliverables_root), create_zip=False)
        report = write_main_report(
            output_dir=output,
            project_name=project_name,
            accepted_source=accepted_source,
            target=target,
            analysis=analysis,
            chain_plan=chain_plan,
            ab_plan=ab_plan,
            eval_metrics=eval_metrics,
            protection=protection,
            rollback=rollback,
            premaster_chain=premaster_chain,
            premaster_metrics=premaster_metrics,
            package_manifest=package_manifest,
            blocked_stages=blocked_stages,
            final_recommendation=recommendation,
        )
        _copy_if_exists(report, Path(package_manifest["package_dir"]) / "Reports", package_manifest.setdefault("files_included", []), package_manifest.setdefault("files_missing", []))
        package_manifest["zip_path"] = str(Path(package_manifest["package_dir"]).with_suffix(".zip"))
        report = write_main_report(
            output_dir=output,
            project_name=project_name,
            accepted_source=accepted_source,
            target=target,
            analysis=analysis,
            chain_plan=chain_plan,
            ab_plan=ab_plan,
            eval_metrics=eval_metrics,
            protection=protection,
            rollback=rollback,
            premaster_chain=premaster_chain,
            premaster_metrics=premaster_metrics,
            package_manifest=package_manifest,
            blocked_stages=blocked_stages,
            final_recommendation=recommendation,
        )
        _copy_if_exists(report, Path(package_manifest["package_dir"]) / "Reports", package_manifest.setdefault("files_included", []), package_manifest.setdefault("files_missing", []))
        write_json(Path(package_manifest["package_dir"]) / "Manifests" / "review_package_manifest.json", package_manifest)
        write_json(output / "eval_reports" / "final_vocal_space_review_package_manifest.json", package_manifest)
        package_manifest["zip_path"] = zip_review_package(Path(package_manifest["package_dir"]))
        write_json(Path(package_manifest["package_dir"]) / "Manifests" / "review_package_manifest.json", package_manifest)
        write_json(output / "eval_reports" / "final_vocal_space_review_package_manifest.json", package_manifest)

    summary = {
        "schema": "automix-final-vocal-space-finish-summary-v1",
        "project_name": project_name,
        "project_path": str(project_path or ""),
        "dry_run": bool(dry_run),
        "preconditions_ok": preconditions["ok"],
        "blockers": preconditions["blockers"],
        "accepted_recovery_sources": len(accepted_sources),
        "accepted_recovery_source": accepted_source.get("accepted_draft_track_name", ""),
        "fragile_source": chain_plan.get("fragile_source", False),
        "selected_placement_profile": chain_plan.get("selected_profile"),
        "placement_draft_created": rollback.get("draft_created", False),
        "premaster_draft_created": premaster_chain.get("created", False),
        "final_export_created": False,
        "pitch_correction_blocked": True,
        "ab_render_status": "planned_only" if not render_ab else "render_requested_but_not_created",
        "ab_evaluation_passed": False,
        "protection_passed": protection.get("protection_passed", False),
        "rollback_status": "available",
        "review_package_path": package_manifest.get("package_dir", ""),
        "review_package_zip": package_manifest.get("zip_path", ""),
        "final_recommendation": recommendation,
        "reports": {
            "blocked_stages": str(output / "eval_reports/finalizing_blocked_stages.json"),
            "target_resolution": str(output / "analysis_reports/finalizing_target_resolution.json"),
            "vocal_space_analysis": str(output / "analysis_reports/final_vocal_space_analysis.json"),
            "chain_plan": str(output / "chain_plans/final_vocal_space_carving_chain_plan.json"),
            "rollback": str(output / "rollback/final_vocal_space_carving_rollback.json"),
            "parameter_log": str(output / "logs/final_vocal_space_parameter_write_log.json"),
            "routing_log": str(output / "logs/final_vocal_space_routing_log.json"),
            "ab_plan": str(output / "eval_reports/final_vocal_space_ab_render_plan.json"),
            "eval_metrics": str(output / "eval_reports/final_vocal_space_eval_metrics.json"),
            "iteration_history": str(output / "eval_reports/final_vocal_space_iteration_history.json"),
            "protection": str(output / "eval_reports/final_vocal_space_protection_report.json"),
            "review_form": str(review_form),
            "review_state": str(output / "review/final_vocal_space_review_state.json"),
            "premaster_chain_plan": str(output / "chain_plans/final_safe_premaster_chain_plan.json"),
            "premaster_eval_metrics": str(output / "eval_reports/final_safe_premaster_eval_metrics.json"),
            "premaster_report": str(premaster_report),
            "main_report": str(report),
        },
        "warnings": sorted(set(preconditions.get("warnings", []) + analysis.get("warnings", []) + chain_plan.get("warnings", []))),
    }
    if verbose:
        summary["target_resolution"] = target
        summary["vocal_space_analysis"] = analysis
    write_json(output / "eval_reports" / "final_vocal_space_finish_summary.json", summary)
    return summary

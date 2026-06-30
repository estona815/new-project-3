from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from automix.analyze_ai_pitch_source import safe_filename, write_json
from automix.routing.vocal_sidechain_routing import build_vocal_placement_rollback, build_vocal_sidechain_routing_plan
from automix.vocal_placement.placement_profiles import resolve_placement_profile


PLACEMENT_ACTIONS = {
    "skip_placement",
    "minimal_vocal_gain_trim",
    "dynamic_space_creation_draft",
    "sidechain_dynamic_eq_draft",
    "ms_center_cleanup_draft",
    "send_cleanup_draft",
    "manual_mix_required",
    "stem_required",
}


def evaluate_placement_policy(analysis: dict[str, Any], target_context: dict[str, Any] | None = None) -> dict[str, Any]:
    target_context = target_context or {}
    source_class = analysis.get("source_classification", "unknown")
    presence = analysis.get("vocal_presence_profile", {})
    masking = analysis.get("masking_profile", {})
    spatial = analysis.get("spatial_profile", {})
    sends = analysis.get("send_profile", {})
    role = analysis.get("role", "lead_vocal")
    reason_codes: list[str] = []
    warnings = list(analysis.get("warnings", []))

    action = "skip_placement"
    selected_profile = "skip_placement"
    draft_required = False

    has_instrumental = bool(target_context.get("instrumental_bus"))
    is_backing = role in {"backing_vocal", "vocal_double", "adlib"}
    too_loud = presence.get("vocal_loudness_lufs", -99.0) > -13.0 or presence.get("vocal_peak_dbfs", -99.0) > -2.0
    fragile = (
        source_class in {"ai_vocal_stem", "source_separated_vocal"}
        or analysis.get("recovery_status") in {"failed_recovery", "missing_renders", "manual_cleanup_required"}
        or presence.get("vocal_harshness_2k5_6k", 0.0) > 0.58
        or spatial.get("mono_compatibility_risk", 0.0) > 0.58
    )
    masking_high = masking.get("instrumental_competes_with_vocal", 0.0) > 0.45 or masking.get("masking_2k_5k", 0.0) > 0.45

    if source_class == "full_mix" or analysis.get("placement_risk") == "unsafe":
        action = "stem_required"
        selected_profile = "skip_placement"
        reason_codes.append("FULL_MIX_UNSAFE")
    elif not has_instrumental and not is_backing:
        action = "manual_mix_required"
        selected_profile = "skip_placement"
        reason_codes.append("NO_INSTRUMENTAL_BUS_TARGET")
    elif is_backing:
        action = "sidechain_dynamic_eq_draft"
        selected_profile = "backing_vocal_duck_under_lead"
        draft_required = True
        reason_codes.append("BACKING_VOCAL_DUCK_UNDER_LEAD")
    elif too_loud:
        action = "manual_mix_required"
        selected_profile = "skip_placement"
        reason_codes.append("VOCAL_ALREADY_TOO_LOUD_DO_NOT_RAISE_GAIN")
    elif sends.get("tail_masking_score", 0.0) > 0.58:
        action = "send_cleanup_draft"
        selected_profile = "dynamic_space_creation"
        draft_required = True
        reason_codes.append("SEND_TAIL_MASKING")
    elif masking_high:
        action = "dynamic_space_creation_draft"
        selected_profile = "fragile_ai_vocal_protect" if fragile else "dynamic_space_creation"
        draft_required = True
        reason_codes.append("MASKING_PREFERS_DYNAMIC_SPACE_OVER_GAIN")
        if spatial.get("instrumental_mid_density", 0.0) > 0.70:
            reason_codes.append("CENTER_DENSITY_USE_VOCAL_KEYED_MID_DUCK")
    elif spatial.get("mono_compatibility_risk", 0.0) > 0.55 or spatial.get("instrumental_mid_density", 0.0) > 0.70:
        action = "ms_center_cleanup_draft"
        selected_profile = "fragile_ai_vocal_protect" if fragile else "dynamic_space_creation"
        draft_required = True
        reason_codes.append("CENTER_OR_MS_CROWDING")
    elif presence.get("vocal_loudness_lufs", -99.0) < -22.0 and not fragile:
        action = "minimal_vocal_gain_trim"
        selected_profile = "minimal_vocal_gain_trim"
        draft_required = True
        reason_codes.append("SLIGHT_GAIN_TRIM_ALLOWED")
    else:
        action = "skip_placement"
        selected_profile = "skip_placement"
        reason_codes.append("NO_PLACEMENT_NEEDED")

    if fragile:
        reason_codes.append("FRAGILE_AI_VOCAL_PROTECT")
        warnings.append("avoid exposing AI artifacts with vocal gain, high boosts, OTT, or saturation")
    if masking.get("masking_5k_10k", 0.0) > 0.50:
        reason_codes.append("SIBILANCE_CONFLICT_AVOID_HIGH_BOOST")
    if spatial.get("mono_compatibility_risk", 0.0) > 0.55:
        reason_codes.append("NO_STEREO_WIDENING")
    return {
        "schema": "automix-vocal-placement-policy-v1",
        "track_name": analysis.get("track_name"),
        "placement_action": action,
        "selected_profile": selected_profile,
        "draft_required": draft_required,
        "draft_created": False,
        "draft_bus_or_track": f"{analysis.get('track_name', 'track')}_PLACEMENT_DRAFT",
        "requires_ab_evaluation": draft_required,
        "reason_codes": sorted(set(reason_codes)),
        "warnings": sorted(set(warnings)),
    }


def build_placement_chain_plan(
    analysis: dict[str, Any],
    decision: dict[str, Any] | None = None,
    target_context: dict[str, Any] | None = None,
    adapter_status: dict[str, Any] | None = None,
    output_dir: Path | None = None,
) -> dict[str, Any]:
    target_context = target_context or {}
    decision = decision or evaluate_placement_policy(analysis, target_context)
    profile = resolve_placement_profile(decision["placement_action"], analysis, adapter_status or {})
    routing_plan = build_vocal_sidechain_routing_plan(
        track_name=analysis["track_name"],
        lead_vocal=target_context.get("lead_vocal") or analysis["track_name"],
        instrumental_bus=target_context.get("instrumental_bus"),
        backing_vocals=target_context.get("backing_vocals", []),
        send_tracks=target_context.get("send_tracks", []),
        action=decision["placement_action"],
        output_dir=output_dir,
    )
    chain = profile["plugin_chain"]
    safe_chain = all(item.get("safe_to_apply", False) for item in chain) if chain else False
    return {
        "schema": "automix-vocal-placement-chain-plan-v1",
        "track_name": analysis["track_name"],
        "target_tracks": {
            "lead_vocal": target_context.get("lead_vocal") or analysis["track_name"],
            "instrumental_bus": target_context.get("instrumental_bus"),
            "backing_vocals": target_context.get("backing_vocals", []),
            "send_tracks": target_context.get("send_tracks", []),
        },
        "placement_action": decision["placement_action"],
        "selected_profile": profile["profile"],
        "masking_profile": analysis["masking_profile"],
        "spatial_profile": analysis["spatial_profile"],
        "plugin_chain": chain,
        "routing_plan": routing_plan,
        "semantic_settings": profile["settings"],
        "semantic_controls_written": profile["semantic_controls_to_write"],
        "semantic_controls_skipped": profile["semantic_controls_skipped"],
        "rollback_required": True,
        "ab_eval_required": decision["requires_ab_evaluation"],
        "draft_only": True,
        "original_mix_must_remain_untouched": True,
        "contains_pitch_correction": False,
        "contains_master_limiter": False,
        "safe_to_apply": bool(decision["draft_required"] and safe_chain),
        "reason_codes": decision.get("reason_codes", []),
        "warnings": sorted(set(decision.get("warnings", []) + profile.get("warnings", []) + routing_plan.get("warnings", []))),
    }


def final_recommendation(decision: dict[str, Any], eval_metrics: dict[str, Any] | None = None) -> str:
    action = decision.get("placement_action")
    if action == "stem_required":
        return "stem_required"
    if action == "manual_mix_required":
        return "manual_mix_required"
    if action == "skip_placement":
        return "no_placement_needed"
    if not eval_metrics:
        return "manual_mix_required"
    if eval_metrics.get("evaluation_passed"):
        return "accept_light_placement"
    return "reject_placement"


def write_placement_report(
    output_dir: Path,
    analysis: dict[str, Any],
    decision: dict[str, Any],
    chain_plan: dict[str, Any],
    eval_metrics: dict[str, Any] | None = None,
    iteration_history: dict[str, Any] | None = None,
) -> Path:
    eval_metrics = eval_metrics or {}
    iteration_history = iteration_history or {"iterations": []}
    path = output_dir / "eval_reports" / f"{safe_filename(analysis['track_name'])}_vocal_placement_report.md"
    presence = analysis["vocal_presence_profile"]
    masking = analysis["masking_profile"]
    spatial = analysis["spatial_profile"]
    final = final_recommendation(decision, eval_metrics)
    lines = [
        "# Vocal Forward Placement Report",
        "",
        "## Summary",
        "",
        f"- Final recommendation: `{final}`",
        f"- Placement applied: `{decision['draft_created']}`",
        f"- Draft bus/track: `{decision['draft_bus_or_track']}`",
        "- Original mix untouched: `true`",
        f"- Source classification: `{analysis['source_classification']}`",
        f"- Recovery status: `{analysis['recovery_status']}`",
        f"- Pitch status: `{analysis['pitch_status']}`",
        "",
        "## Vocal Presence Profile",
        "",
    ]
    for key in (
        "vocal_loudness_lufs",
        "vocal_peak_dbfs",
        "vocal_presence_1k_4k",
        "vocal_air_8k_14k",
        "vocal_body_120_350",
        "vocal_sibilance_5k_10k",
        "vocal_harshness_2k5_6k",
        "vocal_stability_score",
    ):
        lines.append(f"- {key}: `{presence.get(key, 0.0)}`")
    lines.extend(["", "## Masking Profile", ""])
    for key in (
        "masking_120_350",
        "masking_350_800",
        "masking_800_2k",
        "masking_2k_5k",
        "masking_5k_10k",
        "instrumental_competes_with_vocal",
        "snare_hihat_competes_with_sibilance",
        "guitar_synth_competes_with_presence",
        "piano_competes_with_vocal_body",
    ):
        lines.append(f"- {key}: `{masking.get(key, 0.0)}`")
    lines.extend(["", "## Spatial Profile", ""])
    for key in (
        "vocal_center_stability",
        "vocal_side_leakage",
        "instrumental_mid_density",
        "instrumental_side_density",
        "mono_compatibility_risk",
        "stereo_width_change_risk",
    ):
        lines.append(f"- {key}: `{spatial.get(key, 0.0)}`")
    lines.extend(
        [
            "",
            "## Placement Decision",
            "",
            f"- selected profile: `{chain_plan['selected_profile']}`",
            f"- reason codes: `{', '.join(decision.get('reason_codes', [])) or 'none'}`",
            f"- semantic settings: `{json.dumps(chain_plan.get('semantic_settings', {}), sort_keys=True)}`",
            f"- plugin chain: `{json.dumps(chain_plan.get('plugin_chain', []), sort_keys=True)}`",
            f"- routing changes: `{json.dumps(chain_plan.get('routing_plan', {}).get('created_sends', []), sort_keys=True)}`",
            f"- controls written: `{json.dumps(chain_plan.get('semantic_controls_written', {}), sort_keys=True)}`",
            f"- controls skipped: `{json.dumps(chain_plan.get('semantic_controls_skipped', {}), sort_keys=True)}`",
            f"- warnings: `{', '.join(chain_plan.get('warnings', [])) or 'none'}`",
            "",
            "## A/B Render Files",
            "",
            f"- original mix: `{eval_metrics.get('original_mix_path')}`",
            f"- placement draft: `{eval_metrics.get('placement_draft_path')}`",
            f"- loudness matched: `{eval_metrics.get('loudness_matched_path')}`",
            f"- difference: `{eval_metrics.get('difference_path')}`",
            "",
            "## Evaluation Metrics",
            "",
            f"- improvement scores: `{json.dumps(eval_metrics.get('improvement_scores', {}), sort_keys=True)}`",
            f"- damage scores: `{json.dumps(eval_metrics.get('damage_scores', {}), sort_keys=True)}`",
            f"- evaluation passed: `{eval_metrics.get('evaluation_passed', False)}`",
            "",
            "## Iteration History",
            "",
        ]
    )
    iterations = iteration_history.get("iterations", [])
    if iterations:
        for item in iterations:
            lines.append(f"- iteration {item.get('iteration')}: `{item.get('decision')}`")
    else:
        for idx in range(4):
            lines.append(f"- iteration {idx}: `not run`")
    lines.extend(
        [
            "",
            "## Manual Listening Checklist",
            "",
            "- Is the vocal clearer without simply sounding louder?",
            "- Does the beat still hit?",
            "- Did the low end become weak?",
            "- Did snare or hats start pumping?",
            "- Did the vocal become harsh?",
            "- Did the vocal become thinner?",
            "- Did the stereo image move strangely?",
            "- Do reverb or delay tails breathe naturally?",
            "- Does the result sound less AI-like, or just more exposed?",
            "",
            "## Final Recommendation",
            "",
            f"`{final}`",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def write_placement_artifacts(
    output_dir: Path,
    analysis: dict[str, Any],
    decision: dict[str, Any],
    chain_plan: dict[str, Any],
    eval_metrics: dict[str, Any] | None = None,
    iteration_history: dict[str, Any] | None = None,
) -> dict[str, Path]:
    stem = safe_filename(analysis["track_name"])
    paths = {
        "analysis": output_dir / "analysis_reports" / f"{stem}_vocal_placement_analysis.json",
        "chain_plan": output_dir / "chain_plans" / f"{stem}_vocal_placement_chain_plan.json",
        "routing_plan": output_dir / "chain_plans" / f"{stem}_vocal_sidechain_routing_plan.json",
        "rollback": output_dir / "rollback" / f"{stem}_vocal_placement_rollback.json",
        "iteration_history": output_dir / "eval_reports" / f"{stem}_vocal_placement_iteration_history.json",
        "report": output_dir / "eval_reports" / f"{stem}_vocal_placement_report.md",
    }
    write_json(paths["analysis"], analysis)
    write_json(paths["chain_plan"], chain_plan)
    write_json(paths["routing_plan"], chain_plan["routing_plan"])
    rollback = build_vocal_placement_rollback(
        original_tracks=[analysis["track_name"]],
        draft_tracks=[],
        created_sends=chain_plan["routing_plan"].get("created_sends", []),
        created_buses=[],
        chain_plan=paths["chain_plan"],
        analysis_report=paths["analysis"],
        created_at=analysis["scan_date_utc"],
    )
    write_json(paths["rollback"], rollback)
    write_json(paths["iteration_history"], iteration_history or {"iterations": []})
    write_placement_report(output_dir, analysis, decision, chain_plan, eval_metrics, iteration_history)
    return paths

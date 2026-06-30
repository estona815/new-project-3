from __future__ import annotations

import hashlib
from typing import Any

from automix.plugins.plugin_adapter_schema import now_utc


FEEDBACK_ACTION_PLAN_SCHEMA = "automix-feedback-action-plan-v1"


ACTION_LIBRARY: dict[str, list[dict[str, Any]]] = {
    "vocal_clarity": [
        {
            "action_id": "diagnose_vocal_mud_and_presence",
            "stage": "vocal_recovery_or_placement",
            "target": "lead_vocal_and_music_bus",
            "diagnostic_checks": ["200_500hz_mud", "2_5khz_intelligibility", "reverb_wet_distance", "consonant_transients"],
            "planned_action": "Create a dry-run corrective EQ/dynamic EQ and masking check before any vocal gain boost.",
            "safe_processing_bias": "conservative_dynamic_eq",
            "disallowed_actions": ["strong_high_shelf_boost", "heavy_saturation", "stacked_pitch_correction"],
        }
    ],
    "vocal_presence": [
        {
            "action_id": "restore_vocal_front_without_plain_gain_chase",
            "stage": "vocal_placement",
            "target": "lead_vocal_music_bus_sidechain",
            "diagnostic_checks": ["vocal_to_instrument_ratio", "mid_channel_masking", "pre_delay_distance", "send_ducking"],
            "planned_action": "Prefer dynamic instrumental carve and ducked sends before increasing lead-vocal gain.",
            "safe_processing_bias": "vocal_first_dynamic_carve",
            "disallowed_actions": ["unbounded_vocal_gain", "master_limiter_push"],
        }
    ],
    "masking_balance": [
        {
            "action_id": "build_vocal_seat_carving_plan",
            "stage": "vocal_placement",
            "target": "piano_guitar_synth_sample_bus",
            "diagnostic_checks": ["1_5khz_mid_masking", "200_500hz_mud_overlap", "side_channel_fizz"],
            "planned_action": "Plan sidechain dynamic EQ pockets on masking instruments while preserving side width.",
            "safe_processing_bias": "music_bus_duck_only_when_vocal_active",
            "disallowed_actions": ["static_broad_eq_gutting", "arrangement_rewrite_without_request"],
        }
    ],
    "sibilance_harshness": [
        {
            "action_id": "harshness_and_sibilance_guard",
            "stage": "vocal_recovery_or_premaster",
            "target": "lead_vocal_high_mid",
            "diagnostic_checks": ["3_5khz_edge", "6_9khz_sibilance", "post_ott_fizz", "deesser_damage"],
            "planned_action": "Create conservative dynamic harshness/de-ess controls with formant and consonant protection.",
            "safe_processing_bias": "dynamic_cut_not_static_dulling",
            "disallowed_actions": ["broad_air_cut", "aggressive_ott", "unbounded_deesser"],
        }
    ],
    "ai_artifact": [
        {
            "action_id": "suno_ai_artifact_suppression_scan",
            "stage": "vocal_recovery",
            "target": "lead_vocal_first_fx_slot_and_ms_side",
            "diagnostic_checks": ["suno_like_probability", "10khz_plus_fizz", "watery_smear", "fake_stereo_halo", "formant_damage"],
            "planned_action": "Require conservative artifact suppression planning and exact first-slot rescue plugin trace before final claims.",
            "safe_processing_bias": "artifact_reduction_not_total_removal",
            "disallowed_actions": ["claim_100_percent_removal", "fallback_plugin_as_rescue_proof", "strong_pitch_or_saturation_before_clean_pass"],
        }
    ],
    "reverb_delay_space": [
        {
            "action_id": "space_fx_distance_cleanup",
            "stage": "vocal_placement",
            "target": "vocal_sends_delay_reverb",
            "diagnostic_checks": ["wet_level", "pre_delay", "tail_noise", "delay_feedback_clutter"],
            "planned_action": "Plan ducked reverb/delay cleanup and phrase-end throws instead of wetter constant space.",
            "safe_processing_bias": "send_ducking_and_tail_filtering",
            "disallowed_actions": ["more_reverb_for_depth", "unfiltered_delay_feedback"],
        }
    ],
    "low_end": [
        {
            "action_id": "low_end_translation_and_vocal_masking_check",
            "stage": "premaster_or_mix_revision",
            "target": "kick_808_bass_music_bus",
            "diagnostic_checks": ["low_end_buildup", "kick_808_vocal_masking", "mono_low_end", "crest_factor"],
            "planned_action": "Route to mix-side low-end control or sidechain before master limiting.",
            "safe_processing_bias": "mix_revision_before_master_fix",
            "disallowed_actions": ["master_limiter_low_end_fix", "broad_bass_boost"],
        }
    ],
    "mastering_dynamics": [
        {
            "action_id": "premaster_limiter_pressure_audit",
            "stage": "premaster",
            "target": "premaster_bus",
            "diagnostic_checks": ["limiter_gain_reduction", "crest_factor", "lra", "short_term_lufs", "true_peak"],
            "planned_action": "Audit limiter pressure and transient loss; lower processing or return to mix revision if needed.",
            "safe_processing_bias": "translation_before_loudness",
            "disallowed_actions": ["loudness_only_rerender", "clipper_stack_without_qc"],
        }
    ],
    "stereo_mono": [
        {
            "action_id": "mono_compatibility_and_side_hash_check",
            "stage": "premaster",
            "target": "stereo_bus_and_side_channel",
            "diagnostic_checks": ["phase_correlation", "mono_fold_down", "low_end_side_energy", "side_hash"],
            "planned_action": "Plan M/S cleanup and low-end mono management only after correlation checks.",
            "safe_processing_bias": "mono_safe_ms_cleanup",
            "disallowed_actions": ["blind_stereo_widening", "side_air_boost"],
        }
    ],
    "tuning_formant": [
        {
            "action_id": "pitch_and_formant_damage_review",
            "stage": "pitch_safety",
            "target": "lead_vocal_pitch_chain",
            "diagnostic_checks": ["already_tuned_score", "formant_drift", "monophonic_confidence", "source_separation_artifacts"],
            "planned_action": "Skip or micro-correct only if the pitch safety gate and A/B review allow it.",
            "safe_processing_bias": "pitch_skip_is_valid_success",
            "disallowed_actions": ["strong_scale_force", "stacked_autotune_on_ai_vocal"],
        }
    ],
    "female_support_layer": [
        {
            "action_id": "support_layer_lead_intrusion_check",
            "stage": "vocal_placement",
            "target": "female_double_adlib_harmony",
            "diagnostic_checks": ["lead_range_intrusion", "timing_overlap", "pitch_overlap", "adlib_forwardness"],
            "planned_action": "Keep support layers tucked, panned, filtered, or muted when they compete with the male lead.",
            "safe_processing_bias": "male_lead_anchor",
            "disallowed_actions": ["female_layer_as_default_lead", "random_intro_chops"],
        }
    ],
    "general_mix_feedback": [
        {
            "action_id": "manual_triage_required",
            "stage": "diagnostic_review",
            "target": "project",
            "diagnostic_checks": ["operator_clarification", "current_qc_reports", "matched_ab_review"],
            "planned_action": "Keep as human-review feedback until it can be classified into a concrete mix issue.",
            "safe_processing_bias": "review_only",
            "disallowed_actions": ["automatic_processing_without_classification"],
        }
    ],
}


def _plan_id(feedback_id: str, categories: list[str]) -> str:
    digest = hashlib.sha1(f"{feedback_id}|{'|'.join(sorted(categories))}".encode("utf-8")).hexdigest()[:12]
    return f"feedback_action_plan_{digest}"


def map_feedback_to_actions(
    feedback: dict[str, Any],
    *,
    previous_categories: dict[str, int] | None = None,
) -> dict[str, Any]:
    categories = [item.get("category", "general_mix_feedback") for item in feedback.get("categories", [])]
    if not categories:
        categories = ["general_mix_feedback"]
    previous_categories = previous_categories or {}
    planned_actions: list[dict[str, Any]] = []
    blocked_auto_actions: list[dict[str, Any]] = []
    for category in categories:
        for template in ACTION_LIBRARY.get(category, ACTION_LIBRARY["general_mix_feedback"]):
            repeat_count = int(previous_categories.get(category, 0))
            action = dict(template)
            action["feedback_category"] = category
            action["dry_run_only"] = True
            action["requires_human_review"] = True
            action["repeat_count_before_this_pass"] = repeat_count
            action["priority"] = "elevated" if repeat_count else "normal"
            action["status"] = "planned"
            planned_actions.append(action)
            for disallowed in action.get("disallowed_actions", []):
                blocked_auto_actions.append(
                    {
                        "feedback_category": category,
                        "blocked_action": disallowed,
                        "reason": "unsafe_or_unverified_response_to_user_feedback",
                    }
                )
    safety_flags = sorted(set(list(feedback.get("safety_flags", [])) + ["human_review_required", "dry_run_required"]))
    if "ai_artifact" in categories:
        safety_flags.append("artifact_reduction_language_only")
    if "mastering_dynamics" in categories or "low_end" in categories:
        safety_flags.append("do_not_fix_mix_problem_with_master_limiter")
    return {
        "schema": FEEDBACK_ACTION_PLAN_SCHEMA,
        "feedback_id": feedback.get("feedback_id", ""),
        "action_plan_id": _plan_id(str(feedback.get("feedback_id", "")), categories),
        "project_name": feedback.get("project_name", ""),
        "pass_id": feedback.get("pass_id", ""),
        "track_name": feedback.get("track_name", ""),
        "created_at": now_utc(),
        "source_feedback": feedback.get("normalized_text", ""),
        "categories": categories,
        "planned_actions": planned_actions,
        "blocked_auto_actions": blocked_auto_actions,
        "safety_flags": sorted(set(safety_flags)),
        "unresolved": True,
        "resolution_status": "planned_review_required",
    }

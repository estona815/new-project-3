from __future__ import annotations

from pathlib import Path
from typing import Any

from automix.analyze_ai_pitch_source import write_json
from automix.plugins.adapter_confidence_gate import evaluate_adapter_confidence


def _adjustment(priority: int, target: str, issue: str, adjustment_type: str, semantic_settings: dict[str, Any], benefit: str, risk: str = "low") -> dict[str, Any]:
    gate = evaluate_adapter_confidence(
        desired_semantic_controls=semantic_settings,
        adapter=None,
        plugin_name=None,
        plugin_detected=False,
        workflow_stage="reference_matching",
        source_risk=risk,
        fallback="validated stock/JSFX fallback or manual review required",
    )
    return {
        "priority": priority,
        "target": target,
        "issue": issue,
        "adjustment_type": adjustment_type,
        "semantic_settings": semantic_settings,
        "expected_benefit": benefit,
        "risk": risk,
        "requires_draft": True,
        "blocked": False,
        "adapter_confidence_gate_enforced": True,
        "adapter_confidence_gate": gate,
    }


def build_reference_adjustment_plan(
    *,
    project_name: str,
    comparison: dict[str, Any],
    output_dir: Path | None = None,
) -> dict[str, Any]:
    diffs = comparison.get("differences", {})
    blocked_adjustments = []
    adjustments: list[dict[str, Any]] = []
    priority = 1
    blocked_names = set(comparison.get("unsafe_adjustments_blocked", []))
    if "current_mix_missing_target_profile_only" in comparison.get("warnings", []):
        plan = {
            "schema": "automix-reference-adjustment-plan-v1",
            "project_name": project_name,
            "target_profile": comparison.get("target_profile"),
            "adjustments": [],
            "blocked_adjustments": [],
            "ab_eval_required": False,
            "draft_only": True,
            "contains_pitch_correction": False,
            "contains_reference_audio_content": False,
            "warnings": sorted(set(comparison.get("warnings", []) + ["current mix missing; target profile scan only"])),
        }
        if output_dir:
            write_json(output_dir / "chain_plans" / "project_reference_match_adjustment_plan.json", plan)
        return plan

    if diffs.get("vocal_too_low", 0.0) > 0.08:
        adjustments.append(
            _adjustment(
                priority,
                "instrumental_bus",
                "vocal_masked_2k_5k",
                "sidechain_dynamic_eq",
                {"band": "2k_5k", "duck_amount_db": -0.8, "attack_ms": 20, "release_ms": 180},
                "improve vocal forwardness without raising vocal gain",
            )
        )
        priority += 1
        if diffs.get("ai_artifacts_too_exposed", 0.0) <= 0.0:
            adjustments.append(
                _adjustment(
                    priority,
                    "lead_vocal_draft",
                    "vocal_slightly_low_after_space",
                    "utility_gain_trim",
                    {"gain_db": 0.4, "max_gain_db": 0.8},
                    "small draft gain only after instrumental space is created",
                    "medium",
                )
            )
            priority += 1
    if diffs.get("lead_melody_too_low", 0.0) > 0.08:
        adjustments.append(
            _adjustment(
                priority,
                "melody_or_music_bus",
                "lead_melody_buried",
                "dynamic_eq_space",
                {"band": "800_4k", "duck_amount_db": -0.6, "attack_ms": 25, "release_ms": 220},
                "make lead melody clearer by creating space without masking vocal",
            )
        )
        priority += 1
    if diffs.get("low_end_too_muddy", 0.0) > 0.05:
        adjustments.append(
            _adjustment(
                priority,
                "premaster_or_808_bus_draft",
                "low_end_uncontrolled",
                "low_end_control",
                {"mono_below_hz": 95, "dynamic_cut_db": -0.7, "band": "60_180"},
                "control sub/low-mid before adding 808 level",
            )
        )
        priority += 1
    if diffs.get("808_too_weak", 0.0) > 0.10 and diffs.get("low_end_too_muddy", 0.0) <= 0.05:
        adjustments.append(
            _adjustment(
                priority,
                "808_bus_draft",
                "808_weak_but_controlled",
                "subtle_harmonic_support",
                {"harmonic_amount": 0.08, "output_trim_db": -0.2},
                "add audibility without uncontrolled sub boost",
                "medium",
            )
        )
        priority += 1
    if diffs.get("drums_too_soft", 0.0) > 0.10:
        adjustments.append(
            _adjustment(
                priority,
                "drum_bus_draft",
                "drums_too_soft",
                "parallel_transient_support",
                {"parallel_amount": 0.12, "clipper_drive_db": 0.0},
                "support drum energy without master clipping",
                "medium",
            )
        )
        priority += 1
    if diffs.get("vocal_too_harsh", 0.0) > 0.0 or diffs.get("air_too_fizzy", 0.0) > 0.0:
        adjustments.append(
            _adjustment(
                priority,
                "vocal_or_music_bus_draft",
                "harshness_or_fizz_risk",
                "dynamic_harshness_guard",
                {"band": "3k_10k", "max_reduction_db": -0.9, "attack_ms": 8, "release_ms": 120},
                "reduce AI fizz or harshness before any brightness move",
            )
        )
        priority += 1
    if diffs.get("stereo_too_narrow", 0.0) > 0.12 and "master_widening_blocked_mono_risk" not in blocked_names:
        adjustments.append(
            _adjustment(
                priority,
                "non_vocal_side_elements_draft",
                "mix_narrow",
                "stereo_safety",
                {"side_gain_db": 0.3, "exclude_vocal": True, "exclude_low_end_below_hz": 140},
                "widen only non-critical side elements, not vocal or master",
                "medium",
            )
        )
        priority += 1
    if diffs.get("mix_not_loud_enough", 0.0) > 0.12 and "more_limiting_blocked_current_mix_already_limited" not in blocked_names:
        adjustments.append(
            _adjustment(
                priority,
                "premaster_draft",
                "mix_not_loud_enough",
                "safe_loudness",
                {"limiter_max_gain_db": 0.6, "ceiling_dbTP": -1.0},
                "small safe premaster push only after A/B review",
                "medium",
            )
        )

    for name in sorted(blocked_names):
        requested = "high_shelf_boost" if "high_shelf" in name else "reference_matching_adjustment"
        blocked_adjustments.append({"issue": name, "requested_adjustment": requested, "blocked_reason": name.upper()})
    plan = {
        "schema": "automix-reference-adjustment-plan-v1",
        "project_name": project_name,
        "target_profile": comparison.get("target_profile"),
        "adjustments": adjustments,
        "blocked_adjustments": blocked_adjustments,
        "ab_eval_required": bool(adjustments),
        "draft_only": True,
        "contains_pitch_correction": False,
        "contains_reference_audio_content": False,
        "warnings": comparison.get("warnings", []),
    }
    if output_dir:
        write_json(output_dir / "chain_plans" / "project_reference_match_adjustment_plan.json", plan)
    return plan

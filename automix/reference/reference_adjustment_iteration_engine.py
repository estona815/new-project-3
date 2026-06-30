from __future__ import annotations

from typing import Any


def _scale_value(value: Any, factor: float) -> Any:
    if isinstance(value, (int, float)):
        return float(value) * factor
    return value


def next_reference_iteration_plan(plan: dict[str, Any], iteration: int) -> dict[str, Any]:
    out = {**plan, "adjustments": [dict(item) for item in plan.get("adjustments", [])]}
    if iteration == 1:
        for item in out["adjustments"]:
            settings = dict(item.get("semantic_settings", {}))
            for key in ("boost_db", "gain_db", "side_gain_db", "harmonic_amount"):
                if key in settings:
                    settings[key] = _scale_value(settings[key], 0.50)
            for key in ("duck_amount_db", "max_reduction_db", "dynamic_cut_db"):
                if key in settings:
                    settings[key] = _scale_value(settings[key], 0.70)
            item["semantic_settings"] = settings
    elif iteration == 2:
        filtered = []
        for item in out["adjustments"]:
            if item.get("adjustment_type") in {"safe_loudness", "stereo_safety"}:
                continue
            if item.get("adjustment_type") in {"sidechain_dynamic_eq", "dynamic_eq_space", "dynamic_harshness_guard"}:
                filtered.append(item)
        out["adjustments"] = filtered
        out["warnings"] = sorted(set(out.get("warnings", []) + ["removed loudness/master/stereo changes after damage"]))
    elif iteration >= 3:
        safe = [item for item in out["adjustments"] if item.get("risk") == "low"]
        out["adjustments"] = safe[:1]
        out["warnings"] = sorted(set(out.get("warnings", []) + ["single safest adjustment only"]))
    return out


def build_reference_iteration_history(initial_plan: dict[str, Any], metrics_by_iteration: list[dict[str, Any]] | None = None, max_iterations: int = 3) -> dict[str, Any]:
    metrics_by_iteration = metrics_by_iteration or []
    plan = initial_plan
    iterations = []
    final_decision = "reject_reference_match"
    for iteration in range(max_iterations + 1):
        metrics = metrics_by_iteration[iteration] if iteration < len(metrics_by_iteration) else {}
        if metrics.get("evaluation_passed"):
            decision = "accept_light_reference_match"
            final_decision = "accept_light_reference_match"
        elif iteration == 0:
            decision = "reduce_reference_matching_intensity"
        elif iteration == 1:
            decision = "remove_loudness_and_stereo_changes"
        elif iteration == 2:
            decision = "single_safest_adjustment_only"
        else:
            decision = "reject_reference_match_manual_mix_revision"
            final_decision = "manual_mix_revision_required"
        iterations.append({"iteration": iteration, "plan": plan, "metrics": metrics, "decision": decision, "reason_codes": metrics.get("warnings", [])})
        if metrics.get("evaluation_passed"):
            break
        if iteration < max_iterations:
            plan = next_reference_iteration_plan(plan, iteration + 1)
    return {
        "schema": "automix-reference-match-iteration-history-v1",
        "max_iterations": max_iterations,
        "iterations": iterations,
        "final_decision": final_decision,
        "never_intensify_after_damage": True,
    }


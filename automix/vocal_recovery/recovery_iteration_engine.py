from __future__ import annotations

from typing import Any


def next_recovery_iteration_settings(settings: dict[str, Any], iteration: int, metrics: dict[str, Any] | None = None) -> dict[str, Any]:
    metrics = metrics or {}
    damage = metrics.get("damage_scores", {})
    out = dict(settings)
    if iteration == 1:
        if "high_fizz_control_amount" in out:
            out["high_fizz_control_amount"] = float(out["high_fizz_control_amount"]) * 0.60
        if "sibilance_control_amount" in out:
            out["sibilance_control_amount"] = float(out["sibilance_control_amount"]) * 0.70
        if "harshness_dynamic_cut_amount" in out:
            out["harshness_dynamic_cut_amount"] = float(out["harshness_dynamic_cut_amount"]) * 0.75
    elif iteration == 2:
        for key in ("side_noise_reduction_amount", "watery_phase_control_amount"):
            if key in out:
                out[key] = float(out[key]) * 0.60
        if "saturation_amount" in out:
            out["saturation_amount"] = 0.0
        if damage.get("body_loss_db", 0.0) < -1.0 and "low_cut_hz" in out:
            out["low_cut_hz"] = max(50, float(out["low_cut_hz"]) - 20.0)
    elif iteration >= 3:
        out["apply"] = False
        out["bypass_recovery"] = True
    return out


def build_recovery_iteration_history(
    initial_settings: dict[str, Any],
    metrics_by_iteration: list[dict[str, Any]] | None = None,
    max_iterations: int = 3,
) -> dict[str, Any]:
    metrics_by_iteration = metrics_by_iteration or []
    iterations = []
    settings = dict(initial_settings)
    final_decision = "reject_recovery"
    for iteration in range(max_iterations + 1):
        metrics = metrics_by_iteration[iteration] if iteration < len(metrics_by_iteration) else {}
        if metrics.get("evaluation_passed"):
            decision = "accept_light_recovery"
            final_decision = "accept_light_recovery"
        elif iteration == 0:
            decision = "reduce_high_fizz_sibilance_harshness"
        elif iteration == 1:
            decision = "reduce_side_cleanup_disable_saturation"
        elif iteration == 2:
            decision = "switch_to_minimal_or_bypass"
        else:
            decision = "bypass_recovery_manual_review"
            final_decision = "manual_cleanup_required"
        iterations.append(
            {
                "iteration": iteration,
                "settings": dict(settings),
                "metrics": metrics,
                "decision": decision,
                "reason_codes": metrics.get("warnings", []),
            }
        )
        if metrics.get("evaluation_passed"):
            break
        if iteration < max_iterations:
            settings = next_recovery_iteration_settings(settings, iteration + 1, metrics)

    return {
        "schema": "automix-vocal-recovery-iteration-history-v1",
        "max_iterations": max_iterations,
        "iterations": iterations,
        "final_decision": final_decision,
        "never_intensify_after_damage": True,
    }

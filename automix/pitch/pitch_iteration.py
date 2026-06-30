from __future__ import annotations

from typing import Any


def next_iteration_settings(settings: dict[str, Any], iteration: int) -> dict[str, Any]:
    out = dict(settings)
    if iteration == 1:
        out["correction_amount"] = float(out.get("correction_amount", 0.0)) * 0.50
    elif iteration == 2:
        out["speed"] = float(out.get("speed", 0.0)) * 0.50
        out["dry_wet"] = float(out.get("dry_wet", 0.0)) * 0.70
    elif iteration == 3:
        out["scale"] = None
        out["key"] = None
        out["scale_forcing_disabled"] = True
        out["correction_amount"] = min(float(out.get("correction_amount", 0.0)), 0.04)
    return out


def build_iteration_history(
    initial_settings: dict[str, Any],
    metrics_by_iteration: list[dict[str, Any]] | None = None,
    max_iterations: int = 3,
) -> dict[str, Any]:
    metrics_by_iteration = metrics_by_iteration or []
    iterations = []
    settings = dict(initial_settings)
    final_decision = "reject_pitch_correction"
    for iteration in range(max_iterations + 1):
        metrics = metrics_by_iteration[iteration] if iteration < len(metrics_by_iteration) else {}
        evaluation_passed = bool(metrics.get("evaluation_passed", False))
        if evaluation_passed:
            decision = "accept_light"
            final_decision = "accept_light"
        elif iteration == 0:
            decision = "reduce_correction"
        elif iteration == 1:
            decision = "slow_speed_reduce_wet"
        elif iteration == 2:
            decision = "disable_scale_force_micro"
        else:
            decision = "reject_pitch_correction"
        iterations.append(
            {
                "iteration": iteration,
                "settings": dict(settings),
                "metrics": metrics,
                "decision": decision,
                "reason_codes": metrics.get("reason_codes", []),
            }
        )
        if evaluation_passed:
            break
        if iteration < max_iterations:
            settings = next_iteration_settings(settings, iteration + 1)

    return {
        "schema": "automix-pitch-iteration-history-v1",
        "iterations": iterations,
        "final_decision": final_decision,
    }

from __future__ import annotations

from typing import Any


def next_placement_iteration_settings(settings: dict[str, Any], iteration: int, metrics: dict[str, Any] | None = None) -> dict[str, Any]:
    metrics = metrics or {}
    out = dict(settings)
    if iteration == 1:
        if "instrumental_duck_amount_db" in out:
            out["instrumental_duck_amount_db"] = float(out["instrumental_duck_amount_db"]) * 0.70
        if "presence_duck_amount_db" in out:
            out["presence_duck_amount_db"] = float(out["presence_duck_amount_db"]) * 0.75
    elif iteration == 2:
        if "vocal_gain_db" in out:
            out["vocal_gain_db"] = float(out["vocal_gain_db"]) * 0.50
        if "duck_release_ms" in out:
            out["duck_release_ms"] = float(out["duck_release_ms"]) * 1.25
        for key in ("ms_mid_cleanup_amount", "ms_side_cleanup_amount"):
            if key in out:
                out[key] = float(out[key]) * 0.70
    elif iteration >= 3:
        out["switch_profile"] = "fragile_ai_vocal_protect_or_minimal_vocal_gain_trim"
        out["bypass_if_still_failing"] = True
    return out


def build_placement_iteration_history(
    initial_settings: dict[str, Any],
    metrics_by_iteration: list[dict[str, Any]] | None = None,
    max_iterations: int = 3,
) -> dict[str, Any]:
    metrics_by_iteration = metrics_by_iteration or []
    settings = dict(initial_settings)
    iterations = []
    final_decision = "reject_placement"
    for iteration in range(max_iterations + 1):
        metrics = metrics_by_iteration[iteration] if iteration < len(metrics_by_iteration) else {}
        if metrics.get("evaluation_passed"):
            decision = "accept_light_placement"
            final_decision = "accept_light_placement"
        elif iteration == 0:
            decision = "reduce_ducking"
        elif iteration == 1:
            decision = "reduce_gain_slow_release_reduce_ms"
        elif iteration == 2:
            decision = "switch_to_fragile_or_minimal"
        else:
            decision = "bypass_placement_manual_mix"
            final_decision = "manual_mix_required"
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
            settings = next_placement_iteration_settings(settings, iteration + 1, metrics)
    return {
        "schema": "automix-vocal-placement-iteration-history-v1",
        "max_iterations": max_iterations,
        "iterations": iterations,
        "final_decision": final_decision,
        "never_intensify_after_damage": True,
    }

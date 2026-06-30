from __future__ import annotations

from typing import Any


def _contains_warning(metrics: dict[str, Any], *needles: str) -> bool:
    text = " ".join(str(item).lower() for item in metrics.get("warnings", []))
    return any(needle.lower() in text for needle in needles)


def next_premaster_iteration_settings(settings: dict[str, Any], iteration: int, metrics: dict[str, Any] | None = None) -> dict[str, Any]:
    metrics = metrics or {}
    out = dict(settings)
    if iteration == 1:
        if "limiter_max_gain_db" in out:
            out["limiter_max_gain_db"] = float(out["limiter_max_gain_db"]) * 0.60
        if "clipper_drive_db" in out:
            out["clipper_drive_db"] = float(out["clipper_drive_db"]) * 0.50
        if "saturation_amount" in out:
            out["saturation_amount"] = float(out["saturation_amount"]) * 0.50
    elif iteration == 2:
        if "bus_compressor_gain_reduction_db" in out:
            out["bus_compressor_gain_reduction_db"] = float(out["bus_compressor_gain_reduction_db"]) * 0.50
        if "bus_compressor_attack_ms" in out:
            out["bus_compressor_attack_ms"] = float(out["bus_compressor_attack_ms"]) * 1.50
        if "bus_compressor_release_ms" in out:
            out["bus_compressor_release_ms"] = float(out["bus_compressor_release_ms"]) * 1.25
        if _contains_warning(metrics, "fizz", "harsh", "sibilance", "air_loss"):
            for key in ("dynamic_eq_amount", "harshness_guard_amount", "deesser_amount"):
                if key in out:
                    out[key] = float(out[key]) * 0.75
            if "limiter_max_gain_db" in out:
                out["limiter_max_gain_db"] = float(out["limiter_max_gain_db"]) * 0.75
    elif iteration >= 3:
        out["switch_profile"] = "safety_only_premaster"
        out["bypass_if_still_failing"] = True
        for key in ("bus_compressor_gain_reduction_db", "saturation_amount", "clipper_drive_db"):
            if key in out:
                out[key] = 0.0
        if "limiter_max_gain_db" in out:
            out["limiter_max_gain_db"] = min(float(out["limiter_max_gain_db"]), 0.5)
    return out


def build_premaster_iteration_history(
    initial_settings: dict[str, Any],
    metrics_by_iteration: list[dict[str, Any]] | None = None,
    max_iterations: int = 3,
) -> dict[str, Any]:
    metrics_by_iteration = metrics_by_iteration or []
    settings = dict(initial_settings)
    iterations = []
    final_decision = "reject_premaster"
    for iteration in range(max_iterations + 1):
        metrics = metrics_by_iteration[iteration] if iteration < len(metrics_by_iteration) else {}
        if metrics.get("evaluation_passed"):
            decision = "accept_light_premaster"
            final_decision = "accept_light_premaster"
        elif iteration == 0:
            decision = "reduce_limiter_clipper_saturation"
        elif iteration == 1:
            decision = "reduce_compression_slow_attack"
        elif iteration == 2:
            decision = "switch_to_safety_only"
        else:
            decision = "bypass_premaster_fix_mix"
            final_decision = "mix_revision_required"
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
            settings = next_premaster_iteration_settings(settings, iteration + 1, metrics)
    return {
        "schema": "automix-premaster-iteration-history-v1",
        "max_iterations": max_iterations,
        "iterations": iterations,
        "final_decision": final_decision,
        "never_intensify_loudness_after_damage": True,
    }

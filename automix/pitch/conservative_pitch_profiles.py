from __future__ import annotations

from typing import Any

from automix.plugins.adapter_confidence_gate import evaluate_adapter_confidence


PROFILES: dict[str, dict[str, Any]] = {
    "raw_vocal_natural": {
        "correction_amount": 0.25,
        "speed": 0.30,
        "depth": 0.30,
        "formant_preserve": 1.0,
        "humanize": 0.60,
        "vibrato_preserve": 0.70,
        "dry_wet": 0.60,
        "output_gain": 0.0,
    },
    "mixed_vocal_light": {
        "correction_amount": 0.14,
        "speed": 0.18,
        "depth": 0.18,
        "formant_preserve": 1.0,
        "humanize": 0.75,
        "vibrato_preserve": 0.85,
        "dry_wet": 0.40,
        "output_gain": 0.0,
    },
    "ai_vocal_micro": {
        "correction_amount": 0.08,
        "speed": 0.15,
        "depth": 0.15,
        "formant_preserve": 1.0,
        "humanize": 0.70,
        "vibrato_preserve": 0.80,
        "dry_wet": 0.35,
        "output_gain": 0.0,
    },
    "source_separated_phrase_micro": {
        "correction_amount": 0.05,
        "speed": 0.08,
        "depth": 0.08,
        "formant_preserve": 1.0,
        "humanize": 0.85,
        "vibrato_preserve": 0.90,
        "dry_wet": 0.20,
        "output_gain": 0.0,
    },
    "full_mix_skip": {
        "apply": False,
        "correction_amount": 0.0,
    },
    "unknown_skip": {
        "apply": False,
        "correction_amount": 0.0,
    },
}


def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, float(value)))


def profile_name_for_source(source_classification: str) -> str:
    return {
        "raw_vocal": "raw_vocal_natural",
        "mixed_vocal_stem": "mixed_vocal_light",
        "ai_vocal_stem": "ai_vocal_micro",
        "source_separated_vocal": "source_separated_phrase_micro",
        "full_mix": "full_mix_skip",
        "unknown": "unknown_skip",
    }.get(source_classification, "unknown_skip")


def resolve_pitch_profile(
    source_classification: str,
    safety_gate: dict[str, Any],
    available_semantic_controls: dict[str, Any] | None,
) -> dict[str, Any]:
    profile_name = profile_name_for_source(source_classification)
    settings = dict(PROFILES[profile_name])
    controls = available_semantic_controls or {}
    skipped: dict[str, Any] = {}
    write_set: dict[str, Any] = {}

    if not safety_gate.get("eligible", False):
        settings["apply"] = False
        settings["correction_amount"] = 0.0

    max_amount = float(safety_gate.get("max_correction_amount", 0.0))
    if "correction_amount" in settings:
        settings["correction_amount"] = min(float(settings["correction_amount"]), max_amount)
    if "depth" in settings:
        settings["depth"] = min(float(settings["depth"]), max_amount if max_amount > 0.0 else float(settings["depth"]))

    if "formant_preserve" not in controls and settings.get("correction_amount", 0.0) > 0.0:
        settings["correction_amount"] *= 0.5
        if "depth" in settings:
            settings["depth"] *= 0.5

    if source_classification == "full_mix":
        settings["apply"] = False
        settings["correction_amount"] = 0.0
    if source_classification == "unknown":
        settings["apply"] = False
        settings["correction_amount"] = 0.0

    for semantic, value in settings.items():
        if semantic == "apply":
            continue
        if semantic in controls:
            write_set[semantic] = {
                "value": clamp(value, -12.0, 12.0) if semantic == "output_gain" else clamp(value),
                **(controls.get(semantic) if isinstance(controls.get(semantic), dict) else {}),
            }
        else:
            skipped[semantic] = {
                "value": value,
                "reason": "semantic control missing or low-confidence",
            }

    if not safety_gate.get("eligible", False):
        write_set = {}

    adapter_gate = evaluate_adapter_confidence(
        desired_semantic_controls=list(write_set.keys() or controls.keys()),
        adapter=None,
        plugin_name=None,
        plugin_detected=False,
        workflow_stage="pitch",
        source_risk="high" if source_classification in {"ai_vocal_stem", "source_separated_vocal", "full_mix"} else "normal",
        fallback="validated pitch adapter, ReaPitch manual setup, or no pitch correction",
    )

    return {
        "profile": profile_name,
        "settings": settings,
        "semantic_controls_to_write": write_set,
        "semantic_controls_skipped": skipped,
        "adapter_confidence_gate_enforced": True,
        "adapter_confidence_gate": adapter_gate,
    }

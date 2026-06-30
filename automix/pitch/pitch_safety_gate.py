from __future__ import annotations

from dataclasses import dataclass
from typing import Any


REASON_CODES = {
    "FULL_MIX_LIKELY",
    "SOURCE_SEPARATED_HIGH",
    "AI_ARTIFACT_RISK_HIGH",
    "ALREADY_MIXED_HIGH",
    "ALREADY_TUNED_HIGH",
    "PITCH_CONFIDENCE_LOW",
    "KEY_CONFIDENCE_LOW",
    "SCALE_CONFIDENCE_LOW",
    "POLYPHONIC_CONTAMINATION",
    "BAKED_REVERB_HIGH",
    "PLUGIN_MAPPING_UNCERTAIN",
    "SEMANTIC_CONTROL_MISSING",
    "UNKNOWN_PLUGIN_PARAMETER",
    "USER_OVERRIDE_REQUIRED",
    "BENEFIT_TOO_SMALL",
    "DAMAGE_RISK_HIGH",
}

DECISIONS = {
    "apply_light",
    "apply_micro",
    "skip",
    "manual_review_required",
    "full_mix_unsafe",
    "stem_required",
    "plugin_mapping_required",
    "evaluation_required",
    "rollback",
}

OVERRIDE_MODES = {
    "default_conservative",
    "no_pitch_correction",
    "allow_light_pitch_draft",
    "allow_full_mix_pitch_experiment",
    "creative_robotic_autotune",
}

MIN_PLUGIN_MAPPING_CONFIDENCE = 0.85


def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, float(value)))


def _num(mapping: dict[str, Any], key: str, default: float = 0.0) -> float:
    value = mapping.get(key, default)
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _available_control_names(available_semantic_controls: dict[str, Any] | None) -> set[str]:
    if not available_semantic_controls:
        return set()
    return {key for key, value in available_semantic_controls.items() if value is not None}


def _add(reason_codes: list[str], code: str) -> None:
    if code not in reason_codes:
        reason_codes.append(code)


@dataclass(frozen=True)
class PitchSafetyGateInput:
    source_classification: str
    pitch_analysis: dict[str, Any]
    plugin_adapter_confidence: float
    user_goal: str = "default_conservative"
    source_type: str | None = None
    already_mixed_score: float = 0.0
    already_tuned_score: float = 0.0
    baked_reverb_score: float = 0.0
    full_mix_likelihood: float = 0.0
    source_separated_likelihood: float = 0.0
    pitch_confidence: float = 0.0
    key_confidence: float = 0.0
    scale_confidence: float = 0.0
    risk: str = "unsafe"
    available_semantic_controls: dict[str, Any] | None = None
    explicit_user_overrides: dict[str, Any] | None = None
    isolated_vocal_confidence: float = 0.0
    pitch_issue_benefit: float = 0.0


def input_from_reports(
    source_classification: dict[str, Any],
    pitch_analysis: dict[str, Any],
    adapter_status: dict[str, Any],
    *,
    available_semantic_controls: dict[str, Any] | None,
    user_goal: str,
    explicit_user_overrides: dict[str, Any] | None = None,
) -> PitchSafetyGateInput:
    return PitchSafetyGateInput(
        source_classification=str(source_classification.get("classification", "unknown")),
        pitch_analysis=pitch_analysis,
        plugin_adapter_confidence=_num(adapter_status, "mapping_confidence", 0.0),
        user_goal=user_goal,
        source_type=source_classification.get("classification"),
        already_mixed_score=_num(source_classification, "already_mixed_score"),
        already_tuned_score=_num(source_classification, "already_tuned_score"),
        baked_reverb_score=_num(source_classification, "baked_reverb_score"),
        full_mix_likelihood=_num(source_classification, "full_mix_likelihood"),
        source_separated_likelihood=_num(source_classification, "source_separated_likelihood"),
        pitch_confidence=_num(pitch_analysis, "monophonic_pitch_confidence"),
        key_confidence=_num(pitch_analysis, "key_confidence", _num(pitch_analysis, "scale_key_confidence")),
        scale_confidence=_num(pitch_analysis, "scale_confidence", _num(pitch_analysis, "scale_key_confidence")),
        risk=str(source_classification.get("pitch_correction_risk", "unsafe")),
        available_semantic_controls=available_semantic_controls,
        explicit_user_overrides=explicit_user_overrides or {},
        isolated_vocal_confidence=_num(source_classification, "vocal_stem_likelihood"),
        pitch_issue_benefit=_num(pitch_analysis, "pitch_issue_benefit"),
    )


def evaluate_pitch_safety(gate_input: PitchSafetyGateInput | dict[str, Any]) -> dict[str, Any]:
    if isinstance(gate_input, dict):
        gate_input = PitchSafetyGateInput(**gate_input)

    user_goal = gate_input.user_goal if gate_input.user_goal in OVERRIDE_MODES else "default_conservative"
    controls = _available_control_names(gate_input.available_semantic_controls)
    reason_codes: list[str] = []
    risk = gate_input.risk if gate_input.risk in {"low", "medium", "high", "unsafe"} else "unsafe"
    decision = "skip"
    allowed_mode = "none"
    eligible = False
    max_correction_amount = 0.0
    requires_manual_approval = True

    if user_goal == "no_pitch_correction":
        return {
            "eligible": False,
            "decision": "skip",
            "reason_codes": ["USER_OVERRIDE_REQUIRED"],
            "risk": "low",
            "allowed_mode": "none",
            "max_correction_amount": 0.0,
            "requires_manual_approval": False,
            "draft_only": True,
            "rollback_required": True,
            "evaluation_required": False,
            "decision_catalog": sorted(DECISIONS),
            "reason_code_catalog": sorted(REASON_CODES),
            "user_goal": user_goal,
        }

    if gate_input.source_classification == "full_mix" and user_goal != "allow_full_mix_pitch_experiment":
        _add(reason_codes, "FULL_MIX_LIKELY")
        return _closed(
            decision="full_mix_unsafe",
            reason_codes=reason_codes,
            risk="unsafe",
            user_goal=user_goal,
        )

    if gate_input.full_mix_likelihood > 0.65:
        _add(reason_codes, "FULL_MIX_LIKELY")
        if user_goal == "allow_full_mix_pitch_experiment":
            decision = "manual_review_required"
            allowed_mode = "full_mix_pitch_experiment"
            max_correction_amount = 0.03
            risk = "unsafe"
        else:
            return _closed(
                decision="full_mix_unsafe",
                reason_codes=reason_codes,
                risk="unsafe",
                user_goal=user_goal,
            )
    elif gate_input.full_mix_likelihood > 0.45 and gate_input.isolated_vocal_confidence < 0.80:
        _add(reason_codes, "FULL_MIX_LIKELY")
        decision = "manual_review_required"
        risk = "high" if risk != "unsafe" else risk

    if gate_input.source_separated_likelihood > 0.60:
        _add(reason_codes, "SOURCE_SEPARATED_HIGH")
        risk = "high" if risk != "unsafe" else risk

    if gate_input.already_mixed_score > 0.75:
        _add(reason_codes, "ALREADY_MIXED_HIGH")

    if gate_input.already_tuned_score > 0.85:
        _add(reason_codes, "ALREADY_TUNED_HIGH")
        return _closed(decision="skip", reason_codes=reason_codes, risk="high", user_goal=user_goal)
    if gate_input.already_tuned_score > 0.70:
        _add(reason_codes, "ALREADY_TUNED_HIGH")
        if gate_input.pitch_issue_benefit < 0.60:
            _add(reason_codes, "BENEFIT_TOO_SMALL")
            return _closed(decision="skip", reason_codes=reason_codes, risk="high", user_goal=user_goal)
        decision = "apply_micro"
        allowed_mode = "micro"
        max_correction_amount = min(max_correction_amount or 0.06, 0.06)

    if gate_input.pitch_confidence < 0.60:
        _add(reason_codes, "PITCH_CONFIDENCE_LOW")
        if allowed_mode != "full_mix_pitch_experiment":
            return _closed(decision="skip", reason_codes=reason_codes, risk="unsafe", user_goal=user_goal)

    if gate_input.key_confidence < 0.45:
        _add(reason_codes, "KEY_CONFIDENCE_LOW")
    if gate_input.scale_confidence < 0.45:
        _add(reason_codes, "SCALE_CONFIDENCE_LOW")
    if _num(gate_input.pitch_analysis, "polyphonic_contamination_score") > 0.55:
        _add(reason_codes, "POLYPHONIC_CONTAMINATION")
    if gate_input.baked_reverb_score > 0.60:
        _add(reason_codes, "BAKED_REVERB_HIGH")
    if gate_input.source_classification in {"ai_vocal_stem", "source_separated_vocal"} and (
        gate_input.already_mixed_score > 0.55 or gate_input.source_separated_likelihood > 0.45
    ):
        _add(reason_codes, "AI_ARTIFACT_RISK_HIGH")

    if gate_input.plugin_adapter_confidence < MIN_PLUGIN_MAPPING_CONFIDENCE:
        _add(reason_codes, "PLUGIN_MAPPING_UNCERTAIN")
        return _closed(decision="plugin_mapping_required", reason_codes=reason_codes, risk="unsafe", user_goal=user_goal)

    has_amount = "correction_amount" in controls or "depth" in controls
    has_mix = "dry_wet" in controls
    has_speed = "speed" in controls
    if not has_amount:
        _add(reason_codes, "SEMANTIC_CONTROL_MISSING")
        _add(reason_codes, "UNKNOWN_PLUGIN_PARAMETER")
    if not has_mix:
        _add(reason_codes, "SEMANTIC_CONTROL_MISSING")
        _add(reason_codes, "UNKNOWN_PLUGIN_PARAMETER")
    if not has_speed:
        _add(reason_codes, "SEMANTIC_CONTROL_MISSING")
        _add(reason_codes, "UNKNOWN_PLUGIN_PARAMETER")
    if not (has_amount and has_mix and has_speed):
        return _closed(decision="plugin_mapping_required", reason_codes=reason_codes, risk="unsafe", user_goal=user_goal)

    if not max_correction_amount:
        if gate_input.source_classification == "raw_vocal" and risk in {"low", "medium"}:
            decision = "apply_light"
            allowed_mode = "light"
            max_correction_amount = 0.25
            requires_manual_approval = False if risk == "low" and user_goal == "allow_light_pitch_draft" else True
        elif gate_input.source_classification == "mixed_vocal_stem" and risk in {"low", "medium"}:
            decision = "apply_light"
            allowed_mode = "light"
            max_correction_amount = 0.14
        elif gate_input.source_classification == "ai_vocal_stem" and risk in {"low", "medium"}:
            decision = "apply_micro"
            allowed_mode = "micro"
            max_correction_amount = 0.08
        elif gate_input.source_classification == "source_separated_vocal" and user_goal == "allow_light_pitch_draft":
            decision = "apply_micro"
            allowed_mode = "phrase_micro"
            max_correction_amount = 0.05
        else:
            _add(reason_codes, "DAMAGE_RISK_HIGH")
            return _closed(decision="manual_review_required", reason_codes=reason_codes, risk=risk, user_goal=user_goal)

    if "formant_preserve" not in controls:
        _add(reason_codes, "SEMANTIC_CONTROL_MISSING")
        max_correction_amount *= 0.5

    if user_goal == "default_conservative" and risk != "low" and gate_input.source_classification != "raw_vocal":
        _add(reason_codes, "USER_OVERRIDE_REQUIRED")
        return _closed(decision="manual_review_required", reason_codes=reason_codes, risk=risk, user_goal=user_goal)

    if user_goal == "creative_robotic_autotune":
        allowed_mode = "creative_robotic_draft"
        requires_manual_approval = True
        _add(reason_codes, "USER_OVERRIDE_REQUIRED")

    if user_goal == "allow_full_mix_pitch_experiment":
        max_correction_amount = min(max_correction_amount, 0.03)

    eligible = (decision in {"apply_light", "apply_micro"} or allowed_mode == "full_mix_pitch_experiment") and max_correction_amount > 0.0
    return {
        "eligible": eligible,
        "decision": decision,
        "reason_codes": reason_codes,
        "risk": risk,
        "allowed_mode": allowed_mode,
        "max_correction_amount": round(max_correction_amount, 6),
        "requires_manual_approval": requires_manual_approval,
        "draft_only": True,
        "rollback_required": True,
        "evaluation_required": True,
        "decision_catalog": sorted(DECISIONS),
        "reason_code_catalog": sorted(REASON_CODES),
        "user_goal": user_goal,
    }


def _closed(decision: str, reason_codes: list[str], risk: str, user_goal: str) -> dict[str, Any]:
    return {
        "eligible": False,
        "decision": decision,
        "reason_codes": reason_codes,
        "risk": risk,
        "allowed_mode": "none",
        "max_correction_amount": 0.0,
        "requires_manual_approval": True,
        "draft_only": True,
        "rollback_required": True,
        "evaluation_required": decision not in {"skip", "plugin_mapping_required"},
        "decision_catalog": sorted(DECISIONS),
        "reason_code_catalog": sorted(REASON_CODES),
        "user_goal": user_goal,
    }

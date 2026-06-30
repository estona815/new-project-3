from __future__ import annotations

from typing import Any

from automix.plugins.plugin_adapter_schema import control_is_write_safe, safe_float
from automix.plugins.third_party_plugin_policy import evaluate_third_party_policy


GATE_VERSION = "automix-adapter-confidence-gate-v1"

WORKFLOW_MIN_CONFIDENCE = {
    "pitch": 0.90,
    "vocal_recovery": 0.85,
    "vocal_placement": 0.85,
    "reference_matching": 0.88,
    "premaster": 0.90,
    "premaster_limiter": 0.92,
    "mastering": 0.92,
    "default": 0.85,
}

REASON_CODES = {
    "PLUGIN_NOT_DETECTED",
    "ADAPTER_MISSING",
    "ADAPTER_SCHEMA_INVALID",
    "ADAPTER_CONFIDENCE_LOW",
    "VALIDATION_MISSING",
    "SEMANTIC_CONTROL_MISSING",
    "SEMANTIC_CONTROL_CONFIDENCE_LOW",
    "SEMANTIC_CONTROL_NOT_WRITE_ALLOWED",
    "SAFE_RANGE_MISSING",
    "THIRD_PARTY_POLICY_BLOCKED",
    "SOURCE_RISK_RAISED_THRESHOLD",
    "FALLBACK_REQUIRED",
}


def _controls_from_desired(desired_semantic_controls: dict[str, Any] | list[str] | tuple[str, ...] | None) -> list[str]:
    if desired_semantic_controls is None:
        return []
    if isinstance(desired_semantic_controls, dict):
        return list(desired_semantic_controls)
    return [str(item) for item in desired_semantic_controls]


def _threshold(workflow_stage: str, required_confidence: float | None, source_risk: str) -> tuple[float, list[str]]:
    threshold = required_confidence
    if threshold is None:
        threshold = WORKFLOW_MIN_CONFIDENCE.get(workflow_stage, WORKFLOW_MIN_CONFIDENCE["default"])
    reasons: list[str] = []
    if source_risk in {"high", "unsafe", "ai_artifact_high", "already_mastered"}:
        threshold = min(0.98, float(threshold) + 0.05)
        reasons.append("SOURCE_RISK_RAISED_THRESHOLD")
    return float(threshold), reasons


def evaluate_adapter_confidence(
    *,
    desired_semantic_controls: dict[str, Any] | list[str] | tuple[str, ...] | None,
    adapter: dict[str, Any] | None,
    plugin_name: str | None = None,
    plugin_detected: bool = True,
    required_confidence: float | None = None,
    workflow_stage: str = "default",
    source_risk: str = "normal",
    required_controls: list[str] | None = None,
    fallback: str | None = None,
    user_override_mode: bool = False,
    source_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    threshold, reason_codes = _threshold(workflow_stage, required_confidence, source_risk)
    warnings: list[str] = []
    controls_requested = required_controls or _controls_from_desired(desired_semantic_controls)
    controls_allowed: dict[str, Any] = {}
    controls_skipped: dict[str, Any] = {}
    required_missing: list[str] = []

    if user_override_mode:
        warnings.append("User override requested, but adapter validation and semantic gates still apply.")

    if not plugin_detected:
        reason_codes.append("PLUGIN_NOT_DETECTED")
    if not isinstance(adapter, dict):
        reason_codes.append("ADAPTER_MISSING")
        for semantic in controls_requested:
            controls_skipped[semantic] = {"reason": "ADAPTER_MISSING"}
        return _result(False, controls_allowed, controls_skipped, controls_requested, reason_codes, fallback, warnings, threshold)

    adapter_confidence = safe_float(adapter.get("confidence"), 0.0)
    if adapter_confidence < threshold:
        reason_codes.append("ADAPTER_CONFIDENCE_LOW")
    if adapter.get("validation", {}).get("status") != "passed":
        reason_codes.append("VALIDATION_MISSING")
    if not adapter.get("safe_for_automix", False):
        reason_codes.append("VALIDATION_MISSING")

    controls = adapter.get("semantic_controls", {}) if isinstance(adapter.get("semantic_controls"), dict) else {}
    for semantic in controls_requested:
        control = controls.get(semantic)
        if not isinstance(control, dict):
            required_missing.append(semantic)
            controls_skipped[semantic] = {"reason": "SEMANTIC_CONTROL_MISSING"}
            reason_codes.append("SEMANTIC_CONTROL_MISSING")
            continue
        conf = safe_float(control.get("confidence"), 0.0)
        if conf < threshold:
            controls_skipped[semantic] = {"reason": "SEMANTIC_CONTROL_CONFIDENCE_LOW", "confidence": conf, "required": threshold}
            reason_codes.append("SEMANTIC_CONTROL_CONFIDENCE_LOW")
            continue
        if not control_is_write_safe(control, threshold):
            controls_skipped[semantic] = {"reason": "SEMANTIC_CONTROL_NOT_WRITE_ALLOWED", "confidence": conf}
            reason_codes.append("SEMANTIC_CONTROL_NOT_WRITE_ALLOWED")
            continue
        if control.get("safe_min") is None or control.get("safe_max") is None:
            controls_skipped[semantic] = {"reason": "SAFE_RANGE_MISSING"}
            reason_codes.append("SAFE_RANGE_MISSING")
            continue
        controls_allowed[semantic] = {
            "target_name": control.get("target_name"),
            "confidence": conf,
            "safe_min": control.get("safe_min"),
            "safe_max": control.get("safe_max"),
        }

    policy = evaluate_third_party_policy(
        plugin_name or (adapter.get("plugin_name_patterns") or [""])[0],
        adapter,
        source_context=source_context,
        min_confidence=threshold,
    )
    if not policy.get("allowed", True):
        reason_codes.append("THIRD_PARTY_POLICY_BLOCKED")
        warnings.extend(policy.get("warnings", []))

    reason_codes = sorted(set(reason_codes))
    allowed = bool(
        plugin_detected
        and not reason_codes
        and not required_missing
        and len(controls_allowed) == len(controls_requested)
    )
    return _result(allowed, controls_allowed, controls_skipped, required_missing, reason_codes, fallback, warnings, threshold)


def _result(
    allowed: bool,
    controls_allowed: dict[str, Any],
    controls_skipped: dict[str, Any],
    required_missing: list[str],
    reason_codes: list[str],
    fallback: str | None,
    warnings: list[str],
    threshold: float,
) -> dict[str, Any]:
    if not allowed and "FALLBACK_REQUIRED" not in reason_codes:
        reason_codes.append("FALLBACK_REQUIRED")
    return {
        "schema": GATE_VERSION,
        "allowed": allowed,
        "controls_allowed": controls_allowed,
        "controls_skipped": controls_skipped,
        "required_missing": required_missing,
        "reason_codes": sorted(set(reason_codes)),
        "fallback_required": not allowed,
        "fallback": fallback,
        "warnings": sorted(set(warnings)),
        "required_confidence": threshold,
    }


def apply_gate_to_chain_item(
    item: dict[str, Any],
    *,
    adapter: dict[str, Any] | None = None,
    workflow_stage: str = "default",
    source_risk: str = "normal",
) -> dict[str, Any]:
    semantic_settings = item.get("semantic_settings", {})
    gate = evaluate_adapter_confidence(
        desired_semantic_controls=semantic_settings,
        adapter=adapter,
        plugin_name=item.get("plugin"),
        plugin_detected=bool(item.get("plugin")) and item.get("plugin") != "unmapped",
        workflow_stage=workflow_stage,
        source_risk=source_risk,
        fallback=item.get("stock_fallback") or item.get("plugin"),
    )
    out = dict(item)
    out["adapter_confidence_gate"] = gate
    out["adapter_confidence_gate_enforced"] = True
    if semantic_settings:
        out["safe_to_apply"] = bool(out.get("safe_to_apply", False) and gate["allowed"])
        out["requires_parameter_discovery"] = bool(out.get("requires_parameter_discovery", False) or gate["fallback_required"])
    return out

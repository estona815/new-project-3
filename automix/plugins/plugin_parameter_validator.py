from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

from automix.plugins.plugin_adapter_schema import now_utc, safe_float, slugify, validate_adapter_schema, write_json


VALIDATOR_VERSION = "automix-plugin-parameter-validator-v1"


def _fail_all_controls(adapter: dict[str, Any], note: str) -> None:
    for control in adapter.get("semantic_controls", {}).values():
        if not isinstance(control, dict):
            continue
        control["write_allowed"] = False
        control["writable"] = False
        control["validated"] = False
        control["validation_notes"] = note


def validate_adapter(
    adapter: dict[str, Any],
    *,
    output_dir: Path | None = None,
    plugin_available: bool = False,
    validation_observations: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    updated = deepcopy(adapter)
    observations = validation_observations or {}
    controls_observed = observations.get("controls", {}) if isinstance(observations, dict) else {}
    report_controls: dict[str, Any] = {}
    schema_errors = validate_adapter_schema({**updated, "safe_for_automix": False})

    if not plugin_available:
        _fail_all_controls(updated, "validation unavailable because plugin was not confirmed available")
        status = "validation_unavailable"
        reason_codes = ["PLUGIN_NOT_AVAILABLE_FOR_VALIDATION"]
    elif not controls_observed:
        _fail_all_controls(updated, "validation observations missing; no parameter writes allowed")
        status = "validation_unavailable"
        reason_codes = ["VALIDATION_OBSERVATIONS_MISSING"]
    elif schema_errors:
        _fail_all_controls(updated, "schema validation failed; no parameter writes allowed")
        status = "failed"
        reason_codes = ["ADAPTER_SCHEMA_INVALID"]
    else:
        passed_count = 0
        reason_codes = []
        for semantic, control in updated.get("semantic_controls", {}).items():
            observed = controls_observed.get(semantic, {}) if isinstance(controls_observed, dict) else {}
            passed = bool(observed.get("passed", False))
            if passed:
                confidence = max(safe_float(control.get("confidence"), 0.0), safe_float(observed.get("confidence"), 0.0))
                control["confidence"] = min(confidence, 1.0)
                control["write_allowed"] = control["confidence"] >= 0.85
                control["writable"] = control["write_allowed"]
                control["validated"] = control["write_allowed"]
                control["validation_notes"] = observed.get("notes", "semantic response validated")
                if control["write_allowed"]:
                    passed_count += 1
            else:
                control["write_allowed"] = False
                control["writable"] = False
                control["validated"] = False
                control["validation_notes"] = observed.get("notes", "semantic response not validated")
        status = "passed" if passed_count > 0 else "failed"
        if passed_count == 0:
            reason_codes.append("NO_CONTROL_VALIDATED")

    for semantic, control in updated.get("semantic_controls", {}).items():
        if isinstance(control, dict):
            report_controls[semantic] = {
                "target_name": control.get("target_name"),
                "confidence": control.get("confidence"),
                "write_allowed": control.get("write_allowed"),
                "validated": control.get("validated"),
                "notes": control.get("validation_notes"),
            }

    control_values = list(updated.get("semantic_controls", {}).values())
    write_safe_controls = [
        c for c in control_values if isinstance(c, dict) and c.get("write_allowed") and c.get("validated")
    ]
    adapter_confidence = max((safe_float(c.get("confidence"), 0.0) for c in write_safe_controls), default=0.0)
    updated["confidence"] = adapter_confidence
    updated["safe_for_automix"] = bool(status == "passed" and adapter_confidence >= 0.85 and not schema_errors)
    updated["updated_at"] = now_utc()
    updated["validation"] = {
        "status": status,
        "last_validated_at": now_utc() if status == "passed" else None,
        "validated_by": VALIDATOR_VERSION if status == "passed" else None,
        "reason_codes": reason_codes,
        "schema_errors": schema_errors,
        "notes": (
            "Only controls marked write_allowed=true may be used."
            if status == "passed"
            else "Validation did not prove safe parameter control; adapter remains write-blocked."
        ),
    }

    report = {
        "schema": "automix-plugin-parameter-validation-report-v1",
        "validator_version": VALIDATOR_VERSION,
        "scan_time": now_utc(),
        "plugin_name": (updated.get("plugin_name_patterns") or [updated.get("adapter_id", "unknown")])[0],
        "adapter_id": updated.get("adapter_id"),
        "status": status,
        "safe_for_automix": updated["safe_for_automix"],
        "reason_codes": reason_codes,
        "schema_errors": schema_errors,
        "controls": report_controls,
        "no_fake_success": status != "passed" or bool(write_safe_controls),
    }

    if output_dir:
        filename = f"plugin_parameter_validation_{slugify(updated.get('adapter_id'))}.json"
        write_json(output_dir / "analysis_reports" / filename, report)
    return updated, report

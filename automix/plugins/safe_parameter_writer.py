from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from automix.plugins.plugin_adapter_schema import clamp_semantic_value, control_is_write_safe, now_utc, safe_float, slugify, write_json


SAFE_WRITER_VERSION = "automix-safe-parameter-writer-v1"

WriteCallback = Callable[[dict[str, Any]], bool]


def safe_parameter_write_operation(
    *,
    operation: str,
    plugin_name: str,
    track_name: str,
    semantic_settings: dict[str, Any],
    adapter: dict[str, Any],
    output_dir: Path,
    dry_run: bool = True,
    min_confidence: float = 0.85,
    write_callback: WriteCallback | None = None,
) -> dict[str, Any]:
    controls = adapter.get("semantic_controls", {}) if isinstance(adapter, dict) else {}
    do_not_touch = {
        str(item.get("name", "")).lower()
        for item in adapter.get("do_not_touch_parameters", [])
        if isinstance(item, dict)
    }
    written: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []

    for semantic, raw_value in semantic_settings.items():
        control = controls.get(semantic)
        if not isinstance(control, dict):
            skipped.append({"semantic": semantic, "value": raw_value, "reason": "UNKNOWN_PLUGIN_PARAMETER"})
            continue
        target_name = str(control.get("target_name") or "")
        if target_name.lower() in do_not_touch:
            skipped.append({"semantic": semantic, "target_name": target_name, "value": raw_value, "reason": "DO_NOT_TOUCH_PARAMETER"})
            continue
        if not control_is_write_safe(control, min_confidence):
            skipped.append(
                {
                    "semantic": semantic,
                    "target_name": target_name,
                    "value": raw_value,
                    "reason": "SEMANTIC_CONTROL_NOT_WRITE_ALLOWED",
                    "confidence": safe_float(control.get("confidence"), 0.0),
                }
            )
            continue
        clamped = clamp_semantic_value(adapter, semantic, raw_value)
        if not clamped.get("allowed"):
            skipped.append({"semantic": semantic, "value": raw_value, "reason": clamped.get("reason")})
            continue
        entry = {
            "semantic": semantic,
            "target_name": target_name,
            "input_value": raw_value,
            "clamped_value": clamped["clamped_value"],
            "confidence": control.get("confidence"),
            "dry_run": dry_run,
        }
        if dry_run:
            entry["written"] = False
            entry["reason"] = "DRY_RUN_ONLY"
            written.append(entry)
        elif write_callback:
            entry["written"] = bool(write_callback(entry))
            entry["reason"] = "WRITE_CALLBACK_ACCEPTED" if entry["written"] else "WRITE_CALLBACK_REJECTED"
            written.append(entry)
        else:
            entry["written"] = False
            entry["reason"] = "NO_WRITER_CALLBACK"
            skipped.append(entry)

    status = "dry_run" if dry_run else ("ok" if written and all(item.get("written") for item in written) else "partial_or_blocked")
    log = {
        "schema": SAFE_WRITER_VERSION,
        "operation": operation,
        "scan_time": now_utc(),
        "plugin_name": plugin_name,
        "track_name": track_name,
        "adapter_id": adapter.get("adapter_id") if isinstance(adapter, dict) else None,
        "dry_run": dry_run,
        "status": status,
        "written": written,
        "skipped": skipped,
        "fixed_parameter_indexes_used": False,
        "unknown_parameters_skipped": True,
        "do_not_touch_respected": True,
    }
    timestamp = now_utc().replace(":", "").replace("-", "").replace("Z", "Z")
    path = output_dir / "logs" / f"parameter_write_log_{timestamp}_{slugify(plugin_name)}.json"
    write_json(path, log)
    log["path"] = str(path)
    return log

from __future__ import annotations

import json
import platform
from pathlib import Path
from typing import Any

from automix.plugins.plugin_adapter_schema import (
    adapter_matches_plugin,
    compact_plugin_name,
    normalize_plugin_name,
    now_utc,
    safe_float,
    slugify,
    write_json,
)
from automix.plugins.third_party_plugin_policy import EXPECTED_THIRD_PARTY, is_third_party_plugin, plugin_family


AUDIT_SCHEMA = "automix-plugin-inventory-audit-v1"

STOCK_HINTS = ["reaeq", "reacomp", "reaxcomp", "reapitch", "readelay", "reaverbate", "realimit"]
JSFX_HINTS = ["js:", "js ", "loser/", "utility", "stereo width", "saturation"]


def load_inventory(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {
            "schema": "automix-reaper-plugin-inventory-missing",
            "scan_date_utc": None,
            "reaper": {"version": "unknown", "project_name": "unknown"},
            "tracks": [],
            "detected_plugins": [],
            "insertable_plugins": [],
            "missing_recommended_plugins": [],
            "warnings": ["inventory_file_missing"],
        }
    return json.loads(path.read_text(encoding="utf-8"))


def load_adapters(adapter_dirs: list[Path]) -> list[dict[str, Any]]:
    adapters: list[dict[str, Any]] = []
    for directory in adapter_dirs:
        if not directory.exists():
            continue
        for path in sorted(directory.glob("*.json")):
            try:
                adapters.append(json.loads(path.read_text(encoding="utf-8")))
            except json.JSONDecodeError:
                continue
    return adapters


def _plugin_name(plugin: dict[str, Any] | str) -> str:
    if isinstance(plugin, str):
        return plugin
    return str(plugin.get("name") or plugin.get("detected_name") or plugin.get("display_name") or plugin.get("plugin") or "")


def _normalize_plugins(inventory: dict[str, Any]) -> list[dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for source_key in ("detected_plugins", "plugins_detected", "installed_plugins", "insertable_plugins"):
        for plugin in inventory.get(source_key, []) or []:
            name = _plugin_name(plugin)
            if not name:
                continue
            key = compact_plugin_name(name)
            entry = out.setdefault(
                key,
                {
                    "name": normalize_plugin_name(name),
                    "sources": [],
                    "capabilities": [],
                    "confidence": 0.0,
                    "insertable": False,
                    "existing_on_track": False,
                    "ambiguous": False,
                },
            )
            entry["sources"].append(source_key)
            if isinstance(plugin, dict):
                entry["capabilities"] = sorted(set(entry["capabilities"] + list(plugin.get("capabilities", []) or [])))
                entry["confidence"] = max(entry["confidence"], safe_float(plugin.get("confidence"), 0.0))
                entry["insertable"] = bool(entry["insertable"] or plugin.get("insertable", False) or source_key == "insertable_plugins")
                entry["existing_on_track"] = bool(entry["existing_on_track"] or source_key in {"detected_plugins", "plugins_detected"})
                entry["ambiguous"] = bool(entry["ambiguous"] or plugin.get("ambiguous", False))
    for track in inventory.get("tracks", []) or []:
        for fx in track.get("fx", []) or []:
            name = _plugin_name(fx)
            if not name:
                continue
            key = compact_plugin_name(name)
            entry = out.setdefault(
                key,
                {
                    "name": normalize_plugin_name(name),
                    "sources": [],
                    "capabilities": [],
                    "confidence": 0.0,
                    "insertable": False,
                    "existing_on_track": True,
                    "ambiguous": False,
                },
            )
            entry["sources"].append(f"track:{track.get('track_index')}")
            entry["capabilities"] = sorted(set(entry["capabilities"] + list(fx.get("capabilities", []) or [])))
            entry["confidence"] = max(entry["confidence"], safe_float(fx.get("confidence"), 0.0))
            entry["existing_on_track"] = True
            entry["ambiguous"] = bool(entry["ambiguous"] or fx.get("ambiguous", False))
    return sorted(out.values(), key=lambda item: item["name"].lower())


def _plugin_kind(plugin_name: str) -> str:
    compact = compact_plugin_name(plugin_name)
    lower = plugin_name.lower()
    if any(hint in compact for hint in STOCK_HINTS):
        return "stock"
    if any(hint in lower for hint in JSFX_HINTS):
        return "jsfx"
    if is_third_party_plugin(plugin_name):
        return "third_party"
    return "unknown"


def _adapter_for_plugin(plugin_name: str, adapters: list[dict[str, Any]]) -> dict[str, Any] | None:
    best: dict[str, Any] | None = None
    best_conf = -1.0
    for adapter in adapters:
        if adapter_matches_plugin(adapter, plugin_name):
            conf = safe_float(adapter.get("confidence"), 0.0)
            if conf > best_conf:
                best_conf = conf
                best = adapter
    return best


def audit_plugin_inventory(
    inventory: dict[str, Any] | None = None,
    *,
    output_dir: Path,
    inventory_path: Path | None = None,
    adapters: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    inventory = inventory or load_inventory(inventory_path or output_dir / "plugin_inventory.json")
    if adapters is None:
        adapters = load_adapters([output_dir / "plugins" / "builtin_adapters", output_dir / "plugins" / "learned_adapters"])

    plugins = _normalize_plugins(inventory)
    detected: list[dict[str, Any]] = []
    unsafe_or_unmapped: list[dict[str, Any]] = []
    stock_available = False
    jsfx_available = False
    third_party_available = False

    for plugin in plugins:
        kind = _plugin_kind(plugin["name"])
        stock_available = stock_available or kind == "stock"
        jsfx_available = jsfx_available or kind == "jsfx"
        third_party_available = third_party_available or kind == "third_party"
        adapter = _adapter_for_plugin(plugin["name"], adapters)
        mapped = bool(adapter)
        validated = bool(adapter and adapter.get("safe_for_automix") and adapter.get("validation", {}).get("status") == "passed")
        mapping_status = "validated_safe" if validated else ("mapped_unvalidated" if mapped else "unmapped")
        entry = {
            **plugin,
            "kind": kind,
            "family": plugin_family(plugin["name"]),
            "adapter_id": adapter.get("adapter_id") if adapter else None,
            "mapping_status": mapping_status,
            "safe_for_automix": validated,
            "write_allowed": validated,
        }
        detected.append(entry)
        if not validated:
            unsafe_or_unmapped.append(
                {
                    "name": plugin["name"],
                    "kind": kind,
                    "family": entry["family"],
                    "mapping_status": mapping_status,
                    "reason": "plugin detected but not validated for semantic parameter writes",
                }
            )

    present_families = {plugin_family(item["name"]) for item in detected if plugin_family(item["name"])}
    missing_expected = [
        {
            "plugin": name,
            "normal": True,
            "reason": "optional commercial or third-party plugin not detected; fallback should be used",
        }
        for name in EXPECTED_THIRD_PARTY
        if plugin_family(name) not in present_families
    ]
    missing_expected.extend(
        {
            "plugin": item,
            "normal": True,
            "reason": "reported by REAPER inventory as missing recommended plugin",
        }
        for item in inventory.get("missing_recommended_plugins", []) or []
    )

    audit = {
        "schema": AUDIT_SCHEMA,
        "scan_time": now_utc(),
        "source_inventory_scan_time": inventory.get("scan_date_utc"),
        "reaper_version": inventory.get("reaper", {}).get("version", "unknown"),
        "project_name": inventory.get("reaper", {}).get("project_name", "unknown"),
        "platform": {
            "system": platform.system(),
            "release": platform.release(),
            "python": platform.python_version(),
        },
        "plugins_detected": detected,
        "stock_plugins_available": stock_available,
        "jsfx_available": jsfx_available,
        "third_party_plugins_available": third_party_available,
        "missing_expected_plugins": missing_expected,
        "unsafe_or_unmapped_plugins": unsafe_or_unmapped,
        "summary": {
            "detected_count": len(detected),
            "validated_safe_count": sum(1 for item in detected if item["safe_for_automix"]),
            "unsafe_or_unmapped_count": len(unsafe_or_unmapped),
            "missing_expected_count": len(missing_expected),
        },
        "safety": {
            "inventory_only": True,
            "no_audio_changes": True,
            "no_parameter_writes": True,
            "commercial_plugins_optional": True,
            "unmapped_plugins_are_unsafe": True,
        },
        "warnings": inventory.get("warnings", []) or inventory.get("notes", []),
    }
    write_json(output_dir / "analysis_reports" / "plugin_inventory_audit.json", audit)
    return audit


def write_plugin_capability_report(audit: dict[str, Any], output_dir: Path) -> Path:
    lines = [
        "# Plugin Capability Report",
        "",
        f"- Generated UTC: `{audit.get('scan_time')}`",
        f"- REAPER version: `{audit.get('reaper_version')}`",
        f"- Project: `{audit.get('project_name')}`",
        f"- Detected plugins: `{audit.get('summary', {}).get('detected_count', 0)}`",
        f"- Validated safe plugins: `{audit.get('summary', {}).get('validated_safe_count', 0)}`",
        f"- Unsafe/unmapped plugins: `{audit.get('summary', {}).get('unsafe_or_unmapped_count', 0)}`",
        "",
        "## Safety Position",
        "",
        "- This report does not prove audio quality or plugin behavior.",
        "- Detected third-party plugins remain write-blocked until adapter validation passes.",
        "- Missing commercial plugins are normal and should trigger stock/JSFX fallback planning.",
        "",
        "## Detected Plugins",
        "",
    ]
    if not audit.get("plugins_detected"):
        lines.append("- none detected from the available inventory file")
    for plugin in audit.get("plugins_detected", []):
        lines.append(
            f"- `{plugin.get('name')}`: kind `{plugin.get('kind')}`, mapping `{plugin.get('mapping_status')}`, safe `{plugin.get('safe_for_automix')}`"
        )
    lines.extend(["", "## Missing Expected Optional Plugins", ""])
    for missing in audit.get("missing_expected_plugins", []):
        lines.append(f"- `{missing.get('plugin')}`: {missing.get('reason')}")
    if not audit.get("missing_expected_plugins"):
        lines.append("- none")
    lines.extend(["", "## Fallback Strategy", ""])
    lines.extend(
        [
            "- Pitch: use ReaPitch/manual only after semantic adapter validation.",
            "- EQ/dynamics: prefer validated stock ReaEQ/ReaComp/ReaXcomp adapters; otherwise log as skipped.",
            "- Saturation/OTT/Ozone/Valhalla: optional third-party only, never assumed safe from name matching.",
            "- Unknown plugins: inventory/report only; no automated parameter writes.",
        ]
    )
    path = output_dir / "eval_reports" / "plugin_capability_report.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path

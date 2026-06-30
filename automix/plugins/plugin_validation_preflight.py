from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from automix.plugins.plugin_adapter_schema import now_utc, slugify, write_json


PLUGIN_VALIDATION_PREFLIGHT_SCHEMA = "automix-plugin-validation-preflight-v1"

PREFLIGHT_REL_PATH = Path("eval_reports/plugin_validation_preflight.json")
PREFLIGHT_REPORT_REL_PATH = Path("eval_reports/plugin_validation_preflight.md")

STOCK_PLUGIN_FILES = {
    "ReaComp (Cockos)": ["reacomp.vst.dylib", "reacomp.vst.dylib.rpl"],
    "ReaDelay (Cockos)": ["readelay.vst.dylib", "readelay.vst.dylib.rpl"],
    "ReaEQ (Cockos)": ["reaeq.vst.dylib", "reaeq.vst.dylib.rpl"],
    "ReaVerbate (Cockos)": ["reaverbate.vst.dylib", "reaverbate.vst.dylib.rpl"],
    "ReaXcomp (Cockos)": ["reaxcomp.vst.dylib"],
    "ReaPitch (Cockos)": ["reapitch.vst.dylib"],
    "ReaLimit (Cockos)": ["realimit.vst.dylib"],
}

STANDARD_PLUGIN_DIRS = [
    Path("/Library/Audio/Plug-Ins/VST3"),
    Path("/Library/Audio/Plug-Ins/VST"),
    Path("/Library/Audio/Plug-Ins/Components"),
]


def _load_json(path: Path) -> dict[str, Any] | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _normalize(value: str) -> str:
    return "".join(ch.lower() for ch in value if ch.isalnum())


def _safe_path(path: Path) -> dict[str, Any]:
    return {
        "path": str(path),
        "exists": path.exists(),
        "is_file": path.is_file(),
        "is_dir": path.is_dir(),
    }


def _stock_fx_dir(reaper_app: Path) -> Path:
    return reaper_app / "Contents" / "Plugins" / "FX"


def _user_effects_dir(reaper_resource_dir: Path) -> Path:
    return reaper_resource_dir / "Effects"


def _find_stock_plugin(name: str, *, reaper_app: Path) -> list[str]:
    fx_dir = _stock_fx_dir(reaper_app)
    return [str(fx_dir / filename) for filename in STOCK_PLUGIN_FILES.get(name, []) if (fx_dir / filename).exists()]


def _find_jsfx(name: str, *, reaper_resource_dir: Path) -> list[str]:
    if not name.lower().endswith(".jsfx"):
        return []
    candidate = _user_effects_dir(reaper_resource_dir) / name
    if candidate.exists():
        return [str(candidate)]
    compact_target = _normalize(Path(name).name)
    matches: list[str] = []
    effects = _user_effects_dir(reaper_resource_dir)
    if effects.exists():
        for path in effects.rglob("*.jsfx"):
            if _normalize(path.name) == compact_target:
                matches.append(str(path))
    return sorted(set(matches))


def _find_standard_plugin(name: str, *, extra_dirs: list[Path]) -> list[str]:
    compact = _normalize(name)
    dirs = STANDARD_PLUGIN_DIRS + [Path.home() / "Library" / "Audio" / "Plug-Ins" / "VST3", Path.home() / "Library" / "Audio" / "Plug-Ins" / "VST", Path.home() / "Library" / "Audio" / "Plug-Ins" / "Components"] + extra_dirs
    matches: list[str] = []
    for directory in dirs:
        if not directory.exists():
            continue
        for path in directory.rglob("*"):
            if path.is_file() and compact and compact in _normalize(path.name):
                matches.append(str(path))
    return sorted(set(matches))


def _required_plugin_names(readiness: dict[str, Any]) -> list[str]:
    names = set(readiness.get("missing_or_unsafe_mappings", []))
    names.update(readiness.get("stock_fallbacks_available", []))
    names.update(readiness.get("jsfx_fallbacks_available", []))
    detected = readiness.get("plugins_detected", [])
    if isinstance(detected, list):
        names.update(str(item.get("name", "")) for item in detected if isinstance(item, dict))
    return sorted(name for name in names if str(name).strip() and not str(name).startswith("validated "))


def _load_validation_reports(validation_reports_dir: Path) -> list[dict[str, Any]]:
    reports: list[dict[str, Any]] = []
    for path in sorted(validation_reports_dir.glob("plugin_parameter_validation_*.json")):
        data = _load_json(path)
        if not data:
            reports.append({"path": str(path), "json_valid": False})
            continue
        reports.append(
            {
                "path": str(path),
                "json_valid": True,
                "adapter_id": data.get("adapter_id", ""),
                "plugin_name": data.get("plugin_name", ""),
                "status": data.get("status", ""),
                "safe_for_automix": bool(data.get("safe_for_automix", False)),
                "reason_codes": data.get("reason_codes", []),
            }
        )
    return reports


def _availability_record(name: str, *, reaper_app: Path, reaper_resource_dir: Path, extra_plugin_dirs: list[Path]) -> dict[str, Any]:
    if name in STOCK_PLUGIN_FILES:
        category = "stock"
        paths = _find_stock_plugin(name, reaper_app=reaper_app)
    elif name.lower().endswith(".jsfx"):
        category = "jsfx"
        paths = _find_jsfx(name, reaper_resource_dir=reaper_resource_dir)
    else:
        category = "third_party_or_unknown"
        paths = _find_standard_plugin(name, extra_dirs=extra_plugin_dirs)
    return {
        "name": name,
        "category": category,
        "available": bool(paths),
        "candidate_paths": paths,
        "availability_only": True,
        "safe_for_parameter_write": False,
        "notes": "Presence on disk does not validate semantic parameter writes.",
    }


def build_plugin_validation_preflight(
    *,
    project_name: str,
    output_dir: Path,
    reaper_app: Path | None = None,
    reaper_resource_dir: Path | None = None,
    plugin_readiness_path: Path | None = None,
    validation_reports_dir: Path | None = None,
    extra_plugin_dirs: list[Path] | None = None,
    output_path: Path | None = None,
) -> dict[str, Any]:
    output_dir = Path(output_dir)
    reaper_app = Path(reaper_app or Path("/Applications") / "REAPER.app")
    reaper_resource_dir = Path(reaper_resource_dir or Path.home() / "Library" / "Application Support" / "REAPER")
    plugin_readiness_path = Path(plugin_readiness_path or output_dir / "eval_reports" / "real_project_plugin_readiness.json")
    validation_reports_dir = Path(validation_reports_dir or output_dir / "analysis_reports")
    extra_plugin_dirs = [Path(path) for path in (extra_plugin_dirs or [])]

    readiness = _load_json(plugin_readiness_path) or {}
    required_plugins = _required_plugin_names(readiness)
    availability = [
        _availability_record(name, reaper_app=reaper_app, reaper_resource_dir=reaper_resource_dir, extra_plugin_dirs=extra_plugin_dirs)
        for name in required_plugins
    ]
    validation_reports = _load_validation_reports(validation_reports_dir)
    safe_validation_reports = [item for item in validation_reports if item.get("safe_for_automix")]
    unavailable_reports = [item for item in validation_reports if item.get("status") == "validation_unavailable"]
    missing = [item["name"] for item in availability if not item.get("available")]

    blockers: list[str] = []
    if not reaper_app.exists():
        blockers.append("reaper_app_not_found")
    if not reaper_resource_dir.exists():
        blockers.append("reaper_resource_dir_not_found")
    blockers.extend(f"required_plugin_availability_missing:{name}" for name in missing)
    if not bool(readiness.get("safe_draft_plugin_ready", False)):
        blockers.append("semantic_parameter_validation_required")

    warnings: list[str] = []
    if availability and any(item.get("available") for item in availability):
        warnings.append("availability_does_not_grant_write_safety")
    if unavailable_reports:
        warnings.append("adapter_validation_reports_unavailable")
    if not validation_reports:
        warnings.append("adapter_validation_reports_missing")

    safe_to_write = bool(readiness.get("safe_draft_plugin_ready", False) and safe_validation_reports and not missing)
    status = "write_safe_ready" if safe_to_write else "semantic_validation_required"
    if missing:
        status = "availability_or_validation_incomplete"

    preflight = {
        "schema": PLUGIN_VALIDATION_PREFLIGHT_SCHEMA,
        "project_name": project_name or readiness.get("project_name", ""),
        "created_at": now_utc(),
        "output_dir": str(output_dir),
        "paths": {
            "reaper_app": _safe_path(reaper_app),
            "reaper_stock_fx_dir": _safe_path(_stock_fx_dir(reaper_app)),
            "reaper_resource_dir": _safe_path(reaper_resource_dir),
            "user_effects_dir": _safe_path(_user_effects_dir(reaper_resource_dir)),
            "plugin_readiness": _safe_path(plugin_readiness_path),
            "validation_reports_dir": _safe_path(validation_reports_dir),
        },
        "required_plugins": required_plugins,
        "availability": availability,
        "validation_reports": validation_reports,
        "summary": {
            "required_plugins_total": len(required_plugins),
            "available_plugins_total": sum(1 for item in availability if item.get("available")),
            "missing_plugins_total": len(missing),
            "validation_reports_total": len(validation_reports),
            "safe_validation_reports_total": len(safe_validation_reports),
            "validation_unavailable_reports_total": len(unavailable_reports),
            "readiness_safe_draft_plugin_ready": bool(readiness.get("safe_draft_plugin_ready", False)),
            "safe_to_write_parameters": safe_to_write,
        },
        "status": status,
        "blockers": sorted(set(blockers)),
        "warnings": sorted(set(warnings)),
        "limits": [
            "This preflight reads local plugin files and reports only; it does not open REAPER, insert FX, write parameters, render, or save a project.",
            "A plugin or JSFX file being present is not proof of semantic parameter write safety.",
            "safe_to_write_parameters becomes true only when readiness evidence and validation reports prove safe semantic controls.",
        ],
    }
    target = output_path or output_dir / PREFLIGHT_REL_PATH
    write_json(target, preflight)
    write_plugin_validation_preflight_report(preflight, output_dir)
    return preflight


def write_plugin_validation_preflight_report(preflight: dict[str, Any], output_dir: Path) -> Path:
    summary = preflight.get("summary", {})
    lines = [
        "# Plugin Validation Preflight",
        "",
        f"- Project: `{preflight.get('project_name')}`",
        f"- Created UTC: `{preflight.get('created_at')}`",
        f"- Status: `{preflight.get('status')}`",
        f"- Safe to write parameters: `{summary.get('safe_to_write_parameters', False)}`",
        f"- Required plugins: `{summary.get('required_plugins_total', 0)}`",
        f"- Available plugins: `{summary.get('available_plugins_total', 0)}`",
        f"- Missing plugins: `{summary.get('missing_plugins_total', 0)}`",
        f"- Safe validation reports: `{summary.get('safe_validation_reports_total', 0)}`",
        "",
        "This is an inventory-only preflight. It does not prove plugin parameter write safety.",
        "",
        "## Blockers",
        "",
    ]
    lines.extend([f"- `{item}`" for item in preflight.get("blockers", [])] or ["- none"])
    lines.extend(["", "## Warnings", ""])
    lines.extend([f"- `{item}`" for item in preflight.get("warnings", [])] or ["- none"])
    lines.extend(["", "## Availability", ""])
    for item in preflight.get("availability", []):
        paths = ", ".join(item.get("candidate_paths", [])[:3]) or "none"
        lines.append(f"- `{item.get('name')}` `{item.get('category')}` available=`{item.get('available')}` paths=`{paths}`")
    if not preflight.get("availability"):
        lines.append("- none")
    lines.extend(["", "## Validation Reports", ""])
    for item in preflight.get("validation_reports", []):
        lines.append(
            f"- `{item.get('adapter_id') or slugify(item.get('plugin_name', 'unknown'))}` status=`{item.get('status')}` safe=`{item.get('safe_for_automix')}`"
        )
    if not preflight.get("validation_reports"):
        lines.append("- none")
    path = Path(output_dir) / PREFLIGHT_REPORT_REL_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return path

from __future__ import annotations

import hashlib
import json
import platform
import plistlib
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

from automix.plugins.plugin_adapter_schema import now_utc, write_json
from automix.plugins.plugin_validation_preflight import STOCK_PLUGIN_FILES


LOCAL_DEVICE_QC_SCHEMA = "automix-local-device-qc-v1"

JSON_REL_PATH = Path("eval_reports/local_device_qc.json")
MD_REL_PATH = Path("eval_reports/local_device_qc.md")

REQUIRED_JSFX = {
    "Codex Vocal/vocal_ai_artifact_split_tamer.jsfx": "suno_ai_artifact_required_first_slot",
    "Vocal Clarity Repair/vocal_air_guard.jsfx": "post_ott_air_guard",
    "Vocal Clarity Repair/vocal_demud_dynamic_eq.jsfx": "demud_dynamic_eq",
    "Vocal Clarity Repair/vocal_output_guard.jsfx": "output_guard",
    "Vocal Clarity Repair/vocal_presence_enhancer.jsfx": "presence_enhancer",
}

COMMANDS = ["python3", "pytest", "afinfo", "ffmpeg", "ffprobe", "sox"]

GATE_SPECS = [
    {
        "name": "plugin_validation_preflight",
        "rel": "eval_reports/plugin_validation_preflight.json",
        "ready_keys": ["safe_to_write_parameters"],
        "summary_ready_keys": ["safe_to_write_parameters"],
    },
    {
        "name": "plugin_semantic_validation_gate",
        "rel": "eval_reports/plugin_semantic_validation_gate.json",
        "ready_keys": ["semantic_validation_ready", "safe_to_write_parameters"],
    },
    {
        "name": "runtime_collector_package",
        "rel": "eval_reports/plugin_semantic_validation_runtime_collector_package.json",
        "ready_keys": ["ready_for_reaper_runtime_collection"],
    },
    {
        "name": "runtime_collector_safety_audit",
        "rel": "eval_reports/reaper_runtime_collector_safety_audit.json",
        "pass_keys": ["passed"],
    },
    {
        "name": "runtime_observation_gate",
        "rel": "eval_reports/plugin_semantic_validation_runtime_observation_gate.json",
        "ready_keys": ["runtime_observations_ready", "ready_for_manual_report_authoring"],
    },
    {
        "name": "runtime_evidence_gate",
        "rel": "eval_reports/plugin_semantic_validation_runtime_evidence_gate.json",
        "ready_keys": ["ready_for_semantic_gate_rerun", "runtime_evidence_ready"],
    },
    {
        "name": "source_acceptance",
        "rel": "eval_reports/source_acceptance_gate.json",
        "ready_keys": ["accepted_export_source_ready"],
    },
    {
        "name": "final_render_evidence",
        "rel": "eval_reports/final_render_evidence_gate.json",
        "ready_keys": ["ready_for_final_qc"],
    },
    {
        "name": "final_qc_evidence",
        "rel": "eval_reports/final_qc_evidence_gate.json",
        "ready_keys": ["ready_for_approval_readiness"],
    },
    {
        "name": "ab_preview_evidence",
        "rel": "eval_reports/ab_preview_evidence_gate.json",
        "ready_keys": ["ready_for_human_ab_review"],
    },
    {
        "name": "approval_export_readiness",
        "rel": "eval_reports/approval_export_readiness.json",
        "ready_keys": ["ready_for_approval_export"],
    },
    {
        "name": "path_hygiene",
        "rel": "eval_reports/path_hygiene_audit.json",
        "pass_keys": ["passed"],
    },
    {
        "name": "requirements_traceability",
        "rel": "eval_reports/requirements_traceability_audit.json",
        "pass_keys": ["passed"],
    },
    {
        "name": "processing_policy",
        "rel": "eval_reports/processing_policy_audit.json",
        "pass_keys": ["passed"],
    },
]


def _load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _safe_path(path: Path) -> dict[str, Any]:
    return {
        "path": str(path),
        "exists": path.exists(),
        "is_file": path.is_file(),
        "is_dir": path.is_dir(),
    }


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _file_evidence(path: Path) -> dict[str, Any]:
    record = _safe_path(path)
    record.update({"size_bytes": 0, "mtime_ns": 0, "sha256": "", "fingerprint_error": ""})
    if not path.is_file():
        return record
    try:
        stat = path.stat()
        record["size_bytes"] = stat.st_size
        record["mtime_ns"] = stat.st_mtime_ns
        record["sha256"] = _sha256_file(path)
    except OSError as exc:
        record["fingerprint_error"] = exc.__class__.__name__
    return record


def _reaper_info_plist(reaper_app: Path) -> Path:
    return reaper_app / "Contents" / "Info.plist"


def _reaper_app_metadata(reaper_app: Path) -> dict[str, Any]:
    plist_path = _reaper_info_plist(reaper_app)
    data: dict[str, Any] = {}
    parse_error = ""
    if plist_path.is_file():
        try:
            with plist_path.open("rb") as handle:
                loaded = plistlib.load(handle)
            data = loaded if isinstance(loaded, dict) else {}
        except (OSError, plistlib.InvalidFileException) as exc:
            parse_error = exc.__class__.__name__
    return {
        "info_plist": _file_evidence(plist_path),
        "bundle_identifier": str(data.get("CFBundleIdentifier", "")),
        "bundle_name": str(data.get("CFBundleName", "")),
        "version": str(data.get("CFBundleShortVersionString", "")),
        "build": str(data.get("CFBundleVersion", "")),
        "minimum_system_version": str(data.get("LSMinimumSystemVersion", "")),
        "parse_error": parse_error,
    }


def _command_path(command: str, command_overrides: dict[str, str | None] | None = None) -> str | None:
    if command_overrides and command in command_overrides:
        return command_overrides[command]
    return shutil.which(command)


def _command_record(command: str, command_overrides: dict[str, str | None] | None = None) -> dict[str, Any]:
    path = _command_path(command, command_overrides)
    record: dict[str, Any] = {"command": command, "path": path or "", "available": bool(path), "version": ""}
    if not path:
        return record
    version_args = {
        "python3": ["--version"],
        "pytest": ["--version"],
        "ffmpeg": ["-version"],
        "ffprobe": ["-version"],
        "sox": ["--version"],
        "afinfo": [],
    }.get(command, ["--version"])
    if not version_args:
        return record
    try:
        result = subprocess.run([path, *version_args], check=False, capture_output=True, text=True, timeout=3)
    except (OSError, subprocess.SubprocessError):
        return record
    first_line = (result.stdout or result.stderr).splitlines()
    record["version"] = first_line[0][:180] if first_line else ""
    return record


def _stock_fx_dir(reaper_app: Path) -> Path:
    return reaper_app / "Contents" / "Plugins" / "FX"


def _reaper_binary(reaper_app: Path) -> Path:
    return reaper_app / "Contents" / "MacOS" / "REAPER"


def _resource_effects_dir(reaper_resource_dir: Path) -> Path:
    return reaper_resource_dir / "Effects"


def _stock_plugin_records(reaper_app: Path) -> list[dict[str, Any]]:
    fx_dir = _stock_fx_dir(reaper_app)
    records: list[dict[str, Any]] = []
    for name, filenames in STOCK_PLUGIN_FILES.items():
        candidates = [fx_dir / filename for filename in filenames]
        present = [path for path in candidates if path.exists()]
        records.append(
            {
                "name": name,
                "present": bool(present),
                "candidate_paths": [str(path) for path in candidates],
                "present_paths": [str(path) for path in present],
                "present_files": [_file_evidence(path) for path in present],
            }
        )
    return records


def _jsfx_records(reaper_resource_dir: Path) -> list[dict[str, Any]]:
    effects = _resource_effects_dir(reaper_resource_dir)
    records: list[dict[str, Any]] = []
    for rel, purpose in REQUIRED_JSFX.items():
        path = effects / rel
        fallback_matches = []
        if not path.exists() and effects.exists():
            target = Path(rel).name.lower()
            fallback_matches = [str(item) for item in sorted(effects.rglob("*.jsfx")) if item.name.lower() == target]
        records.append(
            {
                "relative_path": rel,
                "purpose": purpose,
                "path": str(path),
                "present": path.exists(),
                "fallback_matches": fallback_matches,
                "file_evidence": _file_evidence(path),
                "fallback_file_evidence": [_file_evidence(Path(item)) for item in fallback_matches[:10]],
            }
        )
    return records


def _render_inventory(workspace_root: Path, limit: int = 20) -> dict[str, Any]:
    renders = workspace_root / "renders"
    suffixes = {".wav", ".mp3", ".flac", ".aif", ".aiff", ".m4a"}
    files = [path for path in renders.rglob("*") if path.is_file() and path.suffix.lower() in suffixes] if renders.exists() else []
    files = sorted(files, key=lambda path: path.stat().st_mtime if path.exists() else 0, reverse=True)
    samples = [
        {
            "path": str(path),
            "relative_path": str(path.relative_to(workspace_root)) if path.is_relative_to(workspace_root) else str(path),
            "suffix": path.suffix.lower(),
            "size_bytes": path.stat().st_size,
        }
        for path in files[:limit]
    ]
    return {
        "renders_dir": str(renders),
        "renders_dir_exists": renders.exists(),
        "audio_files_total": len(files),
        "wav_total": sum(1 for path in files if path.suffix.lower() == ".wav"),
        "mp3_total": sum(1 for path in files if path.suffix.lower() == ".mp3"),
        "recent_audio_files": samples,
    }


def _ready_from_keys(data: dict[str, Any], keys: list[str], summary_keys: list[str] | None = None) -> bool:
    if any(bool(data.get(key)) for key in keys):
        return True
    summary = data.get("summary", {}) if isinstance(data.get("summary"), dict) else {}
    return any(bool(summary.get(key)) for key in (summary_keys or []))


def _gate_record(spec: dict[str, Any], output_dir: Path) -> dict[str, Any]:
    path = output_dir / spec["rel"]
    data = _load_json(path)
    found = bool(data)
    pass_keys = spec.get("pass_keys", [])
    ready_keys = spec.get("ready_keys", [])
    passed = _ready_from_keys(data, pass_keys) if pass_keys else None
    ready = _ready_from_keys(data, ready_keys, spec.get("summary_ready_keys", [])) if ready_keys else bool(passed)
    blockers = data.get("blockers", []) if isinstance(data.get("blockers", []), list) else []
    warnings = data.get("warnings", []) if isinstance(data.get("warnings", []), list) else []
    return {
        "name": spec["name"],
        "path": str(path),
        "found": found,
        "status": data.get("status", ""),
        "passed": passed,
        "ready": ready,
        "blockers": blockers[:25],
        "warnings": warnings[:25],
        "blockers_total": len(blockers),
        "warnings_total": len(warnings),
    }


def build_local_device_qc(
    *,
    project_name: str,
    output_dir: Path,
    workspace_root: Path | None = None,
    reaper_app: Path | None = None,
    reaper_resource_dir: Path | None = None,
    command_overrides: dict[str, str | None] | None = None,
    output_path: Path | None = None,
) -> dict[str, Any]:
    workspace_root = Path(workspace_root or Path.cwd())
    output_dir = Path(output_dir)
    reaper_app = Path(reaper_app or Path("/Applications") / "REAPER.app")
    reaper_resource_dir = Path(reaper_resource_dir or Path.home() / "Library" / "Application Support" / "REAPER")
    commands = [_command_record(command, command_overrides) for command in COMMANDS]
    command_map = {item["command"]: item for item in commands}
    stock_plugins = _stock_plugin_records(reaper_app)
    jsfx = _jsfx_records(reaper_resource_dir)
    reaper_metadata = _reaper_app_metadata(reaper_app)
    gates = [_gate_record(spec, output_dir) for spec in GATE_SPECS]
    gate_map = {item["name"]: item for item in gates}
    final_qc_analyzer = workspace_root / "automix" / "export" / "final_qc_analyzer.py"

    blockers: list[str] = []
    warnings: list[str] = []
    if not reaper_app.exists():
        blockers.append("reaper_app_missing")
    if not _reaper_binary(reaper_app).exists():
        blockers.append("reaper_binary_missing")
    if not reaper_resource_dir.exists():
        blockers.append("reaper_resource_dir_missing")
    if not _resource_effects_dir(reaper_resource_dir).exists():
        blockers.append("reaper_effects_dir_missing")
    if not final_qc_analyzer.exists():
        blockers.append("final_qc_analyzer_missing")
    if reaper_app.exists() and not reaper_metadata["info_plist"]["exists"]:
        warnings.append("reaper_info_plist_missing")
    if reaper_metadata.get("parse_error"):
        warnings.append("reaper_info_plist_unreadable")
    for item in jsfx:
        if not item["present"] and item["relative_path"] == "Codex Vocal/vocal_ai_artifact_split_tamer.jsfx":
            blockers.append("required_codex_vocal_ai_artifact_split_tamer_missing")
        elif not item["present"]:
            warnings.append(f"optional_vocal_clarity_jsfx_missing:{item['relative_path']}")
    missing_stock = [item["name"] for item in stock_plugins if not item["present"]]
    warnings.extend(f"stock_plugin_file_missing:{name}" for name in missing_stock)
    if not command_map["afinfo"]["available"] and not command_map["ffprobe"]["available"]:
        warnings.append("external_audio_metadata_tool_missing")
    if not command_map["ffmpeg"]["available"]:
        warnings.append("ffmpeg_missing_mp3_export_or_filter_qc_limited")
    if not command_map["ffprobe"]["available"]:
        warnings.append("ffprobe_missing_external_probe_limited")
    if not gate_map["plugin_semantic_validation_gate"]["ready"]:
        warnings.append("plugin_semantic_validation_not_ready_for_parameter_writes")
    if not gate_map["runtime_collector_package"]["ready"]:
        warnings.append("runtime_collector_package_not_ready")
    if not gate_map["runtime_collector_safety_audit"]["ready"]:
        warnings.append("runtime_collector_safety_audit_not_ready")
    if not gate_map["source_acceptance"]["ready"]:
        warnings.append("accepted_source_not_ready")
    if not gate_map["final_render_evidence"]["ready"]:
        warnings.append("final_render_evidence_not_ready")
    if not gate_map["final_qc_evidence"]["ready"]:
        warnings.append("final_qc_evidence_not_ready")
    if not gate_map["ab_preview_evidence"]["ready"]:
        warnings.append("ab_preview_evidence_not_ready")

    local_ready = not blockers
    runtime_collection_ready = bool(
        local_ready
        and gate_map["runtime_collector_package"]["ready"]
        and gate_map["runtime_collector_safety_audit"]["ready"]
    )
    parameter_write_ready = bool(
        local_ready
        and gate_map["plugin_validation_preflight"]["ready"]
        and gate_map["plugin_semantic_validation_gate"]["ready"]
        and gate_map["runtime_evidence_gate"]["ready"]
    )
    delivery_ready = bool(
        parameter_write_ready
        and gate_map["source_acceptance"]["ready"]
        and gate_map["final_render_evidence"]["ready"]
        and gate_map["final_qc_evidence"]["ready"]
        and gate_map["ab_preview_evidence"]["ready"]
        and gate_map["approval_export_readiness"]["ready"]
    )
    qc = {
        "schema": LOCAL_DEVICE_QC_SCHEMA,
        "project_name": project_name,
        "created_at": now_utc(),
        "workspace_root": str(workspace_root),
        "output_dir": str(output_dir),
        "platform": {
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
            "python": platform.python_version(),
            "current_executable": sys.executable,
        },
        "commands": commands,
        "paths": {
            "reaper_app": _safe_path(reaper_app),
            "reaper_binary": _safe_path(_reaper_binary(reaper_app)),
            "reaper_info_plist": _safe_path(_reaper_info_plist(reaper_app)),
            "reaper_stock_fx_dir": _safe_path(_stock_fx_dir(reaper_app)),
            "reaper_resource_dir": _safe_path(reaper_resource_dir),
            "reaper_effects_dir": _safe_path(_resource_effects_dir(reaper_resource_dir)),
            "final_qc_analyzer": _safe_path(final_qc_analyzer),
        },
        "file_evidence": {
            "reaper_binary": _file_evidence(_reaper_binary(reaper_app)),
            "reaper_info_plist": reaper_metadata["info_plist"],
            "final_qc_analyzer": _file_evidence(final_qc_analyzer),
        },
        "reaper_app_metadata": reaper_metadata,
        "stock_plugins": stock_plugins,
        "required_jsfx": jsfx,
        "render_inventory": _render_inventory(workspace_root),
        "gate_status": gates,
        "readiness": {
            "local_device_qc_ready": local_ready,
            "ready_for_reaper_runtime_collection": runtime_collection_ready,
            "ready_for_applied_parameter_writes": parameter_write_ready,
            "ready_for_delivery_claims": delivery_ready,
            "report_only": True,
            "opens_reaper": False,
            "renders_audio": False,
            "writes_parameters": False,
            "saves_project": False,
        },
        "blockers": sorted(set(blockers)),
        "warnings": sorted(set(warnings)),
        "status": "local_device_qc_ready" if local_ready else "local_device_qc_blocked",
        "limits": [
            "This report inspects local files, command availability, and existing gate reports only.",
            "It does not open REAPER, insert FX, write parameters, save a project, render audio, or approve delivery.",
            "File fingerprints prove local installation state only; they do not prove audio quality, listening approval, or semantic parameter write safety.",
            "Plugin presence and raw runtime observations do not grant semantic parameter write safety.",
        ],
        "passed": local_ready,
    }
    target = output_path or output_dir / JSON_REL_PATH
    write_json(target, qc)
    write_local_device_qc_report(qc, output_dir)
    return qc


def write_local_device_qc_report(qc: dict[str, Any], output_dir: Path) -> Path:
    readiness = qc.get("readiness", {})
    render_inventory = qc.get("render_inventory", {})
    lines = [
        "# Local Device QC",
        "",
        f"- Project: `{qc.get('project_name')}`",
        f"- Created UTC: `{qc.get('created_at')}`",
        f"- Status: `{qc.get('status')}`",
        f"- Local device QC ready: `{readiness.get('local_device_qc_ready')}`",
        f"- Runtime collection ready: `{readiness.get('ready_for_reaper_runtime_collection')}`",
        f"- Applied parameter writes ready: `{readiness.get('ready_for_applied_parameter_writes')}`",
        f"- Delivery claims ready: `{readiness.get('ready_for_delivery_claims')}`",
        f"- Render audio files found: `{render_inventory.get('audio_files_total', 0)}`",
        "",
        "This is a local-machine readiness report. It does not open REAPER, write parameters, render audio, or approve delivery.",
        "",
        "## Blockers",
        "",
    ]
    lines.extend([f"- `{item}`" for item in qc.get("blockers", [])] or ["- none"])
    lines.extend(["", "## Warnings", ""])
    lines.extend([f"- `{item}`" for item in qc.get("warnings", [])] or ["- none"])
    lines.extend(["", "## Commands", ""])
    for command in qc.get("commands", []):
        version = f" `{command.get('version')}`" if command.get("version") else ""
        lines.append(f"- `{command.get('command')}` available=`{command.get('available')}` path=`{command.get('path')}`{version}")
    lines.extend(["", "## REAPER / JSFX", ""])
    for key, value in qc.get("paths", {}).items():
        lines.append(f"- `{key}` exists=`{value.get('exists')}` path=`{value.get('path')}`")
    metadata = qc.get("reaper_app_metadata", {})
    lines.extend(
        [
            "",
            "## REAPER App Metadata",
            "",
            f"- Bundle id: `{metadata.get('bundle_identifier', '')}`",
            f"- Version: `{metadata.get('version', '')}`",
            f"- Build: `{metadata.get('build', '')}`",
            f"- Info.plist sha256: `{str(metadata.get('info_plist', {}).get('sha256', ''))[:16]}`",
        ]
    )
    lines.extend(["", "## Required JSFX", ""])
    for item in qc.get("required_jsfx", []):
        evidence = item.get("file_evidence", {}) if isinstance(item.get("file_evidence", {}), dict) else {}
        lines.append(
            f"- `{item.get('relative_path')}` present=`{item.get('present')}` purpose=`{item.get('purpose')}` sha256=`{str(evidence.get('sha256', ''))[:16]}`"
        )
    lines.extend(["", "## Stock FX Fingerprints", ""])
    for item in qc.get("stock_plugins", []):
        files = item.get("present_files", []) if isinstance(item.get("present_files", []), list) else []
        first = files[0] if files and isinstance(files[0], dict) else {}
        lines.append(f"- `{item.get('name')}` present=`{item.get('present')}` sha256=`{str(first.get('sha256', ''))[:16]}`")
    lines.extend(["", "## Gate Status", ""])
    for gate in qc.get("gate_status", []):
        lines.append(
            f"- `{gate.get('name')}` found=`{gate.get('found')}` ready=`{gate.get('ready')}` passed=`{gate.get('passed')}` blockers=`{gate.get('blockers_total')}`"
        )
    lines.extend(["", "## Recent Render Files", ""])
    for item in render_inventory.get("recent_audio_files", [])[:10]:
        lines.append(f"- `{item.get('relative_path')}` `{item.get('size_bytes')}` bytes")
    if not render_inventory.get("recent_audio_files"):
        lines.append("- none")
    path = Path(output_dir) / MD_REL_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return path

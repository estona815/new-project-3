from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from automix.plugins.plugin_adapter_schema import now_utc, write_json
from automix.plugins.plugin_semantic_validation_runtime_collector_package import (
    PLUGIN_SEMANTIC_VALIDATION_RUNTIME_COLLECTOR_PACKAGE_SCHEMA,
    REAPER_RUNTIME_QUEUE_SCHEMA,
    RUNTIME_OBSERVATION_SCHEMA,
    RUNTIME_OBSERVATION_TEMPLATE_SCHEMA,
)
from automix.plugins.plugin_semantic_validation_runtime_handoff_packet_gate import (
    PLUGIN_SEMANTIC_VALIDATION_RUNTIME_HANDOFF_PACKET_GATE_SCHEMA,
)
from automix.plugins.plugin_semantic_validation_runtime_observation_gate import (
    PLUGIN_SEMANTIC_VALIDATION_RUNTIME_OBSERVATION_GATE_SCHEMA,
)


PLUGIN_SEMANTIC_VALIDATION_RUNTIME_OBSERVATION_PROVENANCE_GATE_SCHEMA = (
    "automix-plugin-semantic-validation-runtime-observation-provenance-gate-v1"
)

GATE_REL_PATH = Path("eval_reports/plugin_semantic_validation_runtime_observation_provenance_gate.json")
GATE_REPORT_REL_PATH = Path("eval_reports/plugin_semantic_validation_runtime_observation_provenance_gate.md")

COLLECTOR_PACKAGE_REL_PATH = Path("eval_reports/plugin_semantic_validation_runtime_collector_package.json")
HANDOFF_PACKET_REL_PATH = Path("eval_reports/plugin_semantic_validation_runtime_handoff_packet_gate.json")
OBSERVATION_GATE_REL_PATH = Path("eval_reports/plugin_semantic_validation_runtime_observation_gate.json")
LOCAL_DEVICE_QC_REL_PATH = Path("eval_reports/local_device_qc.json")
SAFETY_AUDIT_REL_PATH = Path("eval_reports/reaper_runtime_collector_safety_audit.json")

OPTIONAL_HASH_FIELDS = {
    "queue_payload_sha256": "queue_payload",
    "observation_template_sha256": "observation_template",
    "collector_package_sha256": "collector_package",
    "local_device_qc_sha256": "local_device_qc",
    "safety_audit_sha256": "safety_audit",
}


def _load_json(path: Path) -> tuple[dict[str, Any], bool]:
    try:
        loaded = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return {}, False
    return (loaded, True) if isinstance(loaded, dict) else ({}, False)


def _resolve_path(value: Any, output_dir: Path) -> Path:
    path = Path(str(value or ""))
    if path.is_absolute():
        return path
    if path.parts and path.parts[0] == output_dir.name:
        return output_dir.parent / path
    return output_dir / path


def _norm_path(value: Any, output_dir: Path) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    return str(_resolve_path(text, output_dir).resolve()).replace("\\", "/")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _artifact(path: Path, expected_schema: str | None = None) -> dict[str, Any]:
    blockers: list[str] = []
    data: dict[str, Any] = {}
    valid: bool | None = None
    if not path.exists():
        blockers.append("missing")
    elif expected_schema is None:
        valid = None
    else:
        data, json_valid = _load_json(path)
        valid = bool(json_valid and data)
        if not valid:
            blockers.append("invalid_json")
        elif data.get("schema") != expected_schema:
            blockers.append(f"schema_mismatch:{data.get('schema', '')}")
    return {
        "path": str(path),
        "exists": path.exists(),
        "json_valid": valid,
        "schema": data.get("schema", ""),
        "sha256": _sha256(path) if path.exists() else "",
        "blockers": blockers,
        "data": data,
    }


def _extract_script_version(lua_path: Path) -> str:
    try:
        text = lua_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    match = re.search(r'local\s+SCRIPT_VERSION\s*=\s*"([^"]+)"', text)
    return match.group(1) if match else ""


def _parse_utc(value: Any) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        parsed = datetime.fromisoformat(text)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except ValueError:
        return None


def _job_lookup(items: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for item in items:
        job_id = str(item.get("job_id", "")).strip()
        if job_id:
            out[job_id] = item
    return out


def _observation_path_under_observation_dir(path_text: str) -> bool:
    normalized = str(path_text or "").replace("\\", "/")
    return "/reaper_scripts/observations/" in normalized and normalized.endswith("_observation.json")


def _parameters_are_raw(parameters: Any) -> bool:
    if not isinstance(parameters, list):
        return False
    for item in parameters:
        if not isinstance(item, dict):
            return False
        if item.get("write_allowed", False) or item.get("semantic_validated", False):
            return False
    return True


def _validate_observation_provenance(
    *,
    job: dict[str, Any],
    output_dir: Path,
    expected_hashes: dict[str, str],
    expected_paths: dict[str, str],
    collector_script_version: str,
    collector_created_at: datetime | None,
) -> dict[str, Any]:
    job_id = str(job.get("job_id", "")).strip()
    plugin_name = str(job.get("plugin_name", "")).strip()
    expected_observation_path = _norm_path(job.get("raw_observation_output_path", ""), output_dir)
    observation_path = Path(expected_observation_path)
    blockers: list[str] = []
    warnings: list[str] = []
    data, valid = _load_json(observation_path) if observation_path.exists() else ({}, False)

    if not expected_observation_path:
        blockers.append("expected_observation_path_missing")
    elif not _observation_path_under_observation_dir(expected_observation_path):
        blockers.append("expected_observation_path_not_under_observation_dir")

    if not observation_path.exists():
        warnings.append("runtime_observation_file_missing")
        return {
            "job_id": job_id,
            "plugin_name": plugin_name,
            "expected_observation_path": expected_observation_path,
            "observation_exists": False,
            "json_valid": False,
            "observation_schema": "",
            "observation_status": "",
            "script_version": "",
            "created_at_utc": "",
            "queue_payload_path": "",
            "parameters_observed_total": 0,
            "optional_hashes_present": [],
            "safe_to_write_parameters": False,
            "creates_validation_reports": False,
            "blockers": sorted(set(blockers)),
            "warnings": sorted(set(warnings)),
            "status": "observation_missing" if not blockers else "provenance_blocked",
        }
    if not valid:
        blockers.append("runtime_observation_invalid_json")
        data = data if isinstance(data, dict) else {}

    parameters = data.get("parameters", []) if isinstance(data.get("parameters", []), list) else []
    observed_queue_path = _norm_path(data.get("queue_payload_path", ""), output_dir)
    expected_queue_path = expected_paths.get("queue_payload", "")
    created_at = _parse_utc(data.get("created_at_utc"))

    if data:
        if data.get("schema") != RUNTIME_OBSERVATION_SCHEMA:
            blockers.append("runtime_observation_schema_mismatch")
        if str(data.get("job_id", "")).strip() != job_id:
            blockers.append("runtime_observation_job_id_mismatch")
        if str(data.get("plugin_name", "")).strip() != plugin_name:
            blockers.append("runtime_observation_plugin_name_mismatch")
        if data.get("status") != "raw_observation_collected":
            blockers.append(f"runtime_observation_not_collected:{data.get('status', 'unknown')}")
        if data.get("script_version") != collector_script_version:
            blockers.append("runtime_observation_script_version_mismatch")
        if observed_queue_path != expected_queue_path:
            blockers.append("runtime_observation_queue_payload_path_mismatch")
        if data.get("raw_observation_output_path") and _norm_path(data.get("raw_observation_output_path", ""), output_dir) != expected_observation_path:
            blockers.append("runtime_observation_output_path_mismatch")
        if data.get("safe_to_write_parameters", False):
            blockers.append("runtime_observation_claims_write_safety")
        if data.get("creates_validation_reports", False):
            blockers.append("runtime_observation_claims_validation_report_creation")
        if data.get("writes_parameters", False):
            blockers.append("runtime_observation_claims_parameter_writes")
        if data.get("renders_audio", False):
            blockers.append("runtime_observation_claims_audio_render")
        if data.get("saves_project", False):
            blockers.append("runtime_observation_claims_project_save")
        if data.get("parameter_indexes_assumed", False):
            blockers.append("runtime_observation_assumes_parameter_indexes")
        if not data.get("temporary_muted_probe_track_used", False):
            blockers.append("runtime_observation_temp_probe_track_not_used")
        if not data.get("temporary_muted_probe_track_deleted", False):
            blockers.append("runtime_observation_temp_probe_track_not_deleted")
        if not _parameters_are_raw(parameters):
            blockers.append("runtime_observation_parameters_claim_write_safety")
        if int(data.get("param_count", 0) or 0) <= 0 or not parameters:
            blockers.append("runtime_observation_parameters_missing")
        if data.get("errors"):
            blockers.append("runtime_observation_has_errors")
        if not data.get("actual_fx_name"):
            warnings.append("runtime_observation_actual_fx_name_missing")
        if not created_at:
            warnings.append("runtime_observation_created_at_missing_or_invalid")
        elif collector_created_at and created_at < collector_created_at:
            blockers.append("runtime_observation_created_before_collector_package")

    optional_present: list[str] = []
    missing_optional: list[str] = []
    for field, artifact_id in OPTIONAL_HASH_FIELDS.items():
        value = str(data.get(field, "")).strip()
        if not value:
            missing_optional.append(field)
            continue
        optional_present.append(field)
        expected = expected_hashes.get(artifact_id, "")
        if expected and value != expected:
            blockers.append(f"runtime_observation_hash_mismatch:{field}")
    if missing_optional:
        warnings.append(f"runtime_observation_optional_hash_fields_missing:{len(missing_optional)}")

    return {
        "job_id": job_id,
        "plugin_name": plugin_name,
        "expected_observation_path": expected_observation_path,
        "observation_exists": True,
        "json_valid": bool(valid and data),
        "observation_schema": data.get("schema", ""),
        "observation_status": data.get("status", ""),
        "script_version": data.get("script_version", ""),
        "created_at_utc": data.get("created_at_utc", ""),
        "queue_payload_path": observed_queue_path,
        "parameters_observed_total": len(parameters),
        "optional_hashes_present": sorted(optional_present),
        "safe_to_write_parameters": False,
        "creates_validation_reports": False,
        "blockers": sorted(set(blockers)),
        "warnings": sorted(set(warnings)),
        "status": "provenance_verified" if not blockers else "provenance_blocked",
    }


def build_plugin_semantic_validation_runtime_observation_provenance_gate(
    *,
    project_name: str,
    output_dir: Path,
    collector_package_path: Path | None = None,
    handoff_packet_path: Path | None = None,
    observation_gate_path: Path | None = None,
    local_device_qc_path: Path | None = None,
    safety_audit_path: Path | None = None,
    output_path: Path | None = None,
) -> dict[str, Any]:
    output_dir = Path(output_dir)
    collector_package_path = collector_package_path or output_dir / COLLECTOR_PACKAGE_REL_PATH
    handoff_packet_path = handoff_packet_path or output_dir / HANDOFF_PACKET_REL_PATH
    observation_gate_path = observation_gate_path or output_dir / OBSERVATION_GATE_REL_PATH
    local_device_qc_path = local_device_qc_path or output_dir / LOCAL_DEVICE_QC_REL_PATH
    safety_audit_path = safety_audit_path or output_dir / SAFETY_AUDIT_REL_PATH

    collector_package, collector_valid = _load_json(collector_package_path) if collector_package_path.exists() else ({}, False)
    handoff_packet, handoff_valid = _load_json(handoff_packet_path) if handoff_packet_path.exists() else ({}, False)
    observation_gate, observation_gate_valid = _load_json(observation_gate_path) if observation_gate_path.exists() else ({}, False)
    local_qc, local_valid = _load_json(local_device_qc_path) if local_device_qc_path.exists() else ({}, False)
    safety_audit, safety_valid = _load_json(safety_audit_path) if safety_audit_path.exists() else ({}, False)

    blockers: list[str] = []
    warnings: list[str] = []
    if not collector_package or not collector_valid or collector_package.get("schema") != PLUGIN_SEMANTIC_VALIDATION_RUNTIME_COLLECTOR_PACKAGE_SCHEMA:
        blockers.append("runtime_collector_package_missing_or_invalid")
        collector_package = collector_package if isinstance(collector_package, dict) else {}
    if not handoff_packet or not handoff_valid or handoff_packet.get("schema") != PLUGIN_SEMANTIC_VALIDATION_RUNTIME_HANDOFF_PACKET_GATE_SCHEMA:
        blockers.append("runtime_handoff_packet_gate_missing_or_invalid")
        handoff_packet = handoff_packet if isinstance(handoff_packet, dict) else {}
    if not observation_gate or not observation_gate_valid or observation_gate.get("schema") != PLUGIN_SEMANTIC_VALIDATION_RUNTIME_OBSERVATION_GATE_SCHEMA:
        blockers.append("runtime_observation_gate_missing_or_invalid")
        observation_gate = observation_gate if isinstance(observation_gate, dict) else {}
    if not local_qc or not local_valid:
        blockers.append("local_device_qc_missing_or_invalid")
        local_qc = local_qc if isinstance(local_qc, dict) else {}
    if not safety_audit or not safety_valid:
        blockers.append("collector_safety_audit_missing_or_invalid")
        safety_audit = safety_audit if isinstance(safety_audit, dict) else {}

    local_readiness = local_qc.get("readiness", {}) if isinstance(local_qc.get("readiness", {}), dict) else {}
    if local_qc and not local_readiness.get("ready_for_reaper_runtime_collection", False):
        blockers.append("local_device_qc_runtime_collection_not_ready")
    if safety_audit and not safety_audit.get("passed", False):
        blockers.append("collector_safety_audit_not_passed")
    if handoff_packet and not handoff_packet.get("readiness", {}).get("operator_runtime_handoff_packet_ready", False):
        blockers.append("runtime_handoff_packet_not_ready")

    lua_path = _resolve_path(collector_package.get("lua_collector_script_path", ""), output_dir)
    queue_path = _resolve_path(collector_package.get("queue_payload_path", ""), output_dir)
    observation_template_path = _resolve_path(collector_package.get("observation_template_path", ""), output_dir)
    artifacts = {
        "collector_script": _artifact(lua_path, None),
        "queue_payload": _artifact(queue_path, REAPER_RUNTIME_QUEUE_SCHEMA),
        "observation_template": _artifact(observation_template_path, RUNTIME_OBSERVATION_TEMPLATE_SCHEMA),
        "collector_package": _artifact(collector_package_path, PLUGIN_SEMANTIC_VALIDATION_RUNTIME_COLLECTOR_PACKAGE_SCHEMA),
        "local_device_qc": _artifact(local_device_qc_path, None),
        "safety_audit": _artifact(safety_audit_path, None),
    }
    for artifact_id, artifact in artifacts.items():
        for blocker in artifact.get("blockers", []):
            blockers.append(f"{artifact_id}_{blocker}")

    queue_payload = artifacts["queue_payload"].get("data", {})
    expected_paths = {
        "queue_payload": str(queue_path.resolve()).replace("\\", "/") if str(queue_path) else "",
        "observation_template": str(observation_template_path.resolve()).replace("\\", "/") if str(observation_template_path) else "",
    }
    expected_hashes = {artifact_id: artifact.get("sha256", "") for artifact_id, artifact in artifacts.items()}
    collector_script_version = _extract_script_version(lua_path) if lua_path.exists() else ""
    if not collector_script_version:
        blockers.append("collector_script_version_missing")

    collector_jobs = [job for job in collector_package.get("collector_jobs", []) or [] if isinstance(job, dict)]
    queue_jobs = [job for job in queue_payload.get("jobs", []) or [] if isinstance(job, dict)]
    if len(collector_jobs) != len(queue_jobs) and (collector_jobs or queue_jobs):
        blockers.append("collector_jobs_count_mismatch_with_queue_payload")

    queue_by_id = _job_lookup(queue_jobs)
    for job in collector_jobs:
        job_id = str(job.get("job_id", "")).strip()
        queue_job = queue_by_id.get(job_id)
        if not queue_job:
            blockers.append(f"collector_job_missing_from_queue_payload:{job_id}")
            continue
        if _norm_path(queue_job.get("raw_observation_output_path", ""), output_dir) and _norm_path(queue_job.get("raw_observation_output_path", ""), output_dir) != _norm_path(job.get("raw_observation_output_path", ""), output_dir):
            blockers.append(f"collector_job_observation_path_mismatch_with_queue:{job_id}")

    collector_created_at = _parse_utc(collector_package.get("created_at"))
    job_results = [
        _validate_observation_provenance(
            job=job,
            output_dir=output_dir,
            expected_hashes=expected_hashes,
            expected_paths=expected_paths,
            collector_script_version=collector_script_version,
            collector_created_at=collector_created_at,
        )
        for job in collector_jobs
    ]
    blockers.extend(f"{item['job_id']}:{blocker}" for item in job_results for blocker in item.get("blockers", []))
    warnings.extend(f"{item['job_id']}:{warning}" for item in job_results for warning in item.get("warnings", []))

    existing = [item for item in job_results if item.get("observation_exists")]
    verified = [item for item in job_results if item.get("status") == "provenance_verified"]
    missing = [item for item in job_results if item.get("status") == "observation_missing"]
    if missing:
        warnings.append(f"runtime_observation_files_missing:{len(missing)}")
    if existing and len(verified) < len(existing):
        blockers.append("existing_runtime_observation_provenance_not_verified")

    unique_blockers = sorted(set(blockers))
    unique_warnings = sorted(set(warnings))
    expected_packet_ready = bool(not unique_blockers and collector_jobs)
    observed_ready = bool(expected_packet_ready and collector_jobs and len(verified) == len(collector_jobs))
    if unique_blockers:
        status = "runtime_observation_provenance_blocked"
    elif observed_ready:
        status = "runtime_observation_provenance_ready_for_authoring"
    elif existing:
        status = "runtime_observation_provenance_partial"
    else:
        status = "runtime_observation_provenance_pending_observations"

    gate = {
        "schema": PLUGIN_SEMANTIC_VALIDATION_RUNTIME_OBSERVATION_PROVENANCE_GATE_SCHEMA,
        "project_name": project_name,
        "created_at": now_utc(),
        "output_dir": str(output_dir),
        "status": status,
        "passed": expected_packet_ready,
        "readiness": {
            "expected_observation_provenance_packet_ready": expected_packet_ready,
            "observed_runtime_provenance_ready": observed_ready,
            "ready_for_manual_report_authoring": bool(observed_ready and observation_gate.get("ready_for_manual_report_authoring", False)),
            "safe_to_write_parameters": False,
            "creates_validation_reports": False,
            "safe_to_claim_final_audio_or_delivery": False,
            "report_only": True,
        },
        "sources": {
            "collector_package_path": str(collector_package_path),
            "handoff_packet_path": str(handoff_packet_path),
            "observation_gate_path": str(observation_gate_path),
            "local_device_qc_path": str(local_device_qc_path),
            "safety_audit_path": str(safety_audit_path),
            "lua_collector_script_path": str(lua_path),
            "queue_payload_path": str(queue_path),
            "observation_template_path": str(observation_template_path),
        },
        "provenance": {
            "collector_script_version": collector_script_version,
            "expected_artifact_hashes": expected_hashes,
            "artifacts": {key: {k: v for k, v in artifact.items() if k != "data"} for key, artifact in artifacts.items()},
        },
        "counts": {
            "collector_jobs_total": len(collector_jobs),
            "queue_jobs_total": len(queue_jobs),
            "observations_existing_total": len(existing),
            "observations_missing_total": len(missing),
            "observations_provenance_verified_total": len(verified),
        },
        "job_results": job_results,
        "blockers": unique_blockers,
        "warnings": unique_warnings,
        "limits": [
            "This gate does not open REAPER, execute Lua, create validation reports, write parameters, render, save, or approve audio.",
            "Missing observations do not fail the expected packet; existing observations must match provenance before report authoring.",
            "Optional hash fields are checked when present and warned when absent.",
            "Passing this gate does not make semantic validation ready.",
        ],
    }
    target = output_path or output_dir / GATE_REL_PATH
    write_json(target, gate)
    write_plugin_semantic_validation_runtime_observation_provenance_report(gate, output_dir)
    return gate


def write_plugin_semantic_validation_runtime_observation_provenance_report(gate: dict[str, Any], output_dir: Path) -> Path:
    readiness = gate.get("readiness", {})
    counts = gate.get("counts", {})
    lines = [
        "# Plugin Semantic Validation Runtime Observation Provenance Gate",
        "",
        f"- Project: `{gate.get('project_name')}`",
        f"- Created UTC: `{gate.get('created_at')}`",
        f"- Status: `{gate.get('status')}`",
        f"- Passed: `{gate.get('passed')}`",
        f"- Expected packet ready: `{readiness.get('expected_observation_provenance_packet_ready')}`",
        f"- Observed provenance ready: `{readiness.get('observed_runtime_provenance_ready')}`",
        f"- Safe to write parameters: `{readiness.get('safe_to_write_parameters')}`",
        "",
        "This report checks runtime observation provenance only. It does not create validation reports.",
        "",
        "## Counts",
        "",
    ]
    for key, value in counts.items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(["", "## Blockers", ""])
    lines.extend([f"- `{item}`" for item in gate.get("blockers", [])] or ["- none"])
    lines.extend(["", "## Warnings", ""])
    lines.extend([f"- `{item}`" for item in gate.get("warnings", [])] or ["- none"])
    lines.extend(["", "## Artifact Hashes", ""])
    for key, value in gate.get("provenance", {}).get("expected_artifact_hashes", {}).items():
        lines.append(f"- `{key}`: `{str(value)[:16]}`")
    lines.extend(["", "## Jobs", ""])
    if not gate.get("job_results"):
        lines.append("- none")
    for item in gate.get("job_results", []):
        lines.extend(
            [
                f"### {item.get('job_id')}",
                "",
                f"- Plugin: `{item.get('plugin_name')}`",
                f"- Status: `{item.get('status')}`",
                f"- Observation exists: `{item.get('observation_exists')}`",
                f"- Observation: `{item.get('expected_observation_path')}`",
                f"- Script version: `{item.get('script_version')}`",
                f"- Parameters observed: `{item.get('parameters_observed_total')}`",
                f"- Blockers: `{item.get('blockers', [])}`",
                f"- Warnings: `{item.get('warnings', [])}`",
                "",
            ]
        )
    lines.extend(["## Limits", ""])
    lines.extend([f"- {item}" for item in gate.get("limits", [])])
    path = Path(output_dir) / GATE_REPORT_REL_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return path

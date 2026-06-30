from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from automix.plugins.plugin_adapter_schema import compact_plugin_name, now_utc, write_json
from automix.plugins.plugin_availability_decision_gate import (
    ACCEPTED_DISABLE_MANIFEST_SCHEMA,
    ALLOWED_RESOLUTIONS,
)
from automix.plugins.plugin_availability_operator_decision_package import (
    PLUGIN_AVAILABILITY_DISABLE_MANIFEST_CANDIDATE_SCHEMA,
    PLUGIN_AVAILABILITY_OPERATOR_DECISION_PACKAGE_SCHEMA,
)
from automix.plugins.plugin_availability_resolution_plan import PLUGIN_AVAILABILITY_RESOLUTION_PLAN_SCHEMA


PLUGIN_AVAILABILITY_OPERATOR_DECISION_FIREWALL_GATE_SCHEMA = (
    "automix-plugin-availability-operator-decision-firewall-gate-v1"
)

GATE_REL_PATH = Path("eval_reports/plugin_availability_operator_decision_firewall_gate.json")
GATE_REPORT_REL_PATH = Path("eval_reports/plugin_availability_operator_decision_firewall_gate.md")

RESOLUTION_PLAN_REL_PATH = Path("eval_reports/plugin_availability_resolution_plan.json")
OPERATOR_DECISION_PACKAGE_REL_PATH = Path("eval_reports/plugin_availability_operator_decision_package.json")
DECISION_GATE_REL_PATH = Path("eval_reports/plugin_availability_decision_gate.json")
CANDIDATE_MANIFEST_REL_PATH = Path("review/plugin_availability_disable_manifest_candidate.json")
ACCEPTED_MANIFEST_REL_PATH = Path("review/plugin_availability_disable_manifest.json")


def _load_json(path: Path) -> tuple[dict[str, Any], bool]:
    try:
        loaded = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return {}, False
    return (loaded, True) if isinstance(loaded, dict) else ({}, False)


def _sha256(path: Path) -> str:
    if not path.exists():
        return ""
    if path.is_dir():
        return ""
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError:
        return ""
    return digest.hexdigest()


def _resolve_path(path_text: Any, output_dir: Path) -> Path:
    path = Path(str(path_text or ""))
    if not path_text:
        return output_dir
    if path.is_absolute():
        return path
    if path.parts and path.parts[0] == output_dir.name:
        return output_dir.parent / path
    return output_dir / path


def _provenance_hash_check(source: dict[str, Any], key: str, output_dir: Path, blockers: list[str], warnings: list[str]) -> None:
    artifact = source.get(key) if isinstance(source, dict) else None
    if not isinstance(artifact, dict):
        return
    expected = str(artifact.get("sha256", "")).strip()
    if not expected:
        return
    artifact_path = _resolve_path(artifact.get("path", ""), output_dir)
    if not artifact_path.exists():
        warnings.append(f"operator_decision_candidate_provenance_path_missing:{key}:{artifact.get('path','')}")
        return
    if artifact_path.is_dir():
        blockers.append(
            f"operator_decision_candidate_provenance_path_is_directory:{key}:{artifact.get('path','')}"
        )
        return
    actual = _sha256(artifact_path)
    if actual != expected:
        blockers.append(f"operator_decision_candidate_provenance_hash_mismatch:{key}")


def _decision_names_from_resolution_plan(plan: dict[str, Any]) -> list[str]:
    names: dict[str, str] = {}
    for raw in plan.get("pending_operator_decisions", []) or []:
        name = str(raw).strip()
        if name:
            names.setdefault(compact_plugin_name(name), name)
    for item in plan.get("resolutions", []) or []:
        if not isinstance(item, dict) or not item.get("operator_decision_required", False):
            continue
        name = str(item.get("plugin_name", "")).strip()
        if name:
            names.setdefault(compact_plugin_name(name), name)
    return sorted(names.values(), key=lambda value: value.lower())


def _entry_lookup(manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for item in manifest.get("disabled_plugins", []) or []:
        if not isinstance(item, dict):
            continue
        name = str(item.get("plugin_name", "")).strip()
        if name:
            out[compact_plugin_name(name)] = item
    return out


def _candidate_entry_result(plugin_name: str, entry: dict[str, Any] | None) -> dict[str, Any]:
    blockers: list[str] = []
    warnings: list[str] = []
    entry = entry or {}
    resolution = str(entry.get("resolution", "")).strip()
    fallback_candidate = str(entry.get("fallback_candidate", "")).strip()
    if not entry:
        blockers.append(f"candidate_decision_missing:{plugin_name}")
    else:
        if resolution not in ALLOWED_RESOLUTIONS:
            blockers.append(f"candidate_resolution_unsupported:{plugin_name}:{resolution}")
        if bool(entry.get("operator_acknowledged", False)):
            blockers.append(f"candidate_operator_acknowledgement_must_be_false:{plugin_name}")
        if bool(entry.get("automatic_parameter_writes_allowed", False)):
            blockers.append(f"candidate_automatic_parameter_writes_must_be_false:{plugin_name}")
        if fallback_candidate and not bool(entry.get("fallback_requires_validation", False)):
            blockers.append(f"candidate_fallback_validation_requirement_missing:{plugin_name}")
        if resolution == "install_and_rerun_preflight":
            warnings.append(f"candidate_install_resolution_requires_preflight_rerun:{plugin_name}")
    return {
        "plugin_name": plugin_name,
        "resolution": resolution,
        "fallback_candidate": fallback_candidate,
        "fallback_requires_validation": bool(entry.get("fallback_requires_validation", False)),
        "operator_acknowledged": bool(entry.get("operator_acknowledged", False)),
        "automatic_parameter_writes_allowed": bool(entry.get("automatic_parameter_writes_allowed", False)),
        "status": "candidate_safe" if not blockers else "blocked",
        "blockers": sorted(set(blockers)),
        "warnings": sorted(set(warnings)),
    }


def _accepted_entry_result(plugin_name: str, entry: dict[str, Any] | None) -> dict[str, Any]:
    blockers: list[str] = []
    warnings: list[str] = []
    entry = entry or {}
    resolution = str(entry.get("resolution", "")).strip()
    fallback_candidate = str(entry.get("fallback_candidate", "")).strip()
    if not entry:
        blockers.append(f"accepted_decision_missing:{plugin_name}")
    else:
        if resolution not in ALLOWED_RESOLUTIONS:
            blockers.append(f"accepted_resolution_unsupported:{plugin_name}:{resolution}")
        if not bool(entry.get("operator_acknowledged", False)):
            blockers.append(f"accepted_operator_acknowledgement_missing:{plugin_name}")
        if bool(entry.get("automatic_parameter_writes_allowed", False)):
            blockers.append(f"accepted_automatic_parameter_writes_must_be_false:{plugin_name}")
        if fallback_candidate and not bool(entry.get("fallback_requires_validation", False)):
            blockers.append(f"accepted_fallback_validation_requirement_missing:{plugin_name}")
        if resolution == "install_and_rerun_preflight":
            warnings.append(f"accepted_install_resolution_requires_preflight_rerun:{plugin_name}")
    return {
        "plugin_name": plugin_name,
        "resolution": resolution,
        "fallback_candidate": fallback_candidate,
        "fallback_requires_validation": bool(entry.get("fallback_requires_validation", False)),
        "operator_acknowledged": bool(entry.get("operator_acknowledged", False)),
        "automatic_parameter_writes_allowed": bool(entry.get("automatic_parameter_writes_allowed", False)),
        "status": "accepted_safe" if not blockers else "blocked",
        "blockers": sorted(set(blockers)),
        "warnings": sorted(set(warnings)),
    }


def build_plugin_availability_operator_decision_firewall_gate(
    *,
    project_name: str,
    output_dir: Path,
    resolution_plan_path: Path | None = None,
    operator_decision_package_path: Path | None = None,
    decision_gate_path: Path | None = None,
    candidate_manifest_path: Path | None = None,
    accepted_manifest_path: Path | None = None,
    output_path: Path | None = None,
) -> dict[str, Any]:
    output_dir = Path(output_dir)
    resolution_plan_path = resolution_plan_path or output_dir / RESOLUTION_PLAN_REL_PATH
    operator_decision_package_path = operator_decision_package_path or output_dir / OPERATOR_DECISION_PACKAGE_REL_PATH
    decision_gate_path = decision_gate_path or output_dir / DECISION_GATE_REL_PATH
    candidate_manifest_path = candidate_manifest_path or output_dir / CANDIDATE_MANIFEST_REL_PATH
    accepted_manifest_path = accepted_manifest_path or output_dir / ACCEPTED_MANIFEST_REL_PATH

    resolution_plan, resolution_valid = (
        _load_json(resolution_plan_path) if resolution_plan_path.exists() else ({}, False)
    )
    operator_package, package_valid = (
        _load_json(operator_decision_package_path) if operator_decision_package_path.exists() else ({}, False)
    )
    decision_gate, decision_valid = _load_json(decision_gate_path) if decision_gate_path.exists() else ({}, False)
    candidate, candidate_valid = _load_json(candidate_manifest_path) if candidate_manifest_path.exists() else ({}, False)
    accepted, accepted_valid = _load_json(accepted_manifest_path) if accepted_manifest_path.exists() else ({}, False)

    blockers: list[str] = []
    warnings: list[str] = []
    if not resolution_plan or not resolution_valid or resolution_plan.get("schema") != PLUGIN_AVAILABILITY_RESOLUTION_PLAN_SCHEMA:
        blockers.append("plugin_availability_resolution_plan_missing_or_invalid")
        resolution_plan = resolution_plan if isinstance(resolution_plan, dict) else {}
    if (
        not operator_package
        or not package_valid
        or operator_package.get("schema") != PLUGIN_AVAILABILITY_OPERATOR_DECISION_PACKAGE_SCHEMA
    ):
        blockers.append("plugin_availability_operator_decision_package_missing_or_invalid")
        operator_package = operator_package if isinstance(operator_package, dict) else {}
    operator_decision_request_token = str(operator_package.get("operator_decision_request_token", "")).strip()
    if not operator_decision_request_token:
        blockers.append("operator_decision_request_token_missing_in_package")
    if not decision_gate or not decision_valid or decision_gate.get("schema") != "automix-plugin-availability-decision-gate-v1":
        blockers.append("plugin_availability_decision_gate_missing_or_invalid")
        decision_gate = decision_gate if isinstance(decision_gate, dict) else {}
    if not candidate_manifest_path.exists():
        blockers.append("operator_decision_candidate_manifest_missing")
    elif not candidate_valid:
        blockers.append("operator_decision_candidate_manifest_invalid_json")
    elif candidate.get("schema") != PLUGIN_AVAILABILITY_DISABLE_MANIFEST_CANDIDATE_SCHEMA:
        blockers.append("operator_decision_candidate_manifest_schema_invalid")

    required_decisions = _decision_names_from_resolution_plan(resolution_plan)
    if int(operator_package.get("required_decisions_total", len(required_decisions)) or 0) != len(required_decisions):
        blockers.append("operator_decision_package_required_count_mismatch")
    if str(candidate_manifest_path) == str(accepted_manifest_path):
        blockers.append("candidate_and_accepted_manifest_paths_must_differ")

    candidate_entries: list[dict[str, Any]] = []
    if candidate:
        candidate_sources = candidate.get("provenance", {}).get("source_artifacts", {})
        _provenance_hash_check(candidate_sources, "resolution_plan", output_dir, blockers, warnings)
        _provenance_hash_check(candidate_sources, "decision_gate", output_dir, blockers, warnings)
        if str(candidate.get("operator_decision_request_token", "")).strip() != operator_decision_request_token:
            blockers.append("operator_decision_candidate_request_token_mismatch")
        if not bool(candidate.get("candidate_only", False)):
            blockers.append("operator_decision_candidate_only_flag_missing")
        if candidate.get("target_schema_after_operator_acceptance") != ACCEPTED_DISABLE_MANIFEST_SCHEMA:
            blockers.append("operator_decision_candidate_target_schema_invalid")
        if not bool(candidate.get("operator_acknowledgement_required", False)):
            blockers.append("operator_decision_candidate_acknowledgement_requirement_missing")
        if bool(candidate.get("safe_to_write_parameters", False)):
            blockers.append("operator_decision_candidate_safe_to_write_parameters_must_be_false")
        candidate_lookup = _entry_lookup(candidate)
        candidate_entries = [
            _candidate_entry_result(plugin_name, candidate_lookup.get(compact_plugin_name(plugin_name)))
            for plugin_name in required_decisions
        ]
        blockers.extend(blocker for item in candidate_entries for blocker in item.get("blockers", []))
        warnings.extend(warning for item in candidate_entries for warning in item.get("warnings", []))

    accepted_exists = accepted_manifest_path.exists()
    accepted_entries: list[dict[str, Any]] = []
    if not accepted_exists and required_decisions:
        warnings.append(f"accepted_operator_decision_manifest_missing:{len(required_decisions)}")
    if accepted_exists:
        if not accepted_valid:
            blockers.append("accepted_operator_decision_manifest_invalid_json")
        elif accepted.get("schema") == PLUGIN_AVAILABILITY_DISABLE_MANIFEST_CANDIDATE_SCHEMA:
            blockers.append("accepted_operator_decision_manifest_is_candidate")
        elif accepted.get("schema") == "automix-plugin-availability-disable-manifest-template-v1":
            blockers.append("accepted_operator_decision_manifest_is_template")
        elif accepted.get("schema") != ACCEPTED_DISABLE_MANIFEST_SCHEMA:
            blockers.append("accepted_operator_decision_manifest_schema_invalid")
        else:
            accepted_lookup = _entry_lookup(accepted)
            accepted_token = str(accepted.get("operator_decision_request_token", "")).strip()
            if not accepted_token:
                blockers.append("operator_decision_request_token_missing_in_accepted_manifest")
            elif accepted_token != operator_decision_request_token:
                blockers.append("operator_decision_request_token_mismatch_with_package")
            accepted_entries = [
                _accepted_entry_result(plugin_name, accepted_lookup.get(compact_plugin_name(plugin_name)))
                for plugin_name in required_decisions
            ]
            blockers.extend(blocker for item in accepted_entries for blocker in item.get("blockers", []))
            warnings.extend(warning for item in accepted_entries for warning in item.get("warnings", []))
            for plugin_name in required_decisions:
                normalized = compact_plugin_name(plugin_name)
                entry = accepted_lookup.get(normalized, {})
                entry_token = str(entry.get("operator_decision_request_token", "")).strip()
                if not entry_token:
                    blockers.append(f"operator_decision_request_token_missing_in_accepted_entry:{plugin_name}")
                elif entry_token != operator_decision_request_token:
                    blockers.append(f"operator_decision_request_token_entry_mismatch:{plugin_name}")
            if not bool(decision_gate.get("availability_decisions_ready", False)):
                blockers.append("accepted_manifest_not_accepted_by_decision_gate")

    availability_decisions_ready = bool(decision_gate.get("availability_decisions_ready", False))
    if availability_decisions_ready and not accepted_exists and required_decisions:
        blockers.append("decision_gate_ready_without_accepted_manifest")
    if decision_gate.get("safe_to_write_parameters", False):
        blockers.append("decision_gate_safe_to_write_parameters_must_be_false")

    unique_blockers = sorted(set(blockers))
    unique_warnings = sorted(set(warnings))
    accepted_manifest_ready = bool(accepted_exists and availability_decisions_ready and accepted_entries and not unique_blockers)
    candidate_firewalled = bool(not unique_blockers and candidate_entries)
    if unique_blockers:
        status = "operator_decision_firewall_blocked"
    elif not required_decisions:
        status = "no_operator_decisions_required"
    elif accepted_manifest_ready:
        status = "accepted_operator_decision_manifest_firewalled"
    else:
        status = "operator_decision_candidate_firewalled_pending_acknowledgement"

    gate = {
        "schema": PLUGIN_AVAILABILITY_OPERATOR_DECISION_FIREWALL_GATE_SCHEMA,
        "project_name": project_name,
        "created_at": now_utc(),
        "output_dir": str(output_dir),
        "status": status,
        "passed": not unique_blockers,
        "readiness": {
            "candidate_manifest_firewalled_from_accepted_evidence": candidate_firewalled,
            "candidate_counts_as_accepted_operator_evidence": False,
            "accepted_operator_manifest_ready": accepted_manifest_ready,
            "availability_decisions_ready": availability_decisions_ready,
            "ready_for_plugin_preflight_rerun": bool(accepted_manifest_ready or not required_decisions),
            "safe_to_write_parameters": False,
            "safe_to_claim_final_audio_or_delivery": False,
            "report_only": True,
        },
        "sources": {
            "resolution_plan_path": str(resolution_plan_path),
            "operator_decision_package_path": str(operator_decision_package_path),
            "decision_gate_path": str(decision_gate_path),
            "candidate_manifest_path": str(candidate_manifest_path),
            "accepted_manifest_path": str(accepted_manifest_path),
        },
        "counts": {
            "required_decisions_total": len(required_decisions),
            "candidate_decisions_total": len(candidate_entries),
            "accepted_decisions_total": len(accepted_entries),
            "missing_accepted_decisions_total": len(required_decisions) - len(accepted_entries) if accepted_exists else len(required_decisions),
        },
        "required_decisions": required_decisions,
        "candidate_manifest": {
            "exists": candidate_manifest_path.exists(),
            "schema": candidate.get("schema", ""),
            "candidate_only": bool(candidate.get("candidate_only", False)),
            "safe_to_write_parameters": bool(candidate.get("safe_to_write_parameters", False)),
        },
        "accepted_manifest": {
            "exists": accepted_exists,
            "schema": accepted.get("schema", ""),
            "safe_to_write_parameters": False,
        },
        "candidate_entries": candidate_entries,
        "accepted_entries": accepted_entries,
        "blockers": unique_blockers,
        "warnings": unique_warnings,
        "limits": [
            "This gate does not install plugins, open REAPER, write parameters, render, or approve audio.",
            "Candidate manifests are operator drafts only and must not count as accepted decisions.",
            "Accepted disable manifests still do not grant fallback parameter write safety.",
            "Fallback writes remain blocked until semantic validation reports pass.",
        ],
    }
    target = output_path or output_dir / GATE_REL_PATH
    write_json(target, gate)
    write_plugin_availability_operator_decision_firewall_report(gate, output_dir)
    return gate


def write_plugin_availability_operator_decision_firewall_report(gate: dict[str, Any], output_dir: Path) -> Path:
    readiness = gate.get("readiness", {})
    counts = gate.get("counts", {})
    lines = [
        "# Plugin Availability Operator Decision Firewall Gate",
        "",
        f"- Project: `{gate.get('project_name')}`",
        f"- Created UTC: `{gate.get('created_at')}`",
        f"- Status: `{gate.get('status')}`",
        f"- Passed: `{gate.get('passed')}`",
        f"- Candidate firewalled: `{readiness.get('candidate_manifest_firewalled_from_accepted_evidence')}`",
        f"- Accepted manifest ready: `{readiness.get('accepted_operator_manifest_ready')}`",
        f"- Safe to write parameters: `{readiness.get('safe_to_write_parameters')}`",
        "",
        "This report checks that operator decision candidates do not become accepted evidence without acknowledgement.",
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
    lines.extend(["", "## Candidate Entries", ""])
    if not gate.get("candidate_entries"):
        lines.append("- none")
    for item in gate.get("candidate_entries", []):
        lines.extend(
            [
                f"### {item.get('plugin_name')}",
                "",
                f"- Status: `{item.get('status')}`",
                f"- Resolution: `{item.get('resolution')}`",
                f"- Operator acknowledged: `{item.get('operator_acknowledged')}`",
                f"- Automatic writes allowed: `{item.get('automatic_parameter_writes_allowed')}`",
                f"- Fallback requires validation: `{item.get('fallback_requires_validation')}`",
                f"- Blockers: `{item.get('blockers', [])}`",
                "",
            ]
        )
    lines.extend(["## Accepted Entries", ""])
    if not gate.get("accepted_entries"):
        lines.append("- none")
    for item in gate.get("accepted_entries", []):
        lines.extend(
            [
                f"### {item.get('plugin_name')}",
                "",
                f"- Status: `{item.get('status')}`",
                f"- Resolution: `{item.get('resolution')}`",
                f"- Operator acknowledged: `{item.get('operator_acknowledged')}`",
                f"- Automatic writes allowed: `{item.get('automatic_parameter_writes_allowed')}`",
                f"- Blockers: `{item.get('blockers', [])}`",
                "",
            ]
        )
    lines.extend(["## Limits", ""])
    lines.extend([f"- {item}" for item in gate.get("limits", [])])
    path = Path(output_dir) / GATE_REPORT_REL_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return path

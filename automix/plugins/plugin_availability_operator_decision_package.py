from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from automix.plugins.plugin_adapter_schema import compact_plugin_name, now_utc, write_json


PLUGIN_AVAILABILITY_OPERATOR_DECISION_PACKAGE_SCHEMA = "automix-plugin-availability-operator-decision-package-v1"
PLUGIN_AVAILABILITY_DISABLE_MANIFEST_CANDIDATE_SCHEMA = "automix-plugin-availability-disable-manifest-candidate-v1"
ACCEPTED_DISABLE_MANIFEST_SCHEMA = "automix-plugin-availability-disable-manifest-v1"

PACKAGE_REL_PATH = Path("eval_reports/plugin_availability_operator_decision_package.json")
PACKAGE_REPORT_REL_PATH = Path("eval_reports/plugin_availability_operator_decision_package.md")
CHECKLIST_REL_PATH = Path("review/plugin_availability_operator_decision_checklist.md")
CANDIDATE_REL_PATH = Path("review/plugin_availability_disable_manifest_candidate.json")
ACCEPTED_MANIFEST_REL_PATH = Path("review/plugin_availability_disable_manifest.json")
RESOLUTION_PLAN_REL_PATH = Path("eval_reports/plugin_availability_resolution_plan.json")
DECISION_GATE_REL_PATH = Path("eval_reports/plugin_availability_decision_gate.json")


def _load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _sha256(path: Path) -> str:
    if not path.exists():
        return ""
    if path.is_dir():
        return ""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _source_artifact(path: Path) -> dict[str, Any]:
    data = _load_json(path)
    return {
        "path": str(path),
        "schema": str(data.get("schema", "")),
        "sha256": _sha256(path),
    }


def _stable_request_token(*, project_name: str, output_dir: Path, source_artifacts: dict[str, Any], created_at: str) -> str:
    payload = {
        "project_name": project_name,
        "output_dir": str(output_dir),
        "created_at": created_at,
        "source_artifacts": source_artifacts,
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _decision_lookup(gate: dict[str, Any]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for item in gate.get("decisions", []) or []:
        if not isinstance(item, dict):
            continue
        name = str(item.get("plugin_name", "")).strip()
        if name:
            out[compact_plugin_name(name)] = item
    return out


def _candidate_manifest(
    decision_items: list[dict[str, Any]],
    source_artifacts: dict[str, Any] | None = None,
    *,
    operator_decision_request_token: str,
) -> dict[str, Any]:
    return {
        "schema": PLUGIN_AVAILABILITY_DISABLE_MANIFEST_CANDIDATE_SCHEMA,
        "target_schema_after_operator_acceptance": ACCEPTED_DISABLE_MANIFEST_SCHEMA,
        "candidate_only": True,
        "operator_acknowledgement_required": True,
        "operator_decision_request_token": operator_decision_request_token,
        "generated_at_utc": now_utc(),
        "provenance": {
            "generated_by": "plugin_availability_operator_decision_package",
            "source_artifacts": source_artifacts or {},
        },
        "safe_to_write_parameters": False,
        "disabled_plugins": [
            {
                "plugin_name": item.get("plugin_name", ""),
                "resolution": item.get("recommended_resolution", "disable_for_automatic_drafts"),
                "fallback_candidate": item.get("fallback_candidate", ""),
                "fallback_requires_validation": bool(item.get("fallback_requires_validation", False)),
                "automatic_parameter_writes_allowed": False,
                "operator_decision_request_token": operator_decision_request_token,
                "operator_acknowledged": False,
                "operator_note": "",
            }
            for item in decision_items
            if item.get("recommended_resolution") in {"disable_for_automatic_drafts", "manual_review_only"}
        ],
        "limits": [
            "This candidate is not accepted evidence.",
            "Copy decisions into plugin_availability_disable_manifest.json only after explicit operator acknowledgement.",
            "Fallback parameter writes remain blocked until semantic validation reports pass.",
        ],
    }


def _decision_item(resolution: dict[str, Any], decision: dict[str, Any]) -> dict[str, Any]:
    plugin_name = resolution.get("plugin_name", "")
    return {
        "plugin_name": plugin_name,
        "family": resolution.get("family", ""),
        "category": resolution.get("category", ""),
        "recommended_resolution": resolution.get("recommended_resolution", ""),
        "allowed_operator_resolutions": [
            "disable_for_automatic_drafts",
            "manual_review_only",
            "keep_unavailable_blocked",
            "install_and_rerun_preflight",
        ],
        "fallback_candidate": resolution.get("fallback_candidate", ""),
        "fallback_requires_validation": bool(resolution.get("fallback_requires_validation", False)),
        "automatic_parameter_writes_allowed": False,
        "operator_decision_required": bool(resolution.get("operator_decision_required", True)),
        "current_decision_status": decision.get("status", "missing"),
        "current_operator_resolution": decision.get("operator_resolution", ""),
        "current_operator_acknowledged": bool(decision.get("operator_acknowledged", False)),
        "current_blockers": decision.get("blockers", []),
        "required_evidence": resolution.get("required_evidence", []),
        "disallowed_actions": resolution.get("disallowed_actions", []),
        "decision_steps": [
            "Choose install, disable for automatic drafts, manual-review only, or keep unavailable blocked.",
            "If choosing install_and_rerun_preflight, install the plugin and rerun plugin_validation_preflight before treating it as resolved.",
            "If choosing disable or manual-review only, create plugin_availability_disable_manifest.json with accepted schema and operator_acknowledged=true.",
            "Keep automatic_parameter_writes_allowed=false for unavailable plugins and fallback candidates.",
            "Rerun plugin_availability_decision_gate.py after writing the accepted operator manifest.",
        ],
    }


def build_plugin_availability_operator_decision_package(
    *,
    project_name: str,
    output_dir: Path,
    resolution_plan: dict[str, Any] | None = None,
    decision_gate: dict[str, Any] | None = None,
    resolution_plan_path: Path | None = None,
    decision_gate_path: Path | None = None,
    output_path: Path | None = None,
) -> dict[str, Any]:
    output_dir = Path(output_dir)
    resolution_plan_path = resolution_plan_path or output_dir / RESOLUTION_PLAN_REL_PATH
    decision_gate_path = decision_gate_path or output_dir / DECISION_GATE_REL_PATH
    resolution_plan = resolution_plan or _load_json(resolution_plan_path)
    decision_gate = decision_gate or _load_json(decision_gate_path)

    blockers: list[str] = []
    warnings: list[str] = []
    if not resolution_plan or resolution_plan.get("schema") != "automix-plugin-availability-resolution-plan-v1":
        blockers.append("plugin_availability_resolution_plan_missing_or_invalid")
        resolution_plan = resolution_plan if isinstance(resolution_plan, dict) else {}
    if not decision_gate or decision_gate.get("schema") != "automix-plugin-availability-decision-gate-v1":
        warnings.append("plugin_availability_decision_gate_missing_or_invalid")
        decision_gate = decision_gate if isinstance(decision_gate, dict) else {}

    decisions_by_name = _decision_lookup(decision_gate)
    resolutions = [
        item
        for item in resolution_plan.get("resolutions", []) or []
        if isinstance(item, dict) and item.get("operator_decision_required", False)
    ]
    decision_items = [
        _decision_item(resolution, decisions_by_name.get(compact_plugin_name(str(resolution.get("plugin_name", ""))), {}))
        for resolution in resolutions
    ]
    missing_decisions = [
        item.get("plugin_name", "")
        for item in decision_items
        if item.get("current_decision_status") != "accepted"
    ]
    if resolution_plan.get("warnings"):
        warnings.extend(resolution_plan.get("warnings", []))
    if decision_gate.get("warnings"):
        warnings.extend(decision_gate.get("warnings", []))

    source_artifacts = {
        "resolution_plan": _source_artifact(resolution_plan_path),
        "decision_gate": _source_artifact(decision_gate_path),
    }
    package_created_at = now_utc()
    operator_decision_request_token = _stable_request_token(
        project_name=project_name,
        output_dir=output_dir,
        source_artifacts=source_artifacts,
        created_at=package_created_at,
    )
    candidate = _candidate_manifest(
        decision_items,
        source_artifacts=source_artifacts,
        operator_decision_request_token=operator_decision_request_token,
    )
    write_json(output_dir / CANDIDATE_REL_PATH, candidate)

    accepted_manifest_path = output_dir / ACCEPTED_MANIFEST_REL_PATH
    status = "operator_decision_package_blocked" if blockers else "no_operator_decisions_required"
    if not blockers and decision_items:
        status = "operator_decisions_ready_for_human_acknowledgement"
    if not blockers and decision_items and not missing_decisions:
        status = "operator_decisions_already_accepted"

    package = {
        "schema": PLUGIN_AVAILABILITY_OPERATOR_DECISION_PACKAGE_SCHEMA,
        "project_name": project_name,
        "created_at": package_created_at,
        "output_dir": str(output_dir),
        "source_resolution_plan": str(resolution_plan_path),
        "source_decision_gate": str(decision_gate_path),
        "status": status,
        "operator_decision_package_ready": bool(decision_items and not blockers),
        "availability_decisions_ready": bool(decision_gate.get("availability_decisions_ready", False)),
        "safe_to_write_parameters": False,
        "source_artifacts": source_artifacts,
        "operator_decision_request_token": operator_decision_request_token,
        "required_decisions_total": len(decision_items),
        "accepted_decisions_total": sum(1 for item in decision_items if item.get("current_decision_status") == "accepted"),
        "missing_decisions": missing_decisions,
        "candidate_manifest_path": str(output_dir / CANDIDATE_REL_PATH),
        "accepted_manifest_path": str(accepted_manifest_path),
        "accepted_manifest_exists": accepted_manifest_path.exists(),
        "decision_items": decision_items,
        "blockers": sorted(set(blockers)),
        "warnings": sorted(set(warnings)),
        "limits": [
            "This package does not install plugins, open REAPER, write parameters, render, or approve audio.",
            "The candidate manifest is not accepted evidence and uses a candidate-only schema.",
            "Fallback writes remain blocked until semantic validation reports pass.",
        ],
    }
    target = output_path or output_dir / PACKAGE_REL_PATH
    package["candidate_manifest_sha256"] = _sha256(output_dir / CANDIDATE_REL_PATH)
    write_json(target, package)
    write_plugin_availability_operator_decision_package_report(package, output_dir)
    write_plugin_availability_operator_decision_checklist(package, output_dir)
    return package


def write_plugin_availability_operator_decision_package_report(package: dict[str, Any], output_dir: Path) -> Path:
    lines = [
        "# Plugin Availability Operator Decision Package",
        "",
        f"- Project: `{package.get('project_name')}`",
        f"- Created UTC: `{package.get('created_at')}`",
        f"- Status: `{package.get('status')}`",
        f"- Package ready: `{package.get('operator_decision_package_ready')}`",
        f"- Availability decisions ready: `{package.get('availability_decisions_ready')}`",
        f"- Required decisions: `{package.get('required_decisions_total')}`",
        f"- Accepted decisions: `{package.get('accepted_decisions_total')}`",
        f"- Safe to write parameters: `{package.get('safe_to_write_parameters')}`",
        "",
        "This package prepares operator plugin-availability decisions only. It does not accept decisions by itself.",
        "",
        "## Blockers",
        "",
    ]
    lines.extend([f"- `{item}`" for item in package.get("blockers", [])] or ["- none"])
    lines.extend(["", "## Warnings", ""])
    lines.extend([f"- `{item}`" for item in package.get("warnings", [])] or ["- none"])
    lines.extend(["", "## Decisions", ""])
    if not package.get("decision_items"):
        lines.append("- none")
    for item in package.get("decision_items", []):
        lines.extend(
            [
                f"### {item.get('plugin_name')}",
                "",
                f"- Recommended resolution: `{item.get('recommended_resolution')}`",
                f"- Current status: `{item.get('current_decision_status')}`",
                f"- Fallback candidate: `{item.get('fallback_candidate')}`",
                f"- Fallback requires validation: `{item.get('fallback_requires_validation')}`",
                f"- Automatic parameter writes allowed: `{item.get('automatic_parameter_writes_allowed')}`",
                f"- Current blockers: `{item.get('current_blockers', [])}`",
                "",
            ]
        )
    path = Path(output_dir) / PACKAGE_REPORT_REL_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return path


def write_plugin_availability_operator_decision_checklist(package: dict[str, Any], output_dir: Path) -> Path:
    lines = [
        "# Plugin Availability Operator Decision Checklist",
        "",
        f"- Candidate manifest: `{package.get('candidate_manifest_path')}`",
        f"- Accepted manifest path: `{package.get('accepted_manifest_path')}`",
        f"- Safe to write parameters: `{package.get('safe_to_write_parameters')}`",
        "",
        "The candidate manifest is not accepted evidence. Use it as a draft only.",
        "",
        "## Required Decisions",
        "",
    ]
    if not package.get("decision_items"):
        lines.append("- none")
    for item in package.get("decision_items", []):
        lines.append(f"### {item.get('plugin_name')}")
        lines.append("")
        lines.append(f"- Recommended resolution: `{item.get('recommended_resolution')}`")
        lines.append(f"- Allowed resolutions: `{item.get('allowed_operator_resolutions')}`")
        lines.append(f"- Fallback candidate: `{item.get('fallback_candidate')}`")
        lines.append("- Steps:")
        lines.extend([f"  - {step}" for step in item.get("decision_steps", [])])
        lines.append("- Disallowed actions:")
        lines.extend([f"  - {action}" for action in item.get("disallowed_actions", [])] or ["  - none"])
        lines.append("")
    lines.extend(
        [
            "## After Operator Acknowledgement",
            "",
            "1. Write `automix/review/plugin_availability_disable_manifest.json` with schema `automix-plugin-availability-disable-manifest-v1`.",
            "2. Set `operator_acknowledged=true` only for explicit operator decisions.",
            "3. Keep `automatic_parameter_writes_allowed=false`.",
            "4. Rerun `python3 scripts/run_plugin_availability_decision_gate.py --project-name project --output-dir automix`.",
            "5. Rerun collection and semantic validation planning after the decision gate is ready.",
        ]
    )
    path = Path(output_dir) / CHECKLIST_REL_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return path

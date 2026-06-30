from __future__ import annotations

from pathlib import Path
from typing import Any

from automix.plugins.plugin_adapter_schema import now_utc, write_json


REPORT_INDEX_SCHEMA = "automix-report-index-v1"

GROUPS = {
    "github integration": [
        "github_integration",
        "reaper_mcp",
        "reapy",
        "bridge",
        "current_state",
    ],
    "plugin intelligence": [
        "plugin_inventory",
        "plugin_parameter",
        "plugin_capability",
        "plugin_validation_preflight",
        "plugin_semantic_validation",
        "plugin_semantic_validation_collection",
        "plugin_semantic_validation_queue",
        "plugin_semantic_validation_runtime_collection",
        "plugin_semantic_validation_runtime_collector",
        "plugin_semantic_validation_runtime_observation",
        "plugin_semantic_validation_runtime_report_authoring",
        "plugin_semantic_validation_runtime",
        "reaper_runtime_collection_operator",
        "reaper_runtime_collector_safety",
        "plugin_availability_operator",
        "plugin_validation_action",
        "plugin_availability_resolution",
        "plugin_availability_decision",
    ],
    "project scan": ["project_context", "project_state"],
    "source classification": ["source", "source_acceptance", "batch_pitch", "role_map", "source_handoff"],
    "artifact evidence": ["artifact_evidence", "artifact_signal"],
    "validation harness": ["fixture_coverage", "requirements_traceability", "prompt41_validation"],
    "local device QC": ["local_device_qc"],
    "handoff evidence": [
        "github_upload",
        "public_pc_handoff",
        "handoff_package",
        "legacy_fixture",
        "legacy_api_regression",
        "legacy_semantic_firewall",
    ],
    "intent classification": ["intent_classification"],
    "processing safety": ["processing_policy", "policy_audit"],
    "vocal recovery": ["recovery"],
    "pitch correction": ["pitch"],
    "vocal placement": ["placement"],
    "reference matching": ["reference"],
    "premaster": ["premaster", "translation"],
    "final export": ["final_export", "final_render", "render_evidence", "deliverable", "deliverable_package_evidence", "final_human_approval"],
    "delivery readiness": [
        "professional_readiness",
        "approval_export_readiness",
        "final_approval_evidence",
        "final_delivery_consistency",
        "ab_preview_evidence",
        "readiness_audit",
        "claim_language",
        "open_risk",
        "risk_remediation",
        "risk_root_cause",
        "path_hygiene",
    ],
    "user feedback": ["feedback", "revision_memory", "revision_report", "action_plan", "qc_integration"],
    "QC": ["qc", "final_qc_evidence", "eval", "ab_preview"],
    "rollback": ["rollback"],
}


def _stage_for_path(path: Path) -> str:
    lower = path.name.lower()
    for group, hints in GROUPS.items():
        if any(hint in lower for hint in hints):
            return group
    parent = path.parent.name.lower()
    for group, hints in GROUPS.items():
        if any(hint in parent for hint in hints):
            return group
    return "other"


def build_report_index(
    *,
    project_name: str,
    output_dir: Path,
    stage_results: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    candidates: list[Path] = []
    for pattern in [
        "analysis_reports/*",
        "eval_reports/*",
        "chain_plans/*",
        "rollback/*",
        "export/*",
        "review/*",
        "orchestrator/*",
    ]:
        candidates.extend(path for path in (output_dir).glob(pattern) if path.is_file())
    reports = [
        {
            "stage": _stage_for_path(path),
            "type": path.suffix.lstrip(".") or "file",
            "path": str(path),
            "exists": path.exists(),
            "summary": path.name,
            "status": "passed" if path.exists() else "missing",
        }
        for path in sorted(set(candidates))
    ]
    stage_result_names = {result.get("stage") for result in stage_results or []}
    missing_expected = []
    for expected in ["plugin_intelligence", "project_scan", "global_qc", "rollback"]:
        if expected not in stage_result_names:
            missing_expected.append(expected)
    index = {
        "schema": REPORT_INDEX_SCHEMA,
        "project_name": project_name,
        "created_at": now_utc(),
        "reports": reports,
        "missing_expected_reports": missing_expected,
        "warnings": [],
    }
    write_json(output_dir / "eval_reports" / "automix_report_index.json", index)
    write_report_index_markdown(index, output_dir)
    return index


def write_report_index_markdown(index: dict[str, Any], output_dir: Path) -> Path:
    lines = ["# AutoMix Report Index", "", f"- Project: `{index.get('project_name')}`", f"- Created UTC: `{index.get('created_at')}`", ""]
    grouped: dict[str, list[dict[str, Any]]] = {}
    for report in index.get("reports", []):
        grouped.setdefault(report.get("stage", "other"), []).append(report)
    for group in GROUPS:
        lines.extend([f"## {group.title()}", ""])
        for report in grouped.get(group, []):
            lines.append(f"- `{report.get('path')}` - {report.get('status')}")
        if not grouped.get(group):
            lines.append("- none")
        lines.append("")
    if grouped.get("other"):
        lines.extend(["## Other", ""])
        for report in grouped["other"]:
            lines.append(f"- `{report.get('path')}` - {report.get('status')}")
    path = output_dir / "eval_reports" / "automix_report_index.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from automix.plugins.plugin_adapter_schema import now_utc


CURRENT_STATE_SCHEMA = "automix-current-state-summary-v1"


def _stage_status(manifest: dict[str, Any], stage: str) -> str:
    for result in manifest.get("stage_results", []):
        if result.get("stage") == stage:
            return str(result.get("status", "not_run"))
    return "not_run"


def build_current_state_summary(
    *,
    project_name: str,
    output_dir: Path,
    manifest: dict[str, Any],
    global_qc: dict[str, Any],
    report_count: int,
) -> dict[str, Any]:
    github_smoke_path = output_dir / "eval_reports" / "github_integration_smoke.json"
    github_smoke = _load_json(github_smoke_path)
    blockers = list(manifest.get("failures", [])) + list(global_qc.get("critical_blockers", []))
    warnings = list(manifest.get("warnings", [])) + list(global_qc.get("warnings", []))
    safe_to_export = bool(manifest.get("safe_to_export"))
    global_status = str(manifest.get("global_status", "failed"))
    development_status = "ready_for_dry_run_development"
    if safe_to_export:
        development_status = "ready_for_export_review"
    elif blockers:
        development_status = "blocked_review_required"
    elif global_status not in {"scan_complete", "drafts_created_review_required"}:
        development_status = "review_required"

    return {
        "schema": CURRENT_STATE_SCHEMA,
        "project_name": project_name,
        "created_at": now_utc(),
        "mode": manifest.get("mode"),
        "global_status": global_status,
        "development_status": development_status,
        "safe_to_export": safe_to_export,
        "overall_qc_status": global_qc.get("overall_qc_status", "review_required"),
        "stage_status": {
            "plugin_intelligence": _stage_status(manifest, "plugin_intelligence"),
            "github_integration_smoke": _stage_status(manifest, "github_integration_smoke"),
            "project_scan": _stage_status(manifest, "project_scan"),
            "intent_classification": _stage_status(manifest, "intent_classification"),
            "professional_readiness_audit": _stage_status(manifest, "professional_readiness_audit"),
            "final_export": _stage_status(manifest, "final_export"),
        },
        "github_integration": {
            "path": str(github_smoke_path),
            "exists": github_smoke_path.exists(),
            "status": github_smoke.get("status", "missing") if github_smoke else "missing",
            "qc_passed": bool(github_smoke.get("qc_passed", False)) if github_smoke else False,
            "safe_to_write_parameters": False,
            "live_bridge_enabled": False,
            "warnings": github_smoke.get("warnings", []) if github_smoke else ["github_integration_smoke_missing"],
        },
        "qc": {
            "safe_to_export": global_qc.get("safe_to_export", False),
            "critical_blockers": sorted(set(global_qc.get("critical_blockers", []))),
            "warnings": sorted(set(global_qc.get("warnings", []))),
        },
        "reports": {
            "count": report_count,
            "manifest": str(output_dir / "orchestrator" / "automix_orchestration_manifest.json"),
            "global_qc": str(output_dir / "eval_reports" / "global_qc_summary.json"),
            "report_index": str(output_dir / "eval_reports" / "automix_report_index.json"),
        },
        "next_required_actions": manifest.get("next_required_actions", []),
        "warnings": sorted(set(warnings)),
        "blockers": sorted(set(blockers)),
    }


def write_current_state_summary(summary: dict[str, Any], output_dir: Path) -> dict[str, str]:
    json_path = output_dir / "eval_reports" / "current_state_summary.json"
    md_path = output_dir / "eval_reports" / "current_state_summary.md"
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    md_path.write_text(_to_markdown(summary), encoding="utf-8")
    return {"json": str(json_path), "markdown": str(md_path)}


def _load_json(path: Path) -> dict[str, Any] | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _to_markdown(summary: dict[str, Any]) -> str:
    github = summary.get("github_integration", {})
    qc = summary.get("qc", {})
    lines = [
        "# Current State Summary",
        "",
        "## Status",
        "",
        f"- Project: `{summary.get('project_name')}`",
        f"- Mode: `{summary.get('mode')}`",
        f"- Global status: `{summary.get('global_status')}`",
        f"- Development status: `{summary.get('development_status')}`",
        f"- Overall QC: `{summary.get('overall_qc_status')}`",
        f"- Safe to export: `{summary.get('safe_to_export')}`",
        "",
        "## GitHub Integration",
        "",
        f"- Status: `{github.get('status')}`",
        f"- QC passed: `{github.get('qc_passed')}`",
        f"- Safe to write parameters: `{github.get('safe_to_write_parameters')}`",
        f"- Live bridge enabled: `{github.get('live_bridge_enabled')}`",
        f"- Report: `{github.get('path')}`",
        "",
        "## Key Stage Status",
        "",
    ]
    for stage, status in summary.get("stage_status", {}).items():
        lines.append(f"- `{stage}`: `{status}`")
    lines.extend(["", "## QC Blockers", ""])
    for blocker in qc.get("critical_blockers", []):
        lines.append(f"- `{blocker}`")
    if not qc.get("critical_blockers"):
        lines.append("- none")
    lines.extend(["", "## Next Required Actions", ""])
    for action in summary.get("next_required_actions", []):
        lines.append(f"- {action}")
    if not summary.get("next_required_actions"):
        lines.append("- none")
    lines.append("")
    return "\n".join(lines)

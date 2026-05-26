from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from arrangement_qc import render_arrangement_qc_report, score_arrangement_plan
from commercial_readiness_qc import evaluate_commercial_readiness, render_commercial_readiness_report


def build_autopilot_qc(
    *,
    arrangement_plan: dict[str, Any] | None = None,
    mix_master_plan: dict[str, Any] | None = None,
    reference_profile: dict[str, Any] | None = None,
    sample_analysis: dict[str, Any] | None = None,
    vocal_to_code: dict[str, Any] | None = None,
    song_structure: dict[str, Any] | None = None,
    render_manifest: dict[str, Any] | None = None,
    completion_gate: dict[str, Any] | None = None,
    input_mode: str = "instrumental_beat",
) -> dict[str, Any]:
    arrangement = score_arrangement_plan(
        arrangement_plan,
        sample_analysis=sample_analysis,
        vocal_to_code=vocal_to_code,
        song_structure=song_structure,
    )
    commercial = evaluate_commercial_readiness(
        arrangement_qc=arrangement,
        mix_master_plan=mix_master_plan,
        reference_profile=reference_profile,
        completion_gate=completion_gate or (render_manifest or {}).get("completion_gate"),
        render_manifest=render_manifest,
        input_mode=input_mode,
    )
    return {
        "schema_version": "autopilot_qc_report.v1",
        "arrangement_qc": arrangement,
        "commercial_readiness_qc": commercial,
        "status": commercial["status"],
        "complete": bool((completion_gate or (render_manifest or {}).get("completion_gate") or {}).get("complete")),
        "completion_rule": "PLAN_PASS is not COMPLETE. COMPLETE only when completion_gate complete is true.",
    }


def render_autopilot_qc_report(payload: dict[str, Any]) -> str:
    lines = [
        "# Autopilot QC Report",
        "",
        f"- status: {payload['status']}",
        f"- complete: {str(bool(payload['complete'])).lower()}",
        f"- completion rule: {payload['completion_rule']}",
        "",
        "## Arrangement QC",
        f"- average score: {payload['arrangement_qc']['average_score']}",
        f"- plan pass: {str(bool(payload['arrangement_qc']['plan_pass'])).lower()}",
        "",
        "## Commercial Readiness",
        f"- status: {payload['commercial_readiness_qc']['status']}",
        f"- capability statement: {payload['commercial_readiness_qc']['capability_statement']}",
        f"- release score average: {payload['commercial_readiness_qc'].get('commercial_release_score', {}).get('average_score')}",
        "- commercial success claimed: false",
        "",
        "## False Claim Risk",
        f"- high risk: {str(bool(payload['commercial_readiness_qc']['false_claim_risk']['high'])).lower()}",
        f"- risky flags: {', '.join(payload['commercial_readiness_qc']['false_claim_risk']['risky_flags']) or 'none'}",
    ]
    return "\n".join(lines).rstrip() + "\n"


def write_autopilot_qc_reports(project_root: str | Path, payload: dict[str, Any]) -> dict[str, Path]:
    root = Path(project_root)
    report_dir = root / "06_QC_REPORT"
    report_dir.mkdir(parents=True, exist_ok=True)
    arrangement_path = report_dir / "arrangement_qc_report.md"
    commercial_path = report_dir / "commercial_readiness_report.md"
    autopilot_path = report_dir / "autopilot_qc_report.md"
    json_path = report_dir / "autopilot_qc_report.json"
    arrangement_path.write_text(render_arrangement_qc_report(payload["arrangement_qc"]), encoding="utf-8")
    commercial_path.write_text(render_commercial_readiness_report(payload["commercial_readiness_qc"]), encoding="utf-8")
    autopilot_path.write_text(render_autopilot_qc_report(payload), encoding="utf-8")
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return {
        "arrangement_qc_report": arrangement_path,
        "commercial_readiness_report": commercial_path,
        "autopilot_qc_report": autopilot_path,
        "autopilot_qc_json": json_path,
    }

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from automix.orchestrator.report_index import build_report_index
from automix.orchestrator.risk_remediation_planner import build_risk_remediation_plan
from automix.plugins.plugin_adapter_schema import write_json
from automix.plugins.plugin_semantic_validation_runtime_evidence_gate import (
    PLUGIN_SEMANTIC_VALIDATION_RUNTIME_MANIFEST_SCHEMA,
    build_plugin_semantic_validation_runtime_evidence_gate,
)


def queue_job(out: Path, plugin_name: str = "ReaEQ (Cockos)") -> dict:
    return {
        "job_id": "semantic_validation_01_reaeq_cockos",
        "plugin_name": plugin_name,
        "collection_action": "collect_missing_reaper_observed_semantic_report",
        "target_report_path": str(out / "analysis_reports/plugin_parameter_validation_reaeq_cockos_reaper_observed.json"),
        "requires_reaper_runtime": True,
        "requires_operator_review": True,
    }


def write_queue(out: Path, jobs: list[dict] | None = None, blocked_jobs: list[dict] | None = None) -> None:
    jobs = jobs if jobs is not None else [queue_job(out)]
    write_json(
        out / "eval_reports/plugin_semantic_validation_queue.json",
        {
            "schema": "automix-plugin-semantic-validation-queue-v1",
            "project_name": "unit",
            "queue_jobs_total": len(jobs),
            "blocked_jobs_total": len(blocked_jobs or []),
            "ready_to_run_reaper_collection": bool(jobs),
            "requires_reaper_runtime": bool(jobs),
            "requires_operator_review": bool(jobs or blocked_jobs),
            "safe_to_write_parameters": False,
            "queue_jobs": jobs,
            "blocked_jobs": blocked_jobs or [],
            "blockers": [],
            "warnings": [],
        },
    )


def write_runtime_manifest(out: Path, jobs: list[dict], *, schema: str = PLUGIN_SEMANTIC_VALIDATION_RUNTIME_MANIFEST_SCHEMA) -> None:
    write_json(
        out / "review/plugin_semantic_validation_runtime_manifest.json",
        {
            "schema": schema,
            "operator_ready_to_run": True,
            "requires_reaper_runtime": True,
            "safe_to_write_parameters": False,
            "queue_jobs": jobs,
        },
    )


def manifest_job(job_id: str = "semantic_validation_01_reaeq_cockos") -> dict:
    return {
        "job_id": job_id,
        "plugin_name": "ReaEQ (Cockos)",
        "operator_acknowledged": True,
        "runtime_observed": True,
        "report_written": True,
        "report_reaudited_by_semantic_gate": True,
    }


def write_validation_report(out: Path, *, passed: bool = True, fake_success: bool = False) -> None:
    write_json(
        out / "analysis_reports/plugin_parameter_validation_reaeq_cockos_reaper_observed.json",
        {
            "schema": "automix-plugin-parameter-validation-report-v1",
            "plugin_name": "ReaEQ (Cockos)",
            "adapter_id": "reaeq_cockos",
            "status": "passed" if passed else "failed",
            "safe_for_automix": passed,
            "no_fake_success": not fake_success,
            "controls": {
                "presence_gain": {
                    "validated": passed,
                    "write_allowed": passed,
                    "confidence": 0.91 if passed else 0.2,
                    "target_name": "Band 2 Gain" if passed else "",
                    "safe_min": -2.0,
                    "safe_max": 2.0,
                }
            },
        },
    )


def test_runtime_evidence_gate_missing_manifest_blocks_and_writes_request(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    write_queue(out)
    gate = build_plugin_semantic_validation_runtime_evidence_gate(project_name="unit", output_dir=out)
    assert gate["status"] == "runtime_manifest_missing"
    assert gate["runtime_evidence_ready"] is False
    assert "plugin_semantic_validation_runtime_manifest_missing" in gate["blockers"]
    assert (out / "review/plugin_semantic_validation_runtime_evidence_request.md").exists()


def test_runtime_evidence_gate_rejects_template_manifest_schema(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    write_queue(out)
    write_runtime_manifest(out, [manifest_job()], schema="automix-plugin-semantic-validation-runtime-manifest-template-v1")
    gate = build_plugin_semantic_validation_runtime_evidence_gate(project_name="unit", output_dir=out)
    assert gate["runtime_evidence_ready"] is False
    assert "plugin_semantic_validation_runtime_manifest_is_template" in gate["blockers"]


def test_runtime_evidence_gate_accepts_manifest_and_passing_report_without_granting_writes(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    write_queue(out)
    write_runtime_manifest(out, [manifest_job()])
    write_validation_report(out)
    gate = build_plugin_semantic_validation_runtime_evidence_gate(project_name="unit", output_dir=out)
    assert gate["status"] == "runtime_evidence_ready"
    assert gate["runtime_evidence_ready"] is True
    assert gate["ready_for_semantic_gate_rerun"] is True
    assert gate["safe_to_write_parameters"] is False
    assert gate["accepted_jobs_total"] == 1
    assert gate["blockers"] == []


def test_runtime_evidence_gate_missing_manifest_entry_blocks(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    write_queue(out)
    write_runtime_manifest(out, [])
    write_validation_report(out)
    gate = build_plugin_semantic_validation_runtime_evidence_gate(project_name="unit", output_dir=out)
    assert gate["runtime_evidence_ready"] is False
    assert "runtime_manifest_job_missing:semantic_validation_01_reaeq_cockos" in gate["blockers"]


def test_runtime_evidence_gate_blocks_failing_or_fake_validation_report(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    write_queue(out)
    write_runtime_manifest(out, [manifest_job()])
    write_validation_report(out, passed=False, fake_success=True)
    gate = build_plugin_semantic_validation_runtime_evidence_gate(project_name="unit", output_dir=out)
    assert gate["runtime_evidence_ready"] is False
    assert "runtime_validation_report_not_passed:semantic_validation_01_reaeq_cockos:failed" in gate["blockers"]
    assert "runtime_validation_report_no_fake_success_missing:semantic_validation_01_reaeq_cockos" in gate["blockers"]
    assert "runtime_validation_report_has_no_write_safe_controls:semantic_validation_01_reaeq_cockos" in gate["blockers"]


def test_runtime_evidence_gate_cli_require_ready_returns_nonzero_when_manifest_missing(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    write_queue(out)
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/run_plugin_semantic_validation_runtime_evidence_gate.py"),
            "--project-name",
            "unit",
            "--output-dir",
            str(out),
            "--require-ready",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    data = json.loads(result.stdout)
    assert result.returncode == 2
    assert data["runtime_evidence_ready"] is False
    assert "plugin_semantic_validation_runtime_manifest_missing" in data["blockers"]


def test_report_index_groups_plugin_semantic_validation_runtime_evidence_gate(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    write_queue(out)
    build_plugin_semantic_validation_runtime_evidence_gate(project_name="unit", output_dir=out)
    index = build_report_index(project_name="unit", output_dir=out, stage_results=[])
    assert any(
        item["stage"] == "plugin intelligence" and item["summary"] == "plugin_semantic_validation_runtime_evidence_gate.json"
        for item in index["reports"]
    )


def test_risk_remediation_plan_recommends_runtime_evidence_gate(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    write_json(
        out / "eval_reports/open_risk_register.json",
        {
            "schema": "automix-open-risk-register-v1",
            "project_name": "unit",
            "passed": False,
            "risk_counts": {"blocker": 1, "warning": 0, "review": 0, "info": 0},
            "open_risks": [
                {
                    "risk_id": "risk_plugin_runtime",
                    "severity": "blocker",
                    "category": "plugin",
                    "source_report": "plugin_semantic_validation_runtime_evidence_gate.json",
                    "code": "semantic_validation_runtime:plugin_semantic_validation_runtime_manifest_missing",
                    "summary": "runtime evidence missing",
                    "recommended_next_action": "semantic_validation_runtime",
                }
            ],
            "blockers": ["semantic_validation_runtime:plugin_semantic_validation_runtime_manifest_missing"],
            "warnings": [],
        },
    )
    plan = build_risk_remediation_plan(project_name="unit", output_dir=out)
    plugin_action = next(action for action in plan["actions"] if action["phase"] == "plugin_safety")
    assert any("run_plugin_semantic_validation_runtime_evidence_gate.py" in command for command in plugin_action["recommended_commands"])
    assert "automix/eval_reports/plugin_semantic_validation_runtime_evidence_gate.json" in plugin_action["evidence_to_collect"]


if __name__ == "__main__":
    current = globals()
    failures: list[str] = []
    for name in sorted(k for k in current if k.startswith("test_")):
        fn = current[name]
        try:
            with tempfile.TemporaryDirectory() as directory:
                fn(Path(directory))
        except Exception as exc:  # pragma: no cover
            failures.append(f"{name}: {exc}")
    if failures:
        raise SystemExit("\n".join(failures))
    print("Prompt75 direct tests passed")

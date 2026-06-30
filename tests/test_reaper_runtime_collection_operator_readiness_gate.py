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
from automix.orchestrator.requirements_traceability_audit import build_requirements_traceability_audit
from automix.orchestrator.risk_remediation_planner import build_risk_remediation_plan
from automix.orchestrator.risk_remediation_planner import build_risk_remediation_plan
from automix.plugins.plugin_adapter_schema import write_json
from automix.plugins.plugin_semantic_validation_runtime_collection_package import (
    build_plugin_semantic_validation_runtime_collection_package,
)
from automix.plugins.plugin_semantic_validation_runtime_collector_package import (
    build_plugin_semantic_validation_runtime_collector_package,
)
from automix.plugins.reaper_runtime_collection_operator_readiness_gate import (
    REAPER_RUNTIME_COLLECTION_OPERATOR_READINESS_SCHEMA,
    build_reaper_runtime_collection_operator_readiness_gate,
)
from automix.plugins.reaper_runtime_collector_safety_audit import build_reaper_runtime_collector_safety_audit


def queue_job(plugin_name: str = "ReaEQ (Cockos)", job_id: str = "semantic_validation_01_reaeq_cockos") -> dict:
    return {
        "job_id": job_id,
        "plugin_name": plugin_name,
        "priority": 20,
        "category": "stock",
        "collection_action": "collect_missing_reaper_observed_semantic_report",
        "target_report_path": f"automix/analysis_reports/plugin_parameter_validation_{job_id}_reaper_observed.json",
        "requires_reaper_runtime": True,
        "requires_temporary_muted_test_context": True,
        "requires_operator_review": True,
        "required_observations": ["REAPER runtime observed the exact plugin", "parameter names listed by TrackFX_GetParamName"],
        "acceptance_criteria": ["status=passed only after manual semantic review"],
        "disallowed_actions": ["do not write parameters to the user's mix from this queue"],
    }


def write_local_device_qc(out: Path, *, ready: bool = True) -> None:
    write_json(
        out / "eval_reports/local_device_qc.json",
        {
            "schema": "automix-local-device-qc-v1",
            "status": "local_device_qc_ready" if ready else "local_device_qc_blocked",
            "passed": ready,
            "readiness": {
                "local_device_qc_ready": ready,
                "ready_for_reaper_runtime_collection": ready,
                "ready_for_applied_parameter_writes": False,
                "ready_for_delivery_claims": False,
                "report_only": True,
                "opens_reaper": False,
                "renders_audio": False,
                "writes_parameters": False,
                "saves_project": False,
            },
            "blockers": [] if ready else ["local_device_qc_fixture_blocked"],
            "warnings": [],
        },
    )


def write_queue(out: Path, jobs: list[dict] | None = None, blocked_jobs: list[dict] | None = None) -> None:
    jobs = jobs if jobs is not None else [queue_job()]
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


def build_runtime_package(out: Path, *, blocked: bool = True) -> None:
    blocked_jobs = [{"plugin_name": "OTT (Xfer Records)", "blockers": ["availability_decision_missing:OTT (Xfer Records)"]}] if blocked else []
    write_queue(
        out,
        [
            queue_job("ReaEQ (Cockos)", "semantic_validation_01_reaeq_cockos"),
            queue_job("ReaComp (Cockos)", "semantic_validation_02_reacomp_cockos"),
        ],
        blocked_jobs=blocked_jobs,
    )
    build_plugin_semantic_validation_runtime_collection_package(project_name="unit", output_dir=out)
    build_plugin_semantic_validation_runtime_collector_package(project_name="unit", output_dir=out)
    build_reaper_runtime_collector_safety_audit(project_name="unit", output_dir=out)


def write_availability_decision(out: Path, *, ready: bool, missing: list[str] | None = None) -> None:
    missing = missing or []
    write_json(
        out / "eval_reports/plugin_availability_decision_gate.json",
        {
            "schema": "automix-plugin-availability-decision-gate-v1",
            "status": "availability_decisions_ready" if ready else "operator_decision_manifest_missing",
            "availability_decisions_ready": ready,
            "required_decisions_total": len(missing),
            "missing_decisions": missing,
            "safe_to_write_parameters": False,
            "blockers": [] if ready else [f"operator_decision_missing:{item}" for item in missing],
            "warnings": [],
        },
    )


def test_operator_readiness_allows_partial_collection_but_blocks_complete_when_decisions_missing(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    write_local_device_qc(out)
    build_runtime_package(out, blocked=True)
    write_availability_decision(out, ready=False, missing=["OTT (Xfer Records)"])

    gate = build_reaper_runtime_collection_operator_readiness_gate(project_name="unit", output_dir=out)

    assert gate["schema"] == REAPER_RUNTIME_COLLECTION_OPERATOR_READINESS_SCHEMA
    assert gate["status"] == "partial_operator_runtime_collection_ready"
    assert gate["passed"] is True
    assert gate["ready_for_partial_operator_runtime_collection"] is True
    assert gate["ready_for_complete_operator_runtime_collection"] is False
    assert gate["safe_to_run_lua_collector"] is True
    assert gate["safe_to_write_parameters"] is False
    assert gate["collector_jobs_total"] == 2
    assert gate["blocked_queue_jobs_total"] == 1
    assert "complete_operator_collection_blocked_by_queue_jobs:1" in gate["warnings"]
    assert "availability_operator_decisions_missing:1" in gate["warnings"]
    assert len(gate["expected_observation_paths"]) == 2
    assert (out / "eval_reports/reaper_runtime_collection_operator_readiness.json").exists()
    assert (out / "eval_reports/reaper_runtime_collection_operator_readiness.md").exists()


def test_operator_readiness_marks_complete_when_no_blocked_jobs_or_missing_decisions(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    write_local_device_qc(out)
    build_runtime_package(out, blocked=False)
    write_availability_decision(out, ready=True, missing=[])

    gate = build_reaper_runtime_collection_operator_readiness_gate(project_name="unit", output_dir=out)

    assert gate["status"] == "complete_operator_runtime_collection_ready"
    assert gate["ready_for_partial_operator_runtime_collection"] is True
    assert gate["ready_for_complete_operator_runtime_collection"] is True
    assert gate["warnings"] == []


def test_operator_readiness_blocks_when_safety_audit_fails(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    write_local_device_qc(out)
    build_runtime_package(out, blocked=False)
    write_availability_decision(out, ready=True, missing=[])
    safety_path = out / "eval_reports/reaper_runtime_collector_safety_audit.json"
    safety = json.loads(safety_path.read_text(encoding="utf-8"))
    safety["passed"] = False
    safety["safe_for_operator_runtime_collection"] = False
    safety["disallowed_reaper_calls"] = ["TrackFX_SetParam"]
    safety["blockers"] = ["lua_disallowed_reaper_call:TrackFX_SetParam"]
    write_json(safety_path, safety)

    gate = build_reaper_runtime_collection_operator_readiness_gate(project_name="unit", output_dir=out)

    assert gate["status"] == "operator_runtime_collection_blocked"
    assert gate["ready_for_partial_operator_runtime_collection"] is False
    assert "collector_safety_audit_not_passed" in gate["blockers"]
    assert "collector_safety_audit_disallowed_reaper_calls_present" in gate["blockers"]


def test_operator_readiness_cli_require_complete_fails_for_partial_ready(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    write_local_device_qc(out)
    build_runtime_package(out, blocked=True)
    write_availability_decision(out, ready=False, missing=["OTT (Xfer Records)"])

    partial = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/run_reaper_runtime_collection_operator_readiness_gate.py"),
            "--project-name",
            "unit",
            "--output-dir",
            str(out),
            "--require-partial-ready",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    complete = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/run_reaper_runtime_collection_operator_readiness_gate.py"),
            "--project-name",
            "unit",
            "--output-dir",
            str(out),
            "--require-complete-ready",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    partial_data = json.loads(partial.stdout)
    complete_data = json.loads(complete.stdout)

    assert partial.returncode == 0
    assert partial_data["ready_for_partial_operator_runtime_collection"] is True
    assert complete.returncode == 2
    assert complete_data["ready_for_complete_operator_runtime_collection"] is False


def test_report_index_groups_operator_readiness_gate(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    write_local_device_qc(out)
    build_runtime_package(out, blocked=True)
    write_availability_decision(out, ready=False, missing=["OTT (Xfer Records)"])
    build_reaper_runtime_collection_operator_readiness_gate(project_name="unit", output_dir=out)
    index = build_report_index(project_name="unit", output_dir=out, stage_results=[])
    assert any(
        item["stage"] == "plugin intelligence" and item["summary"] == "reaper_runtime_collection_operator_readiness.json"
        for item in index["reports"]
    )


def test_requirements_traceability_includes_operator_readiness_gate(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    audit = build_requirements_traceability_audit(project_name="unit", output_dir=out, workspace_root=ROOT)
    req09 = next(item for item in audit["requirement_results"] if item["id"] == "REQ-09")
    rels = {item["relative_path"] for item in req09["files"]}
    assert "automix/plugins/reaper_runtime_collection_operator_readiness_gate.py" in rels
    assert "scripts/run_reaper_runtime_collection_operator_readiness_gate.py" in rels
    assert "tests/test_reaper_runtime_collection_operator_readiness_gate.py" in rels
    assert req09["status"] == "satisfied"


def test_risk_remediation_plan_recommends_operator_readiness_gate(tmp_path: Path) -> None:
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
                    "code": "semantic_validation_runtime:runtime_validation_report_missing:semantic_validation_01_reaeq_cockos",
                    "summary": "runtime validation report missing",
                    "recommended_next_action": "semantic_validation_runtime",
                }
            ],
            "blockers": ["semantic_validation_runtime:runtime_validation_report_missing:semantic_validation_01_reaeq_cockos"],
            "warnings": [],
        },
    )
    plan = build_risk_remediation_plan(project_name="unit", output_dir=out)
    plugin_action = next(action for action in plan["actions"] if action["phase"] == "plugin_safety")
    assert any("run_reaper_runtime_collection_operator_readiness_gate.py" in command for command in plugin_action["recommended_commands"])
    assert "automix/eval_reports/reaper_runtime_collection_operator_readiness.json" in plugin_action["evidence_to_collect"]


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
    print("REAPER runtime collection operator readiness direct tests passed")

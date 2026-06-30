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
from automix.plugins.plugin_adapter_schema import write_json
from automix.plugins.plugin_semantic_validation_runtime_collector_package import (
    build_plugin_semantic_validation_runtime_collector_package,
)
from automix.plugins.plugin_semantic_validation_runtime_observation_gate import (
    PLUGIN_SEMANTIC_VALIDATION_RUNTIME_OBSERVATION_GATE_SCHEMA,
    build_plugin_semantic_validation_runtime_observation_gate,
)


def queue_job(plugin_name: str = "ReaEQ (Cockos)", job_id: str = "semantic_validation_01_reaeq_cockos") -> dict:
    return {
        "job_id": job_id,
        "plugin_name": plugin_name,
        "priority": 20,
        "category": "stock",
        "target_report_path": f"automix/analysis_reports/plugin_parameter_validation_{job_id}_reaper_observed.json",
        "required_observations": ["parameter names listed by TrackFX_GetParamName"],
        "acceptance_criteria": ["manual report authoring only"],
        "disallowed_actions": ["do not write parameters"],
    }


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


def prepare_collector(out: Path, jobs: list[dict] | None = None, blocked_jobs: list[dict] | None = None) -> dict:
    write_queue(out, jobs=jobs, blocked_jobs=blocked_jobs)
    return build_plugin_semantic_validation_runtime_collector_package(project_name="unit", output_dir=out)


def write_observation(job: dict, *, fake_write_safe: bool = False, status: str = "raw_observation_collected") -> None:
    path = Path(job["raw_observation_output_path"])
    write_json(
        path,
        {
            "schema": "automix-plugin-semantic-validation-runtime-observation-v1",
            "script_version": "unit",
            "project_name": "unit",
            "job_id": job["job_id"],
            "plugin_name": job["plugin_name"],
            "actual_fx_name": f"VST: {job['plugin_name']}",
            "status": status,
            "safe_to_write_parameters": fake_write_safe,
            "creates_validation_reports": False,
            "writes_parameters": False,
            "renders_audio": False,
            "saves_project": False,
            "temporary_muted_probe_track_used": True,
            "temporary_muted_probe_track_deleted": True,
            "parameter_indexes_assumed": False,
            "add_result": {"inserted": True, "returned_index": 0},
            "param_count": 2,
            "parameters": [
                {"index": 0, "name": "Frequency", "write_allowed": False, "semantic_validated": False},
                {"index": 1, "name": "Gain", "write_allowed": False, "semantic_validated": False},
            ],
            "errors": [],
            "warnings": [],
        },
    )


def test_runtime_observation_gate_accepts_raw_observations_without_write_safety(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    package = prepare_collector(out, jobs=[queue_job("ReaEQ (Cockos)", "semantic_validation_01_reaeq_cockos")])
    write_observation(package["collector_jobs"][0])
    gate = build_plugin_semantic_validation_runtime_observation_gate(project_name="unit", output_dir=out)
    assert gate["schema"] == PLUGIN_SEMANTIC_VALIDATION_RUNTIME_OBSERVATION_GATE_SCHEMA
    assert gate["status"] == "runtime_observations_ready_for_manual_report_authoring"
    assert gate["runtime_observations_ready"] is True
    assert gate["ready_for_manual_report_authoring"] is True
    assert gate["ready_for_runtime_evidence_gate"] is False
    assert gate["safe_to_write_parameters"] is False
    assert gate["creates_validation_reports"] is False
    assert gate["accepted_observations_total"] == 1
    assert (out / "review/plugin_semantic_validation_runtime_report_authoring_request.md").exists()


def test_runtime_observation_gate_blocks_missing_observation_files(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    prepare_collector(out, jobs=[queue_job()])
    gate = build_plugin_semantic_validation_runtime_observation_gate(project_name="unit", output_dir=out)
    assert gate["status"] == "runtime_observations_missing"
    assert gate["runtime_observations_ready"] is False
    assert "runtime_observation_missing:semantic_validation_01_reaeq_cockos" in gate["blockers"]
    assert (out / "review/plugin_semantic_validation_runtime_observation_request.md").exists()


def test_runtime_observation_gate_rejects_fake_write_safety_claim(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    package = prepare_collector(out, jobs=[queue_job()])
    write_observation(package["collector_jobs"][0], fake_write_safe=True)
    gate = build_plugin_semantic_validation_runtime_observation_gate(project_name="unit", output_dir=out)
    assert gate["runtime_observations_ready"] is False
    assert "runtime_observation_claims_write_safety:semantic_validation_01_reaeq_cockos" in gate["blockers"]


def test_runtime_observation_gate_cli_require_ready_returns_nonzero_when_missing(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    prepare_collector(out, jobs=[queue_job()])
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/run_plugin_semantic_validation_runtime_observation_gate.py"),
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
    assert data["runtime_observations_ready"] is False
    assert data["blocked_observations_total"] == 1


def test_report_index_groups_plugin_semantic_validation_runtime_observation_gate(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    package = prepare_collector(out, jobs=[queue_job()])
    write_observation(package["collector_jobs"][0])
    build_plugin_semantic_validation_runtime_observation_gate(project_name="unit", output_dir=out)
    index = build_report_index(project_name="unit", output_dir=out, stage_results=[])
    assert any(
        item["stage"] == "plugin intelligence" and item["summary"] == "plugin_semantic_validation_runtime_observation_gate.json"
        for item in index["reports"]
    )


def test_risk_remediation_plan_recommends_runtime_observation_gate(tmp_path: Path) -> None:
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
                    "risk_id": "risk_plugin_runtime_observation",
                    "severity": "blocker",
                    "category": "plugin",
                    "source_report": "plugin_semantic_validation_runtime_observation_gate.json",
                    "code": "runtime_observation_missing:semantic_validation_01_reaeq_cockos",
                    "summary": "runtime observation missing",
                    "recommended_next_action": "semantic_validation_runtime",
                }
            ],
            "blockers": ["runtime_observation_missing:semantic_validation_01_reaeq_cockos"],
            "warnings": [],
        },
    )
    plan = build_risk_remediation_plan(project_name="unit", output_dir=out)
    plugin_action = next(action for action in plan["actions"] if action["phase"] == "plugin_safety")
    assert any("run_plugin_semantic_validation_runtime_observation_gate.py" in command for command in plugin_action["recommended_commands"])
    assert "automix/eval_reports/plugin_semantic_validation_runtime_observation_gate.json" in plugin_action["evidence_to_collect"]


def test_requirements_traceability_includes_runtime_observation_gate(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    audit = build_requirements_traceability_audit(project_name="unit", output_dir=out, workspace_root=ROOT)
    req09 = next(item for item in audit["requirement_results"] if item["id"] == "REQ-09")
    rels = {item["relative_path"] for item in req09["files"]}
    assert "automix/plugins/plugin_semantic_validation_runtime_observation_gate.py" in rels
    assert "scripts/run_plugin_semantic_validation_runtime_observation_gate.py" in rels
    assert "tests/test_prompt79_plugin_semantic_validation_runtime_observation_gate.py" in rels
    assert req09["status"] == "satisfied"


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
    print("Prompt79 direct tests passed")

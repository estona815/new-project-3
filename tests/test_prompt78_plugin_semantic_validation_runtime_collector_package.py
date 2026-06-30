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
from automix.plugins.plugin_semantic_validation_runtime_collection_package import (
    build_plugin_semantic_validation_runtime_collection_package,
)
from automix.plugins.plugin_semantic_validation_runtime_collector_package import (
    PLUGIN_SEMANTIC_VALIDATION_RUNTIME_COLLECTOR_PACKAGE_SCHEMA,
    REAPER_RUNTIME_QUEUE_SCHEMA,
    build_plugin_semantic_validation_runtime_collector_package,
)


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


def test_runtime_collector_package_writes_lua_queue_and_runbook(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    write_queue(
        out,
        [
            queue_job("ReaEQ (Cockos)", "semantic_validation_01_reaeq_cockos"),
            queue_job("ReaComp (Cockos)", "semantic_validation_02_reacomp_cockos"),
        ],
        blocked_jobs=[{"plugin_name": "OTT (Xfer Records)", "blockers": ["availability_decision_missing:OTT (Xfer Records)"]}],
    )
    build_plugin_semantic_validation_runtime_collection_package(project_name="unit", output_dir=out)
    package = build_plugin_semantic_validation_runtime_collector_package(project_name="unit", output_dir=out)
    assert package["schema"] == PLUGIN_SEMANTIC_VALIDATION_RUNTIME_COLLECTOR_PACKAGE_SCHEMA
    assert package["status"] == "runtime_collector_package_ready"
    assert package["ready_for_reaper_runtime_collection"] is True
    assert package["ready_for_runtime_evidence_gate"] is False
    assert package["safe_to_write_parameters"] is False
    assert package["creates_validation_reports"] is False
    assert package["requires_collector_safety_audit"] is True
    assert package["collector_jobs_total"] == 2
    assert "blocked_queue_jobs_remain:1" in package["warnings"]

    lua_path = out / "reaper_scripts/collect_plugin_semantic_validation_runtime.lua"
    queue_payload_path = out / "reaper_scripts/plugin_semantic_validation_runtime_queue.json"
    runbook_path = out / "review/plugin_semantic_validation_runtime_collector_operator_runbook.md"
    assert lua_path.exists()
    assert queue_payload_path.exists()
    assert runbook_path.exists()
    assert package["safety_audit_path"].endswith("eval_reports/reaper_runtime_collector_safety_audit.json")
    assert "reaper_runtime_collector_safety_audit.json" in runbook_path.read_text(encoding="utf-8")
    lua = lua_path.read_text(encoding="utf-8")
    assert "This collector writes raw observations only" in lua
    assert "TrackFX_AddByName" in lua
    assert "TrackFX_GetNumParams" in lua
    assert "TrackFX_GetParamName" in lua
    assert "B_MAINSEND" in lua
    assert "TrackFX_SetParam(" not in lua
    assert "TrackFX_SetParamNormalized" not in lua

    payload = json.loads(queue_payload_path.read_text(encoding="utf-8"))
    assert payload["schema"] == REAPER_RUNTIME_QUEUE_SCHEMA
    assert payload["jobs_total"] == 2
    assert payload["safety"]["temporary_muted_probe_track_only"] is True
    assert payload["safety"]["safe_to_write_parameters"] is False


def test_runtime_collector_package_falls_back_to_queue_without_collection_package(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    write_queue(out, [queue_job()])
    package = build_plugin_semantic_validation_runtime_collector_package(project_name="unit", output_dir=out)
    assert package["status"] == "runtime_collector_package_ready"
    assert package["source_kind"] == "semantic_validation_queue_fallback"
    assert "runtime_collection_package_missing_using_queue_fallback" in package["warnings"]
    assert package["collector_jobs"][0]["raw_observation_output_path"].endswith("_observation.json")


def test_runtime_collector_package_cli_require_ready_returns_nonzero_without_sources(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/run_plugin_semantic_validation_runtime_collector_package.py"),
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
    assert data["ready_for_reaper_runtime_collection"] is False
    assert data["requires_collector_safety_audit"] is True
    assert data["collector_safety_audit_passed"] is True
    assert data["safe_for_operator_runtime_collection"] is False
    assert data["operator_readiness_status"] == "operator_runtime_collection_blocked"
    assert data["ready_for_partial_operator_runtime_collection"] is False
    assert data["ready_for_complete_operator_runtime_collection"] is False
    assert Path(data["safety_audit_json"]).exists()
    assert Path(data["operator_readiness_json"]).exists()
    assert "runtime_collection_package_or_queue_missing_or_invalid" in data["blockers"]


def test_report_index_groups_plugin_semantic_validation_runtime_collector_package(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    write_queue(out)
    build_plugin_semantic_validation_runtime_collection_package(project_name="unit", output_dir=out)
    build_plugin_semantic_validation_runtime_collector_package(project_name="unit", output_dir=out)
    index = build_report_index(project_name="unit", output_dir=out, stage_results=[])
    assert any(
        item["stage"] == "plugin intelligence" and item["summary"] == "plugin_semantic_validation_runtime_collector_package.json"
        for item in index["reports"]
    )


def test_risk_remediation_plan_recommends_runtime_collector_package(tmp_path: Path) -> None:
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
    assert any("run_plugin_semantic_validation_runtime_collector_package.py" in command for command in plugin_action["recommended_commands"])
    assert any("run_reaper_runtime_collector_safety_audit.py" in command for command in plugin_action["recommended_commands"])
    assert "automix/eval_reports/plugin_semantic_validation_runtime_collector_package.json" in plugin_action["evidence_to_collect"]
    assert "automix/eval_reports/reaper_runtime_collector_safety_audit.json" in plugin_action["evidence_to_collect"]
    assert "automix/reaper_scripts/collect_plugin_semantic_validation_runtime.lua" in plugin_action["evidence_to_collect"]


def test_requirements_traceability_includes_runtime_collector_package(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    audit = build_requirements_traceability_audit(project_name="unit", output_dir=out, workspace_root=ROOT)
    req09 = next(item for item in audit["requirement_results"] if item["id"] == "REQ-09")
    rels = {item["relative_path"] for item in req09["files"]}
    assert "automix/plugins/plugin_semantic_validation_runtime_collector_package.py" in rels
    assert "scripts/run_plugin_semantic_validation_runtime_collector_package.py" in rels
    assert "tests/test_prompt78_plugin_semantic_validation_runtime_collector_package.py" in rels
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
    print("Prompt78 direct tests passed")

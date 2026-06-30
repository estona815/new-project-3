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
from automix.plugins.plugin_semantic_validation_runtime_collection_package import (
    PLUGIN_PARAMETER_VALIDATION_REPORT_TEMPLATE_SCHEMA,
    build_plugin_semantic_validation_runtime_collection_package,
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
        "required_observations": ["REAPER runtime observed the exact plugin"],
        "acceptance_criteria": ["status=passed", "safe_for_automix=true", "no_fake_success=true"],
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


def test_runtime_collection_package_writes_candidate_manifest_and_review_templates(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    write_queue(
        out,
        [
            queue_job("ReaEQ (Cockos)", "semantic_validation_01_reaeq_cockos"),
            queue_job("ReaComp (Cockos)", "semantic_validation_02_reacomp_cockos"),
        ],
        blocked_jobs=[{"plugin_name": "OTT (Xfer Records)", "blockers": ["availability_decision_missing:OTT (Xfer Records)"]}],
    )
    package = build_plugin_semantic_validation_runtime_collection_package(project_name="unit", output_dir=out)
    assert package["status"] == "runtime_collection_package_ready"
    assert package["ready_for_runtime_collection"] is True
    assert package["ready_for_runtime_evidence_gate"] is False
    assert package["safe_to_write_parameters"] is False
    assert package["collection_jobs_total"] == 2
    assert package["report_templates_total"] == 2
    assert package["target_reports_missing_total"] == 2
    assert "blocked_queue_jobs_remain:1" in package["warnings"]
    manifest_candidate = json.loads((out / "review/plugin_semantic_validation_runtime_manifest_candidate.json").read_text(encoding="utf-8"))
    assert manifest_candidate["schema"] == "automix-plugin-semantic-validation-runtime-manifest-v1"
    assert manifest_candidate["candidate_only"] is True
    templates = sorted((out / "review/plugin_semantic_validation_runtime_report_templates").glob("*.json"))
    assert len(templates) == 2
    template = json.loads(templates[0].read_text(encoding="utf-8"))
    assert template["schema"] == PLUGIN_PARAMETER_VALIDATION_REPORT_TEMPLATE_SCHEMA
    assert template["safe_for_automix"] is False
    assert not list((out / "analysis_reports").glob("plugin_parameter_validation_*_reaper_observed.json"))


def test_runtime_collection_package_counts_existing_target_reports(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    job = queue_job()
    write_queue(out, [job])
    target = out / "analysis_reports/plugin_parameter_validation_semantic_validation_01_reaeq_cockos_reaper_observed.json"
    write_json(target, {"schema": "automix-plugin-parameter-validation-report-v1", "status": "passed"})
    package = build_plugin_semantic_validation_runtime_collection_package(project_name="unit", output_dir=out)
    assert package["status"] == "runtime_reports_present_manifest_review_required"
    assert package["target_reports_existing_total"] == 1
    assert package["target_reports_missing_total"] == 0
    assert package["ready_for_runtime_evidence_gate"] is True


def test_runtime_collection_package_cli_require_ready_returns_nonzero_without_queue(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/run_plugin_semantic_validation_runtime_collection_package.py"),
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
    assert data["ready_for_runtime_collection"] is False
    assert "plugin_semantic_validation_queue_missing_or_invalid" in data["blockers"]


def test_report_index_groups_plugin_semantic_validation_runtime_collection_package(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    write_queue(out)
    build_plugin_semantic_validation_runtime_collection_package(project_name="unit", output_dir=out)
    index = build_report_index(project_name="unit", output_dir=out, stage_results=[])
    assert any(
        item["stage"] == "plugin intelligence" and item["summary"] == "plugin_semantic_validation_runtime_collection_package.json"
        for item in index["reports"]
    )


def test_risk_remediation_plan_recommends_runtime_collection_package(tmp_path: Path) -> None:
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
    assert any("run_plugin_semantic_validation_runtime_collection_package.py" in command for command in plugin_action["recommended_commands"])
    assert "automix/eval_reports/plugin_semantic_validation_runtime_collection_package.json" in plugin_action["evidence_to_collect"]


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
    print("Prompt76 direct tests passed")

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
from automix.plugins.plugin_semantic_validation_queue import build_plugin_semantic_validation_queue


def job(plugin_name: str, *, collectable: bool = True, blocked: bool = False, priority: int = 20) -> dict:
    return {
        "plugin_name": plugin_name,
        "source_action_id": "collect_reaper_observed_semantic_validation" if collectable else "install_or_disable_unavailable_plugin",
        "collection_action": "collect_missing_reaper_observed_semantic_report" if collectable else "operator_availability_decision_required",
        "priority": priority,
        "category": "stock" if "Cockos" in plugin_name else "third_party_or_unknown",
        "available": collectable,
        "collectable_in_reaper": collectable,
        "resolved_without_collection": False,
        "target_report_path": f"automix/analysis_reports/plugin_parameter_validation_{plugin_name.lower().replace(' ', '_')}_reaper_observed.json",
        "expected_report_glob": "automix/analysis_reports/plugin_parameter_validation_*.json",
        "required_observations": ["REAPER runtime observed the exact plugin"],
        "acceptance_criteria": ["status=passed", "safe_for_automix=true"],
        "source_blockers": [f"validation_report_missing:{plugin_name}"],
        "blockers": [f"availability_decision_missing:{plugin_name}"] if blocked else [],
        "warnings": [],
    }


def write_collection_plan(out: Path, jobs: list[dict]) -> None:
    write_json(
        out / "eval_reports/plugin_semantic_validation_collection_plan.json",
        {
            "schema": "automix-plugin-semantic-validation-collection-plan-v1",
            "project_name": "unit",
            "status": "availability_decisions_required_before_full_collection",
            "validation_jobs": jobs,
            "open_jobs_total": len(jobs),
            "collectable_jobs_total": sum(1 for item in jobs if item.get("collectable_in_reaper")),
            "decision_blocked_jobs_total": sum(1 for item in jobs if item.get("blockers")),
            "safe_to_write_parameters": False,
            "blockers": [blocker for item in jobs for blocker in item.get("blockers", [])],
            "warnings": [],
        },
    )


def test_semantic_validation_queue_packages_collectable_jobs_and_blocks_unavailable_decisions(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    write_collection_plan(
        out,
        [
            job("OTT (Xfer Records)", collectable=False, blocked=True, priority=10),
            job("ReaEQ (Cockos)", collectable=True, priority=20),
            job("ReaComp (Cockos)", collectable=True, priority=30),
        ],
    )
    queue = build_plugin_semantic_validation_queue(project_name="unit", output_dir=out)
    assert queue["status"] == "queue_ready_with_blocked_unavailable_decisions"
    assert queue["queue_jobs_total"] == 2
    assert queue["blocked_jobs_total"] == 1
    assert queue["ready_to_run_reaper_collection"] is True
    assert queue["safe_to_write_parameters"] is False
    assert queue["next_queue_job"]["plugin_name"] == "ReaEQ (Cockos)"
    assert queue["queue_jobs"][0]["requires_temporary_muted_test_context"] is True
    assert "do not write parameters to the user's mix from this queue" in queue["queue_jobs"][0]["disallowed_actions"]
    assert (out / "review/plugin_semantic_validation_runtime_manifest_template.json").exists()
    assert (out / "review/plugin_semantic_validation_queue_request.md").exists()


def test_semantic_validation_queue_reports_no_jobs_when_collection_is_resolved(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    resolved = job("ReaEQ (Cockos)", collectable=False, blocked=False)
    resolved["collection_action"] = "already_write_safe"
    resolved["resolved_without_collection"] = True
    write_collection_plan(out, [resolved])
    queue = build_plugin_semantic_validation_queue(project_name="unit", output_dir=out)
    assert queue["status"] == "no_collectable_semantic_validation_jobs"
    assert queue["queue_jobs_total"] == 0
    assert queue["blocked_jobs_total"] == 0
    assert queue["ready_to_run_reaper_collection"] is False


def test_semantic_validation_queue_cli_require_ready_returns_nonzero_without_jobs(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    write_collection_plan(out, [])
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/run_plugin_semantic_validation_queue.py"),
            "--project-name",
            "unit",
            "--output-dir",
            str(out),
            "--require-queue-ready",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    data = json.loads(result.stdout)
    assert result.returncode == 2
    assert data["ready_to_run_reaper_collection"] is False
    assert Path(data["runtime_manifest_template"]).exists()


def test_report_index_groups_plugin_semantic_validation_queue(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    write_collection_plan(out, [job("ReaEQ (Cockos)")])
    build_plugin_semantic_validation_queue(project_name="unit", output_dir=out)
    index = build_report_index(project_name="unit", output_dir=out, stage_results=[])
    assert any(
        item["stage"] == "plugin intelligence" and item["summary"] == "plugin_semantic_validation_queue.json"
        for item in index["reports"]
    )


def test_risk_remediation_plan_recommends_semantic_validation_queue(tmp_path: Path) -> None:
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
                    "risk_id": "risk_plugin",
                    "severity": "blocker",
                    "category": "plugin",
                    "source_report": "plugin_semantic_validation_gate.json",
                    "code": "plugin_semantic_validation:validation_report_missing:ReaEQ (Cockos)",
                    "summary": "plugin validation missing",
                    "recommended_next_action": "semantic_validation",
                }
            ],
            "blockers": ["plugin_semantic_validation:validation_report_missing:ReaEQ (Cockos)"],
            "warnings": [],
        },
    )
    plan = build_risk_remediation_plan(project_name="unit", output_dir=out)
    plugin_action = next(action for action in plan["actions"] if action["phase"] == "plugin_safety")
    assert any("run_plugin_semantic_validation_queue.py" in command for command in plugin_action["recommended_commands"])
    assert "automix/eval_reports/plugin_semantic_validation_queue.json" in plugin_action["evidence_to_collect"]


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
    print("Prompt74 direct tests passed")

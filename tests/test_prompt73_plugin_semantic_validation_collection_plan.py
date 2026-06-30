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
from automix.plugins.plugin_semantic_validation_collection_plan import build_plugin_semantic_validation_collection_plan


def action(plugin_name: str, action_id: str, *, available: bool = True, priority: int = 20) -> dict:
    return {
        "plugin_name": plugin_name,
        "action_id": action_id,
        "priority": priority,
        "severity": "blocker" if action_id != "plugin_write_safe_ready" else "info",
        "category": "stock" if "Cockos" in plugin_name else "third_party_or_unknown",
        "available": available,
        "expected_report_glob": f"automix/analysis_reports/plugin_parameter_validation_{plugin_name.lower().replace(' ', '_')}*.json",
        "matching_reports_total": 1 if action_id in {"rerun_or_keep_plugin_read_only", "plugin_write_safe_ready"} else 0,
        "passed_reports_total": 1 if action_id == "plugin_write_safe_ready" else 0,
        "safe_control_count": 2 if action_id == "plugin_write_safe_ready" else 0,
        "semantic_validation_passed": action_id == "plugin_write_safe_ready",
        "source_blockers": [f"validation_report_missing:{plugin_name}"] if action_id == "collect_reaper_observed_semantic_validation" else [],
        "source_warnings": [],
    }


def write_inputs(out: Path, actions: list[dict], *, semantic_ready: bool = False, decision_gate: dict | None = None) -> None:
    write_json(
        out / "eval_reports/plugin_validation_action_plan.json",
        {
            "schema": "automix-plugin-validation-action-plan-v1",
            "project_name": "unit",
            "required_plugins_total": len(actions),
            "plugin_actions_total": len(actions),
            "plugin_actions": actions,
            "summary": {"safe_to_write_parameters": semantic_ready},
            "status": "write_safe_ready" if semantic_ready else "plugin_validation_actions_open",
            "blockers": [f"{item['plugin_name']}:{item['action_id']}" for item in actions if item["action_id"] != "plugin_write_safe_ready"],
            "warnings": [],
        },
    )
    write_json(
        out / "eval_reports/plugin_semantic_validation_gate.json",
        {
            "schema": "automix-plugin-semantic-validation-gate-v1",
            "project_name": "unit",
            "required_plugins": [item["plugin_name"] for item in actions],
            "required_plugins_total": len(actions),
            "semantic_validation_ready": semantic_ready,
            "blockers": [] if semantic_ready else ["semantic_validation_passed_reports_missing"],
            "warnings": [],
        },
    )
    if decision_gate is not None:
        write_json(out / "eval_reports/plugin_availability_decision_gate.json", decision_gate)


def decision_gate_for(plugin_name: str, resolution: str = "disable_for_automatic_drafts") -> dict:
    return {
        "schema": "automix-plugin-availability-decision-gate-v1",
        "project_name": "unit",
        "availability_decisions_ready": True,
        "decisions": [
            {
                "plugin_name": plugin_name,
                "operator_resolution": resolution,
                "operator_acknowledged": True,
                "automatic_parameter_writes_allowed": False,
                "fallback_requires_validation": True,
                "blockers": [],
            }
        ],
        "blockers": [],
        "warnings": [],
    }


def test_collection_plan_classifies_collectable_rerun_ready_and_decision_blocked_jobs(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    write_inputs(
        out,
        [
            action("OTT (Xfer Records)", "install_or_disable_unavailable_plugin", available=False, priority=10),
            action("ReaEQ (Cockos)", "collect_reaper_observed_semantic_validation", priority=20),
            action("ReaComp (Cockos)", "rerun_or_keep_plugin_read_only", priority=30),
            action("ReaDelay (Cockos)", "plugin_write_safe_ready", priority=90),
        ],
    )
    plan = build_plugin_semantic_validation_collection_plan(project_name="unit", output_dir=out)
    by_name = {item["plugin_name"]: item for item in plan["validation_jobs"]}
    assert plan["status"] == "availability_decisions_required_before_full_collection"
    assert plan["open_jobs_total"] == 3
    assert plan["collectable_jobs_total"] == 2
    assert plan["decision_blocked_jobs_total"] == 1
    assert plan["next_collection_job"]["plugin_name"] == "ReaEQ (Cockos)"
    assert by_name["OTT (Xfer Records)"]["collection_action"] == "operator_availability_decision_required"
    assert by_name["ReaEQ (Cockos)"]["collection_action"] == "collect_missing_reaper_observed_semantic_report"
    assert by_name["ReaComp (Cockos)"]["collection_action"] == "rerun_failed_semantic_report_or_keep_read_only"
    assert by_name["ReaDelay (Cockos)"]["collection_action"] == "already_write_safe"
    assert plan["safe_to_write_parameters"] is False
    assert (out / "review/plugin_semantic_validation_collection_request.md").exists()
    assert (out / "review/plugin_semantic_validation_collection_manifest_template.json").exists()


def test_collection_plan_skips_operator_disabled_unavailable_plugin_without_granting_writes(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    write_inputs(
        out,
        [action("OTT (Xfer Records)", "install_or_disable_unavailable_plugin", available=False, priority=10)],
        decision_gate=decision_gate_for("OTT (Xfer Records)"),
    )
    plan = build_plugin_semantic_validation_collection_plan(project_name="unit", output_dir=out)
    job = plan["validation_jobs"][0]
    assert job["collection_action"] == "skip_disabled_or_manual_review_unavailable_plugin"
    assert job["resolved_without_collection"] is True
    assert plan["open_jobs_total"] == 0
    assert plan["safe_to_write_parameters"] is False


def test_collection_plan_reports_all_jobs_resolved_when_plugins_are_write_safe(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    write_inputs(out, [action("ReaEQ (Cockos)", "plugin_write_safe_ready", priority=90)], semantic_ready=True)
    plan = build_plugin_semantic_validation_collection_plan(project_name="unit", output_dir=out)
    assert plan["status"] == "semantic_validation_collection_not_required"
    assert plan["all_jobs_resolved"] is True
    assert plan["open_jobs_total"] == 0
    assert plan["ready_plugins_total"] == 1
    assert plan["safe_to_write_parameters"] is False


def test_collection_plan_cli_require_no_open_jobs_returns_nonzero(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    write_inputs(out, [action("ReaEQ (Cockos)", "collect_reaper_observed_semantic_validation")])
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/run_plugin_semantic_validation_collection_plan.py"),
            "--project-name",
            "unit",
            "--output-dir",
            str(out),
            "--require-no-open-jobs",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    data = json.loads(result.stdout)
    assert result.returncode == 2
    assert data["open_jobs_total"] == 1
    assert data["next_plugin"] == "ReaEQ (Cockos)"
    assert Path(data["manifest_template"]).exists()


def test_report_index_groups_plugin_semantic_validation_collection_plan(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    write_inputs(out, [action("ReaEQ (Cockos)", "collect_reaper_observed_semantic_validation")])
    build_plugin_semantic_validation_collection_plan(project_name="unit", output_dir=out)
    index = build_report_index(project_name="unit", output_dir=out, stage_results=[])
    assert any(
        item["stage"] == "plugin intelligence" and item["summary"] == "plugin_semantic_validation_collection_plan.json"
        for item in index["reports"]
    )


def test_risk_remediation_plan_recommends_semantic_validation_collection_plan(tmp_path: Path) -> None:
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
    assert any("run_plugin_semantic_validation_collection_plan.py" in command for command in plugin_action["recommended_commands"])
    assert "automix/eval_reports/plugin_semantic_validation_collection_plan.json" in plugin_action["evidence_to_collect"]


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
    print("Prompt73 direct tests passed")

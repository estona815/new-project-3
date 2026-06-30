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
from automix.plugins.plugin_validation_action_plan import build_plugin_validation_action_plan


def write_plugin_evidence(out: Path, *, ready: bool = False) -> None:
    if ready:
        write_json(
            out / "eval_reports/plugin_validation_preflight.json",
            {
                "schema": "automix-plugin-validation-preflight-v1",
                "project_name": "unit",
                "required_plugins": ["ReaEQ (Cockos)"],
                "availability": [
                    {
                        "name": "ReaEQ (Cockos)",
                        "category": "stock",
                        "available": True,
                        "candidate_paths": ["/tmp/REAPER.app/Contents/Plugins/FX/reaeq.vst.dylib"],
                    }
                ],
                "summary": {"safe_to_write_parameters": True},
                "blockers": [],
                "warnings": [],
            },
        )
        write_json(
            out / "eval_reports/plugin_semantic_validation_gate.json",
            {
                "schema": "automix-plugin-semantic-validation-gate-v1",
                "project_name": "unit",
                "required_plugins": ["ReaEQ (Cockos)"],
                "semantic_validation_ready": True,
                "plugin_results": [
                    {
                        "plugin_name": "ReaEQ (Cockos)",
                        "matching_reports_total": 1,
                        "passed_reports_total": 1,
                        "safe_control_count": 2,
                        "semantic_validation_passed": True,
                        "blockers": [],
                        "warnings": [],
                    }
                ],
                "blockers": [],
                "warnings": [],
            },
        )
        return

    write_json(
        out / "eval_reports/plugin_validation_preflight.json",
        {
            "schema": "automix-plugin-validation-preflight-v1",
            "project_name": "unit",
            "required_plugins": ["OTT (Xfer Records)", "ReaComp (Cockos)", "ReaDelay (Cockos)", "ReaEQ (Cockos)"],
            "availability": [
                {"name": "OTT (Xfer Records)", "category": "third_party_or_unknown", "available": False, "candidate_paths": []},
                {"name": "ReaComp (Cockos)", "category": "stock", "available": True, "candidate_paths": ["/tmp/reacomp.vst.dylib"]},
                {"name": "ReaDelay (Cockos)", "category": "stock", "available": True, "candidate_paths": ["/tmp/readelay.vst.dylib"]},
                {"name": "ReaEQ (Cockos)", "category": "stock", "available": True, "candidate_paths": ["/tmp/reaeq.vst.dylib"]},
            ],
            "summary": {"safe_to_write_parameters": False},
            "blockers": ["required_plugin_availability_missing:OTT (Xfer Records)", "semantic_parameter_validation_required"],
            "warnings": ["availability_does_not_grant_write_safety"],
        },
    )
    write_json(
        out / "eval_reports/plugin_semantic_validation_gate.json",
        {
            "schema": "automix-plugin-semantic-validation-gate-v1",
            "project_name": "unit",
            "required_plugins": ["OTT (Xfer Records)", "ReaComp (Cockos)", "ReaDelay (Cockos)", "ReaEQ (Cockos)"],
            "semantic_validation_ready": False,
            "plugin_results": [
                {
                    "plugin_name": "ReaComp (Cockos)",
                    "matching_reports_total": 1,
                    "passed_reports_total": 0,
                    "safe_control_count": 0,
                    "semantic_validation_passed": False,
                    "blockers": ["no_passed_semantic_validation_report:ReaComp (Cockos)"],
                    "warnings": [],
                },
                {
                    "plugin_name": "ReaDelay (Cockos)",
                    "matching_reports_total": 1,
                    "passed_reports_total": 1,
                    "safe_control_count": 1,
                    "semantic_validation_passed": True,
                    "blockers": [],
                    "warnings": [],
                },
            ],
            "blockers": ["validation_report_missing:OTT (Xfer Records)", "validation_report_missing:ReaEQ (Cockos)"],
            "warnings": [],
        },
    )


def test_plugin_validation_action_plan_classifies_plugin_next_actions(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    write_plugin_evidence(out)
    plan = build_plugin_validation_action_plan(project_name="unit", output_dir=out)
    by_name = {item["plugin_name"]: item for item in plan["plugin_actions"]}
    assert plan["status"] == "plugin_validation_actions_open"
    assert plan["summary"]["safe_to_write_parameters"] is False
    assert plan["next_plugin_action"]["plugin_name"] == "OTT (Xfer Records)"
    assert by_name["OTT (Xfer Records)"]["action_id"] == "install_or_disable_unavailable_plugin"
    assert by_name["ReaEQ (Cockos)"]["action_id"] == "collect_reaper_observed_semantic_validation"
    assert by_name["ReaComp (Cockos)"]["action_id"] == "rerun_or_keep_plugin_read_only"
    assert by_name["ReaDelay (Cockos)"]["action_id"] == "plugin_write_safe_ready"
    assert (out / "eval_reports/plugin_validation_action_plan.json").exists()
    assert (out / "review/plugin_validation_action_request.md").exists()
    md = (out / "eval_reports/plugin_validation_action_plan.md").read_text(encoding="utf-8")
    assert "does not approve plugin parameter writes" in md


def test_plugin_validation_action_plan_ready_requires_preflight_and_semantic_ready(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    write_plugin_evidence(out, ready=True)
    plan = build_plugin_validation_action_plan(project_name="unit", output_dir=out)
    assert plan["status"] == "write_safe_ready"
    assert plan["summary"]["safe_to_write_parameters"] is True
    assert plan["blockers"] == []
    assert plan["next_plugin_action"]["action_id"] == "plugin_write_safe_ready"


def test_plugin_validation_action_plan_cli_require_safe_write_returns_nonzero(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    write_plugin_evidence(out)
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/run_plugin_validation_action_plan.py"),
            "--project-name",
            "unit",
            "--output-dir",
            str(out),
            "--require-safe-write",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    data = json.loads(result.stdout)
    assert result.returncode == 2
    assert data["status"] == "plugin_validation_actions_open"
    assert data["next_plugin"] == "OTT (Xfer Records)"
    assert Path(data["report_json"]).exists()
    assert Path(data["request_md"]).exists()


def test_report_index_groups_plugin_validation_action_plan(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    write_plugin_evidence(out)
    build_plugin_validation_action_plan(project_name="unit", output_dir=out)
    index = build_report_index(project_name="unit", output_dir=out, stage_results=[])
    assert any(
        item["stage"] == "plugin intelligence" and item["summary"] == "plugin_validation_action_plan.json"
        for item in index["reports"]
    )


def test_risk_remediation_plan_recommends_plugin_validation_action_plan(tmp_path: Path) -> None:
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
    assert any("run_plugin_validation_action_plan.py" in command for command in plugin_action["recommended_commands"])
    assert "automix/eval_reports/plugin_validation_action_plan.json" in plugin_action["evidence_to_collect"]


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
    print("Prompt70 direct tests passed")

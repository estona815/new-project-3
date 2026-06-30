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
    PLUGIN_SEMANTIC_VALIDATION_RUNTIME_COLLECTOR_PACKAGE_SCHEMA,
)
from automix.plugins.plugin_semantic_validation_runtime_observation_gate import (
    PLUGIN_SEMANTIC_VALIDATION_RUNTIME_OBSERVATION_GATE_SCHEMA,
)
from automix.plugins.plugin_semantic_validation_runtime_report_authoring_package import (
    PLUGIN_PARAMETER_VALIDATION_REPORT_AUTHORING_TEMPLATE_SCHEMA,
    PLUGIN_SEMANTIC_VALIDATION_RUNTIME_REPORT_AUTHORING_PACKAGE_SCHEMA,
    build_plugin_semantic_validation_runtime_report_authoring_package,
)


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def observation_path(out: Path) -> Path:
    return out / "reaper_scripts/observations/semantic_validation_01_reaeq_cockos_observation.json"


def write_collector_package(out: Path) -> None:
    write_json(
        out / "eval_reports/plugin_semantic_validation_runtime_collector_package.json",
        {
            "schema": PLUGIN_SEMANTIC_VALIDATION_RUNTIME_COLLECTOR_PACKAGE_SCHEMA,
            "project_name": "unit",
            "collector_jobs": [
                {
                    "job_id": "semantic_validation_01_reaeq_cockos",
                    "plugin_name": "ReaEQ (Cockos)",
                    "target_report_path": str(out / "analysis_reports/plugin_parameter_validation_reaeq.json"),
                    "raw_observation_output_path": str(observation_path(out)),
                }
            ],
            "blocked_queue_jobs": [],
        },
    )


def write_raw_observation(out: Path) -> None:
    write_json(
        observation_path(out),
        {
            "schema": "automix-plugin-semantic-validation-runtime-observation-v1",
            "project_name": "unit",
            "job_id": "semantic_validation_01_reaeq_cockos",
            "plugin_name": "ReaEQ (Cockos)",
            "actual_fx_name": "VST: ReaEQ (Cockos)",
            "status": "raw_observation_collected",
            "safe_to_write_parameters": False,
            "creates_validation_reports": False,
            "writes_parameters": False,
            "renders_audio": False,
            "saves_project": False,
            "param_count": 2,
            "parameters": [
                {"index": 0, "name": "Frequency", "write_allowed": False, "semantic_validated": False},
                {"index": 1, "name": "Gain", "write_allowed": False, "semantic_validated": False},
            ],
            "add_result": {"inserted": True},
            "errors": [],
            "warnings": [],
        },
    )


def write_observation_gate(out: Path, *, accepted: bool = True) -> None:
    result = {
        "job_id": "semantic_validation_01_reaeq_cockos",
        "plugin_name": "ReaEQ (Cockos)",
        "raw_observation_output_path": str(observation_path(out)),
        "actual_fx_name": "VST: ReaEQ (Cockos)" if accepted else "",
        "parameters_observed_total": 2 if accepted else 0,
        "safe_to_write_parameters": False,
        "creates_validation_reports": False,
        "blockers": [] if accepted else ["runtime_observation_missing:semantic_validation_01_reaeq_cockos"],
        "warnings": [],
        "job_status": "accepted_for_manual_report_authoring" if accepted else "blocked",
    }
    write_json(
        out / "eval_reports/plugin_semantic_validation_runtime_observation_gate.json",
        {
            "schema": PLUGIN_SEMANTIC_VALIDATION_RUNTIME_OBSERVATION_GATE_SCHEMA,
            "project_name": "unit",
            "status": "runtime_observations_ready_for_manual_report_authoring" if accepted else "runtime_observations_missing",
            "collector_package_path": str(out / "eval_reports/plugin_semantic_validation_runtime_collector_package.json"),
            "runtime_observations_ready": accepted,
            "ready_for_manual_report_authoring": accepted,
            "ready_for_runtime_evidence_gate": False,
            "safe_to_write_parameters": False,
            "creates_validation_reports": False,
            "collector_jobs_total": 1,
            "accepted_observations_total": 1 if accepted else 0,
            "blocked_observations_total": 0 if accepted else 1,
            "job_results": [result],
            "blockers": [] if accepted else ["runtime_observation_missing:semantic_validation_01_reaeq_cockos"],
            "warnings": [],
        },
    )


def test_runtime_report_authoring_package_creates_review_only_templates_from_accepted_observations(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    write_collector_package(out)
    write_raw_observation(out)
    write_observation_gate(out, accepted=True)
    package = build_plugin_semantic_validation_runtime_report_authoring_package(project_name="unit", output_dir=out)
    assert package["schema"] == PLUGIN_SEMANTIC_VALIDATION_RUNTIME_REPORT_AUTHORING_PACKAGE_SCHEMA
    assert package["status"] == "runtime_report_authoring_package_ready"
    assert package["ready_for_manual_report_authoring"] is True
    assert package["ready_for_runtime_evidence_gate"] is False
    assert package["safe_to_write_parameters"] is False
    assert package["creates_validation_reports"] is False
    assert package["writes_analysis_reports"] is False
    assert package["templates_total"] == 1
    template_path = Path(package["template_results"][0]["template_path"])
    template = read_json(template_path)
    assert template["schema"] == PLUGIN_PARAMETER_VALIDATION_REPORT_AUTHORING_TEMPLATE_SCHEMA
    assert template["status"] == "authoring_template_not_validation_evidence"
    assert template["safe_for_automix"] is False
    assert template["no_fake_success"] is False
    assert template["safe_to_write_parameters"] is False
    assert template["writes_analysis_reports"] is False
    assert "Frequency" in {item["name"] for item in template["observed_parameters"]}
    assert all(control["write_allowed"] is False for control in template["controls"].values())
    assert not (out / "analysis_reports/plugin_parameter_validation_reaeq.json").exists()


def test_runtime_report_authoring_package_blocks_without_accepted_observations(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    write_collector_package(out)
    write_observation_gate(out, accepted=False)
    package = build_plugin_semantic_validation_runtime_report_authoring_package(project_name="unit", output_dir=out)
    assert package["status"] == "no_accepted_runtime_observations"
    assert package["runtime_report_authoring_package_ready"] is False
    assert package["templates_total"] == 0
    assert "accepted_runtime_observations_missing" in package["blockers"]
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/run_plugin_semantic_validation_runtime_report_authoring_package.py"),
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
    assert data["ready_for_manual_report_authoring"] is False


def test_runtime_report_authoring_package_blocks_missing_gate(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    package = build_plugin_semantic_validation_runtime_report_authoring_package(project_name="unit", output_dir=out)
    assert package["status"] == "runtime_report_authoring_package_blocked"
    assert "plugin_semantic_validation_runtime_observation_gate_missing_or_invalid" in package["blockers"]


def test_report_index_groups_runtime_report_authoring_package(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    write_collector_package(out)
    write_raw_observation(out)
    write_observation_gate(out, accepted=True)
    build_plugin_semantic_validation_runtime_report_authoring_package(project_name="unit", output_dir=out)
    index = build_report_index(project_name="unit", output_dir=out, stage_results=[])
    assert any(
        item["stage"] == "plugin intelligence"
        and item["summary"] == "plugin_semantic_validation_runtime_report_authoring_package.json"
        for item in index["reports"]
    )


def test_risk_remediation_plan_recommends_runtime_report_authoring_package(tmp_path: Path) -> None:
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
                    "risk_id": "risk_plugin_report_authoring",
                    "severity": "blocker",
                    "category": "plugin",
                    "source_report": "plugin_semantic_validation_runtime_report_authoring_package.json",
                    "code": "accepted_runtime_observations_missing",
                    "summary": "accepted runtime observations missing",
                    "recommended_next_action": "semantic_validation_runtime",
                }
            ],
            "blockers": ["accepted_runtime_observations_missing"],
            "warnings": [],
        },
    )
    plan = build_risk_remediation_plan(project_name="unit", output_dir=out)
    plugin_action = next(action for action in plan["actions"] if action["phase"] == "plugin_safety")
    assert any("run_plugin_semantic_validation_runtime_report_authoring_package.py" in command for command in plugin_action["recommended_commands"])
    assert "automix/eval_reports/plugin_semantic_validation_runtime_report_authoring_package.json" in plugin_action["evidence_to_collect"]


def test_requirements_traceability_includes_runtime_report_authoring_package(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    audit = build_requirements_traceability_audit(project_name="unit", output_dir=out, workspace_root=ROOT)
    req09 = next(item for item in audit["requirement_results"] if item["id"] == "REQ-09")
    rels = {item["relative_path"] for item in req09["files"]}
    assert "automix/plugins/plugin_semantic_validation_runtime_report_authoring_package.py" in rels
    assert "scripts/run_plugin_semantic_validation_runtime_report_authoring_package.py" in rels
    assert "tests/test_prompt80_plugin_semantic_validation_runtime_report_authoring_package.py" in rels
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
    print("Prompt80 direct tests passed")

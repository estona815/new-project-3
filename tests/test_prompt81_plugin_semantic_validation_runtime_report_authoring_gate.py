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
from automix.plugins.plugin_semantic_validation_runtime_report_authoring_gate import (
    PLUGIN_SEMANTIC_VALIDATION_RUNTIME_REPORT_AUTHORING_GATE_SCHEMA,
    build_plugin_semantic_validation_runtime_report_authoring_gate,
)
from automix.plugins.plugin_semantic_validation_runtime_report_authoring_package import (
    PLUGIN_PARAMETER_VALIDATION_REPORT_AUTHORING_TEMPLATE_SCHEMA,
    PLUGIN_SEMANTIC_VALIDATION_RUNTIME_REPORT_AUTHORING_PACKAGE_SCHEMA,
)


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def template_path(out: Path) -> Path:
    return out / "review/plugin_semantic_validation_runtime_report_authoring_templates/semantic_validation_01_reaeq_cockos_authoring_template.json"


def candidate_path(out: Path) -> Path:
    return out / "review/plugin_semantic_validation_runtime_report_authoring_candidates/semantic_validation_01_reaeq_cockos_validation_report_candidate.json"


def target_report_path(out: Path) -> Path:
    return out / "analysis_reports/plugin_parameter_validation_reaeq_cockos_reaper_observed.json"


def write_authoring_package(out: Path, *, ready: bool = True) -> None:
    write_json(
        template_path(out),
        {
            "schema": PLUGIN_PARAMETER_VALIDATION_REPORT_AUTHORING_TEMPLATE_SCHEMA,
            "target_report_schema": "automix-plugin-parameter-validation-report-v1",
            "project_name": "unit",
            "status": "authoring_template_not_validation_evidence",
            "job_id": "semantic_validation_01_reaeq_cockos",
            "plugin_name": "ReaEQ (Cockos)",
            "actual_fx_name": "VST: ReaEQ (Cockos)",
            "source_observation_path": str(out / "reaper_scripts/observations/semantic_validation_01_reaeq_cockos_observation.json"),
            "target_report_path": str(target_report_path(out)),
            "safe_for_automix": False,
            "no_fake_success": False,
            "safe_to_write_parameters": False,
            "writes_analysis_reports": False,
            "observed_parameters": [{"index": 0, "name": "Frequency"}],
            "controls": {},
        },
    )
    write_json(
        out / "eval_reports/plugin_semantic_validation_runtime_report_authoring_package.json",
        {
            "schema": PLUGIN_SEMANTIC_VALIDATION_RUNTIME_REPORT_AUTHORING_PACKAGE_SCHEMA,
            "project_name": "unit",
            "status": "runtime_report_authoring_package_ready" if ready else "no_accepted_runtime_observations",
            "runtime_report_authoring_package_ready": ready,
            "ready_for_manual_report_authoring": ready,
            "ready_for_runtime_evidence_gate": False,
            "safe_to_write_parameters": False,
            "creates_validation_reports": False,
            "writes_analysis_reports": False,
            "accepted_observations_total": 1 if ready else 0,
            "templates_total": 1 if ready else 0,
            "template_results": [
                {
                    "job_id": "semantic_validation_01_reaeq_cockos",
                    "plugin_name": "ReaEQ (Cockos)",
                    "template_path": str(template_path(out)),
                    "target_report_path": str(target_report_path(out)),
                    "template_written": True,
                    "observed_parameters_total": 1,
                    "job_status": "template_ready_for_manual_authoring",
                }
            ]
            if ready
            else [],
            "blockers": [] if ready else ["accepted_runtime_observations_missing"],
            "warnings": [],
        },
    )


def write_candidate(out: Path, *, passed: bool = True, fake_success: bool = False) -> None:
    write_json(
        candidate_path(out),
        {
            "schema": "automix-plugin-parameter-validation-report-v1",
            "project_name": "unit",
            "job_id": "semantic_validation_01_reaeq_cockos",
            "plugin_name": "ReaEQ (Cockos)",
            "adapter_id": "reaeq_cockos",
            "source_observation_path": str(out / "reaper_scripts/observations/semantic_validation_01_reaeq_cockos_observation.json"),
            "status": "passed" if passed else "failed",
            "safe_for_automix": passed,
            "no_fake_success": not fake_success,
            "controls": {
                "presence_gain": {
                    "target_name": "Band 2 Gain" if passed else "",
                    "confidence": 0.91 if passed else 0.2,
                    "write_allowed": passed,
                    "validated": passed,
                    "safe_min": -2.0,
                    "safe_max": 2.0,
                }
            },
        },
    )


def test_authoring_gate_accepts_review_candidate_without_writing_analysis_reports(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    write_authoring_package(out)
    write_candidate(out)
    gate = build_plugin_semantic_validation_runtime_report_authoring_gate(project_name="unit", output_dir=out)
    assert gate["schema"] == PLUGIN_SEMANTIC_VALIDATION_RUNTIME_REPORT_AUTHORING_GATE_SCHEMA
    assert gate["status"] == "runtime_report_authoring_candidates_ready_for_operator_promotion"
    assert gate["authoring_candidates_ready"] is True
    assert gate["ready_for_operator_promotion"] is True
    assert gate["ready_for_runtime_evidence_gate"] is False
    assert gate["safe_to_write_parameters"] is False
    assert gate["writes_analysis_reports"] is False
    assert gate["candidate_reports_are_validation_evidence"] is False
    assert gate["accepted_candidates_total"] == 1
    assert not target_report_path(out).exists()
    manifest = read_json(out / "review/plugin_semantic_validation_runtime_manifest_candidate_from_authoring.json")
    assert manifest["schema"] == "automix-plugin-semantic-validation-runtime-manifest-v1"
    assert manifest["candidate_only"] is True
    assert manifest["queue_jobs"][0]["report_reaudited_by_semantic_gate"] is False


def test_authoring_gate_blocks_when_package_is_not_ready(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    write_authoring_package(out, ready=False)
    gate = build_plugin_semantic_validation_runtime_report_authoring_gate(project_name="unit", output_dir=out)
    assert gate["status"] == "runtime_report_authoring_package_not_ready"
    assert gate["authoring_candidates_ready"] is False
    assert "runtime_report_authoring_package_not_ready:no_accepted_runtime_observations" in gate["blockers"]
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/run_plugin_semantic_validation_runtime_report_authoring_gate.py"),
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
    assert data["authoring_candidates_ready"] is False


def test_authoring_gate_blocks_fake_or_unsafe_candidate(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    write_authoring_package(out)
    write_candidate(out, passed=False, fake_success=True)
    gate = build_plugin_semantic_validation_runtime_report_authoring_gate(project_name="unit", output_dir=out)
    assert gate["authoring_candidates_ready"] is False
    assert "authoring_candidate_not_passed:semantic_validation_01_reaeq_cockos:failed" in gate["blockers"]
    assert "authoring_candidate_no_fake_success_missing:semantic_validation_01_reaeq_cockos" in gate["blockers"]
    assert "authoring_candidate_has_no_write_safe_controls:semantic_validation_01_reaeq_cockos" in gate["blockers"]


def test_report_index_groups_runtime_report_authoring_gate(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    write_authoring_package(out)
    build_plugin_semantic_validation_runtime_report_authoring_gate(project_name="unit", output_dir=out)
    index = build_report_index(project_name="unit", output_dir=out, stage_results=[])
    assert any(
        item["stage"] == "plugin intelligence"
        and item["summary"] == "plugin_semantic_validation_runtime_report_authoring_gate.json"
        for item in index["reports"]
    )


def test_risk_remediation_plan_recommends_runtime_report_authoring_gate(tmp_path: Path) -> None:
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
                    "risk_id": "risk_plugin_authoring_gate",
                    "severity": "blocker",
                    "category": "plugin",
                    "source_report": "plugin_semantic_validation_runtime_report_authoring_gate.json",
                    "code": "authoring_candidate_missing:semantic_validation_01_reaeq_cockos",
                    "summary": "authoring candidate missing",
                    "recommended_next_action": "semantic_validation_runtime",
                }
            ],
            "blockers": ["authoring_candidate_missing:semantic_validation_01_reaeq_cockos"],
            "warnings": [],
        },
    )
    plan = build_risk_remediation_plan(project_name="unit", output_dir=out)
    plugin_action = next(action for action in plan["actions"] if action["phase"] == "plugin_safety")
    assert any("run_plugin_semantic_validation_runtime_report_authoring_gate.py" in command for command in plugin_action["recommended_commands"])
    assert "automix/eval_reports/plugin_semantic_validation_runtime_report_authoring_gate.json" in plugin_action["evidence_to_collect"]


def test_requirements_traceability_includes_runtime_report_authoring_gate(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    audit = build_requirements_traceability_audit(project_name="unit", output_dir=out, workspace_root=ROOT)
    req09 = next(item for item in audit["requirement_results"] if item["id"] == "REQ-09")
    rels = {item["relative_path"] for item in req09["files"]}
    assert "automix/plugins/plugin_semantic_validation_runtime_report_authoring_gate.py" in rels
    assert "scripts/run_plugin_semantic_validation_runtime_report_authoring_gate.py" in rels
    assert "tests/test_prompt81_plugin_semantic_validation_runtime_report_authoring_gate.py" in rels
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
    print("Prompt81 direct tests passed")

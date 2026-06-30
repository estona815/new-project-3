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
from automix.plugins.plugin_availability_decision_gate import build_plugin_availability_decision_gate
from automix.plugins.plugin_availability_operator_decision_package import (
    PLUGIN_AVAILABILITY_DISABLE_MANIFEST_CANDIDATE_SCHEMA,
    build_plugin_availability_operator_decision_package,
)


def write_resolution_plan(out: Path) -> None:
    write_json(
        out / "eval_reports/plugin_availability_resolution_plan.json",
        {
            "schema": "automix-plugin-availability-resolution-plan-v1",
            "project_name": "unit",
            "status": "operator_resolution_required",
            "pending_operator_decisions": ["OTT (Xfer Records)", "TDR Nova (Tokyo Dawn Labs)"],
            "resolutions": [
                {
                    "plugin_name": "OTT (Xfer Records)",
                    "family": "ott",
                    "category": "third_party_or_unknown",
                    "recommended_resolution": "disable_for_automatic_drafts",
                    "fallback_candidate": "ReaXcomp",
                    "fallback_requires_validation": True,
                    "operator_decision_required": True,
                    "automatic_parameter_writes_allowed": False,
                    "required_evidence": ["explicit operator choice"],
                    "disallowed_actions": ["write parameters to any substitute based on catalog fallback text alone"],
                },
                {
                    "plugin_name": "TDR Nova (Tokyo Dawn Labs)",
                    "family": "tdr_nova",
                    "category": "third_party_or_unknown",
                    "recommended_resolution": "disable_for_automatic_drafts",
                    "fallback_candidate": "ReaEQ plus ReaXcomp",
                    "fallback_requires_validation": True,
                    "operator_decision_required": True,
                    "automatic_parameter_writes_allowed": False,
                    "required_evidence": ["explicit operator choice"],
                    "disallowed_actions": ["replace it with a fallback without semantic validation evidence"],
                },
            ],
            "warnings": ["operator_disable_or_install_decision_required"],
            "blockers": [],
        },
    )


def write_decision_gate(out: Path) -> None:
    write_json(
        out / "eval_reports/plugin_availability_decision_gate.json",
        {
            "schema": "automix-plugin-availability-decision-gate-v1",
            "project_name": "unit",
            "status": "operator_decision_manifest_missing",
            "availability_decisions_ready": False,
            "required_decisions_total": 2,
            "accepted_decisions_total": 0,
            "decisions": [
                {
                    "plugin_name": "OTT (Xfer Records)",
                    "status": "blocked",
                    "operator_resolution": "",
                    "operator_acknowledged": False,
                    "blockers": ["operator_decision_missing:OTT (Xfer Records)"],
                },
                {
                    "plugin_name": "TDR Nova (Tokyo Dawn Labs)",
                    "status": "blocked",
                    "operator_resolution": "",
                    "operator_acknowledged": False,
                    "blockers": ["operator_decision_missing:TDR Nova (Tokyo Dawn Labs)"],
                },
            ],
            "blockers": [
                "operator_decision_missing:OTT (Xfer Records)",
                "operator_decision_missing:TDR Nova (Tokyo Dawn Labs)",
            ],
            "warnings": [],
        },
    )


def test_operator_decision_package_writes_candidate_without_accepting_decisions(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    write_resolution_plan(out)
    write_decision_gate(out)
    package = build_plugin_availability_operator_decision_package(project_name="unit", output_dir=out)
    assert package["status"] == "operator_decisions_ready_for_human_acknowledgement"
    assert package["operator_decision_package_ready"] is True
    assert package["availability_decisions_ready"] is False
    assert package["required_decisions_total"] == 2
    assert package["accepted_decisions_total"] == 0
    assert package["safe_to_write_parameters"] is False
    assert package["missing_decisions"] == ["OTT (Xfer Records)", "TDR Nova (Tokyo Dawn Labs)"]
    assert (out / "review/plugin_availability_operator_decision_checklist.md").exists()
    assert not (out / "review/plugin_availability_disable_manifest.json").exists()
    candidate = json.loads((out / "review/plugin_availability_disable_manifest_candidate.json").read_text(encoding="utf-8"))
    assert candidate["schema"] == PLUGIN_AVAILABILITY_DISABLE_MANIFEST_CANDIDATE_SCHEMA
    assert candidate["candidate_only"] is True
    assert all(item["operator_acknowledged"] is False for item in candidate["disabled_plugins"])


def test_candidate_manifest_is_not_accepted_by_decision_gate(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    write_resolution_plan(out)
    write_decision_gate(out)
    package = build_plugin_availability_operator_decision_package(project_name="unit", output_dir=out)
    gate = build_plugin_availability_decision_gate(
        project_name="unit",
        output_dir=out,
        decision_manifest_path=Path(package["candidate_manifest_path"]),
    )
    assert gate["availability_decisions_ready"] is False
    assert "plugin_availability_decision_manifest_schema_invalid" in gate["blockers"]


def test_operator_decision_package_cli_require_ready_returns_nonzero_without_resolution_plan(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/run_plugin_availability_operator_decision_package.py"),
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
    assert data["operator_decision_package_ready"] is False
    assert "plugin_availability_resolution_plan_missing_or_invalid" in data["blockers"]


def test_report_index_groups_plugin_availability_operator_decision_package(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    write_resolution_plan(out)
    write_decision_gate(out)
    build_plugin_availability_operator_decision_package(project_name="unit", output_dir=out)
    index = build_report_index(project_name="unit", output_dir=out, stage_results=[])
    assert any(
        item["stage"] == "plugin intelligence" and item["summary"] == "plugin_availability_operator_decision_package.json"
        for item in index["reports"]
    )


def test_risk_remediation_plan_recommends_operator_decision_package(tmp_path: Path) -> None:
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
                    "risk_id": "risk_plugin_availability",
                    "severity": "blocker",
                    "category": "plugin",
                    "source_report": "plugin_availability_decision_gate.json",
                    "code": "plugin_availability_decision_manifest_missing",
                    "summary": "availability decision missing",
                    "recommended_next_action": "plugin_availability_decision",
                }
            ],
            "blockers": ["plugin_availability_decision_manifest_missing"],
            "warnings": [],
        },
    )
    plan = build_risk_remediation_plan(project_name="unit", output_dir=out)
    plugin_action = next(action for action in plan["actions"] if action["phase"] == "plugin_safety")
    assert any("run_plugin_availability_operator_decision_package.py" in command for command in plugin_action["recommended_commands"])
    assert "automix/eval_reports/plugin_availability_operator_decision_package.json" in plugin_action["evidence_to_collect"]


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
    print("Prompt77 direct tests passed")

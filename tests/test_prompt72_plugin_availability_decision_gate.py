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
from automix.plugins.plugin_availability_resolution_plan import build_plugin_availability_resolution_plan


def write_action_plan(out: Path, actions: list[dict]) -> None:
    write_json(
        out / "eval_reports/plugin_validation_action_plan.json",
        {
            "schema": "automix-plugin-validation-action-plan-v1",
            "project_name": "unit",
            "plugin_actions": actions,
            "blockers": [f"{item['plugin_name']}:{item['action_id']}" for item in actions if item.get("severity") == "blocker"],
            "summary": {"safe_to_write_parameters": False},
        },
    )


def unavailable(plugin_name: str, *, category: str = "third_party_or_unknown") -> dict:
    return {
        "plugin_name": plugin_name,
        "action_id": "install_or_disable_unavailable_plugin",
        "severity": "blocker",
        "category": category,
        "available": False,
        "matching_reports_total": 0,
        "passed_reports_total": 0,
        "safe_control_count": 0,
        "semantic_validation_passed": False,
    }


def build_resolution(out: Path, actions: list[dict] | None = None) -> dict:
    write_action_plan(out, actions or [unavailable("OTT (Xfer Records)"), unavailable("TDR Nova (Tokyo Dawn Labs)")])
    return build_plugin_availability_resolution_plan(project_name="unit", output_dir=out, catalog_path=ROOT / "automix/plugin_capability_catalog.json")


def write_manifest(out: Path, entries: list[dict]) -> Path:
    path = out / "review/plugin_availability_disable_manifest.json"
    write_json(
        path,
        {
            "schema": "automix-plugin-availability-disable-manifest-v1",
            "disabled_plugins": entries,
            "operator_acknowledgement_required": True,
        },
    )
    return path


def accepted_entry(plugin_name: str, fallback: str) -> dict:
    return {
        "plugin_name": plugin_name,
        "resolution": "disable_for_automatic_drafts",
        "fallback_candidate": fallback,
        "fallback_requires_validation": True,
        "automatic_parameter_writes_allowed": False,
        "operator_acknowledged": True,
    }


def test_decision_gate_blocks_missing_accepted_manifest_and_writes_request(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    build_resolution(out)
    gate = build_plugin_availability_decision_gate(project_name="unit", output_dir=out)
    assert gate["status"] == "operator_decision_manifest_missing"
    assert gate["availability_decisions_ready"] is False
    assert "plugin_availability_decision_manifest_missing" in gate["blockers"]
    assert "operator_decision_missing:OTT (Xfer Records)" in gate["blockers"]
    assert (out / "eval_reports/plugin_availability_decision_gate.json").exists()
    assert (out / "review/plugin_availability_decision_request.md").exists()


def test_decision_gate_accepts_acknowledged_disable_manifest_but_never_writes_parameters(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    build_resolution(out)
    write_manifest(
        out,
        [
            accepted_entry("OTT (Xfer Records)", "ReaXcomp"),
            accepted_entry("TDR Nova (Tokyo Dawn Labs)", "ReaEQ plus ReaXcomp"),
        ],
    )
    gate = build_plugin_availability_decision_gate(project_name="unit", output_dir=out)
    assert gate["status"] == "operator_decisions_ready"
    assert gate["availability_decisions_ready"] is True
    assert gate["accepted_decisions_total"] == 2
    assert gate["safe_to_write_parameters"] is False
    assert gate["blockers"] == []
    assert all(item["fallback_requires_validation"] is True for item in gate["decisions"])
    md = (out / "eval_reports/plugin_availability_decision_gate.md").read_text(encoding="utf-8")
    assert "Fallback writes remain blocked" in md


def test_decision_gate_blocks_automatic_writes_for_unavailable_plugin(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    build_resolution(out, [unavailable("OTT (Xfer Records)")])
    entry = accepted_entry("OTT (Xfer Records)", "ReaXcomp")
    entry["automatic_parameter_writes_allowed"] = True
    write_manifest(out, [entry])
    gate = build_plugin_availability_decision_gate(project_name="unit", output_dir=out)
    assert gate["availability_decisions_ready"] is False
    assert "unavailable_plugin_parameter_write_not_allowed:OTT (Xfer Records)" in gate["blockers"]


def test_decision_gate_blocks_missing_required_plugin_entry(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    build_resolution(out)
    write_manifest(out, [accepted_entry("OTT (Xfer Records)", "ReaXcomp")])
    gate = build_plugin_availability_decision_gate(project_name="unit", output_dir=out)
    assert gate["availability_decisions_ready"] is False
    assert gate["missing_decisions"] == ["TDR Nova (Tokyo Dawn Labs)"]
    assert "operator_decision_missing:TDR Nova (Tokyo Dawn Labs)" in gate["blockers"]


def test_decision_gate_passes_without_manifest_when_no_unavailable_plugins_exist(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    build_resolution(
        out,
        [
            {
                "plugin_name": "ReaEQ (Cockos)",
                "action_id": "plugin_write_safe_ready",
                "severity": "info",
                "category": "stock",
                "available": True,
            }
        ],
    )
    gate = build_plugin_availability_decision_gate(project_name="unit", output_dir=out)
    assert gate["status"] == "no_unavailable_plugins_to_resolve"
    assert gate["availability_decisions_ready"] is True
    assert gate["required_decisions_total"] == 0
    assert gate["safe_to_write_parameters"] is False


def test_decision_gate_cli_require_ready_returns_nonzero_when_manifest_missing(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    build_resolution(out, [unavailable("OTT (Xfer Records)")])
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/run_plugin_availability_decision_gate.py"),
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
    assert data["status"] == "operator_decision_manifest_missing"
    assert data["availability_decisions_ready"] is False
    assert Path(data["request_md"]).exists()


def test_report_index_groups_plugin_availability_decision_gate(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    build_resolution(out, [unavailable("OTT (Xfer Records)")])
    build_plugin_availability_decision_gate(project_name="unit", output_dir=out)
    index = build_report_index(project_name="unit", output_dir=out, stage_results=[])
    assert any(
        item["stage"] == "plugin intelligence" and item["summary"] == "plugin_availability_decision_gate.json"
        for item in index["reports"]
    )


def test_risk_remediation_plan_recommends_plugin_availability_decision_gate(tmp_path: Path) -> None:
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
                    "source_report": "plugin_availability_decision_gate.json",
                    "code": "plugin_availability_decision:operator_decision_manifest_missing",
                    "summary": "operator decision missing",
                    "recommended_next_action": "run plugin availability decision gate",
                }
            ],
            "blockers": ["plugin_availability_decision:operator_decision_manifest_missing"],
            "warnings": [],
        },
    )
    plan = build_risk_remediation_plan(project_name="unit", output_dir=out)
    plugin_action = next(action for action in plan["actions"] if action["phase"] == "plugin_safety")
    assert any("run_plugin_availability_decision_gate.py" in command for command in plugin_action["recommended_commands"])
    assert "automix/eval_reports/plugin_availability_decision_gate.json" in plugin_action["evidence_to_collect"]
    assert "automix/review/plugin_availability_disable_manifest.json" in plugin_action["evidence_to_collect"]


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
    print("Prompt72 direct tests passed")

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


def test_availability_resolution_plan_disables_optional_unavailable_third_party_plugins(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    write_action_plan(out, [unavailable("OTT (Xfer Records)"), unavailable("TDR Nova (Tokyo Dawn Labs)")])
    plan = build_plugin_availability_resolution_plan(project_name="unit", output_dir=out, catalog_path=ROOT / "automix/plugin_capability_catalog.json")
    by_name = {item["plugin_name"]: item for item in plan["resolutions"]}
    assert plan["status"] == "operator_resolution_required"
    assert plan["safe_to_write_parameters"] is False
    assert plan["blockers"] == []
    assert plan["pending_operator_decisions"] == ["OTT (Xfer Records)", "TDR Nova (Tokyo Dawn Labs)"]
    assert by_name["OTT (Xfer Records)"]["recommended_resolution"] == "disable_for_automatic_drafts"
    assert by_name["OTT (Xfer Records)"]["fallback_candidate"] == "ReaXcomp"
    assert by_name["TDR Nova (Tokyo Dawn Labs)"]["fallback_candidate"] == "ReaEQ plus ReaXcomp"
    manifest = json.loads((out / "review/plugin_availability_disable_manifest_template.json").read_text(encoding="utf-8"))
    assert len(manifest["disabled_plugins"]) == 2
    assert all(item["automatic_parameter_writes_allowed"] is False for item in manifest["disabled_plugins"])
    md = (out / "eval_reports/plugin_availability_resolution_plan.md").read_text(encoding="utf-8")
    assert "does not approve fallback parameter writes" in md


def test_availability_resolution_plan_keeps_required_artifact_jsfx_as_blocker(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    write_action_plan(out, [unavailable("Codex Vocal/vocal_ai_artifact_split_tamer.jsfx", category="jsfx")])
    plan = build_plugin_availability_resolution_plan(project_name="unit", output_dir=out, catalog_path=ROOT / "automix/plugin_capability_catalog.json")
    assert plan["blockers"] == ["Codex Vocal/vocal_ai_artifact_split_tamer.jsfx:repair_required_jsfx_path"]
    assert plan["resolutions"][0]["recommended_resolution"] == "repair_required_jsfx_path"
    assert plan["resolutions"][0]["install_or_disable_allowed"] is False


def test_availability_resolution_plan_handles_no_unavailable_plugins(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    write_action_plan(
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
    plan = build_plugin_availability_resolution_plan(project_name="unit", output_dir=out, catalog_path=ROOT / "automix/plugin_capability_catalog.json")
    assert plan["status"] == "no_unavailable_plugins_detected"
    assert plan["unavailable_plugins_total"] == 0
    assert plan["pending_operator_decisions"] == []


def test_availability_resolution_cli_require_resolved_returns_nonzero(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    write_action_plan(out, [unavailable("OTT (Xfer Records)")])
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/run_plugin_availability_resolution_plan.py"),
            "--project-name",
            "unit",
            "--output-dir",
            str(out),
            "--require-resolved",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    data = json.loads(result.stdout)
    assert result.returncode == 2
    assert data["status"] == "operator_resolution_required"
    assert data["pending_operator_decisions"] == ["OTT (Xfer Records)"]
    assert Path(data["disable_manifest_template"]).exists()


def test_report_index_groups_plugin_availability_resolution_plan(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    write_action_plan(out, [unavailable("OTT (Xfer Records)")])
    build_plugin_availability_resolution_plan(project_name="unit", output_dir=out, catalog_path=ROOT / "automix/plugin_capability_catalog.json")
    index = build_report_index(project_name="unit", output_dir=out, stage_results=[])
    assert any(
        item["stage"] == "plugin intelligence" and item["summary"] == "plugin_availability_resolution_plan.json"
        for item in index["reports"]
    )


def test_risk_remediation_plan_recommends_availability_resolution_plan(tmp_path: Path) -> None:
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
                    "source_report": "plugin_validation_preflight.json",
                    "code": "plugin_validation_preflight:required_plugin_availability_missing:OTT (Xfer Records)",
                    "summary": "plugin unavailable",
                    "recommended_next_action": "install or disable",
                }
            ],
            "blockers": ["plugin_validation_preflight:required_plugin_availability_missing:OTT (Xfer Records)"],
            "warnings": [],
        },
    )
    plan = build_risk_remediation_plan(project_name="unit", output_dir=out)
    plugin_action = next(action for action in plan["actions"] if action["phase"] == "plugin_safety")
    assert any("run_plugin_availability_resolution_plan.py" in command for command in plugin_action["recommended_commands"])
    assert "automix/eval_reports/plugin_availability_resolution_plan.json" in plugin_action["evidence_to_collect"]


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
    print("Prompt71 direct tests passed")

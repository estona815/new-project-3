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


def write_register(out: Path, risks: list[dict]) -> None:
    counts = {"blocker": 0, "warning": 0, "review": 0, "info": 0}
    for risk in risks:
        counts[risk["severity"]] = counts.get(risk["severity"], 0) + 1
    write_json(
        out / "eval_reports/open_risk_register.json",
        {
            "schema": "automix-open-risk-register-v1",
            "project_name": "unit",
            "passed": counts.get("blocker", 0) == 0,
            "risk_counts": counts,
            "open_risks": risks,
            "blockers": [risk["code"] for risk in risks if risk["severity"] == "blocker"],
            "warnings": [],
        },
    )


def risk(severity: str, category: str, code: str, *, risk_id: str | None = None, context: dict | None = None) -> dict:
    return {
        "risk_id": risk_id or f"risk_{code.replace(':', '_')}",
        "severity": severity,
        "category": category,
        "source_report": f"{category}.json",
        "code": code,
        "summary": code,
        "context": context or {},
        "recommended_next_action": code,
    }


def test_risk_remediation_plan_maps_open_risks_to_safe_phased_actions(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    write_register(
        out,
        [
            risk("blocker", "plugin", "validated_plugin_mapping_required"),
            risk("warning", "plugin", "missing_or_unsafe_plugin_mapping:OTT (Xfer Records)"),
            risk("blocker", "source", "stem_required_tracks:2"),
            risk(
                "blocker",
                "source",
                "high_risk_track:unsafe:SOURCE full mix reference muted",
                context={"track_name": "SOURCE full mix reference muted", "recommended_next_action": "provide_isolated_stems"},
            ),
            risk("blocker", "intent", "artifact_signal_not_established"),
            risk("blocker", "final_export", "no_accepted_export_source"),
        ],
    )
    plan = build_risk_remediation_plan(project_name="unit", output_dir=out)
    phases = [action["phase"] for action in plan["actions"]]
    assert phases[:5] == ["plugin_safety", "source_intake", "intent_routing", "final_export", "verification"]
    assert all(action["dry_run_only"] is True for action in plan["actions"])
    assert all(action["destructive"] is False for action in plan["actions"])
    plugin = next(action for action in plan["actions"] if action["phase"] == "plugin_safety")
    assert "hard-code uncertain parameter indexes" in plugin["disallowed_actions"]
    source = next(action for action in plan["actions"] if action["phase"] == "source_intake")
    assert "pitch-correct the full mix" in source["disallowed_actions"]
    export = next(action for action in plan["actions"] if action["phase"] == "final_export")
    assert any("final_export_state.safe_to_export" in item for item in export["acceptance_criteria"])
    assert (out / "eval_reports/risk_remediation_plan.json").exists()
    md = (out / "eval_reports/risk_remediation_plan.md").read_text(encoding="utf-8")
    assert "does not apply processing" in md


def test_risk_remediation_plan_handles_no_open_risks_with_verification_action(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    write_register(out, [])
    plan = build_risk_remediation_plan(project_name="unit", output_dir=out)
    assert plan["status"] == "no_open_risks_to_remediate"
    assert plan["actions_total"] == 1
    assert plan["actions"][0]["phase"] == "verification"


def test_risk_remediation_cli_writes_reports(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    write_register(out, [risk("blocker", "final_export", "no_accepted_export_source")])
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/run_risk_remediation_plan.py"),
            "--project-name",
            "unit",
            "--output-dir",
            str(out),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    data = json.loads(result.stdout)
    assert data["status"] == "remediation_plan_ready"
    assert data["actions_total"] >= 2
    assert Path(data["report_json"]).exists()
    assert Path(data["report_md"]).exists()


def test_report_index_groups_risk_remediation_plan(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    write_register(out, [])
    build_risk_remediation_plan(project_name="unit", output_dir=out)
    index = build_report_index(project_name="unit", output_dir=out, stage_results=[])
    assert any(item["stage"] == "delivery readiness" and item["summary"] == "risk_remediation_plan.json" for item in index["reports"])


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
    print("Prompt53 direct tests passed")

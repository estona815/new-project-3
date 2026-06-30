from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from automix.orchestrator.professional_readiness_audit import build_professional_readiness_audit
from automix.orchestrator.report_index import build_report_index
from automix.orchestrator.risk_remediation_planner import build_risk_remediation_plan
from automix.orchestrator.risk_root_cause_rollup import build_risk_root_cause_rollup
from automix.plugins.plugin_adapter_schema import write_json


def risk(severity: str, category: str, code: str, *, risk_id: str | None = None, source_report: str | None = None) -> dict:
    return {
        "risk_id": risk_id or f"risk_{code.replace(':', '_')}",
        "severity": severity,
        "category": category,
        "source_report": source_report or f"{category}.json",
        "code": code,
        "summary": code,
        "context": {},
        "recommended_next_action": code,
    }


def write_register(out: Path, risks: list[dict]) -> None:
    counts = {"blocker": 0, "warning": 0, "review": 0, "info": 0}
    for item in risks:
        counts[item["severity"]] = counts.get(item["severity"], 0) + 1
    write_json(
        out / "eval_reports/open_risk_register.json",
        {
            "schema": "automix-open-risk-register-v1",
            "project_name": "unit",
            "passed": counts.get("blocker", 0) == 0,
            "risk_counts": counts,
            "open_risks": risks,
            "blockers": [item["code"] for item in risks if item["severity"] == "blocker"],
            "warnings": [],
        },
    )


def test_risk_root_cause_rollup_handles_no_open_risks(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    write_register(out, [])
    rollup = build_risk_root_cause_rollup(project_name="unit", output_dir=out)
    assert rollup["passed"] is True
    assert rollup["open_risk_total"] == 0
    assert rollup["root_cause_total"] == 0
    assert rollup["warnings"] == ["no_open_risks_found"]
    assert (out / "eval_reports/risk_root_cause_rollup.json").exists()
    md = (out / "eval_reports/risk_root_cause_rollup.md").read_text(encoding="utf-8")
    assert "does not approve audio" in md


def test_risk_root_cause_rollup_groups_repeated_delivery_risks(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    write_register(
        out,
        [
            risk("blocker", "plugin", "validated_plugin_mapping_required"),
            risk("blocker", "plugin", "plugin_semantic_validation_gate:not_ready"),
            risk("blocker", "source", "no_accepted_export_source"),
            risk("blocker", "render", "primary_wav_render_missing"),
            risk("blocker", "final_qc", "final_qc_evidence_not_ready"),
            risk("blocker", "ab_preview", "ab_preview_output_path_missing"),
            risk("blocker", "approval", "final_approval_evidence_not_ready"),
            risk("blocker", "package", "deliverable_package_manifest_has_missing_files"),
            risk("blocker", "delivery", "final_delivery_consistency_not_ready"),
        ],
    )
    rollup = build_risk_root_cause_rollup(project_name="unit", output_dir=out)
    cause_ids = [cause["cause_id"] for cause in rollup["root_causes"]]
    assert rollup["passed"] is False
    assert rollup["open_risk_total"] == 9
    assert rollup["root_cause_total"] < rollup["open_risk_total"]
    assert rollup["next_root_cause"]["cause_id"] == "plugin_validation_not_ready"
    assert "accepted_source_or_stems_missing" in cause_ids
    assert "primary_render_missing" in cause_ids
    assert "deliverable_package_missing" in cause_ids


def test_risk_root_cause_rollup_cli_require_clear_returns_nonzero(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    write_register(out, [risk("blocker", "final_export", "no_accepted_export_source")])
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/run_risk_root_cause_rollup.py"),
            "--project-name",
            "unit",
            "--output-dir",
            str(out),
            "--require-clear",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    data = json.loads(result.stdout)
    assert result.returncode == 2
    assert data["status"] == "root_causes_open"
    assert data["next_root_cause"] == "accepted_source_or_stems_missing"
    assert Path(data["report_json"]).exists()
    assert Path(data["report_md"]).exists()


def test_risk_remediation_plan_references_root_cause_rollup(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    write_register(out, [risk("blocker", "final_export", "no_accepted_export_source")])
    plan = build_risk_remediation_plan(project_name="unit", output_dir=out)
    assert plan["source_root_cause_rollup"].endswith("risk_root_cause_rollup.json")
    assert plan["root_cause_total"] == 1
    assert plan["next_root_cause"]["cause_id"] == "accepted_source_or_stems_missing"
    assert (out / "eval_reports/risk_root_cause_rollup.json").exists()
    md = (out / "eval_reports/risk_remediation_plan.md").read_text(encoding="utf-8")
    assert "## Next Root Cause" in md


def test_professional_readiness_requires_root_cause_rollup_for_delivery(tmp_path: Path) -> None:
    audit = build_professional_readiness_audit(
        project_name="unit",
        output_dir=tmp_path / "automix",
        workspace_root=ROOT,
        final_delivery_requested=True,
    )
    assert "risk_root_cause_rollup_missing" in audit["blockers"]


def test_report_index_groups_risk_root_cause_rollup(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    write_register(out, [])
    build_risk_root_cause_rollup(project_name="unit", output_dir=out)
    index = build_report_index(project_name="unit", output_dir=out, stage_results=[])
    assert any(
        item["stage"] == "delivery readiness" and item["summary"] == "risk_root_cause_rollup.json"
        for item in index["reports"]
    )


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
    print("Prompt69 direct tests passed")

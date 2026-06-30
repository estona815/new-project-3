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
from automix.plugins.plugin_semantic_validation_gate import build_plugin_semantic_validation_gate
from automix.plugins.plugin_adapter_schema import write_json


def write_required(out: Path, names: list[str]) -> None:
    write_json(
        out / "eval_reports/plugin_validation_preflight.json",
        {
            "schema": "automix-plugin-validation-preflight-v1",
            "project_name": "unit",
            "required_plugins": names,
        },
    )
    write_json(
        out / "eval_reports/real_project_plugin_readiness.json",
        {
            "schema": "automix-real-project-plugin-readiness-v1",
            "project_name": "unit",
            "missing_or_unsafe_mappings": names,
        },
    )


def write_report(out: Path, *, plugin_name: str = "ReaEQ", status: str = "passed", safe: bool = True, control_safe: bool = True, no_fake: bool = True) -> None:
    write_json(
        out / f"analysis_reports/plugin_parameter_validation_{plugin_name.lower()}_adapter.json",
        {
            "schema": "automix-plugin-parameter-validation-report-v1",
            "validator_version": "unit",
            "plugin_name": plugin_name,
            "adapter_id": f"{plugin_name.lower()}_adapter",
            "status": status,
            "safe_for_automix": safe,
            "no_fake_success": no_fake,
            "schema_errors": [],
            "reason_codes": [] if status == "passed" else ["PLUGIN_NOT_AVAILABLE_FOR_VALIDATION"],
            "controls": {
                "gain_db": {
                    "target_name": "Gain",
                    "confidence": 0.93 if control_safe else 0.5,
                    "write_allowed": control_safe,
                    "validated": control_safe,
                    "notes": "observed response" if control_safe else "not observed",
                }
            },
        },
    )


def test_plugin_semantic_gate_blocks_missing_reports_and_writes_template(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    write_required(out, ["ReaEQ (Cockos)"])
    gate = build_plugin_semantic_validation_gate(project_name="unit", output_dir=out)
    assert gate["semantic_validation_ready"] is False
    assert "semantic_validation_reports_missing" in gate["blockers"]
    assert "validation_report_missing:ReaEQ (Cockos)" in gate["blockers"]
    assert (out / "review/plugin_semantic_validation_manifest_template.json").exists()
    assert (out / "review/plugin_semantic_validation_request.md").exists()


def test_plugin_semantic_gate_blocks_validation_unavailable_report(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    write_required(out, ["ReaEQ (Cockos)"])
    write_report(out, plugin_name="ReaEQ", status="validation_unavailable", safe=False, control_safe=False, no_fake=True)
    gate = build_plugin_semantic_validation_gate(project_name="unit", output_dir=out)
    assert gate["semantic_validation_ready"] is False
    assert any("validation_report_not_passed:validation_unavailable" in blocker for blocker in gate["blockers"])
    assert any("validation_report_has_no_write_safe_controls" in blocker for blocker in gate["blockers"])


def test_plugin_semantic_gate_blocks_fake_success_without_write_safe_controls(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    write_required(out, ["ReaEQ (Cockos)"])
    write_report(out, plugin_name="ReaEQ", status="passed", safe=True, control_safe=False, no_fake=False)
    gate = build_plugin_semantic_validation_gate(project_name="unit", output_dir=out)
    assert gate["semantic_validation_ready"] is False
    assert any("validation_report_no_fake_success_missing" in blocker for blocker in gate["blockers"])
    assert any("validation_report_has_no_write_safe_controls" in blocker for blocker in gate["blockers"])


def test_plugin_semantic_gate_passes_all_required_plugins_with_safe_reports(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    write_required(out, ["ReaEQ (Cockos)"])
    write_report(out, plugin_name="ReaEQ", status="passed", safe=True, control_safe=True, no_fake=True)
    gate = build_plugin_semantic_validation_gate(project_name="unit", output_dir=out)
    assert gate["semantic_validation_ready"] is True
    assert gate["blockers"] == []
    assert gate["safe_controls_total"] == 1
    assert gate["plugins_with_passed_semantic_validation"] == ["ReaEQ (Cockos)"]


def test_plugin_semantic_gate_cli_require_ready_returns_nonzero_when_blocked(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    write_required(out, ["ReaEQ (Cockos)"])
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/run_plugin_semantic_validation_gate.py"),
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
    assert data["status"] == "blocked"
    assert "validation_report_missing:ReaEQ (Cockos)" in data["blockers"]
    assert Path(data["report_json"]).exists()


def test_plugin_semantic_gate_cli_ready_with_safe_report(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    write_required(out, ["ReaEQ (Cockos)"])
    write_report(out, plugin_name="ReaEQ", status="passed", safe=True, control_safe=True, no_fake=True)
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/run_plugin_semantic_validation_gate.py"),
            "--project-name",
            "unit",
            "--output-dir",
            str(out),
            "--require-ready",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    data = json.loads(result.stdout)
    assert data["status"] == "ready"
    assert data["semantic_validation_ready"] is True


def test_report_index_groups_plugin_semantic_validation_gate(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    write_required(out, ["ReaEQ (Cockos)"])
    build_plugin_semantic_validation_gate(project_name="unit", output_dir=out)
    index = build_report_index(project_name="unit", output_dir=out, stage_results=[])
    assert any(item["stage"] == "plugin intelligence" and item["summary"] == "plugin_semantic_validation_gate.json" for item in index["reports"])


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
    print("Prompt60 direct tests passed")

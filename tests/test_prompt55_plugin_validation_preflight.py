from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from automix.plugins.plugin_adapter_schema import write_json
from automix.plugins.plugin_validation_preflight import build_plugin_validation_preflight


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_fake_environment(tmp_path: Path) -> tuple[Path, Path, Path]:
    reaper_app = tmp_path / "REAPER.app"
    stock_fx = reaper_app / "Contents/Plugins/FX"
    stock_fx.mkdir(parents=True)
    (stock_fx / "reaeq.vst.dylib").write_text("stock reaeq", encoding="utf-8")
    (stock_fx / "reacomp.vst.dylib").write_text("stock reacomp", encoding="utf-8")
    resource = tmp_path / "REAPER"
    effects = resource / "Effects/Vocal Clarity Repair"
    effects.mkdir(parents=True)
    (effects / "vocal_air_guard.jsfx").write_text("desc:vocal air guard", encoding="utf-8")
    out = tmp_path / "automix"
    write_json(
        out / "eval_reports/real_project_plugin_readiness.json",
        {
            "schema": "automix-real-project-plugin-readiness-v1",
            "project_name": "unit",
            "safe_draft_plugin_ready": False,
            "missing_or_unsafe_mappings": [
                "ReaEQ (Cockos)",
                "ReaComp (Cockos)",
                "Vocal Clarity Repair/vocal_air_guard.jsfx",
            ],
            "stock_fallbacks_available": ["ReaEQ (Cockos)", "ReaComp (Cockos)"],
            "jsfx_fallbacks_available": [],
        },
    )
    write_json(
        out / "analysis_reports/plugin_parameter_validation_reaeq_adapter.json",
        {
            "schema": "automix-plugin-parameter-validation-report-v1",
            "adapter_id": "reaeq_adapter",
            "plugin_name": "ReaEQ",
            "status": "validation_unavailable",
            "safe_for_automix": False,
        },
    )
    return out, reaper_app, resource


def test_plugin_validation_preflight_detects_availability_without_write_safety(tmp_path: Path) -> None:
    out, reaper_app, resource = write_fake_environment(tmp_path)
    preflight = build_plugin_validation_preflight(
        project_name="unit",
        output_dir=out,
        reaper_app=reaper_app,
        reaper_resource_dir=resource,
    )
    assert preflight["summary"]["available_plugins_total"] == 3
    assert preflight["summary"]["missing_plugins_total"] == 0
    assert preflight["summary"]["safe_to_write_parameters"] is False
    assert "semantic_parameter_validation_required" in preflight["blockers"]
    assert "availability_does_not_grant_write_safety" in preflight["warnings"]
    assert "adapter_validation_reports_unavailable" in preflight["warnings"]
    report = (out / "eval_reports/plugin_validation_preflight.md").read_text(encoding="utf-8")
    assert "This is an inventory-only preflight" in report


def test_plugin_validation_preflight_reports_missing_required_plugins(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    reaper_app = tmp_path / "REAPER.app"
    (reaper_app / "Contents/Plugins/FX").mkdir(parents=True)
    resource = tmp_path / "REAPER"
    (resource / "Effects").mkdir(parents=True)
    write_json(
        out / "eval_reports/real_project_plugin_readiness.json",
        {
            "schema": "automix-real-project-plugin-readiness-v1",
            "project_name": "unit",
            "safe_draft_plugin_ready": False,
            "missing_or_unsafe_mappings": ["ReaDelay (Cockos)", "Missing Custom/custom_guard.jsfx"],
        },
    )
    preflight = build_plugin_validation_preflight(project_name="unit", output_dir=out, reaper_app=reaper_app, reaper_resource_dir=resource)
    assert preflight["status"] == "availability_or_validation_incomplete"
    assert preflight["summary"]["missing_plugins_total"] == 2
    assert "required_plugin_availability_missing:ReaDelay (Cockos)" in preflight["blockers"]
    assert "required_plugin_availability_missing:Missing Custom/custom_guard.jsfx" in preflight["blockers"]


def test_plugin_validation_preflight_cli_writes_reports_and_can_require_safe_write(tmp_path: Path) -> None:
    out, reaper_app, resource = write_fake_environment(tmp_path)
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/run_plugin_validation_preflight.py"),
            "--project-name",
            "unit",
            "--output-dir",
            str(out),
            "--reaper-app",
            str(reaper_app),
            "--reaper-resource-dir",
            str(resource),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    data = json.loads(result.stdout)
    assert data["safe_to_write_parameters"] is False
    assert Path(data["report_json"]).exists()
    assert Path(data["report_md"]).exists()

    blocked = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/run_plugin_validation_preflight.py"),
            "--project-name",
            "unit",
            "--output-dir",
            str(out),
            "--reaper-app",
            str(reaper_app),
            "--reaper-resource-dir",
            str(resource),
            "--require-safe-write",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert blocked.returncode == 2
    assert json.loads(blocked.stdout)["safe_to_write_parameters"] is False

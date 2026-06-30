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
from automix.plugins.plugin_adapter_schema import write_json
from automix.plugins.plugin_semantic_validation_runtime_collection_package import (
    build_plugin_semantic_validation_runtime_collection_package,
)
from automix.plugins.plugin_semantic_validation_runtime_collector_package import (
    build_plugin_semantic_validation_runtime_collector_package,
)
from automix.plugins.reaper_runtime_collector_safety_audit import (
    REAPER_RUNTIME_COLLECTOR_SAFETY_AUDIT_SCHEMA,
    build_reaper_runtime_collector_safety_audit,
)


def queue_job(plugin_name: str = "ReaEQ (Cockos)", job_id: str = "semantic_validation_01_reaeq_cockos") -> dict:
    return {
        "job_id": job_id,
        "plugin_name": plugin_name,
        "priority": 20,
        "category": "stock",
        "collection_action": "collect_missing_reaper_observed_semantic_report",
        "target_report_path": f"automix/analysis_reports/plugin_parameter_validation_{job_id}_reaper_observed.json",
        "requires_reaper_runtime": True,
        "requires_temporary_muted_test_context": True,
        "requires_operator_review": True,
        "required_observations": ["REAPER runtime observed the exact plugin", "parameter names listed by TrackFX_GetParamName"],
        "acceptance_criteria": ["status=passed only after manual semantic review"],
        "disallowed_actions": ["do not write parameters to the user's mix from this queue"],
    }


def write_queue(out: Path, jobs: list[dict] | None = None, blocked_jobs: list[dict] | None = None) -> None:
    jobs = jobs if jobs is not None else [queue_job()]
    write_json(
        out / "eval_reports/plugin_semantic_validation_queue.json",
        {
            "schema": "automix-plugin-semantic-validation-queue-v1",
            "project_name": "unit",
            "queue_jobs_total": len(jobs),
            "blocked_jobs_total": len(blocked_jobs or []),
            "ready_to_run_reaper_collection": bool(jobs),
            "requires_reaper_runtime": bool(jobs),
            "requires_operator_review": bool(jobs or blocked_jobs),
            "safe_to_write_parameters": False,
            "queue_jobs": jobs,
            "blocked_jobs": blocked_jobs or [],
            "blockers": [],
            "warnings": [],
        },
    )


def build_good_collector(out: Path) -> None:
    write_queue(
        out,
        [
            queue_job("ReaEQ (Cockos)", "semantic_validation_01_reaeq_cockos"),
            queue_job("ReaComp (Cockos)", "semantic_validation_02_reacomp_cockos"),
        ],
        blocked_jobs=[{"plugin_name": "OTT (Xfer Records)", "blockers": ["availability_decision_missing:OTT (Xfer Records)"]}],
    )
    build_plugin_semantic_validation_runtime_collection_package(project_name="unit", output_dir=out)
    build_plugin_semantic_validation_runtime_collector_package(project_name="unit", output_dir=out)


def test_reaper_runtime_collector_safety_audit_passes_generated_observation_collector(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    build_good_collector(out)

    audit = build_reaper_runtime_collector_safety_audit(project_name="unit", output_dir=out)

    assert audit["schema"] == REAPER_RUNTIME_COLLECTOR_SAFETY_AUDIT_SCHEMA
    assert audit["status"] == "collector_safety_passed"
    assert audit["passed"] is True
    assert audit["safe_for_operator_runtime_collection"] is True
    assert audit["mutation_model"]["in_memory_temporary_probe_track_mutation"] is True
    assert audit["mutation_model"]["writes_parameters"] is False
    assert audit["mutation_model"]["renders_audio"] is False
    assert audit["mutation_model"]["saves_project"] is False
    assert audit["disallowed_reaper_calls"] == []
    assert "temporary_probe_track_mutation_detected" in audit["warnings"]
    assert "collector_writes_raw_observation_files" in audit["warnings"]
    assert "TrackFX_SetParam" not in audit["reaper_calls"]
    assert (out / "eval_reports/reaper_runtime_collector_safety_audit.json").exists()
    assert (out / "eval_reports/reaper_runtime_collector_safety_audit.md").exists()


def test_reaper_runtime_collector_safety_audit_blocks_parameter_write_and_save_calls(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    build_good_collector(out)
    lua_path = out / "reaper_scripts/collect_plugin_semantic_validation_runtime.lua"
    lua_path.write_text(
        lua_path.read_text(encoding="utf-8")
        + "\nreaper.TrackFX_SetParam(track, 0, 0, 0.5)\nreaper.SaveProject(0, false)\n",
        encoding="utf-8",
    )

    audit = build_reaper_runtime_collector_safety_audit(project_name="unit", output_dir=out)

    assert audit["passed"] is False
    assert "lua_disallowed_reaper_call:TrackFX_SetParam" in audit["blockers"]
    assert "lua_disallowed_reaper_call:SaveProject" in audit["blockers"]
    assert audit["safe_for_operator_runtime_collection"] is False


def test_reaper_runtime_collector_safety_audit_cli_require_passed(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    build_good_collector(out)
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/run_reaper_runtime_collector_safety_audit.py"),
            "--project-name",
            "unit",
            "--output-dir",
            str(out),
            "--require-passed",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    data = json.loads(result.stdout)
    assert result.returncode == 0
    assert data["passed"] is True
    assert data["safe_for_operator_runtime_collection"] is True


def test_report_index_groups_reaper_runtime_collector_safety_audit(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    build_good_collector(out)
    build_reaper_runtime_collector_safety_audit(project_name="unit", output_dir=out)
    index = build_report_index(project_name="unit", output_dir=out, stage_results=[])
    assert any(
        item["stage"] == "plugin intelligence" and item["summary"] == "reaper_runtime_collector_safety_audit.json"
        for item in index["reports"]
    )


def test_requirements_traceability_includes_reaper_runtime_collector_safety_audit(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    audit = build_requirements_traceability_audit(project_name="unit", output_dir=out, workspace_root=ROOT)
    req09 = next(item for item in audit["requirement_results"] if item["id"] == "REQ-09")
    rels = {item["relative_path"] for item in req09["files"]}
    assert "automix/plugins/reaper_runtime_collector_safety_audit.py" in rels
    assert "scripts/run_reaper_runtime_collector_safety_audit.py" in rels
    assert "tests/test_reaper_runtime_collector_safety_audit.py" in rels
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
    print("REAPER runtime collector safety audit direct tests passed")

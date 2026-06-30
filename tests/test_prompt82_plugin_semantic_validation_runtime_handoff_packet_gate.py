from __future__ import annotations

import json
import subprocess
import sys
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
from automix.plugins.plugin_semantic_validation_runtime_handoff_packet_gate import (
    PLUGIN_SEMANTIC_VALIDATION_RUNTIME_HANDOFF_PACKET_GATE_SCHEMA,
    build_plugin_semantic_validation_runtime_handoff_packet_gate,
)
from automix.plugins.reaper_runtime_collection_operator_readiness_gate import (
    build_reaper_runtime_collection_operator_readiness_gate,
)
from automix.plugins.reaper_runtime_collector_safety_audit import build_reaper_runtime_collector_safety_audit


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


def write_local_device_qc(out: Path, *, ready: bool = True) -> None:
    write_json(
        out / "eval_reports/local_device_qc.json",
        {
            "schema": "automix-local-device-qc-v1",
            "status": "local_device_qc_ready" if ready else "local_device_qc_blocked",
            "passed": ready,
            "readiness": {
                "local_device_qc_ready": ready,
                "ready_for_reaper_runtime_collection": ready,
                "ready_for_applied_parameter_writes": False,
                "ready_for_delivery_claims": False,
                "report_only": True,
                "opens_reaper": False,
                "renders_audio": False,
                "writes_parameters": False,
                "saves_project": False,
            },
            "blockers": [] if ready else ["local_device_qc_fixture_blocked"],
            "warnings": [],
        },
    )


def write_queue(out: Path, *, blocked: bool = True) -> None:
    blocked_jobs = [{"plugin_name": "OTT (Xfer Records)", "blockers": ["availability_decision_missing:OTT (Xfer Records)"]}] if blocked else []
    write_json(
        out / "eval_reports/plugin_semantic_validation_queue.json",
        {
            "schema": "automix-plugin-semantic-validation-queue-v1",
            "project_name": "unit",
            "queue_jobs_total": 2,
            "blocked_jobs_total": len(blocked_jobs),
            "ready_to_run_reaper_collection": True,
            "requires_reaper_runtime": True,
            "requires_operator_review": True,
            "safe_to_write_parameters": False,
            "queue_jobs": [
                queue_job("ReaEQ (Cockos)", "semantic_validation_01_reaeq_cockos"),
                queue_job("ReaComp (Cockos)", "semantic_validation_02_reacomp_cockos"),
            ],
            "blocked_jobs": blocked_jobs,
            "blockers": [f"collection_job_blocked:{item['plugin_name']}:{item['blockers'][0]}" for item in blocked_jobs],
            "warnings": [],
        },
    )


def write_availability_decision(out: Path, *, ready: bool, missing: list[str] | None = None) -> None:
    missing = missing or []
    write_json(
        out / "eval_reports/plugin_availability_decision_gate.json",
        {
            "schema": "automix-plugin-availability-decision-gate-v1",
            "status": "operator_decisions_ready" if ready else "operator_decision_manifest_missing",
            "availability_decisions_ready": ready,
            "required_decisions_total": len(missing),
            "missing_decisions": missing,
            "safe_to_write_parameters": False,
            "blockers": [] if ready else [f"operator_decision_missing:{item}" for item in missing],
            "warnings": [],
        },
    )


def write_runtime_evidence_gate(out: Path) -> None:
    write_json(
        out / "eval_reports/plugin_semantic_validation_runtime_evidence_gate.json",
        {
            "schema": "automix-plugin-semantic-validation-runtime-evidence-gate-v1",
            "status": "runtime_manifest_missing",
            "runtime_evidence_ready": False,
            "safe_to_write_parameters": False,
            "blockers": ["plugin_semantic_validation_runtime_manifest_missing"],
            "warnings": [],
        },
    )


def build_packet_inputs(out: Path, *, blocked: bool = True, local_ready: bool = True) -> None:
    write_local_device_qc(out, ready=local_ready)
    write_queue(out, blocked=blocked)
    build_plugin_semantic_validation_runtime_collection_package(project_name="unit", output_dir=out)
    build_plugin_semantic_validation_runtime_collector_package(project_name="unit", output_dir=out)
    build_reaper_runtime_collector_safety_audit(project_name="unit", output_dir=out)
    write_availability_decision(out, ready=not blocked, missing=["OTT (Xfer Records)"] if blocked else [])
    build_reaper_runtime_collection_operator_readiness_gate(project_name="unit", output_dir=out)
    write_runtime_evidence_gate(out)


def test_runtime_handoff_packet_gate_passes_partial_ready_with_blocked_unavailable_decisions(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    build_packet_inputs(out, blocked=True)

    gate = build_plugin_semantic_validation_runtime_handoff_packet_gate(project_name="unit", output_dir=out)

    assert gate["schema"] == PLUGIN_SEMANTIC_VALIDATION_RUNTIME_HANDOFF_PACKET_GATE_SCHEMA
    assert gate["status"] == "partial_operator_runtime_handoff_packet_ready"
    assert gate["passed"] is True
    assert gate["readiness"]["operator_runtime_handoff_packet_ready"] is True
    assert gate["readiness"]["complete_operator_runtime_handoff_packet_ready"] is False
    assert gate["readiness"]["safe_to_run_lua_collector"] is True
    assert gate["readiness"]["safe_to_write_parameters"] is False
    assert gate["readiness"]["creates_validation_reports"] is False
    assert gate["counts"]["handoff_jobs_ready_total"] == 2
    assert "blocked_unavailable_queue_jobs_remain:1" in gate["warnings"]
    assert "availability_operator_decisions_missing:1" in gate["warnings"]
    assert all(item["exists"] for item in gate["required_operator_artifacts"])
    assert all(job["status"] == "handoff_job_ready" for job in gate["job_results"])
    assert (out / "eval_reports/plugin_semantic_validation_runtime_handoff_packet_gate.json").exists()
    assert (out / "eval_reports/plugin_semantic_validation_runtime_handoff_packet_gate.md").exists()


def test_runtime_handoff_packet_gate_marks_complete_ready_when_no_blocked_decisions(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    build_packet_inputs(out, blocked=False)

    gate = build_plugin_semantic_validation_runtime_handoff_packet_gate(project_name="unit", output_dir=out)

    assert gate["status"] == "complete_operator_runtime_handoff_packet_ready"
    assert gate["readiness"]["operator_runtime_handoff_packet_ready"] is True
    assert gate["readiness"]["complete_operator_runtime_handoff_packet_ready"] is True
    assert gate["warnings"] == []


def test_runtime_handoff_packet_gate_blocks_missing_operator_runbook(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    build_packet_inputs(out, blocked=False)
    package_path = out / "eval_reports/plugin_semantic_validation_runtime_collector_package.json"
    package = json.loads(package_path.read_text(encoding="utf-8"))
    runbook = out / "review/plugin_semantic_validation_runtime_collector_operator_runbook.md"
    runbook.unlink()
    write_json(package_path, package)

    gate = build_plugin_semantic_validation_runtime_handoff_packet_gate(project_name="unit", output_dir=out)

    assert gate["status"] == "operator_runtime_handoff_packet_blocked"
    assert "required_operator_file_missing:operator_runbook_path" in gate["blockers"]


def test_runtime_handoff_packet_gate_blocks_template_that_claims_success(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    build_packet_inputs(out, blocked=False)
    template = next((out / "review/plugin_semantic_validation_runtime_report_templates").glob("*_validation_report_template.json"))
    data = json.loads(template.read_text(encoding="utf-8"))
    data["status"] = "passed"
    data["safe_for_automix"] = True
    data["no_fake_success"] = True
    write_json(template, data)

    gate = build_plugin_semantic_validation_runtime_handoff_packet_gate(project_name="unit", output_dir=out)

    assert gate["passed"] is False
    assert any("report_template_template_safe_for_automix_must_be_false" in blocker for blocker in gate["blockers"])
    assert any("report_template_template_status_must_not_claim_runtime_observed" in blocker for blocker in gate["blockers"])


def test_runtime_handoff_packet_gate_cli_require_modes(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    build_packet_inputs(out, blocked=True)

    partial = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/run_plugin_semantic_validation_runtime_handoff_packet_gate.py"),
            "--project-name",
            "unit",
            "--output-dir",
            str(out),
            "--require-partial-ready",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    complete = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/run_plugin_semantic_validation_runtime_handoff_packet_gate.py"),
            "--project-name",
            "unit",
            "--output-dir",
            str(out),
            "--require-complete-ready",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    partial_data = json.loads(partial.stdout)
    complete_data = json.loads(complete.stdout)

    assert partial.returncode == 0
    assert partial_data["readiness"]["operator_runtime_handoff_packet_ready"] is True
    assert complete.returncode == 2
    assert complete_data["readiness"]["complete_operator_runtime_handoff_packet_ready"] is False


def test_report_index_groups_runtime_handoff_packet_gate(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    build_packet_inputs(out, blocked=True)
    build_plugin_semantic_validation_runtime_handoff_packet_gate(project_name="unit", output_dir=out)

    index = build_report_index(project_name="unit", output_dir=out, stage_results=[])

    assert any(
        item["stage"] == "plugin intelligence"
        and item["summary"] == "plugin_semantic_validation_runtime_handoff_packet_gate.json"
        for item in index["reports"]
    )


def test_requirements_traceability_includes_runtime_handoff_packet_gate(tmp_path: Path) -> None:
    audit = build_requirements_traceability_audit(project_name="unit", output_dir=tmp_path / "automix", workspace_root=ROOT)
    req09 = next(item for item in audit["requirement_results"] if item["id"] == "REQ-09")
    rels = {item["relative_path"] for item in req09["files"]}

    assert "automix/plugins/plugin_semantic_validation_runtime_handoff_packet_gate.py" in rels
    assert "scripts/run_plugin_semantic_validation_runtime_handoff_packet_gate.py" in rels
    assert "tests/test_prompt82_plugin_semantic_validation_runtime_handoff_packet_gate.py" in rels

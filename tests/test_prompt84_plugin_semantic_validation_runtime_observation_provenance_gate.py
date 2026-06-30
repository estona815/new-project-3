from __future__ import annotations

import hashlib
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
from automix.plugins.plugin_adapter_schema import now_utc, write_json
from automix.plugins.plugin_semantic_validation_runtime_collection_package import (
    build_plugin_semantic_validation_runtime_collection_package,
)
from automix.plugins.plugin_semantic_validation_runtime_collector_package import (
    RUNTIME_OBSERVATION_SCHEMA,
    build_plugin_semantic_validation_runtime_collector_package,
)
from automix.plugins.plugin_semantic_validation_runtime_handoff_packet_gate import (
    build_plugin_semantic_validation_runtime_handoff_packet_gate,
)
from automix.plugins.plugin_semantic_validation_runtime_observation_gate import (
    build_plugin_semantic_validation_runtime_observation_gate,
)
from automix.plugins.plugin_semantic_validation_runtime_observation_provenance_gate import (
    PLUGIN_SEMANTIC_VALIDATION_RUNTIME_OBSERVATION_PROVENANCE_GATE_SCHEMA,
    build_plugin_semantic_validation_runtime_observation_provenance_gate,
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


def write_availability_decision(out: Path, *, ready: bool) -> None:
    missing = [] if ready else ["OTT (Xfer Records)"]
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


def build_packet_inputs(out: Path, *, blocked: bool = True) -> dict:
    write_local_device_qc(out, ready=True)
    write_queue(out, blocked=blocked)
    build_plugin_semantic_validation_runtime_collection_package(project_name="unit", output_dir=out)
    package = build_plugin_semantic_validation_runtime_collector_package(project_name="unit", output_dir=out)
    build_reaper_runtime_collector_safety_audit(project_name="unit", output_dir=out)
    write_availability_decision(out, ready=not blocked)
    build_reaper_runtime_collection_operator_readiness_gate(project_name="unit", output_dir=out)
    write_runtime_evidence_gate(out)
    build_plugin_semantic_validation_runtime_handoff_packet_gate(project_name="unit", output_dir=out)
    build_plugin_semantic_validation_runtime_observation_gate(project_name="unit", output_dir=out)
    return package


def sha256(path: Path | str) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def observation_hashes(out: Path, package: dict) -> dict[str, str]:
    return {
        "queue_payload_sha256": sha256(package["queue_payload_path"]),
        "observation_template_sha256": sha256(package["observation_template_path"]),
        "collector_package_sha256": sha256(out / "eval_reports/plugin_semantic_validation_runtime_collector_package.json"),
        "local_device_qc_sha256": sha256(out / "eval_reports/local_device_qc.json"),
        "safety_audit_sha256": sha256(out / "eval_reports/reaper_runtime_collector_safety_audit.json"),
    }


def write_runtime_observation(
    out: Path,
    package: dict,
    job: dict,
    *,
    script_version: str = "prompt78-runtime-collector-v1",
    hash_overrides: dict[str, str] | None = None,
) -> None:
    hashes = observation_hashes(out, package)
    hashes.update(hash_overrides or {})
    write_json(
        Path(job["raw_observation_output_path"]),
        {
            "schema": RUNTIME_OBSERVATION_SCHEMA,
            "script_version": script_version,
            "project_name": "unit",
            "job_id": job["job_id"],
            "plugin_name": job["plugin_name"],
            "target_report_path": job["target_report_path"],
            "raw_observation_output_path": job["raw_observation_output_path"],
            "queue_payload_path": package["queue_payload_path"],
            "created_at_utc": now_utc(),
            "actual_fx_name": f"VST: {job['plugin_name']}",
            "status": "raw_observation_collected",
            "safe_to_write_parameters": False,
            "creates_validation_reports": False,
            "writes_parameters": False,
            "renders_audio": False,
            "saves_project": False,
            "temporary_muted_probe_track_used": True,
            "temporary_muted_probe_track_deleted": True,
            "parameter_indexes_assumed": False,
            "add_result": {"inserted": True, "returned_index": 0},
            "param_count": 2,
            "parameters": [
                {"index": 0, "name": "Frequency", "write_allowed": False, "semantic_validated": False},
                {"index": 1, "name": "Gain", "write_allowed": False, "semantic_validated": False},
            ],
            "errors": [],
            "warnings": [],
            **hashes,
        },
    )


def write_all_observations(out: Path, package: dict, *, first_script_version: str | None = None, first_hash_overrides: dict[str, str] | None = None) -> None:
    for index, job in enumerate(package["collector_jobs"]):
        write_runtime_observation(
            out,
            package,
            job,
            script_version=first_script_version or "prompt78-runtime-collector-v1" if index == 0 else "prompt78-runtime-collector-v1",
            hash_overrides=first_hash_overrides if index == 0 else None,
        )


def test_observation_provenance_gate_passes_packet_when_runtime_observations_are_pending(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    build_packet_inputs(out, blocked=True)

    gate = build_plugin_semantic_validation_runtime_observation_provenance_gate(project_name="unit", output_dir=out)

    assert gate["schema"] == PLUGIN_SEMANTIC_VALIDATION_RUNTIME_OBSERVATION_PROVENANCE_GATE_SCHEMA
    assert gate["status"] == "runtime_observation_provenance_pending_observations"
    assert gate["passed"] is True
    assert gate["readiness"]["expected_observation_provenance_packet_ready"] is True
    assert gate["readiness"]["observed_runtime_provenance_ready"] is False
    assert gate["readiness"]["ready_for_manual_report_authoring"] is False
    assert gate["readiness"]["safe_to_write_parameters"] is False
    assert gate["counts"]["observations_missing_total"] == 2
    assert gate["blockers"] == []
    assert "runtime_observation_files_missing:2" in gate["warnings"]


def test_observation_provenance_gate_verifies_fresh_runtime_observations(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    package = build_packet_inputs(out, blocked=False)
    write_all_observations(out, package)
    build_plugin_semantic_validation_runtime_observation_gate(project_name="unit", output_dir=out)

    gate = build_plugin_semantic_validation_runtime_observation_provenance_gate(project_name="unit", output_dir=out)

    assert gate["status"] == "runtime_observation_provenance_ready_for_authoring"
    assert gate["passed"] is True
    assert gate["readiness"]["observed_runtime_provenance_ready"] is True
    assert gate["readiness"]["ready_for_manual_report_authoring"] is True
    assert gate["counts"]["observations_provenance_verified_total"] == 2
    assert gate["blockers"] == []


def test_observation_provenance_gate_blocks_script_version_mismatch(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    package = build_packet_inputs(out, blocked=False)
    write_all_observations(out, package, first_script_version="stale-public-pc-script")
    build_plugin_semantic_validation_runtime_observation_gate(project_name="unit", output_dir=out)

    gate = build_plugin_semantic_validation_runtime_observation_provenance_gate(project_name="unit", output_dir=out)

    assert gate["status"] == "runtime_observation_provenance_blocked"
    assert gate["passed"] is False
    assert any("runtime_observation_script_version_mismatch" in blocker for blocker in gate["blockers"])


def test_observation_provenance_gate_blocks_optional_hash_mismatch_when_present(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    package = build_packet_inputs(out, blocked=False)
    write_all_observations(out, package, first_hash_overrides={"queue_payload_sha256": "0" * 64})
    build_plugin_semantic_validation_runtime_observation_gate(project_name="unit", output_dir=out)

    gate = build_plugin_semantic_validation_runtime_observation_provenance_gate(project_name="unit", output_dir=out)

    assert gate["passed"] is False
    assert any("runtime_observation_hash_mismatch:queue_payload_sha256" in blocker for blocker in gate["blockers"])


def test_observation_provenance_gate_cli_require_modes(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    build_packet_inputs(out, blocked=True)

    packet_ready = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/run_plugin_semantic_validation_runtime_observation_provenance_gate.py"),
            "--project-name",
            "unit",
            "--output-dir",
            str(out),
            "--require-packet-ready",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    observed_ready = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/run_plugin_semantic_validation_runtime_observation_provenance_gate.py"),
            "--project-name",
            "unit",
            "--output-dir",
            str(out),
            "--require-observed-ready",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    packet_data = json.loads(packet_ready.stdout)
    observed_data = json.loads(observed_ready.stdout)

    assert packet_ready.returncode == 0
    assert packet_data["readiness"]["expected_observation_provenance_packet_ready"] is True
    assert observed_ready.returncode == 2
    assert observed_data["readiness"]["observed_runtime_provenance_ready"] is False


def test_report_index_groups_observation_provenance_gate(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    build_packet_inputs(out, blocked=True)
    build_plugin_semantic_validation_runtime_observation_provenance_gate(project_name="unit", output_dir=out)

    index = build_report_index(project_name="unit", output_dir=out, stage_results=[])

    assert any(
        item["stage"] == "plugin intelligence"
        and item["summary"] == "plugin_semantic_validation_runtime_observation_provenance_gate.json"
        for item in index["reports"]
    )


def test_risk_remediation_plan_recommends_observation_provenance_gate(tmp_path: Path) -> None:
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
                    "risk_id": "risk_plugin_runtime_observation_provenance",
                    "severity": "blocker",
                    "category": "plugin",
                    "source_report": "plugin_semantic_validation_runtime_observation_provenance_gate.json",
                    "code": "runtime_observation_hash_mismatch:queue_payload_sha256",
                    "summary": "runtime observation provenance mismatch",
                    "recommended_next_action": "semantic_validation_runtime",
                }
            ],
            "blockers": ["runtime_observation_hash_mismatch:queue_payload_sha256"],
            "warnings": [],
        },
    )

    plan = build_risk_remediation_plan(project_name="unit", output_dir=out)
    plugin_action = next(action for action in plan["actions"] if action["phase"] == "plugin_safety")

    assert any("run_plugin_semantic_validation_runtime_observation_provenance_gate.py" in command for command in plugin_action["recommended_commands"])
    assert "automix/eval_reports/plugin_semantic_validation_runtime_observation_provenance_gate.json" in plugin_action["evidence_to_collect"]


def test_requirements_traceability_includes_observation_provenance_gate(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    audit = build_requirements_traceability_audit(project_name="unit", output_dir=out, workspace_root=ROOT)
    req09 = next(item for item in audit["requirement_results"] if item["id"] == "REQ-09")
    rels = {item["relative_path"] for item in req09["files"]}

    assert "automix/plugins/plugin_semantic_validation_runtime_observation_provenance_gate.py" in rels
    assert "scripts/run_plugin_semantic_validation_runtime_observation_provenance_gate.py" in rels
    assert "tests/test_prompt84_plugin_semantic_validation_runtime_observation_provenance_gate.py" in rels
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
    print("Prompt84 direct tests passed")

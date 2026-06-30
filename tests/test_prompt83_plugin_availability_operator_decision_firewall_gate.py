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
from automix.plugins.plugin_availability_decision_gate import build_plugin_availability_decision_gate
from automix.plugins.plugin_availability_operator_decision_firewall_gate import (
    PLUGIN_AVAILABILITY_OPERATOR_DECISION_FIREWALL_GATE_SCHEMA,
    build_plugin_availability_operator_decision_firewall_gate,
)
from automix.plugins.plugin_availability_operator_decision_package import (
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
                },
            ],
            "warnings": ["operator_disable_or_install_decision_required"],
            "blockers": [],
        },
    )


def write_decision_gate_missing(out: Path) -> None:
    write_json(
        out / "eval_reports/plugin_availability_decision_gate.json",
        {
            "schema": "automix-plugin-availability-decision-gate-v1",
            "project_name": "unit",
            "status": "operator_decision_manifest_missing",
            "availability_decisions_ready": False,
            "ready_for_plugin_preflight_rerun": False,
            "safe_to_write_parameters": False,
            "required_decisions_total": 2,
            "missing_decisions": ["OTT (Xfer Records)", "TDR Nova (Tokyo Dawn Labs)"],
            "decisions": [],
            "blockers": [
                "operator_decision_missing:OTT (Xfer Records)",
                "operator_decision_missing:TDR Nova (Tokyo Dawn Labs)",
                "plugin_availability_decision_manifest_missing",
            ],
            "warnings": [],
        },
    )


def build_candidate_inputs(out: Path) -> None:
    write_resolution_plan(out)
    write_decision_gate_missing(out)
    build_plugin_availability_operator_decision_package(project_name="unit", output_dir=out)


def accepted_entry(plugin_name: str, fallback: str) -> dict:
    return {
        "plugin_name": plugin_name,
        "resolution": "disable_for_automatic_drafts",
        "fallback_candidate": fallback,
        "fallback_requires_validation": True,
        "automatic_parameter_writes_allowed": False,
        "operator_acknowledged": True,
    }


def write_accepted_manifest(out: Path, entries: list[dict], operator_decision_request_token: str = "test-token") -> Path:
    for entry in entries:
        entry["operator_decision_request_token"] = str(operator_decision_request_token)
    path = out / "review/plugin_availability_disable_manifest.json"
    write_json(
        path,
        {
            "schema": "automix-plugin-availability-disable-manifest-v1",
            "operator_decision_request_token": str(operator_decision_request_token),
            "disabled_plugins": entries,
            "operator_acknowledgement_required": True,
        },
    )
    return path


def test_operator_decision_firewall_passes_candidate_pending_acknowledgement(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    build_candidate_inputs(out)

    gate = build_plugin_availability_operator_decision_firewall_gate(project_name="unit", output_dir=out)

    assert gate["schema"] == PLUGIN_AVAILABILITY_OPERATOR_DECISION_FIREWALL_GATE_SCHEMA
    assert gate["status"] == "operator_decision_candidate_firewalled_pending_acknowledgement"
    assert gate["passed"] is True
    assert gate["readiness"]["candidate_manifest_firewalled_from_accepted_evidence"] is True
    assert gate["readiness"]["candidate_counts_as_accepted_operator_evidence"] is False
    assert gate["readiness"]["accepted_operator_manifest_ready"] is False
    assert gate["readiness"]["safe_to_write_parameters"] is False
    assert gate["counts"]["required_decisions_total"] == 2
    assert "accepted_operator_decision_manifest_missing:2" in gate["warnings"]
    assert all(item["operator_acknowledged"] is False for item in gate["candidate_entries"])


def test_operator_decision_firewall_blocks_candidate_copied_to_accepted_manifest_path(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    build_candidate_inputs(out)
    candidate = json.loads((out / "review/plugin_availability_disable_manifest_candidate.json").read_text(encoding="utf-8"))
    write_json(out / "review/plugin_availability_disable_manifest.json", candidate)

    gate = build_plugin_availability_operator_decision_firewall_gate(project_name="unit", output_dir=out)

    assert gate["passed"] is False
    assert "accepted_operator_decision_manifest_is_candidate" in gate["blockers"]


def test_operator_decision_firewall_accepts_real_manifest_after_decision_gate_ready(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    build_candidate_inputs(out)
    from automix.plugins.plugin_availability_operator_decision_package import build_plugin_availability_operator_decision_package

    write_accepted_manifest(
        out,
        [
            accepted_entry("OTT (Xfer Records)", "ReaXcomp"),
            accepted_entry("TDR Nova (Tokyo Dawn Labs)", "ReaEQ plus ReaXcomp"),
        ],
        operator_decision_request_token="test-token",
    )
    build_plugin_availability_decision_gate(project_name="unit", output_dir=out)
    build_plugin_availability_operator_decision_package(project_name="unit", output_dir=out)
    package = json.loads((out / "eval_reports/plugin_availability_operator_decision_package.json").read_text(encoding="utf-8"))
    token = package.get("operator_decision_request_token", "test-token")
    write_accepted_manifest(
        out,
        [
            accepted_entry("OTT (Xfer Records)", "ReaXcomp"),
            accepted_entry("TDR Nova (Tokyo Dawn Labs)", "ReaEQ plus ReaXcomp"),
        ],
        operator_decision_request_token=token,
    )

    gate = build_plugin_availability_operator_decision_firewall_gate(project_name="unit", output_dir=out)

    assert gate["status"] == "accepted_operator_decision_manifest_firewalled"
    assert gate["passed"] is True
    assert gate["readiness"]["accepted_operator_manifest_ready"] is True
    assert gate["readiness"]["availability_decisions_ready"] is True
    assert gate["readiness"]["safe_to_write_parameters"] is False
    assert gate["counts"]["accepted_decisions_total"] == 2


def test_operator_decision_firewall_blocks_accepted_manifest_before_decision_gate_accepts_it(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    build_candidate_inputs(out)
    write_accepted_manifest(out, [accepted_entry("OTT (Xfer Records)", "ReaXcomp")])

    gate = build_plugin_availability_operator_decision_firewall_gate(project_name="unit", output_dir=out)

    assert gate["passed"] is False
    assert "accepted_decision_missing:TDR Nova (Tokyo Dawn Labs)" in gate["blockers"]
    assert "accepted_manifest_not_accepted_by_decision_gate" in gate["blockers"]


def test_operator_decision_firewall_blocks_candidate_that_claims_acknowledgement_or_writes(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    build_candidate_inputs(out)
    path = out / "review/plugin_availability_disable_manifest_candidate.json"
    candidate = json.loads(path.read_text(encoding="utf-8"))
    candidate["safe_to_write_parameters"] = True
    candidate["disabled_plugins"][0]["operator_acknowledged"] = True
    candidate["disabled_plugins"][0]["automatic_parameter_writes_allowed"] = True
    write_json(path, candidate)

    gate = build_plugin_availability_operator_decision_firewall_gate(project_name="unit", output_dir=out)

    assert gate["passed"] is False
    assert "operator_decision_candidate_safe_to_write_parameters_must_be_false" in gate["blockers"]
    assert "candidate_operator_acknowledgement_must_be_false:OTT (Xfer Records)" in gate["blockers"]
    assert "candidate_automatic_parameter_writes_must_be_false:OTT (Xfer Records)" in gate["blockers"]


def test_operator_decision_firewall_cli_require_modes(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    build_candidate_inputs(out)

    passed = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/run_plugin_availability_operator_decision_firewall_gate.py"),
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
    accepted = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/run_plugin_availability_operator_decision_firewall_gate.py"),
            "--project-name",
            "unit",
            "--output-dir",
            str(out),
            "--require-accepted-ready",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    passed_data = json.loads(passed.stdout)
    accepted_data = json.loads(accepted.stdout)

    assert passed.returncode == 0
    assert passed_data["readiness"]["candidate_manifest_firewalled_from_accepted_evidence"] is True
    assert accepted.returncode == 2
    assert accepted_data["readiness"]["accepted_operator_manifest_ready"] is False


def test_report_index_groups_operator_decision_firewall_gate(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    build_candidate_inputs(out)
    build_plugin_availability_operator_decision_firewall_gate(project_name="unit", output_dir=out)

    index = build_report_index(project_name="unit", output_dir=out, stage_results=[])

    assert any(
        item["stage"] == "plugin intelligence"
        and item["summary"] == "plugin_availability_operator_decision_firewall_gate.json"
        for item in index["reports"]
    )


def test_requirements_traceability_includes_operator_decision_firewall_gate(tmp_path: Path) -> None:
    audit = build_requirements_traceability_audit(project_name="unit", output_dir=tmp_path / "automix", workspace_root=ROOT)
    req09 = next(item for item in audit["requirement_results"] if item["id"] == "REQ-09")
    rels = {item["relative_path"] for item in req09["files"]}

    assert "automix/plugins/plugin_availability_operator_decision_firewall_gate.py" in rels
    assert "scripts/run_plugin_availability_operator_decision_firewall_gate.py" in rels
    assert "tests/test_prompt83_plugin_availability_operator_decision_firewall_gate.py" in rels

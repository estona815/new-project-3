from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from automix.harness.public_pc_legacy_semantic_firewall_gate import (
    build_public_pc_legacy_semantic_firewall_gate,
)
from automix.orchestrator.report_index import build_report_index
from automix.plugins.plugin_adapter_schema import write_json


def legacy_record(
    rel: str,
    *,
    path: str | None = None,
    sha256: str = "",
    calls: list[str] | None = None,
    parameter_write: bool = False,
    mutation: bool = False,
) -> dict:
    direct_merge_blockers = [
        "legacy_runtime_code_requires_manual_review",
        "current_fail_closed_gates_must_remain_authoritative",
    ]
    if calls:
        direct_merge_blockers.append("legacy_lua_contains_disallowed_runtime_mutation_calls")
    if parameter_write:
        direct_merge_blockers.append("legacy_lua_contains_parameter_write_calls")
    if mutation:
        direct_merge_blockers.append("legacy_lua_mutates_project_structure")
    return {
        "relative_path": rel,
        "path": path or f"/tmp/public-pc/reaper-auto-mix/{rel}",
        "exists": True,
        "sha256": sha256,
        "eligible_as_read_only_fixture": True,
        "safe_to_merge_runtime_code": False,
        "safe_to_execute_in_user_project": False,
        "safe_to_use_for_delivery_claims": False,
        "direct_merge_blockers": direct_merge_blockers,
        "disallowed_reaper_calls": calls or [],
        "contains_parameter_writes": parameter_write,
        "contains_media_import_or_track_creation": mutation,
        "contains_render_or_save_setup": False,
        "secret_markers": [],
    }


def write_plan(out: Path, records: list[dict], *, passed: bool = True) -> None:
    write_json(
        out / "eval_reports/public_pc_legacy_fixture_plan.json",
        {
            "schema": "automix-public-pc-legacy-fixture-plan-v1",
            "project_name": "unit",
            "passed": passed,
            "summary": {
                "unique_disallowed_reaper_calls": sorted(
                    {call for record in records for call in record.get("disallowed_reaper_calls", [])}
                )
            },
            "fixture_groups": [
                {
                    "id": "legacy_reaper_lua_safety_fixtures",
                    "fixture_role": "reaper_api_safety_regression",
                    "files": records,
                }
            ],
            "blockers": [] if passed else ["fixture_plan_blocked"],
            "warnings": [],
        },
    )


def write_api_gate(out: Path, *, passed: bool = True) -> None:
    write_json(
        out / "eval_reports/public_pc_legacy_api_regression_gate.json",
        {
            "schema": "automix-public-pc-legacy-api-regression-gate-v1",
            "project_name": "unit",
            "status": "legacy_api_regression_covered" if passed else "legacy_api_regression_blocked",
            "passed": passed,
            "readiness": {
                "legacy_api_regression_covered": passed,
                "ready_to_use_negative_safety_fixtures": passed,
                "safe_to_write_parameters": False,
                "safe_to_claim_final_audio_or_delivery": False,
                "report_only": True,
            },
            "blockers": [] if passed else ["legacy_disallowed_call_not_in_current_policy:FutureCall"],
            "warnings": [],
        },
    )


def write_clean_semantic_gate(out: Path) -> None:
    write_json(
        out / "eval_reports/plugin_semantic_validation_gate.json",
        {
            "schema": "automix-plugin-semantic-validation-gate-v1",
            "project_name": "unit",
            "semantic_validation_ready": False,
            "validation_reports_total": 0,
            "plugin_results": [],
            "blockers": ["semantic_validation_reports_missing"],
        },
    )


def test_public_pc_legacy_semantic_firewall_passes_when_semantic_reports_do_not_reference_legacy(
    tmp_path: Path,
) -> None:
    out = tmp_path / "automix"
    write_plan(out, [legacy_record("scripts/plugin_registry.lua", calls=["TrackFX_SetParam"], parameter_write=True)])
    write_api_gate(out)
    write_clean_semantic_gate(out)

    gate = build_public_pc_legacy_semantic_firewall_gate(project_name="unit", output_dir=out)

    assert gate["passed"] is True
    assert gate["status"] == "legacy_semantic_firewall_clear"
    assert gate["readiness"]["legacy_fixtures_firewalled_from_semantic_validation"] is True
    assert gate["readiness"]["legacy_fixtures_count_as_validation_evidence"] is False
    assert gate["readiness"]["safe_to_write_parameters"] is False
    assert gate["coverage"]["legacy_semantic_references"] == []


def test_public_pc_legacy_semantic_firewall_blocks_legacy_path_inside_semantic_gate(
    tmp_path: Path,
) -> None:
    out = tmp_path / "automix"
    legacy_path = str(tmp_path / "bundle/source_workspaces/tttt/reaper-auto-mix/scripts/plugin_registry.lua")
    write_plan(out, [legacy_record("scripts/plugin_registry.lua", path=legacy_path, calls=["TrackFX_SetParam"], parameter_write=True)])
    write_api_gate(out)
    write_json(
        out / "eval_reports/plugin_semantic_validation_gate.json",
        {
            "schema": "automix-plugin-semantic-validation-gate-v1",
            "project_name": "unit",
            "semantic_validation_ready": True,
            "plugin_results": [{"report_results": [{"path": legacy_path, "passed": True}]}],
        },
    )

    gate = build_public_pc_legacy_semantic_firewall_gate(project_name="unit", output_dir=out)

    assert gate["passed"] is False
    assert any(
        blocker.startswith(
            "legacy_path_referenced_by_semantic_validation_report:plugin_semantic_validation_gate.json:scripts/plugin_registry.lua"
        )
        for blocker in gate["blockers"]
    )
    assert "semantic_validation_ready_with_legacy_fixture_reference" in gate["blockers"]


def test_public_pc_legacy_semantic_firewall_blocks_when_api_regression_is_not_passed(
    tmp_path: Path,
) -> None:
    out = tmp_path / "automix"
    write_plan(out, [legacy_record("scripts/plugin_registry.lua", calls=["TrackFX_SetParam"], parameter_write=True)])
    write_api_gate(out, passed=False)
    write_clean_semantic_gate(out)

    gate = build_public_pc_legacy_semantic_firewall_gate(project_name="unit", output_dir=out)

    assert gate["passed"] is False
    assert "legacy_api_regression_gate_not_passed" in gate["blockers"]


def test_public_pc_legacy_semantic_firewall_blocks_legacy_hash_in_analysis_validation_reports(
    tmp_path: Path,
) -> None:
    out = tmp_path / "automix"
    content = b'{"schema":"legacy-recipe"}\n'
    digest = hashlib.sha256(content).hexdigest()
    write_plan(out, [legacy_record("recipes/json/target_mix_recipe.json", sha256=digest)])
    write_api_gate(out)
    write_clean_semantic_gate(out)
    validation_report = out / "analysis_reports/plugin_parameter_validation_reaeq.json"
    validation_report.parent.mkdir(parents=True, exist_ok=True)
    validation_report.write_bytes(content)

    gate = build_public_pc_legacy_semantic_firewall_gate(project_name="unit", output_dir=out)

    assert gate["passed"] is False
    assert (
        "legacy_fixture_hash_present_in_analysis_validation_reports:"
        "recipes/json/target_mix_recipe.json:plugin_parameter_validation_reaeq.json"
    ) in gate["blockers"]


def test_public_pc_legacy_semantic_firewall_cli_require_passed(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    write_plan(out, [legacy_record("scripts/plugin_registry.lua", calls=["TrackFX_SetParam"], parameter_write=True)])
    write_api_gate(out)
    write_clean_semantic_gate(out)

    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/run_public_pc_legacy_semantic_firewall_gate.py"),
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
    assert data["status"] == "legacy_semantic_firewall_clear"
    assert data["readiness"]["legacy_fixtures_count_as_validation_evidence"] is False
    assert Path(data["report_json"]).exists()


def test_report_index_groups_public_pc_legacy_semantic_firewall_gate(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    write_json(
        out / "eval_reports/public_pc_legacy_semantic_firewall_gate.json",
        {"schema": "automix-public-pc-legacy-semantic-firewall-gate-v1"},
    )

    index = build_report_index(project_name="unit", output_dir=out, stage_results=[])

    assert any(
        item["stage"] == "handoff evidence" and item["summary"] == "public_pc_legacy_semantic_firewall_gate.json"
        for item in index["reports"]
    )

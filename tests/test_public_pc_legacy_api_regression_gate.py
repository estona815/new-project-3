from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from automix.harness.public_pc_legacy_api_regression_gate import build_public_pc_legacy_api_regression_gate
from automix.orchestrator.report_index import build_report_index
from automix.plugins.plugin_adapter_schema import write_json
from automix.plugins.reaper_runtime_collector_safety_audit import DISALLOWED_REAPER_CALLS


def legacy_record(rel: str, *, calls: list[str] | None = None, parameter_write: bool = False) -> dict:
    direct_merge_blockers = [
        "legacy_runtime_code_requires_manual_review",
        "current_fail_closed_gates_must_remain_authoritative",
    ]
    if calls:
        direct_merge_blockers.append("legacy_lua_contains_disallowed_runtime_mutation_calls")
    if parameter_write:
        direct_merge_blockers.append("legacy_lua_contains_parameter_write_calls")
    return {
        "relative_path": rel,
        "exists": True,
        "eligible_as_read_only_fixture": True,
        "safe_to_merge_runtime_code": False,
        "safe_to_execute_in_user_project": False,
        "safe_to_use_for_delivery_claims": False,
        "direct_merge_blockers": direct_merge_blockers,
        "disallowed_reaper_calls": calls or [],
        "contains_parameter_writes": parameter_write,
        "contains_media_import_or_track_creation": False,
        "contains_render_or_save_setup": False,
        "secret_markers": [],
    }


def write_plan(out: Path, records: list[dict], *, passed: bool = True, calls: list[str] | None = None) -> None:
    write_json(
        out / "eval_reports/public_pc_legacy_fixture_plan.json",
        {
            "schema": "automix-public-pc-legacy-fixture-plan-v1",
            "project_name": "unit",
            "passed": passed,
            "summary": {
                "unique_disallowed_reaper_calls": calls if calls is not None else sorted({call for record in records for call in record.get("disallowed_reaper_calls", [])}),
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


def test_public_pc_legacy_api_regression_gate_passes_when_current_policy_covers_legacy_calls(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    write_plan(
        out,
        [
            legacy_record("scripts/plugin_registry.lua", calls=["TrackFX_SetParam"], parameter_write=True),
            legacy_record("scripts/fx_chain_builder.lua", calls=["TrackFX_SetEQParam"], parameter_write=True),
            legacy_record("scripts/render_setup.lua", calls=["GetSetProjectInfo_String"]),
        ],
    )

    gate = build_public_pc_legacy_api_regression_gate(project_name="unit", output_dir=out)

    assert gate["passed"] is True
    assert gate["status"] == "legacy_api_regression_covered"
    assert gate["readiness"]["ready_to_use_negative_safety_fixtures"] is True
    assert gate["readiness"]["safe_to_merge_legacy_runtime_code"] is False
    assert gate["policy"]["uncovered_policy_calls"] == []
    assert "TrackFX_SetEQParam" in gate["policy"]["current_disallowed_reaper_calls"]
    assert "legacy_parameter_write_records:2" in gate["warnings"]


def test_public_pc_legacy_api_regression_gate_blocks_uncovered_legacy_call(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    write_plan(out, [legacy_record("scripts/new.lua", calls=["TrackFX_SetParam"])], calls=["TrackFX_SetParam", "FutureUnsafeCall"])

    gate = build_public_pc_legacy_api_regression_gate(project_name="unit", output_dir=out)

    assert gate["passed"] is False
    assert "legacy_disallowed_call_not_in_current_policy:FutureUnsafeCall" in gate["blockers"]


def test_public_pc_legacy_api_regression_gate_blocks_unsafe_record_flags(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    record = legacy_record("scripts/plugin_registry.lua", calls=["TrackFX_SetParam"], parameter_write=True)
    record["safe_to_execute_in_user_project"] = True
    record["direct_merge_blockers"] = ["legacy_lua_contains_parameter_write_calls"]
    write_plan(out, [record])

    gate = build_public_pc_legacy_api_regression_gate(project_name="unit", output_dir=out)

    assert gate["passed"] is False
    assert "legacy_record_safe_to_execute_true:scripts/plugin_registry.lua" in gate["blockers"]
    assert "legacy_record_missing_required_direct_merge_blockers:scripts/plugin_registry.lua" in gate["blockers"]


def test_public_pc_legacy_api_regression_gate_cli_require_passed(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    write_plan(out, [legacy_record("scripts/plugin_registry.lua", calls=["TrackFX_SetParam"], parameter_write=True)])

    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/run_public_pc_legacy_api_regression_gate.py"),
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
    assert data["status"] == "legacy_api_regression_covered"
    assert data["readiness"]["safe_to_execute_legacy_lua_in_user_project"] is False


def test_report_index_groups_public_pc_legacy_api_regression_gate(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    write_json(out / "eval_reports/public_pc_legacy_api_regression_gate.json", {"schema": "automix-public-pc-legacy-api-regression-gate-v1"})

    index = build_report_index(project_name="unit", output_dir=out, stage_results=[])

    assert any(
        item["stage"] == "handoff evidence" and item["summary"] == "public_pc_legacy_api_regression_gate.json"
        for item in index["reports"]
    )


def test_reaper_runtime_collector_disallowed_policy_includes_eq_parameter_write_helpers() -> None:
    assert "TrackFX_SetEQParam" in DISALLOWED_REAPER_CALLS
    assert "TrackFX_SetEQBandEnabled" in DISALLOWED_REAPER_CALLS

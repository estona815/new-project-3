from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from automix.harness.public_pc_handoff_package_audit import build_public_pc_handoff_package_audit
from automix.harness.public_pc_legacy_fixture_plan import build_public_pc_legacy_fixture_plan
from automix.orchestrator.report_index import build_report_index
from automix.plugins.plugin_adapter_schema import write_json


def make_bundle(root: Path) -> Path:
    bundle = root / "bundle"
    reaper = bundle / "source_workspaces/tttt/reaper-auto-mix"
    (bundle / "source_workspaces/tttt/data/assets/audio").mkdir(parents=True)
    (bundle / "README_FIRST.md").write_text("# transfer\n", encoding="utf-8")
    (bundle / "SCAN_AND_SCOPE_REPORT.md").write_text("# scope\n", encoding="utf-8")
    (bundle / "PACKAGE_MANIFEST.json").write_text(
        json.dumps(
            {
                "created_at": "2026-06-05T15:23:52",
                "bundle_root": r"C:\Users\user\Documents\리퍼\bundle",
                "included_source_file_count": 259,
                "excluded_source_file_count": 34,
                "collected_archive_count": 19,
            }
        ),
        encoding="utf-8-sig",
    )
    (bundle / "source_workspaces/tttt/data/assets/audio/phase1_sample.wav").write_bytes(b"RIFF")

    files = {
        "README.md": "fixture\n",
        "HANDOFF.md": "fixture\n",
        "PROJECT_STATE.md": "fixture\n",
        "NEXT_CODEX_PROMPT.md": "fixture\n",
        "RESTORE_ON_OTHER_COMPUTER.md": "fixture\n",
        "PACKAGE_WARNINGS.md": "fixture\n",
        "FINAL_DECISIONS.md": "fixture\n",
        "project_manifest.json": "{}\n",
        "review/handoff_validation_actual_targets_20260605.json": "{}\n",
        "review/handoff_validation_20260605.json": "{}\n",
        "review/red_team_report.md": "Major Issues\nTrackFX_SetParam remains a risk.\n",
        "review/mix_risk_report.md": "fixture\n",
        "review/api_risk_report.md": "fixture\n",
        "scripts/plugin_registry.lua": "reaper.TrackFX_SetParam(track, fx, 0, 0.5)\n",
        "scripts/apply_mix_recipe.lua": "reaper.CountTracks(0)\n",
        "scripts/fx_chain_builder.lua": "reaper.TrackFX_SetEQParam(track, fx, 0, 0, 0, 1000, false)\n",
        "scripts/render_setup.lua": "reaper.GetSetProjectInfo_String(0, 'RENDER_FILE', 'renders', true)\n",
        "scripts/routing_builder.lua": "reaper.CreateTrackSend(source, dest)\n",
        "scripts/utils.lua": "reaper.InsertMedia(path, 0)\n",
        "scripts/validate_project_routing.lua": "reaper.GetTrackNumSends(track, 0)\n",
        "scripts/import_and_mix_stems.lua": "reaper.InsertTrackAtIndex(0, false)\n",
        "scripts/apply_revision_actions.lua": "reaper.SetMediaTrackInfo_Value(track, 'D_VOL', 1)\n",
        "tools/validate_recipe.py": "print('ok')\n",
        "recipes/schemas/mix_recipe.schema.json": '{"type":"object"}\n',
        "recipes/schemas/qc_actions.schema.json": '{"type":"object"}\n',
        "recipes/schemas/arrangement_recipe.schema.json": '{"type":"object"}\n',
        "recipes/json/target_mix_recipe.json": '{"recipe_name":"unit"}\n',
        "recipes/json/default_target_arrangement_recipe.json": '{"arrangement":"unit"}\n',
        "recipes/lua/target_mix_recipe.lua": "return { recipe_name = 'unit' }\n",
    }
    for rel, content in files.items():
        path = reaper / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    return bundle


def test_public_pc_legacy_fixture_plan_keeps_legacy_code_read_only(tmp_path: Path) -> None:
    bundle = make_bundle(tmp_path)
    out = tmp_path / "automix"
    build_public_pc_handoff_package_audit(project_name="unit", output_dir=out, bundle_path=bundle)

    plan = build_public_pc_legacy_fixture_plan(project_name="unit", output_dir=out)

    assert plan["passed"] is True
    assert plan["status"] == "legacy_fixture_plan_ready"
    assert plan["readiness"]["ready_to_materialize_read_only_fixtures"] is True
    assert plan["readiness"]["safe_to_merge_legacy_runtime_code"] is False
    assert plan["readiness"]["safe_to_execute_legacy_lua_in_user_project"] is False
    assert plan["summary"]["eligible_read_only_fixture_files"] >= 20
    assert "TrackFX_SetParam" in plan["summary"]["unique_disallowed_reaper_calls"]
    registry = next(
        record
        for group in plan["fixture_groups"]
        for record in group["files"]
        if record["relative_path"] == "scripts/plugin_registry.lua"
    )
    assert registry["eligible_as_read_only_fixture"] is True
    assert registry["safe_to_merge_runtime_code"] is False
    assert "legacy_lua_contains_parameter_write_calls" in registry["direct_merge_blockers"]
    assert (out / "eval_reports/public_pc_legacy_fixture_plan.json").exists()
    assert (out / "eval_reports/public_pc_legacy_fixture_plan.md").exists()


def test_public_pc_legacy_fixture_plan_blocks_without_handoff_audit(tmp_path: Path) -> None:
    plan = build_public_pc_legacy_fixture_plan(
        project_name="unit",
        output_dir=tmp_path / "automix",
        bundle_path=tmp_path / "missing",
    )

    assert plan["passed"] is False
    assert "public_pc_handoff_package_audit_missing_or_invalid" in plan["blockers"]
    assert "reaper_auto_mix_root_missing" in plan["blockers"]


def test_public_pc_legacy_fixture_plan_blocks_high_confidence_credential_pattern(tmp_path: Path) -> None:
    bundle = make_bundle(tmp_path)
    out = tmp_path / "automix"
    build_public_pc_handoff_package_audit(project_name="unit", output_dir=out, bundle_path=bundle)
    secret_file = bundle / "source_workspaces/tttt/reaper-auto-mix/HANDOFF.md"
    secret_file.write_text("api_key = 'not_a_real_secret_value_12345'\n", encoding="utf-8")

    plan = build_public_pc_legacy_fixture_plan(project_name="unit", output_dir=out)

    assert plan["passed"] is False
    assert "high_confidence_credential_patterns_in_legacy_files:1" in plan["blockers"]
    assert "HANDOFF.md" in plan["summary"]["files_with_secret_markers"]


def test_public_pc_legacy_fixture_plan_cli_require_ready(tmp_path: Path) -> None:
    bundle = make_bundle(tmp_path)
    out = tmp_path / "automix"
    build_public_pc_handoff_package_audit(project_name="unit", output_dir=out, bundle_path=bundle)

    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/run_public_pc_legacy_fixture_plan.py"),
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

    assert result.returncode == 0
    assert data["status"] == "legacy_fixture_plan_ready"
    assert data["summary"]["eligible_read_only_fixture_files"] >= 20


def test_report_index_groups_public_pc_legacy_fixture_plan(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    write_json(out / "eval_reports/public_pc_legacy_fixture_plan.json", {"schema": "automix-public-pc-legacy-fixture-plan-v1"})

    index = build_report_index(project_name="unit", output_dir=out, stage_results=[])

    assert any(
        item["stage"] == "handoff evidence" and item["summary"] == "public_pc_legacy_fixture_plan.json"
        for item in index["reports"]
    )

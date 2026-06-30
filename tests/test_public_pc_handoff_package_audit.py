from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from automix.harness.public_pc_handoff_package_audit import build_public_pc_handoff_package_audit
from automix.orchestrator.report_index import build_report_index
from automix.plugins.plugin_adapter_schema import write_json


def make_handoff_bundle(root: Path, *, include_reaper_auto_mix: bool = True) -> Path:
    bundle = root / "REAPER_2222_FULL_PROJECT_20260605-152350"
    workspace = bundle / "source_workspaces" / "tttt"
    reaper = workspace / "reaper-auto-mix"
    bundle.mkdir(parents=True)
    (bundle / "README_FIRST.md").write_text("# REAPER 2222 Transfer Package\n", encoding="utf-8")
    (bundle / "SCAN_AND_SCOPE_REPORT.md").write_text("# Scope And Scan Report\n", encoding="utf-8")
    manifest = {
        "created_at": "2026-06-05T15:23:52",
        "bundle_root": r"C:\Users\user\Documents\리퍼\REAPER_2222_UPLOAD_READY_20260605-152350",
        "source_root": r"C:\Users\user\Documents\tttt",
        "included_source_file_count": 259,
        "excluded_source_file_count": 34,
        "collected_archive_count": 19,
    }
    (bundle / "PACKAGE_MANIFEST.json").write_text(json.dumps(manifest), encoding="utf-8-sig")
    (workspace / "data/assets/audio").mkdir(parents=True)
    (workspace / "data/assets/audio/phase1_sample.wav").write_bytes(b"RIFF")

    if not include_reaper_auto_mix:
        return bundle

    for rel in [
        "README.md",
        "HANDOFF.md",
        "PROJECT_STATE.md",
        "NEXT_CODEX_PROMPT.md",
        "project_manifest.json",
        "review/handoff_validation_actual_targets_20260605.json",
        "review/red_team_report.md",
        "review/mix_risk_report.md",
        "RESTORE_ON_OTHER_COMPUTER.md",
        "scripts/apply_mix_recipe.lua",
        "scripts/plugin_registry.lua",
        "scripts/validate_project_routing.lua",
        "tools/validate_recipe.py",
        "recipes/schemas/mix_recipe.schema.json",
        "recipes/schemas/qc_actions.schema.json",
        "recipes/json/target_mix_recipe.json",
    ]:
        path = reaper / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{}\n" if path.suffix == ".json" else "fixture\n", encoding="utf-8")
    return bundle


def test_public_pc_handoff_package_audit_finds_ready_development_inputs(tmp_path: Path) -> None:
    bundle = make_handoff_bundle(tmp_path)
    out = tmp_path / "automix"

    audit = build_public_pc_handoff_package_audit(project_name="unit", output_dir=out, bundle_path=bundle)

    assert audit["passed"] is True
    assert audit["status"] == "handoff_package_ready_for_targeted_development"
    assert audit["readiness"]["usable_for_development_planning"] is True
    assert audit["readiness"]["ready_for_targeted_fixture_import"] is True
    assert audit["readiness"]["safe_to_merge_code_without_review"] is False
    assert audit["readiness"]["usable_for_runtime_audio_qc"] is False
    assert "legacy_reaper_lua_as_regression_fixtures" in audit["ready_import_candidates"]
    assert "no_rpp_project_file_in_bundle" in audit["warnings"]
    assert "limited_audio_evidence_in_bundle" in audit["warnings"]
    assert "windows_origin_paths_detected" in audit["warnings"]
    assert (out / "eval_reports/public_pc_handoff_package_audit.json").exists()
    assert (out / "eval_reports/public_pc_handoff_package_audit.md").exists()


def test_public_pc_handoff_package_audit_blocks_missing_reaper_workspace(tmp_path: Path) -> None:
    bundle = make_handoff_bundle(tmp_path, include_reaper_auto_mix=False)

    audit = build_public_pc_handoff_package_audit(project_name="unit", output_dir=tmp_path / "automix", bundle_path=bundle)

    assert audit["passed"] is False
    assert "reaper_auto_mix_workspace_missing" in audit["blockers"]
    assert audit["readiness"]["ready_for_targeted_fixture_import"] is False


def test_public_pc_handoff_package_audit_cli_returns_nonzero_when_required_and_missing(tmp_path: Path) -> None:
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/run_public_pc_handoff_package_audit.py"),
            "--project-name",
            "unit",
            "--output-dir",
            str(tmp_path / "automix"),
            "--bundle-path",
            str(tmp_path / "missing"),
            "--require-ready",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    data = json.loads(result.stdout)

    assert result.returncode == 2
    assert data["status"] == "handoff_package_review_required"
    assert "bundle_path_missing_or_not_directory" in data["blockers"]


def test_report_index_groups_public_pc_handoff_package_audit(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    write_json(out / "eval_reports/public_pc_handoff_package_audit.json", {"schema": "automix-public-pc-handoff-package-audit-v1"})

    index = build_report_index(project_name="unit", output_dir=out, stage_results=[])

    assert any(
        item["stage"] == "handoff evidence" and item["summary"] == "public_pc_handoff_package_audit.json"
        for item in index["reports"]
    )

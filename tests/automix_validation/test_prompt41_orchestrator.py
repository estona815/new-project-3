from __future__ import annotations

import json
from pathlib import Path

from automix.orchestrator.automix_orchestrator import AutoMixOrchestrator
from automix.orchestrator.stage_status import StageStatus

from tests.automix_validation.prompt41_validation_common import MOCK_PROJECTS, ensure_prompt41_fixtures


def run_project(tmp_path: Path, project_name: str, **config) -> dict:
    ensure_prompt41_fixtures()
    out = tmp_path / "automix"
    orchestrator = AutoMixOrchestrator(
        {
            "project_path": str(MOCK_PROJECTS / project_name),
            "output_dir": str(out),
            **config,
        }
    )
    return orchestrator.run()


def statuses(manifest: dict) -> dict[str, str]:
    return {result["stage"]: result["status"] for result in manifest["stage_results"]}


def test_scan_only_mock_project_modifies_nothing_and_reports(tmp_path: Path) -> None:
    manifest = run_project(tmp_path, "prompt41_scan_only_test.json", mode="scan_only", dry_run=True)
    out = tmp_path / "automix"
    st = statuses(manifest)
    assert manifest["global_status"] == "scan_complete"
    assert st["vocal_recovery_draft"] == StageStatus.SKIPPED.value
    assert st["pitch_draft"] == StageStatus.SKIPPED.value
    assert st["final_export"] == StageStatus.SKIPPED.value
    assert (out / "orchestrator/automix_orchestration_manifest.json").exists()
    assert (out / "eval_reports/automix_orchestration_report.md").exists()
    assert (out / "eval_reports/automix_report_index.json").exists()
    assert manifest["safe_to_export"] is False


def test_safe_draft_blocks_unvalidated_plugin_mapping_and_keeps_rollback(tmp_path: Path) -> None:
    manifest = run_project(
        tmp_path,
        "prompt41_safe_draft_test.json",
        mode="safe_draft",
        allow_recovery_drafts=True,
        allow_pitch_correction=True,
        allow_placement_drafts=True,
        render_ab=True,
    )
    st = statuses(manifest)
    assert manifest["global_status"] == "blocked_plugin_mapping_required"
    assert st["pitch_draft"] == StageStatus.REQUIRES_PLUGIN_MAPPING.value
    assert st["vocal_recovery_draft"] == StageStatus.REQUIRES_PLUGIN_MAPPING.value
    assert (tmp_path / "automix/rollback/global_rollback_registry.json").exists()


def test_full_mix_mock_project_requires_stem_for_pitch(tmp_path: Path) -> None:
    manifest = run_project(tmp_path, "prompt41_full_mix_block_test.json", mode="safe_draft", allow_pitch_correction=True)
    st = statuses(manifest)
    assert st["pitch_triage"] == StageStatus.REQUIRES_STEM.value
    assert manifest["global_status"] in {"blocked_stem_required", "blocked_plugin_mapping_required", "blocked_safety_failure"}


def test_diagnostic_continue_keeps_analysis_but_no_drafts(tmp_path: Path) -> None:
    manifest = run_project(
        tmp_path,
        "prompt41_safe_draft_test.json",
        mode="diagnostic_continue",
        diagnostic_continue=True,
        allow_recovery_drafts=True,
        allow_placement_drafts=True,
        allow_final_export=True,
    )
    st = statuses(manifest)
    assert manifest["global_status"] == "scan_complete"
    assert st["vocal_recovery_analysis"] == StageStatus.PASSED_WITH_WARNINGS.value
    assert st["vocal_recovery_draft"] == StageStatus.SKIPPED.value
    assert st["final_export"] == StageStatus.SKIPPED.value

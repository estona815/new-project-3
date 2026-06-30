from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from automix.orchestrator.automix_orchestrator import AutoMixOrchestrator, load_orchestrator_config
from automix.orchestrator.global_rollback_registry import build_global_rollback_registry, validate_global_rollback_integrity
from automix.orchestrator.stage_dependency_graph import STAGE_ORDER, can_run_stage
from automix.orchestrator.stage_status import StageStatus
from automix.feedback.revision_memory import append_revision_memory


def run_orchestrator(tmp_path: Path, **overrides) -> dict:
    config = {"output_dir": str(tmp_path / "automix"), **overrides}
    orchestrator = AutoMixOrchestrator(config)
    return orchestrator.run()


def test_default_config_is_scan_only() -> None:
    config = load_orchestrator_config()
    assert config["mode"] == "scan_only"
    assert config["allow_final_export"] is False
    assert config["allow_full_mix_pitch_experiment"] is False


def test_scan_only_writes_manifest_report_index_qc_and_rollback(tmp_path: Path) -> None:
    manifest = run_orchestrator(tmp_path, mode="scan_only", dry_run=True)
    output = tmp_path / "automix"
    assert manifest["global_status"] == "scan_complete"
    assert manifest["safe_to_export"] is False
    assert len(manifest["stage_results"]) == len(STAGE_ORDER)
    assert (output / "orchestrator/automix_orchestration_manifest.json").exists()
    assert (output / "eval_reports/automix_orchestration_report.md").exists()
    assert (output / "eval_reports/automix_report_index.json").exists()
    assert (output / "eval_reports/global_qc_summary.json").exists()
    assert (output / "eval_reports/github_integration_smoke.json").exists()
    assert (output / "eval_reports/current_state_summary.json").exists()
    assert (output / "eval_reports/professional_readiness_audit.json").exists()
    assert (output / "rollback/global_rollback_registry.json").exists()
    statuses = {result["stage"]: result["status"] for result in manifest["stage_results"]}
    assert statuses["github_integration_smoke"] == StageStatus.PASSED_WITH_WARNINGS.value
    assert statuses["professional_readiness_audit"] == StageStatus.PASSED_WITH_WARNINGS.value
    assert all(result["status"] != "passed" for result in manifest["stage_results"] if result["stage"].endswith("_draft"))
    current = json.loads((output / "eval_reports/current_state_summary.json").read_text(encoding="utf-8"))
    assert current["github_integration"]["qc_passed"] is True
    assert current["github_integration"]["safe_to_write_parameters"] is False


def test_safe_draft_blocks_on_missing_validated_plugin_mapping(tmp_path: Path) -> None:
    manifest = run_orchestrator(
        tmp_path,
        mode="safe_draft",
        allow_recovery_drafts=True,
        allow_pitch_correction=True,
        allow_placement_drafts=True,
        allow_premaster_draft=True,
    )
    statuses = {result["stage"]: result["status"] for result in manifest["stage_results"]}
    assert manifest["global_status"] == "blocked_plugin_mapping_required"
    assert statuses["vocal_recovery_draft"] == StageStatus.REQUIRES_PLUGIN_MAPPING.value
    assert statuses["pitch_draft"] == StageStatus.REQUIRES_PLUGIN_MAPPING.value
    assert statuses["vocal_placement_draft"] == StageStatus.REQUIRES_PLUGIN_MAPPING.value


def test_final_delivery_blocks_without_approval(tmp_path: Path) -> None:
    manifest = run_orchestrator(tmp_path, mode="final_delivery", allow_final_export=True, final_approval_explicit=False)
    statuses = {result["stage"]: result["status"] for result in manifest["stage_results"]}
    assert manifest["global_status"] == "final_delivery_failed"
    assert manifest["safe_to_export"] is False
    assert statuses["final_export_state_resolver"] == StageStatus.REQUIRES_APPROVAL.value
    assert statuses["professional_readiness_audit"] == StageStatus.BLOCKED.value
    assert "Approve final export" in " ".join(manifest["next_required_actions"])


def test_approve_final_does_not_override_missing_qc_or_source(tmp_path: Path) -> None:
    manifest = run_orchestrator(tmp_path, mode="final_delivery", allow_final_export=True, final_approval_explicit=True)
    statuses = {result["stage"]: result["status"] for result in manifest["stage_results"]}
    assert manifest["global_status"] == "final_delivery_failed"
    assert manifest["safe_to_export"] is False
    assert statuses["final_export"] == StageStatus.BLOCKED.value
    assert "qc_failure_for_final_delivery" in statuses or any("qc_failure_for_final_delivery" in result.get("blockers", []) for result in manifest["stage_results"])


def test_final_delivery_resolver_surfaces_unresolved_feedback_blocker(tmp_path: Path) -> None:
    output = tmp_path / "automix"
    append_revision_memory(
        output_dir=output,
        project_name="project",
        pass_id="v01",
        feedback_texts=["보컬이 뒤로 빠졌고 리버브가 너무 많다."],
    )
    manifest = run_orchestrator(
        tmp_path,
        mode="final_delivery",
        allow_final_export=True,
        final_approval_explicit=True,
    )
    state = json.loads((output / "export/final_export_state.json").read_text(encoding="utf-8"))
    resolver = next(result for result in manifest["stage_results"] if result["stage"] == "final_export_state_resolver")
    readiness = next(result for result in manifest["stage_results"] if result["stage"] == "professional_readiness_audit")
    assert "user_feedback_unresolved_for_final_delivery" in state["blocked_reasons"]
    assert "user_feedback_unresolved_for_final_delivery" in resolver["warnings"]
    assert "user_feedback_unresolved_for_final_delivery" in readiness["blockers"]
    assert manifest["safe_to_export"] is False


def test_no_pitch_skips_pitch_draft(tmp_path: Path) -> None:
    manifest = run_orchestrator(tmp_path, mode="safe_draft", allow_pitch_correction=False)
    statuses = {result["stage"]: result["status"] for result in manifest["stage_results"]}
    assert statuses["pitch_triage"] == StageStatus.SKIPPED.value
    assert statuses["pitch_draft"] == StageStatus.SKIPPED.value


def test_diagnostic_continue_cannot_apply_processing(tmp_path: Path) -> None:
    manifest = run_orchestrator(
        tmp_path,
        mode="diagnostic_continue",
        diagnostic_continue=True,
        allow_recovery_drafts=True,
        allow_pitch_correction=True,
        allow_placement_drafts=True,
        allow_final_export=True,
    )
    statuses = {result["stage"]: result["status"] for result in manifest["stage_results"]}
    assert manifest["global_status"] == "scan_complete"
    assert statuses["vocal_recovery_draft"] == StageStatus.SKIPPED.value
    assert statuses["pitch_draft"] == StageStatus.SKIPPED.value
    assert statuses["premaster_draft"] == StageStatus.SKIPPED.value
    assert statuses["final_export"] == StageStatus.SKIPPED.value


def test_dependency_graph_blocks_pitch_before_classification() -> None:
    allowed, failures = can_run_stage("pitch_triage", {}, mode="safe_draft")
    assert allowed is False
    assert "source_classification_not_run" in failures or "pitch_triage_requires_source_classification" in failures


def test_global_rollback_registry_fails_missing_applied_stage_rollback(tmp_path: Path) -> None:
    registry = build_global_rollback_registry(project_name="unit", output_dir=tmp_path / "automix", applied_stages=["pitch_draft"])
    validation = validate_global_rollback_integrity(registry, applied_stages=["pitch_draft"])
    assert validation["passed"] is False
    assert "pitch_draft_applied_without_rollback_file" in validation["failures"]


def test_resume_state_detects_previous_manifest(tmp_path: Path) -> None:
    first = run_orchestrator(tmp_path, mode="scan_only", dry_run=True)
    second = run_orchestrator(tmp_path, mode="scan_only", dry_run=True)
    resume = json.loads((tmp_path / "automix/orchestrator/resume_state.json").read_text(encoding="utf-8"))
    assert first["global_status"] == "scan_complete"
    assert second["global_status"] == "scan_complete"
    assert resume["previous_state_found"] is True


def test_cli_default_scan_only_and_dry_run(tmp_path: Path) -> None:
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/run_automix_orchestrator.py"),
            "--output-dir",
            str(tmp_path / "automix"),
            "--dry-run",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    data = json.loads(result.stdout)
    assert data["status"] == "scan_complete"
    assert data["mode"] == "scan_only"
    assert data["dry_run"] is True


def test_cli_final_delivery_without_approval_reports_block(tmp_path: Path) -> None:
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/run_automix_orchestrator.py"),
            "--mode",
            "final_delivery",
            "--allow-final-export",
            "--output-dir",
            str(tmp_path / "automix"),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    data = json.loads(result.stdout)
    assert data["status"] == "final_delivery_failed"
    assert data["final_export_blocked_without_approval"] is True


def test_documentation_exists() -> None:
    assert (ROOT / "docs/end_to_end_automix_orchestrator.md").exists()
    assert (ROOT / "docs/manual_test_plan_prompt40.md").exists()


if __name__ == "__main__":
    current = globals()
    failures: list[str] = []
    for name in sorted(k for k in current if k.startswith("test_")):
        fn = current[name]
        try:
            if "tmp_path" in fn.__code__.co_varnames:
                with tempfile.TemporaryDirectory() as directory:
                    fn(Path(directory))
            else:
                fn()
        except Exception as exc:  # pragma: no cover
            failures.append(f"{name}: {exc}")
    if failures:
        raise SystemExit("\n".join(failures))
    print("Prompt40 direct tests passed")

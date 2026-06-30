from __future__ import annotations

import json
from pathlib import Path

from automix.analyze_ai_pitch_source import run_analysis
from automix.orchestrator.global_rollback_registry import build_global_rollback_registry, validate_global_rollback_integrity
from automix.orchestrator.global_safety_controller import evaluate_workflow_continuation
from automix.orchestrator.stage_result_schema import finish_stage, start_stage
from automix.orchestrator.stage_status import StageStatus

from tests.automix_validation.prompt41_validation_common import AUDIO, ensure_prompt41_fixtures, output_dir


def analyze_fixture(name: str, tmp_path: Path) -> tuple[dict, dict, dict]:
    ensure_prompt41_fixtures()
    paths = run_analysis(AUDIO / name, output_dir(tmp_path), name)
    return (
        json.loads(paths["classification"].read_text(encoding="utf-8")),
        json.loads(paths["pitch_analysis"].read_text(encoding="utf-8")),
        json.loads(paths["chain_plan"].read_text(encoding="utf-8")),
    )


def test_raw_vocal_fixture_not_full_mix_and_pitch_confident(tmp_path: Path) -> None:
    classification, pitch, plan = analyze_fixture("raw_vocal_like_mono.wav", tmp_path)
    assert classification["classification"] != "full_mix"
    assert classification["full_mix_likelihood"] < 0.50
    assert pitch["monophonic_pitch_confidence"] > 0.45
    assert plan["apply"] is False


def test_already_tuned_fixture_blocks_strong_pitch(tmp_path: Path) -> None:
    classification, _pitch, plan = analyze_fixture("already_tuned_ai_like_vocal.wav", tmp_path)
    assert classification["already_tuned_score"] > 0.70
    assert plan["apply"] is False
    assert plan["safety_gate"]["decision"] in {"skip", "apply_micro", "plugin_mapping_required"}


def test_source_separated_watery_fixture_is_unsafe_for_pitch(tmp_path: Path) -> None:
    classification, _pitch, plan = analyze_fixture("source_separated_watery_vocal.wav", tmp_path)
    assert classification["source_separated_likelihood"] > 0.30 or classification["full_mix_likelihood"] > 0.50
    assert plan["apply"] is False


def test_full_mix_fixture_blocks_pitch(tmp_path: Path) -> None:
    classification, _pitch, plan = analyze_fixture("full_mix_dense_polyphonic.wav", tmp_path)
    assert classification["classification"] == "full_mix" or classification["full_mix_likelihood"] > 0.50
    assert plan["apply"] is False
    assert plan["safety_gate"]["decision"] in {"full_mix_unsafe", "skip"}


def test_fragile_thin_and_harsh_fixtures_report_recovery_risk(tmp_path: Path) -> None:
    thin, _pitch, _plan = analyze_fixture("fragile_thin_ai_vocal.wav", tmp_path)
    harsh, _pitch_h, _plan_h = analyze_fixture("harsh_sibilant_vocal.wav", tmp_path)
    assert thin["metrics"]["spectral"]["clarity_ratio"] + thin["metrics"]["spectral"]["air_ratio"] > 0.0
    assert harsh["metrics"]["spectral"]["clarity_ratio"] + harsh["metrics"]["spectral"]["air_ratio"] > 0.0


def test_original_protection_blockers_stop_applied_workflow(tmp_path: Path) -> None:
    stage = finish_stage(
        start_stage("original_protection_probe"),
        status=StageStatus.BLOCKED,
        blockers=["original_track_modified_unexpectedly", "original_master_modified_unexpectedly"],
        safe_to_continue=False,
    )
    safety = evaluate_workflow_continuation(
        mode="safe_draft",
        stage_results=[stage],
        config={"stop_on_safety_failure": True, "require_ab_eval_for_applied_stages": True},
    )
    assert safety["can_apply_processing"] is False
    assert "original_track_modified_unexpectedly" in safety["hard_blockers"]
    assert "original_master_modified_unexpectedly" in safety["hard_blockers"]


def test_missing_rollback_blocks_applied_stage(tmp_path: Path) -> None:
    registry = build_global_rollback_registry(project_name="prompt41", output_dir=output_dir(tmp_path), applied_stages=["pitch_draft"])
    validation = validate_global_rollback_integrity(registry, applied_stages=["pitch_draft"])
    assert validation["passed"] is False
    assert "pitch_draft_applied_without_rollback_file" in validation["failures"]

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from automix.feedback.revision_memory import append_revision_memory, resolve_feedback_items
from automix.intent.intent_classifier import build_intent_classification
from automix.orchestrator.automix_orchestrator import AutoMixOrchestrator
from automix.orchestrator.stage_dependency_graph import STAGE_ORDER
from automix.orchestrator.stage_status import StageStatus
from automix.plugins.plugin_adapter_schema import write_json


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_safe_scan_evidence(out: Path) -> None:
    write_json(
        out / "eval_reports/real_project_source_safety_map.json",
        {
            "schema": "automix-real-project-source-safety-map-v1",
            "project_name": "unit",
            "summary": {
                "safe_vocal_candidates": 1,
                "ai_or_already_processed_vocals": 1,
                "source_separated_vocals": 0,
                "full_mix_unsafe_tracks": 0,
                "stem_required_tracks": 0,
                "unknown_tracks": 0,
                "tracks_total": 4,
            },
            "warnings": [],
        },
    )
    write_json(
        out / "eval_reports/real_project_plugin_readiness.json",
        {
            "schema": "automix-real-project-plugin-readiness-v1",
            "safe_draft_plugin_ready": True,
            "can_run_pitch_correction_safely": True,
            "can_run_vocal_placement_safely": True,
            "can_run_premaster_draft_safely": True,
            "safe_adapters_count": 3,
            "missing_or_unsafe_mappings": [],
            "warnings": [],
        },
    )


def test_intent_classifier_prefers_vocal_and_artifact_safe_drafts_with_review(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    write_safe_scan_evidence(out)
    append_revision_memory(
        output_dir=out,
        project_name="unit",
        pass_id="v01",
        feedback_texts=["보컬이 뿌옇고 Suno fizz가 남아 있다."],
    )
    report = build_intent_classification(project_name="unit", output_dir=out, target_profile="digicore_hyperpop_hiphop_vocal_forward")
    by_intent = {item["intent"]: item for item in report["intents"]}
    assert report["status"] == "safe_draft_intent_available"
    assert report["recommended_primary_intent"] in {"vocal_rescue", "suno_artifact_suppression", "conservative_cleanup"}
    assert "vocal_rescue" in report["safe_draft_intents"]
    assert by_intent["suno_artifact_suppression"]["conservative_mode"] is True
    assert by_intent["suno_artifact_suppression"]["max_artifact_focus_dry_wet"] <= 0.30
    assert by_intent["aggressive_creative_enhancement"]["status"] == "blocked"
    assert report["dry_run_only"] is True
    assert (out / "eval_reports/intent_classification.json").exists()
    md = (out / "eval_reports/intent_classification.md").read_text(encoding="utf-8")
    assert "Intent Classification Report" in md
    assert "Artifact handling is described as reduction or suppression" in md


def test_intent_classifier_blocks_when_full_mix_stems_and_plugins_are_missing(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    write_json(
        out / "analysis_reports/orchestrator_source_classification_summary.json",
        {
            "schema": "automix-orchestrator-source-classification-summary-v1",
            "project_name": "unit",
            "tracks_total": 3,
            "vocal_like_tracks": 0,
            "full_mix_unsafe_tracks": 1,
            "stem_required_tracks": 1,
            "unknown_tracks_skipped": 1,
            "warnings": [],
        },
    )
    write_json(
        out / "analysis_reports/plugin_inventory_audit.json",
        {
            "schema": "automix-plugin-inventory-audit-v1",
            "summary": {"validated_safe_count": 0},
            "unsafe_or_unmapped_plugins": [{"name": "Mystery Enhancer"}],
            "warnings": [],
        },
    )
    report = build_intent_classification(project_name="unit", output_dir=out, requested_intents=["aggressive_creative_enhancement"])
    by_intent = {item["intent"]: item for item in report["intents"]}
    assert report["status"] == "review_required"
    assert report["safe_next_mode"] == "validate_plugin_mappings"
    assert "validated_plugin_mapping_required" in report["blockers"]
    assert "isolated_stems_required" in report["blockers"]
    assert by_intent["full_mix_polish"]["status"] == "manual_review_only"
    assert by_intent["aggressive_creative_enhancement"]["status"] == "blocked"


def test_intent_classifier_safe_next_mode_clears_after_feedback_resolution(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    write_safe_scan_evidence(out)
    memory = append_revision_memory(
        output_dir=out,
        project_name="unit",
        pass_id="v01",
        feedback_texts=["마스터가 너무 납작하다."],
    )
    unresolved = build_intent_classification(project_name="unit", output_dir=out, target_profile="professional_streaming_master")
    assert unresolved["safe_next_mode"] == "safe_draft_review_only_until_feedback_resolved"
    evidence = out / "eval_reports/final_qc_metrics.json"
    write_json(evidence, {"schema": "x", "qc_passed": True})
    resolve_feedback_items(
        output_dir=out,
        project_name="unit",
        pass_id="v02",
        feedback_ids=memory["unresolved_feedback_ids"],
        evidence_paths=[str(evidence)],
        human_reviewed=True,
        measured_qc_passed=True,
        loudness_matched_ab_reviewed=True,
    )
    resolved = build_intent_classification(project_name="unit", output_dir=out, target_profile="professional_streaming_master")
    assert resolved["safe_next_mode"] in {"safe_draft_no_pitch", "safe_draft_recovery_only"}
    streaming = next(item for item in resolved["intents"] if item["intent"] == "streaming_master")
    assert streaming["status"] == "safe_draft_allowed"


def test_intent_classifier_cli_writes_reports(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    write_safe_scan_evidence(out)
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/run_intent_classifier.py"),
            "--project-name",
            "unit",
            "--output-dir",
            str(out),
            "--target-profile",
            "digicore_hyperpop_hiphop_vocal_forward",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    data = json.loads(result.stdout)
    assert data["status"] == "safe_draft_intent_available"
    assert Path(data["report_json"]).exists()
    assert Path(data["report_md"]).exists()


def test_orchestrator_writes_intent_classification_stage(tmp_path: Path) -> None:
    output = tmp_path / "automix"
    manifest = AutoMixOrchestrator({"output_dir": str(output), "mode": "scan_only", "dry_run": True}).run()
    statuses = {result["stage"]: result["status"] for result in manifest["stage_results"]}
    assert "intent_classification" in STAGE_ORDER
    assert statuses["intent_classification"] in {StageStatus.PASSED.value, StageStatus.PASSED_WITH_WARNINGS.value}
    assert (output / "eval_reports/intent_classification.json").exists()
    report_index = read_json(output / "eval_reports/automix_report_index.json")
    assert any(item["stage"] == "intent classification" and item["summary"] == "intent_classification.json" for item in report_index["reports"])


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
    print("Prompt48 direct tests passed")

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from automix.feedback.feedback_action_mapping import map_feedback_to_actions
from automix.feedback.feedback_intake import classify_feedback
from automix.feedback.feedback_qc_integration import build_feedback_qc_integration
from automix.feedback.revision_memory import append_revision_memory, resolve_feedback_items, summarize_feedback_memory
from automix.orchestrator.global_qc_aggregator import build_global_qc_summary
from automix.plugins.plugin_adapter_schema import write_json


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_korean_feedback_classifies_vocal_suno_and_mastering_issues() -> None:
    feedback = classify_feedback(
        "보컬이 뿌옇고 뒤로 빠졌어. 10kHz 이상 Suno fizz가 남아 있고 마스터가 너무 납작하다.",
        project_name="unit_project",
        pass_id="v01",
        track_name="Lead Vocal",
    )
    categories = {item["category"] for item in feedback["categories"]}
    assert "vocal_clarity" in categories
    assert "vocal_presence" in categories
    assert "ai_artifact" in categories
    assert "mastering_dynamics" in categories
    assert feedback["requires_human_review"] is True

    plan = map_feedback_to_actions(feedback)
    action_ids = {item["action_id"] for item in plan["planned_actions"]}
    assert "diagnose_vocal_mud_and_presence" in action_ids
    assert "suno_ai_artifact_suppression_scan" in action_ids
    assert "premaster_limiter_pressure_audit" in action_ids
    assert "artifact_reduction_language_only" in plan["safety_flags"]
    assert any(item["blocked_action"] == "claim_100_percent_removal" for item in plan["blocked_auto_actions"])
    assert all(item["dry_run_only"] is True for item in plan["planned_actions"])


def test_revision_memory_persists_and_marks_repeated_categories(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    append_revision_memory(
        output_dir=out,
        project_name="unit_project",
        pass_id="v01",
        feedback_texts=["보컬이 뿌옇고 리버브가 너무 많다."],
        track_name="Lead Vocal",
    )
    memory = append_revision_memory(
        output_dir=out,
        project_name="unit_project",
        pass_id="v02",
        feedback_texts=["아직 보컬이 뿌옇다. 수노 느낌도 남아 있다."],
        track_name="Lead Vocal",
    )
    assert (out / "review/user_feedback_revision_memory.json").exists()
    assert (out / "eval_reports/user_feedback_action_plan.json").exists()
    assert (out / "eval_reports/user_feedback_revision_report.md").exists()
    assert memory["category_counts"]["vocal_clarity"] == 2
    latest = memory["entries"][-1]
    assert "vocal_clarity" in latest["repeated_categories"]
    assert latest["dry_run_only"] is True

    summary = summarize_feedback_memory(out)
    assert summary["exists"] is True
    assert summary["pending_unresolved_count"] == 2
    assert "vocal_clarity" in summary["repeated_categories"]
    assert "repeated_feedback_category_requires_attention" in summary["warnings"]


def test_global_qc_blocks_final_delivery_when_feedback_is_unresolved(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    write_json(out / "eval_reports/final_qc_metrics.json", {"qc_passed": True, "warnings": []})
    append_revision_memory(
        output_dir=out,
        project_name="unit_project",
        pass_id="v01",
        feedback_texts=["마스터가 너무 납작하고 보컬이 뒤로 빠졌다."],
    )
    summary = build_global_qc_summary(
        project_name="unit_project",
        output_dir=out,
        stage_results=[],
        final_delivery_requested=True,
    )
    assert summary["safe_to_export"] is False
    assert "user_feedback_unresolved_for_final_delivery" in summary["critical_blockers"]
    assert summary["feedback_revision_loop"]["pending_unresolved_count"] == 1
    assert summary["feedback_qc_integration"]["requires_human_review"] is True
    assert "user_feedback_unresolved" in summary["warnings"]


def test_resolution_requires_existing_evidence_qc_ab_and_human_review(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    memory = append_revision_memory(
        output_dir=out,
        project_name="unit_project",
        pass_id="v01",
        feedback_texts=["보컬이 뒤로 빠졌고 수노 fizz가 남아 있다."],
    )
    feedback_id = memory["unresolved_feedback_ids"][0]
    blocked = resolve_feedback_items(
        output_dir=out,
        project_name="unit_project",
        pass_id="v02",
        feedback_ids=[feedback_id],
        evidence_paths=[str(out / "eval_reports/missing_qc.json")],
        human_reviewed=True,
        measured_qc_passed=True,
        loudness_matched_ab_reviewed=True,
    )
    latest_record = blocked["resolution_records"][-1]
    assert latest_record["accepted_for_resolution"] is False
    assert feedback_id in blocked["unresolved_feedback_ids"]
    assert any(item.startswith("evidence_path_missing:") for item in latest_record["missing_requirements"])

    evidence = out / "eval_reports/final_qc_metrics.json"
    write_json(evidence, {"qc_passed": True, "loudness_matched_ab_reviewed": True})
    resolved = resolve_feedback_items(
        output_dir=out,
        project_name="unit_project",
        pass_id="v03",
        feedback_ids=[feedback_id],
        resolution_notes="Matched A/B and final QC confirmed vocal is no longer buried.",
        evidence_paths=[str(evidence)],
        human_reviewed=True,
        measured_qc_passed=True,
        loudness_matched_ab_reviewed=True,
        remaining_risks=["human preference may still require another revision"],
    )
    assert resolved["resolution_records"][-1]["accepted_for_resolution"] is True
    assert feedback_id in resolved["resolved_feedback_ids"]
    assert feedback_id not in resolved["unresolved_feedback_ids"]
    summary = summarize_feedback_memory(out)
    assert summary["pending_unresolved_count"] == 0
    assert summary["resolved_feedback_count"] == 1
    assert summary["requires_human_review"] is False


def test_global_qc_allows_final_delivery_feedback_blocker_to_clear_after_resolution(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    write_json(out / "eval_reports/final_qc_metrics.json", {"qc_passed": True, "warnings": []})
    memory = append_revision_memory(
        output_dir=out,
        project_name="unit_project",
        pass_id="v01",
        feedback_texts=["마스터가 너무 납작하다."],
    )
    feedback_id = memory["unresolved_feedback_ids"][0]
    resolve_feedback_items(
        output_dir=out,
        project_name="unit_project",
        pass_id="v02",
        feedback_ids=[feedback_id],
        resolution_notes="Limiter pressure and A/B review passed.",
        evidence_paths=[str(out / "eval_reports/final_qc_metrics.json")],
        human_reviewed=True,
        measured_qc_passed=True,
        loudness_matched_ab_reviewed=True,
    )
    summary = build_global_qc_summary(
        project_name="unit_project",
        output_dir=out,
        stage_results=[],
        final_delivery_requested=True,
    )
    assert summary["safe_to_export"] is True
    assert "user_feedback_unresolved_for_final_delivery" not in summary["critical_blockers"]
    assert summary["feedback_revision_loop"]["pending_unresolved_count"] == 0
    assert summary["feedback_qc_integration"]["requires_human_review"] is False


def test_feedback_qc_integration_links_feedback_actions_metrics_ab_and_risks(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    memory = append_revision_memory(
        output_dir=out,
        project_name="unit_project",
        pass_id="v01",
        feedback_texts=["보컬이 뿌옇고 10kHz 이상 Suno fizz가 남아 있다."],
        track_name="Lead Vocal",
    )
    write_json(
        out / "eval_reports/final_qc_metrics.json",
        {
            "schema": "automix-final-qc-metrics-v1",
            "qc_passed": True,
            "vocal_preservation": {
                "vocal_forwardness_score": 0.72,
                "vocal_harshness_score": 0.21,
                "sibilance_splatter_score": 0.18,
                "metallic_artifact_score": 0.24,
                "ai_fizz_score": 0.29,
            },
            "translation": {
                "small_speaker_vocal_loss_risk": 0.22,
                "phase_correlation": 0.81,
                "earbud_harshness_risk": 0.19,
            },
            "loudness": {"integrated_lufs": -10.2, "true_peak_dbTP": -1.2, "lra": 6.0},
        },
    )
    preview = out / "deliverables/unit/Audio/Preview/unit_AB_PREVIEW.wav"
    preview.parent.mkdir(parents=True)
    preview.write_bytes(b"RIFF----WAVE-ab")
    write_json(
        out / "eval_reports/final_ab_preview_manifest.json",
        {
            "schema": "automix-final-ab-preview-v1",
            "created": True,
            "loudness_matched": True,
            "output_path": str(preview),
            "warnings": [],
        },
    )
    integration = build_feedback_qc_integration(project_name="unit_project", output_dir=out)
    item = integration["items"][0]
    assert integration["summary"]["total_feedback_items"] == 1
    assert item["resolution_status"] == "unresolved_review_required"
    assert "diagnose_vocal_mud_and_presence" in {action["action_id"] for action in item["planned_actions"]}
    assert "suno_like_probability" in item["cause_hypotheses"]
    assert any(metric["metric"] == "final_qc.vocal_preservation.ai_fizz_score" and metric["value"] == 0.29 for metric in item["qc_metric_snapshot"])
    assert item["before_after_evidence"]["ab_preview_loudness_matched"] is True
    assert "Artifact suppression reduces perceived risk but does not prove total cleanup." in item["remaining_risks"]

    feedback_id = memory["unresolved_feedback_ids"][0]
    resolve_feedback_items(
        output_dir=out,
        project_name="unit_project",
        pass_id="v02",
        feedback_ids=[feedback_id],
        resolution_notes="Measured QC and loudness-matched A/B review passed.",
        evidence_paths=[str(out / "eval_reports/final_qc_metrics.json")],
        human_reviewed=True,
        measured_qc_passed=True,
        loudness_matched_ab_reviewed=True,
    )
    resolved = build_feedback_qc_integration(project_name="unit_project", output_dir=out)
    resolved_item = resolved["items"][0]
    assert resolved_item["resolution_status"] == "resolved_with_evidence"
    assert resolved_item["before_after_evidence"]["result_statement"] == "resolved_with_evidence"
    report = (out / "eval_reports/user_feedback_qc_integration.md").read_text(encoding="utf-8")
    assert "User Feedback QC Integration" in report
    assert "Result statement: `resolved_with_evidence`" in report


def test_feedback_cli_writes_memory_action_plan_and_report(tmp_path: Path) -> None:
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/run_feedback_revision_loop.py"),
            "--output-dir",
            str(tmp_path / "automix"),
            "--project-name",
            "unit_project",
            "--pass-id",
            "v01",
            "--track-name",
            "Lead Vocal",
            "--feedback",
            "보컬이 뭉개지고 3~5kHz 쇳소리가 거칠다.",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    data = json.loads(result.stdout)
    assert data["status"] == "feedback_revision_plan_created"
    assert data["dry_run_only"] is True
    assert Path(data["memory"]).exists()
    assert Path(data["qc_integration"]).exists()
    assert Path(data["qc_integration_report"]).exists()
    action_plan = read_json(Path(data["action_plan"]))
    assert action_plan["requires_human_review"] is True
    assert "dry_run_required" in action_plan["safety_flags"]


def test_feedback_cli_resolution_mode_requires_full_evidence(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    append_revision_memory(
        output_dir=out,
        project_name="unit_project",
        pass_id="v01",
        feedback_texts=["보컬이 뿌옇다."],
    )
    feedback_id = read_json(out / "review/user_feedback_revision_memory.json")["unresolved_feedback_ids"][0]
    blocked = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/run_feedback_revision_loop.py"),
            "--output-dir",
            str(out),
            "--project-name",
            "unit_project",
            "--resolve-feedback-id",
            feedback_id,
            "--human-reviewed",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert blocked.returncode == 2
    blocked_data = json.loads(blocked.stdout)
    assert blocked_data["status"] == "feedback_resolution_blocked"
    assert "evidence_path_required" in blocked_data["missing_requirements"]

    evidence = out / "eval_reports/final_qc_metrics.json"
    write_json(evidence, {"qc_passed": True})
    accepted = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/run_feedback_revision_loop.py"),
            "--output-dir",
            str(out),
            "--project-name",
            "unit_project",
            "--resolve-feedback-id",
            feedback_id,
            "--resolution-notes",
            "A/B review and QC passed.",
            "--evidence-path",
            str(evidence),
            "--human-reviewed",
            "--measured-qc-passed",
            "--loudness-matched-ab-reviewed",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    accepted_data = json.loads(accepted.stdout)
    assert accepted_data["status"] == "feedback_resolution_accepted"
    assert accepted_data["pending_unresolved_count"] == 0


def test_no_feedback_cli_blocks(tmp_path: Path) -> None:
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/run_feedback_revision_loop.py"),
            "--output-dir",
            str(tmp_path / "automix"),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 2
    data = json.loads(result.stdout)
    assert data["reason"] == "feedback_required"


def test_feedback_cli_initialize_baseline_writes_no_feedback_evidence(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/run_feedback_revision_loop.py"),
            "--output-dir",
            str(out),
            "--project-name",
            "unit_project",
            "--initialize-baseline",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    data = json.loads(result.stdout)
    assert data["status"] == "feedback_revision_baseline_ready"
    assert data["total_entries"] == 0
    assert data["pending_unresolved_count"] == 0
    assert data["requires_human_review"] is False
    assert data["baseline_status"] == "no_feedback_recorded"
    assert data["no_feedback_fabricated"] is True
    assert Path(data["memory"]).exists()
    assert Path(data["action_plan"]).exists()
    assert Path(data["qc_integration"]).exists()
    memory = read_json(Path(data["memory"]))
    assert memory["entries"] == []
    assert memory["baseline_status"] == "no_feedback_recorded"
    assert memory["no_feedback_fabricated"] is True
    action_plan = read_json(Path(data["action_plan"]))
    assert action_plan["requires_human_review"] is False
    assert action_plan["no_feedback_fabricated"] is True
    integration = read_json(Path(data["qc_integration"]))
    assert integration["summary"]["total_feedback_items"] == 0
    assert integration["summary"]["requires_human_review"] is False
    report = Path(data["qc_integration_report"]).read_text(encoding="utf-8")
    assert "none recorded; no listening feedback was fabricated" in report


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
    print("Prompt45 direct tests passed")

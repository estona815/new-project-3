from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from automix.feedback.revision_memory import append_revision_memory, resolve_feedback_items
from automix.feedback.feedback_qc_integration import build_feedback_qc_integration
from automix.analyze_ai_pitch_source import AudioData
from automix.export.audio_export_utils import write_pcm_wav
from automix.orchestrator.ab_preview_evidence_gate import build_ab_preview_evidence_gate
from automix.orchestrator.claim_language_guard import run_claim_language_guard
from automix.orchestrator.deliverable_package_evidence_gate import build_deliverable_package_evidence_gate
from automix.orchestrator.final_approval_evidence_gate import build_final_approval_evidence_gate
from automix.orchestrator.final_delivery_consistency_gate import build_final_delivery_consistency_gate
from automix.orchestrator.final_qc_evidence_gate import build_final_qc_evidence_gate
from automix.orchestrator.final_render_evidence_gate import build_final_render_evidence_gate
from automix.orchestrator.rollback_evidence_gate import build_rollback_evidence_gate
from automix.orchestrator.professional_readiness_audit import build_professional_readiness_audit
from automix.orchestrator.risk_root_cause_rollup import build_risk_root_cause_rollup
from automix.plugins.plugin_adapter_schema import write_json


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_safe_delivery_evidence(out: Path, source: Path) -> None:
    render = out / "deliverables/unit/Audio/WAV/unit_FINAL_MASTER.wav"
    render.parent.mkdir(parents=True, exist_ok=True)
    preview = out / "deliverables/unit/Audio/Preview/unit_AB_PREVIEW.wav"
    preview.parent.mkdir(parents=True, exist_ok=True)
    frames = [[0.1, 0.09] for _ in range(4800)]
    write_pcm_wav(source, AudioData(sample_rate=48000, channels=2, frames=frames), bit_depth=24)
    write_pcm_wav(render, AudioData(sample_rate=48000, channels=2, frames=frames), bit_depth=24)
    write_pcm_wav(preview, AudioData(sample_rate=48000, channels=2, frames=frames), bit_depth=24)
    zip_path = out / "deliverables/unit_DELIVERABLES.zip"
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.write(render, arcname="unit/Audio/WAV/unit_FINAL_MASTER.wav")
        archive.write(preview, arcname="unit/Audio/Preview/unit_AB_PREVIEW.wav")
    project_state = {
        "schema": "automix-project-state-manifest-v1",
        "project_name": "unit",
        "original_tracks_protected": True,
        "master_unchanged": True,
        "accepted_sources": [str(source)],
        "render_manifest": [{"path": str(render), "format": "wav", "created": True}],
    }
    write_json(
        out / "export/final_export_state.json",
        {
            "schema": "automix-final-export-state-v1",
            "safe_to_export": True,
            "blocked_reasons": [],
            "selected_export_source": str(source),
            "selected_export_stage": "accepted_premaster_draft",
        },
    )
    write_json(
        out / "export/final_render_manifest.json",
        {
            "schema": "automix-final-render-manifest-v1",
            "project_name": "unit",
            "renders": [
                {
                    "format": "wav",
                    "path": str(render),
                    "created": True,
                    "size_bytes": render.stat().st_size,
                    "sample_rate": 48000,
                    "bit_depth": 24,
                }
            ],
            "failures": [],
            "warnings": [],
        },
    )
    build_final_render_evidence_gate(project_name="unit", output_dir=out)
    write_json(
        out / "export/deliverable_package_manifest.json",
        {
            "schema": "automix-deliverable-package-manifest-v1",
            "zip_path": str(zip_path),
            "files_included": [str(render), str(preview)],
            "files_missing": [],
            "package_created": True,
            "package_size_bytes": zip_path.stat().st_size,
            "project_state_manifest": project_state,
            "warnings": [],
        },
    )
    write_json(out / "export/project_state_manifest.json", project_state)
    plugin_summary = out / "export/plugin_mapping_summary.md"
    plugin_summary.parent.mkdir(parents=True, exist_ok=True)
    plugin_summary.write_text("# Plugin Mapping Summary\n\n- none claimed\n", encoding="utf-8")
    final_qc_report = out / "eval_reports/final_qc_report.md"
    final_qc_report.parent.mkdir(parents=True, exist_ok=True)
    final_qc_report.write_text("# Final Export QC Report\n\n- status: ready\n", encoding="utf-8")
    write_json(
        out / "eval_reports/final_qc_metrics.json",
        {
            "schema": "automix-final-qc-metrics-v1",
            "final_audio_path": str(render),
            "file_integrity": {
                "exists": True,
                "size_bytes": render.stat().st_size,
                "duration_seconds": 0.1,
                "sample_rate": 48000,
                "bit_depth": 24,
                "channels": 2,
                "clipping_detected": False,
                "digital_black_detected": False,
                "unexpected_silence_detected": False,
            },
            "loudness": {"true_peak_dbTP": -6.0},
            "translation": {},
            "vocal_preservation": {},
            "qc_passed": True,
            "warnings": [],
            "failures": [],
        },
    )
    build_final_qc_evidence_gate(project_name="unit", output_dir=out)
    write_json(
        out / "eval_reports/intent_classification.json",
        {
            "schema": "automix-intent-classification-v1",
            "status": "safe_draft_intent_available",
            "recommended_primary_intent": "streaming_master",
            "safe_next_mode": "safe_draft_no_pitch",
            "safe_draft_intents": ["streaming_master"],
            "dry_run_only": True,
        },
    )
    write_json(
        out / "eval_reports/processing_policy_audit.json",
        {
            "schema": "automix-processing-policy-audit-v1",
            "project_name": "unit",
            "plans_checked": 1,
            "passed": True,
            "safe_to_apply": True,
            "blockers": [],
            "warnings": [],
        },
    )
    write_json(
        out / "eval_reports/final_ab_preview_manifest.json",
        {
            "schema": "automix-final-ab-preview-v1",
            "source_original": str(source),
            "source_final": str(render),
            "segments": [{"label": "original_mix"}, {"label": "final_processed"}],
            "loudness_matched": True,
            "loudness_match": {
                "method": "mono_rms",
                "original_rms": 0.1,
                "target_rms": 0.1,
                "final_rms_before_match": 0.1,
                "final_rms_after_match": 0.1,
                "applied_gain_db": 0.0,
                "delta_db_after_match": 0.0,
                "matched": True,
            },
            "output_path": str(preview),
            "created": True,
            "warnings": [],
        },
    )
    build_ab_preview_evidence_gate(project_name="unit", output_dir=out)
    write_json(out / "eval_reports/global_qc_summary.json", {"schema": "x", "safe_to_export": True, "critical_blockers": []})
    write_json(
        out / "eval_reports/fixture_coverage_audit.json",
        {
            "schema": "automix-fixture-coverage-audit-v1",
            "project_name": "unit",
            "passed": True,
            "covered_categories": ["clean_vocal", "feedback_mapping"],
            "missing_categories": [],
            "blockers": [],
            "warnings": [],
        },
    )
    write_json(
        out / "eval_reports/requirements_traceability_audit.json",
        {
            "schema": "automix-requirements-traceability-audit-v1",
            "project_name": "unit",
            "passed": True,
            "requirements_satisfied": 15,
            "requirements_total": 15,
            "incomplete_requirement_ids": [],
            "blockers": [],
            "warnings": [],
        },
    )
    write_json(
        out / "eval_reports/open_risk_register.json",
        {
            "schema": "automix-open-risk-register-v1",
            "project_name": "unit",
            "passed": True,
            "risk_counts": {"blocker": 0, "warning": 0, "review": 0, "info": 0},
            "open_risks": [],
            "blockers": [],
            "warnings": [],
        },
    )
    build_risk_root_cause_rollup(project_name="unit", output_dir=out)
    write_json(
        out / "eval_reports/risk_remediation_plan.json",
        {
            "schema": "automix-risk-remediation-plan-v1",
            "project_name": "unit",
            "status": "no_open_risks_to_remediate",
            "open_risk_total": 0,
            "actions_total": 1,
            "dry_run_only": True,
            "blockers": [],
            "warnings": [],
        },
    )
    write_json(
        out / "eval_reports/path_hygiene_audit.json",
        {
            "schema": "automix-path-hygiene-audit-v1",
            "project_name": "unit",
            "passed": True,
            "finding_counts": {"blocker": 0, "warning": 0, "info": 0},
            "blockers": [],
            "warnings": [],
        },
    )
    write_json(
        out / "review/final_human_approval.json",
        {
            "schema": "automix-final-human-approval-v1",
            "approved": True,
            "approved_by": "user",
            "approved_stage": "accepted_premaster_draft",
            "approved_source": str(source),
            "approval_time": "2026-06-03T00:00:00Z",
            "notes": "",
            "warnings_acknowledged": ["all"],
            "unsafe_override": False,
            "review_decision": "accepted",
            "loudness_matched_ab_reviewed": True,
            "final_audio_accepted_at_matched_loudness": True,
            "reviewed_ab_preview_path": str(preview),
            "reviewed_final_audio_path": str(render),
            "final_qc_evidence_reviewed": True,
        },
    )
    build_final_approval_evidence_gate(project_name="unit", output_dir=out)
    write_json(out / "eval_reports/automix_report_index.json", {"schema": "x", "reports": []})
    write_json(
        out / "rollback/global_rollback_registry.json",
        {
            "schema": "automix-global-rollback-registry-v1",
            "project_name": "unit",
            "rollback_entries": [],
            "original_tracks_protected": True,
            "original_master_protected": True,
            "validation": {"passed": True, "failures": [], "warnings": []},
        },
    )
    build_rollback_evidence_gate(project_name="unit", output_dir=out)
    build_deliverable_package_evidence_gate(project_name="unit", output_dir=out)
    build_final_delivery_consistency_gate(project_name="unit", output_dir=out)


def test_readiness_audit_blocks_missing_final_delivery_evidence(tmp_path: Path) -> None:
    audit = build_professional_readiness_audit(
        project_name="unit",
        output_dir=tmp_path / "automix",
        workspace_root=ROOT,
        final_delivery_requested=True,
    )
    assert audit["ready_for_delivery"] is False
    assert "final_export_state_missing" in audit["blockers"]
    assert "final_render_manifest_missing" in audit["blockers"]
    assert "deliverable_package_manifest_missing" in audit["blockers"]
    assert "deliverable_package_evidence_gate_missing" in audit["blockers"]
    assert "final_delivery_consistency_gate_missing" in audit["blockers"]
    assert "ab_preview_manifest_missing" in audit["blockers"]
    assert "final_qc_metrics_missing" in audit["blockers"]
    assert "global_qc_summary_missing" in audit["blockers"]
    assert "fixture_coverage_audit_missing" in audit["blockers"]
    assert "requirements_traceability_audit_missing" in audit["blockers"]
    assert "open_risk_register_missing" in audit["blockers"]
    assert "risk_root_cause_rollup_missing" in audit["blockers"]
    assert "risk_remediation_plan_missing" in audit["blockers"]
    assert "path_hygiene_audit_missing" in audit["blockers"]
    assert "intent_classification_missing" in audit["blockers"]
    assert "processing_policy_audit_missing" in audit["blockers"]
    assert "global_rollback_registry_missing" in audit["blockers"]
    assert (tmp_path / "automix/eval_reports/professional_readiness_audit.json").exists()
    assert (tmp_path / "automix/eval_reports/professional_readiness_audit.md").exists()


def test_readiness_audit_blocks_unresolved_feedback_even_when_qc_is_safe(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    source = tmp_path / "accepted.wav"
    source.write_bytes(b"RIFF----WAVE")
    write_safe_delivery_evidence(out, source)
    append_revision_memory(
        output_dir=out,
        project_name="unit",
        pass_id="v01",
        feedback_texts=["보컬이 아직 뿌옇다."],
    )
    audit = build_professional_readiness_audit(project_name="unit", output_dir=out, workspace_root=ROOT, final_delivery_requested=True)
    assert audit["ready_for_delivery"] is False
    assert "user_feedback_unresolved_for_final_delivery" in audit["blockers"]
    assert audit["feedback_revision_loop"]["pending_unresolved_count"] == 1


def test_readiness_audit_ready_when_all_evidence_and_feedback_resolution_pass(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    source = tmp_path / "accepted.wav"
    source.write_bytes(b"RIFF----WAVE")
    write_safe_delivery_evidence(out, source)
    memory = append_revision_memory(
        output_dir=out,
        project_name="unit",
        pass_id="v01",
        feedback_texts=["마스터가 너무 납작하다."],
    )
    resolve_feedback_items(
        output_dir=out,
        project_name="unit",
        pass_id="v02",
        feedback_ids=memory["unresolved_feedback_ids"],
        evidence_paths=[str(out / "eval_reports/final_qc_metrics.json")],
        human_reviewed=True,
        measured_qc_passed=True,
        loudness_matched_ab_reviewed=True,
    )
    build_feedback_qc_integration(project_name="unit", output_dir=out)
    audit = build_professional_readiness_audit(project_name="unit", output_dir=out, workspace_root=ROOT, final_delivery_requested=True)
    assert audit["ready_for_delivery"] is True
    assert audit["readiness_status"] == "ready_for_delivery"
    assert audit["blockers"] == []
    assert audit["feedback_revision_loop"]["pending_unresolved_count"] == 0
    md = (out / "eval_reports/professional_readiness_audit.md").read_text(encoding="utf-8")
    assert "## Delivery Evidence Summary" in md
    assert "A/B preview loudness matched: `True`" in md


def test_readiness_audit_blocks_invalid_delivery_package_evidence(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    source = tmp_path / "accepted.wav"
    source.write_bytes(b"RIFF----WAVE")
    write_safe_delivery_evidence(out, source)

    write_json(
        out / "export/final_render_manifest.json",
        {
            "schema": "automix-final-render-manifest-v1",
            "project_name": "unit",
            "renders": [{"format": "wav", "path": str(tmp_path / "missing.wav"), "created": True, "size_bytes": 12}],
            "failures": ["render_failed"],
            "warnings": [],
        },
    )
    write_json(
        out / "export/deliverable_package_manifest.json",
        {
            "schema": "automix-deliverable-package-manifest-v1",
            "zip_path": str(tmp_path / "missing.zip"),
            "files_included": [],
            "files_missing": [str(tmp_path / "missing-report.md")],
            "package_created": False,
            "package_size_bytes": 0,
            "project_state_manifest": {},
        },
    )
    write_json(
        out / "eval_reports/final_ab_preview_manifest.json",
        {
            "schema": "automix-final-ab-preview-v1",
            "loudness_matched": False,
            "output_path": str(tmp_path / "missing-preview.wav"),
            "created": False,
            "warnings": [],
        },
    )
    write_json(
        out / "rollback/global_rollback_registry.json",
        {
            "schema": "automix-global-rollback-registry-v1",
            "original_tracks_protected": False,
            "original_master_protected": False,
            "validation": {"passed": False, "failures": ["premaster_applied_without_rollback_file"]},
        },
    )

    audit = build_professional_readiness_audit(project_name="unit", output_dir=out, workspace_root=ROOT, final_delivery_requested=True)
    assert audit["ready_for_delivery"] is False
    assert "final_render_manifest_has_failures" in audit["blockers"]
    assert "primary_wav_render_file_missing" in audit["blockers"]
    assert "deliverable_zip_not_created" in audit["blockers"]
    assert "deliverable_package_manifest_has_missing_files" in audit["blockers"]
    assert "ab_preview_not_created_for_final_delivery" in audit["blockers"]
    assert "ab_preview_not_loudness_matched" in audit["blockers"]
    assert "rollback_original_tracks_not_protected" in audit["blockers"]
    assert "rollback_original_master_not_protected" in audit["blockers"]
    assert "premaster_applied_without_rollback_file" in audit["blockers"]


def test_readiness_audit_blocks_failed_fixture_coverage(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    source = tmp_path / "accepted.wav"
    source.write_bytes(b"RIFF----WAVE")
    write_safe_delivery_evidence(out, source)
    write_json(
        out / "eval_reports/fixture_coverage_audit.json",
        {
            "schema": "automix-fixture-coverage-audit-v1",
            "project_name": "unit",
            "passed": False,
            "covered_categories": [],
            "missing_categories": ["feedback_mapping"],
            "blockers": ["required_fixture_category_missing:feedback_mapping"],
            "warnings": [],
        },
    )

    audit = build_professional_readiness_audit(project_name="unit", output_dir=out, workspace_root=ROOT, final_delivery_requested=True)
    assert audit["ready_for_delivery"] is False
    assert "required_fixture_category_missing:feedback_mapping" in audit["blockers"]
    assert audit["fixture_coverage_audit_summary"]["passed"] is False


def test_readiness_audit_blocks_failed_requirements_traceability(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    source = tmp_path / "accepted.wav"
    source.write_bytes(b"RIFF----WAVE")
    write_safe_delivery_evidence(out, source)
    write_json(
        out / "eval_reports/requirements_traceability_audit.json",
        {
            "schema": "automix-requirements-traceability-audit-v1",
            "project_name": "unit",
            "passed": False,
            "requirements_satisfied": 13,
            "requirements_total": 14,
            "incomplete_requirement_ids": ["REQ-14"],
            "blockers": ["REQ-14:required_file_missing:docs/final_export_and_delivery.md"],
            "warnings": [],
        },
    )

    audit = build_professional_readiness_audit(project_name="unit", output_dir=out, workspace_root=ROOT, final_delivery_requested=True)
    assert audit["ready_for_delivery"] is False
    assert "REQ-14:required_file_missing:docs/final_export_and_delivery.md" in audit["blockers"]
    assert audit["requirements_traceability_audit_summary"]["passed"] is False


def test_readiness_audit_blocks_open_risk_register_blockers(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    source = tmp_path / "accepted.wav"
    source.write_bytes(b"RIFF----WAVE")
    write_safe_delivery_evidence(out, source)
    write_json(
        out / "eval_reports/open_risk_register.json",
        {
            "schema": "automix-open-risk-register-v1",
            "project_name": "unit",
            "passed": False,
            "risk_counts": {"blocker": 1, "warning": 0, "review": 0, "info": 0},
            "open_risks": [{"severity": "blocker", "code": "no_accepted_export_source"}],
            "blockers": ["no_accepted_export_source"],
            "warnings": [],
        },
    )

    audit = build_professional_readiness_audit(project_name="unit", output_dir=out, workspace_root=ROOT, final_delivery_requested=True)
    assert audit["ready_for_delivery"] is False
    assert "no_accepted_export_source" in audit["blockers"]
    assert audit["open_risk_register_summary"]["passed"] is False


def test_readiness_audit_summarizes_risk_remediation_plan(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    source = tmp_path / "accepted.wav"
    source.write_bytes(b"RIFF----WAVE")
    write_safe_delivery_evidence(out, source)
    audit = build_professional_readiness_audit(project_name="unit", output_dir=out, workspace_root=ROOT, final_delivery_requested=True)
    assert audit["risk_root_cause_rollup_summary"]["passed"] is True
    assert audit["risk_root_cause_rollup_summary"]["root_cause_total"] == 0
    assert audit["risk_remediation_plan_summary"]["status"] == "no_open_risks_to_remediate"
    assert audit["risk_remediation_plan_summary"]["dry_run_only"] is True


def test_claim_language_guard_allows_safety_context_but_blocks_delivery_claims(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    (out / "eval_reports").mkdir(parents=True)
    safe_report = out / "eval_reports/safe_claims.md"
    safe_report.write_text("Do not claim total artifact removal without evidence.\n", encoding="utf-8")
    safe = run_claim_language_guard(workspace_root=ROOT, output_dir=out)
    assert safe["passed"] is True
    assert (out / "eval_reports/claim_language_guard.json").exists()
    assert (out / "eval_reports/claim_language_guard.md").exists()

    unsafe_report = out / "eval_reports/unsafe_claims.md"
    unsafe_report.write_text("All AI artifacts removed. Commercial master quality achieved.\n", encoding="utf-8")
    unsafe = run_claim_language_guard(workspace_root=ROOT, output_dir=out)
    assert unsafe["passed"] is False
    assert "total_artifact_removal_claim" in unsafe["blockers"]
    assert "unsupported_commercial_master_claim" in unsafe["blockers"]


def test_claim_language_guard_skips_generated_readiness_findings_to_avoid_self_poisoning(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    (out / "eval_reports").mkdir(parents=True)
    (out / "eval_reports/professional_readiness_audit.json").write_text(
        json.dumps(
            {
                "schema": "automix-professional-readiness-audit-v1",
                "claim_language_guard": {
                    "findings": [
                        {
                            "claim_id": "total_artifact_removal_claim",
                            "excerpt": "All AI artifacts removed.",
                        }
                    ]
                },
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    result = run_claim_language_guard(workspace_root=ROOT, output_dir=out)
    assert result["passed"] is True
    assert result["blockers"] == []


def test_readiness_audit_blocks_unsafe_claim_language_even_when_other_evidence_is_safe(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    source = tmp_path / "accepted.wav"
    source.write_bytes(b"RIFF----WAVE")
    write_safe_delivery_evidence(out, source)
    (out / "eval_reports/unsafe_claims.md").write_text("Reference matched perfectly.\n", encoding="utf-8")
    audit = build_professional_readiness_audit(project_name="unit", output_dir=out, workspace_root=ROOT, final_delivery_requested=True)
    assert audit["ready_for_delivery"] is False
    assert "unsupported_reference_match_claim" in audit["blockers"]
    assert audit["claim_language_guard"]["passed"] is False


def test_readiness_cli_returns_nonzero_for_requested_delivery_blockers(tmp_path: Path) -> None:
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/run_professional_readiness_audit.py"),
            "--project-name",
            "unit",
            "--output-dir",
            str(tmp_path / "automix"),
            "--final-delivery-requested",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    data = json.loads(result.stdout)
    assert result.returncode == 2
    assert data["status"] == "review_required"
    assert "final_export_state_missing" in data["blockers"]


def test_readiness_cli_diagnostic_inventory_mode_is_zero(tmp_path: Path) -> None:
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/run_professional_readiness_audit.py"),
            "--project-name",
            "unit",
            "--output-dir",
            str(tmp_path / "automix"),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    data = json.loads(result.stdout)
    assert data["status"] == "review_required"
    assert data["ready_for_delivery"] is False
    assert "final_delivery_not_requested_readiness_is_documentation_and_gate_inventory_only" in data["warnings"]


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
    print("Prompt47 direct tests passed")

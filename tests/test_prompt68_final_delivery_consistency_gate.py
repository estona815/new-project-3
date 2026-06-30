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

from automix.orchestrator.final_delivery_consistency_gate import build_final_delivery_consistency_gate
from automix.orchestrator.professional_readiness_audit import build_professional_readiness_audit
from automix.orchestrator.report_index import build_report_index
from automix.plugins.plugin_adapter_schema import write_json


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_file(path: Path, data: bytes = b"evidence") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return path


def write_consistent_delivery_evidence(out: Path, tmp_path: Path) -> dict[str, Path]:
    source = write_file(tmp_path / "accepted_source.wav", b"source-audio")
    final_audio = write_file(out / "deliverables/unit/Audio/WAV/unit_FINAL_MASTER.wav", b"final-audio")
    preview = write_file(out / "deliverables/unit/Audio/Preview/unit_AB_PREVIEW.wav", b"preview-audio")
    readme = write_file(out / "deliverables/unit/README_DELIVERY.md", b"# Delivery\n")
    zip_path = out / "deliverables/unit_DELIVERABLES.zip"
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.write(final_audio, arcname=f"unit/Audio/WAV/{final_audio.name}")
        archive.write(preview, arcname=f"unit/Audio/Preview/{preview.name}")
        archive.write(readme, arcname="unit/README_DELIVERY.md")

    write_json(
        out / "export/final_export_state.json",
        {
            "schema": "automix-final-export-state-v1",
            "safe_to_export": True,
            "selected_export_source": str(source),
            "selected_export_stage": "accepted_premaster_draft",
            "blocked_reasons": [],
            "warnings": [],
        },
    )
    write_json(
        out / "export/final_render_manifest.json",
        {
            "schema": "automix-final-render-manifest-v1",
            "source_stage": "accepted_premaster_draft",
            "renders": [{"format": "wav", "path": str(final_audio), "created": True, "size_bytes": final_audio.stat().st_size}],
            "failures": [],
            "warnings": [],
        },
    )
    write_json(
        out / "eval_reports/final_render_evidence_gate.json",
        {
            "schema": "automix-final-render-evidence-gate-v1",
            "ready_for_final_qc": True,
            "ready_for_approval_readiness": True,
            "primary_wav_path": str(final_audio),
            "blockers": [],
            "warnings": [],
        },
    )
    write_json(
        out / "eval_reports/final_qc_metrics.json",
        {
            "schema": "automix-final-qc-metrics-v1",
            "final_audio_path": str(final_audio),
            "qc_passed": True,
            "failures": [],
            "warnings": [],
        },
    )
    write_json(
        out / "eval_reports/final_qc_evidence_gate.json",
        {
            "schema": "automix-final-qc-evidence-gate-v1",
            "ready_for_delivery_qc": True,
            "ready_for_approval_readiness": True,
            "final_audio_path": str(final_audio),
            "blockers": [],
            "warnings": [],
        },
    )
    write_json(
        out / "eval_reports/final_ab_preview_manifest.json",
        {
            "schema": "automix-final-ab-preview-v1",
            "source_original": str(source),
            "source_final": str(final_audio),
            "output_path": str(preview),
            "created": True,
            "loudness_matched": True,
            "warnings": [],
        },
    )
    write_json(
        out / "eval_reports/ab_preview_evidence_gate.json",
        {
            "schema": "automix-ab-preview-evidence-gate-v1",
            "ready_for_human_ab_review": True,
            "ready_for_final_approval_request": True,
            "manifest_summary": {"source_final": str(final_audio), "output_path": str(preview)},
            "blockers": [],
            "warnings": [],
        },
    )
    write_json(
        out / "review/final_human_approval.json",
        {
            "schema": "automix-final-human-approval-v1",
            "approved": True,
            "approved_source": str(source),
            "approved_stage": "accepted_premaster_draft",
            "reviewed_final_audio_path": str(final_audio),
            "reviewed_ab_preview_path": str(preview),
            "warnings_acknowledged": ["all"],
        },
    )
    write_json(
        out / "eval_reports/final_approval_evidence_gate.json",
        {
            "schema": "automix-final-approval-evidence-gate-v1",
            "ready_for_delivery_request": True,
            "approved": True,
            "supporting_gate_summary": {"final_audio_path": str(final_audio), "ab_preview_output_path": str(preview)},
            "blockers": [],
            "warnings": [],
        },
    )
    write_json(
        out / "export/project_state_manifest.json",
        {
            "schema": "automix-project-state-manifest-v1",
            "original_tracks_protected": True,
            "master_unchanged": True,
            "accepted_sources": [str(source)],
        },
    )
    write_json(
        out / "eval_reports/rollback_evidence_gate.json",
        {
            "schema": "automix-rollback-evidence-gate-v1",
            "ready_for_delivery_readiness": True,
            "blockers": [],
            "warnings": [],
        },
    )
    write_json(
        out / "export/deliverable_package_manifest.json",
        {
            "schema": "automix-deliverable-package-manifest-v1",
            "zip_path": str(zip_path),
            "files_included": [str(final_audio), str(preview), str(readme)],
            "files_missing": [],
            "package_created": True,
            "package_size_bytes": zip_path.stat().st_size,
            "project_state_manifest": read_json(out / "export/project_state_manifest.json"),
            "warnings": [],
        },
    )
    write_json(
        out / "eval_reports/deliverable_package_evidence_gate.json",
        {
            "schema": "automix-deliverable-package-evidence-gate-v1",
            "ready_for_delivery_package": True,
            "ready_for_professional_readiness": True,
            "package_summary": {"zip_path": str(zip_path), "actual_zip_size_bytes": zip_path.stat().st_size},
            "zip_status": {"valid_zip": True},
            "blockers": [],
            "warnings": [],
        },
    )
    return {"source": source, "final_audio": final_audio, "preview": preview, "zip": zip_path}


def test_final_delivery_consistency_gate_blocks_missing_inputs_and_writes_request(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    gate = build_final_delivery_consistency_gate(project_name="unit", output_dir=out)
    assert gate["ready_for_delivery_consistency"] is False
    assert "final_export_state_missing_or_invalid" in gate["blockers"]
    assert (out / "review/final_delivery_consistency_manifest_template.json").exists()
    assert (out / "review/final_delivery_consistency_request.md").exists()


def test_final_delivery_consistency_gate_accepts_consistent_evidence(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    paths = write_consistent_delivery_evidence(out, tmp_path)
    gate = build_final_delivery_consistency_gate(project_name="unit", output_dir=out)
    assert gate["ready_for_delivery_consistency"] is True
    assert gate["blockers"] == []
    assert gate["final_audio_consistency"]["final_audio_path"] == str(paths["final_audio"])
    assert gate["package_consistency"]["final_audio_filename_included"] is True


def test_final_delivery_consistency_gate_blocks_final_audio_mismatch(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    write_consistent_delivery_evidence(out, tmp_path)
    other = write_file(tmp_path / "other_final.wav", b"other-final")
    qc = read_json(out / "eval_reports/final_qc_evidence_gate.json")
    qc["final_audio_path"] = str(other)
    write_json(out / "eval_reports/final_qc_evidence_gate.json", qc)
    gate = build_final_delivery_consistency_gate(project_name="unit", output_dir=out)
    assert gate["ready_for_delivery_consistency"] is False
    assert "final_qc_audio_mismatch_render_evidence_primary_wav" in gate["blockers"]


def test_final_delivery_consistency_gate_blocks_preview_and_approval_mismatch(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    paths = write_consistent_delivery_evidence(out, tmp_path)
    other_preview = write_file(tmp_path / "other_preview.wav", b"other-preview")
    approval = read_json(out / "review/final_human_approval.json")
    approval["reviewed_ab_preview_path"] = str(other_preview)
    approval["approved_stage"] = "accepted_recovery_draft"
    write_json(out / "review/final_human_approval.json", approval)
    gate = build_final_delivery_consistency_gate(project_name="unit", output_dir=out)
    assert "final_approval_reviewed_preview_mismatch_ab_preview" in gate["blockers"]
    assert "final_approval_stage_mismatch_final_export_state" in gate["blockers"]
    assert gate["ab_preview_consistency"]["preview_output_path"] == str(paths["preview"])


def test_final_delivery_consistency_gate_blocks_package_omissions_and_project_state_mismatch(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    write_consistent_delivery_evidence(out, tmp_path)
    package = read_json(out / "export/deliverable_package_manifest.json")
    package["files_included"] = [path for path in package["files_included"] if not path.endswith("unit_FINAL_MASTER.wav")]
    write_json(out / "export/deliverable_package_manifest.json", package)
    project_state = read_json(out / "export/project_state_manifest.json")
    project_state["accepted_sources"] = []
    write_json(out / "export/project_state_manifest.json", project_state)
    gate = build_final_delivery_consistency_gate(project_name="unit", output_dir=out)
    assert "final_audio_filename_not_listed_in_package_manifest" in gate["blockers"]
    assert "selected_export_source_not_recorded_in_project_state" in gate["blockers"]


def test_professional_readiness_requires_final_delivery_consistency_when_delivery_requested(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    write_consistent_delivery_evidence(out, tmp_path)
    audit = build_professional_readiness_audit(project_name="unit", output_dir=out, workspace_root=ROOT, final_delivery_requested=True)
    assert audit["ready_for_delivery"] is False
    assert "final_delivery_consistency_gate_missing" in audit["blockers"]
    build_final_delivery_consistency_gate(project_name="unit", output_dir=out)
    audit = build_professional_readiness_audit(project_name="unit", output_dir=out, workspace_root=ROOT, final_delivery_requested=True)
    assert "final_delivery_consistency_gate_missing" not in audit["blockers"]
    assert audit["final_delivery_consistency_gate_summary"]["ready_for_delivery_consistency"] is True


def test_final_delivery_consistency_gate_cli_require_ready_returns_nonzero_for_blockers(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/run_final_delivery_consistency_gate.py"),
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
    assert result.returncode == 2
    assert data["status"] == "blocked"
    assert "final_export_state_missing_or_invalid" in data["blockers"]
    assert Path(data["report_json"]).exists()


def test_report_index_groups_final_delivery_consistency_gate(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    build_final_delivery_consistency_gate(project_name="unit", output_dir=out)
    index = build_report_index(project_name="unit", output_dir=out, stage_results=[])
    assert any(item["stage"] == "delivery readiness" and item["summary"] == "final_delivery_consistency_gate.json" for item in index["reports"])


if __name__ == "__main__":
    current = globals()
    failures: list[str] = []
    for name in sorted(k for k in current if k.startswith("test_")):
        fn = current[name]
        try:
            with tempfile.TemporaryDirectory() as directory:
                fn(Path(directory))
        except Exception as exc:  # pragma: no cover
            failures.append(f"{name}: {exc}")
    if failures:
        raise SystemExit("\n".join(failures))
    print("Prompt68 direct tests passed")

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

from automix.orchestrator.deliverable_package_evidence_gate import build_deliverable_package_evidence_gate
from automix.orchestrator.professional_readiness_audit import build_professional_readiness_audit
from automix.orchestrator.report_index import build_report_index
from automix.plugins.plugin_adapter_schema import write_json


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_text(path: Path, text: str = "evidence\n") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def write_ready_supporting_evidence(out: Path) -> None:
    write_json(
        out / "export/final_render_manifest.json",
        {
            "schema": "automix-final-render-manifest-v1",
            "renders": [{"format": "wav", "path": str(out / "deliverables/final.wav"), "created": True, "size_bytes": 12}],
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
            "blockers": [],
            "warnings": [],
        },
    )
    write_json(out / "eval_reports/final_qc_metrics.json", {"schema": "automix-final-qc-metrics-v1", "qc_passed": True, "failures": []})
    write_json(
        out / "eval_reports/final_qc_evidence_gate.json",
        {
            "schema": "automix-final-qc-evidence-gate-v1",
            "ready_for_delivery_qc": True,
            "ready_for_approval_readiness": True,
            "blockers": [],
            "warnings": [],
        },
    )
    write_json(out / "eval_reports/final_ab_preview_manifest.json", {"schema": "automix-final-ab-preview-v1", "created": True, "loudness_matched": True})
    write_json(
        out / "eval_reports/ab_preview_evidence_gate.json",
        {
            "schema": "automix-ab-preview-evidence-gate-v1",
            "ready_for_human_ab_review": True,
            "ready_for_final_approval_request": True,
            "blockers": [],
            "warnings": [],
        },
    )
    write_json(out / "review/final_human_approval.json", {"schema": "automix-final-human-approval-v1", "approved": True})
    write_json(
        out / "eval_reports/final_approval_evidence_gate.json",
        {
            "schema": "automix-final-approval-evidence-gate-v1",
            "ready_for_delivery_request": True,
            "blockers": [],
            "warnings": [],
        },
    )
    write_json(
        out / "rollback/global_rollback_registry.json",
        {
            "schema": "automix-global-rollback-registry-v1",
            "original_tracks_protected": True,
            "original_master_protected": True,
            "validation": {"passed": True, "failures": [], "warnings": []},
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
    write_text(out / "eval_reports/final_qc_report.md", "# Final QC\n")
    write_json(
        out / "export/project_state_manifest.json",
        {
            "schema": "automix-project-state-manifest-v1",
            "original_tracks_protected": True,
            "master_unchanged": True,
            "accepted_sources": [],
        },
    )
    write_text(out / "export/plugin_mapping_summary.md", "# Plugin Mapping Summary\n")


def write_valid_package_manifest(out: Path, *, zip_name: str = "unit_DELIVERABLES.zip", extra_included: list[Path] | None = None) -> Path:
    write_ready_supporting_evidence(out)
    delivery_file = write_text(out / "deliverables/unit/README_DELIVERY.md", "# Delivery\n")
    extra_included = extra_included or []
    zip_path = out / "deliverables" / zip_name
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.write(delivery_file, arcname="unit/README_DELIVERY.md")
        for path in extra_included:
            archive.write(path, arcname=path.name)
    project_state = read_json(out / "export/project_state_manifest.json")
    write_json(
        out / "export/deliverable_package_manifest.json",
        {
            "schema": "automix-deliverable-package-manifest-v1",
            "zip_path": str(zip_path),
            "files_included": [str(delivery_file), *(str(path) for path in extra_included)],
            "files_missing": [],
            "package_created": True,
            "package_size_bytes": zip_path.stat().st_size,
            "project_state_manifest": project_state,
            "warnings": [],
        },
    )
    return zip_path


def test_deliverable_package_evidence_gate_blocks_missing_manifest_and_writes_request(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    gate = build_deliverable_package_evidence_gate(project_name="unit", output_dir=out)
    assert gate["ready_for_delivery_package"] is False
    assert "deliverable_package_manifest_missing_or_invalid" in gate["blockers"]
    assert (out / "review/deliverable_package_evidence_manifest_template.json").exists()
    assert (out / "review/deliverable_package_evidence_request.md").exists()


def test_deliverable_package_evidence_gate_accepts_valid_package_and_supporting_evidence(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    zip_path = write_valid_package_manifest(out)
    gate = build_deliverable_package_evidence_gate(project_name="unit", output_dir=out)
    assert gate["ready_for_delivery_package"] is True
    assert gate["ready_for_professional_readiness"] is True
    assert gate["zip_status"]["valid_zip"] is True
    assert gate["package_summary"]["actual_zip_size_bytes"] == zip_path.stat().st_size
    assert gate["blockers"] == []


def test_deliverable_package_evidence_gate_blocks_zip_not_created_missing_zip_and_files_missing(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    write_ready_supporting_evidence(out)
    write_json(
        out / "export/deliverable_package_manifest.json",
        {
            "schema": "automix-deliverable-package-manifest-v1",
            "zip_path": str(tmp_path / "missing.zip"),
            "files_included": [],
            "files_missing": ["automix/eval_reports/final_qc_report.md"],
            "package_created": False,
            "package_size_bytes": 0,
            "project_state_manifest": read_json(out / "export/project_state_manifest.json"),
        },
    )
    gate = build_deliverable_package_evidence_gate(project_name="unit", output_dir=out)
    assert gate["ready_for_delivery_package"] is False
    assert "deliverable_package_not_created" in gate["blockers"]
    assert "deliverable_zip_missing" in gate["blockers"]
    assert "deliverable_package_manifest_has_missing_files" in gate["blockers"]
    assert "deliverable_package_included_files_missing" in gate["blockers"]


def test_deliverable_package_evidence_gate_blocks_size_mismatch_and_missing_included_file(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    zip_path = write_valid_package_manifest(out)
    manifest = read_json(out / "export/deliverable_package_manifest.json")
    manifest["package_size_bytes"] = zip_path.stat().st_size + 9
    manifest["files_included"].append(str(tmp_path / "missing-report.md"))
    write_json(out / "export/deliverable_package_manifest.json", manifest)
    gate = build_deliverable_package_evidence_gate(project_name="unit", output_dir=out)
    assert "deliverable_package_size_mismatch" in gate["blockers"]
    assert any(item.startswith("included_file_missing:") for item in gate["blockers"])


def test_deliverable_package_evidence_gate_blocks_unsafe_naming_and_secret_paths(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    secret = write_text(out / "deliverables/.env", "TOKEN=redacted\n")
    write_valid_package_manifest(out, zip_name="unit_UNSAFE_REVIEW_COPY_FINAL_SAFE.zip", extra_included=[secret])
    manifest = read_json(out / "export/deliverable_package_manifest.json")
    manifest["unsafe_override"] = True
    write_json(out / "export/deliverable_package_manifest.json", manifest)
    gate = build_deliverable_package_evidence_gate(project_name="unit", output_dir=out)
    assert "unsafe_review_copy_named_final_safe" in gate["blockers"]
    assert any(item.startswith("sensitive_or_secret_file_included:") for item in gate["blockers"])


def test_professional_readiness_requires_deliverable_package_evidence_when_delivery_requested(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    write_valid_package_manifest(out)
    audit = build_professional_readiness_audit(project_name="unit", output_dir=out, workspace_root=ROOT, final_delivery_requested=True)
    assert audit["ready_for_delivery"] is False
    assert "deliverable_package_evidence_gate_missing" in audit["blockers"]
    build_deliverable_package_evidence_gate(project_name="unit", output_dir=out)
    audit = build_professional_readiness_audit(project_name="unit", output_dir=out, workspace_root=ROOT, final_delivery_requested=True)
    assert "deliverable_package_evidence_gate_missing" not in audit["blockers"]
    assert audit["deliverable_package_evidence_gate_summary"]["ready_for_delivery_package"] is True


def test_deliverable_package_evidence_gate_cli_require_ready_returns_nonzero_for_blockers(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/run_deliverable_package_evidence_gate.py"),
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
    assert "deliverable_package_manifest_missing_or_invalid" in data["blockers"]
    assert Path(data["report_json"]).exists()


def test_report_index_groups_deliverable_package_evidence_gate(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    build_deliverable_package_evidence_gate(project_name="unit", output_dir=out)
    index = build_report_index(project_name="unit", output_dir=out, stage_results=[])
    assert any(item["stage"] == "final export" and item["summary"] == "deliverable_package_evidence_gate.json" for item in index["reports"])


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
    print("Prompt67 direct tests passed")

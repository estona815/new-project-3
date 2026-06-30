from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from automix.export.final_export_state_resolver import resolve_final_export_state
from automix.export.deliverable_packager import create_deliverables_folder, package_deliverables, write_plugin_mapping_summary
from automix.analyze_ai_pitch_source import write_json
from automix.orchestrator.automix_orchestrator import AutoMixOrchestrator
from automix.orchestrator.stage_status import StageStatus

from tests.automix_validation.prompt41_validation_common import MOCK_PROJECTS, ROOT, ensure_prompt41_fixtures


def test_final_export_state_prefers_accepted_premaster(tmp_path: Path) -> None:
    source = tmp_path / "accepted.wav"
    source.write_bytes(b"RIFF----WAVE")
    state = resolve_final_export_state(
        project_name="prompt41",
        workflow_state={
            "premaster": {
                "accepted": True,
                "status": "accepted",
                "source_path": str(source),
                "review_required": False,
                "ab_required": False,
            },
            "vocal_placement": {
                "accepted": True,
                "status": "accepted",
                "source_path": str(tmp_path / "placement.wav"),
            },
        },
        output_path=tmp_path / "state.json",
    )
    assert state["selected_export_stage"] == "accepted_premaster_draft"
    assert state["safe_to_export"] is True


def test_final_delivery_blocks_without_approval(tmp_path: Path) -> None:
    ensure_prompt41_fixtures()
    out = tmp_path / "automix"
    manifest = AutoMixOrchestrator(
        {
            "project_path": str(MOCK_PROJECTS / "prompt41_export_block_test.json"),
            "output_dir": str(out),
            "mode": "final_delivery",
            "allow_final_export": True,
            "final_approval_explicit": False,
        }
    ).run()
    st = {result["stage"]: result["status"] for result in manifest["stage_results"]}
    assert manifest["safe_to_export"] is False
    assert st["final_export_state_resolver"] == StageStatus.REQUIRES_APPROVAL.value
    assert st["deliverable_package"] == StageStatus.BLOCKED.value


def test_approval_does_not_override_qc_failure_or_missing_source(tmp_path: Path) -> None:
    ensure_prompt41_fixtures()
    manifest = AutoMixOrchestrator(
        {
            "project_path": str(MOCK_PROJECTS / "prompt41_export_block_test.json"),
            "output_dir": str(tmp_path / "automix"),
            "mode": "final_delivery",
            "allow_final_export": True,
            "final_approval_explicit": True,
        }
    ).run()
    st = {result["stage"]: result["status"] for result in manifest["stage_results"]}
    assert manifest["global_status"] == "final_delivery_failed"
    assert manifest["safe_to_export"] is False
    assert st["final_export"] == StageStatus.BLOCKED.value


def test_cli_scan_only_and_final_delivery_blocks(tmp_path: Path) -> None:
    ensure_prompt41_fixtures()
    scan = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/run_automix_orchestrator.py"),
            "--project",
            str(MOCK_PROJECTS / "prompt41_scan_only_test.json"),
            "--mode",
            "scan_only",
            "--dry-run",
            "--output-dir",
            str(tmp_path / "scan" / "automix"),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    assert json.loads(scan.stdout)["status"] == "scan_complete"
    final = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/run_automix_orchestrator.py"),
            "--project",
            str(MOCK_PROJECTS / "prompt41_export_block_test.json"),
            "--mode",
            "final_delivery",
            "--allow-final-export",
            "--output-dir",
            str(tmp_path / "final" / "automix"),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    data = json.loads(final.stdout)
    assert data["status"] == "final_delivery_failed"
    assert data["final_export_blocked_without_approval"] is True


def test_review_package_smoke_preserves_reports_and_rollback(tmp_path: Path) -> None:
    ensure_prompt41_fixtures()
    out = tmp_path / "automix"
    deliverables = create_deliverables_folder(tmp_path / "deliverables", "prompt41_test")
    source = ROOT / "tests/automix_validation/fixtures/audio/raw_vocal_like_mono.wav"
    render_manifest = {
        "schema": "automix-final-render-manifest-v1",
        "renders": [
            {
                "format": "wav",
                "bit_depth": 24,
                "sample_rate": 48000,
                "path": str(source),
                "created": True,
                "size_bytes": source.stat().st_size,
            }
        ],
        "failures": [],
        "warnings": ["prompt41 synthetic review package smoke; not a production final"],
    }
    export_state = {
        "selected_export_source": str(source),
        "selected_export_stage": "accepted_premaster_draft",
        "safe_to_export": True,
        "warnings": [],
    }
    qc_metrics = {"schema": "prompt41-mock-qc-v1", "qc_passed": True, "warnings": ["mock QC only"]}
    write_json(out / "export/final_render_manifest.json", render_manifest)
    write_json(out / "eval_reports/final_qc_metrics.json", qc_metrics)
    (out / "eval_reports").mkdir(parents=True, exist_ok=True)
    (out / "eval_reports/final_qc_report.md").write_text("# Prompt41 Mock QC\n\nMock package smoke only.\n", encoding="utf-8")
    write_json(out / "rollback/prompt41_mock_rollback.json", {"stage": "premaster", "safe_to_rollback": True})
    plugin_summary = write_plugin_mapping_summary(out)
    package = package_deliverables(
        project_name="prompt41_test",
        deliverables_dir=deliverables,
        output_dir=out,
        export_state=export_state,
        render_manifest=render_manifest,
        qc_metrics=qc_metrics,
        create_zip=True,
    )
    assert package["package_created"] is True
    assert Path(package["zip_path"]).exists()
    assert any("plugin_mapping_summary.md" in path for path in package["files_included"])
    assert plugin_summary.exists()

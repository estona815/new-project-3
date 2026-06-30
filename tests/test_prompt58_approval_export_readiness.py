from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from automix.orchestrator.approval_export_readiness import build_approval_export_readiness
from automix.orchestrator.ab_preview_evidence_gate import build_ab_preview_evidence_gate
from automix.orchestrator.final_approval_evidence_gate import build_final_approval_evidence_gate
from automix.orchestrator.final_qc_evidence_gate import build_final_qc_evidence_gate
from automix.orchestrator.final_render_evidence_gate import build_final_render_evidence_gate
from automix.orchestrator.rollback_evidence_gate import build_rollback_evidence_gate
from automix.orchestrator.report_index import build_report_index
from automix.analyze_ai_pitch_source import AudioData
from automix.export.audio_export_utils import wav_info, write_pcm_wav
from automix.plugins.plugin_adapter_schema import write_json


def write_blocked_evidence(out: Path) -> None:
    write_json(
        out / "export/final_export_state.json",
        {
            "schema": "automix-final-export-state-v1",
            "project_name": "unit",
            "selected_export_source": "",
            "selected_export_stage": "",
            "blocked_reasons": ["no_accepted_export_source"],
            "safe_to_export": False,
            "warnings": [],
        },
    )
    write_json(
        out / "eval_reports/final_ab_preview_manifest.json",
        {
            "schema": "automix-final-ab-preview-v1",
            "created": False,
            "loudness_matched": False,
            "output_path": "",
            "warnings": ["ab_preview_not_requested_or_missing_sources"],
        },
    )
    build_ab_preview_evidence_gate(project_name="unit", output_dir=out)
    write_json(
        out / "export/final_render_manifest.json",
        {
            "schema": "automix-final-render-manifest-v1",
            "project_name": "unit",
            "renders": [],
            "failures": [],
            "warnings": ["diagnostic/report-only mode; no final audio rendered"],
        },
    )
    build_final_render_evidence_gate(project_name="unit", output_dir=out)
    write_json(
        out / "review/final_human_approval.json",
        {
            "schema": "automix-final-human-approval-v1",
            "approved": False,
            "approved_stage": "",
            "approved_source": "",
            "warnings_acknowledged": [],
        },
    )
    write_json(
        out / "export/project_state_manifest.json",
        {
            "schema": "automix-project-state-manifest-v1",
            "original_tracks_protected": True,
            "master_unchanged": True,
            "accepted_sources": [],
        },
    )


def write_ready_except_approval(out: Path, tmp_path: Path, *, approved: bool = False) -> Path:
    source = tmp_path / "accepted.wav"
    render = tmp_path / "render.wav"
    preview = tmp_path / "preview.wav"
    frames = [[0.1, 0.09] for _ in range(4800)]
    write_pcm_wav(source, AudioData(sample_rate=48000, channels=2, frames=frames), bit_depth=24)
    write_pcm_wav(render, AudioData(sample_rate=48000, channels=2, frames=frames), bit_depth=24)
    write_pcm_wav(preview, AudioData(sample_rate=48000, channels=2, frames=frames), bit_depth=24)
    write_json(
        out / "export/final_export_state.json",
        {
            "schema": "automix-final-export-state-v1",
            "project_name": "unit",
            "selected_export_source": str(source),
            "selected_export_stage": "accepted_premaster_draft",
            "blocked_reasons": [],
            "safe_to_export": True,
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
            "created": True,
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
            "warnings": [],
        },
    )
    write_json(
        out / "export/final_render_manifest.json",
        {
            "schema": "automix-final-render-manifest-v1",
            "project_name": "unit",
            "source_stage": "accepted_premaster_draft",
            "render_settings": {"normalization": False, "hidden_limiter": False, "source_must_come_from_resolver": True},
            "renders": [{"format": "wav", "path": str(render), "created": True, "size_bytes": render.stat().st_size, "sample_rate": 48000, "bit_depth": 24, "normalization_applied": False, "hidden_limiter_added": False}],
            "failures": [],
            "warnings": [],
        },
    )
    build_final_render_evidence_gate(project_name="unit", output_dir=out)
    info = wav_info(render)
    write_json(
        out / "eval_reports/final_qc_metrics.json",
        {
            "schema": "automix-final-qc-metrics-v1",
            "final_audio_path": str(render),
            "file_integrity": {
                "exists": True,
                "size_bytes": info["size_bytes"],
                "duration_seconds": round(float(info["duration_seconds"]), 6),
                "sample_rate": info["sample_rate"],
                "bit_depth": info["bit_depth"],
                "channels": info["channels"],
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
        out / "review/final_human_approval.json",
        {
            "schema": "automix-final-human-approval-v1",
            "approved": approved,
            "approved_stage": "accepted_premaster_draft" if approved else "",
            "approved_source": str(source) if approved else "",
            "warnings_acknowledged": ["all"] if approved else [],
            "approval_time": "2026-06-03T00:00:00Z" if approved else "",
            "approved_by": "user",
            "review_decision": "accepted" if approved else "pending",
            "loudness_matched_ab_reviewed": approved,
            "final_audio_accepted_at_matched_loudness": approved,
            "reviewed_ab_preview_path": str(preview) if approved else "",
            "reviewed_final_audio_path": str(render) if approved else "",
            "final_qc_evidence_reviewed": approved,
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
    build_ab_preview_evidence_gate(project_name="unit", output_dir=out)
    rollback = tmp_path / "rollback.json"
    write_json(rollback, {"schema": "unit-rollback-v1"})
    write_json(
        out / "rollback/global_rollback_registry.json",
        {
            "schema": "automix-global-rollback-registry-v1",
            "project_name": "unit",
            "applied_stages": ["premaster"],
            "original_tracks_protected": True,
            "original_master_protected": True,
            "rollback_entries": [{"stage": "premaster", "rollback_file": str(rollback), "safe_to_rollback": True}],
            "validation": {"passed": True, "failures": [], "warnings": []},
            "warnings": [],
        },
    )
    build_rollback_evidence_gate(project_name="unit", output_dir=out)
    if approved:
        build_final_approval_evidence_gate(project_name="unit", output_dir=out)
    return source


def test_approval_export_readiness_blocks_missing_source_preview_and_approval(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    write_blocked_evidence(out)
    audit = build_approval_export_readiness(project_name="unit", output_dir=out)
    assert audit["ready_for_delivery_request"] is False
    assert audit["ready_for_human_approval_request"] is False
    assert "accepted_export_source_missing" in audit["blockers"]
    assert "ab_preview_missing_or_not_loudness_matched" in audit["blockers"]
    assert "final_human_approval_missing" in audit["blockers"]
    assert "final_render_missing_or_diagnostic_only" in audit["blockers"]
    assert (out / "eval_reports/approval_export_readiness.json").exists()
    assert (out / "eval_reports/approval_export_readiness.md").exists()
    assert (out / "review/final_approval_request.md").exists()


def test_approval_export_readiness_identifies_approval_only_state(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    write_ready_except_approval(out, tmp_path, approved=False)
    audit = build_approval_export_readiness(project_name="unit", output_dir=out)
    assert audit["readiness_status"] == "ready_for_human_approval_request"
    assert audit["ready_for_delivery_request"] is False
    assert audit["ready_for_human_approval_request"] is True
    assert audit["blockers"] == ["final_human_approval_missing"]
    approval_request = (out / "review/final_approval_request.md").read_text(encoding="utf-8")
    assert "no approval is recorded yet" in approval_request


def test_approval_export_readiness_passes_after_matching_human_approval(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    write_ready_except_approval(out, tmp_path, approved=True)
    audit = build_approval_export_readiness(project_name="unit", output_dir=out)
    assert audit["readiness_status"] == "ready_for_delivery_request"
    assert audit["ready_for_delivery_request"] is True
    assert audit["blockers"] == []
    assert audit["approval_summary"]["approved"] is True


def test_approval_export_readiness_cli_require_ready_returns_nonzero_for_blockers(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    write_blocked_evidence(out)
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/run_approval_export_readiness.py"),
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
    assert "accepted_export_source_missing" in data["blockers"]
    assert Path(data["report_json"]).exists()


def test_report_index_groups_approval_export_readiness(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    write_blocked_evidence(out)
    build_approval_export_readiness(project_name="unit", output_dir=out)
    index = build_report_index(project_name="unit", output_dir=out, stage_results=[])
    assert any(item["stage"] == "delivery readiness" and item["summary"] == "approval_export_readiness.json" for item in index["reports"])


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
    print("Prompt58 direct tests passed")

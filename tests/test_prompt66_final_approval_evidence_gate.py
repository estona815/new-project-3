from __future__ import annotations

import json
import math
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from automix.analyze_ai_pitch_source import AudioData
from automix.export.audio_export_utils import wav_info, write_pcm_wav
from automix.export.human_approval_gate import build_human_approval
from automix.orchestrator.ab_preview_evidence_gate import build_ab_preview_evidence_gate
from automix.orchestrator.approval_export_readiness import build_approval_export_readiness
from automix.orchestrator.final_approval_evidence_gate import build_final_approval_evidence_gate
from automix.orchestrator.final_qc_evidence_gate import build_final_qc_evidence_gate
from automix.orchestrator.final_render_evidence_gate import build_final_render_evidence_gate
from automix.orchestrator.report_index import build_report_index
from automix.orchestrator.rollback_evidence_gate import build_rollback_evidence_gate
from automix.plugins.plugin_adapter_schema import write_json


def make_audio(path: Path, *, amp: float = 0.10, freq: float = 220.0, seconds: float = 0.25) -> Path:
    sample_rate = 48000
    frames = []
    for index in range(int(sample_rate * seconds)):
        t = index / sample_rate
        value = math.sin(2.0 * math.pi * freq * t) * amp
        frames.append([value, value * 0.9])
    write_pcm_wav(path, AudioData(sample_rate=sample_rate, channels=2, frames=frames), bit_depth=24)
    return path


def write_qc(out: Path, render: Path) -> None:
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


def write_ready_technical_evidence(out: Path, tmp_path: Path) -> tuple[Path, Path, Path]:
    source = make_audio(tmp_path / "accepted.wav", amp=0.10)
    original = make_audio(tmp_path / "original.wav", amp=0.12, freq=180.0)
    render = make_audio(tmp_path / "render.wav", amp=0.08)
    preview = make_audio(tmp_path / "preview.wav", amp=0.09)
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
        out / "export/final_render_manifest.json",
        {
            "schema": "automix-final-render-manifest-v1",
            "project_name": "unit",
            "source_stage": "accepted_premaster_draft",
            "render_settings": {"normalization": False, "hidden_limiter": False, "source_must_come_from_resolver": True},
            "renders": [{"format": "wav", "sample_rate": 48000, "bit_depth": 24, "path": str(render), "created": True, "size_bytes": render.stat().st_size, "normalization_applied": False, "hidden_limiter_added": False}],
            "failures": [],
            "warnings": [],
        },
    )
    build_final_render_evidence_gate(project_name="unit", output_dir=out)
    write_qc(out, render)
    build_final_qc_evidence_gate(project_name="unit", output_dir=out)
    write_json(
        out / "eval_reports/final_ab_preview_manifest.json",
        {
            "schema": "automix-final-ab-preview-v1",
            "source_original": str(original),
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
    build_ab_preview_evidence_gate(project_name="unit", output_dir=out)
    return source, render, preview


def write_project_and_rollback(out: Path, tmp_path: Path, source: Path) -> None:
    write_json(
        out / "export/project_state_manifest.json",
        {
            "schema": "automix-project-state-manifest-v1",
            "original_tracks_protected": True,
            "master_unchanged": True,
            "accepted_sources": [str(source)],
        },
    )
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


def write_approval(out: Path, source: Path, render: Path, preview: Path, *, approved: bool = True, complete: bool = True) -> None:
    build_human_approval(
        approved=approved,
        approved_stage="accepted_premaster_draft" if approved else "",
        approved_source=str(source) if approved else "",
        warnings_acknowledged=["all"] if approved else [],
        loudness_matched_ab_reviewed=complete,
        final_audio_accepted_at_matched_loudness=complete,
        reviewed_ab_preview_path=str(preview) if complete else "",
        reviewed_final_audio_path=str(render) if complete else "",
        final_qc_evidence_reviewed=complete,
        output_path=out / "review/final_human_approval.json",
    )


def test_final_approval_evidence_gate_blocks_missing_inputs_and_writes_request(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    gate = build_final_approval_evidence_gate(project_name="unit", output_dir=out)
    assert gate["ready_for_delivery_request"] is False
    assert "final_human_approval_missing_or_invalid" in gate["blockers"]
    assert "ab_preview_evidence_gate_missing_or_invalid" in gate["blockers"]
    assert (out / "review/final_approval_evidence_manifest_template.json").exists()
    assert (out / "review/final_approval_evidence_request.md").exists()


def test_final_approval_evidence_gate_reports_approval_pending_only_when_technical_evidence_ready(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    source, render, preview = write_ready_technical_evidence(out, tmp_path)
    write_approval(out, source, render, preview, approved=False)
    gate = build_final_approval_evidence_gate(project_name="unit", output_dir=out)
    assert gate["ready_for_delivery_request"] is False
    assert gate["approval_pending_only"] is True
    assert gate["blockers"] == ["final_human_approval_missing"]


def test_final_approval_evidence_gate_accepts_matched_loudness_review_record(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    source, render, preview = write_ready_technical_evidence(out, tmp_path)
    write_approval(out, source, render, preview)
    gate = build_final_approval_evidence_gate(project_name="unit", output_dir=out)
    assert gate["ready_for_delivery_request"] is True
    assert gate["approved"] is True
    assert gate["review_decision"] == "accepted"
    assert gate["blockers"] == []


def test_final_approval_evidence_gate_rejects_incomplete_approval_record(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    source, render, preview = write_ready_technical_evidence(out, tmp_path)
    write_approval(out, source, render, preview, complete=False)
    gate = build_final_approval_evidence_gate(project_name="unit", output_dir=out)
    assert gate["ready_for_delivery_request"] is False
    assert "loudness_matched_ab_review_not_recorded" in gate["blockers"]
    assert "final_audio_not_accepted_at_matched_loudness" in gate["blockers"]
    assert "reviewed_ab_preview_path_missing" in gate["blockers"]
    assert "reviewed_final_audio_path_missing" in gate["blockers"]
    assert "final_qc_evidence_not_reviewed_by_human" in gate["blockers"]


def test_approval_export_readiness_requires_final_approval_evidence_when_approved(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    source, render, preview = write_ready_technical_evidence(out, tmp_path)
    write_project_and_rollback(out, tmp_path, source)
    write_approval(out, source, render, preview)

    missing_gate = build_approval_export_readiness(project_name="unit", output_dir=out)
    assert "final_approval_evidence_gate_missing_or_invalid" in missing_gate["blockers"]

    build_final_approval_evidence_gate(project_name="unit", output_dir=out)
    ready = build_approval_export_readiness(project_name="unit", output_dir=out)
    assert ready["ready_for_delivery_request"] is True
    assert ready["blockers"] == []


def test_final_approval_evidence_gate_cli_require_ready_returns_nonzero_for_blockers(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/run_final_approval_evidence_gate.py"),
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
    assert "final_human_approval_missing_or_invalid" in data["blockers"]
    assert Path(data["report_json"]).exists()


def test_report_index_groups_final_approval_evidence_gate(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    build_final_approval_evidence_gate(project_name="unit", output_dir=out)
    index = build_report_index(project_name="unit", output_dir=out, stage_results=[])
    assert any(item["stage"] == "delivery readiness" and item["summary"] == "final_approval_evidence_gate.json" for item in index["reports"])


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
    print("Prompt66 direct tests passed")

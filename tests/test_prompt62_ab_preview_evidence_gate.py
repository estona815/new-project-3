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
from automix.export.ab_preview_montage import generate_ab_preview_montage
from automix.export.audio_export_utils import write_pcm_wav
from automix.orchestrator.ab_preview_evidence_gate import build_ab_preview_evidence_gate
from automix.orchestrator.approval_export_readiness import build_approval_export_readiness
from automix.orchestrator.final_qc_evidence_gate import build_final_qc_evidence_gate
from automix.orchestrator.final_render_evidence_gate import build_final_render_evidence_gate
from automix.orchestrator.rollback_evidence_gate import build_rollback_evidence_gate
from automix.orchestrator.report_index import build_report_index
from automix.plugins.plugin_adapter_schema import write_json


def make_audio(path: Path, *, amp: float = 0.2, freq: float = 220.0, seconds: float = 0.25) -> Path:
    sample_rate = 48000
    frames = []
    for index in range(int(sample_rate * seconds)):
        t = index / sample_rate
        value = math.sin(2.0 * math.pi * freq * t) * amp
        frames.append([value, value * 0.9])
    write_pcm_wav(path, AudioData(sample_rate=sample_rate, channels=2, frames=frames), bit_depth=24)
    return path


def write_render_manifest(out: Path, render: Path) -> None:
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


def write_final_qc(out: Path, render: Path) -> None:
    write_json(
        out / "eval_reports/final_qc_metrics.json",
        {
            "schema": "automix-final-qc-metrics-v1",
            "final_audio_path": str(render),
            "file_integrity": {
                "exists": True,
                "size_bytes": render.stat().st_size,
                "duration_seconds": 0.25,
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


def write_ready_preview(out: Path, tmp_path: Path) -> tuple[Path, Path, Path]:
    original = make_audio(tmp_path / "original.wav", amp=0.22, freq=180.0)
    final = make_audio(tmp_path / "final.wav", amp=0.08, freq=220.0)
    write_render_manifest(out, final)
    preview_manifest = generate_ab_preview_montage(
        project_name="unit",
        original_mix_path=original,
        final_audio_path=final,
        output_dir=out,
        deliverables_dir=tmp_path / "deliverables/unit",
        export_state={"safe_to_export": True},
        segment_seconds=0.1,
    )
    return original, final, Path(preview_manifest["output_path"])


def test_ab_preview_evidence_gate_blocks_missing_manifest_and_writes_request(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    gate = build_ab_preview_evidence_gate(project_name="unit", output_dir=out)
    assert gate["ready_for_human_ab_review"] is False
    assert "final_ab_preview_manifest_missing_or_invalid" in gate["blockers"]
    assert "ab_preview_loudness_match_metrics_missing" in gate["blockers"]
    assert (out / "review/ab_preview_review_manifest_template.json").exists()
    assert (out / "review/ab_preview_review_request.md").exists()


def test_ab_preview_evidence_gate_accepts_generated_measured_preview(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    write_ready_preview(out, tmp_path)
    gate = build_ab_preview_evidence_gate(project_name="unit", output_dir=out)
    assert gate["ready_for_human_ab_review"] is True
    assert gate["ready_for_final_approval_request"] is True
    assert gate["human_ab_review_recorded"] is False
    assert gate["loudness_match_status"]["metrics_present"] is True
    assert gate["loudness_match_status"]["delta_db_after_match"] <= 0.25
    assert gate["blockers"] == []


def test_ab_preview_evidence_gate_rejects_legacy_loudness_boolean_without_metrics(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    original = make_audio(tmp_path / "original.wav")
    final = make_audio(tmp_path / "final.wav")
    preview = make_audio(tmp_path / "preview.wav")
    write_render_manifest(out, final)
    write_json(
        out / "eval_reports/final_ab_preview_manifest.json",
        {
            "schema": "automix-final-ab-preview-v1",
            "source_original": str(original),
            "source_final": str(final),
            "segments": [
                {"label": "original_mix", "duration_seconds": 0.1},
                {"label": "final_processed", "duration_seconds": 0.1},
            ],
            "created": True,
            "loudness_matched": True,
            "output_path": str(preview),
            "warnings": [],
        },
    )
    gate = build_ab_preview_evidence_gate(project_name="unit", output_dir=out)
    assert gate["ready_for_human_ab_review"] is False
    assert "ab_preview_loudness_match_metrics_missing" in gate["blockers"]

    legacy = build_ab_preview_evidence_gate(project_name="unit", output_dir=out, allow_legacy_loudness_flag=True)
    assert legacy["ready_for_human_ab_review"] is True
    assert "ab_preview_loudness_match_metrics_missing_legacy_flag_used" in legacy["warnings"]


def test_ab_preview_evidence_gate_blocks_final_source_not_linked_to_render_manifest(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    original, final, _preview = write_ready_preview(out, tmp_path)
    other = make_audio(tmp_path / "other_render.wav")
    write_render_manifest(out, other)
    gate = build_ab_preview_evidence_gate(project_name="unit", output_dir=out)
    assert gate["ready_for_human_ab_review"] is False
    assert gate["render_manifest_link"]["source_final_in_render_manifest"] is False
    assert "ab_preview_final_not_in_render_manifest" in gate["blockers"]
    assert original.exists()


def test_approval_export_readiness_requires_ab_preview_evidence_gate(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    source = make_audio(tmp_path / "accepted.wav")
    _original, render, _preview = write_ready_preview(out, tmp_path)
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
        out / "export/project_state_manifest.json",
        {
            "schema": "automix-project-state-manifest-v1",
            "original_tracks_protected": True,
            "master_unchanged": True,
            "accepted_sources": [str(source)],
        },
    )
    write_json(
        out / "review/final_human_approval.json",
        {"schema": "automix-final-human-approval-v1", "approved": False, "approved_stage": "", "approved_source": ""},
    )

    missing_gate = build_approval_export_readiness(project_name="unit", output_dir=out)
    assert "ab_preview_evidence_gate_missing_or_invalid" in missing_gate["blockers"]
    assert "ab_preview_evidence_not_ready" in missing_gate["blockers"]

    build_ab_preview_evidence_gate(project_name="unit", output_dir=out)
    build_final_render_evidence_gate(project_name="unit", output_dir=out)
    write_final_qc(out, render)
    build_final_qc_evidence_gate(project_name="unit", output_dir=out)
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
    ready_for_approval = build_approval_export_readiness(project_name="unit", output_dir=out)
    assert ready_for_approval["ready_for_human_approval_request"] is True
    assert ready_for_approval["blockers"] == ["final_human_approval_missing"]
    assert render.exists()


def test_ab_preview_evidence_gate_cli_require_ready_returns_nonzero_for_blockers(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/run_ab_preview_evidence_gate.py"),
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
    assert "final_ab_preview_manifest_missing_or_invalid" in data["blockers"]
    assert Path(data["report_json"]).exists()


def test_report_index_groups_ab_preview_evidence_gate(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    build_ab_preview_evidence_gate(project_name="unit", output_dir=out)
    index = build_report_index(project_name="unit", output_dir=out, stage_results=[])
    assert any(item["stage"] == "delivery readiness" and item["summary"] == "ab_preview_evidence_gate.json" for item in index["reports"])


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
    print("Prompt62 direct tests passed")

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
from automix.orchestrator.report_index import build_report_index
from automix.orchestrator.rollback_evidence_gate import build_rollback_evidence_gate
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


def write_export_state(out: Path, source: Path, *, safe: bool = True) -> None:
    write_json(
        out / "export/final_export_state.json",
        {
            "schema": "automix-final-export-state-v1",
            "project_name": "unit",
            "selected_export_source": str(source),
            "selected_export_stage": "accepted_premaster_draft",
            "blocked_reasons": [] if safe else ["no_accepted_export_source"],
            "safe_to_export": safe,
            "warnings": [],
        },
    )


def write_render_manifest(out: Path, render: Path, *, source_stage: str = "accepted_premaster_draft", extra: dict | None = None) -> None:
    item = {
        "format": "wav",
        "sample_rate": 48000,
        "bit_depth": 24,
        "path": str(render),
        "created": True,
        "size_bytes": render.stat().st_size if render.exists() else 12,
        "normalization_applied": False,
        "hidden_limiter_added": False,
    }
    if extra:
        item.update(extra)
    write_json(
        out / "export/final_render_manifest.json",
        {
            "schema": "automix-final-render-manifest-v1",
            "project_name": "unit",
            "export_profile": "professional_master_delivery",
            "source_stage": source_stage,
            "render_settings": {"normalization": False, "hidden_limiter": False, "source_must_come_from_resolver": True},
            "renders": [item],
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


def write_ready_render(out: Path, tmp_path: Path) -> tuple[Path, Path]:
    source = make_audio(tmp_path / "accepted.wav", amp=0.18)
    render = make_audio(tmp_path / "render.wav", amp=0.16)
    write_export_state(out, source)
    write_render_manifest(out, render)
    return source, render


def test_final_render_evidence_gate_blocks_missing_manifests_and_writes_request(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    gate = build_final_render_evidence_gate(project_name="unit", output_dir=out)
    assert gate["ready_for_final_qc"] is False
    assert "final_render_manifest_missing_or_invalid" in gate["blockers"]
    assert "final_export_state_missing_or_invalid" in gate["blockers"]
    assert "primary_wav_render_missing" in gate["blockers"]
    assert (out / "review/final_render_evidence_manifest_template.json").exists()
    assert (out / "review/final_render_evidence_request.md").exists()


def test_final_render_evidence_gate_accepts_valid_primary_wav(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    _source, render = write_ready_render(out, tmp_path)
    gate = build_final_render_evidence_gate(project_name="unit", output_dir=out)
    assert gate["ready_for_final_qc"] is True
    assert gate["ready_for_approval_readiness"] is True
    assert gate["primary_wav_path"] == str(render)
    assert gate["blockers"] == []


def test_final_render_evidence_gate_rejects_diagnostic_report_only_manifest(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    source = make_audio(tmp_path / "accepted.wav")
    write_export_state(out, source)
    write_json(
        out / "export/final_render_manifest.json",
        {
            "schema": "automix-final-render-manifest-v1",
            "project_name": "unit",
            "source_stage": "accepted_premaster_draft",
            "renders": [],
            "failures": [],
            "warnings": ["diagnostic/report-only mode; no final audio rendered"],
        },
    )
    gate = build_final_render_evidence_gate(project_name="unit", output_dir=out)
    assert gate["ready_for_final_qc"] is False
    assert "final_render_manifest_diagnostic_or_report_only" in gate["blockers"]
    assert "primary_wav_render_missing" in gate["blockers"]


def test_final_render_evidence_gate_blocks_source_path_as_final_render(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    source = make_audio(tmp_path / "accepted.wav")
    write_export_state(out, source)
    write_render_manifest(out, source)
    gate = build_final_render_evidence_gate(project_name="unit", output_dir=out)
    assert gate["ready_for_final_qc"] is False
    assert "primary_wav_path_matches_selected_export_source" in gate["blockers"]


def test_final_render_evidence_gate_blocks_hidden_limiter_and_normalization(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    _source, render = write_ready_render(out, tmp_path)
    write_render_manifest(out, render, extra={"hidden_limiter_added": True, "normalization_applied": True})
    manifest = json.loads((out / "export/final_render_manifest.json").read_text(encoding="utf-8"))
    manifest["render_settings"]["hidden_limiter"] = True
    manifest["render_settings"]["normalization"] = True
    write_json(out / "export/final_render_manifest.json", manifest)
    gate = build_final_render_evidence_gate(project_name="unit", output_dir=out)
    assert "primary_wav_hidden_limiter_added" in gate["blockers"]
    assert "primary_wav_normalization_applied" in gate["blockers"]
    assert "render_settings_hidden_limiter_enabled" in gate["blockers"]
    assert "render_settings_normalization_enabled" in gate["blockers"]


def test_approval_export_readiness_requires_final_render_evidence_gate(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    source, render = write_ready_render(out, tmp_path)
    original = make_audio(tmp_path / "original.wav", amp=0.12)
    preview_manifest = generate_ab_preview_montage(
        project_name="unit",
        original_mix_path=original,
        final_audio_path=render,
        output_dir=out,
        deliverables_dir=tmp_path / "deliverables/unit",
        export_state={"safe_to_export": True},
        segment_seconds=0.1,
    )
    build_ab_preview_evidence_gate(project_name="unit", output_dir=out)
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
    assert "final_render_evidence_gate_missing_or_invalid" in missing_gate["blockers"]
    assert "final_render_evidence_not_ready" in missing_gate["blockers"]

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
    assert Path(preview_manifest["output_path"]).exists()


def test_final_render_evidence_gate_cli_require_ready_returns_nonzero_for_blockers(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/run_final_render_evidence_gate.py"),
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
    assert "final_render_manifest_missing_or_invalid" in data["blockers"]
    assert Path(data["report_json"]).exists()


def test_report_index_groups_final_render_evidence_gate(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    build_final_render_evidence_gate(project_name="unit", output_dir=out)
    index = build_report_index(project_name="unit", output_dir=out, stage_results=[])
    assert any(item["stage"] == "final export" and item["summary"] == "final_render_evidence_gate.json" for item in index["reports"])


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
    print("Prompt63 direct tests passed")

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
from automix.orchestrator.approval_export_readiness import build_approval_export_readiness
from automix.orchestrator.final_qc_evidence_gate import build_final_qc_evidence_gate
from automix.orchestrator.final_render_evidence_gate import build_final_render_evidence_gate
from automix.orchestrator.report_index import build_report_index
from automix.plugins.plugin_adapter_schema import write_json


def make_audio(path: Path, *, amp: float = 0.12, freq: float = 220.0, seconds: float = 0.25) -> Path:
    sample_rate = 48000
    frames = []
    for index in range(int(sample_rate * seconds)):
        t = index / sample_rate
        value = math.sin(2.0 * math.pi * freq * t) * amp
        frames.append([value, value * 0.9])
    write_pcm_wav(path, AudioData(sample_rate=sample_rate, channels=2, frames=frames), bit_depth=24)
    return path


def write_render_evidence(out: Path, tmp_path: Path, render: Path | None = None) -> tuple[Path, Path]:
    source = make_audio(tmp_path / "accepted.wav", amp=0.10)
    render = render or make_audio(tmp_path / "render.wav", amp=0.08)
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
            "renders": [
                {
                    "format": "wav",
                    "sample_rate": 48000,
                    "bit_depth": 24,
                    "path": str(render),
                    "created": True,
                    "size_bytes": render.stat().st_size,
                    "normalization_applied": False,
                    "hidden_limiter_added": False,
                }
            ],
            "failures": [],
            "warnings": [],
        },
    )
    build_final_render_evidence_gate(project_name="unit", output_dir=out)
    return source, render


def write_qc_metrics(out: Path, render: Path, *, passed: bool = True, failures: list[str] | None = None, true_peak: float = -6.0) -> None:
    info = wav_info(render)
    volume_uniformity = {
        "window_seconds": 0.25,
        "window_count": 80,
        "active_window_count": 80,
        "active_dbfs_range": 3.0,
        "active_dbfs_median": -20.0,
        "active_dbfs_p10": -22.0,
        "active_dbfs_p90": -19.0,
        "status": "assessed",
        "abrupt_level_jump_count": 0,
        "severe_level_jump_count": 0,
        "adjacent_jump_ratio": 0.0,
        "warnings": [],
    }
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
            "loudness": {
                "integrated_lufs": -18.0,
                "short_term_lufs_max": -16.0,
                "true_peak_dbTP": true_peak,
                "sample_peak_dbFS": -7.0,
                "lra": 3.0,
            },
            "translation": {},
            "vocal_preservation": {
                "vocal_forwardness_score": 0.55,
                "vocal_clarity_score": 0.45,
                "vocal_body_score": 0.5,
                "vocal_to_beat_balance": 0.4,
                "vocal_masking_risk": 0.2,
                "vocal_harshness_score": 0.2,
                "sibilance_splatter_score": 0.1,
                "metallic_artifact_score": 0.1,
                "ai_fizz_score": 0.1,
            },
            "volume_uniformity": volume_uniformity,
            "qc_passed": passed,
            "warnings": [],
            "failures": failures or [],
        },
    )


def test_final_qc_evidence_gate_blocks_missing_metrics_and_writes_request(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    gate = build_final_qc_evidence_gate(project_name="unit", output_dir=out)
    assert gate["ready_for_delivery_qc"] is False
    assert "final_qc_metrics_missing_or_invalid" in gate["blockers"]
    assert "final_render_evidence_gate_missing_or_invalid" in gate["blockers"]
    assert "final_audio_path_missing" in gate["blockers"]
    assert (out / "review/final_qc_evidence_manifest_template.json").exists()
    assert (out / "review/final_qc_evidence_request.md").exists()


def test_final_qc_evidence_gate_accepts_valid_metrics_linked_to_render(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    _source, render = write_render_evidence(out, tmp_path)
    write_qc_metrics(out, render)
    gate = build_final_qc_evidence_gate(project_name="unit", output_dir=out)
    assert gate["ready_for_delivery_qc"] is True
    assert gate["ready_for_approval_readiness"] is True
    assert gate["final_audio_path"] == str(render)
    assert gate["blockers"] == []


def test_final_qc_evidence_gate_rejects_volume_uniformity_spread_over_limit(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    _source, render = write_render_evidence(out, tmp_path)
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
            "loudness": {
                "integrated_lufs": -18.0,
                "short_term_lufs_max": -16.0,
                "true_peak_dbTP": -2.0,
                "sample_peak_dbFS": -7.0,
                "lra": 3.0,
            },
            "translation": {},
            "vocal_preservation": {},
            "volume_uniformity": {
                "window_seconds": 0.25,
                "window_count": 80,
                "active_window_count": 80,
                "active_dbfs_range": 20.0,
                "active_dbfs_median": -20.0,
                "active_dbfs_p10": -30.0,
                "active_dbfs_p90": -10.0,
                "status": "assessed",
                "warnings": [],
            },
            "qc_passed": False,
            "warnings": [],
            "failures": ["volume_uniformity_exceeds_limit"],
        },
    )
    gate = build_final_qc_evidence_gate(project_name="unit", output_dir=out)
    assert gate["ready_for_delivery_qc"] is False
    assert "final_qc_has_failures" in gate["blockers"]
    assert "final_qc_failure:volume_uniformity_exceeds_limit" in gate["blockers"]
    assert "final_qc_volume_uniformity_exceeds_limit" in gate["blockers"]


def test_final_qc_evidence_gate_rejects_vocal_presence_extremes(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    _source, render = write_render_evidence(out, tmp_path)
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
            "loudness": {
                "integrated_lufs": -18.0,
                "short_term_lufs_max": -16.0,
                "true_peak_dbTP": -2.0,
                "sample_peak_dbFS": -7.0,
                "lra": 3.0,
            },
            "translation": {"mono_compatibility_risk": 0.12},
            "vocal_preservation": {
                "vocal_forwardness_score": 0.05,
                "vocal_clarity_score": 0.1,
                "vocal_masking_risk": 0.85,
                "vocal_body_score": 0.2,
                "vocal_harshness_score": 0.2,
                "sibilance_splatter_score": 0.1,
                "metallic_artifact_score": 0.1,
                "ai_fizz_score": 0.1,
            },
            "volume_uniformity": {
                "window_seconds": 0.25,
                "window_count": 80,
                "active_window_count": 80,
                "active_dbfs_range": 3.0,
                "active_dbfs_median": -20.0,
                "active_dbfs_p10": -22.0,
                "active_dbfs_p90": -19.0,
                "max_adjacent_dbfs_delta": 3.0,
                "status": "assessed",
                "warnings": [],
            },
            "qc_passed": False,
            "warnings": [],
            "failures": ["vocal_presence_critically_weak", "vocal_masking_excessive"],
        },
    )
    gate = build_final_qc_evidence_gate(project_name="unit", output_dir=out)
    assert gate["ready_for_delivery_qc"] is False
    assert "final_qc_has_failures" in gate["blockers"]
    assert "final_qc_failure:vocal_presence_critically_weak" in gate["blockers"]
    assert "final_qc_failure:vocal_masking_excessive" in gate["blockers"]


def test_final_qc_evidence_gate_flags_volume_uniformity_jump(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    _source, render = write_render_evidence(out, tmp_path)
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
            "loudness": {
                "integrated_lufs": -18.0,
                "short_term_lufs_max": -16.0,
                "true_peak_dbTP": -2.0,
                "sample_peak_dbFS": -7.0,
                "lra": 3.0,
            },
            "translation": {"mono_compatibility_risk": 0.12},
            "vocal_preservation": {
                "vocal_forwardness_score": 0.65,
                "vocal_clarity_score": 0.7,
                "vocal_masking_risk": 0.2,
                "vocal_body_score": 0.5,
                "vocal_harshness_score": 0.2,
                "sibilance_splatter_score": 0.1,
                "metallic_artifact_score": 0.1,
                "ai_fizz_score": 0.1,
            },
            "volume_uniformity": {
                "window_seconds": 0.25,
                "window_count": 80,
                "active_window_count": 80,
                "active_dbfs_range": 3.0,
                "active_dbfs_median": -20.0,
                "active_dbfs_p10": -22.0,
                "active_dbfs_p90": -19.0,
                "max_adjacent_dbfs_delta": 18.0,
                "status": "assessed",
                "warnings": [],
            },
            "qc_passed": False,
            "warnings": [],
            "failures": ["volume_uniformity_abrupt_level_jump"],
        },
    )
    gate = build_final_qc_evidence_gate(project_name="unit", output_dir=out)
    assert gate["ready_for_delivery_qc"] is False
    assert "final_qc_failure:volume_uniformity_abrupt_level_jump" in gate["blockers"]
    assert "final_qc_volume_uniformity_abrupt_level_jump" in gate["blockers"]


def test_final_qc_evidence_gate_flags_multiple_rapid_jumps(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    _source, render = write_render_evidence(out, tmp_path)
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
            "loudness": {
                "integrated_lufs": -18.0,
                "short_term_lufs_max": -16.0,
                "true_peak_dbTP": -2.0,
                "sample_peak_dbFS": -7.0,
                "lra": 3.0,
            },
            "translation": {"mono_compatibility_risk": 0.12},
            "vocal_preservation": {
                "vocal_forwardness_score": 0.55,
                "vocal_clarity_score": 0.6,
                "vocal_masking_risk": 0.2,
                "vocal_to_beat_balance": 0.5,
                "vocal_body_score": 0.4,
                "vocal_harshness_score": 0.1,
                "sibilance_splatter_score": 0.1,
                "metallic_artifact_score": 0.1,
                "ai_fizz_score": 0.1,
            },
            "volume_uniformity": {
                "window_seconds": 0.25,
                "window_count": 80,
                "active_window_count": 80,
                "active_dbfs_range": 3.0,
                "active_dbfs_median": -20.0,
                "active_dbfs_p10": -22.0,
                "active_dbfs_p90": -19.0,
                "max_adjacent_dbfs_delta": 12.0,
                "abrupt_level_jump_count": 4,
                "severe_level_jump_count": 0,
                "adjacent_jump_ratio": 0.45,
                "status": "assessed",
                "warnings": [],
            },
            "qc_passed": True,
            "warnings": [],
            "failures": [],
        },
    )
    gate = build_final_qc_evidence_gate(project_name="unit", output_dir=out)
    assert gate["ready_for_delivery_qc"] is True
    assert "final_qc_warning:volume_uniformity_multiple_abrupt_jumps:4" in gate["warnings"]


def test_final_qc_evidence_gate_rejects_excessive_rapid_jumps(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    _source, render = write_render_evidence(out, tmp_path)
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
            "loudness": {
                "integrated_lufs": -18.0,
                "short_term_lufs_max": -16.0,
                "true_peak_dbTP": -2.0,
                "sample_peak_dbFS": -7.0,
                "lra": 3.0,
            },
            "translation": {"mono_compatibility_risk": 0.12},
            "vocal_preservation": {
                "vocal_forwardness_score": 0.55,
                "vocal_clarity_score": 0.6,
                "vocal_masking_risk": 0.2,
                "vocal_to_beat_balance": 0.5,
                "vocal_body_score": 0.4,
                "vocal_harshness_score": 0.1,
                "sibilance_splatter_score": 0.1,
                "metallic_artifact_score": 0.1,
                "ai_fizz_score": 0.1,
            },
            "volume_uniformity": {
                "window_seconds": 0.25,
                "window_count": 80,
                "active_window_count": 80,
                "active_dbfs_range": 3.0,
                "active_dbfs_median": -20.0,
                "active_dbfs_p10": -22.0,
                "active_dbfs_p90": -19.0,
                "max_adjacent_dbfs_delta": 16.0,
                "abrupt_level_jump_count": 4,
                "severe_level_jump_count": 4,
                "adjacent_jump_ratio": 0.45,
                "status": "assessed",
                "warnings": [],
            },
            "qc_passed": True,
            "warnings": [],
            "failures": [],
        },
    )
    gate = build_final_qc_evidence_gate(project_name="unit", output_dir=out)
    assert gate["ready_for_delivery_qc"] is False
    assert "final_qc_volume_uniformity_excessive_abrupt_jumps" in gate["blockers"]
    assert "final_qc_volume_uniformity_abrupt_level_jump" in gate["blockers"]


def test_final_qc_evidence_gate_rejects_vocal_to_beat_balance_critical(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    _source, render = write_render_evidence(out, tmp_path)
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
            "loudness": {
                "integrated_lufs": -18.0,
                "short_term_lufs_max": -16.0,
                "true_peak_dbTP": -2.0,
                "sample_peak_dbFS": -7.0,
                "lra": 3.0,
            },
            "translation": {"mono_compatibility_risk": 0.12},
            "vocal_preservation": {
                "vocal_forwardness_score": 0.05,
                "vocal_clarity_score": 0.6,
                "vocal_masking_risk": 0.2,
                "vocal_to_beat_balance": 0.03,
                "vocal_body_score": 0.4,
                "vocal_harshness_score": 0.1,
                "sibilance_splatter_score": 0.1,
                "metallic_artifact_score": 0.1,
                "ai_fizz_score": 0.1,
            },
            "volume_uniformity": {
                "window_seconds": 0.25,
                "window_count": 80,
                "active_window_count": 80,
                "active_dbfs_range": 3.0,
                "active_dbfs_median": -20.0,
                "active_dbfs_p10": -22.0,
                "active_dbfs_p90": -19.0,
                "max_adjacent_dbfs_delta": 3.0,
                "abrupt_level_jump_count": 0,
                "severe_level_jump_count": 0,
                "adjacent_jump_ratio": 0.0,
                "status": "assessed",
                "warnings": [],
            },
            "qc_passed": True,
            "warnings": [],
            "failures": [],
        },
    )
    gate = build_final_qc_evidence_gate(project_name="unit", output_dir=out)
    assert gate["ready_for_delivery_qc"] is False
    assert "final_qc_vocal_to_beat_balance_critical" in gate["blockers"]


def test_final_qc_evidence_gate_rejects_failures_and_true_peak_over_ceiling(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    _source, render = write_render_evidence(out, tmp_path)
    write_qc_metrics(out, render, passed=False, failures=["true_peak_above_ceiling"], true_peak=-0.2)
    gate = build_final_qc_evidence_gate(project_name="unit", output_dir=out)
    assert gate["ready_for_delivery_qc"] is False
    assert "final_qc_not_passed" in gate["blockers"]
    assert "final_qc_has_failures" in gate["blockers"]
    assert "final_qc_failure:true_peak_above_ceiling" in gate["blockers"]
    assert "final_qc_true_peak_above_ceiling" in gate["blockers"]


def test_final_qc_evidence_gate_rejects_mismatched_audio_path(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    _source, render = write_render_evidence(out, tmp_path)
    other = make_audio(tmp_path / "other.wav", amp=0.08)
    write_qc_metrics(out, other)
    gate = build_final_qc_evidence_gate(project_name="unit", output_dir=out)
    assert gate["ready_for_delivery_qc"] is False
    assert "final_audio_path_mismatch_render_evidence_primary_wav" in gate["blockers"]
    assert "final_audio_not_in_render_manifest_primary_wavs" in gate["blockers"]
    assert render.exists()


def test_approval_export_readiness_requires_final_qc_evidence_gate(tmp_path: Path) -> None:
    from automix.orchestrator.ab_preview_evidence_gate import build_ab_preview_evidence_gate
    from automix.orchestrator.rollback_evidence_gate import build_rollback_evidence_gate

    out = tmp_path / "automix"
    source, render = write_render_evidence(out, tmp_path)
    preview = make_audio(tmp_path / "preview.wav", amp=0.08)
    write_qc_metrics(out, render)
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
    write_json(out / "review/final_human_approval.json", {"schema": "automix-final-human-approval-v1", "approved": False, "approved_stage": "", "approved_source": ""})
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

    missing_gate = build_approval_export_readiness(project_name="unit", output_dir=out)
    assert "final_qc_evidence_gate_missing_or_invalid" in missing_gate["blockers"]
    assert "final_qc_evidence_not_ready" in missing_gate["blockers"]

    build_final_qc_evidence_gate(project_name="unit", output_dir=out)
    ready = build_approval_export_readiness(project_name="unit", output_dir=out)
    assert ready["ready_for_human_approval_request"] is True
    assert ready["blockers"] == ["final_human_approval_missing"]


def test_final_qc_evidence_gate_cli_require_ready_returns_nonzero_for_blockers(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/run_final_qc_evidence_gate.py"),
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
    assert "final_qc_metrics_missing_or_invalid" in data["blockers"]
    assert Path(data["report_json"]).exists()


def test_report_index_groups_final_qc_evidence_gate(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    build_final_qc_evidence_gate(project_name="unit", output_dir=out)
    index = build_report_index(project_name="unit", output_dir=out, stage_results=[])
    assert any(item["stage"] == "QC" and item["summary"] == "final_qc_evidence_gate.json" for item in index["reports"])


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
    print("Prompt65 direct tests passed")

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


def write_registry(out: Path, rollback_file: Path, *, protected: bool = True, safe: bool = True, validation_passed: bool = True) -> None:
    rollback_file.parent.mkdir(parents=True, exist_ok=True)
    if not rollback_file.exists():
        write_json(rollback_file, {"schema": "unit-rollback-v1", "safe_to_rollback": safe})
    write_json(
        out / "rollback/global_rollback_registry.json",
        {
            "schema": "automix-global-rollback-registry-v1",
            "project_name": "unit",
            "applied_stages": ["premaster"],
            "original_tracks_protected": protected,
            "original_master_protected": protected,
            "rollback_entries": [
                {
                    "stage": "premaster",
                    "rollback_file": str(rollback_file),
                    "safe_to_rollback": safe,
                    "original_tracks": [],
                    "draft_tracks": [],
                    "created_sends": [],
                    "plugins_inserted": [],
                }
            ],
            "validation": {"passed": validation_passed, "failures": [] if validation_passed else ["premaster_applied_without_rollback_file"], "warnings": []},
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


def write_delivery_ready_except_approval(out: Path, tmp_path: Path) -> None:
    source = make_audio(tmp_path / "accepted.wav", amp=0.18)
    render = make_audio(tmp_path / "render.wav", amp=0.16)
    original = make_audio(tmp_path / "original.wav", amp=0.12)
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
    generate_ab_preview_montage(
        project_name="unit",
        original_mix_path=original,
        final_audio_path=render,
        output_dir=out,
        deliverables_dir=tmp_path / "deliverables/unit",
        export_state={"safe_to_export": True},
        segment_seconds=0.1,
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
    write_json(out / "review/final_human_approval.json", {"schema": "automix-final-human-approval-v1", "approved": False, "approved_stage": "", "approved_source": ""})
    write_registry(out, tmp_path / "premaster_rollback.json")
    build_final_render_evidence_gate(project_name="unit", output_dir=out)
    write_final_qc(out, render)
    build_final_qc_evidence_gate(project_name="unit", output_dir=out)
    build_ab_preview_evidence_gate(project_name="unit", output_dir=out)


def test_rollback_evidence_gate_blocks_missing_registry_and_writes_request(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    gate = build_rollback_evidence_gate(project_name="unit", output_dir=out)
    assert gate["ready_for_delivery_readiness"] is False
    assert "rollback_registry_missing_or_invalid" in gate["blockers"]
    assert "recomputed_rollback_validation:rollback_registry_missing_or_invalid" in gate["blockers"]
    assert (out / "review/rollback_evidence_manifest_template.json").exists()
    assert (out / "review/rollback_evidence_request.md").exists()


def test_rollback_evidence_gate_accepts_valid_registry(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    rollback_file = tmp_path / "premaster_rollback.json"
    write_registry(out, rollback_file)
    gate = build_rollback_evidence_gate(project_name="unit", output_dir=out)
    assert gate["ready_for_delivery_readiness"] is True
    assert gate["original_tracks_protected"] is True
    assert gate["original_master_protected"] is True
    assert gate["rollback_entries_total"] == 1
    assert gate["safe_entries_total"] == 1
    assert gate["blockers"] == []


def test_rollback_evidence_gate_blocks_missing_rollback_file_even_if_stored_validation_passed(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    missing = tmp_path / "missing_rollback.json"
    write_registry(out, missing)
    missing.unlink()
    gate = build_rollback_evidence_gate(project_name="unit", output_dir=out)
    assert gate["ready_for_delivery_readiness"] is False
    assert "premaster:rollback_entry:rollback_file_missing" in gate["blockers"]
    assert any("recomputed_rollback_validation" in item for item in gate["blockers"])


def test_rollback_evidence_gate_blocks_unprotected_or_unsafe_entries(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    rollback_file = tmp_path / "premaster_rollback.json"
    write_registry(out, rollback_file, protected=False, safe=False, validation_passed=False)
    gate = build_rollback_evidence_gate(project_name="unit", output_dir=out)
    assert "original_tracks_not_protected" in gate["blockers"]
    assert "original_master_not_protected" in gate["blockers"]
    assert "premaster:rollback_entry:rollback_entry_not_safe" in gate["blockers"]
    assert "stored_rollback_validation:premaster_applied_without_rollback_file" in gate["blockers"]


def test_approval_export_readiness_requires_rollback_evidence_gate(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    write_delivery_ready_except_approval(out, tmp_path)
    missing_gate = build_approval_export_readiness(project_name="unit", output_dir=out)
    assert "rollback_evidence_gate_missing_or_invalid" in missing_gate["blockers"]
    assert "rollback_evidence_not_ready" in missing_gate["blockers"]

    build_rollback_evidence_gate(project_name="unit", output_dir=out)
    ready = build_approval_export_readiness(project_name="unit", output_dir=out)
    assert ready["ready_for_human_approval_request"] is True
    assert ready["blockers"] == ["final_human_approval_missing"]


def test_rollback_evidence_gate_cli_require_ready_returns_nonzero_for_blockers(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/run_rollback_evidence_gate.py"),
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
    assert "rollback_registry_missing_or_invalid" in data["blockers"]
    assert Path(data["report_json"]).exists()


def test_report_index_groups_rollback_evidence_gate(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    build_rollback_evidence_gate(project_name="unit", output_dir=out)
    index = build_report_index(project_name="unit", output_dir=out, stage_results=[])
    assert any(item["stage"] == "rollback" and item["summary"] == "rollback_evidence_gate.json" for item in index["reports"])


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
    print("Prompt64 direct tests passed")

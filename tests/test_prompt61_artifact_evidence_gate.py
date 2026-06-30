from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from automix.feedback.revision_memory import append_revision_memory
from automix.orchestrator.artifact_evidence_gate import build_artifact_evidence_gate
from automix.orchestrator.report_index import build_report_index
from automix.plugins.plugin_adapter_schema import write_json


def write_zero_inputs(out: Path) -> None:
    write_json(
        out / "eval_reports/real_project_source_safety_map.json",
        {
            "schema": "automix-real-project-source-safety-map-v1",
            "project_name": "unit",
            "summary": {"ai_or_already_processed_vocals": 0, "source_separated_vocals": 0},
            "safe_vocal_candidates": [{"track_name": "Lead", "source_classification": "raw_vocal", "ai_artifact_score": 0.0}],
        },
    )
    write_json(
        out / "eval_reports/final_qc_metrics.json",
        {
            "schema": "automix-final-qc-metrics-v1",
            "input_stage": "missing render",
            "source_mix_path": "",
            "vocal_preservation": {"ai_fizz_score": 0.0, "metallic_artifact_score": 0.0, "sibilance_splatter_score": 0.0},
        },
    )


def test_artifact_evidence_gate_blocks_missing_evidence_and_writes_template(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    write_zero_inputs(out)
    gate = build_artifact_evidence_gate(project_name="unit", output_dir=out)
    assert gate["artifact_evidence_established"] is False
    assert gate["measured_artifact_metrics_established"] is False
    assert "artifact_evidence_not_established" in gate["blockers"]
    assert "measured_artifact_metrics_missing" in gate["blockers"]
    assert (out / "review/artifact_evidence_manifest_template.json").exists()
    assert (out / "review/artifact_evidence_request.md").exists()


def test_artifact_evidence_gate_accepts_measured_final_qc_metric(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    write_zero_inputs(out)
    render = tmp_path / "render.wav"
    render.write_bytes(b"RIFF----WAVE")
    write_json(
        out / "eval_reports/final_qc_metrics.json",
        {
            "schema": "automix-final-qc-metrics-v1",
            "input_stage": "final_render",
            "source_mix_path": str(render),
            "vocal_preservation": {"ai_fizz_score": 0.61, "metallic_artifact_score": 0.0, "sibilance_splatter_score": 0.0},
        },
    )
    gate = build_artifact_evidence_gate(project_name="unit", output_dir=out)
    assert gate["artifact_evidence_established"] is True
    assert gate["measured_artifact_metrics_established"] is True
    assert gate["ready_for_artifact_review"] is True
    assert gate["safe_to_run_artifact_suppression"] is False
    assert gate["blockers"] == []


def test_artifact_evidence_gate_rejects_report_only_metric_even_when_high(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    write_zero_inputs(out)
    write_json(
        out / "eval_reports/final_qc_metrics.json",
        {
            "schema": "automix-final-qc-metrics-v1",
            "input_stage": "missing render",
            "source_mix_path": "",
            "vocal_preservation": {"ai_fizz_score": 0.83, "metallic_artifact_score": 0.0, "sibilance_splatter_score": 0.0},
            "warnings": ["missing render"],
        },
    )
    gate = build_artifact_evidence_gate(project_name="unit", output_dir=out)
    assert gate["measured_artifact_metrics_established"] is False
    assert "measured_artifact_metrics_missing" in gate["blockers"]
    assert any(item.startswith("report_only_metric:") for item in gate["warnings"])


def test_artifact_evidence_gate_accepts_user_feedback_signal_but_still_requires_metrics(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    write_zero_inputs(out)
    append_revision_memory(
        output_dir=out,
        project_name="unit",
        pass_id="v01",
        feedback_texts=["Suno fizz와 watery smear가 아직 들린다."],
    )
    gate = build_artifact_evidence_gate(project_name="unit", output_dir=out)
    assert gate["artifact_evidence_established"] is True
    assert gate["measured_artifact_metrics_established"] is False
    assert "artifact_evidence_not_established" not in gate["blockers"]
    assert "measured_artifact_metrics_missing" in gate["blockers"]


def test_artifact_evidence_gate_accepts_source_signal_but_still_requires_metrics(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    write_json(
        out / "eval_reports/real_project_source_safety_map.json",
        {
            "schema": "automix-real-project-source-safety-map-v1",
            "project_name": "unit",
            "summary": {"ai_or_already_processed_vocals": 1, "source_separated_vocals": 0},
            "safe_vocal_candidates": [{"track_name": "AI Vocal", "source_classification": "ai_vocal_stem", "ai_artifact_score": 0.72}],
        },
    )
    gate = build_artifact_evidence_gate(project_name="unit", output_dir=out)
    assert gate["artifact_evidence_established"] is True
    assert gate["measured_artifact_metrics_established"] is False
    assert "measured_artifact_metrics_missing" in gate["blockers"]


def test_artifact_evidence_gate_cli_require_measured_returns_nonzero_when_metrics_missing(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    write_zero_inputs(out)
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/run_artifact_evidence_gate.py"),
            "--project-name",
            "unit",
            "--output-dir",
            str(out),
            "--require-measured",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    data = json.loads(result.stdout)
    assert result.returncode == 2
    assert data["status"] == "blocked"
    assert "measured_artifact_metrics_missing" in data["blockers"]
    assert Path(data["report_json"]).exists()


def test_report_index_groups_artifact_evidence_gate(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    write_zero_inputs(out)
    build_artifact_evidence_gate(project_name="unit", output_dir=out)
    index = build_report_index(project_name="unit", output_dir=out, stage_results=[])
    assert any(item["stage"] == "artifact evidence" and item["summary"] == "artifact_evidence_gate.json" for item in index["reports"])


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
    print("Prompt61 direct tests passed")

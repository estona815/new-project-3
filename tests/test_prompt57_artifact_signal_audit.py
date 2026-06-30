from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from automix.feedback.revision_memory import append_revision_memory
from automix.orchestrator.artifact_signal_audit import build_artifact_signal_audit
from automix.plugins.plugin_adapter_schema import write_json


def write_zero_artifact_inputs(out: Path) -> None:
    write_json(
        out / "eval_reports/real_project_source_safety_map.json",
        {
            "schema": "automix-real-project-source-safety-map-v1",
            "project_name": "unit",
            "summary": {
                "ai_or_already_processed_vocals": 0,
                "source_separated_vocals": 0,
                "safe_vocal_candidates": 1,
                "stem_required_tracks": 0,
                "full_mix_unsafe_tracks": 0,
                "unknown_tracks": 0,
            },
            "safe_vocal_candidates": [{"track_name": "Lead", "source_classification": "raw_vocal", "ai_artifact_score": 0.0}],
        },
    )
    write_json(
        out / "eval_reports/final_qc_metrics.json",
        {
            "schema": "automix-final-qc-metrics-v1",
            "vocal_preservation": {
                "ai_fizz_score": 0.0,
                "metallic_artifact_score": 0.0,
                "sibilance_splatter_score": 0.0,
            },
        },
    )


def test_artifact_signal_audit_blocks_when_metrics_feedback_and_source_signal_are_missing(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    write_zero_artifact_inputs(out)
    audit = build_artifact_signal_audit(project_name="unit", output_dir=out)
    assert audit["artifact_signal_established"] is False
    assert "artifact_signal_not_established" in audit["blockers"]
    assert "measured_artifact_metrics_not_established" in audit["blockers"]
    assert "no_user_artifact_feedback_recorded" in audit["warnings"]
    assert "source_map_does_not_classify_ai_or_source_separated_vocals" in audit["warnings"]
    report = (out / "eval_reports/artifact_signal_audit.md").read_text(encoding="utf-8")
    assert "does not claim artifact removal" in report


def test_artifact_signal_audit_accepts_user_artifact_feedback_as_signal(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    write_zero_artifact_inputs(out)
    append_revision_memory(
        output_dir=out,
        project_name="unit",
        pass_id="v01",
        feedback_texts=["10kHz 이상 Suno fizz가 남아 있고 watery smear가 들린다."],
    )
    audit = build_artifact_signal_audit(project_name="unit", output_dir=out)
    assert audit["artifact_signal_established"] is True
    assert audit["feedback_observation"]["ai_artifact_feedback_count"] == 1
    assert "artifact_signal_not_established" not in audit["blockers"]
    assert audit["safe_to_run_artifact_suppression"] is False


def test_artifact_signal_audit_accepts_source_classification_as_signal(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    write_json(
        out / "eval_reports/real_project_source_safety_map.json",
        {
            "schema": "automix-real-project-source-safety-map-v1",
            "project_name": "unit",
            "summary": {
                "ai_or_already_processed_vocals": 1,
                "source_separated_vocals": 1,
                "safe_vocal_candidates": 1,
            },
            "safe_vocal_candidates": [
                {
                    "track_name": "AI Vocal",
                    "source_classification": "ai_vocal_stem",
                    "ai_artifact_score": 0.72,
                    "source_separated_likelihood": 0.10,
                }
            ],
        },
    )
    audit = build_artifact_signal_audit(project_name="unit", output_dir=out)
    assert audit["artifact_signal_established"] is True
    assert audit["summary"]["usable_source_signals"] >= 1


def test_artifact_signal_audit_cli_can_require_established_signal(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    write_zero_artifact_inputs(out)
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/run_artifact_signal_audit.py"),
            "--project-name",
            "unit",
            "--output-dir",
            str(out),
            "--require-established",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    data = json.loads(result.stdout)
    assert result.returncode == 2
    assert data["status"] == "blocked"
    assert Path(data["report_json"]).exists()
    assert Path(data["report_md"]).exists()

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from automix.orchestrator.source_handoff_readiness import build_source_handoff_readiness
from automix.plugins.plugin_adapter_schema import write_json


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_source_inputs(tmp_path: Path, *, accepted: bool = False) -> tuple[Path, Path]:
    out = tmp_path / "automix"
    source = tmp_path / "current_full_mix.wav"
    source.write_bytes(b"RIFF----WAVE-source")
    vocal = tmp_path / "lead_vocal.wav"
    vocal.write_bytes(b"RIFF----WAVE-vocal")
    accepted_source = tmp_path / "accepted.wav"
    if accepted:
        accepted_source.write_bytes(b"RIFF----WAVE-accepted")
    write_json(
        out / "eval_reports/real_project_source_safety_map.json",
        {
            "schema": "automix-real-project-source-safety-map-v1",
            "project_name": "unit",
            "summary": {
                "stem_required_tracks": 1,
                "full_mix_unsafe_tracks": 1,
                "unknown_tracks": 1,
                "safe_vocal_candidates": 1,
            },
            "stem_required_tracks": [
                {
                    "track_name": "SOURCE full mix reference muted",
                    "index": 1,
                    "role": "full_mix_reference",
                    "source_classification": "full_mix",
                    "stem_category": "instrumental_bus_required",
                    "recommended_next_action": "provide_isolated_stems",
                    "media_paths": [str(source)],
                }
            ],
            "unknown_tracks": [
                {
                    "track_name": "PRINTED REVERB SEND",
                    "index": 5,
                    "role": "reverb_send",
                    "source_classification": "unknown",
                    "recommended_next_action": "analyze_manually",
                    "warnings": ["unknown_source_skipped"],
                }
            ],
            "safe_vocal_candidates": [
                {
                    "track_name": "LEAD VOCAL",
                    "index": 3,
                    "role": "lead_vocal",
                    "source_classification": "raw_vocal",
                    "media_paths": [str(vocal)],
                }
            ],
        },
    )
    write_json(
        out / "export/final_export_state.json",
        {
            "schema": "automix-final-export-state-v1",
            "safe_to_export": bool(accepted),
            "selected_export_source": str(accepted_source) if accepted else "",
            "selected_export_stage": "accepted_premaster_draft" if accepted else "",
            "blocked_reasons": [] if accepted else ["no_accepted_export_source"],
        },
    )
    write_json(
        out / "export/project_state_manifest.json",
        {
            "schema": "automix-project-state-manifest-v1",
            "accepted_sources": [str(accepted_source)] if accepted else [],
        },
    )
    return out, source


def test_source_handoff_blocks_stem_requests_even_when_current_source_exists(tmp_path: Path) -> None:
    out, source = write_source_inputs(tmp_path)
    readiness = build_source_handoff_readiness(project_name="unit", output_dir=out)
    assert readiness["summary"]["source_files_present_total"] == 2
    assert readiness["summary"]["stem_requests_total"] == 1
    assert readiness["summary"]["accepted_export_source_present"] is False
    assert "stem_requests_open:1" in readiness["blockers"]
    assert "full_mix_unsafe_tracks:1" in readiness["blockers"]
    assert "accepted_export_source_missing" in readiness["blockers"]
    request = out / "review/source_stem_handoff_request.md"
    assert request.exists()
    assert "instrumental_or_music_bus_stem" in request.read_text(encoding="utf-8")
    assert source.exists()


def test_source_handoff_keeps_stem_blocker_after_accepted_source_exists(tmp_path: Path) -> None:
    out, _ = write_source_inputs(tmp_path, accepted=True)
    readiness = build_source_handoff_readiness(project_name="unit", output_dir=out)
    assert readiness["summary"]["accepted_export_source_present"] is True
    assert "accepted_export_source_missing" not in readiness["blockers"]
    assert "stem_requests_open:1" in readiness["blockers"]
    assert readiness["summary"]["automatic_processing_ready"] is False


def test_source_handoff_cli_writes_reports_and_can_require_ready(tmp_path: Path) -> None:
    out, _ = write_source_inputs(tmp_path)
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/run_source_handoff_readiness.py"),
            "--project-name",
            "unit",
            "--output-dir",
            str(out),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    data = json.loads(result.stdout)
    assert data["status"] == "blocked"
    assert Path(data["report_json"]).exists()
    assert Path(data["report_md"]).exists()
    assert Path(data["handoff_request"]).exists()

    blocked = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/run_source_handoff_readiness.py"),
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
    assert blocked.returncode == 2
    assert json.loads(blocked.stdout)["status"] == "blocked"

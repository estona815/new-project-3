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
from automix.export.audio_export_utils import write_pcm_wav
from automix.orchestrator.report_index import build_report_index
from automix.orchestrator.source_acceptance_gate import build_source_acceptance_gate
from automix.plugins.plugin_adapter_schema import write_json


def write_wav(path: Path, *, sample_rate: int = 48000, bit_depth: int = 24) -> Path:
    frames = []
    for i in range(int(sample_rate * 0.15)):
        value = 0.1 * math.sin(2.0 * math.pi * 220.0 * (i / sample_rate))
        frames.append([value, value])
    write_pcm_wav(path, AudioData(sample_rate=sample_rate, channels=2, frames=frames), bit_depth=bit_depth)
    return path


def test_source_acceptance_gate_blocks_missing_candidates_and_writes_template(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    write_json(
        out / "eval_reports/source_handoff_readiness.json",
        {
            "schema": "automix-source-handoff-readiness-v1",
            "stem_requests": [
                {
                    "track_name": "SOURCE full mix reference muted",
                    "role": "full_mix_reference",
                    "requested_files": [{"label": "instrumental_or_music_bus_stem", "notes": "Needed for vocal seat carving."}],
                }
            ],
        },
    )
    gate = build_source_acceptance_gate(project_name="unit", output_dir=out)
    assert gate["accepted_export_source_ready"] is False
    assert "source_acceptance_candidates_missing" in gate["blockers"]
    assert (out / "review/source_acceptance_manifest_template.json").exists()
    template = json.loads((out / "review/source_acceptance_manifest_template.json").read_text(encoding="utf-8"))
    assert template["candidate_sources"][0]["label"] == "instrumental_or_music_bus_stem"
    assert (out / "review/source_acceptance_request.md").exists()


def test_source_acceptance_gate_accepts_reviewed_premaster_wav(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    source = write_wav(tmp_path / "accepted_premaster.wav")
    gate = build_source_acceptance_gate(
        project_name="unit",
        output_dir=out,
        source_audio=source,
        source_stage="accepted_premaster_draft",
        source_role="premaster",
        source_classification="accepted_premaster_render",
        human_accepted=True,
    )
    assert gate["accepted_export_source_ready"] is True
    assert gate["blockers"] == []
    assert gate["accepted_final_export_sources"][0]["audio"]["sample_rate"] == 48000
    assert gate["accepted_final_export_sources"][0]["audio"]["bit_depth"] == 24


def test_source_acceptance_gate_rejects_full_mix_as_automatic_source(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    source = write_wav(tmp_path / "full_mix.wav")
    gate = build_source_acceptance_gate(
        project_name="unit",
        output_dir=out,
        source_audio=source,
        source_stage="accepted_premaster_draft",
        source_role="full_mix_reference",
        source_classification="full_mix",
        human_accepted=True,
    )
    assert gate["accepted_export_source_ready"] is False
    assert "full_mix_source_cannot_be_accepted_for_automatic_processing" in gate["blockers"]
    assert "reference_role_cannot_be_final_export_source" in gate["blockers"]


def test_source_acceptance_gate_requires_explicit_human_acceptance(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    source = write_wav(tmp_path / "accepted_premaster.wav")
    gate = build_source_acceptance_gate(
        project_name="unit",
        output_dir=out,
        source_audio=source,
        source_stage="accepted_premaster_draft",
        source_role="premaster",
        source_classification="accepted_premaster_render",
        human_accepted=False,
    )
    assert gate["accepted_export_source_ready"] is False
    assert "explicit_source_acceptance_missing" in gate["blockers"]


def test_source_acceptance_cli_require_ready_returns_nonzero_when_blocked(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/run_source_acceptance_gate.py"),
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
    assert "source_acceptance_candidates_missing" in data["blockers"]
    assert Path(data["report_json"]).exists()


def test_source_acceptance_cli_accepts_reviewed_source(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    source = write_wav(tmp_path / "accepted_premaster.wav")
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/run_source_acceptance_gate.py"),
            "--project-name",
            "unit",
            "--output-dir",
            str(out),
            "--source-audio",
            str(source),
            "--source-stage",
            "accepted_premaster_draft",
            "--source-role",
            "premaster",
            "--source-classification",
            "accepted_premaster_render",
            "--human-accepted",
            "--require-ready",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    data = json.loads(result.stdout)
    assert data["status"] == "ready"
    assert data["accepted_export_source_ready"] is True


def test_report_index_groups_source_acceptance_gate(tmp_path: Path) -> None:
    out = tmp_path / "automix"
    build_source_acceptance_gate(project_name="unit", output_dir=out)
    index = build_report_index(project_name="unit", output_dir=out, stage_results=[])
    assert any(item["stage"] == "source classification" and item["summary"] == "source_acceptance_gate.json" for item in index["reports"])


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
    print("Prompt59 direct tests passed")

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from automix.batch.batch_pitch_triage import TrackCandidate, detect_track_role, run_batch_triage


def source(classification: str, *, full_mix: float = 0.05, source_sep: float = 0.05, mixed: float = 0.20, tuned: float = 0.20, risk: str = "low") -> dict:
    return {
        "schema": "automix-source-classification-v1",
        "scan_date_utc": "2026-05-31T00:00:00Z",
        "track_name": "fixture",
        "classification": classification,
        "confidence": 0.82,
        "full_mix_likelihood": full_mix,
        "vocal_stem_likelihood": 0.90,
        "source_separated_likelihood": source_sep,
        "already_mixed_score": mixed,
        "already_tuned_score": tuned,
        "baked_reverb_score": 0.20,
        "compression_limited_score": 0.30,
        "ai_artifact_score": 0.20,
        "pitch_correction_risk": risk,
        "recommendation": "conservative_allowed",
        "metrics": {},
    }


def pitch(confidence: float = 0.85, polyphonic: float = 0.10) -> dict:
    return {
        "schema": "automix-pitch-analysis-v1",
        "scan_date_utc": "2026-05-31T00:00:00Z",
        "track_name": "fixture",
        "source_classification": "raw_vocal",
        "voiced_frame_ratio": 0.80,
        "monophonic_pitch_confidence": confidence,
        "pitch_stability": 0.80,
        "note_confidence": 0.80,
        "scale_key_confidence": 0.80,
        "key_confidence": 0.80,
        "scale_confidence": 0.80,
        "octave_error_suspicion": 0.0,
        "vibrato_presence": 0.40,
        "pitch_jump_density": 0.10,
        "polyphonic_contamination_score": polyphonic,
        "already_tuned_score": 0.20,
        "pitch_correction_risk": "low",
    }


def adapter(path: Path, confidence: float = 0.92) -> None:
    controls = ["correction_amount", "depth", "dry_wet", "speed", "formant_preserve"]
    path.write_text(
        json.dumps(
            {
                "plugin_name": "MAutoPitch",
                "available": True,
                "mapping_confidence": confidence,
                "semantic_controls": {name: {"target_name": name, "confidence": 0.92, "writable": True} for name in controls},
            }
        ),
        encoding="utf-8",
    )


def manifest(path: Path) -> None:
    data = {
        "tracks": [
            {
                "track_name": "Lead Vocal",
                "track_guid": "{lead}",
                "source_classification": source("raw_vocal"),
                "pitch_analysis": pitch(),
            },
            {
                "track_name": "Backing Vox",
                "track_guid": "{bgv}",
                "source_classification": source("mixed_vocal_stem", mixed=0.58, risk="medium"),
                "pitch_analysis": pitch(0.78),
            },
            {
                "track_name": "Vocal Bus",
                "track_guid": "{voxbus}",
                "source_classification": source("mixed_vocal_stem", source_sep=0.50, mixed=0.65, risk="high"),
                "pitch_analysis": pitch(0.60, polyphonic=0.60),
            },
            {
                "track_name": "Source Sep Vox",
                "track_guid": "{sep}",
                "source_classification": source("source_separated_vocal", source_sep=0.75, mixed=0.70, risk="high"),
                "pitch_analysis": pitch(0.72, polyphonic=0.45),
            },
            {
                "track_name": "Full Mix Ref",
                "track_guid": "{ref}",
                "source_classification": source("full_mix", full_mix=0.90, mixed=0.90, risk="unsafe"),
                "pitch_analysis": pitch(0.30, polyphonic=0.90),
            },
            {"track_name": "DRUM BUS", "track_guid": "{drums}"},
            {"track_name": "MASTER", "track_guid": "{master}"},
            {"track_name": "Mystery Track", "track_guid": "{mystery}"},
        ]
    }
    path.write_text(json.dumps(data), encoding="utf-8")


def test_track_role_detection_examples() -> None:
    assert detect_track_role(TrackCandidate("Lead Vocal"))["role"] == "lead_vocal"
    assert detect_track_role(TrackCandidate("DRUM BUS"))["role"] == "drums"
    assert detect_track_role(TrackCandidate("MASTER"))["role"] == "master"
    assert detect_track_role(TrackCandidate("Full Mix Ref"))["role"] == "full_mix_reference"
    assert detect_track_role(TrackCandidate("Backing Vox"))["role"] == "backing_vocal"
    unknown = detect_track_role(TrackCandidate("Mysterious Audio"))
    assert unknown["role"] == "unknown"
    assert unknown["pitch_triage_eligible"] is False


def test_conservative_scan_outputs_role_map_triage_matrix_and_visible_skips() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        manifest_path = tmp_path / "manifest.json"
        adapter_path = tmp_path / "adapter.json"
        manifest(manifest_path)
        adapter(adapter_path)
        paths = run_batch_triage(
            project_path=None,
            track_manifest_path=manifest_path,
            adapter_status_path=adapter_path,
            output_dir=tmp_path / "automix",
            mode="conservative_scan_only",
        )
        role_map = json.loads(paths["role_map"].read_text(encoding="utf-8"))
        matrix = json.loads(paths["matrix"].read_text(encoding="utf-8"))
        report = paths["batch_report"].read_text(encoding="utf-8")

    assert role_map["tracks"][0]["role"] == "lead_vocal"
    assert matrix["summary"]["total_tracks"] == 8
    assert matrix["summary"]["pitch_skipped"] >= 2
    assert "DRUM BUS" in report
    assert "MASTER" in report
    assert "Skipped Tracks" in report


def test_full_mix_instrumental_and_unknown_tracks_are_not_pitch_eligible() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        manifest_path = tmp_path / "manifest.json"
        adapter_path = tmp_path / "adapter.json"
        manifest(manifest_path)
        adapter(adapter_path)
        paths = run_batch_triage(
            project_path=None,
            track_manifest_path=manifest_path,
            adapter_status_path=adapter_path,
            output_dir=tmp_path / "automix",
            mode="conservative_scan_only",
        )
        matrix = json.loads(paths["matrix"].read_text(encoding="utf-8"))
        decisions = {item["track_name"]: item for item in matrix["track_decisions"]}

    assert decisions["Full Mix Ref"]["decision"] == "full_mix_unsafe"
    assert decisions["DRUM BUS"]["decision"] == "skip"
    assert decisions["MASTER"]["decision"] == "skip"
    assert decisions["Mystery Track"]["decision"] == "skip"


def test_stem_required_report_and_vocal_bus_caution_exist() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        manifest_path = tmp_path / "manifest.json"
        adapter_path = tmp_path / "adapter.json"
        manifest(manifest_path)
        adapter(adapter_path)
        run_batch_triage(
            project_path=None,
            track_manifest_path=manifest_path,
            adapter_status_path=adapter_path,
            output_dir=tmp_path / "automix",
            mode="conservative_scan_only",
        )
        stem_report = tmp_path / "automix/eval_reports/Source_Sep_Vox_stem_required_report.md"
        vocal_bus_triage = json.loads((tmp_path / "automix/analysis_reports/Vocal_Bus_pitch_triage.json").read_text(encoding="utf-8"))

        assert stem_report.exists()
        assert "Provide an isolated lead vocal stem" in stem_report.read_text(encoding="utf-8")
        assert any("vocal bus" in warning.lower() for warning in vocal_bus_triage["warnings"])


def test_apply_drafts_requires_explicit_mode_and_writes_rollback_index() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        manifest_path = tmp_path / "manifest.json"
        adapter_path = tmp_path / "adapter.json"
        manifest(manifest_path)
        adapter(adapter_path)
        paths = run_batch_triage(
            project_path=None,
            track_manifest_path=manifest_path,
            adapter_status_path=adapter_path,
            output_dir=tmp_path / "automix",
            mode="conservative_apply_drafts",
            apply_drafts=True,
        )
        rollback = json.loads(paths["rollback_index"].read_text(encoding="utf-8"))
        render_plan = json.loads(paths["render_plan"].read_text(encoding="utf-8"))

    assert rollback["draft_tracks"]
    assert all(item["draft_track_name"].endswith("_PITCH_DRAFT") for item in rollback["draft_tracks"])
    assert render_plan["render_required"] is True
    assert render_plan["tracks_to_render"]


def test_low_adapter_confidence_reports_plugin_mapping_required() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        manifest_path = tmp_path / "manifest.json"
        adapter_path = tmp_path / "adapter.json"
        manifest(manifest_path)
        adapter(adapter_path, confidence=0.20)
        paths = run_batch_triage(
            project_path=None,
            track_manifest_path=manifest_path,
            adapter_status_path=adapter_path,
            output_dir=tmp_path / "automix",
            mode="conservative_scan_only",
        )
        matrix = json.loads(paths["matrix"].read_text(encoding="utf-8"))

    assert matrix["summary"]["plugin_mapping_required"] >= 1


def test_render_plan_includes_only_applied_drafts_and_skips_are_visible() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        manifest_path = tmp_path / "manifest.json"
        adapter_path = tmp_path / "adapter.json"
        manifest(manifest_path)
        adapter(adapter_path)
        paths = run_batch_triage(
            project_path=None,
            track_manifest_path=manifest_path,
            adapter_status_path=adapter_path,
            output_dir=tmp_path / "automix",
            mode="conservative_scan_only",
        )
        render_plan = json.loads(paths["render_plan"].read_text(encoding="utf-8"))

    assert render_plan["render_required"] is False
    assert not render_plan["tracks_to_render"]
    assert render_plan["tracks_skipped_from_render"]


def test_safety_score_treats_correct_skipping_as_valid() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        manifest_path = tmp_path / "manifest.json"
        adapter_path = tmp_path / "adapter.json"
        manifest(manifest_path)
        adapter(adapter_path)
        paths = run_batch_triage(
            project_path=None,
            track_manifest_path=manifest_path,
            adapter_status_path=adapter_path,
            output_dir=tmp_path / "automix",
            mode="conservative_scan_only",
        )
        score = json.loads(paths["safety_score"].read_text(encoding="utf-8"))

    assert 0.0 <= score["project_pitch_safety_score"] <= 1.0
    assert score["unsafe_track_count"] >= 1
    assert score["recommendation"] in {
        "accept_no_pitch",
        "safe_micro_drafts_created",
        "review_before_accept",
        "stems_required",
        "manual_tuning_required",
        "plugin_mapping_required",
        "unsafe_to_autotune",
    }


def test_cli_default_is_dry_scan_and_refuses_unsafe_apply_invocation() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        manifest_path = tmp_path / "manifest.json"
        adapter_path = tmp_path / "adapter.json"
        manifest(manifest_path)
        adapter(adapter_path)
        ok = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts/run_batch_pitch_triage.py"),
                "--track-manifest",
                str(manifest_path),
                "--adapter-status-json",
                str(adapter_path),
                "--output-dir",
                str(tmp_path / "automix"),
                "--dry-run",
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        bad = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts/run_batch_pitch_triage.py"),
                "--track-manifest",
                str(manifest_path),
                "--mode",
                "conservative_apply_drafts",
                "--adapter-status-json",
                str(adapter_path),
                "--output-dir",
                str(tmp_path / "automix2"),
            ],
            check=False,
            capture_output=True,
            text=True,
        )

    assert ok.returncode == 0
    assert "project_pitch_batch_report.md" in ok.stdout
    assert bad.returncode == 2
    assert "requires explicit --apply-drafts" in bad.stdout

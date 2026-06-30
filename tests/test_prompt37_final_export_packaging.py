from __future__ import annotations

import json
import math
import subprocess
import sys
import tempfile
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from automix.analyze_ai_pitch_source import AudioData
from automix.export.ab_preview_montage import generate_ab_preview_montage
from automix.export.audio_export_utils import write_pcm_wav
from automix.export.deliverable_packager import create_deliverables_folder, package_deliverables, write_plugin_mapping_summary
from automix.export.export_format_profiles import resolve_export_profile, validate_export_profile
from automix.export.export_naming import build_export_filename, next_available_path
from automix.export.final_export_state_resolver import resolve_final_export_state
from automix.export.final_qc_analyzer import analyze_final_qc, missing_final_qc, write_final_qc_report
from automix.export.final_render_engine import render_final_outputs
from automix.export.human_approval_gate import build_human_approval, evaluate_human_approval
from automix.feedback.revision_memory import append_revision_memory, resolve_feedback_items
from automix.plugins.plugin_adapter_schema import write_json


def make_audio(freqs: list[float], *, amp: float = 0.2, seconds: float = 0.35, sr: int = 44100, clip: bool = False) -> AudioData:
    frames = []
    for i in range(int(seconds * sr)):
        t = i / sr
        value = sum(math.sin(2.0 * math.pi * freq * t) for freq in freqs) / max(1, len(freqs))
        value *= amp
        if clip:
            value = max(-1.0, min(1.0, value * 8.0))
        frames.append([value, value * 0.9])
    return AudioData(sample_rate=sr, channels=2, frames=frames)


def make_piecewise_audio(path: Path, *, periods: int = 8, high_amp: float = 0.25, low_amp: float = 0.025, sr: int = 48000) -> Path:
    segment_seconds = 0.25
    total_seconds = periods * segment_seconds
    freq = 220.0
    frames = []
    for index in range(int(total_seconds * sr)):
        segment = index // int(segment_seconds * sr)
        amp = high_amp if segment % 2 == 0 else low_amp
        t = index / sr
        value = math.sin(2.0 * math.pi * freq * t) * amp
        frames.append([value, value * 0.9])
    write_pcm_wav(path, AudioData(sample_rate=sr, channels=2, frames=frames), bit_depth=24)
    return path


def write_source(path: Path, *, amp: float = 0.2, sr: int = 44100, clip: bool = False) -> Path:
    audio = make_audio([80.0, 220.0, 1200.0], amp=amp, sr=sr, clip=clip)
    write_pcm_wav(path, audio, bit_depth=24)
    return path


def accepted_state(source: Path) -> dict:
    return resolve_final_export_state(
        project_name="Song",
        workflow_state={
            "premaster": {
                "accepted": True,
                "status": "accepted",
                "source_path": str(source),
                "review_accepted": True,
                "ab_render_exists": True,
            }
        },
    )


def approved_eval(state: dict) -> tuple[dict, dict]:
    approval = build_human_approval(approved=True, approved_stage=state["selected_export_stage"], approved_source=state["selected_export_source"], warnings_acknowledged=["all"])
    return approval, evaluate_human_approval(state, approval)


def test_state_resolver_priority_rejects_and_original_requires_approval() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        premaster = write_source(tmp_path / "premaster.wav")
        placement = write_source(tmp_path / "placement.wav")
        state = resolve_final_export_state(
            project_name="Song",
            workflow_state={
                "vocal_placement": {"accepted": True, "status": "accepted", "source_path": str(placement)},
                "premaster": {"accepted": True, "status": "accepted", "source_path": str(premaster)},
            },
        )
        assert state["selected_export_stage"] == "accepted_premaster_draft"
        rejected = resolve_final_export_state(project_name="Song", workflow_state={"premaster": {"status": "reject_premaster", "source_path": str(premaster)}})
        assert rejected["safe_to_export"] is False
        assert "premaster_status_reject_premaster" in rejected["blocked_reasons"]
        original_blocked = resolve_final_export_state(project_name="Song", workflow_state={"original_mix": {"accepted": True, "status": "accepted", "source_path": str(premaster)}})
        assert original_blocked["safe_to_export"] is False
        original_ok = resolve_final_export_state(
            project_name="Song",
            workflow_state={"original_mix": {"accepted": True, "status": "accepted", "source_path": str(premaster), "explicitly_approved": True}},
            explicit_original_approval=True,
        )
        assert original_ok["selected_export_stage"] == "original_mix_explicitly_approved"


def test_state_resolver_blocks_unresolved_user_feedback_even_with_accepted_source() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        output = tmp_path / "automix"
        premaster = write_source(tmp_path / "premaster.wav")
        append_revision_memory(
            output_dir=output,
            project_name="Song",
            pass_id="v01",
            feedback_texts=["보컬이 아직 뒤로 빠졌고 Suno fizz가 남아 있다."],
        )
        state = resolve_final_export_state(
            project_name="Song",
            workflow_state={
                "premaster": {
                    "accepted": True,
                    "status": "accepted",
                    "source_path": str(premaster),
                    "review_accepted": True,
                    "ab_render_exists": True,
                }
            },
            output_dir=output,
        )
    assert state["selected_export_stage"] == "accepted_premaster_draft"
    assert state["safe_to_export"] is False
    assert "user_feedback_unresolved_for_final_delivery" in state["blocked_reasons"]
    assert "user_feedback_revision_loop" in state["required_reviews"]
    assert state["feedback_revision_loop"]["pending_unresolved_count"] == 1


def test_state_resolver_allows_resolved_user_feedback_with_accepted_source() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        output = tmp_path / "automix"
        premaster = write_source(tmp_path / "premaster.wav")
        evidence = output / "eval_reports/final_qc_metrics.json"
        memory = append_revision_memory(
            output_dir=output,
            project_name="Song",
            pass_id="v01",
            feedback_texts=["마스터가 너무 납작하다."],
        )
        write_json(evidence, {"qc_passed": True, "ab_reviewed": True})
        resolve_feedback_items(
            output_dir=output,
            project_name="Song",
            pass_id="v02",
            feedback_ids=memory["unresolved_feedback_ids"],
            resolution_notes="Premaster dynamics and loudness-matched A/B passed review.",
            evidence_paths=[str(evidence)],
            human_reviewed=True,
            measured_qc_passed=True,
            loudness_matched_ab_reviewed=True,
        )
        state = resolve_final_export_state(
            project_name="Song",
            workflow_state={
                "premaster": {
                    "accepted": True,
                    "status": "accepted",
                    "source_path": str(premaster),
                    "review_accepted": True,
                    "ab_render_exists": True,
                }
            },
            output_dir=output,
        )
    assert state["safe_to_export"] is True
    assert "user_feedback_unresolved_for_final_delivery" not in state["blocked_reasons"]
    assert state["feedback_revision_loop"]["pending_unresolved_count"] == 0


def test_approval_gate_defaults_warnings_and_diagnostic() -> None:
    state = {"safe_to_export": True, "selected_export_source": "a.wav", "warnings": ["manual_check"]}
    default = evaluate_human_approval(state)
    assert default["approved_for_export"] is False
    approval = build_human_approval(approved=True, approved_source="a.wav")
    blocked = evaluate_human_approval(state, approval, warnings=["manual_check"])
    assert "warnings_require_acknowledgment" in blocked["failures"]
    approved = build_human_approval(approved=True, approved_source="a.wav", warnings_acknowledged=["all"])
    assert evaluate_human_approval(state, approved, warnings=["manual_check"])["approved_for_export"] is True
    assert evaluate_human_approval(state, diagnostic_only=True)["approved_for_export"] is True


def test_naming_sanitizes_increments_and_unsafe_uses_review_copy() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        target = {"format": "wav", "sample_rate": 48000, "bit_depth": 24}
        first = next_available_path(root, "My Song!? 01", "FINAL_MASTER", target, ext="wav", today=date(2026, 5, 31))
        first.write_text("x", encoding="utf-8")
        second = next_available_path(root, "My Song!? 01", "FINAL_MASTER", target, ext="wav", today=date(2026, 5, 31))
        unsafe = build_export_filename("My Song", "FINAL_MASTER", 1, target, ext="wav", today=date(2026, 5, 31), unsafe_override=True)
    assert "my_song_01_FINAL_MASTER_v01_24bit_48k_2026-05-31.wav" == first.name
    assert "_v02_" in second.name
    assert "UNSAFE_REVIEW_COPY" in unsafe
    assert "FINAL_SAFE" not in unsafe


def test_profiles_block_mp3_only_and_diagnostic_audio() -> None:
    profile = resolve_export_profile("professional_master_delivery")
    assert validate_export_profile(profile)["valid"] is True
    invalid = {"profile_name": "bad", "mp3_320": True, "wav_24_48": False, "final_audio": True}
    result = validate_export_profile(invalid)
    assert result["valid"] is False
    assert "mp3_only_final_delivery_is_not_allowed" in result["failures"]
    diagnostic = resolve_export_profile("diagnostic_only")
    assert diagnostic["final_audio"] is False


def test_render_engine_wav_primary_requires_approval_and_creates_nonzero_file() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        source = write_source(tmp_path / "source.wav")
        state = accepted_state(source)
        approval, approval_eval = approved_eval(state)
        profile = {"profile_name": "wav_only_test", "wav_24_48": True, "final_audio": True}
        folder = create_deliverables_folder(tmp_path / "deliverables", "Song")
        manifest = render_final_outputs(project_name="Song", export_profile=profile, export_state=state, approval_eval=approval_eval, deliverables_dir=folder, output_dir=tmp_path / "automix", render=True)
        blocked = render_final_outputs(project_name="Song", export_profile=profile, export_state=state, approval_eval=evaluate_human_approval(state), deliverables_dir=folder, output_dir=tmp_path / "automix2", render=True)
    assert manifest["renders"][0]["created"] is True
    assert manifest["renders"][0]["size_bytes"] > 0
    assert manifest["renders"][0]["hidden_limiter_added"] is False
    assert "final_export_requires_explicit_human_approval" in blocked["failures"]
    assert approval["approved"] is True


def test_ab_preview_and_qc_fail_closed_for_rejected_or_bad_sources() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        original = write_source(tmp_path / "original.wav")
        final = write_source(tmp_path / "final.wav")
        state = accepted_state(final)
        folder = create_deliverables_folder(tmp_path / "deliverables", "Song")
        preview = generate_ab_preview_montage(project_name="Song", original_mix_path=original, final_audio_path=final, output_dir=tmp_path / "automix", deliverables_dir=folder, export_state=state)
        missing = missing_final_qc(tmp_path / "none.wav", "file_missing")
        clipped = write_source(tmp_path / "clipped.wav", amp=1.0, sr=48000, clip=True)
        qc = analyze_final_qc(clipped, output_dir=tmp_path / "automix", export_state=state, expected_sample_rate=48000, expected_bit_depth=24)
        wrong_sr = analyze_final_qc(final, output_dir=tmp_path / "automix2", export_state=state, expected_sample_rate=48000, expected_bit_depth=24)
    assert preview["created"] is True
    assert [item["label"] for item in preview["segments"]] == ["original_mix", "final_processed", "original_mix", "final_processed"]
    assert missing["qc_passed"] is False
    assert "clipping_detected" in qc["failures"] or "true_peak_above_ceiling" in qc["failures"]
    assert "wrong_sample_rate" in wrong_sr["failures"]


def test_analyze_final_qc_returns_vocal_presence_and_uniformity_fields() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        output = tmp_path / "automix"
        source = write_source(tmp_path / "source.wav", sr=48000)
        state = accepted_state(source)
        qc = analyze_final_qc(source, output_dir=output, export_state=state)
    vocals = qc["vocal_preservation"]
    uniformity = qc["volume_uniformity"]
    for key in ["vocal_forwardness_score", "vocal_clarity_score", "vocal_body_score", "vocal_masking_risk"]:
        assert key in vocals
    for key in ["status", "active_window_count", "active_dbfs_range", "max_adjacent_dbfs_delta"]:
        assert key in uniformity
    assert "abrupt_level_jump_count" in uniformity
    assert "severe_level_jump_count" in uniformity
    assert "adjacent_jump_ratio" in uniformity
    assert "vocal_to_beat_balance" in vocals
    report = write_final_qc_report(
        output_dir=output,
        project_name="Song",
        export_profile=resolve_export_profile("professional_master_delivery"),
        export_state=state,
        approval=build_human_approval(approved=True, approved_stage=state["selected_export_stage"], approved_source=str(source)),
        approval_eval=evaluate_human_approval(state, build_human_approval(approved=True, approved_stage=state["selected_export_stage"], approved_source=str(source), warnings_acknowledged=["all"])),
        render_manifest={"renders": []},
        qc_metrics=qc,
    )
    text = report.read_text(encoding="utf-8")
    assert "vocal_clarity_score" in text
    assert "vocal_masking_risk" in text
    assert "Max adjacent dbfs delta" in text or "max_adjacent_dbfs_delta" in text
    assert "vocal_to_beat_balance" in text


def test_analyze_final_qc_detects_multiple_abrupt_level_jumps() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        output = tmp_path / "automix"
        path = make_piecewise_audio(tmp_path / "piecewise.wav", periods=12)
        state = accepted_state(path)
        qc = analyze_final_qc(path, output_dir=output, export_state=state)
    uniformity = qc["volume_uniformity"]
    vocals = qc["vocal_preservation"]
    assert qc["qc_passed"] is False
    assert "volume_uniformity_multiple_abrupt_jumps" in qc["warnings"] or "volume_uniformity_excessive_abrupt_jumps" in qc["failures"]
    assert int(uniformity.get("abrupt_level_jump_count", 0)) >= 1
    assert "vocal_to_beat_balance" in vocals


def test_packager_creates_folder_zip_manifests_and_reports() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        output = tmp_path / "automix"
        source = write_source(tmp_path / "source.wav", sr=48000)
        state = accepted_state(source)
        approval, approval_eval = approved_eval(state)
        folder = create_deliverables_folder(tmp_path / "deliverables", "Song")
        profile = {"profile_name": "wav_only_test", "wav_24_48": True, "final_audio": True}
        render_manifest = render_final_outputs(project_name="Song", export_profile=profile, export_state=state, approval_eval=approval_eval, deliverables_dir=folder, output_dir=output, render=True)
        primary = Path(render_manifest["renders"][0]["path"])
        qc = analyze_final_qc(primary, output_dir=output, export_state=state)
        report = write_final_qc_report(
            output_dir=output,
            project_name="Song",
            export_profile=profile,
            export_state=state,
            approval=approval,
            approval_eval=approval_eval,
            render_manifest=render_manifest,
            qc_metrics=qc,
        )
        package = package_deliverables(project_name="Song", deliverables_dir=folder, output_dir=output, export_state=state, render_manifest=render_manifest, qc_metrics=qc, create_zip=True)
        summary = write_plugin_mapping_summary(output)
        readme_exists = (folder / "README_DELIVERY.md").exists()
        report_exists = report.exists()
        summary_exists = summary.exists()
        zip_exists = Path(package["zip_path"]).exists()
    assert readme_exists
    assert report_exists
    assert summary_exists
    assert package["package_created"] is True
    assert zip_exists
    assert any("project_state_manifest.json" in item for item in package["files_included"])


def test_cli_diagnostic_writes_required_prompt37_files() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        cli = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts/run_final_export_packager.py"),
                "--project",
                str(tmp_path / "song.rpp"),
                "--profile",
                "diagnostic_only",
                "--diagnostic-only",
                "--output-dir",
                str(tmp_path / "automix"),
                "--deliverables-root",
                str(tmp_path / "deliverables"),
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        required = [
            tmp_path / "automix/export/final_export_state.json",
            tmp_path / "automix/review/final_human_approval.json",
            tmp_path / "automix/export/final_render_manifest.json",
            tmp_path / "automix/eval_reports/final_qc_metrics.json",
            tmp_path / "automix/eval_reports/final_qc_evidence_gate.json",
            tmp_path / "automix/eval_reports/final_qc_report.md",
            tmp_path / "automix/eval_reports/final_approval_evidence_gate.json",
            tmp_path / "automix/eval_reports/deliverable_package_evidence_gate.json",
            tmp_path / "automix/eval_reports/final_delivery_consistency_gate.json",
            tmp_path / "automix/export/deliverable_package_manifest.json",
            tmp_path / "automix/export/project_state_manifest.json",
            tmp_path / "automix/export/plugin_mapping_summary.md",
        ]
        required_exist = all(path.exists() for path in required)
    assert cli.returncode == 0, cli.stderr
    assert "safe_to_export" in cli.stdout
    assert required_exist


def test_cli_final_export_blocks_unresolved_feedback_with_accepted_source(tmp_path: Path) -> None:
    source = write_source(tmp_path / "accepted.wav", sr=48000)
    out = tmp_path / "automix"
    append_revision_memory(
        output_dir=out,
        project_name="accepted",
        pass_id="v01",
        feedback_texts=["마스터가 너무 납작하고 보컬이 뭉개진다."],
    )
    cli = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/run_final_export_packager.py"),
            "--source-stage",
            "accepted_premaster_draft",
            "--source-audio",
            str(source),
            "--profile",
            "diagnostic_only",
            "--diagnostic-only",
            "--approve",
            "--acknowledge-warnings",
            "--output-dir",
            str(out),
            "--deliverables-root",
            str(tmp_path / "deliverables"),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    data = json.loads(cli.stdout)
    state = json.loads((out / "export/final_export_state.json").read_text(encoding="utf-8"))
    assert data["safe_to_export"] is False
    assert data["export_blocked"] is True
    assert "user_feedback_unresolved_for_final_delivery" in state["blocked_reasons"]


def test_docs_for_prompt37_exist_after_generation() -> None:
    assert (ROOT / "docs/final_export_and_delivery.md").exists()
    assert (ROOT / "docs/manual_test_plan_prompt37.md").exists()


if __name__ == "__main__":
    for name, func in sorted(globals().items()):
        if name.startswith("test_") and callable(func):
            func()
    print("prompt37 final export packaging tests passed")

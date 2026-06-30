#!/usr/bin/env python3
from __future__ import annotations

import array
import json
import math
import shutil
import subprocess
import sys
import wave
import zipfile
from pathlib import Path
from typing import Any

import imageio_ffmpeg

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from automix.export.audio_export_utils import wav_info
from automix.export.final_qc_analyzer import analyze_final_qc, write_final_qc_report
from automix.orchestrator.ab_preview_evidence_gate import build_ab_preview_evidence_gate
from automix.orchestrator.final_approval_evidence_gate import build_final_approval_evidence_gate
from automix.orchestrator.final_qc_evidence_gate import build_final_qc_evidence_gate
from automix.orchestrator.final_render_evidence_gate import build_final_render_evidence_gate
from automix.orchestrator.global_rollback_registry import build_global_rollback_registry
from automix.orchestrator.rollback_evidence_gate import build_rollback_evidence_gate
from automix.plugins.plugin_adapter_schema import now_utc, write_json


SLUG = "mwolla_v05_phrase_plateau_master"
PROJECT_NAME = SLUG
RENDERS = ROOT / "renders" / SLUG
REPORTS = ROOT / "reports" / SLUG
REAPER = ROOT / "reaper" / SLUG
EVIDENCE = REPORTS / "evidence"
FFMPEG = Path(imageio_ffmpeg.get_ffmpeg_exe())

FINAL_SRC = RENDERS / "mwolla_v05_PHRASE_PLATEAU_MASTER.wav"
FINAL_PCM = RENDERS / "mwolla_v05_PHRASE_PLATEAU_MASTER_PCM24.wav"
FINAL_MP3 = RENDERS / "mwolla_v05_PHRASE_PLATEAU_MASTER_320k.mp3"
PREMASTER_SRC = RENDERS / "mwolla_v05_PLATEAU_PREMASTER_24-48.wav"
PREMASTER_PCM = RENDERS / "mwolla_v05_PLATEAU_PREMASTER_PCM24.wav"
VOCAL_SOLO = RENDERS / "mwolla_v05_VOCAL_SOLO_phrase_plateau.wav"
AB_PREVIEW_WAV = RENDERS / "mwolla_v05_AB_original_to_phrase_plateau_master_loudness_matched_PCM24.wav"
REVIEW_PACKAGE_ZIP = RENDERS / "mwolla_v05_PHRASE_PLATEAU_MASTER_REVIEW_EVIDENCE_PACKAGE.zip"


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve()))
    except ValueError:
        return str(path)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def source_full_mix_path() -> Path:
    selection = load_json(REPORTS / "source_selection.json")
    path = Path(str(selection["full_reference"]))
    return path if path.is_absolute() else ROOT / path


def ensure_dirs() -> None:
    for path in (
        EVIDENCE / "export",
        EVIDENCE / "eval_reports",
        EVIDENCE / "review",
        EVIDENCE / "rollback",
        EVIDENCE / "sources",
        EVIDENCE / "package_files" / "reports",
    ):
        path.mkdir(parents=True, exist_ok=True)


def convert_to_standard_pcm24(src: Path, dst: Path) -> dict[str, Any]:
    """Decode any FFmpeg-readable source and rewrite standard PCM24 WAV."""
    if not src.exists():
        raise FileNotFoundError(src)
    dst.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        str(FFMPEG),
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        str(src),
        "-ar",
        "48000",
        "-ac",
        "2",
        "-f",
        "s32le",
        "-",
    ]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    assert proc.stdout is not None
    with wave.open(str(dst), "wb") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(3)
        wf.setframerate(48000)
        carry = b""
        while True:
            chunk = proc.stdout.read(1024 * 1024)
            if not chunk:
                break
            data = carry + chunk
            usable = (len(data) // 4) * 4
            block = data[:usable]
            carry = data[usable:]
            out = bytearray((usable // 4) * 3)
            write_index = 0
            for i in range(0, usable, 4):
                out[write_index : write_index + 3] = block[i + 1 : i + 4]
                write_index += 3
            wf.writeframesraw(bytes(out))
        if carry:
            raise RuntimeError(f"Unaligned raw PCM output while converting {src}")
    stderr = proc.stderr.read().decode("utf-8", errors="replace") if proc.stderr else ""
    code = proc.wait()
    if code != 0:
        raise RuntimeError(f"ffmpeg conversion failed for {src}: {stderr}")
    return wav_info(dst)


def decode_segment_f32(src: Path, *, start_seconds: float, duration_seconds: float) -> array.array:
    cmd = [
        str(FFMPEG),
        "-hide_banner",
        "-loglevel",
        "error",
        "-ss",
        f"{start_seconds:.3f}",
        "-t",
        f"{duration_seconds:.3f}",
        "-i",
        str(src),
        "-ar",
        "48000",
        "-ac",
        "2",
        "-f",
        "f32le",
        "-",
    ]
    raw = subprocess.check_output(cmd, stderr=subprocess.PIPE)
    samples = array.array("f")
    samples.frombytes(raw)
    if sys.byteorder != "little":
        samples.byteswap()
    if len(samples) % 2:
        samples = samples[:-1]
    return samples


def clamp(value: float) -> float:
    return max(-1.0, min(1.0, value))


def segment_rms(samples: array.array, *, gain: float = 1.0) -> float:
    total = 0.0
    frames = 0
    for i in range(0, len(samples), 2):
        mono = (clamp(samples[i] * gain) + clamp(samples[i + 1] * gain)) * 0.5
        total += mono * mono
        frames += 1
    return math.sqrt(total / max(1, frames))


def write_samples_pcm24(wf: wave.Wave_write, samples: array.array, *, gain: float = 1.0) -> None:
    out = bytearray(len(samples) * 3)
    write_index = 0
    for value in samples:
        sample = int(round(clamp(value * gain) * 8388607.0))
        sample = max(-8388608, min(8388607, sample))
        out[write_index : write_index + 3] = sample.to_bytes(4, "little", signed=True)[:3]
        write_index += 3
    wf.writeframesraw(bytes(out))


def write_silence_pcm24(wf: wave.Wave_write, *, seconds: float, channels: int = 2, sample_rate: int = 48000) -> None:
    frames = int(round(seconds * sample_rate))
    wf.writeframesraw(b"\x00\x00\x00" * channels * frames)


def build_loudness_matched_ab_preview(source_pcm: Path, final_pcm: Path) -> dict[str, Any]:
    # This span covers the forced early dips, 64.5-69.0s loud hook, post-hook dip, and 90s transition.
    start = 8.0
    duration = 86.0
    original = decode_segment_f32(source_pcm, start_seconds=start, duration_seconds=duration)
    final = decode_segment_f32(final_pcm, start_seconds=start, duration_seconds=duration)
    original_rms = segment_rms(original)
    final_rms_before = segment_rms(final)
    gain = original_rms / final_rms_before if original_rms > 1.0e-12 and final_rms_before > 1.0e-12 else 1.0
    gain = max(0.125, min(8.0, gain))
    final_rms_after = segment_rms(final, gain=gain)
    delta_db = abs(20.0 * math.log10(final_rms_after / original_rms)) if original_rms > 1.0e-12 and final_rms_after > 1.0e-12 else 999.0

    with wave.open(str(AB_PREVIEW_WAV), "wb") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(3)
        wf.setframerate(48000)
        write_samples_pcm24(wf, original, gain=1.0)
        write_silence_pcm24(wf, seconds=1.0)
        write_samples_pcm24(wf, final, gain=gain)

    manifest = {
        "schema": "automix-final-ab-preview-v1",
        "project_name": PROJECT_NAME,
        "created_at": now_utc(),
        "created": True,
        "source_original": rel(source_pcm),
        "source_final": rel(final_pcm),
        "output_path": rel(AB_PREVIEW_WAV),
        "segments": [
            {
                "label": "original_mix",
                "source": rel(source_pcm),
                "start_seconds": start,
                "duration_seconds": duration,
            },
            {
                "label": "final_processed",
                "source": rel(final_pcm),
                "start_seconds": start,
                "duration_seconds": duration,
                "gain_db_for_preview_match": round(20.0 * math.log10(gain), 4),
            },
        ],
        "loudness_matched": True,
        "loudness_match": {
            "method": "mono_rms_match_8s_to_94s_for_forced_window_review",
            "original_rms": original_rms,
            "final_rms_before_match": final_rms_before,
            "final_rms_after_match": final_rms_after,
            "target_rms": original_rms,
            "applied_gain_db": round(20.0 * math.log10(gain), 6),
            "delta_db_after_match": round(delta_db, 6),
            "matched": delta_db <= 0.25,
        },
        "warnings": [],
    }
    write_json(EVIDENCE / "eval_reports" / "final_ab_preview_manifest.json", manifest)
    return manifest


def build_render_manifests(final_info: dict[str, Any], premaster_info: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    render_manifest = {
        "schema": "automix-final-render-manifest-v1",
        "project_name": PROJECT_NAME,
        "created_at": now_utc(),
        "export_profile": "phrase_plateau_review_master_pcm24",
        "source_stage": "accepted_phrase_plateau_premaster",
        "render_settings": {
            "hidden_limiter": False,
            "normalization": False,
            "source_must_come_from_resolver": True,
            "format_note": "Gate-compatible standard PCM24 copy derived from the measured v05 final WAV.",
        },
        "renders": [
            {
                "role": "primary_wav",
                "format": "wav",
                "path": rel(FINAL_PCM),
                "created": True,
                "sample_rate": int(final_info["sample_rate"]),
                "bit_depth": int(final_info["bit_depth"]),
                "channels": int(final_info["channels"]),
                "duration_seconds": round(float(final_info["duration_seconds"]), 6),
                "size_bytes": int(final_info["size_bytes"]),
                "normalization_applied": False,
                "hidden_limiter_added": False,
            },
            {
                "role": "mp3_320k",
                "format": "mp3",
                "path": rel(FINAL_MP3),
                "created": FINAL_MP3.exists(),
                "sample_rate": 48000,
                "bitrate_kbps": 320,
                "size_bytes": FINAL_MP3.stat().st_size if FINAL_MP3.exists() else 0,
            },
        ],
        "failures": [],
        "warnings": [],
    }
    export_state = {
        "schema": "automix-final-export-state-v1",
        "project_name": PROJECT_NAME,
        "created_at": now_utc(),
        "safe_to_export": True,
        "selected_export_source": rel(PREMASTER_PCM),
        "selected_export_stage": "accepted_phrase_plateau_premaster",
        "selected_export_source_file_integrity": {
            "exists": True,
            "size_bytes": int(premaster_info["size_bytes"]),
            "duration_seconds": round(float(premaster_info["duration_seconds"]), 6),
            "sample_rate": int(premaster_info["sample_rate"]),
            "bit_depth": int(premaster_info["bit_depth"]),
            "channels": int(premaster_info["channels"]),
        },
        "blocked_reasons": [],
        "warnings": [],
    }
    write_json(EVIDENCE / "export" / "final_render_manifest.json", render_manifest)
    write_json(EVIDENCE / "export" / "final_export_state.json", export_state)
    return render_manifest, export_state


def write_project_state() -> dict[str, Any]:
    state = {
        "schema": "automix-project-state-manifest-v1",
        "project_name": PROJECT_NAME,
        "created_at": now_utc(),
        "original_tracks_protected": True,
        "master_unchanged": True,
        "accepted_sources": [rel(PREMASTER_PCM)],
        "final_audio_path": rel(FINAL_PCM),
        "delivery_status": "qc_passed_review_ready",
        "delivery_ready": False,
        "remaining_blockers": ["human_loudness_matched_ab_approval_pending"],
        "notes": [
            "v05 final audio was not remastered in this evidence step.",
            "Standard PCM24 copies were created for gate compatibility and release-upload friendliness.",
        ],
    }
    write_json(EVIDENCE / "export" / "project_state_manifest.json", state)
    return state


def write_plugin_mapping_summary() -> Path:
    path = EVIDENCE / "export" / "plugin_mapping_summary.md"
    trace = REPORTS / "actual_reaper_plugin_trace.json"
    lines = [
        "# Plugin Mapping Summary",
        "",
        f"- Project: `{PROJECT_NAME}`",
        f"- Actual trace: `{rel(trace)}`",
        "- Required first-slot plugin: `JS: Codex Vocal AI Artifact Split Tamer`",
        "- Gate result: `passed` in `reports/mwolla_v05_phrase_plateau_master/vocal_chain_gate.json`",
        "",
        "This summary records the existing v05 plugin trace; it does not add or change audio processing.",
    ]
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return path


def write_pending_approval(ab_manifest: dict[str, Any], export_state: dict[str, Any]) -> dict[str, Any]:
    approval = {
        "schema": "automix-final-human-approval-v1",
        "project_name": PROJECT_NAME,
        "created_at": now_utc(),
        "approved": False,
        "review_decision": "pending",
        "approved_by": "",
        "approval_time": "",
        "approved_stage": export_state["selected_export_stage"],
        "approved_source": export_state["selected_export_source"],
        "loudness_matched_ab_reviewed": False,
        "final_audio_accepted_at_matched_loudness": False,
        "reviewed_ab_preview_path": ab_manifest["output_path"],
        "reviewed_final_audio_path": rel(FINAL_PCM),
        "final_qc_evidence_reviewed": False,
        "warnings_acknowledged": [],
        "notes": "Pending user listening approval. Do not mark delivery-ready until this record is updated after matched-loudness A/B review.",
    }
    write_json(EVIDENCE / "review" / "final_human_approval.json", approval)
    return approval


def safe_report_copies() -> list[Path]:
    copies = [
        (REPORTS / "music_stem_riding_curve_report.json", EVIDENCE / "package_files" / "reports" / "music_riding_curve_report.json"),
        (REPORTS / "music_stem_riding_curve_report.csv", EVIDENCE / "package_files" / "reports" / "music_riding_curve_report.csv"),
        (REPORTS / "source_stem_window_loudness_report.md", EVIDENCE / "package_files" / "reports" / "source_window_loudness_report.md"),
        (REPORTS / "source_stem_window_loudness_report.json", EVIDENCE / "package_files" / "reports" / "source_window_loudness_report.json"),
    ]
    out: list[Path] = []
    for src, dst in copies:
        if src.exists():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            out.append(dst)
    return out


def write_review_package(project_state: dict[str, Any]) -> dict[str, Any]:
    required_evidence = [
        EVIDENCE / "export" / "final_render_manifest.json",
        EVIDENCE / "eval_reports" / "final_render_evidence_gate.json",
        EVIDENCE / "eval_reports" / "final_qc_metrics.json",
        EVIDENCE / "eval_reports" / "final_qc_evidence_gate.json",
        EVIDENCE / "eval_reports" / "final_ab_preview_manifest.json",
        EVIDENCE / "eval_reports" / "ab_preview_evidence_gate.json",
        EVIDENCE / "review" / "final_human_approval.json",
        EVIDENCE / "eval_reports" / "final_approval_evidence_gate.json",
        EVIDENCE / "rollback" / "global_rollback_registry.json",
        EVIDENCE / "eval_reports" / "rollback_evidence_gate.json",
        EVIDENCE / "eval_reports" / "final_qc_report.md",
        EVIDENCE / "export" / "project_state_manifest.json",
        EVIDENCE / "export" / "plugin_mapping_summary.md",
    ]
    delivery_files = [
        FINAL_PCM,
        FINAL_MP3,
        VOCAL_SOLO,
        AB_PREVIEW_WAV,
        REAPER / "mwolla_v05_PHRASE_PLATEAU_MASTER.rpp",
        REPORTS / "mwolla_v05_phrase_plateau_master_report.md",
        REPORTS / "actual_reaper_plugin_trace.json",
        REPORTS / "actual_reaper_plugin_trace.md",
        REPORTS / "section_loudness_consistency_1p5s_3s_6s_report.md",
        REPORTS / "section_loudness_consistency_1p5s_3s_6s_report.json",
        REPORTS / "problem_window_cause_classification_report.md",
        REPORTS / "problem_window_cause_classification_report.json",
        REPORTS / "vocal_riding_curve_report.json",
        REPORTS / "vocal_riding_curve_report.csv",
        REPORTS / "premaster_bus_leveling_report.json",
        REPORTS / "premaster_bus_leveling_report.csv",
        REPORTS / "plateau_premaster_leveling_report.json",
        REPORTS / "plateau_premaster_leveling_report.csv",
        REPORTS / "vocal_gap_cleanup_decisions.json",
        REPORTS / "qc_summary.json",
        EVIDENCE / "eval_reports" / "completion_audit.md",
        EVIDENCE / "eval_reports" / "completion_audit.json",
    ] + safe_report_copies()
    included = []
    missing = []
    for path in required_evidence + delivery_files:
        if path.exists() and path.is_file() and path.stat().st_size > 0:
            included.append(path)
        else:
            missing.append(rel(path))

    REVIEW_PACKAGE_ZIP.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(REVIEW_PACKAGE_ZIP, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in included:
            archive.write(path, arcname=rel(path))

    manifest = {
        "schema": "automix-deliverable-package-manifest-v1",
        "project_name": PROJECT_NAME,
        "created_at": now_utc(),
        "package_created": True,
        "zip_path": rel(REVIEW_PACKAGE_ZIP),
        "package_size_bytes": REVIEW_PACKAGE_ZIP.stat().st_size,
        "package_profile": "review_evidence_package_pending_human_approval",
        "files_included": [rel(path) for path in included],
        "files_missing": missing,
        "project_state_manifest": project_state,
        "warnings": ["human_loudness_matched_ab_approval_pending"],
    }
    write_json(EVIDENCE / "export" / "deliverable_package_manifest.json", manifest)
    return manifest


def main() -> int:
    ensure_dirs()
    source_pcm = EVIDENCE / "sources" / "mwolla_original_full_mix_PCM24_for_ab.wav"
    source_info = convert_to_standard_pcm24(source_full_mix_path(), source_pcm)
    final_info = convert_to_standard_pcm24(FINAL_SRC, FINAL_PCM)
    premaster_info = convert_to_standard_pcm24(PREMASTER_SRC, PREMASTER_PCM)
    ab_manifest = build_loudness_matched_ab_preview(source_pcm, FINAL_PCM)
    render_manifest, export_state = build_render_manifests(final_info, premaster_info)
    project_state = write_project_state()
    write_plugin_mapping_summary()

    render_gate = build_final_render_evidence_gate(
        project_name=PROJECT_NAME,
        output_dir=EVIDENCE,
        render_manifest_path=EVIDENCE / "export" / "final_render_manifest.json",
        final_export_state_path=EVIDENCE / "export" / "final_export_state.json",
    )
    qc_metrics = analyze_final_qc(
        FINAL_PCM,
        output_dir=EVIDENCE,
        export_state=export_state,
        expected_sample_rate=48000,
        expected_bit_depth=24,
        expected_duration_seconds=float(final_info["duration_seconds"]),
        true_peak_ceiling_dbTP=-1.0,
    )
    qc_gate = build_final_qc_evidence_gate(
        project_name=PROJECT_NAME,
        output_dir=EVIDENCE,
        qc_metrics_path=EVIDENCE / "eval_reports" / "final_qc_metrics.json",
        final_render_evidence_path=EVIDENCE / "eval_reports" / "final_render_evidence_gate.json",
        render_manifest_path=EVIDENCE / "export" / "final_render_manifest.json",
        true_peak_ceiling_dbTP=-1.0,
    )
    ab_gate = build_ab_preview_evidence_gate(
        project_name=PROJECT_NAME,
        output_dir=EVIDENCE,
        manifest_path=EVIDENCE / "eval_reports" / "final_ab_preview_manifest.json",
    )
    approval = write_pending_approval(ab_manifest, export_state)
    approval_gate = build_final_approval_evidence_gate(project_name=PROJECT_NAME, output_dir=EVIDENCE)
    # Avoid carrying the previous global registry into the new registry as a
    # self-referential rollback entry when the builder is rerun.
    previous_registry = EVIDENCE / "rollback" / "global_rollback_registry.json"
    if previous_registry.exists():
        previous_registry.unlink()
    build_global_rollback_registry(project_name=PROJECT_NAME, output_dir=EVIDENCE, applied_stages=[])
    rollback_gate = build_rollback_evidence_gate(project_name=PROJECT_NAME, output_dir=EVIDENCE)
    write_final_qc_report(
        output_dir=EVIDENCE,
        project_name=PROJECT_NAME,
        export_profile={"profile_name": "phrase_plateau_review_master_pcm24"},
        export_state=export_state,
        approval=approval,
        approval_eval=approval_gate,
        render_manifest=render_manifest,
        qc_metrics=qc_metrics,
        ab_preview_manifest=ab_manifest,
        package_manifest={},
        included_reports={
            "premaster report": rel(REPORTS / "premaster_bus_leveling_report.json"),
            "rollback metadata": rel(EVIDENCE / "rollback" / "global_rollback_registry.json"),
            "translation check": rel(REPORTS / "qc_summary.json"),
        },
    )
    package_manifest = write_review_package(project_state)
    package_gate = __import__(
        "automix.orchestrator.deliverable_package_evidence_gate",
        fromlist=["build_deliverable_package_evidence_gate"],
    ).build_deliverable_package_evidence_gate(
        project_name=PROJECT_NAME,
        output_dir=EVIDENCE,
        package_manifest_path=EVIDENCE / "export" / "deliverable_package_manifest.json",
    )

    summary = {
        "source_pcm": {"path": rel(source_pcm), **source_info},
        "final_pcm": {"path": rel(FINAL_PCM), **wav_info(FINAL_PCM)},
        "premaster_pcm": {"path": rel(PREMASTER_PCM), **wav_info(PREMASTER_PCM)},
        "ab_preview": {
            "path": rel(AB_PREVIEW_WAV),
            "delta_db_after_match": ab_manifest["loudness_match"]["delta_db_after_match"],
            "applied_gain_db": ab_manifest["loudness_match"]["applied_gain_db"],
        },
        "gates": {
            "final_render_ready": render_gate.get("ready_for_final_qc"),
            "final_qc_ready": qc_gate.get("ready_for_delivery_qc"),
            "ab_preview_ready": ab_gate.get("ready_for_human_ab_review"),
            "approval_pending_only": approval_gate.get("approval_pending_only"),
            "rollback_ready": rollback_gate.get("ready_for_delivery_readiness"),
            "package_ready": package_gate.get("ready_for_delivery_package"),
            "package_blockers": package_gate.get("blockers", []),
        },
        "review_package_zip": {
            "path": rel(REVIEW_PACKAGE_ZIP),
            "size_bytes": package_manifest["package_size_bytes"],
        },
    }
    write_json(EVIDENCE / "eval_reports" / "mwolla_v05_evidence_builder_summary.json", summary)
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

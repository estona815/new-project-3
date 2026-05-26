from __future__ import annotations

from pathlib import Path
from typing import Any

from audio_render_manifest import build_audio_render_manifest, write_audio_render_manifest
from completion_gate import check_completion_status
from export_status import derive_render_status
from final_verify import verify_final_wav
from release_mix_master_autopilot import release_package_audio_ready
from release_workflow_orchestrator import build_release_workflow_status, write_release_workflow_status


def classify_project_state(project_root: str | Path) -> str:
    root = Path(project_root)
    return derive_render_status(
        analysis_ready=(root / "01_ANALYSIS" / "analysis.json").exists() or (root / "01_ANALYSIS" / "sample_analysis.json").exists(),
        vocal_code_ready=(root / "01_ANALYSIS" / "vocal_to_code.json").exists(),
        arrangement_plan_ready=(root / "02_EDIT_PLAN" / "arrangement_plan.json").exists(),
        midi_guide_ready=(root / "02_EDIT_PLAN" / "midi_region_guide.json").exists(),
        logic_manual_required=(root / "02_EDIT_PLAN" / "logic_arrangement_plan.md").exists(),
        fallback_exported=(root / "04_PROCESSED_AUDIO" / "fallback_processed.wav").exists(),
        final_wav_exists=any((root / "05_FINAL_WAV").glob("*.wav")) if (root / "05_FINAL_WAV").exists() else False,
    )


def classify_release_project_state(project_root: str | Path, workflow: str | None = None, mode: str | None = None) -> str:
    status = build_release_workflow_status(project_root=project_root, workflow=workflow, mode=mode)
    return str(status["status"])


def classify_release_package_audio(project_root: str | Path, requested_format: str = "wav24_48k") -> dict[str, Any]:
    root = Path(project_root)
    final_wavs = sorted((root / "05_FINAL_WAV").glob("*.wav")) if (root / "05_FINAL_WAV").exists() else []
    final_wav = final_wavs[0] if final_wavs else None
    return release_package_audio_ready(
        final_wav_path=final_wav,
        requested_format=requested_format,
        qc_report_path=root / "06_QC_REPORT" / "qc_report.md",
        release_checklist_path=root / "06_QC_REPORT" / "release_checklist.md",
    )


def build_plan_only_manifest(project_root: str | Path, status: str) -> dict[str, Any]:
    return build_audio_render_manifest(
        status=status,
        source_files=[],
        rendered_files=[],
        final_verify_result={},
        completion_gate={"complete": False, "blocking_reasons": [f"{status} is not a verified final WAV state"]},
    )


def verify_final_render(
    *,
    project_root: str | Path,
    final_wav_path: str | Path,
    requested_format: str,
    qc_report_path: str | Path | None,
    master_qc_report_path: str | Path | None = None,
    require_master_qc: bool = False,
    manifest_path: str | Path | None = None,
) -> dict[str, Any]:
    root = Path(project_root)
    final_path = Path(final_wav_path)
    try:
        verification = verify_final_wav(final_path, requested_format)
    except Exception as error:  # noqa: BLE001 - manifest should fail closed.
        verification = {"path": str(final_path), "exists": final_path.exists(), "ok": False, "errors": [str(error)]}
    gate = check_completion_status(
        final_wav_path=final_path,
        qc_report_path=qc_report_path,
        requested_format=requested_format,
        final_verify_result=verification,
        require_master_qc=require_master_qc,
        master_qc_report_path=master_qc_report_path,
    )
    status = derive_render_status(
        final_wav_exists=final_path.exists(),
        final_wav_verified=bool(verification.get("ok")),
        completion_complete=gate.complete,
    )
    manifest = build_audio_render_manifest(
        status=status,
        source_files=[],
        rendered_files=[str(final_path)] if final_path.exists() else [],
        final_verify_result=verification,
        qc_report_path=qc_report_path,
        master_qc_report_path=master_qc_report_path,
        completion_gate=gate,
    )
    output = Path(manifest_path) if manifest_path else root / "06_QC_REPORT" / "audio_render_manifest.json"
    write_audio_render_manifest(output, manifest)
    release_status = write_release_workflow_status(
        project_root=root,
        completion_gate=gate,
        final_audio_verified=bool(verification.get("ok")),
    )
    return {
        "status": status,
        "verification": verification,
        "completion_gate": gate,
        "manifest": manifest,
        "manifest_path": output,
        "release_status": release_status["status"],
        "release_status_path": release_status["path"],
    }

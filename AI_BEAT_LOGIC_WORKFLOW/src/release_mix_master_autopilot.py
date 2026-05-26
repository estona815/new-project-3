from __future__ import annotations

from pathlib import Path
from typing import Any

from deliverable_audio_profiles import build_deliverable_profiles
from final_verify import verify_release_package_audio_readiness
from release_master_targets import build_release_master_target, release_master_verified


def build_release_mix_master_plan(
    *,
    input_mode: str = "instrumental_beat",
    master_target_mode: str | None = None,
    release_ready: bool = False,
    requested_deliverables: list[str] | None = None,
    dependency_capabilities: dict[str, Any] | None = None,
    final_verify_result: dict[str, Any] | None = None,
    final_format: str = "wav24_48k",
    qc_report_exists: bool = False,
    release_checklist_exists: bool = False,
    isolated_vocal_available: bool = False,
    stems_provided: bool = False,
    stem_separation_verified: bool = False,
    mp3_preview_created: bool = False,
) -> dict[str, Any]:
    plugins = (dependency_capabilities or {}).get("plugins", {})
    target = build_release_master_target(master_target_mode, release_ready=release_ready)
    deliverables = build_deliverable_profiles(
        requested_profiles=requested_deliverables,
        input_mode=input_mode,
        isolated_vocal_available=isolated_vocal_available,
        stems_provided=stems_provided,
        stem_separation_verified=stem_separation_verified,
        mp3_preview_created=mp3_preview_created,
        final_wav_verified=bool((final_verify_result or {}).get("ok") or (final_verify_result or {}).get("passed")),
        final_format=final_format,
    )
    verified = release_master_verified(
        final_verify_result=final_verify_result,
        qc_report_exists=qc_report_exists,
        release_checklist_exists=release_checklist_exists,
        require_release_checklist=release_ready,
    )
    return {
        "schema_version": "release_mix_master_plan.v1",
        "input_mode": input_mode,
        "master_target": target,
        "actual_processing_performed": [
            "release mix/master planning",
            "final verification summary attached" if final_verify_result else "no final verification attached yet",
        ],
        "recommended_only": [
            "plugin insertion unless verified",
            "stem-level balancing unless stems exist",
            "acapella/stem deliverables unless source exists",
            "Logic automation unless verified",
        ],
        "plugin_requests": {
            "available_plugins_detected": sorted(key for key, value in plugins.items() if isinstance(value, dict) and value.get("available")),
            "applied": [],
            "manual": ["all plugin-style requests require manual insert unless verified"],
            "fallback": ["generic EQ/dynamics/saturation only when actual fallback processing runs"],
        },
        "stereo_only_limitations": [] if input_mode == "stems" else [
            "Stereo-only processing cannot claim stem-level remixing.",
            "No guaranteed vocal removal, true kick/bass replacement, true drum rewrite, true stem separation, or plugin insertion is claimed.",
        ],
        "stem_mode_capabilities": [
            "Direct balancing allowed for provided stems" if input_mode == "stems" or stems_provided else "Stem capabilities unavailable until stems are provided or verified separation exists."
        ],
        "deliverable_profiles": deliverables,
        "final_verification_summary": {
            "verified": verified["verified"],
            "blocking_reasons": verified["blocking_reasons"],
            "source": verified["verification_source"],
            "sample_rate": (final_verify_result or {}).get("sample_rate"),
            "format_verified": bool((final_verify_result or {}).get("format_verified")),
            "clipping_count": (final_verify_result or {}).get("clipping_count"),
            "peak_dbfs": (final_verify_result or {}).get("peak_dbfs"),
            "rms_dbfs": (final_verify_result or {}).get("rms_dbfs"),
        },
        "claim_guard": {
            "final_master_verified": bool(verified["verified"]),
            "verified_only_after_final_verify": True,
            "acapella_faked": False,
            "stems_faked": False,
            "plugin_processing_verified": False,
        },
    }


def release_package_audio_ready(
    *,
    final_wav_path: str | Path | None,
    requested_format: str,
    qc_report_path: str | Path | None = None,
    release_checklist_path: str | Path | None = None,
) -> dict[str, Any]:
    return verify_release_package_audio_readiness(
        final_wav_path=final_wav_path,
        requested_format=requested_format,
        qc_report_path=qc_report_path,
        release_checklist_path=release_checklist_path,
    )

from __future__ import annotations

from typing import Any


STATUS_VALUES = {
    "ANALYSIS_READY",
    "VOCAL_CODE_READY",
    "ARRANGEMENT_PLAN_READY",
    "MIDI_GUIDE_READY",
    "LOGIC_MANUAL_REQUIRED",
    "FALLBACK_AUDIO_EXPORTED_UNVERIFIED",
    "FINAL_WAV_EXPORTED_UNVERIFIED",
    "FINAL_WAV_EXPORTED_VERIFIED",
    "COMPLETE",
    "FAILED",
}


def normalize_export_status(status: str | None) -> str:
    return status if status in STATUS_VALUES else "FAILED"


def status_allows_complete(status: str | None) -> bool:
    return status == "COMPLETE"


def derive_render_status(
    *,
    analysis_ready: bool = False,
    vocal_code_ready: bool = False,
    arrangement_plan_ready: bool = False,
    midi_guide_ready: bool = False,
    logic_manual_required: bool = False,
    fallback_exported: bool = False,
    final_wav_exists: bool = False,
    final_wav_verified: bool = False,
    completion_complete: bool = False,
    failed: bool = False,
) -> str:
    if failed:
        return "FAILED"
    if completion_complete:
        return "COMPLETE"
    if final_wav_verified:
        return "FINAL_WAV_EXPORTED_VERIFIED"
    if final_wav_exists:
        return "FINAL_WAV_EXPORTED_UNVERIFIED"
    if fallback_exported:
        return "FALLBACK_AUDIO_EXPORTED_UNVERIFIED"
    if logic_manual_required:
        return "LOGIC_MANUAL_REQUIRED"
    if midi_guide_ready:
        return "MIDI_GUIDE_READY"
    if arrangement_plan_ready:
        return "ARRANGEMENT_PLAN_READY"
    if vocal_code_ready:
        return "VOCAL_CODE_READY"
    if analysis_ready:
        return "ANALYSIS_READY"
    return "FAILED"


def complete_claim_guard(status: str, completion_gate: dict[str, Any] | None = None) -> dict[str, Any]:
    gate = completion_gate or {}
    return {
        "status": normalize_export_status(status),
        "complete_allowed": status_allows_complete(status) and bool(gate.get("complete")),
        "completion_gate_complete": bool(gate.get("complete")),
        "rule": "Completion gate remains final authority; plan/guide/fallback/unverified export cannot emit COMPLETE.",
    }

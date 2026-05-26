from __future__ import annotations

from typing import Any

from audio_backend_registry import build_audio_backend_registry, can_export_final_wav
from release_status import REQUEST_PARSED


def build_autopilot_status(dependency_capabilities: dict[str, Any]) -> dict[str, Any]:
    registry = build_audio_backend_registry(dependency_capabilities)
    capabilities = dependency_capabilities.get("capabilities", {})
    plugins = dependency_capabilities.get("plugins", {})
    render_available = can_export_final_wav(registry)
    plan_only_reasons: list[str] = []
    if not render_available:
        plan_only_reasons.append("final WAV export backend unavailable")
    if capabilities.get("logic_project_creation") != "available":
        plan_only_reasons.append("Logic project creation is unavailable or manual-only")
    if capabilities.get("plugin_automation") != "partial":
        plan_only_reasons.append("plugin automation is not verified")
    return {
        "schema_version": "autopilot_status.v1",
        "mode": "render_capable" if render_available else "plan_only",
        "plan_only": not render_available,
        "final_wav_export_available": render_available,
        "completion_possible": False,
        "completion_rule": "Only src/main.py may print COMPLETE after src/completion_gate.py passes all final WAV and QC checks.",
        "release_status_model": {
            "initial_status": REQUEST_PARSED,
            "release_package_separate_from_complete": True,
            "plan_only_statuses_complete_allowed": False,
            "completion_requires_release_qc_when_release_ready": True,
        },
        "capability_summary": {
            "metadata_probe": registry["metadata_probe_backend"],
            "wav_export": registry["wav_export_backend"],
            "bpm_estimation": capabilities.get("bpm_estimation"),
            "key_estimation": capabilities.get("key_estimation"),
            "vocal_pitch_tracking": capabilities.get("vocal_pitch_tracking"),
            "logic_project_creation": capabilities.get("logic_project_creation"),
            "plugin_automation": capabilities.get("plugin_automation"),
        },
        "plugin_status": {
            "autotune_like": plugins.get("autotune_like", {}).get("status", "manual_required"),
            "soundtoys_decapitator": plugins.get("soundtoys_decapitator", {}).get("status", "not_detected"),
            "claim_rule": "Detected plugins are availability hints only; no plugin-applied claim is allowed without verified processing.",
        },
        "plan_only_reasons": plan_only_reasons,
        "blocking_reasons": registry.get("blocking_reasons", []),
        "limitations": list(dependency_capabilities.get("limitations", [])),
    }


def final_export_blocked(status: dict[str, Any]) -> bool:
    return not bool(status.get("final_wav_export_available"))


def plugin_claim_allowed(status: dict[str, Any]) -> bool:
    return False

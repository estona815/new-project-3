from __future__ import annotations

from typing import Any


def build_audio_backend_registry(dependency_capabilities: dict[str, Any]) -> dict[str, Any]:
    capabilities = dependency_capabilities.get("capabilities", {})
    tools = dependency_capabilities.get("tools", {})
    wav_export = capabilities.get("wav_export", "unavailable")
    metadata_probe = capabilities.get("metadata_probe", "stdlib")
    render_available = wav_export != "unavailable"
    return {
        "schema_version": "audio_backend_registry.v1",
        "metadata_probe_backend": metadata_probe,
        "wav_export_backend": wav_export,
        "render_available": render_available,
        "analysis_backends": {
            "peak_rms": "stdlib_wave" if capabilities.get("peak_rms_analysis") else "unavailable",
            "rough_onset": capabilities.get("bpm_estimation", "unavailable"),
            "bpm": capabilities.get("bpm_estimation", "unavailable"),
            "key": capabilities.get("key_estimation", "unavailable"),
            "vocal_pitch": capabilities.get("vocal_pitch_tracking", "unavailable"),
        },
        "tool_paths": {
            name: item.get("path")
            for name, item in tools.items()
            if isinstance(item, dict) and item.get("path")
        },
        "final_export_blocked": not render_available,
        "blocking_reasons": [] if render_available else ["No verified WAV export backend is available."],
        "claim_rules": [
            "Missing optional dependencies degrade to stdlib/heuristic analysis.",
            "Final WAV export must be blocked when wav_export_backend is unavailable.",
            "Plugin-applied claims require verified processing, not dependency detection alone.",
            "Logic success requires a verified project or export artifact.",
        ],
    }


def can_export_final_wav(registry: dict[str, Any]) -> bool:
    return bool(registry.get("render_available") and not registry.get("final_export_blocked"))


def choose_metadata_probe(registry: dict[str, Any]) -> str:
    return str(registry.get("metadata_probe_backend") or "stdlib")


def choose_wav_export_backend(registry: dict[str, Any]) -> str:
    return str(registry.get("wav_export_backend") or "unavailable")

from __future__ import annotations

from copy import deepcopy
from typing import Any


TARGET_PROFILES: dict[str, dict[str, Any]] = {
    "digicore_hyperpop_hiphop_vocal_forward": {
        "purpose": "Strong lead vocal, clear digital lead melody, energetic drums/808, controlled high-end, commercial but not over-clean.",
        "vocal_forwardness_target": 0.80,
        "lead_melody_prominence_target": 0.78,
        "drum_energy_target": 0.75,
        "808_energy_target": 0.72,
        "low_end_control_target": 0.75,
        "presence_clarity_target": 0.76,
        "air_band_target": 0.62,
        "harshness_max": 0.45,
        "sibilance_max": 0.42,
        "stereo_width_target": 0.68,
        "mono_compatibility_min": 0.70,
        "loudness_target_lufs_range": [-11.5, -8.5],
        "lra_target_range": [3.0, 7.0],
        "ai_artifact_exposure_max": 0.35,
        "recommended_priority": [
            "vocal_forwardness",
            "lead_melody_prominence",
            "low_end_control",
            "drum_energy",
            "harshness_control",
            "safe_loudness",
        ],
    },
    "raw_digicore_intense": {
        "purpose": "More intense, raw, distorted, fast, aggressive, but still vocal-centered and artifact-controlled.",
        "vocal_forwardness_target": 0.76,
        "lead_melody_prominence_target": 0.82,
        "drum_energy_target": 0.86,
        "808_energy_target": 0.80,
        "low_end_control_target": 0.68,
        "presence_clarity_target": 0.74,
        "air_band_target": 0.60,
        "harshness_max": 0.55,
        "sibilance_max": 0.45,
        "stereo_width_target": 0.70,
        "mono_compatibility_min": 0.64,
        "loudness_target_lufs_range": [-10.5, -7.5],
        "lra_target_range": [2.5, 6.0],
        "ai_artifact_exposure_max": 0.40,
        "recommended_priority": [
            "drum_energy",
            "lead_melody_prominence",
            "vocal_forwardness",
            "808_energy",
            "artifact_guard",
            "safe_loudness",
        ],
    },
    "clean_commercial_ai_repair": {
        "purpose": "Make AI/Suno source sound cleaner, more stable, less fake, with safer high-end and controlled dynamics.",
        "vocal_forwardness_target": 0.78,
        "lead_melody_prominence_target": 0.70,
        "drum_energy_target": 0.68,
        "808_energy_target": 0.65,
        "low_end_control_target": 0.82,
        "presence_clarity_target": 0.80,
        "air_band_target": 0.58,
        "harshness_max": 0.35,
        "sibilance_max": 0.34,
        "stereo_width_target": 0.62,
        "mono_compatibility_min": 0.78,
        "loudness_target_lufs_range": [-13.0, -10.0],
        "lra_target_range": [4.0, 8.0],
        "ai_artifact_exposure_max": 0.25,
        "recommended_priority": [
            "artifact_reduction",
            "vocal_clarity",
            "mono_compatibility",
            "low_end_control",
            "safe_premaster",
        ],
    },
    "melody_sample_flip_forward": {
        "purpose": "Strong piano/synth/sample lead melody in front, vocal and melody balanced, drums support the hook.",
        "vocal_forwardness_target": 0.72,
        "lead_melody_prominence_target": 0.86,
        "drum_energy_target": 0.70,
        "808_energy_target": 0.68,
        "low_end_control_target": 0.72,
        "presence_clarity_target": 0.74,
        "air_band_target": 0.60,
        "harshness_max": 0.42,
        "sibilance_max": 0.38,
        "stereo_width_target": 0.70,
        "mono_compatibility_min": 0.70,
        "loudness_target_lufs_range": [-12.0, -9.0],
        "lra_target_range": [3.5, 7.5],
        "ai_artifact_exposure_max": 0.32,
        "recommended_priority": [
            "lead_melody_prominence",
            "vocal_balance",
            "drum_support",
            "low_end_control",
            "artifact_guard",
        ],
    },
    "phone_reels_loud_clear": {
        "purpose": "15-60 second reels/shorts mix where vocal and hook are clear on phone speakers.",
        "vocal_forwardness_target": 0.84,
        "lead_melody_prominence_target": 0.78,
        "drum_energy_target": 0.72,
        "808_energy_target": 0.55,
        "low_end_control_target": 0.78,
        "presence_clarity_target": 0.84,
        "air_band_target": 0.56,
        "harshness_max": 0.38,
        "sibilance_max": 0.36,
        "stereo_width_target": 0.58,
        "mono_compatibility_min": 0.82,
        "loudness_target_lufs_range": [-11.0, -8.0],
        "lra_target_range": [2.5, 5.5],
        "ai_artifact_exposure_max": 0.30,
        "recommended_priority": [
            "phone_vocal_audibility",
            "hook_clarity",
            "sibilance_control",
            "mono_compatibility",
            "safe_loudness",
        ],
    },
}


DEFAULT_TARGET_PROFILE = "digicore_hyperpop_hiphop_vocal_forward"


def get_target_profile(name: str | None) -> dict[str, Any]:
    key = name or DEFAULT_TARGET_PROFILE
    if key not in TARGET_PROFILES:
        raise ValueError(f"Unknown target profile: {key}")
    profile = deepcopy(TARGET_PROFILES[key])
    profile["profile_name"] = key
    profile["safety_constraints_override_matching"] = True
    profile["copyright_safety_note"] = (
        "Target profiles guide broad mix, tonal, energy, and translation decisions only. "
        "They are not commands to copy melody, lyrics, arrangement, artist identity, or reference audio."
    )
    return profile


def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, float(value)))


def target_gap(current: float, target: float) -> float:
    return round(clamp(float(target) - float(current)), 6)


def max_excess(current: float, maximum: float) -> float:
    return round(clamp(float(current) - float(maximum)), 6)


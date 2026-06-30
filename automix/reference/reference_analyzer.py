from __future__ import annotations

from pathlib import Path
from typing import Any

from automix.analyze_ai_pitch_source import AudioData, clamp, dynamic_features, read_wav, rms, safe_filename, write_json
from automix.mastering.premaster_safety_analyzer import (
    ai_artifact_risk_profile,
    loudness_profile,
    stereo_profile,
    tonal_profile,
    translation_profile,
    vocal_preservation_profile,
)


def energy_profile(audio: AudioData | None, tonal: dict[str, float] | None = None) -> dict[str, float]:
    if audio is None:
        return {
            "drum_energy": 0.0,
            "808_energy": 0.0,
            "transient_punch": 0.0,
            "rhythmic_density": 0.0,
            "hook_energy": 0.0,
        }
    tonal = tonal or tonal_profile(audio)
    dyn = dynamic_features(audio.mono)
    low = tonal["sub_20_60"] + tonal["bass_60_120"]
    return {
        "drum_energy": round(clamp(dyn["transient_density_score"] * 0.55 + low * 0.35 + dyn["rms_density_score"] * 0.10), 6),
        "808_energy": round(clamp(tonal["sub_20_60"] * 0.70 + tonal["bass_60_120"] * 0.50), 6),
        "transient_punch": round(clamp(dyn["transient_density_score"]), 6),
        "rhythmic_density": round(clamp(dyn["rms_density_score"]), 6),
        "hook_energy": round(clamp(tonal["presence_1k_4k"] * 0.38 + tonal["mid_350_1k"] * 0.22 + dyn["rms_density_score"] * 0.20), 6),
    }


def melody_profile(tonal: dict[str, float], loudness: dict[str, float]) -> dict[str, float]:
    density = clamp(tonal["mid_350_1k"] * 0.30 + tonal["presence_1k_4k"] * 0.45 + tonal["air_10k_16k"] * 0.15)
    stability = clamp(density - loudness["limiter_pressure_risk"] * 0.12)
    return {
        "lead_melody_prominence": round(clamp(tonal["presence_1k_4k"] * 0.48 + tonal["mid_350_1k"] * 0.28 + tonal["low_mid_120_350"] * 0.10), 6),
        "mid_high_melodic_density": round(density, 6),
        "hook_melody_stability": round(stability, 6),
    }


def reference_vocal_profile(tonal: dict[str, float], loudness: dict[str, float]) -> dict[str, float]:
    vocal = vocal_preservation_profile(tonal, loudness)
    return {
        "vocal_forwardness": vocal["vocal_forwardness_score"],
        "vocal_clarity": vocal["vocal_clarity_score"],
        "vocal_body": vocal["vocal_body_score"],
        "vocal_presence": tonal["presence_1k_4k"],
        "vocal_air": tonal["air_10k_16k"],
        "vocal_sibilance": tonal["sibilance_5k_10k"],
    }


def analyze_reference_audio(
    audio: AudioData | None,
    *,
    reference_name: str,
    role: str,
    path: str = "",
) -> dict[str, Any]:
    loud = loudness_profile(audio)
    tonal = tonal_profile(audio)
    stereo = stereo_profile(audio)
    artifact = ai_artifact_risk_profile(tonal, loud, stereo)
    vocal = reference_vocal_profile(tonal, loud)
    melody = melody_profile(tonal, loud)
    energy = energy_profile(audio, tonal)
    warnings: list[str] = []
    if artifact["high_fizz_risk"] > 0.55:
        warnings.append("reference_has_high_fizz_or_air_risk_do_not_copy_brightness")
    if loud["limiter_pressure_risk"] > 0.65:
        warnings.append("reference_is_heavily_limited_do_not_chase_loudness_blindly")
    if stereo["mono_compatibility_risk"] > 0.55:
        warnings.append("reference_width_has_phase_risk_do_not_copy_width")
    return {
        "schema": "automix-reference-analysis-v1",
        "reference_name": reference_name,
        "role": role,
        "path": path,
        "loudness_profile": {
            "integrated_lufs": loud["integrated_lufs"],
            "true_peak_dbTP": loud["true_peak_dbTP"],
            "lra": loud["lra"],
            "crest_factor": loud["crest_factor"],
            "peak_density_score": loud["peak_density_score"],
            "limiter_pressure_risk": loud["limiter_pressure_risk"],
        },
        "tonal_profile": {
            "sub_20_60": tonal["sub_20_60"],
            "bass_60_120": tonal["bass_60_120"],
            "low_mid_120_350": tonal["low_mid_120_350"],
            "mid_350_1k": tonal["mid_350_1k"],
            "presence_1k_4k": tonal["presence_1k_4k"],
            "harshness_2k5_6k": tonal["harshness_2k5_6k"],
            "sibilance_5k_10k": tonal["sibilance_5k_10k"],
            "air_10k_16k": tonal["air_10k_16k"],
        },
        "energy_profile": energy,
        "vocal_profile": vocal,
        "melody_profile": melody,
        "stereo_profile": {
            "stereo_width_score": stereo["stereo_width_score"],
            "mid_energy_score": stereo["mid_energy_score"],
            "side_energy_score": stereo["side_energy_score"],
            "mono_compatibility_risk": stereo["mono_compatibility_risk"],
            "phase_correlation": stereo["phase_correlation"],
            "low_end_stereo_risk": stereo["low_end_stereo_risk"],
        },
        "artifact_profile": artifact,
        "translation_profile": translation_profile(tonal, artifact, stereo, vocal_preservation_profile(tonal, loud)),
        "warnings": warnings,
    }


def analyze_reference_file(reference: dict[str, Any], output_dir: Path) -> dict[str, Any]:
    path = Path(reference["path"])
    if not path.exists() or path.suffix.lower() != ".wav":
        analysis = analyze_reference_audio(None, reference_name=reference["name"], role=reference["role"], path=str(path))
        analysis["warnings"] = sorted(set(analysis["warnings"] + reference.get("warnings", []) + ["reference_analysis_blocked"]))
        write_json(output_dir / "analysis_reports" / f"reference_{safe_filename(reference['name'])}_analysis.json", analysis)
        return analysis
    audio = read_wav(path, max_seconds=None)
    analysis = analyze_reference_audio(audio, reference_name=reference["name"], role=reference["role"], path=str(path))
    write_json(output_dir / "analysis_reports" / f"reference_{safe_filename(reference['name'])}_analysis.json", analysis)
    return analysis


def analyze_current_mix(current_mix_path: Path | None, output_dir: Path, project_name: str) -> dict[str, Any]:
    if current_mix_path and current_mix_path.exists() and current_mix_path.suffix.lower() == ".wav":
        audio = read_wav(current_mix_path, max_seconds=None)
        analysis = analyze_reference_audio(audio, reference_name=project_name, role="current_mix", path=str(current_mix_path))
    else:
        analysis = analyze_reference_audio(None, reference_name=project_name, role="current_mix", path=str(current_mix_path or ""))
        analysis["warnings"] = sorted(set(analysis["warnings"] + ["current_mix_missing_target_profile_only"]))
    write_json(output_dir / "analysis_reports" / "current_mix_reference_features.json", analysis)
    return analysis


def analyze_manifest_references(manifest: dict[str, Any], output_dir: Path, current_mix_path: Path | None = None) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    analyses = [analyze_reference_file(ref, output_dir) for ref in manifest.get("references", [])]
    current = analyze_current_mix(current_mix_path, output_dir, manifest.get("project_name", "project"))
    return analyses, current


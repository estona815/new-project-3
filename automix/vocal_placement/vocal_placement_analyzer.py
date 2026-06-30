from __future__ import annotations

import statistics
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from automix.analyze_ai_pitch_source import (
    AudioData,
    baked_reverb_score,
    clamp,
    dynamic_features,
    goertzel_power,
    mean,
    read_wav,
    rms,
    safe_db,
    safe_filename,
    spectral_features,
    stereo_features,
    window_starts,
    write_json,
    write_wav,
)
from automix.vocal_recovery.vocal_recovery_analyzer import phase_correlation


BANDS = {
    "120_350": [120.0, 180.0, 250.0, 350.0],
    "350_800": [350.0, 500.0, 650.0, 800.0],
    "800_2k": [800.0, 1200.0, 1600.0, 2000.0],
    "2k_5k": [2500.0, 3500.0, 4500.0, 5000.0],
    "5k_10k": [5500.0, 7000.0, 9000.0, 10000.0],
    "8k_14k": [8000.0, 10000.0, 12000.0, 14000.0],
}


def now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _band_power(samples: list[float], sample_rate: int, freqs: list[float], max_windows: int = 96) -> float:
    values = []
    for start in window_starts(len(samples), 1024, max_windows):
        segment = samples[start : start + 1024]
        if len(segment) < 64:
            continue
        values.append(mean([goertzel_power(segment, sample_rate, freq) for freq in freqs]))
    return mean(values)


def band_powers(audio: AudioData | None) -> dict[str, float]:
    if audio is None:
        return {key: 0.0 for key in BANDS}
    powers = {key: _band_power(audio.mono, audio.sample_rate, freqs) for key, freqs in BANDS.items()}
    total = sum(powers.values()) + 1.0e-12
    return {key: clamp(value / total * 4.0) for key, value in powers.items()}


def vocal_presence_profile(vocal: AudioData | None) -> dict[str, float]:
    if vocal is None:
        return {
            "vocal_loudness_lufs": -99.0,
            "vocal_peak_dbfs": -99.0,
            "vocal_crest_factor": 0.0,
            "vocal_dynamic_range_proxy": 0.0,
            "vocal_presence_1k_4k": 0.0,
            "vocal_air_8k_14k": 0.0,
            "vocal_body_120_350": 0.0,
            "vocal_sibilance_5k_10k": 0.0,
            "vocal_harshness_2k5_6k": 0.0,
            "vocal_stability_score": 0.0,
        }
    dyn = dynamic_features(vocal.mono)
    bands = band_powers(vocal)
    peak = dyn.get("peak", 0.0)
    crest = dyn.get("crest_factor_db", 0.0)
    return {
        "vocal_loudness_lufs": round(safe_db(dyn.get("rms", 0.0)) - 3.0, 6),
        "vocal_peak_dbfs": round(safe_db(peak), 6),
        "vocal_crest_factor": round(crest, 6),
        "vocal_dynamic_range_proxy": round(clamp(crest / 18.0), 6),
        "vocal_presence_1k_4k": round(clamp((bands["800_2k"] + bands["2k_5k"]) * 0.5), 6),
        "vocal_air_8k_14k": round(bands["8k_14k"], 6),
        "vocal_body_120_350": round(bands["120_350"], 6),
        "vocal_sibilance_5k_10k": round(bands["5k_10k"], 6),
        "vocal_harshness_2k5_6k": round(bands["2k_5k"], 6),
        "vocal_stability_score": round(clamp(1.0 - dyn.get("compression_limited_score", 0.0) * 0.45), 6),
    }


def masking_profile(vocal: AudioData | None, instrumental: AudioData | None, role_context: dict[str, Any] | None = None) -> dict[str, float]:
    role_context = role_context or {}
    vocal_bands = band_powers(vocal)
    inst_bands = band_powers(instrumental)

    def mask_score(key: str) -> float:
        if instrumental is None:
            return float(role_context.get(f"masking_{key}", 0.0))
        return clamp(inst_bands[key] / max(vocal_bands[key] + inst_bands[key], 1.0e-9) * 1.25)

    low = mask_score("120_350")
    low_mid = mask_score("350_800")
    mid = mask_score("800_2k")
    presence = mask_score("2k_5k")
    sibilance = mask_score("5k_10k")
    return {
        "masking_120_350": round(low, 6),
        "masking_350_800": round(low_mid, 6),
        "masking_800_2k": round(mid, 6),
        "masking_2k_5k": round(presence, 6),
        "masking_5k_10k": round(sibilance, 6),
        "instrumental_competes_with_vocal": round(clamp((low_mid + mid + presence) / 3.0), 6),
        "snare_hihat_competes_with_sibilance": round(clamp(sibilance * 0.85 + presence * 0.15), 6),
        "guitar_synth_competes_with_presence": round(clamp(presence * 0.75 + mid * 0.25), 6),
        "piano_competes_with_vocal_body": round(clamp(low * 0.55 + low_mid * 0.45), 6),
    }


def spatial_profile(vocal: AudioData | None, instrumental: AudioData | None) -> dict[str, float]:
    vocal_stereo = stereo_features(vocal) if vocal is not None else {"stereo_width_score": 0.0, "side_energy_ratio": 0.0, "phase_instability_score": 0.0}
    inst_stereo = stereo_features(instrumental) if instrumental is not None else {"stereo_width_score": 0.0, "side_energy_ratio": 0.0, "phase_instability_score": 0.0}
    vocal_corr = phase_correlation(vocal) if vocal is not None else 1.0
    inst_corr = phase_correlation(instrumental) if instrumental is not None else 1.0
    inst_mid_density = 0.0
    inst_side_density = 0.0
    if instrumental is not None:
        inst_mid_density = clamp(rms(instrumental.mid) / max(rms(instrumental.mono), 1.0e-9))
        inst_side_density = clamp(rms(instrumental.side) / max(rms(instrumental.mono), 1.0e-9))
    return {
        "vocal_center_stability": round(clamp(vocal_corr * 0.5 + 0.5 - vocal_stereo.get("phase_instability_score", 0.0) * 0.35), 6),
        "vocal_side_leakage": round(vocal_stereo.get("side_energy_ratio", 0.0), 6),
        "instrumental_mid_density": round(inst_mid_density, 6),
        "instrumental_side_density": round(inst_side_density, 6),
        "mono_compatibility_risk": round(clamp((1.0 - min(vocal_corr, inst_corr)) * 0.55 + inst_stereo.get("phase_instability_score", 0.0) * 0.45), 6),
        "stereo_width_change_risk": round(clamp(vocal_stereo.get("stereo_width_score", 0.0) * 0.30 + inst_stereo.get("stereo_width_score", 0.0) * 0.40), 6),
    }


def send_profile(vocal: AudioData | None, send_audio: AudioData | None = None, source_report: dict[str, Any] | None = None) -> dict[str, Any]:
    source_report = source_report or {}
    if send_audio is not None:
        spectral = spectral_features(send_audio.mono, send_audio.sample_rate)
        baked = baked_reverb_score(send_audio.mono, send_audio.side, spectral)
        tail_masking = clamp(baked * 0.70 + stereo_features(send_audio).get("side_energy_ratio", 0.0) * 0.50)
    else:
        baked = float(source_report.get("baked_reverb_score", 0.0))
        tail_masking = clamp(baked * 0.80)
    delay_like = clamp(tail_masking * 0.45)
    risk = "high" if tail_masking > 0.65 else "medium" if tail_masking > 0.35 else "low"
    return {
        "existing_reverb_likelihood": round(clamp(baked), 6),
        "existing_delay_likelihood": round(delay_like, 6),
        "tail_masking_score": round(tail_masking, 6),
        "send_needed": False,
        "send_risk": risk,
    }


def placement_risk(masking: dict[str, float], spatial: dict[str, float], sends: dict[str, Any], source_report: dict[str, Any]) -> str:
    if source_report.get("classification") == "full_mix" or source_report.get("full_mix_likelihood", 0.0) > 0.65:
        return "unsafe"
    maximum = max(max(masking.values()) if masking else 0.0, spatial.get("mono_compatibility_risk", 0.0), sends.get("tail_masking_score", 0.0))
    if maximum > 0.72:
        return "high"
    if maximum > 0.42:
        return "medium"
    return "low"


def recommended_mode(masking: dict[str, float], spatial: dict[str, float], sends: dict[str, Any], risk: str) -> str:
    if risk == "unsafe":
        return "stem_required"
    if sends.get("tail_masking_score", 0.0) > 0.55:
        return "send_cleanup"
    if spatial.get("mono_compatibility_risk", 0.0) > 0.55 or spatial.get("instrumental_mid_density", 0.0) > 0.70:
        return "ms_center_cleanup"
    if masking.get("masking_2k_5k", 0.0) > 0.45 or masking.get("instrumental_competes_with_vocal", 0.0) > 0.45:
        return "dynamic_space_creation"
    return "skip_or_minimal"


def analyze_vocal_placement(
    vocal_audio: AudioData | None,
    instrumental_audio: AudioData | None = None,
    *,
    track_name: str,
    track_guid: str = "",
    role: str = "lead_vocal",
    source_report: dict[str, Any] | None = None,
    recovery_status: str = "not_evaluated",
    pitch_status: str = "not_evaluated",
    send_audio: AudioData | None = None,
    role_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    source_report = source_report or {"classification": "unknown", "confidence": 0.0}
    presence = vocal_presence_profile(vocal_audio)
    masking = masking_profile(vocal_audio, instrumental_audio, role_context)
    spatial = spatial_profile(vocal_audio, instrumental_audio)
    sends = send_profile(vocal_audio, send_audio, source_report)
    risk = placement_risk(masking, spatial, sends, source_report)
    warnings: list[str] = []
    if source_report.get("classification") == "full_mix":
        warnings.append("full mix source is unsafe for vocal-forward placement automation")
    if recovery_status in {"failed_recovery", "missing_renders", "manual_cleanup_required"}:
        warnings.append("recovery is not accepted; avoid exposing artifacts with placement")
    if presence["vocal_harshness_2k5_6k"] > 0.55 or source_report.get("ai_artifact_score", 0.0) > 0.60:
        warnings.append("avoid high boosts; vocal artifact or harshness risk is elevated")
    if spatial["mono_compatibility_risk"] > 0.55:
        warnings.append("avoid widening; mono or phase risk is elevated")
    return {
        "schema": "automix-vocal-placement-analysis-v1",
        "scan_date_utc": now_utc(),
        "track_name": track_name,
        "track_guid": track_guid,
        "role": role,
        "source_classification": source_report.get("classification", "unknown"),
        "source_classification_confidence": source_report.get("confidence", 0.0),
        "recovery_status": recovery_status,
        "pitch_status": pitch_status,
        "vocal_presence_profile": presence,
        "masking_profile": masking,
        "spatial_profile": spatial,
        "send_profile": sends,
        "placement_risk": risk,
        "recommended_placement_mode": recommended_mode(masking, spatial, sends, risk),
        "warnings": warnings,
    }


def missing_placement_eval_metrics(track_name: str, available_paths: dict[str, str | None] | None = None) -> dict[str, Any]:
    paths = available_paths or {}
    return {
        "schema": "automix-vocal-placement-eval-v1",
        "track_name": track_name,
        "renders_created": {
            "original_mix": bool(paths.get("original_mix")),
            "placement_draft": bool(paths.get("placement_draft")),
            "loudness_matched": False,
            "difference": False,
        },
        "improvement_scores": {
            "vocal_audibility_delta": 0.0,
            "vocal_to_instrumental_balance_delta": 0.0,
            "presence_masking_reduction": 0.0,
            "low_mid_masking_reduction": 0.0,
            "sibilance_conflict_reduction": 0.0,
            "lead_vocal_center_stability_delta": 0.0,
        },
        "damage_scores": {
            "beat_impact_loss": 0.0,
            "low_end_loss_db": 0.0,
            "snare_impact_loss": 0.0,
            "instrumental_hollowing_score": 0.0,
            "vocal_harshness_increase": 0.0,
            "vocal_thinness_increase": 0.0,
            "stereo_width_shift": 0.0,
            "phase_correlation_worsening": 0.0,
            "reverb_tail_pumping_score": 0.0,
        },
        "evaluation_passed": False,
        "recommended_action": "manual_review_required",
        "warnings": ["missing placement A/B renders"],
    }


def evaluate_vocal_placement_ab(original_mix_path: Path, placement_draft_path: Path, output_dir: Path, track_name: str) -> dict[str, Any]:
    if not original_mix_path.exists() or not placement_draft_path.exists():
        metrics = missing_placement_eval_metrics(
            track_name,
            {
                "original_mix": str(original_mix_path) if original_mix_path.exists() else None,
                "placement_draft": str(placement_draft_path) if placement_draft_path.exists() else None,
            },
        )
        write_json(output_dir / "eval_reports" / f"{safe_filename(track_name)}_vocal_placement_eval_metrics.json", metrics)
        return metrics

    original = read_wav(original_mix_path)
    draft = read_wav(placement_draft_path)
    count = min(len(original.frames), len(draft.frames))
    if count <= 0:
        metrics = missing_placement_eval_metrics(track_name)
        write_json(output_dir / "eval_reports" / f"{safe_filename(track_name)}_vocal_placement_eval_metrics.json", metrics)
        return metrics

    original_rms = rms(original.mono[:count])
    draft_rms = rms(draft.mono[:count])
    match_gain = min(max(original_rms / max(draft_rms, 1.0e-9), 0.25), 4.0)
    matched_frames = [[clamp(value * match_gain, -1.0, 1.0) for value in draft.frames[i][: original.channels]] for i in range(count)]
    matched_path = output_dir / "eval_reports" / f"{safe_filename(track_name)}_vocal_placement_loudness_matched.wav"
    write_wav(matched_path, original, matched_frames)
    diff_frames = [[original.frames[i][ch] - matched_frames[i][ch] for ch in range(min(original.channels, draft.channels))] for i in range(count)]
    diff_path = output_dir / "eval_reports" / f"{safe_filename(track_name)}_vocal_placement_difference.wav"
    write_wav(diff_path, original, diff_frames)

    original_bands = band_powers(original)
    draft_bands = band_powers(draft)
    low_end_loss_db = safe_db(draft_bands["120_350"] + 1.0e-9) - safe_db(original_bands["120_350"] + 1.0e-9)
    presence_delta = draft_bands["2k_5k"] - original_bands["2k_5k"]
    sibilance_delta = original_bands["5k_10k"] - draft_bands["5k_10k"]
    stereo_shift = abs(stereo_features(draft)["stereo_width_score"] - stereo_features(original)["stereo_width_score"])
    phase_worse = max(0.0, phase_correlation(original) - phase_correlation(draft))
    beat_impact_loss = max(0.0, dynamic_features(original.mono)["transient_density_score"] - dynamic_features(draft.mono)["transient_density_score"])
    hollowing = clamp(max(0.0, -low_end_loss_db) / 4.0 + max(0.0, original_bands["350_800"] - draft_bands["350_800"]) * 0.5)
    harshness_increase = max(0.0, draft_bands["2k_5k"] - original_bands["2k_5k"])

    improvement = {
        "vocal_audibility_delta": round(max(0.0, presence_delta), 6),
        "vocal_to_instrumental_balance_delta": round(max(0.0, presence_delta - max(0.0, -low_end_loss_db) * 0.1), 6),
        "presence_masking_reduction": round(max(0.0, original_bands["2k_5k"] - draft_bands["2k_5k"]), 6),
        "low_mid_masking_reduction": round(max(0.0, original_bands["350_800"] - draft_bands["350_800"]), 6),
        "sibilance_conflict_reduction": round(max(0.0, sibilance_delta), 6),
        "lead_vocal_center_stability_delta": round(max(0.0, phase_correlation(draft) - phase_correlation(original)), 6),
    }
    damage = {
        "beat_impact_loss": round(beat_impact_loss, 6),
        "low_end_loss_db": round(low_end_loss_db, 6),
        "snare_impact_loss": round(max(0.0, dynamic_features(original.mono)["transient_density_score"] - dynamic_features(draft.mono)["transient_density_score"]) * 0.75, 6),
        "instrumental_hollowing_score": round(hollowing, 6),
        "vocal_harshness_increase": round(harshness_increase, 6),
        "vocal_thinness_increase": round(max(0.0, draft_bands["8k_14k"] - original_bands["8k_14k"] - max(0.0, draft_bands["120_350"] - original_bands["120_350"])), 6),
        "stereo_width_shift": round(stereo_shift, 6),
        "phase_correlation_worsening": round(phase_worse, 6),
        "reverb_tail_pumping_score": 0.0,
    }
    warnings = []
    if beat_impact_loss > 0.25:
        warnings.append("beat_impact_loss_reject")
    if low_end_loss_db < -1.5:
        warnings.append("low_end_loss_reject")
    if harshness_increase > 0.20:
        warnings.append("vocal_harshness_increase_reject")
    if stereo_shift > 0.25 or phase_worse > 0.20:
        warnings.append("stereo_or_phase_shift_reject")
    if hollowing > 0.30:
        warnings.append("instrumental_hollowing_reject")

    evaluation_passed = not warnings and sum(improvement.values()) > 0.05
    metrics = {
        "schema": "automix-vocal-placement-eval-v1",
        "track_name": track_name,
        "renders_created": {
            "original_mix": original_mix_path.exists(),
            "placement_draft": placement_draft_path.exists(),
            "loudness_matched": matched_path.exists(),
            "difference": diff_path.exists(),
        },
        "original_mix_path": str(original_mix_path),
        "placement_draft_path": str(placement_draft_path),
        "loudness_matched_path": str(matched_path),
        "difference_path": str(diff_path),
        "improvement_scores": improvement,
        "damage_scores": damage,
        "evaluation_passed": evaluation_passed,
        "recommended_action": "accept_light_placement" if evaluation_passed else "manual_review_required",
        "warnings": warnings,
    }
    write_json(output_dir / "eval_reports" / f"{safe_filename(track_name)}_vocal_placement_eval_metrics.json", metrics)
    return metrics


def write_vocal_placement_analysis(path: Path, analysis: dict[str, Any]) -> None:
    write_json(path, analysis)

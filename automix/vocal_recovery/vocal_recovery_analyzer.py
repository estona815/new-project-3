from __future__ import annotations

import json
import math
import statistics
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from automix.analyze_ai_pitch_source import (
    AudioData,
    analyze_source,
    baked_reverb_score,
    band_proxy,
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


def now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _band_windows(samples: list[float], sample_rate: int, freqs: list[float], window_size: int = 1024, max_windows: int = 96) -> list[float]:
    values = []
    for start in window_starts(len(samples), window_size, max_windows):
        segment = samples[start : start + window_size]
        if len(segment) < 64:
            continue
        values.append(mean([goertzel_power(segment, sample_rate, freq) for freq in freqs]))
    return values


def _ratio(values: list[float], total: float) -> float:
    return clamp(mean(values) / max(total, 1.0e-12) * 6.0)


def _instability(values: list[float]) -> float:
    if len(values) < 3:
        return 0.0
    avg = mean(values)
    return clamp(statistics.pstdev(values) / max(avg, 1.0e-9) / 2.0)


def _spike_score(groups: list[list[float]]) -> float:
    means = [mean(group) for group in groups if group]
    if len(means) < 2:
        return 0.0
    med = statistics.median(means) + 1.0e-12
    return clamp(max(means) / med / 5.0)


def phase_correlation(audio: AudioData) -> float:
    if audio.channels < 2:
        return 1.0
    left = [frame[0] for frame in audio.frames]
    right = [frame[1] for frame in audio.frames]
    left_rms = rms(left)
    right_rms = rms(right)
    if left_rms <= 1.0e-9 or right_rms <= 1.0e-9:
        return 1.0
    corr = sum(l * r for l, r in zip(left, right)) / max(1.0e-9, len(left) * left_rms * right_rms)
    return max(-1.0, min(1.0, corr))


def side_noise_score(audio: AudioData, dyn: dict[str, float]) -> float:
    if audio.channels < 2:
        return 0.0
    side = audio.side
    mono = audio.mono
    side_rms = rms(side)
    mono_rms = rms(mono)
    quiet_side = []
    quiet_mid = []
    for start in window_starts(len(mono), 2048, 80):
        mono_segment = mono[start : start + 2048]
        side_segment = side[start : start + 2048]
        if rms(mono_segment) < dyn.get("rms", 0.0) * 0.45:
            quiet_side.append(rms(side_segment))
            quiet_mid.append(rms(mono_segment))
    quiet_ratio = mean(quiet_side) / max(mean(quiet_mid) + mean(quiet_side), 1.0e-9) if quiet_side else 0.0
    return clamp(0.55 * side_rms / max(mono_rms + side_rms, 1.0e-9) * 2.0 + 0.45 * quiet_ratio * 2.0)


def analyze_artifacts(audio: AudioData, source_report: dict[str, Any]) -> dict[str, float]:
    mono = audio.mono
    sample_rate = audio.sample_rate
    dyn = dynamic_features(mono)
    spectral = spectral_features(mono, sample_rate)
    stereo = stereo_features(audio)
    baked = baked_reverb_score(mono, audio.side, spectral)
    total = sum(
        mean(_band_windows(mono, sample_rate, freqs))
        for freqs in ([160.0, 250.0, 350.0], [800.0, 1100.0, 1450.0], [2500.0, 3500.0, 5000.0], [6500.0, 8500.0], [11000.0, 14000.0])
    ) + 1.0e-12

    low_mid = _band_windows(mono, sample_rate, [160.0, 250.0, 350.0, 500.0])
    nasal = _band_windows(mono, sample_rate, [750.0, 1000.0, 1300.0, 1500.0])
    harsh_low = _band_windows(mono, sample_rate, [2500.0, 3300.0])
    harsh_high = _band_windows(mono, sample_rate, [4200.0, 5500.0, 6200.0])
    sibilance = _band_windows(mono, sample_rate, [5500.0, 7000.0, 9000.0])
    air = _band_windows(mono, sample_rate, [10000.0, 12000.0, 14500.0])
    body = _band_windows(mono, sample_rate, [120.0, 180.0, 250.0, 350.0])
    presence = _band_windows(mono, sample_rate, [1000.0, 1800.0, 2600.0, 3600.0])

    side_score = side_noise_score(audio, dyn)
    corr = phase_correlation(audio)
    source_sep = float(source_report.get("source_separated_likelihood", 0.0))
    baked_score = float(source_report.get("baked_reverb_score", baked))
    compression = float(source_report.get("compression_limited_score", dyn["compression_limited_score"]))

    metallic_harshness = clamp(
        0.36 * _ratio(harsh_low + harsh_high, total)
        + 0.28 * _spike_score([harsh_low, harsh_high, nasal, sibilance])
        + 0.20 * spectral.get("metallic_chirp_score", 0.0)
        + 0.16 * _instability(harsh_low + harsh_high)
    )
    high_fizz = clamp(0.48 * _ratio(air, total) + 0.30 * _instability(air) + 0.22 * spectral.get("metallic_chirp_score", 0.0))
    codec_birdies = clamp(0.42 * spectral.get("metallic_chirp_score", 0.0) + 0.38 * _instability(air) + 0.20 * _instability(sibilance))
    watery_phase = clamp(
        0.34 * stereo.get("phase_instability_score", 0.0)
        + 0.24 * source_sep
        + 0.18 * side_score
        + 0.16 * clamp((0.72 - corr) / 1.2)
        + 0.08 * baked_score
    )
    formant_wobble = clamp(0.52 * _instability(presence) + 0.24 * _instability(nasal) + 0.24 * watery_phase)
    sibilance_warble = clamp(0.50 * _instability(sibilance) + 0.28 * _ratio(sibilance, total) + 0.22 * watery_phase)
    reverb_smear = clamp(0.46 * baked_score + 0.24 * side_score + 0.18 * source_sep + 0.12 * compression)
    low_mid_mud = clamp(0.68 * _ratio(low_mid, total) + 0.32 * spectral.get("body_ratio", 0.0) * 2.0)
    nasal_resonance = clamp(0.58 * _ratio(nasal, total) + 0.42 * _spike_score([nasal, low_mid, harsh_low]))
    transient_smear = clamp(0.45 * compression + 0.26 * baked_score + 0.18 * source_sep + 0.11 * (1.0 - dyn.get("transient_density_score", 0.0)))
    body_ratio = mean(body) / max(total, 1.0e-12)
    vocal_thinness = clamp(0.50 * clamp((_ratio(air + sibilance, total) - body_ratio * 8.0) / 1.4) + 0.30 * high_fizz + 0.20 * clamp(0.22 - body_ratio * 5.0))

    return {
        "metallic_harshness_score": round(metallic_harshness, 6),
        "watery_phase_score": round(watery_phase, 6),
        "codec_birdies_score": round(codec_birdies, 6),
        "formant_wobble_score": round(formant_wobble, 6),
        "sibilance_warble_score": round(sibilance_warble, 6),
        "reverb_smear_score": round(reverb_smear, 6),
        "side_noise_score": round(side_score, 6),
        "high_band_fizz_score": round(high_fizz, 6),
        "low_mid_mud_score": round(low_mid_mud, 6),
        "nasal_resonance_score": round(nasal_resonance, 6),
        "transient_smear_score": round(transient_smear, 6),
        "vocal_thinness_score": round(vocal_thinness, 6),
    }


def processing_profile(audio: AudioData, source_report: dict[str, Any]) -> dict[str, float]:
    mono = audio.mono
    dyn = dynamic_features(mono)
    spectral = spectral_features(mono, audio.sample_rate)
    stereo = stereo_features(audio)
    corr = phase_correlation(audio)
    peak_ceiling = dyn.get("peak_ceiling_ratio", 0.0)
    compression = float(source_report.get("compression_limited_score", dyn["compression_limited_score"]))
    baked = float(source_report.get("baked_reverb_score", baked_reverb_score(mono, audio.side, spectral)))
    return {
        "compression_limited_score": round(compression, 6),
        "crest_factor": round(dyn.get("crest_factor_db", 0.0), 6),
        "dynamic_range_proxy": round(clamp(dyn.get("crest_factor_db", 0.0) / 18.0), 6),
        "peak_ceiling_likelihood": round(clamp(peak_ceiling * 80.0), 6),
        "baked_reverb_score": round(baked, 6),
        "stereo_width_score": round(stereo.get("stereo_width_score", 0.0), 6),
        "mono_compatibility_risk": round(clamp((1.0 - corr) * 0.60 + stereo.get("side_energy_ratio", 0.0) * 0.80), 6),
        "phase_correlation": round(corr, 6),
    }


def fallback_artifact_profile(source_report: dict[str, Any]) -> dict[str, float]:
    ai = float(source_report.get("ai_artifact_score", 0.0))
    source_sep = float(source_report.get("source_separated_likelihood", 0.0))
    baked = float(source_report.get("baked_reverb_score", 0.0))
    compression = float(source_report.get("compression_limited_score", 0.0))
    already_mixed = float(source_report.get("already_mixed_score", 0.0))
    return {
        "metallic_harshness_score": round(clamp(ai * 0.75 + already_mixed * 0.20), 6),
        "watery_phase_score": round(clamp(source_sep * 0.80 + baked * 0.15), 6),
        "codec_birdies_score": round(clamp(ai * 0.65), 6),
        "formant_wobble_score": round(clamp(ai * 0.40 + source_sep * 0.35), 6),
        "sibilance_warble_score": round(clamp(ai * 0.35 + compression * 0.20), 6),
        "reverb_smear_score": round(clamp(baked * 0.85 + source_sep * 0.20), 6),
        "side_noise_score": round(clamp(source_sep * 0.45 + baked * 0.20), 6),
        "high_band_fizz_score": round(clamp(ai * 0.70 + compression * 0.15), 6),
        "low_mid_mud_score": round(clamp(already_mixed * 0.35 + baked * 0.15), 6),
        "nasal_resonance_score": round(clamp(ai * 0.30), 6),
        "transient_smear_score": round(clamp(compression * 0.55 + baked * 0.25 + source_sep * 0.20), 6),
        "vocal_thinness_score": round(clamp(ai * 0.25 + source_sep * 0.25), 6),
    }


def fallback_processing_profile(source_report: dict[str, Any]) -> dict[str, float]:
    return {
        "compression_limited_score": round(float(source_report.get("compression_limited_score", 0.0)), 6),
        "crest_factor": 0.0,
        "dynamic_range_proxy": 0.0,
        "peak_ceiling_likelihood": 0.0,
        "baked_reverb_score": round(float(source_report.get("baked_reverb_score", 0.0)), 6),
        "stereo_width_score": 0.0,
        "mono_compatibility_risk": round(clamp(float(source_report.get("source_separated_likelihood", 0.0)) * 0.50), 6),
        "phase_correlation": 1.0,
    }


def recovery_risk(source_report: dict[str, Any], artifact: dict[str, float], processing: dict[str, float]) -> str:
    if source_report.get("classification") == "full_mix" or source_report.get("full_mix_likelihood", 0.0) > 0.65:
        return "unsafe"
    max_artifact = max(artifact.values()) if artifact else 0.0
    if max_artifact > 0.75 or processing.get("mono_compatibility_risk", 0.0) > 0.75:
        return "high"
    if max_artifact > 0.45 or source_report.get("already_mixed_score", 0.0) > 0.70:
        return "medium"
    return "low"


def recommended_mode(source_report: dict[str, Any], artifact: dict[str, float], risk: str) -> str:
    if risk == "unsafe":
        return "stem_required"
    if source_report.get("source_separated_likelihood", 0.0) > 0.70 and artifact.get("watery_phase_score", 0.0) > 0.45:
        return "source_separated_rescue"
    if artifact.get("vocal_thinness_score", 0.0) > 0.58:
        return "thin_vocal_body_preserve"
    if max(artifact.values()) < 0.25:
        return "skip_or_minimal_cleanup"
    return "conservative_ai_vocal_cleanup"


def analyze_vocal_recovery(
    audio: AudioData | None,
    track_name: str,
    track_guid: str = "",
    source_report: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if source_report is None:
        if audio is None:
            source_report = {"classification": "unknown", "confidence": 0.0}
        else:
            source_report, _pitch = analyze_source(audio, track_name)

    if audio is not None:
        artifact = analyze_artifacts(audio, source_report)
        processing = processing_profile(audio, source_report)
    else:
        artifact = fallback_artifact_profile(source_report)
        processing = fallback_processing_profile(source_report)

    risk = recovery_risk(source_report, artifact, processing)
    warnings: list[str] = []
    if source_report.get("full_mix_likelihood", 0.0) > 0.65:
        warnings.append("full mix unsafe for vocal recovery")
    if processing.get("compression_limited_score", 0.0) > 0.70:
        warnings.append("avoid compression; source appears already limited")
    if processing.get("baked_reverb_score", 0.0) > 0.60:
        warnings.append("avoid added reverb and protect tails")
    if processing.get("mono_compatibility_risk", 0.0) > 0.55:
        warnings.append("avoid widening; phase/mono risk is elevated")
    if artifact.get("vocal_thinness_score", 0.0) > 0.55:
        warnings.append("avoid over-cleaning; preserve vocal body")

    return {
        "schema": "automix-vocal-recovery-analysis-v1",
        "scan_date_utc": now_utc(),
        "track_name": track_name,
        "track_guid": track_guid,
        "source_classification": source_report.get("classification", "unknown"),
        "source_classification_confidence": source_report.get("confidence", 0.0),
        "already_mixed_score": source_report.get("already_mixed_score", 0.0),
        "already_tuned_score": source_report.get("already_tuned_score", 0.0),
        "source_separated_likelihood": source_report.get("source_separated_likelihood", 0.0),
        "full_mix_likelihood": source_report.get("full_mix_likelihood", 0.0),
        "analysis_basis": "audio" if audio is not None else "source_report_only",
        "artifact_profile": artifact,
        "processing_profile": processing,
        "recovery_risk": risk,
        "recommended_recovery_mode": recommended_mode(source_report, artifact, risk),
        "warnings": warnings,
    }


def analyze_vocal_recovery_file(input_path: Path, output_dir: Path, track_name: str, track_guid: str = "") -> dict[str, Any]:
    audio = read_wav(input_path)
    analysis = analyze_vocal_recovery(audio, track_name, track_guid)
    write_json(output_dir / "analysis_reports" / f"{safe_filename(track_name)}_vocal_recovery_analysis.json", analysis)
    return analysis


def missing_recovery_eval_metrics(track_name: str, available_paths: dict[str, str | None] | None = None) -> dict[str, Any]:
    paths = available_paths or {}
    return {
        "schema": "automix-vocal-recovery-eval-v1",
        "track_name": track_name,
        "renders_created": {
            "original": bool(paths.get("original")),
            "recovered": bool(paths.get("recovered")),
            "loudness_matched": False,
            "difference": False,
        },
        "artifact_reduction_scores": {
            "metallic_harshness_delta": 0.0,
            "high_fizz_delta": 0.0,
            "codec_birdies_delta": 0.0,
            "watery_phase_delta": 0.0,
            "sibilance_warble_delta": 0.0,
            "reverb_smear_delta": 0.0,
            "side_noise_delta": 0.0,
        },
        "damage_scores": {
            "clarity_loss_db": 0.0,
            "air_loss_db": 0.0,
            "body_loss_db": 0.0,
            "transient_loss": 0.0,
            "formant_drift_score": 0.0,
            "phase_shift_score": 0.0,
            "stereo_width_change": 0.0,
            "vocal_thinness_increase": 0.0,
            "difference_source_energy": 0.0,
        },
        "evaluation_passed": False,
        "recommended_action": "manual_review_required",
        "warnings": ["missing recovery A/B renders"],
    }


def evaluate_vocal_recovery_ab(original_path: Path, recovered_path: Path, output_dir: Path, track_name: str) -> dict[str, Any]:
    if not original_path.exists() or not recovered_path.exists():
        metrics = missing_recovery_eval_metrics(
            track_name,
            {"original": str(original_path) if original_path.exists() else None, "recovered": str(recovered_path) if recovered_path.exists() else None},
        )
        write_json(output_dir / "eval_reports" / f"{safe_filename(track_name)}_vocal_recovery_eval_metrics.json", metrics)
        return metrics

    original = read_wav(original_path)
    recovered = read_wav(recovered_path)
    count = min(len(original.frames), len(recovered.frames))
    if count <= 0:
        metrics = missing_recovery_eval_metrics(track_name, {"original": str(original_path), "recovered": str(recovered_path)})
        write_json(output_dir / "eval_reports" / f"{safe_filename(track_name)}_vocal_recovery_eval_metrics.json", metrics)
        return metrics

    original_rms = rms(original.mono[:count])
    recovered_rms = rms(recovered.mono[:count])
    match_gain = min(max(original_rms / max(recovered_rms, 1.0e-9), 0.25), 4.0)
    matched_frames = [[clamp(value * match_gain, -1.0, 1.0) for value in recovered.frames[i][: original.channels]] for i in range(count)]
    matched_path = output_dir / "eval_reports" / f"{safe_filename(track_name)}_vocal_recovery_loudness_matched.wav"
    write_wav(matched_path, original, matched_frames)
    diff_frames = [[original.frames[i][ch] - matched_frames[i][ch] for ch in range(min(original.channels, recovered.channels))] for i in range(count)]
    diff_path = output_dir / "eval_reports" / f"{safe_filename(track_name)}_vocal_recovery_difference.wav"
    write_wav(diff_path, original, diff_frames)

    orig_source, _ = analyze_source(original, track_name)
    rec_source, _ = analyze_source(recovered, track_name)
    orig_analysis = analyze_vocal_recovery(original, track_name, source_report=orig_source)
    rec_analysis = analyze_vocal_recovery(recovered, track_name, source_report=rec_source)
    orig_art = orig_analysis["artifact_profile"]
    rec_art = rec_analysis["artifact_profile"]
    orig_bands = band_proxy(original)
    rec_bands = band_proxy(recovered)
    diff_mono = [sum(frame) / len(frame) for frame in diff_frames] if diff_frames else []

    clarity_loss_db = safe_db(rec_bands["clarity_4k_8k"] + 1.0e-9) - safe_db(orig_bands["clarity_4k_8k"] + 1.0e-9)
    air_loss_db = safe_db(rec_bands["air_8k_plus"] + 1.0e-9) - safe_db(orig_bands["air_8k_plus"] + 1.0e-9)
    body_loss_db = safe_db(rec_bands["formant_1k_4k"] + 1.0e-9) - safe_db(orig_bands["formant_1k_4k"] + 1.0e-9)
    transient_loss = max(0.0, dynamic_features(original.mono)["transient_density_score"] - dynamic_features(recovered.mono)["transient_density_score"])
    formant_drift = clamp(abs(rec_bands["formant_1k_4k"] - orig_bands["formant_1k_4k"]) * 8.0)
    phase_shift = clamp(abs(phase_correlation(original) - phase_correlation(recovered)))
    stereo_width_change = abs(stereo_features(recovered)["stereo_width_score"] - stereo_features(original)["stereo_width_score"])
    thinness_increase = max(0.0, rec_art["vocal_thinness_score"] - orig_art["vocal_thinness_score"])
    difference_source_energy = rms(diff_mono) / max(rms(original.mono), 1.0e-9)

    artifact_reduction = {
        "metallic_harshness_delta": round(orig_art["metallic_harshness_score"] - rec_art["metallic_harshness_score"], 6),
        "high_fizz_delta": round(orig_art["high_band_fizz_score"] - rec_art["high_band_fizz_score"], 6),
        "codec_birdies_delta": round(orig_art["codec_birdies_score"] - rec_art["codec_birdies_score"], 6),
        "watery_phase_delta": round(orig_art["watery_phase_score"] - rec_art["watery_phase_score"], 6),
        "sibilance_warble_delta": round(orig_art["sibilance_warble_score"] - rec_art["sibilance_warble_score"], 6),
        "reverb_smear_delta": round(orig_art["reverb_smear_score"] - rec_art["reverb_smear_score"], 6),
        "side_noise_delta": round(orig_art["side_noise_score"] - rec_art["side_noise_score"], 6),
    }
    damage = {
        "clarity_loss_db": round(clarity_loss_db, 6),
        "air_loss_db": round(air_loss_db, 6),
        "body_loss_db": round(body_loss_db, 6),
        "transient_loss": round(transient_loss, 6),
        "formant_drift_score": round(formant_drift, 6),
        "phase_shift_score": round(phase_shift, 6),
        "stereo_width_change": round(stereo_width_change, 6),
        "vocal_thinness_increase": round(thinness_increase, 6),
        "difference_source_energy": round(difference_source_energy, 6),
    }

    warnings = []
    if clarity_loss_db < -1.5:
        warnings.append("clarity_loss_reject")
    if air_loss_db < -2.0:
        warnings.append("air_loss_reject")
    if body_loss_db < -1.5:
        warnings.append("body_loss_reject")
    if formant_drift > 0.35:
        warnings.append("formant_drift_reject")
    if phase_shift > 0.25 or stereo_width_change > 0.25:
        warnings.append("phase_or_stereo_shift_reject")
    if thinness_increase > 0.25:
        warnings.append("vocal_thinness_increase_reject")
    if difference_source_energy > 0.35:
        warnings.append("difference_contains_too_much_vocal_body")
    reduction_sum = sum(max(0.0, value) for value in artifact_reduction.values())
    evaluation_passed = not warnings and reduction_sum > 0.05

    metrics = {
        "schema": "automix-vocal-recovery-eval-v1",
        "track_name": track_name,
        "renders_created": {
            "original": original_path.exists(),
            "recovered": recovered_path.exists(),
            "loudness_matched": matched_path.exists(),
            "difference": diff_path.exists(),
        },
        "original_path": str(original_path),
        "recovered_path": str(recovered_path),
        "loudness_matched_path": str(matched_path),
        "difference_path": str(diff_path),
        "artifact_reduction_scores": artifact_reduction,
        "damage_scores": damage,
        "evaluation_passed": evaluation_passed,
        "recommended_action": "accept_light_recovery" if evaluation_passed else "manual_review_required",
        "warnings": warnings,
    }
    write_json(output_dir / "eval_reports" / f"{safe_filename(track_name)}_vocal_recovery_eval_metrics.json", metrics)
    return metrics

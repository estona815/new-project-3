from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from automix.analyze_ai_pitch_source import (
    AudioData,
    clamp,
    dynamic_features,
    goertzel_power,
    mean,
    percentile,
    read_wav,
    rms,
    safe_db,
    safe_filename,
    stereo_features,
    window_rms_values,
    window_starts,
    write_json,
    write_wav,
)
from automix.vocal_recovery.vocal_recovery_analyzer import phase_correlation


BANDS = {
    "sub_20_60": [30.0, 45.0, 60.0],
    "bass_60_120": [70.0, 90.0, 120.0],
    "low_mid_120_350": [150.0, 220.0, 350.0],
    "mid_350_1k": [450.0, 700.0, 1000.0],
    "presence_1k_4k": [1200.0, 2000.0, 3200.0, 4000.0],
    "harshness_2k5_6k": [2500.0, 3500.0, 5000.0, 6000.0],
    "sibilance_5k_10k": [5500.0, 7000.0, 9000.0, 10000.0],
    "air_10k_16k": [10000.0, 12000.0, 14000.0, 16000.0],
    "ultra_high_16k_plus": [17000.0, 18000.0],
}


def now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _band_power(samples: list[float], sample_rate: int, freqs: list[float]) -> float:
    values = []
    for start in window_starts(len(samples), 2048, 96):
        segment = samples[start : start + 2048]
        if len(segment) < 64:
            continue
        values.append(mean([goertzel_power(segment, sample_rate, freq) for freq in freqs]))
    return mean(values)


def tonal_profile(audio: AudioData | None) -> dict[str, float]:
    if audio is None:
        return {key: 0.0 for key in BANDS}
    powers = {key: _band_power(audio.mono, audio.sample_rate, freqs) for key, freqs in BANDS.items()}
    total = sum(powers.values()) + 1.0e-12
    return {key: round(clamp(value / total * 5.0), 6) for key, value in powers.items()}


def loudness_profile(audio: AudioData | None) -> dict[str, float]:
    if audio is None:
        return {
            "integrated_lufs": 0.0,
            "short_term_lufs": 0.0,
            "momentary_lufs_peak": 0.0,
            "true_peak_dbTP": 0.0,
            "sample_peak_dbFS": 0.0,
            "lra": 0.0,
            "crest_factor": 0.0,
            "dynamic_range_proxy": 0.0,
            "peak_density_score": 0.0,
            "limiter_pressure_risk": 0.0,
        }
    dyn = dynamic_features(audio.mono)
    windows = window_rms_values(audio.mono, 4096, 120)
    window_db = [safe_db(value) - 3.0 for value in windows if value > 1.0e-8]
    lra = max(0.0, percentile(window_db, 0.95) - percentile(window_db, 0.10)) if window_db else 0.0
    peak_db = safe_db(dyn["peak"])
    peak_density = dyn.get("peak_ceiling_ratio", 0.0)
    crest = dyn.get("crest_factor_db", 0.0)
    limiter_risk = clamp(0.42 * dyn.get("compression_limited_score", 0.0) + 0.35 * clamp((8.0 - crest) / 8.0) + 0.23 * clamp(peak_density * 80.0))
    return {
        "integrated_lufs": round(safe_db(dyn["rms"]) - 3.0, 6),
        "short_term_lufs": round(mean(window_db[-8:]) if window_db else 0.0, 6),
        "momentary_lufs_peak": round(max(window_db) if window_db else 0.0, 6),
        "true_peak_dbTP": round(peak_db, 6),
        "sample_peak_dbFS": round(peak_db, 6),
        "lra": round(lra, 6),
        "crest_factor": round(crest, 6),
        "dynamic_range_proxy": round(clamp(crest / 18.0), 6),
        "peak_density_score": round(clamp(peak_density * 80.0), 6),
        "limiter_pressure_risk": round(limiter_risk, 6),
    }


def stereo_profile(audio: AudioData | None) -> dict[str, float]:
    if audio is None:
        return {
            "stereo_width_score": 0.0,
            "mid_energy_score": 0.0,
            "side_energy_score": 0.0,
            "mono_compatibility_risk": 0.0,
            "phase_correlation": 1.0,
            "low_end_stereo_risk": 0.0,
        }
    stereo = stereo_features(audio)
    corr = phase_correlation(audio)
    mid = rms(audio.mid)
    side = rms(audio.side)
    low_side = _band_power(audio.side, audio.sample_rate, [45.0, 70.0, 100.0]) if audio.channels >= 2 else 0.0
    low_mid = _band_power(audio.mid, audio.sample_rate, [45.0, 70.0, 100.0]) if audio.channels >= 2 else 0.0
    low_side_risk = clamp(low_side / max(low_mid + low_side, 1.0e-12) * 2.0)
    return {
        "stereo_width_score": round(stereo.get("stereo_width_score", 0.0), 6),
        "mid_energy_score": round(clamp(mid / max(mid + side, 1.0e-9) * 1.5), 6),
        "side_energy_score": round(clamp(side / max(mid + side, 1.0e-9) * 2.0), 6),
        "mono_compatibility_risk": round(clamp((1.0 - corr) * 0.55 + stereo.get("phase_instability_score", 0.0) * 0.45), 6),
        "phase_correlation": round(corr, 6),
        "low_end_stereo_risk": round(low_side_risk, 6),
    }


def ai_artifact_risk_profile(tonal: dict[str, float], loudness: dict[str, float], stereo: dict[str, float]) -> dict[str, float]:
    harsh = tonal["harshness_2k5_6k"]
    sib = tonal["sibilance_5k_10k"]
    air = tonal["air_10k_16k"] + tonal["ultra_high_16k_plus"]
    limiter = loudness["limiter_pressure_risk"]
    return {
        "metallic_harshness_risk": round(clamp(harsh * 0.70 + limiter * 0.20), 6),
        "high_fizz_risk": round(clamp(air * 0.55 + sib * 0.25 + limiter * 0.20), 6),
        "codec_birdies_risk": round(clamp(air * 0.45 + tonal["ultra_high_16k_plus"] * 0.45), 6),
        "sibilance_splatter_risk": round(clamp(sib * 0.65 + limiter * 0.35), 6),
        "phasey_width_risk": round(clamp(stereo["mono_compatibility_risk"] * 0.75 + stereo["stereo_width_score"] * 0.20), 6),
        "vocal_thinness_risk": round(clamp((air + sib) * 0.35 + max(0.0, 0.35 - tonal["low_mid_120_350"]) * 0.50), 6),
        "reverb_tail_pump_risk": round(clamp(limiter * 0.45 + stereo["side_energy_score"] * 0.25), 6),
    }


def vocal_preservation_profile(tonal: dict[str, float], loudness: dict[str, float]) -> dict[str, float]:
    body = tonal["low_mid_120_350"] + tonal["mid_350_1k"] * 0.35
    clarity = clamp(tonal["presence_1k_4k"] - tonal["harshness_2k5_6k"] * 0.25)
    harsh = tonal["harshness_2k5_6k"]
    sib = tonal["sibilance_5k_10k"]
    beat_balance = clamp((tonal["sub_20_60"] + tonal["bass_60_120"]) * 0.35 + tonal["presence_1k_4k"] * 0.30)
    forwardness = clamp(clarity * 0.50 + body * 0.25 - loudness["limiter_pressure_risk"] * 0.15)
    return {
        "vocal_forwardness_score": round(forwardness, 6),
        "vocal_clarity_score": round(clarity, 6),
        "vocal_harshness_score": round(harsh, 6),
        "vocal_sibilance_score": round(sib, 6),
        "vocal_body_score": round(clamp(body), 6),
        "vocal_to_beat_balance": round(beat_balance, 6),
        "vocal_masking_risk": round(clamp(max(0.0, 0.45 - clarity) + harsh * 0.25), 6),
    }


def translation_profile(tonal: dict[str, float], artifact: dict[str, float], stereo: dict[str, float], vocal: dict[str, float]) -> dict[str, float]:
    low = tonal["sub_20_60"] + tonal["bass_60_120"]
    return {
        "small_speaker_risk": round(clamp(max(0.0, 0.45 - vocal["vocal_clarity_score"]) + tonal["low_mid_120_350"] * 0.15), 6),
        "earbud_harshness_risk": round(clamp(artifact["sibilance_splatter_risk"] * 0.55 + artifact["high_fizz_risk"] * 0.45), 6),
        "club_low_end_risk": round(clamp(abs(low - 0.55) * 1.6 + stereo["low_end_stereo_risk"] * 0.35), 6),
        "phone_speaker_vocal_loss_risk": round(clamp(vocal["vocal_masking_risk"] * 0.65 + max(0.0, 0.40 - vocal["vocal_forwardness_score"])), 6),
    }


def premaster_risk(loudness: dict[str, float], artifact: dict[str, float], stereo: dict[str, float], translation: dict[str, float]) -> str:
    maximum = max(
        loudness["limiter_pressure_risk"],
        max(artifact.values()) if artifact else 0.0,
        stereo["mono_compatibility_risk"],
        max(translation.values()) if translation else 0.0,
    )
    if maximum > 0.78:
        return "high"
    if maximum > 0.48:
        return "medium"
    return "low"


def recommended_mode(loudness: dict[str, float], artifact: dict[str, float], vocal: dict[str, float], risk: str) -> str:
    if risk == "high" or max(artifact.values()) > 0.65:
        return "safety_only_premaster"
    if loudness["limiter_pressure_risk"] > 0.68 or vocal["vocal_forwardness_score"] < 0.20:
        return "safety_only_premaster"
    return "safe_streaming_premaster"


def analyze_premaster_safety(
    audio: AudioData | None,
    *,
    project_name: str,
    source_mix_path: str = "",
    input_stage: str = "vocal_placement_draft",
) -> dict[str, Any]:
    loud = loudness_profile(audio)
    tonal = tonal_profile(audio)
    stereo = stereo_profile(audio)
    artifact = ai_artifact_risk_profile(tonal, loud, stereo)
    vocal = vocal_preservation_profile(tonal, loud)
    translation = translation_profile(tonal, artifact, stereo, vocal)
    risk = premaster_risk(loud, artifact, stereo, translation)
    warnings: list[str] = []
    if loud["limiter_pressure_risk"] > 0.65:
        warnings.append("limiter pressure risk is already high")
    if artifact["sibilance_splatter_risk"] > 0.55:
        warnings.append("avoid aggressive limiting or clipping around sibilance")
    if stereo["mono_compatibility_risk"] > 0.55:
        warnings.append("avoid master widening; mono compatibility risk is elevated")
    if vocal["vocal_forwardness_score"] < 0.20:
        warnings.append("vocal forwardness is weak; prefer mix placement revision over master boost")
    return {
        "schema": "automix-premaster-safety-analysis-v1",
        "scan_date_utc": now_utc(),
        "project_name": project_name,
        "source_mix_path": source_mix_path,
        "input_stage": input_stage,
        "loudness_profile": loud,
        "tonal_profile": tonal,
        "ai_artifact_risk_profile": artifact,
        "vocal_preservation_profile": vocal,
        "stereo_profile": stereo,
        "translation_profile": translation,
        "premaster_risk": risk,
        "recommended_premaster_mode": recommended_mode(loud, artifact, vocal, risk),
        "warnings": warnings,
    }


def analyze_premaster_file(source_mix: Path, output_dir: Path, project_name: str, input_stage: str = "vocal_placement_draft") -> dict[str, Any]:
    audio = read_wav(source_mix)
    analysis = analyze_premaster_safety(audio, project_name=project_name, source_mix_path=str(source_mix), input_stage=input_stage)
    write_json(output_dir / "analysis_reports" / "project_premaster_safety_analysis.json", analysis)
    return analysis


def missing_premaster_eval_metrics(available_paths: dict[str, str | None] | None = None) -> dict[str, Any]:
    paths = available_paths or {}
    return {
        "schema": "automix-premaster-eval-v1",
        "renders_created": {
            "original_mix": bool(paths.get("original_mix")),
            "premaster_draft": bool(paths.get("premaster_draft")),
            "loudness_matched": False,
            "difference": False,
        },
        "loudness_results": {
            "original_lufs": 0.0,
            "premaster_lufs": 0.0,
            "original_true_peak_dbTP": 0.0,
            "premaster_true_peak_dbTP": 0.0,
            "original_lra": 0.0,
            "premaster_lra": 0.0,
            "gain_increase_db": 0.0,
        },
        "improvement_scores": {
            "overall_loudness_control": 0.0,
            "low_end_translation_delta": 0.0,
            "vocal_forwardness_delta": 0.0,
            "vocal_clarity_delta": 0.0,
            "mix_glue_delta": 0.0,
            "peak_control_delta": 0.0,
        },
        "damage_scores": {
            "vocal_harshness_increase": 0.0,
            "sibilance_splatter_increase": 0.0,
            "metallic_artifact_increase": 0.0,
            "high_fizz_increase": 0.0,
            "vocal_thinness_increase": 0.0,
            "vocal_forwardness_loss": 0.0,
            "beat_impact_loss": 0.0,
            "low_end_loss_db": 0.0,
            "transient_loss": 0.0,
            "stereo_width_shift": 0.0,
            "phase_correlation_worsening": 0.0,
            "limiter_pumping_score": 0.0,
            "reverb_tail_pumping_score": 0.0,
        },
        "evaluation_passed": False,
        "recommended_action": "manual_review_required",
        "warnings": ["missing premaster A/B renders"],
    }


def evaluate_premaster_ab(original_mix_path: Path, premaster_draft_path: Path, output_dir: Path) -> dict[str, Any]:
    if not original_mix_path.exists() or not premaster_draft_path.exists():
        metrics = missing_premaster_eval_metrics(
            {
                "original_mix": str(original_mix_path) if original_mix_path.exists() else None,
                "premaster_draft": str(premaster_draft_path) if premaster_draft_path.exists() else None,
            }
        )
        write_json(output_dir / "eval_reports" / "project_premaster_eval_metrics.json", metrics)
        return metrics

    original = read_wav(original_mix_path)
    draft = read_wav(premaster_draft_path)
    count = min(len(original.frames), len(draft.frames))
    if count <= 0:
        metrics = missing_premaster_eval_metrics()
        write_json(output_dir / "eval_reports" / "project_premaster_eval_metrics.json", metrics)
        return metrics

    def as_channels(frame: list[float], channels: int) -> list[float]:
        if len(frame) >= channels:
            return frame[:channels]
        if not frame:
            return [0.0 for _ in range(channels)]
        return frame + [frame[-1] for _ in range(channels - len(frame))]

    orig_rms = rms(original.mono[:count])
    draft_rms = rms(draft.mono[:count])
    match_gain = min(max(orig_rms / max(draft_rms, 1.0e-9), 0.25), 4.0)
    matched_frames = [
        [clamp(value * match_gain, -1.0, 1.0) for value in as_channels(draft.frames[i], original.channels)]
        for i in range(count)
    ]
    matched_path = output_dir / "eval_reports" / "project_premaster_loudness_matched.wav"
    write_wav(matched_path, original, matched_frames)
    diff_frames = [
        [as_channels(original.frames[i], original.channels)[ch] - matched_frames[i][ch] for ch in range(original.channels)]
        for i in range(count)
    ]
    diff_path = output_dir / "eval_reports" / "project_premaster_difference.wav"
    write_wav(diff_path, original, diff_frames)

    original_analysis = analyze_premaster_safety(original, project_name="original", source_mix_path=str(original_mix_path), input_stage="original_mix")
    draft_analysis = analyze_premaster_safety(draft, project_name="premaster", source_mix_path=str(premaster_draft_path), input_stage="premaster_draft")
    o_loud = original_analysis["loudness_profile"]
    d_loud = draft_analysis["loudness_profile"]
    o_art = original_analysis["ai_artifact_risk_profile"]
    d_art = draft_analysis["ai_artifact_risk_profile"]
    o_vocal = original_analysis["vocal_preservation_profile"]
    d_vocal = draft_analysis["vocal_preservation_profile"]
    o_stereo = original_analysis["stereo_profile"]
    d_stereo = draft_analysis["stereo_profile"]
    o_tonal = original_analysis["tonal_profile"]
    d_tonal = draft_analysis["tonal_profile"]
    gain_increase = d_loud["integrated_lufs"] - o_loud["integrated_lufs"]
    low_loss_db = safe_db(d_tonal["bass_60_120"] + 1.0e-9) - safe_db(o_tonal["bass_60_120"] + 1.0e-9)
    transient_loss = max(0.0, dynamic_features(original.mono)["transient_density_score"] - dynamic_features(draft.mono)["transient_density_score"])
    damage = {
        "vocal_harshness_increase": round(max(0.0, d_vocal["vocal_harshness_score"] - o_vocal["vocal_harshness_score"]), 6),
        "sibilance_splatter_increase": round(max(0.0, d_art["sibilance_splatter_risk"] - o_art["sibilance_splatter_risk"]), 6),
        "metallic_artifact_increase": round(max(0.0, d_art["metallic_harshness_risk"] - o_art["metallic_harshness_risk"]), 6),
        "high_fizz_increase": round(max(0.0, d_art["high_fizz_risk"] - o_art["high_fizz_risk"]), 6),
        "vocal_thinness_increase": round(max(0.0, d_art["vocal_thinness_risk"] - o_art["vocal_thinness_risk"]), 6),
        "vocal_forwardness_loss": round(max(0.0, o_vocal["vocal_forwardness_score"] - d_vocal["vocal_forwardness_score"]), 6),
        "beat_impact_loss": round(transient_loss, 6),
        "low_end_loss_db": round(low_loss_db, 6),
        "transient_loss": round(transient_loss, 6),
        "stereo_width_shift": round(abs(d_stereo["stereo_width_score"] - o_stereo["stereo_width_score"]), 6),
        "phase_correlation_worsening": round(max(0.0, o_stereo["phase_correlation"] - d_stereo["phase_correlation"]), 6),
        "limiter_pumping_score": round(max(0.0, d_loud["limiter_pressure_risk"] - o_loud["limiter_pressure_risk"]), 6),
        "reverb_tail_pumping_score": round(max(0.0, d_art["reverb_tail_pump_risk"] - o_art["reverb_tail_pump_risk"]), 6),
    }
    improvement = {
        "overall_loudness_control": round(clamp(gain_increase / 3.0), 6),
        "low_end_translation_delta": round(max(0.0, d_tonal["bass_60_120"] - o_tonal["bass_60_120"]), 6),
        "vocal_forwardness_delta": round(max(0.0, d_vocal["vocal_forwardness_score"] - o_vocal["vocal_forwardness_score"]), 6),
        "vocal_clarity_delta": round(max(0.0, d_vocal["vocal_clarity_score"] - o_vocal["vocal_clarity_score"]), 6),
        "mix_glue_delta": round(max(0.0, o_loud["crest_factor"] - d_loud["crest_factor"]) * 0.05, 6),
        "peak_control_delta": round(max(0.0, o_loud["true_peak_dbTP"] - d_loud["true_peak_dbTP"]), 6),
    }
    warnings = []
    if damage["vocal_harshness_increase"] > 0.12:
        warnings.append("vocal_harshness_increase_reject")
    if damage["sibilance_splatter_increase"] > 0.12:
        warnings.append("sibilance_splatter_reject")
    if damage["metallic_artifact_increase"] > 0.12 or damage["high_fizz_increase"] > 0.12:
        warnings.append("ai_artifact_increase_reject")
    if damage["beat_impact_loss"] > 0.22 or damage["low_end_loss_db"] < -1.5:
        warnings.append("beat_or_low_end_loss_reject")
    if damage["vocal_forwardness_loss"] > 0.12:
        warnings.append("vocal_forwardness_loss_reject")
    if damage["stereo_width_shift"] > 0.25 or damage["phase_correlation_worsening"] > 0.20:
        warnings.append("stereo_or_phase_shift_reject")
    if d_loud["true_peak_dbTP"] > -0.8:
        warnings.append("true_peak_manual_review_required")
    evaluation_passed = not warnings and sum(improvement.values()) > 0.05
    metrics = {
        "schema": "automix-premaster-eval-v1",
        "renders_created": {
            "original_mix": original_mix_path.exists(),
            "premaster_draft": premaster_draft_path.exists(),
            "loudness_matched": matched_path.exists(),
            "difference": diff_path.exists(),
        },
        "original_mix_path": str(original_mix_path),
        "premaster_draft_path": str(premaster_draft_path),
        "loudness_matched_path": str(matched_path),
        "difference_path": str(diff_path),
        "loudness_results": {
            "original_lufs": o_loud["integrated_lufs"],
            "premaster_lufs": d_loud["integrated_lufs"],
            "original_true_peak_dbTP": o_loud["true_peak_dbTP"],
            "premaster_true_peak_dbTP": d_loud["true_peak_dbTP"],
            "original_lra": o_loud["lra"],
            "premaster_lra": d_loud["lra"],
            "gain_increase_db": round(gain_increase, 6),
        },
        "improvement_scores": improvement,
        "damage_scores": damage,
        "evaluation_passed": evaluation_passed,
        "recommended_action": "accept_light_premaster" if evaluation_passed else "manual_review_required",
        "warnings": warnings,
    }
    write_json(output_dir / "eval_reports" / "project_premaster_eval_metrics.json", metrics)
    return metrics


def build_translation_check(analysis: dict[str, Any], eval_metrics: dict[str, Any] | None = None) -> dict[str, Any]:
    translation = analysis["translation_profile"]
    stereo = analysis["stereo_profile"]
    artifact = analysis["ai_artifact_risk_profile"]
    warnings = []
    if stereo["mono_compatibility_risk"] > 0.55:
        warnings.append("mono_fold_down_risk")
    if translation["phone_speaker_vocal_loss_risk"] > 0.55:
        warnings.append("phone_speaker_vocal_loss_recommend_mix_revision")
    if translation["earbud_harshness_risk"] > 0.55:
        warnings.append("earbud_harshness_reduce_limiting_or_high_end")
    if translation["club_low_end_risk"] > 0.65:
        warnings.append("low_end_translation_manual_review")
    if artifact["sibilance_splatter_risk"] > 0.55:
        warnings.append("vocal_sibilance_warning")
    if eval_metrics and eval_metrics.get("damage_scores", {}).get("limiter_pumping_score", 0.0) > 0.20:
        warnings.append("limiter_pumping_warning")
    return {
        "schema": "automix-project-translation-check-v1",
        "mono_fold_down_risk": stereo["mono_compatibility_risk"],
        "small_speaker_vocal_audibility_proxy": clamp(1.0 - translation["small_speaker_risk"]),
        "earbud_harshness_proxy": translation["earbud_harshness_risk"],
        "low_end_translation_proxy": clamp(1.0 - translation["club_low_end_risk"]),
        "phase_correlation_warning": stereo["phase_correlation"] < 0.35,
        "vocal_sibilance_warning": artifact["sibilance_splatter_risk"] > 0.55,
        "limiter_pumping_warning": "limiter_pumping_warning" in warnings,
        "warnings": warnings,
        "recommended_action": "manual_review_required" if warnings else "translation_check_passed",
    }

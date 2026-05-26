from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import numpy as np

from ai_randomness_detector import detect_ai_randomness
from arrangement_coherence import analyze_arrangement_coherence
from audio_analysis import read_wav_float
from audio_metrics import clipping_count, filter_audio, harshness_score, peak_db, rms_db, side_mid_db, spectral_band_profile, to_stereo
from musical_identity_analyzer import analyze_musical_identity
from paths import PROJECT_ROOT
from tempo_key_estimation import estimate_bpm
from vocal_texture_detection import detect_vocal_like_textures


def _channels_to_audio(channels: list[list[float]]) -> np.ndarray:
    if not channels:
        return np.zeros((0, 2), dtype=np.float32)
    length = min(len(channel) for channel in channels)
    if length <= 0:
        return np.zeros((0, 2), dtype=np.float32)
    return np.column_stack([np.asarray(channel[:length], dtype=np.float32) for channel in channels]).astype(np.float32)


def _mono(channels: list[list[float]]) -> np.ndarray:
    audio = _channels_to_audio(channels)
    if audio.size == 0:
        return np.zeros(0, dtype=np.float32)
    return np.mean(audio[:, :2], axis=1, dtype=np.float32)


def _risk_label(value: float, low: float = 0.33, high: float = 0.66) -> str:
    if value >= high:
        return "high"
    if value >= low:
        return "medium"
    return "low"


def _tempo_from_audio(mono: np.ndarray, sample_rate: int, duration: float) -> dict[str, Any]:
    if sample_rate <= 0 or mono.size < sample_rate:
        return {"bpm_candidates": [], "confidence": "low", "reason": "not enough audio for onset interval tempo estimation"}
    hop = max(1, int(0.05 * sample_rate))
    frame = max(hop, int(0.10 * sample_rate))
    envelope: list[float] = []
    for start in range(0, mono.size - frame + 1, hop):
        chunk = mono[start : start + frame]
        envelope.append(float(np.mean(np.abs(np.diff(chunk))) if chunk.size > 1 else 0.0))
    if len(envelope) < 4:
        return {"bpm_candidates": [], "confidence": "low", "reason": "not enough onset envelope frames"}
    values = np.asarray(envelope, dtype=np.float32)
    threshold = float(np.percentile(values, 82))
    onset_times = [index * hop / sample_rate for index, value in enumerate(values) if value >= threshold and value > 0.0]
    raw = estimate_bpm(onset_times, duration)
    confidence = str(raw.get("confidence", "low"))
    candidates = [{"bpm": float(value), "confidence": confidence} for value in raw.get("bpm_candidates", [])]
    reason = "ambiguous onset intervals / possible half-time/double-time" if raw.get("half_double_ambiguity", True) else str(raw.get("method", "onset interval tempo estimation"))
    return {"bpm_candidates": candidates, "confidence": confidence, "reason": reason}


def _basic_metrics(metadata: dict[str, Any], audio: np.ndarray, sample_rate: int) -> dict[str, Any]:
    stereo = to_stereo(audio)
    low = filter_audio(stereo, 20.0, 150.0, sample_rate)
    return {
        "duration_seconds": round(float(metadata.get("duration_seconds", 0.0)), 3),
        "sample_rate": int(metadata.get("sample_rate", sample_rate)),
        "bit_depth": int(metadata.get("bit_depth", 0)),
        "channels": int(metadata.get("channels", stereo.shape[1] if stereo.ndim == 2 else 1)),
        "peak_dbfs": round(peak_db(stereo), 2),
        "rms_dbfs": round(rms_db(stereo), 2),
        "clipping_count": clipping_count(stereo),
        "side_mid_db": side_mid_db(stereo),
        "low_side_mid_db": side_mid_db(low),
    }


def _vocal_texture(channels: list[list[float]], sample_rate: int, lead_analysis: dict[str, Any]) -> dict[str, Any]:
    candidates = detect_vocal_like_textures(channels, sample_rate)
    candidate_ratio = min(1.0, len(candidates) / 8.0)
    pitch_stability = float(lead_analysis.get("pitch_stability_proxy", 0.0))
    repeated_contour = float(lead_analysis.get("repeated_contour", 0.0))
    return {
        "weird_vocal_texture_risk": _risk_label(candidate_ratio, 0.25, 0.62),
        "vocal_chop_as_unwanted_lead": bool(len(candidates) >= 3 and int(lead_analysis.get("lead_melody_presence", 1)) <= 2),
        "pitch_instability": _risk_label(1.0 - pitch_stability, 0.38, 0.70),
        "phrasing_confusion": _risk_label(1.0 - repeated_contour, 0.42, 0.74),
        "candidate_regions": candidates,
    }


def _mix(audio: np.ndarray, sample_rate: int, basic: dict[str, Any], arrangement: dict[str, Any]) -> dict[str, Any]:
    bands = spectral_band_profile(audio, sample_rate)
    low_energy = max(float(bands.get("sub_20_60", -99.0)), float(bands.get("bass_60_150", -99.0)))
    if low_energy > -8.0:
        low_balance = "excessive"
    elif low_energy < -24.0:
        low_balance = "weak"
    else:
        low_balance = "controlled"
    width = "too_wide" if float(basic["side_mid_db"]) > -8.0 or float(basic["low_side_mid_db"]) > -16.0 else "narrow" if float(basic["side_mid_db"]) < -32.0 else "balanced"
    harsh = harshness_score(audio, sample_rate)
    crest = float(basic["peak_dbfs"]) - float(basic["rms_dbfs"])
    overcompression_seed = 1.0 if crest < 7.0 else 0.6 if crest < 9.0 else 0.2
    if arrangement.get("energy_curve", 3) <= 2:
        overcompression_seed += 0.15
    return {
        "low_end_balance": low_balance,
        "stereo_width": width,
        "harshness_risk": "high" if harsh > -8.0 else "medium" if harsh > -15.0 else "low",
        "overcompressed_risk": _risk_label(min(1.0, overcompression_seed), 0.45, 0.75),
    }


def _rescue_decision(identity: dict[str, Any], arrangement: dict[str, Any], vocal: dict[str, Any]) -> dict[str, bool]:
    lead_required = int(identity["lead_melody_presence"]) <= 2
    hook_required = int(identity["hook_identity"]) <= 2
    arrangement_required = float(arrangement["score"]) <= 2.4
    mix_only_not_enough = bool(lead_required and hook_required and arrangement_required)
    vocal_required = vocal["weird_vocal_texture_risk"] in {"medium", "high"} or bool(vocal["vocal_chop_as_unwanted_lead"])
    return {
        "mix_only_not_enough": mix_only_not_enough,
        "lead_melody_required": lead_required,
        "hook_identity_required": hook_required,
        "arrangement_rebuild_required": arrangement_required,
        "vocal_texture_cleanup_required": vocal_required,
        "sample_motif_rebuild_required": bool(hook_required or int(identity["motif_repetition_quality"]) <= 2),
        "manual_logic_recommended": bool(mix_only_not_enough or arrangement_required or hook_required),
    }


def _required_routes(rescue: dict[str, bool]) -> list[str]:
    routes: list[str] = []
    if rescue["arrangement_rebuild_required"]:
        routes.append("ARRANGEMENT_REBUILD_REQUIRED")
    if rescue["lead_melody_required"]:
        routes.append("LEAD_MELODY_REQUIRED")
    if rescue["hook_identity_required"]:
        routes.append("HOOK_IDENTITY_REQUIRED")
    if rescue["vocal_texture_cleanup_required"]:
        routes.append("VOCAL_TEXTURE_CLEANUP_REQUIRED")
    if rescue["sample_motif_rebuild_required"]:
        routes.append("SAMPLE_MOTIF_REBUILD_REQUIRED")
    return routes


def build_bad_song_diagnosis(path: str | Path, *, mode: str = "full_song_stereo") -> dict[str, Any]:
    source = Path(path).expanduser()
    metadata, channels = read_wav_float(source)
    audio = _channels_to_audio(channels)
    mono = _mono(channels)
    sample_rate = int(metadata["sample_rate"])
    duration = float(metadata["duration_seconds"])
    basic = _basic_metrics(metadata, audio, sample_rate)
    tempo = _tempo_from_audio(mono, sample_rate, duration)
    identity = analyze_musical_identity(mono, sample_rate)
    arrangement = analyze_arrangement_coherence(mono, sample_rate)
    randomness = detect_ai_randomness(mono, sample_rate)
    lead_analysis = identity.get("lead_melody_analysis", {})
    vocal = _vocal_texture(channels, sample_rate, lead_analysis if isinstance(lead_analysis, dict) else {})
    mix = _mix(audio, sample_rate, basic, arrangement)
    rescue = _rescue_decision(identity, arrangement, vocal)
    routes = _required_routes(rescue)
    limitations = [
        "Stereo-only analysis cannot fully isolate stems.",
        "Lead melody detection is heuristic.",
        "A new lead/hook may require synthesis, MIDI, stems, or manual Logic production.",
    ]
    if rescue["mix_only_not_enough"]:
        limitations.append("Mix/master alone is insufficient because musical identity and arrangement structure are weak.")
    diagnosis = {
        "schema_version": "bad_song_diagnosis.v1",
        "status": "RESCUE_PLAN_READY",
        "complete": False,
        "input": {"path": str(source), "mode": mode if mode in {"full_song_stereo", "stems"} else "unknown"},
        "duration_seconds": basic["duration_seconds"],
        "MIX_ONLY_NOT_ENOUGH": rescue["mix_only_not_enough"],
        "decision": "ARRANGEMENT_REBUILD_REQUIRED" if rescue["mix_only_not_enough"] else "MIX_REPAIR_CAN_FOLLOW_RESCUE_PLAN",
        "required_routes": routes,
        "basic_metrics": basic,
        "tempo": tempo,
        "musical_identity": {
            "lead_melody_presence": identity["lead_melody_presence"],
            "hook_identity": identity["hook_identity"],
            "motif_repetition_quality": identity["motif_repetition_quality"],
            "call_response_quality": identity["call_response_quality"],
            "score": identity["score"],
            "diagnosis": identity["diagnosis"],
        },
        "arrangement": {
            "section_clarity": arrangement["section_clarity"],
            "energy_curve": arrangement["energy_curve"],
            "intro_strength": arrangement["intro_strength"],
            "transition_intentionality": arrangement["transition_intentionality"],
            "variation_every_4_8_bars": arrangement["variation_every_4_8_bars"],
            "score": arrangement["score"],
            "diagnosis": arrangement["diagnosis"],
        },
        "vocal_texture": vocal,
        "mix": mix,
        "rescue_decision": rescue,
        "flags": {
            "no_clear_lead_melody": rescue["lead_melody_required"],
            "no_hook_identity": rescue["hook_identity_required"],
            "no_arrangement_structure": rescue["arrangement_rebuild_required"],
            "weird_or_random_vocal_textures": rescue["vocal_texture_cleanup_required"],
            "sections_repeat_without_intention": arrangement["static_region_ratio"] > 0.45,
            "ai_glitches_transitions_dominate": randomness["randomness_risk"] in {"medium", "high"},
            "generated_audio_feel": bool(rescue["mix_only_not_enough"] or randomness["randomness_risk"] == "high"),
        },
        "scores": {
            "lead_melody_score": float(identity["lead_melody_presence"]),
            "hook_identity_score": float(identity["hook_identity"]),
            "arrangement_structure_score": float(arrangement["score"]),
            "vocal_texture_cleanliness_score": 1.0 if vocal["weird_vocal_texture_risk"] == "high" else 3.0 if vocal["weird_vocal_texture_risk"] == "medium" else 5.0,
            "sample_synth_motif_score": float(identity["motif_repetition_quality"]),
            "ai_artifact_risk_score": float(randomness["randomness_score"]),
        },
        "ai_randomness": randomness,
        "stereo_claim_guard": {
            "stem_level_remix_claimed": False,
            "vocal_removal_claimed": False,
            "kick_replacement_claimed": False,
            "drum_rewrite_claimed": False,
            "plugin_insertion_claimed": False,
            "logic_automation_success_claimed": False,
        },
        "analysis_details": {
            "lead_melody": identity.get("lead_melody_analysis", {}),
            "hook_identity": identity.get("hook_identity_analysis", {}),
            "arrangement": arrangement,
        },
        "limitations": limitations,
    }
    return diagnosis


def render_bad_song_diagnosis_markdown(diagnosis: dict[str, Any]) -> str:
    decision = diagnosis["rescue_decision"]
    identity = diagnosis["musical_identity"]
    arrangement = diagnosis["arrangement"]
    lines = [
        "# Bad Song Diagnosis",
        "",
        f"- path: {diagnosis['input']['path']}",
        f"- mode: {diagnosis['input']['mode']}",
        f"- duration: {diagnosis['basic_metrics']['duration_seconds']}s",
        f"- musical identity score: {identity['score']} ({identity['diagnosis']})",
        f"- arrangement score: {arrangement['score']} ({arrangement['diagnosis']})",
        f"- mix only not enough: {str(bool(decision['mix_only_not_enough'])).lower()}",
        "",
        "## Rescue Decision",
        *[f"- {key}: {str(bool(value)).lower()}" for key, value in decision.items()],
        "",
    ]
    if decision["mix_only_not_enough"]:
        lines.extend(
            [
                "## Producer Note",
                "Mix/master alone is insufficient. Rebuild arrangement, lead melody, hook identity, vocal texture, and sample/synth motif before final mastering.",
                "",
            ]
        )
    lines.extend(
        [
            "## Limitations",
            *[f"- {item}" for item in diagnosis.get("limitations", [])],
            "",
        ]
    )
    return "\n".join(lines)


def write_bad_song_diagnosis(
    path: str | Path,
    *,
    project_root: str | Path = PROJECT_ROOT,
    mode: str = "full_song_stereo",
) -> dict[str, Path]:
    root = Path(project_root)
    analysis_dir = root / "01_ANALYSIS"
    analysis_dir.mkdir(parents=True, exist_ok=True)
    diagnosis = build_bad_song_diagnosis(path, mode=mode)
    json_path = analysis_dir / "bad_song_diagnosis.json"
    markdown_path = analysis_dir / "bad_song_diagnosis.md"
    json_path.write_text(json.dumps(diagnosis, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    markdown_path.write_text(render_bad_song_diagnosis_markdown(diagnosis), encoding="utf-8")
    return {"json": json_path, "markdown": markdown_path}

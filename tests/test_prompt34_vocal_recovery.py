from __future__ import annotations

import json
import math
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from automix.analyze_ai_pitch_source import AudioData, write_wav
from automix.batch.batch_pitch_triage import run_batch_triage
from automix.vocal_recovery.recovery_iteration_engine import build_recovery_iteration_history
from automix.vocal_recovery.recovery_profiles import resolve_recovery_profile
from automix.vocal_recovery.vocal_recovery_analyzer import (
    analyze_vocal_recovery,
    evaluate_vocal_recovery_ab,
    missing_recovery_eval_metrics,
)
from automix.vocal_recovery.vocal_recovery_policy import build_recovery_chain_plan, evaluate_recovery_policy


def make_audio(freqs: list[float], *, seconds: float = 0.35, sr: int = 44100, stereo: bool = False, phase_flip: bool = False) -> AudioData:
    frames = []
    for i in range(int(seconds * sr)):
        t = i / sr
        value = sum(math.sin(2.0 * math.pi * freq * t) for freq in freqs) / max(1, len(freqs))
        value *= 0.35
        if stereo:
            right = -value if phase_flip else value * 0.82
            frames.append([value, right])
        else:
            frames.append([value])
    return AudioData(sample_rate=sr, channels=2 if stereo else 1, frames=frames)


def source_report(**overrides) -> dict:
    data = {
        "classification": "ai_vocal_stem",
        "confidence": 0.82,
        "already_mixed_score": 0.62,
        "already_tuned_score": 0.55,
        "source_separated_likelihood": 0.20,
        "full_mix_likelihood": 0.10,
        "baked_reverb_score": 0.25,
        "compression_limited_score": 0.30,
        "ai_artifact_score": 0.35,
    }
    data.update(overrides)
    return data


def high_conf_adapter(path: Path | None = None) -> dict:
    semantic_names = [
        "utility_gain_db",
        "low_cut_hz",
        "low_cut_slope",
        "mud_dynamic_cut_amount",
        "nasal_dynamic_cut_amount",
        "harshness_dynamic_cut_amount",
        "sibilance_control_amount",
        "high_fizz_control_amount",
        "side_noise_reduction_amount",
        "stereo_width_change",
        "output_gain_db",
    ]
    data = {
        "semantic_controls": {name: {"target_name": name, "confidence": 0.92, "writable": True} for name in semantic_names},
        "plugins": {
            "utility_gain": {"plugin": "JS utility", "adapter_confidence": 0.92},
            "cleanup_eq": {"plugin": "ReaEQ", "adapter_confidence": 0.92},
            "dynamic_eq": {"plugin": "TDR Nova", "adapter_confidence": 0.92},
            "de_esser": {"plugin": "ReaXcomp", "adapter_confidence": 0.92},
            "high_fizz_control": {"plugin": "TDR Nova", "adapter_confidence": 0.92},
            "side_cleanup": {"plugin": "JS M/S", "adapter_confidence": 0.92},
            "output_gain": {"plugin": "JS utility", "adapter_confidence": 0.92},
        },
    }
    if path:
        path.write_text(json.dumps(data), encoding="utf-8")
    return data


def test_high_hf_noise_scores_high_band_fizz() -> None:
    analysis = analyze_vocal_recovery(make_audio([220.0, 12000.0, 14500.0]), "HF Vox", source_report=source_report())
    assert analysis["artifact_profile"]["high_band_fizz_score"] > 0.30


def test_phase_instability_scores_watery_phase() -> None:
    analysis = analyze_vocal_recovery(
        make_audio([220.0, 440.0], stereo=True, phase_flip=True),
        "Phase Vox",
        source_report=source_report(source_separated_likelihood=0.72),
    )
    assert analysis["artifact_profile"]["watery_phase_score"] > 0.35
    assert analysis["processing_profile"]["mono_compatibility_risk"] > 0.50


def test_low_mid_energy_scores_mud_and_high_mid_scores_metallic() -> None:
    mud = analyze_vocal_recovery(make_audio([180.0, 250.0, 350.0]), "Mud Vox", source_report=source_report())
    metallic = analyze_vocal_recovery(make_audio([3300.0, 4200.0, 5500.0]), "Metal Vox", source_report=source_report())
    assert mud["artifact_profile"]["low_mid_mud_score"] > 0.30
    assert metallic["artifact_profile"]["metallic_harshness_score"] > 0.30


def test_policy_blocks_full_mix_and_source_report_only_source_separated_stem() -> None:
    full_mix = analyze_vocal_recovery(None, "Full Mix", source_report=source_report(classification="full_mix", full_mix_likelihood=0.90))
    source_sep = analyze_vocal_recovery(None, "Separated", source_report=source_report(classification="source_separated_vocal", source_separated_likelihood=0.78))
    assert evaluate_recovery_policy(full_mix)["recovery_action"] == "stem_required"
    assert evaluate_recovery_policy(source_sep)["recovery_action"] == "stem_required"


def test_profiles_avoid_compression_reverb_widening_and_protect_thin_body() -> None:
    analysis = analyze_vocal_recovery(
        None,
        "Thin Wet Vox",
        source_report=source_report(already_mixed_score=0.82, compression_limited_score=0.85, baked_reverb_score=0.80, source_separated_likelihood=0.65, ai_artifact_score=0.80),
    )
    analysis["artifact_profile"]["vocal_thinness_score"] = 0.70
    profile = resolve_recovery_profile("conservative_ai_vocal_cleanup_draft", analysis, {})
    assert profile["settings"]["compression_amount"] == 0.0
    assert profile["settings"].get("added_reverb_amount", 0.0) == 0.0
    assert profile["settings"]["stereo_width_change"] <= 0.0
    assert profile["settings"]["body_preserve"] >= 1.0


def test_recovery_profile_defaults_are_non_aggressive() -> None:
    conservative = resolve_recovery_profile("conservative_ai_vocal_cleanup_draft", analyze_vocal_recovery(None, "AI", source_report=source_report()), {})
    separated = resolve_recovery_profile(
        "source_separated_rescue_draft",
        analyze_vocal_recovery(None, "Sep", source_report=source_report(classification="source_separated_vocal", source_separated_likelihood=0.75)),
        {},
    )
    thin = resolve_recovery_profile("minimal_cleanup_draft", analyze_vocal_recovery(None, "Thin", source_report=source_report()), {})
    assert conservative["settings"]["compression_amount"] == 0.0
    assert separated["settings"]["saturation_amount"] == 0.0
    assert thin["settings"]["low_cut_hz"] <= 80


def test_adapter_unknown_and_low_confidence_controls_are_skipped() -> None:
    analysis = analyze_vocal_recovery(None, "AI", source_report=source_report(ai_artifact_score=0.80))
    low_adapter = {"semantic_controls": {"utility_gain_db": {"target_name": "gain", "confidence": 0.40, "writable": True}}}
    profile = resolve_recovery_profile("conservative_ai_vocal_cleanup_draft", analysis, low_adapter)
    assert "utility_gain_db" in profile["semantic_controls_skipped"]
    good = resolve_recovery_profile("minimal_cleanup_draft", analysis, high_conf_adapter())
    assert "utility_gain_db" in good["semantic_controls_to_write"]


def test_missing_or_destructive_recovery_eval_fails_closed() -> None:
    missing = missing_recovery_eval_metrics("Lead")
    assert missing["evaluation_passed"] is False
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        original = make_audio([220.0, 440.0, 9000.0], stereo=True)
        recovered = AudioData(sample_rate=original.sample_rate, channels=original.channels, frames=[[0.0, 0.0] for _ in original.frames])
        original_path = tmp_path / "original.wav"
        recovered_path = tmp_path / "recovered.wav"
        write_wav(original_path, original, original.frames)
        write_wav(recovered_path, recovered, recovered.frames)
        metrics = evaluate_vocal_recovery_ab(original_path, recovered_path, tmp_path / "automix", "Lead")
    assert metrics["evaluation_passed"] is False
    assert metrics["damage_scores"]["difference_source_energy"] > 0.35


def test_iteration_engine_reduces_processing_not_intensifies() -> None:
    initial = {"high_fizz_control_amount": 0.20, "sibilance_control_amount": 0.18, "harshness_dynamic_cut_amount": 0.22, "side_noise_reduction_amount": 0.15, "saturation_amount": 0.05, "low_cut_hz": 80}
    history = build_recovery_iteration_history(initial, [{"evaluation_passed": False, "damage_scores": {"body_loss_db": -2.0}}])
    assert history["iterations"][1]["settings"]["high_fizz_control_amount"] < initial["high_fizz_control_amount"]
    assert history["iterations"][2]["settings"]["saturation_amount"] == 0.0
    assert history["iterations"][-1]["settings"].get("bypass_recovery") is True


def test_batch_recovery_matrix_blocks_pitch_until_recovery_review() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        manifest = {
            "tracks": [
                {
                    "track_name": "Lead Vox",
                    "track_guid": "{lead}",
                    "source_classification": source_report(classification="ai_vocal_stem", already_mixed_score=0.80, ai_artifact_score=0.80),
                    "pitch_analysis": {
                        "monophonic_pitch_confidence": 0.85,
                        "key_confidence": 0.80,
                        "scale_confidence": 0.80,
                        "polyphonic_contamination_score": 0.10,
                        "already_tuned_score": 0.40,
                    },
                }
            ]
        }
        manifest_path = tmp_path / "manifest.json"
        adapter_path = tmp_path / "adapter.json"
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        high_conf_adapter(adapter_path)
        paths = run_batch_triage(
            project_path=None,
            track_manifest_path=manifest_path,
            adapter_status_path=adapter_path,
            output_dir=tmp_path / "automix",
            mode="conservative_apply_drafts",
            apply_drafts=True,
        )
        recovery_matrix = json.loads(paths["recovery_matrix"].read_text(encoding="utf-8"))
        pitch_matrix = json.loads(paths["matrix"].read_text(encoding="utf-8"))
    assert recovery_matrix["summary"]["conservative_ai_vocal_cleanup_draft"] == 1
    assert recovery_matrix["track_decisions"][0]["pitch_allowed_after_recovery"] is False
    assert pitch_matrix["track_decisions"][0]["decision"] == "needs_human_review"


def test_reaper_recovery_applicator_is_draft_only_and_disabled_by_default() -> None:
    text = (ROOT / "automix/apply_vocal_recovery_draft.lua").read_text(encoding="utf-8")
    assert "allow_draft_vocal_recovery = false" in text
    assert "_RECOVERY_DRAFT" in text
    assert "assert_original_track_unmodified_for_vocal_recovery" in text
    assert '"contains_pitch_correction": false' in text
    assert "Main_SaveProject" not in text
    assert "RenderFileSection" not in text

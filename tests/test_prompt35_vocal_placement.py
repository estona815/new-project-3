from __future__ import annotations

import json
import math
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from automix.analyze_ai_pitch_source import AudioData, write_wav
from automix.batch.batch_pitch_triage import run_batch_triage
from automix.routing.vocal_sidechain_routing import (
    assert_original_mix_unmodified_for_vocal_placement,
    build_vocal_sidechain_routing_plan,
)
from automix.vocal_placement.placement_iteration_engine import build_placement_iteration_history
from automix.vocal_placement.placement_profiles import resolve_placement_profile
from automix.vocal_placement.vocal_placement_analyzer import (
    analyze_vocal_placement,
    evaluate_vocal_placement_ab,
    missing_placement_eval_metrics,
)
from automix.vocal_placement.vocal_placement_policy import build_placement_chain_plan, evaluate_placement_policy


def make_audio(freqs: list[float], *, amp: float = 0.25, seconds: float = 0.35, sr: int = 44100, stereo: bool = False, phase_flip: bool = False) -> AudioData:
    frames = []
    for i in range(int(seconds * sr)):
        t = i / sr
        value = sum(math.sin(2.0 * math.pi * freq * t) for freq in freqs) / max(1, len(freqs))
        value *= amp
        if stereo:
            frames.append([value, -value if phase_flip else value * 0.75])
        else:
            frames.append([value])
    return AudioData(sample_rate=sr, channels=2 if stereo else 1, frames=frames)


def source_report(**overrides) -> dict:
    data = {
        "classification": "ai_vocal_stem",
        "confidence": 0.85,
        "already_mixed_score": 0.62,
        "already_tuned_score": 0.50,
        "source_separated_likelihood": 0.20,
        "full_mix_likelihood": 0.10,
        "baked_reverb_score": 0.25,
        "compression_limited_score": 0.30,
        "ai_artifact_score": 0.35,
        "placement_context": {},
    }
    data.update(overrides)
    return data


def pitch_report() -> dict:
    return {
        "monophonic_pitch_confidence": 0.85,
        "key_confidence": 0.80,
        "scale_confidence": 0.80,
        "polyphonic_contamination_score": 0.10,
        "already_tuned_score": 0.40,
    }


def high_conf_adapter(path: Path | None = None) -> dict:
    semantic_names = [
        "vocal_gain_db",
        "max_vocal_gain_db",
        "instrumental_duck_amount_db",
        "presence_duck_amount_db",
        "low_mid_duck_amount_db",
        "sibilance_conflict_duck_db",
        "duck_attack_ms",
        "duck_release_ms",
        "duck_ratio",
        "ms_mid_cleanup_amount",
        "ms_side_cleanup_amount",
        "send_duck_amount_db",
        "send_duck_release_ms",
        "output_gain_db",
    ]
    plugins = {
        "utility_gain": {"plugin": "JS utility", "adapter_confidence": 0.92},
        "sidechain_dynamic_eq": {"plugin": "ReaXcomp", "adapter_confidence": 0.92},
        "multiband_ducker": {"plugin": "ReaXcomp", "adapter_confidence": 0.92},
        "ms_eq": {"plugin": "JS M/S", "adapter_confidence": 0.92},
        "vocal_bus_trim": {"plugin": "JS utility", "adapter_confidence": 0.92},
        "backing_vocal_ducker": {"plugin": "ReaComp", "adapter_confidence": 0.92},
        "send_ducker": {"plugin": "ReaComp", "adapter_confidence": 0.92},
        "reverb_tail_ducker": {"plugin": "ReaComp", "adapter_confidence": 0.92},
        "output_gain": {"plugin": "JS utility", "adapter_confidence": 0.92},
    }
    data = {
        "mapping_confidence": 0.92,
        "semantic_controls": {name: {"target_name": name, "confidence": 0.92, "writable": True} for name in semantic_names},
        "plugins": plugins,
    }
    if path:
        path.write_text(json.dumps(data), encoding="utf-8")
    return data


def test_analyzer_detects_mid_low_sibilance_masking_and_center_crowding() -> None:
    vocal = make_audio([220.0, 1200.0, 2800.0], amp=0.18, stereo=True)
    instrumental = make_audio([220.0, 350.0, 2500.0, 7000.0], amp=0.42, stereo=True)
    analysis = analyze_vocal_placement(vocal, instrumental, track_name="Lead Vox", source_report=source_report(), role_context={})
    assert analysis["masking_profile"]["masking_2k_5k"] > 0.35
    assert analysis["masking_profile"]["masking_120_350"] > 0.35
    assert analysis["masking_profile"]["masking_5k_10k"] > 0.30
    assert analysis["spatial_profile"]["instrumental_mid_density"] > 0.50


def test_send_tail_masking_uses_existing_wet_source() -> None:
    analysis = analyze_vocal_placement(None, None, track_name="Wet Vox", source_report=source_report(baked_reverb_score=0.85))
    assert analysis["send_profile"]["tail_masking_score"] > 0.60
    assert analysis["send_profile"]["send_needed"] is False


def test_policy_full_mix_no_bus_buried_and_fragile_ai_cases() -> None:
    full_mix = analyze_vocal_placement(None, None, track_name="Full Mix", source_report=source_report(classification="full_mix", full_mix_likelihood=0.90))
    assert evaluate_placement_policy(full_mix, {"instrumental_bus": "INST"})["placement_action"] == "stem_required"
    no_bus = analyze_vocal_placement(None, None, track_name="Lead", source_report=source_report())
    assert evaluate_placement_policy(no_bus, {})["placement_action"] == "manual_mix_required"
    buried = analyze_vocal_placement(
        make_audio([1200.0], amp=0.10),
        make_audio([1200.0, 2800.0], amp=0.45),
        track_name="Lead",
        source_report=source_report(classification="mixed_vocal_stem", ai_artifact_score=0.10),
    )
    decision = evaluate_placement_policy(buried, {"instrumental_bus": "INST"})
    assert decision["placement_action"] == "dynamic_space_creation_draft"
    profile = resolve_placement_profile(decision["placement_action"], buried, {})
    assert profile["settings"]["vocal_gain_db"] <= profile["settings"]["max_vocal_gain_db"]
    harsh = analyze_vocal_placement(make_audio([3500.0, 5500.0], amp=0.42), make_audio([2500.0], amp=0.25), track_name="Harsh", source_report=source_report(ai_artifact_score=0.90))
    harsh_decision = evaluate_placement_policy(harsh, {"instrumental_bus": "INST"})
    assert "FRAGILE_AI_VOCAL_PROTECT" in harsh_decision["reason_codes"]


def test_profiles_clamp_gain_ducking_and_backing_duck() -> None:
    analysis = analyze_vocal_placement(None, None, track_name="Lead", source_report=source_report(), role="lead_vocal")
    profile = resolve_placement_profile("dynamic_space_creation_draft", analysis, high_conf_adapter())
    assert profile["settings"]["vocal_gain_db"] <= profile["settings"]["max_vocal_gain_db"]
    assert profile["settings"]["presence_duck_amount_db"] >= -2.0
    fragile = resolve_placement_profile("dynamic_space_creation_draft", {**analysis, "source_classification": "ai_vocal_stem", "warnings": ["artifact risk"]}, {})
    assert fragile["settings"]["max_vocal_gain_db"] <= 0.5
    backing = analyze_vocal_placement(None, None, track_name="BGV", source_report=source_report(), role="backing_vocal")
    backing_profile = resolve_placement_profile("sidechain_dynamic_eq_draft", backing, {})
    assert backing_profile["settings"]["backing_duck_amount_db"] < 0.0


def test_routing_plan_is_dry_run_and_original_guard_detects_changes() -> None:
    plan = build_vocal_sidechain_routing_plan(
        track_name="Lead",
        lead_vocal="Lead",
        instrumental_bus="INST BUS",
        backing_vocals=["BGV"],
        send_tracks=["REV"],
        action="dynamic_space_creation_draft",
    )
    assert plan["dry_run"] is True
    assert plan["preserve_existing_sends"] is True
    assert plan["created_sends"]
    before = {"lead_vocal_fx_count": 1, "instrumental_bus_fx_count": 2, "routing_count": 3, "master_fx_count": 0, "media_checksum": "a", "pitch_plugin_count": 0}
    after = dict(before)
    assert_original_mix_unmodified_for_vocal_placement(before, after)
    after["routing_count"] = 4
    try:
        assert_original_mix_unmodified_for_vocal_placement(before, after)
    except AssertionError:
        pass
    else:
        raise AssertionError("routing mutation was not detected")


def test_eval_missing_render_and_destructive_draft_fail_closed() -> None:
    missing = missing_placement_eval_metrics("Lead")
    assert missing["evaluation_passed"] is False
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        original = make_audio([80.0, 180.0, 260.0, 2500.0], amp=0.35, stereo=True)
        draft = make_audio([2500.0, 4500.0], amp=0.12, stereo=True, phase_flip=True)
        original_path = tmp_path / "original.wav"
        draft_path = tmp_path / "draft.wav"
        write_wav(original_path, original, original.frames)
        write_wav(draft_path, draft, draft.frames)
        metrics = evaluate_vocal_placement_ab(original_path, draft_path, tmp_path / "automix", "Lead")
    assert metrics["evaluation_passed"] is False
    assert metrics["damage_scores"]["low_end_loss_db"] < 0.0


def test_iteration_reduces_ducking_gain_and_ms() -> None:
    settings = {"instrumental_duck_amount_db": -1.2, "presence_duck_amount_db": -1.5, "vocal_gain_db": 0.8, "duck_release_ms": 160, "ms_mid_cleanup_amount": 0.15}
    history = build_placement_iteration_history(settings, [{"evaluation_passed": False, "warnings": ["beat_impact_loss_reject"]}])
    assert abs(history["iterations"][1]["settings"]["instrumental_duck_amount_db"]) < abs(settings["instrumental_duck_amount_db"])
    assert history["iterations"][2]["settings"]["vocal_gain_db"] < settings["vocal_gain_db"]
    assert history["iterations"][-1]["settings"].get("bypass_if_still_failing") is True


def test_batch_placement_matrix_and_cli_are_safe() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        manifest = {
            "tracks": [
                {
                    "track_name": "Lead Vocal",
                    "track_guid": "{lead}",
                    "source_classification": source_report(classification="ai_vocal_stem", ai_artifact_score=0.50, placement_context={"masking_2k_5k": 0.80}),
                    "pitch_analysis": pitch_report(),
                },
                {"track_name": "Instrumental Bus", "track_guid": "{inst}"},
                {"track_name": "Backing Vox", "track_guid": "{bgv}", "source_classification": source_report(classification="mixed_vocal_stem"), "pitch_analysis": pitch_report()},
            ]
        }
        manifest_path = tmp_path / "manifest.json"
        adapter_path = tmp_path / "adapter.json"
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        high_conf_adapter(adapter_path)
        paths = run_batch_triage(project_path=None, track_manifest_path=manifest_path, adapter_status_path=adapter_path, output_dir=tmp_path / "automix")
        matrix = json.loads(paths["placement_matrix"].read_text(encoding="utf-8"))
        cli = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts/run_vocal_placement_workflow.py"),
                "--track-manifest",
                str(manifest_path),
                "--adapter-status-json",
                str(adapter_path),
                "--output-dir",
                str(tmp_path / "automix_cli"),
                "--dry-run",
            ],
            check=False,
            capture_output=True,
            text=True,
        )
    assert matrix["summary"]["lead_vocal_tracks"] == 1
    assert matrix["summary"]["dynamic_space_creation_draft"] >= 1
    assert cli.returncode == 0
    assert "project_vocal_placement_matrix.json" in cli.stdout


def test_placement_lua_applicator_is_disabled_draft_only_no_pitch_or_render() -> None:
    text = (ROOT / "automix/apply_vocal_placement_draft.lua").read_text(encoding="utf-8")
    assert "allow_draft_vocal_placement = false" in text
    assert "_PLACEMENT_DRAFT" in text
    assert "assert_original_mix_unmodified_for_vocal_placement" in text
    assert '"contains_pitch_correction": false' in text
    assert "Main_SaveProject" not in text
    assert "RenderFileSection" not in text

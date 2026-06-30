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
from automix.mastering.premaster_iteration_engine import build_premaster_iteration_history
from automix.mastering.premaster_policy import (
    assert_original_master_unmodified_for_premaster,
    build_premaster_chain_plan,
    evaluate_premaster_policy,
    write_premaster_artifacts,
)
from automix.mastering.premaster_profiles import resolve_premaster_profile
from automix.mastering.premaster_safety_analyzer import (
    analyze_premaster_safety,
    build_translation_check,
    evaluate_premaster_ab,
    missing_premaster_eval_metrics,
)


def make_audio(
    freqs: list[float],
    *,
    amp: float = 0.25,
    seconds: float = 0.35,
    sr: int = 44100,
    stereo: bool = True,
    phase_flip: bool = False,
    clip: bool = False,
) -> AudioData:
    frames = []
    for i in range(int(seconds * sr)):
        t = i / sr
        value = sum(math.sin(2.0 * math.pi * freq * t) for freq in freqs) / max(1, len(freqs))
        value *= amp
        if clip:
            value = max(-0.65, min(0.65, value * 2.5))
        if stereo:
            frames.append([value, -value if phase_flip else value * 0.82])
        else:
            frames.append([value])
    return AudioData(sample_rate=sr, channels=2 if stereo else 1, frames=frames)


def high_conf_adapter(path: Path | None = None) -> dict:
    semantic_names = [
        "input_trim_db",
        "clean_eq_amount",
        "dynamic_eq_amount",
        "harshness_guard_amount",
        "deesser_amount",
        "low_end_mono_hz",
        "ms_mid_eq_amount",
        "ms_side_gain_db",
        "bus_compressor_gain_reduction_db",
        "bus_compressor_attack_ms",
        "bus_compressor_release_ms",
        "saturation_amount",
        "clipper_drive_db",
        "limiter_ceiling_dbTP",
        "limiter_max_gain_db",
        "limiter_release_ms",
        "target_lufs",
        "output_gain_db",
    ]
    categories = [
        "input_trim",
        "linear_or_clean_eq",
        "dynamic_eq",
        "de_esser_or_harshness_guard",
        "low_end_mono_control",
        "ms_eq",
        "bus_compressor",
        "optional_subtle_saturation",
        "optional_soft_clipper",
        "true_peak_limiter",
        "loudness_meter",
        "phase_correlation_meter",
        "output_gain",
    ]
    data = {
        "mapping_confidence": 0.92,
        "semantic_controls": {name: {"target_name": name, "confidence": 0.92, "writable": True} for name in semantic_names},
        "plugins": {name: {"plugin": "Mapped " + name, "adapter_confidence": 0.92} for name in categories},
    }
    if path:
        path.write_text(json.dumps(data), encoding="utf-8")
    return data


def test_analyzer_detects_limiter_harshness_fizz_and_stereo_risk() -> None:
    limited = make_audio([80.0, 180.0, 3000.0, 7000.0, 12000.0], amp=0.75, clip=True)
    analysis = analyze_premaster_safety(limited, project_name="Limited")
    assert analysis["loudness_profile"]["limiter_pressure_risk"] > 0.45
    assert analysis["ai_artifact_risk_profile"]["sibilance_splatter_risk"] > 0.20
    phasey = analyze_premaster_safety(make_audio([80.0, 6000.0], amp=0.35, phase_flip=True), project_name="Phase")
    assert phasey["stereo_profile"]["mono_compatibility_risk"] > 0.55


def test_policy_blocks_premaster_when_mix_or_placement_is_not_ready() -> None:
    analysis = analyze_premaster_safety(make_audio([1200.0], amp=0.08), project_name="Buried")
    decision = evaluate_premaster_policy(analysis, workflow_status={"placement_recommendation": "reject_placement"})
    assert decision["premaster_action"] == "mix_revision_required"
    weak = dict(analysis)
    weak["vocal_preservation_profile"] = {**weak["vocal_preservation_profile"], "vocal_forwardness_score": 0.05}
    assert evaluate_premaster_policy(weak)["premaster_action"] == "mix_revision_required"


def test_profiles_are_conservative_and_never_widen_by_default() -> None:
    analysis = analyze_premaster_safety(make_audio([80.0, 180.0, 2500.0], amp=0.78, clip=True), project_name="Loud")
    profile = resolve_premaster_profile("already_mastered_safety", analysis, high_conf_adapter(), requested_target_lufs=-8.0)
    settings = profile["settings"]
    assert settings["bus_compressor_gain_reduction_db"] == 0.0
    assert settings["saturation_amount"] == 0.0
    assert settings["clipper_drive_db"] == 0.0
    assert settings["limiter_max_gain_db"] <= 0.5
    assert settings["ms_side_gain_db"] == 0.0
    assert settings["target_lufs"] <= -14.0


def test_low_confidence_adapter_skips_writes_high_confidence_writes() -> None:
    analysis = analyze_premaster_safety(make_audio([90.0, 1200.0, 2500.0], amp=0.25), project_name="Map")
    low = resolve_premaster_profile("safe_streaming_premaster", analysis, {"semantic_controls": {}, "plugins": {}})
    assert low["semantic_controls_to_write"] == {}
    assert low["semantic_controls_skipped"]
    high = resolve_premaster_profile("safe_streaming_premaster", analysis, high_conf_adapter())
    assert "limiter_max_gain_db" in high["semantic_controls_to_write"]
    assert all(item["safe_to_apply"] for item in high["plugin_chain"])


def test_chain_plan_original_master_guard_and_no_pitch() -> None:
    analysis = analyze_premaster_safety(make_audio([90.0, 1200.0, 2500.0], amp=0.25), project_name="Plan")
    decision = evaluate_premaster_policy(analysis, requested_mode="safe_streaming_premaster")
    plan = build_premaster_chain_plan(analysis, decision, high_conf_adapter())
    assert plan["draft_only"] is True
    assert plan["original_master_must_remain_untouched"] is True
    assert plan["contains_pitch_correction"] is False
    assert plan["safe_to_apply"] is True
    before = {"master_fx_count": 1, "master_volume": 1.0, "master_pan": 0.0, "track_count": 4, "routing_count": 3, "media_checksum": "a", "project_path": "x.rpp"}
    assert_original_master_unmodified_for_premaster(before, dict(before))
    changed = dict(before)
    changed["master_fx_count"] = 2
    try:
        assert_original_master_unmodified_for_premaster(before, changed)
    except AssertionError:
        pass
    else:
        raise AssertionError("master mutation was not detected")


def test_eval_missing_render_and_bad_louder_draft_fail_closed() -> None:
    missing = missing_premaster_eval_metrics()
    assert missing["evaluation_passed"] is False
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        original = make_audio([70.0, 120.0, 250.0, 1200.0], amp=0.35)
        draft = make_audio([4500.0, 7500.0, 12000.0], amp=0.70, phase_flip=True, clip=True)
        original_path = tmp_path / "original.wav"
        draft_path = tmp_path / "draft.wav"
        write_wav(original_path, original, original.frames)
        write_wav(draft_path, draft, draft.frames)
        metrics = evaluate_premaster_ab(original_path, draft_path, tmp_path / "automix")
    assert metrics["evaluation_passed"] is False
    assert metrics["damage_scores"]["low_end_loss_db"] < -1.0
    assert "beat_or_low_end_loss_reject" in metrics["warnings"] or metrics["warnings"]


def test_translation_check_marks_mono_and_phone_risk() -> None:
    analysis = analyze_premaster_safety(make_audio([80.0], amp=0.30, phase_flip=True), project_name="Translation")
    check = build_translation_check(analysis)
    assert check["phase_correlation_warning"] is True
    assert "mono_fold_down_risk" in check["warnings"]


def test_iteration_reduces_processing_and_switches_to_safety() -> None:
    settings = {
        "limiter_max_gain_db": 1.5,
        "clipper_drive_db": 0.3,
        "saturation_amount": 0.06,
        "bus_compressor_gain_reduction_db": 1.0,
        "bus_compressor_attack_ms": 30.0,
        "harshness_guard_amount": 0.18,
    }
    history = build_premaster_iteration_history(settings, [{"evaluation_passed": False, "warnings": ["high_fizz_increase"]}])
    assert history["iterations"][1]["settings"]["limiter_max_gain_db"] < settings["limiter_max_gain_db"]
    assert history["iterations"][2]["settings"]["bus_compressor_gain_reduction_db"] < settings["bus_compressor_gain_reduction_db"]
    assert history["iterations"][-1]["settings"]["switch_profile"] == "safety_only_premaster"


def test_cli_writes_prompt36_artifacts_without_reaper_changes() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        source = make_audio([80.0, 1200.0, 2500.0], amp=0.25)
        source_path = tmp_path / "source.wav"
        adapter_path = tmp_path / "adapter.json"
        write_wav(source_path, source, source.frames)
        high_conf_adapter(adapter_path)
        cli = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts/run_premaster_safety_workflow.py"),
                "--source-mix",
                str(source_path),
                "--adapter-status-json",
                str(adapter_path),
                "--output-dir",
                str(tmp_path / "automix"),
                "--mode",
                "safe_streaming_premaster",
                "--dry-run",
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        plan_path = tmp_path / "automix/chain_plans/project_premaster_chain_plan.json"
        report_path = tmp_path / "automix/eval_reports/project_premaster_report.md"
        plan_exists = plan_path.exists()
        report_exists = report_path.exists()
    assert cli.returncode == 0, cli.stderr
    assert "project_premaster_chain_plan.json" in cli.stdout
    assert plan_exists
    assert report_exists


def test_artifact_writer_creates_required_files() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        output = Path(tmp) / "automix"
        analysis = analyze_premaster_safety(make_audio([100.0, 1200.0], amp=0.22), project_name="Artifacts")
        decision = evaluate_premaster_policy(analysis, requested_mode="safety_only_premaster")
        plan = build_premaster_chain_plan(analysis, decision, high_conf_adapter(), output)
        paths = write_premaster_artifacts(output, analysis, decision, plan)
    assert paths["analysis"].name == "project_premaster_safety_analysis.json"
    assert paths["chain_plan"].name == "project_premaster_chain_plan.json"
    assert paths["rollback"].name == "project_premaster_rollback.json"
    assert paths["translation_check"].name == "project_translation_check.json"
    assert paths["report"].name == "project_premaster_report.md"


def test_premaster_lua_applicator_is_disabled_draft_only_no_pitch_or_render() -> None:
    text = (ROOT / "automix/apply_premaster_draft.lua").read_text(encoding="utf-8")
    assert "allow_draft_premaster = false" in text
    assert "_PREMASTER_DRAFT" in text
    assert "assert_original_master_unmodified_for_premaster" in text
    assert '"contains_pitch_correction": false' in text
    assert "contains_master_limiter_on_original" in text
    assert "Main_SaveProject" not in text
    assert "RenderFileSection" not in text
    assert "Main_OnCommand(40004" not in text


if __name__ == "__main__":
    for name, func in sorted(globals().items()):
        if name.startswith("test_") and callable(func):
            func()
    print("prompt36 premaster safety tests passed")

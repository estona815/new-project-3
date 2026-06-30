from __future__ import annotations

import json
import math
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from automix.analyze_ai_pitch_source import AudioData
from automix.export.audio_export_utils import write_pcm_wav
from automix.reference.genre_target_profiles import get_target_profile
from automix.reference.reference_adjustment_applier import assert_reference_match_draft_safe, create_reference_match_draft_metadata
from automix.reference.reference_adjustment_iteration_engine import build_reference_iteration_history
from automix.reference.reference_adjustment_planner import build_reference_adjustment_plan
from automix.reference.reference_analyzer import analyze_current_mix, analyze_manifest_references, analyze_reference_audio
from automix.reference.reference_comparison_engine import compare_current_to_reference_and_target
from automix.reference.reference_evaluation import build_reference_match_matrix, evaluate_reference_match_ab, missing_reference_match_eval
from automix.reference.reference_intake import build_reference_manifest
from automix.reference.reference_report import write_reference_match_report


def make_audio(freqs: list[float], *, amp: float = 0.25, seconds: float = 0.35, sr: int = 44100, phase_flip: bool = False, clip: bool = False) -> AudioData:
    frames = []
    for i in range(int(seconds * sr)):
        t = i / sr
        value = sum(math.sin(2.0 * math.pi * freq * t) for freq in freqs) / max(1, len(freqs))
        value *= amp
        if clip:
            value = max(-0.7, min(0.7, value * 3.5))
        frames.append([value, -value if phase_flip else value * 0.85])
    return AudioData(sample_rate=sr, channels=2, frames=frames)


def write_source(path: Path, freqs: list[float], *, amp: float = 0.25, phase_flip: bool = False, clip: bool = False) -> Path:
    write_pcm_wav(path, make_audio(freqs, amp=amp, phase_flip=phase_flip, clip=clip), bit_depth=24)
    return path


def test_reference_intake_missing_multi_and_profile_only() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        ref = write_source(tmp_path / "ref.wav", [80.0, 1200.0])
        manifest = build_reference_manifest(project_name="Song", references=[(ref, "primary_reference"), (tmp_path / "missing.wav", "width_reference")], output_dir=tmp_path / "automix")
        profile_only = build_reference_manifest(project_name="Song", references=[], target_profile="phone_reels_loud_clear", output_dir=tmp_path / "automix2")
    assert len(manifest["references"]) == 2
    assert manifest["references"][1]["exists"] is False
    assert "reference_file_missing" in manifest["references"][1]["warnings"]
    assert profile_only["references"] == []
    assert "not copying musical content" in manifest["copyright_safety_note"]


def test_target_profiles_exist_and_safety_values() -> None:
    raw = get_target_profile("raw_digicore_intense")
    phone = get_target_profile("phone_reels_loud_clear")
    clean = get_target_profile("clean_commercial_ai_repair")
    assert get_target_profile("digicore_hyperpop_hiphop_vocal_forward")["vocal_forwardness_target"] == 0.80
    assert raw["drum_energy_target"] > 0.80
    assert raw["ai_artifact_exposure_max"] <= 0.40
    assert phone["mono_compatibility_min"] >= 0.82
    assert clean["ai_artifact_exposure_max"] < raw["ai_artifact_exposure_max"]


def test_analyzer_and_comparison_block_brightness_loudness_and_width() -> None:
    current = analyze_reference_audio(make_audio([12000.0, 7000.0], amp=0.55, phase_flip=True, clip=True), reference_name="current", role="current_mix")
    current["artifact_profile"]["high_fizz_risk"] = 0.70
    ref = analyze_reference_audio(make_audio([80.0, 120.0, 1200.0], amp=0.35), reference_name="ref", role="primary_reference")
    comparison = compare_current_to_reference_and_target(project_name="Song", current_analysis=current, reference_analyses=[ref], target_profile_name="clean_commercial_ai_repair")
    blocked = comparison["unsafe_adjustments_blocked"]
    assert "high_shelf_boost_blocked_ai_fizz_risk" in blocked
    assert "more_limiting_blocked_current_mix_already_limited" in blocked
    assert "master_widening_blocked_mono_risk" in blocked


def test_planner_prefers_space_control_and_blocks_unsafe_moves() -> None:
    comparison = {
        "target_profile": "digicore_hyperpop_hiphop_vocal_forward",
        "differences": {
            "vocal_too_low": 0.4,
            "lead_melody_too_low": 0.3,
            "drums_too_soft": 0.3,
            "808_too_weak": 0.4,
            "low_end_too_muddy": 0.3,
            "vocal_too_harsh": 0.0,
            "air_too_fizzy": 0.0,
            "stereo_too_narrow": 0.0,
            "mix_not_loud_enough": 0.0,
        },
        "unsafe_adjustments_blocked": ["808_boost_blocked_until_low_end_controlled", "high_shelf_boost_blocked_ai_fizz_risk"],
        "warnings": [],
    }
    plan = build_reference_adjustment_plan(project_name="Song", comparison=comparison)
    assert plan["adjustments"][0]["adjustment_type"] == "sidechain_dynamic_eq"
    assert any(item["adjustment_type"] == "low_end_control" for item in plan["adjustments"])
    assert any(item["adjustment_type"] == "parallel_transient_support" for item in plan["adjustments"])
    assert any(item["requested_adjustment"] == "high_shelf_boost" for item in plan["blocked_adjustments"])


def test_draft_safety_rollback_and_iteration_reduce_not_intensify() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        output = Path(tmp) / "automix"
        plan = {"adjustments": [{"risk": "low", "adjustment_type": "sidechain_dynamic_eq", "semantic_settings": {"duck_amount_db": -1.0, "gain_db": 0.8}}], "contains_pitch_correction": False, "contains_reference_audio_content": False}
        rollback = create_reference_match_draft_metadata(plan, output, apply_draft=True)
        assert_reference_match_draft_safe(plan, rollback)
        history = build_reference_iteration_history(plan, [{"evaluation_passed": False, "warnings": ["ai_artifact_exposure_reject"]}])
    assert rollback["original_mix_untouched"] is True
    assert rollback["original_master_untouched"] is True
    assert rollback["contains_pitch_correction"] is False
    assert history["iterations"][1]["plan"]["adjustments"][0]["semantic_settings"]["gain_db"] < 0.8
    assert history["never_intensify_after_damage"] is True


def test_eval_missing_and_bad_draft_rejects() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        missing = missing_reference_match_eval()
        current = write_source(tmp_path / "current.wav", [80.0, 180.0, 1200.0], amp=0.25)
        bad = write_source(tmp_path / "bad.wav", [7000.0, 12000.0], amp=0.8, phase_flip=True, clip=True)
        ref_analysis = analyze_reference_audio(make_audio([1200.0, 2500.0], amp=0.3), reference_name="ref", role="primary_reference")
        metrics = evaluate_reference_match_ab(current_mix_path=current, reference_match_draft_path=bad, reference_analyses=[ref_analysis], target_profile="clean_commercial_ai_repair", project_name="Song", output_dir=tmp_path / "automix")
    assert missing["evaluation_passed"] is False
    assert metrics["evaluation_passed"] is False
    assert metrics["warnings"]


def test_report_matrix_and_cli_target_profile_only_are_safe() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        output = tmp_path / "automix"
        manifest = build_reference_manifest(project_name="Song", references=[], target_profile="phone_reels_loud_clear", output_dir=output)
        refs, current = analyze_manifest_references(manifest, output)
        comparison = compare_current_to_reference_and_target(project_name="Song", current_analysis=current, reference_analyses=refs, target_profile_name="phone_reels_loud_clear", output_dir=output)
        plan = build_reference_adjustment_plan(project_name="Song", comparison=comparison, output_dir=output)
        eval_metrics = missing_reference_match_eval()
        matrix = build_reference_match_matrix("Song", comparison, plan, eval_metrics, output)
        report = write_reference_match_report(output_dir=output, manifest=manifest, current_analysis=current, reference_analyses=refs, comparison=comparison, plan=plan, eval_metrics=eval_metrics, iteration_history={"iterations": []})
        cli = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts/run_reference_match_workflow.py"),
                "--project",
                str(tmp_path / "song.rpp"),
                "--target-profile",
                "phone_reels_loud_clear",
                "--mode",
                "target_profile_scan_only",
                "--dry-run",
                "--output-dir",
                str(tmp_path / "automix_cli"),
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        report_text = report.read_text(encoding="utf-8")
    assert matrix["final_recommendation"] == "target_profile_only_used"
    assert "References were used only for broad tonal" in report_text
    assert cli.returncode == 0
    assert "target_profile_only_used" in cli.stdout


def test_docs_exist() -> None:
    assert (ROOT / "docs/reference_matching_genre_targeting.md").exists()
    assert (ROOT / "docs/manual_test_plan_prompt38.md").exists()


if __name__ == "__main__":
    for name, func in sorted(globals().items()):
        if name.startswith("test_") and callable(func):
            func()
    print("prompt38 reference matching tests passed")

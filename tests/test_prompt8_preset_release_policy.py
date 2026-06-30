from __future__ import annotations

import json
import math
import re
from pathlib import Path

from VOCAL_CLARITY_REPAIR_SYSTEM.eval.preset_policy import (
    fresh_default_values,
    load_factory_presets,
    load_release_policy,
    preset_by_name,
    sanitize_preset_values,
    validate_factory_presets,
)
from VOCAL_CLARITY_REPAIR_SYSTEM.eval.release_gate import evaluate_release_candidate, evaluate_run_report
from VOCAL_CLARITY_REPAIR_SYSTEM.eval.evaluation_harness import preset_slug, run_evaluation
from VOCAL_CLARITY_REPAIR_SYSTEM.eval.synthetic_assets import generate_synthetic_suite


ROOT = Path(__file__).resolve().parents[1]
JSFX = ROOT / "VOCAL_CLARITY_REPAIR_SYSTEM" / "JSFX" / "vocal_ai_artifact_split_tamer.jsfx"
FACTORY = ROOT / "VOCAL_CLARITY_REPAIR_SYSTEM" / "presets" / "factory_presets_safe_defaults.json"
RELEASE = ROOT / "VOCAL_CLARITY_REPAIR_SYSTEM" / "presets" / "release_candidate_policy.json"
PROMPT8_DOC = ROOT / "VOCAL_CLARITY_REPAIR_SYSTEM" / "docs" / "prompt8_preset_release_policy.md"
LISTENING_FORM = ROOT / "VOCAL_CLARITY_REPAIR_SYSTEM" / "reports" / "listening_approval_form.md"
PRESET_REPORT_TEMPLATE = ROOT / "VOCAL_CLARITY_REPAIR_SYSTEM" / "reports" / "preset_report_template.md"


REQUIRED_PRESETS = {
    "Preserve",
    "Balanced",
    "AI Metallic Surgical",
    "Hiss / Room Tone Gentle",
    "Voiceover Clean",
    "Strong Test / Repair",
    "DSP Only Safe",
    "Side Noise Cleanup",
    "Artifact Focus Low Denoise",
}


def parse_jsfx_defaults() -> dict[str, float]:
    defaults: dict[str, float] = {}
    pattern = re.compile(r"^slider(\d+):(-?\d+(?:\.\d+)?)<")
    for line in JSFX.read_text(encoding="utf-8").splitlines():
        match = pattern.match(line)
        if match:
            defaults[f"slider{match.group(1)}"] = float(match.group(2))
    return defaults


def make_report(preset: str, *, score: float = 100.0, safety: float = 100.0) -> dict:
    scores = {
        "noise_reduction": 25.0,
        "source_preservation": score,
        "clarity": score,
        "air": score,
        "transient": score,
        "residual_cleanliness": score,
        "stereo": score,
        "safety": safety,
        "overall": score,
    }
    failures = [] if safety >= 100 else ["nan_inf"]
    return {
        "schema": "codex-vocal-ab-eval-report-v1",
        "preset": preset,
        "summary": {"pass_count": 1, "warning_count": 0, "fail_count": 0 if not failures else 1},
        "files": [
            {
                "id": "clean_vocal_01",
                "category": "clean_vocal",
                "status": "pass" if not failures else "fail",
                "scores": scores,
                "warnings": [],
                "failures": failures,
            }
        ],
    }


def test_factory_presets_schema_and_required_names_are_present() -> None:
    policy = load_factory_presets()

    assert policy["schema"] == "codex-vocal-factory-presets-v1"
    names = {preset["name"] for preset in policy["presets"]}
    assert REQUIRED_PRESETS <= names
    assert policy["default_preset"] == "Preserve"
    assert validate_factory_presets(policy) == []


def test_fresh_preserve_defaults_match_jsfx_slider_defaults() -> None:
    policy = load_factory_presets()
    preserve = fresh_default_values(policy)
    jsfx = parse_jsfx_defaults()

    for slider, value in preserve.items():
        assert slider in jsfx
        assert math.isclose(float(value), jsfx[slider], abs_tol=1.0e-7), slider

    assert preserve["slider8"] == 0
    assert preserve["slider9"] == 30
    assert preserve["slider10"] == 8
    assert preserve["slider14"] == 0.35
    assert preserve["slider16"] >= 0.85
    assert preserve["slider17"] >= 0.85
    assert preserve["slider18"] >= 0.80
    assert preserve["slider22"] == 0
    assert preserve["slider27"] == 0


def test_strong_mode_is_isolated_and_not_default() -> None:
    policy = load_factory_presets()
    release = load_release_policy()
    strong = preset_by_name(policy, "Strong Test / Repair")
    preserve = preset_by_name(policy, "Preserve")

    assert policy["default_preset"] == "Preserve"
    assert not preserve["strong_mode"]
    assert strong["strong_mode"]
    assert not strong["release_default_allowed"]
    assert strong["jsfx_sliders"]["slider22"] == 3
    assert strong["jsfx_sliders"]["slider10"] <= 24
    assert release["strong_policy"]["never_default"]
    assert release["preset_gates"]["Strong Test / Repair"]["quality_report_only"]


def test_legacy_missing_and_invalid_values_are_safely_clamped() -> None:
    policy = load_factory_presets()
    sanitized = sanitize_preset_values(
        {
            "slider1": 50,
            "slider9": float("nan"),
            "slider10": 999,
            "slider16": -5,
            "slider27": "bad",
        },
        policy,
    )

    assert sanitized["slider1"] == 50
    assert sanitized["slider9"] == policy["parameter_definitions"]["slider9"]["default"]
    assert sanitized["slider10"] == 24
    assert sanitized["slider16"] == 0
    assert sanitized["slider27"] == policy["parameter_definitions"]["slider27"]["default"]
    assert sanitized["slider28"] == policy["parameter_definitions"]["slider28"]["default"]


def test_ui_policy_keeps_main_controls_simple_and_labels_honest() -> None:
    policy = load_factory_presets()
    layout = policy["ui_layout"]
    main = set(layout["main_controls"])
    advanced = set(layout["advanced_controls"])
    developer = set(layout["developer_controls"])

    assert {"Amount", "MultibandMode", "DryWet", "VocalPreserve", "ClarityPreserve", "AirPreserve", "ResidualMonitor"} <= main
    assert "MaxSuppressionDb" in advanced
    assert "ProcessingEnabled" in developer
    forbidden = {label.lower() for label in layout["avoid_labels"]}
    serialized = json.dumps(policy, ensure_ascii=False).lower()
    for label in forbidden:
        assert serialized.count(label) == 1


def test_release_policy_contains_blockers_categories_and_required_prompt_gates() -> None:
    policy = load_release_policy()

    assert policy["schema"] == "codex-vocal-release-candidate-policy-v1"
    assert "clean_consonant_vocal" in policy["required_test_categories"]
    assert "full_mix_center_vocal" in policy["required_test_categories"]
    assert "strong_mode_default_or_auto_selected" in policy["release_blockers"]
    assert "Prompt 8 preset gate tests" in policy["required_prompt_tests"]
    assert "Amount" in policy["automation_safety"]["continuous_parameters_to_smooth"]
    assert "MultibandMode" in policy["automation_safety"]["mode_parameters"]
    assert policy["preset_gates"]["Preserve"]["minimum_average_scores"]["source_preservation"] >= 85
    assert policy["preset_gates"]["Preserve"]["minimum_average_scores"]["safety"] == 100


def test_release_gate_passes_complete_high_score_report_set() -> None:
    policy = load_release_policy()
    reports = [make_report(preset) for preset in policy["release_presets"]]

    result = evaluate_release_candidate(reports, policy)

    assert result["status"] == "pass"
    assert result["blockers"] == []


def test_release_gate_fails_missing_preset_and_low_preserve_score() -> None:
    policy = load_release_policy()
    reports = [make_report(preset) for preset in policy["release_presets"] if preset != "Balanced"]
    reports[0] = make_report("Preserve", score=50.0)

    result = evaluate_release_candidate(reports, policy)

    assert result["status"] == "fail"
    assert "missing_report:Balanced" in result["blockers"]
    assert any("Preserve:average_source_preservation_below_gate" in blocker for blocker in result["blockers"])


def test_release_gate_blocks_strong_mode_safety_failure_but_not_quality_role() -> None:
    policy = load_release_policy()
    strong_bad = make_report("Strong Test / Repair", score=40.0, safety=0.0)

    result = evaluate_run_report(strong_bad, policy)

    assert result["status"] == "fail"
    assert any(blocker.startswith("safety_failure") for blocker in result["blockers"])
    assert result["quality_report_only"]


def test_synthetic_assets_cover_prompt8_required_categories(tmp_path: Path) -> None:
    manifest = generate_synthetic_suite(tmp_path)
    generated = {item["category"] for item in manifest["items"]}
    required = set(load_release_policy()["required_test_categories"])

    assert required <= generated
    assert len(manifest["items"]) >= 18


def test_prompt8_preset_names_are_path_safe_in_evaluation_outputs(tmp_path: Path) -> None:
    generate_synthetic_suite(tmp_path / "assets")
    preset = "Hiss / Room Tone Gentle"

    run_evaluation(
        tmp_path / "assets" / "manifest.synthetic.json",
        preset=preset,
        output_dir=tmp_path / "eval",
        renderer="passthrough",
        block_size=256,
    )

    slug = preset_slug(preset)
    assert slug == "Hiss_Room_Tone_Gentle"
    assert (tmp_path / "eval" / slug / "run_metrics.json").exists()
    assert not (tmp_path / "eval" / "Hiss " / " Room Tone Gentle" / "run_metrics.json").exists()


def test_prompt8_documentation_and_checklists_exist() -> None:
    doc = PROMPT8_DOC.read_text(encoding="utf-8")
    form = LISTENING_FORM.read_text(encoding="utf-8")
    template = PRESET_REPORT_TEMPLATE.read_text(encoding="utf-8")

    assert "not a maximum noise-removal tool" in doc
    assert "Residual means" in doc
    assert "Release Blockers" in doc
    assert "Vocal preservation" in form
    assert "Residual cleanliness" in form
    assert "Strong Test / Repair" in template

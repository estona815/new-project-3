from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests/fixtures/pitch_safety"
LUA = ROOT / "automix/apply_conservative_pitch_draft.lua"
AUDIT = ROOT / "automix/analysis_reports/prompt32_audit_report.json"
THRESHOLDS = ROOT / "automix/config/pitch_safety_thresholds.json"

sys.path.insert(0, str(ROOT))

from automix.pitch.conservative_pitch_profiles import resolve_pitch_profile
from automix.pitch.pitch_evaluation import harden_pitch_evaluation, missing_render_metrics
from automix.pitch.pitch_iteration import build_iteration_history
from automix.pitch.pitch_safety_gate import evaluate_pitch_safety, input_from_reports


def fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def adapter(available: bool = True, confidence: float = 0.92, controls: set[str] | None = None) -> dict:
    controls = controls or {"correction_amount", "depth", "dry_wet", "speed", "formant_preserve"}
    return {
        "plugin_name": "MAutoPitch",
        "available": available,
        "mapping_confidence": confidence,
        "semantic_controls": {
            name: {"target_name": name, "confidence": 0.92, "writable": True}
            for name in controls
        },
    }


def gate_for_fixture(name: str, mode: str = "allow_light_pitch_draft", adapter_status: dict | None = None) -> dict:
    data = fixture(name)
    source = {"scan_date_utc": "2026-05-31T00:00:00Z", "track_name": "fixture", **data["classification_metrics"]}
    pitch = data["pitch_metrics"]
    status = adapter_status or adapter(confidence=data["adapter_confidence"])
    available = status["semantic_controls"]
    return evaluate_pitch_safety(
        input_from_reports(source, pitch, status, available_semantic_controls=available, user_goal=mode)
    )


def test_audit_report_exists_and_prompt31_components_found() -> None:
    data = json.loads(AUDIT.read_text(encoding="utf-8"))
    assert data["schema"] == "automix-prompt32-audit-report-v1"
    assert data["test_framework_detected"] is True
    found = {item["component"] for item in data["prompt31_files_found"]}
    assert "source_classification" in found
    assert "pitch_analysis" in found
    assert "draft_track_creation" in found
    assert "human_review_report" in found


def test_full_mix_likelihood_blocks_automatic_tuning() -> None:
    decision = gate_for_fixture("full_mix_dense_polyphonic.json")
    assert decision["eligible"] is False
    assert decision["decision"] == "full_mix_unsafe"
    assert "FULL_MIX_LIKELY" in decision["reason_codes"]
    assert decision["max_correction_amount"] == 0.0


def test_already_tuned_and_low_pitch_confidence_fail_closed() -> None:
    tuned = gate_for_fixture("ai_vocal_already_tuned.json")
    low = gate_for_fixture("unknown_low_confidence.json")
    assert tuned["eligible"] is False
    assert tuned["decision"] == "skip"
    assert "ALREADY_TUNED_HIGH" in tuned["reason_codes"]
    assert low["eligible"] is False
    assert "PITCH_CONFIDENCE_LOW" in low["reason_codes"]


def test_source_separated_defaults_to_manual_review_or_skip() -> None:
    decision = gate_for_fixture("source_separated_watery.json")
    assert decision["decision"] in {"manual_review_required", "skip", "apply_micro"}
    assert decision["max_correction_amount"] <= 0.05
    assert decision["requires_manual_approval"] is True
    assert "SOURCE_SEPARATED_HIGH" in decision["reason_codes"]


def test_adapter_confidence_and_required_controls_block_parameter_writes() -> None:
    low_adapter = gate_for_fixture("raw_vocal_like_monophonic.json", adapter_status=adapter(confidence=0.4))
    missing_amount = gate_for_fixture(
        "raw_vocal_like_monophonic.json",
        adapter_status=adapter(controls={"dry_wet", "speed", "formant_preserve"}),
    )
    missing_mix = gate_for_fixture(
        "raw_vocal_like_monophonic.json",
        adapter_status=adapter(controls={"correction_amount", "speed", "formant_preserve"}),
    )
    assert low_adapter["decision"] == "plugin_mapping_required"
    assert "PLUGIN_MAPPING_UNCERTAIN" in low_adapter["reason_codes"]
    assert missing_amount["eligible"] is False
    assert "SEMANTIC_CONTROL_MISSING" in missing_amount["reason_codes"]
    assert missing_mix["eligible"] is False
    assert "UNKNOWN_PLUGIN_PARAMETER" in missing_mix["reason_codes"]


def test_override_modes_remain_safe() -> None:
    no_pitch = gate_for_fixture("raw_vocal_like_monophonic.json", mode="no_pitch_correction")
    experiment = gate_for_fixture("full_mix_dense_polyphonic.json", mode="allow_full_mix_pitch_experiment")
    assert no_pitch["eligible"] is False
    assert no_pitch["decision"] == "skip"
    assert experiment["allowed_mode"] == "full_mix_pitch_experiment"
    assert experiment["max_correction_amount"] <= 0.03
    assert experiment["draft_only"] is True


def test_profiles_are_source_aware_and_clamped_by_gate() -> None:
    gate = gate_for_fixture("raw_vocal_like_monophonic.json")
    controls = adapter()["semantic_controls"]
    raw = resolve_pitch_profile("raw_vocal", gate, controls)
    ai = resolve_pitch_profile("ai_vocal_stem", {**gate, "max_correction_amount": 0.08}, controls)
    source_sep = resolve_pitch_profile("source_separated_vocal", {**gate, "max_correction_amount": 0.05}, controls)
    full = resolve_pitch_profile("full_mix", {**gate, "eligible": False, "max_correction_amount": 0.0}, controls)
    no_formant = resolve_pitch_profile("raw_vocal", gate, {"correction_amount": {}, "dry_wet": {}, "speed": {}})

    assert raw["profile"] == "raw_vocal_natural"
    assert ai["settings"]["correction_amount"] <= 0.08
    assert source_sep["settings"]["correction_amount"] <= 0.05
    assert full["settings"]["apply"] is False
    assert no_formant["settings"]["correction_amount"] <= raw["settings"]["correction_amount"] * 0.5


def test_evaluation_missing_render_and_damage_metrics_fail() -> None:
    missing = missing_render_metrics("Lead")
    damaged = harden_pitch_evaluation(
        {
            "renders_created": {"original": True, "pitch_processed": True, "loudness_matched": True, "difference": True},
            "pitch_error_improvement": 25.0,
            "formant_drift_score": 0.5,
            "metallic_increase_score": 0.0,
            "clarity_loss_db": 0.0,
            "air_loss_db": 0.0,
            "transient_loss": 0.0,
            "stereo_width_change": 0.0,
            "tail_warble_score": 0.0,
            "reverb_tail_pitch_drag_score": 0.0,
            "difference_source_energy": 0.0,
            "warnings": [],
        }
    )
    assert missing["evaluation_passed"] is False
    assert missing["recommended_action"] == "manual_review_required"
    assert damaged["evaluation_passed"] is False
    assert damaged["recommended_action"] == "reject_pitch_correction"
    assert "FORMANT_DRIFT" in damaged["reason_codes"]


def test_iteration_only_reduces_or_rejects() -> None:
    history = build_iteration_history(
        {"correction_amount": 0.16, "speed": 0.18, "dry_wet": 0.40},
        [{"evaluation_passed": False, "reason_codes": ["FORMANT_DRIFT"]}],
    )
    assert history["iterations"][1]["settings"]["correction_amount"] == 0.08
    assert history["iterations"][2]["settings"]["speed"] == 0.09
    assert history["iterations"][-1]["decision"] == "reject_pitch_correction"


def test_lua_draft_guard_and_rollback_metadata_are_present() -> None:
    text = LUA.read_text(encoding="utf-8")
    assert "allow_draft_pitch_correction = false" in text
    assert "assert_original_track_unmodified" in text
    assert "original_track_guid" in text
    assert "draft_track_guid" in text
    assert "plugins_inserted" in text
    assert "parameters_written" in text
    assert "TrackFX_SetParam(" not in text
    assert "TrackFX_SetPreset" not in text
    assert "Main_SaveProject" not in text


def test_threshold_config_and_docs_exist() -> None:
    thresholds = json.loads(THRESHOLDS.read_text(encoding="utf-8"))
    docs = (ROOT / "docs/already_mixed_ai_pitch_correction.md").read_text(encoding="utf-8")
    runbook = (ROOT / "docs/automix_runbook.md").read_text(encoding="utf-8")
    assert thresholds["formant_drift_score_reject"] == 0.35
    assert "PitchSafetyGate" in docs
    assert "Prompt 32 Fail-Closed Layer" in runbook

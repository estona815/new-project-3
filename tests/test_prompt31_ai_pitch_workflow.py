from __future__ import annotations

import importlib.util
import json
import math
import random
import sys
import tempfile
import wave
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ANALYZER = ROOT / "automix/analyze_ai_pitch_source.py"
LUA_APPLICATOR = ROOT / "automix/apply_conservative_pitch_draft.lua"
ADAPTER_SEMANTICS = ROOT / "automix/pitch_adapter_semantics.json"
DOC = ROOT / "docs/already_mixed_ai_pitch_correction.md"
RUNBOOK = ROOT / "docs/automix_runbook.md"
MANUAL = ROOT / "docs/manual_test_plan_prompt31.md"


def load_analyzer():
    spec = importlib.util.spec_from_file_location("prompt31_analyzer", ANALYZER)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def write_wav(path: Path, frames: list[float] | list[list[float]], sample_rate: int = 16000, channels: int = 1) -> None:
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        raw = bytearray()
        for frame in frames:
            values = frame if isinstance(frame, list) else [frame]
            for value in values[:channels]:
                sample = int(max(-1.0, min(1.0, value)) * 32767.0)
                raw.extend(sample.to_bytes(2, "little", signed=True))
        wf.writeframes(bytes(raw))


def vibrato_vocal(sample_rate: int = 16000, seconds: float = 1.2) -> list[float]:
    out = []
    phase = 0.0
    for n in range(int(sample_rate * seconds)):
        t = n / sample_rate
        f0 = 220.0 * (2.0 ** ((25.0 * math.sin(2.0 * math.pi * 5.0 * t)) / 1200.0))
        phase += 2.0 * math.pi * f0 / sample_rate
        out.append(0.35 * math.sin(phase))
    return out


def quantized_pitch_vocal(sample_rate: int = 16000, seconds: float = 2.0) -> list[float]:
    notes = [220.0, 246.94, 261.63, 293.66]
    out = []
    phase = 0.0
    for n in range(int(sample_rate * seconds)):
        f0 = notes[(n // (sample_rate // 4)) % len(notes)]
        phase += 2.0 * math.pi * f0 / sample_rate
        out.append(0.35 * math.sin(phase))
    return out


def full_mix_like(sample_rate: int = 16000, seconds: float = 2.0) -> list[list[float]]:
    rng = random.Random(31)
    frames = []
    for n in range(int(sample_rate * seconds)):
        t = n / sample_rate
        hit_pos = n % (sample_rate // 8)
        drums = 0.95 * (1.0 - hit_pos / 100.0) if hit_pos < 100 else 0.0
        left = (
            0.45 * math.sin(2.0 * math.pi * 55.0 * t)
            + 0.20 * math.sin(2.0 * math.pi * 220.0 * t)
            + 0.16 * math.sin(2.0 * math.pi * 277.0 * t)
            + 0.14 * math.sin(2.0 * math.pi * 330.0 * t)
            + drums
            + 0.05 * (rng.random() * 2.0 - 1.0)
        )
        right = (
            0.40 * math.sin(2.0 * math.pi * 60.0 * t)
            + 0.18 * math.sin(2.0 * math.pi * 247.0 * t)
            + 0.16 * math.sin(2.0 * math.pi * 311.0 * t)
            + 0.12 * math.sin(2.0 * math.pi * 392.0 * t)
            + drums * 0.60
            - 0.05 * (rng.random() * 2.0 - 1.0)
        )
        peak = max(1.0, abs(left), abs(right))
        frames.append([left / peak * 0.9, right / peak * 0.9])
    return frames


def high_confidence_adapter(path: Path) -> None:
    data = {
        "plugin_name": "MAutoPitch",
        "available": True,
        "mapping_confidence": 0.92,
        "semantic_controls": {
            "correction_amount": {"target_name": "Amount", "confidence": 0.95, "writable": True},
            "speed": {"target_name": "Speed", "confidence": 0.91, "writable": True},
            "depth": {"target_name": "Depth", "confidence": 0.90, "writable": True},
            "formant_preserve": {"target_name": "Formant Preserve", "confidence": 0.90, "writable": True},
            "humanize": {"target_name": "Humanize", "confidence": 0.90, "writable": True},
            "vibrato_preserve": {"target_name": "Vibrato Preserve", "confidence": 0.90, "writable": True},
            "dry_wet": {"target_name": "Dry/Wet", "confidence": 0.90, "writable": True},
        },
    }
    path.write_text(json.dumps(data), encoding="utf-8")


def test_prompt31_assets_exist_and_adapter_json_is_safe() -> None:
    assert ANALYZER.exists()
    assert LUA_APPLICATOR.exists()
    assert DOC.exists()
    assert RUNBOOK.exists()
    assert MANUAL.exists()
    data = json.loads(ADAPTER_SEMANTICS.read_text(encoding="utf-8"))
    assert data["safety"]["no_fixed_parameter_indexes"] is True
    assert data["safety"]["unknown_parameters_are_skipped"] is True
    assert data["safety"]["draft_track_only"] is True
    assert data["conservative_defaults"]["already_mixed_ai_vocal"]["correction_amount"] == 0.08
    assert data["conservative_defaults"]["full_mix"]["apply"] is False


def test_raw_vocal_like_source_is_classified_before_pitch_plan() -> None:
    mod = load_analyzer()
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        source = tmp_path / "raw.wav"
        write_wav(source, vibrato_vocal())
        outputs = mod.run_analysis(source, tmp_path / "automix", "Raw Vocal")
        classification = json.loads(outputs["classification"].read_text(encoding="utf-8"))
        pitch = json.loads(outputs["pitch_analysis"].read_text(encoding="utf-8"))
        plan = json.loads(outputs["chain_plan"].read_text(encoding="utf-8"))

    assert classification["classification"] == "raw_vocal"
    assert classification["full_mix_likelihood"] < 0.45
    assert pitch["monophonic_pitch_confidence"] > 0.45
    assert plan["apply"] is False
    assert "No high-confidence user-learned pitch adapter mapping" in " ".join(plan["skip_or_caution_reasons"])


def test_full_mix_likelihood_blocks_auto_tune_even_with_adapter() -> None:
    mod = load_analyzer()
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        source = tmp_path / "mix.wav"
        adapter = tmp_path / "adapter.json"
        write_wav(source, full_mix_like(), channels=2)
        high_confidence_adapter(adapter)
        outputs = mod.run_analysis(source, tmp_path / "automix", "Full Mix", adapter_status_path=adapter)
        classification = json.loads(outputs["classification"].read_text(encoding="utf-8"))
        plan = json.loads(outputs["chain_plan"].read_text(encoding="utf-8"))

    assert classification["full_mix_likelihood"] > 0.45
    assert classification["classification"] == "full_mix"
    assert classification["pitch_correction_risk"] == "unsafe"
    assert plan["apply"] is False
    assert plan["final_recommendation"] == "full_mix_unsafe"


def test_already_quantized_pitch_contour_skips_global_correction() -> None:
    mod = load_analyzer()
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        source = tmp_path / "quantized.wav"
        adapter = tmp_path / "adapter.json"
        write_wav(source, quantized_pitch_vocal())
        high_confidence_adapter(adapter)
        outputs = mod.run_analysis(source, tmp_path / "automix", "Already Tuned", adapter_status_path=adapter)
        classification = json.loads(outputs["classification"].read_text(encoding="utf-8"))
        plan = json.loads(outputs["chain_plan"].read_text(encoding="utf-8"))

    assert classification["already_tuned_score"] > 0.70
    assert plan["apply"] is False
    assert plan["safety_gate"]["decision"] == "skip"
    assert "ALREADY_TUNED_HIGH" in plan["safety_gate"]["reason_codes"]


def test_low_pitch_confidence_skips_auto_correction() -> None:
    mod = load_analyzer()
    rng = random.Random(5)
    noise = [0.25 * (rng.random() * 2.0 - 1.0) for _ in range(16000)]
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        source = tmp_path / "noise.wav"
        adapter = tmp_path / "adapter.json"
        write_wav(source, noise)
        high_confidence_adapter(adapter)
        outputs = mod.run_analysis(source, tmp_path / "automix", "Noise", adapter_status_path=adapter)
        pitch = json.loads(outputs["pitch_analysis"].read_text(encoding="utf-8"))
        plan = json.loads(outputs["chain_plan"].read_text(encoding="utf-8"))

    assert pitch["monophonic_pitch_confidence"] < 0.45
    assert plan["apply"] is False
    assert plan["safety_gate"]["reason_codes"]


def test_unknown_adapter_parameters_are_skipped_without_fixed_indexes() -> None:
    mod = load_analyzer()
    classification = {
        "scan_date_utc": "2026-05-31T00:00:00Z",
        "track_name": "Lead",
        "classification": "raw_vocal",
        "already_mixed_score": 0.10,
        "already_tuned_score": 0.10,
        "full_mix_likelihood": 0.05,
        "source_separated_likelihood": 0.05,
        "baked_reverb_score": 0.05,
        "pitch_correction_risk": "low",
    }
    pitch = {"monophonic_pitch_confidence": 0.90}
    adapter = {
        "plugin_name": "MAutoPitch",
        "available": True,
        "mapping_confidence": 0.90,
        "semantic_controls": {
            "correction_amount": {"target_name": "Amount", "confidence": 0.95, "writable": True},
            "speed": {"target_name": "Maybe Speed", "confidence": 0.40, "writable": True},
        },
    }
    plan = mod.build_chain_plan(
        classification,
        pitch,
        adapter,
        user_goal_allows_pitch=True,
        force_full_mix_experiment=False,
    )

    assert plan["apply"] is False
    assert plan["fixed_parameter_indexes_required"] is False
    assert plan["unknown_parameters_are_skipped"] is True
    assert "SEMANTIC_CONTROL_MISSING" in plan["safety_gate"]["reason_codes"]


def test_ab_difference_metrics_and_human_report_are_created() -> None:
    mod = load_analyzer()
    original = vibrato_vocal()
    processed = [sample * 0.85 for sample in original]
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        original_path = tmp_path / "original.wav"
        processed_path = tmp_path / "processed.wav"
        write_wav(original_path, original)
        write_wav(processed_path, processed)
        outputs = mod.run_analysis(original_path, tmp_path / "automix", "AB Track", processed_path=processed_path)
        report = outputs["human_report"].read_text(encoding="utf-8")
        metrics_path = tmp_path / "automix/eval_reports/AB_Track_pitch_metrics.json"
        assert metrics_path.exists()
        metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
        assert Path(metrics["difference_path"]).exists()
        assert "difference_source_energy" in metrics
        assert "A/B Render Files" in report


def test_lua_applicator_is_draft_only_and_does_not_use_destructive_project_apis() -> None:
    text = LUA_APPLICATOR.read_text(encoding="utf-8")
    assert "allow_draft_pitch_correction = false" in text
    assert "_PITCH_DRAFT" in text
    assert "B_MUTE" in text
    assert "TrackFX_GetParamName" in text
    assert "TrackFX_SetParamNormalized" in text
    assert "TrackFX_SetParam(" not in text
    assert "TrackFX_SetPreset" not in text
    assert "Main_SaveProject" not in text
    assert "RenderFileSection" not in text
    assert "Main_OnCommand(40004" not in text
    assert "fixed parameter indexes" in text.lower()


def test_docs_explain_skip_autotune_and_isolated_stem_policy() -> None:
    combined = DOC.read_text(encoding="utf-8") + "\n" + RUNBOOK.read_text(encoding="utf-8")
    assert "For these sources, the safest pitch correction is often no pitch correction." in combined
    assert "Full mixes are not auto-tuned by default." in combined
    assert "When To Skip AutoTune" in combined
    assert "When To Request An Isolated Vocal Stem" in combined
    assert "original track remains untouched" in combined

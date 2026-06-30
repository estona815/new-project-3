from __future__ import annotations

import json
import math
from pathlib import Path

from VOCAL_CLARITY_REPAIR_SYSTEM.ml.model_output_contract import (
    ModelDomainStatus,
    ModelMetadata,
    ModelOutputType,
    ModelValidationStatus,
    SafetyConfig,
    band_max_suppression_db,
    db_to_gain,
    min_model_gain,
    postprocess_model_output,
)


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_JSON = ROOT / "VOCAL_CLARITY_REPAIR_SYSTEM/presets/model_output_contract_default.json"
REPORT = ROOT / "VOCAL_CLARITY_REPAIR_SYSTEM/docs/prompt6_ai_model_output_contract_report.md"
EVAL_TEMPLATE = ROOT / "VOCAL_CLARITY_REPAIR_SYSTEM/reports/model_output_evaluation_template.md"


def metadata(output_type: ModelOutputType, shape: tuple[int, ...] = (4,)) -> ModelMetadata:
    return ModelMetadata(
        version="test-v1",
        output_type=output_type,
        expected_sample_rate=48000,
        expected_channels=1,
        expected_output_shape=shape,
        normalization="unit-test",
    )


def test_unknown_model_output_type_is_rejected() -> None:
    result = postprocess_model_output(
        [0.5, 0.5, 0.5, 0.5],
        metadata(ModelOutputType.UNKNOWN),
        input_samples=[0.1, -0.1, 0.05, -0.05],
        sample_rate=48000,
        channels=1,
        dsp_noise_probability=0.25,
        freq_hz=4000.0,
    )

    assert result.status == ModelValidationStatus.UNKNOWN_OUTPUT_TYPE
    assert result.model_confidence == 0.0
    assert result.final_noise_probability == 0.25


def test_wrong_shape_and_nan_fall_back_to_dsp_probability() -> None:
    wrong_shape = postprocess_model_output(
        [0.1, 0.2],
        metadata(ModelOutputType.NOISE_PROBABILITY_MASK),
        input_samples=[0.1, 0.2, 0.1, 0.2],
        sample_rate=48000,
        channels=1,
        dsp_noise_probability=0.30,
        freq_hz=6000.0,
    )
    nan_output = postprocess_model_output(
        [0.1, float("nan"), 0.2, 0.3],
        metadata(ModelOutputType.NOISE_PROBABILITY_MASK),
        input_samples=[0.1, 0.2, 0.1, 0.2],
        sample_rate=48000,
        channels=1,
        dsp_noise_probability=0.30,
        freq_hz=6000.0,
    )

    assert wrong_shape.status == ModelValidationStatus.SHAPE_MISMATCH
    assert nan_output.status == ModelValidationStatus.NON_FINITE_OUTPUT
    assert wrong_shape.model_confidence == 0.0
    assert nan_output.model_confidence == 0.0
    assert math.isfinite(wrong_shape.gain)
    assert math.isfinite(nan_output.gain)


def test_gain_mask_is_advisory_and_cannot_mute_output() -> None:
    config = SafetyConfig()
    floor = min_model_gain(4000.0, config)
    result = postprocess_model_output(
        [0.0, 0.0, 0.0, 0.0],
        metadata(ModelOutputType.GAIN_MASK),
        input_samples=[0.2, -0.2, 0.1, -0.1],
        sample_rate=48000,
        channels=1,
        dsp_noise_probability=0.20,
        freq_hz=4000.0,
        config=config,
    )

    assert result.status == ModelValidationStatus.OK
    assert math.isclose(result.model_noise_probability, 1.0 - floor, rel_tol=1.0e-6)
    assert floor <= result.gain <= 1.0
    assert result.gain > 0.0


def test_noise_probability_uses_model_confidence_but_keeps_safety_caps() -> None:
    result = postprocess_model_output(
        [1.0, 0.9, 0.8, 0.7],
        metadata(ModelOutputType.NOISE_PROBABILITY_MASK),
        input_samples=[0.2, -0.2, 0.1, -0.1],
        sample_rate=48000,
        channels=1,
        dsp_noise_probability=0.10,
        freq_hz=12000.0,
        config=SafetyConfig(max_suppression_db=8.0, air_preserve=0.90),
    )

    assert 0.0 < result.model_confidence <= 1.0
    assert 0.10 < result.final_noise_probability <= 1.0
    assert db_to_gain(-3.0) <= result.gain <= 1.0


def test_residual_estimate_inside_budget_is_bounded_before_subtraction() -> None:
    result = postprocess_model_output(
        [0.02, -0.02, 0.02, -0.02],
        metadata(ModelOutputType.RESIDUAL_ESTIMATE),
        input_samples=[0.1, -0.1, 0.1, -0.1],
        sample_rate=48000,
        channels=1,
        dsp_noise_probability=0.10,
        freq_hz=3000.0,
    )

    assert result.status == ModelValidationStatus.OK
    assert result.processed_samples
    assert max(abs(v) for v in result.processed_samples) < 0.2


def test_suspicious_residual_estimate_uses_fallback() -> None:
    result = postprocess_model_output(
        [1.0, -1.0, 1.0, -1.0],
        metadata(ModelOutputType.RESIDUAL_ESTIMATE),
        input_samples=[0.1, -0.1, 0.1, -0.1],
        sample_rate=48000,
        channels=1,
        dsp_noise_probability=0.10,
        freq_hz=3000.0,
    )

    assert result.status == ModelValidationStatus.SUSPICIOUS_OUTPUT
    assert result.model_confidence == 0.0
    assert result.processed_samples == ()
    assert result.final_noise_probability == 0.10


def test_waveform_output_is_never_blindly_trusted() -> None:
    result = postprocess_model_output(
        [0.001, -0.001, 0.001, -0.001],
        metadata(ModelOutputType.WAVEFORM),
        input_samples=[0.2, -0.2, 0.2, -0.2],
        sample_rate=48000,
        channels=1,
        dsp_noise_probability=0.10,
        freq_hz=3000.0,
    )

    assert result.status == ModelValidationStatus.SUSPICIOUS_OUTPUT
    assert result.model_confidence == 0.0
    assert result.processed_samples == ()
    assert result.final_noise_probability == 0.10


def test_plausible_waveform_output_is_blended_not_replaced() -> None:
    result = postprocess_model_output(
        [0.18, -0.18, 0.18, -0.18],
        metadata(ModelOutputType.WAVEFORM),
        input_samples=[0.2, -0.2, 0.2, -0.2],
        sample_rate=48000,
        channels=1,
        dsp_noise_probability=0.10,
        freq_hz=3000.0,
    )

    assert result.status == ModelValidationStatus.OK
    assert 0.0 < result.model_confidence < 0.35
    assert result.processed_samples
    assert min(abs(v) for v in result.processed_samples) > 0.19


def test_magnitude_and_complex_outputs_are_high_risk_bounded_paths() -> None:
    magnitude = postprocess_model_output(
        [0.01, 0.01, 0.01, 0.01],
        metadata(ModelOutputType.MAGNITUDE_ESTIMATE),
        input_samples=[0.2, -0.2, 0.2, -0.2],
        sample_rate=48000,
        channels=1,
        dsp_noise_probability=0.15,
        freq_hz=5000.0,
    )
    complex_mask = postprocess_model_output(
        [0.0, 0.0, 0.1, 0.0],
        metadata(ModelOutputType.COMPLEX_MASK),
        input_samples=[0.2, -0.2, 0.2, -0.2],
        sample_rate=48000,
        channels=1,
        dsp_noise_probability=0.15,
        freq_hz=5000.0,
    )

    assert magnitude.status == ModelValidationStatus.OK
    assert complex_mask.status == ModelValidationStatus.OK
    assert magnitude.model_confidence < 0.85
    assert complex_mask.model_confidence < 0.85
    assert magnitude.gain > 0.0
    assert complex_mask.gain > 0.0


def test_prompt13_missing_ragged_extreme_and_negative_outputs_are_rejected() -> None:
    common = {
        "input_samples": [0.2, -0.2, 0.2, -0.2],
        "sample_rate": 48000,
        "channels": 1,
        "dsp_noise_probability": 0.15,
        "freq_hz": 5000.0,
    }
    missing = postprocess_model_output(None, metadata(ModelOutputType.NOISE_PROBABILITY_MASK), **common)
    ragged = postprocess_model_output([[0.1, 0.2], [0.3]], metadata(ModelOutputType.NOISE_PROBABILITY_MASK, (2, 2)), **common)
    extreme = postprocess_model_output([100.0, 0.2, 0.2, 0.2], metadata(ModelOutputType.NOISE_PROBABILITY_MASK), **common)
    negative_magnitude = postprocess_model_output([-0.1, 0.2, 0.2, 0.2], metadata(ModelOutputType.MAGNITUDE_ESTIMATE), **common)
    odd_complex = postprocess_model_output([0.1, 0.2, 0.3], metadata(ModelOutputType.COMPLEX_MASK, (3,)), **common)

    assert missing.status == ModelValidationStatus.EMPTY_OUTPUT
    assert ragged.status == ModelValidationStatus.SHAPE_MISMATCH
    assert extreme.status == ModelValidationStatus.SUSPICIOUS_OUTPUT
    assert negative_magnitude.status == ModelValidationStatus.SUSPICIOUS_OUTPUT
    assert odd_complex.status == ModelValidationStatus.SHAPE_MISMATCH
    for result in (missing, ragged, extreme, negative_magnitude, odd_complex):
        assert result.model_confidence == 0.0
        assert math.isfinite(result.gain)


def test_domain_mismatch_reduces_model_confidence() -> None:
    result = postprocess_model_output(
        [0.7, 0.7, 0.7, 0.7],
        metadata(ModelOutputType.NOISE_PROBABILITY_MASK),
        input_samples=[0.2, -0.2, 0.2, -0.2],
        sample_rate=44100,
        channels=1,
        dsp_noise_probability=0.10,
        freq_hz=4000.0,
    )

    assert result.domain_status == ModelDomainStatus.UNSUPPORTED_SAMPLE_RATE
    assert result.model_confidence <= 0.25


def test_silence_input_stays_conservative_and_finite() -> None:
    result = postprocess_model_output(
        [1.0, 1.0, 1.0, 1.0],
        metadata(ModelOutputType.NOISE_PROBABILITY_MASK),
        input_samples=[0.0, 0.0, 0.0, 0.0],
        sample_rate=48000,
        channels=1,
        dsp_noise_probability=0.0,
        freq_hz=4000.0,
    )

    assert result.domain_status == ModelDomainStatus.SILENCE
    assert result.model_confidence == 0.0
    assert result.final_noise_probability == 0.0
    assert result.gain == 1.0


def test_preservation_weights_reduce_presence_and_air_attenuation() -> None:
    loose = postprocess_model_output(
        [1.0, 0.9, 0.8, 0.7],
        metadata(ModelOutputType.NOISE_PROBABILITY_MASK),
        input_samples=[0.2, -0.2, 0.1, -0.1],
        sample_rate=48000,
        channels=1,
        dsp_noise_probability=0.20,
        freq_hz=4000.0,
        config=SafetyConfig(vocal_preserve=0.0, clarity_preserve=0.0, harmonic_preserve=0.0),
    )
    protected = postprocess_model_output(
        [1.0, 0.9, 0.8, 0.7],
        metadata(ModelOutputType.NOISE_PROBABILITY_MASK),
        input_samples=[0.2, -0.2, 0.1, -0.1],
        sample_rate=48000,
        channels=1,
        dsp_noise_probability=0.20,
        freq_hz=4000.0,
        config=SafetyConfig(vocal_preserve=0.90, clarity_preserve=0.90, harmonic_preserve=0.70),
    )

    assert protected.gain > loose.gain


def test_prompt6_contract_assets_cover_required_policy() -> None:
    contract = json.loads(CONTRACT_JSON.read_text(encoding="utf-8"))
    report = REPORT.read_text(encoding="utf-8")
    template = EVAL_TEMPLATE.read_text(encoding="utf-8")

    assert contract["schema"] == "codex-vocal-ai-model-output-contract-v1"
    assert contract["default_mode"] == "DSP Only"
    assert "Unknown" in contract["blocked_output_type_behavior"]
    assert "Direct waveform output is never sent directly to speakers." in contract["safety_contract"]
    assert "Current model output type in the plugin: **none / unknown**" in report
    assert "Model output is advisory only" in "\n".join(contract["safety_contract"])
    assert "Residual Source Leakage" in template
    assert "2 kHz to 8 kHz loses life: fail." in template

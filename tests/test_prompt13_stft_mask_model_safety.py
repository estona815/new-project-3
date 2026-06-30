from __future__ import annotations

import math
from pathlib import Path

from VOCAL_CLARITY_REPAIR_SYSTEM.ml.model_output_contract import (
    ModelMetadata,
    ModelOutputType,
    ModelValidationStatus,
    SafetyConfig,
    min_model_gain,
    postprocess_model_output,
)


ROOT = Path(__file__).resolve().parents[1]
SYSTEM = ROOT / "VOCAL_CLARITY_REPAIR_SYSTEM"
DOCS = SYSTEM / "docs"
JSFX = SYSTEM / "JSFX" / "vocal_ai_artifact_split_tamer.jsfx"


def metadata(output_type: ModelOutputType, shape: tuple[int, ...] = (4,)) -> ModelMetadata:
    return ModelMetadata(
        version="prompt13-test",
        output_type=output_type,
        expected_sample_rate=48000,
        expected_channels=1,
        expected_output_shape=shape,
        normalization="unit-test",
    )


def common_kwargs() -> dict[str, object]:
    return {
        "input_samples": [0.2, -0.2, 0.15, -0.15],
        "sample_rate": 48000,
        "channels": 1,
        "dsp_noise_probability": 0.20,
        "freq_hz": 4000.0,
        "config": SafetyConfig(),
    }


def test_prompt13_docs_map_actual_architecture_without_guessing_stft() -> None:
    text = (DOCS / "stft_mask_model_safety.md").read_text(encoding="utf-8")
    manual = (DOCS / "manual_test_plan_prompt13.md").read_text(encoding="utf-8")

    assert "STFT/FFT file: NOT FOUND in the active plugin path." in text
    assert "Model inference call: NOT FOUND." in text
    assert "Overlap-add/reconstruction file: active STFT overlap-add NOT FOUND" in text
    assert "Mask/gain calculation file: `VOCAL_CLARITY_REPAIR_SYSTEM/JSFX/vocal_ai_artifact_split_tamer.jsfx`" in text
    assert "Adding STFT would be a new denoise algorithm path" in text
    assert "Corrupt Model Output" in manual
    assert "not applicable in the active plugin because no model runtime exists" in manual


def test_jsfx_mask_equivalent_path_has_explicit_floor_and_collapse_constants() -> None:
    text = JSFX.read_text(encoding="utf-8")

    assert "mask_floor_ratio = 1.122018" in text
    assert "suspicious_drop_power_ratio = 0.0158489" in text
    assert "collapse_gain_floor = 0.398107" in text
    assert "mb_collapse_gain_floor = 0.50" in text
    assert "attack_gain <= attack_min_gain * mask_floor_ratio" in text
    assert "mb_avg_gain < mb_collapse_gain_floor" in text
    assert ") : (suspicious_drop || full_band_collapse) ? (" in text
    assert "target_wet *= 0.25;" not in text


def test_all_zero_gain_mask_is_floored_not_allowed_to_request_zero_gain() -> None:
    config = SafetyConfig(max_suppression_db=8.0)
    floor = min_model_gain(4000.0, config)
    result = postprocess_model_output(
        [0.0, 0.0, 0.0, 0.0],
        metadata(ModelOutputType.GAIN_MASK),
        **common_kwargs(),
    )

    assert result.status == ModelValidationStatus.OK
    assert math.isclose(result.model_noise_probability, 1.0 - floor, rel_tol=1.0e-6)
    assert floor <= result.gain <= 1.0
    assert math.isfinite(result.gain)


def test_model_shape_finite_and_range_validation_rejects_invalid_outputs() -> None:
    kwargs = common_kwargs()
    wrong_shape = postprocess_model_output([0.1, 0.2], metadata(ModelOutputType.NOISE_PROBABILITY_MASK), **kwargs)
    ragged = postprocess_model_output([[0.1, 0.2], [0.3]], metadata(ModelOutputType.NOISE_PROBABILITY_MASK, (2, 2)), **kwargs)
    missing = postprocess_model_output(None, metadata(ModelOutputType.NOISE_PROBABILITY_MASK), **kwargs)
    nan_output = postprocess_model_output([0.1, float("nan"), 0.2, 0.3], metadata(ModelOutputType.NOISE_PROBABILITY_MASK), **kwargs)
    extreme = postprocess_model_output([0.1, 100.0, 0.2, 0.3], metadata(ModelOutputType.NOISE_PROBABILITY_MASK), **kwargs)

    assert wrong_shape.status == ModelValidationStatus.SHAPE_MISMATCH
    assert ragged.status == ModelValidationStatus.SHAPE_MISMATCH
    assert missing.status == ModelValidationStatus.EMPTY_OUTPUT
    assert nan_output.status == ModelValidationStatus.NON_FINITE_OUTPUT
    assert extreme.status == ModelValidationStatus.SUSPICIOUS_OUTPUT
    for result in (wrong_shape, ragged, missing, nan_output, extreme):
        assert result.model_confidence == 0.0
        assert result.processed_samples == ()
        assert math.isfinite(result.gain)


def test_model_output_type_specific_suspicious_cases_fallback() -> None:
    kwargs = common_kwargs()
    residual = postprocess_model_output([1.0, -1.0, 1.0, -1.0], metadata(ModelOutputType.RESIDUAL_ESTIMATE), **kwargs)
    negative_magnitude = postprocess_model_output([-0.1, 0.2, 0.2, 0.2], metadata(ModelOutputType.MAGNITUDE_ESTIMATE), **kwargs)
    odd_complex = postprocess_model_output([0.1, 0.2, 0.3], metadata(ModelOutputType.COMPLEX_MASK, (3,)), **kwargs)
    waveform = postprocess_model_output([0.001, -0.001, 0.001, -0.001], metadata(ModelOutputType.WAVEFORM), **kwargs)

    assert residual.status == ModelValidationStatus.SUSPICIOUS_OUTPUT
    assert negative_magnitude.status == ModelValidationStatus.SUSPICIOUS_OUTPUT
    assert odd_complex.status == ModelValidationStatus.SHAPE_MISMATCH
    assert waveform.status == ModelValidationStatus.SUSPICIOUS_OUTPUT
    for result in (residual, negative_magnitude, odd_complex, waveform):
        assert result.model_confidence == 0.0
        assert result.final_noise_probability == 0.20
        assert math.isfinite(result.gain)


def test_unknown_output_type_remains_invalid_and_silence_stays_silence() -> None:
    unknown = postprocess_model_output(
        [0.5, 0.5, 0.5, 0.5],
        metadata(ModelOutputType.UNKNOWN),
        **common_kwargs(),
    )
    silence = postprocess_model_output(
        [1.0, 1.0, 1.0, 1.0],
        metadata(ModelOutputType.NOISE_PROBABILITY_MASK),
        input_samples=[0.0, 0.0, 0.0, 0.0],
        sample_rate=48000,
        channels=1,
        dsp_noise_probability=0.0,
        freq_hz=4000.0,
    )

    assert unknown.status == ModelValidationStatus.UNKNOWN_OUTPUT_TYPE
    assert unknown.model_confidence == 0.0
    assert silence.final_noise_probability == 0.0
    assert silence.gain == 1.0
    assert math.isfinite(silence.gain)

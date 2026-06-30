from __future__ import annotations

import math
from pathlib import Path

from VOCAL_CLARITY_REPAIR_SYSTEM.ml.model_output_contract import (
    ModelMetadata,
    ModelOutputType,
    SafetyConfig,
    apply_full_band_collapse_guard,
    band_max_suppression_db,
    compute_conservative_denoise_gain,
    compute_soft_noise_probability,
    conservative_spectral_subtraction_gain,
    db_to_gain,
    map_amount,
    min_model_gain,
    postprocess_model_output,
)


ROOT = Path(__file__).resolve().parents[1]
SYSTEM = ROOT / "VOCAL_CLARITY_REPAIR_SYSTEM"
JSFX = SYSTEM / "JSFX" / "vocal_ai_artifact_split_tamer.jsfx"
DOCS = SYSTEM / "docs"


def metadata(output_type: ModelOutputType, shape: tuple[int, ...] = (4,)) -> ModelMetadata:
    return ModelMetadata(
        version="prompt14-test",
        output_type=output_type,
        expected_sample_rate=48000,
        expected_channels=1,
        expected_output_shape=shape,
        normalization="unit-test",
    )


def test_prompt14_docs_describe_actual_soft_mask_scope() -> None:
    text = (DOCS / "conservative_soft_mask.md").read_text(encoding="utf-8")

    assert "mask/gain calculation file" in text
    assert "vocal_ai_artifact_split_tamer.jsfx" in text
    assert "spectral subtraction path: NOT FOUND" in text
    assert "STFT reconstruction file: NOT FOUND" in text
    assert "No EQ boost, high shelf, exciter" in text
    assert "Prompt 14 does not add VocalPreserve" in text


def test_jsfx_uses_conservative_soft_mask_caps_without_hard_zeroing() -> None:
    text = JSFX.read_text(encoding="utf-8")

    assert "presence_soft_cap_db = 4;" in text
    assert "air_soft_cap_db = 3;" in text
    assert "attack_band_max_db = min(max_reduction_db, presence_soft_cap_db);" in text
    assert "fizz_band_max_db = min(max_reduction_db, air_soft_cap_db);" in text
    assert "attack_prob = 1 / (1 + exp(-attack_x));" in text
    assert "attack_att_db = sample_attack_band_max_db * attack_prob * snap_mapped_amount * snap_mask_strength" in text
    assert "full_band_floor_count_limit = 2;" in text
    assert "full_band_mask_floor = near_floor_count >= full_band_floor_count_limit;" in text
    assert "target_wet *= 0.25;" not in text
    gain_slice = text[text.index("attack_raw_gain =") : text.index("body_gain =")]
    for token in ("attack_gain = 0;", "sandy_gain = 0;", "fizz_gain = 0;", "air_gain = 0;"):
        assert token not in gain_slice


def test_soft_noise_probability_is_smooth_and_knee_controlled() -> None:
    low_snr = compute_soft_noise_probability(-20.0, 0.0, 9.0)
    at_threshold = compute_soft_noise_probability(0.0, 0.0, 9.0)
    high_snr = compute_soft_noise_probability(20.0, 0.0, 9.0)
    narrow_delta = compute_soft_noise_probability(-6.0, 0.0, 3.0) - compute_soft_noise_probability(6.0, 0.0, 3.0)
    wide_delta = compute_soft_noise_probability(-6.0, 0.0, 12.0) - compute_soft_noise_probability(6.0, 0.0, 12.0)

    assert 0.0 <= high_snr < at_threshold < low_snr <= 1.0
    assert math.isclose(at_threshold, 0.5, rel_tol=1.0e-6)
    assert narrow_delta > wide_delta
    assert math.isfinite(compute_soft_noise_probability(float("nan"), 0.0, 0.0))


def test_amount_mask_strength_and_frequency_caps_bound_gain() -> None:
    floor_4k = db_to_gain(-band_max_suppression_db(4000.0, 8.0))
    no_amount = compute_conservative_denoise_gain(0.1, 1.0, freq_hz=4000.0, amount=0.0, mask_strength=1.0)
    no_strength = compute_conservative_denoise_gain(0.1, 1.0, freq_hz=4000.0, amount=1.0, mask_strength=0.0)
    strong = compute_conservative_denoise_gain(0.1, 1.0, freq_hz=4000.0, amount=1.0, mask_strength=1.0)
    low = compute_conservative_denoise_gain(0.1, 1.0, freq_hz=100.0, amount=1.0, mask_strength=1.0, max_suppression_db=24.0)
    presence = compute_conservative_denoise_gain(0.1, 1.0, freq_hz=4000.0, amount=1.0, mask_strength=1.0, max_suppression_db=24.0)
    air = compute_conservative_denoise_gain(0.1, 1.0, freq_hz=12000.0, amount=1.0, mask_strength=1.0, max_suppression_db=24.0)

    assert map_amount(0.0) == 0.0
    assert 0.32 < map_amount(0.5) < 0.34
    assert map_amount(1.0) == 1.0
    assert no_amount == 1.0
    assert no_strength == 1.0
    assert floor_4k <= strong <= 1.0
    assert low < presence < air
    assert band_max_suppression_db(100.0, 24.0) == 10.0
    assert band_max_suppression_db(4000.0, 24.0) == 4.0
    assert band_max_suppression_db(12000.0, 24.0) == 3.0


def test_model_mask_is_converted_to_bounded_attenuation_intent() -> None:
    config = SafetyConfig(amount=1.0, mask_strength=1.0, max_suppression_db=8.0)
    floor = min_model_gain(4000.0, config)
    gain_mask = postprocess_model_output(
        [0.0, 0.0, 0.0, 0.0],
        metadata(ModelOutputType.GAIN_MASK),
        input_samples=[0.2, -0.2, 0.2, -0.2],
        sample_rate=48000,
        channels=1,
        dsp_noise_probability=0.0,
        freq_hz=4000.0,
        config=config,
    )
    probability_mask = postprocess_model_output(
        [1.0, 1.0, 1.0, 1.0],
        metadata(ModelOutputType.NOISE_PROBABILITY_MASK),
        input_samples=[0.2, -0.2, 0.2, -0.2],
        sample_rate=48000,
        channels=1,
        dsp_noise_probability=0.0,
        freq_hz=12000.0,
        config=config,
    )

    assert gain_mask.gain >= floor
    assert gain_mask.gain > 0.0
    assert probability_mask.gain >= db_to_gain(-3.0)
    assert probability_mask.gain <= 1.0


def test_spectral_subtraction_gain_cannot_go_negative_or_below_floor() -> None:
    floor = db_to_gain(-band_max_suppression_db(4000.0, 8.0))
    silence = conservative_spectral_subtraction_gain(0.0, 100.0, freq_hz=4000.0, amount=1.0, mask_strength=1.0)
    heavy_noise = conservative_spectral_subtraction_gain(0.1, 10.0, freq_hz=4000.0, amount=1.0, mask_strength=1.0)
    no_amount = conservative_spectral_subtraction_gain(0.1, 10.0, freq_hz=4000.0, amount=0.0, mask_strength=1.0)

    assert silence == 1.0
    assert floor <= heavy_noise <= 1.0
    assert no_amount == 1.0
    assert math.isfinite(heavy_noise)


def test_full_band_collapse_guard_blends_floor_gains_toward_dry() -> None:
    floor = db_to_gain(-8.0)
    collapsed = [floor, floor * 1.01, floor * 1.02, floor]
    guarded = apply_full_band_collapse_guard(collapsed, [floor] * 4, active=True, max_floor_fraction=0.70)
    inactive = apply_full_band_collapse_guard(collapsed, [floor] * 4, active=False, max_floor_fraction=0.70)

    assert all(g > c for g, c in zip(guarded, collapsed))
    assert all(floor <= g <= 1.0 for g in guarded)
    assert inactive == tuple(collapsed)

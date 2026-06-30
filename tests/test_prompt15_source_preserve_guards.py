from __future__ import annotations

import math
from pathlib import Path

from VOCAL_CLARITY_REPAIR_SYSTEM.ml.model_output_contract import (
    ModelMetadata,
    ModelOutputType,
    SafetyConfig,
    apply_air_loss_guard,
    apply_harmonic_preserve_to_suppression_limit,
    apply_source_preserve_to_suppression_limit,
    apply_tilt_darkening_guard,
    apply_transient_preserve_to_suppression_limit,
    band_max_suppression_db,
    compute_conservative_denoise_gain,
    compute_source_preserved_denoise_gain,
    conservative_spectral_subtraction_gain,
    db_to_gain,
    get_air_weight,
    get_clarity_weight,
    get_vocal_presence_weight,
    is_near_harmonic,
    min_model_gain,
    postprocess_model_output,
    protected_suppression_limit_db,
)


ROOT = Path(__file__).resolve().parents[1]
SYSTEM = ROOT / "VOCAL_CLARITY_REPAIR_SYSTEM"
JSFX = SYSTEM / "JSFX" / "vocal_ai_artifact_split_tamer.jsfx"
DOCS = SYSTEM / "docs"


def metadata(output_type: ModelOutputType, shape: tuple[int, ...] = (4,)) -> ModelMetadata:
    return ModelMetadata(
        version="prompt15-test",
        output_type=output_type,
        expected_sample_rate=48000,
        expected_channels=1,
        expected_output_shape=shape,
        normalization="unit-test",
    )


def test_preserve_parameters_exist_with_high_defaults_and_snapshots() -> None:
    text = JSFX.read_text(encoding="utf-8")
    filterbank = text.index("mono = 0.5 * (in_l + in_r);")

    assert "slider16:0.85<0,1,0.01>Vocal Preserve" in text
    assert "slider17:0.85<0,1,0.01>Clarity Preserve" in text
    assert "slider18:0.80<0,1,0.01>Air Preserve" in text
    assert "slider19:0.80<0,1,0.01>Transient Preserve" in text
    assert "harmonic_preserve = 0.75;" in text

    for token in (
        "snap_vocal_preserve = max(0, min(vocal_preserve, 1));",
        "snap_clarity_preserve = max(0, min(clarity_preserve, 1));",
        "snap_air_preserve = max(0, min(air_preserve, 1));",
        "snap_transient_preserve = max(0, min(transient_preserve, 1));",
        "snap_harmonic_preserve = max(0, min(harmonic_preserve, 1));",
        "snap_mid_preserve = max(0, min(mid_preserve, 1));",
    ):
        assert token in text
        assert text.index(token) < filterbank


def test_frequency_preserve_weights_are_finite_bounded_and_targeted() -> None:
    for fn in (get_vocal_presence_weight, get_clarity_weight, get_air_weight):
        for freq in (float("nan"), float("inf"), -100.0, 0.0, 100.0, 3500.0, 6000.0, 12000.0):
            weight = fn(freq)
            assert math.isfinite(weight)
            assert 0.0 <= weight <= 1.0

    assert get_vocal_presence_weight(3500.0) > 0.95
    assert get_vocal_presence_weight(900.0) == 0.0
    assert get_clarity_weight(6000.0) > 0.95
    assert get_clarity_weight(1200.0) == 0.0
    assert get_air_weight(12000.0) > 0.95
    assert get_air_weight(4000.0) == 0.0


def test_source_preserve_reduces_suppression_without_boosting() -> None:
    loose = SafetyConfig(
        amount=1.0,
        mask_strength=1.0,
        max_suppression_db=8.0,
        vocal_preserve=0.0,
        clarity_preserve=0.0,
        air_preserve=0.0,
        transient_preserve=0.0,
        harmonic_preserve=0.0,
    )
    protected = SafetyConfig(amount=1.0, mask_strength=1.0, max_suppression_db=8.0)

    for freq in (3500.0, 6000.0, 12000.0):
        raw_limit = band_max_suppression_db(freq, 8.0)
        protected_limit = apply_source_preserve_to_suppression_limit(raw_limit, freq, protected)
        assert 0.0 <= protected_limit < raw_limit
        assert db_to_gain(-protected_limit) <= 1.0

    assert compute_source_preserved_denoise_gain(0.1, 1.0, freq_hz=3500.0, config=protected) > compute_source_preserved_denoise_gain(0.1, 1.0, freq_hz=3500.0, config=loose)
    assert compute_source_preserved_denoise_gain(0.1, 1.0, freq_hz=6000.0, config=protected) > compute_source_preserved_denoise_gain(0.1, 1.0, freq_hz=6000.0, config=loose)
    assert compute_source_preserved_denoise_gain(0.1, 1.0, freq_hz=12000.0, config=protected) > compute_source_preserved_denoise_gain(0.1, 1.0, freq_hz=12000.0, config=loose)
    assert math.isclose(
        compute_source_preserved_denoise_gain(0.1, 1.0, freq_hz=3500.0, config=loose),
        compute_conservative_denoise_gain(0.1, 1.0, freq_hz=3500.0, amount=1.0, mask_strength=1.0),
        rel_tol=1.0e-9,
    )


def test_transient_and_harmonic_guards_only_reduce_attenuation_limits() -> None:
    steady = apply_transient_preserve_to_suppression_limit(4.0, 0.0, 0.80, freq_hz=4000.0)
    transient = apply_transient_preserve_to_suppression_limit(4.0, 1.0, 0.80, freq_hz=4000.0)
    low_freq_transient = apply_transient_preserve_to_suppression_limit(4.0, 1.0, 0.80, freq_hz=300.0)

    assert 0.0 <= transient < low_freq_transient < steady <= 4.0
    assert is_near_harmonic(1320.0, 440.0)
    assert not is_near_harmonic(1375.0, 440.0)
    assert not is_near_harmonic(1320.0, None)
    assert not is_near_harmonic(1320.0, 30.0)

    harmonic = apply_harmonic_preserve_to_suppression_limit(4.0, 1320.0, 440.0, 0.75)
    non_harmonic = apply_harmonic_preserve_to_suppression_limit(4.0, 1375.0, 440.0, 0.75)
    assert 0.0 <= harmonic < non_harmonic == 4.0


def test_model_and_spectral_subtraction_paths_cannot_bypass_preserve_floors() -> None:
    config = SafetyConfig(amount=1.0, mask_strength=1.0, max_suppression_db=8.0)
    raw_floor = db_to_gain(-band_max_suppression_db(3500.0, 8.0))
    protected_floor = min_model_gain(3500.0, config)
    assert protected_floor > raw_floor

    result = postprocess_model_output(
        [0.0, 0.0, 0.0, 0.0],
        metadata(ModelOutputType.GAIN_MASK),
        input_samples=[0.2, -0.2, 0.2, -0.2],
        sample_rate=48000,
        channels=1,
        dsp_noise_probability=0.0,
        freq_hz=3500.0,
        config=config,
    )
    assert result.gain >= protected_floor
    assert math.isclose(result.model_noise_probability, 1.0 - protected_floor, rel_tol=1.0e-6)

    raw_subtraction = conservative_spectral_subtraction_gain(
        0.1,
        10.0,
        freq_hz=3500.0,
        amount=1.0,
        mask_strength=1.0,
        max_suppression_db=8.0,
    )
    protected_subtraction = conservative_spectral_subtraction_gain(
        0.1,
        10.0,
        freq_hz=3500.0,
        config=config,
    )
    assert protected_subtraction > raw_subtraction


def test_tilt_and_air_guards_blend_over_reduced_bands_toward_dry() -> None:
    freqs = (500.0, 3000.0, 6000.0, 12000.0)
    mags = (1.0, 1.0, 1.0, 1.0)
    gains = (0.80, 0.30, 0.30, 0.30)

    tilt_guarded = apply_tilt_darkening_guard(gains, freqs, mags)
    assert tilt_guarded[0] == gains[0]
    assert gains[1] < tilt_guarded[1] <= 1.0
    assert gains[2] < tilt_guarded[2] <= 1.0
    assert tilt_guarded[3] == gains[3]

    air_guarded = apply_air_loss_guard(gains, freqs, mags, sample_rate=48000.0)
    assert air_guarded[2] == gains[2]
    assert gains[3] < air_guarded[3] <= 1.0
    assert apply_air_loss_guard(gains, freqs, mags, sample_rate=16000.0) == gains
    assert apply_tilt_darkening_guard(gains, freqs, (0.0, 0.0, 0.0, 0.0)) == gains


def test_jsfx_contains_transient_tilt_air_and_no_fake_boost_path() -> None:
    text = JSFX.read_text(encoding="utf-8")
    lowered = text.lower()

    assert "transient_score = max(0, min(1, 0.6 * flux_norm + 0.4 * energy_rise_norm));" in text
    assert "transient_guard = max(0.25, min(1, 1 - 0.75 * snap_transient_preserve * transient_score_sm));" in text
    assert "sample_attack_band_max_db *= max(0.25" in text
    assert "tilt_loss_db = input_tilt_db - output_tilt_db;" in text
    assert "air_loss_db = 8.685889638065037 * log(air_in / air_out_est);" in text
    assert "attack_gain += (1 - attack_gain)" in text
    assert "air_gain += (1 - air_gain)" in text
    for blocked in ("exciter", "air boost", "clarity boost"):
        assert blocked not in lowered


def test_prompt15_documentation_records_active_and_deferred_scope() -> None:
    source_doc = (DOCS / "source_preserve_guards.md").read_text(encoding="utf-8")
    harmonic_doc = (DOCS / "harmonic_preserve_deferred.md").read_text(encoding="utf-8")

    assert "VocalPreserve" in source_doc
    assert "ClarityPreserve" in source_doc
    assert "AirPreserve" in source_doc
    assert "TransientPreserve" in source_doc
    assert "frequency preserve weights" in source_doc
    assert "spectral tilt" in source_doc
    assert "air loss" in source_doc
    assert "full F0 harmonic tracking is deferred" in harmonic_doc
    assert "no heavy pitch tracking" in harmonic_doc

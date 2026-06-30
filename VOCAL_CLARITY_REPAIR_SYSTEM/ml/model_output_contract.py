from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import math
from typing import Any, Iterable


class ModelOutputType(Enum):
    UNKNOWN = "unknown"
    GAIN_MASK = "gain_mask"
    NOISE_PROBABILITY_MASK = "noise_probability_mask"
    RESIDUAL_ESTIMATE = "residual_estimate"
    MAGNITUDE_ESTIMATE = "magnitude_estimate"
    COMPLEX_MASK = "complex_mask"
    WAVEFORM = "waveform"


class ModelDomainStatus(Enum):
    OK = "ok"
    SILENCE = "silence"
    TOO_QUIET = "too_quiet"
    CLIPPED = "clipped"
    UNSUPPORTED_SAMPLE_RATE = "unsupported_sample_rate"
    UNSUPPORTED_CHANNELS = "unsupported_channels"
    OUT_OF_DISTRIBUTION_SUSPECTED = "out_of_distribution_suspected"


class ModelValidationStatus(Enum):
    OK = "ok"
    UNKNOWN_OUTPUT_TYPE = "unknown_output_type"
    SHAPE_MISMATCH = "shape_mismatch"
    NON_FINITE_OUTPUT = "non_finite_output"
    EMPTY_OUTPUT = "empty_output"
    SUSPICIOUS_OUTPUT = "suspicious_output"
    DRY_FALLBACK = "dry_fallback"


@dataclass(frozen=True)
class ModelMetadata:
    version: str
    output_type: ModelOutputType
    expected_sample_rate: int = 48000
    expected_channels: int = 1
    expected_input_shape: tuple[int, ...] = field(default_factory=tuple)
    expected_output_shape: tuple[int, ...] = field(default_factory=tuple)
    normalization: str = "unknown"
    latency_samples: int = 0
    dataset_version: str = "unknown"


@dataclass(frozen=True)
class SafetyConfig:
    amount: float = 0.30
    mask_strength: float = 0.35
    max_suppression_db: float = 8.0
    model_blend: float = 0.50
    vocal_preserve: float = 0.85
    clarity_preserve: float = 0.85
    air_preserve: float = 0.80
    transient_preserve: float = 0.80
    harmonic_preserve: float = 0.70
    transient_score: float = 0.0
    max_residual_rms_ratio: float = 0.50
    max_waveform_rms_ratio: float = 1.50
    min_waveform_rms_ratio: float = 0.25
    max_abs_model_value: float = 32.0


@dataclass(frozen=True)
class DomainCheck:
    status: ModelDomainStatus
    confidence_scale: float
    reason: str


@dataclass(frozen=True)
class ModelPostprocessResult:
    status: ModelValidationStatus
    output_type: ModelOutputType
    model_confidence: float
    domain_status: ModelDomainStatus
    model_noise_probability: float
    dsp_noise_probability: float
    final_noise_probability: float
    gain: float
    processed_samples: tuple[float, ...] = field(default_factory=tuple)
    reason: str = ""


def clamp(value: float, low: float, high: float) -> float:
    if not math.isfinite(value):
        return low
    return max(low, min(high, value))


def db_to_gain(db: float) -> float:
    return math.exp(db * 0.1151292546497023)


def map_amount(amount: float) -> float:
    return clamp(amount, 0.0, 1.0) ** 1.6


def compute_soft_noise_probability(snr_db: float, threshold_db: float, knee_db: float) -> float:
    safe_snr = clamp(snr_db, -160.0, 160.0)
    safe_threshold = clamp(threshold_db, -160.0, 160.0)
    safe_knee = max(clamp(knee_db, 0.001, 60.0), 0.001)
    x = clamp((safe_threshold - safe_snr) / safe_knee, -40.0, 40.0)
    return clamp(1.0 / (1.0 + math.exp(-x)), 0.0, 1.0)


def rms(values: Iterable[float]) -> float:
    vals = tuple(float(v) for v in values)
    if not vals:
        return 0.0
    return math.sqrt(sum(v * v for v in vals) / len(vals))


def infer_shape(value: Any) -> tuple[int, ...]:
    if isinstance(value, (str, bytes)):
        return ()
    if isinstance(value, (list, tuple)):
        if not value:
            return (0,)
        return (len(value),) + infer_shape(value[0])
    return ()


def flatten_numeric(value: Any) -> tuple[float, ...]:
    out: list[float] = []

    def walk(node: Any) -> None:
        if isinstance(node, (str, bytes)):
            raise TypeError("non-numeric tensor element")
        if isinstance(node, (list, tuple)):
            for item in node:
                walk(item)
        else:
            out.append(float(node))

    walk(value)
    return tuple(out)


def shape_matches(actual: tuple[int, ...], expected: tuple[int, ...]) -> bool:
    if not expected:
        return True
    if len(actual) != len(expected):
        return False
    return all(e < 0 or a == e for a, e in zip(actual, expected))


def is_rectangular_tensor(value: Any) -> bool:
    if isinstance(value, (str, bytes)) or not isinstance(value, (list, tuple)):
        return True
    if not value:
        return True
    first_shape = infer_shape(value[0])
    return all(infer_shape(item) == first_shape and is_rectangular_tensor(item) for item in value)


def band_max_suppression_db(freq_hz: float, global_max_db: float) -> float:
    global_max_db = clamp(global_max_db, 0.0, 24.0)
    if freq_hz < 120.0:
        return min(global_max_db, 10.0)
    if freq_hz < 1000.0:
        return min(global_max_db, 8.0)
    if freq_hz < 2000.0:
        return min(global_max_db, 6.0)
    if freq_hz < 8000.0:
        return min(global_max_db, 4.0)
    return min(global_max_db, 3.0)


def get_vocal_presence_weight(freq_hz: float) -> float:
    if not math.isfinite(freq_hz) or freq_hz <= 0.0:
        return 0.0
    if freq_hz < 1800.0 or freq_hz > 5500.0:
        return 0.0
    octave_distance = abs(math.log2(freq_hz / 3500.0))
    weight = math.exp(-((octave_distance * octave_distance) / 0.75))
    return clamp(weight, 0.0, 1.0)


def get_clarity_weight(freq_hz: float) -> float:
    if not math.isfinite(freq_hz) or freq_hz <= 0.0:
        return 0.0
    if freq_hz < 3500.0 or freq_hz > 8500.0:
        return 0.0
    octave_distance = abs(math.log2(freq_hz / 6000.0))
    weight = math.exp(-((octave_distance * octave_distance) / 0.80))
    return clamp(weight, 0.0, 1.0)


def get_air_weight(freq_hz: float) -> float:
    if not math.isfinite(freq_hz) or freq_hz <= 0.0:
        return 0.0
    if freq_hz < 8000.0 or freq_hz > 18000.0:
        return 0.0
    octave_distance = abs(math.log2(freq_hz / 12000.0))
    weight = math.exp(-((octave_distance * octave_distance) / 1.20))
    return clamp(weight, 0.0, 1.0)


def apply_source_preserve_to_suppression_limit(
    band_limit_db: float,
    freq_hz: float,
    config: SafetyConfig,
) -> float:
    vocal_w = get_vocal_presence_weight(freq_hz)
    clarity_w = get_clarity_weight(freq_hz)
    air_w = get_air_weight(freq_hz)

    protection = 1.0
    protection *= 1.0 - 0.65 * clamp(config.vocal_preserve, 0.0, 1.0) * vocal_w
    protection *= 1.0 - 0.55 * clamp(config.clarity_preserve, 0.0, 1.0) * clarity_w
    protection *= 1.0 - 0.50 * clamp(config.air_preserve, 0.0, 1.0) * air_w
    protection = clamp(protection, 0.25, 1.0)
    return max(0.0, clamp(band_limit_db, 0.0, 24.0) * protection)


def apply_transient_preserve_to_suppression_limit(
    limit_db: float,
    transient_score: float,
    transient_preserve: float,
    *,
    freq_hz: float | None = None,
) -> float:
    t = clamp(transient_score, 0.0, 1.0)
    p = clamp(transient_preserve, 0.0, 1.0)
    multiplier = 1.0
    if freq_hz is not None and math.isfinite(freq_hz) and freq_hz <= 1000.0:
        multiplier = 0.5
    protection = 1.0 - 0.75 * p * t * multiplier
    return clamp(limit_db, 0.0, 24.0) * clamp(protection, 0.25, 1.0)


def is_near_harmonic(freq_hz: float, estimated_f0: float | None) -> bool:
    if estimated_f0 is None:
        return False
    if not math.isfinite(freq_hz) or not math.isfinite(estimated_f0):
        return False
    if freq_hz <= 0.0 or estimated_f0 < 50.0 or estimated_f0 > 1000.0:
        return False
    harmonic_index = round(freq_hz / estimated_f0)
    if harmonic_index < 1:
        return False
    harmonic_hz = harmonic_index * estimated_f0
    tolerance_hz = max(20.0, harmonic_hz * 0.015)
    return abs(freq_hz - harmonic_hz) <= tolerance_hz


def apply_harmonic_preserve_to_suppression_limit(
    limit_db: float,
    freq_hz: float,
    estimated_f0: float | None,
    harmonic_preserve: float,
) -> float:
    safe_limit = clamp(limit_db, 0.0, 24.0)
    if not is_near_harmonic(freq_hz, estimated_f0):
        return safe_limit
    protection = 1.0 - 0.55 * clamp(harmonic_preserve, 0.0, 1.0)
    return safe_limit * clamp(protection, 0.25, 1.0)


def protected_suppression_limit_db(
    freq_hz: float,
    config: SafetyConfig,
    *,
    estimated_f0: float | None = None,
) -> float:
    limit = band_max_suppression_db(freq_hz, config.max_suppression_db)
    limit = apply_source_preserve_to_suppression_limit(limit, freq_hz, config)
    limit = apply_transient_preserve_to_suppression_limit(
        limit,
        config.transient_score,
        config.transient_preserve,
        freq_hz=freq_hz,
    )
    limit = apply_harmonic_preserve_to_suppression_limit(
        limit,
        freq_hz,
        estimated_f0,
        config.harmonic_preserve,
    )
    return clamp(limit, 0.0, 24.0)


def source_protection(freq_hz: float, config: SafetyConfig) -> float:
    protect = 0.25 * config.harmonic_preserve
    if 2000.0 <= freq_hz < 5000.0:
        protect += 0.45 * config.vocal_preserve + 0.35 * config.clarity_preserve
    elif 5000.0 <= freq_hz < 8000.0:
        protect += 0.50 * config.clarity_preserve + 0.20 * config.vocal_preserve
    elif freq_hz >= 8000.0:
        protect += 0.65 * config.air_preserve + 0.20 * config.clarity_preserve
    else:
        protect += 0.35 * config.vocal_preserve
    protect += 0.40 * config.transient_preserve * clamp(config.transient_score, 0.0, 1.0)
    return clamp(protect, 0.0, 0.95)


def bounded_gain_from_probability(noise_probability: float, freq_hz: float, config: SafetyConfig) -> float:
    protected_limit_db = protected_suppression_limit_db(freq_hz, config)
    attenuation_db = (
        protected_limit_db
        * clamp(noise_probability, 0.0, 1.0)
        * map_amount(config.amount)
        * clamp(config.mask_strength, 0.0, 1.0)
    )
    return clamp(db_to_gain(-attenuation_db), db_to_gain(-protected_limit_db), 1.0)


def compute_conservative_denoise_gain(
    magnitude: float,
    noise_magnitude: float,
    *,
    freq_hz: float,
    threshold_db: float = 0.0,
    knee_db: float = 9.0,
    amount: float = 0.30,
    mask_strength: float = 0.35,
    max_suppression_db: float = 8.0,
) -> float:
    mag = max(clamp(magnitude, 0.0, 1.0e12), 1.0e-8)
    noise = max(clamp(noise_magnitude, 0.0, 1.0e12), 1.0e-8)
    ratio = max(mag / noise, 1.0e-8)
    snr_db = 20.0 * math.log10(ratio)
    band_max_db = band_max_suppression_db(freq_hz, max_suppression_db)
    noise_prob = compute_soft_noise_probability(snr_db, threshold_db, knee_db)
    attenuation_db = band_max_db * noise_prob * map_amount(amount) * clamp(mask_strength, 0.0, 1.0)
    return clamp(db_to_gain(-attenuation_db), db_to_gain(-band_max_db), 1.0)


def compute_source_preserved_denoise_gain(
    magnitude: float,
    noise_magnitude: float,
    *,
    freq_hz: float,
    threshold_db: float = 0.0,
    knee_db: float = 9.0,
    config: SafetyConfig = SafetyConfig(),
    estimated_f0: float | None = None,
) -> float:
    mag = max(clamp(magnitude, 0.0, 1.0e12), 1.0e-8)
    noise = max(clamp(noise_magnitude, 0.0, 1.0e12), 1.0e-8)
    ratio = max(mag / noise, 1.0e-8)
    snr_db = 20.0 * math.log10(ratio)
    limit_db = protected_suppression_limit_db(freq_hz, config, estimated_f0=estimated_f0)
    noise_prob = compute_soft_noise_probability(snr_db, threshold_db, knee_db)
    attenuation_db = limit_db * noise_prob * map_amount(config.amount) * clamp(config.mask_strength, 0.0, 1.0)
    return clamp(db_to_gain(-attenuation_db), db_to_gain(-limit_db), 1.0)


def conservative_spectral_subtraction_gain(
    input_magnitude: float,
    noise_magnitude: float,
    *,
    freq_hz: float,
    amount: float = 0.30,
    mask_strength: float = 0.35,
    max_suppression_db: float = 8.0,
    config: SafetyConfig | None = None,
    estimated_f0: float | None = None,
) -> float:
    input_mag = clamp(input_magnitude, 0.0, 1.0e12)
    if input_mag <= 1.0e-8:
        return 1.0
    noise_mag = clamp(noise_magnitude, 0.0, 1.0e12)
    if config is None:
        band_max_db = band_max_suppression_db(freq_hz, max_suppression_db)
        mapped = map_amount(amount)
        strength = clamp(mask_strength, 0.0, 1.0)
    else:
        band_max_db = protected_suppression_limit_db(freq_hz, config, estimated_f0=estimated_f0)
        mapped = map_amount(config.amount)
        strength = clamp(config.mask_strength, 0.0, 1.0)
    min_gain = db_to_gain(-band_max_db)
    raw_processed = input_mag - noise_mag * mapped * strength
    floored_processed = max(raw_processed, input_mag * min_gain, 0.0)
    effective_gain = floored_processed / max(input_mag, 1.0e-8)
    return clamp(effective_gain, min_gain, 1.0)


def apply_full_band_collapse_guard(
    gains: Iterable[float],
    min_gains: Iterable[float],
    *,
    active: bool,
    near_floor_ratio: float = 1.122018,
    max_floor_fraction: float = 0.70,
    blend_toward_dry: float = 0.35,
) -> tuple[float, ...]:
    safe_gains = tuple(clamp(v, 0.0, 1.0) for v in gains)
    safe_floors = tuple(clamp(v, 0.0, 1.0) for v in min_gains)
    if not safe_gains:
        return ()
    if len(safe_floors) != len(safe_gains):
        safe_floors = tuple(0.0 for _ in safe_gains)

    bounded = tuple(clamp(g, floor, 1.0) for g, floor in zip(safe_gains, safe_floors))
    if not active:
        return bounded

    near_count = sum(g <= floor * near_floor_ratio for g, floor in zip(bounded, safe_floors))
    if near_count / len(bounded) <= max_floor_fraction:
        return bounded

    blend = clamp(blend_toward_dry, 0.0, 1.0)
    return tuple(clamp(g + (1.0 - g) * blend, floor, 1.0) for g, floor in zip(bounded, safe_floors))


def apply_tilt_darkening_guard(
    gains: Iterable[float],
    freqs_hz: Iterable[float],
    input_magnitudes: Iterable[float],
    *,
    vocal_preserve: float = 0.85,
    clarity_preserve: float = 0.85,
    silence_threshold: float = 1.0e-10,
) -> tuple[float, ...]:
    safe_gains = tuple(clamp(v, 0.0, 1.0) for v in gains)
    freqs = tuple(float(v) for v in freqs_hz)
    mags = tuple(clamp(v, 0.0, 1.0e12) for v in input_magnitudes)
    if not safe_gains or len(safe_gains) != len(freqs) or len(safe_gains) != len(mags):
        return safe_gains
    if sum(mags) <= silence_threshold:
        return safe_gains

    low_mid_in = sum(m for f, m in zip(freqs, mags) if 200.0 <= f < 1000.0)
    presence_in = sum(m for f, m in zip(freqs, mags) if 2000.0 <= f < 8000.0)
    presence_out = sum(m * g for f, m, g in zip(freqs, mags, safe_gains) if 2000.0 <= f < 8000.0)
    if low_mid_in <= 1.0e-8 or presence_in <= 1.0e-8:
        return safe_gains

    input_tilt_db = 20.0 * math.log10(max(presence_in, 1.0e-8) / max(low_mid_in, 1.0e-8))
    output_tilt_db = 20.0 * math.log10(max(presence_out, 1.0e-8) / max(low_mid_in, 1.0e-8))
    tilt_loss_db = input_tilt_db - output_tilt_db
    guard = clamp((tilt_loss_db - 1.5) / 4.0, 0.0, 1.0)
    blend = 0.50 * guard * max(clamp(vocal_preserve, 0.0, 1.0), clamp(clarity_preserve, 0.0, 1.0))
    return tuple(
        clamp(g + (1.0 - g) * blend, 0.0, 1.0) if 2000.0 <= f < 8000.0 else g
        for f, g in zip(freqs, safe_gains)
    )


def apply_air_loss_guard(
    gains: Iterable[float],
    freqs_hz: Iterable[float],
    input_magnitudes: Iterable[float],
    *,
    sample_rate: float = 48000.0,
    air_preserve: float = 0.80,
    silence_threshold: float = 1.0e-10,
) -> tuple[float, ...]:
    safe_gains = tuple(clamp(v, 0.0, 1.0) for v in gains)
    freqs = tuple(float(v) for v in freqs_hz)
    mags = tuple(clamp(v, 0.0, 1.0e12) for v in input_magnitudes)
    if not safe_gains or len(safe_gains) != len(freqs) or len(safe_gains) != len(mags):
        return safe_gains
    if not math.isfinite(sample_rate) or sample_rate <= 0.0:
        return safe_gains
    nyquist = sample_rate * 0.5
    high_edge = min(16000.0, nyquist)
    if high_edge <= 8000.0 or sum(mags) <= silence_threshold:
        return safe_gains

    air_in = sum(m for f, m in zip(freqs, mags) if 8000.0 <= f <= high_edge)
    air_out = sum(m * g for f, m, g in zip(freqs, mags, safe_gains) if 8000.0 <= f <= high_edge)
    if air_in <= 1.0e-8:
        return safe_gains

    air_loss_db = 20.0 * math.log10(max(air_in, 1.0e-8) / max(air_out, 1.0e-8))
    guard = clamp((air_loss_db - 2.0) / 5.0, 0.0, 1.0)
    blend = 0.35 * guard * clamp(air_preserve, 0.0, 1.0)
    return tuple(
        clamp(g + (1.0 - g) * blend, 0.0, 1.0) if 8000.0 <= f <= high_edge else g
        for f, g in zip(freqs, safe_gains)
    )


def min_model_gain(freq_hz: float, config: SafetyConfig) -> float:
    return db_to_gain(-protected_suppression_limit_db(freq_hz, config))


def max_abs_model_value(config: SafetyConfig) -> float:
    if not math.isfinite(config.max_abs_model_value):
        return 32.0
    return clamp(config.max_abs_model_value, 1.0, 1.0e6)


def check_domain(
    input_samples: Iterable[float],
    sample_rate: int,
    channels: int,
    metadata: ModelMetadata,
) -> DomainCheck:
    samples = tuple(float(v) for v in input_samples)
    if any(not math.isfinite(v) for v in samples):
        return DomainCheck(ModelDomainStatus.OUT_OF_DISTRIBUTION_SUSPECTED, 0.0, "non-finite input")
    if sample_rate != metadata.expected_sample_rate:
        return DomainCheck(ModelDomainStatus.UNSUPPORTED_SAMPLE_RATE, 0.25, "sample rate mismatch")
    if channels != metadata.expected_channels:
        return DomainCheck(ModelDomainStatus.UNSUPPORTED_CHANNELS, 0.25, "channel count mismatch")
    if not samples or max(abs(v) for v in samples) <= 1.0e-8:
        return DomainCheck(ModelDomainStatus.SILENCE, 0.0, "silence")
    level = rms(samples)
    if level < 1.0e-5:
        return DomainCheck(ModelDomainStatus.TOO_QUIET, 0.20, "too quiet for reliable inference")
    if max(abs(v) for v in samples) >= 0.999:
        return DomainCheck(ModelDomainStatus.CLIPPED, 0.50, "clipped input")
    crest = max(abs(v) for v in samples) / max(level, 1.0e-8)
    if crest > 30.0:
        return DomainCheck(ModelDomainStatus.OUT_OF_DISTRIBUTION_SUSPECTED, 0.50, "extreme crest factor")
    return DomainCheck(ModelDomainStatus.OK, 1.0, "domain ok")


def _base_invalid(
    status: ModelValidationStatus,
    output_type: ModelOutputType,
    domain: DomainCheck,
    dsp_noise_probability: float,
    freq_hz: float,
    config: SafetyConfig,
    reason: str,
) -> ModelPostprocessResult:
    dsp_prob = clamp(dsp_noise_probability, 0.0, 1.0)
    return ModelPostprocessResult(
        status=status,
        output_type=output_type,
        model_confidence=0.0,
        domain_status=domain.status,
        model_noise_probability=0.0,
        dsp_noise_probability=dsp_prob,
        final_noise_probability=dsp_prob,
        gain=bounded_gain_from_probability(dsp_prob, freq_hz, config),
        reason=reason,
    )


def _confidence_from_values(values: tuple[float, ...], domain: DomainCheck) -> float:
    if not values:
        return 0.0
    mean = sum(values) / len(values)
    variance = sum((v - mean) ** 2 for v in values) / len(values)
    dynamic_range = max(values) - min(values)
    confidence = 0.85
    if dynamic_range < 0.02 or variance < 1.0e-5:
        confidence *= 0.65
    if mean > 0.95 or mean < 0.01:
        confidence *= 0.70
    return clamp(confidence * domain.confidence_scale, 0.0, 1.0)


def postprocess_model_output(
    model_output: Any,
    metadata: ModelMetadata,
    *,
    input_samples: Iterable[float],
    sample_rate: int,
    channels: int,
    dsp_noise_probability: float,
    freq_hz: float,
    config: SafetyConfig = SafetyConfig(),
) -> ModelPostprocessResult:
    samples = tuple(float(v) for v in input_samples)
    domain = check_domain(samples, sample_rate, channels, metadata)
    output_type = metadata.output_type
    dsp_prob = clamp(dsp_noise_probability, 0.0, 1.0)

    if output_type is ModelOutputType.UNKNOWN:
        return _base_invalid(
            ModelValidationStatus.UNKNOWN_OUTPUT_TYPE,
            output_type,
            domain,
            dsp_prob,
            freq_hz,
            config,
            "unknown model output type is never valid",
        )

    if model_output is None:
        return _base_invalid(
            ModelValidationStatus.EMPTY_OUTPUT,
            output_type,
            domain,
            dsp_prob,
            freq_hz,
            config,
            "missing model output",
        )

    actual_shape = infer_shape(model_output)
    if not is_rectangular_tensor(model_output):
        return _base_invalid(
            ModelValidationStatus.SHAPE_MISMATCH,
            output_type,
            domain,
            dsp_prob,
            freq_hz,
            config,
            "ragged model output tensor",
        )
    if not shape_matches(actual_shape, metadata.expected_output_shape):
        return _base_invalid(
            ModelValidationStatus.SHAPE_MISMATCH,
            output_type,
            domain,
            dsp_prob,
            freq_hz,
            config,
            f"shape {actual_shape} does not match {metadata.expected_output_shape}",
        )

    try:
        values = flatten_numeric(model_output)
    except (TypeError, ValueError):
        return _base_invalid(
            ModelValidationStatus.NON_FINITE_OUTPUT,
            output_type,
            domain,
            dsp_prob,
            freq_hz,
            config,
            "non-numeric model output",
        )

    if not values:
        return _base_invalid(
            ModelValidationStatus.EMPTY_OUTPUT,
            output_type,
            domain,
            dsp_prob,
            freq_hz,
            config,
            "empty model output",
        )
    if any(not math.isfinite(v) for v in values):
        return _base_invalid(
            ModelValidationStatus.NON_FINITE_OUTPUT,
            output_type,
            domain,
            dsp_prob,
            freq_hz,
            config,
            "NaN or Inf model output",
        )
    if any(abs(v) > max_abs_model_value(config) for v in values):
        return _base_invalid(
            ModelValidationStatus.SUSPICIOUS_OUTPUT,
            output_type,
            domain,
            dsp_prob,
            freq_hz,
            config,
            "absurd model output magnitude",
        )

    model_prob = 0.0
    processed: tuple[float, ...] = ()
    confidence = _confidence_from_values(tuple(clamp(v, 0.0, 1.0) for v in values), domain)
    mask_floor = min_model_gain(freq_hz, config)

    if output_type is ModelOutputType.GAIN_MASK:
        mask_values = tuple(clamp(v, mask_floor, 1.0) for v in values)
        model_prob = 1.0 - (sum(mask_values) / len(mask_values))

    elif output_type is ModelOutputType.NOISE_PROBABILITY_MASK:
        prob_values = tuple(clamp(v, 0.0, 1.0) for v in values)
        model_prob = sum(prob_values) / len(prob_values)

    elif output_type is ModelOutputType.RESIDUAL_ESTIMATE:
        if samples and len(values) != len(samples):
            return _base_invalid(
                ModelValidationStatus.SHAPE_MISMATCH,
                output_type,
                domain,
                dsp_prob,
                freq_hz,
                config,
                "residual length does not match input",
            )
        input_rms = rms(samples)
        residual_rms = rms(values)
        max_residual = input_rms * config.max_residual_rms_ratio
        if input_rms > 1.0e-8 and residual_rms > max_residual:
            return _base_invalid(
                ModelValidationStatus.SUSPICIOUS_OUTPUT,
                output_type,
                domain,
                dsp_prob,
                freq_hz,
                config,
                "residual estimate exceeds safety RMS budget",
            )
        limiter = 1.0 if residual_rms <= max_residual or residual_rms <= 1.0e-8 else max_residual / residual_rms
        processed = tuple(x - r * limiter for x, r in zip(samples, values))
        model_prob = clamp(residual_rms / max(input_rms, 1.0e-8), 0.0, 1.0) * confidence

    elif output_type is ModelOutputType.MAGNITUDE_ESTIMATE:
        if any(v < 0.0 for v in values):
            return _base_invalid(
                ModelValidationStatus.SUSPICIOUS_OUTPUT,
                output_type,
                domain,
                dsp_prob,
                freq_hz,
                config,
                "negative magnitude estimate",
            )
        input_mag = sum(abs(v) for v in samples) / max(len(samples), 1)
        proposed_mag = sum(abs(v) for v in values) / len(values)
        effective_gain = clamp(proposed_mag / max(input_mag, 1.0e-8), mask_floor, 1.0)
        model_prob = 1.0 - effective_gain
        confidence *= 0.65

    elif output_type is ModelOutputType.COMPLEX_MASK:
        if len(values) % 2 != 0:
            return _base_invalid(
                ModelValidationStatus.SHAPE_MISMATCH,
                output_type,
                domain,
                dsp_prob,
                freq_hz,
                config,
                "complex mask requires real/imag pairs",
            )
        magnitudes = tuple(math.hypot(values[i], values[i + 1]) for i in range(0, len(values) - 1, 2))
        if not magnitudes:
            return _base_invalid(
                ModelValidationStatus.EMPTY_OUTPUT,
                output_type,
                domain,
                dsp_prob,
                freq_hz,
                config,
                "complex mask has no pairs",
            )
        safe_magnitudes = tuple(clamp(v, mask_floor, 1.0) for v in magnitudes)
        model_prob = 1.0 - (sum(safe_magnitudes) / len(safe_magnitudes))
        confidence *= 0.55

    elif output_type is ModelOutputType.WAVEFORM:
        if samples and len(values) != len(samples):
            return _base_invalid(
                ModelValidationStatus.SHAPE_MISMATCH,
                output_type,
                domain,
                dsp_prob,
                freq_hz,
                config,
                "waveform length does not match input",
            )
        input_rms = rms(samples)
        output_rms = rms(values)
        if input_rms <= 1.0e-8:
            confidence = 0.0
        else:
            ratio = output_rms / input_rms
            if ratio > config.max_waveform_rms_ratio or ratio < config.min_waveform_rms_ratio:
                return _base_invalid(
                    ModelValidationStatus.SUSPICIOUS_OUTPUT,
                    output_type,
                    domain,
                    dsp_prob,
                    freq_hz,
                    config,
                    "waveform output RMS ratio outside safety range",
                )
            else:
                confidence *= 0.35
        blend = clamp(confidence * config.model_blend, 0.0, 0.35)
        processed = tuple(x + (y - x) * blend for x, y in zip(samples, values))
        model_prob = clamp(1.0 - (rms(processed) / max(input_rms, 1.0e-8)), 0.0, 1.0)

    final_prob = clamp(dsp_prob + (model_prob - dsp_prob) * confidence * config.model_blend, 0.0, 1.0)
    gain = bounded_gain_from_probability(final_prob, freq_hz, config)
    suspicious = confidence <= 0.0 and domain.status is not ModelDomainStatus.SILENCE
    return ModelPostprocessResult(
        status=ModelValidationStatus.SUSPICIOUS_OUTPUT if suspicious else ModelValidationStatus.OK,
        output_type=output_type,
        model_confidence=confidence,
        domain_status=domain.status,
        model_noise_probability=clamp(model_prob, 0.0, 1.0),
        dsp_noise_probability=dsp_prob,
        final_noise_probability=final_prob,
        gain=gain,
        processed_samples=processed,
        reason=domain.reason,
    )

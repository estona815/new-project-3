from __future__ import annotations

import math
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
JSFX = ROOT / "VOCAL_CLARITY_REPAIR_SYSTEM" / "JSFX" / "vocal_ai_artifact_split_tamer.jsfx"
INSTALLED_JSFX = (
    Path.home()
    / "Library/Application Support/REAPER/Effects/Codex Vocal/vocal_ai_artifact_split_tamer.jsfx"
)


def read_jsfx() -> str:
    return JSFX.read_text(encoding="utf-8")


def clamp(value: float, low: float, high: float) -> float:
    if not math.isfinite(value):
        return low
    return max(low, min(high, value))


def db_to_gain(db: float) -> float:
    return math.exp(db * 0.1151292546497023)


def soft_noise_probability(level_db: float, threshold_db: float, knee_db: float) -> float:
    level_db = clamp(level_db, -160.0, 0.0)
    knee_db = max(knee_db, 0.001)
    x = clamp((level_db - threshold_db) / knee_db, -40.0, 40.0)
    return 1.0 / (1.0 + math.exp(-x))


def map_amount(amount: float) -> float:
    return clamp(amount, 0.0, 1.0) ** 1.6


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


def conservative_gain(
    level_db: float,
    threshold_db: float = -18.0,
    knee_db: float = 9.0,
    amount: float = 0.30,
    mask_strength: float = 0.35,
    max_suppression_db: float = 8.0,
    freq_hz: float = 4000.0,
) -> float:
    band_max = band_max_suppression_db(freq_hz, max_suppression_db)
    noise_prob = soft_noise_probability(level_db, threshold_db, knee_db)
    attenuation_db = band_max * noise_prob * map_amount(amount) * clamp(mask_strength, 0.0, 1.0)
    min_gain = db_to_gain(-band_max)
    gain = db_to_gain(-attenuation_db)
    return clamp(gain, min_gain, 1.0)


def jsfx_band_limit(
    band: str,
    max_suppression_db: float = 8.0,
    vocal_preserve: float = 0.85,
    clarity_preserve: float = 0.85,
    air_preserve: float = 0.80,
    transient_preserve: float = 0.80,
    transient_score: float = 0.0,
    harmonic_preserve: float = 0.75,
) -> float:
    max_suppression_db = clamp(max_suppression_db, 0.0, 24.0)
    if band == "attack":
        limit = min(max_suppression_db, 4.0)
        limit *= clamp((1.0 - 0.65 * vocal_preserve) * (1.0 - 0.25 * clarity_preserve), 0.25, 1.0)
        limit *= clamp((1.0 - 0.75 * transient_preserve * transient_score) * (1.0 - 0.15 * harmonic_preserve), 0.25, 1.0)
        return limit
    if band == "sandy":
        limit = min(max_suppression_db, 4.0)
        limit *= clamp((1.0 - 0.55 * clarity_preserve) * (1.0 - 0.20 * vocal_preserve), 0.25, 1.0)
        limit *= clamp((1.0 - 0.75 * transient_preserve * transient_score) * (1.0 - 0.10 * harmonic_preserve), 0.25, 1.0)
        return limit
    if band == "fizz":
        limit = min(max_suppression_db, 3.0)
        limit *= clamp((1.0 - 0.50 * air_preserve) * (1.0 - 0.15 * clarity_preserve), 0.25, 1.0)
        limit *= clamp(1.0 - 0.45 * transient_preserve * transient_score, 0.25, 1.0)
        return limit
    if band == "air":
        limit = min(max_suppression_db, 3.0)
        limit *= clamp(1.0 - 0.50 * air_preserve, 0.25, 1.0)
        limit *= clamp(1.0 - 0.35 * transient_preserve * transient_score, 0.25, 1.0)
        return limit
    raise ValueError(band)


def transient_score(det: float, prev_det: float, high_energy: float, prev_high_energy: float) -> float:
    eps = 1.0e-8
    energy_rise_db = 8.685889638065037 * math.log(max(det, eps) / max(prev_det, eps))
    high_flux = max(0.0, high_energy - prev_high_energy) / max(prev_high_energy + eps, eps)
    energy_rise_norm = clamp((energy_rise_db - 1.5) / 10.0, 0.0, 1.0)
    flux_norm = clamp(high_flux * 2.5, 0.0, 1.0)
    return clamp(0.6 * flux_norm + 0.4 * energy_rise_norm, 0.0, 1.0)


def blend_toward_dry(gain: float, amount: float) -> float:
    return clamp(gain + (1.0 - gain) * clamp(amount, 0.0, 1.0), 0.0, 1.0)


def ms_roundtrip(left: float, right: float) -> tuple[float, float]:
    mid = 0.5 * (left + right)
    side = 0.5 * (left - right)
    return mid + side, mid - side


def multiband_gain(
    artifact_score: float,
    max_db: float,
    amount: float = 0.30,
    mask_strength: float = 0.35,
    mode_scale: float = 0.55,
    channel_scale: float = 0.25 * (1.0 - 0.55 * 0.85),
    source_protect: float = 0.80,
) -> float:
    effective_score = clamp(artifact_score, 0.0, 1.0) * (1.0 - clamp(source_protect, 0.0, 1.0))
    reduction_db = clamp(max_db, 0.0, 24.0) * map_amount(amount) * mask_strength * mode_scale * channel_scale * effective_score
    return clamp(db_to_gain(-reduction_db), db_to_gain(-max_db), 1.0)


def test_legacy_slider_order_is_preserved_for_existing_presets() -> None:
    text = read_jsfx()
    slider_lines = [line for line in text.splitlines() if line.startswith("slider")]

    assert slider_lines[:8] == [
        "slider1:32<0,100,1>Attack Harsh Tame",
        "slider2:38<0,100,1>Sandy Sibilance Tame",
        "slider3:44<0,100,1>Digital Fizz Tame",
        "slider4:28<0,100,1>Tail Warble Hide",
        "slider5:20<0,100,1>Body Preserve",
        "slider6:70<0,100,1>Dry/Wet",
        "slider7:0<-18,18,0.1>Output Trim (dB)",
        "slider8:0<0,1,1{Off,On}>Bypass",
    ]


def test_preservation_first_safety_defaults_are_present() -> None:
    text = read_jsfx()

    assert "slider9:30<0,100,1>Amount" in text
    assert "slider10:8<0,24,0.1>Max Reduction (dB)" in text
    assert "slider11:50<1,200,1>Detector Attack (ms)" in text
    assert "slider12:12<1,500,1>Detector Release (ms)" in text
    assert "slider13:1<0,1,1{Off,On}>Processing Enabled" in text
    assert "slider14:0.35<0,1,0.01>Mask Strength" in text
    assert "slider15:9<1,24,0.1>Soft Knee (dB)" in text
    assert "slider16:0.85<0,1,0.01>Vocal Preserve" in text
    assert "slider17:0.85<0,1,0.01>Clarity Preserve" in text
    assert "slider18:0.80<0,1,0.01>Air Preserve" in text
    assert "slider19:0.80<0,1,0.01>Transient Preserve" in text
    assert "slider20:1<0,1,1{Off,On}>Multiband Enabled" in text
    assert "slider21:1<0,1,1{Off,On}>M/S Enabled" in text
    assert "slider22:0<0,3,1{Preserve,Balanced,Surgical AI,Strong Test}>Multiband Mode" in text
    assert "slider23:0.25<0,1,0.01>Mid Amount" in text
    assert "slider24:0.40<0,1,0.01>Side Amount" in text
    assert "slider25:0.45<0,1,0.01>Side Artifact Reduction" in text
    assert "slider26:0.25<0,1,0.01>Surgical Artifact Reduction" in text
    assert "slider27:0<0,2,1{Off,Processed,Residual}>Residual Monitor" in text
    assert "slider28:0.85<0,1,0.01>Mid Preserve" in text
    assert "Preservation-first defaults" in text


def test_gain_floor_and_wet_mix_are_clamped() -> None:
    text = read_jsfx()

    assert "amount = max(0, min(slider9 / 100, 1));" in text
    assert "mapped_amount = pow(amount, 1.6);" in text
    assert "wet = max(0, min(slider6 / 100, 1));" in text
    assert "max_reduction_db = max(0, min(slider10, 24));" in text
    assert "mask_strength = max(0, min(slider14, 1));" in text
    assert "knee_db = max(1, min(slider15, 24));" in text
    assert "presence_soft_cap_db = 4;" in text
    assert "air_soft_cap_db = 3;" in text
    assert "vocal_preserve = max(0, min(slider16, 1));" in text
    assert "clarity_preserve = max(0, min(slider17, 1));" in text
    assert "air_preserve = max(0, min(slider18, 1));" in text
    assert "transient_preserve = max(0, min(slider19, 1));" in text
    assert "mb_enabled = slider20 >= 0.5;" in text
    assert "ms_enabled = slider21 >= 0.5;" in text
    assert "mid_amount = max(0, min(slider23, 1));" in text
    assert "side_amount = max(0, min(slider24, 1));" in text
    assert "mid_preserve = max(0, min(slider28, 1));" in text
    assert "attack_gain = max(attack_min_gain" in text
    assert "sandy_gain = max(sandy_min_gain" in text
    assert "fizz_gain = max(fizz_min_gain" in text
    assert "air_gain = max(air_min_gain" in text


def test_soft_mask_behavior_is_smooth_and_bounded() -> None:
    low_snr_gain = conservative_gain(-45.0, threshold_db=-18.0, amount=1.0, mask_strength=1.0)
    threshold_gain = conservative_gain(-18.0, threshold_db=-18.0, amount=1.0, mask_strength=1.0)
    high_snr_gain = conservative_gain(0.0, threshold_db=-18.0, amount=1.0, mask_strength=1.0)
    floor = db_to_gain(-band_max_suppression_db(4000.0, 8.0))

    assert floor <= low_snr_gain <= 1.0
    assert floor <= threshold_gain <= 1.0
    assert floor <= high_snr_gain <= 1.0
    assert high_snr_gain < threshold_gain < low_snr_gain
    assert abs(high_snr_gain - threshold_gain) < 0.40
    assert abs(threshold_gain - low_snr_gain) < 0.40


def test_knee_db_changes_transition_width() -> None:
    narrow_low = soft_noise_probability(-22.0, -18.0, 3.0)
    narrow_high = soft_noise_probability(-14.0, -18.0, 3.0)
    wide_low = soft_noise_probability(-22.0, -18.0, 12.0)
    wide_high = soft_noise_probability(-14.0, -18.0, 12.0)

    assert (narrow_high - narrow_low) > (wide_high - wide_low)


def test_amount_curve_is_conservative() -> None:
    assert map_amount(0.0) == 0.0
    assert map_amount(0.5) < 0.5
    assert 0.32 < map_amount(0.5) < 0.34

    no_amount_gain = conservative_gain(0.0, amount=0.0, mask_strength=1.0)
    half_amount_gain = conservative_gain(0.0, amount=0.5, mask_strength=1.0)
    full_amount_gain = conservative_gain(0.0, amount=1.0, mask_strength=1.0)

    assert no_amount_gain == 1.0
    assert half_amount_gain > full_amount_gain
    assert full_amount_gain >= db_to_gain(-band_max_suppression_db(4000.0, 8.0))


def test_frequency_dependent_limits_protect_presence_and_air() -> None:
    low = conservative_gain(0.0, amount=1.0, mask_strength=1.0, freq_hz=100.0)
    presence = conservative_gain(0.0, amount=1.0, mask_strength=1.0, freq_hz=4000.0)
    air = conservative_gain(0.0, amount=1.0, mask_strength=1.0, freq_hz=10000.0)

    assert band_max_suppression_db(100.0, 24.0) == 10.0
    assert band_max_suppression_db(4000.0, 24.0) == 4.0
    assert band_max_suppression_db(10000.0, 24.0) == 3.0
    assert low < presence < air
    assert all(band_max_suppression_db(freq, 8.0) <= 8.0 for freq in (100.0, 4000.0, 10000.0))


def test_preserve_parameters_reduce_attenuation_limits_without_boosting() -> None:
    attack_no_preserve = jsfx_band_limit("attack", vocal_preserve=0.0, clarity_preserve=0.0, transient_preserve=0.0, harmonic_preserve=0.0)
    attack_default = jsfx_band_limit("attack")
    sandy_no_preserve = jsfx_band_limit("sandy", vocal_preserve=0.0, clarity_preserve=0.0, transient_preserve=0.0, harmonic_preserve=0.0)
    sandy_default = jsfx_band_limit("sandy")
    air_no_preserve = jsfx_band_limit("air", air_preserve=0.0, transient_preserve=0.0)
    air_default = jsfx_band_limit("air")

    assert 0.0 <= attack_default < attack_no_preserve
    assert 0.0 <= sandy_default < sandy_no_preserve
    assert 0.0 <= air_default < air_no_preserve
    assert db_to_gain(-attack_default) <= 1.0
    assert db_to_gain(-sandy_default) <= 1.0
    assert db_to_gain(-air_default) <= 1.0


def test_transient_guard_reduces_suppression_and_stays_finite() -> None:
    assert transient_score(0.0, 0.0, 0.0, 0.0) == 0.0
    burst_score = transient_score(1.0, 0.1, 1.0, 0.1)
    assert math.isfinite(burst_score)
    assert 0.0 < burst_score <= 1.0

    steady_limit = jsfx_band_limit("attack", transient_score=0.0)
    transient_limit = jsfx_band_limit("attack", transient_score=burst_score)
    assert transient_limit < steady_limit


def test_harmonic_proxy_only_preserves_more_audio() -> None:
    without_harmonic = jsfx_band_limit("attack", harmonic_preserve=0.0)
    with_harmonic = jsfx_band_limit("attack", harmonic_preserve=0.70)

    assert with_harmonic < without_harmonic
    assert math.isfinite(with_harmonic)


def test_ms_encode_decode_roundtrip_is_level_consistent() -> None:
    for left, right in ((1.0, -0.25), (0.25, 0.75), (-0.5, -0.25), (0.0, 0.0)):
        out_l, out_r = ms_roundtrip(left, right)
        assert math.isclose(out_l, left, abs_tol=1.0e-12)
        assert math.isclose(out_r, right, abs_tol=1.0e-12)


def test_multiband_gain_is_bounded_and_preservation_weighted() -> None:
    no_artifact = multiband_gain(0.0, max_db=1.5)
    full_artifact_mid = multiband_gain(1.0, max_db=1.5, source_protect=0.85)
    full_artifact_side = multiband_gain(
        1.0,
        max_db=1.5,
        channel_scale=0.40 * (0.55 + 0.65 * 0.45),
        source_protect=0.55,
    )

    assert no_artifact == 1.0
    assert db_to_gain(-1.5) <= full_artifact_mid <= 1.0
    assert db_to_gain(-1.5) <= full_artifact_side <= 1.0
    assert full_artifact_mid > full_artifact_side


def test_tilt_and_air_guards_blend_toward_dry_without_boosting() -> None:
    base_gain = 0.55
    tilt_gain = blend_toward_dry(base_gain, 0.50 * 1.0 * 0.80)
    air_gain = blend_toward_dry(base_gain, 0.35 * 1.0 * 0.75)

    assert base_gain < tilt_gain <= 1.0
    assert base_gain < air_gain <= 1.0
    assert blend_toward_dry(1.0, 1.0) == 1.0


def test_numerical_gain_model_sanitizes_bad_values() -> None:
    for bad_level in (float("nan"), float("inf"), -float("inf")):
        gain = conservative_gain(bad_level, amount=1.0, mask_strength=1.0)
        assert math.isfinite(gain)
        assert db_to_gain(-band_max_suppression_db(4000.0, 8.0)) <= gain <= 1.0


def test_dry_fallback_paths_do_not_output_processed_signal() -> None:
    text = read_jsfx()

    assert "snap_bypass ? (" in text
    assert ") : (snap_wet <= eps) ? (" in text
    assert ") : (!snap_processing_enabled) ? (" in text
    assert "bad_proc ? (" in text
    assert ") : (suspicious_drop || full_band_collapse) ? (" in text
    assert "spl0 = in_l;" in text
    assert "spl1 = in_r;" in text
    assert "wet_state = 0;" in text
    assert "last_safe_l = in_l;" in text
    assert "last_safe_r = in_r;" in text


def test_numerical_and_non_destructive_guards_are_present() -> None:
    text = read_jsfx()

    assert "bad_input = (in_l != in_l)" in text
    assert "silent_input = (abs(in_l) + abs(in_r)) <= eps;" in text
    assert "bad_proc = (proc_l != proc_l)" in text
    assert "bad_out = (out_l != out_l)" in text
    assert "suspicious_drop" in text
    assert "0.0158489" in text  # -18 dB power ratio guard.
    assert "suspicious_drop_power_ratio" in text
    assert "full_band_collapse" in text
    assert "target_wet *= 0.25;" not in text
    assert "status = 5;" in text
    assert "mask_floor_ratio = 1.122018" in text
    assert "collapse_gain_floor = 0.398107" in text
    assert "mb_collapse_gain_floor = 0.50" in text
    assert "full_band_floor_count_limit = 2" in text
    assert "near_floor_count" in text
    assert "full_band_mask_floor = near_floor_count >= full_band_floor_count_limit;" in text
    assert "suppression_attack_coeff" in text
    assert "recovery_release_coeff" in text
    assert "transient_score_sm" in text
    assert "tilt_guard_sm" in text
    assert "air_guard_sm" in text
    assert "mb_avg_gain < mb_collapse_gain_floor" in text
    assert "side_width_guard" in text


def test_soft_mask_formula_is_integrated_in_jsfx() -> None:
    text = read_jsfx()

    assert "Soft-knee artifact probability" in text
    assert "attack_prob = 1 / (1 + exp(-attack_x));" in text
    assert "sandy_prob = 1 / (1 + exp(-sandy_x));" in text
    assert "fizz_prob = min(1, 1 / (1 + exp(-fizz_x))" in text
    assert "air_prob = min(1, 1 / (1 + exp(-air_x))" in text
    assert "attack_att_db = sample_attack_band_max_db * attack_prob * snap_mapped_amount * snap_mask_strength" in text
    assert "fizz_att_db = sample_fizz_band_max_db * fizz_prob * snap_mapped_amount * snap_mask_strength" in text


def test_prompt12_parameter_snapshot_and_early_dry_returns_are_integrated() -> None:
    text = read_jsfx()
    snapshot = text.index("JSFX equivalent of a processBlock parameter snapshot")
    filterbank = text.index("mono = 0.5 * (in_l + in_r);")

    for token in (
        "snap_wet = max(0, min(wet, 1));",
        "snap_bypass = bypass >= 0.5;",
        "snap_processing_enabled = processing_enabled >= 0.5;",
        "snap_mapped_amount = max(0, min(mapped_amount, 1));",
        "snap_mask_strength = max(0, min(mask_strength, 1));",
        "snap_vocal_preserve = max(0, min(vocal_preserve, 1));",
        "snap_clarity_preserve = max(0, min(clarity_preserve, 1));",
        "snap_air_preserve = max(0, min(air_preserve, 1));",
        "snap_transient_preserve = max(0, min(transient_preserve, 1));",
        "snap_harmonic_preserve = max(0, min(harmonic_preserve, 1));",
        "snap_residual_monitor = floor(max(0, min(residual_monitor, 2)) + 0.5);",
    ):
        assert token in text
        assert text.index(token) < filterbank

    assert text.index("snap_bypass ? (") < filterbank
    assert text.index(") : (snap_wet <= eps) ? (") < filterbank
    assert text.index(") : (!snap_processing_enabled) ? (") < filterbank
    assert snapshot < filterbank


def test_prompt12_bad_input_uses_last_stable_safe_output() -> None:
    text = read_jsfx()

    bad_input = text.index("bad_input ? (")
    silent = text.index(") : silent_input ? (")
    bad_block = text[bad_input:silent]

    assert "spl0 = last_safe_l;" in bad_block
    assert "spl1 = last_safe_r;" in bad_block
    assert "spl0 = 0;" not in bad_block
    assert "spl1 = 0;" not in bad_block


def test_preservation_guards_are_integrated_in_jsfx() -> None:
    text = read_jsfx()

    assert "Preserve guards only reduce attenuation limits" in text
    assert "attack_band_max_db *= max(0.25" in text
    assert "sandy_band_max_db *= max(0.25" in text
    assert "fizz_band_max_db *= max(0.25" in text
    assert "air_band_max_db *= max(0.25" in text
    assert "harmonic_preserve = 0.75;" in text
    assert "transient_guard = max(0.25" in text
    assert "sample_attack_band_max_db = attack_band_max_db;" in text
    assert "sample_attack_band_max_db *= max(0.25" in text
    assert "mb_mid_attack_protect" in text
    assert "mb_side_attack_protect" in text
    assert "mb_mid_fizz_protect" in text


def test_ms_dynamic_multiband_suppressor_is_integrated() -> None:
    text = read_jsfx()

    assert "M/S dynamic multiband suppressor" in text
    assert "mb_active = mb_enabled && ms_enabled;" in text
    assert "mid_low = 0.5 * (low_l + low_r);" in text
    assert "side_low = 0.5 * (low_l - low_r);" in text
    assert "proc_l = proc_m + proc_s;" in text
    assert "proc_r = proc_m - proc_s;" in text
    assert "mb_band_count = 14" in text
    assert "mb_band_count = 28" in text
    assert "mb_band_count = 48" in text
    assert "mb_band_count = 64" in text
    assert "mb_surgical_gate = surgical_artifact_reduction;" in text


def test_total_attenuation_budget_and_residual_monitor_are_integrated() -> None:
    text = read_jsfx()

    assert "mb_presence_budget_db = 1.5;" in text
    assert "mb_air_budget_db = 2.0;" in text
    assert "presence_budget_gain = exp(-mb_presence_budget_db * db2lin);" in text
    assert "air_budget_gain = exp(-mb_air_budget_db * db2lin);" in text
    assert "Residual monitor convention: dry input minus processed-before-drywet." in text
    assert "residual_monitor == 1" in text
    assert "residual_monitor == 2" in text
    assert "out_l = in_l - proc_l;" in text
    assert "out_r = in_r - proc_r;" in text


def test_tilt_and_air_loss_guards_are_integrated_in_jsfx() -> None:
    text = read_jsfx()

    assert "tilt_loss_db = input_tilt_db - output_tilt_db;" in text
    assert "sample_in_pow > 0.0000000001 ? (" in text
    assert "tilt_guard = max(0, min(1, (tilt_loss_db - 1.5) / 4.0));" in text
    assert "attack_gain += (1 - attack_gain) * 0.50 * tilt_guard_sm" in text
    assert "air_loss_db = 8.685889638065037 * log(air_in / air_out_est);" in text
    assert "air_guard = max(0, min(1, (air_loss_db - 2.0) / 5.0));" in text
    assert "air_gain += (1 - air_gain) * 0.35 * air_guard_sm * snap_air_preserve;" in text


def test_frequency_and_temporal_smoothing_are_lightweight() -> None:
    text = read_jsfx()

    assert "attack_target_gain = 0.25 + 0.50 * attack_raw_gain + 0.25 * sandy_raw_gain;" in text
    assert "sandy_target_gain = 0.25 * attack_raw_gain + 0.50 * sandy_raw_gain + 0.25 * fizz_raw_gain;" in text
    assert "fizz_target_gain = 0.25 * sandy_raw_gain + 0.50 * fizz_raw_gain + 0.25 * air_raw_gain;" in text
    assert "attack_target_gain < attack_gain_sm ? (" in text
    assert "fizz_target_gain < fizz_gain_sm ? (" in text


def test_dry_wet_formula_is_explicit() -> None:
    text = read_jsfx()

    assert "out_l = in_l + (proc_l - in_l) * wet_state;" in text
    assert "out_r = in_r + (proc_r - in_r) * wet_state;" in text


def test_no_fake_clarity_restoration_was_added() -> None:
    text = read_jsfx().lower()

    blocked_terms = ("exciter", "high shelf", "air boost", "clarity boost")
    assert not any(term in text for term in blocked_terms)


def test_installed_reaper_copy_matches_repo_source_when_available() -> None:
    if not INSTALLED_JSFX.exists():
        return

    assert INSTALLED_JSFX.read_text(encoding="utf-8") == read_jsfx()

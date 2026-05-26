from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
from scipy import signal

from audio_metrics import band_eq, bandpass, clipping_count, filter_audio, linear_to_db, mono, normalize_peak, peak_db, rms
from deesser import deess
from dynamic_eq import DynamicEQBand, dynamic_band_process
from pitch_correction import PitchCorrectionSettings, native_pitch_correction_approx
from saturation import soft_saturate
from vocal_rider import VocalRiderSettings, ride_vocal


@dataclass(frozen=True)
class VocalToneSettings:
    role: str = "lead"
    highpass_hz: float = 95.0
    lowpass_hz: float = 14_500.0
    air_lift_db: float = 0.8
    presence_db: float = 1.4
    tune_blend: float = 0.0
    target_relative_to_beat_db: float | None = 2.0
    second_deess_after_saturation: bool = True


def tune_support_layer(audio: np.ndarray, sample_rate: int, blend: float = 0.10) -> tuple[np.ndarray, dict[str, object]]:
    mode = "subtle" if blend <= 0.16 else "medium"
    corrected, _layer, report = native_pitch_correction_approx(audio, sample_rate, PitchCorrectionSettings(blend=min(blend, 0.22), mode=mode), return_layer=True)
    return corrected, report


def _band_delta_db(before: np.ndarray, after: np.ndarray, sample_rate: int, low_hz: float, high_hz: float) -> float:
    before_rms = rms(bandpass(before, low_hz, high_hz, sample_rate)) + 1e-12
    after_rms = rms(bandpass(after, low_hz, high_hz, sample_rate)) + 1e-12
    return round(linear_to_db(after_rms / before_rms), 2)


def _role_settings(role: str, tune_blend: float) -> VocalToneSettings:
    if role in {"double", "adlib"}:
        return VocalToneSettings(role=role, highpass_hz=135.0, lowpass_hz=12_500.0, air_lift_db=0.45, presence_db=0.75, tune_blend=tune_blend, target_relative_to_beat_db=-1.5)
    return VocalToneSettings(role="lead", tune_blend=tune_blend)


def design_vocal_tone(
    audio: np.ndarray,
    sample_rate: int,
    *,
    tune_blend: float = 0.0,
    beat_bus: np.ndarray | None = None,
    role: str = "lead",
) -> tuple[np.ndarray, dict[str, Any]]:
    settings = _role_settings(role, tune_blend)
    original = mono(audio)[:, None]
    vocal = filter_audio(original, settings.highpass_hz, settings.lowpass_hz, sample_rate)
    low_mid = bandpass(vocal, 150.0, 350.0, sample_rate)
    low_mid_db = linear_to_db(rms(low_mid) + 1e-12)
    mud_static_db = -1.2 if low_mid_db > -29.0 else -0.4
    vocal = band_eq(vocal, 150.0, 350.0, mud_static_db, sample_rate)
    vocal = band_eq(vocal, 1_500.0, 4_000.0, settings.presence_db, sample_rate)
    vocal, harsh_report = dynamic_band_process(
        vocal,
        vocal,
        DynamicEQBand(3_000.0, 6_000.0, threshold_db=-31.5, range_db=-2.8, ratio_slope=0.34, attack_ms=2.0, release_ms=70.0, mode="cut", detector="rms"),
        sample_rate,
    )
    vocal, deess_report = deess(vocal, sample_rate, threshold_db=None, range_db=-3.4, attack_ms=2.0, release_ms=70.0)
    rider_settings = VocalRiderSettings(
        target_db=-18.2 if settings.role == "lead" else -21.5,
        target_relative_to_beat_db=settings.target_relative_to_beat_db,
        max_boost_db=4.0,
        max_cut_db=6.0,
        smoothing_ms=110.0 if settings.role == "lead" else 150.0,
    )
    vocal, rider_report = ride_vocal(vocal, sample_rate, beat_bus=beat_bus, settings=rider_settings)
    tune_report: dict[str, object] = {"applied": False, "method": "none", "verified_plugin_used": False}
    if settings.tune_blend > 0.0:
        tuned, tune_report = tune_support_layer(vocal, sample_rate, blend=settings.tune_blend)
        vocal = (vocal * (1.0 - settings.tune_blend) + tuned * settings.tune_blend).astype(np.float32)
    formant_guard = signal.medfilt(mono(vocal), kernel_size=401)[:, None]
    vocal = vocal * 0.986 + formant_guard * 0.014
    vocal = soft_saturate(vocal, 1.04 if settings.role == "lead" else 1.025, 0.965)
    second_deess_report: dict[str, Any] | None = None
    if settings.second_deess_after_saturation:
        vocal, second_deess_report = deess(vocal, sample_rate, threshold_db=None, range_db=-2.0, attack_ms=1.5, release_ms=60.0)
    vocal = band_eq(vocal, 8_000.0, 13_500.0, min(settings.air_lift_db, 0.9), sample_rate)
    vocal, safety_gain = normalize_peak(vocal, -1.2, max_gain_db=0.0)
    harsh_delta = _band_delta_db(original, vocal, sample_rate, 3_000.0, 6_000.0)
    return vocal.astype(np.float32), {
        "role": settings.role,
        "highpass_hz": settings.highpass_hz,
        "mud_static_reduction_db": mud_static_db,
        "presence_db": settings.presence_db,
        "air_lift_db": min(settings.air_lift_db, 0.9),
        "vocal_rider": rider_report,
        "harshness_dynamic_eq": harsh_report,
        "deesser": deess_report,
        "second_deesser": second_deess_report,
        "pitch": tune_report,
        "harshness_band_delta_db": harsh_delta,
        "peak_dbfs": round(peak_db(vocal), 2),
        "safety_gain": safety_gain,
        "clipping_count": clipping_count(vocal),
        "plugin_pitch_correction_applied": False,
        "voice_clone_claimed": False,
    }

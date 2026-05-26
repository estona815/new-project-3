from __future__ import annotations

import numpy as np
from scipy import signal

from audio_metrics import (
    audio_quality_metrics,
    band_eq,
    db_to_linear,
    filter_audio,
    normalize_rms,
    oversampled_peak_db,
    peak_db,
    rms_db,
)
from ms_eq import safe_mid_side_process
from multiband_dynamics import DEFAULT_MASTER_BANDS, envelope_compress, multiband_glue
from saturation import SaturationSettings, saturate


def oversampled_limiter(
    audio: np.ndarray,
    sample_rate: int,
    ceiling_db: float = -1.0,
    drive: float = 1.0,
    oversample: int = 4,
    lookahead_ms: float = 2.0,
    release_ms: float = 65.0,
) -> tuple[np.ndarray, dict[str, float | int]]:
    ceiling = db_to_linear(ceiling_db)
    samples = audio.astype(np.float32, copy=False) * drive
    oversample = max(1, int(oversample))
    work = signal.resample_poly(samples, oversample, 1, axis=0).astype(np.float32) if oversample > 1 else samples.copy()
    work_rate = sample_rate * oversample
    lookahead = max(1, int(work_rate * lookahead_ms / 1000.0))
    release_coeff = np.exp(-1.0 / max(1.0, work_rate * release_ms / 1000.0))
    peak = np.max(np.abs(work), axis=1)
    needed_gain = np.minimum(1.0, ceiling / (peak + 1e-12)).astype(np.float32)
    gain = np.ones_like(needed_gain, dtype=np.float32)
    current = 1.0
    for idx, target in enumerate(needed_gain):
        if target < current:
            current = float(target)
        else:
            current = current * release_coeff + float(target) * (1.0 - release_coeff)
        gain[idx] = current
    if gain.shape[0] > lookahead:
        gain = np.concatenate((gain[lookahead:], np.ones(lookahead, dtype=np.float32)))
    limited = work * gain[:, None]
    limited = np.clip(limited, -ceiling, ceiling).astype(np.float32)
    if oversample > 1:
        limited = signal.resample_poly(limited, 1, oversample, axis=0).astype(np.float32)
        limited = limited[: samples.shape[0]]
    final_peak = float(np.max(np.abs(limited))) if limited.size else 0.0
    final_gain = 1.0
    if final_peak > ceiling:
        final_gain = ceiling / final_peak
        limited *= final_gain
    return limited.astype(np.float32), {
        "ceiling_db": ceiling_db,
        "drive": drive,
        "oversample": oversample,
        "lookahead_ms": lookahead_ms,
        "release_ms": release_ms,
        "peak_before_dbfs": round(peak_db(audio), 2),
        "sample_peak_after_dbfs": round(peak_db(limited), 2),
        "true_peak_proxy_dbfs": round(oversampled_peak_db(limited, oversample), 2),
        "minimum_gain_db": round(20.0 * np.log10(float(np.min(gain)) + 1e-12), 2),
        "final_safety_gain": round(final_gain, 6),
    }


def soft_limiter(audio: np.ndarray, ceiling_db: float = -1.0, drive: float = 1.0) -> tuple[np.ndarray, dict[str, float | int]]:
    return oversampled_limiter(audio, 48_000, ceiling_db=ceiling_db, drive=drive, oversample=4)


def _gentle_reference_tonal_eq(audio: np.ndarray, sample_rate: int) -> tuple[np.ndarray, list[dict[str, float]]]:
    moves = [
        (20.0, 55.0, -0.7),
        (70.0, 125.0, 0.35),
        (150.0, 380.0, 0.45),
        (2_000.0, 4_800.0, 0.25),
        (5_200.0, 8_500.0, -0.15),
        (9_000.0, 15_500.0, 0.45),
    ]
    out = audio.astype(np.float32, copy=False)
    for low, high, gain in moves:
        out = band_eq(out, low, high, gain, sample_rate)
    return out.astype(np.float32), [{"low_hz": low, "high_hz": high, "gain_db": gain} for low, high, gain in moves]


def master_bus_process(audio: np.ndarray, sample_rate: int, target_rms_db: float = -9.25, ceiling_db: float = -1.0) -> tuple[np.ndarray, dict[str, object]]:
    master = filter_audio(audio.astype(np.float32, copy=False), 24.0, 19_500.0, sample_rate)
    master, tonal_moves = _gentle_reference_tonal_eq(master, sample_rate)
    master, density_report = multiband_glue(master, sample_rate, DEFAULT_MASTER_BANDS, parallel_density=0.16)
    master, bus_report = envelope_compress(master, sample_rate, -18.5, 1.55, 18.0, 130.0, 0.55)
    saturated, saturation_report = saturate(
        master,
        sample_rate,
        SaturationSettings(drive=1.012, dry_wet=0.32, output_trim_db=-0.12, post_lowpass_hz=18_500.0, soft_clip=False, oversample=2),
    )
    master = saturated
    master, ms_report = safe_mid_side_process(
        master,
        sample_rate,
        side_low_cut_hz=145.0,
        side_upper_width_db=0.35,
        side_air_lift_db=0.3,
        mid_moves=[(120.0, 360.0, 0.15), (1_800.0, 3_800.0, 0.1)],
    )
    master, rms_gain = normalize_rms(master, target_rms_db, max_gain_db=8.0)
    limiter_ceiling = min(float(ceiling_db), -1.0)
    master, limit_report = oversampled_limiter(master, sample_rate, ceiling_db=limiter_ceiling, drive=1.0, oversample=4)
    true_peak_after = oversampled_peak_db(master, 4)
    peak_gain = 1.0
    if true_peak_after > limiter_ceiling:
        peak_gain = db_to_linear(limiter_ceiling - true_peak_after)
        master = (master * peak_gain).astype(np.float32)
    quality = audio_quality_metrics(master, sample_rate)
    return master.astype(np.float32), {
        "low_cleanup": {"highpass_hz": 24.0, "lowpass_hz": 19_500.0},
        "reference_tonal_eq": tonal_moves,
        "density_bus_multiband": density_report,
        "master_bus_compressor": bus_report,
        "master_saturation": saturation_report,
        "mid_side_safety": ms_report,
        "soft_limiter": limit_report,
        "rms_match_gain": rms_gain,
        "post_limiter_gain": peak_gain,
        "quality_metrics": quality,
        "output_peak_dbfs": round(peak_db(master), 2),
        "output_true_peak_proxy_dbfs": round(oversampled_peak_db(master, 4), 2),
        "output_rms_dbfs": round(rms_db(master), 2),
    }

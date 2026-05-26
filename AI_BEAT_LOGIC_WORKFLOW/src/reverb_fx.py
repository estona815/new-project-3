from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
from scipy import signal

from audio_metrics import clipping_count, db_to_linear, filter_audio, linear_to_db, mono, peak_db, rms, to_stereo
from dynamic_eq import envelope_follower


@dataclass(frozen=True)
class SchroederReverbSettings:
    pre_delay_ms: float = 35.0
    decay_seconds: float = 1.1
    wet: float = 0.09
    dry: float = 0.0
    return_highpass_hz: float = 220.0
    return_lowpass_hz: float = 8_000.0
    damping_hz: float = 6_500.0
    duck_range_db: float = -4.0
    duck_attack_ms: float = 10.0
    duck_release_ms: float = 240.0
    stereo_spread_ms: float = 11.0


def _comb_filter(x: np.ndarray, delay: int, feedback: float, sample_rate: int, damping_hz: float) -> np.ndarray:
    out = np.zeros_like(x, dtype=np.float32)
    damp_state = 0.0
    coeff = np.exp(-2.0 * np.pi * damping_hz / sample_rate)
    for index in range(x.shape[0]):
        delayed = out[index - delay] if index >= delay else 0.0
        damp_state = coeff * damp_state + (1.0 - coeff) * delayed
        out[index] = x[index] + damp_state * feedback
    return out


def _allpass_filter(x: np.ndarray, delay: int, feedback: float) -> np.ndarray:
    out = np.zeros_like(x, dtype=np.float32)
    for index in range(x.shape[0]):
        delayed_in = x[index - delay] if index >= delay else 0.0
        delayed_out = out[index - delay] if index >= delay else 0.0
        out[index] = -feedback * x[index] + delayed_in + feedback * delayed_out
    return out


def _duck_return(return_audio: np.ndarray, dry_source: np.ndarray, sample_rate: int, settings: SchroederReverbSettings) -> tuple[np.ndarray, dict[str, float]]:
    env = envelope_follower(dry_source, sample_rate, attack_ms=settings.duck_attack_ms, release_ms=settings.duck_release_ms, detector="rms")
    active = env > max(float(np.percentile(env, 65)) if env.size else 0.0, 1e-5)
    gain_db = np.where(active, settings.duck_range_db, 0.0).astype(np.float32)
    gain = np.power(10.0, gain_db / 20.0).astype(np.float32)
    if gain.shape[0] < return_audio.shape[0]:
        gain = np.pad(gain, (0, return_audio.shape[0] - gain.shape[0]), constant_values=1.0)
    ducked = return_audio * gain[: return_audio.shape[0], None]
    return ducked.astype(np.float32), {
        "duck_range_db": settings.duck_range_db,
        "duck_attack_ms": settings.duck_attack_ms,
        "duck_release_ms": settings.duck_release_ms,
        "active_ratio": round(float(np.mean(active)) if active.size else 0.0, 3),
    }


def schroeder_reverb(
    source: np.ndarray,
    sample_rate: int,
    settings: SchroederReverbSettings | None = None,
    *,
    duck_source: np.ndarray | None = None,
    length: int | None = None,
) -> tuple[np.ndarray, dict[str, Any]]:
    cfg = settings or SchroederReverbSettings()
    src = mono(source)
    out_len = length or src.shape[0] + int((cfg.pre_delay_ms / 1000.0 + cfg.decay_seconds + 0.4) * sample_rate)
    padded = np.zeros(out_len, dtype=np.float32)
    pre_delay = int(cfg.pre_delay_ms / 1000.0 * sample_rate)
    count = min(src.shape[0], out_len - pre_delay)
    if count > 0:
        padded[pre_delay : pre_delay + count] = src[:count]
    comb_delays = [0.0297, 0.0371, 0.0411, 0.0437]
    feedback = float(np.clip(0.68 + cfg.decay_seconds * 0.08, 0.58, 0.82))
    comb_sum = np.zeros_like(padded, dtype=np.float32)
    for delay_seconds in comb_delays:
        comb_sum += _comb_filter(padded, max(1, int(delay_seconds * sample_rate)), feedback, sample_rate, cfg.damping_hz)
    verb = comb_sum / len(comb_delays)
    for delay_seconds, fb in [(0.005, 0.62), (0.0017, 0.54)]:
        verb = _allpass_filter(verb, max(1, int(delay_seconds * sample_rate)), fb)
    right_delay = int(cfg.stereo_spread_ms / 1000.0 * sample_rate)
    right = np.pad(verb, (right_delay, 0))[:out_len]
    stereo = np.column_stack((verb, right)).astype(np.float32)
    stereo = filter_audio(stereo, cfg.return_highpass_hz, cfg.return_lowpass_hz, sample_rate)
    wet_return = stereo * float(np.clip(cfg.wet, 0.0, 1.0))
    duck_report = {"duck_range_db": 0.0, "active_ratio": 0.0}
    if duck_source is not None:
        duck_signal = to_stereo(duck_source)
        if duck_signal.shape[0] < wet_return.shape[0]:
            duck_signal = np.pad(duck_signal, ((0, wet_return.shape[0] - duck_signal.shape[0]), (0, 0)))
        wet_return, duck_report = _duck_return(wet_return, duck_signal[: wet_return.shape[0]], sample_rate, cfg)
    dry = np.zeros_like(wet_return)
    dry_count = min(to_stereo(source).shape[0], wet_return.shape[0])
    dry[:dry_count] = to_stereo(source)[:dry_count] * cfg.dry
    output = (dry + wet_return).astype(np.float32)
    return output, {
        "type": "schroeder_reverb",
        "pre_delay_ms": cfg.pre_delay_ms,
        "decay_seconds": cfg.decay_seconds,
        "wet": cfg.wet,
        "dry": cfg.dry,
        "return_highpass_hz": cfg.return_highpass_hz,
        "return_lowpass_hz": cfg.return_lowpass_hz,
        "comb_count": len(comb_delays),
        "allpass_count": 2,
        "ducking": duck_report,
        "peak_dbfs": round(peak_db(output), 2),
        "clipping_count": clipping_count(output),
    }


def small_room(source: np.ndarray, sample_rate: int, decay: float = 0.42, wet_db: float = -24.0, length: int | None = None) -> tuple[np.ndarray, dict[str, Any]]:
    wet = min(0.18, db_to_linear(wet_db + 18.0))
    settings = SchroederReverbSettings(pre_delay_ms=24.0, decay_seconds=max(0.45, decay * 1.8), wet=wet, return_highpass_hz=220.0, return_lowpass_hz=8_500.0)
    out, report = schroeder_reverb(source, sample_rate, settings, length=length)
    report["compatibility_wrapper"] = "small_room"
    return out, report

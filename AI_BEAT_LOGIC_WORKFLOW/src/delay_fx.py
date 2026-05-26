from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from audio_metrics import clipping_count, db_to_linear, filter_audio, peak_db, to_stereo
from dynamic_eq import envelope_follower


@dataclass(frozen=True)
class DelaySettings:
    mode: str = "tempo"
    beat_fraction: float = 0.5
    slap_ms: float = 95.0
    feedback: float = 0.18
    wet: float = 0.10
    ping_pong: bool = False
    return_highpass_hz: float = 220.0
    return_lowpass_hz: float = 7_500.0
    duck_range_db: float = -3.5
    duck_attack_ms: float = 8.0
    duck_release_ms: float = 220.0


def delay_frames_for_settings(sample_rate: int, bpm: float, settings: DelaySettings) -> int:
    if settings.mode == "slap":
        return max(1, int(settings.slap_ms / 1000.0 * sample_rate))
    beat_seconds = 60.0 / bpm
    return max(1, int(beat_seconds * settings.beat_fraction * sample_rate))


def _duck_delay(return_audio: np.ndarray, dry_source: np.ndarray, sample_rate: int, settings: DelaySettings) -> tuple[np.ndarray, dict[str, float]]:
    env = envelope_follower(dry_source, sample_rate, attack_ms=settings.duck_attack_ms, release_ms=settings.duck_release_ms, detector="rms")
    active = env > max(float(np.percentile(env, 65)) if env.size else 0.0, 1e-5)
    gain_db = np.where(active, settings.duck_range_db, 0.0).astype(np.float32)
    gain = np.power(10.0, gain_db / 20.0).astype(np.float32)
    if gain.shape[0] < return_audio.shape[0]:
        gain = np.pad(gain, (0, return_audio.shape[0] - gain.shape[0]), constant_values=1.0)
    return (return_audio * gain[: return_audio.shape[0], None]).astype(np.float32), {
        "duck_range_db": settings.duck_range_db,
        "duck_attack_ms": settings.duck_attack_ms,
        "duck_release_ms": settings.duck_release_ms,
        "active_ratio": round(float(np.mean(active)) if active.size else 0.0, 3),
    }


def delay_send(
    source: np.ndarray,
    sample_rate: int,
    bpm: float,
    settings: DelaySettings | None = None,
    *,
    duck_source: np.ndarray | None = None,
    length: int | None = None,
) -> tuple[np.ndarray, dict[str, Any]]:
    cfg = settings or DelaySettings()
    src = to_stereo(source)
    delay = delay_frames_for_settings(sample_rate, bpm, cfg)
    out_len = length or src.shape[0] + delay * 5
    out = np.zeros((out_len, 2), dtype=np.float32)
    current = src.copy()
    start = delay
    tap = 0
    while start < out_len and tap < 6:
        count = min(current.shape[0], out_len - start)
        if count <= 0:
            break
        if cfg.ping_pong and tap % 2 == 1:
            tap_audio = current[:count, ::-1]
        else:
            tap_audio = current[:count]
        out[start : start + count] += tap_audio * (cfg.wet * (cfg.feedback ** tap))
        current = current * cfg.feedback
        start += delay
        tap += 1
        if cfg.feedback <= 0.001:
            break
    out = filter_audio(out, cfg.return_highpass_hz, cfg.return_lowpass_hz, sample_rate)
    duck_report = {"duck_range_db": 0.0, "active_ratio": 0.0}
    if duck_source is not None:
        duck = to_stereo(duck_source)
        if duck.shape[0] < out.shape[0]:
            duck = np.pad(duck, ((0, out.shape[0] - duck.shape[0]), (0, 0)))
        out, duck_report = _duck_delay(out, duck[: out.shape[0]], sample_rate, cfg)
    return out.astype(np.float32), {
        "type": "delay_send",
        "mode": cfg.mode,
        "delay_seconds": round(delay / sample_rate, 4),
        "beat_fraction": cfg.beat_fraction if cfg.mode == "tempo" else None,
        "slap_ms": cfg.slap_ms if cfg.mode == "slap" else None,
        "feedback": cfg.feedback,
        "wet": cfg.wet,
        "ping_pong": cfg.ping_pong,
        "return_highpass_hz": cfg.return_highpass_hz,
        "return_lowpass_hz": cfg.return_lowpass_hz,
        "ducking": duck_report,
        "tap_count": tap,
        "peak_dbfs": round(peak_db(out), 2),
        "clipping_count": clipping_count(out),
    }


def tempo_delay(source: np.ndarray, sample_rate: int, bpm: float, taps: list[tuple[float, float, float]], length: int | None = None) -> tuple[np.ndarray, list[dict[str, float]]]:
    src = to_stereo(source)
    out_len = length or src.shape[0] + int(sample_rate * 2.0)
    out = np.zeros((out_len, 2), dtype=np.float32)
    beat_seconds = 60.0 / bpm
    report: list[dict[str, float]] = []
    for beat_offset, gain_db, pan in taps:
        delay = int(beat_offset * beat_seconds * sample_rate)
        if delay >= out_len:
            continue
        count = min(src.shape[0], out_len - delay)
        delayed = src[:count].copy()
        if pan < 0:
            delayed[:, 1] *= max(0.0, 1.0 + pan)
        elif pan > 0:
            delayed[:, 0] *= max(0.0, 1.0 - pan)
        out[delay : delay + count] += delayed * db_to_linear(gain_db)
        report.append({"beat_offset": beat_offset, "delay_seconds": round(beat_offset * beat_seconds, 3), "gain_db": gain_db, "pan": pan})
    return out, report

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from audio_metrics import linear_to_db, mono, rms, rms_db
from dynamic_eq import envelope_follower


@dataclass(frozen=True)
class VocalRiderSettings:
    target_db: float = -18.0
    target_relative_to_beat_db: float | None = None
    max_boost_db: float = 4.0
    max_cut_db: float = 6.0
    window_ms: float = 250.0
    smoothing_ms: float = 120.0
    activity_threshold_db: float = -48.0


def phrase_window_rms(audio: np.ndarray, sample_rate: int, window_ms: float = 250.0, activity_threshold_db: float = -48.0) -> list[dict[str, float | bool]]:
    samples = mono(audio)
    window = max(1, int(sample_rate * window_ms / 1000.0))
    report: list[dict[str, float | bool]] = []
    for start in range(0, samples.shape[0], window):
        end = min(samples.shape[0], start + window)
        value_db = rms_db(samples[start:end])
        report.append(
            {
                "start_seconds": round(start / sample_rate, 3),
                "end_seconds": round(end / sample_rate, 3),
                "rms_dbfs": round(value_db, 2),
                "active": bool(value_db >= activity_threshold_db),
            }
        )
    return report


def _window_target_db(beat_bus: np.ndarray | None, sample_rate: int, window_report: list[dict[str, float | bool]], settings: VocalRiderSettings) -> np.ndarray:
    if beat_bus is None or settings.target_relative_to_beat_db is None:
        return np.full(len(window_report), settings.target_db, dtype=np.float32)
    beat_windows = phrase_window_rms(beat_bus, sample_rate, settings.window_ms, activity_threshold_db=-90.0)
    targets = []
    for index, item in enumerate(window_report):
        beat_db = float(beat_windows[min(index, len(beat_windows) - 1)]["rms_dbfs"]) if beat_windows else settings.target_db
        if not bool(item["active"]):
            targets.append(settings.target_db)
        else:
            targets.append(min(settings.target_db + 3.0, beat_db + settings.target_relative_to_beat_db))
    return np.asarray(targets, dtype=np.float32)


def ride_vocal(
    audio: np.ndarray,
    sample_rate: int,
    beat_bus: np.ndarray | None = None,
    settings: VocalRiderSettings | None = None,
    *,
    target_db: float | None = None,
    max_boost_db: float | None = None,
    max_cut_db: float | None = None,
) -> tuple[np.ndarray, dict[str, Any]]:
    cfg = settings or VocalRiderSettings(
        target_db=target_db if target_db is not None else -18.0,
        max_boost_db=max_boost_db if max_boost_db is not None else 4.0,
        max_cut_db=max_cut_db if max_cut_db is not None else 6.0,
    )
    windows = phrase_window_rms(audio, sample_rate, cfg.window_ms, cfg.activity_threshold_db)
    targets = _window_target_db(beat_bus, sample_rate, windows, cfg)
    env = envelope_follower(audio, sample_rate, attack_ms=cfg.smoothing_ms, release_ms=cfg.smoothing_ms, detector="rms")
    env_db = np.array([linear_to_db(float(value) + 1e-9) for value in env], dtype=np.float32)
    sample_targets = np.zeros_like(env_db)
    window_frames = max(1, int(sample_rate * cfg.window_ms / 1000.0))
    for index, target in enumerate(targets):
        start = index * window_frames
        sample_targets[start : start + window_frames] = target
    if sample_targets.shape[0] < env_db.shape[0]:
        sample_targets[len(sample_targets) :] = cfg.target_db
    gain_db = np.clip(sample_targets[: env_db.shape[0]] - env_db, -abs(cfg.max_cut_db), abs(cfg.max_boost_db))
    active_mask = env_db >= cfg.activity_threshold_db
    gain_db = np.where(active_mask, gain_db, np.minimum(gain_db, 0.0))
    gain_linear = np.power(10.0, gain_db / 20.0).astype(np.float32)
    output = audio.astype(np.float32, copy=False) * gain_linear[: audio.shape[0], None]
    active_windows = [window for window in windows if bool(window["active"])]
    return output.astype(np.float32), {
        "target_db": cfg.target_db,
        "target_relative_to_beat_db": cfg.target_relative_to_beat_db,
        "window_ms": cfg.window_ms,
        "smoothing_ms": cfg.smoothing_ms,
        "activity_threshold_db": cfg.activity_threshold_db,
        "input_rms_db": round(rms_db(audio), 2),
        "output_rms_db": round(rms_db(output), 2),
        "active_window_count": len(active_windows),
        "window_rms": windows,
        "gain_envelope_db_summary": {
            "min": round(float(np.min(gain_db)) if gain_db.size else 0.0, 2),
            "max": round(float(np.max(gain_db)) if gain_db.size else 0.0, 2),
            "mean_active": round(float(np.mean(gain_db[active_mask])) if np.any(active_mask) else 0.0, 2),
        },
        "gain_envelope_linear_summary": {
            "min": round(float(np.min(gain_linear)) if gain_linear.size else 1.0, 4),
            "max": round(float(np.max(gain_linear)) if gain_linear.size else 1.0, 4),
        },
        "phrase_rms_spread_before_db": round(float(np.std([float(w["rms_dbfs"]) for w in active_windows])) if active_windows else 0.0, 2),
        "phrase_rms_spread_after_db": round(_active_window_spread(output, sample_rate, cfg), 2),
    }


def _active_window_spread(audio: np.ndarray, sample_rate: int, settings: VocalRiderSettings) -> float:
    windows = phrase_window_rms(audio, sample_rate, settings.window_ms, settings.activity_threshold_db)
    active = [float(window["rms_dbfs"]) for window in windows if bool(window["active"])]
    return float(np.std(active)) if active else 0.0

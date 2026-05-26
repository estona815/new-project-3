from __future__ import annotations

import numpy as np

from audio_metrics import BAND_RANGES, bandpass, linear_to_db, rms, to_stereo


def _band_rms(audio: np.ndarray, sample_rate: int, low_hz: float, high_hz: float) -> float:
    return rms(bandpass(to_stereo(audio), low_hz, high_hz, sample_rate)) + 1e-12


def vocal_to_beat_masking_score(
    vocal_bus: np.ndarray,
    beat_bus: np.ndarray,
    sample_rate: int,
    *,
    low_hz: float = 1_000.0,
    high_hz: float = 4_000.0,
    window_seconds: float = 1.0,
) -> dict[str, object]:
    window = max(1, int(window_seconds * sample_rate))
    frames = min(vocal_bus.shape[0], beat_bus.shape[0])
    windows: list[dict[str, float]] = []
    for start in range(0, frames, window):
        end = min(frames, start + window)
        if end <= start:
            continue
        vocal_rms = _band_rms(vocal_bus[start:end], sample_rate, low_hz, high_hz)
        beat_rms = _band_rms(beat_bus[start:end], sample_rate, low_hz, high_hz)
        vocal_minus_beat_db = linear_to_db(vocal_rms / beat_rms)
        windows.append(
            {
                "start_seconds": round(start / sample_rate, 3),
                "end_seconds": round(end / sample_rate, 3),
                "vocal_rms_dbfs": round(linear_to_db(vocal_rms), 2),
                "beat_rms_dbfs": round(linear_to_db(beat_rms), 2),
                "score_db": round(vocal_minus_beat_db, 2),
            }
        )
    active_windows = [window_report for window_report in windows if window_report["vocal_rms_dbfs"] > -80.0 or window_report["beat_rms_dbfs"] > -80.0]
    voiced_windows = [window_report for window_report in active_windows if window_report["vocal_rms_dbfs"] > -80.0]
    score_source = voiced_windows or active_windows or windows
    score_values = [window_report["score_db"] for window_report in score_source]
    return {
        "band_hz": [low_hz, high_hz],
        "score_db": round(float(np.mean(score_values)) if score_values else 0.0, 2),
        "worst_score_db": round(float(np.min(score_values)) if score_values else 0.0, 2),
        "window_seconds": window_seconds,
        "active_window_count": len(active_windows),
        "voiced_window_count": len(voiced_windows),
        "windows": windows,
        "interpretation": "higher is clearer vocal presence; lower means beat dominates vocal presence",
    }


def masking_score(vocal_bus: np.ndarray, instrumental_bus: np.ndarray, sample_rate: int) -> dict[str, float | str]:
    scores: dict[str, float | str] = {}
    for name in ["low_mid_150_400", "mid_400_1500", "presence_1500_4500"]:
        low_hz, high_hz = BAND_RANGES[name]
        vocal_rms = _band_rms(vocal_bus, sample_rate, low_hz, high_hz)
        inst_rms = _band_rms(instrumental_bus, sample_rate, low_hz, high_hz)
        scores[name] = round(linear_to_db(inst_rms / vocal_rms), 2)
    scores["presence_collision"] = vocal_to_beat_masking_score(vocal_bus, instrumental_bus, sample_rate)
    scores["interpretation"] = "negative band ratios mean vocal dominates; presence_collision score rises when vocal clears the beat"
    return scores

from __future__ import annotations

import numpy as np

from audio_metrics import db_to_linear, to_stereo


def add_to_mix(mix: np.ndarray, source: np.ndarray, gain: float, start_frame: int = 0, pan: float | None = None) -> None:
    stereo = to_stereo(source, pan)
    dst_start = start_frame
    src_start = 0
    if dst_start < 0:
        src_start = -dst_start
        dst_start = 0
    if src_start >= stereo.shape[0] or dst_start >= mix.shape[0]:
        return
    count = min(mix.shape[0] - dst_start, stereo.shape[0] - src_start)
    mix[dst_start : dst_start + count] += stereo[src_start : src_start + count] * gain


def gain_db(audio: np.ndarray, value_db: float) -> np.ndarray:
    return (audio.astype(np.float32, copy=False) * db_to_linear(value_db)).astype(np.float32)

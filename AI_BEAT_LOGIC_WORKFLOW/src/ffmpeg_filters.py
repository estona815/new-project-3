from __future__ import annotations

import shutil
from typing import Any


def ffmpeg_available() -> bool:
    return shutil.which("ffmpeg") is not None


def ffprobe_available() -> bool:
    return shutil.which("ffprobe") is not None


def build_filter_chain(analysis: dict[str, Any], fade_in: float, fade_out: float, duration: float) -> tuple[str, list[str]]:
    filters = ["highpass=f=25"]
    notes = ["highpass around 25Hz to remove unnecessary sub rumble"]

    low_end = analysis.get("low_end_excess_candidates", [])
    if low_end:
        filters.append("equalizer=f=260:t=q:w=1.0:g=-1.5")
        notes.append("gentle low-mid cleanup because analysis flagged low-end/mud risk")

    over = analysis.get("over_compression_detection", {})
    if over.get("possible_over_compression"):
        notes.append("compression skipped because over-compression was already suspected")
    else:
        filters.append("acompressor=threshold=-18dB:ratio=1.4:attack=20:release=120:makeup=0")
        notes.append("optional gentle compression with low ratio")

    if fade_in > 0:
        filters.append(f"afade=t=in:st=0:d={fade_in:.3f}")
        notes.append(f"fade in {fade_in:.3f}s")
    if fade_out > 0 and duration > fade_out:
        fade_start = max(0.0, duration - fade_out)
        filters.append(f"afade=t=out:st={fade_start:.3f}:d={fade_out:.3f}")
        notes.append(f"fade out {fade_out:.3f}s")

    filters.append("alimiter=limit=0.891")
    notes.append("safety limiter around -1 dBFS equivalent, not loudness-war mastering")
    return ",".join(filters), notes


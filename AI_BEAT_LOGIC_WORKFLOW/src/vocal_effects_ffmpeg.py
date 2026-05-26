from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass


@dataclass(frozen=True)
class FfmpegEffectSupport:
    ffmpeg_path: str | None
    compressor_available: bool
    limiter_available: bool
    reverb_available: bool
    delay_available: bool
    note: str


def _filter_list(ffmpeg: str) -> str:
    result = subprocess.run([ffmpeg, "-hide_banner", "-filters"], check=False, capture_output=True, text=True)
    if result.returncode != 0:
        return ""
    return result.stdout + result.stderr


def detect_ffmpeg_effect_support() -> FfmpegEffectSupport:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        return FfmpegEffectSupport(
            ffmpeg_path=None,
            compressor_available=False,
            limiter_available=False,
            reverb_available=False,
            delay_available=False,
            note="ffmpeg unavailable; using conservative Python processing only.",
        )
    filters = _filter_list(ffmpeg)
    return FfmpegEffectSupport(
        ffmpeg_path=ffmpeg,
        compressor_available="acompressor" in filters,
        limiter_available="alimiter" in filters,
        reverb_available="aecho" in filters or "afir" in filters,
        delay_available="adelay" in filters or "aecho" in filters,
        note=(
            "ffmpeg effects are available for rough preview only; high-quality vocal sends "
            "should be built manually in Logic Pro."
        ),
    )

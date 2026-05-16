from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from audio_analysis import read_wav_float
from export_audio import verify_wav
from loudness_estimation import rms_db


def expected_sample_rate(export_format: str) -> int:
    return 44100 if export_format == "wav24_44k" else 48000


def expected_final_name(export_format: str) -> str:
    return "final_suno_logic_processed_24bit_44k.wav" if export_format == "wav24_44k" else "final_suno_logic_processed_24bit_48k.wav"


def clipping_count(path: Path) -> int:
    _metadata, channels = read_wav_float(path)
    return sum(1 for channel in channels for sample in channel if abs(sample) >= 0.999969)


def rms_for_wav(path: Path) -> float:
    _metadata, channels = read_wav_float(path)
    samples = [sample for channel in channels for sample in channel]
    return rms_db(samples)


def verify_final_export(path: Path, export_format: str, length_mode: str = "under_2min") -> dict[str, Any]:
    info = verify_wav(path)
    clips = clipping_count(path)
    rms = rms_for_wav(path)
    expected_sr = expected_sample_rate(export_format)
    warnings: list[str] = []

    if int(info["sample_rate"]) != expected_sr:
        warnings.append(f"sample rate mismatch: expected {expected_sr}, got {info['sample_rate']}")
    if int(info["bit_depth"]) not in {16, 24, 32}:
        warnings.append(f"unexpected bit depth: {info['bit_depth']}")
    if float(info["peak_dbfs"]) > -1.0:
        warnings.append("final peak is above the approximate -1.0 dBFS safety target")
    if clips > 0:
        warnings.append("clipped samples detected")
    duration = float(info["duration_seconds"])
    if length_mode == "under_2min" and duration > 120.5:
        warnings.append("duration exceeds under-2-minute mode")
    if length_mode == "15sec_reels" and abs(duration - 15.0) > 0.75:
        warnings.append("duration does not match 15-second reels mode")

    result = {
        **info,
        "expected_sample_rate": expected_sr,
        "rms_dbfs": rms,
        "clipping_count": clips,
        "length_mode": length_mode,
        "warnings": warnings,
        "passed": not warnings,
    }
    return result


def write_verification_json(verification: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(verification, indent=2) + "\n", encoding="utf-8")


from __future__ import annotations

import shutil
import subprocess
import wave
from pathlib import Path

from audio_analysis import read_wav_float
from loudness_estimation import linear_to_db


def run_command(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, check=False, capture_output=True, text=True)


def verify_wav(path: Path) -> dict[str, float | int | str]:
    if not path.exists():
        raise FileNotFoundError(f"WAV output does not exist: {path}")
    if path.stat().st_size <= 0:
        raise ValueError(f"WAV output is empty: {path}")
    metadata, channels = read_wav_float(path)
    peak = max((abs(sample) for channel in channels for sample in channel), default=0.0)
    return {
        "path": str(path),
        "file_size": path.stat().st_size,
        "duration_seconds": metadata["duration_seconds"],
        "sample_rate": metadata["sample_rate"],
        "channels": metadata["channels"],
        "bit_depth": metadata["bit_depth"],
        "peak_dbfs": linear_to_db(peak),
    }


def write_float_wav(path: Path, channel_samples: list[list[float]], sample_rate: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    channels = len(channel_samples)
    frame_count = min((len(channel) for channel in channel_samples), default=0)
    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(channels)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        for index in range(frame_count):
            frame = bytearray()
            for channel in range(channels):
                value = max(-1.0, min(1.0, channel_samples[channel][index]))
                integer = int(round(value * (32767 if value >= 0 else 32768)))
                frame.extend(integer.to_bytes(2, "little", signed=True))
            wav_file.writeframesraw(bytes(frame))


def ffmpeg_path() -> str | None:
    return shutil.which("ffmpeg")


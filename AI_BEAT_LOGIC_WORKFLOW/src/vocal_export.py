from __future__ import annotations

from pathlib import Path
from typing import Any

from audio_analysis import read_wav_float
from export_audio import verify_wav, write_float_wav
from loudness_estimation import linear_to_db


def _peak(channels: list[list[float]]) -> float:
    return max((abs(sample) for channel in channels for sample in channel), default=0.0)


def _match_channels(channels: list[list[float]], target_channels: int) -> list[list[float]]:
    if not channels:
        return [[0.0] for _ in range(target_channels)]
    if len(channels) == target_channels:
        return [list(channel) for channel in channels]
    if len(channels) == 1 and target_channels == 2:
        return [list(channels[0]), list(channels[0])]
    mono_length = min(len(channel) for channel in channels)
    mono = [sum(channel[index] for channel in channels) / len(channels) for index in range(mono_length)]
    return [list(mono) for _ in range(target_channels)]


def _pad_to(channels: list[list[float]], frame_count: int) -> list[list[float]]:
    padded: list[list[float]] = []
    for channel in channels:
        if len(channel) >= frame_count:
            padded.append(channel[:frame_count])
        else:
            padded.append(channel + [0.0] * (frame_count - len(channel)))
    return padded


def _scale_to_peak(channels: list[list[float]], target_peak: float) -> tuple[list[list[float]], float]:
    peak = _peak(channels)
    if peak <= 0.0 or peak <= target_peak:
        return channels, 1.0
    gain = target_peak / peak
    return [[sample * gain for sample in channel] for channel in channels], gain


def mix_vocals_with_beat(
    beat_path: Path,
    vocal_paths: dict[str, Path],
    output_path: Path,
    vocal_analysis: dict[str, Any],
) -> dict[str, Any]:
    beat_metadata, beat_channels = read_wav_float(beat_path)
    sample_rate = beat_metadata["sample_rate"]
    target_channels = max(2, beat_metadata["channels"])
    beat = _match_channels(beat_channels, target_channels)
    frame_count = max(len(channel) for channel in beat)
    mix = _pad_to(beat, frame_count)
    mix = [[sample * 0.82 for sample in channel] for channel in mix]

    vocal_gains = {"lead_vocal": 0.8, "adlibs": 0.38, "backing_vocals": 0.48}
    mixed_vocals: dict[str, Any] = {}
    for label, path in vocal_paths.items():
        metadata, channels = read_wav_float(path)
        if metadata["sample_rate"] != sample_rate:
            return {
                "created": False,
                "path": str(output_path),
                "reason": f"{label} sample rate {metadata['sample_rate']} does not match beat sample rate {sample_rate}",
            }
        matched = _pad_to(_match_channels(channels, target_channels), frame_count)
        gain = vocal_gains.get(label, 0.5)
        if label == "lead_vocal":
            lead_metrics = vocal_analysis.get("files", {}).get("lead_vocal", {}).get("metrics", {})
            if lead_metrics.get("rms_dbfs") is not None and lead_metrics["rms_dbfs"] < -26.0:
                gain = min(0.92, gain + 0.08)
        for channel_index in range(target_channels):
            for index in range(frame_count):
                mix[channel_index][index] += matched[channel_index][index] * gain
        mixed_vocals[label] = {"path": str(path), "gain": gain}

    mix, trim_gain = _scale_to_peak(mix, 0.707945784)  # -3 dBFS preview headroom.
    write_float_wav(output_path, mix, sample_rate)
    verification = verify_wav(output_path)
    return {
        "created": True,
        "path": str(output_path),
        "sample_rate": sample_rate,
        "channels": target_channels,
        "mixed_vocals": mixed_vocals,
        "final_trim_gain": trim_gain,
        "peak_dbfs": linear_to_db(_peak(mix)),
        "verification": verification,
        "note": "Rough pre-master aligns all provided files at zero; detailed timing offsets and rides remain manual Logic work.",
    }

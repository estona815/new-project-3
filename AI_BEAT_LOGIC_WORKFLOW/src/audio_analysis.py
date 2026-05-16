from __future__ import annotations

import math
import struct
from pathlib import Path
from typing import Any

from loudness_estimation import estimate_integrated_loudness_dbfs, linear_to_db, rms_db, short_term_loudness_windows
from melody_focus_detection import detect_low_end_excess_and_melody_burial
from paths import PROJECT_ROOT
from report_analysis import write_analysis_json, write_analysis_summary
from section_detection import detect_arrangement_candidates, detect_silence_regions, windowed_features
from vocal_texture_detection import detect_vocal_like_textures


WORKING_WAV = PROJECT_ROOT / "04_PROCESSED_AUDIO" / "working_input.wav"
ANALYSIS_JSON = PROJECT_ROOT / "01_ANALYSIS" / "analysis.json"
ANALYSIS_SUMMARY = PROJECT_ROOT / "01_ANALYSIS" / "analysis_summary.md"


def read_wav_float(path: Path) -> tuple[dict[str, Any], list[list[float]]]:
    data = path.read_bytes()
    if len(data) < 44 or data[0:4] != b"RIFF" or data[8:12] != b"WAVE":
        raise ValueError("Invalid or unsupported WAV header")

    offset = 12
    fmt: dict[str, int] | None = None
    pcm_data: bytes | None = None
    while offset + 8 <= len(data):
        chunk_id = data[offset : offset + 4]
        chunk_size = int.from_bytes(data[offset + 4 : offset + 8], "little")
        chunk_start = offset + 8
        chunk_end = chunk_start + chunk_size
        if chunk_end > len(data):
            raise ValueError("WAV chunk size exceeds file size")
        chunk = data[chunk_start:chunk_end]
        if chunk_id == b"fmt ":
            if len(chunk) < 16:
                raise ValueError("WAV fmt chunk is too small")
            audio_format, channels, sample_rate, _byte_rate, block_align, bits_per_sample = struct.unpack("<HHIIHH", chunk[:16])
            fmt = {
                "audio_format": audio_format,
                "channels": channels,
                "sample_rate": sample_rate,
                "block_align": block_align,
                "bits_per_sample": bits_per_sample,
            }
        elif chunk_id == b"data":
            pcm_data = chunk
        offset = chunk_end + (chunk_size % 2)

    if fmt is None or pcm_data is None:
        raise ValueError("WAV file is missing fmt or data chunk")

    audio_format = fmt["audio_format"]
    channels = fmt["channels"]
    sample_rate = fmt["sample_rate"]
    bits_per_sample = fmt["bits_per_sample"]
    sample_width = bits_per_sample // 8
    block_align = fmt["block_align"]

    if audio_format not in {1, 3}:
        raise ValueError(f"Unsupported WAV audio format: {audio_format}")
    if channels <= 0:
        raise ValueError("WAV file has no channels")
    if sample_width not in {1, 2, 3, 4}:
        raise ValueError(f"Unsupported WAV sample width: {sample_width}")
    if audio_format == 3 and bits_per_sample != 32:
        raise ValueError("Only 32-bit IEEE float WAV is supported")
    if block_align != channels * sample_width:
        raise ValueError("WAV block alignment mismatch")

    frame_count = len(pcm_data) // block_align
    channel_samples = [[] for _ in range(channels)]
    frame_size = block_align
    for frame_start in range(0, frame_count * frame_size, frame_size):
        frame = pcm_data[frame_start : frame_start + frame_size]
        if len(frame) < frame_size:
            break
        for channel in range(channels):
            start = channel * sample_width
            raw = frame[start : start + sample_width]
            if audio_format == 3:
                value = struct.unpack("<f", raw)[0]
                if not math.isfinite(value):
                    value = 0.0
            elif sample_width == 1:
                value = (raw[0] - 128) / 128.0
            elif sample_width == 2:
                integer = int.from_bytes(raw, "little", signed=True)
                value = integer / (32768.0 if integer < 0 else 32767.0)
            elif sample_width == 3:
                integer = int.from_bytes(raw + (b"\xff" if raw[2] & 0x80 else b"\x00"), "little", signed=True)
                value = integer / (8388608.0 if integer < 0 else 8388607.0)
            else:
                integer = int.from_bytes(raw, "little", signed=True)
                value = integer / (2147483648.0 if integer < 0 else 2147483647.0)
            channel_samples[channel].append(max(-1.0, min(1.0, value)))

    metadata = {
        "path": str(path),
        "duration_seconds": frame_count / sample_rate if sample_rate else 0.0,
        "sample_rate": sample_rate,
        "channels": channels,
        "file_size": path.stat().st_size,
        "bit_depth": bits_per_sample,
        "audio_format": "ieee_float" if audio_format == 3 else "pcm",
        "frame_count": frame_count,
    }
    return metadata, channel_samples


def flatten_channels(channel_samples: list[list[float]]) -> list[float]:
    return [sample for channel in channel_samples for sample in channel]


def mono_mix(channel_samples: list[list[float]]) -> list[float]:
    if not channel_samples:
        return []
    length = min(len(channel) for channel in channel_samples)
    channels = len(channel_samples)
    return [sum(channel[index] for channel in channel_samples) / channels for index in range(length)]


def clipping_count(samples: list[float]) -> int:
    return sum(1 for sample in samples if abs(sample) >= 0.999969)


def detect_over_compression(short_term: list[dict[str, float]], peak_dbfs: float, rms_value_dbfs: float) -> dict[str, object]:
    valid = [item["loudness_dbfs"] for item in short_term if math.isfinite(item["loudness_dbfs"])]
    crest_factor = peak_dbfs - rms_value_dbfs if math.isfinite(peak_dbfs) and math.isfinite(rms_value_dbfs) else None
    similar_windows = 0
    if len(valid) > 1:
        for left, right in zip(valid, valid[1:]):
            if abs(left - right) < 1.0:
                similar_windows += 1
    possible = bool(crest_factor is not None and crest_factor < 7.0 and similar_windows >= max(1, len(valid) // 2))
    reasons: list[str] = []
    if crest_factor is not None and crest_factor < 7.0:
        reasons.append("very high RMS relative to peak")
    if similar_windows >= max(1, len(valid) // 2):
        reasons.append("repeated short-term windows have similar loudness")
    return {
        "possible_over_compression": possible,
        "crest_factor_db": crest_factor,
        "similar_loudness_window_count": similar_windows,
        "reason": "; ".join(reasons) if reasons else "No strong over-compression heuristic triggered",
    }


def analyze_working_wav(path: Path = WORKING_WAV, project_root: Path = PROJECT_ROOT) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"working_input.wav not found: {path}")
    metadata, channel_samples = read_wav_float(path)
    all_samples = flatten_channels(channel_samples)
    mono = mono_mix(channel_samples)
    peak_linear = max((abs(sample) for sample in all_samples), default=0.0)
    peak_db = linear_to_db(peak_linear)
    rms_value = rms_db(all_samples)
    short_term = short_term_loudness_windows(mono, metadata["sample_rate"])
    silence = detect_silence_regions(mono, metadata["sample_rate"])
    features = windowed_features(mono, metadata["sample_rate"])
    arrangement = detect_arrangement_candidates(features, metadata["duration_seconds"])
    low_end, melody_buried = detect_low_end_excess_and_melody_burial(mono, metadata["sample_rate"])
    vocal_candidates = detect_vocal_like_textures(channel_samples, metadata["sample_rate"])

    analysis: dict[str, Any] = {
        "metadata": metadata,
        "level_analysis": {
            "peak_dbfs": peak_db,
            "rms_dbfs": rms_value,
            "estimated_integrated_loudness_dbfs": estimate_integrated_loudness_dbfs(all_samples),
            "estimated_loudness_note": "Heuristic RMS-based estimate, not gated K-weighted LUFS.",
            "short_term_loudness_windows": short_term,
            "clipping_count": clipping_count(all_samples),
            "possible_intersample_risk_note": "Peak is close to full scale; true-peak verification is recommended." if peak_db > -1.0 else "No obvious intersample risk from sample peak heuristic.",
        },
        "silence_detection": silence,
        "over_compression_detection": detect_over_compression(short_term, peak_db, rms_value),
        "low_end_excess_candidates": low_end,
        "vocal_like_texture_candidates": vocal_candidates,
        "melody_buried_candidates": melody_buried,
        "arrangement_candidates": arrangement,
        "producer_notes": {
            "human_arrangement_cleanup": "Review heuristic hook/drop/glitch candidates manually. Tighten random transitions and remove meaningless repetition.",
            "main_melody_strongest": arrangement.get("main_melody_strongest_region"),
            "heuristic_disclaimer": "Vocal texture, low-end, melody burial, and arrangement detections are heuristic only.",
        },
    }
    write_analysis_json(analysis, project_root / "01_ANALYSIS" / "analysis.json")
    write_analysis_summary(analysis, project_root / "01_ANALYSIS" / "analysis_summary.md")
    return analysis


def main() -> int:
    analysis = analyze_working_wav()
    print(f"Wrote analysis for {analysis['metadata']['path']}")
    print(f"Duration: {analysis['metadata']['duration_seconds']:.2f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

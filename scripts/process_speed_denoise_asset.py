#!/usr/bin/env python3
"""Decode, denoise, speed up, and re-encode an audio asset with evidence."""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import shutil
import subprocess
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
from scipy.io import wavfile
from scipy.signal import resample_poly, stft, istft


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = ROOT / "processed_audio"
DEFAULT_REPORTS_DIR = ROOT / "reports"
KNOWN_FFMPEG_CANDIDATES = (
    Path("/Applications/Live2D Cubism 5.3/tools/ffmpeg/ffmpeg"),
)


@dataclass
class AudioMetrics:
    sample_rate_hz: int
    channels: int
    samples_per_channel: int
    duration_seconds: float
    peak_dbfs: float
    rms_dbfs: float


def slugify(value: str) -> str:
    value = value.lower()
    value = re.sub(r"[^a-z0-9]+", "_", value)
    return value.strip("_") or "audio_asset"


def run(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True)


def resolve_ffmpeg() -> Path | None:
    ffmpeg_env = os.environ.get("FFMPEG_BIN")
    if ffmpeg_env:
        candidate = Path(ffmpeg_env).expanduser()
        if candidate.exists():
            return candidate.resolve()

    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg:
        return Path(ffmpeg).resolve()

    for candidate in KNOWN_FFMPEG_CANDIDATES:
        if candidate.exists():
            return candidate.resolve()

    return None


def bitrate_kbps_string(bitrate: int) -> str:
    return f"{max(1, int(round(bitrate / 1000.0)))}k"


def decode_to_wav(input_path: Path, wav_path: Path) -> str:
    afconvert = shutil.which("afconvert")
    if afconvert:
        try:
            run([afconvert, "-f", "WAVE", "-d", "LEI16", str(input_path), str(wav_path)])
            return "afconvert"
        except subprocess.CalledProcessError:
            if wav_path.exists():
                wav_path.unlink()

    ffmpeg = resolve_ffmpeg()
    if ffmpeg:
        run(
            [
                str(ffmpeg),
                "-y",
                "-hide_banner",
                "-loglevel",
                "error",
                "-i",
                str(input_path),
                "-vn",
                "-acodec",
                "pcm_s16le",
                str(wav_path),
            ]
        )
        return "ffmpeg"

    raise RuntimeError("afconvert or ffmpeg is required but neither was found")


def encode_mp3(input_wav_path: Path, mp3_path: Path, bitrate: int) -> str:
    ffmpeg = resolve_ffmpeg()
    if ffmpeg:
        run(
            [
                str(ffmpeg),
                "-y",
                "-hide_banner",
                "-loglevel",
                "error",
                "-i",
                str(input_wav_path),
                "-codec:a",
                "libmp3lame",
                "-b:a",
                bitrate_kbps_string(bitrate),
                str(mp3_path),
            ]
        )
        return "ffmpeg"

    afconvert = shutil.which("afconvert")
    if afconvert:
        run([afconvert, "-f", "MPG3", "-d", ".mp3", "-b", str(bitrate), str(input_wav_path), str(mp3_path)])
        return "afconvert"

    raise RuntimeError("ffmpeg or afconvert is required but neither was found")


def encode_m4a(input_wav_path: Path, m4a_path: Path, bitrate: int) -> str:
    ffmpeg = resolve_ffmpeg()
    if ffmpeg:
        run(
            [
                str(ffmpeg),
                "-y",
                "-hide_banner",
                "-loglevel",
                "error",
                "-i",
                str(input_wav_path),
                "-codec:a",
                "aac",
                "-b:a",
                bitrate_kbps_string(bitrate),
                str(m4a_path),
            ]
        )
        return "ffmpeg"

    afconvert = shutil.which("afconvert")
    if afconvert:
        run([afconvert, "-f", "m4af", "-d", "aac", "-b", str(bitrate), str(input_wav_path), str(m4a_path)])
        return "afconvert"

    raise RuntimeError("ffmpeg or afconvert is required but neither was found")


def read_audio(path: Path) -> tuple[int, np.ndarray]:
    sample_rate, audio = wavfile.read(path)
    if audio.ndim == 1:
        audio = audio[:, np.newaxis]
    if np.issubdtype(audio.dtype, np.integer):
        max_value = np.iinfo(audio.dtype).max
        audio_float = audio.astype(np.float32) / max_value
    else:
        audio_float = audio.astype(np.float32)
    return sample_rate, np.clip(audio_float, -1.0, 1.0)


def write_audio(path: Path, sample_rate: int, audio: np.ndarray) -> None:
    audio = np.clip(audio, -1.0, 1.0)
    audio_i16 = np.round(audio * 32767.0).astype(np.int16)
    if audio_i16.shape[1] == 1:
        wavfile.write(path, sample_rate, audio_i16[:, 0])
    else:
        wavfile.write(path, sample_rate, audio_i16)


def compute_metrics(sample_rate: int, audio: np.ndarray) -> AudioMetrics:
    mono = audio.mean(axis=1)
    peak = float(np.max(np.abs(audio)))
    rms = float(np.sqrt(np.mean(np.square(mono), dtype=np.float64)))
    peak_dbfs = -120.0 if peak <= 0.0 else 20.0 * math.log10(peak)
    rms_dbfs = -120.0 if rms <= 0.0 else 20.0 * math.log10(rms)
    return AudioMetrics(
        sample_rate_hz=sample_rate,
        channels=int(audio.shape[1]),
        samples_per_channel=int(audio.shape[0]),
        duration_seconds=float(audio.shape[0] / sample_rate),
        peak_dbfs=peak_dbfs,
        rms_dbfs=rms_dbfs,
    )


def denoise_channel(channel: np.ndarray, sample_rate: int, strength: float) -> np.ndarray:
    nperseg = 2048
    noverlap = 1536
    freqs, _, spec = stft(
        channel,
        fs=sample_rate,
        nperseg=nperseg,
        noverlap=noverlap,
        boundary="zeros",
        padded=True,
    )
    magnitude = np.abs(spec)
    phase = np.angle(spec)

    # Use a low percentile profile as a conservative stationary-noise estimate.
    noise_profile = np.percentile(magnitude, 20.0, axis=1, keepdims=True)

    # Reduce less in the upper-presence region to avoid stripping violin detail.
    freq_scale = np.ones_like(freqs, dtype=np.float32)
    freq_scale[freqs >= 3000.0] = 0.8
    freq_scale[freqs >= 7000.0] = 0.65
    freq_scale = freq_scale[:, np.newaxis]

    suppression = strength * freq_scale * noise_profile
    cleaned_magnitude = np.maximum(magnitude - suppression, magnitude * 0.28)
    cleaned_spec = cleaned_magnitude * np.exp(1j * phase)
    _, cleaned = istft(
        cleaned_spec,
        fs=sample_rate,
        nperseg=nperseg,
        noverlap=noverlap,
        input_onesided=True,
        boundary=True,
    )
    cleaned = cleaned[: channel.shape[0]]
    return np.clip(cleaned.astype(np.float32), -1.0, 1.0)


def denoise_audio(audio: np.ndarray, sample_rate: int, strength: float) -> np.ndarray:
    cleaned_channels = [denoise_channel(audio[:, idx], sample_rate, strength) for idx in range(audio.shape[1])]
    return np.stack(cleaned_channels, axis=1)


def speed_up_audio(audio: np.ndarray, speed: float) -> np.ndarray:
    up = 2
    down = max(1, int(round(speed * up)))
    sped_channels = [resample_poly(audio[:, idx], up, down).astype(np.float32) for idx in range(audio.shape[1])]
    min_len = min(channel.shape[0] for channel in sped_channels)
    trimmed = [channel[:min_len] for channel in sped_channels]
    return np.stack(trimmed, axis=1)


def build_report_md(
    input_path: Path,
    output_audio_path: Path,
    output_wav_path: Path,
    metrics_before: AudioMetrics,
    metrics_after: AudioMetrics,
    speed: float,
    denoise_strength: float,
    process_report_json: Path,
    fallback_used: bool,
    decode_backend: str,
    encode_backend: str,
) -> str:
    return "\n".join(
        [
            f"# {output_audio_path.stem} Processing Report",
            "",
            "## Summary",
            f"- Source: `{input_path}`",
            f"- Output audio: `{output_audio_path}`",
            f"- Output WAV: `{output_wav_path}`",
            f"- Speed factor: `{speed}`",
            f"- Denoise strength: `{denoise_strength}`",
            f"- Container fallback used: `{fallback_used}`",
            f"- Decode backend: `{decode_backend}`",
            f"- Encode backend: `{encode_backend}`",
            "",
            "## Measured Input",
            f"- Duration seconds: `{metrics_before.duration_seconds:.3f}`",
            f"- Sample rate Hz: `{metrics_before.sample_rate_hz}`",
            f"- Channels: `{metrics_before.channels}`",
            f"- Peak dBFS: `{metrics_before.peak_dbfs:.2f}`",
            f"- RMS dBFS: `{metrics_before.rms_dbfs:.2f}`",
            "",
            "## Measured Output",
            f"- Duration seconds: `{metrics_after.duration_seconds:.3f}`",
            f"- Sample rate Hz: `{metrics_after.sample_rate_hz}`",
            f"- Channels: `{metrics_after.channels}`",
            f"- Peak dBFS: `{metrics_after.peak_dbfs:.2f}`",
            f"- RMS dBFS: `{metrics_after.rms_dbfs:.2f}`",
            "",
            "## Notes",
            "- Noise reduction is a conservative spectral subtraction pass using a low-percentile stationary-noise estimate.",
            "- The 1.5x speed change is implemented as playback-speed resampling, so pitch rises with speed.",
            "- The script prefers ffmpeg for export when available, then falls back to platform encoders before using AAC `.m4a` as a last resort.",
            "- This report documents file existence and measured signal properties only; it does not claim listening outcomes.",
            "",
            "## Evidence",
            f"- JSON report: `{process_report_json}`",
        ]
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_audio", type=Path)
    parser.add_argument("--speed", type=float, default=1.5)
    parser.add_argument("--denoise-strength", type=float, default=0.7)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--reports-dir", type=Path, default=DEFAULT_REPORTS_DIR)
    args = parser.parse_args()

    input_audio = args.input_audio.expanduser().resolve()
    if not input_audio.exists():
        raise FileNotFoundError(f"Input file not found: {input_audio}")

    output_dir = args.output_dir.resolve()
    reports_dir = args.reports_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    slug = f"{slugify(input_audio.stem)}_{str(args.speed).replace('.', 'p')}x_denoised"
    report_dir = reports_dir / slug
    report_dir.mkdir(parents=True, exist_ok=True)

    decoded_wav = report_dir / f"{slug}_decoded.wav"
    processed_wav = report_dir / f"{slug}_processed.wav"
    output_mp3 = output_dir / f"{slug}.mp3"
    output_m4a = output_dir / f"{slug}.m4a"
    json_report = report_dir / f"{slug}_report.json"
    md_report = report_dir / f"{slug}_report.md"

    decode_backend = decode_to_wav(input_audio, decoded_wav)
    sample_rate, audio = read_audio(decoded_wav)
    metrics_before = compute_metrics(sample_rate, audio)

    denoised = denoise_audio(audio, sample_rate, args.denoise_strength)
    processed = speed_up_audio(denoised, args.speed)
    metrics_after = compute_metrics(sample_rate, processed)

    write_audio(processed_wav, sample_rate, processed)
    fallback_used = False
    output_audio = output_mp3
    encode_backend = ""
    try:
        encode_backend = encode_mp3(processed_wav, output_mp3, bitrate=320000)
        if output_m4a.exists():
            output_m4a.unlink()
    except subprocess.CalledProcessError:
        fallback_used = True
        encode_backend = encode_m4a(processed_wav, output_m4a, bitrate=256000)
        output_audio = output_m4a
        if output_mp3.exists():
            output_mp3.unlink()

    payload: dict[str, Any] = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "input_audio": str(input_audio),
        "output_audio": str(output_audio),
        "output_mp3": str(output_mp3),
        "output_m4a": str(output_m4a),
        "output_wav": str(processed_wav),
        "processing": {
            "speed_factor": args.speed,
            "denoise_strength": args.denoise_strength,
            "denoise_method": "spectral_subtraction_low_percentile_profile",
            "speed_method": "resample_poly_playback_speed_change",
            "fallback_used": fallback_used,
            "decode_backend": decode_backend,
            "encode_backend": encode_backend,
        },
        "input_metrics": asdict(metrics_before),
        "output_metrics": asdict(metrics_after),
        "file_existence": {
            "decoded_wav": decoded_wav.exists(),
            "processed_wav": processed_wav.exists(),
            "output_mp3": output_mp3.exists(),
            "output_m4a": output_m4a.exists(),
        },
        "file_sizes_bytes": {
            "decoded_wav": decoded_wav.stat().st_size if decoded_wav.exists() else None,
            "processed_wav": processed_wav.stat().st_size if processed_wav.exists() else None,
            "output_mp3": output_mp3.stat().st_size if output_mp3.exists() else None,
            "output_m4a": output_m4a.stat().st_size if output_m4a.exists() else None,
        },
    }
    json_report.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    md_report.write_text(
        build_report_md(
            input_path=input_audio,
            output_audio_path=output_audio,
            output_wav_path=processed_wav,
            metrics_before=metrics_before,
            metrics_after=metrics_after,
            speed=args.speed,
            denoise_strength=args.denoise_strength,
            process_report_json=json_report,
            fallback_used=fallback_used,
            decode_backend=decode_backend,
            encode_backend=encode_backend,
        )
        + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()

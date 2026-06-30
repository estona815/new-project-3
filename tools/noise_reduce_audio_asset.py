#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import imageio_ffmpeg
import numpy as np
from scipy import signal
from scipy.io import wavfile


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_AUDIO = ROOT / "output" / "audio"
OUTPUT_ANALYSIS = ROOT / "output" / "audio-analysis"
FFMPEG = Path(imageio_ffmpeg.get_ffmpeg_exe())

BASE_REDUCTION_DB = 2.6
NOISE_PERCENTILE = 12.0
THRESHOLD_MULT = 3.0
FRAME_MS = 50


@dataclass
class AudioData:
    sample_rate: int
    samples: np.ndarray
    source_decode_path: Path | None = None


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    return slug or "audio"


def db_amp(db: float | np.ndarray) -> float | np.ndarray:
    return np.power(10.0, np.asarray(db) / 20.0)


def amp_db(value: float | np.ndarray) -> float | np.ndarray:
    return 20.0 * np.log10(np.maximum(np.asarray(value), 1.0e-12))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run(command: list[str]) -> None:
    subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)


def pcm_to_float32(data: np.ndarray) -> np.ndarray:
    if data.dtype.kind == "f":
        out = data.astype(np.float32)
    elif data.dtype.kind in {"i", "u"}:
        scale = max(abs(np.iinfo(data.dtype).min), np.iinfo(data.dtype).max)
        out = data.astype(np.float32) / float(scale)
    else:
        raise TypeError(f"unsupported PCM dtype: {data.dtype}")
    if out.ndim == 1:
        out = out[:, None]
    return np.clip(out, -1.0, 1.0)


def wav_write_ready_float32(samples: np.ndarray) -> np.ndarray:
    return np.clip(samples, -1.0, 1.0 - (1.0 / (2**23))).astype(np.float32)


def decode_audio(path: Path, decode_path: Path) -> AudioData:
    if path.suffix.lower() in {".wav", ".wave"}:
        sample_rate, data = wavfile.read(path)
        return AudioData(int(sample_rate), pcm_to_float32(data))
    run(
        [
            str(FFMPEG),
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(path),
            "-c:a",
            "pcm_f32le",
            str(decode_path),
        ]
    )
    sample_rate, data = wavfile.read(decode_path)
    return AudioData(int(sample_rate), pcm_to_float32(data), source_decode_path=decode_path)


def encode_mp3(source_wav: Path, output_mp3: Path) -> None:
    run(
        [
            str(FFMPEG),
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(source_wav),
            "-codec:a",
            "libmp3lame",
            "-b:a",
            "320k",
            str(output_mp3),
        ]
    )


def rms(samples: np.ndarray) -> float:
    return float(np.sqrt(np.mean(np.square(samples), dtype=np.float64)))


def peak(samples: np.ndarray) -> float:
    return float(np.max(np.abs(samples))) if samples.size else 0.0


def frame_rms(samples: np.ndarray, frame_size: int) -> np.ndarray:
    mono = samples.mean(axis=1)
    if mono.size < frame_size:
        mono = np.pad(mono, (0, frame_size - mono.size))
    hop = frame_size
    frames = []
    for start in range(0, mono.size - frame_size + 1, hop):
        frame = mono[start : start + frame_size]
        frames.append(np.sqrt(np.mean(frame * frame, dtype=np.float64)))
    return np.asarray(frames, dtype=np.float64) if frames else np.zeros(1, dtype=np.float64)


def high_band_share(samples: np.ndarray, sample_rate: int, low_hz: float = 6000.0, high_hz: float = 16000.0) -> float:
    mono = samples.mean(axis=1)
    window = np.hanning(mono.size)
    spectrum = np.abs(np.fft.rfft(mono * window)) ** 2
    freqs = np.fft.rfftfreq(mono.size, 1.0 / sample_rate)
    total = float(spectrum.sum()) or 1.0
    band = float(spectrum[(freqs >= low_hz) & (freqs <= high_hz)].sum())
    return band / total


def spectral_flatness_median(samples: np.ndarray, sample_rate: int) -> float:
    mono = samples.mean(axis=1)
    nperseg = min(2048, max(512, len(mono)))
    _, _, zxx = signal.stft(mono, fs=sample_rate, window="hann", nperseg=nperseg, noverlap=nperseg // 2, boundary=None, padded=False)
    mags = np.abs(zxx) + 1.0e-12
    geometric = np.exp(np.mean(np.log(mags), axis=0))
    arithmetic = np.mean(mags, axis=0)
    flatness = geometric / np.maximum(arithmetic, 1.0e-12)
    return float(np.median(flatness)) if flatness.size else 0.0


def noise_floor_proxy_dbfs(samples: np.ndarray, sample_rate: int) -> float:
    frame_size = max(1, int(sample_rate * FRAME_MS / 1000.0))
    frames = frame_rms(samples, frame_size)
    return float(amp_db(np.percentile(frames, 10.0)))


def metrics(samples: np.ndarray, sample_rate: int) -> dict[str, float]:
    return {
        "duration_s": round(samples.shape[0] / sample_rate, 3),
        "peak_dbfs": round(float(amp_db(peak(samples))), 3),
        "rms_dbfs": round(float(amp_db(rms(samples))), 3),
        "noise_floor_proxy_dbfs": round(noise_floor_proxy_dbfs(samples, sample_rate), 3),
        "high_band_share_6k_16k": round(high_band_share(samples, sample_rate), 6),
        "spectral_flatness_median": round(spectral_flatness_median(samples, sample_rate), 6),
    }


def spectral_denoise(samples: np.ndarray, sample_rate: int, reduction_db: float, percentile: float, threshold_mult: float) -> np.ndarray:
    min_gain = float(db_amp(-reduction_db))
    nperseg = 2048
    noverlap = 1536
    output = np.zeros_like(samples, dtype=np.float32)
    for channel in range(samples.shape[1]):
        _, _, zxx = signal.stft(
            samples[:, channel],
            fs=sample_rate,
            window="hann",
            nperseg=nperseg,
            noverlap=noverlap,
            boundary="zeros",
            padded=True,
        )
        magnitude = np.abs(zxx).astype(np.float32)
        frame_energy = np.mean(magnitude, axis=0)
        noise_frames = frame_energy <= np.percentile(frame_energy, percentile)
        if not np.any(noise_frames):
            noise_frames = np.ones_like(frame_energy, dtype=bool)
        profile = np.median(magnitude[:, noise_frames], axis=1, keepdims=True) + 1.0e-9
        over = magnitude / (profile * threshold_mult)
        gate = np.clip((over - 0.35) / 0.65, 0.0, 1.0)
        gain = min_gain + (1.0 - min_gain) * gate
        _, reconstructed = signal.istft(
            zxx * gain,
            fs=sample_rate,
            window="hann",
            nperseg=nperseg,
            noverlap=noverlap,
            input_onesided=True,
            boundary=True,
        )
        if reconstructed.shape[0] < samples.shape[0]:
            reconstructed = np.pad(reconstructed, (0, samples.shape[0] - reconstructed.shape[0]))
        output[:, channel] = reconstructed[: samples.shape[0]]
    peak_value = peak(output)
    if peak_value > 0.999:
        output *= np.float32(0.999 / peak_value)
    return output.astype(np.float32)


def write_wav(path: Path, sample_rate: int, samples: np.ndarray) -> None:
    wavfile.write(path, sample_rate, wav_write_ready_float32(samples))


def build_report(payload: dict[str, Any]) -> str:
    params = payload["processing"]
    before = payload["metrics"]["before"]
    after = payload["metrics"]["after"]
    delta = payload["metrics"]["delta"]
    files = payload["files"]
    lines = [
        f"# Noise Reduction Report: {payload['source']['name']}",
        "",
        "## Summary",
        f"- Source: `{payload['source']['path']}`",
        f"- Output WAV: `{files['processed_wav']}`",
        f"- Output MP3: `{files['processed_mp3']}`",
        f"- Residual WAV: `{files['residual_wav']}`",
        f"- Strength multiplier: `{params['strength_multiplier']}`",
        f"- Reduction dB used: `{params['reduction_db']}`",
        "",
        "## Measured Metrics",
        f"- Duration: `{after['duration_s']} s`",
        f"- Peak: `{before['peak_dbfs']} dBFS -> {after['peak_dbfs']} dBFS`",
        f"- RMS: `{before['rms_dbfs']} dBFS -> {after['rms_dbfs']} dBFS`",
        f"- Noise floor proxy: `{before['noise_floor_proxy_dbfs']} dBFS -> {after['noise_floor_proxy_dbfs']} dBFS`",
        f"- High-band share (6k-16k): `{before['high_band_share_6k_16k']} -> {after['high_band_share_6k_16k']}`",
        f"- Spectral flatness median: `{before['spectral_flatness_median']} -> {after['spectral_flatness_median']}`",
        "",
        "## Delta",
        f"- Peak delta: `{delta['peak_dbfs']} dB`",
        f"- RMS delta: `{delta['rms_dbfs']} dB`",
        f"- Noise floor proxy delta: `{delta['noise_floor_proxy_dbfs']} dB`",
        f"- High-band share delta: `{delta['high_band_share_6k_16k']}`",
        f"- Spectral flatness delta: `{delta['spectral_flatness_median']}`",
        "",
        "## Repro",
        f"- Command: `{payload['command']}`",
        f"- Source SHA256: `{payload['source']['sha256']}`",
        f"- Embedded ffmpeg: `{payload['processing']['ffmpeg']}`",
    ]
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Apply reproducible spectral noise reduction to an audio asset.")
    parser.add_argument("source", help="Path to the source audio asset.")
    parser.add_argument("--strength", type=float, default=1.5, help="Noise reduction multiplier relative to the base 2.6 dB pass.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    source = Path(args.source).expanduser().resolve()
    if not source.exists():
        raise FileNotFoundError(f"source not found: {source}")

    OUTPUT_AUDIO.mkdir(parents=True, exist_ok=True)
    OUTPUT_ANALYSIS.mkdir(parents=True, exist_ok=True)

    stem_slug = slugify(source.stem)
    variant_slug = f"{stem_slug}_denoise_{str(args.strength).replace('.', 'p')}x"
    decoded_wav = OUTPUT_ANALYSIS / f"{variant_slug}_decoded.wav"
    processed_wav = OUTPUT_AUDIO / f"{variant_slug}.wav"
    processed_mp3 = OUTPUT_AUDIO / f"{variant_slug}.mp3"
    residual_wav = OUTPUT_AUDIO / f"{variant_slug}_residual.wav"
    report_json = OUTPUT_ANALYSIS / f"{variant_slug}_report.json"
    report_md = OUTPUT_ANALYSIS / f"{variant_slug}_report.md"

    audio = decode_audio(source, decoded_wav)
    before = audio.samples
    reduction_db = round(BASE_REDUCTION_DB * float(args.strength), 3)
    after = spectral_denoise(before, audio.sample_rate, reduction_db, NOISE_PERCENTILE, THRESHOLD_MULT)
    residual = before - after

    write_wav(processed_wav, audio.sample_rate, after)
    write_wav(residual_wav, audio.sample_rate, residual)
    encode_mp3(processed_wav, processed_mp3)

    before_metrics = metrics(before, audio.sample_rate)
    after_metrics = metrics(after, audio.sample_rate)
    delta_metrics = {
        key: round(after_metrics[key] - before_metrics[key], 6)
        for key in before_metrics
        if key != "duration_s"
    }

    payload = {
        "source": {
            "name": source.name,
            "path": str(source),
            "sha256": sha256(source),
            "sample_rate": audio.sample_rate,
            "channels": int(before.shape[1]),
        },
        "processing": {
            "strength_multiplier": float(args.strength),
            "reduction_db": reduction_db,
            "noise_percentile": NOISE_PERCENTILE,
            "threshold_multiplier": THRESHOLD_MULT,
            "ffmpeg": str(FFMPEG),
        },
        "metrics": {
            "before": before_metrics,
            "after": after_metrics,
            "delta": delta_metrics,
        },
        "files": {
            "processed_wav": str(processed_wav),
            "processed_mp3": str(processed_mp3),
            "residual_wav": str(residual_wav),
            "decoded_source_wav": str(decoded_wav) if audio.source_decode_path else None,
        },
        "command": " ".join(
            [
                "python3",
                str(Path(__file__).resolve()),
                str(source),
                "--strength",
                str(args.strength),
            ]
        ),
    }

    report_json.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    report_md.write_text(build_report(payload), encoding="utf-8")
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

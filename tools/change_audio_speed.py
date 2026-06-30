#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any
import re

import imageio_ffmpeg
from mutagen import File as MutagenFile
from scipy.io import wavfile


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_AUDIO = ROOT / "output" / "audio"
OUTPUT_ANALYSIS = ROOT / "output" / "audio-analysis"
FFMPEG = Path(imageio_ffmpeg.get_ffmpeg_exe())


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create a speed-changed copy of an audio file without touching the original.")
    parser.add_argument("source", help="Path to the source audio file.")
    parser.add_argument("--speed", type=float, required=True, help="Playback speed multiplier, e.g. 1.5")
    return parser.parse_args()


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    return slug or "audio"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run(command: list[str]) -> None:
    subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)


def atempo_chain(speed: float) -> str:
    if speed <= 0:
        raise ValueError("speed must be greater than 0")
    factors: list[float] = []
    remaining = speed
    while remaining > 2.0:
        factors.append(2.0)
        remaining /= 2.0
    while remaining < 0.5:
        factors.append(0.5)
        remaining /= 0.5
    factors.append(remaining)
    return ",".join(f"atempo={factor:.12g}" for factor in factors)


def audio_info(path: Path) -> dict[str, Any]:
    info = {
        "path": str(path),
        "exists": path.exists(),
        "size_bytes": path.stat().st_size if path.exists() else None,
        "duration_s": None,
        "sample_rate": None,
        "channels": None,
        "bitrate": None,
    }
    if not path.exists():
        return info
    if path.suffix.lower() in {".wav", ".wave"}:
        sample_rate, data = wavfile.read(path)
        frames = int(data.shape[0]) if getattr(data, "ndim", 1) > 0 else 0
        channels = int(data.shape[1]) if getattr(data, "ndim", 1) > 1 else 1
        info["duration_s"] = round(frames / sample_rate, 6) if sample_rate else None
        info["sample_rate"] = int(sample_rate)
        info["channels"] = channels
        return info
    audio = MutagenFile(path)
    if audio and getattr(audio, "info", None):
        meta = audio.info
        info["duration_s"] = round(getattr(meta, "length", 0.0), 6) if getattr(meta, "length", None) is not None else None
        info["sample_rate"] = getattr(meta, "sample_rate", None)
        info["channels"] = getattr(meta, "channels", None)
        info["bitrate"] = getattr(meta, "bitrate", None)
    return info


def build_report(payload: dict[str, Any]) -> str:
    source = payload["source"]
    output_wav = payload["outputs"]["wav"]
    output_mp3 = payload["outputs"]["mp3"]
    validation = payload["validation"]
    return "\n".join(
        [
            f"# Speed Change Report: {source['name']}",
            "",
            "## Summary",
            f"- Source: `{source['path']}`",
            f"- Speed: `{payload['processing']['speed']}x`",
            f"- Filter: `{payload['processing']['atempo_filter']}`",
            f"- Output WAV: `{output_wav['path']}`",
            f"- Output MP3: `{output_mp3['path']}`",
            "",
            "## Durations",
            f"- Source duration: `{source['duration_s']} s`",
            f"- WAV duration: `{output_wav['duration_s']} s`",
            f"- MP3 duration: `{output_mp3['duration_s']} s`",
            f"- Expected duration ratio: `{validation['expected_duration_ratio']}`",
            f"- Actual WAV duration ratio: `{validation['actual_wav_duration_ratio']}`",
            "",
            "## Repro",
            f"- Command: `{payload['command']}`",
            f"- Source SHA256: `{source['sha256']}`",
            f"- Embedded ffmpeg: `{payload['processing']['ffmpeg']}`",
        ]
    ) + "\n"


def main() -> int:
    args = parse_args()
    source = Path(args.source).expanduser().resolve()
    if not source.exists():
        raise FileNotFoundError(f"source not found: {source}")
    if args.speed <= 0:
        raise ValueError("speed must be greater than 0")

    OUTPUT_AUDIO.mkdir(parents=True, exist_ok=True)
    OUTPUT_ANALYSIS.mkdir(parents=True, exist_ok=True)

    speed_label = str(args.speed).replace(".", "p")
    stem_slug = slugify(source.stem)
    base_name = f"{stem_slug}_speed_{speed_label}x"
    output_wav = OUTPUT_AUDIO / f"{base_name}.wav"
    output_mp3 = OUTPUT_AUDIO / f"{base_name}.mp3"
    report_json = OUTPUT_ANALYSIS / f"{base_name}_report.json"
    report_md = OUTPUT_ANALYSIS / f"{base_name}_report.md"

    filter_chain = atempo_chain(args.speed)
    run(
        [
            str(FFMPEG),
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(source),
            "-filter:a",
            filter_chain,
            "-c:a",
            "pcm_s24le",
            str(output_wav),
        ]
    )
    run(
        [
            str(FFMPEG),
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(source),
            "-filter:a",
            filter_chain,
            "-codec:a",
            "libmp3lame",
            "-b:a",
            "320k",
            str(output_mp3),
        ]
    )

    source_info = audio_info(source)
    output_wav_info = audio_info(output_wav)
    output_mp3_info = audio_info(output_mp3)
    expected_ratio = round(1.0 / args.speed, 6)
    actual_wav_ratio = None
    if source_info["duration_s"] and output_wav_info["duration_s"]:
        actual_wav_ratio = round(output_wav_info["duration_s"] / source_info["duration_s"], 6)

    payload = {
        "source": {
            "name": source.name,
            "path": str(source),
            "sha256": sha256(source),
            "duration_s": source_info["duration_s"],
            "sample_rate": source_info["sample_rate"],
            "channels": source_info["channels"],
            "bitrate": source_info["bitrate"],
        },
        "processing": {
            "speed": args.speed,
            "atempo_filter": filter_chain,
            "ffmpeg": str(FFMPEG),
        },
        "outputs": {
            "wav": output_wav_info,
            "mp3": output_mp3_info,
        },
        "validation": {
            "expected_duration_ratio": expected_ratio,
            "actual_wav_duration_ratio": actual_wav_ratio,
        },
        "command": " ".join(
            [
                "python3",
                str(Path(__file__).resolve()),
                str(source),
                "--speed",
                str(args.speed),
            ]
        ),
    }

    report_json.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    report_md.write_text(build_report(payload), encoding="utf-8")
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

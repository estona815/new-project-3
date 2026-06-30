"""Portable audio diagnostics for GitHub integration smoke checks.

The values here are deliberately lightweight proxies. They are useful for
preflight triage on machines without the full mastering toolchain, but they must
not be labeled as LUFS, reference matching, or final QC evidence.
"""

from __future__ import annotations

import json
import math
import struct
import wave
from pathlib import Path
from typing import Any


def _empty_result(path: Path, error: str | None = None) -> dict[str, Any]:
    return {
        "path": str(path),
        "readable": False,
        "duration_seconds": None,
        "sample_rate": None,
        "channel_count": None,
        "peak": None,
        "rms": None,
        "rms_dbfs": None,
        "clipping_risk": "unknown",
        "low_energy_ratio": None,
        "backend": None,
        "warnings": [error] if error else [],
    }


def _dbfs(value: float) -> float | None:
    if value <= 0:
        return None
    return 20.0 * math.log10(min(value, 1.0))


def _risk_from_peak(peak: float | None) -> str:
    if peak is None:
        return "unknown"
    if peak >= 0.995:
        return "high"
    if peak >= 0.97:
        return "medium"
    return "low"


def _iter_normalized_samples(data: bytes, sample_width: int):
    if sample_width == 1:
        for value in data:
            yield (value - 128) / 128.0
    elif sample_width == 2:
        count = len(data) // 2
        for values in struct.iter_unpack("<h", data[: count * 2]):
            yield values[0] / 32768.0
    elif sample_width == 3:
        for index in range(0, len(data) - 2, 3):
            raw = data[index : index + 3]
            sign = b"\xff" if raw[2] & 0x80 else b"\x00"
            value = int.from_bytes(raw + sign, byteorder="little", signed=True)
            yield value / 8388608.0
    elif sample_width == 4:
        count = len(data) // 4
        for values in struct.iter_unpack("<i", data[: count * 4]):
            yield values[0] / 2147483648.0
    else:
        raise ValueError(f"unsupported WAV sample width: {sample_width}")


def _extract_with_wave(path: Path) -> dict[str, Any]:
    with wave.open(str(path), "rb") as handle:
        channels = handle.getnchannels()
        sample_rate = handle.getframerate()
        sample_width = handle.getsampwidth()
        frames = handle.getnframes()
        duration = frames / sample_rate if sample_rate else None

        chunk_size = max(sample_rate // 2, 4096)
        peak = 0.0
        rms_accum = 0.0
        sample_accum = 0
        low_energy_chunks = 0
        total_chunks = 0

        while True:
            data = handle.readframes(chunk_size)
            if not data:
                break
            total_chunks += 1
            samples = list(_iter_normalized_samples(data, sample_width))
            if not samples:
                continue
            chunk_peak = max(abs(sample) for sample in samples)
            chunk_rms = math.sqrt(sum(sample * sample for sample in samples) / len(samples))
            peak = max(peak, chunk_peak)
            rms_accum += sum(sample * sample for sample in samples)
            sample_accum += len(samples)
            if chunk_rms < 0.01:
                low_energy_chunks += 1

        rms = math.sqrt(rms_accum / sample_accum) if sample_accum else 0.0
        low_energy_ratio = low_energy_chunks / total_chunks if total_chunks else None

    return {
        "path": str(path),
        "readable": True,
        "duration_seconds": duration,
        "sample_rate": sample_rate,
        "channel_count": channels,
        "peak": min(peak, 1.0),
        "rms": min(rms, 1.0),
        "rms_dbfs": _dbfs(rms),
        "clipping_risk": _risk_from_peak(peak),
        "low_energy_ratio": low_energy_ratio,
        "backend": "wave",
        "warnings": [],
    }


def _extract_with_soundfile(path: Path, wave_error: str) -> dict[str, Any]:
    import numpy as np  # type: ignore
    import soundfile as sf  # type: ignore

    data, sample_rate = sf.read(str(path), always_2d=True)
    if data.size == 0:
        return _empty_result(path, "audio file contained no samples")

    peak = float(np.max(np.abs(data)))
    rms = float(np.sqrt(np.mean(np.square(data))))
    duration = float(data.shape[0] / sample_rate) if sample_rate else None
    frame_size = max(int(sample_rate * 0.5), 1)
    low_chunks = 0
    total_chunks = 0

    for start in range(0, data.shape[0], frame_size):
        chunk = data[start : start + frame_size]
        if chunk.size == 0:
            continue
        total_chunks += 1
        chunk_rms = float(np.sqrt(np.mean(np.square(chunk))))
        if chunk_rms < 0.01:
            low_chunks += 1

    return {
        "path": str(path),
        "readable": True,
        "duration_seconds": duration,
        "sample_rate": int(sample_rate) if sample_rate else None,
        "channel_count": int(data.shape[1]),
        "peak": min(peak, 1.0),
        "rms": min(rms, 1.0),
        "rms_dbfs": _dbfs(rms),
        "clipping_risk": _risk_from_peak(peak),
        "low_energy_ratio": low_chunks / total_chunks if total_chunks else None,
        "backend": "soundfile",
        "warnings": [wave_error],
    }


def extract_features(audio_path: str | Path) -> dict[str, Any]:
    """Extract JSON-safe basic diagnostics from an audio file."""

    path = Path(audio_path)
    if not path.exists():
        return _empty_result(path, "file does not exist")

    suffix = path.suffix.lower()
    if suffix == ".wav":
        try:
            return _extract_with_wave(path)
        except Exception as exc:
            wave_error = f"wave backend failed: {exc}"
    else:
        wave_error = "wave backend supports only .wav files"

    try:
        return _extract_with_soundfile(path, wave_error)
    except Exception as exc:
        return _empty_result(
            path,
            f"{wave_error}; optional soundfile/numpy backend unavailable or failed: {exc}",
        )


def estimate_loudness_proxy(features: dict[str, Any]) -> dict[str, Any]:
    """Return an RMS-derived loudness proxy, explicitly not LUFS."""

    rms_dbfs = features.get("rms_dbfs")
    peak = features.get("peak")
    warnings = ["proxy_not_lufs: RMS-derived estimate, not ITU BS.1770 LUFS"]

    if rms_dbfs is None:
        return {
            "kind": "proxy_not_lufs",
            "integrated_loudness_proxy_db": None,
            "dynamic_headroom_proxy_db": None,
            "warnings": warnings + ["RMS unavailable"],
        }

    peak_db = None
    if isinstance(peak, (int, float)) and peak > 0:
        peak_db = 20.0 * math.log10(min(float(peak), 1.0))

    headroom = peak_db - float(rms_dbfs) if peak_db is not None else None
    return {
        "kind": "proxy_not_lufs",
        "integrated_loudness_proxy_db": float(rms_dbfs),
        "dynamic_headroom_proxy_db": headroom,
        "warnings": warnings,
    }


def analyze_spectrum(audio_path: str | Path) -> dict[str, Any]:
    """Return coarse spectral diagnostics when optional libraries exist."""

    path = Path(audio_path)
    try:
        import numpy as np  # type: ignore
        import soundfile as sf  # type: ignore
    except Exception as exc:
        return {
            "available": False,
            "backend": None,
            "spectral_centroid_hz_proxy": None,
            "high_frequency_energy_ratio_proxy": None,
            "warnings": [f"optional numpy/soundfile backend unavailable: {exc}"],
        }

    try:
        data, sample_rate = sf.read(str(path), always_2d=True)
        if data.size == 0:
            raise ValueError("audio file contained no samples")
        mono = np.mean(data, axis=1)
        window = mono[: min(len(mono), sample_rate * 30)]
        if window.size == 0:
            raise ValueError("audio file contained no analysis window")
        spectrum = np.abs(np.fft.rfft(window))
        freqs = np.fft.rfftfreq(window.size, d=1.0 / sample_rate)
        total = float(np.sum(spectrum))
        high_mask = freqs >= 8000.0
        return {
            "available": True,
            "backend": "numpy+soundfile",
            "spectral_centroid_hz_proxy": float(np.sum(freqs * spectrum) / total) if total else None,
            "high_frequency_energy_ratio_proxy": float(np.sum(spectrum[high_mask]) / total) if total else None,
            "warnings": ["proxy values are coarse diagnostics, not mastering-grade measurements"],
        }
    except Exception as exc:
        return {
            "available": False,
            "backend": "numpy+soundfile",
            "spectral_centroid_hz_proxy": None,
            "high_frequency_energy_ratio_proxy": None,
            "warnings": [f"spectral analysis failed gracefully: {exc}"],
        }


def _score_to_level(score: int) -> str:
    if score >= 5:
        return "high"
    if score >= 3:
        return "medium"
    return "low"


def detect_vocal_artifacts(
    features: dict[str, Any],
    spectral: dict[str, Any] | None = None,
    loudness: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return conservative heuristic artifact risk labels and explanations."""

    spectral = spectral or {}
    loudness = loudness or {}
    explanations: list[str] = []
    score = 0

    peak = features.get("peak")
    clipping_risk = features.get("clipping_risk")
    rms_dbfs = features.get("rms_dbfs")
    low_energy_ratio = features.get("low_energy_ratio")
    headroom = loudness.get("dynamic_headroom_proxy_db")
    high_ratio = spectral.get("high_frequency_energy_ratio_proxy")
    centroid = spectral.get("spectral_centroid_hz_proxy")

    if clipping_risk == "high" or (isinstance(peak, (int, float)) and peak >= 0.995):
        score += 2
        explanations.append("clipped_or_limited_master_like_source: peak is extremely close to full scale")
    elif clipping_risk == "medium":
        score += 1
        explanations.append("possible_limiter_pressure: peak leaves little safety margin")

    if isinstance(rms_dbfs, (int, float)) and rms_dbfs > -12:
        score += 1
        explanations.append("over_compressed_dynamics_risk: RMS proxy is very loud for repair input")

    if isinstance(headroom, (int, float)) and headroom < 8:
        score += 1
        explanations.append("limited_dynamic_headroom_proxy: peak-to-RMS gap is narrow")

    if isinstance(high_ratio, (int, float)) and high_ratio > 0.18:
        score += 2
        explanations.append("harsh_high_frequency_fizz_risk: high-frequency energy proxy is elevated")

    if isinstance(centroid, (int, float)) and centroid > 5500:
        score += 1
        explanations.append("smeared_vocal_clarity_risk: spectral centroid proxy is unusually bright")

    if isinstance(low_energy_ratio, (int, float)) and 0.02 < low_energy_ratio < 0.35:
        score += 1
        explanations.append("unstable_noise_floor_risk: alternating low-energy sections may expose artifacts")

    if not explanations:
        explanations.append("no strong artifact indicators from available lightweight diagnostics")

    return {
        "risk_level": _score_to_level(score),
        "risk_score": score,
        "heuristics": {
            "harsh_high_frequency_fizz": "high_frequency_energy_ratio_proxy",
            "unstable_noise_floor": "low_energy_ratio",
            "over_compressed_dynamics": "rms_dbfs and dynamic_headroom_proxy_db",
            "clipped_limited_source": "peak and clipping_risk",
            "smeared_vocal_clarity": "spectral_centroid_hz_proxy",
        },
        "explanations": explanations,
        "warnings": [
            "heuristic detector only; confirm with listening tests and A/B renders",
            "do not aggressively denoise or thin vocal body based on this score alone",
        ],
    }


def build_audio_diagnostic_report(audio_path: str | Path) -> dict[str, Any]:
    """Build a self-contained portable audio diagnostic report."""

    features = extract_features(audio_path)
    spectral = (
        analyze_spectrum(audio_path)
        if features.get("readable")
        else {
            "available": False,
            "backend": None,
            "warnings": ["spectral diagnostics skipped because audio was not readable"],
        }
    )
    loudness = estimate_loudness_proxy(features)
    artifact_risk = detect_vocal_artifacts(features, spectral=spectral, loudness=loudness)
    return {
        "schema": "automix-github-integration-audio-diagnostics-v1",
        "status": "report_only",
        "claim_limits": [
            "not_lufs",
            "not_reference_matching",
            "not_final_qc_evidence",
            "human_ab_review_required",
        ],
        "features": features,
        "spectral": spectral,
        "loudness": loudness,
        "artifact_risk": artifact_risk,
    }


def write_audio_diagnostic_report(
    report: dict[str, Any],
    output_dir: str | Path,
    *,
    stem: str = "github_audio_diagnostics",
) -> dict[str, str]:
    """Write diagnostic JSON and Markdown reports under a chosen output dir."""

    path = Path(output_dir)
    path.mkdir(parents=True, exist_ok=True)
    json_path = path / f"{stem}.json"
    md_path = path / f"{stem}.md"
    json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    md_path.write_text(_to_markdown(report), encoding="utf-8")
    return {"json": str(json_path), "markdown": str(md_path)}


def _to_markdown(report: dict[str, Any]) -> str:
    features = report.get("features", {})
    loudness = report.get("loudness", {})
    artifact = report.get("artifact_risk", {})
    spectral = report.get("spectral", {})

    lines = [
        "# GitHub Integration Audio Diagnostics",
        "",
        "## Status",
        "",
        f"- Schema: `{report.get('schema')}`",
        f"- Status: `{report.get('status')}`",
        f"- Claim limits: `{', '.join(report.get('claim_limits', []))}`",
        "",
        "## Summary",
        "",
        f"- Path: `{features.get('path')}`",
        f"- Readable: `{features.get('readable')}`",
        f"- Duration seconds: `{features.get('duration_seconds')}`",
        f"- Sample rate: `{features.get('sample_rate')}`",
        f"- Channels: `{features.get('channel_count')}`",
        f"- Peak: `{features.get('peak')}`",
        f"- RMS dBFS: `{features.get('rms_dbfs')}`",
        f"- Clipping risk: `{features.get('clipping_risk')}`",
        "",
        "## Loudness Proxy",
        "",
        f"- Kind: `{loudness.get('kind')}`",
        f"- Integrated loudness proxy dB: `{loudness.get('integrated_loudness_proxy_db')}`",
        f"- Dynamic headroom proxy dB: `{loudness.get('dynamic_headroom_proxy_db')}`",
        "",
        "## Spectral Diagnostics",
        "",
        f"- Available: `{spectral.get('available')}`",
        f"- Backend: `{spectral.get('backend')}`",
        f"- Spectral centroid Hz proxy: `{spectral.get('spectral_centroid_hz_proxy')}`",
        f"- High-frequency energy ratio proxy: `{spectral.get('high_frequency_energy_ratio_proxy')}`",
        "",
        "## Vocal Artifact Risk",
        "",
        f"- Risk level: `{artifact.get('risk_level')}`",
        f"- Risk score: `{artifact.get('risk_score')}`",
        "",
        "### Explanations",
        "",
    ]
    lines.extend(f"- {item}" for item in artifact.get("explanations", []))
    lines.extend(["", "## Warnings", ""])
    for section in (features, loudness, spectral, artifact):
        for warning in section.get("warnings", []):
            lines.append(f"- {warning}")
    lines.append("")
    return "\n".join(lines)

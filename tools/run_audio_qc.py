#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

import numpy as np
import pyloudnorm as pyln
import soundfile as sf
from scipy import signal


EPS = 1e-12


def dbfs(value: float) -> float:
    return 20.0 * math.log10(max(float(value), EPS))


def load_audio(path: Path) -> tuple[np.ndarray, int]:
    data, sr = sf.read(path, always_2d=True)
    if data.size == 0:
        raise ValueError(f"Empty audio file: {path}")
    return data.astype(np.float64), int(sr)


def spectral_metrics(mono: np.ndarray, sr: int) -> dict[str, float]:
    freqs, _, spec = signal.spectrogram(
        mono,
        fs=sr,
        window="hann",
        nperseg=min(4096, max(256, len(mono))),
        noverlap=None,
        scaling="spectrum",
        mode="magnitude",
    )
    mag = np.mean(spec, axis=1) if spec.ndim == 2 else spec
    mag_sum = float(np.sum(mag)) + EPS
    centroid = float(np.sum(freqs * mag) / mag_sum)

    power = np.square(mag)
    total_power = float(np.sum(power[(freqs >= 20) & (freqs <= min(20000, sr / 2))])) + EPS
    high_power = float(np.sum(power[(freqs >= 8000) & (freqs <= min(20000, sr / 2))]))
    return {
        "spectral_centroid_hz": round(centroid, 3),
        "high_frequency_energy_ratio_8k_20k": round(high_power / total_power, 6),
    }


def analyze(path: Path) -> dict[str, Any]:
    data, sr = load_audio(path)
    channels = int(data.shape[1])
    mono = np.mean(data, axis=1)
    duration = len(data) / sr

    peak = float(np.max(np.abs(data)))
    rms = float(np.sqrt(np.mean(np.square(data))))
    crest = dbfs(peak) - dbfs(rms)
    dc_offset = float(np.max(np.abs(np.mean(data, axis=0))))

    meter = pyln.Meter(sr)
    try:
        lufs = float(meter.integrated_loudness(data if channels > 1 else mono))
    except Exception:
        lufs = float(meter.integrated_loudness(mono))

    # Approximate true peak by 4x oversampling. This is not a certified ITU meter,
    # but it catches common inter-sample overs.
    oversampled = signal.resample_poly(data, 4, 1, axis=0)
    true_peak = float(np.max(np.abs(oversampled)))

    corr: float | None = None
    if channels >= 2:
        left = data[:, 0]
        right = data[:, 1]
        if np.std(left) > EPS and np.std(right) > EPS:
            corr = float(np.corrcoef(left, right)[0, 1])

    metrics: dict[str, Any] = {
        "file": str(path),
        "sample_rate": sr,
        "channels": channels,
        "duration_s": round(duration, 3),
        "integrated_lufs": round(lufs, 3),
        "peak_dbfs": round(dbfs(peak), 3),
        "approx_true_peak_dbfs": round(dbfs(true_peak), 3),
        "rms_dbfs": round(dbfs(rms), 3),
        "crest_factor_db": round(crest, 3),
        "dc_offset": round(dc_offset, 8),
        "stereo_correlation": round(corr, 6) if corr is not None else None,
    }
    metrics.update(spectral_metrics(mono, sr))
    metrics["warning_flags"] = warning_flags(metrics)
    return metrics


def warning_flags(metrics: dict[str, Any]) -> dict[str, bool]:
    lufs = float(metrics["integrated_lufs"])
    peak = float(metrics["peak_dbfs"])
    true_peak = float(metrics["approx_true_peak_dbfs"])
    corr = metrics.get("stereo_correlation")
    high_ratio = float(metrics["high_frequency_energy_ratio_8k_20k"])
    return {
        "too_loud": lufs > -7.0 or true_peak > -0.5,
        "too_quiet": lufs < -18.0,
        "possible_clipping": peak >= -0.1 or true_peak >= 0.0,
        "excessive_high_frequency_hash": high_ratio > 0.18,
        "mono_incompatibility_risk": bool(corr is not None and corr < 0.15),
        "vocal_beat_balance_cannot_be_judged_without_stems": True,
    }


def reference_delta(target: dict[str, Any], reference: dict[str, Any]) -> dict[str, Any]:
    keys = [
        "integrated_lufs",
        "peak_dbfs",
        "approx_true_peak_dbfs",
        "rms_dbfs",
        "crest_factor_db",
        "spectral_centroid_hz",
        "high_frequency_energy_ratio_8k_20k",
        "stereo_correlation",
    ]
    delta: dict[str, Any] = {}
    for key in keys:
        if target.get(key) is not None and reference.get(key) is not None:
            delta[key] = round(float(target[key]) - float(reference[key]), 6)
    return delta


def write_markdown(path: Path, result: dict[str, Any]) -> None:
    target = result["target"]
    lines = [
        "# Audio QC Report",
        "",
        f"- Target: `{target['file']}`",
        f"- Sample rate: `{target['sample_rate']}`",
        f"- Channels: `{target['channels']}`",
        f"- Duration: `{target['duration_s']} s`",
        "",
        "## Metrics",
        "",
        "| metric | value |",
        "| --- | ---: |",
    ]
    for key in [
        "integrated_lufs",
        "peak_dbfs",
        "approx_true_peak_dbfs",
        "rms_dbfs",
        "crest_factor_db",
        "dc_offset",
        "stereo_correlation",
        "spectral_centroid_hz",
        "high_frequency_energy_ratio_8k_20k",
    ]:
        lines.append(f"| {key} | {target.get(key)} |")

    lines.extend(["", "## Warning Flags", ""])
    for key, value in target["warning_flags"].items():
        lines.append(f"- `{key}`: `{value}`")

    if "reference" in result:
        lines.extend(["", "## Reference", "", f"- Reference: `{result['reference']['file']}`", "", "## Delta Target Minus Reference", "", "| metric | delta |", "| --- | ---: |"])
        for key, value in result["delta_target_minus_reference"].items():
            lines.append(f"| {key} | {value} |")

    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Production-safe audio QC metrics for REAPER renders.")
    parser.add_argument("input", type=Path)
    parser.add_argument("--reference", type=Path)
    parser.add_argument("--out", type=Path, required=True, help="Output stem without extension.")
    args = parser.parse_args()

    result: dict[str, Any] = {"target": analyze(args.input)}
    if args.reference:
        result["reference"] = analyze(args.reference)
        result["delta_target_minus_reference"] = reference_delta(result["target"], result["reference"])

    json_path = args.out.with_suffix(".json")
    md_path = args.out.with_suffix(".md")
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_markdown(md_path, result)
    print(json.dumps({"json": str(json_path), "markdown": str(md_path)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

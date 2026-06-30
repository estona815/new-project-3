#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import math
from pathlib import Path
from typing import Any


def linear_to_db(value: float | None) -> float | None:
    if value is None or value <= 0 or not math.isfinite(value):
        return None
    return 20.0 * math.log10(value)


def empty_row(path: Path, status: str, reason: str) -> dict[str, Any]:
    return {
        "path": str(path),
        "status": status,
        "reason": reason,
        "sample_rate": "",
        "duration_seconds": "",
        "channels": "",
        "lufs_i": "",
        "sample_peak_dbfs": "",
        "spectral_centroid_hz": "",
        "spectral_rolloff_hz": "",
        "low_energy_ratio_20_120": "",
        "mid_energy_ratio_120_2500": "",
        "high_energy_ratio_2500_16000": "",
        "stereo_correlation": "",
    }


def band_energy_ratio(mono, sample_rate: int, low: float, high: float) -> float:
    import numpy as np

    if mono.size == 0:
        return 0.0
    window = np.hanning(mono.size)
    spectrum = np.abs(np.fft.rfft(mono * window)) ** 2
    freqs = np.fft.rfftfreq(mono.size, 1.0 / sample_rate)
    total = float(spectrum.sum()) or 1.0
    return float(spectrum[(freqs >= low) & (freqs < high)].sum()) / total


def spectral_features(mono, sample_rate: int) -> tuple[float | None, float | None]:
    import numpy as np

    try:
        import librosa

        centroid = librosa.feature.spectral_centroid(y=mono.astype(float), sr=sample_rate)
        rolloff = librosa.feature.spectral_rolloff(y=mono.astype(float), sr=sample_rate, roll_percent=0.85)
        return float(np.nanmean(centroid)), float(np.nanmean(rolloff))
    except Exception:
        if mono.size == 0:
            return None, None
        spectrum = np.abs(np.fft.rfft(mono * np.hanning(mono.size)))
        freqs = np.fft.rfftfreq(mono.size, 1.0 / sample_rate)
        total = float(spectrum.sum())
        if total <= 0:
            return None, None
        centroid = float((freqs * spectrum).sum() / total)
        cumsum = np.cumsum(spectrum)
        idx = int(np.searchsorted(cumsum, total * 0.85))
        idx = min(idx, len(freqs) - 1)
        return centroid, float(freqs[idx])


def analyze(path: Path) -> dict[str, Any]:
    if not path.exists():
        return empty_row(path, "missing", "file does not exist")
    try:
        import numpy as np
        import soundfile as sf

        data, sample_rate = sf.read(str(path), always_2d=True, dtype="float64")
        data = np.asarray(data)
    except Exception as exc:
        return empty_row(path, "decode_failed", str(exc))

    if data.size == 0:
        return empty_row(path, "decode_failed", "decoded audio is empty")

    mono = data.mean(axis=1)
    peak = float(np.max(np.abs(data)))
    duration = float(len(data) / sample_rate) if sample_rate else 0.0
    channels = int(data.shape[1])

    lufs_i: float | None = None
    lufs_reason = ""
    try:
        import pyloudnorm as pyln

        meter = pyln.Meter(sample_rate)
        lufs_i = float(meter.integrated_loudness(data))
    except Exception as exc:
        lufs_reason = f"pyloudnorm unavailable or failed: {exc}"

    if channels >= 2 and data[:, 0].std() > 0 and data[:, 1].std() > 0:
        correlation: float | None = float(np.corrcoef(data[:, 0], data[:, 1])[0, 1])
    else:
        correlation = None

    centroid, rolloff = spectral_features(mono, sample_rate)
    low_ratio = band_energy_ratio(mono, sample_rate, 20, 120)
    mid_ratio = band_energy_ratio(mono, sample_rate, 120, 2500)
    high_ratio = band_energy_ratio(mono, sample_rate, 2500, 16000)

    status = "measured" if lufs_i is not None else "partial"
    return {
        "path": str(path),
        "status": status,
        "reason": lufs_reason,
        "sample_rate": sample_rate,
        "duration_seconds": round(duration, 3),
        "channels": channels,
        "lufs_i": round(lufs_i, 3) if lufs_i is not None else "",
        "sample_peak_dbfs": round(linear_to_db(peak) or -999.0, 3),
        "spectral_centroid_hz": round(centroid, 3) if centroid is not None else "",
        "spectral_rolloff_hz": round(rolloff, 3) if rolloff is not None else "",
        "low_energy_ratio_20_120": round(low_ratio, 6),
        "mid_energy_ratio_120_2500": round(mid_ratio, 6),
        "high_energy_ratio_2500_16000": round(high_ratio, 6),
        "stereo_correlation": round(correlation, 6) if correlation is not None else "",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Analyze user-owned reference or render audio into CSV features.")
    parser.add_argument("audio", nargs="+", type=Path)
    parser.add_argument("--output", type=Path, default=Path("reports/reference_analysis.csv"))
    args = parser.parse_args()

    rows = [analyze(path.expanduser()) for path in args.audio]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    failed = [row for row in rows if row["status"] in {"missing", "decode_failed"}]
    print(f"wrote {args.output} ({len(rows)} row(s), {len(failed)} failed)")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())

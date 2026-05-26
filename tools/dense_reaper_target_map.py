#!/usr/bin/env python3
"""Generate dense reference target control points for REAPER automation.

Creates many narrow-ish log-spaced EQ/M/S/dynamic EQ targets. These are target
ranges, not instructions to copy the reference or apply hundreds of filters.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Iterable, List, Tuple

import numpy as np
import soundfile as sf
from scipy import signal


PROJECT_ROOT = Path("/Users/hantaeheuk/Documents/New project 3")
INPUT_DIRS = [PROJECT_ROOT / "00_AUDIO_INPUT", Path("/Users/hantaeheuk/Desktop/Estona-4dium_MASTER_24-48.")]
REPORTS_DIR = PROJECT_ROOT / "reports"
AUDIO_EXTENSIONS = {".wav", ".wave", ".aif", ".aiff", ".flac", ".mp3", ".m4a"}
EPS = 1e-12


def db_power(x: float) -> float:
    return 10.0 * math.log10(max(float(x), EPS))


def dist(values: Iterable[float]) -> dict:
    arr = np.asarray([x for x in values if np.isfinite(x)], dtype=float)
    if arr.size == 0:
        return {"median": None, "low": None, "high": None, "min": None, "max": None}
    return {
        "median": float(np.median(arr)),
        "low": float(np.percentile(arr, 25)),
        "high": float(np.percentile(arr, 75)),
        "min": float(np.min(arr)),
        "max": float(np.max(arr)),
    }


def reference_files() -> List[Path]:
    files = []
    for folder in INPUT_DIRS:
        if folder.exists():
            files.extend(p for p in folder.iterdir() if p.is_file() and p.suffix.lower() in AUDIO_EXTENSIONS)
    return sorted({p.resolve(): p for p in files}.values())


def log_bands(points_per_octave: int = 24, low: float = 25.0, high: float = 19000.0) -> List[Tuple[float, float, float]]:
    centers = []
    f = low
    step = 2 ** (1 / points_per_octave)
    while f <= high:
        centers.append(f)
        f *= step
    bands = []
    half = 2 ** (1 / (points_per_octave * 2))
    for center in centers:
        bands.append((center / half, center, min(high, center * half)))
    return bands


def welch(x: np.ndarray, sr: int) -> Tuple[np.ndarray, np.ndarray]:
    nperseg = min(16384, max(2048, int(sr * 0.25)))
    return signal.welch(x, fs=sr, nperseg=nperseg, noverlap=nperseg // 2)


def band_power(freqs: np.ndarray, pxx: np.ndarray, low: float, high: float) -> float:
    mask = (freqs >= low) & (freqs < high)
    if not np.any(mask):
        center = (low * high) ** 0.5
        width = max(high - low, 1.0)
        interp = float(np.interp(center, freqs, pxx))
        return float(interp * width + EPS)
    return float(np.sum(pxx[mask]) + EPS)


def stft_power(x: np.ndarray, sr: int) -> Tuple[np.ndarray, np.ndarray]:
    freqs, _, zxx = signal.stft(x, fs=sr, nperseg=4096, noverlap=3072, boundary=None)
    return freqs, np.abs(zxx) ** 2


def analyze_one(path: Path, bands: List[Tuple[float, float, float]]) -> dict:
    audio, sr = sf.read(str(path), always_2d=True, dtype="float64")
    mono = audio.mean(axis=1)
    mid = (audio[:, 0] + audio[:, 1]) * 0.5 if audio.shape[1] > 1 else mono
    side = (audio[:, 0] - audio[:, 1]) * 0.5 if audio.shape[1] > 1 else np.zeros_like(mono)
    f_mono, p_mono = welch(mono, sr)
    f_mid, p_mid = welch(mid, sr)
    f_side, p_side = welch(side, sr)
    sfreq, stft = stft_power(mono, sr)
    total = float(np.sum(p_mono) + EPS)
    frame_total = np.sum(stft, axis=0) + EPS
    rows = []
    for idx, (low, center, high) in enumerate(bands):
        bp = band_power(f_mono, p_mono, low, high)
        mp = band_power(f_mid, p_mid, low, high)
        sp = band_power(f_side, p_side, low, high)
        mask = (sfreq >= low) & (sfreq < high)
        if np.any(mask):
            frame_band = np.sum(stft[mask], axis=0) + EPS
        else:
            nearest = int(np.argmin(np.abs(sfreq - center)))
            width = max(high - low, 1.0)
            frame_band = stft[nearest] * width + EPS
        rel = 10.0 * np.log10(frame_band / frame_total)
        dyn = float(np.percentile(rel, 90) - np.percentile(rel, 10))
        burst = float(np.percentile(rel, 95) - np.percentile(rel, 50))
        rows.append({
            "index": idx,
            "low_hz": low,
            "center_hz": center,
            "high_hz": high,
            "relative_power_db": db_power(bp / total),
            "mid_power_db": db_power(mp),
            "side_minus_mid_db": db_power(sp / max(mp, EPS)),
            "dynamic_range_db": dyn,
            "burstiness_db": burst,
        })
    return {"filename": path.name, "sample_rate": sr, "bands": rows}


def aggregate(files: List[dict], bands: List[Tuple[float, float, float]]) -> List[dict]:
    control_points = []
    for idx, (low, center, high) in enumerate(bands):
        rows = [f["bands"][idx] for f in files]
        rel = dist(r["relative_power_db"] for r in rows)
        side = dist(r["side_minus_mid_db"] for r in rows)
        dyn = dist(r["dynamic_range_db"] for r in rows)
        burst = dist(r["burstiness_db"] for r in rows)
        if center < 120:
            module = "MonoSub/M-S low control"
        elif 120 <= center < 350:
            module = "ReaEQ/ReaXcomp mud control"
        elif 2000 <= center < 8000:
            module = "ReaXcomp presence/harsh dynamic EQ"
        elif center >= 8000:
            module = "Air/hash smoothing"
        else:
            module = "ReaEQ broad tonal control"
        control_points.append({
            "index": idx,
            "center_hz": round(center, 2),
            "low_hz": round(low, 2),
            "high_hz": round(high, 2),
            "target_relative_power_db": rel,
            "target_side_minus_mid_db": side,
            "target_dynamic_range_db": dyn,
            "target_burstiness_db": burst,
            "reaper_module": module,
            "confidence": "reference_target_only_no_current_mix",
        })
    return control_points


def resonance_clusters(files: List[dict], max_points: int = 80) -> List[dict]:
    # Use local maxima in the dense target curve as watch frequencies.
    med = np.array([p["target_relative_power_db"]["median"] for p in files], dtype=float)
    centers = np.array([p["center_hz"] for p in files], dtype=float)
    smooth = signal.medfilt(med, kernel_size=9)
    prominence = med - smooth
    peaks, props = signal.find_peaks(prominence, height=0.8, distance=2)
    rows = []
    for p in peaks:
        rows.append({
            "center_hz": float(centers[p]),
            "prominence_over_local_curve_db": float(prominence[p]),
            "target_relative_power_db": float(med[p]),
            "suggested_use": "watch frequency for current-vs-reference comparison, not an automatic cut",
        })
    return sorted(rows, key=lambda x: x["prominence_over_local_curve_db"], reverse=True)[:max_points]


def write_reports(data: dict) -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    (REPORTS_DIR / "dense_reaper_control_map.json").write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    lines = [
        "# Dense REAPER Control Map",
        "",
        "This map contains many measured control points. They are target ranges for automation, not proof of exact plugin settings.",
        "",
        f"- Source files: {len(data['source_files'])}",
        f"- Dense EQ/M-S/dynamic points: {len(data['control_points'])}",
        f"- Resonance watch points: {len(data['resonance_watch_points'])}",
        "",
        "## Example Control Points",
    ]
    for point in data["control_points"][:: max(1, len(data["control_points"]) // 18)]:
        lines.append(
            f"- {point['center_hz']} Hz: target {point['target_relative_power_db']['median']:.2f} dB share, side-mid {point['target_side_minus_mid_db']['median']:.2f} dB, {point['reaper_module']}"
        )
    lines += ["", "## Strongest Resonance Watch Points"]
    for row in data["resonance_watch_points"][:30]:
        lines.append(
            f"- {row['center_hz']:.1f} Hz: local prominence {row['prominence_over_local_curve_db']:.2f} dB, target level {row['target_relative_power_db']:.2f} dB"
        )
    lines += [
        "",
        "## How To Use",
        "- When `current_mix.wav` exists, compare its dense map to this reference map.",
        "- Only automate bands with meaningful deltas, grouped into a small number of musical moves.",
        "- Do not instantiate hundreds of ReaEQ bands blindly; use this as a measurement grid.",
    ]
    (REPORTS_DIR / "dense_reaper_control_map.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    bands = log_bands(points_per_octave=24)
    paths = reference_files()
    analyzed = [analyze_one(path, bands) for path in paths]
    points = aggregate(analyzed, bands)
    data = {
        "status": "reference_dense_target_only",
        "source_files": [str(p) for p in paths],
        "control_points": points,
        "resonance_watch_points": resonance_clusters(points),
        "policy": {
            "do_not_copy_reference_music": True,
            "do_not_apply_all_points_blindly": True,
            "current_mix_required_for_exact_moves": True,
        },
    }
    write_reports(data)
    print(json.dumps({"control_points": len(points), "resonance_watch_points": len(data["resonance_watch_points"])}, indent=2))


if __name__ == "__main__":
    main()

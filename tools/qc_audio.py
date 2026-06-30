#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

try:
    from .schemas import QC_JSON_PATH, blocked_qc_report, ensure_harness_dirs, linear_to_db, now_iso, write_json, write_qc_markdown
except ImportError:
    from schemas import QC_JSON_PATH, blocked_qc_report, ensure_harness_dirs, linear_to_db, now_iso, write_json, write_qc_markdown


def _read_wav_float(path: Path):
    try:
        import numpy as np
        import soundfile as sf

        data, sample_rate = sf.read(str(path), always_2d=True, dtype="float64")
        return np.asarray(data), int(sample_rate), None
    except Exception as exc:
        return None, None, f"audio decode failed or dependencies unavailable: {exc}"


def _band_share(data, sample_rate: int, low_hz: float, high_hz: float) -> float:
    import numpy as np

    mono = data.mean(axis=1)
    if mono.size == 0:
        return 0.0
    window = np.hanning(mono.size)
    spectrum = np.abs(np.fft.rfft(mono * window)) ** 2
    freqs = np.fft.rfftfreq(mono.size, 1.0 / sample_rate)
    total = float(spectrum.sum()) or 1.0
    band = float(spectrum[(freqs >= low_hz) & (freqs <= high_hz)].sum())
    return band / total


def analyze_audio(path: Path) -> dict:
    if not path.exists():
        return blocked_qc_report(path, "render file does not exist")
    data, sample_rate, error = _read_wav_float(path)
    if error:
        return blocked_qc_report(path, error)

    import numpy as np

    if data.shape[1] == 1:
        left = right = data[:, 0]
    else:
        left = data[:, 0]
        right = data[:, 1]
    sample_peak = float(np.max(np.abs(data))) if data.size else 0.0
    mono = data.mean(axis=1)
    mono_peak = float(np.max(np.abs(mono))) if mono.size else 0.0
    left_rms = float(np.sqrt(np.mean(left**2))) if left.size else 0.0
    right_rms = float(np.sqrt(np.mean(right**2))) if right.size else 0.0
    lr_delta = abs((linear_to_db(left_rms) or -120.0) - (linear_to_db(right_rms) or -120.0))
    if left.size and right.size and left.std() > 0 and right.std() > 0:
        corr = float(np.corrcoef(left, right)[0, 1])
    else:
        corr = None

    integrated_lufs = None
    lufs_reason = "pyloudnorm unavailable"
    try:
        import pyloudnorm as pyln

        meter = pyln.Meter(sample_rate)
        integrated_lufs = float(meter.integrated_loudness(data))
        lufs_reason = None
    except Exception as exc:
        lufs_reason = f"pyloudnorm unavailable or failed: {exc}"

    harshness = _band_share(data, sample_rate, 2500, 6000)
    sibilance = _band_share(data, sample_rate, 5000, 10000)
    metrics = {
        "integrated_lufs": {"value": integrated_lufs, "unit": "LUFS", "status": "available" if integrated_lufs is not None else "unavailable", "reason": lufs_reason},
        "true_peak_db_tp": {"value": None, "unit": "dBTP", "status": "unavailable", "reason": "true peak oversampling is not implemented in this harness"},
        "sample_peak_dbfs": {"value": linear_to_db(sample_peak), "unit": "dBFS", "status": "available", "reason": None},
        "lr_rms_delta_db": {"value": lr_delta, "unit": "dB", "status": "available", "reason": None},
        "stereo_correlation": {"value": corr, "unit": "", "status": "available" if corr is not None else "unavailable", "reason": None if corr is not None else "mono or silent file"},
        "mono_peak_dbfs": {"value": linear_to_db(mono_peak), "unit": "dBFS", "status": "available", "reason": None},
        "mono_loudness_delta_db": {"value": None, "unit": "dB", "status": "unavailable", "reason": "mono loudness delta requires LUFS on stereo and mono paths"},
        "female_vs_male_level_delta_db": {"value": None, "unit": "dB", "status": "unavailable", "reason": "requires comparable isolated male/female assets"},
        "harshness_band_result": {"value": harshness, "unit": "share", "status": "available", "reason": "FFT band share approximation"},
        "sibilance_band_result": {"value": sibilance, "unit": "share", "status": "available", "reason": "FFT band share approximation"},
    }
    return {
        "timestamp": now_iso(),
        "status": "MEASURED",
        "audio_path": str(path),
        "sample_rate": sample_rate,
        "channels": int(data.shape[1]),
        "metrics": metrics,
        "summary": "Metrics are file-derived; true peak and isolated vocal balance remain unavailable unless separately measured.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Measure final render QC.")
    parser.add_argument("audio_path", nargs="?", default="work/renders/final_24bit_48k.wav")
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    args = parser.parse_args()
    root = Path(args.root).resolve()
    ensure_harness_dirs(root)
    path = Path(args.audio_path)
    if not path.is_absolute():
        path = root / path
    report = analyze_audio(path)
    write_json(root / QC_JSON_PATH.relative_to(Path(__file__).resolve().parents[1]), report)
    write_qc_markdown(report)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] != "BLOCKED" else 2


if __name__ == "__main__":
    raise SystemExit(main())

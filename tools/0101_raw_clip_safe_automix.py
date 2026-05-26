#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import math
from pathlib import Path

import numpy as np
from scipy.io import wavfile
from scipy import signal


ROOT = Path("/Users/hantaeheuk/Documents/New project 3")
SRC = ROOT / "audio_work/0101_suno_studio_v04_real_female_audible_vocal_ride/stems"
WORK = ROOT / "audio_work/0101_raw_clip_safe_v01"
RENDERS = ROOT / "renders/0101_raw_clip_safe_v01"
REPORTS = ROOT / "reports/0101_raw_clip_safe_v01"

FINAL_WAV = RENDERS / "0101_RAW_CLIP_SAFE_v01.wav"
PREVIEW_WAV = RENDERS / "0101_RAW_CLIP_SAFE_v01_preview_30s.wav"
STEM_METRICS_CSV = REPORTS / "source_stem_metrics.csv"
QC_JSON = REPORTS / "raw_clip_safe_qc.json"
NOTES_MD = REPORTS / "raw_clip_safe_report.md"

EXCLUDE_FROM_MIX = {
    "0101_original_reference.wav",
    "0101_original_reference_duplicate.wav",
    "0101_instrumental_raw.wav",
}

GAINS_DB = {
    "0101_vocal_raw.wav": 1.2,
    "0101_backing_vocals_raw.wav": -5.8,
    "0101_drums_raw.wav": -1.8,
    "0101_bass808_raw.wav": -0.9,
    "0101_melody_raw.wav": -2.2,
    "0101_keyboard_raw.wav": -2.8,
    "0101_synth_raw.wav": -3.2,
    "0101_fx_raw.wav": -5.5,
    "0101_brass_raw.wav": -90.0,
    "0101_guitar_raw.wav": -90.0,
    "0101_percussion_raw.wav": -90.0,
    "0101_strings_raw.wav": -90.0,
    "0101_woodwinds_raw.wav": -90.0,
}

BANDS = [
    ("sub_20_80", 20, 80),
    ("bass_80_200", 80, 200),
    ("low_mid_200_500", 200, 500),
    ("mid_500_2000", 500, 2000),
    ("presence_2k_5k", 2000, 5000),
    ("sibilance_5k_8k", 5000, 8000),
    ("fizz_8k_12k", 8000, 12000),
    ("air_12k_20k", 12000, 20000),
]


def db_to_gain(db: float) -> float:
    return 10 ** (db / 20.0)


def amp_to_db(x: float) -> float:
    return 20.0 * math.log10(max(float(x), 1e-12))


def read_wav(path: Path) -> tuple[int, np.ndarray]:
    sr, x = wavfile.read(path)
    x = np.asarray(x)
    if np.issubdtype(x.dtype, np.integer):
        x = x.astype(np.float32) / float(np.iinfo(x.dtype).max)
    else:
        x = x.astype(np.float32)
    if x.ndim == 1:
        x = np.stack([x, x], axis=1)
    return sr, x


def write_wav(path: Path, sr: int, x: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    wavfile.write(path, sr, np.asarray(x, dtype=np.float32))


def butter_filter(x: np.ndarray, sr: int, kind: str, freq: float | tuple[float, float], order: int = 2) -> np.ndarray:
    sos = signal.butter(order, freq, btype=kind, fs=sr, output="sos")
    return signal.sosfiltfilt(sos, x, axis=0).astype(np.float32)


def high_shelf(x: np.ndarray, sr: int, freq: float, gain_db: float, slope: float = 0.707) -> np.ndarray:
    a = 10 ** (gain_db / 40.0)
    w0 = 2 * math.pi * freq / sr
    cosw = math.cos(w0)
    sinw = math.sin(w0)
    alpha = sinw / 2 * math.sqrt((a + 1 / a) * (1 / slope - 1) + 2)
    b0 = a * ((a + 1) + (a - 1) * cosw + 2 * math.sqrt(a) * alpha)
    b1 = -2 * a * ((a - 1) + (a + 1) * cosw)
    b2 = a * ((a + 1) + (a - 1) * cosw - 2 * math.sqrt(a) * alpha)
    a0 = (a + 1) - (a - 1) * cosw + 2 * math.sqrt(a) * alpha
    a1 = 2 * ((a - 1) - (a + 1) * cosw)
    a2 = (a + 1) - (a - 1) * cosw - 2 * math.sqrt(a) * alpha
    b = np.array([b0, b1, b2]) / a0
    acoef = np.array([1, a1 / a0, a2 / a0])
    return signal.lfilter(b, acoef, x, axis=0).astype(np.float32)


def peak_eq(x: np.ndarray, sr: int, freq: float, gain_db: float, q: float) -> np.ndarray:
    a = 10 ** (gain_db / 40.0)
    w0 = 2 * math.pi * freq / sr
    alpha = math.sin(w0) / (2 * q)
    cosw = math.cos(w0)
    b0 = 1 + alpha * a
    b1 = -2 * cosw
    b2 = 1 - alpha * a
    a0 = 1 + alpha / a
    a1 = -2 * cosw
    a2 = 1 - alpha / a
    b = np.array([b0, b1, b2]) / a0
    acoef = np.array([1, a1 / a0, a2 / a0])
    return signal.lfilter(b, acoef, x, axis=0).astype(np.float32)


def frame_gain_for_deess(band: np.ndarray, sr: int, threshold_db: float, max_reduction_db: float) -> np.ndarray:
    mono = np.sqrt(np.mean(np.square(band), axis=1))
    frame = 1024
    hop = 256
    if len(mono) < frame:
        return np.ones(len(mono), dtype=np.float32)
    values = []
    centers = []
    for start in range(0, len(mono) - frame + 1, hop):
        block = mono[start:start + frame]
        rms = math.sqrt(float(np.mean(block * block)) + 1e-20)
        db = amp_to_db(rms)
        over = max(0.0, db - threshold_db)
        reduction = min(max_reduction_db, over * 0.45)
        values.append(db_to_gain(-reduction))
        centers.append(start + frame // 2)
    if not values:
        return np.ones(len(mono), dtype=np.float32)
    env = np.interp(np.arange(len(mono)), centers, values, left=values[0], right=values[-1])
    env = signal.savgol_filter(env, 301 if len(env) > 301 else max(5, len(env) // 2 * 2 - 1), 2, mode="interp")
    return np.clip(env, db_to_gain(-max_reduction_db), 1.0).astype(np.float32)


def deess_band(x: np.ndarray, sr: int, lo: float, hi: float, threshold_db: float, max_reduction_db: float, wet: float) -> np.ndarray:
    band = butter_filter(x, sr, "bandpass", (lo, hi), order=2)
    gain = frame_gain_for_deess(band, sr, threshold_db, max_reduction_db)[:, None]
    reduced_band = band * gain
    return (x - band * wet + reduced_band * wet).astype(np.float32)


def process_vocal(x: np.ndarray, sr: int) -> np.ndarray:
    y = butter_filter(x, sr, "highpass", 80.0, order=2)
    y = peak_eq(y, sr, 260.0, -1.2, 0.85)
    y = peak_eq(y, sr, 950.0, -0.7, 1.0)
    y = peak_eq(y, sr, 3300.0, -0.8, 1.05)
    y = deess_band(y, sr, 5500.0, 8200.0, -33.5, 2.3, 0.65)
    y = deess_band(y, sr, 8200.0, 12000.0, -37.0, 2.0, 0.55)
    y = high_shelf(y, sr, 10500.0, -0.8, slope=0.8)
    return y.astype(np.float32)


def process_backing(x: np.ndarray, sr: int) -> np.ndarray:
    y = butter_filter(x, sr, "highpass", 105.0, order=2)
    y = peak_eq(y, sr, 300.0, -1.0, 0.9)
    y = deess_band(y, sr, 5500.0, 11000.0, -38.0, 1.8, 0.5)
    return y.astype(np.float32)


def process_bass(x: np.ndarray, sr: int) -> np.ndarray:
    y = butter_filter(x, sr, "highpass", 24.0, order=2)
    return y.astype(np.float32)


def process_drums(x: np.ndarray, sr: int) -> np.ndarray:
    y = butter_filter(x, sr, "highpass", 25.0, order=2)
    y = high_shelf(y, sr, 12000.0, -0.5, slope=0.9)
    return y.astype(np.float32)


def process_melody_like(x: np.ndarray, sr: int) -> np.ndarray:
    y = butter_filter(x, sr, "highpass", 45.0, order=2)
    y = peak_eq(y, sr, 3600.0, -0.4, 1.0)
    y = high_shelf(y, sr, 12500.0, -0.4, slope=0.9)
    return y.astype(np.float32)


def process_fx(x: np.ndarray, sr: int) -> np.ndarray:
    y = butter_filter(x, sr, "highpass", 80.0, order=2)
    y = high_shelf(y, sr, 10000.0, -1.0, slope=0.8)
    return y.astype(np.float32)


def process_stem(name: str, x: np.ndarray, sr: int) -> np.ndarray:
    lower = name.lower()
    if "vocal_raw" in lower:
        return process_vocal(x, sr)
    if "backing_vocals" in lower:
        return process_backing(x, sr)
    if "bass808" in lower:
        return process_bass(x, sr)
    if "drums" in lower:
        return process_drums(x, sr)
    if "fx" in lower:
        return process_fx(x, sr)
    if any(k in lower for k in ["melody", "keyboard", "synth"]):
        return process_melody_like(x, sr)
    return x.astype(np.float32)


def true_peak(x: np.ndarray, oversample: int = 4) -> float:
    up = signal.resample_poly(x, oversample, 1, axis=0)
    return float(np.max(np.abs(up)))


def k_weighted_lufs_approx(x: np.ndarray) -> float:
    # Approximation for 48 kHz based on BS.1770 K-weighting filters, no gating.
    b1 = np.array([1.53512485958697, -2.69169618940638, 1.19839281085285])
    a1 = np.array([1.0, -1.69065929318241, 0.73248077421585])
    b2 = np.array([1.0, -2.0, 1.0])
    a2 = np.array([1.0, -1.99004745483398, 0.99007225036621])
    y = signal.lfilter(b1, a1, x, axis=0)
    y = signal.lfilter(b2, a2, y, axis=0)
    ms = float(np.mean(np.square(y[:, 0])) + np.mean(np.square(y[:, 1])))
    return -0.691 + 10.0 * math.log10(max(ms, 1e-20))


def band_rms_db(x: np.ndarray, sr: int, lo: float, hi: float) -> float:
    hi = min(hi, sr / 2 - 100)
    if hi <= lo:
        return -120.0
    y = butter_filter(x, sr, "bandpass", (lo, hi), order=2)
    return amp_to_db(math.sqrt(float(np.mean(np.square(y))) + 1e-20))


def metrics(path: Path, x: np.ndarray, sr: int) -> dict:
    peak = float(np.max(np.abs(x)))
    rms = float(math.sqrt(float(np.mean(np.square(x))) + 1e-20))
    clipped = int(np.sum(np.abs(x) >= 0.999))
    out = {
        "file": path.name,
        "sr": sr,
        "duration_sec": len(x) / sr,
        "peak_dbfs": amp_to_db(peak),
        "rms_dbfs": amp_to_db(rms),
        "crest_db": amp_to_db(peak) - amp_to_db(rms),
        "clipped_samples_ge_0_999": clipped,
    }
    for label, lo, hi in BANDS:
        out[label + "_rms_dbfs"] = band_rms_db(x, sr, lo, hi)
    return out


def main() -> None:
    WORK.mkdir(parents=True, exist_ok=True)
    RENDERS.mkdir(parents=True, exist_ok=True)
    REPORTS.mkdir(parents=True, exist_ok=True)

    wavs = sorted(SRC.glob("*.wav"))
    all_metrics = []
    mix = None
    sr0 = None
    included = []
    excluded = []

    for path in wavs:
        sr, x = read_wav(path)
        if sr0 is None:
            sr0 = sr
            mix = np.zeros_like(x, dtype=np.float64)
        if sr != sr0:
            raise RuntimeError(f"sample-rate mismatch: {path}")
        all_metrics.append(metrics(path, x, sr))
        if path.name in EXCLUDE_FROM_MIX:
            excluded.append({"file": path.name, "reason": "reference/composite, analyzed but not mixed"})
            continue
        gain_db = GAINS_DB.get(path.name, -3.0)
        if gain_db <= -80:
            excluded.append({"file": path.name, "reason": "near-silent separated stem, analyzed but muted"})
            continue
        processed = process_stem(path.name, x, sr)
        mix += processed.astype(np.float64) * db_to_gain(gain_db)
        included.append({"file": path.name, "gain_db": gain_db})

    assert mix is not None and sr0 is not None
    pre_peak = float(np.max(np.abs(mix)))
    pre_true = true_peak(mix.astype(np.float32))

    # Clip-safe final: no hard clipper, no loudness maximizer. Scale to true peak margin.
    target_true_peak_db = -1.2
    target_true_peak = db_to_gain(target_true_peak_db)
    final_gain = target_true_peak / max(pre_true, 1e-12)
    final = (mix * final_gain).astype(np.float32)
    # Tiny safety check after scaling.
    final_true = true_peak(final)
    if final_true > target_true_peak:
        final = (final * (target_true_peak / final_true)).astype(np.float32)

    write_wav(FINAL_WAV, sr0, final)
    write_wav(PREVIEW_WAV, sr0, final[: int(sr0 * 30)])

    final_metrics = metrics(FINAL_WAV, final, sr0)
    final_metrics.update({
        "true_peak_dbfs_4x": amp_to_db(true_peak(final)),
        "lufs_i_approx_no_gate": k_weighted_lufs_approx(final),
        "final_gain_db": amp_to_db(final_gain),
        "pre_mix_peak_dbfs": amp_to_db(pre_peak),
        "pre_mix_true_peak_dbfs_4x": amp_to_db(pre_true),
    })

    with STEM_METRICS_CSV.open("w", newline="") as f:
        fieldnames = list(all_metrics[0].keys())
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_metrics)

    qc = {
        "source_folder": str(SRC),
        "final_wav": str(FINAL_WAV),
        "preview_wav": str(PREVIEW_WAV),
        "included_stems": included,
        "excluded_or_muted_stems": excluded,
        "final_metrics": final_metrics,
        "notes": [
            "No hard clipping or aggressive limiter was used.",
            "Raw stems were analyzed before processing.",
            "Original reference and instrumental composite were analyzed but not mixed to avoid double-counting.",
            "Near-silent separation artifact stems were analyzed and muted.",
            "Vocal cleanup is conservative: HPF, tiny mud/plastic/harshness cuts, and light de-ess/fizz reduction.",
        ],
    }
    QC_JSON.write_text(json.dumps(qc, indent=2), encoding="utf-8")

    NOTES_MD.write_text(
        "\n".join([
            "# 0101 Raw Clip-Safe v01 Report",
            "",
            f"- Source folder: `{SRC}`",
            f"- Final WAV: `{FINAL_WAV}`",
            f"- Preview WAV: `{PREVIEW_WAV}`",
            f"- Source metrics CSV: `{STEM_METRICS_CSV}`",
            f"- Pre-mix sample peak before final gain: {amp_to_db(pre_peak):.2f} dBFS",
            f"- Pre-mix true peak before final gain: {amp_to_db(pre_true):.2f} dBFS",
            f"- Final gain applied: {amp_to_db(final_gain):.2f} dB",
            f"- Final sample peak: {final_metrics['peak_dbfs']:.2f} dBFS",
            f"- Final true peak 4x: {final_metrics['true_peak_dbfs_4x']:.2f} dBFS",
            f"- Final approximate integrated loudness: {final_metrics['lufs_i_approx_no_gate']:.2f} LUFS",
            f"- Final clipped samples >= 0.999: {final_metrics['clipped_samples_ge_0_999']}",
            "",
            "## Included Stems",
            "",
            *[f"- `{item['file']}` at {item['gain_db']:+.1f} dB" for item in included],
            "",
            "## Analyzed But Not Mixed",
            "",
            *[f"- `{item['file']}`: {item['reason']}" for item in excluded],
            "",
            "## Processing Notes",
            "",
            "- Clip-safe rebuild from raw stems; no hard clipper, no aggressive maximizer.",
            "- Vocal kept close/raw: HPF near 80 Hz, tiny mud/plastic/harshness cleanup, light 5.5-12 kHz de-ess/fizz reduction.",
            "- Drums/bass kept transient/sub-forward with only minimal cleanup.",
            "- The final file is intentionally less crushed than clipped versions, so it should hold up better without crackle/breakup.",
            "",
            "## Remaining Check",
            "",
            "- Human A/B check is still needed for AI vowel-tail artifacts and vocal emotion.",
        ]) + "\n",
        encoding="utf-8",
    )

    print(json.dumps({
        "final_wav": str(FINAL_WAV),
        "true_peak_dbfs_4x": final_metrics["true_peak_dbfs_4x"],
        "lufs_i_approx_no_gate": final_metrics["lufs_i_approx_no_gate"],
        "clipped_samples": final_metrics["clipped_samples_ge_0_999"],
        "included_count": len(included),
        "excluded_count": len(excluded),
    }, indent=2))


if __name__ == "__main__":
    main()

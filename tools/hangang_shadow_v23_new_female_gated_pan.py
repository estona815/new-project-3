from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path("/Users/hantaeheuk/Documents/New project 3")
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.mgmg_v03_human_vocal_dynamic_fx import (
    amp_db,
    butter_filter,
    compressor,
    convert_wav_24,
    delay_samples,
    dynamic_band_tame,
    pan_stereo,
    read_wav,
    write_float_wav,
)

WORK = ROOT / "audio_work" / "hangang_shadow_v23_new_female_gated_pan"
SOURCE = ROOT / "audio_work" / "hangang_shadow_v20_commercial_polish" / "source_full_stems"
NEW_FEMALE_SOURCE = WORK / "source_new_female_2stem"
REPORTS = ROOT / "reports" / "hangang_shadow_v23_new_female_gated_pan"
INTERMEDIATE = WORK / "intermediate"
PROCESSED = WORK / "processed_stems"

MALE = SOURCE / "12 Vocals.wav"
FEMALE = NEW_FEMALE_SOURCE / "0 Lead Vocals.wav"
GATED_FLOAT = PROCESSED / "female_double_new_gated_pan_float.wav"
GATED_WAV = PROCESSED / "female_double_new_gated_pan_24-48.wav"
ALIGN_JSON = REPORTS / "female_gated_alignment_report.json"
ALIGN_MD = REPORTS / "female_gated_alignment_report.md"


def smooth_mask(mask: np.ndarray, sr: int, fade_ms: float = 65.0) -> np.ndarray:
    fade = max(3, int(sr * fade_ms / 1000.0))
    kernel = np.hanning(fade * 2 + 1).astype(np.float64)
    kernel /= np.sum(kernel)
    return np.clip(np.convolve(mask.astype(np.float64), kernel, mode="same"), 0.0, 1.0)


def remove_short_regions(mask: np.ndarray, sr: int, min_ms: float = 180.0) -> np.ndarray:
    out = mask.astype(bool).copy()
    min_len = max(1, int(sr * min_ms / 1000.0))
    padded = np.r_[False, out, False]
    edges = np.flatnonzero(padded[1:] != padded[:-1])
    for start, end in zip(edges[0::2], edges[1::2]):
        if end - start < min_len:
            out[start:end] = False
    return out.astype(np.float64)


def align_to_male(male: np.ndarray, female: np.ndarray, sr: int) -> tuple[np.ndarray, dict[str, float | int]]:
    m = np.mean(male, axis=1).astype(np.float64)
    f = np.mean(female, axis=1).astype(np.float64)
    kernel_len = max(1, int(sr * 0.050))
    env_kernel = np.ones(kernel_len, dtype=np.float64) / kernel_len
    menv = np.sqrt(np.convolve(m * m, env_kernel, mode="same"))
    fenv = np.sqrt(np.convolve(f * f, env_kernel, mode="same"))

    hop = max(1, int(sr * 0.010))
    md = menv[::hop]
    fd = fenv[::hop]
    max_lag = int(1.2 * sr / hop)
    best_lag_steps = 0
    best_corr = -1.0
    for lag in range(-max_lag, max_lag + 1):
        if lag >= 0:
            n = min(len(md) - lag, len(fd))
            if n < 100:
                continue
            a = md[lag : lag + n]
            b = fd[:n]
        else:
            n = min(len(md), len(fd) + lag)
            if n < 100:
                continue
            a = md[:n]
            b = fd[-lag : -lag + n]
        a = a - np.mean(a)
        b = b - np.mean(b)
        denom = (np.linalg.norm(a) * np.linalg.norm(b)) + 1e-12
        corr = float(np.dot(a, b) / denom)
        if corr > best_corr:
            best_corr = corr
            best_lag_steps = lag

    lag_samples = int(best_lag_steps * hop)
    aligned = np.zeros_like(male)
    if lag_samples >= 0:
        n = min(len(female), len(aligned) - lag_samples)
        if n > 0:
            aligned[lag_samples : lag_samples + n] = female[:n]
    else:
        trim = -lag_samples
        n = min(max(0, len(female) - trim), len(aligned))
        if n > 0:
            aligned[:n] = female[trim : trim + n]

    return aligned, {
        "global_best_lag_samples": lag_samples,
        "global_best_lag_ms": round(lag_samples / sr * 1000.0, 2),
        "global_envelope_corr": round(best_corr, 4),
        "female_source_duration_s": round(len(female) / sr, 3),
        "male_duration_s": round(len(male) / sr, 3),
    }


def chroma_similarity(m: np.ndarray, f: np.ndarray, sr: int, start: int, n_fft: int, pcs: np.ndarray, valid_idx: np.ndarray, window: np.ndarray) -> float:
    ms = m[start : start + n_fft] * window
    fs = f[start : start + n_fft] * window
    mag_m = np.abs(np.fft.rfft(ms))[valid_idx]
    mag_f = np.abs(np.fft.rfft(fs))[valid_idx]
    cm = (mag_m ** 0.6) @ pcs
    cf = (mag_f ** 0.6) @ pcs
    cm /= np.linalg.norm(cm) + 1e-12
    cf /= np.linalg.norm(cf) + 1e-12
    return float(np.dot(cm, cf))


def local_envelope_corr(menv: np.ndarray, fenv: np.ndarray, start: int, length: int) -> float:
    a = menv[start : start + length]
    b = fenv[start : start + length]
    if len(a) < 8 or len(b) < 8:
        return 0.0
    a = a - np.mean(a)
    b = b - np.mean(b)
    denom = (np.linalg.norm(a) * np.linalg.norm(b)) + 1e-12
    return float(np.dot(a, b) / denom)


def main() -> int:
    INTERMEDIATE.mkdir(parents=True, exist_ok=True)
    PROCESSED.mkdir(parents=True, exist_ok=True)
    REPORTS.mkdir(parents=True, exist_ok=True)

    sr, male, _ = read_wav(MALE)
    sr2, female_raw, _ = read_wav(FEMALE)
    if sr != sr2:
        raise RuntimeError(f"sample-rate mismatch: {sr} vs {sr2}")

    length = len(male)
    male = male[:length]
    female, align_info = align_to_male(male, female_raw, sr)
    m = np.mean(male, axis=1).astype(np.float64)
    f = np.mean(female, axis=1).astype(np.float64)

    env_kernel = np.ones(max(1, int(sr * 0.050)), dtype=np.float64)
    env_kernel /= np.sum(env_kernel)
    menv = np.sqrt(np.convolve(m * m, env_kernel, mode="same"))
    fenv = np.sqrt(np.convolve(f * f, env_kernel, mode="same"))
    m_thr = max(float(np.percentile(menv[menv > 1e-8], 55)), float(amp_db(-55)))
    f_thr = max(float(np.percentile(fenv[fenv > 1e-8], 55)), float(amp_db(-58)))
    m_active = menv > m_thr
    f_active = fenv > f_thr

    n_fft = 4096
    hop = 1024
    window = np.hanning(n_fft)
    freqs = np.fft.rfftfreq(n_fft, 1 / sr)
    valid_idx = np.where((freqs >= 80) & (freqs <= 4200))[0]
    pcs = np.zeros((len(valid_idx), 12), dtype=np.float64)
    for row, idx in enumerate(valid_idx):
        midi = 69 + 12 * np.log2(freqs[idx] / 440.0)
        pcs[row, int(round(midi)) % 12] = 1.0

    keep = np.zeros(length, dtype=np.float64)
    sims: list[float] = []
    timing_sims: list[float] = []
    kept_frames = 0
    tested_frames = 0
    for start in range(0, max(0, length - n_fft), hop):
        center = start + n_fft // 2
        if not (m_active[center] and f_active[center]):
            continue
        tested_frames += 1
        sim = chroma_similarity(m, f, sr, start, n_fft, pcs, valid_idx, window)
        timing_sim = local_envelope_corr(menv, fenv, start, n_fft)
        sims.append(sim)
        timing_sims.append(timing_sim)
        if sim >= 0.84 and timing_sim >= 0.18:
            keep[start : start + n_fft] = 1.0
            kept_frames += 1

    keep = remove_short_regions(keep > 0.5, sr)
    mask = smooth_mask(keep, sr)
    processed = female.copy()
    processed = butter_filter(processed, sr, "highpass", 185, 3)
    processed = butter_filter(processed, sr, "lowpass", 9200, 3)
    processed, deess = dynamic_band_tame(processed, sr, 5600, 8800, 2.2, 68, 70, slope=0.55)
    processed = compressor(processed, sr, threshold_db=-27.0, ratio=1.35, smooth_ms=135, makeup_db=-0.5)
    processed *= mask[:, None]

    left = pan_stereo(processed, -0.28)
    right_shadow = pan_stereo(delay_samples(processed, int(sr * 0.017)), 0.34) * float(amp_db(-17.0))
    out = (left + right_shadow) * float(amp_db(-7.5))

    write_float_wav(GATED_FLOAT, sr, out.astype(np.float32))
    convert_wav_24(GATED_FLOAT, GATED_WAV)

    kept_seconds = float(np.sum(mask > 0.08) / sr)
    metrics = {
        "male_source": str(MALE),
        "female_source": str(FEMALE),
        "output": str(GATED_WAV),
        **align_info,
        "duration_s": round(length / sr, 3),
        "tested_overlap_frames": tested_frames,
        "kept_frames": kept_frames,
        "kept_seconds_mask_gt_0_08": round(kept_seconds, 3),
        "kept_ratio_of_song": round(kept_seconds / (length / sr), 4),
        "median_chroma_similarity_tested": round(float(np.median(sims)), 4) if sims else None,
        "p10_chroma_similarity_tested": round(float(np.percentile(sims, 10)), 4) if sims else None,
        "median_local_timing_corr_tested": round(float(np.median(timing_sims)), 4) if timing_sims else None,
        "p10_local_timing_corr_tested": round(float(np.percentile(timing_sims, 10)), 4) if timing_sims else None,
        "chroma_threshold": 0.84,
        "local_timing_corr_threshold": 0.18,
        "deess": deess,
        "policy": "The new female file was globally envelope-aligned to the male lead. Only overlapping male/female active frames with octave-insensitive chroma similarity >= 0.84 and local envelope correlation >= 0.18 were kept. Everything else was cut.",
    }
    ALIGN_JSON.write_text(json.dumps(metrics, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# Female Gated Alignment Report",
        "",
        f"- Output: `{GATED_WAV.relative_to(ROOT)}`",
        f"- Global lag correction: {metrics['global_best_lag_ms']} ms",
        f"- Global envelope correlation: {metrics['global_envelope_corr']}",
        f"- Kept seconds: {metrics['kept_seconds_mask_gt_0_08']}",
        f"- Kept ratio: {metrics['kept_ratio_of_song']}",
        f"- Tested overlap frames: {tested_frames}",
        f"- Kept frames: {kept_frames}",
        f"- Median chroma similarity: {metrics['median_chroma_similarity_tested']}",
        f"- Median local timing corr: {metrics['median_local_timing_corr_tested']}",
        "",
        "Policy: keep only overlapping, timing-compatible, pitch-compatible frames; cut the rest.",
    ]
    ALIGN_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(metrics, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

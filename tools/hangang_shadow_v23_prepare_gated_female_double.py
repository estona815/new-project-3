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

WORK = ROOT / "audio_work" / "hangang_shadow_v23_female_gated_pan"
SOURCE = ROOT / "audio_work" / "hangang_shadow_v20_commercial_polish" / "source_full_stems"
REPORTS = ROOT / "reports" / "hangang_shadow_v23_female_gated_pan"
INTERMEDIATE = WORK / "intermediate"
PROCESSED = WORK / "processed_stems"

MALE = SOURCE / "12 Vocals.wav"
FEMALE = SOURCE / "11 Backing_Vocals.wav"
GATED_FLOAT = PROCESSED / "female_double_gated_pan_float.wav"
GATED_WAV = PROCESSED / "female_double_gated_pan_24-48.wav"
ALIGN_JSON = REPORTS / "female_gated_alignment_report.json"
ALIGN_MD = REPORTS / "female_gated_alignment_report.md"


def smooth_mask(mask: np.ndarray, sr: int, fade_ms: float = 65.0) -> np.ndarray:
    fade = max(3, int(sr * fade_ms / 1000.0))
    kernel = np.hanning(fade * 2 + 1).astype(np.float64)
    kernel /= np.sum(kernel)
    return np.clip(np.convolve(mask.astype(np.float64), kernel, mode="same"), 0.0, 1.0)


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


def main() -> int:
    INTERMEDIATE.mkdir(parents=True, exist_ok=True)
    PROCESSED.mkdir(parents=True, exist_ok=True)
    REPORTS.mkdir(parents=True, exist_ok=True)

    sr, male, _ = read_wav(MALE)
    sr2, female, _ = read_wav(FEMALE)
    if sr != sr2:
        raise RuntimeError(f"sample-rate mismatch: {sr} vs {sr2}")

    length = min(len(male), len(female))
    male = male[:length]
    female = female[:length]
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
    hop = 2048
    window = np.hanning(n_fft)
    freqs = np.fft.rfftfreq(n_fft, 1 / sr)
    valid_idx = np.where((freqs >= 80) & (freqs <= 4200))[0]
    pcs = np.zeros((len(valid_idx), 12), dtype=np.float64)
    for row, idx in enumerate(valid_idx):
        midi = 69 + 12 * np.log2(freqs[idx] / 440.0)
        pcs[row, int(round(midi)) % 12] = 1.0

    keep = np.zeros(length, dtype=np.float64)
    sims: list[float] = []
    kept_frames = 0
    tested_frames = 0
    for start in range(0, max(0, length - n_fft), hop):
        center = start + n_fft // 2
        if not (m_active[center] and f_active[center]):
            continue
        tested_frames += 1
        sim = chroma_similarity(m, f, sr, start, n_fft, pcs, valid_idx, window)
        sims.append(sim)
        if sim >= 0.82:
            keep[start : start + n_fft] = 1.0
            kept_frames += 1

    mask = smooth_mask(keep, sr)
    processed = female.copy()
    processed = butter_filter(processed, sr, "highpass", 185, 3)
    processed = butter_filter(processed, sr, "lowpass", 9200, 3)
    processed, deess = dynamic_band_tame(processed, sr, 5600, 8800, 2.2, 68, 70, slope=0.55)
    processed = compressor(processed, sr, threshold_db=-27.0, ratio=1.35, smooth_ms=135, makeup_db=-0.5)
    processed *= mask[:, None]

    left = pan_stereo(processed, -0.32)
    right_shadow = pan_stereo(delay_samples(processed, int(sr * 0.017)), 0.38) * float(amp_db(-15.5))
    out = (left + right_shadow) * float(amp_db(-5.0))

    write_float_wav(GATED_FLOAT, sr, out.astype(np.float32))
    convert_wav_24(GATED_FLOAT, GATED_WAV)

    kept_seconds = float(np.sum(mask > 0.08) / sr)
    metrics = {
        "male_source": str(MALE),
        "female_source": str(FEMALE),
        "output": str(GATED_WAV),
        "duration_s": round(length / sr, 3),
        "tested_overlap_frames": tested_frames,
        "kept_frames": kept_frames,
        "kept_seconds_mask_gt_0_08": round(kept_seconds, 3),
        "kept_ratio_of_song": round(kept_seconds / (length / sr), 4),
        "median_chroma_similarity_tested": round(float(np.median(sims)), 4) if sims else None,
        "p10_chroma_similarity_tested": round(float(np.percentile(sims, 10)), 4) if sims else None,
        "chroma_threshold": 0.82,
        "deess": deess,
        "policy": "Only overlapping male/female active frames with octave-insensitive chroma similarity >= 0.82 were kept. Everything else was cut.",
    }
    ALIGN_JSON.write_text(json.dumps(metrics, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# Female Gated Alignment Report",
        "",
        f"- Output: `{GATED_WAV.relative_to(ROOT)}`",
        f"- Kept seconds: {metrics['kept_seconds_mask_gt_0_08']}",
        f"- Kept ratio: {metrics['kept_ratio_of_song']}",
        f"- Tested overlap frames: {tested_frames}",
        f"- Kept frames: {kept_frames}",
        f"- Median chroma similarity: {metrics['median_chroma_similarity_tested']}",
        "",
        "Policy: keep only overlapping, pitch-compatible frames; cut the rest.",
    ]
    ALIGN_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(metrics, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import csv
import importlib.util
import json
import math
import shutil
import sys
import uuid
import zipfile
from pathlib import Path

import numpy as np
from scipy import signal

ROOT = Path("/Users/hantaeheuk/Documents/New project 3")
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.mgmg_v03_human_vocal_dynamic_fx import (  # noqa: E402
    amp_db,
    audio_metrics,
    bandpass,
    biquad_peaking,
    biquad_shelf,
    butter_filter,
    compressor,
    convert_mp3,
    db_amp,
    delay_samples,
    dynamic_band_tame,
    ffmpeg_loudnorm,
    limiter,
    normalize_to_rms,
    pan_stereo,
    read_wav,
    reverb_send,
    rms,
    saturate,
    sidechain_duck_full,
    soft_clip,
    stem_metrics,
    write_float_wav,
)
from tools.mgmg_v11_female_70_mseq_layers import stable_master_tone  # noqa: E402


def load_male_only_module():
    path = ROOT / "tools" / "0101_male_only_strong_tune_mix.py"
    spec = importlib.util.spec_from_file_location("codex_0101_male_only", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


MO = load_male_only_module()

SLUG = "0101_female_candidate_v10_qc_support"
BPM = 135
BASE_STEMS = ROOT / "audio_work" / "0101_suno_studio_v01" / "stems"
CANDIDATE_DIRS = [
    Path("/Users/hantaeheuk/Downloads/0101 Stems"),
    Path("/Users/hantaeheuk/Downloads/0101 Stems-2"),
]

WORK = ROOT / "audio_work" / SLUG
STEMS = WORK / "stems"
CANDIDATES = WORK / "candidate_sources"
PROCESSED = WORK / "processed"
RENDERS = ROOT / "renders" / SLUG
REPORTS = ROOT / "reports" / SLUG
REAPER_DIR = ROOT / "reaper" / SLUG
RPP = REAPER_DIR / "0101_REAPER_FEMALE_QC_SUPPORT_PROJECT.rpp"

BASE_REQUIRED = [
    "0101_original_reference.wav",
    "0101_vocal_raw.wav",
    "0101_instrumental_raw.wav",
    "0101_drums_raw.wav",
    "0101_bass808_raw.wav",
    "0101_melody_raw.wav",
    "0101_keyboard_raw.wav",
    "0101_synth_raw.wav",
    "0101_fx_raw.wav",
    "0101_percussion_raw.wav",
    "0101_backing_vocals_raw.wav",
    "0101_woodwinds_raw.wav",
    "0101_strings_raw.wav",
    "0101_guitar_raw.wav",
    "0101_brass_raw.wav",
]


def ensure_dirs() -> None:
    for directory in (WORK, STEMS, CANDIDATES, PROCESSED, RENDERS, REPORTS, REAPER_DIR):
        directory.mkdir(parents=True, exist_ok=True)


def pad_or_trim(y: np.ndarray, length: int) -> np.ndarray:
    return MO.pad_or_trim(y, length)


def safe_sum(parts: list[tuple[np.ndarray, float]], length: int, ceiling_db: float = -1.6) -> np.ndarray:
    return MO.safe_sum(parts, length, ceiling_db)


def safe_normalize_to_rms(y: np.ndarray, target_db: float) -> np.ndarray:
    if rms(y) < 1e-10:
        return y.astype(np.float32)
    return normalize_to_rms(y, target_db).astype(np.float32)


def copy_sources() -> tuple[dict[str, Path], list[dict[str, Path | str]]]:
    copied: dict[str, Path] = {}
    for name in BASE_REQUIRED:
        src = BASE_STEMS / name
        if not src.exists():
            raise FileNotFoundError(src)
        dst = STEMS / name
        shutil.copy2(src, dst)
        copied[name] = dst

    candidates: list[dict[str, Path | str]] = []
    for idx, folder in enumerate(CANDIDATE_DIRS, start=1):
        lead = folder / "0 Lead Vocals.wav"
        inst = folder / "1 Instrumental.wav"
        if not lead.exists() or not inst.exists():
            continue
        label = f"candidate_{idx}_{folder.name.replace(' ', '_')}"
        dst_dir = CANDIDATES / label
        dst_dir.mkdir(parents=True, exist_ok=True)
        lead_dst = dst_dir / "0 Lead Vocals.wav"
        inst_dst = dst_dir / "1 Instrumental.wav"
        shutil.copy2(lead, lead_dst)
        shutil.copy2(inst, inst_dst)
        candidates.append({"label": label, "folder": str(folder), "lead": lead_dst, "instrumental": inst_dst})
    if not candidates:
        raise FileNotFoundError("No candidate folders with 0 Lead Vocals.wav and 1 Instrumental.wav were found.")
    return copied, candidates


def load_base(copied: dict[str, Path]) -> tuple[int, dict[str, np.ndarray], dict[str, str]]:
    sample_rates = set()
    audio: dict[str, np.ndarray] = {}
    dtypes: dict[str, str] = {}
    for name, path in copied.items():
        sr, y, dtype_name = read_wav(path)
        sample_rates.add(sr)
        audio[name] = y
        dtypes[name] = dtype_name
    if sample_rates != {48000}:
        raise RuntimeError(f"Expected 48 kHz base sources, got {sorted(sample_rates)}")
    length = max(len(y) for y in audio.values())
    audio = {name: pad_or_trim(y, length) for name, y in audio.items()}
    return 48000, audio, dtypes


def frame_env(y: np.ndarray, sr: int, low: float = 180.0, high: float = 5200.0, rate: int = 100) -> np.ndarray:
    band = bandpass(y, sr, low, high, 3)
    mono = np.mean(band, axis=1).astype(np.float32)
    win = max(int(sr / rate), 1)
    frames = len(mono) // win
    if frames <= 0:
        return np.zeros(0, dtype=np.float32)
    mono = mono[: frames * win]
    env = np.sqrt(np.mean(mono.reshape(frames, win) ** 2, axis=1) + 1e-12).astype(np.float32)
    env = np.log1p(env * 80.0)
    return ((env - np.mean(env)) / (np.std(env) + 1e-8)).astype(np.float32)


def best_offset(ref: np.ndarray, cand: np.ndarray, rate: int = 100, max_shift_s: float = 90.0) -> list[dict[str, float]]:
    if len(ref) == 0 or len(cand) == 0:
        return []
    max_shift = int(max_shift_s * rate)
    corr = signal.correlate(ref, cand, mode="full", method="fft")
    lags = np.arange(-len(cand) + 1, len(ref))
    mask = (lags >= -max_shift) & (lags <= max_shift)
    corr_m = corr[mask]
    lags_m = lags[mask]
    if len(corr_m) == 0:
        return []
    top = min(24, len(corr_m))
    idxs = np.argpartition(corr_m, -top)[-top:]
    rows: list[dict[str, float]] = []
    for idx in idxs:
        lag = int(lags_m[idx])
        if lag >= 0:
            a = ref[lag : min(len(ref), lag + len(cand))]
            b = cand[: len(a)]
        else:
            b = cand[-lag : min(len(cand), len(ref) - lag)]
            a = ref[: len(b)]
        if len(a) < rate * 8:
            continue
        score = float(np.dot(a, b) / ((np.linalg.norm(a) * np.linalg.norm(b)) + 1e-9))
        rows.append({"score": score, "offset_s": lag / rate, "overlap_s": len(a) / rate})
    rows = sorted(rows, key=lambda row: row["score"], reverse=True)
    deduped: list[dict[str, float]] = []
    for row in rows:
        if all(abs(row["offset_s"] - old["offset_s"]) > 0.16 for old in deduped):
            deduped.append({k: round(float(v), 4) for k, v in row.items()})
        if len(deduped) >= 6:
            break
    return deduped


def place_at(source: np.ndarray, length: int, sr: int, offset_s: float) -> tuple[np.ndarray, dict[str, float]]:
    out = np.zeros((length, 2), dtype=np.float32)
    offset = int(round(offset_s * sr))
    src_start = max(-offset, 0)
    dst_start = max(offset, 0)
    usable = min(len(source) - src_start, length - dst_start)
    if usable > 0:
        segment = source[src_start : src_start + usable].copy()
        segment = MO.edge_fade(segment, sr, 18.0)
        out[dst_start : dst_start + usable] = segment
    return out, {
        "offset_s": round(offset_s, 3),
        "dst_start_s": round(dst_start / sr, 3),
        "src_start_s": round(src_start / sr, 3),
        "placed_duration_s": round(max(usable, 0) / sr, 3),
    }


def downsample_energy(y: np.ndarray, sr: int, rate: int = 50) -> np.ndarray:
    mono = np.abs(np.mean(y, axis=1)).astype(np.float32)
    win = max(int(sr / rate), 1)
    frames = len(mono) // win
    if frames <= 0:
        return np.zeros(0, dtype=np.float32)
    out = np.mean(mono[: frames * win].reshape(frames, win), axis=1).astype(np.float32)
    active = out[out > 1e-10]
    if len(active):
        out = out / (float(np.percentile(active, 95)) + 1e-10)
    return np.clip(out, 0.0, 3.0).astype(np.float32)


def f0_track(y: np.ndarray, sr: int, rate: int = 50) -> tuple[np.ndarray, np.ndarray]:
    mono = np.mean(bandpass(y, sr, 75, 900, 2), axis=1).astype(np.float32)
    hop = max(int(sr / rate), 1)
    frame = max(int(sr * 0.046), hop * 2)
    min_lag = max(int(sr / 760), 1)
    max_lag = min(int(sr / 70), frame - 2)
    n = max((len(mono) - frame) // hop + 1, 0)
    logs = np.full(n, np.nan, dtype=np.float32)
    conf = np.zeros(n, dtype=np.float32)
    if n <= 0 or max_lag <= min_lag:
        return logs, conf
    for i in range(n):
        start = i * hop
        seg = mono[start : start + frame]
        seg = seg - float(np.mean(seg))
        energy = float(np.dot(seg, seg))
        if energy < 1e-6:
            continue
        corr = np.correlate(seg, seg, mode="full")[frame - 1 :]
        window = corr[min_lag:max_lag]
        if not len(window):
            continue
        lag = int(np.argmax(window) + min_lag)
        peak = float(corr[lag] / (corr[0] + 1e-9))
        if peak < 0.22:
            continue
        f0 = sr / lag
        logs[i] = math.log2(f0)
        conf[i] = min(1.0, max(0.0, peak))
    return logs, conf


def chroma_match_score(male_log: np.ndarray, female_log: np.ndarray, male_conf: np.ndarray, female_conf: np.ndarray) -> float | None:
    n = min(len(male_log), len(female_log), len(male_conf), len(female_conf))
    if n <= 0:
        return None
    ml = male_log[:n]
    fl = female_log[:n]
    mc = male_conf[:n]
    fc = female_conf[:n]
    valid = np.isfinite(ml) & np.isfinite(fl) & (mc > 0.26) & (fc > 0.24)
    if int(np.sum(valid)) < 6:
        return None
    diff = np.abs(((fl[valid] - ml[valid] + 0.5) % 1.0) - 0.5)
    return round(float(np.mean(diff < 0.18)), 4)


def local_qc_mask(male: np.ndarray, female: np.ndarray, sr: int, rate: int = 50) -> tuple[np.ndarray, dict[str, object]]:
    male_env = downsample_energy(bandpass(male, sr, 180, 5200, 3), sr, rate)
    female_env = downsample_energy(bandpass(female, sr, 180, 6200, 3), sr, rate)
    n = min(len(male_env), len(female_env))
    male_env = male_env[:n]
    female_env = female_env[:n]
    male_log, male_conf = f0_track(male, sr, rate)
    female_log, female_conf = f0_track(female, sr, rate)
    pitch_global = chroma_match_score(male_log, female_log, male_conf, female_conf)
    mask_points = np.zeros(n, dtype=np.float32)
    score_values: list[float] = []
    pitch_values: list[float] = []
    lag_values: list[float] = []
    accepted = 0
    frame = max(int(0.68 * rate), 8)
    hop = max(int(0.045 * rate), 1)
    max_lag = max(int(0.14 * rate), 1)
    male_thr = max(float(np.percentile(male_env[male_env > 1e-8], 36)) if np.any(male_env > 1e-8) else 0.035, 0.040)
    female_thr = max(float(np.percentile(female_env[female_env > 1e-8], 38)) if np.any(female_env > 1e-8) else 0.030, 0.035)

    for start in range(0, max(n - frame, 1), hop):
        end = min(start + frame, n)
        if end - start < frame // 2:
            continue
        m = male_env[start:end]
        if float(np.max(m)) < male_thr:
            continue
        best_score = -1.0
        best_lag = 999
        best_pitch: float | None = None
        for lag in range(-max_lag, max_lag + 1):
            fs = start + lag
            fe = end + lag
            if fs < 0 or fe > n:
                continue
            f = female_env[fs:fe]
            if float(np.max(f)) < female_thr:
                continue
            mm = m - float(np.mean(m))
            ff = f - float(np.mean(f))
            score = float(np.dot(mm, ff) / (float(np.linalg.norm(mm) * np.linalg.norm(ff)) + 1e-9))
            if score > best_score:
                best_score = score
                best_lag = lag
                ml = male_log[start:end] if end <= len(male_log) else np.array([], dtype=np.float32)
                fl = female_log[fs:fe] if fe <= len(female_log) else np.array([], dtype=np.float32)
                mc = male_conf[start:end] if end <= len(male_conf) else np.array([], dtype=np.float32)
                fc = female_conf[fs:fe] if fe <= len(female_conf) else np.array([], dtype=np.float32)
                best_pitch = chroma_match_score(ml, fl, mc, fc)
        if best_score < -0.5:
            continue
        pitch_ok = True if best_pitch is None else best_pitch >= 0.35
        score_values.append(best_score)
        lag_values.append(best_lag / rate)
        if best_pitch is not None:
            pitch_values.append(best_pitch)
        if best_score >= 0.25 and abs(best_lag / rate) <= 0.065 and pitch_ok:
            strength = min(1.0, 0.30 + best_score * 1.15 + ((best_pitch or 0.45) - 0.35) * 0.35)
            mask_points[start:end] = np.maximum(mask_points[start:end], strength)
            accepted += 1

    if not np.any(mask_points > 0):
        return np.zeros(len(male), dtype=np.float32), {
            "coverage_pct": 0.0,
            "events": 0,
            "accepted_windows": 0,
            "score_median": round(float(np.median(score_values)), 4) if score_values else None,
            "pitch_global_match": pitch_global,
            "pitch_window_median": round(float(np.median(pitch_values)), 4) if pitch_values else None,
        }
    close = max(int(0.040 * rate), 1)
    mask_points = np.convolve(mask_points, np.ones(close, dtype=np.float32), mode="same")
    mask_points = np.clip(mask_points, 0.0, 1.0)
    sample_positions = np.arange(n) * (sr / rate)
    mask_full = np.interp(np.arange(len(male)), sample_positions, mask_points, left=0.0, right=0.0).astype(np.float32)
    fade = max(int(sr * 0.080), 3)
    kernel = np.hanning(fade).astype(np.float32)
    kernel /= max(float(np.sum(kernel)), 1e-9)
    mask_full = np.clip(signal.fftconvolve(mask_full, kernel, mode="same"), 0.0, 1.0).astype(np.float32)
    events = int(np.sum(np.diff((mask_full > 0.08).astype(np.int8), prepend=0) == 1))
    return mask_full, {
        "coverage_pct": round(float(np.mean(mask_full > 0.08) * 100.0), 2),
        "events": events,
        "accepted_windows": accepted,
        "score_median": round(float(np.median(score_values)), 4) if score_values else None,
        "score_p75": round(float(np.percentile(score_values, 75)), 4) if score_values else None,
        "abs_lag_median_s": round(float(np.median(np.abs(lag_values))), 4) if lag_values else None,
        "pitch_global_match": pitch_global,
        "pitch_window_median": round(float(np.median(pitch_values)), 4) if pitch_values else None,
        "rule": "opens only on matching timing windows; pitch check is used where f0 is reliable",
    }


def process_candidate_vocal(y: np.ndarray, sr: int, label: str) -> tuple[np.ndarray, list[dict[str, object]]]:
    moves: list[dict[str, object]] = []
    out = MO.edge_fade(y, sr, 26.0)
    out = butter_filter(out, sr, "highpass", 150, 3)
    moves.append({"stage": "female_candidate_highpass", "hz": 150, "label": label})
    out, beep = MO.suppress_beep_artifacts(out, sr, label, strength=0.94)
    out, sip = MO.suppress_sip_breaths(out, sr, label)
    out, denoise = MO.spectral_denoise_vocal(out, sr, label, reduction=0.66, high_reduction=0.84, floor=0.42, high_floor=0.28)
    moves.extend([beep, sip, denoise])
    for low, high, cut, pct, smooth, name in [
        (185, 370, 1.8, 70, 130, "mud_cleanup"),
        (690, 1250, 1.7, 70, 120, "nasal_plastic_cleanup"),
        (2450, 4800, 2.6, 66, 80, "harsh_attack_cleanup"),
        (5400, 8500, 4.1, 61, 54, "de_ess"),
        (8500, 13200, 3.4, 64, 48, "metallic_ai_fizz_cleanup"),
    ]:
        out, stats = dynamic_band_tame(out, sr, low, high, cut, pct, smooth)
        moves.append({"stage": f"female_candidate_{name}", **stats})
    out = biquad_peaking(out, sr, 820, -0.45, 1.0)
    out = biquad_peaking(out, sr, 3050, 0.25, 0.9)
    out = biquad_shelf(out, sr, 9800, -0.55, True)
    out = saturate(out, drive_db=0.7, mix=0.045)
    out = compressor(out, sr, threshold_db=-27.0, ratio=1.75, smooth_ms=100, makeup_db=0.0)
    out, ride = MO.vocal_level_ride(out, sr, target_db=-24.4, max_cut_db=-6.0, max_boost_db=0.55, label=label)
    moves.append(ride)
    out = safe_normalize_to_rms(out, -24.6)
    out = limiter(out, -2.4)
    moves.append({"stage": "female_candidate_final_gain", "target_rms_dbfs": -24.6})
    return out.astype(np.float32), moves


def make_female_support_layer(female: np.ndarray, male: np.ndarray, mask: np.ndarray, sr: int) -> tuple[np.ndarray, dict[str, object]]:
    female = pad_or_trim(female, len(male))
    mask = np.clip(mask[: len(male)], 0.0, 1.0)
    ducked_center = sidechain_duck_full(female * mask[:, None], male, sr, amount_db=2.6, release_ms=105, threshold_percentile=64)
    center = ducked_center * float(amp_db(-15.2))
    wide_src = butter_filter(female, sr, "highpass", 220, 2) * mask[:, None]
    wide = (
        pan_stereo(delay_samples(wide_src, int(sr * 0.012)), -0.58)
        + pan_stereo(delay_samples(wide_src, int(sr * 0.024)), 0.58)
    ) * float(amp_db(-11.3))
    wide = sidechain_duck_full(wide, male, sr, amount_db=3.1, release_ms=120, threshold_percentile=62)
    wet = reverb_send(wide_src, sr, decay_s=0.72, wet_db=-20.5, predelay_ms=34, hp_hz=440, lp_hz=6900, seed=204)
    delay_l = delay_samples(wide_src, int(sr * 0.185))
    delay_r = delay_samples(wide_src, int(sr * 0.285))
    delay = (pan_stereo(delay_l, -0.46) + pan_stereo(delay_r, 0.46)) * float(amp_db(-23.0))
    fx = sidechain_duck_full(wet + delay, male, sr, amount_db=3.5, release_ms=180, threshold_percentile=62)
    layer = limiter(center + wide + fx, -2.6)
    layer, tame = dynamic_band_tame(layer.astype(np.float32), sr, 5200, 11800, 3.6, 58, 45)
    layer = safe_normalize_to_rms(layer, -29.0) if np.max(np.abs(layer)) > 1e-8 else layer
    return layer.astype(np.float32), {
        "stage": "female_qc_support_layer",
        "center_gain_db": -15.2,
        "wide_gain_db": -11.3,
        "reverb_wet_db": -20.5,
        "delay_gain_db": -23.0,
        "sidechain_duck_db": "2.6-3.5",
        "high_tame": tame,
    }


def analyze_candidates(
    sr: int,
    base_audio: dict[str, np.ndarray],
    candidates: list[dict[str, Path | str]],
    male_proc: np.ndarray,
) -> tuple[dict[str, object] | None, list[dict[str, object]]]:
    male_raw = base_audio["0101_vocal_raw.wav"]
    inst_raw = base_audio["0101_instrumental_raw.wav"]
    male_env = frame_env(male_raw, sr, 180, 5200, 100)
    inst_env = frame_env(inst_raw, sr, 35, 260, 100)
    rows: list[dict[str, object]] = []
    best: dict[str, object] | None = None
    for cand in candidates:
        label = str(cand["label"])
        lead_path = Path(cand["lead"])
        inst_path = Path(cand["instrumental"])
        csr, lead, dtype_name = read_wav(lead_path)
        isr, inst, inst_dtype = read_wav(inst_path)
        if csr != sr or isr != sr:
            raise RuntimeError(f"{label} sample rate mismatch: {csr}/{isr}")
        vocal_offsets = best_offset(male_env, frame_env(lead, sr, 180, 5200, 100), 100, 90)
        inst_offsets = best_offset(inst_env, frame_env(inst, sr, 35, 260, 100), 100, 90)
        offset = float(vocal_offsets[0]["offset_s"]) if vocal_offsets else 0.0
        clean, moves = process_candidate_vocal(lead, sr, label)
        aligned, placement = place_at(clean, len(male_raw), sr, offset)
        mask, mask_stats = local_qc_mask(male_proc, aligned, sr, rate=50)
        layer, layer_stats = make_female_support_layer(aligned, male_proc, mask, sr)
        coverage = float(mask_stats.get("coverage_pct", 0.0) or 0.0)
        vocal_score = float(vocal_offsets[0]["score"]) if vocal_offsets else 0.0
        inst_score = float(inst_offsets[0]["score"]) if inst_offsets else 0.0
        pitch_score = mask_stats.get("pitch_window_median")
        pitch_component = 0.45 if pitch_score is None else float(pitch_score)
        total_score = round(vocal_score * 0.52 + inst_score * 0.16 + min(coverage / 35.0, 1.0) * 0.22 + pitch_component * 0.10, 4)
        accepted = bool(vocal_score >= 0.45 and coverage >= 6.0 and total_score >= 0.48)
        clean_path = PROCESSED / f"{label}_clean_aligned.wav"
        layer_path = PROCESSED / f"{label}_qc_support_layer.wav"
        mask_path = PROCESSED / f"{label}_qc_mask.wav"
        write_float_wav(clean_path, sr, aligned)
        write_float_wav(layer_path, sr, layer)
        write_float_wav(mask_path, sr, np.column_stack([mask, mask]).astype(np.float32))
        row: dict[str, object] = {
            "label": label,
            "folder": cand["folder"],
            "lead_path": str(lead_path),
            "lead_dtype": dtype_name,
            "lead_duration_s": round(len(lead) / sr, 3),
            "vocal_best": vocal_offsets[0] if vocal_offsets else None,
            "instrumental_best": inst_offsets[0] if inst_offsets else None,
            "placement": placement,
            "mask": mask_stats,
            "layer": layer_stats,
            "score": total_score,
            "accepted": accepted,
            "decision": "use_as_tucked_qc_support" if accepted else "reference_only",
            "processed_clean": str(clean_path),
            "processed_layer": str(layer_path),
            "processing_moves": moves,
        }
        rows.append(row)
        if accepted and (best is None or float(row["score"]) > float(best["score"])):
            best = row
    return best, rows


def render_versions(sr: int, processed: dict[str, np.ndarray], female_accepted: bool) -> dict[str, Path | list[dict[str, object]]]:
    length = len(processed["instrumental"])
    male = processed["male"]
    female_layer = processed["female_layer"] if female_accepted else np.zeros_like(male)
    male_reverb = reverb_send(male, sr, decay_s=0.62, wet_db=-22.5, predelay_ms=24, hp_hz=360, lp_hz=7400, seed=301)
    female_fx = reverb_send(female_layer, sr, decay_s=0.82, wet_db=-23.5, predelay_ms=36, hp_hz=460, lp_hz=6800, seed=302)
    female_fx = sidechain_duck_full(female_fx, male, sr, amount_db=3.4, release_ms=180, threshold_percentile=62)
    support_mix = safe_sum(
        [
            (processed["instrumental"], -0.30),
            (processed["melody"], 2.1),
            (male, -5.8),
            (female_layer, -0.8),
            (male_reverb, -0.5),
            (female_fx, -0.2),
        ],
        length,
        -1.7,
    )
    male_only = safe_sum(
        [
            (processed["instrumental"], -0.28),
            (processed["melody"], 2.1),
            (male, -5.55),
            (male_reverb, -0.5),
        ],
        length,
        -1.7,
    )
    rendered: dict[str, Path | list[dict[str, object]]] = {}
    mix_moves_all: list[dict[str, object]] = []
    for key, mix, target_lufs in [
        ("female_qc_support", support_mix, -11.25),
        ("male_only_safety", male_only, -11.30),
    ]:
        mix = MO.edge_fade(mix, sr, 24.0)
        mix, mix_moves = MO.full_mix_resonance_polish(mix, sr)
        mix_moves_all.extend([{"version": key, **row} for row in mix_moves])
        mix = stable_master_tone(mix, sr)
        mix = compressor(mix, sr, threshold_db=-11.8, ratio=1.08, smooth_ms=260, makeup_db=0.0)
        mix = soft_clip(mix, drive_db=0.32, ceiling=0.88)
        mix = limiter(mix, -2.2)
        premaster = RENDERS / f"0101_mix_{key}_premaster.wav"
        final_wav = RENDERS / f"0101_FINAL_{key}.wav"
        final_mp3 = RENDERS / f"0101_FINAL_{key}_320.mp3"
        write_float_wav(premaster, sr, mix)
        ffmpeg_loudnorm(premaster, final_wav, target_lufs=target_lufs, target_tp=-1.25, target_lra=4.0)
        convert_mp3(final_wav, final_mp3)
        rendered[f"{key}_premaster"] = premaster
        rendered[f"{key}_wav"] = final_wav
        rendered[f"{key}_mp3"] = final_mp3
    rendered["mix_moves"] = mix_moves_all
    return rendered


def write_processed_stems(sr: int, processed: dict[str, np.ndarray]) -> dict[str, Path]:
    outputs = {
        "processed_male_vocal_stem.wav": processed["male"],
        "processed_female_qc_support_stem.wav": processed["female_layer"],
        "processed_instrumental_stem.wav": processed["instrumental"],
        "drums_stem.wav": processed["drums"],
        "bass808_stem.wav": processed["bass"],
        "melody_stem.wav": processed["melody"],
    }
    paths: dict[str, Path] = {}
    for name, y in outputs.items():
        path = RENDERS / name
        write_float_wav(path, sr, limiter(y, -1.8))
        paths[name] = path
    return paths


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        return
    keys: list[str] = []
    for row in rows:
        for key in row:
            if key not in keys:
                keys.append(key)
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)


def markdown_table(rows: list[dict[str, object]], columns: list[str]) -> str:
    out = ["| " + " | ".join(columns) + " |", "| " + " | ".join(["---"] * len(columns)) + " |"]
    for row in rows:
        out.append("| " + " | ".join(str(row.get(col, "")) for col in columns) + " |")
    return "\n".join(out)


def rpp_item(file_path: Path, length: float, iid: int, muted: bool = False) -> str:
    return f"""    <ITEM
      POSITION 0
      SNAPOFFS 0
      LENGTH {length:.12f}
      LOOP 1
      ALLTAKES 0
      FADEIN 1 0.012 0 1 0 0 0
      FADEOUT 1 0.012 0 1 0 0 0
      MUTE {1 if muted else 0} 0
      SEL 0
      IGUID {{{uuid.uuid4()}}}
      IID {iid}
      NAME {file_path.name}
      VOLPAN 1 0 1 -1
      SOFFS 0
      PLAYRATE 1 1 0 -1 0 0.0025
      CHANMODE 0
      GUID {{{uuid.uuid4()}}}
      <SOURCE WAVE
        FILE "{file_path}"
      >
    >"""


def rpp_track(name: str, file_path: Path | None, length: float, iid: int, muted: bool = False, mainsend: bool = True) -> str:
    item = rpp_item(file_path, length, iid, muted=muted) if file_path else ""
    vol = "0.70794578438414" if muted else "1"
    return f"""  <TRACK {{{uuid.uuid4()}}}
    NAME "{name}"
    PEAKCOL 16576
    BEAT -1
    AUTOMODE 0
    PANLAWFLAGS 3
    VOLPAN {vol} 0 -1 -1 1
    MUTESOLO {1 if muted else 0} 0 0
    IPHASE 0
    PLAYOFFS 0 1
    ISBUS 0 0
    BUSCOMP 0 0 0 0 0
    SHOWINMIX 1 0.6667 0.5 1 0.5 0 0 0 0
    SEL 0
    REC 0 0 1 0 0 0 0 0
    VU 64
    TRACKHEIGHT 0 0 0 0 0 0 0
    INQ 0 0 0 0.5 100 0 0 100
    NCHAN 2
    FX 1
    TRACKID {{{uuid.uuid4()}}}
    PERF 0
    MIDIOUT -1
    MAINSEND {1 if mainsend else 0} 0
{item}
  >"""


def write_reaper_project(sr: int, audio: dict[str, np.ndarray], rendered: dict[str, Path | list[dict[str, object]]], processed_paths: dict[str, Path]) -> None:
    length = len(next(iter(audio.values()))) / sr
    track_defs = [
        ("ORIGINAL_REFERENCE muted", STEMS / "0101_original_reference.wav", True, False),
        ("MALE_VOCAL_RAW muted", STEMS / "0101_vocal_raw.wav", True, False),
        ("FEMALE_CANDIDATE_QC_SUPPORT processed muted", processed_paths["processed_female_qc_support_stem.wav"], True, False),
        ("MALE_VOCAL_PROCESSED strong tune muted", processed_paths["processed_male_vocal_stem.wav"], True, False),
        ("DRUM_BUS print muted", processed_paths["drums_stem.wav"], True, False),
        ("BASS_BUS print muted", processed_paths["bass808_stem.wav"], True, False),
        ("MELODY_BUS print muted", processed_paths["melody_stem.wav"], True, False),
        ("INSTRUMENTAL_PROCESSED muted", processed_paths["processed_instrumental_stem.wav"], True, False),
        ("MIX_BUS female qc support ACTIVE", Path(rendered["female_qc_support_wav"]), False, True),
        ("ALT male only safety muted", Path(rendered["male_only_safety_wav"]), True, False),
    ]
    tracks = [
        rpp_track(name, path, length, idx, muted=muted, mainsend=mainsend)
        for idx, (name, path, muted, mainsend) in enumerate(track_defs, start=1)
    ]
    markers = [
        f'  MARKER {i} {time:.6f} "{name}" 0 0 1 B {{{uuid.uuid4()}}} 0 2'
        for i, (time, name) in enumerate(
            zip([0, 14.2, 42.7, 72.0, 101.3, length], ["intro", "verse", "hook lift", "second section", "final lift/outro", "render end"]),
            start=1,
        )
    ]
    project = f"""<REAPER_PROJECT 0.1 "7.73/macOS-arm64" 1779750000 0
  <NOTES 0 2
    |0101 female candidate QC support revision. Female candidate is only active after timing/pitch QC mask and ducked under male lead.
  >
  RIPPLE 0 0
  AUTOXFADE 129
  PEAKGAIN 1
  PANLAW 1
  PROJOFFS 0 0 0
  GRID 3199 8 1 8 1 0 0 0
  TIMEMODE 1 5 -1 30 0 0 -1 0
  ITEMMIX 1
  SAMPLERATE 48000 1 0
  RENDER_FILE "{RENDERS / '0101_REAPER_project_sum.wav'}"
  RENDER_FMT 0 2 48000
  RENDER_RANGE 0 0 {length:.12f} 0 1000
  TEMPO {BPM}.000000 4 4 0
  PLAYRATE 1 0 0.25 4
  MASTER_NCH 2 2
  MASTER_VOLUME 1 0 -1 -1 1
{chr(10).join(markers)}
{chr(10).join(tracks)}
>
"""
    RPP.write_text(project, encoding="utf-8")


def create_delivery_zip(rendered: dict[str, Path | list[dict[str, object]]], processed_paths: dict[str, Path]) -> Path:
    zip_path = RENDERS / f"{SLUG}_DELIVERABLES.zip"
    include: list[Path] = [
        Path(rendered["female_qc_support_wav"]),
        Path(rendered["female_qc_support_mp3"]),
        Path(rendered["male_only_safety_wav"]),
        Path(rendered["male_only_safety_mp3"]),
        Path(rendered["female_qc_support_premaster"]),
        *processed_paths.values(),
        RPP,
        REPORTS / "female_candidate_qc_report.md",
        REPORTS / "reaper_mix_decision_log.md",
        REPORTS / "final_qc_report.md",
        REPORTS / "final_render_metrics.csv",
    ]
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        seen: set[Path] = set()
        for path in include:
            if path.exists() and path not in seen:
                zf.write(path, arcname=path.name)
                seen.add(path)
    return zip_path


def write_reports(
    sr: int,
    audio: dict[str, np.ndarray],
    dtypes: dict[str, str],
    candidate_rows: list[dict[str, object]],
    chosen: dict[str, object] | None,
    decisions: dict[str, object],
    rendered: dict[str, Path | list[dict[str, object]]],
    processed_paths: dict[str, Path],
) -> None:
    (REPORTS / "female_candidate_analysis.json").write_text(json.dumps(candidate_rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (REPORTS / "processing_decisions.json").write_text(json.dumps(decisions, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    final_paths = {
        "female_qc_support_wav": Path(rendered["female_qc_support_wav"]),
        "female_qc_support_mp3": Path(rendered["female_qc_support_mp3"]),
        "male_only_safety_wav": Path(rendered["male_only_safety_wav"]),
        "male_only_safety_mp3": Path(rendered["male_only_safety_mp3"]),
        "processed_male_vocal": processed_paths["processed_male_vocal_stem.wav"],
        "processed_female_qc_support": processed_paths["processed_female_qc_support_stem.wav"],
    }
    metrics = [audio_metrics(path, label) for label, path in final_paths.items()]
    write_csv(REPORTS / "final_render_metrics.csv", metrics)
    stem_rows = []
    for name, y in sorted(audio.items()):
        role = "male_vocal_source" if name == "0101_vocal_raw.wav" else "muted_reference" if "original_reference" in name else "source_or_support"
        row = stem_metrics(name, role, y, sr, dtypes[name])
        row["status"] = "used" if name in {"0101_vocal_raw.wav", "0101_instrumental_raw.wav", "0101_drums_raw.wav", "0101_bass808_raw.wav", "0101_melody_raw.wav"} else "support/reference"
        stem_rows.append(row)
    write_csv(REPORTS / "stem_metrics.csv", stem_rows)

    candidate_summary = [
        {
            "label": row["label"],
            "vocal_score": (row.get("vocal_best") or {}).get("score") if isinstance(row.get("vocal_best"), dict) else "",
            "offset_s": (row.get("vocal_best") or {}).get("offset_s") if isinstance(row.get("vocal_best"), dict) else "",
            "coverage_pct": (row.get("mask") or {}).get("coverage_pct") if isinstance(row.get("mask"), dict) else "",
            "pitch_window_median": (row.get("mask") or {}).get("pitch_window_median") if isinstance(row.get("mask"), dict) else "",
            "score": row.get("score"),
            "decision": row.get("decision"),
        }
        for row in candidate_rows
    ]
    chosen_label = str(chosen["label"]) if chosen else "none"
    (REPORTS / "female_candidate_qc_report.md").write_text(
        "\n".join(
            [
                "# Female Candidate QC Report",
                "",
                markdown_table(candidate_summary, ["label", "vocal_score", "offset_s", "coverage_pct", "pitch_window_median", "score", "decision"]),
                "",
                f"- Selected candidate: `{chosen_label}`.",
                "- 여자 보컬은 전체 리드로 쓰지 않고, timing/pitch QC mask를 통과한 구간만 wide support/adlib texture로 사용했다.",
                "- 가사 자동 인식은 로컬에서 신뢰 가능한 엔진이 없어 직접 보장하지 않았다. 대신 남자 보컬 phrasing, 음정 chroma, active overlap이 맞는 구간만 열었다.",
                "- QC에 실패하는 구간은 음소거되어 전처럼 가사/음정이 다르게 크게 들리는 상황을 피했다.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    final_summary = [
        {
            "version": row["label"],
            "duration_s": row.get("duration_s"),
            "integrated_lufs": row.get("integrated_lufs"),
            "true_peak_dbfs": row.get("true_peak_dbfs"),
            "peak_dbfs": row.get("peak_dbfs"),
            "rms_dbfs": row.get("rms_dbfs"),
            "stereo_corr": row.get("stereo_corr"),
        }
        for row in metrics
    ]
    (REPORTS / "reaper_mix_decision_log.md").write_text(
        "\n".join(
            [
                "# REAPER Mix Decision Log",
                "",
                f"- Slug: `{SLUG}`.",
                "- 새 폴더 `0101 Stems` / `0101 Stems-2`의 여자/새 리드 후보를 분석했다.",
                f"- 선택 후보: `{chosen_label}`.",
                "- 여자 후보는 남자 보컬과 맞는 구간에만 마스크로 열고, 남자 리드를 덮지 않도록 center/wide 모두 사이드체인 덕킹했다.",
                "- 여자 후보 처리: spectral denoise, dynamic EQ, de-ess, AI fizz tame, short reverb, stereo delay, male-lead sidechain duck.",
                "- 남자 보컬 처리: 강한 tune-feel density layer, spectral denoise, dynamic resonance EQ, sip/breath/beep suppress.",
                "- 반주 처리: melody-forward, round kick support, mono sub reinforcement, vocal-triggered ducking.",
                "- 마스터: -11 LUFS대, true peak -1.25 dBTP target.",
                "- 같이 제공되는 `male_only_safety`는 여자 레이어가 취향에 안 맞을 때 바로 비교용이다.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (REPORTS / "final_qc_report.md").write_text(
        "\n".join(
            [
                "# Final QC Report",
                "",
                markdown_table(final_summary, ["version", "duration_s", "integrated_lufs", "true_peak_dbfs", "peak_dbfs", "rms_dbfs", "stereo_corr"]),
                "",
                "## Notes",
                "",
                "- 메인 렌더는 `0101_FINAL_female_qc_support.wav`이다.",
                "- 여자 보컬은 전체가 아니라 QC 통과 구간만 들어가며, 보컬 중심은 남자 리드다.",
                "- 전처럼 이상하게 튀는 가사/음정/엇박 구간은 마스크에서 닫히도록 했다.",
                "- 리버브/딜레이는 짧고 어둡게 넣고 남자 보컬에 사이드체인으로 밀리게 했다.",
                "- MP3도 320kbps로 렌더했다.",
                "",
                "## Deliverables",
                "",
            ]
            + [f"- `{path}`" for path in final_paths.values()]
            + [f"- `{RPP}`", ""]
        ),
        encoding="utf-8",
    )


def main() -> None:
    ensure_dirs()
    copied, candidates = copy_sources()
    sr, audio, dtypes = load_base(copied)
    male_proc, male_moves = MO.process_male_vocal(audio["0101_vocal_raw.wav"], sr)
    chosen, candidate_rows = analyze_candidates(sr, audio, candidates, male_proc)
    female_accepted = chosen is not None
    if female_accepted:
        female_layer_path = Path(str(chosen["processed_layer"]))
        _, female_layer, _ = read_wav(female_layer_path)
        female_layer = pad_or_trim(female_layer, len(male_proc))
    else:
        female_layer = np.zeros_like(male_proc, dtype=np.float32)
    vocal_trigger = limiter(male_proc * float(amp_db(-2.0)) + female_layer * float(amp_db(-4.5)), -2.5)
    inst_processed, inst_moves = MO.process_instrumental(audio, sr, vocal_trigger)
    processed = {**inst_processed, "male": male_proc, "female_layer": female_layer}
    processed_paths = write_processed_stems(sr, processed)
    rendered = render_versions(sr, processed, female_accepted)
    decisions = {
        "female_accepted": female_accepted,
        "chosen_candidate": chosen,
        "candidate_count": len(candidate_rows),
        "male_vocal": male_moves,
        "instrumental": inst_moves,
        "mix_master": rendered.get("mix_moves", []),
    }
    write_reaper_project(sr, audio, rendered, processed_paths)
    write_reports(sr, audio, dtypes, candidate_rows, chosen, decisions, rendered, processed_paths)
    zip_path = create_delivery_zip(rendered, processed_paths)
    print(
        json.dumps(
            {
                "slug": SLUG,
                "female_accepted": female_accepted,
                "chosen_candidate": chosen["label"] if chosen else None,
                "renders": str(RENDERS),
                "reports": str(REPORTS),
                "main_wav": str(rendered["female_qc_support_wav"]),
                "main_mp3": str(rendered["female_qc_support_mp3"]),
                "male_only_safety_wav": str(rendered["male_only_safety_wav"]),
                "delivery_zip": str(zip_path),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()

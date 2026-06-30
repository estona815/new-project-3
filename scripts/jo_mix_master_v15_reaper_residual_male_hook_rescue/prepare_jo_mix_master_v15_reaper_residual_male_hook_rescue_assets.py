#!/usr/bin/env python3
from __future__ import annotations

import json
import math
import shutil
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from scipy import signal
from scipy.io import wavfile


PROJECT_ROOT = Path("/Users/hantaeheuk/Documents/New project 3")
SLUG = "jo_mix_master_v15_reaper_residual_male_hook_rescue"
SOURCE_DIR = PROJECT_ROOT / "audio_work" / "jo_mix_master_v01" / "source_stems"
AUDIO_WORK = PROJECT_ROOT / "audio_work" / SLUG
REPORT_DIR = PROJECT_ROOT / "reports" / SLUG

SECTION_WINDOWS = {
    "early_hook_0_15": (0.0, 15.0),
    "post_15_support": (15.0, 34.0),
    "middle_verse": (34.0, 80.0),
    "male_83s_boost": (80.0, 88.0),
    "pre_final_turn": (88.0, 92.0),
    "final_hook": (92.0, 128.416),
}

HOOK_RESCUE_WINDOWS = {
    "early_hook_0_15": (0.0, 15.0, -18.0),
    "male_83s_boost": (80.0, 88.0, -17.0),
    "pre_final_turn": (88.0, 92.0, -17.5),
    "final_hook": (92.0, 128.416, -17.0),
}


def now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def db_to_gain(db: float) -> float:
    return float(10.0 ** (db / 20.0))


def gain_to_db(gain: float, floor: float = -120.0) -> float:
    if not np.isfinite(gain) or gain <= 1.0e-12:
        return floor
    return float(20.0 * math.log10(gain))


def read_wav(path: Path) -> tuple[int, np.ndarray]:
    sr, data = wavfile.read(str(path))
    data = np.asarray(data)
    if np.issubdtype(data.dtype, np.floating):
        audio = data.astype(np.float32)
    else:
        info = np.iinfo(data.dtype)
        audio = data.astype(np.float32) / float(max(abs(info.min), abs(info.max)))
    if audio.ndim == 1:
        audio = np.stack([audio, audio], axis=1)
    if audio.shape[1] == 1:
        audio = np.repeat(audio, 2, axis=1)
    if audio.shape[1] > 2:
        audio = audio[:, :2]
    return int(sr), np.nan_to_num(audio.astype(np.float32))


def write_float(path: Path, audio: np.ndarray, sr: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    wavfile.write(str(path), sr, np.nan_to_num(audio.astype(np.float32)))


def write_clip(path: Path, audio: np.ndarray, sr: int, start_s: float, end_s: float) -> None:
    start = max(0, int(round(start_s * sr)))
    end = min(len(audio), int(round(end_s * sr)))
    write_float(path, audio[start:end], sr)


def mono(audio: np.ndarray) -> np.ndarray:
    return audio.mean(axis=1).astype(np.float32)


def rms_db(audio: np.ndarray) -> float:
    if audio.size == 0:
        return -120.0
    return gain_to_db(float(np.sqrt(np.mean(np.square(audio, dtype=np.float64))) + 1.0e-12))


def butter(audio: np.ndarray, sr: int, btype: str, cutoff: float | tuple[float, float], order: int = 2) -> np.ndarray:
    sos = signal.butter(order, cutoff, btype=btype, fs=sr, output="sos")
    return signal.sosfilt(sos, audio).astype(np.float32)


def butter_zero(audio: np.ndarray, sr: int, btype: str, cutoff: float | tuple[float, float], order: int = 2) -> np.ndarray:
    sos = signal.butter(order, cutoff, btype=btype, fs=sr, output="sos")
    return signal.sosfiltfilt(sos, audio).astype(np.float32)


def delay_mono(audio: np.ndarray, samples: int) -> np.ndarray:
    if samples <= 0:
        return audio.astype(np.float32)
    out = np.zeros_like(audio, dtype=np.float32)
    out[samples:] = audio[:-samples]
    return out


def stereo_corr(left: np.ndarray, right: np.ndarray) -> float:
    left = left.astype(np.float64) - float(np.mean(left))
    right = right.astype(np.float64) - float(np.mean(right))
    denom = math.sqrt(float(np.sum(left * left) * np.sum(right * right))) + 1.0e-20
    return float(np.sum(left * right) / denom)


def make_phrase_throw(source: np.ndarray, sr: int) -> np.ndarray:
    """Create a very tucked phrase-end throw print. It is intentionally not a lead."""
    mono_src = mono(source)
    win = max(1, int(sr * 0.055))
    power = signal.convolve(mono_src * mono_src, np.ones(win, dtype=np.float32) / win, mode="same", method="direct")
    env = np.sqrt(np.maximum(power, 0.0) + 1.0e-12)
    threshold = max(float(np.percentile(env, 58.0)) * 0.55, db_to_gain(-50.0))
    active = env > threshold
    # Phrase endings: keep only short tails after an active region falls away.
    tail = np.zeros_like(mono_src, dtype=np.float32)
    release = int(sr * 0.72)
    for idx in np.flatnonzero(active[:-1] & ~active[1:]):
        end = min(len(tail), idx + release)
        if end > idx:
            tail[idx:end] = np.maximum(tail[idx:end], np.linspace(1.0, 0.0, end - idx, dtype=np.float32))
    tail = signal.convolve(tail, np.ones(max(1, int(sr * 0.020))) / max(1, int(sr * 0.020)), mode="same")
    if float(np.max(tail)) <= 0.0:
        hop = int(sr * 0.50)
        block = int(sr * 0.32)
        for start in range(hop, len(mono_src) - block, hop):
            prev = env[max(0, start - hop) : start]
            cur = env[start : start + block]
            if prev.size and cur.size and float(np.mean(prev)) > threshold * 1.2 and float(np.mean(cur)) < float(np.mean(prev)) * 0.72:
                end = min(len(tail), start + release)
                tail[start:end] = np.maximum(tail[start:end], np.linspace(1.0, 0.0, end - start, dtype=np.float32))
    if float(np.max(tail)) <= 0.0:
        tail[:] = 0.18
    throw_src = mono_src * tail.astype(np.float32)
    delayed_l = delay_mono(throw_src, int(sr * 0.245))
    delayed_r = delay_mono(throw_src, int(sr * 0.365))
    delayed_l = butter(delayed_l, sr, "bandpass", (260.0, 6200.0), order=2)
    delayed_r = butter(delayed_r, sr, "bandpass", (300.0, 5600.0), order=2)
    out = np.stack([delayed_l, delayed_r], axis=1) * db_to_gain(-20.0)
    return out.astype(np.float32)


def section_fade(length: int, sr: int, fade_ms: float = 35.0) -> np.ndarray:
    env = np.ones(length, dtype=np.float32)
    fade = min(length // 2, max(1, int(round(sr * fade_ms / 1000.0))))
    ramp = np.linspace(0.0, 1.0, fade, dtype=np.float32)
    env[:fade] *= ramp
    env[-fade:] *= ramp[::-1]
    return env


def smooth_gate(audio: np.ndarray, sr: int) -> np.ndarray:
    win = max(1, int(round(sr * 0.045)))
    power = signal.convolve(audio * audio, np.ones(win, dtype=np.float32) / win, mode="same", method="direct")
    env = np.sqrt(np.maximum(power, 0.0) + 1.0e-12)
    hi = max(float(np.percentile(env, 86.0)), db_to_gain(-46.0))
    lo = max(float(np.percentile(env, 42.0)) * 0.75, db_to_gain(-58.0))
    if hi <= lo:
        return np.ones_like(audio, dtype=np.float32)
    mask = np.clip((env - lo) / (hi - lo), 0.0, 1.0).astype(np.float32)
    smooth = max(1, int(round(sr * 0.055)))
    mask = signal.convolve(mask, np.ones(smooth, dtype=np.float32) / smooth, mode="same", method="direct")
    return np.clip(0.25 + 0.75 * mask, 0.20, 1.0).astype(np.float32)


def ridge_fit_residual(y: np.ndarray, predictors: list[np.ndarray]) -> tuple[np.ndarray, list[float]]:
    if not predictors:
        return y.astype(np.float32), []
    n = len(y)
    cols = []
    scales = []
    for pred in predictors:
        col = pred[:n].astype(np.float64)
        col = col - float(np.mean(col))
        scale = float(np.sqrt(np.mean(col * col)) + 1.0e-9)
        cols.append(col / scale)
        scales.append(scale)
    x = np.stack(cols, axis=1)
    yc = y.astype(np.float64) - float(np.mean(y))
    lam = 0.02
    xtx = x.T @ x
    xty = x.T @ yc
    coef_norm = np.linalg.solve(xtx + lam * np.eye(x.shape[1]), xty)
    model = x @ coef_norm
    residual = yc - model
    coefs = [float(c / s) for c, s in zip(coef_norm, scales)]
    return residual.astype(np.float32), coefs


def make_male_hook_residual_rescue(
    full_mix: np.ndarray,
    instruments: list[np.ndarray],
    male_raw: np.ndarray,
    female_raw: np.ndarray,
    sr: int,
) -> tuple[np.ndarray, dict[str, dict[str, float | list[float]]]]:
    full_mono = mono(full_mix)
    inst_monos = [mono(stem) for stem in instruments]
    male_mono = mono(male_raw)
    female_mono = mono(female_raw)
    length = min([len(full_mono), len(male_mono), len(female_mono), *[len(x) for x in inst_monos]])
    rescue = np.zeros(length, dtype=np.float32)
    rows: dict[str, dict[str, float | list[float]]] = {}

    for name, (start_s, end_s, target_db) in HOOK_RESCUE_WINDOWS.items():
        a = max(0, int(round(start_s * sr)))
        b = min(length, int(round(end_s * sr)))
        if b <= a:
            continue

        y = full_mono[a:b]
        predictors = [stem[a:b] for stem in inst_monos] + [male_mono[a:b], female_mono[a:b]]
        fit_residual, coefs = ridge_fit_residual(y, predictors)
        simple_music = np.sum(np.stack([stem[a:b] for stem in inst_monos], axis=0), axis=0).astype(np.float32)
        simple_residual = (y - 0.82 * simple_music).astype(np.float32)
        raw_residual = (0.72 * fit_residual + 0.28 * simple_residual).astype(np.float32)
        raw_residual -= float(np.mean(raw_residual))

        voice_band = butter_zero(raw_residual, sr, "bandpass", (95.0, 4800.0), order=3)
        low_body = butter_zero(raw_residual, sr, "bandpass", (105.0, 360.0), order=2)
        chest = butter_zero(raw_residual, sr, "bandpass", (170.0, 720.0), order=2)
        consonant = butter_zero(raw_residual, sr, "bandpass", (900.0, 2700.0), order=2)
        high_fizz = butter_zero(raw_residual, sr, "bandpass", (3600.0, 7600.0), order=2)
        processed = (0.60 * voice_band + 0.55 * low_body + 0.35 * chest + 0.18 * consonant - 0.12 * high_fizz).astype(np.float32)
        processed *= smooth_gate(processed, sr)
        processed *= section_fade(len(processed), sr)

        before_db = rms_db(processed)
        gain_db = max(-8.0, min(18.0, target_db - before_db))
        processed *= db_to_gain(gain_db)
        peak = float(np.max(np.abs(processed)) + 1.0e-12)
        if peak > db_to_gain(-3.0):
            processed *= db_to_gain(-3.0) / peak

        rescue[a:b] += processed.astype(np.float32)
        rows[name] = {
            "start_seconds": start_s,
            "end_seconds": round(b / sr, 3),
            "full_mix_mono_rms_dbFS": round(rms_db(y), 3),
            "fit_residual_raw_rms_dbFS": round(rms_db(fit_residual), 3),
            "simple_residual_raw_rms_dbFS": round(rms_db(simple_residual), 3),
            "rescue_post_process_rms_dbFS": round(rms_db(processed), 3),
            "rescue_gain_db_applied": round(gain_db, 3),
            "predictor_coefficients_inst1_to_6_then_v9_v8": [round(float(c), 6) for c in coefs],
        }

    rescue = np.tanh(rescue * 1.15).astype(np.float32) / 1.15
    return np.stack([rescue, rescue], axis=1), rows


def main() -> int:
    AUDIO_WORK.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    sr, male_raw = read_wav(SOURCE_DIR / "9 Vocals.wav")
    _, female_raw = read_wav(SOURCE_DIR / "8 Vocals.wav")
    _, full_mix = read_wav(SOURCE_DIR / "0 ㅈㅇ.wav")
    instrument_stems = [read_wav(SOURCE_DIR / name)[1] for name in ["1 FX.wav", "2 Synth.wav", "3 Keyboard.wav", "4 Guitar.wav", "5 Bass.wav", "6 Drums.wav"]]
    if sr != 48000:
        raise RuntimeError(f"Expected 48 kHz stems, got {sr}")

    male_mono = mono(male_raw)
    female_mono = mono(female_raw)

    # Clean role assets only: exact mix/master balancing happens in REAPER.
    male_center = np.stack([male_mono, male_mono], axis=1).astype(np.float32)
    female_filtered = butter(female_mono, sr, "bandpass", (145.0, 8600.0), order=2)
    female_l = female_filtered.astype(np.float32)
    female_r = delay_mono(female_filtered, int(sr * 0.016))
    female_r = butter(female_r, sr, "bandpass", (180.0, 7800.0), order=2)
    residual_rescue, residual_rows = make_male_hook_residual_rescue(full_mix, instrument_stems, male_raw, female_raw, sr)

    write_float(AUDIO_WORK / "male_lead_center_role_asset.wav", male_center, sr)
    write_float(AUDIO_WORK / "male_hook_residual_rescue_center.wav", residual_rescue, sr)
    write_float(AUDIO_WORK / "female_shadow_L_role_asset.wav", female_l[:, None], sr)
    write_float(AUDIO_WORK / "female_shadow_R_role_asset.wav", female_r[:, None], sr)
    write_float(AUDIO_WORK / "vocal_phrase_end_throw_print.wav", make_phrase_throw(male_center, sr), sr)
    write_clip(AUDIO_WORK / "DIAG_residual_male_hook_rescue_early_hook_0_15.wav", residual_rescue, sr, 0.0, 15.0)
    write_clip(AUDIO_WORK / "DIAG_residual_male_hook_rescue_male_83s_80_88.wav", residual_rescue, sr, 80.0, 88.0)
    write_clip(AUDIO_WORK / "DIAG_residual_male_hook_rescue_final_hook_92_end.wav", residual_rescue, sr, 92.0, 128.416)
    write_clip(AUDIO_WORK / "DIAG_9_male_candidate_early_hook_0_15.wav", male_center, sr, 0.0, 15.0)
    write_clip(AUDIO_WORK / "DIAG_8_female_candidate_early_hook_0_15.wav", female_raw, sr, 0.0, 15.0)
    write_clip(AUDIO_WORK / "DIAG_9_male_candidate_male_83s_80_88.wav", male_center, sr, 80.0, 88.0)
    write_clip(AUDIO_WORK / "DIAG_8_female_candidate_male_83s_80_88.wav", female_raw, sr, 80.0, 88.0)
    write_clip(AUDIO_WORK / "DIAG_9_male_candidate_final_hook_92_end.wav", male_center, sr, 92.0, 128.416)
    write_clip(AUDIO_WORK / "DIAG_8_female_candidate_final_hook_92_end.wav", female_raw, sr, 92.0, 128.416)

    for name in ["0 ㅈㅇ.wav", "1 FX.wav", "2 Synth.wav", "3 Keyboard.wav", "4 Guitar.wav", "5 Bass.wav", "6 Drums.wav", "7 Backing_Vocals.wav"]:
        src = SOURCE_DIR / name
        if src.exists():
            shutil.copy2(src, AUDIO_WORK / name)

    section_rows = {}
    for section, (start, end) in SECTION_WINDOWS.items():
        a = int(round(start * sr))
        b = min(len(male_mono), int(round(end * sr)))
        section_rows[section] = {
            "start_seconds": start,
            "end_seconds": round(b / sr, 3),
            "raw_male_center_rms_dbFS": round(rms_db(male_mono[a:b]), 3),
            "raw_female_mono_rms_dbFS": round(rms_db(female_mono[a:b]), 3),
            "raw_male_minus_female_db": round(rms_db(male_mono[a:b]) - rms_db(female_mono[a:b]), 3),
        }

    report = {
        "schema": "jo-mix-master-reaper-v15-assets",
        "created_at": now_utc(),
        "slug": SLUG,
        "source_dir": str(SOURCE_DIR),
        "audio_work": str(AUDIO_WORK),
        "assets": {
            "male_lead_center_role_asset": str(AUDIO_WORK / "male_lead_center_role_asset.wav"),
            "male_hook_residual_rescue_center": str(AUDIO_WORK / "male_hook_residual_rescue_center.wav"),
            "female_shadow_L_role_asset": str(AUDIO_WORK / "female_shadow_L_role_asset.wav"),
            "female_shadow_R_role_asset": str(AUDIO_WORK / "female_shadow_R_role_asset.wav"),
            "vocal_phrase_end_throw_print": str(AUDIO_WORK / "vocal_phrase_end_throw_print.wav"),
        },
        "role_rules": [
            "9 Vocals.wav is kept for non-hook center lead support, but its hook regions are not trusted as male lead after source-audit evidence.",
            "male_hook_residual_rescue_center.wav is generated only from the user-provided full mix residual after fitting/subtracting instruments and the 8/9 vocal candidates.",
            "8 Vocals.wav is only a lower female L/R panned double-harmony layer.",
            "The female layer is split to separate L/R mono assets with a 16 ms right-side delay so it does not collapse into a center lead.",
            "v15 throw print is generated from the male lead only and tucked lower to avoid lifting female/noise tails.",
            "v15 writes DIAG hook solo clips for 8/9 vocal source identity checks.",
            "Full mix track 0 is copied only as a muted reference for the REAPER session.",
        ],
        "raw_section_vocal_balance": section_rows,
        "residual_rescue_section_generation": residual_rows,
        "female_lr_asset_correlation": round(stereo_corr(female_l, female_r), 6),
    }
    report_path = REPORT_DIR / f"{SLUG}_asset_report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"ok": True, "report": str(report_path), "audio_work": str(AUDIO_WORK)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

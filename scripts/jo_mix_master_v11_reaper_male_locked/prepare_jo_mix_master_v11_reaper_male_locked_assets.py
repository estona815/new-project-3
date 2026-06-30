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
SLUG = "jo_mix_master_v11_reaper_male_locked"
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


def mono(audio: np.ndarray) -> np.ndarray:
    return audio.mean(axis=1).astype(np.float32)


def rms_db(audio: np.ndarray) -> float:
    if audio.size == 0:
        return -120.0
    return gain_to_db(float(np.sqrt(np.mean(np.square(audio, dtype=np.float64))) + 1.0e-12))


def butter(audio: np.ndarray, sr: int, btype: str, cutoff: float | tuple[float, float], order: int = 2) -> np.ndarray:
    sos = signal.butter(order, cutoff, btype=btype, fs=sr, output="sos")
    return signal.sosfilt(sos, audio).astype(np.float32)


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
    out = np.stack([delayed_l, delayed_r], axis=1) * db_to_gain(-12.0)
    return out.astype(np.float32)


def main() -> int:
    AUDIO_WORK.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    sr, male_raw = read_wav(SOURCE_DIR / "9 Vocals.wav")
    _, female_raw = read_wav(SOURCE_DIR / "8 Vocals.wav")
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

    write_float(AUDIO_WORK / "male_lead_center_role_asset.wav", male_center, sr)
    write_float(AUDIO_WORK / "female_shadow_L_role_asset.wav", female_l[:, None], sr)
    write_float(AUDIO_WORK / "female_shadow_R_role_asset.wav", female_r[:, None], sr)
    write_float(AUDIO_WORK / "vocal_phrase_end_throw_print.wav", make_phrase_throw(male_center + np.stack([female_l, female_r], axis=1), sr), sr)

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
        "schema": "jo-mix-master-reaper-v11-assets",
        "created_at": now_utc(),
        "slug": SLUG,
        "source_dir": str(SOURCE_DIR),
        "audio_work": str(AUDIO_WORK),
        "assets": {
            "male_lead_center_role_asset": str(AUDIO_WORK / "male_lead_center_role_asset.wav"),
            "female_shadow_L_role_asset": str(AUDIO_WORK / "female_shadow_L_role_asset.wav"),
            "female_shadow_R_role_asset": str(AUDIO_WORK / "female_shadow_R_role_asset.wav"),
            "vocal_phrase_end_throw_print": str(AUDIO_WORK / "vocal_phrase_end_throw_print.wav"),
        },
        "role_rules": [
            "9 Vocals.wav is the male center lead from start to finish.",
            "8 Vocals.wav is only a female L/R panned double-harmony layer.",
            "The female layer is split to separate L/R mono assets with a 16 ms right-side delay so it does not collapse into a center lead.",
            "Full mix track 0 is copied only as a muted reference for the REAPER session.",
        ],
        "raw_section_vocal_balance": section_rows,
        "female_lr_asset_correlation": round(stereo_corr(female_l, female_r), 6),
    }
    report_path = REPORT_DIR / f"{SLUG}_asset_report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"ok": True, "report": str(report_path), "audio_work": str(AUDIO_WORK)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

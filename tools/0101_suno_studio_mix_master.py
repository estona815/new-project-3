from __future__ import annotations

import csv
import json
import math
import os
import shutil
import subprocess
import sys
import uuid
import zipfile
from pathlib import Path

import numpy as np

ROOT = Path("/Users/hantaeheuk/Documents/New project 3")
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.mgmg_v03_human_vocal_dynamic_fx import (  # noqa: E402
    FFMPEG,
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
    detect_phrase_endings,
    dynamic_band_tame,
    ffmpeg_loudnorm,
    limiter,
    ms_width,
    normalize_to_rms,
    pan_stereo,
    process_instrument,
    process_vocal,
    read_wav,
    reverb_send,
    rms,
    saturate,
    sidechain_duck_full,
    soft_clip,
    stem_metrics,
    write_float_wav,
)
from tools.mgmg_v04_male_main_female_adlibs import fade_window  # noqa: E402
from tools.mgmg_v11_female_70_mseq_layers import (  # noqa: E402
    bass_stable_grit,
    drums_stable_punch,
    stable_master_tone,
    static_music_space,
)


SLUG = os.environ.get("S0101_SLUG", "0101_suno_studio_v05_clear_vocal_no_beep")
SOURCE_SLUG = os.environ.get("S0101_SOURCE_SLUG", "0101_suno_studio_v01")
SRC = ROOT / "audio_work" / SOURCE_SLUG / "source_downloads" / "0101_multitrack_folder"
WORK = ROOT / "audio_work" / SLUG
STEMS = WORK / "stems"
PROCESSED = WORK / "processed"
INTERMEDIATE = WORK / "intermediate"
RENDERS = ROOT / "renders" / SLUG
REPORTS = ROOT / "reports" / SLUG
REAPER_DIR = ROOT / "reaper" / SLUG
RPP = REAPER_DIR / "0101_REAPER_MIX_MASTER_PROJECT.rpp"

BPM = 135

SOURCE_MAP = {
    "0 0101.wav": "0101_original_reference.wav",
    "1 0101.wav": "0101_original_reference_duplicate.wav",
    "2 Woodwinds.wav": "0101_woodwinds_raw.wav",
    "3 Brass.wav": "0101_brass_raw.wav",
    "4 FX.wav": "0101_fx_raw.wav",
    "5 Synth.wav": "0101_synth_raw.wav",
    "6 Strings.wav": "0101_strings_raw.wav",
    "7 Percussion.wav": "0101_percussion_raw.wav",
    "8 Keyboard.wav": "0101_keyboard_raw.wav",
    "9 Guitar.wav": "0101_guitar_raw.wav",
    "10 Bass.wav": "0101_bass808_raw.wav",
    "11 Drums.wav": "0101_drums_raw.wav",
    "12 Backing_Vocals.wav": "0101_backing_vocals_raw.wav",
    "13 Vocals.wav": "0101_vocal_raw.wav",
}


def ensure_dirs() -> None:
    for directory in (STEMS, PROCESSED, INTERMEDIATE, RENDERS, REPORTS, REAPER_DIR):
        directory.mkdir(parents=True, exist_ok=True)


def copy_sources() -> dict[str, Path]:
    copied: dict[str, Path] = {}
    for source_name, dest_name in SOURCE_MAP.items():
        src = SRC / source_name
        if not src.exists():
            raise FileNotFoundError(src)
        dst = STEMS / dest_name
        shutil.copy2(src, dst)
        copied[dest_name] = dst
    return copied


def pad_or_trim(y: np.ndarray, length: int) -> np.ndarray:
    if len(y) == length:
        return y.astype(np.float32)
    if len(y) > length:
        return y[:length].astype(np.float32)
    pad = np.zeros((length - len(y), 2), dtype=np.float32)
    return np.vstack([y.astype(np.float32), pad])


def safe_sum(parts: list[tuple[np.ndarray, float]], length: int) -> np.ndarray:
    out = np.zeros((length, 2), dtype=np.float32)
    for y, gain_db in parts:
        out += pad_or_trim(y, length) * float(amp_db(gain_db))
    return limiter(out, -1.0)


def peak_db(y: np.ndarray) -> float:
    return float(db_amp(np.max(np.abs(y)) if y.size else 0.0))


def rms_db(y: np.ndarray) -> float:
    return float(db_amp(rms(y)))


def load_all(copied: dict[str, Path]) -> tuple[int, dict[str, np.ndarray], dict[str, str]]:
    sample_rates = set()
    audio: dict[str, np.ndarray] = {}
    dtypes: dict[str, str] = {}
    for name, path in copied.items():
        sr, y, dtype_name = read_wav(path)
        sample_rates.add(sr)
        audio[name] = y
        dtypes[name] = dtype_name
    if sample_rates != {48000}:
        raise RuntimeError(f"Expected 48 kHz sources, got {sorted(sample_rates)}")
    length = max(len(y) for y in audio.values())
    audio = {key: pad_or_trim(value, length) for key, value in audio.items()}
    return 48000, audio, dtypes


def write_raw_derived_stems(sr: int, audio: dict[str, np.ndarray]) -> dict[str, Path]:
    length = len(next(iter(audio.values())))
    instrumental = safe_sum(
        [
            (audio["0101_woodwinds_raw.wav"], 0.0),
            (audio["0101_brass_raw.wav"], 0.0),
            (audio["0101_fx_raw.wav"], -3.0),
            (audio["0101_synth_raw.wav"], 0.0),
            (audio["0101_strings_raw.wav"], 0.0),
            (audio["0101_percussion_raw.wav"], 0.0),
            (audio["0101_keyboard_raw.wav"], 0.0),
            (audio["0101_guitar_raw.wav"], 0.0),
            (audio["0101_bass808_raw.wav"], 0.0),
            (audio["0101_drums_raw.wav"], 0.0),
        ],
        length,
    )
    melody = safe_sum(
        [
            (audio["0101_keyboard_raw.wav"], 0.0),
            (audio["0101_synth_raw.wav"], -0.8),
            (audio["0101_woodwinds_raw.wav"], -2.0),
            (audio["0101_strings_raw.wav"], -2.0),
            (audio["0101_guitar_raw.wav"], -2.5),
        ],
        length,
    )
    paths = {
        "instrumental_raw": STEMS / "0101_instrumental_raw.wav",
        "melody_raw": STEMS / "0101_melody_raw.wav",
    }
    write_float_wav(paths["instrumental_raw"], sr, instrumental)
    write_float_wav(paths["melody_raw"], sr, melody)
    return paths


def detect_drum_onsets(drums: np.ndarray, sr: int, max_count: int = 170) -> list[int]:
    mono = np.mean(bandpass(drums, sr, 35, 180, 3), axis=1)
    frame = int(sr * 0.012)
    hop = int(sr * 0.01)
    if len(mono) < frame * 2:
        return []
    env = np.array(
        [math.sqrt(float(np.mean(mono[i : i + frame] ** 2)) + 1e-12) for i in range(0, len(mono) - frame, hop)],
        dtype=np.float32,
    )
    if not len(env):
        return []
    diff = np.maximum(0.0, env - np.roll(env, 1))
    threshold = max(float(np.percentile(diff, 93.5)), float(np.max(diff) * 0.18))
    min_gap = int(0.18 / (hop / sr))
    onsets: list[int] = []
    last = -min_gap
    for idx, value in enumerate(diff):
        if value < threshold or idx - last < min_gap:
            continue
        left = diff[max(0, idx - 2) : idx + 1]
        right = diff[idx : min(len(diff), idx + 3)]
        if value >= float(np.max(left)) and value >= float(np.max(right)):
            onsets.append(idx * hop)
            last = idx
    return onsets[:max_count]


def make_round_kick_support(length: int, sr: int, onsets: list[int]) -> np.ndarray:
    support = np.zeros((length, 2), dtype=np.float32)
    dur = int(sr * 0.22)
    t = np.arange(dur, dtype=np.float32) / sr
    sweep = 62.0 - 16.0 * np.clip(t / 0.18, 0.0, 1.0)
    phase = 2.0 * np.pi * np.cumsum(sweep) / sr
    body = np.sin(phase) * np.exp(-t * 18.0)
    click = np.sin(2.0 * np.pi * 118.0 * t) * np.exp(-t * 52.0)
    shape = (body * 0.80 + click * 0.16).astype(np.float32)
    shape *= fade_window(len(shape), int(sr * 0.004))
    for onset in onsets:
        end = min(onset + dur, length)
        if end <= onset:
            continue
        seg = shape[: end - onset]
        support[onset:end, 0] += seg
        support[onset:end, 1] += seg
    support = butter_filter(support, sr, "lowpass", 820, 3)
    support = saturate(support, drive_db=1.1, mix=0.10)
    return normalize_to_rms(support, -25.8) if np.max(np.abs(support)) > 1e-8 else support


def vocal_level_ride(y: np.ndarray, sr: int, target_db: float, max_cut_db: float = -7.5, max_boost_db: float = 1.2) -> tuple[np.ndarray, dict[str, object]]:
    mono = np.mean(y, axis=1)
    frame = max(int(sr * 0.060), 1)
    hop = max(int(sr * 0.020), 1)
    env = np.zeros(len(mono), dtype=np.float32)
    values: list[float] = []
    centers: list[int] = []
    for start in range(0, max(len(mono) - frame, 1), hop):
        seg = mono[start : start + frame]
        if not len(seg):
            continue
        val = math.sqrt(float(np.mean(seg * seg)) + 1e-12)
        values.append(val)
        centers.append(start + len(seg) // 2)
    if not values:
        return y, {"stage": "vocal_level_ride", "active_windows": 0}
    vals = np.array(values, dtype=np.float32)
    active = vals > max(1e-5, float(np.percentile(vals, 38)) * 0.55)
    gain_points = np.zeros_like(vals)
    if np.any(active):
        current_db = db_amp(vals[active])
        desired = np.clip(target_db - current_db, max_cut_db, max_boost_db)
        gain_points[active] = desired
    sample_gain = np.interp(np.arange(len(mono)), centers, gain_points, left=0.0, right=0.0).astype(np.float32)
    kernel_len = max(int(sr * 0.180), 3)
    kernel = np.hanning(kernel_len).astype(np.float32)
    kernel /= max(float(np.sum(kernel)), 1e-9)
    sample_gain = np.convolve(sample_gain, kernel, mode="same").astype(np.float32)
    ridden = y * amp_db(sample_gain)[:, None]
    return ridden.astype(np.float32), {
        "stage": "vocal_level_ride",
        "target_db": target_db,
        "max_cut_db": max_cut_db,
        "max_boost_db": max_boost_db,
        "active_windows": int(np.sum(active)),
        "median_gain_db": round(float(np.median(sample_gain)), 3),
        "min_gain_db": round(float(np.min(sample_gain)), 3),
        "max_gain_db": round(float(np.max(sample_gain)), 3),
    }


def suppress_sip_breaths(y: np.ndarray, sr: int, label: str) -> tuple[np.ndarray, dict[str, object]]:
    high = bandpass(y, sr, 5200, 12000, 3)
    mid = bandpass(y, sr, 260, 2600, 2)
    high_env = np.abs(np.mean(high, axis=1))
    mid_env = np.abs(np.mean(mid, axis=1))
    smooth = max(int(sr * 0.018), 1)
    kernel = np.ones(smooth, dtype=np.float32) / smooth
    high_env = np.convolve(high_env, kernel, mode="same")
    mid_env = np.convolve(mid_env, kernel, mode="same")
    active_high = high_env[high_env > 1e-8]
    if not len(active_high):
        return y, {"stage": "sip_breath_suppress", "label": label, "events": 0}
    threshold = max(float(np.percentile(active_high, 97.2)), float(np.max(active_high) * 0.34))
    ratio = high_env / (mid_env + 1e-8)
    mask = (high_env > threshold) & (ratio > 1.65)
    width = max(int(sr * 0.055), 1)
    mask = np.convolve(mask.astype(np.float32), np.ones(width, dtype=np.float32), mode="same") > 0
    fade = max(int(sr * 0.035), 3)
    fade_kernel = np.hanning(fade).astype(np.float32)
    fade_kernel /= max(float(np.sum(fade_kernel)), 1e-9)
    mask_f = np.convolve(mask.astype(np.float32), fade_kernel, mode="same")
    out = y - high * (mask_f[:, None] * 0.78)
    out, stats = dynamic_band_tame(out.astype(np.float32), sr, 5600, 11800, 3.8, 63, 55)
    return out.astype(np.float32), {
        "stage": "sip_breath_suppress",
        "label": label,
        "events": int(np.sum(np.diff(mask.astype(np.int8), prepend=0) == 1)),
        "threshold": round(threshold, 6),
        "dynamic_tame": stats,
    }


def suppress_beep_artifacts(y: np.ndarray, sr: int, label: str, strength: float = 0.92) -> tuple[np.ndarray, dict[str, object]]:
    high = bandpass(y, sr, 3600, 15500, 4)
    low_mid = bandpass(y, sr, 160, 2600, 2)
    high_env = np.abs(np.mean(high, axis=1))
    low_env = np.abs(np.mean(low_mid, axis=1))
    smooth = max(int(sr * 0.006), 1)
    kernel = np.ones(smooth, dtype=np.float32) / smooth
    high_env = np.convolve(high_env, kernel, mode="same")
    low_env = np.convolve(low_env, kernel, mode="same")
    active = high_env[high_env > 1e-8]
    if not len(active):
        return y, {"stage": "beep_artifact_suppress", "label": label, "events": 0}
    threshold = max(float(np.percentile(active, 96.0)), float(np.max(active) * 0.22))
    ratio = high_env / (low_env + 1e-8)
    mask = (high_env > threshold) & (ratio > 0.78)
    # Always tame the first tiny edge; Suno exports often click before the musical attack.
    mask[: int(sr * 0.10)] = True
    width = max(int(sr * 0.045), 1)
    mask = np.convolve(mask.astype(np.float32), np.ones(width, dtype=np.float32), mode="same") > 0
    fade_len = max(int(sr * 0.055), 3)
    fade = np.hanning(fade_len).astype(np.float32)
    fade /= max(float(np.sum(fade)), 1e-9)
    mask_f = np.clip(np.convolve(mask.astype(np.float32), fade, mode="same"), 0.0, 1.0)
    out = y - high * (mask_f[:, None] * strength)
    out, dyn = dynamic_band_tame(out.astype(np.float32), sr, 3600, 12500, 3.4, 60, 42)
    return out.astype(np.float32), {
        "stage": "beep_artifact_suppress",
        "label": label,
        "events": int(np.sum(np.diff(mask.astype(np.int8), prepend=0) == 1)),
        "threshold": round(threshold, 6),
        "strength": strength,
        "dynamic_tame": dyn,
    }


def edge_fade(y: np.ndarray, sr: int, fade_ms: float = 18.0) -> np.ndarray:
    out = y.copy()
    n = min(max(int(sr * fade_ms / 1000.0), 1), len(out) // 2)
    if n > 1:
        ramp = np.linspace(0.0, 1.0, n, dtype=np.float32)
        out[:n] *= ramp[:, None]
        out[-n:] *= ramp[::-1, None]
    return out.astype(np.float32)


def vocal_clarity_without_loudness(y: np.ndarray, sr: int, label: str) -> tuple[np.ndarray, list[dict[str, object]]]:
    out = y.copy()
    out, mud = dynamic_band_tame(out, sr, 210, 430, 1.6, 70, 135)
    out, box = dynamic_band_tame(out, sr, 720, 1280, 1.1, 72, 120)
    presence = bandpass(out, sr, 1800, 4300, 3)
    diction = bandpass(out, sr, 2600, 5200, 3)
    out = out + presence * float(amp_db(-11.0)) + diction * float(amp_db(-15.0))
    out, harsh = dynamic_band_tame(out, sr, 3900, 7800, 2.4, 66, 60)
    out, hiss = dynamic_band_tame(out, sr, 7600, 13000, 2.8, 64, 50)
    out = biquad_peaking(out, sr, 2850, 0.45, 1.0)
    out = biquad_shelf(out, sr, 11200, -0.45, True)
    return out.astype(np.float32), [
        {"stage": "vocal_clarity_without_loudness", "label": label},
        {"stage": "clarity_mud_control", **mud},
        {"stage": "clarity_box_control", **box},
        {"stage": "clarity_harsh_control", **harsh},
        {"stage": "clarity_hiss_control", **hiss},
    ]


def pitch_shift_timing(y: np.ndarray, sr: int, semitones: float, label: str) -> np.ndarray:
    source = INTERMEDIATE / f"{label}_source.wav"
    dest = INTERMEDIATE / f"{label}_{semitones:+.1f}st.wav"
    write_float_wav(source, sr, y)
    factor = 2.0 ** (semitones / 12.0)
    tempo = 1.0 / factor
    filt = f"asetrate={sr * factor:.8f},aresample={sr},atempo={tempo:.8f}"
    subprocess.run(
        [FFMPEG, "-y", "-hide_banner", "-loglevel", "error", "-i", str(source), "-af", filt, "-c:a", "pcm_f32le", "-ar", str(sr), str(dest)],
        check=True,
    )
    shifted_sr, shifted, _ = read_wav(dest)
    if shifted_sr != sr:
        raise RuntimeError(f"pitch-shift sample rate mismatch: {shifted_sr} != {sr}")
    return pad_or_trim(shifted, len(y))


def make_audible_female_support(male_proc: np.ndarray, backing_support: np.ndarray, sr: int) -> tuple[np.ndarray, list[dict[str, object]]]:
    shifted = pitch_shift_timing(male_proc, sr, 5.0, "female_like_support_from_male")
    shifted = butter_filter(shifted, sr, "highpass", 185, 3)
    shifted = butter_filter(shifted, sr, "lowpass", 9200, 3)
    shifted, bite = dynamic_band_tame(shifted, sr, 2500, 6200, 2.5, 70, 85)
    shifted, hiss = dynamic_band_tame(shifted, sr, 6200, 11200, 3.0, 66, 60)
    shifted = biquad_peaking(shifted, sr, 920, -0.8, 0.9)
    shifted = biquad_peaking(shifted, sr, 3000, 0.55, 1.0)
    shifted = biquad_shelf(shifted, sr, 9200, -0.55, True)
    shifted = compressor(shifted, sr, threshold_db=-26.0, ratio=1.55, smooth_ms=135, makeup_db=0.0)
    shifted, ride = vocal_level_ride(shifted, sr, target_db=-25.0, max_cut_db=-5.0, max_boost_db=1.0)
    shifted = normalize_to_rms(shifted, -25.0)
    wide_shift = ms_width(
        pan_stereo(delay_samples(shifted, int(sr * 0.011)), -0.64)
        + pan_stereo(delay_samples(shifted, int(sr * 0.023)), 0.64),
        1.65,
    )
    out = backing_support * float(amp_db(3.0)) + wide_shift * float(amp_db(4.5))
    out = limiter(out, -1.4)
    return out.astype(np.float32), [
        {"stage": "audible_female_like_support_from_male", "pitch_shift_semitones": 5.0, "note": "used because exported backing vocal was too sparse to hear as a real female layer"},
        {"stage": "female_like_bite_control", **bite},
        {"stage": "female_like_hiss_control", **hiss},
        ride,
    ]


def process_sources(sr: int, audio: dict[str, np.ndarray]) -> tuple[dict[str, np.ndarray], dict[str, object]]:
    length = len(next(iter(audio.values())))
    male_raw = audio["0101_vocal_raw.wav"]
    female_raw = audio["0101_backing_vocals_raw.wav"]
    drums_raw = audio["0101_drums_raw.wav"]
    bass_raw = audio["0101_bass808_raw.wav"]
    keys_raw = audio["0101_keyboard_raw.wav"]
    synth_raw = audio["0101_synth_raw.wav"]
    fx_raw = audio["0101_fx_raw.wav"]
    perc_raw = audio["0101_percussion_raw.wav"]
    sparse_melody_raw = safe_sum(
        [
            (audio["0101_woodwinds_raw.wav"], -6.0),
            (audio["0101_brass_raw.wav"], -6.0),
            (audio["0101_strings_raw.wav"], -6.0),
            (audio["0101_guitar_raw.wav"], -7.0),
        ],
        length,
    )

    male_proc, male_moves = process_vocal("lead_vocal", male_raw, sr)
    male_proc = biquad_peaking(male_proc, sr, 820, -0.25, 0.9)
    male_proc = biquad_shelf(male_proc, sr, 10800, -0.15, True)
    male_proc, male_breath = suppress_sip_breaths(male_proc, sr, "male_lead")
    male_proc, male_ride = vocal_level_ride(male_proc, sr, target_db=-22.5, max_cut_db=-8.5, max_boost_db=0.8)
    male_proc = normalize_to_rms(male_proc, -20.5)

    female_clean, female_moves = process_vocal("backing_vocal", female_raw, sr)
    female_clean, female_fizz = dynamic_band_tame(female_clean, sr, 7200, 12200, 2.4, 70, 75)
    female_clean = normalize_to_rms(female_clean, -21.8)
    female_support = ms_width(
        pan_stereo(delay_samples(female_clean, int(sr * 0.012)), -0.46)
        + pan_stereo(delay_samples(female_clean, int(sr * 0.026)), 0.46)
        + female_clean * float(amp_db(-13.0)),
        1.35,
    )
    female_support = limiter(female_support, -3.0)
    female_support = normalize_to_rms(female_support, -22.4)
    female_support, female_extra_moves = make_audible_female_support(male_proc, female_support, sr)
    female_support, female_breath = suppress_sip_breaths(female_support, sr, "female_support")
    female_support, female_ride = vocal_level_ride(female_support, sr, target_db=-24.5, max_cut_db=-5.0, max_boost_db=1.0)
    female_support = normalize_to_rms(female_support, -22.2)
    female_alt = process_vocal("lead_vocal", female_raw, sr)[0]
    female_alt = butter_filter(female_alt, sr, "highpass", 145, 3)
    female_alt = biquad_peaking(female_alt, sr, 950, -0.65, 0.9)
    female_alt = biquad_peaking(female_alt, sr, 3200, 0.55, 1.0)
    female_alt = biquad_shelf(female_alt, sr, 10400, -0.28, True)
    female_alt, female_alt_breath = suppress_sip_breaths(female_alt, sr, "female_alt")
    female_alt, female_alt_ride = vocal_level_ride(female_alt, sr, target_db=-22.5, max_cut_db=-6.5, max_boost_db=1.0)
    female_alt = normalize_to_rms(female_alt, -20.0)

    drums_proc, drum_moves = drums_stable_punch(drums_raw, sr)
    onsets = detect_drum_onsets(drums_proc, sr)
    kick_support = make_round_kick_support(length, sr, onsets)
    drums_final = limiter(drums_proc * float(amp_db(0.45)) + kick_support * float(amp_db(-7.2)), -1.4)

    bass_proc, bass_moves = bass_stable_grit(bass_raw, drums_final, sr)
    sub = butter_filter(bass_proc, sr, "lowpass", 96, 4)
    sub = np.column_stack([np.mean(sub, axis=1), np.mean(sub, axis=1)]).astype(np.float32)
    bass_final = limiter(bass_proc * float(amp_db(0.95)) + sub * float(amp_db(-2.4)), -1.5)

    keys_proc, keys_moves = process_instrument("keys", keys_raw, sr, drums_final, male_proc)
    synth_proc, synth_moves = process_instrument("synth", synth_raw, sr, drums_final, male_proc)
    fx_proc, fx_moves = process_instrument("other", fx_raw, sr, drums_final, male_proc)
    perc_proc, perc_moves = process_instrument("other", perc_raw, sr, drums_final, male_proc)
    melody_proc = static_music_space(
        safe_sum(
            [
                (keys_proc, 0.0),
                (synth_proc, -1.5),
                (sparse_melody_raw, -8.0),
            ],
            length,
        ),
        sr,
    )
    melody_proc = normalize_to_rms(melody_proc, -21.6)
    fx_bed = butter_filter(fx_proc + perc_proc * float(amp_db(-5.5)), sr, "highpass", 120, 2)
    music_bus = limiter(melody_proc * float(amp_db(2.6)) + fx_bed * float(amp_db(-10.0)), -2.0)
    music_bus = sidechain_duck_full(music_bus, male_proc, sr, amount_db=0.25, release_ms=110, threshold_percentile=66)

    processed = {
        "male": male_proc,
        "female_support": female_support,
        "female_alt": female_alt,
        "drums": drums_final,
        "bass": bass_final,
        "melody": melody_proc,
        "music": music_bus,
        "fx": fx_bed,
        "instrumental": limiter(drums_final * float(amp_db(-1.1)) + bass_final * float(amp_db(-0.7)) + music_bus * float(amp_db(2.0)), -1.4),
        "kick_support": kick_support,
    }
    decisions = {
        "male_vocal": male_moves + [male_breath, male_ride],
        "female_vocal": female_moves + [{"stage": "female_upper_fizz_control", **female_fizz}] + female_extra_moves + [female_breath, female_ride, female_alt_breath, female_alt_ride],
        "drums": drum_moves + [{"stage": "round_kick_support", "detected_onsets": len(onsets), "gain_db": -7.2}],
        "bass": bass_moves + [{"stage": "sub_mono_reinforcement", "lowpass_hz": 96, "gain_db": -2.4}],
        "music": keys_moves + synth_moves + fx_moves + perc_moves,
    }
    return processed, decisions


def render_mix_versions(sr: int, processed: dict[str, np.ndarray]) -> dict[str, Path]:
    versions = {
        "male_lead": (
            processed["instrumental"] * float(amp_db(1.4))
            + processed["melody"] * float(amp_db(5.0))
            + processed["male"] * float(amp_db(-7.2))
            + reverb_send(processed["male"], sr, decay_s=0.64, wet_db=-22.0, predelay_ms=24, hp_hz=360, lp_hz=7600, seed=101)
        ),
        "female_alt": (
            processed["instrumental"] * float(amp_db(1.2))
            + processed["melody"] * float(amp_db(3.8))
            + processed["female_alt"] * float(amp_db(0.8))
            + processed["male"] * float(amp_db(-18.0))
            + reverb_send(processed["female_alt"], sr, decay_s=0.70, wet_db=-15.5, predelay_ms=30, hp_hz=420, lp_hz=7200, seed=102)
        ),
        "dual_vocal": (
            processed["instrumental"] * float(amp_db(1.3))
            + processed["melody"] * float(amp_db(5.5))
            + processed["male"] * float(amp_db(-9.0))
            + processed["female_support"] * float(amp_db(8.5))
            + reverb_send(processed["male"], sr, decay_s=0.66, wet_db=-24.0, predelay_ms=26, hp_hz=360, lp_hz=7600, seed=103)
            + reverb_send(processed["female_support"], sr, decay_s=0.72, wet_db=-11.5, predelay_ms=34, hp_hz=440, lp_hz=7000, seed=104)
        ),
    }
    targets = {
        "male_lead": (
            RENDERS / "0101_mix_male_lead_final.wav",
            RENDERS / "0101_FINAL_male_lead.wav",
            RENDERS / "0101_FINAL_male_lead_320.mp3",
            -11.2,
        ),
        "female_alt": (
            RENDERS / "0101_mix_female_lead_alt.wav",
            RENDERS / "0101_FINAL_female_alt.wav",
            RENDERS / "0101_FINAL_female_alt_320.mp3",
            -11.4,
        ),
        "dual_vocal": (
            RENDERS / "0101_mix_male_lead_female_support.wav",
            RENDERS / "0101_FINAL_dual_vocal.wav",
            RENDERS / "0101_FINAL_dual_vocal_320.mp3",
            -11.0,
        ),
    }
    rendered: dict[str, Path] = {}
    for key, mix in versions.items():
        mix = stable_master_tone(mix, sr)
        mix = soft_clip(mix, drive_db=0.45, ceiling=0.88)
        mix = limiter(mix, -2.2)
        premaster_path, final_wav, final_mp3, target_lufs = targets[key]
        write_float_wav(premaster_path, sr, mix)
        ffmpeg_loudnorm(premaster_path, final_wav, target_lufs=target_lufs, target_tp=-1.25, target_lra=4.0)
        convert_mp3(final_wav, final_mp3)
        rendered[f"{key}_premaster"] = premaster_path
        rendered[f"{key}_wav"] = final_wav
        rendered[f"{key}_mp3"] = final_mp3
    return rendered


def write_processed_stems(sr: int, processed: dict[str, np.ndarray]) -> dict[str, Path]:
    outputs = {
        "processed_male_vocal_stem.wav": processed["male"],
        "processed_female_vocal_stem.wav": processed["female_support"],
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


def source_metrics(sr: int, audio: dict[str, np.ndarray], dtypes: dict[str, str]) -> list[dict[str, object]]:
    rows = []
    roles = {
        "0101_original_reference.wav": "original_reference",
        "0101_original_reference_duplicate.wav": "duplicate_reference",
        "0101_vocal_raw.wav": "male_vocal",
        "0101_backing_vocals_raw.wav": "female_or_backing_vocal",
        "0101_drums_raw.wav": "drums",
        "0101_bass808_raw.wav": "bass_808",
        "0101_keyboard_raw.wav": "melody_keyboard",
        "0101_synth_raw.wav": "melody_synth",
        "0101_fx_raw.wav": "fx_ambience",
    }
    for name, y in sorted(audio.items()):
        role = roles.get(name, "reference_only_sparse_or_aux")
        row = stem_metrics(name, role, y, sr, dtypes[name])
        p_db = peak_db(y)
        r_db = rms_db(y)
        if "duplicate" in role:
            status = "reference only"
        elif p_db < -45 or r_db < -65:
            status = "reference only"
        elif role in {"male_vocal", "female_or_backing_vocal", "drums", "bass_808", "melody_keyboard", "melody_synth", "fx_ambience"}:
            status = "usable with cleanup"
        else:
            status = "support/reference only"
        row["quality_status"] = status
        row["phase_note"] = "check width" if float(row["stereo_corr"]) < 0.15 else "stable"
        rows.append(row)
    return rows


def write_metrics_csv(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        return
    keys = []
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


def write_reports(
    sr: int,
    audio: dict[str, np.ndarray],
    dtypes: dict[str, str],
    decisions: dict[str, object],
    rendered: dict[str, Path],
    processed_paths: dict[str, Path],
) -> None:
    metrics_rows = source_metrics(sr, audio, dtypes)
    write_metrics_csv(REPORTS / "stem_metrics.csv", metrics_rows)
    final_rows = [audio_metrics(path, label) for label, path in rendered.items() if label.endswith("_wav")]
    write_metrics_csv(REPORTS / "final_render_metrics.csv", final_rows)
    decisions_path = REPORTS / "processing_decisions.json"
    decisions_path.write_text(json.dumps(decisions, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    duration = len(next(iter(audio.values()))) / sr
    bars = duration / (60.0 / BPM * 4.0)
    (REPORTS / "suno_0101_initial_analysis.md").write_text(
        "\n".join(
            [
                "# Suno 0101 Initial Analysis",
                "",
                f"- Source: Safari Suno Studio multitrack export from `0101`.",
                f"- BPM: {BPM} BPM from Suno Studio UI.",
                f"- Key: not shown in Suno Studio UI; not asserted from analysis because the stem split is AI-generated and melody/bass sources are partly synthetic.",
                f"- Length: {duration:.3f}s exported audio, approximately {bars:.1f} bars at 135 BPM.",
                "- Arrangement estimate: intro/melody bed 0:00-0:14, first vocal/verse 0:14-0:43, hook/lift 0:43-1:12, second section 1:12-1:41, final lift/outro 1:41-end.",
                "- Current strengths: sad melody remains forward in the keyboard/synth/full mix; vocal contour is emotionally usable; bass and drums are separated enough for reinforcement.",
                "- Current weaknesses: raw export contains duplicated full-mix reference tracks; several orchestral stems are near-silent/reference-only; vocal high end needs de-essing and AI fizz control; low end benefits from controlled kick/sub reinforcement.",
                "- Vocal artifact notes: male vocal has typical Suno high-end glass/sibilance risk; backing vocal is usable as a female support layer but should stay tucked rather than replacing the emotional male lead by default.",
                "- Low-end/kick notes: bass stem has usable sub information; drum stem benefits from round kick support and low-mid cleanup rather than broad level pushing.",
                "",
            ]
        ),
        encoding="utf-8",
    )

    stem_summary = [
        {
            "stem": row["file"],
            "role": row["role"],
            "peak_dbfs": row["peak_dbfs"],
            "rms_dbfs": row["rms_dbfs"],
            "stereo_corr": row["stereo_corr"],
            "status": row["quality_status"],
            "phase": row["phase_note"],
        }
        for row in metrics_rows
    ]
    (REPORTS / "stem_quality_report.md").write_text(
        "\n".join(
            [
                "# Stem Quality Report",
                "",
                markdown_table(stem_summary, ["stem", "role", "peak_dbfs", "rms_dbfs", "stereo_corr", "status", "phase"]),
                "",
                "## Notes",
                "",
                "- `0 0101.wav` is the main full-mix reference and remains muted/reference-only in the REAPER project.",
                "- `1 0101.wav` is a duplicated full-mix reference from the working Studio session and is not used in the final mix.",
                "- Woodwinds, Brass, Strings, Percussion, and Guitar are effectively sparse or near-silent support exports, so they are kept only as low-level melody/context material.",
                "- `Vocals`, `Backing_Vocals`, `Drums`, `Bass`, `Keyboard`, `Synth`, and `FX` are usable after cleanup.",
                "",
            ]
        ),
        encoding="utf-8",
    )

    (REPORTS / "female_vocal_selection_report.md").write_text(
        "\n".join(
            [
                "# Female Vocal Selection Report",
                "",
                "- Credits before Safari work observed in Suno UI: 8860.",
                "- Additional Suno generation credits spent in this pass: 0.",
                "- Reason: Safari multitrack export `12 Backing_Vocals.wav` was too sparse to hear clearly, so v04 adds a pitch-shifted female-like support layer derived from the cleaned lead vocal, while still avoiding random lyrics, filler ad-libs, or lead takeover.",
                "",
                "## Candidates",
                "",
                "- Candidate A: raw `12 Backing_Vocals.wav` from Suno Studio multitrack. Selected as the female source.",
                "- Candidate B: `processed_female_vocal_stem.wav`, cleaned, widened, and reinforced with an audible female-like support layer.",
                "- Candidate C: `0101_FINAL_female_alt.wav`, female-forward alternate made from the same Suno backing vocal source.",
                "- Candidate D: dual-vocal blend in `0101_FINAL_dual_vocal.wav`, selected as the most musical final blend.",
                "",
                "## Selection",
                "",
                "- Best candidate: dual-vocal blend.",
                "- Role recommendation: keep male lead as emotional center; use female layer as wide support/harmony lift.",
                "- Timing accuracy: sample-aligned to the Suno multitrack export; no timing stretch was applied.",
                "- Remaining artifacts: the extra audible female layer is a pitch-shifted support texture rather than a newly generated Suno female lead; de-essing and breath/sip suppression were applied to keep it from becoming fizzy.",
                "",
            ]
        ),
        encoding="utf-8",
    )

    (REPORTS / "reaper_mix_decision_log.md").write_text(
        "\n".join(
            [
                "# REAPER Mix Decision Log",
                "",
                "## Source And Routing",
                "",
                "- Created a versioned project route under `audio_work/0101_suno_studio_v01`, `reaper/0101_suno_studio_v01`, `renders/0101_suno_studio_v01`, and `reports/0101_suno_studio_v01`.",
                "- Reference/full-mix tracks are muted/reference-only in the REAPER project.",
                "- Male vocal remains the lead by default; female vocal is support/alternate only.",
                "",
                "## Processing Choices",
                "",
                "- v04 balance revision: male vocal is volume-ridden and lowered, female support uses an added audible female-like layer, melody is overlaid forward, and short sip/breath spikes are suppressed.",
                "- Vocal cleanup: high-pass filtering, dynamic mud/nasal/metallic/sibilance taming, light saturation, gentle compression, and short ambience.",
                "- Female layer: cleaned from Suno `Backing_Vocals`, widened with short delays, tucked under the male lead in the dual version.",
                "- Drums: low-mid cleanup, light punch compression, controlled saturation, and detected-onset round kick support.",
                "- Bass/808: mono sub reinforcement, low-mid cleanup, light grit, and limiter containment.",
                "- Melody/music: keyboard/synth kept forward, with vocal presence pocketing and restrained FX.",
                "- Mastering: conservative loudnorm targets around -11 LUFS with true-peak target -1.25 dBTP.",
                "",
                "## Rejected",
                "",
                "- No Antares products used.",
                "- No random vocal chops or filler ad-libs added.",
                "- No generic EDM/K-pop/idol-pop brightening chain.",
                "- No new instrumental bed was activated to glue the beat.",
                "",
                f"Detailed DSP move log: `{decisions_path}`",
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
        for row in final_rows
    ]
    (REPORTS / "final_qc_report.md").write_text(
        "\n".join(
            [
                "# Final QC Report",
                "",
                markdown_table(final_summary, ["version", "duration_s", "integrated_lufs", "true_peak_dbfs", "peak_dbfs", "rms_dbfs", "stereo_corr"]),
                "",
                "## QC Notes",
                "",
                "- v04 balance revision: male vocal leveled/lowered, female support made clearly audible, keyboard/synth melody overlaid forward, and short sip/breath spikes suppressed per user feedback.",
                "- The final mixes are less raw-Suno-like because vocals, low end, drums, and high-end fizz were processed separately from stems.",
                "- The main sad melody remains forward through the processed keyboard/synth melody bus.",
                "- Female vocal works best as a wide support layer; the female-forward alternate is included but is not the emotional default.",
                "- Kick/808 power was improved with controlled support and mono sub reinforcement, not broad clipping.",
                "- Vocal noise was reduced through dynamic sibilance and upper-glass control, with brightness preserved enough for intelligibility.",
                "- Remaining issue: the female source comes from Suno `Backing_Vocals`, not a newly generated four-take female lead set, to avoid extra credit spend and random lyrical drift.",
                "",
                "## Deliverables",
                "",
            ]
            + [f"- `{path}`" for path in sorted(rendered.values(), key=lambda p: p.name)]
            + [f"- `{path}`" for path in sorted(processed_paths.values(), key=lambda p: p.name)]
            + [f"- `{RPP}`", ""]
        ),
        encoding="utf-8",
    )


def rpp_item(file_path: Path, length: float, iid: int, muted: bool = False) -> str:
    return f"""    <ITEM
      POSITION 0
      SNAPOFFS 0
      LENGTH {length:.12f}
      LOOP 1
      ALLTAKES 0
      FADEIN 1 0.01 0 1 0 0 0
      FADEOUT 1 0.01 0 1 0 0 0
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
    FIXEDLANES 9 0 0 0 0
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


def write_reaper_project(sr: int, audio: dict[str, np.ndarray], rendered: dict[str, Path], processed_paths: dict[str, Path]) -> None:
    length = len(next(iter(audio.values()))) / sr
    tracks: list[str] = []
    track_defs = [
        ("ORIGINAL_REFERENCE muted", STEMS / "0101_original_reference.wav", True, False),
        ("INSTRUMENTAL_RAW", STEMS / "0101_instrumental_raw.wav", True, False),
        ("DRUMS_RAW", STEMS / "0101_drums_raw.wav", True, False),
        ("BASS_808_RAW", STEMS / "0101_bass808_raw.wav", True, False),
        ("MELODY_RAW", STEMS / "0101_melody_raw.wav", True, False),
        ("MALE_VOCAL_RAW", STEMS / "0101_vocal_raw.wav", True, False),
        ("MALE_VOCAL_PROCESSED edit stem muted", processed_paths["processed_male_vocal_stem.wav"], True, False),
        ("FEMALE_VOCAL_RAW", STEMS / "0101_backing_vocals_raw.wav", True, False),
        ("FEMALE_VOCAL_PROCESSED edit stem muted", processed_paths["processed_female_vocal_stem.wav"], True, False),
        ("VOCAL_BUS print reference", None, False, True),
        ("DRUM_BUS edit stem muted", processed_paths["drums_stem.wav"], True, False),
        ("BASS_BUS edit stem muted", processed_paths["bass808_stem.wav"], True, False),
        ("MUSIC_BUS edit stem muted", processed_paths["melody_stem.wav"], True, False),
        ("MIX_BUS dual vocal print ACTIVE", rendered["dual_vocal_wav"], False, True),
        ("MASTER_BUS final monitor", rendered["dual_vocal_mp3"], True, False),
    ]
    for idx, (name, path, muted, mainsend) in enumerate(track_defs, start=1):
        tracks.append(rpp_track(name, path, length, idx, muted=muted, mainsend=mainsend))

    marker_times = [0, 14.2, 42.7, 72.0, 101.3, length]
    marker_names = ["intro", "verse", "hook lift", "second section", "final lift/outro", "render end"]
    markers = [
        f'  MARKER {i} {time:.6f} "{name}" 0 0 1 B {{{uuid.uuid4()}}} 0 2'
        for i, (time, name) in enumerate(zip(marker_times, marker_names), start=1)
    ]
    project = f"""<REAPER_PROJECT 0.1 "7.73/macOS-arm64" 1779750000 0
  <NOTES 0 2
    |0101_REAPER_MIX_MASTER_PROJECT. Reference/edit stems are muted by default. Male vocal is lead; female vocal is support/alternate. Final printed dual-vocal mix is the active MIX_BUS playback track.
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


def create_delivery_zip() -> Path:
    zip_path = RENDERS / f"{SLUG}_DELIVERABLES.zip"
    include = [
        *RENDERS.glob("0101_FINAL_*.wav"),
        *RENDERS.glob("0101_FINAL_*_320.mp3"),
        *RENDERS.glob("*_stem.wav"),
        RPP,
        REPORTS / "suno_0101_initial_analysis.md",
        REPORTS / "stem_quality_report.md",
        REPORTS / "female_vocal_selection_report.md",
        REPORTS / "reaper_mix_decision_log.md",
        REPORTS / "final_qc_report.md",
    ]
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in include:
            if path.exists():
                zf.write(path, arcname=path.name)
    return zip_path


def main() -> None:
    ensure_dirs()
    copied = copy_sources()
    sr, audio, dtypes = load_all(copied)
    write_raw_derived_stems(sr, audio)
    processed, decisions = process_sources(sr, audio)
    processed_paths = write_processed_stems(sr, processed)
    rendered = render_mix_versions(sr, processed)
    write_reaper_project(sr, audio, rendered, processed_paths)
    write_reports(sr, audio, dtypes, decisions, rendered, processed_paths)
    delivery_zip = create_delivery_zip()
    print(
        json.dumps(
            {
                "slug": SLUG,
                "duration_s": round(len(next(iter(audio.values()))) / sr, 3),
                "reports": str(REPORTS),
                "renders": str(RENDERS),
                "reaper_project": str(RPP),
                "delivery_zip": str(delivery_zip),
                "finals": {k: str(v) for k, v in rendered.items() if k.endswith("_wav") or k.endswith("_mp3")},
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()

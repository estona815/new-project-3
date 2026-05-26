from __future__ import annotations

import csv
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
    process_instrument,
    process_vocal,
    read_wav,
    reverb_send,
    rms,
    saturate,
    sidechain_duck_full,
    soft_clip,
    stem_metrics,
    vocal_harmonic_density,
    write_float_wav,
)
from tools.mgmg_v05_more_female_tuned_grit import autotune_edge_layer  # noqa: E402
from tools.mgmg_v11_female_70_mseq_layers import (  # noqa: E402
    bass_stable_grit,
    drums_stable_punch,
    stable_master_tone,
    static_music_space,
)


SLUG = "0101_male_only_v09_strong_tune_mix"
SOURCE_SLUG = "0101_suno_studio_v01"
BPM = 135

SRC = ROOT / "audio_work" / SOURCE_SLUG / "source_downloads" / "0101_multitrack_folder"
WORK = ROOT / "audio_work" / SLUG
STEMS = WORK / "stems"
PROCESSED = WORK / "processed"
INTERMEDIATE = WORK / "intermediate"
RENDERS = ROOT / "renders" / SLUG
REPORTS = ROOT / "reports" / SLUG
REAPER_DIR = ROOT / "reaper" / SLUG
RPP = REAPER_DIR / "0101_REAPER_MALE_ONLY_STRONG_TUNE_PROJECT.rpp"

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
    for directory in (WORK, STEMS, PROCESSED, INTERMEDIATE, RENDERS, REPORTS, REAPER_DIR):
        directory.mkdir(parents=True, exist_ok=True)


def pad_or_trim(y: np.ndarray, length: int) -> np.ndarray:
    if len(y) == length:
        return y.astype(np.float32)
    if len(y) > length:
        return y[:length].astype(np.float32)
    return np.vstack([y.astype(np.float32), np.zeros((length - len(y), 2), dtype=np.float32)])


def safe_normalize_to_rms(y: np.ndarray, target_db: float) -> np.ndarray:
    if rms(y) < 1e-10:
        return y.astype(np.float32)
    return normalize_to_rms(y, target_db).astype(np.float32)


def safe_sum(parts: list[tuple[np.ndarray, float]], length: int, ceiling_db: float = -1.6) -> np.ndarray:
    out = np.zeros((length, 2), dtype=np.float32)
    for y, gain_db in parts:
        out += pad_or_trim(y, length) * float(amp_db(gain_db))
    return limiter(out, ceiling_db)


def fade_window(length: int, fade_samples: int) -> np.ndarray:
    env = np.ones(length, dtype=np.float32)
    fade_samples = min(max(int(fade_samples), 1), max(length // 2, 1))
    if fade_samples > 1:
        ramp = np.linspace(0.0, 1.0, fade_samples, dtype=np.float32)
        env[:fade_samples] *= ramp
        env[-fade_samples:] *= ramp[::-1]
    return env


def edge_fade(y: np.ndarray, sr: int, fade_ms: float = 28.0) -> np.ndarray:
    out = y.copy()
    n = min(max(int(sr * fade_ms / 1000.0), 1), max(len(out) // 2, 1))
    if n > 1:
        ramp = np.linspace(0.0, 1.0, n, dtype=np.float32)
        out[:n] *= ramp[:, None]
        out[-n:] *= ramp[::-1, None]
    return out.astype(np.float32)


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


def load_sources(copied: dict[str, Path]) -> tuple[int, dict[str, np.ndarray], dict[str, str]]:
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
    audio = {name: pad_or_trim(y, length) for name, y in audio.items()}
    return 48000, audio, dtypes


def write_raw_derived_stems(sr: int, audio: dict[str, np.ndarray]) -> None:
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
            (audio["0101_synth_raw.wav"], -0.9),
            (audio["0101_woodwinds_raw.wav"], -3.0),
            (audio["0101_strings_raw.wav"], -3.2),
            (audio["0101_guitar_raw.wav"], -4.0),
        ],
        length,
    )
    write_float_wav(STEMS / "0101_instrumental_raw.wav", sr, instrumental)
    write_float_wav(STEMS / "0101_melody_raw.wav", sr, melody)


def spectral_denoise_vocal(
    y: np.ndarray,
    sr: int,
    label: str,
    reduction: float = 0.57,
    high_reduction: float = 0.78,
    floor: float = 0.48,
    high_floor: float = 0.34,
) -> tuple[np.ndarray, dict[str, object]]:
    nperseg = 2048
    noverlap = 1024
    out_channels = []
    noise_counts = []
    mean_gains = []
    high_gains = []
    for ch in range(2):
        freq, _, zxx = signal.stft(
            y[:, ch],
            fs=sr,
            window="hann",
            nperseg=nperseg,
            noverlap=noverlap,
            boundary="zeros",
            padded=True,
        )
        mag = np.abs(zxx).astype(np.float32)
        phase = np.exp(1j * np.angle(zxx))
        frame_energy = np.mean(mag, axis=0)
        if frame_energy.size == 0:
            out_channels.append(y[:, ch])
            continue
        noise_mask = frame_energy <= np.percentile(frame_energy, 24)
        if int(np.sum(noise_mask)) < 8:
            noise_mask = frame_energy <= np.percentile(frame_energy, 34)
        profile = np.percentile(mag[:, noise_mask], 58, axis=1)[:, None] if np.any(noise_mask) else np.percentile(mag, 18, axis=1)[:, None]
        high_weight = np.clip((freq[:, None] - 3800.0) / 6200.0, 0.0, 1.0).astype(np.float32)
        reduction_curve = reduction + (high_reduction - reduction) * high_weight
        floor_curve = floor + (high_floor - floor) * high_weight
        ratio = profile / (mag + 1e-8)
        gain = 1.0 - reduction_curve * np.power(np.clip(ratio, 0.0, 4.0), 0.82)
        gain = np.clip(gain, floor_curve, 1.0).astype(np.float32)
        _, cleaned = signal.istft(mag * gain * phase, fs=sr, window="hann", nperseg=nperseg, noverlap=noverlap, input_onesided=True, boundary=True)
        cleaned = cleaned.astype(np.float32)
        if len(cleaned) < len(y):
            cleaned = np.pad(cleaned, (0, len(y) - len(cleaned)))
        out_channels.append(cleaned[: len(y)])
        noise_counts.append(int(np.sum(noise_mask)))
        mean_gains.append(float(np.mean(gain)))
        high_mask = freq >= 5500
        high_gains.append(float(np.mean(gain[high_mask])) if np.any(high_mask) else float(np.mean(gain)))
    return np.column_stack(out_channels).astype(np.float32), {
        "stage": "spectral_denoise_vocal",
        "label": label,
        "reduction": reduction,
        "high_reduction": high_reduction,
        "floor": floor,
        "high_floor": high_floor,
        "noise_frames_per_channel": noise_counts,
        "mean_gain": round(float(np.mean(mean_gains)), 4) if mean_gains else 1.0,
        "mean_high_band_gain": round(float(np.mean(high_gains)), 4) if high_gains else 1.0,
    }


def suppress_sip_breaths(y: np.ndarray, sr: int, label: str) -> tuple[np.ndarray, dict[str, object]]:
    high = bandpass(y, sr, 5100, 12200, 3)
    mid = bandpass(y, sr, 260, 2600, 2)
    high_env = np.abs(np.mean(high, axis=1))
    mid_env = np.abs(np.mean(mid, axis=1))
    smooth = max(int(sr * 0.018), 1)
    kernel = np.ones(smooth, dtype=np.float32) / smooth
    high_env = np.convolve(high_env, kernel, mode="same")
    mid_env = np.convolve(mid_env, kernel, mode="same")
    active = high_env[high_env > 1e-8]
    if not len(active):
        return y.astype(np.float32), {"stage": "sip_breath_suppress", "label": label, "events": 0}
    threshold = max(float(np.percentile(active, 96.5)), float(np.max(active) * 0.30))
    ratio = high_env / (mid_env + 1e-8)
    mask = (high_env > threshold) & (ratio > 1.42)
    width = max(int(sr * 0.062), 1)
    mask = np.convolve(mask.astype(np.float32), np.ones(width, dtype=np.float32), mode="same") > 0
    fade = max(int(sr * 0.045), 3)
    fade_kernel = np.hanning(fade).astype(np.float32)
    fade_kernel /= max(float(np.sum(fade_kernel)), 1e-9)
    mask_f = np.clip(np.convolve(mask.astype(np.float32), fade_kernel, mode="same"), 0.0, 1.0)
    out = y - high * (mask_f[:, None] * 0.78)
    out, stats = dynamic_band_tame(out.astype(np.float32), sr, 5600, 11800, 3.5, 63, 55)
    return out.astype(np.float32), {
        "stage": "sip_breath_suppress",
        "label": label,
        "events": int(np.sum(np.diff(mask.astype(np.int8), prepend=0) == 1)),
        "dynamic_tame": stats,
    }


def suppress_beep_artifacts(y: np.ndarray, sr: int, label: str, strength: float = 0.96) -> tuple[np.ndarray, dict[str, object]]:
    high = bandpass(y, sr, 3500, 15500, 4)
    low_mid = bandpass(y, sr, 150, 2600, 2)
    high_env = np.abs(np.mean(high, axis=1))
    low_env = np.abs(np.mean(low_mid, axis=1))
    smooth = max(int(sr * 0.006), 1)
    kernel = np.ones(smooth, dtype=np.float32) / smooth
    high_env = np.convolve(high_env, kernel, mode="same")
    low_env = np.convolve(low_env, kernel, mode="same")
    active = high_env[high_env > 1e-8]
    if not len(active):
        return y.astype(np.float32), {"stage": "beep_artifact_suppress", "label": label, "events": 0}
    threshold = max(float(np.percentile(active, 95.8)), float(np.max(active) * 0.20))
    ratio = high_env / (low_env + 1e-8)
    mask = (high_env > threshold) & (ratio > 0.68)
    mask[: int(sr * 0.18)] = True
    width = max(int(sr * 0.050), 1)
    mask = np.convolve(mask.astype(np.float32), np.ones(width, dtype=np.float32), mode="same") > 0
    fade = max(int(sr * 0.065), 3)
    fade_kernel = np.hanning(fade).astype(np.float32)
    fade_kernel /= max(float(np.sum(fade_kernel)), 1e-9)
    mask_f = np.clip(np.convolve(mask.astype(np.float32), fade_kernel, mode="same"), 0.0, 1.0)
    out = y - high * (mask_f[:, None] * strength)
    out, dyn = dynamic_band_tame(out.astype(np.float32), sr, 3600, 12500, 3.1, 60, 42)
    return out.astype(np.float32), {
        "stage": "beep_artifact_suppress",
        "label": label,
        "events": int(np.sum(np.diff(mask.astype(np.int8), prepend=0) == 1)),
        "strength": strength,
        "dynamic_tame": dyn,
    }


def vocal_level_ride(
    y: np.ndarray,
    sr: int,
    target_db: float,
    max_cut_db: float = -7.5,
    max_boost_db: float = 0.9,
    label: str = "vocal",
) -> tuple[np.ndarray, dict[str, object]]:
    mono = np.mean(y, axis=1)
    frame = max(int(sr * 0.060), 1)
    hop = max(int(sr * 0.020), 1)
    values: list[float] = []
    centers: list[int] = []
    for start in range(0, max(len(mono) - frame, 1), hop):
        seg = mono[start : start + frame]
        if len(seg):
            values.append(math.sqrt(float(np.mean(seg * seg)) + 1e-12))
            centers.append(start + len(seg) // 2)
    if not values:
        return y.astype(np.float32), {"stage": "vocal_level_ride", "label": label, "active_windows": 0}
    vals = np.array(values, dtype=np.float32)
    active = vals > max(1e-5, float(np.percentile(vals, 40)) * 0.54)
    gain_points = np.zeros_like(vals)
    if np.any(active):
        current_db = db_amp(vals[active])
        desired = np.clip(target_db - current_db, max_cut_db, max_boost_db)
        gain_points[active] = desired
    sample_gain = np.interp(np.arange(len(mono)), centers, gain_points, left=0.0, right=0.0).astype(np.float32)
    kernel_len = max(int(sr * 0.240), 3)
    kernel = np.hanning(kernel_len).astype(np.float32)
    kernel /= max(float(np.sum(kernel)), 1e-9)
    sample_gain = np.convolve(sample_gain, kernel, mode="same").astype(np.float32)
    return (y * amp_db(sample_gain)[:, None]).astype(np.float32), {
        "stage": "vocal_level_ride",
        "label": label,
        "target_db": target_db,
        "active_windows": int(np.sum(active)),
        "min_gain_db": round(float(np.min(sample_gain)), 3),
        "median_gain_db": round(float(np.median(sample_gain)), 3),
        "max_gain_db": round(float(np.max(sample_gain)), 3),
    }


def male_dynamic_resonance_eq(y: np.ndarray, sr: int) -> tuple[np.ndarray, list[dict[str, object]]]:
    out = y.copy()
    moves: list[dict[str, object]] = []
    for low, high, cut, pct, smooth, name in [
        (245, 405, 2.0, 65, 145, "low_mud_ring"),
        (430, 640, 1.5, 70, 130, "box_resonance"),
        (690, 960, 2.2, 63, 115, "nasal_plastic_ring"),
        (980, 1360, 2.0, 64, 105, "formant_honk"),
        (1550, 2260, 1.2, 72, 95, "forward_resonance"),
        (2820, 3920, 2.3, 62, 72, "hard_attack_edge"),
        (4100, 5700, 2.0, 63, 62, "scratch_presence"),
        (6100, 8500, 3.8, 58, 48, "sibilance_hash"),
        (8800, 12800, 3.0, 60, 44, "ai_air_fizz"),
    ]:
        out, stats = dynamic_band_tame(out, sr, low, high, cut, pct, smooth)
        moves.append({"stage": f"male_dynamic_eq_{name}", **stats})
    out = biquad_peaking(out, sr, 315, -0.45, 1.2)
    out = biquad_peaking(out, sr, 880, -0.55, 1.25)
    out = biquad_peaking(out, sr, 2920, 0.45, 0.92)
    out = biquad_shelf(out, sr, 11600, -0.22, True)
    moves.append({"stage": "male_static_finish_eq", "presence_restore_db": 0.45, "air_trim_db": -0.22})
    return out.astype(np.float32), moves


def strong_tune_density_layer(vocal: np.ndarray, sr: int) -> tuple[np.ndarray, dict[str, object]]:
    base_edge = autotune_edge_layer(vocal, sr)
    fast = bandpass(vocal, sr, 220, 5000, 3)
    fast = compressor(fast, sr, threshold_db=-31.5, ratio=5.4, smooth_ms=24, makeup_db=1.25)
    fixed = fast * 0.68 + delay_samples(fast, int(sr * 0.0035)) * 0.32
    fixed = vocal_harmonic_density(fixed, sr, drive_db=4.0, wet=0.23)
    fixed, bite = dynamic_band_tame(fixed, sr, 2700, 5900, 2.0, 70, 62)
    fixed, hiss = dynamic_band_tame(fixed, sr, 5900, 9800, 2.9, 66, 46)
    fixed = biquad_peaking(fixed, sr, 920, -0.9, 1.0)
    fixed = biquad_peaking(fixed, sr, 2500, 0.85, 0.9)
    fixed = biquad_shelf(fixed, sr, 9800, -0.55, True)
    layer = limiter(base_edge * float(amp_db(-1.8)) + fixed * float(amp_db(-2.8)), -2.2)
    layer = safe_normalize_to_rms(layer, -23.2)
    return layer.astype(np.float32), {
        "stage": "strong_tune_density_layer",
        "wet_layer_rms_dbfs": -23.2,
        "mix_gain_db": -4.8,
        "retune_feel": "fast hard-tune edge via compressed parallel harmonic-density layer",
        "note": "DSP tune-feel layer; no Antares or paid pitch plugin used",
        "bite_tame": bite,
        "hiss_tame": hiss,
    }


def process_male_vocal(raw: np.ndarray, sr: int) -> tuple[np.ndarray, list[dict[str, object]]]:
    moves: list[dict[str, object]] = []
    out = edge_fade(raw, sr, 30.0)
    out = butter_filter(out, sr, "highpass", 92, 3)
    moves.append({"stage": "male_highpass", "hz": 92})
    out, beep = suppress_beep_artifacts(out, sr, "male_lead", strength=0.96)
    out, sip = suppress_sip_breaths(out, sr, "male_lead_pre")
    moves.extend([beep, sip])
    out, denoise = spectral_denoise_vocal(out, sr, "male_lead", reduction=0.57, high_reduction=0.78, floor=0.48, high_floor=0.34)
    moves.append(denoise)
    out, stock_moves = process_vocal("lead_vocal", out, sr)
    moves.extend(stock_moves)
    out, resonance_moves = male_dynamic_resonance_eq(out, sr)
    moves.extend(resonance_moves)
    out, sip_post = suppress_sip_breaths(out, sr, "male_lead_post")
    moves.append(sip_post)
    tune_layer, tune_stats = strong_tune_density_layer(out, sr)
    out = out * float(amp_db(0.15)) + tune_layer * float(amp_db(-4.8))
    moves.append(tune_stats)
    out, edge_control = dynamic_band_tame(out, sr, 2650, 6200, 1.35, 72, 78)
    out, air_control = dynamic_band_tame(out, sr, 6200, 11800, 2.2, 66, 52)
    moves.extend([{"stage": "post_tune_edge_control", **edge_control}, {"stage": "post_tune_air_control", **air_control}])
    out = compressor(out, sr, threshold_db=-22.5, ratio=2.45, smooth_ms=62, makeup_db=0.45)
    out = saturate(out, drive_db=1.8, mix=0.105)
    out = biquad_peaking(out, sr, 2850, 0.45, 0.9)
    out = biquad_shelf(out, sr, 10600, -0.10, True)
    out, ride = vocal_level_ride(out, sr, target_db=-22.6, max_cut_db=-7.4, max_boost_db=0.65, label="male_lead")
    moves.append(ride)
    out = safe_normalize_to_rms(out, -20.35)
    out = limiter(edge_fade(out, sr, 18.0), -2.0)
    moves.append({"stage": "male_final_gain_stage", "target_rms_dbfs": -20.35, "female_tracks": "muted/excluded"})
    return out.astype(np.float32), moves


def detect_drum_onsets(drums: np.ndarray, sr: int, max_count: int = 180) -> list[int]:
    mono = np.mean(bandpass(drums, sr, 35, 180, 3), axis=1)
    frame = int(sr * 0.012)
    hop = int(sr * 0.01)
    if len(mono) < frame * 2:
        return []
    env = np.array(
        [math.sqrt(float(np.mean(mono[i : i + frame] ** 2)) + 1e-12) for i in range(0, len(mono) - frame, hop)],
        dtype=np.float32,
    )
    diff = np.maximum(0.0, env - np.roll(env, 1))
    threshold = max(float(np.percentile(diff, 93.2)), float(np.max(diff) * 0.17))
    min_gap = max(int(0.18 / (hop / sr)), 1)
    onsets: list[int] = []
    last = -min_gap
    for idx, value in enumerate(diff):
        if value < threshold or idx - last < min_gap:
            continue
        if value >= float(np.max(diff[max(0, idx - 2) : min(len(diff), idx + 3)])):
            onsets.append(idx * hop)
            last = idx
    return onsets[:max_count]


def make_round_kick_support(length: int, sr: int, onsets: list[int]) -> np.ndarray:
    support = np.zeros((length, 2), dtype=np.float32)
    dur = int(sr * 0.22)
    t = np.arange(dur, dtype=np.float32) / sr
    sweep = 64.0 - 18.0 * np.clip(t / 0.18, 0.0, 1.0)
    phase = 2.0 * np.pi * np.cumsum(sweep) / sr
    body = np.sin(phase) * np.exp(-t * 18.0)
    click = np.sin(2.0 * np.pi * 118.0 * t) * np.exp(-t * 52.0)
    shape = (body * 0.82 + click * 0.14).astype(np.float32)
    shape *= fade_window(len(shape), int(sr * 0.004))
    for onset in onsets:
        end = min(onset + dur, length)
        if end > onset:
            seg = shape[: end - onset]
            support[onset:end, 0] += seg
            support[onset:end, 1] += seg
    support = butter_filter(support, sr, "lowpass", 760, 3)
    support = saturate(support, drive_db=1.0, mix=0.10)
    return safe_normalize_to_rms(support, -26.0) if np.max(np.abs(support)) > 1e-8 else support.astype(np.float32)


def process_instrumental(audio: dict[str, np.ndarray], sr: int, vocal_trigger: np.ndarray) -> tuple[dict[str, np.ndarray], dict[str, object]]:
    length = len(audio["0101_original_reference.wav"])
    drums_proc, drum_moves = drums_stable_punch(audio["0101_drums_raw.wav"], sr)
    onsets = detect_drum_onsets(drums_proc, sr)
    kick_support = make_round_kick_support(length, sr, onsets)
    drums_final = limiter(drums_proc * float(amp_db(0.50)) + kick_support * float(amp_db(-7.6)), -1.7)

    bass_proc, bass_moves = bass_stable_grit(audio["0101_bass808_raw.wav"], drums_final, sr)
    sub = butter_filter(bass_proc, sr, "lowpass", 98, 4)
    sub = np.column_stack([np.mean(sub, axis=1), np.mean(sub, axis=1)]).astype(np.float32)
    bass_final = limiter(bass_proc * float(amp_db(0.85)) + sub * float(amp_db(-2.5)), -1.8)

    keys_proc, keys_moves = process_instrument("keys", audio["0101_keyboard_raw.wav"], sr, drums_final, vocal_trigger)
    synth_proc, synth_moves = process_instrument("synth", audio["0101_synth_raw.wav"], sr, drums_final, vocal_trigger)
    fx_proc, fx_moves = process_instrument("other", audio["0101_fx_raw.wav"], sr, drums_final, vocal_trigger)
    perc_proc, perc_moves = process_instrument("other", audio["0101_percussion_raw.wav"], sr, drums_final, vocal_trigger)
    sparse_melody = safe_sum(
        [
            (audio["0101_melody_raw.wav"], 0.0),
            (audio["0101_woodwinds_raw.wav"], -5.5),
            (audio["0101_strings_raw.wav"], -5.8),
            (audio["0101_guitar_raw.wav"], -6.8),
            (audio["0101_brass_raw.wav"], -7.0),
        ],
        length,
    )
    melody = safe_sum([(keys_proc, 0.0), (synth_proc, -1.3), (sparse_melody, -4.7)], length, -1.8)
    melody = butter_filter(melody, sr, "highpass", 92, 3)
    melody, melody_mud = dynamic_band_tame(melody, sr, 220, 640, 1.5, 72, 145)
    melody, melody_nasal = dynamic_band_tame(melody, sr, 760, 1280, 0.8, 78, 135)
    melody, melody_glass = dynamic_band_tame(melody, sr, 3600, 7800, 0.75, 80, 90)
    melody = biquad_peaking(melody, sr, 1550, 0.50, 0.9)
    melody = biquad_peaking(melody, sr, 3200, 0.45, 1.0)
    melody = biquad_shelf(melody, sr, 9800, -0.12, True)
    melody = static_music_space(melody, sr)
    melody = safe_normalize_to_rms(melody, -20.6)
    melody = sidechain_duck_full(melody, vocal_trigger, sr, amount_db=0.12, release_ms=125, threshold_percentile=72)

    fx_bed = butter_filter(fx_proc + perc_proc * float(amp_db(-5.2)), sr, "highpass", 130, 2)
    fx_bed, fx_mud = dynamic_band_tame(fx_bed, sr, 220, 700, 1.8, 73, 150)

    inst_clean = butter_filter(audio["0101_instrumental_raw.wav"], sr, "highpass", 24, 3)
    inst_clean, inst_mud = dynamic_band_tame(inst_clean, sr, 210, 520, 1.2, 74, 145)
    inst_clean, inst_nasal = dynamic_band_tame(inst_clean, sr, 650, 1180, 0.8, 79, 150)
    inst_clean = biquad_shelf(inst_clean, sr, 10800, -0.20, True)

    instrumental = safe_sum(
        [
            (inst_clean, -1.8),
            (drums_final, -8.3),
            (bass_final, -8.5),
            (melody, 4.2),
            (fx_bed, -12.0),
        ],
        length,
        -1.5,
    )
    instrumental = sidechain_duck_full(instrumental, vocal_trigger, sr, amount_db=0.08, release_ms=145, threshold_percentile=73)
    instrumental = limiter(instrumental, -1.5)
    processed = {
        "instrumental": instrumental,
        "drums": drums_final,
        "bass": bass_final,
        "melody": melody,
        "fx": fx_bed,
        "kick_support": kick_support,
    }
    moves = {
        "drums": drum_moves + [{"stage": "round_kick_support", "detected_onsets": len(onsets), "gain_db": -7.6}],
        "bass": bass_moves + [{"stage": "mono_sub_reinforcement", "lowpass_hz": 98, "gain_db": -2.5}],
        "melody": [
            *keys_moves,
            *synth_moves,
            {"stage": "melody_forward_overlay", "rms_target_dbfs": -20.6, "mix_gain_db": 4.2},
            {"stage": "melody_mud_control", **melody_mud},
            {"stage": "melody_nasal_resonance_control", **melody_nasal},
            {"stage": "melody_glass_control", **melody_glass},
        ],
        "fx": fx_moves + perc_moves + [{"stage": "fx_tucked", **fx_mud}],
        "instrumental": [
            {"stage": "raw_instrumental_cleanup", **inst_mud},
            {"stage": "instrumental_nasal_cleanup", **inst_nasal},
        ],
    }
    return processed, moves


def full_mix_resonance_polish(y: np.ndarray, sr: int) -> tuple[np.ndarray, list[dict[str, object]]]:
    out = y.copy()
    moves: list[dict[str, object]] = []
    for low, high, cut, pct, smooth, name in [
        (230, 420, 0.8, 76, 170, "mix_low_mid_resonance"),
        (680, 1120, 0.70, 78, 145, "mix_nasal_resonance"),
        (2450, 4200, 0.75, 76, 105, "mix_presence_spike"),
        (5400, 9200, 0.95, 74, 72, "mix_sibilance_hash"),
    ]:
        out, stats = dynamic_band_tame(out, sr, low, high, cut, pct, smooth)
        moves.append({"stage": name, **stats})
    out = biquad_peaking(out, sr, 760, -0.10, 0.9)
    out = biquad_shelf(out, sr, 12000, -0.08, True)
    moves.append({"stage": "full_mix_static_finish", "nasal_db": -0.10, "air_trim_db": -0.08})
    return out.astype(np.float32), moves


def render_mix(sr: int, processed: dict[str, np.ndarray]) -> dict[str, Path]:
    length = len(processed["instrumental"])
    male = processed["male"]
    vocal_reverb = reverb_send(male, sr, decay_s=0.62, wet_db=-22.5, predelay_ms=24, hp_hz=360, lp_hz=7400, seed=91)
    tune_shadow = bandpass(male, sr, 1800, 5200, 3)
    tune_shadow = compressor(tune_shadow, sr, threshold_db=-33.0, ratio=4.2, smooth_ms=24, makeup_db=0.0)
    tune_shadow, _ = dynamic_band_tame(tune_shadow, sr, 3600, 6900, 1.6, 70, 55)
    tune_shadow = pan_stereo(delay_samples(tune_shadow, int(sr * 0.006)), 0.0) * float(amp_db(-16.0))

    premaster = safe_sum(
        [
            (processed["instrumental"], -0.25),
            (processed["melody"], 2.1),
            (male, -5.6),
            (tune_shadow, 0.0),
            (vocal_reverb, -0.5),
        ],
        length,
        -1.7,
    )
    premaster, mix_moves = full_mix_resonance_polish(edge_fade(premaster, sr, 24.0), sr)
    premaster = stable_master_tone(premaster, sr)
    premaster = compressor(premaster, sr, threshold_db=-11.8, ratio=1.08, smooth_ms=260, makeup_db=0.0)
    premaster = soft_clip(premaster, drive_db=0.32, ceiling=0.88)
    premaster = limiter(premaster, -2.2)

    premaster_path = RENDERS / "0101_mix_male_only_strong_tune_premaster.wav"
    final_wav = RENDERS / "0101_FINAL_male_only_strong_tune.wav"
    final_mp3 = RENDERS / "0101_FINAL_male_only_strong_tune_320.mp3"
    write_float_wav(premaster_path, sr, premaster)
    ffmpeg_loudnorm(premaster_path, final_wav, target_lufs=-11.3, target_tp=-1.25, target_lra=4.0)
    convert_mp3(final_wav, final_mp3)
    return {
        "premaster": premaster_path,
        "final_wav": final_wav,
        "final_mp3": final_mp3,
        "mix_moves": mix_moves,  # type: ignore[dict-item]
    }


def write_processed_stems(sr: int, processed: dict[str, np.ndarray]) -> dict[str, Path]:
    outputs = {
        "processed_male_vocal_stem.wav": processed["male"],
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
    muted_female = np.zeros_like(processed["male"], dtype=np.float32)
    female_path = RENDERS / "muted_female_vocal_removed.wav"
    write_float_wav(female_path, sr, muted_female)
    paths["muted_female_vocal_removed.wav"] = female_path
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


def write_reaper_project(sr: int, audio: dict[str, np.ndarray], rendered: dict[str, Path], processed_paths: dict[str, Path]) -> None:
    length = len(next(iter(audio.values()))) / sr
    track_defs = [
        ("ORIGINAL_REFERENCE muted", STEMS / "0101_original_reference.wav", True, False),
        ("MALE_VOCAL_RAW muted", STEMS / "0101_vocal_raw.wav", True, False),
        ("FEMALE_BACKING_RAW muted removed", STEMS / "0101_backing_vocals_raw.wav", True, False),
        ("MALE_VOCAL_PROCESSED strong tune muted", processed_paths["processed_male_vocal_stem.wav"], True, False),
        ("DRUM_BUS print muted", processed_paths["drums_stem.wav"], True, False),
        ("BASS_BUS print muted", processed_paths["bass808_stem.wav"], True, False),
        ("MELODY_BUS print muted", processed_paths["melody_stem.wav"], True, False),
        ("INSTRUMENTAL_PROCESSED muted", processed_paths["processed_instrumental_stem.wav"], True, False),
        ("MIX_BUS male only strong tune ACTIVE", rendered["final_wav"], False, True),
        ("MASTER_BUS mp3 monitor muted", rendered["final_mp3"], True, False),
    ]
    tracks = [
        rpp_track(name, path, length, idx, muted=muted, mainsend=mainsend)
        for idx, (name, path, muted, mainsend) in enumerate(track_defs, start=1)
    ]
    marker_times = [0, 14.2, 42.7, 72.0, 101.3, length]
    marker_names = ["intro", "verse", "hook lift", "second section", "final lift/outro", "render end"]
    markers = [
        f'  MARKER {i} {time:.6f} "{name}" 0 0 1 B {{{uuid.uuid4()}}} 0 2'
        for i, (time, name) in enumerate(zip(marker_times, marker_names), start=1)
    ]
    project = f"""<REAPER_PROJECT 0.1 "7.73/macOS-arm64" 1779750000 0
  <NOTES 0 2
    |0101 male-only strong tune revision. Female/backing vocal tracks are muted/excluded. Active playback is the printed male-only master.
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


def write_reports(
    sr: int,
    audio: dict[str, np.ndarray],
    dtypes: dict[str, str],
    decisions: dict[str, object],
    rendered: dict[str, Path],
    processed_paths: dict[str, Path],
) -> None:
    stem_rows = []
    roles = {
        "0101_original_reference.wav": "muted_reference",
        "0101_original_reference_duplicate.wav": "muted_duplicate_reference",
        "0101_vocal_raw.wav": "male_vocal_source",
        "0101_backing_vocals_raw.wav": "female_backing_removed",
        "0101_drums_raw.wav": "drums",
        "0101_bass808_raw.wav": "bass_808",
        "0101_keyboard_raw.wav": "melody_keyboard",
        "0101_synth_raw.wav": "melody_synth",
        "0101_fx_raw.wav": "fx",
    }
    for name, y in sorted(audio.items()):
        role = roles.get(name, "support_or_sparse_reference")
        row = stem_metrics(name, role, y, sr, dtypes[name])
        if role == "female_backing_removed":
            row["status"] = "excluded by user request"
        elif "reference" in role:
            row["status"] = "muted/reference only"
        elif role in {"male_vocal_source", "drums", "bass_808", "melody_keyboard", "melody_synth", "fx"}:
            row["status"] = "used with cleanup"
        else:
            row["status"] = "support/low-level"
        stem_rows.append(row)
    write_csv(REPORTS / "stem_metrics.csv", stem_rows)

    metrics = [
        audio_metrics(rendered["premaster"], "premaster"),
        audio_metrics(rendered["final_wav"], "final_wav"),
        audio_metrics(rendered["final_mp3"], "final_mp3"),
        audio_metrics(processed_paths["processed_male_vocal_stem.wav"], "processed_male_vocal_stem"),
    ]
    write_csv(REPORTS / "final_render_metrics.csv", metrics)
    (REPORTS / "processing_decisions.json").write_text(json.dumps(decisions, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    duration = len(next(iter(audio.values()))) / sr
    (REPORTS / "reaper_mix_decision_log.md").write_text(
        "\n".join(
            [
                "# REAPER Mix Decision Log",
                "",
                f"- Slug: `{SLUG}`.",
                "- Direction: female/backing vocal completely removed from the active mix.",
                "- Male vocal: spectral denoise, beep/click suppression, sip-breath suppression, stronger dynamic EQ, and a stronger parallel hard-tune density layer.",
                "- Tune note: no Antares or paid pitch plugin used; the tune feel is a DSP hard-tune edge layer, not manual note-by-note correction.",
                "- Melody: keyboard/synth/melody overlay kept forward so the sad hook does not get buried.",
                "- Kick/808: existing drums and bass are reinforced with round kick support and mono sub reinforcement.",
                "- Master: conservative loudnorm target around -11.3 LUFS, true peak target -1.25 dBTP.",
                "- Rejected: no female layer, no vocal chops, no random adlibs, no new instrumental glue bed.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    summary = [
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
    (REPORTS / "final_qc_report.md").write_text(
        "\n".join(
            [
                "# Final QC Report",
                "",
                markdown_table(summary, ["version", "duration_s", "integrated_lufs", "true_peak_dbfs", "peak_dbfs", "rms_dbfs", "stereo_corr"]),
                "",
                "## Notes",
                "",
                "- 여자 보컬/백킹 보컬은 최종 믹스에서 완전히 제외했다.",
                "- 남자 보컬은 이전보다 튠 느낌을 강하게 만들고, 레조넌스/스읍/초반 삑 계열 고역을 더 눌렀다.",
                "- 멜로디는 별도 오버레이로 앞으로 올렸다.",
                "- 전체 음압은 -11 LUFS대 스트리밍용으로 정리했고, MP3까지 확인했다.",
                "- 남는 한계: 실제 ReaTune/Melodyne식 노트별 수동 보정은 아니며, 로컬 DSP 튠 감/밀도 보강이다.",
                "",
                "## Deliverables",
                "",
            ]
            + [f"- `{path}`" for path in [rendered["final_wav"], rendered["final_mp3"], rendered["premaster"]]]
            + [f"- `{path}`" for path in sorted(processed_paths.values(), key=lambda p: p.name)]
            + [f"- `{RPP}`", ""]
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
            "status": row["status"],
        }
        for row in stem_rows
    ]
    (REPORTS / "stem_quality_report.md").write_text(
        "\n".join(
            [
                "# Stem Quality Report",
                "",
                markdown_table(stem_summary, ["stem", "role", "peak_dbfs", "rms_dbfs", "stereo_corr", "status"]),
                "",
            ]
        ),
        encoding="utf-8",
    )
    (REPORTS / "suno_0101_initial_analysis.md").write_text(
        "\n".join(
            [
                "# Suno 0101 Initial Analysis",
                "",
                f"- BPM: {BPM}.",
                f"- Length: {duration:.3f}s.",
                "- Arrangement estimate: intro 0:00-0:14, verse 0:14-0:43, hook/lift 0:43-1:12, second vocal/lift 1:12-1:41, outro/final lift after 1:41.",
                "- Current revision: male-only strong tune mix after user rejected the female layer.",
                "",
            ]
        ),
        encoding="utf-8",
    )


def create_delivery_zip(rendered: dict[str, Path], processed_paths: dict[str, Path]) -> Path:
    zip_path = RENDERS / f"{SLUG}_DELIVERABLES.zip"
    include = [
        rendered["final_wav"],
        rendered["final_mp3"],
        rendered["premaster"],
        *processed_paths.values(),
        RPP,
        REPORTS / "reaper_mix_decision_log.md",
        REPORTS / "final_qc_report.md",
        REPORTS / "final_render_metrics.csv",
        REPORTS / "stem_quality_report.md",
    ]
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        seen: set[Path] = set()
        for path in include:
            if path.exists() and path not in seen:
                zf.write(path, arcname=path.name)
                seen.add(path)
    return zip_path


def main() -> None:
    ensure_dirs()
    copied = copy_sources()
    sr, audio, dtypes = load_sources(copied)
    write_raw_derived_stems(sr, audio)
    male, male_moves = process_male_vocal(audio["0101_vocal_raw.wav"], sr)
    processed_instruments, instrument_moves = process_instrumental(audio, sr, male)
    processed = {**processed_instruments, "male": male}
    processed_paths = write_processed_stems(sr, processed)
    rendered = render_mix(sr, processed)
    mix_moves = rendered.pop("mix_moves")  # type: ignore[assignment]
    decisions = {
        "female_removed": True,
        "male_vocal": male_moves,
        "instrumental": instrument_moves,
        "mix_master": mix_moves,
        "target": {"lufs": -11.3, "true_peak_dbfs": -1.25},
    }
    write_reaper_project(sr, audio, rendered, processed_paths)
    write_reports(sr, audio, dtypes, decisions, rendered, processed_paths)
    zip_path = create_delivery_zip(rendered, processed_paths)
    print(
        json.dumps(
            {
                "slug": SLUG,
                "duration_s": round(len(next(iter(audio.values()))) / sr, 3),
                "final_wav": str(rendered["final_wav"]),
                "final_mp3": str(rendered["final_mp3"]),
                "premaster": str(rendered["premaster"]),
                "reports": str(REPORTS),
                "reaper_project": str(RPP),
                "delivery_zip": str(zip_path),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()

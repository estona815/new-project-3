from __future__ import annotations

import json
import shutil
import sys
import zipfile
from pathlib import Path

import numpy as np
from scipy import signal

ROOT = Path("/Users/hantaeheuk/Documents/New project 3")
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.mgmg_v03_human_vocal_dynamic_fx import (
    FFMPEG,
    amp_db,
    audio_metrics,
    bandpass,
    biquad_peaking,
    biquad_shelf,
    butter_filter,
    compressor,
    convert_mp3,
    convert_wav_24,
    delay_samples,
    delay_throw,
    detect_phrase_endings,
    dynamic_band_tame,
    limiter,
    make_throw_gate,
    ms_width,
    normalize_to_rms,
    pan_stereo,
    process_instrument,
    process_vocal,
    read_wav,
    reverb_send,
    sidechain_duck_full,
    soft_clip,
    write_float_wav,
)
from tools.mgmg_v04_male_main_female_adlibs import fade_window, pad_or_trim, write_csv
from tools.mgmg_v05_original_voice_match import select_phrase_events
from tools.mgmg_v07_mseq_male_center_human_tone import from_mid_side, mid_side, mono_center
from tools.mgmg_v11_female_70_mseq_layers import (
    bass_stable_grit,
    dilated_activity_mask,
    drums_stable_punch,
    female_70_mseq_layers,
    mseq_female_separation,
    stable_master_tone,
    static_music_space,
)


WORK = ROOT / "suno_studio_extract" / "v11_precision_mix"
RAW_STEMS = ROOT / "suno_studio_extract" / "raw_stems"
INTERMEDIATE = WORK / "intermediate"
REPORTS = WORK / "reports"
OUTPUT = WORK / "renders"
STEM_OUTPUT = WORK / "processed_stems_v23_vocal_clarity_rebalance"
EXTERNAL_FEMALE_STEMS = ROOT / "suno_studio_extract" / "external_female_v20_stems"

OUT_WAV = OUTPUT / "hangang_shadow_mashup_v11_precision_MASTER_24-48.wav"
OUT_MP3 = OUTPUT / "hangang_shadow_mashup_v11_precision_MASTER_320k.mp3"
OUT_REPAIR_WAV = OUTPUT / "hangang_shadow_mashup_v23_vocal_clarity_rebalance_MASTER_24-48.wav"
OUT_REPAIR_MP3 = OUTPUT / "hangang_shadow_mashup_v23_vocal_clarity_rebalance_MASTER_320k.mp3"
STEM_ZIP = OUTPUT / "hangang_shadow_mashup_v23_vocal_clarity_rebalance_processed_stems.zip"
PREMASTER = INTERMEDIATE / "hangang_shadow_mashup_v11_precision_premaster_float.wav"
REPAIR_PREMASTER = INTERMEDIATE / "hangang_shadow_mashup_v23_vocal_clarity_rebalance_premaster_float.wav"
REPORT_MD = REPORTS / "audio_audit_suno_v11_precision.md"
REPAIR_REPORT_MD = REPORTS / "audio_audit_suno_v23_vocal_clarity_rebalance.md"
SETTINGS_JSON = REPORTS / "processing_settings_suno_v11_precision.json"
REPAIR_SETTINGS_JSON = REPORTS / "processing_settings_suno_v23_vocal_clarity_rebalance.json"
AUDIT_CSV = REPORTS / "render_audit_suno_v11_precision.csv"
REPAIR_AUDIT_CSV = REPORTS / "render_audit_suno_v23_vocal_clarity_rebalance.csv"


STEM_PATHS = {
    "reference": "00_REF_Full_Mix.wav",
    "woodwinds": "01_Woodwinds.wav",
    "brass": "02_Brass.wav",
    "fx": "03_FX.wav",
    "synth": "04_Synth.wav",
    "strings": "05_Strings.wav",
    "percussion": "06_Percussion.wav",
    "keys": "07_Keyboard.wav",
    "guitar": "08_Guitar.wav",
    "bass": "09_Bass.wav",
    "drums": "10_Drums.wav",
    "female_backing": "11_Backing_Vocals.wav",
    "lead_vocal": "12_Vocals.wav",
}


def db_rms(y: np.ndarray) -> float:
    return float(20.0 * np.log10(max(float(np.sqrt(np.mean(y * y))), 1e-12)))


def load_stem(role: str) -> tuple[int, np.ndarray, str]:
    return read_wav(RAW_STEMS / STEM_PATHS[role])


def active_stem(y: np.ndarray, rms_floor: float = -74.0, peak_floor: float = -42.0) -> bool:
    peak = float(np.max(np.abs(y))) if len(y) else 0.0
    peak_db = float(20.0 * np.log10(max(peak, 1e-12)))
    return db_rms(y) >= rms_floor or peak_db >= peak_floor


def pad_all(stems: dict[str, np.ndarray], length: int) -> dict[str, np.ndarray]:
    return {key: pad_or_trim(value, length) for key, value in stems.items()}


def main_center_clear_vocal(y: np.ndarray, sr: int) -> tuple[np.ndarray, list[dict[str, object]]]:
    base, moves = process_vocal("lead_vocal", y, sr)
    base = mono_center(base)
    clarity = butter_filter(base, sr, "highpass", 118, 3)
    clarity = butter_filter(clarity, sr, "lowpass", 14500, 3)
    clarity = biquad_peaking(clarity, sr, 2250, 0.95, 0.95)
    clarity = biquad_peaking(clarity, sr, 3350, 1.18, 1.0)
    clarity = biquad_peaking(clarity, sr, 4650, 0.72, 1.05)
    clarity = biquad_peaking(clarity, sr, 6100, 0.30, 1.0)
    clarity, sibilance = dynamic_band_tame(clarity, sr, 6200, 10200, 1.65, 74, 58, slope=0.45)
    body = butter_filter(base, sr, "lowpass", 420, 3)
    out = base * float(amp_db(1.0)) + clarity * float(amp_db(-4.55)) + body * float(amp_db(-20.5))
    out, metal = dynamic_band_tame(out, sr, 2800, 6900, 0.82, 84, 105, slope=0.26)
    out, air = dynamic_band_tame(out, sr, 7600, 12400, 0.95, 82, 70, slope=0.34)
    out = biquad_peaking(out, sr, 230, -0.22, 0.8)
    out = biquad_peaking(out, sr, 980, -0.16, 0.85)
    out = biquad_peaking(out, sr, 2650, 0.82, 0.95)
    out = biquad_peaking(out, sr, 3550, 0.78, 1.0)
    out = biquad_peaking(out, sr, 4850, 0.46, 1.05)
    out = biquad_shelf(out, sr, 11200, 0.34, True)
    out = compressor(out, sr, threshold_db=-20.5, ratio=1.42, smooth_ms=105, makeup_db=0.42)
    moves.extend(
        [
            {"stage": "suno_v11_center_lock", "pan": "mono center"},
            {"stage": "suno_v23_clarity_layer", "return_db": -4.55, "note": "more forward consonants and upper presence without hard clipping"},
            {"stage": "suno_v11_sibilance_tame", **sibilance},
            {"stage": "suno_v11_metallic_presence_tame", **metal},
            {"stage": "suno_v11_upper_air_tame", **air},
        ]
    )
    return mono_center(out.astype(np.float32)) * float(amp_db(-3.15)), moves


def backing_source_v11(y: np.ndarray, sr: int) -> tuple[np.ndarray, list[dict[str, object]]]:
    out, moves = process_vocal("backing_vocal", y, sr)
    out = butter_filter(out, sr, "highpass", 150, 3)
    out, stats = dynamic_band_tame(out, sr, 2500, 6200, 2.1, 72, 84, slope=0.58)
    out, deess = dynamic_band_tame(out, sr, 5600, 9600, 3.0, 68, 55, slope=0.62)
    out = biquad_shelf(out, sr, 9400, -0.35, True)
    out = compressor(out, sr, threshold_db=-25.0, ratio=1.45, smooth_ms=135, makeup_db=0.2)
    moves.extend(
        [
            {"stage": "suno_v11_female_candidate_cleanup", **stats},
            {"stage": "suno_v11_female_candidate_deess", **deess},
        ]
    )
    return out.astype(np.float32), moves


def pitch_shift_preserve_timing(y: np.ndarray, sr: int, semitones: float, label: str) -> np.ndarray:
    src = INTERMEDIATE / f"_{label}_source.wav"
    dst = INTERMEDIATE / f"_{label}_pitch_{semitones:+.1f}.wav"
    write_float_wav(src, sr, y)
    factor = 2.0 ** (semitones / 12.0)
    tempo = 1.0 / factor
    filt = f"asetrate={sr * factor:.8f},aresample={sr},atempo={tempo:.8f}"
    subprocess_args = [FFMPEG, "-y", "-hide_banner", "-loglevel", "error", "-i", str(src), "-af", filt, "-c:a", "pcm_f32le", "-ar", str(sr), str(dst)]
    import subprocess

    subprocess.run(subprocess_args, check=True)
    shifted_sr, shifted, _ = read_wav(dst)
    if shifted_sr != sr:
        raise RuntimeError(f"pitch shift sample-rate mismatch: {shifted_sr} != {sr}")
    return pad_or_trim(shifted, len(y))


def female_tone_source_repair(lead: np.ndarray, backing: np.ndarray, sr: int) -> tuple[np.ndarray, list[dict[str, object]]]:
    backing_body = normalize_to_rms(backing, -30.0)
    lead_shadow = normalize_to_rms(lead, -38.0)
    source = backing_body + lead_shadow * float(amp_db(-18.0))
    shifted = butter_filter(source, sr, "highpass", 210, 3)
    shifted = butter_filter(shifted, sr, "lowpass", 10800, 3)
    shifted, low_formant = dynamic_band_tame(shifted, sr, 420, 980, 2.2, 68, 135, slope=0.55)
    shifted, nasal = dynamic_band_tame(shifted, sr, 820, 1650, 1.45, 73, 120, slope=0.40)
    shifted, bite = dynamic_band_tame(shifted, sr, 5200, 9600, 2.8, 68, 60, slope=0.58)
    shifted = biquad_peaking(shifted, sr, 2450, 0.15, 0.9)
    shifted = biquad_peaking(shifted, sr, 4200, -0.25, 1.0)
    shifted = biquad_shelf(shifted, sr, 10300, -0.35, True)
    shifted = compressor(shifted, sr, threshold_db=-28.0, ratio=1.35, smooth_ms=155, makeup_db=-0.2)
    shifted = normalize_to_rms(shifted, -31.0)
    write_float_wav(INTERMEDIATE / "female_tone_repair_source_float.wav", sr, shifted)
    moves = [
        {"stage": "female_tone_repair_no_pitch_shift", "semitones": 0.0, "source_blend": "quiet backing only + nearly inaudible lead shadow"},
        {"stage": "female_tone_low_formant_cut", **low_formant},
        {"stage": "female_tone_nasal_control", **nasal},
        {"stage": "female_tone_deess", **bite},
        {"stage": "female_tone_tucked_support", "peaks_db": {"2450": 0.15, "4200": -0.25}, "air_shelf_db": -0.35, "target_rms_dbfs": -31.0},
    ]
    return shifted.astype(np.float32), moves


def female_adlib_double_repair(female_source: np.ndarray, phrase_events: list[dict[str, float]], sr: int, length: int) -> tuple[np.ndarray, list[dict[str, object]], float]:
    src = pad_or_trim(female_source, length)
    mono = np.mean(src, axis=1)
    from tools.mgmg_v03_human_vocal_dynamic_fx import smooth_envelope

    env = smooth_envelope(mono, sr, 80)
    active_vals = env[env > 1e-8]
    if len(active_vals):
        threshold = float(np.percentile(active_vals, 72))
        active = env > threshold
    else:
        active = np.ones(len(src), dtype=bool)
    dilated = np.convolve(active.astype(np.float32), np.ones(max(int(sr * 0.16), 1), dtype=np.float32), mode="same") > 0
    mask = dilated.astype(np.float32)
    fade = max(int(sr * 0.045), 1)
    kernel = np.hanning(fade * 2 + 1).astype(np.float32)
    kernel /= float(np.sum(kernel))
    mask = np.clip(np.convolve(mask, kernel, mode="same"), 0.0, 1.0)
    coverage = float(np.mean(mask > 0.08))

    bed_l = pan_stereo(delay_samples(src, int(sr * 0.010)), -0.68)
    bed_r = pan_stereo(delay_samples(src, int(sr * 0.024)), 0.68)
    whisper = butter_filter(src, sr, "highpass", 310, 2)
    whisper = butter_filter(whisper, sr, "lowpass", 7600, 2)
    bed = (bed_l + bed_r) * float(amp_db(-14.0)) + whisper * float(amp_db(-23.0))
    bed *= mask[:, None]

    adlibs = np.zeros((length, 2), dtype=np.float32)
    events: list[dict[str, object]] = []
    selected = phrase_events[:]
    for idx, event in enumerate(selected):
        center = int(float(event["time_s"]) * sr)
        start = max(center - int(0.62 * sr), 0)
        end = min(center + int(0.44 * sr), length)
        if end - start <= int(0.13 * sr):
            continue
        seg = src[start:end].copy()
        seg *= fade_window(len(seg), int(0.035 * sr))[:, None]
        pan = -0.72 if idx % 2 == 0 else 0.72
        adlibs[start:end] += pan_stereo(seg, pan) * float(amp_db(-11.5))
        adlibs[start:end] += pan_stereo(delay_samples(seg, int(sr * 0.016)), -pan) * float(amp_db(-17.5))
        events.append({"time_s": round(start / sr, 3), "type": "tucked female tail/double", "pan": pan, "gain_db": -11.5})

        chop_len = int((0.095 + 0.015 * (idx % 3)) * sr)
        chop_start = max(center - int(0.18 * sr), 0)
        if chop_start + chop_len < length:
            chop = src[chop_start : chop_start + chop_len].copy()
            chop = butter_filter(chop, sr, "highpass", 300, 2)
            chop = butter_filter(chop, sr, "lowpass", 7200, 2)
            chop *= fade_window(len(chop), int(0.01 * sr))[:, None]
            place = min(center + int(0.10 * sr), length - chop_len)
            chop_pan = 0.78 if idx % 2 == 0 else -0.78
            adlibs[place : place + chop_len] += pan_stereo(chop, chop_pan) * float(amp_db(-15.0))
            events.append({"time_s": round(place / sr, 3), "type": "tucked female side tail", "pan": chop_pan, "gain_db": -15.0})
    out = mseq_female_separation(ms_width(bed + adlibs, 1.45), sr)
    out = normalize_to_rms(out, -34.0)
    write_float_wav(INTERMEDIATE / "female_adlib_double_repair_layer_float.wav", sr, out)
    return out.astype(np.float32), events, coverage


def external_female_source_v20(source: np.ndarray, sr: int) -> tuple[np.ndarray, list[dict[str, object]]]:
    out, moves = process_vocal("backing_vocal", source, sr)
    out = butter_filter(out, sr, "highpass", 185, 3)
    out = butter_filter(out, sr, "lowpass", 10200, 3)
    out, body = dynamic_band_tame(out, sr, 210, 540, 3.2, 64, 150, slope=0.62)
    out, nasal = dynamic_band_tame(out, sr, 760, 1550, 1.65, 70, 120, slope=0.42)
    out, bite = dynamic_band_tame(out, sr, 2450, 6200, 1.55, 76, 95, slope=0.36)
    out, deess = dynamic_band_tame(out, sr, 5600, 9800, 2.8, 70, 65, slope=0.58)
    out = biquad_peaking(out, sr, 1850, 0.25, 0.95)
    out = biquad_peaking(out, sr, 3600, -0.2, 1.05)
    out = biquad_shelf(out, sr, 9800, -0.4, True)
    out = compressor(out, sr, threshold_db=-27.5, ratio=1.28, smooth_ms=160, makeup_db=-0.15)
    out = normalize_to_rms(out, -31.4)
    write_float_wav(INTERMEDIATE / "external_female_v20_source_float.wav", sr, out)
    moves.extend(
        [
            {"stage": "external_female_v20_body_cleanup", **body},
            {"stage": "external_female_v20_nasal_control", **nasal},
            {"stage": "external_female_v20_bite_guard", **bite},
            {"stage": "external_female_v20_deess", **deess},
            {"stage": "external_female_v20_target_rms", "target_rms_dbfs": -31.4},
        ]
    )
    return out.astype(np.float32), moves


def female_55_residual_layers(female_source: np.ndarray, phrase_events: list[dict[str, float]], sr: int, length: int) -> tuple[np.ndarray, list[dict[str, object]], float]:
    src = pad_or_trim(female_source, length)
    if phrase_events:
        mask = np.zeros(length, dtype=np.float32)
        for pad_s in np.linspace(1.15, 3.80, 22):
            candidate = np.zeros(length, dtype=np.float32)
            for idx, event in enumerate(phrase_events):
                center = int(float(event["time_s"]) * sr)
                pre = int((0.50 + 0.08 * (idx % 3)) * sr)
                post = int(pad_s * sr)
                start = max(center - pre, 0)
                end = min(center + post, length)
                candidate[start:end] = 1.0
            coverage_now = float(np.mean(candidate > 0.08))
            mask = candidate
            if coverage_now >= 0.56:
                break
        fade = max(int(sr * 0.055), 1)
        kernel = np.hanning(fade * 2 + 1).astype(np.float32)
        kernel /= float(np.sum(kernel))
        mask = np.clip(np.convolve(mask, kernel, mode="same"), 0.0, 1.0)
        coverage = float(np.mean(mask > 0.08))
    else:
        mask, coverage = dilated_activity_mask(src, sr, target_coverage=0.55)

    bed_left = pan_stereo(delay_samples(src, int(sr * 0.006)), -0.42)
    bed_right = pan_stereo(delay_samples(src, int(sr * 0.018)), 0.42)
    center_shadow = mono_center(src) * float(amp_db(-15.8))
    bed = (bed_left + bed_right) * float(amp_db(-9.8)) + center_shadow
    bed *= mask[:, None]
    bed = ms_width(bed, 1.24)

    adlibs = np.zeros((length, 2), dtype=np.float32)
    events: list[dict[str, object]] = []
    selected = phrase_events[:]
    for idx, event in enumerate(selected):
        center = int(float(event["time_s"]) * sr)
        start = max(center - int(0.46 * sr), 0)
        end = min(center + int(0.50 * sr), length)
        if end - start <= int(0.13 * sr):
            continue
        seg = src[start:end].copy()
        seg *= fade_window(len(seg), int(0.035 * sr))[:, None]
        pan = -0.46 if idx % 2 == 0 else 0.46
        adlibs[start:end] += pan_stereo(seg, pan) * float(amp_db(-8.6))
        adlibs[start:end] += pan_stereo(delay_samples(seg, int(sr * 0.012)), -pan) * float(amp_db(-13.8))
        events.append({"time_s": round(start / sr, 3), "type": "female 55 blended phrase double", "pan": pan, "gain_db": -8.6})

        if idx % 2 == 0:
            chop_len = int((0.085 + 0.012 * (idx % 3)) * sr)
            chop_start = max(center - int(0.16 * sr), 0)
            if chop_start + chop_len < length:
                chop = src[chop_start : chop_start + chop_len].copy()
                chop = butter_filter(chop, sr, "highpass", 330, 2)
                chop = butter_filter(chop, sr, "lowpass", 6800, 2)
                chop *= fade_window(len(chop), int(0.012 * sr))[:, None]
                place = min(center + int(0.11 * sr), length - chop_len)
                chop_pan = 0.66 if idx % 4 == 0 else -0.66
                adlibs[place : place + chop_len] += pan_stereo(chop, chop_pan) * float(amp_db(-14.2))
            events.append({"time_s": round(place / sr, 3), "type": "female 55 blended side adlib", "pan": chop_pan, "gain_db": -14.2})

    adlibs = biquad_shelf(adlibs, sr, 9300, -0.5, True)
    adlibs = ms_width(adlibs, 1.46)
    out = mseq_female_separation(bed + adlibs, sr)
    out = normalize_to_rms(out, -33.2)
    write_float_wav(INTERMEDIATE / "female_55_residual_layer_float.wav", sr, out)
    return out.astype(np.float32), events, coverage


def stem_space(role: str, y: np.ndarray, sr: int, vocal: np.ndarray | None = None) -> tuple[np.ndarray, list[dict[str, object]]]:
    mapped = "other" if role in {"fx", "guitar", "woodwinds", "brass", "strings", "percussion"} else role
    if mapped == "keys":
        mapped = "keys"
    out, moves = process_instrument(mapped, y, sr, drums=None, vocal=vocal)
    if role == "fx":
        out = butter_filter(out, sr, "highpass", 70, 3)
        out, stats = dynamic_band_tame(out, sr, 1600, 6200, 1.7, 78, 100, slope=0.45)
        out = biquad_shelf(out, sr, 9800, -0.55, True)
        out = biquad_peaking(out, sr, 3600, 0.55, 1.0)
        moves.append({"stage": "suno_v11_fx_soften", **stats})
    elif role == "synth":
        out, stats = dynamic_band_tame(out, sr, 2100, 5200, 0.95, 82, 135, slope=0.34)
        out = biquad_peaking(out, sr, 920, -0.45, 0.85)
        out = biquad_peaking(out, sr, 1850, 0.25, 0.95)
        out = biquad_peaking(out, sr, 3600, 1.1, 1.0)
        out = biquad_shelf(out, sr, 10500, 0.42, True)
        moves.append({"stage": "suno_v11_synth_presence_control", **stats})
    elif role == "guitar":
        out = biquad_peaking(out, sr, 2800, 0.75, 0.95)
        out = biquad_shelf(out, sr, 9500, 0.2, True)
        moves.append({"stage": "suno_v13_guitar_edge"})
    return out.astype(np.float32), moves


def render_static_master_local(src: Path, dst: Path) -> dict[str, object]:
    sr, y, _ = read_wav(src)
    gain_db = 14.15
    drive_db = 0.14
    clip_ceiling = 0.82
    oversample = 4
    upsampled = signal.resample_poly(y * float(amp_db(gain_db)), oversample, 1, axis=0).astype(np.float32)
    upsampled = soft_clip(upsampled, drive_db=drive_db, ceiling=clip_ceiling)
    upsampled = limiter(upsampled, float(20.0 * np.log10(clip_ceiling)))
    final = signal.resample_poly(upsampled, 1, oversample, axis=0).astype(np.float32)[: len(y)]
    final = limiter(final, -1.85)
    final_float = INTERMEDIATE / "_suno_v11_precision_static_master_float.wav"
    write_float_wav(final_float, sr, final)
    convert_wav_24(final_float, dst)
    return {
        "static_gain_db": gain_db,
        "clip_drive_db": drive_db,
        "clip_ceiling": clip_ceiling,
        "oversample": oversample,
        "final_limiter_db": -1.85,
    }


def export_processed_stem(label: str, y: np.ndarray, sr: int) -> Path:
    STEM_OUTPUT.mkdir(parents=True, exist_ok=True)
    float_path = INTERMEDIATE / f"_{label}_float.wav"
    out_path = STEM_OUTPUT / f"{label}.wav"
    write_float_wav(float_path, sr, limiter(y.astype(np.float32), -2.8))
    convert_wav_24(float_path, out_path)
    return out_path


def zip_processed_stems(paths: list[Path]) -> Path:
    STEM_ZIP.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(STEM_ZIP, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=4) as archive:
        for path in paths:
            archive.write(path, arcname=path.name)
    return STEM_ZIP


def v11_width_recovery(y: np.ndarray, sr: int) -> np.ndarray:
    mid, side = mid_side(y)
    mid_st = np.column_stack([mid, mid]).astype(np.float32)
    side_st = np.column_stack([side, side]).astype(np.float32)
    low = butter_filter(mid_st, sr, "lowpass", 120, 4)
    low_mono = np.mean(low, axis=1)
    mid_hi = np.mean(mid_st - low, axis=1)
    side_hi = butter_filter(side_st, sr, "highpass", 135, 3)
    side_hi = biquad_peaking(side_hi, sr, 2300, 0.55, 0.9)
    side_hi = biquad_peaking(side_hi, sr, 4300, 0.45, 1.0)
    side_hi = biquad_shelf(side_hi, sr, 9800, -0.18, True)
    side_new = np.mean(side_hi, axis=1) * float(amp_db(4.7))
    widened = from_mid_side(low_mono + mid_hi, side_new)
    return limiter(widened.astype(np.float32), -2.4)


def commercial_ms_instrument_bus(music: np.ndarray, vocal: np.ndarray, sr: int) -> np.ndarray:
    from tools.mgmg_v03_human_vocal_dynamic_fx import smooth_envelope

    mid, side = mid_side(music)
    mid_st = np.column_stack([mid, mid]).astype(np.float32)
    side_st = np.column_stack([side, side]).astype(np.float32)
    low = butter_filter(mid_st, sr, "lowpass", 122, 4)
    low_mono = np.mean(low, axis=1)
    mid_hi = mid_st - low

    pocket = bandpass(mid_hi, sr, 1280, 5400, 3)
    rest = mid_hi - pocket
    env = smooth_envelope(np.mean(vocal, axis=1), sr, 90)
    active = env[env > 1e-8]
    threshold = float(np.percentile(active, 52)) if len(active) else 0.01
    top = float(np.percentile(env, 97))
    norm = np.clip((env - threshold) / (top - threshold + 1e-9), 0.0, 1.0)
    pocket_gain = amp_db(-2.65 * norm).astype(np.float32)
    mid_new = np.mean(rest + pocket * pocket_gain[:, None], axis=1) * float(amp_db(-0.68)) + low_mono * float(amp_db(0.62))

    side_st = butter_filter(side_st, sr, "highpass", 135, 3)
    side_st, _ = dynamic_band_tame(side_st, sr, 240, 780, 1.05, 79, 160, slope=0.36)
    side_st = biquad_peaking(side_st, sr, 2400, 0.52, 0.9)
    side_st = biquad_peaking(side_st, sr, 5200, 0.62, 1.0)
    side_st = biquad_shelf(side_st, sr, 11200, 0.22, True)
    side_new = np.mean(side_st, axis=1) * float(amp_db(4.25))

    out = from_mid_side(mid_new, side_new)
    out, _ = dynamic_band_tame(out, sr, 160, 560, 1.6, 76, 190, slope=0.42)
    out, _ = dynamic_band_tame(out, sr, 6100, 9900, 0.9, 84, 80, slope=0.28)
    out = biquad_peaking(out, sr, 3150, -0.28, 0.95)
    out = compressor(out, sr, threshold_db=-16.5, ratio=1.08, smooth_ms=205, makeup_db=0.16)
    return limiter(out.astype(np.float32), -2.8)


def safe_synth_stereo_support(synth: np.ndarray, sr: int) -> np.ndarray:
    side_source = butter_filter(synth, sr, "highpass", 340, 3)
    side_source = butter_filter(side_source, sr, "lowpass", 11800, 3)
    side_source, _ = dynamic_band_tame(side_source, sr, 2500, 6200, 0.8, 82, 120, slope=0.30)
    side_source = biquad_shelf(side_source, sr, 9800, 0.35, True)
    left = pan_stereo(delay_samples(side_source, int(sr * 0.013)), -0.58)
    right = pan_stereo(delay_samples(side_source, int(sr * 0.027)), 0.58)
    return limiter((left + right).astype(np.float32), -4.0)


def melody_focus_layer(synth: np.ndarray, sr: int) -> np.ndarray:
    focus = butter_filter(synth, sr, "highpass", 620, 3)
    focus = butter_filter(focus, sr, "lowpass", 7400, 3)
    focus = biquad_peaking(focus, sr, 1500, 0.55, 0.95)
    focus = biquad_peaking(focus, sr, 2650, 1.15, 0.95)
    focus = biquad_peaking(focus, sr, 3650, 0.95, 1.05)
    focus = biquad_peaking(focus, sr, 5200, -0.18, 1.0)
    focus, _ = dynamic_band_tame(focus, sr, 4550, 7900, 1.25, 81, 95, slope=0.34)
    focus = compressor(focus, sr, threshold_db=-25.5, ratio=1.18, smooth_ms=130, makeup_db=0.16)
    focus = ms_width(focus, 1.28)
    return limiter(focus.astype(np.float32), -4.4)


def nova_style_master_balance(y: np.ndarray, sr: int) -> tuple[np.ndarray, list[dict[str, object]]]:
    out = y.astype(np.float32)
    moves: list[dict[str, object]] = []
    out, sub_bloom = dynamic_band_tame(out, sr, 32, 84, 1.25, 82, 230, slope=0.34)
    out, bass_body = dynamic_band_tame(out, sr, 88, 220, 2.35, 72, 220, slope=0.44)
    out, mud = dynamic_band_tame(out, sr, 210, 520, 2.05, 73, 185, slope=0.44)
    out, low_formant = dynamic_band_tame(out, sr, 560, 1250, 0.95, 82, 150, slope=0.24)
    out = biquad_peaking(out, sr, 1800, 0.52, 1.0)
    out = biquad_peaking(out, sr, 2850, 0.88, 0.95)
    out = biquad_peaking(out, sr, 3850, 0.68, 1.0)
    out = biquad_peaking(out, sr, 5200, 0.25, 1.05)
    out = biquad_shelf(out, sr, 10800, 0.22, True)
    out, edge = dynamic_band_tame(out, sr, 6100, 9400, 0.72, 86, 95, slope=0.22)
    out = compressor(out, sr, threshold_db=-16.2, ratio=1.035, smooth_ms=250, makeup_db=0.0)
    moves.extend(
        [
            {"stage": "nova_style_sub_bloom_control", **sub_bloom},
            {"stage": "nova_style_bass_body_control", **bass_body},
            {"stage": "nova_style_low_mid_mud_control", **mud},
            {"stage": "nova_style_vocal_melody_space", **low_formant},
            {"stage": "nova_style_upper_edge_guard", **edge},
            {"stage": "vocal_presence_static_lift", "peaks_db": {"1800": 0.52, "2850": 0.88, "3850": 0.68, "5200": 0.25}, "air_shelf_db": 0.22},
        ]
    )
    return limiter(out.astype(np.float32), -2.5), moves


def write_report(rows: list[dict[str, object]], settings: dict[str, object], path: Path = REPORT_MD, title: str = "Suno Studio v11 Precision Mix") -> None:
    lines = [
        f"# {title}",
        "",
        "- Rebuilt from raw Suno multitrack WAV stems, not from the earlier quick cleaned MP3.",
        "- v23 stance: full EQ/master rebalance for clearer main vocal, wider vocal pocket, tighter low end, and less final-stage smearing.",
        "- Near-silent Suno stems were skipped instead of being boosted into noise.",
        "- MIDI remains guide-only because the Suno export did not include native MIDI.",
        "",
        "| label | LUFS | TP | LRA | corr | side_mid |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['label']} | {row.get('integrated_lufs')} | {row.get('true_peak_dbfs')} | "
            f"{row.get('lra_lu')} | {row.get('stereo_corr')} | {row.get('side_mid_db')} |"
        )
    lines.extend(
        [
            "",
            f"- Phrase events detected: {settings['phrase_event_count']}",
            f"- Female layer coverage: {settings['female_layer_coverage']}",
            f"- Active music stems used: {', '.join(settings['active_music_stems'])}",
            f"- Excluded from main music bus: {', '.join(settings.get('excluded_from_music_bus', [])) or 'none'}",
            f"- Processed stem ZIP: {settings['processed_stem_zip']}",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    for d in [WORK, INTERMEDIATE, REPORTS, OUTPUT, STEM_OUTPUT]:
        d.mkdir(parents=True, exist_ok=True)

    loaded: dict[str, np.ndarray] = {}
    sr_seen: int | None = None
    stem_dtypes: dict[str, str] = {}
    for role in STEM_PATHS:
        sr, y, dtype_name = load_stem(role)
        if sr_seen is None:
            sr_seen = sr
        if sr != sr_seen:
            raise RuntimeError(f"Sample rate mismatch for {role}: {sr} != {sr_seen}")
        loaded[role] = y
        stem_dtypes[role] = dtype_name
    assert sr_seen is not None
    sr = sr_seen
    length = max(len(y) for y in loaded.values())
    loaded = pad_all(loaded, length)

    lead, lead_moves = main_center_clear_vocal(loaded["lead_vocal"], sr)
    backing_src, backing_moves = backing_source_v11(loaded["female_backing"], sr)
    phrase_events = select_phrase_events(detect_phrase_endings(lead, sr))
    external_female_path = EXTERNAL_FEMALE_STEMS / "0 Lead Vocals.wav"
    if external_female_path.exists():
        external_sr, external_female_raw, _ = read_wav(external_female_path)
        if external_sr != sr:
            raise RuntimeError(f"External female sample-rate mismatch: {external_sr} != {sr}")
        female_tone_src, female_tone_moves = external_female_source_v20(pad_or_trim(external_female_raw, length), sr)
        female_layers, female_events, female_coverage = female_55_residual_layers(female_tone_src, phrase_events, sr, length)
        female_source_note = str(external_female_path)
    else:
        female_tone_src, female_tone_moves = female_tone_source_repair(lead, backing_src, sr)
        female_layers, female_events, female_coverage = female_adlib_double_repair(female_tone_src, phrase_events, sr, length)
        female_source_note = "fallback raw backing vocal stem"

    processed: dict[str, np.ndarray] = {}
    moves: dict[str, object] = {}
    active_music: list[str] = []
    processed["drums"], moves["drums"] = drums_stable_punch(loaded["drums"], sr)
    processed["bass"], moves["bass"] = bass_stable_grit(loaded["bass"], loaded["drums"], sr)
    active_music.extend(["drums", "bass"])

    for role in ["synth", "fx", "keys", "guitar", "percussion", "woodwinds", "brass", "strings"]:
        if not active_stem(loaded[role]):
            moves[role] = [{"stage": "skipped_near_silent_suno_stem", "rms_dbfs": round(db_rms(loaded[role]), 2)}]
            continue
        processed[role], moves[role] = stem_space(role, loaded[role], sr, vocal=lead)
        active_music.append(role)

    music_components: dict[str, np.ndarray] = {
        "01_drums_eq_gain_v23": processed["drums"] * float(amp_db(2.8)),
        "02_bass_eq_gain_v23": processed["bass"] * float(amp_db(0.85)),
    }
    if "synth" in processed:
        music_components["03_synth_eq_gain_v23"] = processed["synth"] * float(amp_db(4.65))
        music_components["03b_synth_safe_stereo_support_v23"] = safe_synth_stereo_support(processed["synth"], sr) * float(amp_db(0.35))
        music_components["03c_melody_focus_layer_v23"] = melody_focus_layer(processed["synth"], sr) * float(amp_db(1.25))
    if "keys" in processed:
        music_components["05_keys_eq_gain_v23"] = processed["keys"] * float(amp_db(0.15))
    if "percussion" in processed:
        music_components["07_percussion_eq_gain_v23"] = processed["percussion"] * float(amp_db(-2.6))
    music = np.zeros_like(lead, dtype=np.float32)
    for component in music_components.values():
        music += component.astype(np.float32)
    music = commercial_ms_instrument_bus(static_music_space(music, sr), lead, sr)

    reverb = reverb_send(lead * float(amp_db(-13.4)) + female_layers * float(amp_db(-12.5)), sr, 0.82, -32.8, 36, 360, 6800, 1124)
    reverb = sidechain_duck_full(reverb, lead, sr, 3.4, 520, 65)
    throw_gate = make_throw_gate(length, sr, phrase_events, pre_ms=170, post_ms=120, fade_ms=30)
    delay_src = female_layers * throw_gate[:, None] * float(amp_db(-11.0))
    delay_fx = delay_throw(delay_src, sr, 370.4, 0.08, -30.8, 430, 4300, True)
    delay_fx = sidechain_duck_full(delay_fx, lead, sr, 3.2, 520, 65)

    mix = music * float(amp_db(1.25)) + lead * float(amp_db(-5.35)) + female_layers * float(amp_db(-8.8)) + reverb + delay_fx
    mix = limiter(mix * float(amp_db(-6.95)), -2.8)
    balanced_mix, master_balance_moves = nova_style_master_balance(stable_master_tone(mix, sr), sr)
    premaster = v11_width_recovery(balanced_mix, sr)
    write_float_wav(REPAIR_PREMASTER, sr, premaster)

    stem_exports: list[Path] = []
    for label, component in music_components.items():
        stem_exports.append(export_processed_stem(label, component, sr))
    stem_exports.extend(
        [
            export_processed_stem("90_music_ms_eq_bus_v23_no_fx_guitar", music, sr),
            export_processed_stem("91_lead_vocal_clear_forward_center_v23", lead * float(amp_db(-5.35)), sr),
            export_processed_stem("92_female_55_tucked_double_adlib_v23", female_layers * float(amp_db(-8.8)), sr),
            export_processed_stem("93_vocal_reverb_delay_fx_v23", reverb + delay_fx, sr),
        ]
    )
    processed_stem_zip = zip_processed_stems(stem_exports)

    master_settings = render_static_master_local(REPAIR_PREMASTER, OUT_REPAIR_WAV)
    convert_mp3(OUT_REPAIR_WAV, OUT_REPAIR_MP3)
    rows = [
        audio_metrics(OUT_REPAIR_WAV, "suno_v23_vocal_clarity_rebalance_wav"),
        audio_metrics(OUT_REPAIR_MP3, "suno_v23_vocal_clarity_rebalance_mp3"),
    ]
    write_csv(REPAIR_AUDIT_CSV, rows)
    settings = {
        "direction": "v23 vocal clarity rebalance: continue from v22 using raw Suno WAV stems, rebuild EQ/master balance for a clearer main male vocal, stronger instrument pocket around 1.3-5.4 kHz, lower low-end masking, less final-stage clipping, female vocal kept tucked as 50-60 percent residual double/adlib support",
        "source_dir": str(RAW_STEMS),
        "output_wav": str(OUT_REPAIR_WAV),
        "output_mp3": str(OUT_REPAIR_MP3),
        "premaster": str(REPAIR_PREMASTER),
        "premaster_removed_after_render": True,
        "processed_stem_dir": str(STEM_OUTPUT),
        "processed_stem_zip": str(processed_stem_zip),
        "processed_stems": [str(path) for path in stem_exports],
        "external_female_source": female_source_note,
        "active_music_stems": [role for role in active_music if role not in {"fx", "guitar"}],
        "excluded_from_music_bus": ["fx", "guitar"],
        "lead_moves": lead_moves,
        "female_backing_moves": backing_moves,
        "female_tone_moves": female_tone_moves,
        "female_events": female_events,
        "female_layer_coverage": round(female_coverage, 3),
        "phrase_events": phrase_events,
        "phrase_event_count": len(phrase_events),
        "instrument_moves": moves,
        "master_balance_moves": master_balance_moves,
        "master_render": master_settings,
        "metrics": rows,
    }
    REPAIR_SETTINGS_JSON.write_text(json.dumps(settings, ensure_ascii=False, indent=2), encoding="utf-8")
    if INTERMEDIATE.exists():
        shutil.rmtree(INTERMEDIATE)
    write_report(rows, settings, REPAIR_REPORT_MD, "Suno Studio v23 Vocal Clarity Rebalance")
    print(OUT_REPAIR_WAV)
    print(OUT_REPAIR_MP3)
    print(processed_stem_zip)
    print(REPAIR_REPORT_MD)
    print(REPAIR_SETTINGS_JSON)


if __name__ == "__main__":
    main()

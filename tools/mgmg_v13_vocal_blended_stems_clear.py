from __future__ import annotations

import json
import sys
import zipfile
from pathlib import Path

import numpy as np
from scipy import signal

ROOT = Path("/Users/hantaeheuk/Documents/New project 3")
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.mgmg_v03_human_vocal_dynamic_fx import (
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
    pan_stereo,
    process_instrument,
    process_vocal,
    read_wav,
    reverb_send,
    rms,
    saturate,
    sidechain_duck_full,
    smooth_envelope,
    soft_clip,
    vocal_harmonic_density,
    write_float_wav,
)
from tools.mgmg_v04_male_main_female_adlibs import (
    FEMALE_ROLE_MAP,
    FEMALE_ZIP,
    MALE_ROLE_MAP,
    MALE_ZIP,
    extract_zip,
    fade_window,
    load_stems,
    pad_or_trim,
    write_csv,
)
from tools.mgmg_v05_original_voice_match import select_phrase_events
from tools.mgmg_v07_mseq_male_center_human_tone import male_human_tone_v07, mono_center, mid_side, from_mid_side


WORK = ROOT / "mgmg_mashup_v13_work"
MALE_STEMS = WORK / "male_main_stems"
FEMALE_STEMS = WORK / "female_stems"
INTERMEDIATE = WORK / "intermediate"
OUTPUT = ROOT / "output"
REPORTS = ROOT / "reports"

CURRENT_ZIP = OUTPUT / "mgmg_mashup_v12_vocals_down_clear_stems_lufs6_preview_320.mp3.zip"
CURRENT_EXTRACT = WORK / "current_v12_preview"

BALANCED_WAV = OUTPUT / "mgmg_mashup_v13_vocal_blended_stems_clear_balanced_24-48.wav"
LOUD_WAV = OUTPUT / "mgmg_mashup_v13_vocal_blended_stems_clear_loud_24-48.wav"
PREVIEW_MP3 = OUTPUT / "mgmg_mashup_v13_preview_320.mp3"
REPORT_MD = REPORTS / "final_balance_audit.md"
SETTINGS_JSON = REPORTS / "final_processing_settings.json"


def music_mseq_v13(music: np.ndarray, sr: int) -> np.ndarray:
    mid, side = mid_side(music)
    mid_st = np.column_stack([mid, mid]).astype(np.float32)
    side_st = np.column_stack([side, side]).astype(np.float32)
    low = butter_filter(mid_st, sr, "lowpass", 120, 4)
    low_mono = np.mean(low, axis=1)
    mid_body = mid_st - low

    center_lowmid = bandpass(mid_body, sr, 1000, 2500, 3)
    center_presence = bandpass(mid_body, sr, 2500, 5500, 3)
    rest = mid_body - center_lowmid - center_presence
    mid_new = np.mean(
        rest
        + center_lowmid * float(amp_db(-0.45))
        + center_presence * float(amp_db(-0.75)),
        axis=1,
    ) + low_mono

    side_st = butter_filter(side_st, sr, "highpass", 140, 3)
    side_st = biquad_peaking(side_st, sr, 3400, 1.15, 1.0)
    side_st = biquad_peaking(side_st, sr, 6800, 0.85, 1.0)
    side_st = biquad_shelf(side_st, sr, 9800, 0.55, True)
    side_new = np.mean(side_st, axis=1) * float(amp_db(1.15))
    return from_mid_side(mid_new, side_new)


def mseq_female_separation(female_layer: np.ndarray, sr: int) -> np.ndarray:
    mid, side = mid_side(female_layer)
    mid_st = np.column_stack([mid, mid]).astype(np.float32)
    side_st = np.column_stack([side, side]).astype(np.float32)

    mid_st = butter_filter(mid_st, sr, "highpass", 175, 3)
    center_presence = bandpass(mid_st, sr, 900, 5200, 3)
    mid_st = mid_st - center_presence + center_presence * float(amp_db(-6.2))
    mid_st = biquad_peaking(mid_st, sr, 2600, -1.05, 1.1)

    side_st = butter_filter(side_st, sr, "highpass", 165, 3)
    side_st = biquad_peaking(side_st, sr, 2100, 0.45, 0.9)
    side_st = biquad_peaking(side_st, sr, 4300, 0.15, 1.0)
    side_st = biquad_shelf(side_st, sr, 9300, -0.70, True)
    side_st = side_st * float(amp_db(0.4))

    return from_mid_side(np.mean(mid_st, axis=1), np.mean(side_st, axis=1))


def seat_vocal_tone_v13(y: np.ndarray, sr: int, lead: bool) -> tuple[np.ndarray, list[dict[str, object]]]:
    out = y.copy()
    moves: list[dict[str, object]] = []
    for low, high, cut, pct, smooth, name in [
        (800, 1500, 1.4 if lead else 1.7, 76, 145, "nasal/shout dynamic seat"),
        (1500, 2500, 1.0 if lead else 1.4, 78, 130, "front-mid dynamic seat"),
        (2500, 5500, 2.5 if lead else 3.0, 75, 115, "presence dynamic seat"),
        (5500, 9200, 2.6 if lead else 3.0, 70, 75, "de-ess to reduce perceived vocal size"),
    ]:
        out, stats = dynamic_band_tame(out, sr, low, high, cut, pct, smooth, slope=0.52)
        stats["stage"] = name
        moves.append(stats)
    out = biquad_peaking(out, sr, 230, 0.45 if lead else 0.15, 0.85)
    out = saturate(out, drive_db=0.75 if lead else 0.55, mix=0.055 if lead else 0.04)
    out = compressor(out, sr, threshold_db=-17.0 if lead else -20.5, ratio=1.45 if lead else 1.35, smooth_ms=150, makeup_db=0.0)
    moves.append({"stage": "shorter vocal seat chain", "body_230_db": 0.45 if lead else 0.15, "sat_mix": 0.055 if lead else 0.04})
    return out.astype(np.float32), moves


def vocal_auto_seat(y: np.ndarray, sr: int, base_cut_db: float, peak_extra_db: float, smooth_ms: float = 180.0) -> np.ndarray:
    env = smooth_envelope(np.mean(y, axis=1), sr, smooth_ms)
    active = env[env > 1e-8]
    if not len(active):
        return y.astype(np.float32)
    low = float(np.percentile(active, 42))
    high = float(np.percentile(active, 97))
    norm = np.clip((env - low) / (high - low + 1e-9), 0.0, 1.0)
    gain = amp_db(-(base_cut_db + peak_extra_db * norm)).astype(np.float32)
    return (y * gain[:, None]).astype(np.float32)


def male_clear_tone_v10(y: np.ndarray, sr: int) -> tuple[np.ndarray, list[dict[str, object]]]:
    base, moves = process_vocal("lead_vocal", y, sr)
    base = mono_center(base)
    clarity = bandpass(base, sr, 1200, 5200, 3)
    clarity = compressor(clarity, sr, threshold_db=-27.5, ratio=2.2, smooth_ms=34, makeup_db=0.35)
    clarity = saturate(clarity, drive_db=1.45, mix=0.10)
    clarity, _ = dynamic_band_tame(clarity, sr, 5600, 9200, 1.6, 70, 55)
    body = bandpass(base, sr, 150, 420, 3)
    out = base * float(amp_db(0.8)) + clarity * float(amp_db(-8.5)) + body * float(amp_db(-13.0))
    out, _ = dynamic_band_tame(out, sr, 2600, 5600, 1.15, 82, 115)
    out, _ = dynamic_band_tame(out, sr, 5600, 9400, 2.0, 70, 65)
    out = biquad_peaking(out, sr, 230, 0.35, 0.8)
    out = biquad_peaking(out, sr, 2900, 0.75, 0.95)
    out = biquad_shelf(out, sr, 11200, 0.18, True)
    out = compressor(out, sr, threshold_db=-19.8, ratio=1.8, smooth_ms=96, makeup_db=0.25)
    moves.extend(
        [
            {"stage": "v10_clean_clarity_layer", "band_hz": "1200-5200", "return_db": -8.5, "sat_drive_db": 1.45, "sat_mix": 0.10},
            {"stage": "v10_no_hard_vocal_clip", "note": "removed heavy v07 Decapitator/clip layer to avoid crackle"},
            {"stage": "male_center_lock", "pan": "mono center"},
        ]
    )
    return mono_center(out.astype(np.float32)), moves


def drums_stable_punch(y: np.ndarray, sr: int) -> tuple[np.ndarray, list[dict[str, object]]]:
    out = butter_filter(y, sr, "highpass", 24, 3)
    out, stats = dynamic_band_tame(out, sr, 240, 560, 0.8, 82, 150)
    out = biquad_peaking(out, sr, 65, 0.9, 0.9)
    out = biquad_peaking(out, sr, 3600, 0.55, 1.0)
    out = biquad_peaking(out, sr, 7600, 0.35, 1.0)
    out = compressor(out, sr, threshold_db=-13.0, ratio=1.22, smooth_ms=230, makeup_db=0.25)
    out = saturate(out, drive_db=0.95, mix=0.09)
    out = soft_clip(out, drive_db=0.35, ceiling=0.96)
    out = limiter(out, -1.8)
    return out.astype(np.float32), [
        {"stage": "no_gate_drum_cleanup", "note": "no noise gate to avoid beat cut"},
        {"stage": "drum_low_mid_cleanup", **stats},
        {"stage": "clean_punch_light_sat", "ratio": 1.25, "sat_drive_db": 0.8},
    ]


def bass_stable_grit(y: np.ndarray, drums: np.ndarray, sr: int) -> tuple[np.ndarray, list[dict[str, object]]]:
    out, moves = process_instrument("bass", y, sr, drums=None, vocal=None)
    low = butter_filter(out, sr, "lowpass", 118, 4)
    low_mono = np.mean(low, axis=1)
    mid = bandpass(out, sr, 118, 820, 3)
    mid = saturate(mid, drive_db=2.2, mix=0.18)
    mid = biquad_peaking(mid, sr, 640, 0.8, 1.1)
    out = np.column_stack([low_mono, low_mono]).astype(np.float32) + mid * float(amp_db(0.35))
    out = compressor(out, sr, threshold_db=-14.8, ratio=1.18, smooth_ms=260, makeup_db=0.1)
    out = limiter(out, -1.8)
    moves.append({"stage": "clean_bass_no_hard_grit", "drive_db": 1.7, "note": "removed rough clip layer to avoid breakup"})
    return out.astype(np.float32), moves


def stem_clarity_v13(role: str, y: np.ndarray, sr: int) -> tuple[np.ndarray, list[dict[str, object]]]:
    out = y.copy()
    moves: list[dict[str, object]] = []
    if role in {"keys", "synth"}:
        out, stats = dynamic_band_tame(out, sr, 240, 620, 0.80, 82, 180, slope=0.36)
        out = biquad_peaking(out, sr, 1700, 0.65, 0.95)
        out = biquad_peaking(out, sr, 3800, 1.20, 1.05)
        out = biquad_peaking(out, sr, 7100, 0.55, 1.0)
        out = biquad_shelf(out, sr, 9800, 0.70, True)
        out = saturate(out, drive_db=0.45, mix=0.045)
        out = ms_width(out, 0.9 if role == "keys" else 1.2)
        moves.append({"stage": "stem_clarity_keys_synth_v13", **stats, "presence_db": 1.2, "side_width_db": 0.9 if role == "keys" else 1.2})
    elif role == "percussion":
        out, stats = dynamic_band_tame(out, sr, 260, 700, 0.75, 84, 130, slope=0.35)
        out = biquad_peaking(out, sr, 4800, 0.95, 1.0)
        out = biquad_shelf(out, sr, 9800, 0.35, True)
        out = ms_width(out, 1.1)
        moves.append({"stage": "stem_clarity_percussion_v13", **stats, "presence_db": 0.95, "side_width_db": 1.1})
    else:
        out, stats = dynamic_band_tame(out, sr, 260, 680, 0.65, 84, 160, slope=0.32)
        out = biquad_peaking(out, sr, 3000, 0.65, 1.0)
        out = biquad_shelf(out, sr, 9000, 0.35, True)
        out = ms_width(out, 0.8)
        moves.append({"stage": "stem_clarity_other_v13", **stats, "presence_db": 0.65, "side_width_db": 0.8})
    return out.astype(np.float32), moves


def dilated_activity_mask(source: np.ndarray, sr: int, target_coverage: float = 0.70) -> tuple[np.ndarray, float]:
    mono = np.mean(source, axis=1)
    env = smooth_envelope(mono, sr, 80)
    active_vals = env[env > 1e-8]
    if not len(active_vals):
        return np.ones(len(source), dtype=np.float32), 1.0
    threshold = float(np.percentile(active_vals, 30))
    active = env > threshold
    width = max(int(sr * 0.78), 1)
    dilated = np.convolve(active.astype(np.float32), np.ones(width, dtype=np.float32), mode="same") > 0
    if float(np.mean(dilated)) < target_coverage:
        needed = int(target_coverage * len(source))
        centers = np.flatnonzero(active)
        if len(centers):
            step = max(len(centers) // 48, 1)
            pad = int(sr * 0.55)
            for center in centers[::step]:
                start = max(center - pad, 0)
                end = min(center + pad, len(source))
                dilated[start:end] = True
                if int(np.sum(dilated)) >= needed:
                    break
    mask = dilated.astype(np.float32)
    fade = max(int(sr * 0.045), 1)
    kernel = np.hanning(fade * 2 + 1).astype(np.float32)
    kernel /= float(np.sum(kernel))
    mask = np.convolve(mask, kernel, mode="same").astype(np.float32)
    mask = np.clip(mask, 0.0, 1.0)
    return mask, float(np.mean(mask > 0.08))


def female_70_mseq_layers(female_source: np.ndarray, phrase_events: list[dict[str, float]], sr: int, length: int) -> tuple[np.ndarray, list[dict[str, object]], float]:
    src = pad_or_trim(female_source, length)
    src = butter_filter(src, sr, "highpass", 145, 3)
    src, _ = dynamic_band_tame(src, sr, 2600, 6200, 1.2, 78, 95)
    src, _ = dynamic_band_tame(src, sr, 5600, 9600, 1.9, 72, 70)
    src = biquad_peaking(src, sr, 1850, 0.35, 1.0)
    src = biquad_shelf(src, sr, 9800, -0.2, True)
    src = saturate(src, drive_db=0.9, mix=0.07)

    mask, coverage = dilated_activity_mask(src, sr, target_coverage=0.70)
    bed_left = pan_stereo(delay_samples(src, int(sr * 0.012)), -0.62)
    bed_right = pan_stereo(delay_samples(src, int(sr * 0.025)), 0.62)
    bed_center_shadow = mono_center(src) * float(amp_db(-15.0))
    bed = (bed_left + bed_right) * float(amp_db(-10.7)) + bed_center_shadow * float(amp_db(-4.0))
    bed *= mask[:, None]
    bed = ms_width(bed, 1.5)

    adlibs = np.zeros((length, 2), dtype=np.float32)
    events: list[dict[str, object]] = []
    selected = phrase_events[:]
    for idx, event in enumerate(selected):
        center = int(float(event["time_s"]) * sr)
        start = max(center - int(0.75 * sr), 0)
        end = min(center + int(0.55 * sr), length)
        if end - start <= int(0.14 * sr):
            continue
        seg = src[start:end].copy()
        seg *= fade_window(len(seg), int(0.04 * sr))[:, None]
        pan = -0.58 if idx % 2 == 0 else 0.58
        adlibs[start:end] += pan_stereo(seg, pan) * float(amp_db(-6.2))
        adlibs[start:end] += pan_stereo(delay_samples(seg, int(sr * 0.019)), -pan) * float(amp_db(-12.0))
        events.append({"time_s": round(start / sr, 3), "type": "female wide phrase layer", "pan": pan, "gain_db": -6.2})

        chop_len = int((0.10 + 0.012 * (idx % 3)) * sr)
        chop_start = max(center - int(0.20 * sr), 0)
        if chop_start + chop_len < length:
            chop = src[chop_start : chop_start + chop_len].copy()
            chop = butter_filter(chop, sr, "highpass", 260, 2)
            chop = butter_filter(chop, sr, "lowpass", 6900, 2)
            chop *= fade_window(len(chop), int(0.012 * sr))[:, None]
            place = min(center + int(0.12 * sr), length - chop_len)
            chop_pan = 0.72 if idx % 2 == 0 else -0.72
            adlibs[place : place + chop_len] += pan_stereo(chop, chop_pan) * float(amp_db(-8.4))
            events.append({"time_s": round(place / sr, 3), "type": "female side chop", "pan": chop_pan, "gain_db": -8.4})
    adlibs = biquad_shelf(adlibs, sr, 9300, -0.35, True)
    adlibs = ms_width(adlibs, 1.9)
    out = mseq_female_separation(bed + adlibs, sr)
    return out.astype(np.float32), events, coverage


def master_ms_tone_v13(y: np.ndarray, sr: int) -> np.ndarray:
    out = butter_filter(y, sr, "highpass", 22, 3)
    mid, side = mid_side(out)
    mid_st = np.column_stack([mid, mid]).astype(np.float32)
    side_st = np.column_stack([side, side]).astype(np.float32)
    mid_st, _ = dynamic_band_tame(mid_st, sr, 1000, 2500, 0.65, 84, 170, slope=0.34)
    mid_st, _ = dynamic_band_tame(mid_st, sr, 2500, 5500, 1.05, 82, 140, slope=0.42)
    mid_st = biquad_peaking(mid_st, sr, 260, -0.10, 1.0)
    side_st = butter_filter(side_st, sr, "highpass", 145, 3)
    side_st = biquad_peaking(side_st, sr, 4200, 0.75, 1.0)
    side_st = biquad_shelf(side_st, sr, 9500, 0.65, True)
    out = from_mid_side(np.mean(mid_st, axis=1), np.mean(side_st, axis=1) * float(amp_db(0.8)))
    out = compressor(out, sr, threshold_db=-12.8, ratio=1.18, smooth_ms=210, makeup_db=0.0)
    out = saturate(out, 0.18, 0.02)
    return limiter(out, -2.6)


def render_static_master(src: Path, dst: Path, label: str, target_lufs: float, drive_db: float, clip_ceiling: float) -> dict[str, object]:
    sr, y, _ = read_wav(src)
    oversample = 4
    gain_db = 20.0
    attempts: list[dict[str, object]] = []
    final = y.copy()
    for idx in range(10):
        upsampled = signal.resample_poly(y * float(amp_db(gain_db)), oversample, 1, axis=0).astype(np.float32)
        upsampled = soft_clip(upsampled, drive_db=drive_db, ceiling=clip_ceiling)
        upsampled = limiter(upsampled, float(20.0 * np.log10(clip_ceiling)))
        final = signal.resample_poly(upsampled, 1, oversample, axis=0).astype(np.float32)[: len(y)]
        final = limiter(final, -1.65)
        attempt_path = INTERMEDIATE / f"_{label}_attempt_{idx}.wav"
        write_float_wav(attempt_path, sr, final)
        metrics = audio_metrics(attempt_path, f"{label}_attempt_{idx}")
        attempts.append(metrics)
        current_lufs = metrics.get("integrated_lufs")
        if current_lufs is None:
            break
        delta = target_lufs - float(current_lufs)
        if abs(delta) < 0.12:
            break
        gain_db += float(np.clip(delta, -3.0, 3.0))
    final_float = INTERMEDIATE / f"_{label}_final_float.wav"
    write_float_wav(final_float, sr, final)
    convert_wav_24(final_float, dst)
    metrics = audio_metrics(dst, label)
    return {
        "target_lufs": target_lufs,
        "static_gain_db": round(gain_db, 3),
        "clip_drive_db": drive_db,
        "clip_ceiling": clip_ceiling,
        "oversample": oversample,
        "attempts": attempts,
        "metrics": metrics,
    }


def extract_current_preview() -> Path | None:
    if not CURRENT_ZIP.exists():
        return None
    CURRENT_EXTRACT.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(CURRENT_ZIP) as zf:
        for info in zf.infolist():
            name = Path(info.filename)
            if "__MACOSX" in name.parts or name.name.startswith("._"):
                continue
            zf.extract(info, CURRENT_EXTRACT)
    matches = sorted(CURRENT_EXTRACT.rglob("*.mp3"))
    return matches[0] if matches else None


def bus_stat(label: str, y: np.ndarray, sr: int) -> dict[str, object]:
    mid, side = mid_side(y)
    return {
        "label": label,
        "rms_dbfs": round(float(20.0 * np.log10(rms(y) + 1e-12)), 2),
        "peak_dbfs": round(float(20.0 * np.log10(np.max(np.abs(y)) + 1e-12)), 2),
        "side_mid_db": round(float(20.0 * np.log10((rms(side) + 1e-12) / (rms(mid) + 1e-12))), 2),
        "duration_s": round(len(y) / sr, 3),
    }


def write_report(
    current_metrics: dict[str, object] | None,
    output_rows: list[dict[str, object]],
    bus_stats: list[dict[str, object]],
    settings: dict[str, object],
) -> None:
    lines = [
        "# Final Balance Audit",
        "",
        "## Diagnosis",
        "",
        "- The v12 preview was pushed to about -6 LUFS, which made center vocal midrange dominate the mix.",
        "- The fix uses stems, not master-only processing: vocal presence is dynamically seated, instrumental side detail is lifted, and the master limiter/clipper is backed off.",
        "- The target is balance first: balanced version around -9 to -8.5 LUFS and loud version around -8.3 to -7.8 LUFS.",
        "",
    ]
    if current_metrics is not None:
        lines.extend(
            [
                "## Current v12 Preview",
                "",
                f"- Integrated LUFS: {current_metrics.get('integrated_lufs')}",
                f"- True peak: {current_metrics.get('true_peak_dbfs')} dBTP",
                f"- LRA: {current_metrics.get('lra_lu')} LU",
                f"- Short-term median/max: {current_metrics.get('short_term_lufs_median')} / {current_metrics.get('short_term_lufs_max')} LUFS",
                f"- Side/Mid: {current_metrics.get('side_mid_db')} dB",
                "",
            ]
        )
    lines.extend([
        "## Output Metrics",
        "",
        "| label | LUFS | TP | LRA | corr | side_mid |",
        "| --- | --- | --- | --- | --- | --- |",
    ])
    for row in output_rows:
        lines.append(f"| {row['label']} | {row.get('integrated_lufs')} | {row.get('true_peak_dbfs')} | {row.get('lra_lu')} | {row.get('stereo_corr')} | {row.get('side_mid_db')} |")
    lines.extend(["", "## Bus Balance", "", "| bus | RMS dBFS | peak dBFS | side/mid dB |", "| --- | --- | --- | --- |"])
    for row in bus_stats:
        lines.append(f"| {row['label']} | {row['rms_dbfs']} | {row['peak_dbfs']} | {row['side_mid_db']} |")
    lines.extend(
        [
            "",
            "## Main Moves",
            "",
            f"- Vocal-to-instrumental RMS ratio after balancing: {settings['analysis']['vocal_to_instrumental_rms_db']} dB.",
            "- Lead vocal was reduced with static gain plus envelope automation: base cut about 2.2 dB, loud phrase extra cut about 1.2 dB.",
            "- Female/adlib layer was reduced further and moved more to side energy with center presence cut.",
            "- Music M/S EQ: MID 1-2.5 kHz -0.45 dB, MID 2.5-5.5 kHz -0.75 dB, SIDE 3.4 kHz +1.15 dB, SIDE 6.8 kHz +0.85 dB, SIDE 9.8 kHz shelf +0.55 dB.",
            "- Master M/S EQ: MID 1-5.5 kHz dynamic control, SIDE 4.2 kHz/9.5 kHz lift, low end kept mono below about 120 Hz.",
            f"- Limiter/clipper was reduced versus v12: v12 used target -6 LUFS; v13 balanced/loud use gains {settings['master']['balanced']['static_gain_db']} dB and {settings['master']['loud']['static_gain_db']} dB with lighter drive.",
            "",
            f"- Phrase events used: {len(settings['phrase_events'])}",
            f"- Female layer coverage ratio: {settings['female_moves']['coverage_ratio']}",
        ]
    )
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    for directory in [WORK, MALE_STEMS, FEMALE_STEMS, INTERMEDIATE, OUTPUT, REPORTS]:
        directory.mkdir(parents=True, exist_ok=True)
    current_preview = extract_current_preview()
    current_metrics = audio_metrics(current_preview, "current_v12_preview_zip") if current_preview is not None else None
    extract_zip(MALE_ZIP, MALE_STEMS)
    extract_zip(FEMALE_ZIP, FEMALE_STEMS)
    male, sr, _ = load_stems(MALE_STEMS, MALE_ROLE_MAP)
    length = max(len(y) for y in male.values())
    female, female_sr, _ = load_stems(FEMALE_STEMS, FEMALE_ROLE_MAP, length=length)
    if female_sr != sr:
        raise RuntimeError("sample-rate mismatch")

    male_lead, male_moves = male_clear_tone_v10(male["lead_vocal"], sr)
    male_lead, male_seat_moves = seat_vocal_tone_v13(mono_center(male_lead), sr, lead=True)
    male_lead = vocal_auto_seat(male_lead, sr, base_cut_db=2.2, peak_extra_db=1.2)
    male_back, male_back_moves = process_vocal("backing_vocal", male["backing_vocal"], sr)
    male_back, male_back_seat_moves = seat_vocal_tone_v13(mono_center(male_back), sr, lead=False)
    male_back = vocal_auto_seat(male_back, sr, base_cut_db=4.0, peak_extra_db=1.0)
    male_vocal = male_lead + male_back

    phrase_endings = detect_phrase_endings(male_vocal, sr)
    phrase_events = select_phrase_events(phrase_endings)

    female_lead, female_lead_moves = process_vocal("backing_vocal", female["female_lead_source"], sr)
    female_back, female_back_moves = process_vocal("backing_vocal", female["female_backing_source"], sr)
    female_src = female_lead * float(amp_db(-1.1)) + female_back * float(amp_db(-2.5))
    female_src, female_seat_moves = seat_vocal_tone_v13(female_src, sr, lead=False)
    female_src = compressor(female_src, sr, -22.0, 1.2, 210, 0.0)
    female_layers, female_events, female_coverage = female_70_mseq_layers(female_src, phrase_events, sr, length)

    processed: dict[str, np.ndarray] = {}
    moves: dict[str, object] = {}
    processed["drums"], moves["drums"] = drums_stable_punch(male["drums"], sr)
    processed["bass"], moves["bass"] = bass_stable_grit(male["bass"], male["drums"], sr)
    for role in ["keys", "percussion", "synth", "other"]:
        instrument_role = "other" if role == "percussion" else role
        out, role_moves = process_instrument(instrument_role, male[role], sr, drums=None, vocal=None)
        out, clarity_moves = stem_clarity_v13(role, out, sr)
        processed[role] = out
        moves[role] = role_moves + clarity_moves

    music = (
        processed["drums"] * float(amp_db(2.15))
        + processed["bass"] * float(amp_db(1.65))
        + processed["keys"] * float(amp_db(2.25))
        + processed["percussion"] * float(amp_db(-0.65))
        + processed["synth"] * float(amp_db(2.35))
        + processed["other"] * float(amp_db(0.85))
    )
    music = music_mseq_v13(music, sr)

    ambience = reverb_send(male_vocal * float(amp_db(-2.8)) + female_layers * float(amp_db(-4.5)), sr, 0.62, -24.0, 18, 220, 7200, 909)
    ambience = sidechain_duck_full(ambience, male_vocal, sr, 2.8, 360, 68)
    reverb = reverb_send(male_vocal * float(amp_db(-5.8)) + female_layers * float(amp_db(-5.0)), sr, 1.12, -26.0, 42, 240, 6800, 808)
    reverb = sidechain_duck_full(reverb, male_vocal, sr, 4.2, 620, 70)
    throw_gate = make_throw_gate(length, sr, phrase_events, pre_ms=180, post_ms=110, fade_ms=30)
    delay_src = (female_layers * float(amp_db(-4.4)) + male_vocal * float(amp_db(-7.0))) * throw_gate[:, None]
    delay_fx = delay_throw(delay_src, sr, 322.6, 0.14, -25.0, 300, 5400, True)
    delay_fx = sidechain_duck_full(delay_fx, male_vocal, sr, 5.0, 520, 70)

    vocal_bus = male_vocal * float(amp_db(-1.2)) + female_layers * float(amp_db(-4.0))
    fx_bus = ambience + reverb + delay_fx
    mix = music + vocal_bus + fx_bus
    mix = limiter(mix * float(amp_db(-6.2)), -2.8)
    premaster = master_ms_tone_v13(mix, sr)
    premaster_wav = INTERMEDIATE / "v13_premaster_float.wav"
    write_float_wav(premaster_wav, sr, premaster)
    music_wav = INTERMEDIATE / "v13_music_bus_float.wav"
    vocal_wav = INTERMEDIATE / "v13_vocal_bus_float.wav"
    fx_wav = INTERMEDIATE / "v13_fx_bus_float.wav"
    write_float_wav(music_wav, sr, music)
    write_float_wav(vocal_wav, sr, vocal_bus)
    write_float_wav(fx_wav, sr, fx_bus)

    balanced_render = render_static_master(premaster_wav, BALANCED_WAV, "v13_balanced", -8.75, drive_db=0.28, clip_ceiling=0.82)
    loud_render = render_static_master(premaster_wav, LOUD_WAV, "v13_loud", -8.05, drive_db=0.45, clip_ceiling=0.78)
    convert_mp3(BALANCED_WAV, PREVIEW_MP3)
    rows = [
        audio_metrics(BALANCED_WAV, "v13_balanced"),
        audio_metrics(LOUD_WAV, "v13_loud"),
        audio_metrics(PREVIEW_MP3, "v13_preview_mp3"),
    ]
    write_csv(REPORTS / "render_audit_v13.csv", rows)
    bus_stats = [bus_stat("music_bus", music, sr), bus_stat("vocal_bus", vocal_bus, sr), bus_stat("fx_bus", fx_bus, sr)]
    vocal_to_inst = round(float(20.0 * np.log10((rms(vocal_bus) + 1e-12) / (rms(music) + 1e-12))), 2)
    settings = {
        "direction": "blend vocals into track, reduce vocal-forward center image, improve stem audibility, avoid -6 LUFS vocal-popout mastering",
        "analysis": {"vocal_to_instrumental_rms_db": vocal_to_inst},
        "male_moves": male_moves + male_seat_moves + male_back_seat_moves + [
            {"stage": "lead_vocal_static_plus_automation_down", "base_cut_db": 2.2, "peak_extra_cut_db": 1.2},
            {"stage": "vocal_bus_down", "gain_db": -1.2},
        ],
        "female_moves": {"lead": female_lead_moves, "backing": female_back_moves, "seat": female_seat_moves, "events": female_events, "coverage_ratio": round(female_coverage, 3), "bus_gain_db": -4.0},
        "instrument_moves": moves,
        "stem_gain_changes_db": {"drums": 2.15, "bass": 1.65, "keys": 2.25, "percussion": -0.65, "synth": 2.35, "other": 0.85},
        "mseq": {
            "music": "MID 1-2.5 kHz -0.45 dB, MID 2.5-5.5 kHz -0.75 dB, SIDE 3.4 kHz +1.15 dB, SIDE 6.8 kHz +0.85 dB, SIDE 9.8 kHz shelf +0.55 dB",
            "female": "MID 900-5200 Hz reduced by about 6.2 dB, side support kept but moderated",
            "master": "dynamic MID 1-5.5 kHz control, SIDE 4.2 kHz +0.75 dB and 9.5 kHz shelf +0.65 dB",
            "low_end": "under 120 Hz kept mono/center",
        },
        "fx": {"ambience": "0.62s short room, predelay 18ms, ducked 2.8 dB", "plate": "1.12s plate, ducked 4.2 dB", "delay": "phrase throws only, feedback 0.14, ducked 5 dB"},
        "master": {"balanced": balanced_render, "loud": loud_render},
        "phrase_events": phrase_events,
        "metrics": rows,
        "bus_stats": bus_stats,
    }
    SETTINGS_JSON.write_text(json.dumps(settings, ensure_ascii=False, indent=2), encoding="utf-8")
    write_report(current_metrics, rows, bus_stats, settings)
    print(BALANCED_WAV)
    print(LOUD_WAV)
    print(PREVIEW_MP3)
    print(REPORT_MD)
    print(SETTINGS_JSON)


if __name__ == "__main__":
    main()

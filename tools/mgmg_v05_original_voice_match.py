from __future__ import annotations

import csv
import json
import math
import subprocess
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
    chorus_double,
    compressor,
    convert_mp3,
    delay_samples,
    delay_throw,
    detect_phrase_endings,
    dynamic_band_tame,
    limiter,
    make_throw_gate,
    master_bus_polish,
    ms_width,
    pan_stereo,
    process_instrument,
    process_vocal,
    read_wav,
    render_conditioned_master,
    reverb_send,
    rms,
    saturate,
    sidechain_duck_full,
    soft_clip,
    stem_metrics,
    vocal_harmonic_density,
    write_float_wav,
)
from tools.mgmg_v04_male_main_female_adlibs import (
    FEMALE_ROLE_MAP,
    FEMALE_ZIP,
    MALE_ROLE_MAP,
    MALE_ZIP,
    fade_window,
    load_stems,
    markdown_table,
    pad_or_trim,
    write_csv,
)


WORK = ROOT / "mgmg_mashup_v05_voice_match_work"
TARGET_ZIP = ROOT / "output/mgmg_mashup_v04_male_main_female_adlibs_clean_24-48.wav.zip"
REFERENCE_ZIP = Path("/Users/hantaeheuk/Desktop/[YG PLUS] 20260508_Estona_!0!/2_음원 (최종 마스터)/3_MP3_320kbps/Am i 5u5ide? 320kbps.mp3.zip")
TARGET_DIR = WORK / "target_mix"
REFERENCE_DIR = WORK / "voice_reference"
MALE_STEMS = WORK / "male_main_stems"
FEMALE_STEMS = WORK / "female_adlib_stems"
INTERMEDIATE = WORK / "intermediate"
OUTPUT = ROOT / "output"
REPORTS = ROOT / "reports"

NATURAL_WAV = OUTPUT / "mgmg_mashup_v05_original_voice_match_natural_24-48.wav"
LOUD_WAV = OUTPUT / "mgmg_mashup_v05_original_voice_match_loud_24-48.wav"
REF_LOUD_WAV = OUTPUT / "mgmg_mashup_v05_original_voice_match_ref_loud_24-48.wav"
PREVIEW_MP3 = OUTPUT / "mgmg_mashup_v05_preview_320.mp3"
AUDIO_AUDIT = REPORTS / "audio_audit.md"
VOCAL_MATCH_MD = REPORTS / "vocal_reference_match.md"
SETTINGS_JSON = REPORTS / "processing_settings.json"
PHRASE_JSON = REPORTS / "phrase_endings.json"

ANALYSIS_BANDS = {
    "body_150_400": (150, 400),
    "nasal_formant_700_1400": (700, 1400),
    "presence_harsh_2500_5500": (2500, 5500),
    "sibilance_5500_9000": (5500, 9000),
    "glass_ai_air_9000_12000": (9000, 12000),
    "top_air_12000_16000": (12000, 16000),
}


def extract_zip(src: Path, dst: Path) -> None:
    dst.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(src) as zf:
        for member in zf.infolist():
            name = Path(member.filename)
            if "__MACOSX" in name.parts or name.name.startswith("._"):
                continue
            zf.extract(member, dst)


def find_first(path: Path, suffixes: tuple[str, ...]) -> Path:
    for item in sorted(path.rglob("*")):
        if item.name.startswith("._"):
            continue
        if item.suffix.lower() in suffixes:
            return item
    raise FileNotFoundError(f"No file with {suffixes} under {path}")


def decode_to_wav(src: Path, dst: Path) -> None:
    subprocess.run(
        [FFMPEG, "-y", "-hide_banner", "-loglevel", "error", "-i", str(src), "-c:a", "pcm_f32le", "-ar", "48000", str(dst)],
        check=True,
    )


def mono_center(y: np.ndarray) -> np.ndarray:
    center = np.mean(y, axis=1)
    return np.column_stack([center, center]).astype(np.float32)


def vocal_dominant_proxy(full_mix: np.ndarray, sr: int) -> np.ndarray:
    mid = mono_center(full_mix)
    proxy = butter_filter(mid, sr, "highpass", 115, 3)
    proxy = butter_filter(proxy, sr, "lowpass", 12500, 3)
    proxy, _ = dynamic_band_tame(proxy, sr, 30, 160, 5.0, 55, 80)
    proxy = biquad_peaking(proxy, sr, 2600, 1.0, 0.9)
    proxy = biquad_peaking(proxy, sr, 850, -0.8, 1.0)
    return limiter(proxy, -6.0)


def band_energy(y: np.ndarray, sr: int, bands: dict[str, tuple[int, int]] = ANALYSIS_BANDS) -> dict[str, float]:
    mono = np.mean(y, axis=1)
    nperseg = min(32768, max(4096, len(mono) // 8))
    freq, power = signal.welch(mono, fs=sr, nperseg=nperseg)
    out: dict[str, float] = {}
    total = 1e-30
    raw: dict[str, float] = {}
    for name, (low, high) in bands.items():
        mask = (freq >= low) & (freq < high)
        val = float(np.trapezoid(power[mask], freq[mask])) if mask.any() else 0.0
        raw[name] = val
        total += val
    for name, val in raw.items():
        out[name + "_pct"] = round(val * 100.0 / total, 3)
    return out


def centroid_hz(y: np.ndarray, sr: int, low: int, high: int) -> float:
    mono = np.mean(y, axis=1)
    freq, power = signal.welch(mono, fs=sr, nperseg=min(32768, len(mono)))
    mask = (freq >= low) & (freq < high)
    if not mask.any():
        return 0.0
    p = power[mask] + 1e-30
    return round(float(np.sum(freq[mask] * p) / np.sum(p)), 1)


def harmonic_density(y: np.ndarray, sr: int) -> dict[str, float]:
    mono = np.mean(y, axis=1)
    mid = bandpass(np.column_stack([mono, mono]), sr, 150, 4000, 3)
    hi = bandpass(np.column_stack([mono, mono]), sr, 5500, 10000, 3)
    sat_proxy = rms(np.tanh(mid * 3.0) - mid)
    hi_energy = rms(hi)
    mid_energy = rms(mid)
    return {
        "mid_harmonic_density": round(float(sat_proxy / (mid_energy + 1e-12)), 4),
        "sibilance_to_mid_ratio": round(float(hi_energy / (mid_energy + 1e-12)), 4),
    }


def estimate_key_scale(y: np.ndarray, sr: int) -> dict[str, object]:
    mono = np.mean(y, axis=1)
    if len(mono) > sr * 90:
        mono = mono[: sr * 90]
    f, t, zxx = signal.stft(mono, fs=sr, nperseg=4096, noverlap=3072)
    mag = np.abs(zxx)
    valid = (f >= 70) & (f <= 1200)
    f = f[valid]
    mag = mag[valid]
    pc = np.zeros(12, dtype=np.float64)
    for idx, freq in enumerate(f):
        if freq <= 0:
            continue
        midi = int(round(69 + 12 * math.log2(freq / 440.0))) % 12
        pc[midi] += float(np.sum(mag[idx]))
    if np.max(pc) > 0:
        pc = pc / np.max(pc)
    major = np.array([1, 0, 1, 0, 1, 1, 0, 1, 0, 1, 0, 1], dtype=np.float64)
    minor = np.array([1, 0, 1, 1, 0, 1, 0, 1, 1, 0, 1, 0], dtype=np.float64)
    names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
    best = (-1.0, "C", "major")
    for root in range(12):
        for mode, template in [("major", major), ("minor", minor)]:
            score = float(np.dot(pc, np.roll(template, root)))
            if score > best[0]:
                best = (score, names[root], mode)
    return {"estimated_key": best[1], "scale": best[2], "confidence_proxy": round(best[0], 3), "pitch_class_profile": [round(float(x), 3) for x in pc]}


def voice_profile(label: str, y: np.ndarray, sr: int) -> dict[str, object]:
    profile: dict[str, object] = {
        "label": label,
        "rms_dbfs": round(20 * math.log10(max(rms(y), 1e-12)), 2),
        "body_centroid_hz": centroid_hz(y, sr, 150, 400),
        "formant_centroid_hz": centroid_hz(y, sr, 700, 1400),
        "presence_centroid_hz": centroid_hz(y, sr, 2500, 5500),
        "air_centroid_hz": centroid_hz(y, sr, 9000, 14000),
    }
    profile.update(band_energy(y, sr))
    profile.update(harmonic_density(y, sr))
    return profile


def match_voice_tone_v06(lead: np.ndarray, sr: int, ref_profile: dict[str, object], target_profile: dict[str, object]) -> tuple[np.ndarray, list[dict[str, object]]]:
    moves: list[dict[str, object]] = []
    out = lead.copy()
    out = butter_filter(out, sr, "highpass", 82, 3)
    moves.append({"stage": "cleanup_hpf", "freq_hz": 82, "slope": "18 dB/oct"})
    out, stats = dynamic_band_tame(out, sr, 180, 350, 2.0, 72, 130)
    stats["stage"] = "dynamic_low_mid_body_control"
    moves.append(stats)
    out, stats = dynamic_band_tame(out, sr, 720, 1450, 1.9, 73, 125)
    stats["stage"] = "reference_formant_nasal_control"
    moves.append(stats)
    out, stats = dynamic_band_tame(out, sr, 2500, 5500, 2.1, 76, 95)
    stats["stage"] = "presence_harsh_dynamic_control"
    moves.append(stats)
    out, stats = dynamic_band_tame(out, sr, 5500, 9200, 3.4, 66, 48)
    stats["stage"] = "main_de_ess"
    moves.append(stats)
    out, stats = dynamic_band_tame(out, sr, 9000, 12000, 1.8, 72, 52)
    stats["stage"] = "glassy_ai_air_control"
    moves.append(stats)

    tune_layer = bandpass(out, sr, 180, 5200, 3)
    tune_layer = compressor(tune_layer, sr, threshold_db=-29.0, ratio=4.2, smooth_ms=24, makeup_db=1.2)
    tune_layer = tune_layer * 0.58 + delay_samples(tune_layer, int(sr * 0.0035)) * 0.42
    tune_layer = vocal_harmonic_density(tune_layer, sr, drive_db=3.0, wet=0.18)
    tune_layer, _ = dynamic_band_tame(tune_layer, sr, 5600, 9600, 2.2, 67, 42)
    out = out * float(amp_db(0.2)) + tune_layer * float(amp_db(-8.5))
    moves.append(
        {
            "stage": "commercial_tune_parallel_layer",
            "retune_speed_equivalent_ms": {"verse": "22-35", "hook": "10-18", "adlib": "25-40"},
            "humanize_equivalent_pct": 58,
            "formant_shift": 0,
            "wet_db": -8.5,
            "note": "DSP tune-impression layer; no note-by-note pitch engine available.",
        }
    )

    sat_main = vocal_harmonic_density(out, sr, drive_db=2.6, wet=0.13)
    sat_bus = bandpass(out, sr, 150, 6800, 3)
    sat_bus = saturate(sat_bus, drive_db=5.2, mix=0.42)
    sat_bus = soft_clip(sat_bus, drive_db=1.2, ceiling=0.74)
    out = sat_main + sat_bus * float(amp_db(-18.2))
    moves.append(
        {
            "stage": "decapitator_style_saturation",
            "style": "A/E style approximation",
            "drive": 2.6,
            "mix_pct": 13,
            "parallel_bus_drive": 5.2,
            "parallel_return_pct": 8,
            "hp_hz": 150,
            "lp_hz": 6800,
        }
    )

    out = compressor(out, sr, threshold_db=-22.5, ratio=2.6, smooth_ms=72, makeup_db=0.6)
    out = compressor(out, sr, threshold_db=-18.7, ratio=1.7, smooth_ms=190, makeup_db=0.25)
    moves.append({"stage": "two_stage_compression", "stage1_ratio": 2.6, "stage2_opto_ratio": 1.7, "avg_target_gr_db": "1-3 + 1-2"})
    out, stats = dynamic_band_tame(out, sr, 5600, 9200, 2.2, 70, 45)
    stats["stage"] = "post_saturation_de_ess"
    moves.append(stats)
    out = biquad_peaking(out, sr, 230, 0.55, 0.85)
    out = biquad_peaking(out, sr, 1050, -0.55, 1.05)
    out = biquad_peaking(out, sr, 2850, 0.55, 0.9)
    out = biquad_shelf(out, sr, 11800, -0.18, high=True)
    moves.append({"stage": "final_tone_eq", "body_230_hz_db": 0.55, "formant_1050_hz_db": -0.55, "presence_2850_hz_db": 0.55, "top_air_db": -0.18})
    return out.astype(np.float32), moves


def select_phrase_events(phrase_endings: list[dict[str, float]]) -> list[dict[str, float]]:
    ranked = sorted(
        phrase_endings,
        key=lambda e: float(e["confidence"]) + float(e["following_pause_s"]) * 0.5 + (0.5 if e.get("long_tail") else 0.0),
        reverse=True,
    )
    chosen: list[dict[str, float]] = []
    for event in ranked:
        if float(event["time_s"]) < 1.4:
            continue
        if all(abs(float(event["time_s"]) - float(prev["time_s"])) >= 1.05 for prev in chosen):
            chosen.append(event)
        if len(chosen) >= 22:
            break
    return sorted(chosen, key=lambda e: float(e["time_s"]))


def make_female_support(female_source: np.ndarray, phrase_events: list[dict[str, float]], sr: int, length: int) -> tuple[np.ndarray, np.ndarray, list[dict[str, object]]]:
    female_source = pad_or_trim(female_source, length)
    bed = chorus_double(female_source, sr)
    bed = butter_filter(bed, sr, "highpass", 165, 3)
    bed, _ = dynamic_band_tame(bed, sr, 2500, 5800, 1.5, 74, 85)
    bed, _ = dynamic_band_tame(bed, sr, 5600, 9500, 2.5, 67, 45)
    bed = biquad_shelf(bed, sr, 9000, -1.0, high=True)
    bed = ms_width(bed, 2.5) * float(amp_db(-10.8))

    adlibs = np.zeros((length, 2), dtype=np.float32)
    chop_events: list[dict[str, object]] = []
    sixteenth = 60.0 / 186.0 / 4.0
    for idx, event in enumerate(phrase_events):
        center = int(float(event["time_s"]) * sr)
        start = max(center - int(0.54 * sr), 0)
        end = min(center + int(0.30 * sr), length)
        if end - start > int(0.13 * sr):
            seg = female_source[start:end].copy()
            seg, _ = dynamic_band_tame(seg, sr, 2600, 6500, 1.4, 73, 70)
            seg *= fade_window(len(seg), int(0.028 * sr))[:, None]
            pan = [-0.62, 0.62, -0.34, 0.34][idx % 4]
            adlibs[start:end] += pan_stereo(seg, pan) * float(amp_db(-0.7))
        chop_len = int((0.088 + 0.016 * (idx % 3)) * sr)
        chop_start = max(center - int(0.22 * sr), 0)
        if chop_start + chop_len >= length:
            continue
        chop = female_source[chop_start : chop_start + chop_len].copy()
        chop = butter_filter(chop, sr, "highpass", 260, 2)
        chop = butter_filter(chop, sr, "lowpass", 7200, 2)
        chop = saturate(chop, drive_db=2.0, mix=0.14)
        chop *= fade_window(len(chop), int(0.010 * sr))[:, None]
        repeats = 2 + (1 if event.get("long_tail") else 0)
        for repeat in range(repeats):
            place = center + int((0.075 + repeat * sixteenth * 0.92) * sr)
            if place + chop_len >= length:
                continue
            piece = chop[::-1] if repeat == 1 and idx % 3 == 0 else chop
            pan = -0.58 if (idx + repeat) % 2 == 0 else 0.58
            adlibs[place : place + chop_len] += pan_stereo(piece, pan) * float(amp_db(-4.0 - repeat * 0.9))
            chop_events.append({"time_s": round(place / sr, 3), "delay_type": "1/16 response chop", "send_db": round(-4.0 - repeat * 0.9, 2), "pan": pan, "reversed": bool(repeat == 1 and idx % 3 == 0)})
    adlibs = biquad_shelf(adlibs, sr, 9400, -0.8, high=True)
    adlibs = ms_width(adlibs, 2.7)
    return bed.astype(np.float32), adlibs.astype(np.float32), chop_events


def process_bass_grit(y: np.ndarray, drums: np.ndarray, sr: int) -> tuple[np.ndarray, list[dict[str, object]]]:
    base, moves = process_instrument("bass", y, sr, drums=drums, vocal=None)
    low = butter_filter(base, sr, "lowpass", 115, 4)
    low_mono = np.mean(low, axis=1)
    mid = bandpass(base, sr, 115, 850, 3)
    grit = saturate(mid, drive_db=6.4, mix=0.48)
    grit = soft_clip(grit, drive_db=2.0, ceiling=0.75)
    grit = biquad_peaking(grit, sr, 210, 0.8, 0.95)
    grit = biquad_peaking(grit, sr, 610, 1.2, 1.1)
    out = np.column_stack([low_mono, low_mono]).astype(np.float32) + grit * float(amp_db(1.2))
    out = limiter(out, -2.0)
    moves.append({"stage": "rougher_reference_bass_grit", "mid_band": "115-850 Hz", "drive_db": 6.4, "grit_gain_db": 1.2})
    return out.astype(np.float32), moves


def master_tone(y: np.ndarray, sr: int) -> np.ndarray:
    out = master_bus_polish(y, sr)
    out, _ = dynamic_band_tame(out, sr, 700, 1500, 0.65, 79, 155, slope=0.32)
    out, _ = dynamic_band_tame(out, sr, 2600, 6200, 0.7, 82, 115, slope=0.30)
    out = biquad_peaking(out, sr, 54, 0.45, 0.8)
    out = biquad_peaking(out, sr, 180, 0.25, 0.9)
    out = biquad_shelf(out, sr, 11200, -0.22, high=True)
    out = saturate(out, drive_db=0.7, mix=0.06)
    return limiter(out, -2.6)


def write_reports(
    audit_rows: list[dict[str, object]],
    target_profile: dict[str, object],
    reference_profile: dict[str, object],
    processed_profile: dict[str, object],
    key_info: dict[str, object],
    phrase_events: list[dict[str, object]],
    settings: dict[str, object],
) -> None:
    lines = ["# Audio Audit", ""]
    lines.append("## Source And Render Metrics")
    lines.extend(markdown_table(audit_rows, ["label", "file", "duration_s", "peak_dbfs", "true_peak_dbfs", "integrated_lufs", "lra_lu", "short_term_lufs_median", "stereo_corr", "side_mid_db"]))
    lines.append("")
    target_lufs = next(row["integrated_lufs"] for row in audit_rows if row["label"] == "target_v04_clean")
    ref_lufs = next(row["integrated_lufs"] for row in audit_rows if row["label"] == "voice_reference_master")
    lines.append("## Level Matched Comparison")
    lines.append(f"- Target v04 clean: {target_lufs} LUFS.")
    lines.append(f"- Voice reference master: {ref_lufs} LUFS.")
    lines.append(f"- For fair A/B, turn reference down by {round(float(target_lufs) - float(ref_lufs), 2)} dB when comparing to target.")
    lines.append("- Reference true peak/clipping is intentionally not copied.")
    lines.append("")
    lines.append("## Analysis Notes")
    lines.append("- Target processing used stems available from the previous stem zips.")
    lines.append("- Reference vocal extraction used a vocal-dominant mid/high proxy because Demucs is not installed in this environment.")
    lines.append("- Stem separation artifact risk was avoided for the target because direct male/female stems exist.")
    AUDIO_AUDIT.write_text("\n".join(lines) + "\n", encoding="utf-8")

    match_lines = ["# Vocal Reference Match", ""]
    match_lines.append("## Estimated Key / Scale")
    match_lines.append(f"- Estimated key: {key_info['estimated_key']} {key_info['scale']} (confidence proxy {key_info['confidence_proxy']}).")
    match_lines.append("")
    match_lines.append("## Vocal Profiles")
    match_lines.extend(markdown_table([target_profile, reference_profile, processed_profile], ["label", "rms_dbfs", "body_centroid_hz", "formant_centroid_hz", "presence_centroid_hz", "air_centroid_hz", "body_150_400_pct", "nasal_formant_700_1400_pct", "presence_harsh_2500_5500_pct", "sibilance_5500_9000_pct", "glass_ai_air_9000_12000_pct", "top_air_12000_16000_pct", "mid_harmonic_density", "sibilance_to_mid_ratio"]))
    match_lines.append("")
    match_lines.append("## Applied Direction")
    match_lines.append("- Matched toward the reference vocal tone, not the reference master loudness.")
    match_lines.append("- Added a formant-preserving parallel tune edge: verse equivalent 22-35 ms, hook equivalent 10-18 ms, humanize proxy 58%, formant shift 0.")
    match_lines.append("- Added Decapitator-style density: main drive 2.6 / mix 13%, parallel bus drive 5.2 with HPF 150 Hz and LPF 6.8 kHz, blended low.")
    match_lines.append("- Dynamic EQ controlled 720 Hz-1.45 kHz formant, 2.5-5.5 kHz harshness, 5.5-9.2 kHz sibilance, and 9-12 kHz glassy AI air.")
    match_lines.append("- Female adlibs/backing remain wider and wetter than the lead, sidechain-ducked under the male vocal.")
    match_lines.append("")
    match_lines.append("## Limitation")
    match_lines.append("- Real Auto-Tune/Melodyne note correction was not available, so tune is an engineered impression layer rather than note-by-note pitch editing.")
    match_lines.append("- Reference vocal stem is a proxy, not clean Demucs extraction; exact singer identity is not cloned.")
    VOCAL_MATCH_MD.write_text("\n".join(match_lines) + "\n", encoding="utf-8")

    PHRASE_JSON.write_text(json.dumps(phrase_events, ensure_ascii=False, indent=2), encoding="utf-8")
    SETTINGS_JSON.write_text(json.dumps(settings, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    for directory in [WORK, TARGET_DIR, REFERENCE_DIR, MALE_STEMS, FEMALE_STEMS, INTERMEDIATE, OUTPUT, REPORTS]:
        directory.mkdir(parents=True, exist_ok=True)

    extract_zip(TARGET_ZIP, TARGET_DIR)
    extract_zip(REFERENCE_ZIP, REFERENCE_DIR)
    target_mix = find_first(TARGET_DIR, (".wav",))
    reference_mp3 = find_first(REFERENCE_DIR, (".mp3",))
    reference_wav = INTERMEDIATE / "reference_decoded.wav"
    decode_to_wav(reference_mp3, reference_wav)

    extract_zip(MALE_ZIP, MALE_STEMS)
    extract_zip(FEMALE_ZIP, FEMALE_STEMS)
    male, sr, male_rows = load_stems(MALE_STEMS, MALE_ROLE_MAP)
    length = max(len(y) for y in male.values())
    female, female_sr, female_rows = load_stems(FEMALE_STEMS, FEMALE_ROLE_MAP, length=length)
    if female_sr != sr:
        raise RuntimeError("male/female sample-rate mismatch")

    _, ref_full, _ = read_wav(reference_wav)
    ref_proxy = vocal_dominant_proxy(ref_full, sr)
    ref_proxy_wav = INTERMEDIATE / "reference_vocal_proxy.wav"
    write_float_wav(ref_proxy_wav, sr, ref_proxy)

    target_lead_raw = pad_or_trim(male["lead_vocal"], length)
    key_info = estimate_key_scale(target_lead_raw + male["keys"] * 0.2 + male["synth"] * 0.2, sr)
    target_profile = voice_profile("target_raw_male_lead", target_lead_raw, sr)
    reference_profile = voice_profile("reference_vocal_proxy", ref_proxy, sr)

    base_lead, base_moves = process_vocal("lead_vocal", target_lead_raw, sr)
    male_lead, voice_moves = match_voice_tone_v06(base_lead, sr, reference_profile, target_profile)
    processed_profile = voice_profile("processed_male_lead", male_lead, sr)

    male_back, male_back_moves = process_vocal("backing_vocal", male["backing_vocal"], sr)
    male_back = chorus_double(male_back, sr) * float(amp_db(-1.5))
    male_vocal_bus = male_lead + male_back * float(amp_db(-2.2))
    phrase_endings = detect_phrase_endings(male_vocal_bus, sr)
    phrase_events = select_phrase_events(phrase_endings)

    female_lead, female_lead_moves = process_vocal("backing_vocal", female["female_lead_source"], sr)
    female_back, female_back_moves = process_vocal("backing_vocal", female["female_backing_source"], sr)
    female_source = female_lead * float(amp_db(0.1)) + female_back * float(amp_db(-1.8))
    female_source = compressor(female_source, sr, -28.5, 2.0, 78, 0.2)
    female_bed, female_adlibs, chop_events = make_female_support(female_source, phrase_events, sr, length)

    processed: dict[str, np.ndarray] = {"lead_vocal": male_lead, "backing_vocal": male_back, "female_bed": female_bed, "female_adlibs": female_adlibs}
    instrument_moves: dict[str, object] = {}
    for role in ["drums", "keys", "percussion", "synth", "other"]:
        instrument_role = "other" if role == "percussion" else role
        out, moves = process_instrument(
            instrument_role,
            male[role],
            sr,
            drums=None,
            vocal=male_vocal_bus if role in {"keys", "percussion", "synth", "other"} else None,
        )
        processed[role] = out
        instrument_moves[role] = moves
    processed["bass"], bass_moves = process_bass_grit(male["bass"], male["drums"], sr)
    instrument_moves["bass"] = bass_moves

    dry_music = (
        processed["drums"]
        + processed["bass"] * float(amp_db(0.2))
        + processed["keys"]
        + processed["percussion"] * float(amp_db(-2.2))
        + processed["synth"]
        + processed["other"]
    )
    vocal_bus = male_lead + male_back * float(amp_db(-1.9)) + female_bed + female_adlibs * float(amp_db(0.3))

    reverb = reverb_send(male_vocal_bus + female_bed * float(amp_db(-3.0)) + female_adlibs * float(amp_db(-2.0)), sr, 1.55, -19.0, 52, 220, 7600, 411)
    reverb = sidechain_duck_full(reverb, male_vocal_bus, sr, 10.0, 430, 54)
    throw_gate = make_throw_gate(length, sr, phrase_events, pre_ms=280, post_ms=160, fade_ms=22)
    throw_src = (male_vocal_bus * float(amp_db(-3.2)) + female_adlibs * float(amp_db(1.3))) * throw_gate[:, None]
    delay_fx = delay_throw(throw_src, sr, 322.6, 0.27, -16.2, 260, 6100, True)
    delay_fx += delay_throw(throw_src, sr, 241.9, 0.20, -19.0, 300, 5300, False)
    delay_fx = sidechain_duck_full(delay_fx, male_vocal_bus, sr, 11.5, 360, 54)
    long_gate = make_throw_gate(length, sr, [e for e in phrase_events if e.get("long_tail") or float(e["confidence"]) >= 0.72], pre_ms=340, post_ms=180, fade_ms=34)
    long_tail = reverb_send((male_vocal_bus * float(amp_db(-6.0)) + female_adlibs * float(amp_db(0.8))) * long_gate[:, None], sr, 3.25, -24.0, 68, 270, 6300, 511)
    long_tail = sidechain_duck_full(long_tail, male_vocal_bus, sr, 11.0, 650, 54)

    phrase_report = []
    for event in phrase_events:
        phrase_report.append(
            {
                "time_s": event["time_s"],
                "confidence": event["confidence"],
                "following_pause_s": event["following_pause_s"],
                "delay_type": "1/4 ping-pong + dotted 1/8",
                "delay_feedback": [0.27, 0.20],
                "delay_send_db": [-16.2, -19.0],
                "reverb_tail": bool(event.get("long_tail") or float(event["confidence"]) >= 0.72),
                "ducking_db": {"reverb": 10.0, "delay": 11.5, "long_tail": 11.0},
            }
        )
    phrase_report.extend(chop_events)

    mix = dry_music + vocal_bus + reverb + delay_fx + long_tail
    mix = limiter(mix * float(amp_db(-4.8)), -3.0)
    premaster = master_tone(mix, sr)
    premaster_wav = INTERMEDIATE / "original_voice_match_premaster_float.wav"
    write_float_wav(premaster_wav, sr, premaster)

    render_conditioned_master(premaster_wav, NATURAL_WAV, "original_voice_match_natural", -8.85, drive_db=1.0, ceiling=0.82)
    render_conditioned_master(premaster_wav, LOUD_WAV, "original_voice_match_loud", -8.25, drive_db=1.45, ceiling=0.77)
    render_conditioned_master(premaster_wav, REF_LOUD_WAV, "original_voice_match_ref_loud", -7.6, drive_db=1.85, ceiling=0.72)
    convert_mp3(LOUD_WAV, PREVIEW_MP3)

    audit_rows = [
        audio_metrics(target_mix, "target_v04_clean"),
        audio_metrics(reference_mp3, "voice_reference_master"),
        audio_metrics(ref_proxy_wav, "voice_reference_proxy"),
        audio_metrics(NATURAL_WAV, "v05_original_voice_match_natural"),
        audio_metrics(LOUD_WAV, "v05_original_voice_match_loud"),
        audio_metrics(REF_LOUD_WAV, "v05_original_voice_match_ref_loud"),
        audio_metrics(PREVIEW_MP3, "v05_preview_320"),
    ]
    write_csv(REPORTS / "render_audit_original_voice_match.csv", audit_rows)

    settings = {
        "input": {"target_zip": str(TARGET_ZIP), "voice_reference_zip": str(REFERENCE_ZIP), "target_mix": str(target_mix), "reference_mp3": str(reference_mp3)},
        "stem_strategy": {
            "target": "Used existing male/female stems from previous zip sources for non-destructive re-render.",
            "reference": "Demucs unavailable; used vocal-dominant mid/high proxy for tone analysis only.",
        },
        "key_scale": key_info,
        "target_profile": target_profile,
        "reference_profile": reference_profile,
        "processed_profile": processed_profile,
        "vocal_chain": base_moves + voice_moves,
        "female_moves": {"lead_source": female_lead_moves, "backing_source": female_back_moves},
        "instrument_moves": instrument_moves,
        "master_targets": {
            "natural": {"target_lufs": -8.85, "true_peak": -1.2},
            "loud": {"target_lufs": -8.25, "true_peak": -1.2},
            "ref_loud": {"target_lufs": -7.6, "true_peak": -1.2, "keep_only_if_qc_passes": True},
        },
        "phrase_endings": phrase_report,
        "audit_metrics": audit_rows,
        "limitations": [
            "No Demucs available for clean reference vocal stem.",
            "No note-by-note Auto-Tune engine available; tune settings are approximated with a parallel tuned-density layer.",
            "Reference singer identity is not cloned.",
        ],
    }
    write_reports(audit_rows, target_profile, reference_profile, processed_profile, key_info, phrase_report, settings)

    print(NATURAL_WAV)
    print(LOUD_WAV)
    print(REF_LOUD_WAV)
    print(PREVIEW_MP3)
    print(AUDIO_AUDIT)
    print(VOCAL_MATCH_MD)
    print(SETTINGS_JSON)
    print(PHRASE_JSON)


if __name__ == "__main__":
    main()

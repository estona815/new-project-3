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
    audio_metrics,
    bandpass,
    biquad_peaking,
    biquad_shelf,
    butter_filter,
    compressor,
    convert_mp3,
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
    render_conditioned_master,
    reverb_send,
    smooth_envelope,
    saturate,
    sidechain_duck_full,
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
from tools.mgmg_v05_original_voice_match import (
    match_voice_tone_v06,
    master_tone,
    process_bass_grit,
    select_phrase_events,
    voice_profile,
)


WORK = ROOT / "mgmg_mashup_v07_work"
MALE_STEMS = WORK / "male_main_stems"
FEMALE_STEMS = WORK / "female_full_pan_stems"
INTERMEDIATE = WORK / "intermediate"
OUTPUT = ROOT / "output"
REPORTS = ROOT / "reports"

OUT_WAV = OUTPUT / "mgmg_mashup_v07_mseq_male_center_human_tone_loud_24-48.wav"
OUT_MP3 = OUTPUT / "mgmg_mashup_v07_mseq_male_center_human_tone_preview_320.mp3"
REPORT_MD = REPORTS / "audio_audit_v07.md"
SETTINGS_JSON = REPORTS / "processing_settings_v07.json"


def mono_center(y: np.ndarray) -> np.ndarray:
    mono = np.mean(y, axis=1)
    return np.column_stack([mono, mono]).astype(np.float32)


def mid_side(y: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    mid = (y[:, 0] + y[:, 1]) * 0.5
    side = (y[:, 0] - y[:, 1]) * 0.5
    return mid.astype(np.float32), side.astype(np.float32)


def from_mid_side(mid: np.ndarray, side: np.ndarray) -> np.ndarray:
    return np.column_stack([mid + side, mid - side]).astype(np.float32)


def mseq_music_pocket(music: np.ndarray, vocal: np.ndarray, sr: int) -> np.ndarray:
    mid, side = mid_side(music)
    mid_st = np.column_stack([mid, mid]).astype(np.float32)
    side_st = np.column_stack([side, side]).astype(np.float32)

    low = butter_filter(mid_st, sr, "lowpass", 120, 4)
    mid_hi = mid_st - low
    low_mono = np.mean(low, axis=1)

    pocket = bandpass(mid_hi, sr, 1500, 4700, 3)
    rest = mid_hi - pocket
    trig = np.mean(vocal, axis=1)
    env = np.abs(trig)
    env = env / (np.percentile(env, 97) + 1e-9)
    env = np.clip(env, 0.0, 1.0)
    gain = amp_db(-1.8 * env).astype(np.float32)
    mid_ducked = rest + pocket * gain[:, None]

    side_st = butter_filter(side_st, sr, "highpass", 135, 3)
    side_st = biquad_peaking(side_st, sr, 3200, 0.45, 1.0)
    side_st = biquad_shelf(side_st, sr, 9000, -0.25, True)
    side_st = side_st * float(amp_db(1.1))
    new_mid = np.mean(mid_ducked, axis=1) + low_mono
    new_side = np.mean(side_st, axis=1)
    return from_mid_side(new_mid, new_side)


def mseq_female_side_space(female: np.ndarray, sr: int) -> np.ndarray:
    mid, side = mid_side(female)
    mid_st = np.column_stack([mid, mid]).astype(np.float32)
    side_st = np.column_stack([side, side]).astype(np.float32)
    mid_st = butter_filter(mid_st, sr, "highpass", 190, 3)
    mid_st = biquad_peaking(mid_st, sr, 2600, -0.9, 1.0)
    side_st = butter_filter(side_st, sr, "highpass", 155, 3)
    side_st = biquad_peaking(side_st, sr, 3300, 0.55, 1.0)
    side_st = biquad_shelf(side_st, sr, 9200, -0.6, True)
    return from_mid_side(np.mean(mid_st, axis=1) * float(amp_db(-2.2)), np.mean(side_st, axis=1) * float(amp_db(2.1)))


def downward_noise_gate(y: np.ndarray, sr: int, threshold_percentile: float, floor_db: float, smooth_ms: float) -> np.ndarray:
    env = smooth_envelope(np.mean(y, axis=1), sr, smooth_ms)
    active = env[env > 1e-7]
    threshold = float(np.percentile(active, threshold_percentile)) if len(active) else 1e-4
    openness = np.clip(env / (threshold + 1e-9), 0.0, 1.0)
    gain_db = floor_db * np.power(1.0 - openness, 1.7)
    return (y * amp_db(gain_db)[:, None]).astype(np.float32)


def drums_punch_clean_v07(y: np.ndarray, sr: int) -> tuple[np.ndarray, list[dict[str, object]]]:
    out = butter_filter(y, sr, "highpass", 26, 3)
    out = downward_noise_gate(out, sr, threshold_percentile=28, floor_db=-14.0, smooth_ms=24)
    out, stats = dynamic_band_tame(out, sr, 230, 560, 1.4, 76, 90)
    out = biquad_peaking(out, sr, 68, 0.8, 0.9)
    out = biquad_peaking(out, sr, 3600, 0.6, 1.0)
    out = compressor(out, sr, threshold_db=-18.0, ratio=2.3, smooth_ms=72, makeup_db=1.1)
    out = saturate(out, drive_db=2.8, mix=0.22)
    out = soft_clip(out, drive_db=1.4, ceiling=0.88)
    out = limiter(out, -2.0)
    return out.astype(np.float32), [
        {"stage": "drum_noise_gate", "threshold_percentile": 28, "floor_db": -14.0},
        {"stage": "drum_low_mid_cleanup", **stats},
        {"stage": "drum_punch_comp_sat_clip", "compression_ratio": 2.3, "saturation_drive_db": 2.8, "soft_clip_drive_db": 1.4},
    ]


def bass_punch_clean_v07(y: np.ndarray, drums: np.ndarray, sr: int) -> tuple[np.ndarray, list[dict[str, object]]]:
    gated = downward_noise_gate(y, sr, threshold_percentile=18, floor_db=-9.0, smooth_ms=85)
    out, moves = process_bass_grit(gated, drums, sr)
    low = butter_filter(out, sr, "lowpass", 118, 4)
    low_mono = np.mean(low, axis=1)
    mid = bandpass(out, sr, 118, 900, 3)
    mid = saturate(mid, drive_db=5.2, mix=0.36)
    out = np.column_stack([low_mono, low_mono]).astype(np.float32) + mid * float(amp_db(1.0))
    out = compressor(out, sr, threshold_db=-19.0, ratio=2.0, smooth_ms=95, makeup_db=0.9)
    out = limiter(out, -2.0)
    moves.append({"stage": "bass_noise_gate_and_level", "threshold_percentile": 18, "floor_db": -9.0, "makeup_db": 0.9})
    return out.astype(np.float32), moves


def male_human_tone_v07(y: np.ndarray, sr: int) -> tuple[np.ndarray, list[dict[str, object]]]:
    base, base_moves = process_vocal("lead_vocal", y, sr)
    profile = voice_profile("male_raw", y, sr)
    matched, match_moves = match_voice_tone_v06(base, sr, profile, profile)

    locked = bandpass(matched, sr, 160, 5400, 3)
    locked = compressor(locked, sr, threshold_db=-30.0, ratio=5.0, smooth_ms=18, makeup_db=1.4)
    locked = locked * 0.50 + delay_samples(locked, int(sr * 0.003)) * 0.34 + delay_samples(locked, int(sr * 0.006)) * 0.16
    locked = vocal_harmonic_density(locked, sr, drive_db=3.6, wet=0.22)
    locked, _ = dynamic_band_tame(locked, sr, 5600, 9500, 2.8, 66, 42)

    sat_bus = bandpass(matched, sr, 145, 7200, 3)
    sat_bus = saturate(sat_bus, drive_db=6.6, mix=0.50)
    sat_bus = soft_clip(sat_bus, drive_db=1.5, ceiling=0.72)
    sat_bus = biquad_shelf(sat_bus, sr, 7600, -1.2, True)

    out = matched * float(amp_db(0.6)) + locked * float(amp_db(-6.7)) + sat_bus * float(amp_db(-15.5))
    out, _ = dynamic_band_tame(out, sr, 700, 1450, 1.8, 75, 115)
    out, _ = dynamic_band_tame(out, sr, 2600, 5600, 1.8, 78, 90)
    out, _ = dynamic_band_tame(out, sr, 5600, 9200, 3.0, 67, 45)
    out = compressor(out, sr, threshold_db=-21.2, ratio=2.8, smooth_ms=64, makeup_db=0.7)
    out = biquad_peaking(out, sr, 235, 0.7, 0.85)
    out = biquad_peaking(out, sr, 2800, 0.55, 0.9)
    out = biquad_shelf(out, sr, 11200, -0.35, True)
    moves = base_moves + match_moves + [
        {"stage": "v07_stronger_tune_layer", "retune_feel": "hook 8-15ms / verse 18-30ms", "wet_db": -6.7, "formant_shift": 0},
        {"stage": "v07_decapitator_style_sat", "drive": 6.6, "return_db": -15.5, "hp_hz": 145, "lp_hz": 7200, "tone": "slightly dark"},
        {"stage": "male_center_lock", "pan": "mono center after tone chain"},
    ]
    return mono_center(out), moves


def female_full_layers(female_source: np.ndarray, phrase_events: list[dict[str, float]], sr: int, length: int) -> tuple[np.ndarray, list[dict[str, object]]]:
    source = pad_or_trim(female_source, length)
    source = butter_filter(source, sr, "highpass", 155, 3)
    source, _ = dynamic_band_tame(source, sr, 2500, 6200, 1.9, 73, 85)
    source, _ = dynamic_band_tame(source, sr, 5600, 9600, 2.8, 67, 45)
    source = biquad_shelf(source, sr, 9300, -0.95, True)

    left = pan_stereo(delay_samples(source, int(sr * 0.013)), -0.74)
    right = pan_stereo(delay_samples(source, int(sr * 0.026)), 0.74)
    bed = (left + right) * float(amp_db(-7.5))
    bed = mseq_female_side_space(bed, sr)

    emphasis = np.zeros((length, 2), dtype=np.float32)
    events: list[dict[str, object]] = []
    sixteenth = 60.0 / 186.0 / 4.0
    for idx, event in enumerate(phrase_events):
        center = int(float(event["time_s"]) * sr)
        start = max(center - int(0.62 * sr), 0)
        end = min(center + int(0.42 * sr), length)
        if end - start > int(0.14 * sr):
            seg = source[start:end].copy()
            seg *= fade_window(len(seg), int(0.03 * sr))[:, None]
            pan = -0.68 if idx % 2 == 0 else 0.68
            emphasis[start:end] += pan_stereo(seg, pan) * float(amp_db(0.3))
            emphasis[start:end] += pan_stereo(delay_samples(seg, int(sr * 0.018)), -pan) * float(amp_db(-4.4))
            events.append({"time_s": round(start / sr, 3), "type": "female phrase overlap", "pan": pan, "gain_db": 0.3})
        chop_len = int((0.09 + 0.016 * (idx % 3)) * sr)
        chop_start = max(center - int(0.24 * sr), 0)
        if chop_start + chop_len >= length:
            continue
        chop = source[chop_start : chop_start + chop_len].copy()
        chop = butter_filter(chop, sr, "highpass", 270, 2)
        chop = butter_filter(chop, sr, "lowpass", 7200, 2)
        chop = saturate(chop, 2.1, 0.14)
        chop *= fade_window(len(chop), int(0.010 * sr))[:, None]
        repeats = 2 + (1 if idx % 3 == 0 or event.get("long_tail") else 0)
        for repeat in range(repeats):
            place = center + int((0.07 + repeat * sixteenth * 0.86) * sr)
            if place + chop_len >= length:
                continue
            piece = chop[::-1] if repeat == 1 and idx % 2 == 0 else chop
            pan = -0.60 if (idx + repeat) % 2 == 0 else 0.60
            gain_db = -3.1 - repeat * 0.95
            emphasis[place : place + chop_len] += pan_stereo(piece, pan) * float(amp_db(gain_db))
            events.append({"time_s": round(place / sr, 3), "type": "female chop", "pan": pan, "gain_db": round(gain_db, 2), "reversed": bool(repeat == 1 and idx % 2 == 0)})
    emphasis = mseq_female_side_space(emphasis, sr)
    return (bed + emphasis).astype(np.float32), events


def write_report(rows: list[dict[str, object]], phrase_events: list[dict[str, object]], female_events: list[dict[str, object]]) -> None:
    lines = [
        "# v07 M/S EQ Male Center Human Tone",
        "",
        "- Male lead/backing: mono center, no panning.",
        "- M/S EQ: instrumental mid 1.5-4.7 kHz ducks under male vocal; female/FX sit wider in side.",
        "- Male vocal: stronger tune-impression layer and Decapitator-style saturation, then de-ess/dynamic EQ.",
        "",
        "| label | LUFS | TP | LRA | corr | side_mid |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(f"| {row['label']} | {row.get('integrated_lufs')} | {row.get('true_peak_dbfs')} | {row.get('lra_lu')} | {row.get('stereo_corr')} | {row.get('side_mid_db')} |")
    lines.extend(["", f"- Phrase events: {len(phrase_events)}", f"- Female pan/overlap/chop events: {len(female_events)}"])
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


WORK = ROOT / "mgmg_mashup_v07_work"
MALE_STEMS = WORK / "male_main_stems"
FEMALE_STEMS = WORK / "female_stems"
INTERMEDIATE = WORK / "intermediate"
OUTPUT = ROOT / "output"
REPORTS = ROOT / "reports"
OUT_WAV = OUTPUT / "mgmg_mashup_v07_mseq_male_center_human_tone_loud_24-48.wav"
OUT_MP3 = OUTPUT / "mgmg_mashup_v07_mseq_male_center_human_tone_preview_320.mp3"
REPORT_MD = REPORTS / "audio_audit_v07.md"
SETTINGS_JSON = REPORTS / "processing_settings_v07.json"


def main() -> None:
    for directory in [WORK, MALE_STEMS, FEMALE_STEMS, INTERMEDIATE, OUTPUT, REPORTS]:
        directory.mkdir(parents=True, exist_ok=True)
    extract_zip(MALE_ZIP, MALE_STEMS)
    extract_zip(FEMALE_ZIP, FEMALE_STEMS)
    male, sr, _ = load_stems(MALE_STEMS, MALE_ROLE_MAP)
    length = max(len(y) for y in male.values())
    female, female_sr, _ = load_stems(FEMALE_STEMS, FEMALE_ROLE_MAP, length=length)
    if female_sr != sr:
        raise RuntimeError("sample-rate mismatch")

    male_lead, male_moves = male_human_tone_v07(male["lead_vocal"], sr)
    male_back, male_back_moves = process_vocal("backing_vocal", male["backing_vocal"], sr)
    male_back = mono_center(male_back) * float(amp_db(-4.8))
    male_vocal = male_lead * float(amp_db(1.2)) + male_back
    phrase_endings = detect_phrase_endings(male_vocal, sr)
    phrase_events = select_phrase_events(phrase_endings)

    female_lead, female_lead_moves = process_vocal("backing_vocal", female["female_lead_source"], sr)
    female_back, female_back_moves = process_vocal("backing_vocal", female["female_backing_source"], sr)
    female_source = female_lead * float(amp_db(0.9)) + female_back * float(amp_db(-0.9))
    female_source = compressor(female_source, sr, -28.0, 2.0, 74, 0.5)
    female_layers, female_events = female_full_layers(female_source, phrase_events, sr, length)

    processed: dict[str, np.ndarray] = {}
    instrument_moves: dict[str, object] = {}
    for role in ["drums", "keys", "percussion", "synth", "other"]:
        instrument_role = "other" if role == "percussion" else role
        out, moves = process_instrument(instrument_role, male[role], sr, drums=None, vocal=male_vocal if role in {"keys", "percussion", "synth", "other"} else None)
        processed[role] = out
        instrument_moves[role] = moves
    processed["drums"], drum_moves = drums_punch_clean_v07(male["drums"], sr)
    instrument_moves["drums"] = drum_moves
    processed["bass"], bass_moves = bass_punch_clean_v07(male["bass"], male["drums"], sr)
    instrument_moves["bass"] = bass_moves

    music = processed["drums"] * float(amp_db(1.2)) + processed["bass"] * float(amp_db(1.1)) + processed["keys"] + processed["percussion"] * float(amp_db(-2.4)) + processed["synth"] + processed["other"]
    music = mseq_music_pocket(music, male_vocal, sr)
    reverb = reverb_send(male_vocal * float(amp_db(-1.5)) + female_layers * float(amp_db(-1.0)), sr, 1.55, -19.2, 52, 225, 7400, 707)
    reverb = sidechain_duck_full(reverb, male_vocal, sr, 10.5, 430, 54)
    throw_gate = make_throw_gate(length, sr, phrase_events, pre_ms=300, post_ms=180, fade_ms=22)
    delay_src = (female_layers * float(amp_db(1.1))) * throw_gate[:, None]
    delay_fx = delay_throw(delay_src, sr, 322.6, 0.27, -16.0, 260, 6000, True)
    delay_fx += delay_throw(delay_src, sr, 241.9, 0.20, -19.0, 300, 5200, False)
    delay_fx = sidechain_duck_full(delay_fx, male_vocal, sr, 12.0, 360, 54)

    mix = music + male_vocal + female_layers + reverb + delay_fx
    mix = limiter(mix * float(amp_db(-5.2)), -3.0)
    premaster = master_tone(mix, sr)
    premaster_wav = INTERMEDIATE / "v07_premaster_float.wav"
    write_float_wav(premaster_wav, sr, premaster)
    render_conditioned_master(premaster_wav, OUT_WAV, "v07_mseq_male_center_human_tone", -8.35, drive_db=1.45, ceiling=0.77)
    convert_mp3(OUT_WAV, OUT_MP3)
    rows = [audio_metrics(OUT_WAV, "v07_loud"), audio_metrics(OUT_MP3, "v07_preview_mp3")]
    write_csv(REPORTS / "render_audit_v07.csv", rows)
    settings = {
        "direction": "M/S EQ separation, male mono center, stronger tune/saturation human tone, female panned layers",
        "male_moves": {"lead": male_moves, "backing": male_back_moves},
        "female_moves": {"lead": female_lead_moves, "backing": female_back_moves},
        "mseq": {
            "music_mid_vocal_pocket": "1.5-4.7 kHz mid duck up to 1.8 dB from male vocal envelope",
            "female_side_space": "female mid tucked -2.2 dB, side +2.1 dB, HPF 155-190 Hz",
            "low_end": "music low under 120 Hz forced to mid/mono",
        },
        "drum_bass_cleanup": {
            "drums": "HPF 26 Hz, downward noise gate floor -14 dB, low-mid cleanup, punch compression, saturation, soft clipping",
            "bass": "subtle downward gate floor -9 dB, mono low band, grit saturation, compression makeup",
        },
        "phrase_events": phrase_events,
        "female_events": female_events,
        "instrument_moves": instrument_moves,
        "metrics": rows,
    }
    SETTINGS_JSON.write_text(json.dumps(settings, ensure_ascii=False, indent=2), encoding="utf-8")
    write_report(rows, phrase_events, female_events)
    print(OUT_WAV)
    print(OUT_MP3)
    print(REPORT_MD)
    print(SETTINGS_JSON)


if __name__ == "__main__":
    main()

from __future__ import annotations

import json
import sys
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


WORK = ROOT / "mgmg_mashup_v10_work"
MALE_STEMS = WORK / "male_main_stems"
FEMALE_STEMS = WORK / "female_stems"
INTERMEDIATE = WORK / "intermediate"
OUTPUT = ROOT / "output"
REPORTS = ROOT / "reports"

OUT_WAV = OUTPUT / "mgmg_mashup_v10_clean_clear_vocal_melody_24-48.wav"
OUT_MP3 = OUTPUT / "mgmg_mashup_v10_clean_clear_vocal_melody_preview_320.mp3"
REPORT_MD = REPORTS / "audio_audit_v10.md"
SETTINGS_JSON = REPORTS / "processing_settings_v10.json"


def static_music_space(music: np.ndarray, sr: int) -> np.ndarray:
    mid, side = mid_side(music)
    mid_st = np.column_stack([mid, mid]).astype(np.float32)
    side_st = np.column_stack([side, side]).astype(np.float32)
    low = butter_filter(mid_st, sr, "lowpass", 120, 4)
    low_mono = np.mean(low, axis=1)
    mid_body = mid_st - low

    pocket = bandpass(mid_body, sr, 1800, 4200, 3)
    rest = mid_body - pocket
    mid_new = np.mean(rest + pocket * float(amp_db(-0.10)), axis=1) + low_mono

    side_st = butter_filter(side_st, sr, "highpass", 140, 3)
    side_st = biquad_peaking(side_st, sr, 2600, 0.45, 1.0)
    side_st = biquad_peaking(side_st, sr, 5200, 0.25, 1.0)
    side_new = np.mean(side_st, axis=1) * float(amp_db(0.55))
    return from_mid_side(mid_new, side_new)


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
    out = biquad_peaking(out, sr, 3600, 0.3, 1.0)
    out = compressor(out, sr, threshold_db=-13.5, ratio=1.25, smooth_ms=210, makeup_db=0.15)
    out = saturate(out, drive_db=0.8, mix=0.08)
    out = soft_clip(out, drive_db=0.25, ceiling=0.96)
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
    mid = saturate(mid, drive_db=1.7, mix=0.14)
    out = np.column_stack([low_mono, low_mono]).astype(np.float32) + mid * float(amp_db(0.15))
    out = compressor(out, sr, threshold_db=-14.8, ratio=1.18, smooth_ms=260, makeup_db=0.1)
    out = limiter(out, -1.8)
    moves.append({"stage": "clean_bass_no_hard_grit", "drive_db": 1.7, "note": "removed rough clip layer to avoid breakup"})
    return out.astype(np.float32), moves


def female_adlib_layers(female_source: np.ndarray, phrase_events: list[dict[str, float]], sr: int, length: int) -> tuple[np.ndarray, list[dict[str, object]]]:
    src = pad_or_trim(female_source, length)
    src = butter_filter(src, sr, "highpass", 155, 3)
    src, _ = dynamic_band_tame(src, sr, 2500, 6200, 1.7, 74, 85)
    src, _ = dynamic_band_tame(src, sr, 5600, 9600, 2.6, 67, 45)
    src = biquad_shelf(src, sr, 9400, -0.8, True)

    bed_left = pan_stereo(delay_samples(src, int(sr * 0.014)), -0.56)
    bed_right = pan_stereo(delay_samples(src, int(sr * 0.026)), 0.56)
    bed = (bed_left + bed_right) * float(amp_db(-15.5))
    bed = ms_width(bed, 1.0)

    adlibs = np.zeros((length, 2), dtype=np.float32)
    events: list[dict[str, object]] = []
    selected = phrase_events[:14]
    for idx, event in enumerate(selected):
        center = int(float(event["time_s"]) * sr)
        start = max(center - int(0.56 * sr), 0)
        end = min(center + int(0.34 * sr), length)
        if end - start <= int(0.14 * sr):
            continue
        seg = src[start:end].copy()
        seg *= fade_window(len(seg), int(0.03 * sr))[:, None]
        pan = -0.46 if idx % 2 == 0 else 0.46
        adlibs[start:end] += pan_stereo(seg, pan) * float(amp_db(-5.3))
        adlibs[start:end] += pan_stereo(delay_samples(seg, int(sr * 0.018)), -pan) * float(amp_db(-11.0))
        events.append({"time_s": round(start / sr, 3), "type": "female adlib/double layer", "pan": pan, "gain_db": -5.3})
    adlibs = biquad_shelf(adlibs, sr, 9300, -0.7, True)
    adlibs = ms_width(adlibs, 1.15)
    return (bed + adlibs).astype(np.float32), events


def stable_master_tone(y: np.ndarray, sr: int) -> np.ndarray:
    out = butter_filter(y, sr, "highpass", 22, 3)
    out = biquad_peaking(out, sr, 58, 0.10, 0.9)
    out = biquad_peaking(out, sr, 260, -0.18, 1.0)
    out = biquad_peaking(out, sr, 3300, 0.25, 1.0)
    out = biquad_shelf(out, sr, 11200, 0.08, high=True)
    out = saturate(out, 0.18, 0.025)
    return limiter(out, -2.4)


def render_static_master(src: Path, dst: Path, target_lufs: float) -> dict[str, object]:
    sr, y, _ = read_wav(src)
    gain_db = 16.8
    drive_db = 0.65
    clip_ceiling = 0.80
    oversample = 4
    upsampled = signal.resample_poly(y * float(amp_db(gain_db)), oversample, 1, axis=0).astype(np.float32)
    upsampled = soft_clip(upsampled, drive_db=drive_db, ceiling=clip_ceiling)
    upsampled = limiter(upsampled, float(20.0 * np.log10(clip_ceiling)))
    final = signal.resample_poly(upsampled, 1, oversample, axis=0).astype(np.float32)[: len(y)]
    final = limiter(final, -1.3)
    final_float = INTERMEDIATE / "_v10_static_master_final_float.wav"
    write_float_wav(final_float, sr, final)
    convert_wav_24(final_float, dst)
    metrics = audio_metrics(dst, "v09_static_master")
    return {
        "target_lufs": target_lufs,
        "static_gain_db": gain_db,
        "clip_drive_db": drive_db,
        "clip_ceiling": clip_ceiling,
        "oversample": oversample,
        "metrics": metrics,
    }


def write_report(rows: list[dict[str, object]], phrase_events: list[dict[str, object]], female_events: list[dict[str, object]]) -> None:
    lines = [
        "# v10 Clean Clear Vocal Melody",
        "",
        "- Lowered the loudness push to stop breakup/crackling.",
        "- Rebuilt the male main vocal with a cleaner clarity layer and no hard vocal clip.",
        "- Brought keyboard/synth melody forward in the mix instead of crushing the master.",
        "- Female vocal remains quieter adlib/double/layer only.",
        "",
        "| label | LUFS | TP | LRA | corr | side_mid |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(f"| {row['label']} | {row.get('integrated_lufs')} | {row.get('true_peak_dbfs')} | {row.get('lra_lu')} | {row.get('stereo_corr')} | {row.get('side_mid_db')} |")
    lines.extend(["", f"- Phrase events detected/used: {len(phrase_events)}", f"- Female adlib/double events: {len(female_events)}"])
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


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

    male_lead, male_moves = male_clear_tone_v10(male["lead_vocal"], sr)
    male_lead = mono_center(male_lead) * float(amp_db(3.0))
    male_back, male_back_moves = process_vocal("backing_vocal", male["backing_vocal"], sr)
    male_back = mono_center(male_back) * float(amp_db(-5.5))
    male_vocal = male_lead + male_back

    phrase_endings = detect_phrase_endings(male_vocal, sr)
    phrase_events = select_phrase_events(phrase_endings)

    female_lead, female_lead_moves = process_vocal("backing_vocal", female["female_lead_source"], sr)
    female_back, female_back_moves = process_vocal("backing_vocal", female["female_backing_source"], sr)
    female_src = female_lead * float(amp_db(0.2)) + female_back * float(amp_db(-1.4))
    female_src = compressor(female_src, sr, -24.0, 1.4, 150, 0.0)
    female_layers, female_events = female_adlib_layers(female_src, phrase_events, sr, length)

    processed: dict[str, np.ndarray] = {}
    moves: dict[str, object] = {}
    processed["drums"], moves["drums"] = drums_stable_punch(male["drums"], sr)
    processed["bass"], moves["bass"] = bass_stable_grit(male["bass"], male["drums"], sr)
    for role in ["keys", "percussion", "synth", "other"]:
        instrument_role = "other" if role == "percussion" else role
        out, role_moves = process_instrument(instrument_role, male[role], sr, drums=None, vocal=None)
        processed[role] = out
        moves[role] = role_moves

    music = (
        processed["drums"] * float(amp_db(0.9))
        + processed["bass"] * float(amp_db(0.6))
        + processed["keys"] * float(amp_db(1.0))
        + processed["percussion"] * float(amp_db(-2.5))
        + processed["synth"] * float(amp_db(1.1))
        + processed["other"] * float(amp_db(-0.2))
    )
    music = static_music_space(music, sr)

    reverb = reverb_send(male_vocal * float(amp_db(-4.0)) + female_layers * float(amp_db(-4.0)), sr, 1.15, -24.5, 48, 240, 6800, 808)
    reverb = sidechain_duck_full(reverb, male_vocal, sr, 2.5, 650, 72)
    throw_gate = make_throw_gate(length, sr, phrase_events, pre_ms=180, post_ms=110, fade_ms=30)
    delay_src = (female_layers * float(amp_db(-1.8))) * throw_gate[:, None]
    delay_fx = delay_throw(delay_src, sr, 322.6, 0.16, -22.0, 300, 5400, True)
    delay_fx = sidechain_duck_full(delay_fx, male_vocal, sr, 2.5, 560, 72)

    mix = music + male_vocal + female_layers + reverb + delay_fx
    mix = limiter(mix * float(amp_db(-6.0)), -2.7)
    premaster = stable_master_tone(mix, sr)
    premaster_wav = INTERMEDIATE / "v10_premaster_float.wav"
    write_float_wav(premaster_wav, sr, premaster)
    master_render = render_static_master(premaster_wav, OUT_WAV, -7.8)
    convert_mp3(OUT_WAV, OUT_MP3)
    rows = [audio_metrics(OUT_WAV, "v10_clean_clear"), audio_metrics(OUT_MP3, "v10_preview_mp3")]
    write_csv(REPORTS / "render_audit_v10.csv", rows)
    settings = {
        "direction": "fix v09 clipping/breakup; prioritize clean clear centered male vocal and clear main melody over -6 LUFS loudness",
        "male_moves": male_moves + [{"stage": "male_level_up", "gain_db": 3.0}, {"stage": "male_back_center_low", "gain_db": -5.5}],
        "female_moves": {"lead": female_lead_moves, "backing": female_back_moves, "events": female_events},
        "instrument_moves": moves,
        "mseq": {"music_pocket": "static 0.10 dB mid pocket only, melody side/presence retained", "low_end": "under 120 Hz kept mono/center"},
        "master_render": master_render,
        "phrase_events": phrase_events,
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

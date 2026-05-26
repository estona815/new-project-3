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
from tools.mgmg_v05_original_voice_match import master_tone, process_bass_grit, select_phrase_events, voice_profile
from tools.mgmg_v07_mseq_male_center_human_tone import male_human_tone_v07, mono_center, mid_side, from_mid_side


WORK = ROOT / "mgmg_mashup_v08_work"
MALE_STEMS = WORK / "male_main_stems"
FEMALE_STEMS = WORK / "female_stems"
INTERMEDIATE = WORK / "intermediate"
OUTPUT = ROOT / "output"
REPORTS = ROOT / "reports"

OUT_WAV = OUTPUT / "mgmg_mashup_v08_clear_main_female_layers_lufs6_24-48.wav"
OUT_MP3 = OUTPUT / "mgmg_mashup_v08_clear_main_female_layers_lufs6_preview_320.mp3"
REPORT_MD = REPORTS / "audio_audit_v08.md"
SETTINGS_JSON = REPORTS / "processing_settings_v08.json"


def stable_mseq_music(music: np.ndarray, vocal: np.ndarray, sr: int) -> np.ndarray:
    mid, side = mid_side(music)
    mid_st = np.column_stack([mid, mid]).astype(np.float32)
    side_st = np.column_stack([side, side]).astype(np.float32)
    low = butter_filter(mid_st, sr, "lowpass", 120, 4)
    low_mono = np.mean(low, axis=1)
    mid_body = mid_st - low

    pocket = bandpass(mid_body, sr, 1800, 4200, 3)
    rest = mid_body - pocket
    env = smooth_envelope(np.mean(vocal, axis=1), sr, 140)
    env = env / (np.percentile(env, 97) + 1e-9)
    env = np.clip(env, 0.0, 1.0)
    duck = amp_db(-0.75 * env).astype(np.float32)
    mid_new = np.mean(rest + pocket * duck[:, None], axis=1) + low_mono

    side_st = butter_filter(side_st, sr, "highpass", 140, 3)
    side_st = biquad_peaking(side_st, sr, 3200, 0.25, 1.0)
    side_new = np.mean(side_st, axis=1) * float(amp_db(0.45))
    return from_mid_side(mid_new, side_new)


def drums_stable_punch(y: np.ndarray, sr: int) -> tuple[np.ndarray, list[dict[str, object]]]:
    out = butter_filter(y, sr, "highpass", 24, 3)
    out, stats = dynamic_band_tame(out, sr, 240, 560, 1.2, 77, 95)
    out = biquad_peaking(out, sr, 65, 0.9, 0.9)
    out = biquad_peaking(out, sr, 3600, 0.45, 1.0)
    out = compressor(out, sr, threshold_db=-18.3, ratio=2.0, smooth_ms=85, makeup_db=1.0)
    out = saturate(out, drive_db=2.3, mix=0.18)
    out = soft_clip(out, drive_db=1.0, ceiling=0.90)
    out = limiter(out, -2.0)
    return out.astype(np.float32), [
        {"stage": "no_gate_drum_cleanup", "note": "no noise gate to avoid beat cut"},
        {"stage": "drum_low_mid_cleanup", **stats},
        {"stage": "punch_comp_sat_clip", "ratio": 2.0, "sat_drive_db": 2.3},
    ]


def bass_stable_grit(y: np.ndarray, drums: np.ndarray, sr: int) -> tuple[np.ndarray, list[dict[str, object]]]:
    out, moves = process_bass_grit(y, drums, sr)
    low = butter_filter(out, sr, "lowpass", 115, 4)
    low_mono = np.mean(low, axis=1)
    mid = bandpass(out, sr, 115, 850, 3)
    mid = saturate(mid, drive_db=4.2, mix=0.30)
    out = np.column_stack([low_mono, low_mono]).astype(np.float32) + mid * float(amp_db(0.8))
    out = compressor(out, sr, threshold_db=-19.2, ratio=1.8, smooth_ms=110, makeup_db=0.8)
    out = limiter(out, -2.0)
    moves.append({"stage": "stable_bass_grit_no_gate", "drive_db": 4.2, "note": "no gate to avoid low-end dropouts"})
    return out.astype(np.float32), moves


def female_adlib_layers(female_source: np.ndarray, phrase_events: list[dict[str, float]], sr: int, length: int) -> tuple[np.ndarray, list[dict[str, object]]]:
    src = pad_or_trim(female_source, length)
    src = butter_filter(src, sr, "highpass", 155, 3)
    src, _ = dynamic_band_tame(src, sr, 2500, 6200, 1.7, 74, 85)
    src, _ = dynamic_band_tame(src, sr, 5600, 9600, 2.6, 67, 45)
    src = biquad_shelf(src, sr, 9400, -0.8, True)

    bed_left = pan_stereo(delay_samples(src, int(sr * 0.014)), -0.56)
    bed_right = pan_stereo(delay_samples(src, int(sr * 0.026)), 0.56)
    bed = (bed_left + bed_right) * float(amp_db(-12.2))
    bed = ms_width(bed, 1.4)

    adlibs = np.zeros((length, 2), dtype=np.float32)
    events: list[dict[str, object]] = []
    selected = phrase_events[:18]
    for idx, event in enumerate(selected):
        center = int(float(event["time_s"]) * sr)
        start = max(center - int(0.56 * sr), 0)
        end = min(center + int(0.34 * sr), length)
        if end - start <= int(0.14 * sr):
            continue
        seg = src[start:end].copy()
        seg *= fade_window(len(seg), int(0.03 * sr))[:, None]
        pan = -0.46 if idx % 2 == 0 else 0.46
        adlibs[start:end] += pan_stereo(seg, pan) * float(amp_db(-1.4))
        adlibs[start:end] += pan_stereo(delay_samples(seg, int(sr * 0.018)), -pan) * float(amp_db(-6.0))
        events.append({"time_s": round(start / sr, 3), "type": "female adlib/double layer", "pan": pan, "gain_db": -1.4})
    adlibs = biquad_shelf(adlibs, sr, 9300, -0.7, True)
    adlibs = ms_width(adlibs, 1.7)
    return (bed + adlibs).astype(np.float32), events


def write_report(rows: list[dict[str, object]], phrase_events: list[dict[str, object]], female_events: list[dict[str, object]]) -> None:
    lines = [
        "# v08 Clear Main No Beat Cut LUFS6",
        "",
        "- Beat cutting fixed by removing drum/bass gates.",
        "- Male vocal is mono center, louder and clearer.",
        "- Female vocal is only low support bed + phrase adlib/double layers, not the main.",
        "- Target loudness pushed to around -6 LUFS.",
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

    male_lead, male_moves = male_human_tone_v07(male["lead_vocal"], sr)
    male_lead = mono_center(male_lead) * float(amp_db(2.2))
    male_back, male_back_moves = process_vocal("backing_vocal", male["backing_vocal"], sr)
    male_back = mono_center(male_back) * float(amp_db(-5.5))
    male_vocal = male_lead + male_back

    phrase_endings = detect_phrase_endings(male_vocal, sr)
    phrase_events = select_phrase_events(phrase_endings)

    female_lead, female_lead_moves = process_vocal("backing_vocal", female["female_lead_source"], sr)
    female_back, female_back_moves = process_vocal("backing_vocal", female["female_backing_source"], sr)
    female_src = female_lead * float(amp_db(0.2)) + female_back * float(amp_db(-1.4))
    female_src = compressor(female_src, sr, -28.5, 2.0, 78, 0.2)
    female_layers, female_events = female_adlib_layers(female_src, phrase_events, sr, length)

    processed: dict[str, np.ndarray] = {}
    moves: dict[str, object] = {}
    processed["drums"], moves["drums"] = drums_stable_punch(male["drums"], sr)
    processed["bass"], moves["bass"] = bass_stable_grit(male["bass"], male["drums"], sr)
    for role in ["keys", "percussion", "synth", "other"]:
        instrument_role = "other" if role == "percussion" else role
        out, role_moves = process_instrument(instrument_role, male[role], sr, drums=None, vocal=male_vocal if role in {"keys", "percussion", "synth", "other"} else None)
        processed[role] = out
        moves[role] = role_moves

    music = (
        processed["drums"] * float(amp_db(1.8))
        + processed["bass"] * float(amp_db(1.4))
        + processed["keys"] * float(amp_db(-0.4))
        + processed["percussion"] * float(amp_db(-2.5))
        + processed["synth"] * float(amp_db(-0.4))
        + processed["other"] * float(amp_db(-0.5))
    )
    music = stable_mseq_music(music, male_vocal, sr)

    reverb = reverb_send(male_vocal * float(amp_db(-2.0)) + female_layers * float(amp_db(-1.4)), sr, 1.45, -20.2, 48, 230, 7200, 808)
    reverb = sidechain_duck_full(reverb, male_vocal, sr, 10.0, 420, 54)
    throw_gate = make_throw_gate(length, sr, phrase_events, pre_ms=260, post_ms=150, fade_ms=22)
    delay_src = (female_layers * float(amp_db(0.8))) * throw_gate[:, None]
    delay_fx = delay_throw(delay_src, sr, 322.6, 0.24, -17.0, 280, 5700, True)
    delay_fx = sidechain_duck_full(delay_fx, male_vocal, sr, 11.0, 360, 54)

    mix = music + male_vocal + female_layers + reverb + delay_fx
    mix = limiter(mix * float(amp_db(-5.4)), -3.0)
    premaster = master_tone(mix, sr)
    premaster_wav = INTERMEDIATE / "v08_premaster_float.wav"
    write_float_wav(premaster_wav, sr, premaster)
    render_conditioned_master(premaster_wav, OUT_WAV, "v08_clear_main_lufs6", -6.0, drive_db=2.2, ceiling=0.66)
    convert_mp3(OUT_WAV, OUT_MP3)
    rows = [audio_metrics(OUT_WAV, "v08_lufs6"), audio_metrics(OUT_MP3, "v08_preview_mp3")]
    write_csv(REPORTS / "render_audit_v08.csv", rows)
    settings = {
        "direction": "fix v07 beat cuts; clear centered male main; female only adlib/double layers; target -6 LUFS",
        "male_moves": male_moves + [{"stage": "male_level_up", "gain_db": 2.2}, {"stage": "male_back_center_low", "gain_db": -5.5}],
        "female_moves": {"lead": female_lead_moves, "backing": female_back_moves, "events": female_events},
        "instrument_moves": moves,
        "mseq": {"music_pocket": "stable M/S pocket only, max 0.75 dB mid duck, no hard cuts", "low_end": "under 120 Hz kept mono/center"},
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

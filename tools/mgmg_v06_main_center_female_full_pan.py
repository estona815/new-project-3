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
    soft_clip,
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


WORK = ROOT / "mgmg_mashup_v06_work"
MALE_STEMS = WORK / "male_main_stems"
FEMALE_STEMS = WORK / "female_full_pan_stems"
INTERMEDIATE = WORK / "intermediate"
OUTPUT = ROOT / "output"
REPORTS = ROOT / "reports"

OUT_WAV = OUTPUT / "mgmg_mashup_v06_main_center_female_full_pan_loud_24-48.wav"
OUT_MP3 = OUTPUT / "mgmg_mashup_v06_main_center_female_full_pan_preview_320.mp3"
REPORT_MD = REPORTS / "audio_audit_v06.md"
SETTINGS_JSON = REPORTS / "processing_settings_v06.json"


def mono_center(y: np.ndarray) -> np.ndarray:
    mono = np.mean(y, axis=1)
    return np.column_stack([mono, mono]).astype(np.float32)


def full_width_female_layers(female_source: np.ndarray, phrase_events: list[dict[str, float]], sr: int, length: int) -> tuple[np.ndarray, np.ndarray, list[dict[str, object]]]:
    source = pad_or_trim(female_source, length)
    source = butter_filter(source, sr, "highpass", 150, 3)
    source, _ = dynamic_band_tame(source, sr, 2400, 6200, 1.8, 73, 85)
    source, _ = dynamic_band_tame(source, sr, 5600, 9600, 2.8, 67, 45)
    source = biquad_shelf(source, sr, 9200, -0.9, high=True)

    left = pan_stereo(delay_samples(source, int(sr * 0.012)), -0.78)
    right = pan_stereo(delay_samples(source, int(sr * 0.024)), 0.78)
    wide_bed = (left + right) * float(amp_db(-7.2))
    wide_bed = ms_width(wide_bed, 2.7)

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
            pan = -0.70 if idx % 2 == 0 else 0.70
            emphasis[start:end] += pan_stereo(seg, pan) * float(amp_db(0.8))
            emphasis[start:end] += pan_stereo(delay_samples(seg, int(sr * 0.018)), -pan) * float(amp_db(-4.0))
            events.append({"time_s": round(start / sr, 3), "type": "female full phrase overlap", "pan": pan, "gain_db": 0.8})

        chop_len = int((0.095 + 0.018 * (idx % 3)) * sr)
        chop_start = max(center - int(0.24 * sr), 0)
        if chop_start + chop_len >= length:
            continue
        chop = source[chop_start : chop_start + chop_len].copy()
        chop = butter_filter(chop, sr, "highpass", 250, 2)
        chop = butter_filter(chop, sr, "lowpass", 7400, 2)
        chop = saturate(chop, 2.2, 0.16)
        chop *= fade_window(len(chop), int(0.010 * sr))[:, None]
        repeats = 2 + (1 if idx % 3 == 0 or event.get("long_tail") else 0)
        for repeat in range(repeats):
            place = center + int((0.07 + repeat * sixteenth * 0.86) * sr)
            if place + chop_len >= length:
                continue
            piece = chop[::-1] if repeat == 1 and idx % 2 == 0 else chop
            pan = -0.64 if (idx + repeat) % 2 == 0 else 0.64
            gain_db = -2.6 - repeat * 0.9
            emphasis[place : place + chop_len] += pan_stereo(piece, pan) * float(amp_db(gain_db))
            events.append({"time_s": round(place / sr, 3), "type": "female vocal chop", "pan": pan, "gain_db": round(gain_db, 2), "reversed": bool(repeat == 1 and idx % 2 == 0)})

    emphasis = biquad_peaking(emphasis, sr, 3000, 0.4, 1.0)
    emphasis = biquad_shelf(emphasis, sr, 9300, -0.8, high=True)
    emphasis = ms_width(emphasis, 2.4)
    return wide_bed.astype(np.float32), emphasis.astype(np.float32), events


def write_report(rows: list[dict[str, object]], phrase_events: list[dict[str, object]], female_events: list[dict[str, object]]) -> None:
    lines = [
        "# v06 main center female full pan",
        "",
        "## Direction",
        "- Male main vocal and male backing are mono-centered. No lead panning.",
        "- Full female lead/backing vocal is used as left/right panned layers across the song.",
        "- Verse/phrase endings get extra female overlap, response chops, and ducked throws.",
        "",
        "## Metrics",
        "| label | file | LUFS | TP | LRA | corr | side_mid |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(f"| {row['label']} | {row['file']} | {row.get('integrated_lufs')} | {row.get('true_peak_dbfs')} | {row.get('lra_lu')} | {row.get('stereo_corr')} | {row.get('side_mid_db')} |")
    lines.extend(
        [
            "",
            "## Event Counts",
            f"- Phrase events used: {len(phrase_events)}",
            f"- Female overlap/chop events: {len(female_events)}",
        ]
    )
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    for directory in [WORK, MALE_STEMS, FEMALE_STEMS, INTERMEDIATE, OUTPUT, REPORTS]:
        directory.mkdir(parents=True, exist_ok=True)
    extract_zip(MALE_ZIP, MALE_STEMS)
    extract_zip(FEMALE_ZIP, FEMALE_STEMS)

    male, sr, _male_rows = load_stems(MALE_STEMS, MALE_ROLE_MAP)
    length = max(len(y) for y in male.values())
    female, female_sr, _female_rows = load_stems(FEMALE_STEMS, FEMALE_ROLE_MAP, length=length)
    if female_sr != sr:
        raise RuntimeError("male/female sample rate mismatch")

    base_lead, base_moves = process_vocal("lead_vocal", male["lead_vocal"], sr)
    target_profile = voice_profile("target_raw_male_lead", male["lead_vocal"], sr)
    male_lead, voice_moves = match_voice_tone_v06(base_lead, sr, target_profile, target_profile)
    male_lead = mono_center(male_lead)

    male_back, male_back_moves = process_vocal("backing_vocal", male["backing_vocal"], sr)
    male_back = mono_center(male_back) * float(amp_db(-4.0))
    male_vocal_bus = male_lead + male_back
    phrase_endings = detect_phrase_endings(male_vocal_bus, sr)
    phrase_events = select_phrase_events(phrase_endings)

    female_lead, female_lead_moves = process_vocal("backing_vocal", female["female_lead_source"], sr)
    female_back, female_back_moves = process_vocal("backing_vocal", female["female_backing_source"], sr)
    female_source = female_lead * float(amp_db(1.1)) + female_back * float(amp_db(-0.8))
    female_source = compressor(female_source, sr, -28.0, 2.0, 74, 0.5)
    female_bed, female_emphasis, female_events = full_width_female_layers(female_source, phrase_events, sr, length)

    processed: dict[str, np.ndarray] = {}
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

    dry_music = processed["drums"] + processed["bass"] * float(amp_db(0.2)) + processed["keys"] + processed["percussion"] * float(amp_db(-2.2)) + processed["synth"] + processed["other"]
    vocal_bus = male_vocal_bus + female_bed + female_emphasis * float(amp_db(0.7))

    reverb = reverb_send(male_vocal_bus * float(amp_db(-1.0)) + female_bed * float(amp_db(-1.2)) + female_emphasis * float(amp_db(-1.0)), sr, 1.65, -18.8, 52, 220, 7600, 612)
    reverb = sidechain_duck_full(reverb, male_vocal_bus, sr, 10.0, 430, 54)
    throw_gate = make_throw_gate(length, sr, phrase_events, pre_ms=300, post_ms=180, fade_ms=22)
    throw_src = (female_emphasis * float(amp_db(1.4)) + female_bed * float(amp_db(0.6))) * throw_gate[:, None]
    delay_fx = delay_throw(throw_src, sr, 322.6, 0.28, -15.5, 260, 6200, True)
    delay_fx += delay_throw(throw_src, sr, 241.9, 0.22, -18.5, 300, 5400, False)
    delay_fx = sidechain_duck_full(delay_fx, male_vocal_bus, sr, 11.5, 360, 54)

    mix = dry_music + vocal_bus + reverb + delay_fx
    mix = limiter(mix * float(amp_db(-5.0)), -3.0)
    premaster = master_tone(mix, sr)
    premaster_wav = INTERMEDIATE / "v06_premaster_float.wav"
    write_float_wav(premaster_wav, sr, premaster)
    render_conditioned_master(premaster_wav, OUT_WAV, "v06_main_center_female_full_pan", -8.35, drive_db=1.45, ceiling=0.77)
    convert_mp3(OUT_WAV, OUT_MP3)

    rows = [audio_metrics(OUT_WAV, "v06_loud"), audio_metrics(OUT_MP3, "v06_preview_mp3")]
    write_csv(REPORTS / "render_audit_v06.csv", rows)
    settings = {
        "direction": "male main mono center, all female vocals used as panned layers and phrase-end overlaps",
        "male_moves": {"lead_base": base_moves, "lead_match": voice_moves, "backing": male_back_moves},
        "female_moves": {"lead": female_lead_moves, "backing": female_back_moves},
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

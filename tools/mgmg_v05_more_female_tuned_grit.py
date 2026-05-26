from __future__ import annotations

import csv
import json
import sys
import zipfile
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
    REFERENCE_TRACKS,
    extract_zip,
    fade_window,
    load_stems,
    markdown_table,
    pad_or_trim,
    reference_tone_polish,
    write_csv,
)


WORK = ROOT / "mgmg_mashup_v05_work"
MALE_STEMS = WORK / "male_main_stems"
FEMALE_STEMS = WORK / "female_adlib_stems"
INTERMEDIATE = WORK / "intermediate"
OUTPUT = ROOT / "output"
REPORTS = ROOT / "reports"

CLEAN_WAV = OUTPUT / "mgmg_mashup_v05_more_female_tuned_grit_clean_24-48.wav"
LOUD_WAV = OUTPUT / "mgmg_mashup_v05_more_female_tuned_grit_loud_24-48.wav"
PREVIEW_MP3 = OUTPUT / "mgmg_mashup_v05_preview.mp3"
AUDIT_MD = REPORTS / "audio_audit_v05.md"
SETTINGS_JSON = REPORTS / "processing_settings_v05.json"


def select_dense_adlib_events(phrase_endings: list[dict[str, float]]) -> list[dict[str, float]]:
    candidates = sorted(
        phrase_endings,
        key=lambda e: float(e["confidence"]) + float(e["following_pause_s"]) * 0.42 + (0.45 if e.get("long_tail") else 0.0),
        reverse=True,
    )
    chosen: list[dict[str, float]] = []
    for event in candidates:
        if float(event["time_s"]) < 1.2:
            continue
        if all(abs(float(event["time_s"]) - float(prev["time_s"])) >= 0.92 for prev in chosen):
            chosen.append(event)
        if len(chosen) >= 26:
            break
    return sorted(chosen, key=lambda e: float(e["time_s"]))


def autotune_edge_layer(vocal: np.ndarray, sr: int) -> np.ndarray:
    mid = bandpass(vocal, sr, 220, 4800, 3)
    fast = compressor(mid, sr, threshold_db=-29.0, ratio=4.0, smooth_ms=28, makeup_db=1.1)
    fixed = fast * 0.62 + delay_samples(fast, int(sr * 0.004)) * 0.38
    fixed = vocal_harmonic_density(fixed, sr, drive_db=3.2, wet=0.18)
    fixed, _ = dynamic_band_tame(fixed, sr, 2700, 5600, 1.7, 72, 70)
    fixed, _ = dynamic_band_tame(fixed, sr, 5600, 9400, 2.4, 68, 45)
    fixed = biquad_peaking(fixed, sr, 950, -0.8, 1.0)
    fixed = biquad_peaking(fixed, sr, 2450, 0.9, 0.85)
    fixed = biquad_shelf(fixed, sr, 9800, -0.4, high=True)
    return fixed.astype(np.float32)


def process_male_main_v05(y: np.ndarray, sr: int) -> tuple[np.ndarray, list[dict[str, object]]]:
    lead, moves = process_vocal("lead_vocal", y, sr)
    edge = autotune_edge_layer(lead, sr)
    lead = lead * float(amp_db(0.5)) + edge * float(amp_db(-7.8))
    lead, stats = dynamic_band_tame(lead, sr, 600, 1550, 1.2, 77, 120)
    stats["type"] = "030-ish formant tightening"
    moves.append(stats)
    lead, stats = dynamic_band_tame(lead, sr, 2800, 6200, 1.1, 80, 90)
    stats["type"] = "tuned presence edge control"
    moves.append(stats)
    lead = compressor(lead, sr, threshold_db=-21.5, ratio=2.8, smooth_ms=58, makeup_db=0.7)
    lead = saturate(lead, drive_db=2.2, mix=0.14)
    lead = biquad_peaking(lead, sr, 2600, 0.65, 0.9)
    lead = biquad_shelf(lead, sr, 10500, -0.25, high=True)
    moves.append({"type": "parallel hard-tune sheen", "wet_db": -7.8, "note": "DSP approximation, not real pitch correction"})
    moves.append({"type": "extra front compression/saturation", "ratio": 2.8, "saturation_mix": 0.14})
    return lead.astype(np.float32), moves


def process_bass_grit_v05(y: np.ndarray, drums: np.ndarray, sr: int) -> tuple[np.ndarray, list[dict[str, object]]]:
    bass, moves = process_instrument("bass", y, sr, drums=drums, vocal=None)
    low = butter_filter(bass, sr, "lowpass", 118, 4)
    low_mono = np.mean(low, axis=1)
    mid = bandpass(bass, sr, 118, 900, 3)
    upper = butter_filter(bass - low - mid, sr, "highpass", 900, 2)
    grit = saturate(mid, drive_db=7.0, mix=0.55)
    grit = soft_clip(grit, drive_db=2.4, ceiling=0.72)
    grit = biquad_peaking(grit, sr, 210, 1.1, 0.95)
    grit = biquad_peaking(grit, sr, 620, 1.7, 1.1)
    out = np.column_stack([low_mono, low_mono]).astype(np.float32) + grit * float(amp_db(1.8)) + upper * float(amp_db(-2.0))
    out = limiter(out, -2.0)
    moves.append({"type": "v05 bass grit", "drive_db": 7.0, "mid_band_hz": "118-900", "grit_gain_db": 1.8})
    return out.astype(np.float32), moves


def make_female_layers_v05(
    female_source: np.ndarray,
    phrase_endings: list[dict[str, float]],
    sr: int,
    length: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, list[dict[str, object]], list[dict[str, float]]]:
    female_source = pad_or_trim(female_source, length)
    events = select_dense_adlib_events(phrase_endings)
    bed = chorus_double(female_source, sr)
    bed = butter_filter(bed, sr, "highpass", 150, 3)
    bed, _ = dynamic_band_tame(bed, sr, 2500, 6200, 1.6, 73, 85)
    bed, _ = dynamic_band_tame(bed, sr, 5600, 9600, 2.4, 67, 45)
    bed = biquad_shelf(bed, sr, 9200, -1.1, high=True)
    bed = ms_width(bed, 3.1) * float(amp_db(-10.2))

    adlibs = np.zeros((length, 2), dtype=np.float32)
    chops = np.zeros((length, 2), dtype=np.float32)
    chop_events: list[dict[str, object]] = []
    sixteenth = 60.0 / 186.0 / 4.0
    for idx, event in enumerate(events):
        center = int(float(event["time_s"]) * sr)
        start = max(center - int(0.56 * sr), 0)
        end = min(center + int(0.32 * sr), length)
        if end - start > int(0.13 * sr):
            seg = female_source[start:end].copy()
            seg, _ = dynamic_band_tame(seg, sr, 2600, 6800, 1.3, 72, 70)
            seg *= fade_window(len(seg), int(0.032 * sr))[:, None]
            pan = [-0.72, 0.72, -0.38, 0.38][idx % 4]
            adlibs[start:end] += pan_stereo(seg, pan) * float(amp_db(0.2))
            low_double = delay_samples(seg, int(sr * (0.016 + 0.004 * (idx % 3))))
            adlibs[start:end] += pan_stereo(low_double, -pan * 0.72) * float(amp_db(-5.2))

        chop_start = max(center - int(0.24 * sr), 0)
        chop_len = int((0.088 + 0.018 * (idx % 3)) * sr)
        if chop_start + chop_len >= length:
            continue
        chop = female_source[chop_start : chop_start + chop_len].copy()
        chop = butter_filter(chop, sr, "highpass", 240, 2)
        chop = butter_filter(chop, sr, "lowpass", 7600, 2)
        chop = saturate(chop, drive_db=2.4, mix=0.18)
        chop *= fade_window(len(chop), int(0.01 * sr))[:, None]
        repeats = 2 + (1 if idx % 3 == 0 else 0) + (1 if event.get("long_tail") else 0)
        for repeat in range(repeats):
            place = center + int((0.055 + repeat * sixteenth * 0.82) * sr)
            if place + chop_len >= length:
                continue
            piece = chop[::-1] if repeat == 1 and idx % 2 == 0 else chop
            pan = -0.64 if (idx + repeat) % 2 == 0 else 0.64
            chops[place : place + chop_len] += pan_stereo(piece, pan) * float(amp_db(-2.7 - repeat * 0.8))
            chop_events.append(
                {
                    "source_time_s": round(chop_start / sr, 3),
                    "place_time_s": round(place / sr, 3),
                    "duration_ms": round(chop_len / sr * 1000, 1),
                    "pan": pan,
                    "reversed": bool(repeat == 1 and idx % 2 == 0),
                }
            )
    adlibs = biquad_peaking(adlibs, sr, 3100, -0.25, 1.0)
    adlibs = biquad_shelf(adlibs, sr, 9500, -0.85, high=True)
    adlibs = ms_width(adlibs, 3.0)
    chops = biquad_peaking(chops, sr, 2800, 0.8, 1.0)
    chops = biquad_shelf(chops, sr, 9000, -0.75, high=True)
    chops = ms_width(chops, 2.4)
    return bed.astype(np.float32), adlibs.astype(np.float32), chops.astype(np.float32), chop_events, events


def reference_tone_polish_v05(y: np.ndarray, sr: int) -> np.ndarray:
    out = reference_tone_polish(y, sr)
    out, _ = dynamic_band_tame(out, sr, 700, 1700, 0.7, 78, 150, slope=0.35)
    out, _ = dynamic_band_tame(out, sr, 2600, 6400, 0.75, 82, 110, slope=0.32)
    out = biquad_peaking(out, sr, 52, 0.55, 0.8)
    out = biquad_peaking(out, sr, 155, 0.25, 0.9)
    out = biquad_peaking(out, sr, 720, -0.25, 1.0)
    out = biquad_shelf(out, sr, 11200, -0.25, high=True)
    return out.astype(np.float32)


def write_report(
    render_rows: list[dict[str, object]],
    reference_rows: list[dict[str, object]],
    phrase_endings: list[dict[str, object]],
    adlib_events: list[dict[str, object]],
    chop_events: list[dict[str, object]],
    settings: dict[str, object],
) -> None:
    lines: list[str] = []
    lines.append("# mgmg mashup v05 audit")
    lines.append("")
    lines.append("## Direction")
    lines.append("- Male vocal remains the main lead.")
    lines.append("- Female vocal is now deliberately louder and denser: continuous side double bed, phrase adlibs, response doubles, and vocal chops.")
    lines.append("- Male tone is pushed toward the reference attitude with tighter formant, stronger tuned sheen, more compression/saturation, and less airy glass.")
    lines.append("- Bass is rougher through mid-band saturation/clipping while keeping sub centered.")
    lines.append("")
    lines.append("## Render audit")
    lines.extend(markdown_table(render_rows, ["label", "file", "duration_s", "peak_dbfs", "true_peak_dbfs", "integrated_lufs", "lra_lu", "short_term_lufs_median", "stereo_corr", "side_mid_db"]))
    lines.append("")
    lines.append("## Reference audit")
    lines.extend(markdown_table(reference_rows, ["label", "file", "integrated_lufs", "lra_lu", "true_peak_dbfs", "stereo_corr", "side_mid_db", "sub_20_80_pct", "body_200_500_pct", "presence_1500_5000_pct", "sibilance_5000_10000_pct"]))
    lines.append("")
    lines.append("## Female vocal use")
    lines.append(f"- Phrase endings detected from male vocal: {len(phrase_endings)}")
    lines.append(f"- Female adlib/layer events used: {len(adlib_events)}")
    lines.append(f"- Female chop placements generated: {len(chop_events)}")
    lines.append("- Female bed is a low-level wide double across the song, with sibilance softened.")
    lines.extend(markdown_table(adlib_events[:32], ["time_s", "confidence", "following_pause_s", "long_tail"]))
    lines.append("")
    lines.append("## Limits")
    lines.append("- The tuned male layer is a DSP approximation, not actual note-by-note Auto-Tune/Melodyne.")
    lines.append("- The reference singer identity is not cloned; only mix/tone behavior is approximated.")
    lines.append("- Final subjective balance still needs listening, especially whether female layers are now too loud.")
    AUDIT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    SETTINGS_JSON.write_text(json.dumps(settings, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    for directory in [WORK, MALE_STEMS, FEMALE_STEMS, INTERMEDIATE, OUTPUT, REPORTS]:
        directory.mkdir(parents=True, exist_ok=True)
    extract_zip(MALE_ZIP, MALE_STEMS)
    extract_zip(FEMALE_ZIP, FEMALE_STEMS)

    reference_rows = [audio_metrics(path, path.stem) for path in REFERENCE_TRACKS if path.exists()]
    male, sr, male_rows = load_stems(MALE_STEMS, MALE_ROLE_MAP)
    length = max(len(y) for y in male.values())
    female, female_sr, female_rows = load_stems(FEMALE_STEMS, FEMALE_ROLE_MAP, length=length)
    if female_sr != sr:
        raise RuntimeError("male/female sample-rate mismatch")

    male_lead, male_lead_moves = process_male_main_v05(male["lead_vocal"], sr)
    male_back, male_back_moves = process_vocal("backing_vocal", male["backing_vocal"], sr)
    male_back = chorus_double(male_back, sr) * float(amp_db(-1.2))
    male_vocal_bus = male_lead + male_back * float(amp_db(-2.1))
    phrase_endings = detect_phrase_endings(male_vocal_bus, sr)

    female_lead, female_lead_moves = process_vocal("backing_vocal", female["female_lead_source"], sr)
    female_back, female_back_moves = process_vocal("backing_vocal", female["female_backing_source"], sr)
    female_source = female_lead * float(amp_db(0.7)) + female_back * float(amp_db(-1.2))
    female_source = compressor(female_source, sr, -28.0, 2.2, 72, 0.4)
    female_bed, female_adlibs, female_chops, chop_events, adlib_events = make_female_layers_v05(female_source, phrase_endings, sr, length)

    processed: dict[str, np.ndarray] = {
        "lead_vocal": male_lead,
        "backing_vocal": male_back,
        "female_bed": female_bed,
        "female_adlibs": female_adlibs,
        "female_chops": female_chops,
    }
    drums_ref = male["drums"]
    instrument_moves: dict[str, list[dict[str, object]]] = {}
    for role in ["drums", "keys", "percussion", "synth", "other"]:
        instrument_role = "other" if role == "percussion" else role
        out, role_moves = process_instrument(
            instrument_role,
            male[role],
            sr,
            drums=None,
            vocal=male_vocal_bus if role in {"keys", "percussion", "synth", "other"} else None,
        )
        processed[role] = out
        instrument_moves[role] = role_moves
    processed["bass"], bass_moves = process_bass_grit_v05(male["bass"], drums_ref, sr)
    instrument_moves["bass"] = bass_moves

    dry_music = (
        processed["drums"]
        + processed["bass"] * float(amp_db(0.4))
        + processed["keys"]
        + processed["percussion"] * float(amp_db(-2.1))
        + processed["synth"]
        + processed["other"]
    )
    vocal_bus = (
        male_lead
        + male_back * float(amp_db(-1.8))
        + female_bed
        + female_adlibs * float(amp_db(1.7))
        + female_chops * float(amp_db(1.2))
    )

    fx_trigger = male_vocal_bus
    reverb_main = reverb_send(male_vocal_bus + female_bed * float(amp_db(-2.5)) + female_adlibs * float(amp_db(-1.5)), sr, 1.55, -18.5, 48, 220, 7300, 275)
    reverb_main = sidechain_duck_full(reverb_main, fx_trigger, sr, 10.0, 410, 54)
    throw_gate = make_throw_gate(length, sr, adlib_events, pre_ms=285, post_ms=160, fade_ms=20)
    throw_src = (male_vocal_bus * float(amp_db(-3.5)) + female_adlibs * float(amp_db(1.2)) + female_chops * float(amp_db(2.0))) * throw_gate[:, None]
    delay_fx = delay_throw(throw_src, sr, 322.6, 0.28, -15.6, 260, 6200, pingpong=True)
    delay_fx += delay_throw(throw_src, sr, 241.9, 0.22, -18.2, 300, 5400, pingpong=False)
    delay_fx = sidechain_duck_full(delay_fx, fx_trigger, sr, 11.5, 360, 54)
    long_gate = make_throw_gate(length, sr, [e for e in adlib_events if e.get("long_tail") or float(e["confidence"]) > 0.72], pre_ms=340, post_ms=180, fade_ms=34)
    long_tail = reverb_send((female_adlibs * float(amp_db(1.0)) + female_chops * float(amp_db(0.5)) + male_vocal_bus * float(amp_db(-6.0))) * long_gate[:, None], sr, 3.25, -23.5, 68, 270, 6300, 311)
    long_tail = sidechain_duck_full(long_tail, fx_trigger, sr, 11.0, 650, 54)

    mix = dry_music + vocal_bus + reverb_main + delay_fx + long_tail
    mix = limiter(mix * float(amp_db(-4.9)), -3.0)
    polished = reference_tone_polish_v05(master_bus_polish(mix, sr), sr)
    temp_mix = INTERMEDIATE / "mgmg_v05_premaster_float.wav"
    write_float_wav(temp_mix, sr, polished)
    render_conditioned_master(temp_mix, CLEAN_WAV, "v05_clean", -9.5, drive_db=1.0, ceiling=0.82)
    render_conditioned_master(temp_mix, LOUD_WAV, "v05_loud", -8.3, drive_db=1.45, ceiling=0.77)
    convert_mp3(LOUD_WAV, PREVIEW_MP3)

    render_rows = [
        audio_metrics(CLEAN_WAV, "v05_clean"),
        audio_metrics(LOUD_WAV, "v05_loud"),
        audio_metrics(PREVIEW_MP3, "v05_preview_mp3"),
    ]
    write_csv(REPORTS / "render_audit_v05.csv", render_rows)
    write_csv(REPORTS / "reference_audit_v05.csv", reference_rows)
    write_csv(REPORTS / "male_stem_audit_v05.csv", male_rows)
    write_csv(REPORTS / "female_source_stem_audit_v05.csv", female_rows)
    settings = {
        "direction": "v05: more female doubling/adlibs/layers/chops, more tuned male tone, rougher bass grit",
        "male_zip": str(MALE_ZIP),
        "female_zip": str(FEMALE_ZIP),
        "references": [str(path) for path in REFERENCE_TRACKS],
        "reference_metrics": reference_rows,
        "targets": {"clean_lufs": -9.5, "loud_lufs": -8.3, "true_peak_dbtp": -1.2, "sample_rate": 48000, "bit_depth": 24},
        "male_vocal_moves": {"lead": male_lead_moves, "backing": male_back_moves},
        "female_vocal_moves": {"lead_source_processed_as_backing": female_lead_moves, "backing_source": female_back_moves},
        "instrument_moves": instrument_moves,
        "phrase_endings": phrase_endings,
        "adlib_events": adlib_events,
        "chop_events": chop_events,
        "render_metrics": render_rows,
        "limits": "No identity cloning; tuned layer is a DSP approximation, not real Auto-Tune note correction.",
    }
    write_report(render_rows, reference_rows, phrase_endings, adlib_events, chop_events, settings)
    print(CLEAN_WAV)
    print(LOUD_WAV)
    print(PREVIEW_MP3)
    print(AUDIT_MD)
    print(SETTINGS_JSON)


if __name__ == "__main__":
    main()

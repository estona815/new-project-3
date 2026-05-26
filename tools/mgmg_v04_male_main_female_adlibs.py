from __future__ import annotations

import csv
import json
import math
import sys
import zipfile
from pathlib import Path

import numpy as np

ROOT = Path("/Users/hantaeheuk/Documents/New project 3")
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.mgmg_v03_human_vocal_dynamic_fx import (
    FFMPEG,
    amp_db,
    audio_metrics,
    biquad_peaking,
    biquad_shelf,
    butter_filter,
    chorus_double,
    compressor,
    convert_mp3,
    detect_phrase_endings,
    delay_throw,
    dynamic_band_tame,
    ffmpeg_loudnorm,
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
    sidechain_duck_full,
    stem_metrics,
    write_float_wav,
)


MALE_ZIP = Path("/Users/hantaeheuk/Downloads/ㅁㄱㅁㄱ x ㅁㄱㅁㄱ (Mashup) Stems.zip")
FEMALE_ZIP = Path("/Users/hantaeheuk/Downloads/ㅁㄱㅁㄱ x ㅁㄱㅁㄱ (Mashup) Stems (1).zip")
WORK = ROOT / "mgmg_mashup_v04_work"
MALE_STEMS = WORK / "male_main_stems"
FEMALE_STEMS = WORK / "female_adlib_stems"
INTERMEDIATE = WORK / "intermediate"
OUTPUT = ROOT / "output"
REPORTS = ROOT / "reports"

CLEAN_WAV = OUTPUT / "mgmg_mashup_v04_male_main_female_adlibs_clean_24-48.wav"
LOUD_WAV = OUTPUT / "mgmg_mashup_v04_male_main_female_adlibs_loud_24-48.wav"
PREVIEW_MP3 = OUTPUT / "mgmg_mashup_v04_preview.mp3"
AUDIT_MD = REPORTS / "audio_audit_v04.md"
SETTINGS_JSON = REPORTS / "processing_settings_v04.json"
REFERENCE_TRACKS = [
    Path("/Users/hantaeheuk/Desktop/[YG PLUS] 20260508_Estona_!0!/2_음원 (최종 마스터)/3_MP3_320kbps/Am i 5u5ide? 320kbps.mp3"),
    Path("/Users/hantaeheuk/Desktop/[YG PLUS] 20260508_Estona_!0!/2_음원 (최종 마스터)/3_MP3_320kbps/030 320kbps.mp3"),
    Path("/Users/hantaeheuk/Desktop/[YG PLUS] 20260508_Estona_!0!/2_음원 (최종 마스터)/3_MP3_320kbps/00 320kbps.mp3"),
]

MALE_ROLE_MAP = {
    "0 Lead Vocals.wav": "lead_vocal",
    "1 Backing Vocals.wav": "backing_vocal",
    "2 Drums.wav": "drums",
    "3 Bass.wav": "bass",
    "4 Keyboard.wav": "keys",
    "5 Percussion.wav": "percussion",
    "6 Synth.wav": "synth",
    "7 Other.wav": "other",
}

FEMALE_ROLE_MAP = {
    "0 Lead Vocals.wav": "female_lead_source",
    "1 Backing Vocals.wav": "female_backing_source",
}


def extract_zip(src: Path, dst: Path) -> None:
    dst.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(src) as zf:
        for member in zf.infolist():
            name = Path(member.filename)
            if "__MACOSX" in name.parts or name.name.startswith("._"):
                continue
            zf.extract(member, dst)


def pad_or_trim(y: np.ndarray, length: int) -> np.ndarray:
    if len(y) == length:
        return y
    if len(y) > length:
        return y[:length]
    return np.pad(y, ((0, length - len(y)), (0, 0))).astype(np.float32)


def fade_window(length: int, fade: int) -> np.ndarray:
    window = np.ones(length, dtype=np.float32)
    fade = max(1, min(fade, length // 2))
    window[:fade] *= np.linspace(0.0, 1.0, fade, dtype=np.float32)
    window[-fade:] *= np.linspace(1.0, 0.0, fade, dtype=np.float32)
    return window


def select_adlib_events(phrase_endings: list[dict[str, float]]) -> list[dict[str, float]]:
    candidates = [e for e in phrase_endings if e.get("throw")]
    if not candidates:
        candidates = phrase_endings
    ranked = sorted(
        candidates,
        key=lambda e: float(e["confidence"]) + float(e["following_pause_s"]) * 0.35 + (0.35 if e.get("long_tail") else 0.0),
        reverse=True,
    )
    chosen: list[dict[str, float]] = []
    for event in ranked:
        if all(abs(float(event["time_s"]) - float(prev["time_s"])) >= 1.55 for prev in chosen):
            chosen.append(event)
        if len(chosen) >= 16:
            break
    return sorted(chosen, key=lambda e: float(e["time_s"]))


def make_female_layers(
    female_source: np.ndarray,
    phrase_endings: list[dict[str, float]],
    sr: int,
    length: int,
) -> tuple[np.ndarray, np.ndarray, list[dict[str, object]]]:
    female_source = pad_or_trim(female_source, length)
    events = select_adlib_events(phrase_endings)
    adlibs = np.zeros((length, 2), dtype=np.float32)
    chops = np.zeros((length, 2), dtype=np.float32)
    chop_events: list[dict[str, object]] = []
    sixteenth = 60.0 / 186.0 / 4.0
    for idx, event in enumerate(events):
        center = int(float(event["time_s"]) * sr)
        start = max(center - int(0.48 * sr), 0)
        end = min(center + int(0.24 * sr), length)
        if end - start > int(0.12 * sr):
            seg = female_source[start:end].copy()
            seg *= fade_window(len(seg), int(0.035 * sr))[:, None]
            pan = -0.64 if idx % 2 == 0 else 0.64
            adlibs[start:end] += pan_stereo(seg, pan) * float(amp_db(-2.0))
        if idx % 2 == 0 or event.get("long_tail"):
            chop_start = max(center - int(0.20 * sr), 0)
            chop_len = int(0.105 * sr)
            if chop_start + chop_len < length:
                chop = female_source[chop_start : chop_start + chop_len].copy()
                chop = butter_filter(chop, sr, "highpass", 260, 2)
                chop = butter_filter(chop, sr, "lowpass", 7200, 2)
                chop *= fade_window(len(chop), int(0.012 * sr))[:, None]
                repeats = 2 + (1 if event.get("long_tail") else 0)
                for repeat in range(repeats):
                    place = center + int((0.08 + repeat * sixteenth) * sr)
                    if place + chop_len >= length:
                        continue
                    piece = chop[::-1] if repeat == 1 and idx % 4 == 0 else chop
                    pan = -0.52 if (idx + repeat) % 2 == 0 else 0.52
                    chops[place : place + chop_len] += pan_stereo(piece, pan) * float(amp_db(-4.8 - repeat * 1.0))
                    chop_events.append(
                        {
                            "source_time_s": round(chop_start / sr, 3),
                            "place_time_s": round(place / sr, 3),
                            "duration_ms": round(chop_len / sr * 1000, 1),
                            "pan": pan,
                            "reversed": bool(repeat == 1 and idx % 4 == 0),
                        }
                    )
    adlibs = butter_filter(adlibs, sr, "highpass", 145, 3)
    adlibs = biquad_peaking(adlibs, sr, 3200, -0.8, 1.1)
    adlibs = biquad_shelf(adlibs, sr, 9100, -0.95, high=True)
    adlibs = ms_width(adlibs, 2.6)
    chops = biquad_peaking(chops, sr, 2800, 0.7, 1.2)
    chops = biquad_shelf(chops, sr, 8500, -0.8, high=True)
    chops = ms_width(chops, 1.8)
    return adlibs.astype(np.float32), chops.astype(np.float32), chop_events


def reference_tone_polish(y: np.ndarray, sr: int) -> np.ndarray:
    out = y.copy()
    out, _ = dynamic_band_tame(out, sr, 520, 1450, 0.9, 79, 165, slope=0.42)
    out, _ = dynamic_band_tame(out, sr, 2400, 6200, 0.65, 82, 105, slope=0.34)
    out = biquad_peaking(out, sr, 58, 0.35, 0.85)
    out = biquad_peaking(out, sr, 950, -0.35, 1.0)
    out = biquad_shelf(out, sr, 10500, -0.18, high=True)
    return out.astype(np.float32)


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


def markdown_table(rows: list[dict[str, object]], keys: list[str]) -> list[str]:
    lines = ["| " + " | ".join(keys) + " |", "| " + " | ".join(["---"] * len(keys)) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(str(row.get(key, "")) for key in keys) + " |")
    return lines


def write_report(
    render_rows: list[dict[str, object]],
    reference_rows: list[dict[str, object]],
    male_stem_rows: list[dict[str, object]],
    female_stem_rows: list[dict[str, object]],
    phrase_endings: list[dict[str, object]],
    adlib_events: list[dict[str, object]],
    chop_events: list[dict[str, object]],
    settings: dict[str, object],
) -> None:
    lines: list[str] = []
    lines.append("# mgmg mashup v04 audit")
    lines.append("")
    lines.append("## Direction correction")
    lines.append("- Male vocal from the earlier stem zip is the main vocal foundation.")
    lines.append("- Female vocal from the newer `(1)` zip is used only as adlibs, phrase-end layers, and occasional vocal chops.")
    lines.append("- Female drums/bass/music stems from the newer zip were not used.")
    lines.append("")
    lines.append("## Render audit")
    lines.extend(markdown_table(render_rows, ["label", "file", "duration_s", "peak_dbfs", "true_peak_dbfs", "integrated_lufs", "lra_lu", "short_term_lufs_median", "stereo_corr", "side_mid_db"]))
    lines.append("")
    lines.append("## Reference audit")
    lines.extend(markdown_table(reference_rows, ["label", "file", "integrated_lufs", "lra_lu", "true_peak_dbfs", "stereo_corr", "side_mid_db", "sub_20_80_pct", "body_200_500_pct", "formant_500_1500_pct", "presence_1500_5000_pct", "sibilance_5000_10000_pct", "air_10000_16000_pct"]))
    lines.append("")
    lines.append("## Male main stems")
    lines.extend(markdown_table(male_stem_rows, ["file", "role", "duration_s", "peak_dbfs", "rms_dbfs", "stereo_corr", "side_mid_db"]))
    lines.append("")
    lines.append("## Female source stems")
    lines.extend(markdown_table(female_stem_rows, ["file", "role", "duration_s", "peak_dbfs", "rms_dbfs", "stereo_corr", "side_mid_db"]))
    lines.append("")
    lines.append("## Vocal routing")
    lines.append("- Male lead: cleanup, dynamic de-harsh/de-ess, light saturation, 1176/LA-style controlled compression, front position.")
    lines.append("- Male backing: tucked support under the male lead.")
    lines.append("- Female adlib/layer bus: phrase-end gated, alternating left/right pan, filtered and softened so it does not replace the lead.")
    lines.append("- Female chop bus: selected short 105 ms snippets after important phrase endings, alternating pan, some reverse chops, filtered 260 Hz-7.2 kHz.")
    lines.append("- FX returns are ducked from the male vocal bus, so reverb/delay should bloom after lines instead of covering the main vocal.")
    lines.append("- Reference response: sub/low-end density and restrained air were used as the tonal guide; unsafe positive true peaks in the MP3 references were not copied.")
    lines.append("")
    lines.append("## Phrase/adlib selection")
    lines.append(f"- Phrase endings detected from male vocal: {len(phrase_endings)}")
    lines.append(f"- Female adlib/layer events used: {len(adlib_events)}")
    lines.append(f"- Female chop placements generated: {len(chop_events)}")
    lines.extend(markdown_table(adlib_events[:24], ["time_s", "confidence", "following_pause_s", "long_tail"]))
    lines.append("")
    lines.append("## QC notes")
    lines.append("- Stem separation was not needed because both male and female vocal stems were available.")
    lines.append("- Clean/loud masters are true-peak-safe and non-destructive; v03 files were not overwritten.")
    lines.append("- This is a measured DSP render. Final call still needs playback listening for whether female chops are too frequent or too quiet.")
    AUDIT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    SETTINGS_JSON.write_text(json.dumps(settings, ensure_ascii=False, indent=2), encoding="utf-8")


def load_stems(folder: Path, role_map: dict[str, str], length: int | None = None) -> tuple[dict[str, np.ndarray], int, list[dict[str, object]]]:
    loaded: dict[str, np.ndarray] = {}
    rows: list[dict[str, object]] = []
    sr_ref: int | None = None
    max_len = 0
    raw: dict[str, tuple[np.ndarray, str, str]] = {}
    for path in sorted(folder.glob("*.wav")):
        if path.name not in role_map:
            continue
        sr, y, dtype_name = read_wav(path)
        if sr_ref is None:
            sr_ref = sr
        if sr != sr_ref:
            raise RuntimeError(f"sample-rate mismatch: {path}")
        role = role_map[path.name]
        raw[role] = (y, dtype_name, path.name)
        max_len = max(max_len, len(y))
    if sr_ref is None:
        raise RuntimeError(f"no stems in {folder}")
    target_len = length or max_len
    for role, (y, dtype_name, name) in raw.items():
        y = pad_or_trim(y, target_len)
        loaded[role] = y
        rows.append(stem_metrics(name, role, y, sr_ref, dtype_name))
    return loaded, sr_ref, rows


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

    male_lead, male_lead_moves = process_vocal("lead_vocal", male["lead_vocal"], sr)
    male_back, male_back_moves = process_vocal("backing_vocal", male["backing_vocal"], sr)
    male_back = chorus_double(male_back, sr) * float(amp_db(-1.5))
    male_vocal_bus = male_lead + male_back * float(amp_db(-2.5))
    phrase_endings = detect_phrase_endings(male_vocal_bus, sr)

    female_lead, female_lead_moves = process_vocal("backing_vocal", female["female_lead_source"], sr)
    female_back, female_back_moves = process_vocal("backing_vocal", female["female_backing_source"], sr)
    female_source = female_lead + female_back * float(amp_db(-2.0))
    female_source = compressor(female_source, sr, -28.0, 2.0, 80, 0.0)
    female_adlibs, female_chops, chop_events = make_female_layers(female_source, phrase_endings, sr, length)
    adlib_events = select_adlib_events(phrase_endings)

    processed: dict[str, np.ndarray] = {
        "lead_vocal": male_lead,
        "backing_vocal": male_back,
        "female_adlibs": female_adlibs,
        "female_chops": female_chops,
    }
    drums_ref = male["drums"]
    for role in ["drums", "bass", "keys", "percussion", "synth", "other"]:
        instrument_role = "other" if role == "percussion" else role
        out, _moves = process_instrument(
            instrument_role,
            male[role],
            sr,
            drums=drums_ref if role == "bass" else None,
            vocal=male_vocal_bus if role in {"keys", "percussion", "synth", "other"} else None,
        )
        processed[role] = out

    dry_music = processed["drums"] + processed["bass"] + processed["keys"] + processed["percussion"] * float(amp_db(-2.0)) + processed["synth"] + processed["other"]
    vocal_bus = (
        male_lead
        + male_back * float(amp_db(-2.0))
        + female_adlibs * float(amp_db(0.4))
        + female_chops * float(amp_db(-0.7))
    )

    reverb_main = reverb_send(male_vocal_bus + female_adlibs * float(amp_db(-3.0)), sr, 1.55, -19.0, 48, 210, 7600, 174)
    reverb_main = sidechain_duck_full(reverb_main, male_vocal_bus, sr, 10.5, 430, 54)
    throw_gate = make_throw_gate(length, sr, adlib_events, pre_ms=250, post_ms=130, fade_ms=22)
    throw_src = (male_vocal_bus * float(amp_db(-2.0)) + female_adlibs + female_chops * float(amp_db(1.2))) * throw_gate[:, None]
    delay_fx = delay_throw(throw_src, sr, 322.6, 0.25, -17.0, 260, 6100, pingpong=True)
    delay_fx += delay_throw(throw_src, sr, 241.9, 0.18, -20.0, 290, 5200, pingpong=False)
    delay_fx = sidechain_duck_full(delay_fx, male_vocal_bus, sr, 12.0, 370, 54)
    long_gate = make_throw_gate(length, sr, [e for e in adlib_events if e.get("long_tail")], pre_ms=330, post_ms=170, fade_ms=36)
    long_tail = reverb_send((female_adlibs + male_vocal_bus * float(amp_db(-5.0))) * long_gate[:, None], sr, 3.2, -24.5, 66, 260, 6400, 211)
    long_tail = sidechain_duck_full(long_tail, male_vocal_bus, sr, 11.0, 650, 54)

    mix = dry_music + vocal_bus + reverb_main + delay_fx + long_tail
    mix = limiter(mix * float(amp_db(-4.7)), -3.0)
    polished = reference_tone_polish(master_bus_polish(mix, sr), sr)
    temp_mix = INTERMEDIATE / "mgmg_v04_premaster_float.wav"
    write_float_wav(temp_mix, sr, polished)
    render_conditioned_master(temp_mix, CLEAN_WAV, "v04_clean", -9.7, drive_db=0.9, ceiling=0.82)
    render_conditioned_master(temp_mix, LOUD_WAV, "v04_loud", -8.5, drive_db=1.35, ceiling=0.78)
    convert_mp3(LOUD_WAV, PREVIEW_MP3)

    render_rows = [
        audio_metrics(CLEAN_WAV, "v04_clean"),
        audio_metrics(LOUD_WAV, "v04_loud"),
        audio_metrics(PREVIEW_MP3, "v04_preview_mp3"),
    ]
    write_csv(REPORTS / "render_audit_v04.csv", render_rows)
    write_csv(REPORTS / "reference_audit_v04.csv", reference_rows)
    write_csv(REPORTS / "male_stem_audit_v04.csv", male_rows)
    write_csv(REPORTS / "female_source_stem_audit_v04.csv", female_rows)
    settings: dict[str, object] = {
        "direction": "male main vocal from earlier zip; female vocal from newer zip used as adlibs/layers/chops only",
        "male_zip": str(MALE_ZIP),
        "female_zip": str(FEMALE_ZIP),
        "references": [str(path) for path in REFERENCE_TRACKS],
        "reference_metrics": reference_rows,
        "targets": {"clean_lufs": -9.7, "loud_lufs": -8.5, "true_peak_dbtp": -1.2, "sample_rate": 48000, "bit_depth": 24},
        "reference_tone_polish": {
            "dynamic_formant_control_hz": "520-1450",
            "dynamic_presence_control_hz": "2400-6200",
            "sub_push_hz_db": "58 Hz +0.35 dB",
            "air_shelf_db": "10.5 kHz -0.18 dB",
        },
        "male_vocal_moves": {"lead": male_lead_moves, "backing": male_back_moves},
        "female_vocal_moves": {"lead_source_processed_as_backing": female_lead_moves, "backing_source": female_back_moves},
        "phrase_endings": phrase_endings,
        "adlib_events": adlib_events,
        "chop_events": chop_events,
        "render_metrics": render_rows,
    }
    write_report(render_rows, reference_rows, male_rows, female_rows, phrase_endings, adlib_events, chop_events, settings)

    print(CLEAN_WAV)
    print(LOUD_WAV)
    print(PREVIEW_MP3)
    print(AUDIT_MD)
    print(SETTINGS_JSON)


if __name__ == "__main__":
    main()

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
    compressor,
    convert_mp3,
    convert_wav_24,
    delay_throw,
    detect_phrase_endings,
    limiter,
    make_throw_gate,
    reverb_send,
    sidechain_duck_full,
    write_float_wav,
)
from tools.thin_shadow_v02_commercial_mix import (
    ANALYSIS,
    INTERMEDIATE,
    RENDERS,
    WORK,
    clean_backing,
    clean_lead_vocal,
    commercial_music_bus,
    ensure_dirs,
    load_stems,
    make_female_tone_layer,
    master_bus_polish_v02,
    pad_or_trim,
    run_reaper_batch,
    usable,
    write_batch,
    write_csv,
)


PREMASTER_FLOAT = INTERMEDIATE / "thin_shadow_v03_moderate_female_premaster_float.wav"
PREMASTER_WAV = RENDERS / "thin_shadow_v03_moderate_female_PREMASTER_24-48.wav"
LOUD_MASTER = RENDERS / "thin_shadow_v03_moderate_female_MASTER_loud_24-48.wav"
CLEAN_MASTER = RENDERS / "thin_shadow_v03_moderate_female_MASTER_clean_24-48.wav"
LOUD_MP3 = RENDERS / "thin_shadow_v03_moderate_female_MASTER_loud_320k.mp3"
CLEAN_MP3 = RENDERS / "thin_shadow_v03_moderate_female_MASTER_clean_320k.mp3"
BATCH_LOUD = WORK / "reaper" / "batch_master_v03_moderate_female_loud.txt"
BATCH_CLEAN = WORK / "reaper" / "batch_master_v03_moderate_female_clean.txt"
NOTES = WORK / "thin_shadow_v03_moderate_female_notes.md"


def write_notes(metrics: list[dict[str, object]], moves: dict[str, object]) -> None:
    lines = [
        "# Thin Shadow v03 Moderate Female Tone",
        "",
        "- 여성톤 레이어를 리드 뒤에 자연스럽게 묻히도록 낮춘 버전.",
        "- v02보다 여성 레이어는 약 2.8 dB 더 뒤로, FX send에서도 약 1.4 dB 더 뒤로 배치.",
        "- 원본 스템은 그대로 보존.",
        "",
        "## Deliverables",
        "",
        f"- Loud MP3: `{LOUD_MP3.relative_to(WORK)}`",
        f"- Loud WAV: `{LOUD_MASTER.relative_to(WORK)}`",
        f"- Clean MP3: `{CLEAN_MP3.relative_to(WORK)}`",
        f"- Clean WAV: `{CLEAN_MASTER.relative_to(WORK)}`",
        "",
        "## Metrics",
        "",
        "| label | LUFS | LRA | true peak | peak | RMS |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in metrics:
        lines.append(
            f"| {row.get('label')} | {row.get('integrated_lufs')} | {row.get('lra_lu')} | "
            f"{row.get('true_peak_dbfs')} | {row.get('peak_dbfs')} | {row.get('rms_dbfs')} |"
        )
    lines.extend(
        [
            "",
            "## Blend",
            "",
            f"- female layer bus gain: {moves['female_layer_bus_gain_db']} dB",
            f"- female layer FX-send trim: {moves['female_layer_fx_trim_db']} dB",
            "- lead vocal remains the main center image.",
        ]
    )
    NOTES.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    ensure_dirs()
    sr, stems, _stem_rows = load_stems()
    length = len(stems["lead"])
    for key in list(stems):
        stems[key] = pad_or_trim(stems[key], length)

    lead, _lead_moves = clean_lead_vocal(stems["lead"], sr)
    backing_source = stems["backing_b"] if usable(stems["backing_b"], -70.0) else stems["lead"] * float(amp_db(-18.0))
    backing = clean_backing(backing_source, sr)
    female_layer, _female_moves = make_female_tone_layer(lead, backing, sr)
    music, _music_moves = commercial_music_bus(stems, sr, lead)

    female_layer_bus_gain_db = -4.4
    female_layer_fx_trim_db = -3.4
    endings = detect_phrase_endings(lead, sr)
    throw_gate = make_throw_gate(length, sr, endings, pre_ms=60, post_ms=520, fade_ms=45)
    vocal_fx_source = lead + female_layer * float(amp_db(female_layer_fx_trim_db))
    reverb = reverb_send(vocal_fx_source, sr, decay_s=0.78, wet_db=-18.4, predelay_ms=26, hp_hz=260, lp_hz=7900, seed=33)
    reverb = sidechain_duck_full(reverb, lead, sr, amount_db=3.5, release_ms=180, threshold_percentile=55)
    delay = delay_throw(vocal_fx_source, sr, delay_ms=322, feedback=0.28, wet_db=-16.2, hp_hz=340, lp_hz=5800, pingpong=True)
    delay = delay * throw_gate[:, None]

    vocal_bus = lead * float(amp_db(0.9)) + backing * float(amp_db(-5.8)) + female_layer * float(amp_db(female_layer_bus_gain_db))
    vocal_bus = compressor(vocal_bus, sr, threshold_db=-15.2, ratio=1.28, smooth_ms=135, makeup_db=0.1)
    music = sidechain_duck_full(music, vocal_bus, sr, amount_db=0.75, release_ms=120, threshold_percentile=58)
    mix = music * float(amp_db(0.25)) + vocal_bus + reverb + delay
    premaster = limiter(master_bus_polish_v02(mix, sr), -3.0)

    write_float_wav(PREMASTER_FLOAT, sr, premaster)
    convert_wav_24(PREMASTER_FLOAT, PREMASTER_WAV)
    write_batch(BATCH_LOUD, PREMASTER_WAV, LOUD_MASTER, -7.9)
    write_batch(BATCH_CLEAN, PREMASTER_WAV, CLEAN_MASTER, -11.2)
    run_reaper_batch(BATCH_LOUD)
    run_reaper_batch(BATCH_CLEAN)
    convert_mp3(LOUD_MASTER, LOUD_MP3)
    convert_mp3(CLEAN_MASTER, CLEAN_MP3)

    metrics = [
        audio_metrics(PREMASTER_WAV, "v03_moderate_female_premaster"),
        audio_metrics(CLEAN_MASTER, "v03_moderate_female_clean"),
        audio_metrics(LOUD_MASTER, "v03_moderate_female_loud"),
        audio_metrics(LOUD_MP3, "v03_moderate_female_loud_mp3"),
    ]
    write_csv(ANALYSIS / "render_audit_v03_moderate_female.csv", metrics)
    (ANALYSIS / "render_audit_v03_moderate_female.json").write_text(json.dumps(metrics, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    moves = {
        "female_layer_bus_gain_db": female_layer_bus_gain_db,
        "female_layer_fx_trim_db": female_layer_fx_trim_db,
        "phrase_endings_detected": len(endings),
        "delay_throws_enabled": sum(1 for item in endings if item.get("throw")),
    }
    write_notes(metrics, moves)
    print(json.dumps({"loud_mp3": str(LOUD_MP3), "loud_wav": str(LOUD_MASTER), "notes": str(NOTES)}, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

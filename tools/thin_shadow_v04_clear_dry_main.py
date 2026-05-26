from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path("/Users/hantaeheuk/Documents/New project 3")
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.mgmg_v03_human_vocal_dynamic_fx import (
    amp_db,
    audio_metrics,
    biquad_peaking,
    biquad_shelf,
    compressor,
    convert_mp3,
    convert_wav_24,
    delay_throw,
    detect_phrase_endings,
    dynamic_band_tame,
    limiter,
    make_throw_gate,
    reverb_send,
    sidechain_duck_full,
    saturate,
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


PREMASTER_FLOAT = INTERMEDIATE / "thin_shadow_v04_clear_dry_main_premaster_float.wav"
PREMASTER_WAV = RENDERS / "thin_shadow_v04_clear_dry_main_PREMASTER_24-48.wav"
LOUD_MASTER = RENDERS / "thin_shadow_v04_clear_dry_main_MASTER_loud_24-48.wav"
CLEAN_MASTER = RENDERS / "thin_shadow_v04_clear_dry_main_MASTER_clean_24-48.wav"
LOUD_MP3 = RENDERS / "thin_shadow_v04_clear_dry_main_MASTER_loud_320k.mp3"
CLEAN_MP3 = RENDERS / "thin_shadow_v04_clear_dry_main_MASTER_clean_320k.mp3"
BATCH_LOUD = WORK / "reaper" / "batch_master_v04_clear_dry_main_loud.txt"
BATCH_CLEAN = WORK / "reaper" / "batch_master_v04_clear_dry_main_clean.txt"
NOTES = WORK / "thin_shadow_v04_clear_dry_main_notes.md"


def clarify_lead(lead, sr):
    out = lead
    out, _ = dynamic_band_tame(out, sr, 180, 360, 0.8, 74, 145, slope=0.38)
    out, _ = dynamic_band_tame(out, sr, 5200, 8800, 1.4, 72, 58, slope=0.35)
    out = biquad_peaking(out, sr, 2700, 0.8, 0.95)
    out = biquad_peaking(out, sr, 4200, 0.65, 1.05)
    out = biquad_shelf(out, sr, 10400, 0.35, True)
    out = saturate(out, drive_db=0.45, mix=0.035)
    return compressor(out, sr, threshold_db=-17.6, ratio=1.2, smooth_ms=95, makeup_db=0.1)


def write_notes(metrics: list[dict[str, object]], moves: dict[str, object]) -> None:
    lines = [
        "# Thin Shadow v04 Clear Dry Main Vocal",
        "",
        "- 메인 보컬 리버브를 줄이고 발음 선명도 중심으로 다시 블렌드한 버전.",
        "- v03 대비 리버브 wet은 약 4.8 dB 낮추고 decay도 0.78s -> 0.52s로 줄임.",
        "- 딜레이는 phrase-end throw만 낮게 남김.",
        "- 여성톤은 유지하되 리드 뒤쪽에 더 낮게 배치.",
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
            "## Moves",
            "",
            f"- lead gain: {moves['lead_gain_db']} dB",
            f"- reverb wet: {moves['reverb_wet_db']} dB, decay {moves['reverb_decay_s']} s",
            f"- delay wet: {moves['delay_wet_db']} dB",
            f"- female layer bus gain: {moves['female_layer_bus_gain_db']} dB",
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
    lead = clarify_lead(lead, sr)
    backing_source = stems["backing_b"] if usable(stems["backing_b"], -70.0) else stems["lead"] * float(amp_db(-18.0))
    backing = clean_backing(backing_source, sr)
    female_layer, _female_moves = make_female_tone_layer(lead, backing, sr)
    music, _music_moves = commercial_music_bus(stems, sr, lead)

    lead_gain_db = 1.25
    female_layer_bus_gain_db = -5.6
    female_layer_fx_trim_db = -5.2
    reverb_wet_db = -23.2
    reverb_decay_s = 0.52
    delay_wet_db = -20.4

    endings = detect_phrase_endings(lead, sr)
    throw_gate = make_throw_gate(length, sr, endings, pre_ms=40, post_ms=410, fade_ms=35)
    vocal_fx_source = lead * float(amp_db(-1.2)) + female_layer * float(amp_db(female_layer_fx_trim_db))
    reverb = reverb_send(vocal_fx_source, sr, decay_s=reverb_decay_s, wet_db=reverb_wet_db, predelay_ms=18, hp_hz=320, lp_hz=6900, seed=44)
    reverb = sidechain_duck_full(reverb, lead, sr, amount_db=5.2, release_ms=150, threshold_percentile=52)
    delay = delay_throw(vocal_fx_source, sr, delay_ms=322, feedback=0.22, wet_db=delay_wet_db, hp_hz=430, lp_hz=5200, pingpong=True)
    delay = delay * throw_gate[:, None]

    vocal_bus = (
        lead * float(amp_db(lead_gain_db))
        + backing * float(amp_db(-7.2))
        + female_layer * float(amp_db(female_layer_bus_gain_db))
    )
    vocal_bus = compressor(vocal_bus, sr, threshold_db=-15.0, ratio=1.22, smooth_ms=120, makeup_db=0.05)
    music = sidechain_duck_full(music, vocal_bus, sr, amount_db=0.92, release_ms=115, threshold_percentile=56)
    mix = music * float(amp_db(0.15)) + vocal_bus + reverb + delay
    premaster = limiter(master_bus_polish_v02(mix, sr), -3.0)

    write_float_wav(PREMASTER_FLOAT, sr, premaster)
    convert_wav_24(PREMASTER_FLOAT, PREMASTER_WAV)
    write_batch(BATCH_LOUD, PREMASTER_WAV, LOUD_MASTER, -8.0)
    write_batch(BATCH_CLEAN, PREMASTER_WAV, CLEAN_MASTER, -11.3)
    run_reaper_batch(BATCH_LOUD)
    run_reaper_batch(BATCH_CLEAN)
    convert_mp3(LOUD_MASTER, LOUD_MP3)
    convert_mp3(CLEAN_MASTER, CLEAN_MP3)

    metrics = [
        audio_metrics(PREMASTER_WAV, "v04_clear_dry_main_premaster"),
        audio_metrics(CLEAN_MASTER, "v04_clear_dry_main_clean"),
        audio_metrics(LOUD_MASTER, "v04_clear_dry_main_loud"),
        audio_metrics(LOUD_MP3, "v04_clear_dry_main_loud_mp3"),
    ]
    write_csv(ANALYSIS / "render_audit_v04_clear_dry_main.csv", metrics)
    (ANALYSIS / "render_audit_v04_clear_dry_main.json").write_text(json.dumps(metrics, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    moves = {
        "lead_gain_db": lead_gain_db,
        "reverb_wet_db": reverb_wet_db,
        "reverb_decay_s": reverb_decay_s,
        "delay_wet_db": delay_wet_db,
        "female_layer_bus_gain_db": female_layer_bus_gain_db,
        "phrase_endings_detected": len(endings),
        "delay_throws_enabled": sum(1 for item in endings if item.get("throw")),
    }
    write_notes(metrics, moves)
    print(json.dumps({"loud_mp3": str(LOUD_MP3), "loud_wav": str(LOUD_MASTER), "notes": str(NOTES)}, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

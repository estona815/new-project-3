from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path("/Users/hantaeheuk/Documents/New project 3")
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.mgmg_v03_human_vocal_dynamic_fx import audio_metrics, convert_mp3

REAPER_BIN = Path("/Applications/REAPER.app/Contents/MacOS/REAPER")
WORK = ROOT / "audio_work" / "hangang_shadow_v20_commercial_polish"
FEMALE_WORK = ROOT / "audio_work" / "hangang_shadow_v23_new_female_gated_pan"
REAPER_WORK = ROOT / "reaper" / "hangang_shadow_v24_vocals_down_stems_clear"
RENDERS = ROOT / "renders" / "hangang_shadow_v24_vocals_down_stems_clear"
REPORTS = ROOT / "reports" / "hangang_shadow_v24_vocals_down_stems_clear"

SOURCE_SUM = WORK / "source_full_stems" / "0 한강 Shadow x 얇은 Shadow (Mashup).wav"
NEW_FEMALE_RAW = FEMALE_WORK / "source_new_female_2stem" / "0 Lead Vocals.wav"
BEAT_GLUE_SOURCE = FEMALE_WORK / "source_new_female_2stem" / "1 Instrumental.wav"
FEMALE_GATED = FEMALE_WORK / "processed_stems" / "female_double_new_gated_pan_24-48.wav"
ALIGN_JSON = ROOT / "reports" / "hangang_shadow_v23_new_female_gated_pan" / "female_gated_alignment_report.json"
PREMASTER = RENDERS / "hangang_shadow_mashup_v24_vocals_down_stems_clear_PREMASTER_24-48.wav"
REAPER_PRINT = RENDERS / "hangang_shadow_mashup_v24_vocals_down_stems_clear_REAPERPRINT_24-48.wav"
FINAL_MASTER = RENDERS / "hangang_shadow_mashup_v24_vocals_down_stems_clear_MASTER_loud_24-48.wav"
FINAL_MP3 = RENDERS / "hangang_shadow_mashup_v24_vocals_down_stems_clear_MASTER_loud_320k.mp3"
BATCH_LOUD = REAPER_WORK / "batch_master_v24_vocals_down_stems_clear_loud.txt"
AUDIT_JSON = REPORTS / "render_audit_v24_vocals_down_stems_clear.json"
AUDIT_CSV = REPORTS / "render_audit_v24_vocals_down_stems_clear.csv"
NOTES = REPORTS / "hangang_shadow_v24_vocals_down_stems_clear_notes.md"


def ensure_dirs() -> None:
    RENDERS.mkdir(parents=True, exist_ok=True)
    REPORTS.mkdir(parents=True, exist_ok=True)
    REAPER_WORK.mkdir(parents=True, exist_ok=True)


def write_reaper_batch(target_lufs: float = -8.2) -> None:
    BATCH_LOUD.write_text(
        "\n".join(
            [
                f"{REAPER_PRINT}\t{FINAL_MASTER}",
                "<CONFIG",
                "  SRATE 48000",
                "  NCH 2",
                "  DITHER 3",
                f"  NORMALIZE 3 {target_lufs:.1f} 0",
                "  BRICKWALL 2 -1.0",
                ">",
                "",
            ]
        ),
        encoding="utf-8",
    )


def run_reaper_batch() -> None:
    subprocess.run([str(REAPER_BIN), "-newinst", "-nosplash", "-batchconvert", str(BATCH_LOUD)], check=True)


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    keys: list[str] = []
    for row in rows:
        for key in row:
            if key not in keys:
                keys.append(key)
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)


def write_notes(rows: list[dict[str, object]]) -> None:
    by_label = {str(row.get("label")): row for row in rows}
    final = by_label.get("v24_final_master_loud", {})
    source = by_label.get("source_full_mix_reference", {})
    align = json.loads(ALIGN_JSON.read_text(encoding="utf-8")) if ALIGN_JSON.exists() else {}
    lines = [
        "# Hangang Shadow v24 Vocals Down Stem Glue Notes",
        "",
        "## Summary",
        "",
        "- Source stance: full-stem `12 Vocals.wav` is the male main vocal.",
        "- Vocal bus is reduced 1.5 dB from v23 so the lead is less over-emphasized.",
        "- New instrumental is active as a low beat glue bed; split stems are kept as clearer detail/texture reinforcement instead of acting like separate unglued pieces.",
        "- New female `0 Lead Vocals.wav` remains a quiet gated/panned double only where timing and pitch overlap passed.",
        f"- Female gate kept {align.get('kept_seconds_mask_gt_0_08')} s ({align.get('kept_ratio_of_song')}) after {align.get('global_best_lag_ms')} ms global correction.",
        "- Old female candidates (`11 Backing_Vocals.wav` and v19 `0 Lead Vocals.wav`) remain muted as reference material.",
        "- Revision from v23: vocal down, beat cohesion up, stem detail rebalanced to avoid the separated-stem feeling.",
        "- Processing: REAPER JSFX channel EQ/comp/saturation, bus glue, master soft clip, then REAPER batch loudness/brickwall pass.",
        "- Status: genre_based_draft; this is a mix/master polish pass, not a reference-matched master.",
        "",
        "## Deliverables",
        "",
        f"- REAPER project: `{(REAPER_WORK / 'hangang_shadow_mashup_v24_vocals_down_stems_clear.rpp').relative_to(ROOT)}`",
        f"- Premaster WAV: `{PREMASTER.relative_to(ROOT)}`",
        f"- REAPER print WAV: `{REAPER_PRINT.relative_to(ROOT)}`",
        f"- Loud master WAV: `{FINAL_MASTER.relative_to(ROOT)}`",
        f"- Loud master MP3: `{FINAL_MP3.relative_to(ROOT)}`",
        "",
        "## Result",
        "",
        f"- Source full mix LUFS: {source.get('integrated_lufs')} / true peak {source.get('true_peak_dbfs')}",
        f"- Final master LUFS: {final.get('integrated_lufs')} / true peak {final.get('true_peak_dbfs')}",
        "- Audible intent: male stays main but less oversized; beat reads as one glued bed with clearer stem detail around it.",
        "",
        "## Metrics",
        "",
        "| label | LUFS | LRA | true peak | peak | RMS | corr |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in rows:
        lines.append(
            f"| {row.get('label')} | {row.get('integrated_lufs')} | {row.get('lra_lu')} | "
            f"{row.get('true_peak_dbfs')} | {row.get('peak_dbfs')} | {row.get('rms_dbfs')} | {row.get('stereo_corr')} |"
        )
    lines.extend(
        [
            "",
            "## Main Moves",
            "",
            "- Vocal bus: -1.5 dB from v23, with less presence/air makeup on the vocal bus.",
            "- Beat glue: new instrumental is active under the split stems with mild compression, low-mid tightening, and light saturation.",
            "- Female layer: new `0 Lead Vocals.wav` was shifted by the measured global lag, then only overlap frames passing chroma and local timing thresholds were kept.",
            "- Stems: bass/drums/synth/FX are pulled into detail roles while quiet melodic stems are level-normalized upward where safe.",
            "- Bass/kick: saturation reduced from the separate-stem version so the instrumental bed and detail stems glue together instead of doubling too hard.",
            "- Melody M/S: synth, keyboard, and woodwinds get side presence with a slight mid tuck so melody stays audible but embedded.",
            "- Mix/master: conservative low-end tighten, presence smoothing, soft clipping, then REAPER loudness normalize/brickwall; measured final values are listed above.",
        ]
    )
    NOTES.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    ensure_dirs()
    missing = [path for path in [SOURCE_SUM, NEW_FEMALE_RAW, BEAT_GLUE_SOURCE, FEMALE_GATED, ALIGN_JSON, PREMASTER, REAPER_PRINT] if not path.exists()]
    if missing:
        raise FileNotFoundError("Missing required render/source files: " + ", ".join(str(path) for path in missing))

    write_reaper_batch()
    run_reaper_batch()
    convert_mp3(FINAL_MASTER, FINAL_MP3)

    rows = [
        audio_metrics(SOURCE_SUM, "source_full_mix_reference"),
        audio_metrics(NEW_FEMALE_RAW, "new_female_raw_candidate"),
        audio_metrics(BEAT_GLUE_SOURCE, "beat_glue_instrumental_source"),
        audio_metrics(FEMALE_GATED, "new_female_gated_pan_layer"),
        audio_metrics(PREMASTER, "v24_reaper_premaster"),
        audio_metrics(REAPER_PRINT, "v24_reaper_print"),
        audio_metrics(FINAL_MASTER, "v24_final_master_loud"),
        audio_metrics(FINAL_MP3, "v24_final_master_loud_mp3"),
    ]
    AUDIT_JSON.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_csv(AUDIT_CSV, rows)
    write_notes(rows)
    print(json.dumps({"master_wav": str(FINAL_MASTER), "master_mp3": str(FINAL_MP3), "notes": str(NOTES)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

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
REAPER_WORK = ROOT / "reaper" / "hangang_shadow_v25_v23_base_vocal_down"
RENDERS = ROOT / "renders" / "hangang_shadow_v25_v23_base_vocal_down"
REPORTS = ROOT / "reports" / "hangang_shadow_v25_v23_base_vocal_down"

SOURCE_SUM = WORK / "source_full_stems" / "0 한강 Shadow x 얇은 Shadow (Mashup).wav"
NEW_FEMALE_RAW = FEMALE_WORK / "source_new_female_2stem" / "0 Lead Vocals.wav"
FEMALE_GATED = FEMALE_WORK / "processed_stems" / "female_double_new_gated_pan_24-48.wav"
ALIGN_JSON = ROOT / "reports" / "hangang_shadow_v23_new_female_gated_pan" / "female_gated_alignment_report.json"
PREMASTER = RENDERS / "hangang_shadow_mashup_v25_v23_base_vocal_down_PREMASTER_24-48.wav"
REAPER_PRINT = RENDERS / "hangang_shadow_mashup_v25_v23_base_vocal_down_REAPERPRINT_24-48.wav"
FINAL_MASTER = RENDERS / "hangang_shadow_mashup_v25_v23_base_vocal_down_MASTER_loud_24-48.wav"
FINAL_MP3 = RENDERS / "hangang_shadow_mashup_v25_v23_base_vocal_down_MASTER_loud_320k.mp3"
BATCH_LOUD = REAPER_WORK / "batch_master_v25_v23_base_vocal_down_loud.txt"
AUDIT_JSON = REPORTS / "render_audit_v25_v23_base_vocal_down.json"
AUDIT_CSV = REPORTS / "render_audit_v25_v23_base_vocal_down.csv"
NOTES = REPORTS / "hangang_shadow_v25_v23_base_vocal_down_notes.md"


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
    final = by_label.get("v25_final_master_loud", {})
    source = by_label.get("source_full_mix_reference", {})
    align = json.loads(ALIGN_JSON.read_text(encoding="utf-8")) if ALIGN_JSON.exists() else {}
    lines = [
        "# Hangang Shadow v25 v23 Base Vocal Down Notes",
        "",
        "## Summary",
        "",
        "- Source stance: full-stem `12 Vocals.wav` is the male main vocal.",
        "- This version restarts from v23 because v24 changed the beat feel too much.",
        "- No new instrumental bed is active; only the original v23 full-stem timing is used for the beat.",
        "- Vocal bus is reduced 1.5 dB from v23 with a smaller presence/air push.",
        "- New female `0 Lead Vocals.wav` is not a lead: it is globally aligned, hard-gated by timing/pitch overlap, then added as a quiet panned double only where it passes.",
        f"- Female gate kept {align.get('kept_seconds_mask_gt_0_08')} s ({align.get('kept_ratio_of_song')}) after {align.get('global_best_lag_ms')} ms global correction.",
        "- Old female candidates (`11 Backing_Vocals.wav` and v19 `0 Lead Vocals.wav`) remain muted as reference material.",
        "- Revision from v23: minimal vocal-down correction only; stem timing/structure is kept intact.",
        "- Processing: REAPER JSFX channel EQ/comp/saturation, bus glue, master soft clip, then REAPER batch loudness/brickwall pass.",
        "- Status: genre_based_draft; this is a mix/master polish pass, not a reference-matched master.",
        "",
        "## Deliverables",
        "",
        f"- REAPER project: `{(REAPER_WORK / 'hangang_shadow_mashup_v25_v23_base_vocal_down.rpp').relative_to(ROOT)}`",
        f"- Premaster WAV: `{PREMASTER.relative_to(ROOT)}`",
        f"- REAPER print WAV: `{REAPER_PRINT.relative_to(ROOT)}`",
        f"- Loud master WAV: `{FINAL_MASTER.relative_to(ROOT)}`",
        f"- Loud master MP3: `{FINAL_MP3.relative_to(ROOT)}`",
        "",
        "## Result",
        "",
        f"- Source full mix LUFS: {source.get('integrated_lufs')} / true peak {source.get('true_peak_dbfs')}",
        f"- Final master LUFS: {final.get('integrated_lufs')} / true peak {final.get('true_peak_dbfs')}",
        "- Audible intent: return to v23 song feel, with the vocal less oversized and no added beat timing risk.",
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
            "- V23 base preserved: active music uses the same original full-stem sources and item positions.",
            "- Vocal bus: -1.5 dB from v23, with a smaller presence/air push to reduce the over-forward vocal feel.",
            "- Female layer: new `0 Lead Vocals.wav` was shifted by the measured global lag, then only overlap frames passing chroma and local timing thresholds were kept.",
            "- Stems: no v24 instrumental bed and no broad stem rebalance; the beat structure remains v23.",
            "- Bass/kick: bass and drum stems get added saturation, low-end body, and dynamic low-mid control.",
            "- Melody M/S: synth, keyboard, and woodwinds get side presence with a slight mid tuck so melody stays audible but embedded.",
            "- Mix/master: conservative low-end tighten, presence smoothing, soft clipping, then REAPER loudness normalize/brickwall; measured final values are listed above.",
        ]
    )
    NOTES.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    ensure_dirs()
    missing = [path for path in [SOURCE_SUM, NEW_FEMALE_RAW, FEMALE_GATED, ALIGN_JSON, PREMASTER, REAPER_PRINT] if not path.exists()]
    if missing:
        raise FileNotFoundError("Missing required render/source files: " + ", ".join(str(path) for path in missing))

    write_reaper_batch()
    run_reaper_batch()
    convert_mp3(FINAL_MASTER, FINAL_MP3)

    rows = [
        audio_metrics(SOURCE_SUM, "source_full_mix_reference"),
        audio_metrics(NEW_FEMALE_RAW, "new_female_raw_candidate"),
        audio_metrics(FEMALE_GATED, "new_female_gated_pan_layer"),
        audio_metrics(PREMASTER, "v25_reaper_premaster"),
        audio_metrics(REAPER_PRINT, "v25_reaper_print"),
        audio_metrics(FINAL_MASTER, "v25_final_master_loud"),
        audio_metrics(FINAL_MP3, "v25_final_master_loud_mp3"),
    ]
    AUDIT_JSON.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_csv(AUDIT_CSV, rows)
    write_notes(rows)
    print(json.dumps({"master_wav": str(FINAL_MASTER), "master_mp3": str(FINAL_MP3), "notes": str(NOTES)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

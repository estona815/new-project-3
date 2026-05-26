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
FEMALE_SOURCE_WORK = ROOT / "audio_work" / "hangang_shadow_v23_new_female_gated_pan"
FEMALE_WORK = ROOT / "audio_work" / "hangang_shadow_v28_reference_estona"
REAPER_WORK = ROOT / "reaper" / "hangang_shadow_v28_reference_estona"
RENDERS = ROOT / "renders" / "hangang_shadow_v28_reference_estona"
REPORTS = ROOT / "reports" / "hangang_shadow_v28_reference_estona"
REFERENCE_SUMMARY = REPORTS / "estona_reference_delta_summary.json"

SOURCE_SUM = WORK / "source_full_stems" / "0 한강 Shadow x 얇은 Shadow (Mashup).wav"
SYNTH_SOURCE = WORK / "source_full_stems" / "4 Synth.wav"
NEW_FEMALE_RAW = FEMALE_SOURCE_WORK / "source_new_female_2stem" / "0 Lead Vocals.wav"
FEMALE_GATED = FEMALE_WORK / "processed_stems" / "female_double_no_intro_chops_24-48.wav"
ALIGN_JSON = ROOT / "reports" / "hangang_shadow_v23_new_female_gated_pan" / "female_gated_alignment_report.json"
INTRO_CHOP_JSON = REPORTS / "intro_chop_removal_report.json"
PREMASTER = RENDERS / "hangang_shadow_mashup_v28_reference_estona_PREMASTER_24-48.wav"
REAPER_PRINT = RENDERS / "hangang_shadow_mashup_v28_reference_estona_REAPERPRINT_24-48.wav"
FINAL_MASTER = RENDERS / "hangang_shadow_mashup_v28_reference_estona_MASTER_loud_24-48.wav"
FINAL_MP3 = RENDERS / "hangang_shadow_mashup_v28_reference_estona_MASTER_loud_320k.mp3"
BATCH_LOUD = REAPER_WORK / "batch_master_v28_reference_estona_loud.txt"
AUDIT_JSON = REPORTS / "render_audit_v28_reference_estona.json"
AUDIT_CSV = REPORTS / "render_audit_v28_reference_estona.csv"
NOTES = REPORTS / "hangang_shadow_v28_reference_estona_notes.md"


def ensure_dirs() -> None:
    RENDERS.mkdir(parents=True, exist_ok=True)
    REPORTS.mkdir(parents=True, exist_ok=True)
    REAPER_WORK.mkdir(parents=True, exist_ok=True)


def write_reaper_batch(target_lufs: float = -7.2) -> None:
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
    final = by_label.get("v28_final_master_loud", {})
    source = by_label.get("source_full_mix_reference", {})
    align = json.loads(ALIGN_JSON.read_text(encoding="utf-8")) if ALIGN_JSON.exists() else {}
    reference = json.loads(REFERENCE_SUMMARY.read_text(encoding="utf-8")) if REFERENCE_SUMMARY.exists() else {}
    ref_median = reference.get("reference_set_median", {})
    lines = [
        "# Hangang Shadow v28 Reference Estona Notes",
        "",
        "## Summary",
        "",
        "- Source stance: full-stem `12 Vocals.wav` is the male main vocal.",
        "- This version restarts from v23 because v24 changed the beat feel too much.",
        "- No new instrumental bed is active; only the original v23 full-stem timing is used for the beat.",
        "- Estona/Nib reference set was analyzed as a folder of 24/48 masters, then translated conservatively.",
        "- Vocal remains slightly tucked from the earlier vocal-forward passes; presence/air are softened to avoid the synthetic top edge.",
        "- Added female-double intro chops before 9.20s are removed; the male main vocal is not cut.",
        "- Kick and bass get a reference-informed low texture pass: more 60-80 Hz density, more saturation, and extra low-mid control.",
        "- Main melody is lifted by side/embedded M/S presence after 1.18 kHz and 3.15 kHz resonance control.",
        "- Vocal tune feel is increased slightly with a quiet parallel lead density layer; ReaTune remains present, but this is not note-by-note manual pitch editing.",
        "- New female `0 Lead Vocals.wav` is not a lead: it is globally aligned, hard-gated by timing/pitch overlap, then added as a quiet panned double only where it passes.",
        f"- Female gate kept {align.get('kept_seconds_mask_gt_0_08')} s ({align.get('kept_ratio_of_song')}) after {align.get('global_best_lag_ms')} ms global correction.",
        "- Old female candidates (`11 Backing_Vocals.wav` and v19 `0 Lead Vocals.wav`) remain muted as reference material.",
        "- Revision from v27: slightly wider music bed, controlled low-end density, less 1.5-5 kHz/air glare, and a slightly hotter but true-peak-safe loud master.",
        f"- Reference median: {ref_median.get('integrated_lufs')} LUFS / side-mid {ref_median.get('side_mid_db')} dB / sub share {ref_median.get('sub_20_80_pct')}%.",
        "- Processing: REAPER JSFX channel EQ/comp/saturation, bus glue, master soft clip, then REAPER batch loudness/brickwall pass.",
        "- Status: genre_based_draft; this is a measured reference-informed polish pass, not a claim of identical reference matching.",
        "",
        "## Deliverables",
        "",
        f"- REAPER project: `{(REAPER_WORK / 'hangang_shadow_mashup_v28_reference_estona.rpp').relative_to(ROOT)}`",
        f"- Premaster WAV: `{PREMASTER.relative_to(ROOT)}`",
        f"- REAPER print WAV: `{REAPER_PRINT.relative_to(ROOT)}`",
        f"- Loud master WAV: `{FINAL_MASTER.relative_to(ROOT)}`",
        f"- Loud master MP3: `{FINAL_MP3.relative_to(ROOT)}`",
        "",
        "## Result",
        "",
        f"- Source full mix LUFS: {source.get('integrated_lufs')} / true peak {source.get('true_peak_dbfs')}",
        f"- Final master LUFS: {final.get('integrated_lufs')} / true peak {final.get('true_peak_dbfs')}",
        "- Audible intent: keep the v23/v25/v27 song feel while pushing the master closer to the measured Estona/Nib reference traits.",
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
            "- Vocal bus: stays tucked from the earlier vocal-forward passes, with less presence/air emphasis and slightly stronger de-ess/harshness control.",
            "- Intro chops: removed only the added female-double layer before 9.20s; original male lead and beat are untouched.",
            "- Vocal tune: quiet parallel lead density layer is a little more present, but still below the male main. This is a tune-feel support layer, not manual note correction.",
            "- Kick/bass: saturation drive/mix and 60-80 Hz body are raised, with output trims and 200 Hz control to avoid boom.",
            "- Melody: synth level/M/S readability is lifted only after dynamic 1.18 kHz and 3.15 kHz resonance control plus high-tail taming.",
            "- Female layer: new `0 Lead Vocals.wav` was shifted by the measured global lag, then only overlap frames passing chroma and local timing thresholds were kept.",
            "- Stems: no v24 instrumental bed and no broad stem rebalance; the beat structure remains v23.",
            "- Reference translation: v27 measured narrower and less sub-dense than the reference median, so v28 adds music width and controlled low-end density without chasing the reference's clipped true peaks.",
            "- Mix/master: low-end tighten, presence smoothing, soft clipping, then REAPER loudness normalize/brickwall; measured final values are listed above.",
        ]
    )
    NOTES.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    ensure_dirs()
    missing = [path for path in [SOURCE_SUM, SYNTH_SOURCE, NEW_FEMALE_RAW, FEMALE_GATED, ALIGN_JSON, INTRO_CHOP_JSON, PREMASTER, REAPER_PRINT] if not path.exists()]
    if missing:
        raise FileNotFoundError("Missing required render/source files: " + ", ".join(str(path) for path in missing))

    write_reaper_batch()
    run_reaper_batch()
    convert_mp3(FINAL_MASTER, FINAL_MP3)

    rows = [
        audio_metrics(SOURCE_SUM, "source_full_mix_reference"),
        audio_metrics(SYNTH_SOURCE, "synth_source_reference"),
        audio_metrics(NEW_FEMALE_RAW, "new_female_raw_candidate"),
        audio_metrics(FEMALE_GATED, "new_female_gated_no_intro_chops_layer"),
        audio_metrics(PREMASTER, "v28_reaper_premaster"),
        audio_metrics(REAPER_PRINT, "v28_reaper_print"),
        audio_metrics(FINAL_MASTER, "v28_final_master_loud"),
        audio_metrics(FINAL_MP3, "v28_final_master_loud_mp3"),
    ]
    AUDIT_JSON.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_csv(AUDIT_CSV, rows)
    write_notes(rows)
    print(json.dumps({"master_wav": str(FINAL_MASTER), "master_mp3": str(FINAL_MP3), "notes": str(NOTES)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

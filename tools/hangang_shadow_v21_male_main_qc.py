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
REAPER_WORK = ROOT / "reaper" / "hangang_shadow_v21_male_main"
RENDERS = ROOT / "renders" / "hangang_shadow_v21_male_main"
REPORTS = ROOT / "reports" / "hangang_shadow_v21_male_main"

SOURCE_SUM = WORK / "source_full_stems" / "0 한강 Shadow x 얇은 Shadow (Mashup).wav"
PREMASTER = RENDERS / "hangang_shadow_mashup_v21_male_main_PREMASTER_24-48.wav"
REAPER_PRINT = RENDERS / "hangang_shadow_mashup_v21_male_main_REAPERPRINT_24-48.wav"
FINAL_MASTER = RENDERS / "hangang_shadow_mashup_v21_male_main_MASTER_loud_24-48.wav"
FINAL_MP3 = RENDERS / "hangang_shadow_mashup_v21_male_main_MASTER_loud_320k.mp3"
BATCH_LOUD = REAPER_WORK / "batch_master_v21_male_main_loud.txt"
AUDIT_JSON = REPORTS / "render_audit_v21_male_main.json"
AUDIT_CSV = REPORTS / "render_audit_v21_male_main.csv"
NOTES = REPORTS / "hangang_shadow_v21_male_main_notes.md"


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
    final = by_label.get("v21_final_master_loud", {})
    source = by_label.get("source_full_mix_reference", {})
    lines = [
        "# Hangang Shadow v21 Male Main Notes",
        "",
        "## Summary",
        "",
        "- Source stance: full-stem `12 Vocals.wav` is the male main vocal.",
        "- Female material is not the lead: `11 Backing_Vocals.wav` is tucked as a low double/adlib layer, and v19 `0 Lead Vocals.wav` is muted as reference only.",
        "- Processing: REAPER JSFX channel EQ/comp/saturation, bus glue, master soft clip, then REAPER batch loudness/brickwall pass.",
        "- Status: genre_based_draft; this is a mix/master polish pass, not a reference-matched master.",
        "",
        "## Deliverables",
        "",
        f"- REAPER project: `{(REAPER_WORK / 'hangang_shadow_mashup_v21_male_main.rpp').relative_to(ROOT)}`",
        f"- Premaster WAV: `{PREMASTER.relative_to(ROOT)}`",
        f"- REAPER print WAV: `{REAPER_PRINT.relative_to(ROOT)}`",
        f"- Loud master WAV: `{FINAL_MASTER.relative_to(ROOT)}`",
        f"- Loud master MP3: `{FINAL_MP3.relative_to(ROOT)}`",
        "",
        "## Result",
        "",
        f"- Source full mix LUFS: {source.get('integrated_lufs')} / true peak {source.get('true_peak_dbfs')}",
        f"- Final master LUFS: {final.get('integrated_lufs')} / true peak {final.get('true_peak_dbfs')}",
        "- Audible intent: male voice stays in front; female layer supports only as a tucked double/adlib texture.",
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
            "- Male lead: high-pass cleanup, low-mid dip, 3 kHz presence lift, gentle air, 1.7:1 leveling, light saturation.",
            "- Female double: high-passed, de-essed, lowered, widened, and routed under the male bus so it cannot become the main vocal.",
            "- Instrumental: rebuilt from full music stems with bass/drums/synth/keys active and artifact-prone guitar muted.",
            "- Mix/master: conservative low-end tighten, presence smoothing, soft clipping, then REAPER loudness normalize/brickwall; measured final values are listed above.",
        ]
    )
    NOTES.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    ensure_dirs()
    missing = [path for path in [SOURCE_SUM, PREMASTER, REAPER_PRINT] if not path.exists()]
    if missing:
        raise FileNotFoundError("Missing required render/source files: " + ", ".join(str(path) for path in missing))

    write_reaper_batch()
    run_reaper_batch()
    convert_mp3(FINAL_MASTER, FINAL_MP3)

    rows = [
        audio_metrics(SOURCE_SUM, "source_full_mix_reference"),
        audio_metrics(PREMASTER, "v21_reaper_premaster"),
        audio_metrics(REAPER_PRINT, "v21_reaper_print"),
        audio_metrics(FINAL_MASTER, "v21_final_master_loud"),
        audio_metrics(FINAL_MP3, "v21_final_master_loud_mp3"),
    ]
    AUDIT_JSON.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_csv(AUDIT_CSV, rows)
    write_notes(rows)
    print(json.dumps({"master_wav": str(FINAL_MASTER), "master_mp3": str(FINAL_MP3), "notes": str(NOTES)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import csv
import json
import statistics
import sys
from pathlib import Path

ROOT = Path("/Users/hantaeheuk/Documents/New project 3")
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.mgmg_v03_human_vocal_dynamic_fx import audio_metrics

REF_DIR = Path("/Users/hantaeheuk/Desktop/Estona-4dium_MASTER_24-48.")
BASELINE_V27_MASTER = ROOT / "renders" / "hangang_shadow_v27_kick_bass_melody_tune" / "hangang_shadow_mashup_v27_kick_bass_melody_tune_MASTER_loud_24-48.wav"
BASELINE_V27_PREMASTER = ROOT / "renders" / "hangang_shadow_v27_kick_bass_melody_tune" / "hangang_shadow_mashup_v27_kick_bass_melody_tune_PREMASTER_24-48.wav"
FINAL_V28_MASTER = ROOT / "renders" / "hangang_shadow_v28_reference_estona" / "hangang_shadow_mashup_v28_reference_estona_MASTER_loud_24-48.wav"
FINAL_V28_PREMASTER = ROOT / "renders" / "hangang_shadow_v28_reference_estona" / "hangang_shadow_mashup_v28_reference_estona_PREMASTER_24-48.wav"
SOURCE_MIX = ROOT / "audio_work" / "hangang_shadow_v20_commercial_polish" / "source_full_stems" / "0 한강 Shadow x 얇은 Shadow (Mashup).wav"

REPORT_DIR = ROOT / "reports" / "hangang_shadow_v28_reference_estona"
METRICS_JSON = REPORT_DIR / "estona_reference_set_metrics.json"
METRICS_CSV = REPORT_DIR / "estona_reference_set_metrics.csv"
SUMMARY_JSON = REPORT_DIR / "estona_reference_delta_summary.json"
SUMMARY_MD = REPORT_DIR / "estona_reference_delta_summary.md"

KEYS = [
    "integrated_lufs",
    "lra_lu",
    "true_peak_dbfs",
    "rms_dbfs",
    "crest_db",
    "stereo_corr",
    "side_mid_db",
    "sub_20_80_pct",
    "bass_body_80_200_pct",
    "body_200_500_pct",
    "formant_500_1500_pct",
    "presence_1500_5000_pct",
    "sibilance_5000_10000_pct",
    "air_10000_16000_pct",
    "short_term_lufs_median",
    "short_term_lufs_max",
]


def clean_ref_label(path: Path) -> str:
    return path.stem.replace("Estona,Nib-", "ref_").replace("_MASTER_24-48", "")


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


def median(values: list[float]) -> float | None:
    values = [float(v) for v in values if v is not None]
    if not values:
        return None
    return round(float(statistics.median(values)), 4)


def avg(values: list[float]) -> float | None:
    values = [float(v) for v in values if v is not None]
    if not values:
        return None
    return round(float(sum(values) / len(values)), 4)


def aggregate_reference(rows: list[dict[str, object]]) -> dict[str, object]:
    refs = [row for row in rows if str(row.get("label", "")).startswith("ref_")]
    aggregate: dict[str, object] = {"label": "reference_set_median", "reference_count": len(refs)}
    for key in KEYS:
        vals = [row.get(key) for row in refs if isinstance(row.get(key), (int, float))]
        aggregate[key] = median(vals)
        aggregate[f"{key}_avg"] = avg(vals)
    return aggregate


def numeric_delta(current: dict[str, object], target: dict[str, object], key: str) -> float | None:
    if not isinstance(current.get(key), (int, float)) or not isinstance(target.get(key), (int, float)):
        return None
    return round(float(current[key]) - float(target[key]), 4)


def build_summary(rows: list[dict[str, object]], aggregate: dict[str, object]) -> dict[str, object]:
    current = next((row for row in rows if row.get("label") == "final_v28_master"), None)
    if current is None:
        current = next(row for row in rows if row.get("label") == "baseline_v27_master")
    baseline = next(row for row in rows if row.get("label") == "baseline_v27_master")
    source = next(row for row in rows if row.get("label") == "source_full_mix")
    delta = {key: numeric_delta(current, aggregate, key) for key in KEYS}
    v28_minus_v27 = {key: numeric_delta(current, baseline, key) for key in KEYS}
    return {
        "status": "genre_based_draft",
        "reference_dir": str(REF_DIR),
        "current_master": str(FINAL_V28_MASTER if FINAL_V28_MASTER.exists() else BASELINE_V27_MASTER),
        "source_full_mix": str(SOURCE_MIX),
        "reference_set_median": aggregate,
        "baseline_v27_master": baseline,
        "current_final_master": current,
        "source_full_mix_metrics": source,
        "current_minus_reference_median": delta,
        "current_minus_baseline_v27": v28_minus_v27,
        "mix_translation_notes": [
            "Reference set is louder and more peak-dense than a conservative streaming master, but true peak remains controlled.",
            "Use the reference median as tonal direction, not as a command to copy arrangement or vocal placement.",
            "Keep v23/v25 timing intact; do not use the rejected v24 active instrumental bed.",
            "Favor small low-end texture and melody clarity changes over broad stem rebalance.",
        ],
    }


def write_markdown(rows: list[dict[str, object]], summary: dict[str, object]) -> None:
    agg = summary["reference_set_median"]
    current = summary["current_final_master"]
    baseline = summary["baseline_v27_master"]
    delta = summary["current_minus_reference_median"]
    v28_minus_v27 = summary["current_minus_baseline_v27"]
    lines = [
        "# Hangang Shadow v28 Estona Reference Analysis",
        "",
        "## Scope",
        "",
        "- Reference material: Estona/Nib 24-bit 48 kHz master WAV set from the user-provided folder.",
        "- Comparison basis: final v28, baseline v27, and original full mix.",
        "- Status: genre_based_draft; this is measured reference-informed direction, not an identical match claim.",
        "",
        "## Reference Median vs Final v28",
        "",
        "| metric | reference median | final v28 | v28 - ref | v28 - v27 |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for key in KEYS:
        lines.append(f"| {key} | {agg.get(key)} | {current.get(key)} | {delta.get(key)} | {v28_minus_v27.get(key)} |")
    lines.extend(
        [
            "",
            "## Baseline v27",
            "",
            "| metric | v27 | final v28 |",
            "| --- | ---: | ---: |",
        ]
    )
    for key in KEYS:
        lines.append(f"| {key} | {baseline.get(key)} | {current.get(key)} |")
    lines.extend(
        [
            "",
            "## Per-Reference Metrics",
            "",
            "| label | LUFS | LRA | true peak | RMS | crest | side/mid | sub | bass body | low-mid | presence | sibilance | air |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for row in rows:
        lines.append(
            f"| {row.get('label')} | {row.get('integrated_lufs')} | {row.get('lra_lu')} | "
            f"{row.get('true_peak_dbfs')} | {row.get('rms_dbfs')} | {row.get('crest_db')} | "
            f"{row.get('side_mid_db')} | {row.get('sub_20_80_pct')} | {row.get('bass_body_80_200_pct')} | "
            f"{row.get('body_200_500_pct')} | {row.get('presence_1500_5000_pct')} | "
            f"{row.get('sibilance_5000_10000_pct')} | {row.get('air_10000_16000_pct')} |"
        )
    lines.extend(
        [
            "",
            "## Translation Into v28",
            "",
            "- Keep male vocal main and female layer tucked; no broad vocal lift.",
            "- Move low-end density toward the reference set with controlled kick/bass saturation and 80-200 Hz body, while keeping sub mono and clipped safely.",
            "- Make the main melody more readable by removing resonant bite first, then adding a small embedded presence lift.",
            "- Reduce synthetic top glare instead of simply boosting air.",
            "- Use slightly stronger bus glue and limiter conditioning only after checking true peak.",
        ]
    )
    SUMMARY_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    refs = sorted(path for path in REF_DIR.glob("*.wav") if path.is_file())
    if not refs:
        raise FileNotFoundError(f"No WAV reference files found in {REF_DIR}")
    required = [BASELINE_V27_MASTER, BASELINE_V27_PREMASTER, SOURCE_MIX]
    missing = [path for path in required if not path.exists()]
    if missing:
        raise FileNotFoundError("Missing comparison files: " + ", ".join(str(path) for path in missing))

    rows: list[dict[str, object]] = []
    for path in refs:
        rows.append(audio_metrics(path, clean_ref_label(path)))
    rows.append(audio_metrics(SOURCE_MIX, "source_full_mix"))
    rows.append(audio_metrics(BASELINE_V27_PREMASTER, "baseline_v27_premaster"))
    rows.append(audio_metrics(BASELINE_V27_MASTER, "baseline_v27_master"))
    if FINAL_V28_PREMASTER.exists():
        rows.append(audio_metrics(FINAL_V28_PREMASTER, "final_v28_premaster"))
    if FINAL_V28_MASTER.exists():
        rows.append(audio_metrics(FINAL_V28_MASTER, "final_v28_master"))
    aggregate = aggregate_reference(rows)
    summary = build_summary(rows, aggregate)

    METRICS_JSON.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    SUMMARY_JSON.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_csv(METRICS_CSV, rows)
    write_markdown(rows, summary)
    print(json.dumps({"metrics": str(METRICS_JSON), "summary": str(SUMMARY_JSON), "markdown": str(SUMMARY_MD)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

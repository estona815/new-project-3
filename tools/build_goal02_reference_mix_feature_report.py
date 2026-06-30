#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FEATURES_CSV = ROOT / "reports" / "goal02_8_reference_match" / "goal02_reference_features.csv"
DEFAULT_MATCH_JSON = ROOT / "reports" / "goal02_8_reference_match" / "goal02_reference_match.json"
DEFAULT_OUTPUT_DIR = ROOT / "reports" / "goal02_8_reference_match"


METRIC_FIELDS = [
    "rms_dbfs",
    "sample_peak_dbfs",
    "crest_factor_db",
    "peak_density_over_minus1db_pct",
    "transient_density_per_second",
    "spectral_centroid_hz",
    "spectral_rolloff_hz",
    "low_energy_ratio_20_120",
    "low_mid_energy_ratio_120_350",
    "mid_energy_ratio_350_2500",
    "presence_energy_ratio_2500_6000",
    "sibilance_energy_ratio_5000_10000",
    "air_energy_ratio_10000_16000",
    "high_energy_ratio_2500_16000",
    "stereo_correlation",
]


def now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_float(value: Any) -> float | None:
    if value in ("", None):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number


def fmt(value: Any, digits: int = 3) -> str:
    number = parse_float(value)
    if number is None:
        return "unavailable"
    return f"{number:.{digits}f}"


def basename(path: str) -> str:
    return Path(path).name if path else ""


def load_rows(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def band_level(value: float | None, *, high: float, mid: float) -> str:
    if value is None:
        return "unavailable"
    if value >= high:
        return "high"
    if value >= mid:
        return "medium"
    return "low"


def density_level(rms: float | None, crest: float | None, peak_density: float | None) -> str:
    if rms is None or crest is None:
        return "unavailable"
    if rms >= -6.5 and crest <= 6.5 and (peak_density or 0.0) >= 1.0:
        return "very dense / clipped-master leaning"
    if rms >= -8.0 and crest <= 8.0:
        return "dense release-master leaning"
    return "less dense / more open"


def low_end_character(row: dict[str, Any]) -> str:
    low = parse_float(row.get("low_energy_ratio_20_120"))
    low_mid = parse_float(row.get("low_mid_energy_ratio_120_350"))
    high = parse_float(row.get("high_energy_ratio_2500_16000"))
    if low is None:
        return "unavailable"
    if low >= 0.75 and (low_mid or 0.0) < 0.14 and (high or 0.0) < 0.04:
        return "sub-dominant low end; harmonic content is controlled"
    if low >= 0.55 and (high or 0.0) >= 0.04:
        return "sub plus audible upper harmonic/hat energy"
    if low >= 0.55:
        return "sub-forward but not purely sub-only"
    return "less sub-forward than the primary low-end references"


def stereo_character(correlation: float | None) -> str:
    if correlation is None:
        return "unavailable"
    if correlation >= 0.95:
        return "very mono-compatible center"
    if correlation >= 0.85:
        return "wide but still positive-correlation"
    if correlation >= 0.50:
        return "moderate stereo safety"
    return "mono-collapse risk"


def brightness_character(row: dict[str, Any]) -> str:
    centroid = parse_float(row.get("spectral_centroid_hz"))
    sibilance = parse_float(row.get("sibilance_energy_ratio_5000_10000"))
    air = parse_float(row.get("air_energy_ratio_10000_16000"))
    high = parse_float(row.get("high_energy_ratio_2500_16000"))
    parts: list[str] = []
    if centroid is not None:
        if centroid >= 4400:
            parts.append("bright centroid")
        elif centroid >= 3600:
            parts.append("moderate-bright centroid")
        else:
            parts.append("darker centroid")
    parts.append(f"{band_level(high, high=0.05, mid=0.025)} high-band share")
    parts.append(f"{band_level(sibilance, high=0.018, mid=0.009)} 5-10 kHz sibilance proxy")
    parts.append(f"{band_level(air, high=0.007, mid=0.002)} 10-16 kHz air proxy")
    return "; ".join(parts)


def target_gap_against(row: dict[str, Any], target: dict[str, Any]) -> list[str]:
    gaps: list[str] = []
    for field, label in [
        ("rms_dbfs", "RMS/master density"),
        ("low_energy_ratio_20_120", "20-120 Hz low-end share"),
        ("transient_density_per_second", "transient density"),
        ("spectral_centroid_hz", "brightness centroid"),
        ("stereo_correlation", "stereo correlation"),
    ]:
        ref_value = parse_float(row.get(field))
        target_value = parse_float(target.get(field))
        if ref_value is None or target_value is None:
            continue
        if field == "rms_dbfs":
            delta = target_value - ref_value
            gaps.append(f"{label}: target is {delta:.2f} dB lower by RMS")
        elif field == "stereo_correlation":
            gaps.append(f"{label}: target {target_value:.3f} vs ref {ref_value:.3f}")
        else:
            delta = ref_value - target_value
            gaps.append(f"{label}: ref exceeds target by {delta:.3f}")
    return gaps


def core_features(row: dict[str, Any]) -> list[str]:
    rms = parse_float(row.get("rms_dbfs"))
    crest = parse_float(row.get("crest_factor_db"))
    peak_density = parse_float(row.get("peak_density_over_minus1db_pct"))
    transient = parse_float(row.get("transient_density_per_second"))
    corr = parse_float(row.get("stereo_correlation"))
    features = [
        density_level(rms, crest, peak_density),
        low_end_character(row),
        brightness_character(row),
    ]
    if transient is not None:
        features.append("fast drum/hat transient proxy" if transient >= 20.0 else "less transient-dense than the fastest references")
    if corr is not None:
        features.append(stereo_character(corr))
    return features[:3]


def build_reference_entry(row: dict[str, Any], target: dict[str, Any], primary_ids: set[str]) -> dict[str, Any]:
    rms = parse_float(row.get("rms_dbfs"))
    crest = parse_float(row.get("crest_factor_db"))
    peak_density = parse_float(row.get("peak_density_over_minus1db_pct"))
    transient = parse_float(row.get("transient_density_per_second"))
    corr = parse_float(row.get("stereo_correlation"))
    low = parse_float(row.get("low_energy_ratio_20_120"))
    low_mid = parse_float(row.get("low_mid_energy_ratio_120_350"))
    presence = parse_float(row.get("presence_energy_ratio_2500_6000"))
    sibilance = parse_float(row.get("sibilance_energy_ratio_5000_10000"))
    air = parse_float(row.get("air_energy_ratio_10000_16000"))
    return {
        "id": row["id"],
        "role": row.get("role", ""),
        "file": basename(row.get("path", "")),
        "is_primary_reference": row["id"] in primary_ids,
        "measurement_scope": "auto-selected 20-second loudest-RMS window from stereo master",
        "claim_limit": "No isolated vocal/drum/bass stems for references; vocal, tune, reverb, kick/808, and distortion notes are measured proxies, not listening claims.",
        "metrics": {field: parse_float(row.get(field)) for field in METRIC_FIELDS},
        "overall_loudness_rms_lufs": {
            "lufs_i": row.get("lufs_i") or "unavailable",
            "rms_dbfs": rms,
            "crest_factor_db": crest,
            "density_read": density_level(rms, crest, peak_density),
        },
        "true_peak_peak_density": {
            "true_peak_dbtp": "unavailable",
            "sample_peak_dbfs": parse_float(row.get("sample_peak_dbfs")),
            "peak_density_over_minus1db_pct": peak_density,
            "note": "Only sample peak and peak-density proxy are available in this stage.",
        },
        "vocal_position_thickness_brightness_proxy": {
            "proxy_basis": "350-2500 Hz mid, 2.5-6 kHz presence, 10-16 kHz air, stereo correlation",
            "mid_ratio": parse_float(row.get("mid_energy_ratio_350_2500")),
            "presence_ratio": presence,
            "air_ratio": air,
            "stereo_correlation": corr,
            "read": f"{band_level(presence, high=0.02, mid=0.012)} presence; {band_level(air, high=0.007, mid=0.002)} air; {stereo_character(corr)}",
        },
        "autotune_sibilance_proxy": {
            "autotune_strength": "not directly measurable from current feature set",
            "sibilance_ratio_5000_10000": sibilance,
            "read": f"{band_level(sibilance, high=0.018, mid=0.009)} sibilance/hat-brightness proxy",
        },
        "bass_808_character_proxy": {
            "low_ratio_20_120": low,
            "low_mid_ratio_120_350": low_mid,
            "read": low_end_character(row),
        },
        "kick_808_relationship_proxy": {
            "proxy_basis": "20-120 Hz low share plus transient density; kick and 808 are not isolated in reference masters",
            "transient_density_per_second": transient,
            "read": "dense low-end with active kick/hat transients" if (low or 0.0) >= 0.55 and (transient or 0.0) >= 18.0 else "requires ear/user check after level-matched A/B",
        },
        "drum_hihat_proxy": {
            "transient_density_per_second": transient,
            "high_ratio_2500_16000": parse_float(row.get("high_energy_ratio_2500_16000")),
            "sibilance_ratio_5000_10000": sibilance,
            "read": "fast transient field" if (transient or 0.0) >= 20.0 else "moderate transient field",
        },
        "presence_harshness_air": {
            "presence_2500_6000": presence,
            "sibilance_5000_10000": sibilance,
            "air_10000_16000": air,
            "read": brightness_character(row),
        },
        "stereo_width_mono_compatibility": {
            "stereo_correlation": corr,
            "read": stereo_character(corr),
        },
        "reverb_delay_depth_proxy": {
            "proxy_basis": "not directly measured; stereo width and high-band persistence are weak proxies only",
            "read": "requires listening/user A/B confirmation; do not claim reverb depth from this report alone",
        },
        "saturation_clipping_distortion_proxy": {
            "crest_factor_db": crest,
            "peak_density_over_minus1db_pct": peak_density,
            "sample_peak_dbfs": parse_float(row.get("sample_peak_dbfs")),
            "read": density_level(rms, crest, peak_density),
        },
        "master_compression_proxy": {
            "rms_dbfs": rms,
            "crest_factor_db": crest,
            "peak_density_over_minus1db_pct": peak_density,
            "read": density_level(rms, crest, peak_density),
        },
        "target_gaps_against_this_reference": target_gap_against(row, target),
        "core_mix_features_3": core_features(row),
    }


def build_report(features_csv: Path, match_json: Path) -> dict[str, Any]:
    rows = load_rows(features_csv)
    match = load_json(match_json)
    target = next((row for row in rows if row.get("id") == "target_chorus"), match.get("target", {}))
    refs = [row for row in rows if str(row.get("id", "")).startswith("ref_")]
    primary_ids = {item.get("id") for item in match.get("primary_references", []) if item.get("id")}
    entries = [build_reference_entry(row, target, primary_ids) for row in refs]
    return {
        "schema": "goal02-reference-8-track-mix-feature-report-v1",
        "created_at": now_utc(),
        "status": "REFERENCE_8_TRACK_MIX_FEATURE_REPORT_READY_METRIC_PROXIES",
        "claim_policy": "Metrics and measured proxies only; no listening claims; no isolated reference vocal/drum/bass assertions.",
        "source_features_csv": str(features_csv),
        "source_match_json": str(match_json),
        "reference_count": len(entries),
        "primary_reference_ids": sorted(primary_ids),
        "analysis_window_seconds": 20.0,
        "target_id": "target_chorus",
        "target_metrics": {field: parse_float(target.get(field)) for field in METRIC_FIELDS if field in target},
        "references": entries,
    }


def write_markdown(path: Path, report: dict[str, Any]) -> None:
    lines = [
        "# GOAL 02 Reference 8-Track Mix Feature Report",
        "",
        f"- Created UTC: `{report['created_at']}`",
        f"- Status: `{report['status']}`",
        f"- References measured: `{report['reference_count']}` / `8`",
        f"- Primary references: `{', '.join(report['primary_reference_ids'])}`",
        f"- Claim policy: `{report['claim_policy']}`",
        "",
        "## Measurement Limits",
        "",
        "- The references are stereo masters, not separated stems.",
        "- Vocal position, autotune strength, reverb/delay depth, kick/808 separation, and distortion texture are written as measured proxies only.",
        "- True peak is not available in this feature report; sample peak and peak-density are used until FFmpeg loudnorm/true-peak evidence is available for a rendered candidate.",
        "",
        "## Reference Summary Table",
        "",
        "| id | primary | file | RMS | crest | peak density | transient/s | low 20-120 | presence | sibilance | air | corr | 3 core features |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for ref in report["references"]:
        m = ref["metrics"]
        features = "; ".join(ref["core_mix_features_3"])
        lines.append(
            f"| `{ref['id']}` | `{ref['is_primary_reference']}` | `{ref['file']}` | "
            f"`{fmt(m.get('rms_dbfs'))}` | `{fmt(m.get('crest_factor_db'))}` | "
            f"`{fmt(m.get('peak_density_over_minus1db_pct'))}` | `{fmt(m.get('transient_density_per_second'))}` | "
            f"`{fmt(m.get('low_energy_ratio_20_120'), 6)}` | `{fmt(m.get('presence_energy_ratio_2500_6000'), 6)}` | "
            f"`{fmt(m.get('sibilance_energy_ratio_5000_10000'), 6)}` | `{fmt(m.get('air_energy_ratio_10000_16000'), 6)}` | "
            f"`{fmt(m.get('stereo_correlation'), 6)}` | {features} |"
        )
    lines.extend(["", "## Per-Reference Details", ""])
    required_labels = [
        ("overall_loudness_rms_lufs", "Overall Loudness / RMS / LUFS"),
        ("true_peak_peak_density", "True Peak / Peak Density"),
        ("vocal_position_thickness_brightness_proxy", "Vocal Position / Thickness / Brightness Proxy"),
        ("autotune_sibilance_proxy", "Autotune / Sibilance Proxy"),
        ("bass_808_character_proxy", "808 Sub vs Harmonic Proxy"),
        ("kick_808_relationship_proxy", "Kick and 808 Relationship Proxy"),
        ("drum_hihat_proxy", "Drum Transient and Hi-Hat Proxy"),
        ("presence_harshness_air", "2-5 kHz Presence / 6-12 kHz Harshness-Air"),
        ("stereo_width_mono_compatibility", "Stereo Width / Mono Compatibility"),
        ("reverb_delay_depth_proxy", "Reverb / Delay Depth Proxy"),
        ("saturation_clipping_distortion_proxy", "Saturation / Clipping / Distortion Proxy"),
        ("master_compression_proxy", "Master Compression Proxy"),
    ]
    for ref in report["references"]:
        lines.extend(
            [
                f"### {ref['id']} - {ref['file']}",
                "",
                f"- Role: `{ref['role']}`",
                f"- Primary reference: `{ref['is_primary_reference']}`",
                f"- Measurement scope: `{ref['measurement_scope']}`",
                f"- Claim limit: `{ref['claim_limit']}`",
                "",
            ]
        )
        for key, label in required_labels:
            value = ref[key]
            lines.append(f"#### {label}")
            for item_key, item_value in value.items():
                if isinstance(item_value, float):
                    item_value = fmt(item_value, 6)
                lines.append(f"- {item_key}: `{item_value}`")
            lines.append("")
        lines.append("#### Target Gaps Against This Reference")
        for gap in ref["target_gaps_against_this_reference"]:
            lines.append(f"- {gap}")
        lines.append("")
        lines.append("#### Core Mix Features 3")
        for feature in ref["core_mix_features_3"]:
            lines.append(f"- {feature}")
        lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run(args: argparse.Namespace) -> dict[str, Any]:
    report = build_report(args.features_csv.resolve(), args.match_json.resolve())
    args.output_dir.mkdir(parents=True, exist_ok=True)
    json_path = args.output_dir / "goal02_reference_8_track_mix_features.json"
    md_path = args.output_dir / "GOAL02_REFERENCE_8_TRACK_MIX_FEATURES.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    write_markdown(md_path, report)
    report["json_path"] = str(json_path)
    report["report_path"] = str(md_path)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Build Goal 02 per-reference mix feature proxy report.")
    parser.add_argument("--features-csv", type=Path, default=DEFAULT_FEATURES_CSV)
    parser.add_argument("--match-json", type=Path, default=DEFAULT_MATCH_JSON)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()
    report = run(args)
    print(
        json.dumps(
            {
                "status": report["status"],
                "reference_count": report["reference_count"],
                "report_path": report["report_path"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if report["reference_count"] == 8 else 2


if __name__ == "__main__":
    raise SystemExit(main())

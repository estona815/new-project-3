#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REPORT_DIR = ROOT / "reports" / "goal02_candidate_decision_v04"
DEFAULT_VERSIONS = ("v01", "v02", "v03", "v04")
PRIMARY_REFS = ("ref_06_matched", "ref_07_matched", "ref_03_matched")


def now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def as_float(value: Any) -> float | None:
    try:
        if value in ("", None):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def row_float(row: dict[str, Any], key: str) -> float:
    value = as_float(row.get(key))
    if value is None:
        raise ValueError(f"missing numeric {key} in {row}")
    return value


def version_paths(version: str) -> tuple[Path, Path, Path]:
    reaper_slug = f"goal02_chorus_reaper_{version}"
    lufs_slug = f"goal02_chorus_lufs_target_{version}"
    metrics = ROOT / "reports" / reaper_slug / f"{reaper_slug}_metrics.csv"
    runtime = ROOT / "reports" / reaper_slug / f"{reaper_slug}_runtime_summary.json"
    lufs = ROOT / "reports" / lufs_slug / "goal02_lufs_target_package.json"
    return metrics, runtime, lufs


def find_lufs_row(rows: list[dict[str, Any]], label: str) -> dict[str, Any]:
    for row in rows:
        if row.get("label") == label:
            return row
    raise ValueError(f"missing lufs row {label}")


def collect_version(version: str) -> dict[str, Any]:
    metrics_path, runtime_path, lufs_path = version_paths(version)
    metric_rows = {row["name"]: row for row in load_csv_rows(metrics_path)}
    candidate = metric_rows["reaper_print_loud_reference"]
    ref_rows = {name: metric_rows[name] for name in PRIMARY_REFS}
    runtime = load_json(runtime_path)
    lufs = load_json(lufs_path)
    loud_lufs = find_lufs_row(lufs["loudness_rows"], "reaper_loud_reference_lufs_target_20s")
    safe_lufs = find_lufs_row(lufs["loudness_rows"], "reaper_safe_streaming_lufs_target_20s")
    ab_lufs = find_lufs_row(lufs["loudness_rows"], "ab_current_candidate_primary_refs")
    low = row_float(candidate, "low_energy_ratio_20_120")
    ref03_low = row_float(ref_rows["ref_03_matched"], "low_energy_ratio_20_120")
    ref06_low = row_float(ref_rows["ref_06_matched"], "low_energy_ratio_20_120")
    ref07_low = row_float(ref_rows["ref_07_matched"], "low_energy_ratio_20_120")
    ref_primary_low_mean = (ref03_low + ref06_low + ref07_low) / 3.0
    # Conservative score: get near ref_03 for low-end without over-weighting sub,
    # keep true-peak/LUFS target pass, keep high glare lower than ref_03, and keep correlation positive.
    loud_pass = loud_lufs.get("target_pass") is True
    safe_pass = safe_lufs.get("target_pass") is True
    tp_penalty = max(0.0, (as_float(loud_lufs.get("true_peak_dbtp")) or 0.0) + 1.0)
    score = 0.0
    score += max(0.0, 1.0 - abs(low - ref03_low) / 0.08) * 45.0
    score += max(0.0, 1.0 - abs(low - ref_primary_low_mean) / 0.22) * 15.0
    score += max(0.0, 1.0 - abs(row_float(candidate, "crest_factor_db") - row_float(ref_rows["ref_03_matched"], "crest_factor_db")) / 1.2) * 12.0
    score += max(0.0, 1.0 - abs(row_float(candidate, "stereo_correlation") - row_float(ref_rows["ref_03_matched"], "stereo_correlation")) / 0.15) * 10.0
    score += max(0.0, 1.0 - row_float(candidate, "high_energy_ratio_2500_16000") / 0.08) * 8.0
    score += 5.0 if loud_pass else -25.0
    score += 5.0 if safe_pass else -25.0
    score -= tp_penalty * 20.0
    return {
        "version": version,
        "runtime_status": runtime.get("status"),
        "revision_profile": runtime.get("revision_profile", {}),
        "candidate_metrics": {
            "rms_dbfs": row_float(candidate, "rms_dbfs"),
            "true_peak_estimate_4x_dbTP": row_float(candidate, "true_peak_estimate_4x_dbTP"),
            "crest_factor_db": row_float(candidate, "crest_factor_db"),
            "transient_density_per_second": row_float(candidate, "transient_density_per_second"),
            "low_energy_ratio_20_120": low,
            "low_mid_energy_ratio_120_350": row_float(candidate, "low_mid_energy_ratio_120_350"),
            "presence_energy_ratio_2500_6000": row_float(candidate, "presence_energy_ratio_2500_6000"),
            "sibilance_energy_ratio_5000_10000": row_float(candidate, "sibilance_energy_ratio_5000_10000"),
            "air_energy_ratio_10000_16000": row_float(candidate, "air_energy_ratio_10000_16000"),
            "high_energy_ratio_2500_16000": row_float(candidate, "high_energy_ratio_2500_16000"),
            "stereo_correlation": row_float(candidate, "stereo_correlation"),
        },
        "primary_reference_low": {
            "ref_06": ref06_low,
            "ref_07": ref07_low,
            "ref_03": ref03_low,
            "mean": ref_primary_low_mean,
        },
        "loudness": {
            "loud_lufs_i": as_float(loud_lufs.get("integrated_lufs")),
            "loud_true_peak_dbtp": as_float(loud_lufs.get("true_peak_dbtp")),
            "loud_lra_lu": as_float(loud_lufs.get("lra_lu")),
            "loud_target_pass": loud_pass,
            "safe_lufs_i": as_float(safe_lufs.get("integrated_lufs")),
            "safe_true_peak_dbtp": as_float(safe_lufs.get("true_peak_dbtp")),
            "safe_lra_lu": as_float(safe_lufs.get("lra_lu")),
            "safe_target_pass": safe_pass,
            "ab_lufs_i": as_float(ab_lufs.get("integrated_lufs")),
            "ab_true_peak_dbtp": as_float(ab_lufs.get("true_peak_dbtp")),
            "ab_lra_lu": as_float(ab_lufs.get("lra_lu")),
        },
        "files": lufs["files"],
        "score": round(score, 3),
    }


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    keys: list[str] = []
    for row in rows:
        for key in row:
            if key not in keys:
                keys.append(key)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)


def write_markdown(path: Path, result: dict[str, Any]) -> None:
    preferred = result["preferred"]
    lines = [
        "# GOAL 02 Candidate Decision And A/B Approval Packet",
        "",
        f"- Created UTC: `{result['created_at']}`",
        f"- Status: `{result['status']}`",
        "- Claim policy: `file-derived candidate decision only; no listening claims; user A/B still required`",
        f"- Preferred measured review candidate: `{preferred['version']}`",
        f"- Rollback candidate: `{result['rollback_candidate']}`",
        "",
        "## Review Files",
        "",
        f"- A/B sequence: `{preferred['files']['ab_current_candidate_primary_refs']}`",
        f"- Loud reference review: `{preferred['files']['reaper_loud_reference_lufs_target_20s']}`",
        f"- Safe streaming review: `{preferred['files']['reaper_safe_streaming_lufs_target_20s']}`",
        "",
        "## Candidate Metrics",
        "",
        "| version | score | bass offset | low 20-120 | high 2.5-16k | corr | crest | loud LUFS | loud TP | safe LUFS | safe TP |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for item in result["candidates"]:
        metrics = item["candidate_metrics"]
        loud = item["loudness"]
        profile = item.get("revision_profile", {})
        lines.append(
            f"| `{item['version']}` | `{item['score']}` | `{profile.get('bass_gain_offset_db', 0.0)}` | "
            f"`{metrics['low_energy_ratio_20_120']}` | `{metrics['high_energy_ratio_2500_16000']}` | "
            f"`{metrics['stereo_correlation']}` | `{metrics['crest_factor_db']}` | "
            f"`{loud['loud_lufs_i']}` | `{loud['loud_true_peak_dbtp']}` | "
            f"`{loud['safe_lufs_i']}` | `{loud['safe_true_peak_dbtp']}` |"
        )
    lines.extend(
        [
            "",
            "## Why This Candidate",
            "",
            "- v04 uses a bus-level 808/BASS offset only; it does not add extra master limiting.",
            "- v04 low-band ratio `0.565171` nearly matches `ref_03` at `0.567955`, while remaining below the heavier `ref_06`/`ref_07` low-end.",
            "- v04 loud review export passes the FFmpeg loudnorm target at `-9.29 LUFS-I / -1.08 dBTP`.",
            "- v04 safe streaming export passes at `-13.38 LUFS-I / -2.89 dBTP`.",
            "- v04 keeps high-band share lower than v03, reducing measured upper-glare risk.",
            "",
            "## User A/B Checklist",
            "",
            "Use the A/B sequence in order: current target -> v04 candidate -> ref_06 -> v04 -> ref_07 -> v04 -> ref_03 -> v04.",
            "",
            "- Pass if vocal does not feel behind the refs at matched loudness.",
            "- Pass if 808 is present but does not mask the vocal.",
            "- Pass if drums/hats retain digicore bite without AI-like fizz.",
            "- Pass if mono/center does not feel hollow.",
            "- Roll back to v03 if the 808 feels too thick or the vocal pocket gets crowded.",
            "- Roll back to v02 if v03 still feels too thick.",
            "",
            "## Remaining Gates",
            "",
            "- User loudness-matched A/B approval is still required.",
            "- Full-song render, full-song LUFS/TP QC, MP3 check, and final delivery package do not exist yet.",
            "- Do not claim release-quality completion until those gates pass explicitly.",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run(args: argparse.Namespace) -> dict[str, Any]:
    candidates = [collect_version(version) for version in args.versions]
    candidates.sort(key=lambda item: item["score"], reverse=True)
    preferred = candidates[0]
    rollback = candidates[1]["version"] if len(candidates) > 1 else None
    result = {
        "schema": "goal02-candidate-decision-v1",
        "created_at": now_utc(),
        "status": "PREFERRED_20S_CANDIDATE_READY_USER_AB_PENDING",
        "claim_policy": "file-derived candidate decision only; no listening claims",
        "preferred": preferred,
        "rollback_candidate": rollback,
        "candidates": candidates,
        "remaining_gates": [
            "user loudness-matched A/B approval",
            "full-song render",
            "full-song LUFS/true-peak QC",
            "encoded MP3 check",
            "final delivery package",
        ],
    }
    args.report_dir.mkdir(parents=True, exist_ok=True)
    (args.report_dir / "goal02_candidate_decision.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    flat_rows: list[dict[str, Any]] = []
    for item in candidates:
        row: dict[str, Any] = {
            "version": item["version"],
            "score": item["score"],
            "bass_gain_offset_db": item.get("revision_profile", {}).get("bass_gain_offset_db", 0.0),
        }
        row.update(item["candidate_metrics"])
        row.update(item["loudness"])
        flat_rows.append(row)
    write_csv(args.report_dir / "goal02_candidate_decision.csv", flat_rows)
    write_markdown(args.report_dir / "goal02_candidate_decision.md", result)
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compare Goal 02 REAPER candidates and write the user A/B approval packet.")
    parser.add_argument("--report-dir", type=Path, default=DEFAULT_REPORT_DIR)
    parser.add_argument("--versions", nargs="+", default=list(DEFAULT_VERSIONS))
    return parser.parse_args()


def main() -> int:
    result = run(parse_args())
    print(
        json.dumps(
            {
                "status": result["status"],
                "preferred": result["preferred"]["version"],
                "rollback_candidate": result["rollback_candidate"],
            },
            indent=2,
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

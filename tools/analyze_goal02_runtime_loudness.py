#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import imageio_ffmpeg


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SUMMARY = ROOT / "reports" / "goal02_chorus_reaper_v01" / "goal02_chorus_reaper_v01_runtime_summary.json"
DEFAULT_REPORT_DIR = ROOT / "reports" / "goal02_chorus_reaper_v01"

TARGETS = {
    "reaper_print_safe_streaming_20s": {"lufs_min": -14.5, "lufs_max": -12.5, "tp_max": -1.0},
    "reaper_print_loud_reference_20s": {"lufs_min": -9.5, "lufs_max": -8.0, "tp_max": -1.0},
}


def now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def parse_loudnorm_json(text: str) -> dict[str, Any]:
    matches = list(re.finditer(r"\{\s*\"input_i\".*?\}", text, flags=re.S))
    if not matches:
        raise ValueError("ffmpeg loudnorm JSON block not found")
    payload = json.loads(matches[-1].group(0))
    return payload


def as_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def measure_loudnorm(ffmpeg: str, label: str, path: Path) -> dict[str, Any]:
    if not path.exists():
        return {
            "label": label,
            "path": str(path),
            "status": "missing_file",
            "integrated_lufs": None,
            "true_peak_dbtp": None,
            "lra_lu": None,
            "threshold_lufs": None,
        }
    cmd = [
        ffmpeg,
        "-hide_banner",
        "-nostats",
        "-i",
        str(path),
        "-af",
        "loudnorm=I=-14:TP=-1:LRA=11:print_format=json",
        "-f",
        "null",
        "-",
    ]
    proc = subprocess.run(cmd, check=False, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    row: dict[str, Any] = {
        "label": label,
        "path": str(path),
        "status": "measured" if proc.returncode == 0 else "ffmpeg_failed",
        "ffmpeg_returncode": proc.returncode,
        "integrated_lufs": None,
        "true_peak_dbtp": None,
        "lra_lu": None,
        "threshold_lufs": None,
        "target_lufs_min": None,
        "target_lufs_max": None,
        "target_true_peak_max": None,
        "target_pass": None,
        "notes": "",
    }
    if proc.returncode != 0:
        row["notes"] = proc.stderr[-800:]
        return row
    try:
        payload = parse_loudnorm_json(proc.stderr)
    except Exception as exc:
        row["status"] = "parse_failed"
        row["notes"] = f"{exc}; stderr_tail={proc.stderr[-800:]}"
        return row
    row["integrated_lufs"] = as_float(payload.get("input_i"))
    row["true_peak_dbtp"] = as_float(payload.get("input_tp"))
    row["lra_lu"] = as_float(payload.get("input_lra"))
    row["threshold_lufs"] = as_float(payload.get("input_thresh"))
    row["normalization_type"] = payload.get("normalization_type")
    row["target_offset"] = as_float(payload.get("target_offset"))

    target = TARGETS.get(label)
    if target:
        row["target_lufs_min"] = target["lufs_min"]
        row["target_lufs_max"] = target["lufs_max"]
        row["target_true_peak_max"] = target["tp_max"]
        lufs = row["integrated_lufs"]
        tp = row["true_peak_dbtp"]
        row["target_pass"] = (
            lufs is not None
            and tp is not None
            and target["lufs_min"] <= lufs <= target["lufs_max"]
            and tp <= target["tp_max"]
        )
    return row


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


def write_report(path: Path, result: dict[str, Any]) -> None:
    lines = [
        "# GOAL 02 Runtime Loudness Evidence",
        "",
        f"- Created UTC: `{result['created_at']}`",
        f"- Status: `{result['status']}`",
        f"- Meter: `{result['meter']}`",
        "- Claim policy: `file-derived metering only; no listening claims; user A/B still required`",
        "",
        "## Measurements",
        "",
        "| label | LUFS-I | true peak dBTP | LRA LU | target pass |",
        "| --- | ---: | ---: | ---: | --- |",
    ]
    for row in result["rows"]:
        lines.append(
            f"| `{row['label']}` | `{row.get('integrated_lufs')}` | `{row.get('true_peak_dbtp')}` | `{row.get('lra_lu')}` | `{row.get('target_pass')}` |"
        )
    lines.extend(
        [
            "",
            "## Target Notes",
            "",
            "- Safe streaming target: `-14.5` to `-12.5 LUFS-I`, true peak `<= -1.0 dBTP`.",
            "- Loud reference review target: `-9.5` to `-8.0 LUFS-I`, true peak `<= -1.0 dBTP`.",
            "- Primary references are measured after RMS matching to the loud review candidate; they are comparison files, not active mix path inputs.",
            "- This does not replace user loudness-matched A/B approval.",
        ]
    )
    if result.get("next_action"):
        lines.extend(["", "## Next Action", "", result["next_action"]])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def files_from_summary(summary: dict[str, Any]) -> dict[str, Path]:
    files = summary.get("files", {})
    wanted = [
        "current_target_20s",
        "raw_reaper_render",
        "reaper_print_safe_streaming_20s",
        "reaper_print_loud_reference_20s",
        "ref_06_rms_matched_20s",
        "ref_07_rms_matched_20s",
        "ref_03_rms_matched_20s",
        "ab_current_loudmaster_primary_refs",
    ]
    return {key: Path(files[key]) for key in wanted if files.get(key)}


def run(args: argparse.Namespace) -> dict[str, Any]:
    summary = load_json(args.runtime_summary)
    report_dir = args.report_dir
    report_dir.mkdir(parents=True, exist_ok=True)
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    rows = [measure_loudnorm(ffmpeg, label, path) for label, path in files_from_summary(summary).items()]
    measured = [row for row in rows if row["status"] == "measured"]
    target_failures = [row for row in measured if row.get("target_pass") is False]
    status = "LOUDNESS_EVIDENCE_READY_USER_AB_PENDING"
    if len(measured) != len(rows):
        status = "LOUDNESS_EVIDENCE_PARTIAL"
    elif target_failures:
        status = "LOUDNESS_TARGET_CHECK_HAS_FAILURES"
    result = {
        "schema": "goal02-runtime-loudness-evidence-v1",
        "created_at": now_utc(),
        "status": status,
        "meter": "ffmpeg loudnorm input_i/input_tp via imageio_ffmpeg",
        "ffmpeg": ffmpeg,
        "runtime_summary": str(args.runtime_summary),
        "rows": rows,
        "next_action": "Use the loud reference candidate for user A/B. If low-end still feels behind the primary references, make v02 at the 808/BASS BUS before increasing master pressure.",
    }
    (report_dir / "goal02_runtime_loudness_evidence.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    write_csv(report_dir / "goal02_runtime_loudness_evidence.csv", rows)
    write_report(report_dir / "goal02_runtime_loudness_evidence.md", result)
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Measure Goal 02 runtime render LUFS-I/true peak with ffmpeg loudnorm.")
    parser.add_argument("--runtime-summary", type=Path, default=DEFAULT_SUMMARY)
    parser.add_argument("--report-dir", type=Path, default=DEFAULT_REPORT_DIR)
    return parser.parse_args()


def main() -> int:
    result = run(parse_args())
    print(json.dumps({"status": result["status"], "rows": len(result["rows"]), "meter": result["meter"]}, indent=2))
    return 0 if result["status"] != "LOUDNESS_EVIDENCE_PARTIAL" else 1


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import imageio_ffmpeg
import numpy as np
from scipy.io import wavfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.analyze_goal02_runtime_loudness import measure_loudnorm
from tools.render_goal02_chorus_candidate import (
    concatenate_with_silence,
    limit_true_peak_estimate,
    normalize_audio_array,
    write_float_wav,
)


DEFAULT_RUNTIME_SUMMARY = ROOT / "reports" / "goal02_chorus_reaper_v01" / "goal02_chorus_reaper_v01_runtime_summary.json"
DEFAULT_RENDER_DIR = ROOT / "renders" / "goal02_chorus_lufs_target_v01"
DEFAULT_REPORT_DIR = ROOT / "reports" / "goal02_chorus_lufs_target_v01"
DEFAULT_OUTPUT_SLUG = "goal02_lufs_target_v01"


def now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def loudnorm_render(
    ffmpeg: str,
    source: Path,
    dest: Path,
    *,
    target_i: float,
    target_tp: float,
    target_lra: float,
    post_filter: str | None = None,
) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    filter_graph = f"loudnorm=I={target_i}:TP={target_tp}:LRA={target_lra}:linear=false:print_format=summary"
    if post_filter:
        filter_graph = f"{filter_graph},{post_filter}"
    subprocess.run(
        [
            ffmpeg,
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(source),
            "-af",
            filter_graph,
            "-ar",
            "48000",
            "-c:a",
            "pcm_f32le",
            str(dest),
        ],
        check=True,
    )


def filter_render(ffmpeg: str, source: Path, dest: Path, filter_graph: str) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            ffmpeg,
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(source),
            "-af",
            filter_graph,
            "-ar",
            "48000",
            "-c:a",
            "pcm_f32le",
            str(dest),
        ],
        check=True,
    )


def read_wav(path: Path) -> tuple[int, np.ndarray]:
    sample_rate, data = wavfile.read(str(path), mmap=False)
    audio = normalize_audio_array(data)
    if audio.ndim == 1:
        audio = audio[:, None]
    if audio.shape[1] == 1:
        audio = np.repeat(audio, 2, axis=1)
    return int(sample_rate), audio[:, :2]


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
        "# GOAL 02 LUFS Target Package",
        "",
        f"- Created UTC: `{result['created_at']}`",
        f"- Status: `{result['status']}`",
        f"- Meter: `{result['meter']}`",
        "- Claim policy: `file-derived LUFS/TP package only; no listening claims; user A/B still required`",
        "",
        "## Files",
        "",
    ]
    for key, value in result["files"].items():
        lines.append(f"- {key}: `{value}`")
    lines.extend(
        [
            "",
            "## Loudness Measurements",
            "",
            "| label | LUFS-I | true peak dBTP | LRA LU | target pass |",
            "| --- | ---: | ---: | ---: | --- |",
        ]
    )
    for row in result["loudness_rows"]:
        lines.append(
            f"| `{row['label']}` | `{row.get('integrated_lufs')}` | `{row.get('true_peak_dbtp')}` | `{row.get('lra_lu')}` | `{row.get('target_pass')}` |"
        )
    lines.extend(
        [
            "",
            "## Decision Notes",
            "",
            "- This package supersedes the earlier RMS-only loud reference A/B for loudness evaluation.",
            "- The loud review candidate and primary references are LUFS-targeted through the same FFmpeg loudnorm meter path.",
            "- The safe streaming candidate is a separate lower-loudness review export.",
            "- Remaining completion gate: user A/B approval. If the 808 still feels behind, v02 should be bus-level low-end transfer, not more master limiting.",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run(args: argparse.Namespace) -> dict[str, Any]:
    summary = load_json(args.runtime_summary)
    files = summary["files"]
    render_dir = args.render_dir
    report_dir = args.report_dir
    output_slug = args.output_slug
    output_tag = args.output_tag or summary.get("window", {}).get("tag", "20s")
    full_song_mode = summary.get("window", {}).get("mode") == "full-song"
    render_dir.mkdir(parents=True, exist_ok=True)
    report_dir.mkdir(parents=True, exist_ok=True)
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()

    sources = {
        "current_target_20s": Path(files.get("current_target_window", files["current_target_20s"])),
        "raw_reaper_render": Path(files["raw_reaper_render"]),
        "reaper_loud_source": Path(files.get("reaper_print_loud_reference_window", files.get("reaper_print_loud_reference_20s", files["raw_reaper_render"]))),
        "ref_06_source": Path(files.get("ref_06_rms_matched_window", files["ref_06_rms_matched_20s"])),
        "ref_07_source": Path(files.get("ref_07_rms_matched_window", files["ref_07_rms_matched_20s"])),
        "ref_03_source": Path(files.get("ref_03_rms_matched_window", files["ref_03_rms_matched_20s"])),
    }
    out = {
        "current_target_lufs_matched_20s": render_dir / f"{output_slug}_CURRENT_TARGET_LIMITED_MATCH_TO_LOUD_{output_tag}.wav",
        "reaper_safe_streaming_lufs_target_20s": render_dir / f"{output_slug}_REAPER_SAFE_STREAMING_-13p5LUFS_{output_tag}.wav",
        "reaper_loud_reference_lufs_target_20s": render_dir / f"{output_slug}_REAPER_LOUD_REFERENCE_-9p5LUFS_{output_tag}.wav",
        "ref_06_lufs_matched_20s": render_dir / f"{output_slug}_REF_06_MATCHED_-9p5LUFS_{output_tag}.wav",
        "ref_07_lufs_matched_20s": render_dir / f"{output_slug}_REF_07_MATCHED_-9p5LUFS_{output_tag}.wav",
        "ref_03_lufs_matched_20s": render_dir / f"{output_slug}_REF_03_MATCHED_-9p5LUFS_{output_tag}.wav",
    }

    loudnorm_render(ffmpeg, sources["current_target_20s"], out["current_target_lufs_matched_20s"], target_i=-9.5, target_tp=-1.0, target_lra=2.0)
    loudnorm_render(ffmpeg, sources["raw_reaper_render"], out["reaper_safe_streaming_lufs_target_20s"], target_i=-13.5, target_tp=-1.2, target_lra=6.0)
    if full_song_mode:
        filter_render(
            ffmpeg,
            sources["reaper_loud_source"],
            out["reaper_loud_reference_lufs_target_20s"],
            f"volume={args.full_song_loud_gain_db}dB",
        )
    else:
        loudnorm_render(ffmpeg, sources["raw_reaper_render"], out["reaper_loud_reference_lufs_target_20s"], target_i=-8.4, target_tp=-1.0, target_lra=2.0, post_filter="volume=-0.12dB")
    loudnorm_render(ffmpeg, sources["ref_06_source"], out["ref_06_lufs_matched_20s"], target_i=-9.5, target_tp=-1.2, target_lra=2.0)
    loudnorm_render(ffmpeg, sources["ref_07_source"], out["ref_07_lufs_matched_20s"], target_i=-9.5, target_tp=-1.2, target_lra=2.0)
    loudnorm_render(ffmpeg, sources["ref_03_source"], out["ref_03_lufs_matched_20s"], target_i=-9.5, target_tp=-1.2, target_lra=2.0)

    sr, current = read_wav(out["current_target_lufs_matched_20s"])
    _, candidate = read_wav(out["reaper_loud_reference_lufs_target_20s"])
    _, ref_06 = read_wav(out["ref_06_lufs_matched_20s"])
    _, ref_07 = read_wav(out["ref_07_lufs_matched_20s"])
    _, ref_03 = read_wav(out["ref_03_lufs_matched_20s"])
    ab_audio = limit_true_peak_estimate(
        concatenate_with_silence([current, candidate, ref_06, candidate, ref_07, candidate, ref_03, candidate], sr),
        -1.0,
    )
    if output_tag == "20s":
        ab_path = render_dir / f"{output_slug}_AB_CURRENT_CANDIDATE_PRIMARY_REFS.wav"
    else:
        ab_path = render_dir / f"{output_slug}_AB_CURRENT_CANDIDATE_PRIMARY_REFS_{output_tag}.wav"
    write_float_wav(ab_path, sr, ab_audio)
    out["ab_current_candidate_primary_refs"] = ab_path

    loudness_rows = [
        measure_loudnorm(ffmpeg, "current_target_lufs_matched_20s", out["current_target_lufs_matched_20s"]),
        measure_loudnorm(ffmpeg, "reaper_safe_streaming_lufs_target_20s", out["reaper_safe_streaming_lufs_target_20s"]),
        measure_loudnorm(ffmpeg, "reaper_loud_reference_lufs_target_20s", out["reaper_loud_reference_lufs_target_20s"]),
        measure_loudnorm(ffmpeg, "ref_06_lufs_matched_20s", out["ref_06_lufs_matched_20s"]),
        measure_loudnorm(ffmpeg, "ref_07_lufs_matched_20s", out["ref_07_lufs_matched_20s"]),
        measure_loudnorm(ffmpeg, "ref_03_lufs_matched_20s", out["ref_03_lufs_matched_20s"]),
        measure_loudnorm(ffmpeg, "ab_current_candidate_primary_refs", ab_path),
    ]
    for row in loudness_rows:
        if row["label"] == "reaper_safe_streaming_lufs_target_20s":
            row["target_lufs_min"] = -14.5
            row["target_lufs_max"] = -12.5
            row["target_true_peak_max"] = -1.0
            row["target_pass"] = (
                row["integrated_lufs"] is not None
                and -14.5 <= row["integrated_lufs"] <= -12.5
                and row["true_peak_dbtp"] is not None
                and row["true_peak_dbtp"] <= -1.0
            )
        elif row["label"] == "reaper_loud_reference_lufs_target_20s":
            row["target_lufs_min"] = -9.5
            row["target_lufs_max"] = -8.0
            row["target_true_peak_max"] = -1.0
            row["target_pass"] = (
                row["integrated_lufs"] is not None
                and -9.5 <= row["integrated_lufs"] <= -8.0
                and row["true_peak_dbtp"] is not None
                and row["true_peak_dbtp"] <= -1.0
            )

    target_rows = [row for row in loudness_rows if row["label"].startswith("reaper_")]
    status = "LUFS_TARGET_PACKAGE_READY_USER_AB_PENDING"
    if any(row.get("target_pass") is False for row in target_rows):
        status = "LUFS_TARGET_PACKAGE_HAS_TARGET_FAILURES"

    result = {
        "schema": "goal02-lufs-target-package-v1",
        "created_at": now_utc(),
        "status": status,
        "output_slug": output_slug,
        "output_tag": output_tag,
        "full_song_loud_source_policy": "trim_existing_reaper_loud_reference_print" if full_song_mode else "loudnorm_raw_reaper_render",
        "full_song_loud_gain_db": args.full_song_loud_gain_db if full_song_mode else None,
        "meter": "ffmpeg loudnorm input_i/input_tp via imageio_ffmpeg",
        "ffmpeg": ffmpeg,
        "runtime_summary": str(args.runtime_summary),
        "files": {key: str(value) for key, value in out.items()},
        "loudness_rows": loudness_rows,
    }
    (report_dir / "goal02_lufs_target_package.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    write_csv(report_dir / "goal02_lufs_target_package.csv", loudness_rows)
    write_report(report_dir / "goal02_lufs_target_package.md", result)
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build Goal 02 LUFS-targeted safe/loud review and A/B package.")
    parser.add_argument("--runtime-summary", type=Path, default=DEFAULT_RUNTIME_SUMMARY)
    parser.add_argument("--render-dir", type=Path, default=DEFAULT_RENDER_DIR)
    parser.add_argument("--report-dir", type=Path, default=DEFAULT_REPORT_DIR)
    parser.add_argument("--output-slug", default=DEFAULT_OUTPUT_SLUG)
    parser.add_argument("--output-tag", default=None, help="filename tag for generated review files; defaults to runtime summary window tag or 20s")
    parser.add_argument("--full-song-loud-gain-db", type=float, default=-1.6, help="gain trim applied to the existing REAPER loud-reference print in full-song mode")
    return parser.parse_args()


def main() -> int:
    result = run(parse_args())
    print(json.dumps({"status": result["status"], "files": result["files"]}, indent=2, ensure_ascii=False))
    return 0 if result["status"] != "LUFS_TARGET_PACKAGE_HAS_TARGET_FAILURES" else 1


if __name__ == "__main__":
    raise SystemExit(main())

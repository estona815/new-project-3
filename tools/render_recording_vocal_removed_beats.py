#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import shutil
import subprocess
import zipfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import imageio_ffmpeg


ROOT = Path(__file__).resolve().parents[1]
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
TARGET_LUFS = -8.6
TARGET_LRA = 2.5
BASE_CHAIN_TRUE_PEAK = -2.2
TARGET_POST_TRUE_PEAK = -1.35
TARGET_TRUE_PEAK = TARGET_POST_TRUE_PEAK
MP3_TRUE_PEAK_GUARD = -1.10

BASE_LOUD_CHAIN = (
    "highpass=f=24,"
    "compand=attacks=0.002:decays=0.06:"
    "points=-80/-80|-36/-20|-24/-13|-18/-9|-12/-6.5|-6/-4.5|0/-4:"
    "soft-knee=8:gain=11:volume=-4,"
    "asoftclip=type=tanh:threshold=0.55:output=0.66:oversample=4,"
    "loudnorm=I=-8.6:TP=-2.2:LRA=2.5:linear=false,"
    "alimiter=limit=0.64:attack=2:release=140:level=false,"
    "volume=1.4dB"
)

VOCAL_RE = re.compile(r"(vocal|vocals|backing[_ -]?vocals|main[_ -]?vocal|vox|voice|acapella)", re.I)
PLACEHOLDER_RE = re.compile(r"(__missing_.*silence|silence|new track)", re.I)


@dataclass(frozen=True)
class SourceSet:
    slug: str
    folder: Path
    included: tuple[Path, ...]
    excluded: tuple[dict[str, str], ...]


def now_stamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def natural_key(path: Path) -> list[Any]:
    return [int(part) if part.isdigit() else part.lower() for part in re.split(r"(\d+)", path.name)]


def safe_slug(value: str) -> str:
    value = re.sub(r"[^A-Za-z0-9._-]+", "_", value.strip())
    value = re.sub(r"_+", "_", value).strip("._-")
    return value or "stem_set"


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    keys: list[str] = []
    for row in rows:
        for key in row:
            if key not in keys:
                keys.append(key)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)


def run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, check=False, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def checked(cmd: list[str]) -> None:
    proc = run(cmd)
    if proc.returncode != 0:
        raise RuntimeError(f"command failed ({proc.returncode}): {' '.join(cmd)}\n{proc.stderr[-2000:]}")


def parse_loudnorm_json(text: str) -> dict[str, Any]:
    matches = list(re.finditer(r"\{\s*\"input_i\".*?\}", text, flags=re.S))
    if not matches:
        raise ValueError("ffmpeg loudnorm JSON block not found")
    return json.loads(matches[-1].group(0))


def measure_loudnorm(path: Path) -> dict[str, Any]:
    proc = run(
        [
            FFMPEG,
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
    )
    row: dict[str, Any] = {
        "path": rel(path),
        "status": "measured" if proc.returncode == 0 else "ffmpeg_failed",
        "integrated_lufs": None,
        "true_peak_dbtp": None,
        "lra_lu": None,
        "threshold_lufs": None,
        "normalization_type": None,
        "target_offset": None,
    }
    if proc.returncode != 0:
        row["notes"] = proc.stderr[-1000:]
        return row
    try:
        payload = parse_loudnorm_json(proc.stderr)
    except Exception as exc:
        row["status"] = "parse_failed"
        row["notes"] = f"{exc}; stderr_tail={proc.stderr[-1000:]}"
        return row
    row["integrated_lufs"] = as_float(payload.get("input_i"))
    row["true_peak_dbtp"] = as_float(payload.get("input_tp"))
    row["lra_lu"] = as_float(payload.get("input_lra"))
    row["threshold_lufs"] = as_float(payload.get("input_thresh"))
    row["normalization_type"] = payload.get("normalization_type")
    row["target_offset"] = as_float(payload.get("target_offset"))
    row["loud_reference_target_pass"] = target_pass(row)
    return row


def as_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def target_pass(row: dict[str, Any]) -> bool | None:
    lufs = as_float(row.get("integrated_lufs"))
    tp = as_float(row.get("true_peak_dbtp"))
    if lufs is None or tp is None:
        return None
    return -9.5 <= lufs <= -8.0 and tp <= -1.0


def discover_source_sets(include_input_stems: bool) -> list[SourceSet]:
    folders: list[Path] = []
    audio_work = ROOT / "audio_work"
    if audio_work.exists():
        for project in sorted(audio_work.iterdir(), key=natural_key):
            if not project.is_dir():
                continue
            for leaf in ("source_stems", "raw_stems"):
                folder = project / leaf
                if folder.is_dir():
                    folders.append(folder)
    if include_input_stems:
        input_stems = ROOT / "input" / "stems"
        if input_stems.exists():
            folders.extend(sorted([path for path in input_stems.iterdir() if path.is_dir()], key=natural_key))

    source_sets: list[SourceSet] = []
    used_slugs: set[str] = set()
    for folder in folders:
        wavs = sorted(folder.glob("*.wav"), key=natural_key)
        included: list[Path] = []
        excluded: list[dict[str, str]] = []
        for wav in wavs:
            reason = exclusion_reason(wav)
            if reason:
                excluded.append({"path": rel(wav), "reason": reason})
            else:
                included.append(wav)
        if not included:
            continue
        if folder.parent.parent == ROOT / "input":
            base_slug = safe_slug("input_" + folder.name)
        else:
            base_slug = safe_slug(folder.parent.name)
        slug = base_slug
        counter = 2
        while slug in used_slugs:
            slug = f"{base_slug}_{counter}"
            counter += 1
        used_slugs.add(slug)
        source_sets.append(SourceSet(slug=slug, folder=folder, included=tuple(included), excluded=tuple(excluded)))
    return source_sets


def exclusion_reason(path: Path) -> str | None:
    name = path.name
    lower = name.lower()
    if re.match(r"^0\s", name):
        return "full_mix_reference_excluded_from_active_master_path"
    if VOCAL_RE.search(lower):
        return "vocal_or_backing_vocal_excluded"
    if PLACEHOLDER_RE.search(lower):
        return "silence_or_placeholder_excluded"
    return None


def render_raw_mix(source: SourceSet, raw_path: Path) -> None:
    cmd = [FFMPEG, "-y", "-hide_banner", "-loglevel", "error"]
    for stem in source.included:
        cmd.extend(["-i", str(stem)])
    filter_complex = (
        f"amix=inputs={len(source.included)}:duration=longest:dropout_transition=0:normalize=0,"
        "aresample=48000"
    )
    cmd.extend(["-filter_complex", filter_complex, "-ac", "2", "-c:a", "pcm_f32le", str(raw_path)])
    checked(cmd)


def render_base_loud_wav(raw_path: Path, wav_path: Path) -> None:
    checked(
        [
            FFMPEG,
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(raw_path),
            "-af",
            BASE_LOUD_CHAIN,
            "-ar",
            "48000",
            "-ac",
            "2",
            "-c:a",
            "pcm_s24le",
            str(wav_path),
        ]
    )


def apply_gain(input_path: Path, output_path: Path, gain_db: float) -> None:
    checked(
        [
            FFMPEG,
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(input_path),
            "-af",
            f"volume={gain_db:.4f}dB",
            "-ar",
            "48000",
            "-ac",
            "2",
            "-c:a",
            "pcm_s24le",
            str(output_path),
        ]
    )


def target_gain(row: dict[str, Any], lufs_target: float = TARGET_LUFS, tp_target: float = TARGET_POST_TRUE_PEAK) -> float | None:
    lufs = as_float(row.get("integrated_lufs"))
    tp = as_float(row.get("true_peak_dbtp"))
    if lufs is None or tp is None:
        return None
    return min(lufs_target - lufs, tp_target - tp)


def post_adjust_wav(wav_path: Path, work_dir: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    adjustments: list[dict[str, Any]] = []
    qc = measure_loudnorm(wav_path)
    gain = target_gain(qc)
    if gain is None or abs(gain) < 0.05:
        return qc, adjustments

    adjusted = work_dir / f"{wav_path.stem}_post_gain.wav"
    apply_gain(wav_path, adjusted, gain)
    adjusted.replace(wav_path)
    qc = measure_loudnorm(wav_path)
    adjustments.append({"stage": "wav_post_gain", "gain_db": round(gain, 4), "qc_after": qc})
    return qc, adjustments


def guard_mp3_peak(wav_path: Path, mp3_path: Path, work_dir: Path) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    adjustments: list[dict[str, Any]] = []
    wav_qc = measure_loudnorm(wav_path)
    encode_mp3(wav_path, mp3_path)
    mp3_qc = measure_loudnorm(mp3_path)

    mp3_lufs = as_float(mp3_qc.get("integrated_lufs"))
    mp3_tp = as_float(mp3_qc.get("true_peak_dbtp"))
    down_candidates: list[float] = []
    if mp3_lufs is not None and mp3_lufs > -8.0:
        down_candidates.append(-8.3 - mp3_lufs)
    if mp3_tp is not None and mp3_tp > -1.0:
        down_candidates.append(MP3_TRUE_PEAK_GUARD - mp3_tp)
    if not down_candidates:
        return wav_qc, mp3_qc, adjustments

    gain = min(down_candidates)
    if gain < -0.05:
        adjusted = work_dir / f"{wav_path.stem}_mp3_guard.wav"
        apply_gain(wav_path, adjusted, gain)
        adjusted.replace(wav_path)
        wav_qc = measure_loudnorm(wav_path)
        encode_mp3(wav_path, mp3_path)
        mp3_qc = measure_loudnorm(mp3_path)
        adjustments.append({"stage": "mp3_true_peak_guard", "gain_db": round(gain, 4), "wav_qc_after": wav_qc, "mp3_qc_after": mp3_qc})
    return wav_qc, mp3_qc, adjustments


def encode_mp3(wav_path: Path, mp3_path: Path) -> None:
    checked(
        [
            FFMPEG,
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(wav_path),
            "-c:a",
            "libmp3lame",
            "-b:a",
            "320k",
            str(mp3_path),
        ]
    )


def render_source(source: SourceSet, output_dir: Path, temp_dir: Path) -> dict[str, Any]:
    raw_path = temp_dir / f"{source.slug}_raw_instrumental_32f.wav"
    wav_path = output_dir / f"{source.slug}_VOCAL_REMOVED_RECORDING_LOUD_24bit_48k.wav"
    mp3_path = output_dir / f"{source.slug}_VOCAL_REMOVED_RECORDING_LOUD_320k.mp3"
    render_raw_mix(source, raw_path)
    render_base_loud_wav(raw_path, wav_path)
    wav_qc, post_adjustments = post_adjust_wav(wav_path, temp_dir)
    wav_qc, mp3_qc, mp3_adjustments = guard_mp3_peak(wav_path, mp3_path, temp_dir)
    return {
        "slug": source.slug,
        "source_folder": rel(source.folder),
        "included_stems": [rel(path) for path in source.included],
        "excluded_stems": list(source.excluded),
        "raw_intermediate_removed_from_package": True,
        "target": {
            "integrated_lufs": TARGET_LUFS,
            "base_chain_true_peak_dbtp": BASE_CHAIN_TRUE_PEAK,
            "post_gain_true_peak_dbtp": TARGET_POST_TRUE_PEAK,
            "mp3_true_peak_guard_dbtp": MP3_TRUE_PEAK_GUARD,
            "lra_lu": TARGET_LRA,
            "profile": "loud_reference_recording_beat",
        },
        "processing_chain": BASE_LOUD_CHAIN,
        "post_adjustments": post_adjustments + mp3_adjustments,
        "files": {
            "wav": rel(wav_path),
            "mp3": rel(mp3_path),
        },
        "sizes": {
            "wav_bytes": wav_path.stat().st_size,
            "mp3_bytes": mp3_path.stat().st_size,
        },
        "sha256": {
            "wav": sha256_file(wav_path),
            "mp3": sha256_file(mp3_path),
        },
        "qc": {
            "wav": wav_qc,
            "mp3": mp3_qc,
        },
    }


def build_markdown(result: dict[str, Any]) -> str:
    lines = [
        "# Recording Vocal-Removed Beat Batch",
        "",
        f"- Created: `{result['created_at']}`",
        f"- Status: `{result['status']}`",
        f"- Output folder: `{result['output_dir']}`",
        f"- Source sets rendered: `{len(result['items'])}`",
        f"- Loudness target: `{TARGET_LUFS} LUFS-I`, true peak target `{TARGET_TRUE_PEAK} dBTP`",
        "- Claim policy: file-derived rendering/QC only; no listening claims.",
        "- Source policy: full mix/reference files and vocal/backing vocal stems were excluded from the active render path.",
        "",
        "## Rendered Files",
        "",
        "| slug | WAV LUFS | WAV TP | MP3 LUFS | MP3 TP | target pass |",
        "| --- | ---: | ---: | ---: | ---: | --- |",
    ]
    for item in result["items"]:
        wav_qc = item["qc"]["wav"]
        mp3_qc = item["qc"]["mp3"]
        wav_pass = wav_qc.get("loud_reference_target_pass")
        mp3_pass = mp3_qc.get("loud_reference_target_pass")
        lines.append(
            f"| `{item['slug']}` | `{wav_qc.get('integrated_lufs')}` | `{wav_qc.get('true_peak_dbtp')}` | "
            f"`{mp3_qc.get('integrated_lufs')}` | `{mp3_qc.get('true_peak_dbtp')}` | `wav={wav_pass}; mp3={mp3_pass}` |"
        )
    if result.get("warnings"):
        lines.extend(["", "## Warnings", ""])
        lines.extend(f"- `{warning}`" for warning in result["warnings"])
    lines.extend(
        [
            "",
            "## Reproduction",
            "",
            "```sh",
            "python3 tools/render_recording_vocal_removed_beats.py",
            "```",
        ]
    )
    return "\n".join(lines) + "\n"


def package_zip(output_dir: Path, package_path: Path) -> None:
    with zipfile.ZipFile(package_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(output_dir.iterdir(), key=natural_key):
            if path == package_path or path.name.endswith("_raw_instrumental_32f.wav"):
                continue
            archive.write(path, arcname=f"{output_dir.name}/{path.name}")


def run_batch(args: argparse.Namespace) -> dict[str, Any]:
    stamp = args.stamp or now_stamp()
    output_dir = ROOT / "output" / "audio" / f"recording_vocal_removed_beats_loud_{stamp}"
    report_dir = ROOT / "reports" / f"recording_vocal_removed_beats_loud_{stamp}"
    temp_dir = output_dir / "_tmp"
    output_dir.mkdir(parents=True, exist_ok=True)
    report_dir.mkdir(parents=True, exist_ok=True)
    temp_dir.mkdir(parents=True, exist_ok=True)

    sources = discover_source_sets(include_input_stems=not args.no_input_stems)
    if args.limit:
        sources = sources[: args.limit]
    if not sources:
        raise RuntimeError("no source stem folders found")

    items: list[dict[str, Any]] = []
    warnings: list[str] = []
    for index, source in enumerate(sources, start=1):
        print(f"[{index}/{len(sources)}] rendering {source.slug}", flush=True)
        try:
            items.append(render_source(source, output_dir, temp_dir))
        except Exception as exc:
            warnings.append(f"{source.slug}: render_failed: {exc}")
            items.append(
                {
                    "slug": source.slug,
                    "source_folder": rel(source.folder),
                    "included_stems": [rel(path) for path in source.included],
                    "excluded_stems": list(source.excluded),
                    "status": "render_failed",
                    "error": str(exc),
                }
            )
    shutil.rmtree(temp_dir, ignore_errors=True)

    rendered = [item for item in items if item.get("files")]
    failed = [item for item in items if item.get("status") == "render_failed"]
    target_failures = [
        item["slug"]
        for item in rendered
        if item["qc"]["wav"].get("loud_reference_target_pass") is not True
        or item["qc"]["mp3"].get("loud_reference_target_pass") is not True
    ]
    status = "RENDERED_QC_PASS"
    if failed:
        status = "RENDERED_PARTIAL_FAILURE"
    elif target_failures:
        status = "RENDERED_QC_WARNINGS"
        warnings.append("some WAV/MP3 loud-reference target checks did not pass")

    result: dict[str, Any] = {
        "schema": "recording-vocal-removed-beats-batch-v1",
        "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "status": status,
        "ffmpeg": FFMPEG,
        "output_dir": rel(output_dir),
        "report_dir": rel(report_dir),
        "source_policy": {
            "excluded_full_mix_reference": True,
            "excluded_vocal_stems": True,
            "excluded_placeholder_silence": True,
            "raw_originals_modified": False,
        },
        "items": items,
        "warnings": warnings,
    }

    package_path = output_dir / f"{output_dir.name}.zip"
    result["package_zip"] = rel(package_path)

    manifest_path = output_dir / "recording_vocal_removed_beats_manifest.json"
    report_path = output_dir / "recording_vocal_removed_beats_report.md"
    csv_path = output_dir / "recording_vocal_removed_beats_qc.csv"
    write_json(manifest_path, result)
    report_path.write_text(build_markdown(result), encoding="utf-8")
    csv_rows: list[dict[str, Any]] = []
    for item in rendered:
        csv_rows.append(
            {
                "slug": item["slug"],
                "wav": item["files"]["wav"],
                "mp3": item["files"]["mp3"],
                "wav_lufs": item["qc"]["wav"].get("integrated_lufs"),
                "wav_true_peak_dbtp": item["qc"]["wav"].get("true_peak_dbtp"),
                "wav_target_pass": item["qc"]["wav"].get("loud_reference_target_pass"),
                "mp3_lufs": item["qc"]["mp3"].get("integrated_lufs"),
                "mp3_true_peak_dbtp": item["qc"]["mp3"].get("true_peak_dbtp"),
                "mp3_target_pass": item["qc"]["mp3"].get("loud_reference_target_pass"),
            }
        )
    write_csv(csv_path, csv_rows)
    shutil.copy2(manifest_path, report_dir / manifest_path.name)
    shutil.copy2(report_path, report_dir / report_path.name)
    shutil.copy2(csv_path, report_dir / csv_path.name)

    package_zip(output_dir, package_path)
    result["package_zip_bytes"] = package_path.stat().st_size
    result["package_zip_sha256"] = sha256_file(package_path)
    write_json(manifest_path, result)
    shutil.copy2(manifest_path, report_dir / manifest_path.name)
    print(json.dumps({"status": result["status"], "output_dir": rel(output_dir), "package_zip": rel(package_path), "rendered": len(rendered), "failed": len(failed)}, ensure_ascii=False, indent=2))
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render loud recording instrumentals from local stem folders with vocals removed.")
    parser.add_argument("--stamp", help="Optional deterministic output timestamp suffix.")
    parser.add_argument("--limit", type=int, help="Render only the first N source sets for smoke testing.")
    parser.add_argument("--no-input-stems", action="store_true", help="Skip input/stems folders and render audio_work only.")
    return parser.parse_args()


def main() -> int:
    result = run_batch(parse_args())
    return 0 if result["status"] != "RENDERED_PARTIAL_FAILURE" else 1


if __name__ == "__main__":
    raise SystemExit(main())

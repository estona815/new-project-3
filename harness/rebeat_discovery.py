from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

try:
    from .audio_qc import analyze_file
    from .severity import Finding, add_finding, findings_to_dicts, findings_to_markdown, max_severity
except ImportError:  # pragma: no cover
    from audio_qc import analyze_file
    from severity import Finding, add_finding, findings_to_dicts, findings_to_markdown, max_severity


AUDIO_EXTS = {".wav", ".mp3", ".flac", ".aif", ".aiff", ".m4a", ".aac", ".ogg"}
MIDI_EXTS = {".mid", ".midi"}
REPORT_EXTS = {".json", ".md", ".csv", ".txt"}
IGNORE_DIRS = {".git", "__pycache__", ".venv", ".venv_handoff", "build", "external_models", "node_modules"}


def _slug(path: str | Path) -> str:
    stem = Path(path).stem.lower()
    stem = re.sub(r"_v\d+.*$", "", stem)
    stem = re.sub(r"[^a-z0-9가-힣]+", "_", stem).strip("_")
    return stem or "song"


def _is_lossy(path: Path) -> bool:
    return path.suffix.lower() in {".mp3", ".m4a", ".aac", ".ogg"}


def _role(path: Path) -> str:
    name = path.name.lower()
    if "drum" in name or "kick" in name or "snare" in name:
        return "drums"
    if "bass" in name or "808" in name:
        return "bass"
    if any(term in name for term in ("music", "instrument", "synth", "keys", "guitar", "piano", "melody")):
        return "music"
    if "vocal" in name or "vox" in name:
        return "vocal"
    if "ref" in name or "reference" in name:
        return "reference"
    if "master" in name or "fullmix" in name or "full_mix" in name:
        return "fullmix"
    return "unknown"


def _score_folder(folder: Path, source_slug: str) -> dict[str, Any]:
    files = [path for path in folder.rglob("*") if path.is_file()]
    score = 0
    counts = {"audio": 0, "stems": 0, "midi": 0, "rpp": 0, "reports": 0, "samples": 0, "fxchains": 0, "jsfx": 0}
    for path in files:
        lowered = path.name.lower()
        if source_slug and source_slug in lowered:
            score += 12
        suffix = path.suffix.lower()
        if suffix in AUDIO_EXTS:
            counts["audio"] += 1
            score += 2
            if _role(path) in {"drums", "bass", "music", "vocal"}:
                counts["stems"] += 1
                score += 5
            if any(term in lowered for term in ("sample", "oneshot", "one_shot", "kick", "snare", "hat")):
                counts["samples"] += 1
                score += 2
        elif suffix in MIDI_EXTS:
            counts["midi"] += 1
            score += 8
        elif suffix == ".rpp":
            counts["rpp"] += 1
            score += 8
        elif suffix == ".rfxchain":
            counts["fxchains"] += 1
            score += 3
        elif suffix in {".jsfx", ".eel", ".eel2"}:
            counts["jsfx"] += 1
            score += 3
        elif suffix in REPORT_EXTS:
            counts["reports"] += 1
            score += 1
    try:
        newest = max((path.stat().st_mtime for path in files), default=0)
    except OSError:
        newest = 0
    return {"folder": str(folder), "score": score, "counts": counts, "mtime": newest}


def run_rebeat_discovery(project_root: str | Path, source: str | Path | None = None, *, song: str | None = None) -> dict[str, Any]:
    findings: list[Finding] = []
    root = Path(project_root)
    source_path = Path(source) if source else None
    if source_path and not source_path.is_absolute():
        source_path = root / source_path
    source_slug = _slug(source_path or song or "song")

    if source_path and not source_path.exists():
        add_finding(
            "BLOCKER",
            "SELECTED_SOURCE_MISSING",
            "Selected source file is missing.",
            str(source_path),
            "Correct --source and rerun discovery.",
            findings,
            affected_file=str(source_path),
            failed_assumption="Selected source exists.",
        )

    all_files = [
        path
        for path in root.rglob("*")
        if path.is_file() and not any(part in IGNORE_DIRS or part.startswith(".venv") for part in path.parts)
    ]
    related = []
    for path in all_files:
        lowered = path.name.lower()
        if source_slug in lowered or (source_path and path.name == source_path.name):
            related.append(path)
    if source_path and source_path.exists() and source_path not in related:
        related.append(source_path)

    candidate_folders = {}
    for path in related:
        for folder in [path.parent, path.parent.parent if path.parent.parent != path.parent else path.parent]:
            if root in folder.parents or folder == root:
                candidate_folders[str(folder)] = _score_folder(folder, source_slug)
    candidates = sorted(candidate_folders.values(), key=lambda item: (item["score"], item["mtime"]), reverse=True)
    if len(candidates) > 1 and candidates[0]["score"] - candidates[1]["score"] < 10:
        add_finding(
            "WARN",
            "DISCOVERY_FOLDER_AMBIGUOUS",
            "Multiple project folders have similar relevance.",
            json.dumps(candidates[:3], sort_keys=True),
            "Proceed with the highest score but verify source selection before rendering.",
            findings,
            failed_assumption="One project folder is clearly correct.",
            human_listening_required=False,
        )

    files_by_type = {
        "audio": [],
        "stems": [],
        "midi": [],
        "rpp": [],
        "references": [],
        "reports": [],
        "samples": [],
        "fxchains": [],
        "jsfx": [],
    }
    search_pool = related if related else all_files
    for path in search_pool:
        suffix = path.suffix.lower()
        role = _role(path)
        record = {"path": str(path), "role": role, "format": suffix.lstrip(".")}
        if suffix in AUDIO_EXTS:
            files_by_type["audio"].append(record)
            if role in {"drums", "bass", "music", "vocal"}:
                files_by_type["stems"].append(record)
            if role == "reference":
                files_by_type["references"].append(record)
            if any(term in path.name.lower() for term in ("sample", "oneshot", "one_shot", "kick", "snare", "hat")):
                files_by_type["samples"].append(record)
        elif suffix in MIDI_EXTS:
            files_by_type["midi"].append(record)
        elif suffix == ".rpp":
            files_by_type["rpp"].append(record)
        elif suffix == ".rfxchain":
            files_by_type["fxchains"].append(record)
        elif suffix in {".jsfx", ".eel", ".eel2"}:
            files_by_type["jsfx"].append(record)
        elif suffix in REPORT_EXTS:
            files_by_type["reports"].append(record)

    selected_source: dict[str, Any] | None = None
    if source_path and source_path.exists():
        selected_source = {
            "path": str(source_path),
            "format": source_path.suffix.lower().lstrip("."),
            "lossy": _is_lossy(source_path),
        }
        if source_path.suffix.lower() == ".wav":
            try:
                metrics_findings: list[Finding] = []
                metrics = analyze_file(source_path, metrics_findings)
                selected_source.update(
                    {
                        "sample_rate_hz": metrics.get("sample_rate_hz"),
                        "channels": metrics.get("channels"),
                        "duration_sec": metrics.get("duration_sec"),
                    }
                )
                findings.extend(metrics_findings)
            except Exception as exc:
                add_finding(
                    "WARN",
                    "SOURCE_METADATA_PARTIAL",
                    "Source metadata could not be fully analyzed.",
                    str(exc),
                    "Convert source to WAV or run audio_qc separately.",
                    findings,
                    affected_file=str(source_path),
                )
    elif files_by_type["audio"]:
        selected_source = files_by_type["audio"][0]
        selected_source["lossy"] = _is_lossy(Path(selected_source["path"]))

    payload = {
        "schema_version": 1,
        "song_slug": source_slug,
        "project_root": str(root),
        "selected_source": selected_source,
        "source_format": selected_source.get("format") if selected_source else None,
        "source_is_lossy": selected_source.get("lossy") if selected_source else None,
        "candidate_project_folder": candidates[0]["folder"] if candidates else str(root),
        "confidence_score": candidates[0]["score"] if candidates else 0,
        "candidate_folders": candidates[:10],
        "available_stems": files_by_type["stems"],
        "available_midi": files_by_type["midi"],
        "available_rpp": files_by_type["rpp"],
        "available_reference_tracks": files_by_type["references"],
        "available_sample_libraries": files_by_type["samples"],
        "available_fxchains": files_by_type["fxchains"],
        "available_jsfx": files_by_type["jsfx"],
        "reports": files_by_type["reports"][:200],
        "max_severity": max_severity(findings),
        "findings": findings_to_dicts(findings),
    }
    return payload


def markdown_report(payload: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# Rebeat Discovery",
            "",
            f"- Song slug: `{payload.get('song_slug')}`",
            f"- Selected source: `{(payload.get('selected_source') or {}).get('path')}`",
            f"- Source format: `{payload.get('source_format')}`",
            f"- Source lossy: `{payload.get('source_is_lossy')}`",
            f"- Candidate folder: `{payload.get('candidate_project_folder')}`",
            f"- Confidence score: `{payload.get('confidence_score')}`",
            "",
            "## Counts",
            "",
            f"- Stems: `{len(payload.get('available_stems', []))}`",
            f"- MIDI: `{len(payload.get('available_midi', []))}`",
            f"- RPP: `{len(payload.get('available_rpp', []))}`",
            f"- References: `{len(payload.get('available_reference_tracks', []))}`",
            f"- Samples: `{len(payload.get('available_sample_libraries', []))}`",
            "",
            "## Findings",
            "",
            findings_to_markdown([Finding(**finding) for finding in payload.get("findings", [])]),
            "",
        ]
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Discover source/stem/MIDI/RPP evidence for a rebeat workflow.")
    parser.add_argument("--project-root", default=".")
    parser.add_argument("--source")
    parser.add_argument("--song")
    parser.add_argument("--out-json", required=True)
    parser.add_argument("--out-md", required=True)
    args = parser.parse_args(argv)

    payload = run_rebeat_discovery(args.project_root, args.source, song=args.song)
    Path(args.out_json).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out_json).write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    Path(args.out_md).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out_md).write_text(markdown_report(payload), encoding="utf-8")
    return 1 if payload["max_severity"] in {"FAIL", "BLOCKER"} else 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from automix.plugins.plugin_adapter_schema import now_utc, write_json


SNAPSHOT_SCHEMA = "automix-read-only-project-snapshot-v1"
REPORT_SCHEMA = "automix-read-only-guard-report-v1"
PLUGIN_LINE_RE = re.compile(r"^<(?:VST|JS|AU|CLAP|LV2|DX)\b", re.IGNORECASE)
FILE_RE = re.compile(r'FILE\s+"([^"]+)"')


def _sha256(path: Path) -> str:
    if not path.exists() or not path.is_file():
        return ""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _json_tracks(path: Path) -> tuple[list[dict[str, Any]], int, list[str]]:
    warnings: list[str] = []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return [], 0, ["json_project_parse_failed"]
    tracks = data.get("tracks", []) if isinstance(data.get("tracks"), list) else []
    normalized: list[dict[str, Any]] = []
    for idx, track in enumerate(tracks):
        if not isinstance(track, dict):
            warnings.append(f"track_{idx + 1}_not_object")
            continue
        media = track.get("media_items", track.get("items", []))
        fx = track.get("fx", track.get("fx_chain", []))
        sends = track.get("sends", [])
        receives = track.get("receives", [])
        normalized.append(
            {
                "track_index": int(track.get("track_index", idx + 1)),
                "name": str(track.get("name", f"Track {idx + 1}")),
                "track_guid": str(track.get("track_guid", track.get("guid", ""))),
                "fx_count": len(fx) if isinstance(fx, list) else int(fx or 0),
                "media_item_count": len(media) if isinstance(media, list) else int(media or 0),
                "send_count": int(track.get("send_count", len(sends) if isinstance(sends, list) else 0)),
                "receive_count": int(track.get("receive_count", len(receives) if isinstance(receives, list) else 0)),
                "take_pitch_playrate_states": list(track.get("take_pitch_playrate_states", [])),
            }
        )
    master_fx = int(data.get("master_fx_count", len(data.get("master_fx", [])) if isinstance(data.get("master_fx"), list) else 0))
    return normalized, master_fx, warnings


def _rpp_tracks(path: Path) -> tuple[list[dict[str, Any]], int, list[str]]:
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return [], 0, ["rpp_project_read_failed"]

    tracks: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    before_first_track = True
    master_fx_count = 0
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("<TRACK"):
            before_first_track = False
            current = {
                "name": "",
                "track_guid": "",
                "fx_count": 0,
                "media_item_count": 0,
                "send_count": 0,
                "receive_count": 0,
                "take_pitch_playrate_states": [],
            }
            tracks.append(current)
            continue
        if before_first_track and PLUGIN_LINE_RE.match(stripped):
            master_fx_count += 1
            continue
        if current is None:
            continue
        if stripped.startswith("NAME ") and not current.get("name"):
            current["name"] = stripped[5:].strip().strip('"')
        elif stripped.startswith("TRACKID "):
            current["track_guid"] = stripped[8:].strip()
        elif stripped.startswith("<ITEM"):
            current["media_item_count"] += 1
        elif PLUGIN_LINE_RE.match(stripped):
            current["fx_count"] += 1
        elif stripped.startswith("AUXSEND "):
            current["send_count"] += 1
        elif stripped.startswith("AUXRECV "):
            current["receive_count"] += 1
        elif stripped.startswith("PLAYRATE ") or stripped.startswith("PITCH "):
            current["take_pitch_playrate_states"].append(stripped)
        elif stripped.startswith("FILE "):
            match = FILE_RE.search(stripped)
            if match:
                current.setdefault("media_files", []).append(match.group(1))

    normalized = []
    for idx, track in enumerate(tracks):
        normalized.append(
            {
                "track_index": idx + 1,
                "name": track.get("name") or f"Track {idx + 1}",
                "track_guid": track.get("track_guid", ""),
                "fx_count": int(track.get("fx_count", 0)),
                "media_item_count": int(track.get("media_item_count", 0)),
                "send_count": int(track.get("send_count", 0)),
                "receive_count": int(track.get("receive_count", 0)),
                "take_pitch_playrate_states": list(track.get("take_pitch_playrate_states", [])),
            }
        )
    return normalized, master_fx_count, []


def snapshot_project_state(project_path: str | Path | None) -> dict[str, Any]:
    path = Path(project_path).expanduser() if project_path else Path("")
    exists = bool(project_path and path.exists() and path.is_file())
    warnings: list[str] = []
    tracks: list[dict[str, Any]] = []
    master_fx_count = 0
    stat = path.stat() if exists else None
    if not exists:
        warnings.append("project_file_missing_or_not_provided")
    elif path.suffix.lower() == ".json":
        tracks, master_fx_count, warnings = _json_tracks(path)
    else:
        tracks, master_fx_count, warnings = _rpp_tracks(path)

    return {
        "schema": SNAPSHOT_SCHEMA,
        "snapshot_time": now_utc(),
        "project_name": path.stem if project_path else "project",
        "project_path": str(path) if project_path else "",
        "project_exists": exists,
        "project_file_modified_timestamp": stat.st_mtime if stat else None,
        "project_file_size_bytes": stat.st_size if stat else 0,
        "project_file_sha256": _sha256(path) if exists else "",
        "track_count": len(tracks),
        "track_names": [track["name"] for track in tracks],
        "track_guids": [track["track_guid"] for track in tracks],
        "fx_counts_per_track": [track["fx_count"] for track in tracks],
        "media_item_counts": [track["media_item_count"] for track in tracks],
        "take_pitch_playrate_states": [track["take_pitch_playrate_states"] for track in tracks],
        "send_counts": [track["send_count"] for track in tracks],
        "receive_counts": [track["receive_count"] for track in tracks],
        "routing_summary": {
            "send_counts": [track["send_count"] for track in tracks],
            "receive_counts": [track["receive_count"] for track in tracks],
        },
        "master_fx_count": master_fx_count,
        "tracks": tracks,
        "warnings": warnings,
    }


def compare_project_snapshots(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    fields = [
        "project_file_modified_timestamp",
        "project_file_size_bytes",
        "project_file_sha256",
        "track_count",
        "track_names",
        "track_guids",
        "fx_counts_per_track",
        "media_item_counts",
        "take_pitch_playrate_states",
        "send_counts",
        "receive_counts",
        "routing_summary",
        "master_fx_count",
    ]
    modifications = []
    for field in fields:
        if before.get(field) != after.get(field):
            modifications.append(
                {
                    "field": field,
                    "before": before.get(field),
                    "after": after.get(field),
                }
            )
    return {
        "modified": bool(modifications),
        "modification_detected": modifications,
        "safe": not modifications,
    }


def build_read_only_guard_report(
    *,
    project_name: str,
    output_dir: Path,
    before_snapshot: dict[str, Any],
    after_snapshot: dict[str, Any],
    warnings: list[str] | None = None,
) -> dict[str, Any]:
    comparison = compare_project_snapshots(before_snapshot, after_snapshot)
    report = {
        "schema": REPORT_SCHEMA,
        "project_name": project_name,
        "read_only_mode": True,
        "before_snapshot": before_snapshot,
        "after_snapshot": after_snapshot,
        "modified": comparison["modified"],
        "modification_detected": comparison["modification_detected"],
        "safe": comparison["safe"],
        "warnings": sorted(set((warnings or []) + before_snapshot.get("warnings", []) + after_snapshot.get("warnings", []))),
    }
    write_json(output_dir / "real_project" / "read_only_guard_report.json", report)
    return report
